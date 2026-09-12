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

    # 自动检查并补充缺失的字段（如 images, publisher_role, housing_location, age, social_account 字段）
    with app.app_context():
        try:
            from sqlalchemy import text
            with db.engine.connect() as conn:
                result = conn.execute(text("SHOW COLUMNS FROM notices LIKE 'images'"))
                if not result.fetchone():
                    conn.execute(text("ALTER TABLE notices ADD COLUMN images TEXT COMMENT '照片列表(JSON数组)' AFTER weight"))
                    conn.commit()

                result_pub = conn.execute(text("SHOW COLUMNS FROM notices LIKE 'publisher_role'"))
                if not result_pub.fetchone():
                    conn.execute(text("ALTER TABLE notices ADD COLUMN publisher_role VARCHAR(20) DEFAULT '本人' COMMENT '发布人身份' AFTER user_id"))
                    conn.commit()

                result_age = conn.execute(text("SHOW COLUMNS FROM notices LIKE 'age'"))
                if not result_age.fetchone():
                    conn.execute(text("ALTER TABLE notices ADD COLUMN age INT DEFAULT 0 COMMENT '年龄' AFTER gender"))
                    conn.commit()

                result_house = conn.execute(text("SHOW COLUMNS FROM notices LIKE 'housing_location'"))
                if not result_house.fetchone():
                    conn.execute(text("ALTER TABLE notices ADD COLUMN housing_location VARCHAR(20) DEFAULT '本地' COMMENT '住房位置' AFTER birthday"))
                    conn.commit()

                result_social = conn.execute(text("SHOW COLUMNS FROM notices LIKE 'social_account'"))
                if not result_social.fetchone():
                    conn.execute(text("ALTER TABLE notices ADD COLUMN social_account VARCHAR(100) DEFAULT '' COMMENT '社交账号' AFTER birthday"))
                    conn.commit()
        except Exception as e:
            # 若表未创建或连接异常，不阻断启动
            pass


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
