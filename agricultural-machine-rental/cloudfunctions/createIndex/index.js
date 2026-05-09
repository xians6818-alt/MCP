// 云函数入口文件
const cloud = require('wx-server-sdk');

cloud.init({
  env: 'nongjizulin-0gefgipo1fccdf85'
});

const db = cloud.database();

// 云函数入口函数
exports.main = async (event, context) => {
  const { action } = event;
  
  try {
    // 创建索引
    if (action === 'createIndexes') {
      const indexes = [
        // machines 集合索引
        {
          collectionName: 'machines',
          indexes: [
            { name: 'status_idx', fields: { status: 1 } },
            { name: 'category_idx', fields: { category: 1 } },
            { name: 'status_category_idx', fields: { status: 1, category: 1 } },
            { name: 'created_at_idx', fields: { created_at: -1 } }
          ]
        },
        // rent_orders 集合索引
        {
          collectionName: 'rent_orders',
          indexes: [
            { name: 'customer_openid_idx', fields: { customer_openid: 1 } },
            { name: 'status_idx', fields: { status: 1 } },
            { name: 'created_at_idx', fields: { created_at: -1 } }
          ]
        }
      ];
      
      const results = [];
      
      for (const { collectionName, indexes: idxList } of indexes) {
        for (const idx of idxList) {
          try {
            await db.collection(collectionName).indexes().create({
              name: idx.name,
              fields: idx.fields
            });
            results.push({ collection: collectionName, index: idx.name, success: true });
          } catch (createErr) {
            // 索引已存在会报错，忽略
            if (createErr.errCode !== 600005) {
              results.push({ collection: collectionName, index: idx.name, success: false, error: createErr.message });
            } else {
              results.push({ collection: collectionName, index: idx.name, success: true, note: '已存在' });
            }
          }
        }
      }
      
      return { success: true, results };
    }
    
    // 获取现有索引
    if (action === 'listIndexes') {
      const collection = event.collection || 'machines';
      const result = await db.collection(collection).indexes().get();
      return { success: true, indexes: result.indexes, collection };
    }
    
    return { success: false, message: '未知操作' };
    
  } catch (err) {
    console.error(err);
    return { success: false, message: err.message };
  }
};
