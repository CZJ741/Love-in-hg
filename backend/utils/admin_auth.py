# backend/utils/admin_auth.py
"""
管理员后台身份认证与 Token 鉴权工具类
采用 HMAC-SHA256 签名，无第三方依赖（标准库 hashlib + hmac + base64 + time）
"""
import hmac
import hashlib
import base64
import json
import time
from functools import wraps
from flask import request, jsonify, g
from config import Config


def generate_admin_token(username: str, expires_in: int = 86400 * 7) -> str:
    """
    生成带签名的 Admin Token（默认 7 天有效）
    格式: base64(payload).base64(signature)
    """
    payload = {
        'username': username,
        'exp': int(time.time()) + expires_in,
        'iat': int(time.time())
    }
    payload_json = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode('utf-8')).decode('utf-8').rstrip('=')

    secret = Config.ADMIN_TOKEN_SECRET.encode('utf-8')
    sig = hmac.new(secret, payload_b64.encode('utf-8'), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode('utf-8').rstrip('=')

    return f"{payload_b64}.{sig_b64}"


def verify_admin_token(token: str) -> dict:
    """
    验证 Admin Token 是否合法且未过期
    成功返回 payload 字典，失败返回 None
    """
    if not token or '.' not in token:
        return None

    try:
        payload_b64, sig_b64 = token.split('.', 1)

        # 补齐 base64 padding
        pad = len(payload_b64) % 4
        if pad:
            payload_b64_padded = payload_b64 + '=' * (4 - pad)
        else:
            payload_b64_padded = payload_b64

        # 校验签名
        secret = Config.ADMIN_TOKEN_SECRET.encode('utf-8')
        expected_sig = hmac.new(secret, payload_b64.encode('utf-8'), hashlib.sha256).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode('utf-8').rstrip('=')

        if not hmac.compare_digest(sig_b64, expected_sig_b64):
            return None

        payload_bytes = base64.urlsafe_b64decode(payload_b64_padded.encode('utf-8'))
        payload = json.loads(payload_bytes.decode('utf-8'))

        # 校验是否过期
        if payload.get('exp', 0) < time.time():
            return None

        return payload
    except Exception:
        return None


def admin_required(f):
    """
    管理员鉴权装饰器：从 Authorization Header 中提取 Bearer Token 并进行验证
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        token = ''
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()
        elif auth_header:
            token = auth_header.strip()
        else:
            token = request.headers.get('X-Admin-Token', '')

        payload = verify_admin_token(token)
        if not payload:
            return jsonify(code=401, msg='未授权或登录已过期，请重新登录'), 401

        g.admin_username = payload.get('username')
        return f(*args, **kwargs)

    return decorated_function
