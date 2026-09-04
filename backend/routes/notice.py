# backend/routes/notice.py
"""启事发布 + 查看（随机分配+筛选+配额）"""
import re
from datetime import datetime, date
from flask import Blueprint, request, jsonify
from sqlalchemy import func, and_
from models import db, User, Notice, NoticeView
from services.quota_service import get_membership_limit, get_quota_info


notice_bp = Blueprint('notice', __name__)


def _mask_phone(phone):
    """手机号脱敏：138****1234（非 11 位原样返回）"""
    if not phone or len(phone) != 11:
        return phone
    return phone[:3] + '****' + phone[7:]


def _get_user(user_id=None, phone=None):
    """从请求参数/header中获取用户"""
    if user_id:
        return User.query.get(int(user_id))
    if phone:
        return User.query.filter_by(phone=phone).first()
    return None


@notice_bp.route('/publish', methods=['POST'])
def publish():
    """发布启事"""
    data = request.get_json() or {}
    phone = (data.get('phone') or '').strip()
    name = (data.get('name') or '').strip()
    gender = data.get('gender', '')

    # 校验必填项
    if not phone or not re.match(r'^1[3-9]\d{9}$', phone):
        return jsonify(code=400, msg='请输入正确的手机号码'), 400
    if not name:
        return jsonify(code=400, msg='请输入姓名'), 400
    if not gender:
        return jsonify(code=400, msg='请选择性别'), 400
    birthday = data.get('birthday', '')
    if not birthday:
        return jsonify(code=400, msg='请选择生日'), 400

    # 生日/年龄校验：格式合法 + 不晚于今天 + 年满18周岁
    try:
        birth_date = datetime.strptime(birthday, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify(code=400, msg='生日格式不正确'), 400
    today = date.today()
    if birth_date > today:
        return jsonify(code=400, msg='生日不能晚于今天'), 400
    # 精确计算周岁年龄（考虑月份/日期）
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    if age < 18:
        return jsonify(code=400, msg='本平台仅面向年满18周岁的用户'), 400

    # 查找或创建用户
    user = User.query.filter_by(phone=phone).first()
    if user:
        user.name = name
        user.gender = gender
        user.birthday = data.get('birthday', '')
        user.occupation = data.get('occupation', '')
        user.income = data.get('income', '')
        user.is_public_sector = data.get('isPublicSector', False)
        user.height = data.get('height', 0) or 0
        user.weight = data.get('weight', 0) or 0
        user.updated_at = datetime.utcnow()
    else:
        user = User(
            phone=phone,
            name=name,
            gender=gender,
            birthday=data.get('birthday', ''),
            occupation=data.get('occupation', ''),
            income=data.get('income', ''),
            is_public_sector=data.get('isPublicSector', False),
            height=data.get('height', 0) or 0,
            weight=data.get('weight', 0) or 0,
            membership_type='free',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(user)
        db.session.flush()

    # 一个手机号可发布多条启事，始终新增
    notice = Notice(
        user_id=user.id,
        phone=phone,
        name=name,
        nickname=data.get('nickname', ''),
        gender=gender,
        birthday=data.get('birthday', ''),
        occupation=data.get('occupation', ''),
        income=data.get('income', ''),
        is_public_sector=data.get('isPublicSector', False),
        height=data.get('height', 0) or 0,
        weight=data.get('weight', 0) or 0,
        remark=data.get('remark', ''),
        source='user',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.session.add(notice)
    db.session.flush()
    notice_id = notice.id

    db.session.commit()

    return jsonify(code=0, msg='发布成功', data={
        'noticeId': str(notice_id),
        'userId': str(user.id)
    })


@notice_bp.route('/update/<int:notice_id>', methods=['POST'])
def update_notice(notice_id):
    """修改已有启事"""
    notice = Notice.query.get(notice_id)
    if not notice:
        return jsonify(code=404, msg='启事不存在'), 404

    data = request.get_json() or {}
    notice.name = (data.get('name') or '').strip()
    notice.nickname = (data.get('nickname') or '').strip()
    notice.gender = data.get('gender', notice.gender)
    notice.birthday = data.get('birthday', notice.birthday)
    notice.occupation = data.get('occupation', '')
    notice.income = data.get('income', '')
    notice.is_public_sector = data.get('isPublicSector', False)
    notice.height = data.get('height', 0) or 0
    notice.weight = data.get('weight', 0) or 0
    notice.remark = data.get('remark', '')
    notice.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify(code=0, msg='修改成功', data={
        'noticeId': str(notice.id)
    })


@notice_bp.route('/list', methods=['GET'])
def get_notices():
    """启事分配：free/member每月1号分配，vip每天分配，分配后可反复查看"""
    user_id = request.args.get('userId') or request.headers.get('X-User-Id')
    if not user_id:
        return jsonify(code=401, msg='请先登录'), 401

    user = User.query.get(int(user_id))
    if not user:
        return jsonify(code=401, msg='用户不存在'), 401

    today = date.today()
    period_type, period_limit = get_membership_limit(user)

    # 筛选条件
    gender = request.args.get('gender')
    min_height = request.args.get('minHeight', type=int)
    max_height = request.args.get('maxHeight', type=int)
    min_age = request.args.get('minAge', type=int)
    max_age = request.args.get('maxAge', type=int)
    income = request.args.get('income')
    is_public_sector = request.args.get('isPublicSector')
    occupation = request.args.get('occupation')

    # 判断当前周期是否已分配
    if period_type == 'daily':
        period_start = datetime(today.year, today.month, today.day)
    else:
        period_start = datetime(today.year, today.month, 1)

    period_view_count = NoticeView.query.filter(
        NoticeView.user_id == user.id,
        NoticeView.viewed_at >= period_start
    ).count()

    if period_view_count == 0:
        # 新周期：随机分配启事，排除历史上已分配过的
        all_assigned_ids = [v.notice_id for v in NoticeView.query.filter_by(user_id=user.id).all()]

        query = Notice.query.filter(Notice.user_id != user.id)
        if all_assigned_ids:
            query = query.filter(Notice.id.notin_(all_assigned_ids))
        if gender:
            query = query.filter(Notice.gender == gender)
        if min_height:
            query = query.filter(Notice.height >= min_height)
        if max_height:
            query = query.filter(Notice.height <= max_height)
        if income:
            query = query.filter(Notice.income == income)
        if is_public_sector is not None:
            query = query.filter(Notice.is_public_sector == (is_public_sector.lower() == 'true'))
        if occupation:
            query = query.filter(Notice.occupation.like(f'%{occupation}%'))
        if min_age:
            max_birth = f'{today.year - min_age}-{today.month:02d}-{today.day:02d}'
            query = query.filter(Notice.birthday <= max_birth)
        if max_age:
            min_birth = f'{today.year - max_age - 1}-{today.month:02d}-{today.day:02d}'
            query = query.filter(Notice.birthday >= min_birth)

        total = query.count()
        assign_count = min(period_limit, total)

        if assign_count > 0:
            assign_ids = [row[0] for row in query.with_entities(Notice.id).order_by(func.rand()).limit(assign_count).all()]
            for nid in assign_ids:
                db.session.add(NoticeView(user_id=user.id, notice_id=nid, viewed_at=datetime.utcnow()))
            db.session.commit()

    # 查询当前周期已分配的启事
    assigned_views = NoticeView.query.filter(
        NoticeView.user_id == user.id,
        NoticeView.viewed_at >= period_start
    ).all()
    assigned_ids = [v.notice_id for v in assigned_views]

    if not assigned_ids:
        return jsonify(code=0, data={
            'notices': [],
            'remaining': 0,
            'membershipType': user.membership_type,
            'periodType': period_type,
            'limitReached': False
        })

    nq = Notice.query.filter(Notice.id.in_(assigned_ids))
    if gender:
        nq = nq.filter(Notice.gender == gender)
    if min_height:
        nq = nq.filter(Notice.height >= min_height)
    if max_height:
        nq = nq.filter(Notice.height <= max_height)
    if income:
        nq = nq.filter(Notice.income == income)
    if is_public_sector is not None:
        nq = nq.filter(Notice.is_public_sector == (is_public_sector.lower() == 'true'))
    if occupation:
        nq = nq.filter(Notice.occupation.like(f'%{occupation}%'))
    if min_age:
        max_birth = f'{today.year - min_age}-{today.month:02d}-{today.day:02d}'
        nq = nq.filter(Notice.birthday <= max_birth)
    if max_age:
        min_birth = f'{today.year - max_age - 1}-{today.month:02d}-{today.day:02d}'
        nq = nq.filter(Notice.birthday >= min_birth)

    notices = nq.all()
    quota = get_quota_info(user, len(assigned_ids))

    # 手机号脱敏（完整号需通过 viewPhone 接口按需获取）
    notice_list = [n.to_dict() for n in notices]
    for item in notice_list:
        item['phone'] = _mask_phone(item['phone'])

    return jsonify(code=0, data={
        'notices': notice_list,
        'remaining': quota['remaining'],
        'membershipType': user.membership_type,
        'periodType': period_type,
        'limitReached': False
    })


@notice_bp.route('/history', methods=['GET'])
def get_notice_history():
    """历史查看：系统每月/每天分配给用户的所有启事（跨周期汇总）"""
    user_id = request.args.get('userId') or request.headers.get('X-User-Id')
    if not user_id:
        return jsonify(code=401, msg='请先登录'), 401

    user = User.query.get(int(user_id))
    if not user:
        return jsonify(code=401, msg='用户不存在'), 401

    # 按分配时间倒序取出所有历史分配记录
    views = NoticeView.query.filter_by(user_id=user.id).order_by(NoticeView.viewed_at.desc()).all()
    notice_ids = [v.notice_id for v in views]

    if not notice_ids:
        return jsonify(code=0, data={'notices': []})

    notices = Notice.query.filter(Notice.id.in_(notice_ids)).all()
    notice_map = {n.id: n for n in notices}

    # 保持分配时间倒序
    ordered = [notice_map[nid] for nid in notice_ids if nid in notice_map]

    # 手机号脱敏（完整号需通过 viewPhone 接口按需获取）
    notice_list = [n.to_dict() for n in ordered]
    for item in notice_list:
        item['phone'] = _mask_phone(item['phone'])

    return jsonify(code=0, data={'notices': notice_list})


@notice_bp.route('/viewPhone', methods=['POST'])
def view_phone():
    """查看完整手机号（需登录；查看其他用户启事时按需获取）"""
    user_id = request.args.get('userId') or request.headers.get('X-User-Id')
    if not user_id:
        return jsonify(code=401, msg='请先登录'), 401

    user = User.query.get(int(user_id))
    if not user:
        return jsonify(code=401, msg='用户不存在'), 401

    data = request.get_json() or {}
    notice_id = data.get('noticeId')
    if not notice_id:
        return jsonify(code=400, msg='缺少启事ID'), 400

    notice = Notice.query.get(int(notice_id))
    if not notice:
        return jsonify(code=404, msg='启事不存在'), 404

    return jsonify(code=0, data={
        'noticeId': str(notice.id),
        'name': notice.name,
        'phone': notice.phone
    })


@notice_bp.route('/delete/<int:notice_id>', methods=['POST'])
def delete_notice(notice_id):
    """删除启事（仅启事所有者可操作）

    删除内容：启事本身 + 关联的浏览记录(notice_views)
    """
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        return jsonify(code=401, msg='请先登录'), 401

    user = User.query.get(int(user_id))
    if not user:
        return jsonify(code=401, msg='用户不存在'), 401

    notice = Notice.query.get(notice_id)
    if not notice:
        return jsonify(code=404, msg='启事不存在'), 404

    # 权限校验：只有启事所有者才能删除
    if notice.user_id != user.id:
        return jsonify(code=403, msg='无权删除他人启事'), 403

    # 先删除关联的浏览记录
    NoticeView.query.filter_by(notice_id=notice_id).delete()
    # 再删除启事本身
    db.session.delete(notice)
    db.session.commit()

    return jsonify(code=0, msg='删除成功', data={
        'noticeId': str(notice_id)
    })
