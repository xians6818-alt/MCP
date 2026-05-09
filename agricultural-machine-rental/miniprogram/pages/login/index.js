const db = wx.cloud.database();

Page({
  data: {
    loading: false
  },

  onLoad() {
    // 检查是否已登录
    const openid = wx.getStorageSync('openid');
    if (openid) {
      wx.switchTab({ url: '/pages/my-orders/index' });
    }
  },

  async onLogin() {
    if (this.data.loading) return;
    
    this.setData({ loading: true });
    
    try {
      // 调用login云函数
      const result = await wx.cloud.callFunction({ name: 'login' });
      
      if (result.result && result.result.success) {
        const { openid, isAdmin } = result.result;
        
        // 保存登录信息
        wx.setStorageSync('openid', openid);
        wx.setStorageSync('isAdmin', isAdmin);
        
        // 如果是管理员且没有初始化，初始化为第一个管理员
        if (isAdmin) {
          await wx.cloud.callFunction({ 
            name: 'admin', 
            data: { action: 'initFirstAdmin' }
          });
        }
        
        wx.showToast({ title: '登录成功', icon: 'success' });
        
        setTimeout(() => {
          wx.switchTab({ url: '/pages/my-orders/index' });
        }, 1500);
      } else {
        wx.showToast({ title: '登录失败', icon: 'none' });
      }
    } catch (err) {
      console.error('登录失败:', err);
      wx.showModal({
        title: '登录失败',
        content: err.message || '请检查网络连接',
        showCancel: false
      });
    } finally {
      this.setData({ loading: false });
    }
  }
});
