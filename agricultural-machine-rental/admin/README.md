# 农机出租 - 订单管理后台

## 项目概述
网页版订单管理系统，用于查看和处理微信小程序中的租赁订单。

## 功能特性
- 📋 订单列表展示
- 🔍 订单状态筛选（全部/待确认/进行中/已完成/已取消）
- 📝 订单详情查看
- ✅ 修改订单状态
- 📊 今日统计（订单数、总金额）
- 🔄 实时刷新

## 技术方案
- 纯前端 HTML + CSS + JavaScript
- 对接微信云开发 REST API
- 无需后端服务器

## 文件结构
```
admin/
├── index.html      # 管理后台主页
├── style.css       # 样式文件
└── app.js          # 核心逻辑
```

## 微信云开发 API
使用微信云开发的数据库 REST API：
- 环境 ID: `nongjizulin-0gefgipo1fccdf85`
- 集合名: `rent_orders`, `machines`

API 格式: `https://api.weixin.qq.com/tcb/databasequery?access_token=xxx`
