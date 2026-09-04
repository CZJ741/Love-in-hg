# backend/routes/auth.py
"""登录认证 — 手机号弱校验：启事表中存在的手机号即可登录"""
import re
from flask import Blueprint, request, jsonify
from models import db, User, Notice
from datetime import datetime

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    """手机号登录 — 只要启事表中存在该手机号即可登录"""
    data = request.get_json() or {}
    phone = (data.get('phone') or '').strip()

    if not re.match(r'^1[3-9]\d{9}$', phone):
        return jsonify(code=400, msg='请输入正确的手机号码'), 400

    # 弱校验：检查启事表中是否存在该手机号
    notice = Notice.query.filter_by(phone=phone).first()

    if not notice:
        return jsonify(code=0, msg='该手机号未发布过启事，请先发布', data={
            'user': None,
            'isNewUser': True,
            'phone': phone
        })

    # 启事表中存在 → 查找或创建用户
    user = User.query.filter_by(phone=phone).first()
    if not user:
        user = User(
            phone=phone,
            name=notice.name,
            gender=notice.gender,
            birthday=notice.birthday or '',
            occupation=notice.occupation or '',
            income=notice.income or '',
            is_public_sector=notice.is_public_sector or False,
            height=notice.height or 0,
            weight=notice.weight or 0,
            membership_type='free',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(user)
        db.session.flush()

    user.last_login_at = datetime.utcnow()
    db.session.commit()

    return jsonify(code=0, msg='登录成功', data={
        'user': user.to_dict(),
        'isNewUser': False
    })
