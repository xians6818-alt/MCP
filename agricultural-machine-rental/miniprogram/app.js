// app.js
App({
  globalData: {
    userInfo: null,
    openid: null
  },

  onLaunch() {
    // 初始化云环境
    if (!wx.cloud) {
      console.error('请使用 2.2.3 或以上的基础库以使用云能力');
    } else {
      wx.cloud.init({
        env: 'nongjizulin-0gefgipo1fccdf85',
        traceUser: true
      });
    }

    // 获取openid
    this.getOpenId();
  },

  async getOpenId() {
    try {
      const res = await wx.cloud.callFunction({
        name: 'login'
      });
      this.globalData.openid = res.result.openid;
    } catch (err) {
      console.error('获取openid失败', err);
    }
  }
});
