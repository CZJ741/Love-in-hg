// pages/publish-edit/publish-edit.js
// 启事编辑页面 — 承载发布/编辑表单
// 新增模式：纯空白表单，不预填数据
// 编辑模式：从 storage.editNoticeData 回填启事数据
const api = require('../../utils/api');

Page({
  data: {
    isEdit: false,
    hasDraft: false,
    existingNoticeId: null,
    publisherRoles: ['本人', '父母', '亲戚', '朋友'],
    form: {
      publisherRole: '本人',
      phone: '',
      name: '',
      gender: '',
      age: '',
      housingLocation: '本地',
      occupation: '',
      income: '',
      isPublicSector: undefined,
      height: '',
      weight: '',
      socialAccount: '',
      remark: ''
    },
    images: [], // 已上传或选中的图片列表（最多9张）
    incomeOptions: ['3万以下', '3-5万', '5-10万', '10-20万', '20-30万', '30-50万', '50万以上'],
    submitting: false
  },

  onLoad() {
    // 登录校验：未登录不能发布或修改启事
    const userInfo = wx.getStorageSync('userInfo');
    const userId = wx.getStorageSync('userId');
    if (!userInfo || !userId) {
      wx.showModal({
        title: '提示',
        content: '请先登录后再发布或修改启事',
        showCancel: false,
        success: () => {
          wx.switchTab({ url: '/pages/notice/notice' });
        }
      });
      return;
    }

    const currentPhone = (userInfo && userInfo.phone) || '';

    // 编辑模式：优先取 storage 中的启事数据回填
    const editNotice = wx.getStorageSync('editNoticeData');
    if (editNotice && editNotice.id) {
      wx.setNavigationBarTitle({ title: '修改启事' });
      let noticeImages = editNotice.images || [];
      if (typeof noticeImages === 'string') {
        try {
          noticeImages = JSON.parse(noticeImages);
        } catch (e) {
          noticeImages = [];
        }
      }
      this.setData({
        isEdit: true,
        hasDraft: false,
        existingNoticeId: editNotice.id,
        images: Array.isArray(noticeImages) ? noticeImages : [],
        form: {
          publisherRole: editNotice.publisherRole || '本人',
          phone: editNotice.phone || currentPhone,
          name: editNotice.name || '',
          gender: editNotice.gender || '',
          age: editNotice.age ? String(editNotice.age) : '',
          housingLocation: editNotice.housingLocation || '本地',
          occupation: editNotice.occupation || '',
          income: editNotice.income || '',
          isPublicSector: editNotice.isPublicSector || undefined,
          height: editNotice.height ? String(editNotice.height) : '',
          weight: editNotice.weight ? String(editNotice.weight) : '',
          socialAccount: editNotice.socialAccount || '',
          remark: editNotice.remark || ''
        }
      });
      // 编辑数据用完即清，避免下次误入编辑模式
      wx.removeStorageSync('editNoticeData');
      return;
    }

    // 新增模式：检查是否有本地暂存草稿，手机号强制绑定为当前用户手机号
    const draft = wx.getStorageSync('publishNoticeDraft');
    if (draft && draft.form) {
      this.setData({
        isEdit: false,
        hasDraft: true,
        images: Array.isArray(draft.images) ? draft.images : [],
        form: {
          ...draft.form,
          phone: currentPhone // 始终以当前登录手机号为准
        }
      });
      wx.showToast({ title: '已恢复暂存草稿', icon: 'none' });
    } else {
      this.setData({
        isEdit: false,
        hasDraft: false,
        'form.phone': currentPhone
      });
    }
  },

  // 手动暂存草稿
  onSaveDraft() {
    if (this.data.isEdit) return;
    const draftData = {
      form: this.data.form,
      images: this.data.images,
      savedAt: Date.now()
    };
    wx.setStorageSync('publishNoticeDraft', draftData);
    this.setData({ hasDraft: true });
    wx.showToast({ title: '草稿暂存成功', icon: 'success' });
  },

  // 清除草稿
  onClearDraft() {
    wx.showModal({
      title: '清除暂存',
      content: '确定要清空已暂存的草稿内容吗？',
      confirmColor: '#e74c3c',
      success: (res) => {
        if (!res.confirm) return;
        wx.removeStorageSync('publishNoticeDraft');
        const userInfo = wx.getStorageSync('userInfo');
        const currentPhone = (userInfo && userInfo.phone) || '';
        this.setData({
          hasDraft: false,
          images: [],
          form: {
            publisherRole: '本人',
            phone: currentPhone,
            name: '',
            gender: '',
            age: '',
            housingLocation: '本地',
            occupation: '',
            income: '',
            isPublicSector: undefined,
            height: '',
            weight: '',
            socialAccount: '',
            remark: ''
          }
        });
        wx.showToast({ title: '已清空草稿', icon: 'none' });
      }
    });
  },

  onFieldChange(e) {
    const { field } = e.currentTarget.dataset;
    this.setData({ [`form.${field}`]: e.detail.value });
    // 用户编辑时自动同步保存到草稿
    if (!this.data.isEdit) {
      this.autoSaveDraft();
    }
  },

  onSelectPublisherRole(e) {
    const role = e.currentTarget.dataset.role;
    this.setData({ 'form.publisherRole': role });
    if (!this.data.isEdit) this.autoSaveDraft();
  },

  onSelectGender(e) {
    this.setData({ 'form.gender': e.currentTarget.dataset.value });
    if (!this.data.isEdit) this.autoSaveDraft();
  },

  onSelectHousingLocation(e) {
    this.setData({ 'form.housingLocation': e.currentTarget.dataset.value });
    if (!this.data.isEdit) this.autoSaveDraft();
  },

  onIncomeChange(e) {
    const idx = parseInt(e.detail.value);
    this.setData({ 'form.income': this.data.incomeOptions[idx] });
    if (!this.data.isEdit) this.autoSaveDraft();
  },

  onSelectSector(e) {
    const val = e.currentTarget.dataset.value;
    const isPublic = (val === true || val === 'true');
    this.setData({ 'form.isPublicSector': isPublic });
    if (!this.data.isEdit) this.autoSaveDraft();
  },

  // 轻量防抖自动暂存
  autoSaveDraft() {
    if (this._draftTimer) clearTimeout(this._draftTimer);
    this._draftTimer = setTimeout(() => {
      wx.setStorageSync('publishNoticeDraft', {
        form: this.data.form,
        images: this.data.images,
        savedAt: Date.now()
      });
      if (!this.data.hasDraft) {
        this.setData({ hasDraft: true });
      }
    }, 600);
  },



  // 选择并上传图片（最多9张）
  onChooseImages() {
    const maxCount = 9 - this.data.images.length;
    if (maxCount <= 0) {
      wx.showToast({ title: '最多支持上传9张图片', icon: 'none' });
      return;
    }

    wx.chooseMedia({
      count: maxCount,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFilePaths = res.tempFiles.map(file => file.tempFilePath);
        wx.showLoading({ title: '上传中...' });

        // 调用批量上传接口
        api.uploadImages(tempFilePaths).then(uploadedUrls => {
          wx.hideLoading();
          this.setData({
            images: [...this.data.images, ...uploadedUrls].slice(0, 9)
          });
          wx.showToast({ title: '上传成功', icon: 'success' });
        }).catch(err => {
          wx.hideLoading();
          wx.showToast({ title: err.message || '上传失败', icon: 'none' });
        });
      },
      fail: (err) => {
        // 用户取消或拒绝权限
        if (err.errMsg && !err.errMsg.includes('cancel')) {
          wx.showToast({ title: '选择图片失败', icon: 'none' });
        }
      }
    });
  },

  // 预览大图
  onPreviewImage(e) {
    const current = e.currentTarget.dataset.current;
    wx.previewImage({
      current,
      urls: this.data.images
    });
  },

  // 删除某张图片
  onDeleteImage(e) {
    const index = e.currentTarget.dataset.index;
    const images = [...this.data.images];
    images.splice(index, 1);
    this.setData({ images });
  },

  async onSubmit() {
    const { form, images } = this.data;

    if (!form.phone.trim()) {
      wx.showToast({ title: '请输入联系方式', icon: 'none' });
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
    const ageNum = parseInt(form.age, 10);
    if (!form.age || isNaN(ageNum) || ageNum < 18 || ageNum > 100) {
      wx.showToast({ title: '请输入有效年龄(18-100)', icon: 'none' });
      return;
    }
    if (!form.housingLocation) {
      wx.showToast({ title: '请选择住房位置', icon: 'none' });
      return;
    }

    this.setData({ submitting: true });
    wx.showLoading({ title: this.data.isEdit ? '保存中...' : '提交中...', mask: true });

    try {
      const data = {
        publisherRole: form.publisherRole || '本人',
        phone: form.phone.trim(),
        name: form.name.trim(),
        gender: form.gender,
        age: ageNum,
        housingLocation: form.housingLocation || '本地',
        occupation: form.occupation.trim(),
        income: form.income,
        isPublicSector: form.isPublicSector,
        height: form.height ? parseInt(form.height) : 0,
        weight: form.weight ? parseInt(form.weight) : 0,
        socialAccount: form.socialAccount ? form.socialAccount.trim() : '',
        images: images || [],
        remark: form.remark.trim()
      };

      let res;
      if (this.data.isEdit && this.data.existingNoticeId) {
        res = await api.updateNotice(this.data.existingNoticeId, data);
      } else {
        res = await api.publishNotice(data);
      }

      wx.hideLoading();

      if (res.code === 0) {
        // 发布成功后清空暂存草稿
        if (!this.data.isEdit) {
          wx.removeStorageSync('publishNoticeDraft');
        }

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
      wx.hideLoading();
      wx.showToast({ title: '操作失败，请重试', icon: 'none' });
    }

    this.setData({ submitting: false });
  }
});

