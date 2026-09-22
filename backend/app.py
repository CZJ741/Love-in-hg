# backend/app.py
import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from config import Config
from models.database import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 显式配置 CORS：允许所有来源、所有方法、所有自定义头
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
            "allow_headers": ["Content-Type", "X-User-Id", "Authorization", "X-Requested-With", "Accept"],
            "expose_headers": ["Content-Type", "X-User-Id"],
            "supports_credentials": False,
            "max_age": 86400
        }
    })

    # 统一 OPTIONS 预检处理，确保所有路由都响应 204
    @app.after_request
    def after_request(resp):
        # 错误响应也补上 CORS 头（兜底）
        if 'Access-Control-Allow-Origin' not in resp.headers:
            resp.headers['Access-Control-Allow-Origin'] = '*'
        if 'Access-Control-Allow-Headers' not in resp.headers:
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-User-Id, Authorization, X-Requested-With, Accept'
        if 'Access-Control-Allow-Methods' not in resp.headers:
            resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD'
        return resp

    # 根路径健康检查（避免 404 被误判为跨域问题）
    @app.route('/')
    def index():
        return jsonify(code=0, msg='Love-in-hg backend is running', data={'service': '相亲角后端', 'status': 'ok'})

    @app.route('/ping')
    def ping():
        return jsonify(code=0, msg='pong')

    # 静态文件访问：上传的图片 /uploads/<filename>
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        upload_folder = app.config.get('UPLOAD_FOLDER', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads'))
        return send_from_directory(upload_folder, filename)


    # 初始化数据库
    db.init_app(app)

    # 自动检查并补充缺失的字段/表，保证老数据库升级后结构完整
    #
    # 说明：项目未接入 Alembic，改用「启动时幂等补齐」的方式做轻量迁移。
    # 这里显式调用 db.create_all()，确保模型新增的表（如 membership_orders）
    # 在老库上也会被自动创建，避免 "Unknown column / Table doesn't exist" 类报错。
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            app.logger.warning(f"db.create_all() 失败（不影响启动）: {e}")

        try:
            from sqlalchemy import text

            # 需要补齐的列：(表名, 列名, 建列 SQL)
            required_columns = [
                ('notices', 'images',
                 "ALTER TABLE notices ADD COLUMN images TEXT COMMENT '照片列表(JSON数组)' AFTER weight"),
                ('notices', 'publisher_role',
                 "ALTER TABLE notices ADD COLUMN publisher_role VARCHAR(20) DEFAULT '本人' COMMENT '发布人身份' AFTER user_id"),
                ('notices', 'age',
                 "ALTER TABLE notices ADD COLUMN age INT DEFAULT 0 COMMENT '年龄' AFTER gender"),
                ('notices', 'housing_location',
                 "ALTER TABLE notices ADD COLUMN housing_location VARCHAR(20) DEFAULT '本地' COMMENT '住房位置' AFTER age"),
                ('notices', 'social_account',
                 "ALTER TABLE notices ADD COLUMN social_account VARCHAR(100) DEFAULT '' COMMENT '社交账号' AFTER age"),
                # 以下为会员订单表历史缺失字段（2026-09-15 补充）
                ('membership_orders', 'order_no',
                 "ALTER TABLE membership_orders ADD COLUMN order_no VARCHAR(32) NULL COMMENT '商户订单号' AFTER id"),
                ('membership_orders', 'transaction_id',
                 "ALTER TABLE membership_orders ADD COLUMN transaction_id VARCHAR(64) NULL COMMENT '微信支付交易单号' AFTER order_no"),
            ]

            with db.engine.begin() as conn:
                for table, column, ddl in required_columns:
                    # 表不存在时跳过（create_all 已负责建表）
                    if not conn.execute(text("SHOW TABLES LIKE :t"), {'t': table}).fetchone():
                        continue
                    exists = conn.execute(
                        text("SHOW COLUMNS FROM `%s` LIKE :c" % table), {'c': column}
                    ).fetchone()
                    if not exists:
                        conn.execute(text(ddl))
                        app.logger.info(f"自动迁移: {table}.{column} 已补齐")

                # order_no 的唯一索引单独补齐（ADD COLUMN 时不带 UNIQUE，便于老数据为空值）
                if conn.execute(text("SHOW TABLES LIKE 'membership_orders'")).fetchone():
                    idx = conn.execute(text("SHOW INDEX FROM membership_orders WHERE Key_name = 'uk_order_no'")).fetchone()
                    if not idx:
                        conn.execute(text("ALTER TABLE membership_orders ADD UNIQUE KEY uk_order_no (order_no)"))
                        app.logger.info("自动迁移: membership_orders.uk_order_no 唯一索引已补齐")
        except Exception as e:
            # 若表未创建或连接异常，不阻断启动
            app.logger.warning(f"自动迁移检查失败（不阻断启动）: {e}")


    # 注册蓝图

    from routes.auth import auth_bp
    from routes.notice import notice_bp
    from routes.user import user_bp
    from routes.membership import membership_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(notice_bp, url_prefix='/api/notice')
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(membership_bp, url_prefix='/api/membership')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
