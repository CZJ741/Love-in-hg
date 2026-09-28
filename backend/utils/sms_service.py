# backend/utils/sms_service.py
"""
阿里云短信发送服务封装
"""
import json
import logging
import random
import time
from config import Config
from alibabacloud_dysmsapi20170525.client import Client as DysmsClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dysmsapi20170525 import models as dysms_models

logger = logging.getLogger(__name__)

# 内存缓存验证码（key: phone, val: {"code": "123456", "expire_at": timestamp, "send_at": timestamp}）
_SMS_CACHE = {}


class SmsService:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client

        access_key_id = Config.ALIYUN_ACCESS_KEY_ID
        access_key_secret = Config.ALIYUN_ACCESS_KEY_SECRET

        if not access_key_id or not access_key_secret:
            logger.warning("未配置阿里云短信 AccessKey，短信将以 Mock 形式运行")
            return None

        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint="dysmsapi.aliyuncs.com"
        )
        self._client = DysmsClient(config)
        return self._client

    def send_verification_code(self, phone: str) -> dict:
        """
        发送手机验证码（6位数字），含60s防刷与5分钟有效期
        """
        now = time.time()
        record = _SMS_CACHE.get(phone)
        if record and now - record.get('send_at', 0) < 60:
            remaining = int(60 - (now - record['send_at']))
            return {
                "success": False,
                "msg": f"请勿频繁请求，{remaining}秒后再试"
            }

        # 生成 6 位随机验证码
        code = str(random.randint(100000, 999999))
        client = self._get_client()

        if client and Config.ALIYUN_SMS_SIGN_NAME and Config.ALIYUN_SMS_TEMPLATE_CODE:
            try:
                send_request = dysms_models.SendSmsRequest(
                    phone_numbers=phone,
                    sign_name=Config.ALIYUN_SMS_SIGN_NAME,
                    template_code=Config.ALIYUN_SMS_TEMPLATE_CODE,
                    template_param=json.dumps({"code": code})
                )
                response = client.send_sms(send_request)
                body = response.body
                if body.code != 'OK':
                    logger.error(f"阿里云短信发送失败: {body.code} - {body.message}")
                    return {
                        "success": False,
                        "msg": f"短信发送失败: {body.message}"
                    }
                logger.info(f"短信验证码发送成功: {phone} -> {code}")
            except Exception as e:
                logger.exception("调用阿里云短信异常:")
                return {
                    "success": False,
                    "msg": f"短信发送异常: {str(e)}"
                }
        else:
            # Mock 模式（开发调试兜底）
            logger.info(f"[MOCK 短信] 向手机号 {phone} 发送验证码: {code}")

        # 缓存验证码，有效期 5 分钟 (300 秒)
        _SMS_CACHE[phone] = {
            "code": code,
            "send_at": now,
            "expire_at": now + 300
        }

        return {
            "success": True,
            "msg": "验证码已发送",
            "debug_code": code if not client else None
        }

    def verify_code(self, phone: str, input_code: str) -> bool:
        """
        校验验证码，通过后立即失效防重放
        """
        if not phone or not input_code:
            return False

        # 方便特殊开发联调测试码
        if input_code == '888888':
            return True

        record = _SMS_CACHE.get(phone)
        if not record:
            return False

        now = time.time()
        if now > record.get('expire_at', 0):
            _SMS_CACHE.pop(phone, None)
            return False

        if record.get('code') == str(input_code).strip():
            # 校验成功后立即清除验证码，防止复用
            _SMS_CACHE.pop(phone, None)
            return True

        return False


sms_service = SmsService()
