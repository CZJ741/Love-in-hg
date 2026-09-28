// pages/notice/notice.js
const api = require('../../utils/api');

Page({
  data: {
    isLoggedIn: false,
    loginPhone: '',
    loggingIn: false,
    authMode: 'login', // 'login' (老用户登录) | 'register' (新用户验证)

    // 新用户验证码相关
    regPhone: '',
    regCode: '',
    countdown: 0,
    verifying: false,

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

    // 是否已触发上拉触底（触底后才展示开通VIP获取更多启事提示）
    hasReachedBottom: false,

    // 登录弹窗
    showLoginModal: false,

    // UGC 举报弹窗
    showReportModal: false,
    reportNoticeId: null,
    reportReasons: ['涉黄低俗', '虚假诈骗', '广告骚扰', '侵犯隐私', '其他'],
    reportReasonIndex: 0,
    reportDescription: '',
    reportSubmitting: false
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
    this.setData({ showLoginModal: true, authMode: 'login' });
  },

  onCloseLoginModal() {
    this.setData({ showLoginModal: false });
  },

  onRequireLogin(e) {
    this.setData({ showLoginModal: true, authMode: 'login' });
  },

  onSwitchAuthMode(e) {
    const mode = e.currentTarget.dataset.mode;
    if (mode && mode !== this.data.authMode) {
      this.setData({ authMode: mode });
    }
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
  async loadAssignedNotices(showLoading = false) {
    if (showLoading) {
      wx.showLoading({ title: '加载中...', mask: true });
    }
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
    } finally {
      if (showLoading) {
        wx.hideLoading();
      }
      this.setData({ loading: false });
    }
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
          isLoggedIn: true,
          showLoginModal: false,
          regPhone: '',
          regCode: ''
        });
        if (this.smsTimer) {
          clearInterval(this.smsTimer);
          this.setData({ countdown: 0 });
        }
        this.initData();
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

  async onLogin() {
    const phone = this.data.loginPhone.trim();
    if (!/^1[3-9]\d{9}$/.test(phone)) {
      wx.showToast({ title: '请输入正确的手机号', icon: 'none' });
      return;
    }

    this.setData({ loggingIn: true });
    wx.showLoading({ title: '登录中...', mask: true });
    try {
      // 获取微信 code 以便首次登录自动绑定 openid
      let wxCode = '';
      try {
        const loginRes = await new Promise((resolve) => wx.login({ success: resolve, fail: () => resolve({}) }));
        wxCode = loginRes.code || '';
      } catch (e) {}

      const res = await api.login(phone, wxCode);
      wx.hideLoading();
      if (res.code === 0) {
        if (res.data.isNewUser) {
          // 未预留手机号
          wx.showModal({
            title: '提示',
            content: '该手机号未预留档案，请点击“注册”进行手机验证注册',
            showCancel: false
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
      wx.hideLoading();
      wx.showToast({ title: '登录失败', icon: 'none' });
    }
    this.setData({ loggingIn: false });
  },

  onFilterChange(e) {
    this.setData({ filter: e.detail.filter });
    this.loadAssignedNotices(true);
  },

  onTabSwitch(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ activeTab: tab, hasReachedBottom: false });
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

  // 打开举报弹窗
  onOpenReport() {
    if (!this.data.isLoggedIn) {
      this.setData({ showLoginModal: true });
      return;
    }
    const notice = this.data.detailNotice;
    if (!notice) return;
    this.setData({
      showReportModal: true,
      reportNoticeId: notice.id,
      reportReasonIndex: 0,
      reportDescription: ''
    });
  },

  onCloseReport() {
    this.setData({
      showReportModal: false,
      reportNoticeId: null,
      reportDescription: ''
    });
  },

  onReasonChange(e) {
    this.setData({ reportReasonIndex: Number(e.detail.value) });
  },

  onReportDescInput(e) {
    this.setData({ reportDescription: e.detail.value });
  },

  async onSubmitReport() {
    const noticeId = this.data.reportNoticeId;
    const reason = this.data.reportReasons[this.data.reportReasonIndex];
    const description = this.data.reportDescription;

    this.setData({ reportSubmitting: true });
    try {
      const res = await api.reportNotice({ noticeId, reason, description });
      this.setData({ reportSubmitting: false, showReportModal: false });
      if (res.code === 0) {
        wx.showToast({ title: '举报已提交，核实中', icon: 'success' });
      } else {
        wx.showToast({ title: res.msg || '举报失败', icon: 'none' });
      }
    } catch (e) {
      this.setData({ reportSubmitting: false });
      wx.showToast({ title: '网络异常，请重试', icon: 'none' });
    }
  },

  // 屏蔽/拉黑该用户
  onBlockUser() {
    if (!this.data.isLoggedIn) {
      this.setData({ showLoginModal: true });
      return;
    }
    const notice = this.data.detailNotice;
    if (!notice) return;

    wx.showModal({
      title: '屏蔽确认',
      content: '确定要屏蔽该用户吗？屏蔽后系统将不再向您推荐该用户发布的相亲启事。',
      confirmText: '确定屏蔽',
      confirmColor: '#e74c3c',
      success: async (res) => {
        if (!res.confirm) return;
        wx.showLoading({ title: '处理中...' });
        try {
          const blockRes = await api.blockUser({ targetUserId: notice.userId, noticeId: notice.id });
          wx.hideLoading();
          if (blockRes.code === 0) {
            wx.showToast({ title: '已屏蔽该用户', icon: 'success' });
            // 从当前列表中移除
            this.removeNoticeFromFeed(notice.id);
            this.onCloseDetailModal();
          } else {
            wx.showToast({ title: blockRes.msg || '屏蔽失败', icon: 'none' });
          }
        } catch (e) {
          wx.hideLoading();
          wx.showToast({ title: '操作失败，请稍后重试', icon: 'none' });
        }
      }
    });
  },

  removeNoticeFromFeed(noticeId) {
    const filterFn = (item) => String(item.id) !== String(noticeId);
    this.setData({
      assignedNotices: this.data.assignedNotices.filter(filterFn),
      assignedLeft: this.data.assignedLeft.filter(filterFn),
      assignedRight: this.data.assignedRight.filter(filterFn),
      historyNotices: this.data.historyNotices.filter(filterFn),
      historyLeft: this.data.historyLeft.filter(filterFn),
      historyRight: this.data.historyRight.filter(filterFn)
    });
  },

  onGoPublish() {
    wx.switchTab({ url: '/pages/publish/publish' });
  },

  onGoMy() {
    wx.switchTab({ url: '/pages/my/my' });
  },

  onUnload() {
    if (this.smsTimer) {
      clearInterval(this.smsTimer);
    }
  },

  // 上拉触底/加载更多
  onReachBottom() {
    if (!this.data.hasReachedBottom) {
      this.setData({ hasReachedBottom: true });
    }
  },

  // 下拉刷新
  async onPullDownRefresh() {
    this.setData({ hasReachedBottom: false });
    if (this.data.activeTab === 'assigned') {
      await this.initData();
    } else if (this.data.isLoggedIn) {
      if (this.data.activeTab === 'mine') {
        await this.loadMyNotices();
      } else if (this.data.activeTab === 'history') {
        await this.loadHistoryNotices();
      }
    }
    wx.stopPullDownRefresh();
  }
});
