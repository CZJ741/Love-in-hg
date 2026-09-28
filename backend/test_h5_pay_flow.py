# backend/test_h5_pay_flow.py
"""测试移动端 H5 会员开通与多端权益互通完整流程"""
import unittest
from datetime import datetime, timedelta
from app import create_app
from models import db, User, MembershipOrder
from config import Config


class H5PayFlowTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_h5_membership_config_endpoint(self):
        """测试获取 H5 价格与配置接口"""
        res = self.client.get('/api/membership/config')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['code'], 0)
        self.assertIn('tiers', data['data'])
        self.assertIn('prices', data['data'])

    def test_h5_purchase_and_multi_platform_equity_sync(self):
        """测试 H5 下单并支付后，同一手机号在多端（含小程序端）权益实时互通"""
        with self.app.app_context():
            test_phone = '13699998888'
            user = User.query.filter_by(phone=test_phone).first()
            if not user:
                user = User(phone=test_phone, name='H5多端测试用户', membership_type='free')
                db.session.add(user)
                db.session.commit()
            else:
                user.membership_type = 'free'
                user.membership_expire = None
                db.session.commit()

            # 1. 验证在 H5 端下单
            res = self.client.post('/api/membership/h5-purchase', json={
                'phone': test_phone,
                'type': 'vip',
                'redirectUrl': 'https://aibao.love/pay'
            })
            self.assertEqual(res.status_code, 200)
            order_data = res.get_json()['data']
            order_no = order_data['orderNo']
            order_id = order_data['orderId']

            # 2. 模拟支付成功 (回调或测试流)
            res_pay = self.client.post('/api/membership/mock-pay-success', json={
                'orderId': order_id,
                'orderNo': order_no
            })
            # 如果本地允许 mock 则通过
            if Config.WX_PAY_MOCK_ENABLED:
                self.assertEqual(res_pay.status_code, 200)
            else:
                # 若未开启 Mock，手动触发发放逻辑测试多端生效
                from routes.membership import grant_membership_to_user
                grant_membership_to_user(user, 'vip')
                db.session.commit()

            # 3. 验证后端数据库中该用户的权益
            refreshed_user = User.query.get(user.id)
            self.assertEqual(refreshed_user.membership_type, 'vip')
            self.assertIsNotNone(refreshed_user.membership_expire)
            self.assertTrue(refreshed_user.membership_expire > datetime.utcnow() + timedelta(days=360))

            # 4. 模拟微信小程序端以该手机号调用 profile 获取资料，验证权益全端即时可见
            mp_res = self.client.get(f'/api/user/profile?userId={user.id}')
            self.assertEqual(mp_res.status_code, 200)
            mp_data = mp_res.get_json()['data']
            self.assertEqual(mp_data['quota']['membershipType'], 'vip')
            self.assertEqual(mp_data['quota']['periodType'], 'daily')
            self.assertEqual(mp_data['quota']['monthlyLimit'], 30)

    def test_h5_page_serving(self):
        """测试 /pay 路由能正确返回移动端 H5 静态收银台页面"""
        res = self.client.get('/pay')
        self.assertEqual(res.status_code, 200)
        self.assertIn('相亲角 · 会员服务中心', res.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
