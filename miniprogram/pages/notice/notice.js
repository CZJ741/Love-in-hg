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
    loadingHistory: false,

    // 详情弹窗（包含全部信息：姓名、属性、照片画廊、联系方式）
    showDetailModal: false,
    detailNotice: null,
    detailLoading: false,

    // 登录弹窗
    showLoginModal: false
  },

  onLoad() {
    this.checkLogin();
    this.initData();
  },

  onShow() {
    this.checkLogin();
    if (this.data.activeTab === 'assigned') {
      this.initData();
    } else if (this.data.activeTab === 'mine' && this.data.isLoggedIn) {
      this.loadMyNotices();
    } else if (this.data.activeTab === 'history' && this.data.isLoggedIn) {
      this.loadHistoryNotices();
    }
  },

  checkLogin() {
    const userInfo = wx.getStorageSync('userInfo');
    const userId = wx.getStorageSync('userId');
    const logged = !!(userInfo && userId);
    this.setData({ isLoggedIn: logged });
  },

  onOpenLoginModal() {
    this.setData({ showLoginModal: true });
  },

  onCloseLoginModal() {
    this.setData({ showLoginModal: false });
  },

  onRequireLogin(e) {
    wx.showToast({ title: '登录后可查看启事详细信息', icon: 'none' });
    this.setData({ showLoginModal: true });
  },

  // 初始化
  async initData() {
    if (this.data.isLoggedIn) {
      await this.loadQuota();
    }
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
    if (notice.weight) h += 46;
    if (notice.remark) {
      const lines = Math.ceil((notice.remark.length || 0) / 16);
      h += 30 + lines * 34;
    }
    h += 60; // 底部：查看详情按钮
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
          this.setData({
            isLoggedIn: true,
            showLoginModal: false
          });
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

  // 点击查看详情（全量信息弹窗：包含照片相册与按需获取联系方式）
  async onViewDetail(e) {
    const notice = e.detail && e.detail.notice;
    if (!notice) return;

    if (!this.data.isLoggedIn) {
      wx.showToast({ title: '登录后可查看启事详细信息', icon: 'none' });
      this.setData({ showLoginModal: true });
      return;
    }

    // 初始化详情数据并展示弹窗
    this.setData({
      detailNotice: {
        ...notice,
        fullPhone: notice.phone && !notice.phone.includes('*') ? notice.phone : '',
        unlockedContact: !!(notice.phone && !notice.phone.includes('*'))
      },
      showDetailModal: true
    });

    // 如果未解锁联系方式（是脱敏号且不是本人启事），调用接口按需获取真实联系方式
    if (notice.phone && notice.phone.includes('*')) {
      try {
        const res = await api.viewNoticePhone(notice.id);
        if (res.code === 0) {
          this.setData({
            'detailNotice.fullPhone': res.data.phone,
            'detailNotice.socialAccount': res.data.socialAccount || notice.socialAccount || '',
            'detailNotice.name': res.data.name || notice.name,
            'detailNotice.unlockedContact': true
          });
        }
      } catch (err) {
        console.warn('获取联系方式失败:', err);
      }
    }
  },

  onCloseDetailModal() {
    this.setData({
      showDetailModal: false,
      detailNotice: null
    });
  },

  // 预览照片
  onPreviewPhoto(e) {
    const current = e.currentTarget.dataset.src;
    const urls = (this.data.detailNotice && this.data.detailNotice.images) || [];
    wx.previewImage({
      current,
      urls
    });
  },

  onCopyDetailPhone() {
    const phone = this.data.detailNotice && this.data.detailNotice.fullPhone;
    if (!phone) return;
    wx.setClipboardData({
      data: phone,
      success: () => {
        wx.showToast({ title: '电话已复制', icon: 'success' });
      }
    });
  },

  onCopyDetailSocial() {
    const social = this.data.detailNotice && this.data.detailNotice.socialAccount;
    if (!social) return;
    wx.setClipboardData({
      data: social,
      success: () => {
        wx.showToast({ title: '社交账号已复制', icon: 'success' });
      }
    });
  },

  onCallDetailPhone() {
    const phone = this.data.detailNotice && this.data.detailNotice.fullPhone;
    if (!phone) return;
    wx.makePhoneCall({
      phoneNumber: phone
    });
  },

  onGoPublish() {
    wx.switchTab({ url: '/pages/publish/publish' });
  },

  onGoMy() {
    wx.switchTab({ url: '/pages/my/my' });
  },

  // 下拉刷新
  async onPullDownRefresh() {
    if (this.data.isLoggedIn) {
      if (this.data.activeTab === 'assigned') {
        await this.initData();
      } else if (this.data.activeTab === 'mine') {
        await this.loadMyNotices();
      } else if (this.data.activeTab === 'history') {
        await this.loadHistoryNotices();
      }
    }
    wx.stopPullDownRefresh();
  }
});
