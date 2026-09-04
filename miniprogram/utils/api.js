// utils/api.js
// Python 后端 REST API 调用封装

const BASE_URL = 'http://127.0.0.1:5000/api';  // 生产环境服务器地址
//const BASE_URL = 'https://aibao.love/api';  // 生产环境服务器地址
/**
 * 通用请求方法
 */
function request(path, options = {}) {
  const { method = 'GET', data = {}, header = {} } = options;
  const userId = wx.getStorageSync('userId') || '';

  return new Promise((resolve, reject) => {
    wx.request({
      url: `${BASE_URL}${path}`,
      method,
      data,
      header: {
        'Content-Type': 'application/json',
        'X-User-Id': userId,
        ...header
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          resolve(res.data || { code: res.statusCode, msg: '请求失败' });
        }
      },
      fail(err) {
        console.error('API Error:', path, err);
        reject(err);
      }
    });
  });
}

/**
 * GET 请求
 */
function get(path, params = {}) {
  const qs = Object.keys(params)
    .filter(k => params[k] !== undefined && params[k] !== null && params[k] !== '')
    .map(k => `${encodeURIComponent(k)}=${encodeURIComponent(params[k])}`)
    .join('&');
  const url = qs ? `${path}?${qs}` : path;
  return request(url, { method: 'GET' });
}

/**
 * POST 请求
 */
function post(path, data = {}) {
  return request(path, { method: 'POST', data });
}

/**
 * 手机号登录
 */
function login(phone) {
  return post('/auth/login', { phone });
}

/**
 * 发布启事
 */
function publishNotice(data) {
  return post('/notice/publish', data);
}

/**
 * 修改启事
 */
function updateNotice(noticeId, data) {
  return post(`/notice/update/${noticeId}`, data);
}

/**
 * 删除启事
 */
function deleteNotice(noticeId) {
  return post(`/notice/delete/${noticeId}`);
}

/**
 * 获取启事列表（随机分配 + 筛选）
 * filter: { gender, minHeight, maxHeight, minAge, maxAge, income, isPublicSector, occupation }
 */
function getNotices(filter = {}) {
  const userId = wx.getStorageSync('userId') || '';
  return get('/notice/list', { ...filter, userId });
}

/**
 * 获取我的启事
 */
function getMyNotices() {
  const userId = wx.getStorageSync('userId') || '';
  return get('/user/notices', { userId });
}

/**
 * 获取历史分配的启事（跨周期汇总）
 */
function getNoticeHistory() {
  const userId = wx.getStorageSync('userId') || '';
  return get('/notice/history', { userId });
}

/**
 * 按需获取启事完整手机号（列表/历史返回的是脱敏号）
 */
function viewNoticePhone(noticeId) {
  return post('/notice/viewPhone', { noticeId });
}

/**
 * 获取用户信息
 */
function getUserProfile() {
  const userId = wx.getStorageSync('userId') || '';
  return get('/user/profile', { userId });
}

/**
 * 购买会员（创建订单并统一下单获取支付参数）
 */
function purchaseMembership(type) {
  return post('/membership/purchase', { type });
}

/**
 * 查询订单支付状态
 */
function getOrderStatus(orderId, orderNo) {
  return get('/membership/order/status', { orderId, orderNo });
}

/**
 * 模拟支付成功（未配置商户号/开发测试使用）
 */
function mockPaySuccess(orderId, orderNo) {
  return post('/membership/mock-pay-success', { orderId, orderNo });
}

/**
 * 微信支付调起封装
 * @param {Object} paymentParams 后端返回的统一下单参数 (timeStamp, nonceStr, package, signType, paySign)
 */
function requestPayment(paymentParams) {
  return new Promise((resolve, reject) => {
    wx.requestPayment({
      timeStamp: paymentParams.timeStamp,
      nonceStr: paymentParams.nonceStr,
      package: paymentParams.package,
      signType: paymentParams.signType || 'RSA',
      paySign: paymentParams.paySign,
      success: (res) => resolve(res),
      fail: (err) => reject(err)
    });
  });
}

/**
 * 注销账号（删除用户及全部关联数据）
 */
function deleteAccount() {
  return post('/user/deleteAccount');
}

/**
 * 提取并导入文本信息（管理端使用）
 */
function extractAndImport(text) {
  return post('/admin/extractAndImport', { text });
}

module.exports = {
  BASE_URL,
  request,
  get,
  post,
  login,
  publishNotice,
  updateNotice,
  deleteNotice,
  getNotices,
  getMyNotices,
  getNoticeHistory,
  viewNoticePhone,
  getUserProfile,
  purchaseMembership,
  getOrderStatus,
  mockPaySuccess,
  requestPayment,
  deleteAccount,
  extractAndImport
};

