// app.js
const api = require('./utils/api');

App({
  onLaunch() {
    // 检查并静默恢复登录状态
    this.checkLoginStatus();
  },

  async checkLoginStatus() {
    const userInfo = wx.getStorageSync('userInfo');
    const userId = wx.getStorageSync('userId');
    if (userInfo && userId) {
      this.globalData.userInfo = userInfo;
      this.globalData.isLoggedIn = true;
      this.globalData.userId = userId;
      return;
    }

    // 若本地无缓存，通过微信 wx.login 进行静默自动登录恢复
    try {
      const loginRes = await new Promise((resolve) => wx.login({ success: resolve, fail: () => resolve({}) }));
      if (loginRes.code) {
        const res = await api.wxLogin(loginRes.code);
        if (res.code === 0 && res.data && res.data.user) {
          const u = res.data.user;
          wx.setStorageSync('userInfo', u);
          wx.setStorageSync('userId', String(u.id));
          this.globalData.userInfo = u;
          this.globalData.isLoggedIn = true;
          this.globalData.userId = String(u.id);
        }
      }
    } catch (e) {
      console.warn('静默自动登录检查跳过:', e);
    }
  },

  globalData: {
    userInfo: null,
    userId: null,
    isLoggedIn: false,
    membershipTypes: {
      free: { name: '普通用户', monthlyLimit: 10 },
      member: { name: '会员', monthlyLimit: 30 },
      vip: { name: '大会员', monthlyLimit: 999 }
    },
    membershipPrices: {
      member: 99,
      vip: 999
    }
  }
});
