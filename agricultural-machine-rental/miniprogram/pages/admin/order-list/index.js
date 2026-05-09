Page({
  data: {
    orders: [],
    allOrders: [],
    statusFilter: '',
    searchKeyword: '',
    loading: true,
    statusMap: {
      'pending': '待确认',
      'confirmed': '已确认',
      'completed': '已完成',
      'cancelled': '已取消'
    }
  },

  onShow() {
    this.loadOrders();
  },

  async loadOrders() {
    this.setData({ loading: true });
    
    try {
      const result = await wx.cloud.callFunction({
        name: 'order',
        data: { action: 'getAll' }
      });
      
      let orders = result.result?.orders || [];
      
      // 格式化时间
      orders = orders.map(o => ({
        ...o,
        created_at: this.formatDate(o.created_at)
      }));
      
      this.setData({
        allOrders: orders,
        loading: false
      });
      
      this.filterOrders();
    } catch (err) {
      console.error('加载失败:', err);
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

  filterOrders() {
    const { allOrders, statusFilter, searchKeyword } = this.data;
    let orders = allOrders;
    
    if (statusFilter) {
      orders = orders.filter(o => o.status === statusFilter);
    }
    
    if (searchKeyword) {
      orders = orders.filter(o => 
        o.customer_name?.includes(searchKeyword) || 
        o.customer_phone?.includes(searchKeyword) || 
        o.location?.address?.includes(searchKeyword) ||
        o.usage_name?.includes(searchKeyword)
      );
    }
    
    this.setData({ orders });
  },

  onSearch(e) {
    const searchKeyword = e.detail.value;
    this.setData({ searchKeyword });
    this.filterOrders();
  },

  onFilterStatus(e) {
    const status = e.currentTarget.dataset.status;
    this.setData({ statusFilter: status }, () => {
      this.filterOrders();
    });
  },

  onOrderTap(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: `/pages/order-detail/index?id=${id}` });
  },

  preventBubble(e) {
    e.stopPropagation && e.stopPropagation();
  },

  async onConfirmOrder(e) {
    const id = e.currentTarget.dataset.id;
    
    wx.showModal({
      title: '确认订单',
      content: '确认接受此订单？库存将减1',
      success: async (res) => {
        if (res.confirm) {
          await this.updateOrder(id, 'confirm');
        }
      }
    });
  },

  async onCompleteOrder(e) {
    const id = e.currentTarget.dataset.id;
    
    wx.showModal({
      title: '完成订单',
      content: '确认作业已完成？库存将恢复',
      success: async (res) => {
        if (res.confirm) {
          await this.updateOrder(id, 'complete');
        }
      }
    });
  },

  async onCancelOrder(e) {
    const id = e.currentTarget.dataset.id;
    
    wx.showModal({
      title: '取消订单',
      content: '确定要取消此订单吗？',
      success: async (res) => {
        if (res.confirm) {
          await this.updateOrder(id, 'cancel');
        }
      }
    });
  },

  async updateOrder(id, action) {
    wx.showLoading({ title: '处理中...' });
    
    try {
      const result = await wx.cloud.callFunction({
        name: 'order',
        data: { action, data: { order_id: id } }
      });
      
      wx.hideLoading();
      
      if (result.result?.success) {
        wx.showToast({ title: '操作成功', icon: 'success' });
        this.loadOrders();
      } else {
        wx.showToast({ title: '操作失败', icon: 'none' });
      }
    } catch (err) {
      wx.hideLoading();
      wx.showToast({ title: '操作失败', icon: 'none' });
    }
  },

  async onDeleteOrder(e) {
    const id = e.currentTarget.dataset.id;
    
    wx.showModal({
      title: '删除订单',
      content: '确定要删除此订单吗？删除后无法恢复。',
      success: async (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '处理中...' });
          
          try {
            const result = await wx.cloud.callFunction({
              name: 'order',
              data: { action: 'delete', data: { order_id: id } }
            });
            
            wx.hideLoading();
            
            if (result.result?.success) {
              wx.showToast({ title: '删除成功', icon: 'success' });
              this.loadOrders();
            } else {
              wx.showToast({ title: '删除失败', icon: 'none' });
            }
          } catch (err) {
            wx.hideLoading();
            wx.showToast({ title: '删除失败', icon: 'none' });
          }
        }
      }
    });
  }
});
