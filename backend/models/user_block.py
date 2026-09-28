# backend/models/user_block.py
"""UGC 用户拉黑/屏蔽记录模型"""
from .database import db
from datetime import datetime


class UserBlock(db.Model):
    __tablename__ = 'user_blocks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)  # 执行拉黑的用户
    blocked_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)  # 被拉黑的用户
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'blocked_user_id', name='uix_user_blocked_user'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'userId': self.user_id,
            'blockedUserId': self.blocked_user_id,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }
