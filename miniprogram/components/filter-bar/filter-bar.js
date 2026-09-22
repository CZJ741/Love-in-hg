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
    tempFilter: {},

    // 基础筛选选项（直接呈现在筛选栏上的下拉选项）
    genderOptions: ['不限', '男', '女'],
    housingOptions: ['不限', '本地', '外地'],
    ageOptions: ['不限', '18-25岁', '26-30岁', '31-35岁', '36-40岁', '41-50岁', '50岁以上'],

    genderIndex: 0,
    housingIndex: 0,
    ageIndex: 0
  },

  lifetimes: {
    attached() {
      this.syncFromFilter(this.properties.filter);
    }
  },

  observers: {
    filter(newVal) {
      this.syncFromFilter(newVal);
    }
  },

  methods: {
    isMember() {
      const type = this.properties.membershipType;
      return type === 'member' || type === 'vip';
    },

    syncFromFilter(f = {}) {
      const gIdx = f.gender === '男' ? 1 : (f.gender === '女' ? 2 : 0);
      const hIdx = f.housingLocation === '本地' ? 1 : (f.housingLocation === '外地' ? 2 : 0);

      let aIdx = 0;
      let ageKey = f.ageRange;
      if (!ageKey && f.minAge && f.maxAge) {
        ageKey = `${f.minAge}-${f.maxAge}`;
      }
      if (ageKey) {
        const ageMap = {
          '18-25': 1,
          '26-30': 2,
          '31-35': 3,
          '36-40': 4,
          '41-50': 5,
          '50-100': 6
        };
        aIdx = ageMap[ageKey] || 0;
      }

      this.setData({
        tempFilter: { ...f },
        genderIndex: gIdx,
        housingIndex: hIdx,
        ageIndex: aIdx
      });
      this.updateActiveCount(f);
    },

    updateActiveCount(f) {
      let count = 0;
      if (f.gender) count++;
      if (f.housingLocation) count++;
      if (f.ageRange) count++;
      if (f.heightRange) count++;
      if (f.weightRange) count++;
      if (f.isPublicSector !== undefined && f.isPublicSector !== '') count++;
      if (f.income) count++;
      if (f.occupation) count++;
      this.setData({ activeCount: count });
    },

    onToggleExpand() {
      this.setData({ expanded: !this.data.expanded });
    },

    // 基础筛选：下拉菜单变更
    onGenderChange(e) {
      const idx = Number(e.detail.value);
      const val = idx === 1 ? '男' : (idx === 2 ? '女' : '');
      const newFilter = { ...this.data.tempFilter };
      if (val) {
        newFilter.gender = val;
      } else {
        delete newFilter.gender;
      }
      this.setData({ genderIndex: idx, tempFilter: newFilter });
      this.updateActiveCount(newFilter);
      this.emitChange(newFilter);
    },

    onHousingChange(e) {
      const idx = Number(e.detail.value);
      const val = idx === 1 ? '本地' : (idx === 2 ? '外地' : '');
      const newFilter = { ...this.data.tempFilter };
      if (val) {
        newFilter.housingLocation = val;
      } else {
        delete newFilter.housingLocation;
      }
      this.setData({ housingIndex: idx, tempFilter: newFilter });
      this.updateActiveCount(newFilter);
      this.emitChange(newFilter);
    },

    onAgeChange(e) {
      const idx = Number(e.detail.value);
      const ageMap = ['', '18-25', '26-30', '31-35', '36-40', '41-50', '50-100'];
      const val = ageMap[idx] || '';
      const newFilter = { ...this.data.tempFilter };
      if (val) {
        newFilter.ageRange = val;
      } else {
        delete newFilter.ageRange;
      }
      this.setData({ ageIndex: idx, tempFilter: newFilter });
      this.updateActiveCount(newFilter);
      this.emitChange(newFilter);
    },

    // 会员进阶筛选点击
    onMemberFilter(e) {
      const { key, value } = e.currentTarget.dataset;
      if (!this.isMember()) {
        wx.showModal({
          title: '会员专享功能',
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

      const newFilter = { ...this.data.tempFilter };
      if (newFilter[key] === value || value === '') {
        delete newFilter[key];
      } else {
        newFilter[key] = value;
      }
      this.setData({ tempFilter: newFilter });
      this.updateActiveCount(newFilter);
    },

    onReset() {
      this.setData({
        tempFilter: {},
        genderIndex: 0,
        housingIndex: 0,
        ageIndex: 0,
        activeCount: 0
      });
      this.triggerEvent('change', { filter: {} });
    },

    onConfirm() {
      this.setData({ expanded: false });
      this.emitChange(this.data.tempFilter);
    },

    emitChange(filterObj) {
      this.triggerEvent('change', { filter: this.convertFilter(filterObj) });
    },

    convertFilter(f) {
      const result = {};
      if (f.gender) result.gender = f.gender;
      if (f.housingLocation) result.housingLocation = f.housingLocation;
      if (f.ageRange) {
        result.ageRange = f.ageRange;
        const [min, max] = f.ageRange.split('-').map(Number);
        result.minAge = min;
        result.maxAge = max;
      } else if (f.minAge && f.maxAge) {
        result.minAge = f.minAge;
        result.maxAge = f.maxAge;
        result.ageRange = `${f.minAge}-${f.maxAge}`;
      }

      // 选填项筛选（仅会员生效）
      if (this.isMember()) {
        if (f.heightRange) {
          result.heightRange = f.heightRange;
          const [min, max] = f.heightRange.split('-').map(Number);
          result.minHeight = min;
          result.maxHeight = max;
        }
        if (f.weightRange) {
          result.weightRange = f.weightRange;
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
