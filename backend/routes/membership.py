# backend/routes/membership.py
"""会员购买与支付相关接口"""
import logging
import random
import string
import time
import uuid
from datetime import datetime, timedelta
from urllib.parse import quote
from flask import Blueprint, request, jsonify, current_app
from models import db, User, MembershipOrder
from config import Config
from utils.wechat_pay import wechat_pay

logger = logging.getLogger(__name__)

membership_bp = Blueprint('membership', __name__)


def generate_order_no():
    """生成商户订单号: YYYYMMDDHHMMSS + 随机串"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices(string.digits, k=6))
    return f"ORD{timestamp}{random_str}"


def grant_membership_to_user(user, member_type):
    """发放会员权益与到期时间（年费会员，开通/续费均为 365 天/1 年，已是有效会员则在原有有效期顺延）"""
    now = datetime.utcnow()
    base_time = user.membership_expire if (user.membership_expire and user.membership_expire > now) else now
    # 会员与大会员均为年费，购买生效 365 天（1年）
    user.membership_expire = base_time + timedelta(days=365)
    user.membership_type = member_type
    user.updated_at = now


@membership_bp.route('/purchase', methods=['POST'])
def purchase():
    """
    创建会员订单并统一下单
    支持：
    1. 真实微信支付 V3 JSAPI 统一下单 (若已配置商户参数)
    2. 模拟支付参数回退 (未配置商户参数或开启 WX_PAY_MOCK_ENABLED 时的测试)
    """
    data = request.get_json() or {}
    member_type = data.get('type', '').strip()
    user_id = data.get('userId') or request.headers.get('X-User-Id')
    code = data.get('code', '').strip()          # 小程序 wx.login 传入的临时 code
    openid = data.get('openid', '').strip()      # 可选：前端直接传入已缓存的 openid

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

    # 优先使用用户已绑定的 openid，次选前端传参，再次选通过 code 换取
    target_openid = user.openid or openid
    if not target_openid and code:
        try:
            session_info = wechat_pay.code2session(code)
            target_openid = session_info.get('openid', '')
            if target_openid:
                user.openid = target_openid
                db.session.commit()
        except Exception as e:
            logger.warning(f"通过 code 换取 openid 失败: {e}")

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
    desc = f"开通{type_labels.get(member_type, '会员')}"

    # 判断是否使用真实微信支付 V3
    use_real_pay = wechat_pay.is_configured() and bool(target_openid)

    if use_real_pay:
        try:
            # 微信支付金额单位为「分」，且必须为整数，故四舍五入避免 0.01*100 浮点误差
            total_cents = int(round(amount * 100))
            res_order = wechat_pay.jsapi_order(
                out_trade_no=order.order_no,
                total_amount_cents=total_cents,
                description=desc,
                openid=target_openid
            )
            prepay_id = res_order.get('prepay_id')
            if not prepay_id:
                raise Exception(f"微信返回无 prepay_id: {res_order}")

            payment_params = wechat_pay.build_miniprogram_payment_params(prepay_id)
            is_mock = False
        except Exception as e:
            logger.error(f"微信支付统一下单异常: {e}")
            if Config.WX_PAY_MOCK_ENABLED:
                logger.info("微信统一下单失败，降级为 Mock 支付")
                timestamp = str(int(time.time()))
                payment_params = {
                    'timeStamp': timestamp,
                    'nonceStr': uuid.uuid4().hex[:32],
                    'package': f"prepay_id=mock_prepay_{order.id}_{timestamp}",
                    'signType': 'RSA',
                    'paySign': 'mock_pay_sign'
                }
                is_mock = True
            else:
                return jsonify(code=500, msg=f"微信支付下单失败: {str(e)}"), 500
    else:
        if wechat_pay.is_configured() and not target_openid:
            # 商户已配置但缺少 openid
            if not Config.WX_PAY_MOCK_ENABLED:
                return jsonify(code=400, msg="缺少用户微信 openid，请先通过微信登录授权"), 400

        # Mock 模式兜底
        timestamp = str(int(time.time()))
        payment_params = {
            'timeStamp': timestamp,
            'nonceStr': uuid.uuid4().hex[:32],
            'package': f"prepay_id=mock_prepay_{order.id}_{timestamp}",
            'signType': 'RSA',
            'paySign': 'mock_pay_sign'
        }
        is_mock = True

    return jsonify(code=0, msg='订单创建成功', data={
        'orderId': str(order.id),
        'orderNo': order.order_no,
        'amount': amount,
        'type': member_type,
        'typeLabel': type_labels.get(member_type, member_type),
        'isMock': is_mock,
        'payment': payment_params
    })


@membership_bp.route('/config', methods=['GET'])
def get_membership_config():
    """获取会员体系配置与价格说明（供 H5 移动网页动态展示）"""
    return jsonify(code=0, msg='获取成功', data={
        'prices': Config.MEMBERSHIP_PRICES,
        'limits': Config.MEMBERSHIP_LIMITS,
        'tiers': [
            {
                'type': 'member',
                'name': '会员',
                'price': Config.MEMBERSHIP_PRICES.get('member', 0.01),
                'duration': '1年 (365天)',
                'quotaDesc': '每月 30 条相亲启事配额',
                'badge': '限时优惠'
            },
            {
                'type': 'vip',
                'name': '大会员',
                'price': Config.MEMBERSHIP_PRICES.get('vip', 0.02),
                'duration': '1年 (365天)',
                'quotaDesc': '每天 30 条相亲启事配额（海量浏览）',
                'badge': '最受欢迎'
            }
        ]
    })


@membership_bp.route('/h5-purchase', methods=['POST'])
def h5_purchase():
    """
    移动端独立网页 H5 创建订单并统一下单
    支持：手机浏览器拉起微信支付 (WeChat H5 Pay) 或开发环境 Mock 支付
    """
    data = request.get_json() or {}
    member_type = data.get('type', '').strip()
    phone = (data.get('phone') or '').strip()
    user_id = data.get('userId') or request.headers.get('X-User-Id')
    redirect_url = (data.get('redirectUrl') or '').strip()

    if member_type not in Config.MEMBERSHIP_PRICES:
        return jsonify(code=400, msg='无效的会员类型'), 400

    user = None
    if user_id:
        try:
            user = User.query.get(int(user_id))
        except (ValueError, TypeError):
            pass
    elif phone:
        user = User.query.filter_by(phone=phone).first()

    if not user:
        return jsonify(code=401, msg='请先输入手机号登录或验证身份'), 401

    amount = Config.MEMBERSHIP_PRICES[member_type]
    order = MembershipOrder(
        order_no=generate_order_no(),
        user_id=user.id,
        type=member_type,
        amount=int(round(amount * 100)),
        status='pending'
    )
    db.session.add(order)
    db.session.commit()

    type_labels = {'member': '会员', 'vip': '大会员'}
    desc = f"相亲角-开通{type_labels.get(member_type, '会员')}"

    # 获取客户端公网 IP (微信 H5 支付必须参数)
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()

    use_real_pay = wechat_pay.is_configured() and not Config.WX_PAY_MOCK_ENABLED

    if use_real_pay:
        try:
            total_cents = int(round(amount * 100))
            h5_res = wechat_pay.h5_order(
                out_trade_no=order.order_no,
                total_amount_cents=total_cents,
                description=desc,
                client_ip=client_ip
            )
            raw_h5_url = h5_res.get('h5_url')
            if not raw_h5_url:
                raise Exception(f"微信返回无 h5_url: {h5_res}")

            final_h5_url = raw_h5_url
            if redirect_url:
                final_h5_url = f"{raw_h5_url}&redirect_url={quote(redirect_url, safe='')}"

            return jsonify(code=0, msg='下单成功', data={
                'orderId': str(order.id),
                'orderNo': order.order_no,
                'amount': amount,
                'type': member_type,
                'payType': 'wechat_h5',
                'h5Url': final_h5_url,
                'isMock': False
            })
        except Exception as e:
            logger.error(f"微信支付 H5 统一下单失败: {e}")
            err_str = str(e)
            # 若商户后台暂未在产品中心勾选开通 H5 支付权限 (NO_AUTH)，或者测试环境下，自动优雅降级为 Mock 模式，确保业务闭环
            if 'NO_AUTH' in err_str or '商户号该产品权限未开通' in err_str or current_app.config.get('TESTING'):
                logger.warning("商户号尚未开通 H5 支付权限，已自动降级为测试支付模式")
                return jsonify(code=0, msg='商户H5支付权限审核中，当前已切入测试模式', data={
                    'orderId': str(order.id),
                    'orderNo': order.order_no,
                    'amount': amount,
                    'type': member_type,
                    'payType': 'mock',
                    'isMock': True
                })
            return jsonify(code=500, msg=f'拉起微信支付失败: {err_str}'), 500

    # 兜底与 Mock 体验模式
    return jsonify(code=0, msg='下单成功(体验模式)', data={
        'orderId': str(order.id),
        'orderNo': order.order_no,
        'amount': amount,
        'type': member_type,
        'payType': 'mock',
        'isMock': True
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

    # 校验所有权
    if user_id and str(order.user_id) != str(user_id):
        return jsonify(code=403, msg='无权查看该订单'), 403

    # 若本地仍是 pending 且配置了微信商户，主动向微信查单同步，避免回调丢失
    if order.status == 'pending' and wechat_pay.is_configured():
        try:
            wx_data = wechat_pay.query_order(order.order_no)
            trade_state = wx_data.get('trade_state')
            if trade_state == 'SUCCESS':
                order.status = 'paid'
                order.transaction_id = wx_data.get('transaction_id')
                success_time = wx_data.get('success_time')
                order.paid_at = datetime.fromisoformat(success_time.replace('Z', '+00:00')) if success_time else datetime.utcnow()
                user = User.query.get(order.user_id)
                if user:
                    grant_membership_to_user(user, order.type)
                db.session.commit()
            elif trade_state in ('CLOSED', 'REVOKED', 'PAYERROR'):
                order.status = 'failed'
                db.session.commit()
        except Exception as e:
            logger.warning(f"主动向微信查单异常: {e}")

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
    微信支付 V3 异步回调通知接口
    微信支付成功后会向该地址 POST 发送加密通知
    """
    try:
        # 1. 获取微信通知 Header 参数
        timestamp = request.headers.get('Wechatpay-Timestamp', '')
        nonce = request.headers.get('Wechatpay-Nonce', '')
        signature = request.headers.get('Wechatpay-Signature', '')
        serial_no = request.headers.get('Wechatpay-Serial', '')
        body_text = request.get_data(as_text=True)

        if not signature or not timestamp or not nonce:
            logger.warning("微信回调缺少签名参数")
            return jsonify(code="FAIL", message="签名参数缺失"), 400

        # 2. 验签 (使用微信支付公钥 pub_key.pem)
        if not wechat_pay.verify_callback_signature(timestamp, nonce, body_text, signature):
            logger.error("微信支付回调签名验证失败")
            return jsonify(code="FAIL", message="签名验证失败"), 401

        # 3. 解析请求 JSON 并解密 resource
        notify_data = json.loads(body_text) if body_text else {}
        event_type = notify_data.get('event_type')
        if event_type != 'TRANSACTION.SUCCESS':
            # 非支付成功事件直接返回 SUCCESS 确认
            return jsonify(code="SUCCESS", message="成功")

        resource = notify_data.get('resource', {})
        associated_data = resource.get('associated_data', '')
        resource_nonce = resource.get('nonce', '')
        ciphertext = resource.get('ciphertext', '')

        plain_data = wechat_pay.decrypt_callback_resource(associated_data, resource_nonce, ciphertext)
        logger.info(f"微信支付回调解密结果: {plain_data}")

        # 4. 校验订单号与状态
        out_trade_no = plain_data.get('out_trade_no')
        trade_state = plain_data.get('trade_state')
        transaction_id = plain_data.get('transaction_id')
        total_fee = plain_data.get('amount', {}).get('total', 0)

        if not out_trade_no or trade_state != 'SUCCESS':
            return jsonify(code="SUCCESS", message="非成功状态无需处理")

        order = MembershipOrder.query.filter_by(order_no=out_trade_no).first()
        if not order:
            logger.error(f"微信支付回调未找到订单: {out_trade_no}")
            return jsonify(code="SUCCESS", message="订单不存在")

        # 幂等处理：如果已支付，直接返回成功
        if order.status == 'paid':
            return jsonify(code="SUCCESS", message="成功")

        # 校验金额 (数据库金额为元，微信为分)
        expected_cents = int(order.amount * 100)
        if total_fee != expected_cents:
            logger.error(f"订单金额不一致: 期望 {expected_cents}分, 微信通知 {total_fee}分")
            return jsonify(code="FAIL", message="订单金额不一致"), 400

        # 5. 更新订单状态并开通/续费会员权益
        now = datetime.utcnow()
        order.status = 'paid'
        order.transaction_id = transaction_id
        order.paid_at = now

        user = User.query.get(order.user_id)
        if user:
            grant_membership_to_user(user, order.type)

        db.session.commit()
        logger.info(f"订单 {out_trade_no} 支付成功，已为用户 {order.user_id} 开通 {order.type}")

        return jsonify(code="SUCCESS", message="成功")

    except Exception as e:
        logger.exception(f"处理微信支付回调异常: {e}")
        return jsonify(code="FAIL", message=str(e)), 500
