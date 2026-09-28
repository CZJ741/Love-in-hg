# backend/utils/wechat_pay.py
"""
微信支付 V3 API 工具类
支持：
1. 商户请求微信接口的 V3 签名生成 (Authorization)
2. JSAPI 统一下单 (Transactions JSAPI)
3. 小程序调起支付参数签名 (paySign)
4. 微信支付异步回调验签 (使用微信支付公钥 pub_key.pem)
5. 微信支付异步回调解密 (AEAD_AES_256_GCM)
6. 主动查询订单状态 (out-trade-no)
7. 小程序 code2session 换取 openid
"""
import base64
import json
import logging
import os
import time
import uuid
import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from config import Config

logger = logging.getLogger(__name__)


class WeChatPayV3:
    def __init__(self):
        self.app_id = Config.WX_APP_ID
        self.mch_id = Config.WX_MCH_ID
        self.api_v3_key = Config.WX_API_V3_KEY
        self.cert_serial_no = Config.WX_CERT_SERIAL_NO
        self.public_key_id = Config.WX_PUBLIC_KEY_ID
        self.notify_url = Config.WX_PAY_NOTIFY_URL

        self._private_key = None
        self._wx_public_key = None
        self._load_keys()

    def is_configured(self) -> bool:
        """判断微信支付商户必要配置是否完整"""
        return bool(self.mch_id and self.api_v3_key and self._private_key)

    def _load_keys(self):
        """加载商户私钥与微信支付公钥"""
        # 加载商户私钥
        private_key_pem = Config.WX_PRIVATE_KEY
        if not private_key_pem and Config.WX_PRIVATE_KEY_PATH and os.path.exists(Config.WX_PRIVATE_KEY_PATH):
            try:
                with open(Config.WX_PRIVATE_KEY_PATH, 'rb') as f:
                    private_key_pem = f.read().decode('utf-8')
            except Exception as e:
                logger.error(f"读取商户私钥文件失败: {e}")

        if private_key_pem:
            try:
                if not private_key_pem.strip().startswith('-----BEGIN'):
                    private_key_pem = f"-----BEGIN PRIVATE KEY-----\n{private_key_pem.strip()}\n-----END PRIVATE KEY-----"
                self._private_key = load_pem_private_key(private_key_pem.encode('utf-8'), password=None)
            except Exception as e:
                logger.error(f"解析商户私钥失败: {e}")

        # 加载微信支付公钥
        public_key_pem = Config.WX_PUBLIC_KEY
        if not public_key_pem and Config.WX_PUBLIC_KEY_PATH and os.path.exists(Config.WX_PUBLIC_KEY_PATH):
            try:
                with open(Config.WX_PUBLIC_KEY_PATH, 'rb') as f:
                    public_key_pem = f.read().decode('utf-8')
            except Exception as e:
                logger.error(f"读取微信支付公钥文件失败: {e}")

        if public_key_pem:
            try:
                if not public_key_pem.strip().startswith('-----BEGIN'):
                    public_key_pem = f"-----BEGIN PUBLIC KEY-----\n{public_key_pem.strip()}\n-----END PUBLIC KEY-----"
                self._wx_public_key = load_pem_public_key(public_key_pem.encode('utf-8'))
            except Exception as e:
                logger.error(f"解析微信支付公钥失败: {e}")

    def sign_sha256_rsa(self, message: str) -> str:
        """使用商户私钥计算 SHA256-RSA 签名 (Base64 编码)"""
        if not self._private_key:
            raise ValueError("商户私钥未配置或未正确加载")
        signature = self._private_key.sign(
            message.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode('utf-8')

    def build_authorization_header(self, method: str, url_path: str, body: str = '') -> str:
        """
        构建 V3 请求 Header 中的 Authorization 字符串
        格式: WECHATPAY2-SHA256-RSA2048 mchid="...",nonce_str="...",signature="...",timestamp="...",serial_no="..."
        """
        timestamp = str(int(time.time()))
        nonce_str = uuid.uuid4().hex

        # 构造待签名字符串: HTTP请求方法\nURL\n请求时间戳\n请求随机串\n请求报文主体\n
        message = f"{method.upper()}\n{url_path}\n{timestamp}\n{nonce_str}\n{body}\n"
        signature = self.sign_sha256_rsa(message)

        auth_parts = [
            f'mchid="{self.mch_id}"',
            f'nonce_str="{nonce_str}"',
            f'timestamp="{timestamp}"',
            f'serial_no="{self.cert_serial_no}"',
            f'signature="{signature}"'
        ]
        return f"WECHATPAY2-SHA256-RSA2048 {','.join(auth_parts)}"

    def jsapi_order(self, out_trade_no: str, total_amount_cents: int, description: str, openid: str, notify_url: str = None) -> dict:
        """
        发起微信支付 JSAPI 统一下单
        :param out_trade_no: 商户订单号
        :param total_amount_cents: 金额 (单位：分)
        :param description: 商品描述
        :param openid: 用户的微信 openid
        :param notify_url: 支付结果通知回调地址
        :return: 微信统一下单返回结果字典，包含 prepay_id
        """
        url = "https://api.mch.weixin.qq.com/v3/pay/transactions/jsapi"
        path = "/v3/pay/transactions/jsapi"
        callback_url = notify_url or self.notify_url

        payload = {
            "appid": self.app_id,
            "mchid": self.mch_id,
            "description": description,
            "out_trade_no": out_trade_no,
            "notify_url": callback_url,
            "amount": {
                "total": total_amount_cents,
                "currency": "CNY"
            },
            "payer": {
                "openid": openid
            }
        }
        body = json.dumps(payload, ensure_ascii=False)
        auth_header = self.build_authorization_header('POST', path, body)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": auth_header,
            "User-Agent": "Love-in-hg WeChatPay Client"
        }

        # 如果配置了微信支付公钥ID，微信平台推荐在请求头携带 Wechatpay-Serial
        if self.public_key_id:
            headers["Wechatpay-Serial"] = self.public_key_id

        res = requests.post(url, data=body.encode('utf-8'), headers=headers, timeout=10)
        res_json = res.json()
        if res.status_code != 200:
            logger.error(f"微信支付统一下单失败 [{res.status_code}]: {res.text}")
            raise Exception(res_json.get('message', f'微信统一下单失败: {res.text}'))

        return res_json

    def h5_order(self, out_trade_no: str, total_amount_cents: int, description: str, client_ip: str, notify_url: str = None) -> dict:
        """
        发起微信支付 H5 统一下单（供手机浏览器调用并拉起微信 App 支付）
        :param out_trade_no: 商户订单号
        :param total_amount_cents: 金额 (单位：分)
        :param description: 商品描述
        :param client_ip: 用户的真实公网客户端IP
        :param notify_url: 支付结果通知回调地址
        :return: 微信返回字典，包含 h5_url
        """
        url = "https://api.mch.weixin.qq.com/v3/pay/transactions/h5"
        path = "/v3/pay/transactions/h5"
        callback_url = notify_url or self.notify_url

        payload = {
            "appid": self.app_id,
            "mchid": self.mch_id,
            "description": description,
            "out_trade_no": out_trade_no,
            "notify_url": callback_url,
            "amount": {
                "total": total_amount_cents,
                "currency": "CNY"
            },
            "scene_info": {
                "payer_client_ip": client_ip or "127.0.0.1",
                "h5_info": {
                    "type": "Wap"
                }
            }
        }
        body = json.dumps(payload)
        auth_header = self.build_authorization_header('POST', path, body)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": auth_header,
            "User-Agent": "Love-in-hg WeChatPay Client"
        }

        if self.public_key_id:
            headers["Wechatpay-Serial"] = self.public_key_id

        res = requests.post(url, data=body.encode('utf-8'), headers=headers, timeout=10)
        res_json = res.json()
        if res.status_code != 200:
            logger.error(f"微信支付H5统一下单失败 [{res.status_code}]: {res.text}")
            raise Exception(res_json.get('message', f'微信H5统一下单失败: {res.text}'))

        return res_json

    def build_miniprogram_payment_params(self, prepay_id: str) -> dict:
        """
        生成小程序调用 wx.requestPayment 需要的参数与签名
        """
        timestamp = str(int(time.time()))
        nonce_str = uuid.uuid4().hex
        package_str = f"prepay_id={prepay_id}"

        # 待签名内容:
        # 小程序appId\n时间戳\n随机字符串\n订单详情扩展字符串\n
        message = f"{self.app_id}\n{timestamp}\n{nonce_str}\n{package_str}\n"
        pay_sign = self.sign_sha256_rsa(message)

        return {
            "timeStamp": timestamp,
            "nonceStr": nonce_str,
            "package": package_str,
            "signType": "RSA",
            "paySign": pay_sign
        }

    def verify_callback_signature(self, timestamp: str, nonce: str, body: str, signature: str) -> bool:
        """
        验证微信支付回调签名 (使用微信支付公钥 pub_key.pem)
        待签名字符串:
        HTTP头 Wechatpay-Timestamp\n
        HTTP头 Wechatpay-Nonce\n
        请求体\n
        """
        if not self._wx_public_key:
            logger.warning("未配置微信支付公钥，跳过公钥验签")
            return True

        message = f"{timestamp}\n{nonce}\n{body}\n"
        try:
            signature_bytes = base64.b64decode(signature)
            self._wx_public_key.verify(
                signature_bytes,
                message.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            logger.error(f"微信支付回调验签失败: {e}")
            return False

    def decrypt_callback_resource(self, associated_data: str, nonce: str, ciphertext: str) -> dict:
        """
        使用 APIv3Key 解密微信回调通知报文 (AEAD_AES_256_GCM)
        """
        if not self.api_v3_key:
            raise ValueError("未配置 APIv3Key，无法解密微信回调报文")

        key_bytes = self.api_v3_key.encode('utf-8')
        nonce_bytes = nonce.encode('utf-8')
        ad_bytes = associated_data.encode('utf-8') if associated_data else b''
        cipher_bytes = base64.b64decode(ciphertext)

        aesgcm = AESGCM(key_bytes)
        decrypted_bytes = aesgcm.decrypt(nonce_bytes, cipher_bytes, ad_bytes)
        return json.loads(decrypted_bytes.decode('utf-8'))

    def query_order(self, out_trade_no: str) -> dict:
        """
        主动向微信查询订单状态
        GET /v3/pay/transactions/out-trade-no/{out_trade_no}?mchid={mchid}
        """
        path = f"/v3/pay/transactions/out-trade-no/{out_trade_no}?mchid={self.mch_id}"
        url = f"https://api.mch.weixin.qq.com{path}"

        auth_header = self.build_authorization_header('GET', path, '')
        headers = {
            "Accept": "application/json",
            "Authorization": auth_header,
            "User-Agent": "Love-in-hg WeChatPay Client"
        }
        if self.public_key_id:
            headers["Wechatpay-Serial"] = self.public_key_id

        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
        logger.warning(f"向微信查询订单失败 [{res.status_code}]: {res.text}")
        return {}

    @staticmethod
    def code2session(js_code: str) -> dict:
        """
        使用小程序登录凭证 code 换取 openid 和 session_key
        """
        app_id = Config.WX_APP_ID
        app_secret = Config.WX_APP_SECRET
        if not app_secret:
            raise ValueError("未配置小程序 WX_APP_SECRET，无法换取 openid")

        url = "https://api.weixin.qq.com/sns/jscode2session"
        params = {
            "appid": app_id,
            "secret": app_secret,
            "js_code": js_code,
            "grant_type": "authorization_code"
        }
        try:
            res = requests.get(url, params=params, timeout=4)
            data = res.json()
            if 'errcode' in data and data['errcode'] != 0:
                logger.error(f"code2session 失败: {data}")
                raise Exception(data.get('errmsg', '换取 openid 失败'))
            return data
        except requests.exceptions.Timeout:
            logger.warning(f"微信 code2session 请求超时")
            return {"openid": "", "session_key": "", "timeout": True}
        except Exception as e:
            logger.error(f"微信 code2session 发生异常: {e}")
            raise e

    @staticmethod
    def get_stable_access_token() -> str:
        """
        获取小程序接口全局调用凭证 access_token (使用稳定版接口 getStableAccessToken)
        """
        app_id = Config.WX_APP_ID
        app_secret = Config.WX_APP_SECRET
        if not app_secret:
            raise ValueError("未配置小程序 WX_APP_SECRET，无法获取 access_token")

        url = "https://api.weixin.qq.com/cgi-bin/stable_token"
        payload = {
            "grant_type": "client_credential",
            "appid": app_id,
            "secret": app_secret,
            "force_refresh": False
        }
        res = requests.post(url, json=payload, timeout=10)
        data = res.json()
        token = data.get('access_token')
        if not token:
            logger.error(f"获取 access_token 失败: {data}")
            raise Exception(data.get('errmsg', '获取微信 access_token 失败'))
        return token

    @classmethod
    def get_phone_number(cls, phone_code: str) -> str:
        """
        通过 button open-type="getPhoneNumber" 返回的 code 换取用户微信绑定的手机号
        """
        token = cls.get_stable_access_token()
        url = f"https://api.weixin.qq.com/wxa/business/getuserphonenumber?access_token={token}"
        payload = {"code": phone_code}
        res = requests.post(url, json=payload, timeout=10)
        data = res.json()
        if data.get('errcode') != 0:
            logger.error(f"获取微信手机号失败: {data}")
            raise Exception(data.get('errmsg', '获取微信手机号失败'))
        phone_info = data.get('phone_info') or {}
        phone = phone_info.get('purePhoneNumber') or phone_info.get('phoneNumber')
        if not phone:
            raise Exception('微信返回的手机号为空')
        return phone


wechat_pay = WeChatPayV3()
