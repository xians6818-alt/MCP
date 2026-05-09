// 云函数：登录
const cloud = require('wx-server-sdk');
cloud.init({ env: 'nongjizulin-0gefgipo1fccdf85' });
const db = cloud.database();

exports.main = async (event, context) => {
  const wxContext = cloud.getWXContext();
  const openid = wxContext.OPENID;
  
  try {
    // 检查是否是管理员
    const adminCheck = await db.collection('admin_users').where({ openid }).count();
    const isAdmin = adminCheck.total > 0;
    
    // 如果是管理员，获取管理员列表
    let admins = [];
    if (isAdmin) {
      const adminList = await db.collection('admin_users').get();
      admins = adminList.data.map(a => ({
        openid: a.openid,
        created_at: a.created_at
      }));
    }
    
    return {
      success: true,
      openid,
      isAdmin,
      admins
    };
  } catch (err) {
    console.error('login云函数错误:', err);
    return {
      success: false,
      error: err.message
    };
  }
};
