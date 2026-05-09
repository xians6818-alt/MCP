const db = wx.cloud.database();

Page({
  data: {
    machine: {},
    pricingOptions: [],
    selectedPricing: null,
    formData: {
      customer_name: '',
      customer_phone: '',
      usage_type: '',
      usage_name: '',
      unit_price: 0,
      mu: '',
      location: '',
      remark: ''
    },
    estimatedPrice: 0,
    isSubmitting: false
  },

  onLoad(options) {
    if (!options.id) {
      wx.showToast({ title: '参数错误', icon: 'none' });
      wx.navigateBack();
      return;
    }
    
    this.loadMachine(options.id);
  },

  async loadMachine(id) {
    wx.showLoading({ title: '加载中...' });
    
    try {
      const res = await db.collection('machines').doc(id).get();
      
      console.log('加载的农机数据:', res.data);
      console.log('加载的价格配置:', res.data.pricing);
      
      if (!res.data) {
        wx.showToast({ title: '农机不存在', icon: 'none' });
        wx.navigateBack();
        return;
      }
      
      // 获取定价配置
      let pricingOptions = res.data.pricing || [];
      
      console.log('处理后的价格配置:', pricingOptions);
      
      // 如果为空，使用默认值
      if (!pricingOptions || pricingOptions.length === 0) {
        pricingOptions = [
          { type: 'rice_plow', name: '水稻翻耕', price: 50 },
          { type: 'rice_seed', name: '水稻播种', price: 45 },
          { type: 'rice_harvest', name: '水稻收割', price: 60 },
          { type: 'wheat_plow', name: '小麦翻耕', price: 45 },
          { type: 'wheat_seed', name: '小麦条播', price: 40 },
          { type: 'wheat_harvest', name: '小麦收割', price: 55 },
          { type: 'corn_plow', name: '玉米翻耕', price: 45 },
          { type: 'corn_seed', name: '玉米播种', price: 40 },
          { type: 'corn_harvest', name: '玉米收割', price: 55 },
          { type: 'transport', name: '农田运输', price: 40 },
          { type: 'spray', name: '农药喷洒', price: 35 },
          { type: 'other', name: '其他用途', price: 50 }
        ];
        console.log('使用默认价格配置:', pricingOptions);
      }
      
      this.setData({
        machine: res.data,
        pricingOptions
      });
      
    } catch (err) {
      console.error('加载农机失败:', err);
      wx.showToast({ title: '加载失败', icon: 'none' });
    } finally {
      wx.hideLoading();
    }
  },

  onInputChange(e) {
    const field = e.currentTarget.dataset.field;
    const value = e.detail.value;
    
    this.setData({
      [`formData.${field}`]: value
    }, () => {
      this.calcPrice();
    });
  },

  onUsageSelect(e) {
    const { type, name, price } = e.currentTarget.dataset;
    
    this.setData({
      'formData.usage_type': type,
      'formData.usage_name': name,
      'formData.unit_price': price,
      selectedPricing: { type, name, price }
    }, () => {
      this.calcPrice();
    });
  },

  calcPrice() {
    const { mu, unit_price } = this.data.formData;
    
    if (mu && unit_price) {
      const price = parseFloat(mu) * parseFloat(unit_price);
      this.setData({ estimatedPrice: price.toFixed(2) });
    } else {
      this.setData({ estimatedPrice: 0 });
    }
  },

  async onSubmit() {
    const { machine, formData, estimatedPrice, isSubmitting } = this.data;
    
    if (isSubmitting) return;
    
    // 验证表单
    if (!formData.customer_name) {
      wx.showToast({ title: '请输入联系人姓名', icon: 'none' });
      return;
    }
    
    if (!formData.customer_phone || formData.customer_phone.length !== 11) {
      wx.showToast({ title: '请输入正确的联系电话', icon: 'none' });
      return;
    }
    
    if (!formData.usage_type) {
      wx.showToast({ title: '请选择业务类型', icon: 'none' });
      return;
    }
    
    if (!formData.mu || parseFloat(formData.mu) <= 0) {
      wx.showToast({ title: '请输入作业亩数', icon: 'none' });
      return;
    }
    
    if (!formData.location) {
      wx.showToast({ title: '请输入作业地址', icon: 'none' });
      return;
    }
    
    this.setData({ isSubmitting: true });
    
    try {
      const result = await wx.cloud.callFunction({
        name: 'order',
        data: {
          action: 'create',
          data: {
            machine_id: machine._id,
            machine_name: machine.name,
            customer_name: formData.customer_name,
            customer_phone: formData.customer_phone,
            usage_type: formData.usage_type,
            usage_name: formData.usage_name,
            unit_price: formData.unit_price,
            mu: parseFloat(formData.mu),
            total_price: parseFloat(estimatedPrice),
            location: formData.location,
            remark: formData.remark
          }
        }
      });
      
      if (result.result?.success) {
        wx.showToast({ title: '提交成功', icon: 'success' });
        
        setTimeout(() => {
          wx.switchTab({ url: '/pages/my-orders/index' });
        }, 1500);
      } else {
        wx.showToast({ title: '提交失败', icon: 'none' });
        this.setData({ isSubmitting: false });
      }
      
    } catch (err) {
      console.error('提交失败:', err);
      wx.showToast({ title: '提交失败', icon: 'none' });
      this.setData({ isSubmitting: false });
    }
  }
});
