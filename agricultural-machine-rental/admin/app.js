// ==================== 配置 ====================
const CONFIG = {
  envId: 'nongjizulin-0gefgipo1fccdf85',
  // 云函数名称（需在微信开发者工具中部署）
  functionName: 'adminApi'
};

// ==================== 状态映射 ====================
const STATUS_MAP = {
  'pending': { text: '待确认', class: 'status-pending' },
  'confirmed': { text: '已确认', class: 'status-confirmed' },
  'in_progress': { text: '进行中', class: 'status-in_progress' },
  'completed': { text: '已完成', class: 'status-completed' },
  'cancelled': { text: '已取消', class: 'status-cancelled' }
};

// ==================== 用途映射 ====================
const USAGE_MAP = {
  'rice_plow': '水稻翻耕',
  'rice_seed': '水稻播种',
  'rice_harvest': '水稻收割',
  'wheat_plow': '小麦翻耕',
  'wheat_seed': '小麦条播',
  'wheat_harvest': '小麦收割',
  'corn_plow': '玉米翻耕',
  'corn_seed': '玉米播种',
  'corn_harvest': '玉米收割',
  'transport': '农田运输',
  'spray': '农药喷洒',
  'other': '其他用途'
};

// ==================== 全局状态 ====================
let allOrders = [];
let currentFilter = 'all';
let currentOrder = null;

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
  // 检查是否隐藏演示提示
  checkDemoBanner();
  
  // 检查 URL 中的 token
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.has('access_token')) {
    CONFIG.accessToken = urlParams.get('access_token');
    isDemoMode = false;
  } else {
    // 检查本地存储的 token
    const savedToken = localStorage.getItem('admin_access_token');
    if (savedToken) {
      CONFIG.accessToken = savedToken;
      isDemoMode = false;
    }
  }
  
  // 加载订单数据
  loadOrders();
});

// ==================== 显示配置指南 ====================
function showConfigGuide() {
  const tbody = document.getElementById('ordersTableBody');
  tbody.innerHTML = `
    <tr>
      <td colspan="10">
        <div class="empty-state">
          <div class="icon">🔐</div>
          <p>需要配置访问凭证</p>
          <p style="margin-top: 10px; font-size: 13px; color: #666;">
            请在微信开发者工具中创建一个 adminApi 云函数，<br>
            然后访问以下地址获取帮助：
          </p>
          <div style="margin-top: 16px; padding: 16px; background: #f8f9fa; border-radius: 8px; text-align: left; font-size: 12px;">
            <strong>步骤：</strong><br>
            1. 在 miniprogram 同级目录创建 cloudfunctions/adminApi<br>
            2. 编写云函数查询 rent_orders 集合<br>
            3. 部署云函数<br>
            4. 在下方输入云函数返回的凭证
          </div>
        </div>
      </td>
    </tr>
  `;
  
  // 尝试使用本地存储的凭证
  const savedToken = localStorage.getItem('admin_access_token');
  if (savedToken) {
    CONFIG.accessToken = savedToken;
    loadOrders();
  }
}

// ==================== 加载订单 ====================
async function loadOrders() {
  const tbody = document.getElementById('ordersTableBody');
  tbody.innerHTML = `
    <tr class="loading-row">
      <td colspan="10">
        <div class="loading">
          <span class="loading-spinner"></span>
          加载中...
        </div>
      </td>
    </tr>
  `;

  try {
    // 使用微信云开发 REST API
    const orders = await queryOrders();
    allOrders = orders;
    renderOrders(orders);
    updateStats(orders);
  } catch (error) {
    console.error('加载失败:', error);
    tbody.innerHTML = `
      <tr>
        <td colspan="10">
          <div class="empty-state">
            <div class="icon">❌</div>
            <p>加载失败: ${error.message}</p>
          </div>
        </td>
      </tr>
    `;
  }
}

// ==================== 查询订单 ====================
async function queryOrders() {
  // 如果是演示模式或没有 token，返回演示数据
  if (isDemoMode || !CONFIG.accessToken) {
    isDemoMode = true;
    document.body.classList.add('demo-mode');
    return getMockOrders();
  }
  
  try {
    // 使用 fetch 直接调用微信云开发数据库查询
    const response = await fetch(`https://api.weixin.qq.com/tcb/databasequery?access_token=${CONFIG.accessToken}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        env: CONFIG.envId,
        query: 'db.collection("rent_orders").orderBy("created_at", "desc").limit(100).get()'
      })
    });
    
    const result = await response.json();
    
    if (result.errcode && result.errcode !== 0) {
      throw new Error(result.errmsg || 'API 请求失败');
    }
    
    return result.data || [];
  } catch (error) {
    // 如果出错，回退到演示模式
    console.log('API 请求失败，使用演示数据:', error.message);
    isDemoMode = true;
    document.body.classList.add('demo-mode');
    return getMockOrders();
  }
}

// ==================== 演示数据 ====================
function getMockOrders() {
  return [
    {
      _id: 'demo001',
      order_no: 'RD20260416001',
      machine_name: '东方红LX1504大型拖拉机',
      customer_name: '张三',
      customer_phone: '138****1234',
      rent_type: 'day',
      rent_days: 3,
      land_area: 50,
      usage: 'wheat_plow',
      location: { address: '山东省济南市历下区' },
      total_price: 2400,
      status: 'pending',
      created_at: { value: new Date().toISOString() },
      remark: '需要开具发票'
    },
    {
      _id: 'demo002',
      order_no: 'RD20260415002',
      machine_name: '约翰迪尔S760联合收割机',
      customer_name: '李四',
      customer_phone: '139****5678',
      rent_type: 'hour',
      rent_hours: 8,
      land_area: 100,
      usage: 'rice_harvest',
      location: { address: '河南省郑州市中原区' },
      total_price: 1440,
      status: 'completed',
      created_at: { value: '2026-04-15T10:30:00Z' },
      remark: ''
    },
    {
      _id: 'demo003',
      order_no: 'RD20260414003',
      machine_name: '大疆T50农业无人机',
      customer_name: '王五',
      customer_phone: '136****9012',
      rent_type: 'day',
      rent_days: 2,
      land_area: 200,
      usage: 'spray',
      location: { address: '江苏省徐州市铜山区' },
      total_price: 1000,
      status: 'confirmed',
      created_at: { value: '2026-04-14T14:20:00Z' },
      remark: '病虫害防治'
    },
    {
      _id: 'demo004',
      order_no: 'RD20260413004',
      machine_name: '小麦精密播种机',
      customer_name: '赵六',
      customer_phone: '137****3456',
      rent_type: 'day',
      rent_days: 1,
      land_area: 80,
      usage: 'wheat_seed',
      location: { address: '安徽省宿州市埇桥区' },
      total_price: 400,
      status: 'in_progress',
      created_at: { value: '2026-04-13T08:00:00Z' },
      remark: '要求上午到达'
    }
  ];
}

// ==================== 渲染订单列表 ====================
function renderOrders(orders) {
  const tbody = document.getElementById('ordersTableBody');
  const filteredCount = document.getElementById('filteredCount');
  
  // 筛选
  let filteredOrders = orders;
  if (currentFilter !== 'all') {
    filteredOrders = orders.filter(order => order.status === currentFilter);
  }
  
  filteredCount.textContent = filteredOrders.length;
  
  if (filteredOrders.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="10">
          <div class="empty-state">
            <div class="icon">📭</div>
            <p>暂无订单</p>
          </div>
        </td>
      </tr>
    `;
    return;
  }
  
  tbody.innerHTML = filteredOrders.map(order => {
    const statusInfo = STATUS_MAP[order.status] || { text: order.status, class: '' };
    const usageText = USAGE_MAP[order.usage] || order.usage || '-';
    const createdTime = order.created_at?.value 
      ? new Date(order.created_at.value).toLocaleString('zh-CN')
      : (order.created_at?.$date ? new Date(order.created_at.$date).toLocaleString('zh-CN') : '-');
    
    return `
      <tr>
        <td><strong>${order.order_no || '-'}</strong></td>
        <td>
          <div>${order.customer_name || '-'}</div>
          <div style="font-size: 11px; color: #888;">${order.customer_phone || '-'}</div>
        </td>
        <td>${order.machine_name || '-'}</td>
        <td>
          <div>${order.rent_type === 'day' ? '按天租' : '按时租'}</div>
          <div style="font-size: 11px; color: #667eea;">${usageText}</div>
        </td>
        <td>
          <div>${order.rent_days ? order.rent_days + '天' : (order.rent_hours ? order.rent_hours + '小时' : '-')}</div>
          <div style="font-size: 11px; color: #888;">${order.land_area || '-'}亩</div>
        </td>
        <td><strong style="color: #e74c3c;">¥${order.total_price || 0}</strong></td>
        <td style="max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${order.location?.address || order.location_address || '-'}">
          ${order.location?.address || order.location_address || '-'}
        </td>
        <td><span class="status-badge ${statusInfo.class}">${statusInfo.text}</span></td>
        <td style="font-size: 11px;">${createdTime}</td>
        <td>
          <button class="action-btn" onclick="showOrderDetail('${order._id}')">查看</button>
        </td>
      </tr>
    `;
  }).join('');
}

// ==================== 更新统计 ====================
function updateStats(orders) {
  const totalOrders = orders.length;
  const totalAmount = orders.reduce((sum, order) => sum + (order.total_price || 0), 0);
  const pendingOrders = orders.filter(order => order.status === 'pending').length;
  const completedOrders = orders.filter(order => order.status === 'completed').length;
  
  document.getElementById('totalOrders').textContent = totalOrders;
  document.getElementById('totalAmount').textContent = '¥' + totalAmount.toLocaleString();
  document.getElementById('pendingOrders').textContent = pendingOrders;
  document.getElementById('completedOrders').textContent = completedOrders;
}

// ==================== 筛选订单 ====================
function filterOrders(status) {
  currentFilter = status;
  
  // 更新按钮状态
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.status === status);
  });
  
  renderOrders(allOrders);
}

// ==================== 显示订单详情 ====================
function showOrderDetail(orderId) {
  const order = allOrders.find(o => o._id === orderId);
  if (!order) return;
  
  currentOrder = order;
  
  const statusInfo = STATUS_MAP[order.status] || { text: order.status, class: '' };
  const usageText = USAGE_MAP[order.usage] || order.usage || '-';
  const createdTime = order.created_at?.value 
    ? new Date(order.created_at.value).toLocaleString('zh-CN')
    : (order.created_at?.$date ? new Date(order.created_at.$date).toLocaleString('zh-CN') : '-');
  
  const modalBody = document.getElementById('modalBody');
  modalBody.innerHTML = `
    <div class="detail-grid">
      <div class="detail-item">
        <div class="detail-label">订单号</div>
        <div class="detail-value">${order.order_no || '-'}</div>
      </div>
      <div class="detail-item">
        <div class="detail-label">当前状态</div>
        <div class="detail-value">
          <span class="status-badge ${statusInfo.class}">${statusInfo.text}</span>
        </div>
      </div>
      <div class="detail-item">
        <div class="detail-label">客户姓名</div>
        <div class="detail-value">${order.customer_name || '-'}</div>
      </div>
      <div class="detail-item">
        <div class="detail-label">联系电话</div>
        <div class="detail-value">
          <a href="tel:${order.customer_phone}" style="color: #667eea;">${order.customer_phone || '-'}</a>
        </div>
      </div>
      <div class="detail-item">
        <div class="detail-label">农机名称</div>
        <div class="detail-value">${order.machine_name || '-'}</div>
      </div>
      <div class="detail-item">
        <div class="detail-label">租赁方式</div>
        <div class="detail-value">${order.rent_type === 'day' ? '按天租' : '按时租'}</div>
      </div>
      <div class="detail-item">
        <div class="detail-label">作业用途</div>
        <div class="detail-value" style="color: #667eea; font-weight: 600;">${usageText}</div>
      </div>
      <div class="detail-item">
        <div class="detail-label">租赁时长</div>
        <div class="detail-value">${order.rent_days ? order.rent_days + '天' : (order.rent_hours ? order.rent_hours + '小时' : '-')}</div>
      </div>
      <div class="detail-item">
        <div class="detail-label">作业面积</div>
        <div class="detail-value">${order.land_area || '-'} 亩</div>
      </div>
      <div class="detail-item">
        <div class="detail-label">订单金额</div>
        <div class="detail-value" style="color: #e74c3c; font-size: 18px;">¥${order.total_price || 0}</div>
      </div>
      <div class="detail-item">
        <div class="detail-label">下单时间</div>
        <div class="detail-value">${createdTime}</div>
      </div>
      <div class="detail-item full-width">
        <div class="detail-label">作业地址</div>
        <div class="detail-value">${order.location?.address || order.location_address || '-'}</div>
      </div>
      ${order.location?.latitude ? `
      <div class="detail-item full-width">
        <div class="detail-label">GPS坐标</div>
        <div class="detail-value">
          <a href="https://uri.amap.com/marker?position=${order.location.longitude},${order.location.latitude}" 
             target="_blank" style="color: #667eea;">
            查看地图 (${order.location.latitude}, ${order.location.longitude})
          </a>
        </div>
      </div>
      ` : ''}
      <div class="detail-item full-width">
        <div class="detail-label">备注信息</div>
        <div class="detail-value">${order.remark || '无'}</div>
      </div>
      <div class="detail-item full-width">
        <div class="detail-label">修改状态</div>
        <select class="status-select" id="statusSelect">
          <option value="pending" ${order.status === 'pending' ? 'selected' : ''}>待确认</option>
          <option value="confirmed" ${order.status === 'confirmed' ? 'selected' : ''}>已确认</option>
          <option value="in_progress" ${order.status === 'in_progress' ? 'selected' : ''}>进行中</option>
          <option value="completed" ${order.status === 'completed' ? 'selected' : ''}>已完成</option>
          <option value="cancelled" ${order.status === 'cancelled' ? 'selected' : ''}>已取消</option>
        </select>
      </div>
    </div>
  `;
  
  document.getElementById('orderModal').classList.add('show');
}

// ==================== 关闭弹窗 ====================
function closeModal() {
  document.getElementById('orderModal').classList.remove('show');
  currentOrder = null;
}

// ==================== 更新订单状态 ====================
async function updateOrderStatus() {
  if (!currentOrder) return;
  
  const newStatus = document.getElementById('statusSelect').value;
  const orderId = currentOrder._id;
  
  // 演示模式下直接更新本地数据
  if (isDemoMode) {
    const order = allOrders.find(o => o._id === orderId);
    if (order) {
      order.status = newStatus;
      closeModal();
      renderOrders(allOrders);
      updateStats(allOrders);
      showToast('状态已更新（演示模式）', 'success');
    }
    return;
  }
  
  try {
    // 调用云函数更新状态
    const response = await fetch(`https://api.weixin.qq.com/tcb/databaseupdate?access_token=${CONFIG.accessToken}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        env: CONFIG.envId,
        query: `db.collection("rent_orders").doc("${orderId}").update({ data: { status: "${newStatus}" } })`
      })
    });
    
    const result = await response.json();
    
    if (result.errcode && result.errcode !== 0) {
      throw new Error(result.errmsg || 'API 请求失败');
    }
    
    // 更新本地数据
    const orderIndex = allOrders.findIndex(o => o._id === orderId);
    if (orderIndex !== -1) {
      allOrders[orderIndex].status = newStatus;
    }
    
    closeModal();
    renderOrders(allOrders);
    updateStats(allOrders);
    showToast('状态更新成功', 'success');
    
  } catch (error) {
    console.error('更新失败:', error);
    showToast('更新失败: ' + error.message, 'error');
  }
}

// ==================== 演示模式控制 ====================
let isDemoMode = true;

function switchToRealMode() {
  const token = prompt('请输入微信云开发的 access_token：\n\n获取方式：\n1. 登录微信公众平台\n2. 开发管理 → 开发设置\n3. 获取 AppID 和 AppSecret\n4. 调用接口获取 access_token\n\n或者直接在微信开发者工具中运行云函数获取数据。');
  
  if (token) {
    CONFIG.accessToken = token;
    localStorage.setItem('admin_access_token', token);
    isDemoMode = false;
    document.getElementById('configBanner').classList.add('hidden');
    document.body.classList.remove('demo-mode');
    loadOrders();
    showToast('已切换到真实数据模式', 'success');
  }
}

function hideBanner() {
  document.getElementById('configBanner').classList.add('hidden');
  localStorage.setItem('hide_demo_banner', 'true');
}

function checkDemoBanner() {
  if (localStorage.getItem('hide_demo_banner') === 'true') {
    document.getElementById('configBanner').classList.add('hidden');
  }
}

// ==================== Toast 提示 ====================
function showToast(message, type = '') {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.className = 'toast show ' + type;
  
  setTimeout(() => {
    toast.classList.remove('show');
  }, 3000);
}

// ==================== 键盘事件 ====================
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeModal();
  }
});

// 点击遮罩关闭
document.getElementById('orderModal').addEventListener('click', (e) => {
  if (e.target.id === 'orderModal') {
    closeModal();
  }
});

// ==================== 农机管理功能 ====================
let allMachines = [];
let currentTab = 'orders';
let editingMachine = null;

// 切换标签页
function switchTab(tab) {
  currentTab = tab;
  
  // 更新按钮状态
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tab);
  });
  
  // 显示/隐藏内容
  document.querySelector('.orders-section').style.display = tab === 'orders' ? 'block' : 'none';
  document.querySelector('.filter-bar').style.display = tab === 'orders' ? 'flex' : 'none';
  document.getElementById('machinesSection').style.display = tab === 'machines' ? 'block' : 'none';
  
  if (tab === 'machines') {
    loadMachines();
  }
}

// 加载农机数据
async function loadMachines() {
  const grid = document.getElementById('machinesGrid');
  grid.innerHTML = `
    <div class="loading">
      <span class="loading-spinner"></span>
      加载中...
    </div>
  `;
  
  try {
    const machines = await queryMachines();
    allMachines = machines;
    renderMachines(machines);
  } catch (error) {
    console.error('加载农机失败:', error);
    grid.innerHTML = `
      <div class="empty-state">
        <div class="icon">❌</div>
        <p>加载失败: ${error.message}</p>
      </div>
    `;
  }
}

// 查询农机
async function queryMachines() {
  if (isDemoMode || !CONFIG.accessToken) {
    return getMockMachines();
  }
  
  try {
    const response = await fetch(`https://api.weixin.qq.com/tcb/databasequery?access_token=${CONFIG.accessToken}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        env: CONFIG.envId,
        query: 'db.collection("machines").get()'
      })
    });
    
    const result = await response.json();
    
    if (result.errcode && result.errcode !== 0) {
      throw new Error(result.errmsg || 'API 请求失败');
    }
    
    return result.data || [];
  } catch (error) {
    console.log('API 请求失败，使用演示数据:', error.message);
    return getMockMachines();
  }
}

// 演示数据 - 农机
function getMockMachines() {
  return [
    {
      _id: 'mock001',
      name: '东方红LX1504大型拖拉机',
      category: 'tractor',
      stock: 3,
      price_per_day: 800,
      price_per_hour: 100,
      status: 'available'
    },
    {
      _id: 'mock002',
      name: '雷沃M1804-K轮式拖拉机',
      category: 'tractor',
      stock: 2,
      price_per_day: 1000,
      price_per_hour: 120,
      status: 'available'
    },
    {
      _id: 'mock003',
      name: '约翰迪尔S760联合收割机',
      category: 'harvester',
      stock: 1,
      price_per_day: 1500,
      price_per_hour: 180,
      status: 'available'
    },
    {
      _id: 'mock004',
      name: '洋马YH1180全喂入收割机',
      category: 'harvester',
      stock: 0,
      price_per_day: 1200,
      price_per_hour: 150,
      status: 'available'
    },
    {
      _id: 'mock005',
      name: '大疆T50农业无人机',
      category: 'sprayer',
      stock: 5,
      price_per_day: 500,
      price_per_hour: 80,
      status: 'available'
    },
    {
      _id: 'mock006',
      name: '小麦精密播种机',
      category: 'seeder',
      stock: 4,
      price_per_day: 400,
      price_per_hour: 60,
      status: 'available'
    }
  ];
}

// 渲染农机列表
function renderMachines(machines) {
  const grid = document.getElementById('machinesGrid');
  const count = document.getElementById('machinesCount');
  count.textContent = machines.length;
  
  if (machines.length === 0) {
    grid.innerHTML = `
      <div class="empty-state">
        <div class="icon">🚜</div>
        <p>暂无农机</p>
      </div>
    `;
    return;
  }
  
  const categoryMap = {
    'tractor': '拖拉机',
    'harvester': '收割机',
    'seeder': '播种机',
    'sprayer': '喷雾机'
  };
  
  grid.innerHTML = machines.map(machine => `
    <div class="machine-card ${machine.stock <= 0 ? 'no-stock' : ''}">
      <div class="machine-header">
        <span class="machine-category">${categoryMap[machine.category] || machine.category}</span>
        <span class="machine-status ${machine.status === 'available' ? 'available' : 'rented'}">
          ${machine.status === 'available' ? '可租' : '已出租'}
        </span>
      </div>
      <div class="machine-name">${machine.name}</div>
      <div class="machine-price">
        <span>¥${machine.price_per_day}/天</span>
        <span class="price-sep">|</span>
        <span>¥${machine.price_per_hour}/时</span>
      </div>
      <div class="machine-stock ${machine.stock <= 0 ? 'no-stock' : ''}">
        <span class="stock-label">库存：</span>
        <span class="stock-value ${machine.stock <= 0 ? 'warning' : ''}">${machine.stock !== undefined ? machine.stock : '—'}</span>
        <span class="stock-unit">台</span>
      </div>
      <div class="machine-actions">
        <button class="btn btn-sm btn-primary" onclick="showStockModal('${machine._id}')">
          设置库存
        </button>
      </div>
    </div>
  `).join('');
}

// 显示库存编辑弹窗
function showStockModal(machineId) {
  const machine = allMachines.find(m => m._id === machineId);
  if (!machine) return;
  
  editingMachine = machine;
  
  const body = document.getElementById('stockModalBody');
  body.innerHTML = `
    <div class="stock-edit-form">
      <div class="stock-machine-name">${machine.name}</div>
      <div class="stock-current">
        当前库存：<span class="${machine.stock <= 0 ? 'warning' : ''}">${machine.stock !== undefined ? machine.stock : 0}</span> 台
      </div>
      <div class="stock-input-group">
        <label>新库存数量：</label>
        <input type="number" id="newStockInput" value="${machine.stock !== undefined ? machine.stock : 0}" min="0" max="99">
      </div>
    </div>
  `;
  
  document.getElementById('stockModal').classList.add('show');
}

// 关闭库存弹窗
function closeStockModal() {
  document.getElementById('stockModal').classList.remove('show');
  editingMachine = null;
}

// 更新农机库存
async function updateMachineStock() {
  if (!editingMachine) return;
  
  const newStock = parseInt(document.getElementById('newStockInput').value, 10);
  
  if (isNaN(newStock) || newStock < 0) {
    showToast('请输入有效的库存数量', 'error');
    return;
  }
  
  // 演示模式：更新本地数据
  if (isDemoMode) {
    const machine = allMachines.find(m => m._id === editingMachine._id);
    if (machine) {
      machine.stock = newStock;
    }
    closeStockModal();
    renderMachines(allMachines);
    showToast('库存已更新（演示模式）', 'success');
    return;
  }
  
  try {
    const response = await fetch(`https://api.weixin.qq.com/tcb/databaseupdate?access_token=${CONFIG.accessToken}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        env: CONFIG.envId,
        query: `db.collection("machines").doc("${editingMachine._id}").update({ data: { stock: ${newStock}, updated_at: db.serverDate() } })`
      })
    });
    
    const result = await response.json();
    
    if (result.errcode && result.errcode !== 0) {
      throw new Error(result.errmsg || 'API 请求失败');
    }
    
    // 更新本地数据
    const machine = allMachines.find(m => m._id === editingMachine._id);
    if (machine) {
      machine.stock = newStock;
    }
    
    closeStockModal();
    renderMachines(allMachines);
    showToast('库存更新成功', 'success');
    
  } catch (error) {
    console.error('更新库存失败:', error);
    showToast('更新失败: ' + error.message, 'error');
  }
}

// 键盘事件 - 库存弹窗
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeStockModal();
  }
});

// 点击遮罩关闭 - 库存弹窗
document.getElementById('stockModal').addEventListener('click', (e) => {
  if (e.target.id === 'stockModal') {
    closeStockModal();
  }
});
