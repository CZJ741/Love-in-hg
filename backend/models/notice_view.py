# backend/models/notice_view.py
from .database import db
from datetime import datetime


class NoticeView(db.Model):
    __tablename__ = 'notice_views'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    notice_id = db.Column(db.Integer, db.ForeignKey('notices.id'), nullable=False, index=True)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)
