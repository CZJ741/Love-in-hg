# backend/models/notice.py
from .database import db
from datetime import datetime


class Notice(db.Model):
    __tablename__ = 'notices'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), default=0, index=True)
    phone = db.Column(db.String(11), default='', index=True)
    name = db.Column(db.String(20), default='')
    nickname = db.Column(db.String(50), default='')
    gender = db.Column(db.String(2), default='')
    birthday = db.Column(db.String(10), default='')
    occupation = db.Column(db.String(50), default='')
    income = db.Column(db.String(20), default='')
    is_public_sector = db.Column(db.Boolean, default=False)
    height = db.Column(db.Integer, default=0)
    weight = db.Column(db.Integer, default=0)
    source = db.Column(db.String(20), default='user')  # user / seed / import
    remark = db.Column(db.Text, default='')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            '_id': str(self.id),          # 兼容前端
            'userId': str(self.user_id),
            'phone': self.phone,
            'name': self.name,
            'nickname': self.nickname,
            'gender': self.gender,
            'birthday': self.birthday,
            'occupation': self.occupation,
            'income': self.income,
            'isPublicSector': self.is_public_sector,
            'height': self.height,
            'weight': self.weight,
            'source': self.source,
            'remark': self.remark or '',
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }
