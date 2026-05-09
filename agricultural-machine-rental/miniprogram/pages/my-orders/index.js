const db = wx.cloud.database();

Page({
  data: {
    openid: '',
    isAdmin: false,
    orders: [],
    allOrders: [],
    admins: [],
    statusFilter: '',
    loading: true,
    showAdminModal: false,
    newAdminOpenid: '',
    statusMap: {
      'pending': '待确认',
      'confirmed': '已确认',
      'completed': '已完成',
      'cancelled': '已取消'
    }
  },

  onLoad() {
    const openid = wx.getStorageSync('openid');
    const isAdmin = wx.getStorageSync('isAdmin');
    
    if (!openid) {
      wx.navigateTo({ url: '/pages/login/index' });
      return;
    }
    
    this.setData({ openid, isAdmin });
    // 修复：不在 onLoad 中调用 loadData，由 onShow 统一触发，避免重复请求
  },

  onShow() {
    this.loadData();
  },

  async loadData() {
    this.setData({ loading: true });
    
    try {
      // 获取用户订单
      const orderRes = await wx.cloud.callFunction({
        name: 'order',
        data: { action: 'getByUser' }
      });
      
      let orders = orderRes.result?.orders || [];
      
      // 格式化时间
      orders = orders.map(o => ({
        ...o,
        created_at: this.formatDate(o.created_at)
      }));
      
      this.setData({ 
        allOrders: orders,
        orders,
        loading: false
      });
      
      this.filterOrders();
      
      // 管理员获取更多信息
      if (this.data.isAdmin) {
        await this.loadAdminData();
      }
    } catch (err) {
      console.error('加载失败:', err);
      this.setData({ loading: false });
    }
  },

  async loadAdminData() {
    try {
      // 获取管理员列表
      const adminRes = await wx.cloud.callFunction({
        name: 'admin',
        data: { action: 'getAll' }
      });
      
      if (adminRes.result?.success) {
        this.setData({ admins: adminRes.result.admins || [] });
      }
    } catch (err) {
      console.error('加载管理员数据失败:', err);
    }
  },

  formatDate(dateObj) {
    if (!dateObj) return '';
    const date = dateObj instanceof Date ? dateObj : new Date(dateObj);
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  },

  filterOrders() {
    const { allOrders, statusFilter } = this.data;
    let orders = allOrders;
    
    if (statusFilter) {
      orders = orders.filter(o => o.status === statusFilter);
    }
    
    this.setData({ orders });
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

  goToMachineManage() {
    wx.navigateTo({ url: '/pages/admin/machine-manage/index' });
  },

  goToAllOrders() {
    wx.navigateTo({ url: '/pages/admin/order-list/index' });
  },

  toggleAdminModal() {
    this.setData({ 
      showAdminModal: !this.data.showAdminModal,
      newAdminOpenid: ''
    });
  },

  onAdminOpenidInput(e) {
    this.setData({ newAdminOpenid: e.detail.value });
  },

  async onAddAdmin() {
    const { newAdminOpenid } = this.data;
    
    if (!newAdminOpenid) {
      wx.showToast({ title: '请输入openid', icon: 'none' });
      return;
    }
    
    try {
      wx.showLoading({ title: '添加中...' });
      
      const result = await wx.cloud.callFunction({
        name: 'admin',
        data: { 
          action: 'add',
          data: { target_openid: newAdminOpenid }
        }
      });
      
      wx.hideLoading();
      
      if (result.result?.success) {
        wx.showToast({ title: '添加成功', icon: 'success' });
        this.toggleAdminModal();
        this.loadAdminData();
      } else {
        wx.showToast({ title: result.result?.message || '添加失败', icon: 'none' });
      }
    } catch (err) {
      wx.hideLoading();
      wx.showToast({ title: '添加失败', icon: 'none' });
    }
  },

  async onRemoveAdmin(e) {
    const openid = e.currentTarget.dataset.openid;
    
    wx.showModal({
      title: '确认移除',
      content: '确定要移除该管理员吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await wx.cloud.callFunction({
              name: 'admin',
              data: { 
                action: 'remove',
                data: { target_openid: openid }
              }
            });
            
            wx.showToast({ title: '已移除', icon: 'success' });
            this.loadAdminData();
          } catch (err) {
            wx.showToast({ title: '移除失败', icon: 'none' });
          }
        }
      }
    });
  },

  preventBubble() {},

  onLogout() {
    wx.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          wx.clearStorageSync();
          wx.navigateTo({ url: '/pages/login/index' });
        }
      }
    });
  }
});
