# backend/services/quota_service.py
"""配额服务 — free/member每月分配，vip每日分配，分配后可反复查看"""
from datetime import date
from config import Config


def get_membership_limit(user):
    """获取用户配额限制"""
    limits = Config.MEMBERSHIP_LIMITS.get(user.membership_type, Config.MEMBERSHIP_LIMITS['free'])
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