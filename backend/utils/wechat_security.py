# backend/utils/wechat_security.py
"""
微信内容安全检测工具（文本 msgSecCheck 与图片 imgSecCheck）
具备内存缓存 Token、自动提前刷新及优雅降级容错机制。
"""
import time
import json
import logging
import requests
from config import Config

logger = logging.getLogger(__name__)


class WeChatSecurity:
    _token_cache = {
        'token': None,
        'expires_at': 0
    }

    @classmethod
    def get_access_token(cls) -> str:
        """获取 stable access_token，带内存有效期缓存（提前 600 秒刷新）"""
        now = time.time()
        if cls._token_cache['token'] and now < cls._token_cache['expires_at']:
            return cls._token_cache['token']

        app_id = Config.WX_APP_ID
        app_secret = Config.WX_APP_SECRET
        if not app_id or not app_secret or 'your_' in app_secret:
            logger.warning("未配置合法的 WX_APP_SECRET，跳过微信安全检测凭证获取")
            return ""

        url = "https://api.weixin.qq.com/cgi-bin/stable_token"
        payload = {
            "grant_type": "client_credential",
            "appid": app_id,
            "secret": app_secret,
            "force_refresh": False
        }
        try:
            res = requests.post(url, json=payload, timeout=8)
            data = res.json()
            token = data.get('access_token')
            expires_in = data.get('expires_in', 7200)
            if token:
                cls._token_cache['token'] = token
                cls._token_cache['expires_at'] = now + expires_in - 600
                return token
            logger.warning(f"获取微信 stable_token 未返回 token: {data}")
        except Exception as e:
            logger.warning(f"请求微信 stable_token 异常 (跳过机审阻断): {e}")
        return ""

    @classmethod
    def check_text(cls, text: str, openid: str = "") -> tuple[bool, str]:
        """
        检查文本内容安全 (msgSecCheck v2)
        :param text: 待检测文本内容
        :param openid: 用户微信 openid
        :return: (is_safe: bool, reason: str)
        """
        if not text or not text.strip():
            return True, ""

        token = cls.get_access_token()
        if not token:
            # 兼容开发环境或未配置微信 Secret 的情况，放行
            return True, ""

        url = f"https://api.weixin.qq.com/wxa/msg_sec_check?access_token={token}"
        payload = {
            "content": text.strip()[:1000],  # 微信单次检测限制
            "version": 2,
            "scene": 2  # 资料/相亲/信息发布
        }
        if openid:
            payload["openid"] = openid
        try:
            res = requests.post(url, json=payload, timeout=6)
            data = res.json()
            errcode = data.get('errcode', 0)
            if errcode == 87014:
                return False, "内容包含违规或敏感信息，请修改后重试"
            if errcode == 0:
                result = data.get('result', {})
                if result.get('suggest') == 'risky':
                    return False, "内容包含敏感或不合规信息，请修改后重试"
                return True, ""
            logger.warning(f"微信文本安全检测返回非零状态: {data}")
            return True, ""
        except Exception as e:
            logger.warning(f"微信文本安全检测网络请求异常: {e}")
            return True, ""

    @classmethod
    def check_image(cls, image_bytes: bytes) -> tuple[bool, str]:
        """
        检查图片内容安全 (同步 imgSecCheck)
        :param image_bytes: 图片二进制字节流
        :return: (is_safe: bool, reason: str)
        """
        if not image_bytes:
            return True, ""

        token = cls.get_access_token()
        if not token:
            return True, ""

        url = f"https://api.weixin.qq.com/wxa/img_sec_check?access_token={token}"
        files = {'media': ('image.jpg', image_bytes, 'image/jpeg')}
        try:
            res = requests.post(url, files=files, timeout=10)
            data = res.json()
            errcode = data.get('errcode', 0)
            if errcode == 87014:
                return False, "图片包含违规或敏感内容，请重新选择"
            if errcode != 0:
                logger.warning(f"微信图片安全检测返回状态: {data}")
            return True, ""
        except Exception as e:
            logger.warning(f"微信图片安全检测请求异常: {e}")
            return True, ""
