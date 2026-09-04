# backend/models/user.py
from .database import db
from datetime import datetime


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    openid = db.Column(db.String(64), default='', index=True)
    phone = db.Column(db.String(11), unique=True, nullable=False, index=True)
    name = db.Column(db.String(20), default='')
    gender = db.Column(db.String(2), default='')
    birthday = db.Column(db.String(10), default='')
    occupation = db.Column(db.String(50), default='')
    income = db.Column(db.String(20), default='')
    is_public_sector = db.Column(db.Boolean, default=False)
    height = db.Column(db.Integer, default=0)
    weight = db.Column(db.Integer, default=0)

    # 会员
    membership_type = db.Column(db.String(10), default='free')  # free / member / vip
    membership_expire = db.Column(db.DateTime, nullable=True)

    # 配额
    monthly_notice_count = db.Column(db.Integer, default=0)
    daily_notice_count = db.Column(db.Integer, default=0)
    last_reset_month = db.Column(db.String(7), default='')
    last_reset_day = db.Column(db.String(10), default='')

    # 时间
    last_login_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'phone': self.phone,
            'name': self.name,
            'gender': self.gender,
            'birthday': self.birthday,
            'occupation': self.occupation,
            'income': self.income,
            'isPublicSector': self.is_public_sector,
            'height': self.height,
            'weight': self.weight,
            'membershipType': self.membership_type,
            'membershipExpire': self.membership_expire.isoformat() if self.membership_expire else None,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }
