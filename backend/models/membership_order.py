# backend/models/membership_order.py
from .database import db
from datetime import datetime


class MembershipOrder(db.Model):
    __tablename__ = 'membership_orders'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_no = db.Column(db.String(32), unique=True, nullable=True, index=True)  # 商户订单号
    transaction_id = db.Column(db.String(64), nullable=True)  # 微信支付交易单号
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    type = db.Column(db.String(10), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending / paid / cancelled

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'orderNo': self.order_no,
            'transactionId': self.transaction_id,
            'userId': self.user_id,
            'type': self.type,
            'amount': self.amount,
            'status': self.status,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'paidAt': self.paid_at.isoformat() if self.paid_at else None
        }

