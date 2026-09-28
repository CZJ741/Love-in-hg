# backend/routes/admin.py
"""
管理后台完整 REST API：
1. 管理员登录/登出/个人信息
2. 运营仪表盘（Dashboard 核心指标与统计趋势）
3. 启事全生命周期管理（分页列表、多维筛选、详情、编辑、上下架、置顶、删除）
4. 用户与会员管理（列表筛选、手动调整会员等级、调整到期时间、修改配额）
5. 订单与支付管理（订单查询、手动补单核销）
6. 智能文本解析提取与种子数据导入
"""
import json
import os
import re
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g
from sqlalchemy import func, or_, and_, desc
from models import db, User, Notice, NoticeView, MembershipOrder, Report, UserBlock
from config import Config
from services.extract_service import extract_key_values, try_parse_json
from utils.admin_auth import generate_admin_token, admin_required

admin_bp = Blueprint('admin', __name__)


# ============================================================
# 一、管理员认证模块
# ============================================================

@admin_bp.route('/login', methods=['POST'])
def admin_login():
    """管理员登录接口"""
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if not username or not password:
        return jsonify(code=400, msg='请输入用户名和密码'), 400

    target_user = Config.ADMIN_USERNAME
    target_pwd = Config.ADMIN_PASSWORD

    if username != target_user or password != target_pwd:
        return jsonify(code=401, msg='用户名或密码错误'), 401

    token = generate_admin_token(username)
    return jsonify(code=0, msg='登录成功', data={
        'token': token,
        'user': {
            'username': username,
            'role': 'super_admin',
            'name': '系统超级管理员'
        }
    })


@admin_bp.route('/info', methods=['GET'])
@admin_required
def admin_info():
    """获取当前登录管理员信息"""
    return jsonify(code=0, data={
        'username': g.admin_username,
        'role': 'super_admin',
        'name': '系统超级管理员',
        'roles': ['admin']
    })


@admin_bp.route('/logout', methods=['POST'])
@admin_required
def admin_logout():
    """退出登录"""
    return jsonify(code=0, msg='已成功退出登录')


# ============================================================
# 二、仪表盘与统计分析模块
# ============================================================

@admin_bp.route('/dashboard/stats', methods=['GET'])
@admin_required
def dashboard_stats():
    """获取管理后台运营仪表盘核心统计指标"""
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    yesterday_start = today_start - timedelta(days=1)

    # 1. 核心数字指标
    total_users = User.query.count()
    today_users = User.query.filter(User.created_at >= today_start).count()

    total_notices = Notice.query.count()
    today_notices = Notice.query.filter(Notice.created_at >= today_start).count()

    # 会员等级统计
    free_users = User.query.filter_by(membership_type='free').count()
    member_users = User.query.filter_by(membership_type='member').count()
    vip_users = User.query.filter_by(membership_type='vip').count()

    # 财务数据 (单位分 -> 转换成元)
    paid_orders = MembershipOrder.query.filter_by(status='paid').all()
    total_revenue_cents = sum(o.amount for o in paid_orders)
    total_revenue = round(total_revenue_cents / 100.0, 2)

    today_paid_orders = MembershipOrder.query.filter(
        MembershipOrder.status == 'paid',
        MembershipOrder.paid_at >= today_start
    ).all()
    today_revenue_cents = sum(o.amount for o in today_paid_orders)
    today_revenue = round(today_revenue_cents / 100.0, 2)

    total_views = NoticeView.query.count()
    today_views = NoticeView.query.filter(NoticeView.viewed_at >= today_start).count()

    # 2. 性别与年龄分布
    male_count = Notice.query.filter_by(gender='男').count()
    female_count = Notice.query.filter_by(gender='女').count()

    # 3. 近 7 天趋势走势
    trend_dates = []
    trend_user_counts = []
    trend_notice_counts = []
    trend_order_revenues = []

    for i in range(6, -1, -1):
        day_date = (now - timedelta(days=i)).date()
        day_start = datetime(day_date.year, day_date.month, day_date.day)
        day_end = day_start + timedelta(days=1)
        day_label = day_date.strftime('%m-%d')
        trend_dates.append(day_label)

        u_cnt = User.query.filter(User.created_at >= day_start, User.created_at < day_end).count()
        trend_user_counts.append(u_cnt)

        n_cnt = Notice.query.filter(Notice.created_at >= day_start, Notice.created_at < day_end).count()
        trend_notice_counts.append(n_cnt)

        d_orders = MembershipOrder.query.filter(
            MembershipOrder.status == 'paid',
            MembershipOrder.paid_at >= day_start,
            MembershipOrder.paid_at < day_end
        ).all()
        d_rev = round(sum(o.amount for o in d_orders) / 100.0, 2)
        trend_order_revenues.append(d_rev)

    return jsonify(code=0, data={
        'overview': {
            'totalUsers': total_users,
            'todayUsers': today_users,
            'totalNotices': total_notices,
            'todayNotices': today_notices,
            'totalRevenue': total_revenue,
            'todayRevenue': today_revenue,
            'totalViews': total_views,
            'todayViews': today_views,
            'membership': {
                'free': free_users,
                'member': member_users,
                'vip': vip_users
            },
            'gender': {
                'male': male_count,
                'female': female_count
            }
        },
        'trends': {
            'dates': trend_dates,
            'users': trend_user_counts,
            'notices': trend_notice_counts,
            'revenues': trend_order_revenues
        }
    })


# ============================================================
# 三、启事管理模块 (CRUD + 批量操作)
# ============================================================

@admin_bp.route('/notices', methods=['GET'])
@admin_required
def admin_get_notices():
    """启事列表分页与多维筛选"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('pageSize', 10, type=int)
    keyword = (request.args.get('keyword') or '').strip()
    gender = request.args.get('gender')
    source = request.args.get('source')
    housing_location = request.args.get('housingLocation')
    is_public_sector = request.args.get('isPublicSector')

    query = Notice.query

    if keyword:
        # 支持手机号、姓名、职业、昵称搜索
        query = query.filter(or_(
            Notice.name.ilike(f'%{keyword}%'),
            Notice.phone.ilike(f'%{keyword}%'),
            Notice.nickname.ilike(f'%{keyword}%'),
            Notice.occupation.ilike(f'%{keyword}%')
        ))

    if gender:
        query = query.filter(Notice.gender == gender)
    if source:
        query = query.filter(Notice.source == source)
    if housing_location:
        query = query.filter(Notice.housing_location == housing_location)
    if is_public_sector is not None and is_public_sector != '':
        is_ps = str(is_public_sector).lower() in ('true', '1')
        query = query.filter(Notice.is_public_sector == is_ps)

    total = query.count()
    items = query.order_by(Notice.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return jsonify(code=0, data={
        'total': total,
        'page': page,
        'pageSize': page_size,
        'list': [item.to_dict() for item in items]
    })


@admin_bp.route('/notices/<int:notice_id>', methods=['GET'])
@admin_required
def admin_get_notice_detail(notice_id):
    """获取单个启事完整未脱敏信息"""
    notice = Notice.query.get(notice_id)
    if not notice:
        return jsonify(code=404, msg='启事不存在'), 404
    return jsonify(code=0, data=notice.to_dict())


@admin_bp.route('/notices/<int:notice_id>', methods=['PUT'])
@admin_required
def admin_update_notice(notice_id):
    """管理员修改启事资料"""
    notice = Notice.query.get(notice_id)
    if not notice:
        return jsonify(code=404, msg='启事不存在'), 404

    data = request.get_json() or {}

    notice.name = (data.get('name') or notice.name).strip()
    notice.nickname = (data.get('nickname') or notice.nickname).strip()
    notice.phone = (data.get('phone') or notice.phone).strip()
    notice.gender = data.get('gender') or notice.gender
    if 'age' in data:
        try:
            notice.age = int(data.get('age') or 0)
        except (ValueError, TypeError):
            pass
    notice.publisher_role = data.get('publisherRole') or notice.publisher_role
    notice.social_account = data.get('socialAccount', notice.social_account)
    notice.housing_location = data.get('housingLocation', notice.housing_location)
    notice.occupation = data.get('occupation', notice.occupation)
    notice.income = data.get('income', notice.income)
    if 'isPublicSector' in data:
        notice.is_public_sector = bool(data.get('isPublicSector'))
    if 'height' in data:
        notice.height = int(data.get('height') or 0)
    if 'weight' in data:
        notice.weight = int(data.get('weight') or 0)
    if 'remark' in data:
        notice.remark = data.get('remark') or ''
    if 'images' in data:
        imgs = data.get('images', [])
        notice.images = json.dumps(imgs) if isinstance(imgs, list) else str(imgs)

    notice.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify(code=0, msg='更新成功', data=notice.to_dict())


@admin_bp.route('/notices/<int:notice_id>', methods=['DELETE'])
@admin_required
def admin_delete_notice(notice_id):
    """管理员删除启事"""
    notice = Notice.query.get(notice_id)
    if not notice:
        return jsonify(code=404, msg='启事不存在'), 404

    # 清理该启事对应的查看记录
    NoticeView.query.filter_by(notice_id=notice.id).delete()
    db.session.delete(notice)
    db.session.commit()

    return jsonify(code=0, msg='删除成功')


@admin_bp.route('/notices/batch-delete', methods=['POST'])
@admin_required
def admin_batch_delete_notices():
    """批量删除启事"""
    data = request.get_json() or {}
    ids = data.get('ids', [])
    if not ids or not isinstance(ids, list):
        return jsonify(code=400, msg='请提供要删除的启事ID列表'), 400

    NoticeView.query.filter(NoticeView.notice_id.in_(ids)).delete(synchronize_session=False)
    Notice.query.filter(Notice.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()

    return jsonify(code=0, msg=f'成功批量删除 {len(ids)} 条启事')


# ============================================================
# 四、用户管理模块
# ============================================================

@admin_bp.route('/users', methods=['GET'])
@admin_required
def admin_get_users():
    """用户列表分页与搜索"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('pageSize', 10, type=int)
    keyword = (request.args.get('keyword') or '').strip()
    membership_type = request.args.get('membershipType')

    query = User.query

    if keyword:
        query = query.filter(or_(
            User.phone.ilike(f'%{keyword}%'),
            User.name.ilike(f'%{keyword}%')
        ))

    if membership_type:
        query = query.filter(User.membership_type == membership_type)

    total = query.count()
    users = query.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    res_list = []
    for u in users:
        d = u.to_dict()
        # 统计该用户发布的启事数
        d['publishedCount'] = Notice.query.filter_by(user_id=u.id).count()
        d['monthlyNoticeCount'] = u.monthly_notice_count or 0
        d['dailyNoticeCount'] = u.daily_notice_count or 0
        res_list.append(d)

    return jsonify(code=0, data={
        'total': total,
        'page': page,
        'pageSize': page_size,
        'list': res_list
    })


@admin_bp.route('/users/<int:user_id>/membership', methods=['PUT'])
@admin_required
def admin_update_user_membership(user_id):
    """管理员手动修改用户会员等级与到期时间"""
    user = User.query.get(user_id)
    if not user:
        return jsonify(code=404, msg='用户不存在'), 404

    data = request.get_json() or {}
    membership_type = data.get('membershipType')
    expire_str = data.get('membershipExpire')  # 形如 '2027-01-01' 或 '2027-01-01 00:00:00'

    if membership_type not in ('free', 'member', 'vip'):
        return jsonify(code=400, msg='无效的会员类型，支持 free / member / vip'), 400

    user.membership_type = membership_type
    if expire_str:
        try:
            if 'T' in expire_str:
                expire_str = expire_str.replace('T', ' ').split('.')[0]
            if len(expire_str) == 10:
                user.membership_expire = datetime.strptime(expire_str, '%Y-%m-%d')
            else:
                user.membership_expire = datetime.strptime(expire_str[:19], '%Y-%m-%d %H:%M:%S')
        except Exception as e:
            return jsonify(code=400, msg=f'到期时间格式错误: {str(e)}'), 400
    else:
        if membership_type == 'free':
            user.membership_expire = None

    user.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify(code=0, msg='会员状态已更新', data=user.to_dict())


@admin_bp.route('/users/<int:user_id>/quota', methods=['PUT'])
@admin_required
def admin_update_user_quota(user_id):
    """管理员重置/调整用户配额"""
    user = User.query.get(user_id)
    if not user:
        return jsonify(code=404, msg='用户不存在'), 404

    data = request.get_json() or {}
    if 'monthlyNoticeCount' in data:
        user.monthly_notice_count = max(0, int(data.get('monthlyNoticeCount') or 0))
    if 'dailyNoticeCount' in data:
        user.daily_notice_count = max(0, int(data.get('dailyNoticeCount') or 0))

    user.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify(code=0, msg='配额已调整', data={
        'monthlyNoticeCount': user.monthly_notice_count,
        'dailyNoticeCount': user.daily_notice_count
    })


# ============================================================
# 五、订单与对账管理模块
# ============================================================

@admin_bp.route('/orders', methods=['GET'])
@admin_required
def admin_get_orders():
    """订单列表分页与搜索"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('pageSize', 10, type=int)
    keyword = (request.args.get('keyword') or '').strip()
    status = request.args.get('status')
    order_type = request.args.get('type')

    query = MembershipOrder.query

    if keyword:
        # 支持按订单号或微信单号搜索
        query = query.filter(or_(
            MembershipOrder.order_no.ilike(f'%{keyword}%'),
            MembershipOrder.transaction_id.ilike(f'%{keyword}%')
        ))

    if status:
        query = query.filter(MembershipOrder.status == status)
    if order_type:
        query = query.filter(MembershipOrder.type == order_type)

    total = query.count()
    orders = query.order_by(MembershipOrder.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    res_list = []
    for o in orders:
        d = o.to_dict()
        user = User.query.get(o.user_id)
        d['userPhone'] = user.phone if user else '未知用户'
        d['userName'] = user.name if user else '未实名'
        d['amountYuan'] = round(o.amount / 100.0, 2)
        res_list.append(d)

    return jsonify(code=0, data={
        'total': total,
        'page': page,
        'pageSize': page_size,
        'list': res_list
    })


@admin_bp.route('/orders/<int:order_id>/fulfill', methods=['POST'])
@admin_required
def admin_manual_fulfill_order(order_id):
    """管理员手动补单：将未支付或异常订单核销为 paid，并为对应用户自动开通权益"""
    order = MembershipOrder.query.get(order_id)
    if not order:
        return jsonify(code=404, msg='订单不存在'), 404

    user = User.query.get(order.user_id)
    if not user:
        return jsonify(code=404, msg='关联用户不存在'), 404

    order.status = 'paid'
    order.paid_at = datetime.utcnow()

    # 开通会员：若已是会员则在原有基础上顺延1年，否则从当前时间起算1年
    now = datetime.utcnow()
    current_expire = user.membership_expire
    base_time = current_expire if current_expire and current_expire > now else now
    new_expire = base_time + timedelta(days=365)

    user.membership_type = order.type
    user.membership_expire = new_expire
    user.updated_at = now

    db.session.commit()

    return jsonify(code=0, msg='手动补单核销成功，已为用户激活会员权益', data=order.to_dict())


# ============================================================
# 六、智能文本提取与批量种子导入 (保留并支持Token鉴权)
# ============================================================

@admin_bp.route('/extractAndImport', methods=['POST'])
def extract_and_import():
    """
    从长文本中提取键值对并入库。
    兼容原有 X-Init-Password 及新版 Bearer Token 两种鉴权
    """
    # 鉴权
    auth_header = request.headers.get('Authorization', '')
    token = auth_header[7:].strip() if auth_header.startswith('Bearer ') else ''
    init_pwd = request.headers.get('X-Init-Password', '')

    from utils.admin_auth import verify_admin_token
    is_valid_token = bool(verify_admin_token(token))
    is_valid_pwd = (init_pwd == Config.ADMIN_PASSWORD)

    if not is_valid_token and not is_valid_pwd:
        return jsonify(code=401, msg='未授权访问'), 401

    data = request.get_json() or {}
    text = data.get('text', '')
    if not text:
        return jsonify(code=400, msg='文本内容不能为空'), 400

    extracted = extract_key_values(text)

    # 必填校验：姓名、性别
    if not extracted.get('name'):
        return jsonify(code=400, msg='未识别到姓名，请检查格式', data={'extracted': extracted}), 400
    if not extracted.get('gender'):
        return jsonify(code=400, msg='未识别到性别，请检查格式', data={'extracted': extracted}), 400

    phone = extracted.get('phone', '')
    if phone:
        existing = Notice.query.filter_by(phone=phone).first()
        if existing:
            return jsonify(code=409, msg=f'该手机号已存在启事: {existing.name}',
                           data={'extracted': extracted, 'existingId': existing.id}), 409

    age_val = int(extracted.get('age', 0) or 0)
    notice = Notice(
        user_id=0,
        phone=phone,
        name=extracted.get('name', ''),
        nickname=extracted.get('nickname', ''),
        gender=extracted.get('gender', ''),
        age=age_val,
        social_account=extracted.get('socialAccount', ''),
        occupation=extracted.get('occupation', ''),
        income=extracted.get('income', ''),
        is_public_sector=bool(extracted.get('isPublicSector', False)),
        height=int(extracted.get('height', 0) or 0),
        weight=int(extracted.get('weight', 0) or 0),
        publisher_role=extracted.get('publisherRole', '本人'),
        housing_location=extracted.get('housingLocation', '本地'),
        remark=extracted.get('remark', ''),
        source='import',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.session.add(notice)
    db.session.commit()

    return jsonify(code=0, msg='导入成功', data={
        'noticeId': notice.id,
        'extracted': extracted
    })


@admin_bp.route('/initData', methods=['POST'])
def init_data():
    """从 sql/seed_notices.json 导入初始种子数据"""
    auth_header = request.headers.get('Authorization', '')
    token = auth_header[7:].strip() if auth_header.startswith('Bearer ') else ''
    init_pwd = request.headers.get('X-Init-Password', '')

    from utils.admin_auth import verify_admin_token
    is_valid_token = bool(verify_admin_token(token))
    is_valid_pwd = (init_pwd == Config.ADMIN_PASSWORD)

    if not is_valid_token and not is_valid_pwd:
        return jsonify(code=401, msg='未授权访问'), 401

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    seed_path = os.path.join(base_dir, 'sql', 'seed_notices.json')

    try:
        with open(seed_path, 'r', encoding='utf-8') as f:
            seeds = json.load(f)
    except FileNotFoundError:
        return jsonify(code=500, msg='种子数据文件不存在: sql/seed_notices.json'), 500

    success, skip, errors = 0, 0, []

    for item in seeds:
        try:
            existing = Notice.query.filter_by(phone=item.get('phone', '')).first()
            if existing:
                skip += 1
                continue

            age_val = int(item.get('age', 0) or 0)
            if age_val <= 0 and item.get('birthday'):
                match = re.search(r'(\d{4})', str(item.get('birthday')))
                if match:
                    age_val = datetime.now().year - int(match.group(1))

            notice = Notice(
                user_id=0,
                phone=item.get('phone', ''),
                name=item.get('name', ''),
                nickname=item.get('nickname', ''),
                gender=item.get('gender', ''),
                age=age_val,
                social_account=item.get('socialAccount', '') or item.get('social_account', ''),
                occupation=item.get('occupation', ''),
                income=item.get('income', ''),
                is_public_sector=item.get('isPublicSector', False),
                height=item.get('height', 0),
                weight=item.get('weight', 0),
                remark=item.get('remark', ''),
                source='seed',
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(notice)
            success += 1
        except Exception as e:
            errors.append({'phone': item.get('phone'), 'error': str(e)})

    db.session.commit()

    return jsonify(code=0, msg=f'导入完成: 成功{success}, 跳过{skip}, 失败{len(errors)}',
                   data={'successCount': success, 'skipCount': skip, 'errorCount': len(errors)})


# ============================================================
# 七、UGC 违规举报与内容审查处理
# ============================================================

@admin_bp.route('/reports', methods=['GET'])
@admin_required
def admin_get_reports():
    """获取举报记录列表"""
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(50, max(1, int(request.args.get('pageSize', 20))))
    status = request.args.get('status')

    q = Report.query
    if status:
        q = q.filter(Report.status == status)
    q = q.order_by(Report.created_at.desc())

    total = q.count()
    reports = q.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for r in reports:
        item = r.to_dict()
        reporter = User.query.get(r.reporter_id)
        notice = Notice.query.get(r.notice_id)
        item['reporterPhone'] = reporter.phone if reporter else ''
        item['noticeName'] = notice.name if notice else '[已删除]'
        item['noticePhone'] = notice.phone if notice else ''
        items.append(item)

    return jsonify(code=0, data={
        'total': total,
        'page': page,
        'pageSize': page_size,
        'reports': items
    })


@admin_bp.route('/reports/<int:report_id>/handle', methods=['POST'])
@admin_required
def admin_handle_report(report_id):
    """处理举报：下架启事 (take_down) 或驳回举报 (reject)"""
    report = Report.query.get(report_id)
    if not report:
        return jsonify(code=404, msg='举报记录不存在'), 404

    data = request.get_json() or {}
    action = data.get('action')  # 'take_down' or 'reject'
    remark = data.get('remark', '')

    if action not in ('take_down', 'reject'):
        return jsonify(code=400, msg='处理动作无效'), 400

    report.handled_at = datetime.utcnow()
    report.handle_result = remark or ('违规已下架处理' if action == 'take_down' else '经核实不构成违规，驳回举报')

    if action == 'take_down':
        report.status = 'resolved'
        # 联动下架/删除启事及浏览记录
        notice = Notice.query.get(report.notice_id)
        if notice:
            NoticeView.query.filter_by(notice_id=notice.id).delete()
            db.session.delete(notice)
    else:
        report.status = 'rejected'

    db.session.commit()
    return jsonify(code=0, msg='处理完成', data=report.to_dict())

