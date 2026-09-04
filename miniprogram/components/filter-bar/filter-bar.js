// components/filter-bar/filter-bar.js
Component({
  properties: {
    filter: {
      type: Object,
      value: {}
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
    updateActiveCount(f) {
      let count = 0;
      if (f.gender) count++;
      if (f.ageRange) count++;
      if (f.heightRange) count++;
      if (f.isPublicSector !== undefined) count++;
      if (f.income) count++;
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
      if (f.gender) result.gender = f.gender;
      if (f.income) result.income = f.income;
      if (f.isPublicSector !== undefined) result.isPublicSector = f.isPublicSector;

      if (f.ageRange) {
        const [min, max] = f.ageRange.split('-').map(Number);
        result.minAge = min;
        result.maxAge = max;
      }
      if (f.heightRange) {
        const [min, max] = f.heightRange.split('-').map(Number);
        result.minHeight = min;
        result.maxHeight = max;
      }
      return result;
    }
  }
});
