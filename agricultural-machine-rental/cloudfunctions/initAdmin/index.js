// 云函数：初始化管理员集合
const cloud = require('wx-server-sdk');

cloud.init({
  env: 'nongjizulin-0gefgipo1fccdf85'
});

const db = cloud.database();

exports.main = async (event, context) => {
  const wxContext = cloud.getWXContext();
  
  try {
    // 获取当前用户openid
    const openid = wxContext.OPENID;
    
    // 尝试创建集合（如果已存在会报错，我们捕获错误）
    try {
      await db.createCollection('admin_users');
      console.log('admin_users集合创建成功');
    } catch (createErr) {
      // 集合已存在或其他错误，忽略
      console.log('集合创建结果:', createErr.message || '可能已存在');
    }
    
    // 检查是否已有管理员
    let adminCheck;
    try {
      adminCheck = await db.collection('admin_users').count();
    } catch (countErr) {
      return {
        success: false,
        error: '集合不存在，请在云开发控制台手动创建 admin_users 集合'
      };
    }
    
    let result = {
      success: true,
      message: '',
      isFirstAdmin: false,
      currentAdmins: adminCheck.total
    };
    
    // 如果没有管理员，将当前用户设为管理员
    if (adminCheck.total === 0) {
      await db.collection('admin_users').add({
        data: {
          openid: openid,
          created_at: db.serverDate(),
          created_by: 'system_first_admin'
        }
      });
      result.isFirstAdmin = true;
      result.message = '你已成为第一个管理员！';
    } else {
      result.message = '管理员已存在，请联系管理员添加你';
    }
    
    return {
      ...result,
      openid: openid
    };
    
  } catch (err) {
    console.error('initAdmin云函数错误', err);
    return {
      success: false,
      error: err.message || err.errMsg || JSON.stringify(err)
    };
  }
};
