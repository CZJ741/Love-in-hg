# backend/config.py
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

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
        'member': 99,
        'vip': 999,
    }

    # 微信支付相关配置（占位，可在 .env 中配置）
    WX_APP_ID = os.getenv('WX_APP_ID', '')               # 小程序 AppID
    WX_MCH_ID = os.getenv('WX_MCH_ID', '')               # 微信支付商户号
    WX_PAY_API_KEY = os.getenv('WX_PAY_API_KEY', '')     # 商户 API 密钥 (v2 apiKey 或 v3 APIv3Key)
    WX_PAY_NOTIFY_URL = os.getenv('WX_PAY_NOTIFY_URL', '') # 支付成功异步回调地址
    WX_PAY_MOCK_ENABLED = os.getenv('WX_PAY_MOCK_ENABLED', 'true').lower() in ('true', '1', 'yes') # 缺少商户号时启用模拟支付/测试支付参数

