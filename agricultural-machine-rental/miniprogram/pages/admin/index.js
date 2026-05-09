// pages/admin/index.js
const db = wx.cloud.database();
const _ = db.command;

Page({
  data: {
    // 统计数据
    stats: {
      totalOrders: 0,
      pendingOrders: 0,
      totalRevenue: 0
    },
    
    // 待处理订单
    pendingOrders: [],
    
    // 最近订单
    recentOrders: [],
    
    // 权限状态
    isAdmin: false,
    userOpenid: ''
  },

  onLoad() {
    // 检查登录状态和权限
    wx.cloud.callFunction({
      name: 'login',
      success: async res => {
        const openid = res.result.openid;
        console.log('用户openid:', openid);
        this.setData({ userOpenid: openid });

        // 统一使用 admin_users 集合校验管理员身份
        try {
          const adminRes = await db.collection('admin_users')
            .where({ openid })
            .limit(1)
            .get();
          const isAdmin = adminRes.data && adminRes.data.length > 0;
          this.setData({ isAdmin });

          if (!isAdmin) {
            wx.showModal({
              title: '无权限访问',
              content: '您没有管理权限，如需开通请联系管理员',
              showCancel: false,
              success: () => {
                wx.switchTab({ url: '/pages/index/index' });
              }
            });
            return;
          }

          // 有权限，加载数据
          this.loadStats();
          this.loadPendingOrders();
          this.loadRecentOrders();
        } catch (err) {
          console.error('权限校验失败', err);
          wx.showToast({ title: '权限校验失败', icon: 'error' });
        }
      },
      fail: err => {
        console.error('登录失败', err);
        wx.showToast({ title: '请先登录', icon: 'error' });
      }
    });
  },

  onShow() {
    // 每次显示页面时刷新数据（仅当有权限时）
    if (this.data.isAdmin) {
      this.loadStats();
      this.loadPendingOrders();
      this.loadRecentOrders();
    }
  },

  // 加载统计数据
  async loadStats() {
    try {
      // 获取总订单数
      const totalRes = await db.collection('rent_orders').count();
      
      // 获取待处理订单数
      const pendingRes = await db.collection('rent_orders').where({
        status: 'pending'
      }).count();
      
      // 获取总收入
      const revenueRes = await db.collection('rent_orders').where({
        status: _.in(['completed', 'in_progress'])
      }).field({
        total_price: true
      }).get();
      
      let totalRevenue = 0;
      revenueRes.data.forEach(order => {
        totalRevenue += order.total_price || 0;
      });
      
      this.setData({
        'stats.totalOrders': totalRes.total,
        'stats.pendingOrders': pendingRes.total,
        'stats.totalRevenue': totalRevenue
      });
    } catch (err) {
      console.error('加载统计数据失败', err);
    }
  },

  // 加载待处理订单
  async loadPendingOrders() {
    try {
      wx.showLoading({ title: '加载中...' });
      
      const res = await db.collection('rent_orders')
        .where({
          status: 'pending'
        })
        .orderBy('created_at', 'desc')
        .limit(10)
        .get();
      
      const orders = res.data.map(order => {
        order.usageText = this._getUsageText(order.usage);
        return order;
      });
      
      this.setData({ pendingOrders: orders });
    } catch (err) {
      console.error('加载待处理订单失败', err);
      wx.showToast({ title: '加载失败', icon: 'error' });
    } finally {
      wx.hideLoading();
    }
  },

  // 加载最近订单
  async loadRecentOrders() {
    try {
      const res = await db.collection('rent_orders')
        .orderBy('created_at', 'desc')
        .limit(10)
        .get();
      
      const orders = res.data.map(order => {
        order.statusText = this._getStatusText(order.status);
        order.statusClass = this._getStatusClass(order.status);
        order.createdText = this._formatTime(order.created_at);
        return order;
      });
      
      this.setData({ recentOrders: orders });
    } catch (err) {
      console.error('加载最近订单失败', err);
    }
  },

  // 刷新数据
  onRefreshData() {
    wx.showLoading({ title: '刷新中...' });
    Promise.all([
      this.loadStats(),
      this.loadPendingOrders(),
      this.loadRecentOrders()
    ]).finally(() => {
      wx.hideLoading();
      wx.showToast({ title: '已刷新', icon: 'success' });
    });
  },

  // 农机管理
  onManageStock() {
    wx.navigateTo({
      url: '/pages/admin/machine-manage/index'
    });
  },

  // 查看全部订单
  onViewAllOrders() {
    wx.navigateTo({
      url: '/pages/admin/all-orders/index'
    });
  },

  // 联系客户
  onCallPhone(e) {
    const phone = e.currentTarget.dataset.phone;
    wx.makePhoneCall({
      phoneNumber: phone,
      fail: () => {}
    });
  },

  // 打开地图
  onOpenMap(e) {
    const { lat, lng, address } = e.currentTarget.dataset;
    if (!lat || !lng) {
      wx.showToast({ title: '暂无位置信息', icon: 'none' });
      return;
    }
    wx.openLocation({
      latitude: lat,
      longitude: lng,
      name: address || '作业地点',
      address: address || '',
      scale: 15
    });
  },

  // 确认订单
  async onConfirmOrder(e) {
    const order = e.currentTarget.dataset.order;
    
    wx.showModal({
      title: '确认订单',
      content: `确认接受 ${order.customer_name} 的租赁申请？`,
      success: async (res) => {
        if (res.confirm) {
          try {
            wx.showLoading({ title: '处理中...' });
            
            await db.collection('rent_orders').doc(order._id).update({
              data: {
                status: 'confirmed',
                updated_at: db.serverDate()
              }
            });
            
            wx.showToast({ title: '已确认', icon: 'success' });
            this.loadStats();
            this.loadPendingOrders();
            this.loadRecentOrders();
          } catch (err) {
            console.error('确认订单失败', err);
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
          try {
            wx.showLoading({ title: '处理中...' });
            
            await db.collection('rent_orders').doc(order._id).update({
              data: {
                status: 'rejected',
                reject_reason: res.content || '',
                updated_at: db.serverDate()
              }
            });
            
            wx.showToast({ title: '已拒绝', icon: 'success' });
            this.loadStats();
            this.loadPendingOrders();
            this.loadRecentOrders();
          } catch (err) {
            console.error('拒绝订单失败', err);
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
          try {
            wx.showLoading({ title: '处理中...' });
            
            await db.collection('rent_orders').doc(order._id).update({
              data: {
                status: 'in_progress',
                start_time: db.serverDate(),
                updated_at: db.serverDate()
              }
            });
            
            wx.showToast({ title: '已开始作业', icon: 'success' });
            this.loadRecentOrders();
          } catch (err) {
            console.error('开始作业失败', err);
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
          try {
            wx.showLoading({ title: '处理中...' });
            
            await db.collection('rent_orders').doc(order._id).update({
              data: {
                status: 'completed',
                complete_time: db.serverDate(),
                updated_at: db.serverDate()
              }
            });
            
            wx.showToast({ title: '作业已完成', icon: 'success' });
            this.loadStats();
            this.loadRecentOrders();
          } catch (err) {
            console.error('完成作业失败', err);
            wx.showToast({ title: '操作失败', icon: 'error' });
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
    const usageMap = {
      'rice_plow': '水稻翻耕', 'rice_seed': '水稻播种', 'rice_harvest': '水稻收割',
      'wheat_plow': '小麦翻耕', 'wheat_seed': '小麦条播', 'wheat_harvest': '小麦收割',
      'corn_plow': '玉米翻耕', 'corn_seed': '玉米播种', 'corn_harvest': '玉米收割',
      'transport': '农田运输', 'spray': '农药喷洒', 'other': '其他用途'
    };
    return usageMap[usage] || usage || '未指定';
  },

  _getStatusText(status) {
    const statusMap = {
      'pending': '待确认', 'confirmed': '已确认', 'in_progress': '进行中',
      'completed': '已完成', 'rejected': '已拒绝', 'cancelled': '已取消'
    };
    return statusMap[status] || status;
  },

  _getStatusClass(status) {
    const classMap = {
      'pending': 'pending', 'confirmed': 'confirmed', 'in_progress': 'in-progress',
      'completed': 'completed', 'rejected': 'rejected', 'cancelled': 'cancelled'
    };
    return classMap[status] || '';
  },

  _formatTime(timestamp) {
    if (!timestamp) return '';
    const date = timestamp instanceof Date ? timestamp : new Date(timestamp);
    return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
  }
});
