# backend/models/report.py
"""UGC 用户举报记录模型"""
from .database import db
from datetime import datetime


class Report(db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    notice_id = db.Column(db.Integer, db.ForeignKey('notices.id'), nullable=False, index=True)
    reason = db.Column(db.String(50), nullable=False)  # 涉黄低俗 / 虚假诈骗 / 广告骚扰 / 侵犯隐私 / 其他
    description = db.Column(db.String(500), default='')
    status = db.Column(db.String(20), default='pending', index=True)  # pending / resolved / rejected
    handle_result = db.Column(db.String(255), default='')
    handled_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'reporterId': self.reporter_id,
            'noticeId': self.notice_id,
            'reason': self.reason,
            'description': self.description,
            'status': self.status,
            'handleResult': self.handle_result,
            'handledAt': self.handled_at.isoformat() if self.handled_at else None,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }
