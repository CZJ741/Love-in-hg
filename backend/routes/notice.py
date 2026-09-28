# backend/routes/notice.py
"""启事发布 + 查看（随机分配+筛选+配额）"""
import os
import re
import json
import uuid
import io
from datetime import datetime, date
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import func, and_, or_
from werkzeug.utils import secure_filename
from PIL import Image
from models import db, User, Notice, NoticeView, Report, UserBlock
from services.quota_service import get_membership_limit, get_quota_info
from utils.file_cleaner import delete_notice_images
from utils.wechat_security import WeChatSecurity


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
    age = data.get('age')
    try:
        age = int(age) if age is not None and str(age).strip() != '' else 0
    except (ValueError, TypeError):
        age = 0

    if age <= 0:
        birthday = (data.get('birthday') or '').strip()
        if birthday:
            match = re.search(r'(\d{4})', birthday)
            if match:
                age = datetime.now().year - int(match.group(1))
    if age <= 0:
        return jsonify(code=400, msg='请输入有效年龄'), 400

    housing_location = (data.get('housingLocation') or '本地').strip()
    if not housing_location:
        return jsonify(code=400, msg='请选择住房位置'), 400

    publisher_role = (data.get('publisherRole') or '本人').strip()


    # 登录鉴权：检查发布者是否已登录
    req_user_id = request.headers.get('X-User-Id')
    current_user = None
    if req_user_id:
        try:
            current_user = User.query.get(int(req_user_id))
        except (ValueError, TypeError):
            pass

    if not current_user:
        return jsonify(code=401, msg='请先登录后再发布启事'), 401

    # 微信内容安全机审 (msgSecCheck)：检查启事文本是否违规
    sec_content = f"{name} {data.get('nickname', '')} {data.get('occupation', '')} {data.get('remark', '')} {housing_location}"
    is_safe, sec_err = WeChatSecurity.check_text(sec_content, openid=current_user.openid)
    if not is_safe:
        return jsonify(code=400, msg=sec_err or '内容包含违规或敏感信息，请修改后重试'), 400

    # 用户存在则更新用户资料
    user = current_user
    user.name = name
    user.gender = gender
    user.occupation = data.get('occupation', '')
    user.income = data.get('income', '')
    user.is_public_sector = data.get('isPublicSector', False)
    user.height = data.get('height', 0) or 0
    user.weight = data.get('weight', 0) or 0
    user.updated_at = datetime.utcnow()

    # 一个手机号可发布多条启事，始终新增
    images_input = data.get('images', [])
    if isinstance(images_input, str):
        try:
            images_input = json.loads(images_input)
        except Exception:
            images_input = []
    if not isinstance(images_input, list):
        images_input = []
    # 限制最多9张
    images_input = images_input[:9]

    notice = Notice(
        user_id=user.id,
        publisher_role=publisher_role,
        phone=phone,
        name=name,
        nickname=data.get('nickname', ''),
        gender=gender,
        age=age,
        social_account=(data.get('socialAccount') or '').strip(),
        housing_location=housing_location,
        occupation=data.get('occupation', ''),
        income=data.get('income', ''),
        is_public_sector=data.get('isPublicSector', False),
        height=data.get('height', 0) or 0,
        weight=data.get('weight', 0) or 0,
        images=json.dumps(images_input, ensure_ascii=False),
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

    # 微信内容安全机审 (msgSecCheck)：检查启事文本是否违规
    check_name = (data.get('name') or notice.name or '').strip()
    check_nick = (data.get('nickname') or notice.nickname or '').strip()
    check_occ = (data.get('occupation') or notice.occupation or '').strip()
    check_remark = (data.get('remark') or notice.remark or '').strip()
    sec_content = f"{check_name} {check_nick} {check_occ} {check_remark}"
    is_safe, sec_err = WeChatSecurity.check_text(sec_content)
    if not is_safe:
        return jsonify(code=400, msg=sec_err or '修改内容包含违规或敏感信息，请修改后重试'), 400
    if 'publisherRole' in data:
        notice.publisher_role = (data.get('publisherRole') or '本人').strip()
    notice.name = (data.get('name') or '').strip()
    notice.nickname = (data.get('nickname') or '').strip()
    notice.gender = data.get('gender', notice.gender)
    if 'age' in data:
        try:
            notice.age = int(data.get('age') or 0)
        except (ValueError, TypeError):
            pass
    elif 'birthday' in data:
        b_str = (data.get('birthday') or '').strip()
        m = re.search(r'(\d{4})', b_str)
        if m:
            notice.age = datetime.now().year - int(m.group(1))
    if 'socialAccount' in data:
        notice.social_account = (data.get('socialAccount') or '').strip()
    if 'housingLocation' in data:
        notice.housing_location = (data.get('housingLocation') or '本地').strip()
    notice.occupation = data.get('occupation', '')
    notice.income = data.get('income', '')
    notice.is_public_sector = data.get('isPublicSector', False)
    notice.height = data.get('height', 0) or 0
    notice.weight = data.get('weight', 0) or 0

    if 'images' in data:
        images_input = data.get('images', [])
        if isinstance(images_input, str):
            try:
                images_input = json.loads(images_input)
            except Exception:
                images_input = []
        if not isinstance(images_input, list):
            images_input = []
        notice.images = json.dumps(images_input[:9], ensure_ascii=False)
    notice.remark = data.get('remark', '')
    notice.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify(code=0, msg='修改成功', data={
        'noticeId': str(notice.id)
    })


def _compress_and_save_image(file_storage, dest_path, target_kb=120):
    """
    智能图片压缩与优化保存：
    - 读取图片流并修正色彩模式（RGBA/P转RGB或保持RGBA）
    - 约束最大分辨率（长边不超过1600px）
    - 质量迭代压缩至目标大小约 120KB 左右
    """
    try:
        img = Image.open(file_storage)

        # 处理 EXIF 旋转（手机拍照方向修正）
        try:
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        # 限制最大宽高（例如 1600px，保持比例缩小）
        max_dim = 1600
        if max(img.width, img.height) > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        # 格式判断
        orig_ext = os.path.splitext(dest_path)[1].lower().replace('.', '')
        # 如果是透明通道且非PNG，转RGB保存为JPEG
        is_transparent = (img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info))

        if orig_ext in ('jpg', 'jpeg') or not is_transparent:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            save_format = 'JPEG'
        else:
            save_format = 'PNG'

        # 动态二分/循环调整 quality 逼近 target_kb (120KB)
        target_bytes = target_kb * 1024
        quality = 85
        buffer = io.BytesIO()

        if save_format == 'JPEG':
            for q in [85, 75, 65, 55, 45, 35]:
                buffer.seek(0)
                buffer.truncate()
                img.save(buffer, format='JPEG', quality=q, optimize=True)
                if buffer.tell() <= target_bytes or q == 35:
                    quality = q
                    break
        else:
            # PNG 格式通过优化压缩
            buffer.seek(0)
            buffer.truncate()
            img.save(buffer, format='PNG', optimize=True)
            # 如果 PNG 还是明显超过 target_bytes，转换为高质量 JPEG
            if buffer.tell() > target_bytes:
                img_rgb = img.convert('RGB')
                buffer.seek(0)
                buffer.truncate()
                img_rgb.save(buffer, format='JPEG', quality=80, optimize=True)

        with open(dest_path, 'wb') as f:
            f.write(buffer.getvalue())

        return True
    except Exception as e:
        # 若压缩异常则回退至原生保存，保证上传稳定性
        file_storage.seek(0)
        file_storage.save(dest_path)
        return True


@notice_bp.route('/upload', methods=['POST'])
def upload_image():
    """上传图片接口，支持单张/多张图片上传并压缩至120KB左右，限制最多9张"""
    allowed_exts = current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif', 'webp'})
    upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads'))
    os.makedirs(upload_folder, exist_ok=True)

    files = request.files.getlist('files') or request.files.getlist('images') or request.files.getlist('file') or request.files.getlist('image')
    if not files and 'file' in request.files:
        files = [request.files['file']]
    elif not files and 'image' in request.files:
        files = [request.files['image']]

    if not files:
        return jsonify(code=400, msg='请选择要上传的图片文件'), 400

    if len(files) > 9:
        return jsonify(code=400, msg='单次最多支持上传9张图片'), 400

    saved_urls = []
    for f in files:
        if not f or not f.filename:
            continue
        ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
        if ext not in allowed_exts:
            return jsonify(code=400, msg=f'不支持的文件类型: {ext}，仅支持 {", ".join(allowed_exts)}'), 400

        # 生成唯一文件名（统一转为 jpg 便于高质量压缩）
        out_ext = 'jpg' if ext in ('jpg', 'jpeg', 'webp', 'png') else ext
        unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.{out_ext}"
        filepath = os.path.join(upload_folder, unique_name)

        # 压缩并保存图片到本地 uploads 目录，目标大小约 120KB
        _compress_and_save_image(f, filepath, target_kb=120)

        # 微信图片安全审查 (imgSecCheck)
        try:
            with open(filepath, 'rb') as img_f:
                img_bytes = img_f.read()
            is_safe, sec_err = WeChatSecurity.check_image(img_bytes)
            if not is_safe:
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify(code=400, msg=sec_err or '图片包含违规或敏感内容，请重新选择'), 400
        except Exception as e:
            current_app.logger.warning(f"图片安全检查异常跳过: {e}")

        file_url = f"/uploads/{unique_name}"
        saved_urls.append(file_url)

    if not saved_urls:
        return jsonify(code=400, msg='没有有效的文件被上传'), 400

    return jsonify(code=0, msg='上传成功', data={
        'url': saved_urls[0] if len(saved_urls) == 1 else saved_urls,
        'urls': saved_urls
    })




@notice_bp.route('/list', methods=['GET'])
def get_notices():
    """启事分配：free/member每月1号分配，vip每天分配，未登录展示公开推荐"""
    user_id = request.args.get('userId') or request.headers.get('X-User-Id')
    user = User.query.get(int(user_id)) if user_id and str(user_id).isdigit() else None

    # 筛选条件
    gender = request.args.get('gender')
    housing_location = request.args.get('housingLocation')
    min_age = request.args.get('minAge', type=int)
    max_age = request.args.get('maxAge', type=int)

    is_member_user = user and user.membership_type in ('member', 'vip')
    min_height = request.args.get('minHeight', type=int) if is_member_user else None
    max_height = request.args.get('maxHeight', type=int) if is_member_user else None
    min_weight = request.args.get('minWeight', type=int) if is_member_user else None
    max_weight = request.args.get('maxWeight', type=int) if is_member_user else None
    income = request.args.get('income') if is_member_user else None
    is_public_sector = request.args.get('isPublicSector') if is_member_user else None
    occupation = request.args.get('occupation') if is_member_user else None

    def _apply_filters(q):
        if gender:
            q = q.filter(Notice.gender == gender)
        if housing_location:
            q = q.filter(Notice.housing_location == housing_location)
        if min_age or max_age:
            if min_age and max_age:
                q = q.filter(Notice.age.between(min_age, max_age))
            elif min_age:
                q = q.filter(Notice.age >= min_age)
            elif max_age:
                q = q.filter(Notice.age <= max_age)

        if min_height:
            q = q.filter(Notice.height >= min_height)
        if max_height:
            q = q.filter(Notice.height <= max_height)
        if min_weight:
            q = q.filter(Notice.weight >= min_weight)
        if max_weight:
            q = q.filter(Notice.weight <= max_weight)
        if income:
            q = q.filter(Notice.income == income)
        if is_public_sector is not None and is_public_sector != '':
            q = q.filter(Notice.is_public_sector == (str(is_public_sector).lower() == 'true'))
        if occupation:
            q = q.filter(Notice.occupation.like(f'%{occupation}%'))
        return q

    # 获取已拉黑与被拉黑用户 ID 列表
    blocked_user_ids = []
    if user:
        # 当前用户拉黑的人
        my_blocks = UserBlock.query.filter_by(user_id=user.id).all()
        blocked_user_ids.extend([b.blocked_user_id for b in my_blocks])
        # 拉黑当前用户的人
        reverse_blocks = UserBlock.query.filter_by(blocked_user_id=user.id).all()
        blocked_user_ids.extend([b.user_id for b in reverse_blocks])

    # 1. 未登录访客逻辑：直接返回最新的公开启事列表供浏览
    if not user:
        nq = Notice.query.order_by(Notice.created_at.desc())
        nq = _apply_filters(nq)
        notices = nq.limit(20).all()
        notice_list = [n.to_dict() for n in notices]
        for item in notice_list:
            item['phone'] = _mask_phone(item['phone'])
        return jsonify(code=0, data={
            'notices': notice_list,
            'remaining': 0,
            'membershipType': 'free',
            'periodType': 'monthly',
            'limitReached': False
        })

    # 2. 已登录用户逻辑：按配额分配与查看
    today = date.today()
    period_type, period_limit = get_membership_limit(user)
    db.session.commit()

    # 判断当前周期是否已分配
    if period_type == 'daily':
        period_start = datetime(today.year, today.month, today.day)
    else:
        period_start = datetime(today.year, today.month, 1)

    # 1. 检查当前周期已分配的启事数量
    assigned_views = NoticeView.query.filter(
        NoticeView.user_id == user.id,
        NoticeView.viewed_at >= period_start
    ).all()
    assigned_ids = [v.notice_id for v in assigned_views]
    assigned_count = len(assigned_ids)

    # 2. 如果已分配数量小于当前会员等级对应的周期额度，补充分配差额
    needed_count = period_limit - assigned_count
    if needed_count > 0:
        # 排除历史上所有已为该用户分配过的启事
        all_assigned_ids = [v.notice_id for v in NoticeView.query.filter_by(user_id=user.id).all()]

        query = Notice.query.filter(Notice.user_id != user.id)
        if all_assigned_ids:
            query = query.filter(Notice.id.notin_(all_assigned_ids))
        if blocked_user_ids:
            query = query.filter(Notice.user_id.notin_(blocked_user_ids))
        query = _apply_filters(query)

        total_available = query.count()
        assign_count = min(needed_count, total_available)

        if assign_count > 0:
            assign_ids = [row[0] for row in query.with_entities(Notice.id).order_by(func.rand()).limit(assign_count).all()]
            for nid in assign_ids:
                db.session.add(NoticeView(user_id=user.id, notice_id=nid, viewed_at=datetime.utcnow()))
            db.session.commit()
            assigned_ids.extend(assign_ids)

    if not assigned_ids:
        return jsonify(code=0, data={
            'notices': [],
            'remaining': 0,
            'membershipType': user.membership_type,
            'periodType': period_type,
            'limitReached': False
        })

    nq = Notice.query.filter(Notice.id.in_(assigned_ids))
    if blocked_user_ids:
        nq = nq.filter(Notice.user_id.notin_(blocked_user_ids))
    nq = _apply_filters(nq)

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
        'phone': notice.phone,
        'socialAccount': notice.social_account or ''
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
    # 清除启事上传在本地磁盘的图片
    if notice.images:
        delete_notice_images(notice.images)
    # 再删除启事本身
    db.session.delete(notice)
    db.session.commit()

    return jsonify(code=0, msg='删除成功', data={
        'noticeId': str(notice_id)
    })


@notice_bp.route('/report', methods=['POST'])
def report_notice():
    """UGC 内容举报接口（审核合规刚需）"""
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        return jsonify(code=401, msg='请先登录后再提交举报'), 401

    user = User.query.get(int(user_id))
    if not user:
        return jsonify(code=401, msg='用户不存在'), 401

    data = request.get_json() or {}
    notice_id = data.get('noticeId')
    reason = (data.get('reason') or '').strip()
    description = (data.get('description') or '').strip()

    if not notice_id:
        return jsonify(code=400, msg='请选择要举报的启事'), 400
    if not reason:
        return jsonify(code=400, msg='请选择举报原因'), 400

    notice = Notice.query.get(int(notice_id))
    if not notice:
        return jsonify(code=404, msg='举报的启事不存在或已被下架'), 404

    # 创建举报记录
    report = Report(
        reporter_id=user.id,
        notice_id=notice.id,
        reason=reason,
        description=description[:500],
        status='pending'
    )
    db.session.add(report)
    db.session.commit()

    return jsonify(code=0, msg='举报已收到，平台将在24小时内严格审核处理')

