# backend/test_account_delete.py
"""测试账号注销与文件物理清理功能"""
import os
import json
import unittest
from app import create_app
from models import db, User, Notice, NoticeView, MembershipOrder
from utils.sms_service import _SMS_CACHE
from utils.file_cleaner import delete_notice_images


class AccountDeleteTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_file_cleaner_security_and_deletion(self):
        """测试图片清理函数防目录穿越与安全删除"""
        with self.app.app_context():
            upload_folder = self.app.config.get(
                'UPLOAD_FOLDER',
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
            )
            os.makedirs(upload_folder, exist_ok=True)

            # 1. 创建合法测试文件
            test_filename = 'test_cleaner_img_2026.jpg'
            test_filepath = os.path.join(upload_folder, test_filename)
            with open(test_filepath, 'w') as f:
                f.write('fake image data')
            self.assertTrue(os.path.exists(test_filepath))

            # 2. 尝试目录穿越攻击（比如尝试删除上级目录文件）
            evil_images = ['../../app.py', '/etc/passwd', '..\\config.py']
            delete_notice_images(evil_images)
            # app.py 和 config.py 绝不能被删除
            self.assertTrue(os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.py')))

            # 3. 正常删除
            delete_notice_images(json.dumps([f"/uploads/{test_filename}"]))
            self.assertFalse(os.path.exists(test_filepath))

    def test_delete_account_verification_code(self):
        """测试注销账号必须校验短信验证码"""
        with self.app.app_context():
            # 创建临时测试用户
            test_phone = '13800009999'
            user = User.query.filter_by(phone=test_phone).first()
            if not user:
                user = User(phone=test_phone, name='注销测试用户')
                db.session.add(user)
                db.session.commit()

            user_id = user.id

            # 1. 不传验证码 -> 400
            res = self.client.post(
                '/api/user/deleteAccount',
                headers={'X-User-Id': str(user_id)},
                json={}
            )
            self.assertEqual(res.status_code, 400)
            self.assertIn('请输入短信验证码', res.get_json()['msg'])

            # 2. 传错误验证码 -> 400
            res = self.client.post(
                '/api/user/deleteAccount',
                headers={'X-User-Id': str(user_id)},
                json={'code': '000000'}
            )
            self.assertEqual(res.status_code, 400)
            self.assertIn('验证码错误', res.get_json()['msg'])

            # 3. 注入有效验证码（使用开发通用码 888888 或缓存注入）
            _SMS_CACHE[test_phone] = {
                'code': '654321',
                'expire_at': 9999999999,
                'send_at': 0
            }

            res = self.client.post(
                '/api/user/deleteAccount',
                headers={'X-User-Id': str(user_id)},
                json={'code': '654321'}
            )
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data['code'], 0)

            # 确认用户已从数据库删除
            deleted_user = User.query.get(user_id)
            self.assertIsNone(deleted_user)


if __name__ == '__main__':
    unittest.main()
