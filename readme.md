# 相亲角 - 后端服务

## 环境准备

### 1. 安装 MySQL
确保 MySQL 5.7+ 已安装并运行。

### 2. 创建数据库
mysql -u root -p < backend/sql/schema.sql

### 3. 安装 Python 依赖
cd backend
pip install -r requirements.txt

### 4. 配置环境变量
cp .env.example .env
# 编辑 .env 填入实际的 MySQL 连接信息

### 5. 启动服务
python app.py

默认监听 http://0.0.0.0:5000

### 6. 导入种子数据（100条启事）
curl -X POST http://localhost:5000/api/admin/initData \
  -H "Content-Type: application/json" \
  -d '{"password": "admin123"}'

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/login | 手机号登录 |
| POST | /api/notice/publish | 发布启事 |
| GET  | /api/notice/list | 启事列表（随机+筛选+配额） |
| GET  | /api/user/profile | 用户信息+配额 |
| GET  | /api/user/notices | 我的启事 |
| POST | /api/membership/purchase | 购买会员（创建订单与统一下单） |
| GET  | /api/membership/order/status | 查询订单支付状态 |
| POST | /api/membership/mock-pay-success | 模拟支付成功（未填商户号时调试测试） |
| POST | /api/membership/notify | 微信支付异步回调通知（预留） |
| POST | /api/admin/extractAndImport | 文本提取导入 |
| POST | /api/admin/initData | 种子数据导入 |

## 前端配置

编辑 miniprogram/utils/api.js 中的 BASE_URL 为你的服务器地址。
