const db = wx.cloud.database();

Page({
  data: {
    machines: [],
    allMachines: [],
    searchKeyword: '',
    loading: true,
    showPriceModal: false,
    currentMachine: null,
    currentIndex: -1,
    currentPricing: [],
    showAddModal: false,
    addMachineForm: {
      name: '',
      category: '',
      image: '',
      intro: '',
      stock: 1
    }
  },

  onShow() {
    this.loadMachines();
  },

  async loadMachines() {
    this.setData({ loading: true });
    
    try {
      // 加载所有机器数据
      const res = await db.collection('machines')
        .orderBy('created_at', 'desc')
        .get();
      
      console.log('加载的农机数据:', res.data);
      
      // 打印每个农机的价格数据
      res.data.forEach((machine, index) => {
        console.log(`农机 ${index + 1} 名称:`, machine.name);
        console.log(`农机 ${index + 1} 价格字段(pricing):`, machine.pricing);
        console.log(`农机 ${index + 1} 价格字段(defaultPricing):`, machine.defaultPricing);
      });
      
      // 如果有机器数据，测试第一个机器
      if (res.data.length > 0) {
        const firstMachine = res.data[0];
        const testRes = await db.collection('machines').doc(firstMachine._id).get();
        console.log('测试机器数据:', testRes.data);
        console.log('测试机器价格:', testRes.data.pricing);
      }
      
      this.setData({ 
        allMachines: res.data,
        machines: res.data,
        loading: false
      });
      
      // 应用搜索
      this.filterMachines();
    } catch (err) {
      console.error('加载失败:', err);
      wx.showToast({ title: '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  onSearch(e) {
    const searchKeyword = e.detail.value;
    this.setData({ searchKeyword });
    this.filterMachines();
  },

  filterMachines() {
    const { allMachines, searchKeyword } = this.data;
    
    let filtered = allMachines;
    
    // 关键词搜索
    if (searchKeyword) {
      filtered = filtered.filter(m => 
        m.name?.includes(searchKeyword) || m.intro?.includes(searchKeyword) || m.category?.includes(searchKeyword)
      );
    }
    
    this.setData({ machines: filtered });
  },

  onInitData() {
    wx.showModal({
      title: '初始化数据',
      content: '将添加示例农机数据，确定吗？',
      success: async (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '初始化中...' });
          
          try {
            const result = await wx.cloud.callFunction({
              name: 'addMachine',
              data: { action: 'init' }
            });
            
            wx.hideLoading();
            
            if (result.result?.success) {
              wx.showToast({ title: `已添加 ${result.result.count} 台农机`, icon: 'success' });
              this.loadMachines();
            } else {
              wx.showToast({ title: '初始化失败', icon: 'none' });
            }
          } catch (err) {
            wx.hideLoading();
            wx.showToast({ title: '初始化失败', icon: 'none' });
          }
        }
      }
    });
  },

  async onMinusStock(e) {
    const { id, stock } = e.currentTarget.dataset;
    if (stock <= 0) return;
    
    await this.updateStock(id, stock - 1);
  },

  async onPlusStock(e) {
    const { id, stock } = e.currentTarget.dataset;
    await this.updateStock(id, stock + 1);
  },

  async updateStock(id, newStock) {
    try {
      // 通过云函数更新，避免客户端权限限制
      const result = await wx.cloud.callFunction({
        name: 'addMachine',
        data: {
          action: 'updateStock',
          data: { machineId: id, stock: newStock }
        }
      });

      if (result.result?.success) {
        // 更新本地数据
        const machines = this.data.machines.map(m => {
          if (m._id === id) m.stock = newStock;
          return m;
        });
        this.setData({ machines });
        wx.showToast({ title: '已更新', icon: 'success', duration: 800 });
      } else {
        console.error('更新库存失败:', result.result?.message);
        wx.showToast({ title: '更新失败', icon: 'none' });
      }
    } catch (err) {
      console.error('更新库存失败:', err);
      wx.showToast({ title: '更新失败', icon: 'none' });
    }
  },

  onConfigPrice(e) {
    const index = e.currentTarget.dataset.index;
    const machine = this.data.machines[index];
    
    this.setData({
      showPriceModal: true,
      currentMachine: machine,
      currentIndex: index,
      currentPricing: JSON.parse(JSON.stringify(machine.defaultPricing || machine.pricing || []))
    });
  },

  onCloseModal() {
    this.setData({
      showPriceModal: false,
      currentMachine: null,
      currentIndex: -1,
      currentPricing: []
    });
  },

  preventBubble() {},

  onPriceInput(e) {
    const type = e.currentTarget.dataset.type;
    const price = parseFloat(e.detail.value) || 0;
    
    const pricing = this.data.currentPricing.map(p => {
      if (p.type === type) p.price = price;
      return p;
    });
    
    this.setData({ currentPricing: pricing });
  },

  async onSavePrice() {
    const { currentMachine, currentPricing, currentIndex } = this.data;
    
    if (!currentMachine) return;
    
    console.log('当前机器:', currentMachine);
    console.log('要保存的价格:', currentPricing);
    console.log('当前索引:', currentIndex);
    console.log('机器ID:', currentMachine._id);
    
    wx.showLoading({ title: '保存中...' });
    
    try {
      // 使用云函数更新价格
      const result = await wx.cloud.callFunction({
        name: 'addMachine',
        data: {
          action: 'updatePrice',
          data: {
            machineId: currentMachine._id,
            pricing: currentPricing
          }
        }
      });
      
      console.log('云函数更新结果:', result);
      
      if (result.result?.success) {
        // 更新后获取机器数据，验证是否更新成功
        const updatedData = await db.collection('machines').doc(currentMachine._id).get();
        console.log('更新后的机器数据:', updatedData.data);
        console.log('更新后的价格:', updatedData.data.pricing);
        
        // 更新本地数据
        const machines = this.data.machines.map((m, i) => {
          if (i === currentIndex) {
            m.pricing = currentPricing;
          }
          return m;
        });
        
        this.setData({ machines, showPriceModal: false });
        console.log('本地数据已更新');
        wx.showToast({ title: '保存成功', icon: 'success' });
      } else {
        console.error('保存失败:', result.result?.message);
        wx.showToast({ title: '保存失败', icon: 'none' });
      }
    } catch (err) {
      console.error('保存失败:', err);
      wx.showToast({ title: '保存失败', icon: 'none' });
    } finally {
      wx.hideLoading();
    }
  },

  // 打开添加农机弹窗
  onAddMachine() {
    this.setData({
      showAddModal: true,
      addMachineForm: {
        name: '',
        category: '',
        image: '',
        intro: '',
        stock: 1
      }
    });
  },

  // 关闭添加农机弹窗
  onCloseAddModal() {
    this.setData({
      showAddModal: false,
      addMachineForm: {
        name: '',
        category: '',
        image: '',
        intro: '',
        stock: 1
      }
    });
  },

  // 处理添加农机表单输入
  onAddMachineInput(e) {
    const field = e.currentTarget.dataset.field;
    const value = e.detail.value;
    
    this.setData({
      [`addMachineForm.${field}`]: field === 'stock' ? parseInt(value) || 1 : value
    });
  },

  // 提交添加农机表单
  async onSubmitAddMachine() {
    const { addMachineForm } = this.data;
    
    // 验证表单
    if (!addMachineForm.name) {
      wx.showToast({ title: '请输入农机名称', icon: 'none' });
      return;
    }
    
    if (!addMachineForm.category) {
      wx.showToast({ title: '请输入农机类别', icon: 'none' });
      return;
    }
    
    if (!addMachineForm.image) {
      wx.showToast({ title: '请输入图片URL', icon: 'none' });
      return;
    }
    
    if (!addMachineForm.intro) {
      wx.showToast({ title: '请输入农机介绍', icon: 'none' });
      return;
    }
    
    if (!addMachineForm.stock || addMachineForm.stock <= 0) {
      wx.showToast({ title: '请输入正确的库存数量', icon: 'none' });
      return;
    }
    
    wx.showLoading({ title: '添加中...' });
    
    try {
      // 默认价格配置
      const defaultPricing = [
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
      
      // 直接在前端添加农机
      const result = await db.collection('machines').add({
        data: {
          name: addMachineForm.name,
          category: addMachineForm.category,
          image: addMachineForm.image,
          intro: addMachineForm.intro,
          stock: addMachineForm.stock,
          pricing: defaultPricing,
          status: 'available',
          created_at: db.serverDate(),
          updated_at: db.serverDate()
        }
      });
      
      wx.hideLoading();
      wx.showToast({ title: '添加成功', icon: 'success' });
      
      // 关闭弹窗并重新加载农机列表
      this.onCloseAddModal();
      this.loadMachines();
    } catch (err) {
      wx.hideLoading();
      console.error('添加失败:', err);
      wx.showToast({ title: '添加失败', icon: 'none' });
    }
  },

  // 删除农机
  onDeleteMachine(e) {
    const id = e.currentTarget.dataset.id;
    
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这台农机吗？删除后无法恢复。',
      success: async (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '删除中...' });
          
          try {
            // 直接在前端删除农机
            await db.collection('machines').doc(id).remove();
            
            wx.hideLoading();
            wx.showToast({ title: '删除成功', icon: 'success' });
            
            // 重新加载农机列表
            this.loadMachines();
          } catch (err) {
            wx.hideLoading();
            console.error('删除失败:', err);
            wx.showToast({ title: '删除失败', icon: 'none' });
          }
        }
      }
    });
  }
});
