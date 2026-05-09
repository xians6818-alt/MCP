const db = wx.cloud.database();

Page({
  data: {
    order: {},
    statusMap: {
      'pending': '待确认',
      'confirmed': '已确认',
      'completed': '已完成',
      'cancelled': '已取消'
    },
    isAdmin: false,
    showActions: false,
    loading: true
  },

  onLoad(options) {
    console.log('订单详情页面接收的参数:', options);
    
    if (!options.id) {
      wx.showToast({ title: '参数错误', icon: 'none' });
      wx.navigateBack();
      return;
    }
    
    this.setData({ 
      isAdmin: wx.getStorageSync('isAdmin') || false
    });
    
    this.loadOrder(options.id);
  },

  async loadOrder(id) {
    this.setData({ loading: true });
    
    try {
      const res = await db.collection('rent_orders').doc(id).get();
      
      if (!res.data) {
        wx.showToast({ title: '订单不存在', icon: 'none' });
        wx.navigateBack();
        return;
      }
      
      const order = {
        ...res.data,
        created_at: this.formatDate(res.data.created_at),
        confirmed_at: this.formatDate(res.data.confirmed_at)
      };
      
      this.setData({ 
        order,
        showActions: true,
        loading: false
      });
      
    } catch (err) {
      console.error('加载订单失败:', err);
      wx.showToast({ title: '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  formatDate(dateObj) {
    if (!dateObj) return '';
    const date = dateObj instanceof Date ? dateObj : new Date(dateObj);
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    const h = String(date.getHours()).padStart(2, '0');
    const min = String(date.getMinutes()).padStart(2, '0');
    return `${y}-${m}-${d} ${h}:${min}`;
  },

  onCallPhone() {
    const { order } = this.data;
    if (order.customer_phone) {
      wx.makePhoneCall({
        phoneNumber: order.customer_phone
      });
    }
  },

  async onConfirm() {
    wx.showModal({
      title: '确认订单',
      content: '确认接受此订单吗？确认后库存将减1。',
      success: async (res) => {
        if (res.confirm) {
          await this.updateOrderStatus('confirm');
        }
      }
    });
  },

  async onComplete() {
    wx.showModal({
      title: '完成作业',
      content: '确认作业已完成吗？完成后库存将恢复。',
      success: async (res) => {
        if (res.confirm) {
          await this.updateOrderStatus('complete');
        }
      }
    });
  },

  async onCancel() {
    wx.showModal({
      title: '取消订单',
      content: '确定要取消此订单吗？',
      success: async (res) => {
        if (res.confirm) {
          await this.updateOrderStatus('cancel');
        }
      }
    });
  },

  async updateOrderStatus(action) {
    wx.showLoading({ title: '处理中...' });
    
    try {
      const result = await wx.cloud.callFunction({
        name: 'order',
        data: {
          action,
          data: { order_id: this.data.order._id }
        }
      });
      
      wx.hideLoading();
      
      if (result.result?.success) {
        wx.showToast({ title: '操作成功', icon: 'success' });
        
        setTimeout(() => {
          wx.navigateBack();
        }, 1500);
      } else {
        wx.showToast({ title: result.result?.message || '操作失败', icon: 'none' });
      }
      
    } catch (err) {
      wx.hideLoading();
      console.error('操作失败:', err);
      wx.showToast({ title: '操作失败', icon: 'none' });
    }
  }
});
