# backend/routes/auth.py
"""登录认证 — 手机号弱校验：启事表中存在的手机号即可登录"""
import re
from flask import Blueprint, request, jsonify
from models import db, User, Notice
from datetime import datetime
from utils.wechat_pay import wechat_pay
from utils.sms_service import sms_service

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    预留手机号登录通道：
    1. 必须在系统启事表 Notice 或 User 表中存在预留信息；
    2. 若前端传入 wx.login code，则自动绑定该微信号的 openid；
    3. 若库中无此手机号，提示其走微信一键授权通道。
    """
    data = request.get_json() or {}
    phone = (data.get('phone') or '').strip()
    code = (data.get('code') or '').strip()

    if not re.match(r'^1[3-9]\d{9}$', phone):
        return jsonify(code=400, msg='请输入正确的手机号码'), 400

    # 检查启事表中是否存在该手机号
    notice = Notice.query.filter_by(phone=phone).first()
    user = User.query.filter_by(phone=phone).first()

    if not notice and not user:
        return jsonify(code=404, msg='该手机号未预留档案，请切换至“注册”进行手机验证', data={
            'user': None,
            'isNewUser': True,
            'phone': phone
        })

    # 若未建 user，根据 notice 初始化用户档案
    if not user and notice:
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

    # 如果提供了微信 code，换取 openid 并绑定
    if code:
        try:
            session_info = wechat_pay.code2session(code)
            openid = session_info.get('openid')
            if openid:
                user.openid = openid
        except Exception as e:
            # 记录日志但不阻断基础登录
            pass

    user.last_login_at = datetime.utcnow()
    db.session.commit()

    return jsonify(code=0, msg='登录成功', data={
        'user': user.to_dict(),
        'isNewUser': False
    })


@auth_bp.route('/send-sms', methods=['POST'])
def send_sms():
    """
    发送手机验证码接口
    入参：{ "phone": "13800138000" }
    """
    data = request.get_json() or {}
    phone = (data.get('phone') or '').strip()

    if not re.match(r'^1[3-9]\d{9}$', phone):
        return jsonify(code=400, msg='请输入正确的手机号码'), 400

    result = sms_service.send_verification_code(phone)
    if not result.get('success'):
        return jsonify(code=400, msg=result.get('msg', '发送失败')), 400

    return jsonify(code=0, msg=result.get('msg', '验证码已发送'))


@auth_bp.route('/verify-register', methods=['POST'])
def verify_register():
    """
    新用户手机号验证码验证/注册建档登录：
    1. 前端传入 phone, code(验证码), wxCode(可选，换取openid)；
    2. 核验验证码，成功后查询或创建 User 记录，并绑定 openid；
    3. 返回登录成功信息。
    """
    data = request.get_json() or {}
    phone = (data.get('phone') or '').strip()
    sms_code = (data.get('code') or '').strip()
    wx_code = (data.get('wxCode') or '').strip()

    if not re.match(r'^1[3-9]\d{9}$', phone):
        return jsonify(code=400, msg='请输入正确的手机号码'), 400

    if not sms_code:
        return jsonify(code=400, msg='请输入验证码'), 400

    # 核验验证码
    if not sms_service.verify_code(phone, sms_code):
        return jsonify(code=400, msg='验证码错误或已过期'), 400

    # 换取 openid（若有 wx_code）
    openid = ''
    if wx_code:
        try:
            session_info = wechat_pay.code2session(wx_code)
            openid = session_info.get('openid', '')
        except Exception:
            pass

    # 查找或创建用户
    user = User.query.filter_by(phone=phone).first()
    notice = Notice.query.filter_by(phone=phone).first()

    is_new_user = False
    if not user:
        is_new_user = True
        user = User(
            phone=phone,
            openid=openid,
            name=notice.name if notice else f'用户{phone[-4:]}',
            gender=notice.gender if notice else '',
            occupation=notice.occupation or '' if notice else '',
            income=notice.income or '' if notice else '',
            is_public_sector=notice.is_public_sector if notice else False,
            height=notice.height or 0 if notice else 0,
            weight=notice.weight or 0 if notice else 0,
            membership_type='free',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(user)
        db.session.flush()
    else:
        if openid:
            user.openid = openid

    user.last_login_at = datetime.utcnow()
    db.session.commit()

    return jsonify(code=0, msg='验证成功', data={
        'user': user.to_dict(),
        'isNewUser': is_new_user
    })


@auth_bp.route('/wx-login', methods=['POST'])
def wx_login():
    """
    通过小程序 wx.login 的 code 换取 openid 并静默登录/绑定
    1. 若提供了 userId，直接将换取到的 openid 与该用户绑定；
    2. 若未提供 userId，根据 openid 寻找已绑定过的用户实现静默登录恢复。
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
        else:
            # 静默根据 openid 寻找用户
            user = User.query.filter_by(openid=openid).first()
            if user:
                user.last_login_at = datetime.utcnow()
                db.session.commit()

        return jsonify(code=0, msg='成功获取 openid', data={
            'openid': openid,
            'user': user.to_dict() if user else None
        })
    except Exception as e:
        return jsonify(code=500, msg=str(e)), 500
