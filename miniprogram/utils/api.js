// utils/api.js
// Python 后端 REST API 调用封装

const BASE_URL = 'http://127.0.0.1:5000/api';  // 生产环境服务器地址
// const BASE_URL = 'https://aibao.love/api';  // 本地开发调试地址
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
function purchaseMembership(type, extra = {}) {
  return post('/membership/purchase', { type, ...extra });
}

/**
 * 微信静默登录获取 openid
 */
function wxLogin(code) {
  const userId = wx.getStorageSync('userId') || '';
  return post('/auth/wx-login', { code, userId });
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

/**
 * 上传单张图片
 * @param {string} filePath 本地临时文件路径
 * @returns {Promise<string>} 返回图片访问URL
 */
function uploadImage(filePath) {
  const userId = wx.getStorageSync('userId') || '';
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${BASE_URL}/notice/upload`,
      filePath,
      name: 'file',
      header: {
        'X-User-Id': userId
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try {
            const data = JSON.parse(res.data);
            if (data.code === 0 && data.data && data.data.url) {
              // 若返回的是相对路径，拼接 BASE_URL 前缀（去掉 /api）
              let url = data.data.url;
              if (url.startsWith('/')) {
                const origin = BASE_URL.replace(/\/api\/?$/, '');
                url = `${origin}${url}`;
              }
              resolve(url);
            } else {
              reject(new Error(data.msg || '上传失败'));
            }
          } catch (e) {
            reject(new Error('解析上传结果失败'));
          }
        } else {
          reject(new Error(`上传失败(${res.statusCode})`));
        }
      },
      fail(err) {
        reject(err);
      }
    });
  });
}

/**
 * 批量上传多张图片
 * @param {string[]} filePaths
 * @returns {Promise<string[]>}
 */
async function uploadImages(filePaths) {
  const urls = [];
  for (const path of filePaths) {
    // 如果已经是网络图片或已有URL则不需要重新上传
    if (path.startsWith('http://') || path.startsWith('https://')) {
      urls.push(path);
    } else {
      const url = await uploadImage(path);
      urls.push(url);
    }
  }
  return urls;
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
  wxLogin,
  purchaseMembership,
  getOrderStatus,
  mockPaySuccess,
  requestPayment,
  deleteAccount,
  extractAndImport,
  uploadImage,
  uploadImages
};


