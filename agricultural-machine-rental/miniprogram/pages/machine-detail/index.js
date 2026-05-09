// pages/machine-detail/index.js
const app = getApp();

Page({
  data: {
    machine: {
      _id: '',
      name: '',
      category: '',
      categoryText: '',
      image: '',
      intro: '',
      price_per_day: 0,
      price_per_hour: 0,
      min_hours: 0,
      specs: []
    }
  },

  onLoad(options) {
    // 从页面参数获取农机信息
    if (options.machine) {
      try {
        const machine = JSON.parse(decodeURIComponent(options.machine));
        this.formatMachineData(machine);
      } catch (e) {
        console.error('解析农机信息失败', e);
        wx.showToast({ title: '数据加载失败', icon: 'error' });
      }
    } else if (options.id) {
      // 通过ID从数据库获取
      this.loadMachineById(options.id);
    }
  },

  // 格式化农机数据
  formatMachineData(machine) {
    const categoryMap = {
      'tractor': '拖拉机',
      'harvester': '收割机',
      'seeder': '播种机',
      'sprayer': '喷雾机'
    };

    // 转换规格参数为数组格式
    const specs = [];
    if (machine.specs) {
      const specLabels = {
        'power': '动力',
        'weight': '重量',
        'type': '类型',
        'capacity': '容量',
        'rows': '行数',
        'width': '作业宽度',
        'load': '载药量'
      };
      
      for (const key in machine.specs) {
        specs.push({
          label: specLabels[key] || key,
          value: machine.specs[key]
        });
      }
    }

    this.setData({
      machine: {
        ...machine,
        categoryText: categoryMap[machine.category] || machine.category,
        specs: specs
      }
    });
  },

  // 通过ID加载农机信息
  async loadMachineById(id) {
    wx.showLoading({ title: '加载中...' });
    
    try {
      const db = wx.cloud.database();
      const res = await db.collection('machines').doc(id).get();
      
      this.formatMachineData(res.data);
    } catch (err) {
      console.error('加载农机信息失败', err);
      wx.showToast({ title: '加载失败', icon: 'error' });
    } finally {
      wx.hideLoading();
    }
  },

  // 图片加载失败处理
  onImageError() {
    const machine = this.data.machine;
    machine.image = 'https://6e6f-nongjizulin-0gefgipo1fccdf85-1422712168.tcb.qcloud.la/0d9462d0a68d6f3e7247131e55129b6a.jpg';
    this.setData({ machine });
  },

  // 点击租赁按钮
  onRentTap() {
    const machine = this.data.machine;
    
    // 跳转到租赁申请页
    wx.navigateTo({
      url: `/pages/rent-apply/index?machine=${encodeURIComponent(JSON.stringify(machine))}`
    });
  }
});
