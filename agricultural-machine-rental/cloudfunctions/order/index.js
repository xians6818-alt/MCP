// 云函数：订单管理
const cloud = require('wx-server-sdk');
cloud.init({ env: 'nongjizulin-0gefgipo1fccdf85' });
const db = cloud.database();

// 校验是否为管理员
function checkAdmin(openid) {
  return db.collection('admin_users')
    .where({ openid })
    .limit(1)
    .get()
    .then(res => {
      return res.data && res.data.length > 0;
    });
}

exports.main = (event, context) => {
  const wxContext = cloud.getWXContext();
  const openid = wxContext.OPENID;
  const { action, data } = event;
  
  // 创建订单
  if (action === 'create') {
    return db.collection('rent_orders').add({
      data: {
        machine_id: data.machine_id,
        machine_name: data.machine_name,
        customer_name: data.customer_name,
        customer_phone: data.customer_phone,
        usage: data.usage_type,
        usage_type: data.usage_type,
        usage_name: data.usage_name,
        unit_price: data.unit_price,
        mu: data.mu,
        total_price: data.total_price,
        location: data.location,
        remark: data.remark || '',
        status: 'pending',  // pending/confirmed/completed/cancelled
        openid: openid,
        created_at: db.serverDate(),
        updated_at: db.serverDate()
      }
    })
    .then(result => {
      return { success: true, id: result._id };
    })
    .catch(err => {
      console.error(err);
      return { success: false, error: err.message };
    });
  }
  
  // 获取用户订单
  if (action === 'getByUser') {
    return db.collection('rent_orders')
      .where({ openid })
      .orderBy('created_at', 'desc')
      .get()
      .then(res => {
        return { success: true, orders: res.data };
      })
      .catch(err => {
        console.error(err);
        return { success: false, error: err.message };
      });
  }
  
  // 获取所有订单（管理员）
  if (action === 'getAll') {
    return checkAdmin(openid)
      .then(isAdmin => {
        if (!isAdmin) {
          return { success: false, message: '无权限操作' };
        }
        return db.collection('rent_orders')
          .orderBy('created_at', 'desc')
          .get();
      })
      .then(res => {
        return { success: true, orders: res.data };
      })
      .catch(err => {
        console.error(err);
        return { success: false, error: err.message };
      });
  }
  
  // 确认订单（管理员）- 库存-1
  if (action === 'confirm') {
    const { order_id } = data;
    return checkAdmin(openid)
      .then(isAdmin => {
        if (!isAdmin) {
          return { success: false, message: '无权限操作' };
        }
        return db.collection('rent_orders').doc(order_id).get();
      })
      .then(order => {
        if (!order.data) {
          return { success: false, message: '订单不存在' };
        }
        // 更新订单状态
        return db.collection('rent_orders').doc(order_id).update({
          data: {
            status: 'confirmed',
            admin_openid: openid,
            confirmed_at: db.serverDate(),
            updated_at: db.serverDate()
          }
        })
        .then(() => {
          // 库存-1
          return db.collection('machines').doc(order.data.machine_id).get();
        })
        .then(machine => {
          if (machine.data) {
            return db.collection('machines').doc(order.data.machine_id).update({
              data: {
                stock: machine.data.stock - 1,
                updated_at: db.serverDate()
              }
            });
          }
          return Promise.resolve();
        })
        .then(() => {
          return { success: true };
        });
      })
      .catch(err => {
        console.error(err);
        return { success: false, error: err.message };
      });
  }
  
  // 完成订单 - 库存+1
  if (action === 'complete') {
    const { order_id } = data;
    return checkAdmin(openid)
      .then(isAdmin => {
        if (!isAdmin) {
          return { success: false, message: '无权限操作' };
        }
        return db.collection('rent_orders').doc(order_id).get();
      })
      .then(order => {
        if (!order.data) {
          return { success: false, message: '订单不存在' };
        }
        return db.collection('rent_orders').doc(order_id).update({
          data: {
            status: 'completed',
            completed_at: db.serverDate(),
            updated_at: db.serverDate()
          }
        })
        .then(() => {
          // 库存+1
          return db.collection('machines').doc(order.data.machine_id).get();
        })
        .then(machine => {
          if (machine.data) {
            return db.collection('machines').doc(order.data.machine_id).update({
              data: {
                stock: machine.data.stock + 1,
                updated_at: db.serverDate()
              }
            });
          }
          return Promise.resolve();
        })
        .then(() => {
          return { success: true };
        });
      })
      .catch(err => {
        console.error(err);
        return { success: false, error: err.message };
      });
  }
  
  // 取消订单
  if (action === 'cancel') {
    const { order_id } = data;
    return db.collection('rent_orders').doc(order_id).update({
      data: {
        status: 'cancelled',
        updated_at: db.serverDate()
      }
    })
    .then(() => {
      return { success: true };
    })
    .catch(err => {
      console.error(err);
      return { success: false, error: err.message };
    });
  }
  
  // 删除订单
  if (action === 'delete') {
    const { order_id } = data;
    return checkAdmin(openid)
      .then(isAdmin => {
        if (!isAdmin) {
          return { success: false, message: '无权限操作' };
        }
        return db.collection('rent_orders').doc(order_id).get();
      })
      .then(order => {
        if (!order.data) {
          return { success: false, message: '订单不存在' };
        }
        // 如果订单已确认，恢复库存
        if (order.data.status === 'confirmed') {
          return db.collection('machines').doc(order.data.machine_id).get()
            .then(machine => {
              if (machine.data) {
                return db.collection('machines').doc(order.data.machine_id).update({
                  data: {
                    stock: machine.data.stock + 1,
                    updated_at: db.serverDate()
                  }
                });
              }
              return Promise.resolve();
            })
            .then(() => {
              // 删除订单
              return db.collection('rent_orders').doc(order_id).remove();
            });
        } else {
          // 直接删除订单
          return db.collection('rent_orders').doc(order_id).remove();
        }
      })
      .then(() => {
        return { success: true };
      })
      .catch(err => {
        console.error(err);
        return { success: false, error: err.message };
      });
  }
  
  return { success: false, message: '未知操作' };
};
