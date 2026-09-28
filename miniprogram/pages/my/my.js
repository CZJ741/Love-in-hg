// pages/my/my.js
const api = require('../../utils/api');

Page({
  data: {
    user: {},
    userInitial: '?',
    maskedUserPhone: '',
    membershipType: 'free',
    membershipName: '普通用户',
    membershipExpire: '',
    noticeCount: 0,
    monthlyAssigned: 0,
    remaining: 0,
    quotaLimit: 10,
    periodLabel: '本月配额',
    prices: { member: 0.01, vip: 0.02 },
    showLoginModal: false,
    loginPhone: '',
    authMode: 'login', // 'login' | 'register'
    regPhone: '',
    regCode: '',
    countdown: 0,
    verifying: false,
    // 注销弹窗相关
    showDeleteModal: false,
    deleteCode: '',
    deleteCountdown: 0,
    deleteSubmitting: false,
    // 平台检测
    isIOS: false
  },

  onLoad() {
    try {
      const sys = wx.getSystemInfoSync();
      const isIOS = (sys.platform === 'ios');
      this.setData({ isIOS });
    } catch (e) {
      console.warn('获取系统平台信息失败:', e);
    }
  },

  onShow() {
    this.loadUserProfile();
  },

  async loadUserProfile() {
    const userInfo = wx.getStorageSync('userInfo');
    if (!userInfo) {
      this.setData({
        user: {},
        userInitial: '?'
      });
      return;
    }

    try {
      const res = await api.getUserProfile();
      if (res.code === 0) {
        const { user, quota } = res.data;
        const remaining = quota.monthlyAssigned;

        const memberNames = { free: '普通用户', member: '会员', vip: '大会员' };
        const isDaily = quota.periodType === 'daily';

        let expireStr = user.membershipExpire || '';
        if (expireStr) {
          // 处理形如 '2026-10-16T12:30:00' 或 '2026-10-16 12:30:00'，只保留日期部分 YYYY-MM-DD
          expireStr = expireStr.split('T')[0].split(' ')[0];
        }

        let maskedPhone = '';
        if (user.phone && user.phone.length === 11) {
          maskedPhone = user.phone.slice(0, 3) + '****' + user.phone.slice(7);
        }

        const initialChar = user.name ? user.name[0] : (user.phone ? user.phone.slice(-2) : '?');

        this.setData({
          user,
          userInitial: initialChar,
          maskedUserPhone: maskedPhone,
          membershipType: quota.membershipType,
          membershipName: memberNames[quota.membershipType] || '普通用户',
          membershipExpire: expireStr,
          noticeCount: user.noticeCount || 0,
          monthlyAssigned: quota.monthlyAssigned,
          remaining: Math.max(0, remaining),
          quotaLimit: quota.monthlyLimit,
          periodLabel: isDaily ? '今日配额' : '本月配额'
        });
      }
    } catch (err) {
      console.error('加载用户信息失败:', err);
    }
  },

  // 显示手动登录弹窗
  onShowLoginModal() {
    this.setData({ showLoginModal: true, authMode: 'login' });
  },

  onHideLogin() {
    this.setData({ showLoginModal: false });
  },

  onSwitchAuthMode(e) {
    const mode = e.currentTarget.dataset.mode;
    if (mode && mode !== this.data.authMode) {
      this.setData({ authMode: mode });
    }
  },

  stopBubble() {},

  onPhoneInput(e) {
    this.setData({ loginPhone: e.detail.value });
  },

  onRegPhoneInput(e) {
    this.setData({ regPhone: e.detail.value });
  },

  onRegCodeInput(e) {
    this.setData({ regCode: e.detail.value });
  },

  // 发送短信验证码
  async onSendSmsCode() {
    if (this.data.countdown > 0) return;

    const phone = (this.data.regPhone || '').trim();
    if (!/^1[3-9]\d{9}$/.test(phone)) {
      wx.showToast({ title: '请输入正确的手机号', icon: 'none' });
      return;
    }

    wx.showLoading({ title: '发送中...', mask: true });
    try {
      const res = await api.sendSms(phone);
      wx.hideLoading();
      if (res.code === 0) {
        wx.showToast({ title: '验证码已发送', icon: 'success' });
        this.setData({ countdown: 60 });
        this.smsTimer = setInterval(() => {
          if (this.data.countdown <= 1) {
            clearInterval(this.smsTimer);
            this.setData({ countdown: 0 });
          } else {
            this.setData({ countdown: this.data.countdown - 1 });
          }
        }, 1000);
      } else {
        wx.showToast({ title: res.msg || '发送失败', icon: 'none' });
      }
    } catch (err) {
      wx.hideLoading();
      wx.showToast({ title: '网络异常，发送失败', icon: 'none' });
    }
  },

  // 新用户验证码核验并登录
  async onVerifyRegister() {
    const phone = (this.data.regPhone || '').trim();
    const code = (this.data.regCode || '').trim();

    if (!/^1[3-9]\d{9}$/.test(phone)) {
      wx.showToast({ title: '请输入正确的手机号', icon: 'none' });
      return;
    }
    if (!code || code.length < 4) {
      wx.showToast({ title: '请输入有效验证码', icon: 'none' });
      return;
    }

    this.setData({ verifying: true });
    wx.showLoading({ title: '验证中...', mask: true });

    try {
      let wxCode = '';
      try {
        const loginRes = await new Promise((resolve) => wx.login({ success: resolve, fail: () => resolve({}) }));
        wxCode = loginRes.code || '';
      } catch (e) {}

      const res = await api.verifyRegister(phone, code, wxCode);
      wx.hideLoading();

      if (res.code === 0 && res.data && res.data.user) {
        const u = res.data.user;
        wx.setStorageSync('userInfo', u);
        wx.setStorageSync('userId', String(u.id));
        this.setData({
          showLoginModal: false,
          regPhone: '',
          regCode: ''
        });
        if (this.smsTimer) {
          clearInterval(this.smsTimer);
          this.setData({ countdown: 0 });
        }
        this.loadUserProfile();
        wx.showToast({ title: '注册成功', icon: 'success' });
      } else {
        wx.showToast({ title: res.msg || '验证失败', icon: 'none' });
      }
    } catch (err) {
      wx.hideLoading();
      wx.showToast({ title: '验证失败，请重试', icon: 'none' });
    }
    this.setData({ verifying: false });
  },

  async onManualLogin() {
    const phone = this.data.loginPhone.trim();
    if (!/^1[3-9]\d{9}$/.test(phone)) {
      wx.showToast({ title: '请输入正确的手机号', icon: 'none' });
      return;
    }

    wx.showLoading({ title: '登录中...', mask: true });
    try {
      let wxCode = '';
      try {
        const loginRes = await new Promise((resolve) => wx.login({ success: resolve, fail: () => resolve({}) }));
        wxCode = loginRes.code || '';
      } catch (e) {}

      const res = await api.login(phone, wxCode);
      wx.hideLoading();
      if (res.code === 0) {
        if (res.data.isNewUser) {
          wx.showModal({
            title: '提示',
            content: '该手机号未预留档案，请点击“注册”进行手机验证注册',
            showCancel: false
          });
        } else {
          const u = res.data.user;
          wx.setStorageSync('userInfo', u);
          wx.setStorageSync('userId', String(u.id));
          this.setData({ showLoginModal: false });
          this.loadUserProfile();
          wx.showToast({ title: '登录成功', icon: 'success' });
        }
      } else {
        wx.showToast({ title: res.msg, icon: 'none' });
      }
    } catch (err) {
      wx.hideLoading();
      wx.showToast({ title: '登录失败', icon: 'none' });
    }
  },

  afterLogin(data) {
    if (data.isNewUser) {
      wx.showModal({
        title: '提示',
        content: '您还未注册，请先发布启事',
        showCancel: false,
        success: () => wx.switchTab({ url: '/pages/publish/publish' })
      });
    } else {
      wx.setStorageSync('userInfo', data.user);
      wx.setStorageSync('userId', String(data.user.id));
      this.loadUserProfile();
    }
  },

  // iOS 复制外部专属开通链接
  onCopyPayLink() {
    const phone = (this.data.user && this.data.user.phone) || '';
    const origin = api.BASE_URL.replace(/\/api\/?$/, '');
    const payUrl = `${origin}/pay${phone ? `?phone=${phone}` : ''}`;

    wx.setClipboardData({
      data: payUrl,
      success: () => {
        wx.showModal({
          title: '专属开通链接已复制',
          content: '请在手机自带浏览器（Safari/Chrome）中粘贴打开链接完成支付。支付成功后，同一手机号权益立即全端生效！',
          confirmText: '我知道了',
          showCancel: false
        });
      }
    });
  },

  async onBuyMembership(e) {
    if (this.data.isIOS) {
      this.onCopyPayLink();
      return;
    }

    const type = e.currentTarget.dataset.type;
    if (type === this.data.membershipType) {
      wx.showToast({ title: '您已开通该级别会员', icon: 'none' });
      return;
    }

    const userId = wx.getStorageSync('userId');
    if (!userId) {
      wx.showModal({
        title: '提示',
        content: '开通会员前请先登录',
        confirmText: '去登录',
        success: (res) => {
          if (res.confirm) {
            this.setData({ showLoginModal: true });
          }
        }
      });
      return;
    }

    const price = this.data.prices[type];
    const name = type === 'vip' ? '大会员' : '会员';
    const quotaDesc = type === 'vip' ? '每天30条' : '每月30条';

    wx.showModal({
      title: `开通${name}`,
      content: `确认支付 ${price} 元开通${name}服务（有效期1年，享有配额：${quotaDesc}）？`,
      success: async (modalRes) => {
        if (!modalRes.confirm) return;

        wx.showLoading({ title: '正在发起支付...', mask: true });

        try {
          // 获取最新的微信登录 code，以便后端获取或绑定 openid
          let wxCode = '';
          try {
            const loginRes = await new Promise((resolve, reject) => {
              wx.login({
                success: resolve,
                fail: reject
              });
            });
            wxCode = loginRes.code || '';
          } catch (codeErr) {
            console.warn('获取 wx.login code 失败:', codeErr);
          }

          // 1. 创建订单并统一下单
          const res = await api.purchaseMembership(type, { code: wxCode });
          wx.hideLoading();

          if (res.code !== 0 || !res.data) {
            wx.showToast({ title: res.msg || '订单创建失败', icon: 'none' });
            return;
          }

          const orderData = res.data;
          const { orderId, orderNo, payment, isMock } = orderData;

          // 2. 判断是否为开发环境模拟支付测试模式
          if (isMock) {
            wx.showModal({
              title: '支付测试环境',
              content: `已生成订单（单号: ${orderNo}），当前为测试支付模式，是否模拟支付完成？`,
              confirmText: '模拟支付',
              cancelText: '取消',
              success: async (mockModal) => {
                if (mockModal.confirm) {
                  wx.showLoading({ title: '正在开通权益...', mask: true });
                  try {
                    const mockRes = await api.mockPaySuccess(orderId, orderNo);
                    wx.hideLoading();
                    if (mockRes.code === 0) {
                      wx.showToast({ title: '开通成功！', icon: 'success' });
                      this.loadUserProfile();
                    } else {
                      wx.showToast({ title: mockRes.msg || '开通失败', icon: 'none' });
                    }
                  } catch (mockErr) {
                    wx.hideLoading();
                    wx.showToast({ title: '请求失败，请稍后重试', icon: 'none' });
                  }
                }
              }
            });
            return;
          }

          // 3. 正式环境：调起微信原生支付控件
          try {
            await api.requestPayment(payment);

            // 支付完成后主动查询一次状态并刷新用户资料
            wx.showLoading({ title: '正在确认支付结果...', mask: true });
            try {
              await api.getOrderStatus(orderId, orderNo);
            } catch (statusErr) {
              console.warn('查询订单状态失败:', statusErr);
            }
            wx.hideLoading();

            wx.showToast({ title: '支付成功', icon: 'success' });
            setTimeout(() => {
              this.loadUserProfile();
            }, 800);
          } catch (payErr) {
            // 用户取消支付或支付失败
            if (payErr.errMsg && payErr.errMsg.includes('cancel')) {
              wx.showToast({ title: '已取消支付', icon: 'none' });
            } else {
              wx.showModal({
                title: '支付未完成',
                content: payErr.errMsg || '支付过程中遇到问题，您可稍后在订单中重试',
                showCancel: false
              });
            }
          }
        } catch (err) {
          wx.hideLoading();
          wx.showToast({ title: '网络异常，请重试', icon: 'none' });
        }
      }
    });
  },


  onLogout() {
    wx.showModal({
      title: '退出登录',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          // 清除本地全部用户数据（兑现隐私政策"退出登录后清除"承诺）
          wx.removeStorageSync('userInfo');
          wx.removeStorageSync('userId');
          wx.removeStorageSync('tempPhone');
          wx.removeStorageSync('editNoticeData');
          this.setData({
            user: {},
            userInitial: '?',
            maskedUserPhone: '',
            membershipType: 'free'
          });
          wx.showToast({ title: '已退出', icon: 'none' });
        }
      }
    });
  },

  // 联系客服（拨打热线）
  onContactService() {
    wx.makePhoneCall({
      phoneNumber: '13581267798',
      fail: () => {
        wx.showToast({ title: '拨打失败，请稍后重试', icon: 'none' });
      }
    });
  },

  // 打开隐私政策页面
  onOpenPrivacy() {
    wx.navigateTo({ url: '/pages/privacy/privacy' });
  },

  // 点击注销账号，直接打开安全验证弹窗
  onDeleteAccount() {
    const user = this.data.user || {};
    if (!user.phone) {
      wx.showToast({ title: '未获取到手机号', icon: 'none' });
      return;
    }
    this.setData({
      showDeleteModal: true,
      deleteCode: ''
    });
  },

  onHideDeleteModal() {
    this.setData({
      showDeleteModal: false,
      deleteCode: ''
    });
  },

  onDeleteCodeInput(e) {
    this.setData({ deleteCode: e.detail.value });
  },

  // 发送注销短信验证码
  async onSendDeleteSmsCode() {
    if (this.data.deleteCountdown > 0) return;

    const phone = this.data.user && this.data.user.phone;
    if (!phone) {
      wx.showToast({ title: '用户手机号异常', icon: 'none' });
      return;
    }

    wx.showLoading({ title: '发送中...', mask: true });
    try {
      const res = await api.sendSms(phone);
      wx.hideLoading();
      if (res.code === 0) {
        wx.showToast({ title: '验证码已发送', icon: 'success' });
        this.setData({ deleteCountdown: 60 });
        if (this.deleteSmsTimer) clearInterval(this.deleteSmsTimer);
        this.deleteSmsTimer = setInterval(() => {
          if (this.data.deleteCountdown <= 1) {
            clearInterval(this.deleteSmsTimer);
            this.setData({ deleteCountdown: 0 });
          } else {
            this.setData({ deleteCountdown: this.data.deleteCountdown - 1 });
          }
        }, 1000);
      } else {
        wx.showToast({ title: res.msg || '发送失败', icon: 'none' });
      }
    } catch (err) {
      wx.hideLoading();
      wx.showToast({ title: '网络请求失败，请稍后重试', icon: 'none' });
    }
  },

  // 确认注销
  async onConfirmDeleteAccount() {
    const code = (this.data.deleteCode || '').trim();
    if (!code || code.length !== 6) {
      wx.showToast({ title: '请输入6位有效验证码', icon: 'none' });
      return;
    }

    this.setData({ deleteSubmitting: true });
    try {
      const result = await api.deleteAccount(code);
      this.setData({ deleteSubmitting: false });
      if (result.code === 0) {
        if (this.deleteSmsTimer) clearInterval(this.deleteSmsTimer);
        // 清除本地全部用户数据
        wx.removeStorageSync('userInfo');
        wx.removeStorageSync('userId');
        wx.removeStorageSync('tempPhone');
        wx.removeStorageSync('editNoticeData');
        this.setData({
          showDeleteModal: false,
          deleteCode: '',
          deleteCountdown: 0,
          user: {},
          userInitial: '?',
          maskedUserPhone: '',
          membershipType: 'free',
          noticeCount: 0,
          monthlyAssigned: 0,
          remaining: 0,
          membershipExpire: ''
        });
        wx.showToast({ title: '账号已注销', icon: 'success', duration: 2500 });
      } else {
        wx.showToast({ title: result.msg || '注销失败', icon: 'none' });
      }
    } catch (err) {
      this.setData({ deleteSubmitting: false });
      wx.showToast({ title: '注销失败，请重试', icon: 'none' });
    }
  },

  onUnload() {
    if (this.smsTimer) {
      clearInterval(this.smsTimer);
    }
    if (this.deleteSmsTimer) {
      clearInterval(this.deleteSmsTimer);
    }
  }
});
