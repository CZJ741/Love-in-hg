# backend/models/notice.py
import json
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
    age = db.Column(db.Integer, default=0)
    birthday = db.Column(db.String(10), default='')
    social_account = db.Column(db.String(100), default='')
    occupation = db.Column(db.String(50), default='')
    income = db.Column(db.String(20), default='')
    is_public_sector = db.Column(db.Boolean, default=False)
    height = db.Column(db.Integer, default=0)
    weight = db.Column(db.Integer, default=0)
    # 发布人关系（本人、父母、亲戚、朋友）
    publisher_role = db.Column(db.String(20), default='本人')
    # 住房位置（本地、外地）
    housing_location = db.Column(db.String(20), default='本地')
    images = db.Column(db.Text, default='[]')  # JSON array of image URLs, up to 9
    source = db.Column(db.String(20), default='user')  # user / seed / import
    remark = db.Column(db.Text, default='')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        images_list = []
        if self.images:
            try:
                images_list = json.loads(self.images) if isinstance(self.images, str) else self.images
            except Exception:
                images_list = []

        return {
            'id': self.id,
            '_id': str(self.id),          # 兼容前端
            'userId': str(self.user_id),
            'publisherRole': self.publisher_role or '本人',
            'phone': self.phone,
            'name': self.name,
            'nickname': self.nickname,
            'gender': self.gender,
            'age': self.age or 0,
            'birthday': self.birthday,
            'socialAccount': self.social_account or '',
            'housingLocation': self.housing_location or '本地',
            'occupation': self.occupation,
            'income': self.income,
            'isPublicSector': self.is_public_sector,
            'height': self.height,
            'weight': self.weight,
            'images': images_list,
            'source': self.source,
            'remark': self.remark or '',
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }


