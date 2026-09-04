// pages/my/my.js
const api = require('../../utils/api');

Page({
  data: {
    user: {},
    userInitial: '?',
    membershipType: 'free',
    membershipName: '普通用户',
    membershipExpire: '',
    noticeCount: 0,
    monthlyAssigned: 0,
    remaining: 0,
    quotaLimit: 10,
    periodLabel: '本月配额',
    prices: { member: 99, vip: 999 },
    showLoginModal: false,
    loginPhone: ''
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

        this.setData({
          user,
          userInitial: (user.name || '?')[0],
          membershipType: quota.membershipType,
          membershipName: memberNames[quota.membershipType] || '普通用户',
          membershipExpire: user.membershipExpire || '',
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
    this.setData({ showLoginModal: true });
  },

  onHideLogin() {
    this.setData({ showLoginModal: false });
  },

  onPhoneInput(e) {
    this.setData({ loginPhone: e.detail.value });
  },

  async onManualLogin() {
    const phone = this.data.loginPhone.trim();
    if (!/^1[3-9]\d{9}$/.test(phone)) {
      wx.showToast({ title: '请输入正确的手机号', icon: 'none' });
      return;
    }

    try {
      const res = await api.login(phone);
      if (res.code === 0) {
        if (res.data.isNewUser) {
          wx.setStorageSync('tempPhone', phone);
          wx.showModal({
            title: '提示',
            content: '您还未注册，请先发布启事',
            showCancel: false,
            success: () => wx.switchTab({ url: '/pages/publish/publish' })
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

  async onBuyMembership(e) {
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
      content: `确认支付 ${price} 元开通${name}服务？（享有配额：${quotaDesc}）`,
      success: async (modalRes) => {
        if (!modalRes.confirm) return;

        wx.showLoading({ title: '正在发起支付...', mask: true });

        try {
          // 1. 创建订单并统一下单
          const res = await api.purchaseMembership(type);
          wx.hideLoading();

          if (res.code !== 0 || !res.data) {
            wx.showToast({ title: res.msg || '订单创建失败', icon: 'none' });
            return;
          }

          const orderData = res.data;
          const { orderId, orderNo, payment, isMock } = orderData;

          // 2. 判断是否为未配置商户号的模拟支付测试模式
          if (isMock) {
            wx.showModal({
              title: '支付测试环境',
              content: `已生成订单（单号: ${orderNo}），当前未绑定微信商户号，是否模拟支付完成？`,
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

            // 支付成功提示并主动刷新用户配置
            wx.showToast({ title: '支付成功', icon: 'success' });
            setTimeout(() => {
              this.loadUserProfile();
            }, 1000);
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

  // 注销账号（双重确认）
  onDeleteAccount() {
    wx.showModal({
      title: '注销账号',
      content: '注销后，您的全部启事和个人信息将被永久删除，且无法恢复。确定继续吗？',
      confirmText: '继续注销',
      confirmColor: '#e74c3c',
      success: (res) => {
        if (res.confirm) {
          this.confirmDeleteAccount();
        }
      }
    });
  },

  async confirmDeleteAccount() {
    // 需要用户输入手机号验证身份（防止误操作）
    wx.showModal({
      title: '二次确认',
      content: '为确认是本人操作，请点击"我已确认"完成注销。此操作不可撤销。',
      confirmText: '我已确认',
      confirmColor: '#e74c3c',
      success: async (res) => {
        if (!res.confirm) return;
        try {
          wx.showLoading({ title: '注销中...' });
          const result = await api.deleteAccount();
          wx.hideLoading();
          if (result.code === 0) {
            // 清除本地全部用户数据
            wx.removeStorageSync('userInfo');
            wx.removeStorageSync('userId');
            wx.removeStorageSync('tempPhone');
            wx.removeStorageSync('editNoticeData');
            this.setData({
              user: {},
              userInitial: '?',
              membershipType: 'free',
              noticeCount: 0,
              monthlyAssigned: 0,
              remaining: 0,
              membershipExpire: ''
            });
            wx.showToast({ title: '注销成功', icon: 'success' });
          } else {
            wx.showToast({ title: result.msg || '注销失败', icon: 'none' });
          }
        } catch (err) {
          wx.hideLoading();
          wx.showToast({ title: '注销失败，请重试', icon: 'none' });
        }
      }
    });
  }
});
