# backend/routes/auth.py
"""登录认证 — 手机号弱校验：启事表中存在的手机号即可登录"""
import re
from flask import Blueprint, request, jsonify
from models import db, User, Notice
from datetime import datetime
from utils.wechat_pay import wechat_pay

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


@auth_bp.route('/wx-login', methods=['POST'])
def wx_login():
    """
    通过小程序 wx.login 的 code 换取 openid 并绑定/登录
    """
    data = request.get_json() or {}
    code = (data.get('code') or '').strip()
    user_id = data.get('userId')

    if not code:
        return jsonify(code=400, msg='缺少微信登录凭证 code'), 400

    try:
        session_info = wechat_pay.code2session(code)
        openid = session_info.get('openid')
        if not openid:
            return jsonify(code=400, msg='获取 openid 失败'), 400

        user = None
        if user_id:
            user = User.query.get(user_id)
            if user:
                user.openid = openid
                db.session.commit()

        return jsonify(code=0, msg='成功获取 openid', data={
            'openid': openid,
            'user': user.to_dict() if user else None
        })
    except Exception as e:
        return jsonify(code=500, msg=str(e)), 500
