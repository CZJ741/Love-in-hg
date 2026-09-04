// pages/notice/notice.js
const api = require('../../utils/api');

Page({
  data: {
    isLoggedIn: false,
    loginPhone: '',
    loggingIn: false,

    // 配额
    remaining: 0,
    quotaLabel: '',
    membershipType: 'free',

    // 筛选
    filter: {},

    // Tab
    activeTab: 'assigned',

    // 数据
    assignedNotices: [],
    myNotices: [],
    historyNotices: [],

    // 瀑布流分列
    assignedLeft: [],
    assignedRight: [],
    myLeft: [],
    myRight: [],
    historyLeft: [],
    historyRight: [],

    // 加载状态
    loading: false,
    loadingMy: false,
    loadingHistory: false
  },

  onLoad() {
    const userInfo = wx.getStorageSync('userInfo');
    if (userInfo) {
      this.setData({ isLoggedIn: true });
      this.initData();
    }
  },

  onShow() {
    if (this.data.isLoggedIn && this.data.activeTab === 'mine') {
      this.loadMyNotices();
    } else if (this.data.isLoggedIn && this.data.activeTab === 'history') {
      this.loadHistoryNotices();
    }
  },

  // 初始化
  async initData() {
    await this.loadQuota();
    await this.loadAssignedNotices();
  },

  // 加载配额
  async loadQuota() {
    try {
      const res = await api.getUserProfile();
      if (res.code === 0) {
        const { quota } = res.data;
        let remaining = quota.monthlyAssigned;
        const labels = { free: '普通用户·本月', member: '会员·本月', vip: '大会员·今日' };
        let quotaLabel = labels[quota.membershipType] || '普通用户·本月';
        this.setData({
          remaining: Math.max(0, remaining),
          quotaLabel,
          membershipType: quota.membershipType
        });
      }
    } catch (err) {
      console.error('加载配额失败:', err);
    }
  },

  // 加载随机分配的启事
  async loadAssignedNotices() {
    this.setData({ loading: true });
    try {
      const res = await api.getNotices(this.data.filter);
      if (res.code === 0) {
        const { notices, remaining } = res.data;
        const list = notices || [];
        const { left, right } = this.splitColumns(list);
        this.setData({
          assignedNotices: list,
          assignedLeft: left,
          assignedRight: right,
          remaining: remaining || 0
        });
      }
    } catch (err) {
      console.error('加载启事失败:', err);
    }
    this.setData({ loading: false });
  },

  // 加载我的启事
  async loadMyNotices() {
    this.setData({ loadingMy: true });
    try {
      const res = await api.getMyNotices();
      if (res.code === 0) {
        const list = res.data.notices || [];
        const { left, right } = this.splitColumns(list);
        this.setData({
          myNotices: list,
          myLeft: left,
          myRight: right
        });
      }
    } catch (err) {
      console.error('加载我的启事失败:', err);
    }
    this.setData({ loadingMy: false });
  },

  // 加载历史分配的启事
  async loadHistoryNotices() {
    this.setData({ loadingHistory: true });
    try {
      const res = await api.getNoticeHistory();
      if (res.code === 0) {
        const list = res.data.notices || [];
        const { left, right } = this.splitColumns(list);
        this.setData({
          historyNotices: list,
          historyLeft: left,
          historyRight: right
        });
      }
    } catch (err) {
      console.error('加载历史启事失败:', err);
    }
    this.setData({ loadingHistory: false });
  },

  // 估算卡片高度，用于瀑布流分列（单位 rpx，近似即可）
  estimateCardHeight(notice) {
    let h = 84; // 头部：姓名/性别/年龄/身高
    if (notice.occupation) h += 46;
    if (notice.isPublicSector) h += 46;
    if (notice.income) h += 46;
    if (notice.birthday) h += 46;
    if (notice.weight) h += 46;
    if (notice.remark) {
      const lines = Math.ceil((notice.remark.length || 0) / 16);
      h += 30 + lines * 34;
    }
    h += 60; // 底部：查看联系方式
    return h;
  },

  // 两列瀑布流分列：贪心放入较矮的一列
  splitColumns(list) {
    const left = [];
    const right = [];
    let leftH = 0;
    let rightH = 0;
    (list || []).forEach(item => {
      const h = this.estimateCardHeight(item);
      if (leftH <= rightH) {
        left.push(item);
        leftH += h;
      } else {
        right.push(item);
        rightH += h;
      }
    });
    return { left, right };
  },

  // 事件处理
  onPhoneInput(e) {
    this.setData({ loginPhone: e.detail.value });
  },

  async onLogin() {
    const phone = this.data.loginPhone.trim();
    if (!/^1[3-9]\d{9}$/.test(phone)) {
      wx.showToast({ title: '请输入正确的手机号', icon: 'none' });
      return;
    }

    this.setData({ loggingIn: true });
    try {
      const res = await api.login(phone);
      if (res.code === 0) {
        if (res.data.isNewUser) {
          // 新用户跳转发布页
          wx.setStorageSync('tempPhone', phone);
          wx.showModal({
            title: '提示',
            content: '您还未注册，请先发布启事',
            showCancel: false,
            success: () => {
              wx.switchTab({ url: '/pages/publish/publish' });
            }
          });
        } else {
          // 登录成功
          const u = res.data.user;
          wx.setStorageSync('userInfo', u);
          wx.setStorageSync('userId', String(u.id));
          this.setData({ isLoggedIn: true });
          this.initData();
          wx.showToast({ title: '登录成功', icon: 'success' });
        }
      } else {
        wx.showToast({ title: res.msg, icon: 'none' });
      }
    } catch (err) {
      wx.showToast({ title: '登录失败', icon: 'none' });
    }
    this.setData({ loggingIn: false });
  },

  onFilterChange(e) {
    this.setData({ filter: e.detail.filter });
    this.loadAssignedNotices();
  },

  onTabSwitch(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ activeTab: tab });
    if (tab === 'mine') {
      this.loadMyNotices();
    } else if (tab === 'history') {
      this.loadHistoryNotices();
    }
  },

  // 查看完整手机号（列表返回的是脱敏号，需按需获取）
  async onShowPhone(e) {
    const { notice } = e.detail;
    try {
      const res = await api.viewNoticePhone(notice.id);
      if (res.code === 0) {
        wx.showModal({
          title: '联系方式',
          content: `手机号码：${res.data.phone}\n姓名：${res.data.name}`,
          showCancel: false,
          confirmText: '知道了'
        });
      } else {
        wx.showToast({ title: res.msg || '获取联系方式失败', icon: 'none' });
      }
    } catch (err) {
      wx.showToast({ title: '获取联系方式失败，请重试', icon: 'none' });
    }
  },

  onGoPublish() {
    wx.switchTab({ url: '/pages/publish/publish' });
  },

  onGoMy() {
    wx.switchTab({ url: '/pages/my/my' });
  }
});
