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
    'notice.birthday'(birthday) {
      if (birthday) {
        const birthYear = parseInt(birthday.split('-')[0]);
        const now = new Date().getFullYear();
        this.setData({ age: now - birthYear });
      }
    }
  },

  methods: {
    onTap() {
      this.triggerEvent('tap', { notice: this.data.notice });
    },

    onShowPhone() {
      this.triggerEvent('showphone', { notice: this.data.notice });
    }
  }
});
