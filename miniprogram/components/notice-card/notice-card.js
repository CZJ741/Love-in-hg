// components/notice-card/notice-card.js
Component({
  properties: {
    notice: {
      type: Object,
      value: {}
    },
    // 是否已登录
    isLoggedIn: {
      type: Boolean,
      value: true
    },
    // 是否显示完整手机号
    showPhone: {
      type: Boolean,
      value: false
    },
    // 是否隐藏查看联系方式按钮
    hidePhoneAction: {
      type: Boolean,
      value: false
    }
  },

  computed: {},

  data: {
    age: 0,
    showPhotoModal: false
  },

  observers: {
    'notice.age'(age) {
      if (age && Number(age) > 0) {
        this.setData({ age: Number(age) });
        return;
      }
      this.setData({ age: 0 });
    }
  },

  methods: {
    stopBubble() {},

    onTap() {
      this.triggerEvent('tap', { notice: this.data.notice });
    },

    onViewDetail() {
      if (!this.properties.isLoggedIn) {
        this.triggerEvent('requirelogin', { action: 'detail' });
        return;
      }
      this.triggerEvent('viewdetail', { notice: this.data.notice });
    },

    onShowPhone() {
      if (!this.properties.isLoggedIn) {
        this.triggerEvent('requirelogin', { action: 'phone' });
        return;
      }
      this.triggerEvent('showphone', { notice: this.data.notice });
    },

    onOpenPhotoModal() {
      if (!this.properties.isLoggedIn) {
        this.triggerEvent('requirelogin', { action: 'photo' });
        return;
      }
      this.setData({ showPhotoModal: true });
    },

    onClosePhotoModal() {
      this.setData({ showPhotoModal: false });
    },

    onPreviewPhoto(e) {
      const current = e.currentTarget.dataset.src;
      const urls = this.data.notice.images || [];
      wx.previewImage({
        current,
        urls
      });
    }
  }
});

