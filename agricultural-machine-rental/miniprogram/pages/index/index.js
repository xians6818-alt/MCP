const db = wx.cloud.database();

Page({
  data: {
    machines: [],
    allMachines: [],
    keyword: '',
    loading: true
  },

  onShow() {
    this.loadMachines();
  },

  async loadMachines() {
    this.setData({ loading: true });
    
    try {
      const res = await db.collection('machines')
        .where({ status: 'available' })
        .get();
      
      this.setData({
        allMachines: res.data,
        machines: res.data,
        loading: false
      });
    } catch (err) {
      console.error('加载失败:', err);
      this.setData({ loading: false });
    }
  },

  onSearch(e) {
    const keyword = e.detail.value;
    const { allMachines } = this.data;
    
    if (!keyword) {
      this.setData({ machines: allMachines, keyword: '' });
      return;
    }
    
    const filtered = allMachines.filter(m => 
      m.name?.includes(keyword) || m.intro?.includes(keyword)
    );
    
    this.setData({ machines: filtered, keyword });
  },

  onMachineTap(e) {
    const id = e.currentTarget.dataset.id;
    
    // 检查是否登录
    const openid = wx.getStorageSync('openid');
    if (!openid) {
      wx.navigateTo({ url: '/pages/login/index' });
      return;
    }
    
    wx.navigateTo({ url: `/pages/rent-apply/index?id=${id}` });
  }
});
