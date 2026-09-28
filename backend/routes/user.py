# backend/routes/user.py
"""用户信息"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from models import db, User, Notice, NoticeView, MembershipOrder, UserBlock
from services.quota_service import get_membership_limit, get_quota_info
from utils.sms_service import sms_service
from utils.file_cleaner import delete_notice_images

user_bp = Blueprint('user', __name__)


@user_bp.route('/profile', methods=['GET'])
def get_profile():
    """获取用户信息及配额"""
    user_id = request.args.get('userId') or request.headers.get('X-User-Id')
    phone = request.args.get('phone')

    user = None
    if user_id:
        user = User.query.get(int(user_id))
    elif phone:
        user = User.query.filter_by(phone=phone).first()

    if not user:
        return jsonify(code=401, msg='用户不存在'), 401

    # 启事数量（按user_id或手机号匹配）
    notice_count = Notice.query.filter(
        (Notice.user_id == user.id) | (Notice.phone == user.phone)
    ).count()

    # 当前周期已分配启事数
    period_type, period_limit = get_membership_limit(user)
    db.session.commit()
    now = datetime.utcnow()
    if period_type == 'daily':
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    assigned_count = NoticeView.query.filter(
        NoticeView.user_id == user.id,
        NoticeView.viewed_at >= period_start
    ).count()
    quota = get_quota_info(user, assigned_count)

    user_dict = user.to_dict()
    user_dict['noticeCount'] = notice_count

    return jsonify(code=0, data={
        'user': user_dict,
        'quota': quota
    })


@user_bp.route('/notices', methods=['GET'])
def get_my_notices():
    """获取我的启事列表（按user_id或手机号匹配）"""

    user_id = request.args.get('userId') or request.headers.get('X-User-Id')

    if not user_id:
        return jsonify(code=401, msg='请先登录'), 401

    user = User.query.get(int(user_id))
    if not user:
        return jsonify(code=401, msg='用户不存在'), 401

    notices = Notice.query.filter(
        (Notice.user_id == int(user_id)) | (Notice.phone == user.phone)
    ).order_by(Notice.created_at.desc()).all()

    return jsonify(code=0, data={
        'notices': [n.to_dict() for n in notices]
    })


@user_bp.route('/deleteAccount', methods=['POST'])
def delete_account():
    """注销账号：短信验证码校验后，删除用户及其全部关联数据与上传图片（启事、查看记录、会员订单）"""
    user_id = request.args.get('userId') or request.headers.get('X-User-Id')
    if not user_id:
        return jsonify(code=401, msg='请先登录'), 401

    user = User.query.get(int(user_id))
    if not user:
        return jsonify(code=401, msg='用户不存在'), 401

    # 1. 强安全校验：必须验证短信验证码，防误操作或他人盗用
    data = request.get_json(silent=True) or {}
    code = str(data.get('code') or '').strip()
    if not code:
        return jsonify(code=400, msg='请输入短信验证码'), 400

    if not sms_service.verify_code(user.phone, code):
        return jsonify(code=400, msg='验证码错误或已过期'), 400

    try:
        # 2. 查找该用户的启事（含系统导入但手机号属于该用户的启事）
        own_notices = Notice.query.filter(
            (Notice.user_id == user.id) | (Notice.phone == user.phone)
        ).all()
        own_notice_ids = [n.id for n in own_notices]

        # 3. 清理启事上传在服务器本地的物理图片文件
        for n in own_notices:
            if n.images:
                delete_notice_images(n.images)

        # 4. 删除这些启事被其他用户查看的记录（避免外键残留）
        if own_notice_ids:
            NoticeView.query.filter(NoticeView.notice_id.in_(own_notice_ids)).delete(synchronize_session=False)

        # 5. 删除启事本身
        for n in own_notices:
            db.session.delete(n)

        # 6. 删除该用户的查看记录
        NoticeView.query.filter(NoticeView.user_id == user.id).delete(synchronize_session=False)

        # 7. 删除该用户的会员订单
        MembershipOrder.query.filter(MembershipOrder.user_id == user.id).delete(synchronize_session=False)

        # 8. 删除用户
        deleted_user_id = user.id
        db.session.delete(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify(code=500, msg=f'注销失败: {str(e)}'), 500

    return jsonify(code=0, msg='注销成功，您的个人信息及关联启事已全部删除', data={
        'deletedUserId': str(deleted_user_id)
    })


@user_bp.route('/block', methods=['POST'])
def block_user():
    """UGC 用户拉黑/屏蔽接口（审核合规刚需）"""
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        return jsonify(code=401, msg='请先登录后再操作'), 401

    user = User.query.get(int(user_id))
    if not user:
        return jsonify(code=401, msg='用户不存在'), 401

    data = request.get_json() or {}
    target_user_id = data.get('targetUserId')
    notice_id = data.get('noticeId')

    # 若未直接传 targetUserId，尝试从 noticeId 获取
    if not target_user_id and notice_id:
        notice = Notice.query.get(int(notice_id))
        if notice:
            target_user_id = notice.user_id

    if not target_user_id:
        return jsonify(code=400, msg='请指定要屏蔽的目标用户'), 400

    target_user_id = int(target_user_id)
    if target_user_id == user.id:
        return jsonify(code=400, msg='不能屏蔽自己'), 400

    # 查重后入库
    existing = UserBlock.query.filter_by(user_id=user.id, blocked_user_id=target_user_id).first()
    if not existing:
        block = UserBlock(user_id=user.id, blocked_user_id=target_user_id)
        db.session.add(block)
        db.session.commit()

    return jsonify(code=0, msg='已屏蔽该用户，平台将不再为您推荐其发布的相亲启事')

