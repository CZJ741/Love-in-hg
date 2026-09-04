# ============================================================
# Love-in-hg Flask 后端 Dockerfile
# 单阶段构建：简单可靠，避免多阶段构建丢可执行文件
# ============================================================

FROM python:3.12-slim

# 标签信息
LABEL maintainer="Love-in-hg Team" \
      description="相亲角 Flask 后端服务" \
      version="1.1"

# 设置时区为中国时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 工作目录
WORKDIR /app

# 先拷贝依赖清单，利用 Docker 层缓存
COPY requirements.txt .

# 安装依赖（gunicorn 的可执行文件会正确装到 /usr/local/bin/）
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 拷贝项目源码
COPY . .

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/ping').read()" || exit 1

# Gunicorn 生产启动
# app:create_app() 带括号 → Gunicorn 先调用工厂函数，拿到 Flask app 实例再作为 WSGI 入口
CMD ["gunicorn", \
     "--workers", "4", \
     "--bind", "0.0.0.0:5000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:create_app()"]
