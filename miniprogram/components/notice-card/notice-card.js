// components/notice-card/notice-card.js
Component({
  properties: {
    notice: {
      type: Object,
      value: {}
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
    age: 0
  },

  observers: {
    'notice.age, notice.birthday'(age, birthday) {
      if (age && Number(age) > 0) {
        this.setData({ age: Number(age) });
        return;
      }
      if (birthday) {
        // 尝试从生日中匹配出4位年份
        const match = String(birthday).match(/(\d{4})/);
        if (match) {
          const birthYear = parseInt(match[1]);
          const now = new Date().getFullYear();
          if (birthYear > 1900 && birthYear <= now) {
            this.setData({ age: now - birthYear });
            return;
          }
        }
      }
      this.setData({ age: 0 });
    }
  },


  methods: {
    onTap() {
      this.triggerEvent('tap', { notice: this.data.notice });
    },

    onShowPhone() {
      this.triggerEvent('showphone', { notice: this.data.notice });
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

