# Love-in-hg 生产环境接口测试用例

> Base URL: `https://aibao.love/api`
> 所有请求需开启 HTTPS（生产环境强制）
> 认证方式：登录后获取 userId，通过 `X-User-Id` 请求头传递

---

## 测试账号准备

| 账号 | 手机号 | 用途 |
|------|--------|------|
| 种子用户A | `13800138001` | free 会员，首次登录测试 |
| 种子用户B | `13800138002` | free 会员，配额测试 |
| 种子用户C | `13800138003` | 发布测试用（已有启事） |
| 新手机号 | `19900001111` | 不存在的手机号 |
| 管理密码 | `admin123` | initData 接口密码 |

---

## 1. 健康检查

### TC1.1 根路径可访问
```
GET https://aibao.love/
```
**预期**: 200, `{"code":0,"msg":"Love-in-hg backend is running",...}`

### TC1.2 ping 接口可访问
```
GET https://aibao.love/ping
```
**预期**: 200, `{"code":0,"msg":"pong"}`

### TC1.3 CORS 头存在
```
OPTIONS https://aibao.love/ping
Access-Control-Request-Method: GET
Access-Control-Request-Headers: Content-Type
```
**预期**: 204, 响应头包含 `Access-Control-Allow-Origin: *`、`Access-Control-Allow-Methods`

---

## 2. 认证模块

### TC2.1 正常登录（种子手机号）
```
POST /auth/login
Content-Type: application/json

{"phone":"13800138001"}
```
**预期**: 200, `code=0`, 返回 user 对象（含 id、phone、name、membershipType=free）

### TC2.2 不存在的手机号登录
```
POST /auth/login
Content-Type: application/json

{"phone":"19900001111"}
```
**预期**: 200, `code=0`, `isNewUser=true`, `user=null`, `msg="该手机号未发布过启事，请先发布"`

### TC2.3 手机号格式错误（短号）
```
POST /auth/login
{"phone":"1380013800"}
```
**预期**: 400, `msg="请输入正确的手机号码"`

### TC2.4 手机号格式错误（非1开头）
```
POST /auth/login
{"phone":"23800138001"}
```
**预期**: 400, `msg="请输入正确的手机号码"`

### TC2.5 空手机号
```
POST /auth/login
{"phone":""}
```
**预期**: 400, `msg="请输入正确的手机号码"`

### TC2.6 非 POST 方法
```
GET /auth/login
```
**预期**: 405 Method Not Allowed

---

## 3. 启事模块

### TC3.1 首次访问分配列表（free 用户）
```
GET /notice/list?userId=1
Header: X-User-Id: 1
```
**预期**: 200, `notices` 数组长度 ≤ 10, `membershipType=free`, `periodType=monthly`, 手机号脱敏显示（138****0001）

### TC3.2 本月重复访问（返回相同列表）
连续请求 3 次 `/notice/list?userId=1`
**预期**: 3 次返回的 `notices` ID 集合完全一致

### TC3.3 带筛选条件
```
GET /notice/list?userId=1&gender=女&minHeight=160&maxHeight=170
```
**预期**: 返回符合筛选条件的启事（分配后的列表再过滤）

### TC3.4 登录态缺失
```
GET /notice/list
```
**预期**: 401, `msg="请先登录"`

### TC3.5 userId 无效
```
GET /notice/list?userId=99999
```
**预期**: 401, `msg="用户不存在"`

### TC3.6 发布启事（新手机号）
```
POST /notice/publish
Content-Type: application/json

{
  "phone":"19900002222",
  "name":"测试用户",
  "nickname":"小测",
  "gender":"男",
  "birthday":"1992-06-01",
  "occupation":"工程师",
  "income":"20-30万",
  "isPublicSector":false,
  "height":175,
  "weight":68,
  "remark":"性格好"
}
```
**预期**: 200, `noticeId` 和 `userId` 返回

### TC3.7 发布启事（手机号已存在，多条）
对同一手机号 `19900002222` 再次调用 `/notice/publish`
**预期**: 200, 创建新的 notice（一个手机号多条）

### TC3.8 发布参数校验 - 缺少必填
```
POST /notice/publish
{"phone":"13800138001"}
```
**预期**: 400, `msg="请输入姓名"` 或其他校验错误

### TC3.9 修改启事
```
POST /notice/update/1
{
  "name":"修改后名字",
  "gender":"男",
  "birthday":"1990-03-15"
}
```
**预期**: 200, `noticeId` 返回

### TC3.10 修改不存在的启事
```
POST /notice/update/99999
```
**预期**: 404, `msg="启事不存在"`

### TC3.11 删除启事
```
POST /notice/delete/1
Header: X-User-Id: <启事所有者userId>
```
**预期**: 200, `noticeId` 返回

### TC3.12 删除他人启事
```
POST /notice/delete/1
Header: X-User-Id: <非所有者userId>
```
**预期**: 403, `msg="无权删除他人启事"`

### TC3.13 历史查看列表
```
GET /notice/history?userId=1
```
**预期**: 200, 返回所有历史分配过的启事（跨周期汇总），手机号脱敏

### TC3.14 查看完整手机号
```
POST /notice/viewPhone
Header: X-User-Id: 1
{"noticeId":1}
```
**预期**: 200, 返回完整手机号（非脱敏）

### TC3.15 viewPhone 未登录
```
POST /notice/viewPhone
{"noticeId":1}
```
**预期**: 401

---

## 4. 用户模块

### TC4.1 获取用户信息
```
GET /user/profile?userId=1
```
**预期**: 200, 返回 user 对象 + quota 对象
```json
{
  "user": {
    "id": 1, "phone": "13800138001", "name": "...",
    "membershipType": "free", "noticeCount": 2,
    ...
  },
  "quota": {
    "membershipType": "free",
    "periodType": "monthly",
    "monthlyLimit": 10,
    "monthlyAssigned": 10,
    "remaining": 10,
    "limitReached": false
  }
}
```

### TC4.2 我的启事
```
GET /user/notices?userId=1
```
**预期**: 200, `notices` 数组，包含该用户发布的所有启事

### TC4.3 用户不存在
```
GET /user/profile?userId=99999
```
**预期**: 401, `msg="用户不存在"`

### TC4.4 通过手机号获取
```
GET /user/profile?phone=13800138001
```
**预期**: 200, 返回对应用户

---

## 5. 会员模块

### TC5.1 创建会员订单（member）
```
POST /membership/purchase
Header: X-User-Id: 1
{"type":"member"}
```
**预期**: 200, `orderId`、`amount:99`、`typeLabel:"会员"`

### TC5.2 创建会员订单（vip）
```
POST /membership/purchase
Header: X-User-Id: 1
{"type":"vip"}
```
**预期**: 200, `amount:999`, `typeLabel:"大会员"`

### TC5.3 无效会员类型
```
POST /membership/purchase
Header: X-User-Id: 1
{"type":"gold"}
```
**预期**: 400, `msg="无效的会员类型"`

### TC5.4 未登录购买
```
POST /membership/purchase
{"type":"member"}
```
**预期**: 401

---

## 6. 管理模块

### TC6.1 批量导入种子数据
```
POST /admin/initData
{"password":"admin123"}
```
**预期**: 200, `successCount=100, skipCount=0, errorCount=0`
（重复执行时 skipCount 会变成 100，因为已存在）

### TC6.2 密码错误
```
POST /admin/initData
{"password":"wrong"}
```
**预期**: 403, `msg="无权限"`

### TC6.3 文本提取导入
```
POST /admin/extractAndImport
{"text":"{姓名：王五，性别：女，出生年月：1993-08-20，身高：162，职业：医生，手机号：13912345678}"}
```
**预期**: 200, 返回 `extracted` 对象和 `id`

### TC6.4 提取已存在手机号
```
POST /admin/extractAndImport
{"text":"{手机号：13800138001，姓名：重复}"}
```
**预期**: 409, `msg="手机号 13800138001 已存在"`

---

## 7. 配额/周期逻辑

### TC7.1 free 用户配额
登录 free 用户后调用 `/user/profile`
**预期**: `quota.membershipType=free`, `monthlyLimit=10`, `periodType=monthly`

### TC7.2 本月分配后反复查看不消耗配额
连续请求 `/notice/list?userId=1` 5 次
每次再调 `/user/profile?userId=1`，观察 `monthlyAssigned` 不变
**预期**: `monthlyAssigned` 始终为 10（首次分配后不再变化）

### TC7.3 不同用户分配不同启事
用 `userId=1` 和 `userId=2` 分别调 `/notice/list`
**预期**: 两个用户的分配列表不完全相同（随机分配）

### TC7.4 跨周期不重复分配（逻辑验证）
系统设计：下月 1 号新周期分配时排除所有历史已分配过的
**验证方式**: 连续调用同一用户 `/notice/list`，确认本月不变；下月换账号测

---

## 8. 边界 & 异常

### TC8.1 极长手机号
```
POST /auth/login
{"phone":"13800138001111111111"}
```
**预期**: 400 或 数据库层报错但不崩溃

### TC8.2 SQL 注入尝试
```
POST /auth/login
{"phone":"' OR '1'='1"}
```
**预期**: 400（格式校验拦截），绝不能返回数据

### TC8.3 超量发布（同手机号 50 条）
循环调用 `/notice/publish` 50 次
**预期**: 200 全部成功，`/user/notices` 返回 50 条

### TC8.4 大数据量筛选
```
GET /notice/list?userId=1&income=10万以下&occupation=IT
```
**预期**: 200，可能返回空数组（筛选后无结果），但不报错

### TC8.5 Content-Type 缺失
```
POST /auth/login
phone=13800138001
```
**预期**: 400 或 Flask 默认错误，不应 500

### TC8.6 空 Body
```
POST /auth/login
{}
```
**预期**: 400, `msg="请输入正确的手机号码"`

### TC8.7 注销账号完整流程
1. 登录获取 userId
2. `POST /user/deleteAccount` 带上 X-User-Id
3. 再次请求 `/user/profile`
**预期**: 步骤2 → 200 `deletedUserId`；步骤3 → 401 用户不存在

---

## 9. 性能测试（生产环境）

### TC9.1 登录响应时间
```
POST /auth/login {"phone":"13800138001"}
```
**预期**: < 500ms

### TC9.2 分配列表响应时间
```
GET /notice/list?userId=1
```
**预期**: < 1s（首次分配涉及随机查询，后续纯查询应更快）

### TC9.3 并发登录
10 个并发 `/auth/login` 请求
**预期**: 全部成功，无数据库锁等待

### TC9.4 连续分配后查询
同一用户连续 100 次请求 `/notice/list`
**预期**: 始终返回 200，返回列表不变，无性能劣化

---

## 10. HTTPS/安全

### TC10.1 HTTP 强制跳转 HTTPS
```
GET http://aibao.love/ping
```
**预期**: 301/302 跳转到 HTTPS，或返回 403（取决于 Nginx 配置）

### TC10.2 TLS 证书有效
```
openssl s_client -connect aibao.love:443 -servername aibao.love
```
**预期**: 证书链完整，无警告

### TC10.3 OPTIONS 预检请求
```
OPTIONS https://aibao.love/api/auth/login
Origin: https://servicewechat.com
Access-Control-Request-Method: POST
Access-Control-Request-Headers: content-type,x-user-id
```
**预期**: 204，响应头包含正确的 CORS 字段

### TC10.4 HSTS 头存在
```
curl -I https://aibao.love/ping
```
**预期**: 响应头包含 `Strict-Transport-Security`

---

## 测试执行建议

1. **先跑 TC1.x**（健康检查），确认生产环境可达
2. **跑 TC2.1**（正常登录），拿到 userId 用于后续测试
3. **跑 TC6.1**（initData），确保有种子数据
4. **顺序跑 TC3 → TC5 → TC7**，覆盖核心业务流
5. **最后跑 TC8、TC9、TC10**，覆盖边界和安全

每跑完一个用例，**清理数据**（必要时调用 `/user/deleteAccount`）。
