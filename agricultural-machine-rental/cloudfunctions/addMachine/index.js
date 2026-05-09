// 云函数：农机管理
const cloud = require('wx-server-sdk');
cloud.init({ env: 'nongjizulin-0gefgipo1fccdf85' });
const db = cloud.database();

// 默认价格配置
const DEFAULT_PRICING = [
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

exports.main = async (event, context) => {
  const { action, data } = event;
  
  try {
    // 添加农机
    if (action === 'add') {
      const result = await db.collection('machines').add({
        data: {
          name: data.name,
          category: data.category || 'tractor',
          image: data.image || '',
          intro: data.intro || '',
          stock: data.stock || 1,
          pricing: DEFAULT_PRICING,
          status: 'available',
          created_at: db.serverDate(),
          updated_at: db.serverDate()
        }
      });
      return { success: true, id: result._id };
    }
    
    // 初始化示例数据
    if (action === 'init') {
      const machines = [
        {
          name: '东方红LX1504大型拖拉机',
          category: 'tractor',
          image: 'https://6e6f-nongjizulin-0gefgipo1fccdf85-1422712168.tcb.qcloud.la/0d9462d0a68d6f3e7247131e55129b6a.jpg',
          intro: '150马力大型轮式拖拉机，适用于大面积农田作业',
          stock: 3,
          pricing: DEFAULT_PRICING,
          status: 'available'
        },
        {
          name: '雷沃M1804-K轮式拖拉机',
          category: 'tractor',
          image: 'https://6e6f-nongjizulin-0gefgipo1fccdf85-1422712168.tcb.qcloud.la/tractor2.jpg',
          intro: '180马力智能拖拉机，配备自动导航系统',
          stock: 2,
          pricing: DEFAULT_PRICING,
          status: 'available'
        },
        {
          name: '约翰迪尔S760联合收割机',
          category: 'harvester',
          image: 'https://6e6f-nongjizulin-0gefgipo1fccdf85-1422712168.tcb.qcloud.la/harvester1.jpg',
          intro: '高效谷物联合收割机，可收割小麦、玉米、水稻',
          stock: 2,
          pricing: DEFAULT_PRICING,
          status: 'available'
        },
        {
          name: '大疆T50农业无人机',
          category: 'sprayer',
          image: 'https://6e6f-nongjizulin-0gefgipo1fccdf85-1422712168.tcb.qcloud.la/drone1.jpg',
          intro: '智能植保无人机，精准喷洒，高效作业',
          stock: 5,
          pricing: DEFAULT_PRICING,
          status: 'available'
        },
        {
          name: '久保田KX165-5挖掘机',
          category: 'excavator',
          image: 'https://6e6f-nongjizulin-0gefgipo1fccdf85-1422712168.tcb.qcloud.la/excavator.jpg',
          intro: '久保田KX165-5挖掘机，适用于小型工程作业',
          stock: 2,
          pricing: DEFAULT_PRICING,
          status: 'available'
        }
      ];
      
      // 修复：云开发 add() 不支持数组，改为循环逐条插入
      let addedCount = 0;
      for (const machine of machines) {
        await db.collection('machines').add({
          data: {
            ...machine,
            created_at: db.serverDate(),
            updated_at: db.serverDate()
          }
        });
        addedCount++;
      }
      return { success: true, count: addedCount };
    }
    
    // 更新农机库存
    if (action === 'updateStock') {
      const { machineId, stock } = data;

      if (!machineId || stock === undefined || stock < 0) {
        return { success: false, message: '缺少参数或库存不能为负数' };
      }

      try {
        const result = await db.collection('machines').doc(machineId).update({
          data: { stock, updated_at: db.serverDate() }
        });

        return {
          success: true,
          updated: result.stats.updated
        };
      } catch (err) {
        console.error('更新库存失败:', err);
        return { success: false, message: err.message };
      }
    }

    // 更新农机价格
    if (action === 'updatePrice') {
      const { machineId, pricing } = data;
      
      if (!machineId || !pricing) {
        return { success: false, message: '缺少参数' };
      }
      
      try {
        const result = await db.collection('machines').doc(machineId).update({
          data: { pricing, updated_at: db.serverDate() }
        });
        
        return {
          success: true,
          updated: result.stats.updated
        };
      } catch (err) {
        console.error('更新价格失败:', err);
        return { success: false, message: err.message };
      }
    }
    
    return { success: false, message: '未知操作' };
    
  } catch (err) {
    console.error(err);
    return { success: false, error: err.message };
  }
};
