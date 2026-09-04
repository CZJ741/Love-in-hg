// pages/publish/publish.js
// 发布页 — 只展示"我的启事"列表，点击编辑/新增跳转到 publish-edit 页面
const api = require('../../utils/api');

Page({
  data: {
    myNotices: [],
    loading: false
  },

  onShow() {
    this.loadMyNotices();
  },

  async loadMyNotices() {
    const userId = wx.getStorageSync('userId');
    if (!userId) return;

    this.setData({ loading: true });
    try {
      const res = await api.getMyNotices();
      if (res.code === 0) {
        this.setData({ myNotices: res.data.notices || [] });
      }
    } catch (err) {
      console.error('加载我的启事失败:', err);
    }
    this.setData({ loading: false });
  },

  // 编辑已有启事：存数据并跳转编辑页
  onEditNotice(e) {
    const notice = e.currentTarget.dataset.notice;
    wx.setStorageSync('editNoticeData', notice);
    wx.navigateTo({ url: '/pages/publish-edit/publish-edit' });
  },

  // 新增启事：清空编辑数据并跳转编辑页
  onNewNotice() {
    wx.removeStorageSync('editNoticeData');
    wx.navigateTo({ url: '/pages/publish-edit/publish-edit' });
  },

  // 删除启事：二次确认后调用后端接口
  onDeleteNotice(e) {
    const noticeId = e.currentTarget.dataset.id;
    const noticeName = e.currentTarget.dataset.name || '该启事';

    wx.showModal({
      title: '确认删除',
      content: `确定要删除「${noticeName}」的启事吗？删除后不可恢复。`,
      confirmColor: '#e74c3c',
      confirmText: '删除',
      cancelText: '取消',
      success: async (res) => {
        if (!res.confirm) return;

        wx.showLoading({ title: '删除中...' });
        try {
          const result = await api.deleteNotice(noticeId);
          wx.hideLoading();

          if (result.code === 0) {
            wx.showToast({ title: '删除成功', icon: 'success' });
            this.loadMyNotices();
          } else {
            wx.showToast({ title: result.msg || '删除失败', icon: 'none' });
          }
        } catch (err) {
          wx.hideLoading();
          console.error('删除启事失败:', err);
          wx.showToast({ title: '网络错误，删除失败', icon: 'none' });
        }
      }
    });
  }
});
