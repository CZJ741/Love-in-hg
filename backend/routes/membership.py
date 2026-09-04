# backend/routes/membership.py
"""会员购买与支付相关接口"""
import time
import uuid
import random
import string
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from models import db, User, MembershipOrder
from config import Config

membership_bp = Blueprint('membership', __name__)


def generate_order_no():
    """生成商户订单号: YYYYMMDDHHMMSS + 随机串"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices(string.digits, k=6))
    return f"ORD{timestamp}{random_str}"


def grant_membership_to_user(user, member_type):
    """发放会员权益与到期时间（默认 30 天，已是会员则在原有有效期顺延）"""
    now = datetime.utcnow()
    base_time = user.membership_expire if (user.membership_expire and user.membership_expire > now) else now
    # 会员与大会员购买均默认生效 30 天
    user.membership_expire = base_time + timedelta(days=30)
    user.membership_type = member_type
    user.updated_at = now


@membership_bp.route('/purchase', methods=['POST'])
def purchase():
    """
    创建会员订单并统一下单
    返回前端调起微信支付 wx.requestPayment 所需全部参数
    若未配置真实商户号，则返回模拟支付参数，前端与后端可联动测试
    """
    data = request.get_json() or {}
    member_type = data.get('type', '').strip()
    user_id = data.get('userId') or request.headers.get('X-User-Id')

    if member_type not in Config.MEMBERSHIP_PRICES:
        return jsonify(code=400, msg='无效的会员类型'), 400
    if not user_id:
        return jsonify(code=401, msg='请先登录'), 401

    try:
        user = User.query.get(int(user_id))
    except (ValueError, TypeError):
        return jsonify(code=400, msg='无效的用户ID'), 400

    if not user:
        return jsonify(code=401, msg='用户不存在'), 401

    amount = Config.MEMBERSHIP_PRICES[member_type]
    order_no = generate_order_no()

    order = MembershipOrder(
        order_no=order_no,
        user_id=user.id,
        type=member_type,
        amount=amount,
        status='pending',
        created_at=datetime.utcnow()
    )
    db.session.add(order)
    db.session.commit()

    type_labels = {'member': '会员', 'vip': '大会员'}

    # 微信统一下单参数构建
    # 若已配置真实微信商户信息，需请求微信统一下单接口（如 WeChat Pay v3 /v3/pay/transactions/jsapi）
    # 在未配置商户号时，提供模拟/占位参数，方便前端完整链路联调
    has_real_mch = bool(Config.WX_MCH_ID and Config.WX_PAY_API_KEY)

    timestamp = str(int(time.time()))
    nonce_str = uuid.uuid4().hex[:32]

    if has_real_mch:
        # TODO: 接入真实微信支付统一下单 API
        # 1. 向 https://api.mch.weixin.qq.com/v3/pay/transactions/jsapi 发送请求
        # 2. 获取 prepay_id
        # 3. 使用商户私钥对 (appId, timeStamp, nonceStr, prepay_id) 生成 paySign
        prepay_id = f"wx{timestamp}"
        pay_sign = "placeholder_real_pay_sign"
    else:
        # 开发/模拟阶段占位参数
        prepay_id = f"mock_prepay_{order.id}_{timestamp}"
        pay_sign = "mock_pay_sign"

    payment_params = {
        'timeStamp': timestamp,
        'nonceStr': nonce_str,
        'package': f"prepay_id={prepay_id}",
        'signType': 'RSA',
        'paySign': pay_sign
    }

    return jsonify(code=0, msg='订单创建成功', data={
        'orderId': str(order.id),
        'orderNo': order.order_no,
        'amount': amount,
        'type': member_type,
        'typeLabel': type_labels.get(member_type, member_type),
        'isMock': not has_real_mch,
        'payment': payment_params
    })


@membership_bp.route('/order/status', methods=['GET'])
def query_order_status():
    """查询订单状态（供前端轮询或支付结果确认）"""
    order_id = request.args.get('orderId')
    order_no = request.args.get('orderNo')
    user_id = request.args.get('userId') or request.headers.get('X-User-Id')

    query = MembershipOrder.query
    if order_id:
        query = query.filter_by(id=order_id)
    elif order_no:
        query = query.filter_by(order_no=order_no)
    else:
        return jsonify(code=400, msg='缺少订单标识'), 400

    order = query.first()
    if not order:
        return jsonify(code=404, msg='订单不存在'), 404

    # 简单校验所有权
    if user_id and str(order.user_id) != str(user_id):
        return jsonify(code=403, msg='无权查看该订单'), 403

    return jsonify(code=0, msg='获取成功', data=order.to_dict())


@membership_bp.route('/mock-pay-success', methods=['POST'])
def mock_pay_success():
    """
    开发测试环境专属：模拟微信支付成功回调
    用于在未配置微信商户号时，完整走通支付成功、更新订单状态与下发会员特权的闭环
    """
    if not Config.WX_PAY_MOCK_ENABLED:
        return jsonify(code=403, msg='模拟支付接口未开启'), 403

    data = request.get_json() or {}
    order_id = data.get('orderId')
    order_no = data.get('orderNo')

    query = MembershipOrder.query
    if order_id:
        query = query.filter_by(id=order_id)
    elif order_no:
        query = query.filter_by(order_no=order_no)
    else:
        return jsonify(code=400, msg='缺少订单参数'), 400

    order = query.first()
    if not order:
        return jsonify(code=404, msg='订单不存在'), 404

    if order.status == 'paid':
        return jsonify(code=0, msg='订单已是支付状态', data=order.to_dict())

    now = datetime.utcnow()
    order.status = 'paid'
    order.paid_at = now
    order.transaction_id = f"mock_tx_{int(now.timestamp())}"

    user = User.query.get(order.user_id)
    if user:
        grant_membership_to_user(user, order.type)

    db.session.commit()

    return jsonify(code=0, msg='模拟支付成功并已开通会员', data={
        'order': order.to_dict(),
        'membershipType': user.membership_type if user else order.type,
        'membershipExpire': user.membership_expire.isoformat() if user and user.membership_expire else None
    })


@membership_bp.route('/notify', methods=['POST'])
def wx_pay_notify():
    """
    微信支付异步回调通知接口（预留）
    微信支付成功后会向该地址 POST 发送加密通知
    """
    # 真实商户环境接入步骤:
    # 1. 验证微信支付平台签名（避免伪造）
    # 2. 使用 APIv3Key 对 resource 报文解密，获取 order_no、transaction_id、trade_state
    # 3. 校验金额与币种
    # 4. 更新订单为 paid，并调用 grant_membership_to_user(user, order.type)
    # 5. 返回微信规定的 200/SUCCESS JSON 响应
    return jsonify(code="SUCCESS", message="成功")

