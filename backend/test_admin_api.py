# backend/test_admin_api.py
"""测试管理员后台接口与权限鉴权机制"""
import unittest
from app import create_app
from config import Config
from utils.admin_auth import generate_admin_token, verify_admin_token


class AdminApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.valid_token = generate_admin_token('admin')

    def test_token_generation_and_verification(self):
        token = generate_admin_token('admin', expires_in=100)
        self.assertTrue(bool(token))
        payload = verify_admin_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload['username'], 'admin')

        # 篡改 token 应当失败
        tampered_token = token[:-4] + 'xxxx'
        self.assertIsNone(verify_admin_token(tampered_token))

    def test_unauthorized_access(self):
        # 无 Token 访问应当返回 401
        res = self.client.get('/api/admin/dashboard/stats')
        self.assertEqual(res.status_code, 401)

        res2 = self.client.get('/api/admin/notices')
        self.assertEqual(res2.status_code, 401)

    def test_admin_login_success(self):
        res = self.client.post('/api/admin/login', json={
            'username': Config.ADMIN_USERNAME,
            'password': Config.ADMIN_PASSWORD
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['code'], 0)
        self.assertIn('token', data['data'])

    def test_admin_login_fail(self):
        res = self.client.post('/api/admin/login', json={
            'username': 'admin',
            'password': 'wrong_password_xyz'
        })
        self.assertEqual(res.status_code, 401)

    def test_authorized_dashboard_stats(self):
        res = self.client.get('/api/admin/dashboard/stats', headers={
            'Authorization': f'Bearer {self.valid_token}'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['code'], 0)
        self.assertIn('overview', data['data'])
        self.assertIn('trends', data['data'])


if __name__ == '__main__':
    unittest.main()
