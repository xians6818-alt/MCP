// 云函数：管理员管理
const cloud = require('wx-server-sdk');
cloud.init({ env: 'nongjizulin-0gefgipo1fccdf85' });
const db = cloud.database();

exports.main = async (event, context) => {
  const wxContext = cloud.getWXContext();
  const openid = wxContext.OPENID;
  const { action, data } = event;
  
  try {
    // 成为第一个管理员（初始化）
    if (action === 'initFirstAdmin') {
      const count = await db.collection('admin_users').count();
      if (count.total === 0) {
        await db.collection('admin_users').add({
          data: {
            openid: openid,
            created_at: db.serverDate(),
            created_by: 'system'
          }
        });
        return { success: true, isFirstAdmin: true };
      }
      return { success: true, isFirstAdmin: false };
    }
    
    // 获取所有管理员
    if (action === 'getAll') {
      const res = await db.collection('admin_users').get();
      return { success: true, admins: res.data };
    }
    
    // 添加管理员（需要管理员权限）
    if (action === 'add') {
      // 验证调用者是否是管理员
      const check = await db.collection('admin_users').where({ openid }).count();
      if (check.total === 0) {
        return { success: false, message: '无权限' };
      }
      
      const { target_openid } = data;
      if (!target_openid) {
        return { success: false, message: '缺少openid' };
      }
      
      // 检查是否已是管理员
      const exist = await db.collection('admin_users').where({ openid: target_openid }).count();
      if (exist.total > 0) {
        return { success: false, message: '已是管理员' };
      }
      
      await db.collection('admin_users').add({
        data: {
          openid: target_openid,
          created_at: db.serverDate(),
          created_by: openid
        }
      });
      
      return { success: true };
    }
    
    // 移除管理员（需要管理员权限）
    if (action === 'remove') {
      const check = await db.collection('admin_users').where({ openid }).count();
      if (check.total === 0) {
        return { success: false, message: '无权限' };
      }
      
      const { target_openid } = data;
      await db.collection('admin_users').where({ openid: target_openid }).remove();
      return { success: true };
    }
    
    // 检查是否是管理员
    if (action === 'check') {
      const check = await db.collection('admin_users').where({ openid }).count();
      return { success: true, isAdmin: check.total > 0 };
    }
    
    return { success: false, message: '未知操作' };
    
  } catch (err) {
    console.error(err);
    return { success: false, error: err.message };
  }
};
