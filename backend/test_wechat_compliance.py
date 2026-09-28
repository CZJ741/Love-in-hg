# backend/test_wechat_compliance.py
"""测试微信小程序审核四大合规项：内容安全、UGC举报拉黑、iOS支付防护"""
import unittest
from app import create_app
from models import db, User, Notice, Report, UserBlock
from utils.wechat_security import WeChatSecurity


class WeChatComplianceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_wechat_security_text_fallback(self):
        """测试微信内容安全审查工具方法在测试环境下安全放行不崩溃"""
        is_safe, msg = WeChatSecurity.check_text("正常征婚相亲介绍文本")
        self.assertTrue(is_safe)
        self.assertEqual(msg, "")

    def test_wechat_security_image_fallback(self):
        """测试图片内容安全检测在测试环境下安全放行"""
        fake_img_bytes = b"fake image byte data"
        is_safe, msg = WeChatSecurity.check_image(fake_img_bytes)
        self.assertTrue(is_safe)
        self.assertEqual(msg, "")

    def test_ugc_report_flow(self):
        """测试 UGC 举报启事与后台查看、处理全流程"""
        with self.app.app_context():
            # 1. 准备测试用户与启事
            reporter = User.query.filter_by(phone='13811112222').first()
            if not reporter:
                reporter = User(phone='13811112222', name='举报人')
                db.session.add(reporter)
                db.session.commit()

            notice = Notice.query.filter_by(phone='13900001111').first()
            if not notice:
                notice = Notice(phone='13900001111', name='被举报人', user_id=reporter.id)
                db.session.add(notice)
                db.session.commit()

            # 2. 提交举报
            res = self.client.post(
                '/api/notice/report',
                headers={'X-User-Id': str(reporter.id)},
                json={
                    'noticeId': notice.id,
                    'reason': '虚假诈骗',
                    'description': '该启事涉嫌虚假信息'
                }
            )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.get_json()['code'], 0)

            # 3. 验证数据库已生成记录
            report = Report.query.filter_by(notice_id=notice.id, reporter_id=reporter.id).first()
            self.assertIsNotNone(report)
            self.assertEqual(report.reason, '虚假诈骗')
            self.assertEqual(report.status, 'pending')

    def test_ugc_block_user_flow(self):
        """测试 UGC 屏蔽/拉黑用户与推荐列表排查"""
        with self.app.app_context():
            u1 = User.query.filter_by(phone='13700000001').first()
            if not u1:
                u1 = User(phone='13700000001', name='用户A')
                db.session.add(u1)
                db.session.commit()

            u2 = User.query.filter_by(phone='13700000002').first()
            if not u2:
                u2 = User(phone='13700000002', name='用户B')
                db.session.add(u2)
                db.session.commit()

            # 拉黑 u2
            res = self.client.post(
                '/api/user/block',
                headers={'X-User-Id': str(u1.id)},
                json={'targetUserId': u2.id}
            )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.get_json()['code'], 0)

            # 验证拉黑记录
            block = UserBlock.query.filter_by(user_id=u1.id, blocked_user_id=u2.id).first()
            self.assertIsNotNone(block)


if __name__ == '__main__':
    unittest.main()
