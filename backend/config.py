# backend/config.py
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

# 加载 backend/.env 或当前目录 .env
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
load_dotenv()

class Config:
    # MySQL 配置
    MYSQL_HOST = os.getenv('MYSQL_HOST', '127.0.0.1')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DB = os.getenv('MYSQL_DB', 'love_hg')

    # SQLAlchemy — 密码做 URL 编码，防止 @ 等特殊字符破坏连接串
    SQLALCHEMY_DATABASE_URI = (
        f'mysql+pymysql://{MYSQL_USER}:{quote_plus(MYSQL_PASSWORD)}'
        f'@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}'
        '?charset=utf8mb4'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }

    # 种子数据导入密码
    INIT_DATA_PASSWORD = os.getenv('INIT_DATA_PASSWORD', 'admin123')

    # 会员配额配置
    # free/member: 每月首次登录分配，本月内可反复查看
    # vip: 每天首次登录分配30条，当天内可反复查看
    MEMBERSHIP_LIMITS = {
        'free':   {'monthly': 10},
        'member': {'monthly': 30},
        'vip':    {'daily': 30},
    }

    MEMBERSHIP_PRICES = {
        'member': 0.01,   # 普通会员 0.01 元/年
        'vip': 0.02,      # 大会员 0.02 元/年
    }

    # 上传文件配置
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # 项目根目录下的微信支付配置目录
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    PAY_CONFIG_DIR = os.path.join(ROOT_DIR, '微信支付配置')

    # 解析微信支付配置.txt (作为兜底默认值)
    _txt_config = {}
    _config_txt_path = os.path.join(PAY_CONFIG_DIR, '微信支付配置.txt')
    if os.path.exists(_config_txt_path):
        try:
            with open(_config_txt_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        _txt_config[k.strip()] = v.strip()
        except Exception:
            pass

    # 微信小程序与微信支付配置 (优先环境变量，次选 微信支付配置.txt，再选默认值)
    WX_APP_ID = os.getenv('WX_APP_ID', 'wx1a4d12553ae2c86b')               # 小程序 AppID
    WX_APP_SECRET = os.getenv('WX_APP_SECRET', '67ea6ab4ddd4a33f6f757d68f7392115')                   # 小程序 AppSecret (code2session 用)
    WX_MCH_ID = os.getenv('WX_MCH_ID', _txt_config.get('wx.merchantId', ''))
    WX_MCH_NAME = os.getenv('WX_MCH_NAME', _txt_config.get('wx.merchantName', ''))
    WX_API_V3_KEY = os.getenv('WX_API_V3_KEY', _txt_config.get('wx.apiV3Key', ''))
    WX_CERT_SERIAL_NO = os.getenv('WX_CERT_SERIAL_NO', _txt_config.get('wx.merchantSerialNumber', ''))
    WX_PUBLIC_KEY_ID = os.getenv('WX_PUBLIC_KEY_ID', _txt_config.get('wx.publicKeyId', ''))

    # 私钥与公钥配置
    WX_PRIVATE_KEY_PATH = os.getenv('WX_PRIVATE_KEY_PATH', os.path.join(PAY_CONFIG_DIR, 'apiclient_key.pem'))
    WX_PRIVATE_KEY = os.getenv('WX_PRIVATE_KEY', _txt_config.get('wx.privateKey', ''))

    WX_PUBLIC_KEY_PATH = os.getenv('WX_PUBLIC_KEY_PATH', os.path.join(PAY_CONFIG_DIR, 'pub_key.pem'))
    WX_PUBLIC_KEY = os.getenv('WX_PUBLIC_KEY', _txt_config.get('wx.publicKey', ''))

    WX_PAY_NOTIFY_URL = os.getenv('WX_PAY_NOTIFY_URL', 'https://love.yourdomain.com/api/membership/notify') # 支付成功异步回调公网地址
    WX_PAY_MOCK_ENABLED = os.getenv('WX_PAY_MOCK_ENABLED', 'false').lower() in ('true', '1', 'yes') # 是否启用模拟支付兜底

    # 阿里云短信配置
    ALIYUN_ACCESS_KEY_ID = os.getenv('ALIYUN_ACCESS_KEY_ID', '')
    ALIYUN_ACCESS_KEY_SECRET = os.getenv('ALIYUN_ACCESS_KEY_SECRET', '')
    ALIYUN_SMS_SIGN_NAME = os.getenv('ALIYUN_SMS_SIGN_NAME', '')
    ALIYUN_SMS_TEMPLATE_CODE = os.getenv('ALIYUN_SMS_TEMPLATE_CODE', '')

    # 管理员后台配置
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', os.getenv('INIT_DATA_PASSWORD', 'admin123456'))
    ADMIN_TOKEN_SECRET = os.getenv('ADMIN_TOKEN_SECRET', 'love-in-hg-admin-token-secret-2026')


