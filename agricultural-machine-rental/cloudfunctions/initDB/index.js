const cloud = require('wx-server-sdk')
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })

const db = cloud.database()

// 初始化数据库集合和示例数据
exports.main = async (event, context) => {
  const { action } = event

  try {
    // 创建 machines 集合（如果不存在）
    await createCollectionIfNotExist('machines')

    // 创建 orders 集合（如果不存在）
    await createCollectionIfNotExist('orders')

    // 创建 admin_users 集合（如果不存在）
    await createCollectionIfNotExist('admin_users')

    // 如果需要添加示例农机数据
    if (action === 'initMachines') {
      const machines = await db.collection('machines').count()
      if (machines.total === 0) {
        await db.collection('machines').add({
          data: {
            name: '示例联合收割机',
            type: 'harvester',
            image: '/images/machine1.png',
            description: '高性能稻麦联合收割机，适合大面积作业',
            model: '星光-988',
            power: '150马力',
            workingWidth: '2.5米',
            defaultPricing: [
              { type: 'rice_harvest', name: '水稻收割', price: 80 },
              { type: 'wheat_harvest', name: '小麦收割', price: 75 }
            ],
            status: 'available',
            createdAt: db.serverDate(),
            updatedAt: db.serverDate()
          }
        })
      }
    }

    // 如果需要创建默认管理员
    if (action === 'initAdmin') {
      const admins = await db.collection('admin_users').count()
      if (admins.total === 0) {
        await db.collection('admin_users').add({
          data: {
            username: 'admin',
            password: '123456',
            name: '系统管理员',
            createdAt: db.serverDate()
          }
        })
      }
    }

    return { success: true, message: '数据库初始化完成' }
  } catch (err) {
    console.error('初始化失败:', err)
    return { success: false, error: err.message }
  }
}

// 创建集合（如果不存在）
async function createCollectionIfNotExist(name) {
  try {
    await db.createCollection(name)
    console.log(`集合 ${name} 创建成功`)
  } catch (err) {
    // 如果集合已存在，忽略错误
    if (err.errCode !== -502006 || err.message.indexOf('already exist') === -1) {
      console.log(`集合 ${name} 已存在或跳过`)
    }
  }
}
