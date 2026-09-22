# backend/services/quota_service.py
"""配额服务 — free/member每月分配，vip每日分配，分配后可反复查看"""
from datetime import datetime
from config import Config


def check_and_update_membership(user):
    """
    检查并自动维护用户会员状态：
    若会员已过期，自动降级为普通用户 free
    """
    if user.membership_type in ('member', 'vip') and user.membership_expire:
        if datetime.utcnow() > user.membership_expire:
            user.membership_type = 'free'
    return user.membership_type


def get_membership_limit(user):
    """获取用户配额限制（含过期检查）"""
    m_type = check_and_update_membership(user)
    limits = Config.MEMBERSHIP_LIMITS.get(m_type, Config.MEMBERSHIP_LIMITS['free'])
    if 'daily' in limits:
        return ('daily', limits['daily'])
    return ('monthly', limits['monthly'])


def get_quota_info(user, assigned_count):
    """获取配额信息（仅用于展示）"""
    period_type, limit = get_membership_limit(user)
    return {
        'membershipType': user.membership_type,
        'periodType': period_type,
        'monthlyLimit': limit,
        'monthlyAssigned': assigned_count,
        'remaining': assigned_count,
        'limitReached': False
    }
