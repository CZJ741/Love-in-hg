// components/privacy-popup/privacy-popup.js
/**
 * 微信官方规范隐私协议授权弹窗组件
 * 监听 wx.onNeedPrivacyAuthorization 事件，并在敏感权限触发时弹出
 */
Component({
  data: {
    showModal: false
  },

  lifetimes: {
    attached() {
      if (wx.onNeedPrivacyAuthorization) {
        wx.onNeedPrivacyAuthorization((resolve) => {
          this.resolvePrivacyAuthorization = resolve;
          this.setData({ showModal: true });
        });
      }
    }
  },

  methods: {
    onOpenPrivacyContract() {
      if (wx.openPrivacyContract) {
        wx.openPrivacyContract({
          fail: () => {
            wx.navigateTo({ url: '/pages/privacy/privacy' });
          }
        });
      } else {
        wx.navigateTo({ url: '/pages/privacy/privacy' });
      }
    },

    onAgree(e) {
      this.setData({ showModal: false });
      if (this.resolvePrivacyAuthorization) {
        this.resolvePrivacyAuthorization({
          buttonId: 'agree-btn',
          event: 'agree'
        });
        this.resolvePrivacyAuthorization = null;
      }
    },

    onDisagree() {
      this.setData({ showModal: false });
      if (this.resolvePrivacyAuthorization) {
        this.resolvePrivacyAuthorization({
          event: 'disagree'
        });
        this.resolvePrivacyAuthorization = null;
      }
    }
  }
});
