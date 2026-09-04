// pages/publish-edit/publish-edit.js
// 启事编辑页面 — 承载发布/编辑表单
// 新增模式：从 storage.userInfo 回填基础信息
// 编辑模式：从 storage.editNoticeData 回填启事数据
const api = require('../../utils/api');

Page({
  data: {
    isEdit: false,
    existingNoticeId: null,
    form: {
      phone: '',
      name: '',
      nickname: '',
      gender: '',
      birthday: '',
      occupation: '',
      income: '',
      isPublicSector: undefined,
      height: '',
      weight: '',
      remark: ''
    },
    today: '',
    maxBirthday: '',
    incomeOptions: ['3万以下', '3-5万', '5-10万', '10-20万', '20-30万', '30-50万', '50万以上'],
    submitting: false
  },

  onLoad() {
    const now = new Date();
    this.setData({
      today: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
    });

    // 生日选择上限：18 年前（仅面向年满 18 周岁用户）
    const maxDate = new Date(now.getFullYear() - 18, now.getMonth(), now.getDate());
    this.setData({
      maxBirthday: `${maxDate.getFullYear()}-${String(maxDate.getMonth() + 1).padStart(2, '0')}-${String(maxDate.getDate()).padStart(2, '0')}`
    });

    // 编辑模式：优先取 storage 中的启事数据回填
    const editNotice = wx.getStorageSync('editNoticeData');
    if (editNotice && editNotice.id) {
      wx.setNavigationBarTitle({ title: '修改启事' });
      this.setData({
        isEdit: true,
        existingNoticeId: editNotice.id,
        form: {
          phone: editNotice.phone || '',
          name: editNotice.name || '',
          nickname: editNotice.nickname || '',
          gender: editNotice.gender || '',
          birthday: editNotice.birthday || '',
          occupation: editNotice.occupation || '',
          income: editNotice.income || '',
          isPublicSector: editNotice.isPublicSector || undefined,
          height: editNotice.height ? String(editNotice.height) : '',
          weight: editNotice.weight ? String(editNotice.weight) : '',
          remark: editNotice.remark || ''
        }
      });
      // 编辑数据用完即清，避免下次误入编辑模式
      wx.removeStorageSync('editNoticeData');
      return;
    }

    // 新增模式：从临时手机号 / 用户信息回填
    const tempPhone = wx.getStorageSync('tempPhone');
    if (tempPhone) {
      this.setData({ 'form.phone': tempPhone });
      wx.removeStorageSync('tempPhone');
    }

    const userInfo = wx.getStorageSync('userInfo');
    if (userInfo) {
      this.setData({
        'form.phone': userInfo.phone || '',
        'form.name': userInfo.name || '',
        'form.gender': userInfo.gender || '',
        'form.birthday': userInfo.birthday || '',
        'form.occupation': userInfo.occupation || '',
        'form.income': userInfo.income || '',
        'form.isPublicSector': userInfo.isPublicSector || undefined,
        'form.height': userInfo.height ? String(userInfo.height) : '',
        'form.weight': userInfo.weight ? String(userInfo.weight) : '',
      });
    }
  },

  onFieldChange(e) {
    const { field } = e.currentTarget.dataset;
    this.setData({ [`form.${field}`]: e.detail.value });
  },

  onSelectGender(e) {
    this.setData({ 'form.gender': e.currentTarget.dataset.value });
  },

  onBirthdayChange(e) {
    this.setData({ 'form.birthday': e.detail.value });
  },

  onIncomeChange(e) {
    const idx = parseInt(e.detail.value);
    this.setData({ 'form.income': this.data.incomeOptions[idx] });
  },

  onSelectSector(e) {
    const val = e.currentTarget.dataset.value;
    this.setData({ 'form.isPublicSector': val === 'true' });
  },

  async onSubmit() {
    const { form } = this.data;

    if (!form.phone.trim()) {
      wx.showToast({ title: '请输入手机号码', icon: 'none' });
      return;
    }
    if (!/^1[3-9]\d{9}$/.test(form.phone.trim())) {
      wx.showToast({ title: '手机号码格式不正确', icon: 'none' });
      return;
    }
    if (!form.name.trim()) {
      wx.showToast({ title: '请输入姓名', icon: 'none' });
      return;
    }
    if (!form.gender) {
      wx.showToast({ title: '请选择性别', icon: 'none' });
      return;
    }
    if (!form.birthday) {
      wx.showToast({ title: '请选择生日', icon: 'none' });
      return;
    }

    this.setData({ submitting: true });

    try {
      const data = {
        phone: form.phone.trim(),
        name: form.name.trim(),
        nickname: form.nickname.trim(),
        gender: form.gender,
        birthday: form.birthday,
        occupation: form.occupation.trim(),
        income: form.income,
        isPublicSector: form.isPublicSector,
        height: form.height ? parseInt(form.height) : 0,
        weight: form.weight ? parseInt(form.weight) : 0,
        remark: form.remark.trim()
      };

      let res;
      if (this.data.isEdit && this.data.existingNoticeId) {
        res = await api.updateNotice(this.data.existingNoticeId, data);
      } else {
        res = await api.publishNotice(data);
      }

      if (res.code === 0) {
        wx.setStorageSync('userInfo', {
          ...data,
          id: res.data.userId || wx.getStorageSync('userId')
        });
        if (!this.data.isEdit) {
          wx.setStorageSync('userId', String(res.data.userId));
        }
        wx.showToast({ title: this.data.isEdit ? '修改成功' : '发布成功', icon: 'success' });
        setTimeout(() => {
          wx.navigateBack();
        }, 1500);
      } else {
        wx.showToast({ title: res.msg, icon: 'none' });
      }
    } catch (err) {
      wx.showToast({ title: '操作失败，请重试', icon: 'none' });
    }

    this.setData({ submitting: false });
  }
});
