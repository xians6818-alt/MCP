# 农机出租微信小程序

一个基于微信云开发的农机租赁服务平台。

## 功能特性

- 🏠 **首页**：展示农机列表，支持分类筛选和搜索
- 🚜 **农机详情**：查看农机详细信息和价格
- 📝 **租赁申请**：填写客户信息、租赁时长、位置信息
- 📍 **位置获取**：调用微信定位 + 腾讯地图逆地理编码
- 📋 **订单管理**：查看订单列表和订单详情
- ✅ **订单状态**：待确认 → 已确认 → 进行中 → 已完成

## 技术栈

- **前端**：微信小程序原生开发
- **后端**：微信云开发 (Cloud Functions + Cloud Database)
- **定位**：微信 `wx.getLocation` + 腾讯位置服务

## 项目结构

```
agricultural-machine-rental/
├── miniprogram/                 # 小程序前端代码
│   ├── pages/
│   │   ├── index/               # 首页 - 农机列表
│   │   ├── machine-detail/      # 农机详情页
│   │   ├── rent-apply/          # 租赁申请页
│   │   ├── my-orders/           # 我的订单
│   │   └── order-detail/        # 订单详情
│   ├── app.js                   # 应用入口
│   ├── app.json                 # 应用配置
│   └── app.wxss                 # 全局样式
├── cloudfunctions/              # 云函数
│   ├── login/                  # 登录云函数
│   └── addMachine/             # 添加农机/初始化数据
└── project.config.json         # 项目配置
```

## 数据库设计

### machines 集合（农机列表）

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 农机名称 |
| category | string | 分类：tractor/harvester/seeder/sprayer |
| image | string | 图片URL |
| intro | string | 简介 |
| price_per_day | number | 日租金 |
| price_per_hour | number | 时租金 |
| min_hours | number | 最小租赁时长 |
| specs | object | 规格参数 |
| status | string | 状态：available/rented/maintenance |
| created_at | Date | 创建时间 |
| updated_at | Date | 更新时间 |

### rent_orders 集合（租赁订单）

| 字段 | 类型 | 说明 |
|------|------|------|
| order_no | string | 订单号 |
| machine_id | string | 农机ID |
| machine_name | string | 农机名称 |
| customer_name | string | 联系人姓名 |
| customer_phone | string | 联系电话 |
| rent_type | string | 租赁类型：day/hour |
| rent_days | number | 租赁天数 |
| rent_hours | number | 租赁小时数 |
| land_area | number | 地块亩数 |
| location | object | 位置信息 |
| status | string | 订单状态 |
| total_price | number | 总费用 |
| remark | string | 备注 |
| created_at | Date | 创建时间 |
| updated_at | Date | 更新时间 |

## 快速开始

### 1. 配置云环境

1. 登录 [微信公众平台](https://mp.weixin.qq.com/)
2. 开通云开发能力
3. 获取云环境 ID
4. 修改以下文件中的云环境ID：
   - `miniprogram/app.js` 中的 `env`
   - `cloudfunctions/login/index.js` 中的 `env`
   - `cloudfunctions/addMachine/index.js` 中的 `env`

### 2. 配置腾讯地图Key（可选）

如需使用位置逆地理编码功能：
1. 申请 [腾讯位置服务](https://lbs.qq.com/) Key
2. 修改 `pages/rent-apply/index.js` 中的 `key` 值

### 3. 上传云函数

```bash
# 在微信开发者工具中右键 cloudfunctions 文件夹
# 选择 "上传并部署"
```

### 4. 初始化数据

在控制台执行以下代码初始化示例农机数据：

```javascript
// 在小程序中调用
wx.cloud.callFunction({
  name: 'addMachine',
  data: { action: 'init' }
}).then(console.log);
```

### 5. 配置权限

在微信云开发控制台设置集合权限：

- `machines`：全部可读，仅管理员可写
- `rent_orders`：创建者可读写

## 使用说明

### 开发调试

1. 使用微信开发者工具导入项目
2. 填入 AppID
3. 勾选"不校验合法域名"
4. 开启云开发控制台

### 添加新农机

```javascript
wx.cloud.callFunction({
  name: 'addMachine',
  data: {
    action: 'add',
    data: {
      name: '新农机名称',
      category: 'tractor',
      image: '图片URL',
      intro: '简介',
      price_per_day: 500,
      price_per_hour: 80
    }
  }
});
```

## 页面预览

| 页面 | 说明 |
|------|------|
| 首页 | 农机卡片列表 + 分类筛选 + 搜索 |
| 租赁申请 | 表单 + 位置获取 + 费用预览 |
| 我的订单 | 订单列表 + 状态筛选 |
| 订单详情 | 完整订单信息 + 操作按钮 |

## License

MIT
