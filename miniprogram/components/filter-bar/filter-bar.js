// components/filter-bar/filter-bar.js
Component({
  properties: {
    filter: {
      type: Object,
      value: {}
    },
    membershipType: {
      type: String,
      value: 'free'
    }
  },

  data: {
    expanded: false,
    activeCount: 0,
    tempFilter: {}
  },

  lifetimes: {
    attached() {
      this.setData({ tempFilter: { ...this.properties.filter } });
      this.updateActiveCount(this.properties.filter);
    }
  },

  observers: {
    filter(newVal) {
      this.setData({ tempFilter: { ...newVal } });
      this.updateActiveCount(newVal);
    }
  },

  methods: {
    isMember() {
      const type = this.properties.membershipType;
      return type === 'member' || type === 'vip';
    },

    updateActiveCount(f) {
      let count = 0;
      if (f.housingLocation) count++;
      if (f.ageRange) count++;
      if (f.heightRange) count++;
      if (f.weightRange) count++;
      if (f.isPublicSector !== undefined) count++;
      if (f.income) count++;
      if (f.occupation) count++;
      this.setData({ activeCount: count });
    },

    onToggle() {
      this.setData({ expanded: !this.data.expanded });
    },

    onFilter(e) {
      const { key, value } = e.currentTarget.dataset;
      let val = value;
      if (value === 'true') val = true;
      else if (value === 'false') val = false;
      else if (value === '') val = undefined;

      const newFilter = { ...this.data.tempFilter };

      if (val === undefined) {
        delete newFilter[key];
      } else {
        newFilter[key] = val;
      }

      this.setData({ tempFilter: newFilter });
      this.updateActiveCount(newFilter);

      this.triggerEvent('change', { filter: this.convertFilter(newFilter) });
    },

    onMemberFilter(e) {
      if (!this.isMember()) {
        wx.showModal({
          title: '会员专享',
          content: '该筛选项为会员专享功能，请先升级会员',
          confirmText: '去开通',
          cancelText: '取消',
          success: (res) => {
            if (res.confirm) {
              wx.switchTab({ url: '/pages/my/my' });
            }
          }
        });
        return;
      }
      this.onFilter(e);
    },

    onReset() {
      this.setData({
        tempFilter: {},
        activeCount: 0
      });
      this.triggerEvent('change', { filter: {} });
    },

    onConfirm() {
      this.setData({ expanded: false });
      this.triggerEvent('change', { filter: this.convertFilter(this.data.tempFilter) });
    },

    convertFilter(f) {
      const result = {};
      // 必填项筛选（所有用户可用）
      if (f.housingLocation) result.housingLocation = f.housingLocation;
      if (f.ageRange) {
        const [min, max] = f.ageRange.split('-').map(Number);
        result.minAge = min;
        result.maxAge = max;
      }

      // 选填项筛选（仅会员生效）
      if (this.isMember()) {
        if (f.heightRange) {
          const [min, max] = f.heightRange.split('-').map(Number);
          result.minHeight = min;
          result.maxHeight = max;
        }
        if (f.weightRange) {
          const [min, max] = f.weightRange.split('-').map(Number);
          result.minWeight = min;
          result.maxWeight = max;
        }
        if (f.isPublicSector !== undefined) result.isPublicSector = f.isPublicSector;
        if (f.income) result.income = f.income;
        if (f.occupation) result.occupation = f.occupation;
      }

      return result;
    }
  }
});

