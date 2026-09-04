# Love-in-hg Docker 服务器部署完整方案

> 适用环境：Linux 服务器（宝塔面板）+ Docker + MySQL
> 核心思路：**全部在服务器 SSH 上操作，直接构建镜像，不从 Windows 传 tar 包**
> 预计耗时：15-20 分钟（含镜像构建下载时间）

---

## 目录

- [第 0 步：前置条件检查](#第-0-步前置条件检查)
- [第 1 步：上传项目源码到服务器](#第-1-步上传项目源码到服务器)
- [第 2 步：创建 requirements.txt](#第-2-步创建-requirementstxt)
- [第 3 步：创建 Dockerfile](#第-3-步创建-dockerfile)
- [第 4 步：创建 .dockerignore](#第-4-步创建-dockerignore)
- [第 5 步：构建 Docker 镜像](#第-5-步构建-docker-镜像)
- [第 6 步：导入 MySQL 数据库](#第-6-步导入-mysql-数据库)
- [第 7 步：启动容器](#第-7-步启动容器)
- [第 8 步：验证部署](#第-8-步验证部署)
- [第 9 步：配置 Nginx 反向代理（可选）](#第-9-步配置-nginx-反向代理可选)
- [附录：日常运维命令](#附录日常运维命令)
- [附录：常见问题排查](#附录常见问题排查)

---

## 第 0 步：前置条件检查

SSH 登录服务器，逐条执行以下命令确认环境就绪：

```bash
# 1. 检查 Docker 是否安装并运行（应输出版本号，不报错）
docker --version
docker info

# 2. 检查 Docker Compose（可选，本方案不需要）
docker compose version

# 3. 检查 MySQL 是否运行（宝塔面板装的 MySQL 用这条）
systemctl status mysqld
# 或者
mysql --version

# 4. 检查 MySQL 版本（重要！决定建表 SQL 用哪种排序规则）
mysql -uroot -p -e "SELECT VERSION();"
```

**版本对照表**：

| MySQL 版本 | 排序规则 | 说明 |
|---|---|---|
| 8.0+ | `utf8mb4_0900_ai_ci` 可用 | Navicat 导出的 SQL 可直接用 |
| 5.7 / 5.6 | 必须用 `utf8mb4_general_ci` | 否则报 `#1273 Unknown collation` |

> 如果 Docker 未安装，先在宝塔面板「Docker」菜单安装，或执行：
> `curl -fsSL https://get.docker.com | bash && systemctl enable --now docker`

---

## 第 1 步：上传项目源码到服务器

### 方式 A：宝塔文件管理器上传（推荐）

1. 在 Windows 本地，把 `D:\czj_project\Love-in-hg\backend` 文件夹**压缩为 zip**
   - 压缩前删除这些内容：`__pycache__/`、`.idea/`、`love-in-hg*.tar`、`.env`
2. 宝塔面板 → 文件 → 进入 `/www/wwwroot/love-in-hg/`
3. 上传 `backend.zip` → 右键解压
4. 确认目录结构如下：

```
/www/wwwroot/love-in-hg/backend/
├── app.py
├── config.py
├── models/
│   ├── __init__.py
│   ├── database.py
│   ├── membership_order.py
│   ├── notice.py
│   ├── notice_view.py
│   └── user.py
├── routes/
│   ├── __init__.py
│   ├── admin.py
│   ├── auth.py
│   ├── membership.py
│   ├── notice.py
│   └── user.py
├── services/
│   ├── __init__.py
│   ├── extract_service.py
│   └── quota_service.py
└── utils/
    ├── __init__.py
    └── ...
```

### 方式 B：Git 拉取（如果代码在 GitHub）

```bash
cd /www/wwwroot/love-in-hg
git clone 你的仓库地址 backend
```

### 验证源码完整

```bash
ls -la /www/wwwroot/love-in-hg/backend/
# 必须能看到 app.py 和 config.py，以及 models/ routes/ services/ utils/ 四个目录
```

---

## 第 2 步：创建 requirements.txt

SSH 执行（整段复制粘贴，回车）：

```bash
cat > /www/wwwroot/love-in-hg/backend/requirements.txt << 'EOF'
Flask==3.1.0
Flask-CORS==5.0.1
Flask-SQLAlchemy==3.1.1
PyMySQL==1.1.1
cryptography==44.0.2
gunicorn==23.0.0
python-dotenv==1.1.0
EOF
```

验证：

```bash
cat /www/wwwroot/love-in-hg/backend/requirements.txt
```

---

## 第 3 步：创建 Dockerfile

SSH 执行（整段复制粘贴）：

```bash
cat > /www/wwwroot/love-in-hg/backend/Dockerfile << 'EOF'
FROM python:3.12-slim

LABEL maintainer="Love-in-hg Team" \
      description="相亲角 Flask 后端服务" \
      version="1.1"

ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/ping').read()" || exit 1

CMD ["gunicorn", \
     "--workers", "4", \
     "--bind", "0.0.0.0:5000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:create_app"]
EOF
```

> **要点**：单阶段构建，`pip install` 直接装进系统，gunicorn 可执行文件会正确出现在 `/usr/local/bin/gunicorn`。
> （之前失败的多阶段构建 `pip install --target=` 方式会丢失这个入口文件）

---

## 第 4 步：创建 .dockerignore

SSH 执行（整段复制粘贴）：

```bash
cat > /www/wwwroot/love-in-hg/backend/.dockerignore << 'EOF'
__pycache__/
*.pyc
*.pyo
.venv/
venv/
test_fix.py
verify.py
reset.py
*.tmp
*.log
.idea/
.vscode/
.git/
.gitignore
.env
.env.local
*.pem
*.key
Dockerfile
.dockerignore
docker-compose*.yml
*.md
docs/
seed/
*.tar
*.zip
EOF
```

**验证三个文件都创建好了**：

```bash
ls -la /www/wwwroot/love-in-hg/backend/ | grep -E "Dockerfile|requirements|dockerignore"
# 应看到三行：Dockerfile、requirements.txt、.dockerignore
```

---

## 第 5 步：构建 Docker 镜像

```bash
cd /www/wwwroot/love-in-hg/backend

# 删掉旧的失败镜像（如果有）
docker rmi love-in-hg:latest 2>/dev/null

# 构建镜像（首次需下载 python:3.12-slim 基础镜像，约 1-3 分钟）
docker build -t love-in-hg:latest .
```

**构建成功的标志**（最后几行）：

```
 => => naming to docker.io/library/love-in-hg:latest
```

验证镜像存在：

```bash
docker images | grep love-in-hg
# 应看到 love-in-hg   latest   <镜像ID>   几分钟前   约200MB
```

---

## 第 6 步：导入 MySQL 数据库

### 6.1 创建数据库

宝塔面板 → 数据库 → 添加数据库：

| 配置项 | 值 |
|---|---|
| 数据库名 | `love_hg` |
| 用户名 | `love_hg`（或 root） |
| 密码 | 自己设一个，**记下来** |
| 字符集 | `utf8mb4` |

或用命令行：

```bash
mysql -uroot -p -e "CREATE DATABASE IF NOT EXISTS love_hg DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"
```

### 6.2 导入表结构

**情况 A：MySQL 8.0** — 直接导入 Navicat 导出的 `love_hg.sql`

**情况 B：MySQL 5.7 及以下** — 导入前先把 SQL 文件里所有 `utf8mb4_0900_ai_ci` 替换为 `utf8mb4_general_ci`（桌面上的 love_hg.sql 已经改好了）

宝塔面板 → 数据库 → love_hg → 导入 → 上传 SQL 文件 → 导入

或命令行：

```bash
mysql -uroot -p love_hg < /www/wwwroot/love-in-hg/love_hg.sql
```

### 6.3 验证表已创建

```bash
mysql -uroot -p -e "USE love_hg; SHOW TABLES;"
# 应看到 4 张表：membership_orders, notice_views, notices, users
```

---

## 第 7 步：启动容器

### 关键概念：容器里访问宿主机 MySQL

容器内的 `127.0.0.1` 是容器自己，**不是服务器**。所以 `MYSQL_HOST` 不能填 `127.0.0.1`。

| 场景 | MYSQL_HOST 填什么 |
|---|---|
| MySQL 装在宿主机（宝塔），Docker 版本 ≥ 20.10 | `host.docker.internal`（需加 `--add-host` 参数） |
| MySQL 装在宿主机（宝塔），任何 Docker 版本 | `172.17.0.1`（Docker 默认网桥网关，最通用） |
| MySQL 也是 Docker 容器 | 该容器的名字或 IP |

### 启动命令（MySQL 在宿主机的情况，最常见）

```bash
docker rm -f love-hg-api 2>/dev/null

docker run -d \
  --name love-hg-api \
  --restart always \
  --add-host=host.docker.internal:host-gateway \
  -p 5000:5000 \
  -e MYSQL_HOST=172.17.0.1 \
  -e MYSQL_PORT=3306 \
  -e MYSQL_USER=root \
  -e MYSQL_PASSWORD=你的数据库密码 \
  -e MYSQL_DB=love_hg \
  love-in-hg:latest
```

**参数说明**：

| 参数 | 作用 |
|---|---|
| `--name love-hg-api` | 容器名，方便管理 |
| `--restart always` | 服务器重启后容器自动拉起 |
| `-p 5000:5000` | 宿主机 5000 端口映射到容器 5000 |
| `-e MYSQL_*` | 数据库连接信息，覆盖容器内默认值 |
| `host.docker.internal` 备用 | 如果 172.17.0.1 连不上，把 `MYSQL_HOST` 换成 `host.docker.internal` |

> **注意**：如果 MySQL 用的是 `love_hg` 专用用户（不是 root），需要先授权容器网段访问：
> ```sql
> -- 在 mysql 命令行执行
> GRANT ALL ON love_hg.* TO 'love_hg'@'172.17.%' IDENTIFIED BY '密码';
> FLUSH PRIVILEGES;
> ```
> 宝塔面板装 MySQL 默认 root 只允许 localhost 访问，也可能需要改成"所有人"或添加授权。

---

## 第 8 步：验证部署

### 8.1 看容器状态

```bash
docker ps | grep love-hg-api
# STATUS 列应显示 "Up X minutes (healthy)"
```

### 8.2 看启动日志

```bash
docker logs love-hg-api
# 正常应看到:
# [INFO] Starting gunicorn 23.0.0
# [INFO] Listening at: http://0.0.0.0:5000 (1)
# [INFO] Booting worker with pid: 7 ...
```

### 8.3 本机测试接口

```bash
curl http://127.0.0.1:5000/
curl http://127.0.0.1:5000/ping
# 应返回 JSON: {"code":0,"msg":"pong",...}
```

### 8.4 测试数据库连接（登录接口）

```bash
curl -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800000001"}'
```

- 返回 `code:0` → **数据库连接成功，部署完成！** 🎉
- 返回 500 或超时 → 数据库连不上，看[附录排查](#附录常见问题排查)

### 8.5 防火墙放行（外网访问才需要）

```bash
# 宝塔面板 → 安全 → 放行 5000 端口
# 云服务器还需在云控制台安全组放行 5000（或后续用 Nginx 反代后只放行 80/443）
```

---

## 第 9 步：配置 Nginx 反向代理（可选）

生产环境建议用域名 + HTTPS，不直接暴露 5000 端口。

宝塔面板 → 网站 → 添加站点（绑定你的域名，如 `api.your-domain.com`）→ 设置 → 反向代理：

| 配置项 | 值 |
|---|---|
| 代理名称 | love-hg-api |
| 目标 URL | `http://127.0.0.1:5000` |
| 发送域名 | `$host` |

然后申请 SSL 证书（宝塔 → SSL → Let's Encrypt 一键申请）。

配置完成后：

```bash
curl https://api.your-domain.com/ping
# 应返回 {"code":0,"msg":"pong",...}
```

**别忘了小程序端**：`miniprogram/utils/api.js` 里的 `BASE_URL` 改为 `https://api.your-domain.com/api`，并在微信公众平台 → 开发管理 → 服务器域名 → request 合法域名 中添加 `https://api.your-domain.com`。

---

## 附录：日常运维命令

```bash
# 查看容器运行状态
docker ps -a | grep love-hg-api

# 查看实时日志（Ctrl+C 退出）
docker logs -f love-hg-api

# 重启容器
docker restart love-hg-api

# 停止并删除容器
docker rm -f love-hg-api

# 更新代码后重新部署（完整流程）
cd /www/wwwroot/love-in-hg/backend
# ...上传/修改代码...
docker rm -f love-hg-api
docker rmi love-in-hg:latest
docker build -t love-in-hg:latest .
docker run -d \
  --name love-hg-api \
  --restart always \
  -p 5000:5000 \
  -e MYSQL_HOST=172.17.0.1 \
  -e MYSQL_PORT=3306 \
  -e MYSQL_USER=root \
  -e MYSQL_PASSWORD=你的数据库密码 \
  -e MYSQL_DB=love_hg \
  love-in-hg:latest

# 进入容器内部调试
docker exec -it love-hg-api bash

# 在容器里测试数据库连通性
docker exec -it love-hg-api python -c "
from config import Config
from models.database import db
print('DB URI:', Config.SQLALCHEMY_DATABASE_URI)
"
```

---

## 附录：常见问题排查

### 问题 1：`gunicorn: executable file not found in $PATH`

**原因**：用了多阶段构建 + `pip install --target=`，丢失了 gunicorn 可执行入口。

**解决**：用本方案第 3 步的单阶段 Dockerfile（v1.1），重新 build。

---

### 问题 2：容器启动了但接口报数据库错误

```bash
docker logs love-hg-api 2>&1 | grep -i error
```

常见报错与解决：

| 报错关键字 | 原因 | 解决 |
|---|---|---|
| `Can't connect to MySQL server on '127.0.0.1'` | MYSQL_HOST 填了 127.0.0.1 | 改成 `172.17.0.1` |
| `Access denied for user` | 用户名/密码错，或 MySQL 未授权容器网段 | 核对密码；执行第 7 步的 GRANT 语句 |
| `Host '172.17.0.x' is not allowed to connect` | MySQL 拒绝容器 IP | GRANT 授权，或宝塔里 MySQL root 改为"所有人" |
| `Unknown database 'love_hg'` | 库还没建 | 回到第 6 步先建库导表 |

**测试容器到宿主机 MySQL 连通性**：

```bash
# 进容器里 ping 宿主机
docker exec -it love-hg-api python -c "
import socket
s = socket.socket()
s.settimeout(3)
try:
    s.connect(('172.17.0.1', 3306))
    print('✅ 宿主机 3306 端口可达')
except Exception as e:
    print('❌ 连不上:', e)
"
```

---

### 问题 3：`docker build` 报 Dockerfile 不存在

```
ERROR: failed to solve: failed to read dockerfile: ... no such file or directory
```

**原因**：当前目录没有 Dockerfile。

**解决**：

```bash
ls -la   # 确认在 /www/wwwroot/love-in-hg/backend 目录且 Dockerfile 存在
pwd      # 查看当前目录
cd /www/wwwroot/love-in-hg/backend   # 不在就切过去
```

---

### 问题 4：`#1273 - Unknown collation: 'utf8mb4_0900_ai_ci'`

**原因**：MySQL < 8.0 不支持该排序规则。

**解决**：SQL 文件里全部替换 `utf8mb4_0900_ai_ci` → `utf8mb4_general_ci`（桌面的 love_hg.sql 已改好，共 25 处）。

```bash
# 服务器上批量替换的命令
sed -i 's/utf8mb4_0900_ai_ci/utf8mb4_general_ci/g' /www/wwwroot/love-in-hg/love_hg.sql
```

---

### 问题 5：端口被占用

```
Error response from daemon: driver failed programming external connectivity ... port is already allocated
```

**解决**：

```bash
# 查谁占了 5000
ss -tlnp | grep 5000

# 杀掉旧进程（如是旧的 python/宝塔 python 项目）
# 或换端口映射: -p 5001:5000
```

---

### 问题 6：curl 本机通，外网不通

依次检查：

1. 宝塔面板 → 安全 → 5000 端口是否放行
2. 云服务器控制台 → 安全组 → 5000 入站规则是否添加
3. 如果只想走域名+Nginx，就别放行 5000，直接配第 9 步反代

---

## 部署架构总览

```
微信小程序
    │
    │ HTTPS (https://api.your-domain.com)
    ▼
Nginx (宝塔, 80/443)
    │ 反向代理
    ▼
Docker 容器 love-hg-api (宿主机 5000 → 容器 5000)
    │ Gunicorn x 4 workers
    │ Flask app:create_app()
    ▼
宿主机 MySQL 5.7/8.0 (172.17.0.1:3306)
    │
    ▼
数据库 love_hg (users / notices / notice_views / membership_orders)
```
