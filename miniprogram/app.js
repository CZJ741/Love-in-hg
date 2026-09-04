// app.js
App({
  onLaunch() {
    // 检查登录状态
    this.checkLoginStatus();
  },

  checkLoginStatus() {
    const userInfo = wx.getStorageSync('userInfo');
    const userId = wx.getStorageSync('userId');
    if (userInfo && userId) {
      this.globalData.userInfo = userInfo;
      this.globalData.isLoggedIn = true;
      this.globalData.userId = userId;
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
