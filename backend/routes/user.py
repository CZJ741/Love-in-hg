# backend/routes/user.py
"""用户信息"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from models import db, User, Notice, NoticeView, MembershipOrder
from services.quota_service import get_membership_limit, get_quota_info

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
    """注销账号：删除用户及其全部关联数据（启事、查看记录、会员订单）"""
    user_id = request.args.get('userId') or request.headers.get('X-User-Id')
    if not user_id:
        return jsonify(code=401, msg='请先登录'), 401

    user = User.query.get(int(user_id))
    if not user:
        return jsonify(code=401, msg='用户不存在'), 401

    try:
        # 1. 查找该用户的启事（含系统导入但手机号属于该用户的启事）
        own_notices = Notice.query.filter(
            (Notice.user_id == user.id) | (Notice.phone == user.phone)
        ).all()
        own_notice_ids = [n.id for n in own_notices]

        # 2. 删除这些启事被其他用户查看的记录（避免外键残留）
        if own_notice_ids:
            NoticeView.query.filter(NoticeView.notice_id.in_(own_notice_ids)).delete(synchronize_session=False)

        # 3. 删除启事本身
        for n in own_notices:
            db.session.delete(n)

        # 4. 删除该用户的查看记录
        NoticeView.query.filter(NoticeView.user_id == user.id).delete(synchronize_session=False)

        # 5. 删除该用户的会员订单
        MembershipOrder.query.filter(MembershipOrder.user_id == user.id).delete(synchronize_session=False)

        # 6. 删除用户
        deleted_user_id = user.id
        db.session.delete(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify(code=500, msg=f'注销失败: {str(e)}'), 500

    return jsonify(code=0, msg='注销成功，您的个人信息已全部删除', data={
        'deletedUserId': str(deleted_user_id)
    })
