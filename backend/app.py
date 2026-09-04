# backend/app.py
from flask import Flask, jsonify
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

    # 初始化数据库
    db.init_app(app)

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
