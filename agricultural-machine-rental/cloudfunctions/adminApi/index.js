// 云函数入口文件 - 管理后台 API
const cloud = require('wx-server-sdk');

cloud.init({
  env: 'nongjizulin-0gefgipo1fccdf85'
});

const db = cloud.database();
const MAX_LIMIT = 100;

// 云函数入口函数
exports.main = async (event, context) => {
  const { action, data } = event;
  
  try {
    // 获取所有订单（支持筛选）
    if (action === 'getOrders') {
      const { status, limit = MAX_LIMIT } = data || {};
      
      let query = db.collection('rent_orders').orderBy('created_at', 'desc');
      
      if (status && status !== 'all') {
        query = query.where({ status });
      }
      
      const result = await query.limit(limit).get();
      
      return {
        success: true,
        data: result.data,
        total: result.data.length
      };
    }
    
    // 获取订单详情
    if (action === 'getOrderDetail') {
      const { orderId } = data;
      
      if (!orderId) {
        return { success: false, message: '缺少订单ID' };
      }
      
      const result = await db.collection('rent_orders').doc(orderId).get();
      
      if (!result.data) {
        return { success: false, message: '订单不存在' };
      }
      
      return { success: true, data: result.data };
    }
    
    // 更新订单状态
    if (action === 'updateStatus') {
      const { orderId, status } = data;
      
      if (!orderId || !status) {
        return { success: false, message: '缺少参数' };
      }
      
      const result = await db.collection('rent_orders').doc(orderId).update({
        data: {
          status,
          updated_at: db.serverDate()
        }
      });
      
      return {
        success: true,
        updated: result.stats.updated
      };
    }
    
    // 获取统计数据
    if (action === 'getStats') {
      const countResult = await db.collection('rent_orders').count();
      const pendingResult = await db.collection('rent_orders').where({ status: 'pending' }).count();
      const completedResult = await db.collection('rent_orders').where({ status: 'completed' }).count();
      
      // 计算总收入（需要聚合查询，这里简化为获取已完成订单）
      const completedOrders = await db.collection('rent_orders')
        .where({ status: 'completed' })
        .field({ total_price: true })
        .limit(1000)
        .get();
      
      const totalRevenue = completedOrders.data.reduce((sum, order) => sum + (order.total_price || 0), 0);
      
      return {
        success: true,
        data: {
          totalOrders: countResult.total,
          pendingOrders: pendingResult.total,
          completedOrders: completedResult.total,
          totalRevenue
        }
      };
    }
    
    // 获取农机列表（用于关联显示）
    if (action === 'getMachines') {
      const result = await db.collection('machines').get();
      
      return {
        success: true,
        data: result.data
      };
    }
    
    // 更新农机价格
    if (action === 'updateMachinePrice') {
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
    
    // 删除重复农机记录
    if (action === 'deleteDuplicateMachines') {
      try {
        // 获取所有农机记录
        const result = await db.collection('machines').get();
        const machines = result.data;
        
        // 按照名称和图片URL分组，找出重复的记录
        const machineGroups = {};
        
        machines.forEach(machine => {
          // 使用名称和图片URL作为分组键
          const key = `${machine.name}_${machine.image}`;
          if (!machineGroups[key]) {
            machineGroups[key] = [];
          }
          machineGroups[key].push(machine);
        });
        
        // 统计需要删除的记录
        let deletedCount = 0;
        
        // 遍历每个分组，保留第一条记录，删除其他重复的记录
        for (const key in machineGroups) {
          const group = machineGroups[key];
          if (group.length > 1) {
            // 保留第一条记录，删除其他记录
            for (let i = 1; i < group.length; i++) {
              await db.collection('machines').doc(group[i]._id).remove();
              deletedCount++;
            }
          }
        }
        
        return {
          success: true,
          deletedCount,
          message: `成功删除 ${deletedCount} 条重复记录`
        };
      } catch (err) {
        console.error('删除重复记录失败:', err);
        return { success: false, message: err.message };
      }
    }
    
    return { success: false, message: '未知操作' };
    
  } catch (err) {
    console.error(err);
    return { success: false, message: err.message };
  }
};
