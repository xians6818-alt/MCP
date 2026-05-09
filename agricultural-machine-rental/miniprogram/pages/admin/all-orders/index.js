// pages/admin/all-orders/index.js
const db = wx.cloud.database();
const _ = db.command;

Page({
  data: {
    currentFilter: 'all',
    searchKeyword: '',
    orders: [],
    allOrders: [],
    page: 0,
    pageSize: 10,
    hasMore: true
  },

  onLoad() {
    this.loadOrders();
  },

  onShow() {
    this.loadOrders();
  },

  onPullDownRefresh() {
    this.setData({ page: 0, hasMore: true });
    this.loadOrders().finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  // 切换筛选
  onFilterChange(e) {
    const filter = e.currentTarget.dataset.filter;
    this.setData({ 
      currentFilter: filter, 
      page: 0, 
      hasMore: true,
      orders: []
    });
    this.loadOrders();
  },

  // 加载订单
  async loadOrders() {
    if (!this.data.hasMore) return;
    
    wx.showLoading({ title: '加载中...' });
    
    try {
      const { currentFilter, page, pageSize, orders } = this.data;
      
      let query = db.collection('rent_orders');
      
      if (currentFilter !== 'all') {
        query = query.where({ status: currentFilter });
      }
      
      const res = await query
        .orderBy('created_at', 'desc')
        .skip(page * pageSize)
        .limit(pageSize)
        .get();
      
      const newOrders = res.data.map(order => {
        order.usageText = this._getUsageText(order.usage);
        order.statusText = this._getStatusText(order.status);
        order.statusClass = this._getStatusClass(order.status);
        order.createdText = this._formatTime(order.created_at);
        return order;
      });
      
      const updatedOrders = page === 0 ? newOrders : [...orders, ...newOrders];
      
      this.setData({
        allOrders: updatedOrders,
        orders: updatedOrders,
        hasMore: res.data.length === pageSize
      });
      
      // 应用搜索
      this.filterOrders();
    } catch (err) {
      console.error('加载订单失败', err);
      wx.showToast({ title: '加载失败', icon: 'error' });
    } finally {
      wx.hideLoading();
    }
  },

  // 搜索订单
  onSearch(e) {
    const searchKeyword = e.detail.value;
    this.setData({ searchKeyword });
    this.filterOrders();
  },

  // 筛选订单
  filterOrders() {
    const { allOrders, searchKeyword } = this.data;
    
    let filtered = allOrders;
    
    // 关键词搜索
    if (searchKeyword) {
      filtered = filtered.filter(order => 
        order.customer_name?.includes(searchKeyword) || 
        order.phone?.includes(searchKeyword) || 
        order.address?.includes(searchKeyword) ||
        order.usageText?.includes(searchKeyword)
      );
    }
    
    this.setData({ orders: filtered });
  },

  // 加载更多
  onLoadMore() {
    // 修复：setData 是异步的，必须在回调中调用 loadOrders 才能拿到最新 page 值
    this.setData({ page: this.data.page + 1 }, () => {
      this.loadOrders();
    });
  },

  // 联系客户
  onCallPhone(e) {
    const phone = e.currentTarget.dataset.phone;
    wx.makePhoneCall({ phoneNumber: phone, fail: () => {} });
  },

  // 打开地图
  onOpenMap(e) {
    const { lat, lng, address } = e.currentTarget.dataset;
    if (!lat || !lng) {
      wx.showToast({ title: '暂无位置信息', icon: 'none' });
      return;
    }
    wx.openLocation({ latitude: lat, longitude: lng, name: address, address, scale: 15 });
  },

  // 确认订单
  async onConfirmOrder(e) {
    const order = e.currentTarget.dataset.order;
    wx.showModal({
      title: '确认订单',
      content: `确认接受 ${order.customer_name} 的租赁申请？`,
      success: async (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '处理中...' });
          try {
            await db.collection('rent_orders').doc(order._id).update({
              data: { status: 'confirmed', updated_at: db.serverDate() }
            });
            wx.showToast({ title: '已确认', icon: 'success' });
            this.loadOrders();
          } catch (err) {
            wx.showToast({ title: '操作失败', icon: 'error' });
          } finally {
            wx.hideLoading();
          }
        }
      }
    });
  },

  // 拒绝订单
  onRejectOrder(e) {
    const order = e.currentTarget.dataset.order;
    wx.showModal({
      title: '拒绝订单',
      content: `拒绝 ${order.customer_name} 的租赁申请？`,
      input: 'textarea',
      placeholderText: '请输入拒绝原因（可选）',
      success: async (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '处理中...' });
          try {
            await db.collection('rent_orders').doc(order._id).update({
              data: { status: 'rejected', reject_reason: res.content || '', updated_at: db.serverDate() }
            });
            wx.showToast({ title: '已拒绝', icon: 'success' });
            this.loadOrders();
          } catch (err) {
            wx.showToast({ title: '操作失败', icon: 'error' });
          } finally {
            wx.hideLoading();
          }
        }
      }
    });
  },

  // 开始作业
  async onStartWork(e) {
    const order = e.currentTarget.dataset.order;
    wx.showModal({
      title: '开始作业',
      content: '确认开始此订单的作业？',
      success: async (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '处理中...' });
          try {
            await db.collection('rent_orders').doc(order._id).update({
              data: { status: 'in_progress', start_time: db.serverDate(), updated_at: db.serverDate() }
            });
            wx.showToast({ title: '已开始作业', icon: 'success' });
            this.loadOrders();
          } catch (err) {
            wx.showToast({ title: '操作失败', icon: 'error' });
          } finally {
            wx.hideLoading();
          }
        }
      }
    });
  },

  // 完成作业
  async onCompleteWork(e) {
    const order = e.currentTarget.dataset.order;
    wx.showModal({
      title: '完成作业',
      content: '确认此订单已完成作业？',
      success: async (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '处理中...' });
          try {
            await db.collection('rent_orders').doc(order._id).update({
              data: { status: 'completed', complete_time: db.serverDate(), updated_at: db.serverDate() }
            });
            wx.showToast({ title: '作业已完成', icon: 'success' });
            this.loadOrders();
          } catch (err) {
            wx.showToast({ title: '操作失败', icon: 'error' });
          } finally {
            wx.hideLoading();
          }
        }
      }
    });
  },

  // 删除订单
  async onDeleteOrder(e) {
    const order = e.currentTarget.dataset.order;
    wx.showModal({
      title: '删除订单',
      content: '确定要删除此订单吗？删除后无法恢复。',
      success: async (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '处理中...' });
          try {
            await db.collection('rent_orders').doc(order._id).remove();
            wx.showToast({ title: '删除成功', icon: 'success' });
            this.loadOrders();
          } catch (err) {
            wx.showToast({ title: '删除失败', icon: 'error' });
          } finally {
            wx.hideLoading();
          }
        }
      }
    });
  },

  // 查看详情
  onViewDetail(e) {
    const order = e.currentTarget.dataset.order;
    wx.navigateTo({
      url: `/pages/order-detail/index?order=${encodeURIComponent(JSON.stringify(order))}`
    });
  },

  _getUsageText(usage) {
    const map = {
      'rice_plow': '水稻翻耕', 'rice_seed': '水稻播种', 'rice_harvest': '水稻收割',
      'wheat_plow': '小麦翻耕', 'wheat_seed': '小麦条播', 'wheat_harvest': '小麦收割',
      'corn_plow': '玉米翻耕', 'corn_seed': '玉米播种', 'corn_harvest': '玉米收割',
      'transport': '农田运输', 'spray': '农药喷洒', 'other': '其他用途'
    };
    return map[usage] || usage || '未指定';
  },

  _getStatusText(status) {
    const map = {
      'pending': '待确认', 'confirmed': '已确认', 'in_progress': '进行中',
      'completed': '已完成', 'rejected': '已拒绝', 'cancelled': '已取消'
    };
    return map[status] || status;
  },

  _getStatusClass(status) {
    const map = {
      'pending': 'pending', 'confirmed': 'confirmed', 'in_progress': 'in-progress',
      'completed': 'completed', 'rejected': 'rejected', 'cancelled': 'cancelled'
    };
    return map[status] || '';
  },

  _formatTime(timestamp) {
    if (!timestamp) return '';
    const date = timestamp instanceof Date ? timestamp : new Date(timestamp);
    return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
  }
});
