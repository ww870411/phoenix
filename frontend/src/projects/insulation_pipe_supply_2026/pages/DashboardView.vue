<template>
  <div class="tube-page-root">
    <!-- 大连洁净能源集团生产系统统一页头 -->
    <AppHeader />
    
    <main class="tube-page-main container">
      <!-- 统一面包屑导航 -->
      <Breadcrumbs :items="breadcrumbItems" />
      
      <!-- 看板顶栏总控区 -->
      <header class="topbar">
        <div>
          <h2>全局数据看板</h2>
          <p class="sub">
            物流供应链全链路（计划-发货-到货-接收-库管-使用）的宏观指标、可视化大盘与预警扫描中心。
          </p>
        </div>
        <div class="topbar-actions">
          <!-- 核心日期上下文显示 -->
          <div class="date-context-badge">
            <span class="date-context-item">
              <span class="dot green"></span>
              业务日期 (show_date)：<strong>{{ configSummary?.show_date || '—' }}</strong>
            </span>
            <span class="date-context-item">
              <span class="dot blue"></span>
              计划起点 (plan_start_date)：<strong>{{ configSummary?.plan_start_date || '—' }}</strong>
            </span>
          </div>
          <button class="btn ghost" type="button" @click="goProjectPages">返回功能页</button>
          <button class="btn primary" type="button" :disabled="loading || loadingSummary" @click="refreshAllData">
            {{ (loading || loadingSummary) ? '刷新中...' : '刷新看板数据' }}
          </button>
        </div>
      </header>

      <p v-if="errorMessage" class="page-error">{{ errorMessage }}</p>

      <!-- 第一区：四大全局核心指标 HSL 磨砂卡片大盘 -->
      <section class="stats-grid">
        <!-- 卡片1：采购与覆盖率 -->
        <div class="stat-card">
          <div class="stat-card__icon">📐</div>
          <div class="stat-card__label">项目总设计量 / 计划采购</div>
          <div class="stat-card__value">
            {{ formatQty(kpi.design) }} <span class="stat-card__unit">m</span>
            <span class="stat-card__separator">/</span>
            <span class="highlight-blue">{{ formatQty(kpi.purchase) }}</span> <span class="stat-card__unit">m</span>
          </div>
          <div class="stat-card__progress">
            <div class="progress-bar-bg">
              <div class="progress-bar-fill blue" :style="{ width: getPercent(kpi.purchase, kpi.design) + '%' }"></div>
            </div>
            <div class="progress-bar-text">计划采购率：{{ getPercent(kpi.purchase, kpi.design) }}%</div>
          </div>
        </div>

        <!-- 卡片2：已发货与在途资产 -->
        <div class="stat-card">
          <div class="stat-card__icon">🚚</div>
          <div class="stat-card__label">累计已发货 / 当前在途待到货</div>
          <div class="stat-card__value">
            {{ formatQty(kpi.shipped) }} <span class="stat-card__unit">m</span>
            <span class="stat-card__separator">/</span>
            <span class="highlight-cyan">{{ formatQty(kpi.pendingArrival) }}</span> <span class="stat-card__unit">m</span>
          </div>
          <div class="stat-card__progress">
            <div class="progress-bar-bg">
              <div class="progress-bar-fill cyan" :style="{ width: getPercent(kpi.pendingArrival, kpi.shipped) + '%' }"></div>
            </div>
            <div class="progress-bar-text">在途占比：{{ getPercent(kpi.pendingArrival, kpi.shipped) }}%</div>
          </div>
        </div>

        <!-- 卡片3：现场库存与累计使用 -->
        <div class="stat-card">
          <div class="stat-card__icon">⛺</div>
          <div class="stat-card__label">全局现场总库存 / 累计实际使用</div>
          <div class="stat-card__value">
            <span class="highlight-green">{{ formatQty(kpi.inventory) }}</span> <span class="stat-card__unit">m</span>
            <span class="stat-card__separator">/</span>
            {{ formatQty(kpi.usage) }} <span class="stat-card__unit">m</span>
          </div>
          <div class="stat-card__progress">
            <div class="progress-bar-bg">
              <div class="progress-bar-fill green" :style="{ width: getPercent(kpi.usage, kpi.inventory + kpi.usage) + '%' }"></div>
            </div>
            <div class="progress-bar-text">耗用转化率：{{ getPercent(kpi.usage, kpi.inventory + kpi.usage) }}%</div>
          </div>
        </div>

        <!-- 卡片4：未来三日缺口与硬缺口 -->
        <div class="stat-card" :class="{ 'alert-pulsing': kpi.hardGap > 0 }">
          <div class="stat-card__icon">⚠️</div>
          <div class="stat-card__label">三日计划硬缺口 / 三日净缺口</div>
          <div class="stat-card__value">
            <span class="highlight-red" :class="{ 'blink': kpi.hardGap > 0 }">{{ formatQty(kpi.hardGap) }}</span> <span class="stat-card__unit">m</span>
            <span class="stat-card__separator">/</span>
            <span class="highlight-orange">{{ formatQty(kpi.netGap) }}</span> <span class="stat-card__unit">m</span>
          </div>
          <div class="stat-card__progress">
            <div class="progress-bar-bg">
              <div class="progress-bar-fill red" :style="{ width: getPercent(kpi.hardGap, kpi.hardGap + kpi.netGap || 1) + '%' }"></div>
            </div>
            <div class="progress-bar-text">
              <template v-if="kpi.hardGap > 0">🚨 警报：现场库存不足以维持施工！</template>
              <template v-else-if="kpi.netGap > 0">提示：在途能抵扣，但仍需组织新发货</template>
              <template v-else>✅ 供需平稳，近期无断料风险</template>
            </div>
          </div>
        </div>
      </section>

      <!-- 第二区：ECharts 全局供需可视化直观图表大盘 -->
      <section class="charts-grid card elevated">
        <div class="charts-section-header">
          <h3>📊 全局供需直观可视化大盘</h3>
          <span class="charts-tip">支持缩放、滑块与多维图例对比</span>
        </div>
        <div class="charts-container">
          <!-- 图表一：各保温管型号供需堆叠柱状图 -->
          <div class="chart-wrapper">
            <div class="chart-title">📏 保温管型号供需及三日缺口分布 (m)</div>
            <div ref="chartContainer1" class="echarts-dom"></div>
            <div v-if="!hasEcharts" class="chart-placeholder">ECharts 全局对象未加载</div>
          </div>
          <!-- 图表二：换热站缺口 TOP 10 排名大盘 -->
          <div class="chart-wrapper">
            <div class="chart-title">🏢 换热站缺口 TOP 10 危险排队大盘 (m)</div>
            <div ref="chartContainer2" class="echarts-dom"></div>
            <div v-if="!hasEcharts" class="chart-placeholder">ECharts 全局对象未加载</div>
          </div>
        </div>
      </section>

      <!-- 第三区：时效超时与风险扫描中心（从角落彻底释放，升级为全宽大气网格） -->
      <section class="card elevated alert-section-fluid">
        <div class="alert-header-fluid-accent">
          <div class="alert-title-group">
            <h3>🛡️ 全局时效与风险扫描控制大盘</h3>
            <span class="alert-badge">实时秒级动态时间时效扫描</span>
          </div>
          <span class="alert-fluid-count" :class="{ danger: alerts.length > 0 }">
            当前扫描出：<strong>{{ alerts.length }}</strong> 项物流与手续异常风险
          </span>
        </div>

        <div class="alert-list-grid-container">
          <div v-for="(alt, idx) in alerts" :key="idx" class="alert-grid-item-card" :class="alt.type">
            <div class="alert-grid-item-card__header">
              <span class="alert-grid-item-card__title">{{ alt.title }}</span>
              <span class="alert-grid-item-card__badge">{{ getAlertBadgeText(alt.type) }}</span>
            </div>
            <p class="alert-grid-item-card__desc">{{ alt.desc }}</p>
            <div class="alert-grid-item-card__detail">
              {{ alt.detail }}
            </div>
            <div class="alert-grid-item-card__footer">
              <span>时空追踪点：{{ alt.timeDisplay }}</span>
            </div>
          </div>
          
          <!-- 空白状态 -->
          <div v-if="alerts.length === 0" class="alerts-fluid-empty-state">
            <div class="empty-fluid-icon">🛡️</div>
            <h4>全链路物流在途与确认时效完美健康</h4>
            <p>系统未扫描到任何发货超时、接收延滞或人为标记的异常单据。</p>
          </div>
        </div>
      </section>

      <!-- 第四区：多维数据穿透透视表（独占一行，展现大气表格） -->
      <section class="card elevated pivot-section-fluid">
        <div class="card-header pivot-header">
          <div class="pivot-title-group">
            <h3>🏢 供需全链路多维穿透透视表</h3>
            <span class="pivot-badge">已包含 show_date 上限截断</span>
          </div>
          <!-- 透视切换 Tab -->
          <div class="tab-workbench">
            <button 
              class="tab-btn" 
              :class="{ active: pivotMode === 'station' }" 
              @click="pivotMode = 'station'"
            >
              🏢 按换热站维度
            </button>
            <button 
              class="tab-btn" 
              :class="{ active: pivotMode === 'model' }" 
              @click="pivotMode = 'model'"
            >
              📏 按管径型号维度
            </button>
          </div>
        </div>

        <div class="search-filter-bar">
          <div class="filter-item">
            <label>过滤站点：</label>
            <select v-model="filterStationId">
              <option value="">全部站点</option>
              <option 
                v-for="st in configSummary?.demand_entities || []" 
                :key="st.station_id" 
                :value="st.station_id"
              >
                {{ st.station_name }}
              </option>
            </select>
          </div>
          <div class="filter-item">
            <label>过滤型号：</label>
            <select v-model="filterPipeModelId">
              <option value="">全部型号</option>
              <option 
                v-for="pm in configSummary?.pipe_models || []" 
                :key="pm.pipe_model_id" 
                :value="pm.pipe_model_id"
              >
                {{ pm.pipe_model_name }}
              </option>
            </select>
          </div>
          <button class="btn link-btn" @click="resetFilters">重置过滤</button>
        </div>

        <div class="pivot-table-container">
          <table class="pivot-table">
            <thead>
              <tr>
                <th class="left-align text-col">{{ pivotMode === 'station' ? '换热站名称' : '保温管型号' }}</th>
                <th class="right-align num-col sortable" @click="handleSort('design_qty')">
                  设计量 {{ getSortSymbol('design_qty') }}
                </th>
                <th class="right-align num-col sortable" @click="handleSort('purchase_plan_qty')">
                  计划采购 {{ getSortSymbol('purchase_plan_qty') }}
                </th>
                <th class="right-align num-col sortable" @click="handleSort('future_plan_qty')">
                  三日计划 {{ getSortSymbol('future_plan_qty') }}
                </th>
                <th class="right-align num-col sortable" @click="handleSort('total_shipped_qty')">
                  累计发货 {{ getSortSymbol('total_shipped_qty') }}
                </th>
                <th class="right-align num-col sortable" @click="handleSort('pending_arrival_qty')">
                  在途在管 {{ getSortSymbol('pending_arrival_qty') }}
                </th>
                <th class="right-align num-col sortable highlight-th-green" @click="handleSort('station_inventory_qty')">
                  现场库存 {{ getSortSymbol('station_inventory_qty') }}
                </th>
                <th class="right-align num-col sortable" @click="handleSort('total_usage_qty')">
                  累计使用 {{ getSortSymbol('total_usage_qty') }}
                </th>
                <th class="right-align num-col sortable highlight-th-red" @click="handleSort('hard_gap_qty')">
                  三日硬缺 {{ getSortSymbol('hard_gap_qty') }}
                </th>
                <th class="right-align num-col sortable highlight-th-orange" @click="handleSort('net_gap_qty')">
                  三日净缺 {{ getSortSymbol('net_gap_qty') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in computedTableData" :key="item.id" class="pivot-row">
                <td class="left-align text-col font-bold cell-ellipsis" :title="item.name">
                  {{ item.name || '—' }}
                </td>
                <td class="right-align num-col">{{ formatQty(item.design_qty) }}</td>
                <td class="right-align num-col">{{ formatQty(item.purchase_plan_qty) }}</td>
                <td class="right-align num-col font-bold">{{ formatQty(item.future_plan_qty) }}</td>
                <td class="right-align num-col">{{ formatQty(item.total_shipped_qty) }}</td>
                <td class="right-align num-col">{{ formatQty(item.pending_arrival_qty) }}</td>
                <td class="right-align num-col highlight-cell-green">{{ formatQty(item.station_inventory_qty) }}</td>
                <td class="right-align num-col">{{ formatQty(item.total_usage_qty) }}</td>
                <td class="right-align num-col highlight-cell-red" :class="{ 'danger-text': item.hard_gap_qty > 0 }">
                  {{ formatQty(item.hard_gap_qty) }}
                </td>
                <td class="right-align num-col highlight-cell-orange" :class="{ 'warning-text': item.net_gap_qty > 0 }">
                  {{ formatQty(item.net_gap_qty) }}
                </td>
              </tr>
              <tr v-if="computedTableData.length === 0" class="empty-row">
                <td colspan="10" class="center-align">暂无筛选对应的汇总数据</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { AppHeader, Breadcrumbs, useTubePageShell } from './shared'
import {
  getTubeSupplyManagementDemandSummary,
  getTubeSupplyManagementDeliveries
} from '../../daily_report_25_26/services/api'

// 获取路由与当前项目 Key
const route = useRoute()
const projectKey = computed(() => String(route.params.projectKey || 'insulation_pipe_supply_2026'))

// 使用 tube 统一页面壳
const {
  loading,
  errorMessage,
  configSummary,
  breadcrumbItems,
  goProjectPages,
  reloadConfigSummary,
} = useTubePageShell('全局数据看板')

// 业务汇总行与发货流水行
const summaryRows = ref([])
const deliveries = ref([])
const loadingSummary = ref(false)

// 前端过滤与排序配置
const pivotMode = ref('station') // 'station' / 'model'
const sortKey = ref('')
const sortOrder = ref('desc')
const filterStationId = ref('')
const filterPipeModelId = ref('')

// ECharts 挂载节点
const chartContainer1 = ref(null)
const chartContainer2 = ref(null)
let chartInstance1 = null
let chartInstance2 = null
const hasEcharts = ref(false)

// 刷新全部配置与明细
async function refreshAllData() {
  await reloadConfigSummary()
  await loadDashboardData()
}

// 拉取后端真实数据
async function loadDashboardData() {
  loadingSummary.value = true
  try {
    const summaryRes = await getTubeSupplyManagementDemandSummary(projectKey.value)
    summaryRows.value = summaryRes?.rows || []

    const deliveriesRes = await getTubeSupplyManagementDeliveries(projectKey.value)
    deliveries.value = deliveriesRes || []
    
    // 数据加载完毕后渲染图表
    nextTick(() => {
      renderCharts()
    })
  } catch (error) {
    console.error('拉取 tube 汇总数据失败:', error)
  } finally {
    loadingSummary.value = false
  }
}

// HSL 名字映射解析
function stationName(id) {
  const list = configSummary.value?.demand_entities || []
  const item = list.find(x => String(x.station_id) === String(id))
  return item ? item.station_name : id
}

// 保温管型号名映射
function pipeModelName(id) {
  const list = configSummary.value?.pipe_models || []
  const item = list.find(x => String(x.pipe_model_id) === String(id))
  return item ? item.pipe_model_name : id
}

// 供给主体映射
function supplyEntityName(id) {
  const list = configSummary.value?.supply_entities || []
  const item = list.find(x => String(x.entity_id) === String(id))
  return item ? item.entity_name : id
}

// 格式化时间
function formatTime(isoStr) {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    return `${d.getMonth() + 1}-${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  } catch (e) {
    return isoStr
  }
}

// 格式化展示量（数值以 m 为单位）
function formatQty(val) {
  if (val === null || val === undefined) return '0'
  const num = Number(val)
  return isNaN(num) ? '0' : num.toFixed(0)
}

function getPercent(n, total) {
  if (!total || total <= 0) return 0
  const pct = (n / total) * 100
  return Math.min(100, Math.max(0, Number(pct.toFixed(1))))
}

// 重置过滤
function resetFilters() {
  filterStationId.value = ''
  filterPipeModelId.value = ''
  sortKey.value = ''
}

// 排序符号
function getSortSymbol(key) {
  if (sortKey.value !== key) return '⇅'
  return sortOrder.value === 'asc' ? '▲' : '▼'
}

// 排序处理
function handleSort(key) {
  if (sortKey.value === key) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortOrder.value = 'desc'
  }
}

// 1. KPI 大盘计算
const kpi = computed(() => {
  let design = 0
  let purchase = 0
  let plan = 0
  let shipped = 0
  let pendingArrival = 0
  let pendingReceive = 0
  let pendingWarehouse = 0
  let completed = 0
  let arrived = 0
  let usage = 0
  let inventory = 0
  let netGap = 0
  let hardGap = 0

  summaryRows.value.forEach(row => {
    design += row.design_qty || 0
    purchase += row.purchase_plan_qty || 0
    plan += row.future_plan_qty || 0
    shipped += row.total_shipped_qty || 0
    pendingArrival += row.pending_arrival_qty || 0
    pendingReceive += row.pending_receive_qty || 0
    pendingWarehouse += row.pending_warehouse_qty || 0
    completed += row.completed_qty || 0
    arrived += row.total_arrived_qty || 0
    usage += row.total_usage_qty || 0
    inventory += row.station_inventory_qty || 0
    netGap += row.net_gap_qty || 0
    
    // 硬缺口计算：滚动三日计划 > 当前库存
    if (row.future_plan_qty > row.station_inventory_qty) {
      hardGap += (row.future_plan_qty - row.station_inventory_qty)
    }
  })

  return {
    design,
    purchase,
    plan,
    shipped,
    pendingArrival,
    pendingReceive,
    pendingWarehouse,
    completed,
    arrived,
    usage,
    inventory,
    netGap,
    hardGap
  }
})

// 2. 透视（Pivot）与排序、全局条件过滤
const computedTableData = computed(() => {
  const isStationMode = pivotMode.value === 'station'
  const groups = {}

  summaryRows.value.forEach(row => {
    // 过滤逻辑：站点过滤
    if (filterStationId.value && String(row.station_id) !== String(filterStationId.value)) {
      return
    }
    // 过滤逻辑：管径型号过滤
    if (filterPipeModelId.value && String(row.pipe_model_id) !== String(filterPipeModelId.value)) {
      return
    }

    const groupKey = isStationMode ? row.station_id : row.pipe_model_id
    const groupName = isStationMode ? row.station_name : row.pipe_model_name

    if (!groups[groupKey]) {
      groups[groupKey] = {
        id: groupKey,
        name: groupName,
        design_qty: 0,
        purchase_plan_qty: 0,
        future_plan_qty: 0,
        total_shipped_qty: 0,
        pending_arrival_qty: 0,
        pending_receive_qty: 0,
        pending_warehouse_qty: 0,
        completed_qty: 0,
        total_arrived_qty: 0,
        total_usage_qty: 0,
        station_inventory_qty: 0,
        net_gap_qty: 0,
        hard_gap_qty: 0,
      }
    }

    const g = groups[groupKey]
    g.design_qty += row.design_qty || 0
    g.purchase_plan_qty += row.purchase_plan_qty || 0
    g.future_plan_qty += row.future_plan_qty || 0
    g.total_shipped_qty += row.total_shipped_qty || 0
    g.pending_arrival_qty += row.pending_arrival_qty || 0
    g.pending_receive_qty += row.pending_receive_qty || 0
    g.pending_warehouse_qty += row.pending_warehouse_qty || 0
    g.completed_qty += row.completed_qty || 0
    g.total_arrived_qty += row.total_arrived_qty || 0
    g.total_usage_qty += row.total_usage_qty || 0
    g.station_inventory_qty += row.station_inventory_qty || 0
    g.net_gap_qty += row.net_gap_qty || 0
    if (row.future_plan_qty > row.station_inventory_qty) {
      g.hard_gap_qty += (row.future_plan_qty - row.station_inventory_qty)
    }
  })

  const list = Object.values(groups)

  // 排序逻辑
  if (sortKey.value) {
    list.sort((a, b) => {
      const valA = a[sortKey.value] || 0
      const valB = b[sortKey.value] || 0
      return sortOrder.value === 'asc' ? valA - valB : valB - valA
    })
  }

  return list
})

// 3. 时效与风险扫描大盘（前端高阶判定）
const alerts = computed(() => {
  const list = []
  const now = new Date().getTime()

  deliveries.value.forEach(d => {
    // 1. 异常标记发货单
    if (d.abnormal_flag || d.status === 'abnormal') {
      list.push({
        type: 'abnormal',
        title: '🔴 现场标记异常发货单',
        desc: `单号: ${d.order_no || d.id} (车牌: ${d.vehicle_plate_no || '—'})`,
        detail: `发往 ${stationName(d.station_id)} 的 ${pipeModelName(d.pipe_model_id)} (${formatQty(d.shipped_qty)}m) 被标记异常。反馈: ${d.arrived_remark || d.received_remark || d.warehouse_remark || '暂无说明'}`,
        time: d.updated_at || d.created_at || new Date().toISOString(),
        timeDisplay: formatTime(d.updated_at || d.created_at),
        row: d
      })
    }

    // 2. 到货确认严重超时（>12h）
    if (d.status === 'pending_arrival' && d.shipped_at) {
      const elapsed = (now - new Date(d.shipped_at).getTime()) / (1000 * 3600)
      if (elapsed > 12) {
        list.push({
          type: 'timeout-arrival',
          title: '🚨 到货确认严重超时（>12h）',
          desc: `发货在途时长已达 ${elapsed.toFixed(1)} 小时`,
          detail: `${supplyEntityName(d.supply_entity_id)} 发往 ${stationName(d.station_id)} 的 ${pipeModelName(d.pipe_model_id)} (${formatQty(d.shipped_qty)}m)。发货时间: ${formatTime(d.shipped_at)}。`,
          time: d.shipped_at,
          timeDisplay: formatTime(d.shipped_at),
          row: d
        })
      }
    }

    // 3. 施工接收确认超时（>6h）
    if (d.status === 'pending_receive' && d.arrived_confirm_at) {
      const elapsed = (now - new Date(d.arrived_confirm_at).getTime()) / (1000 * 3600)
      if (elapsed > 6) {
        list.push({
          type: 'timeout-receive',
          title: '⚠️ 施工接收超时预警（>6h）',
          desc: `到货签收后已滞留 ${elapsed.toFixed(1)} 小时`,
          detail: `单号 ${d.order_no || d.id} (车牌 ${d.vehicle_plate_no || '—'}) 已到货现场 (${formatQty(d.arrived_qty)}m)，施工单位尚未点击接收。到货时间: ${formatTime(d.arrived_confirm_at)}。`,
          time: d.arrived_confirm_at,
          timeDisplay: formatTime(d.arrived_confirm_at),
          row: d
        })
      }
    }

    // 4. 库管未确认（>12h）
    if (d.status === 'pending_warehouse' && d.received_confirm_at) {
      const elapsed = (now - new Date(d.received_confirm_at).getTime()) / (1000 * 3600)
      if (elapsed > 12) {
        list.push({
          type: 'timeout-warehouse',
          title: '💼 库房最终接收手续超期（>12h）',
          desc: `接收后滞留 ${elapsed.toFixed(1)} 小时`,
          detail: `单号: ${d.order_no || d.id} 已由施工方接收确认 (${formatQty(d.received_qty)}m)，库管尚未完成台账手续闭环。施工接收时间: ${formatTime(d.received_confirm_at)}。`,
          time: d.received_confirm_at,
          timeDisplay: formatTime(d.received_confirm_at),
          row: d
        })
      }
    }
  })

  // 按发生时间降序排序
  list.sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())
  return list
})

function getAlertBadgeText(type) {
  if (type === 'abnormal') return '异常标记'
  if (type === 'timeout-arrival') return '到货超时'
  if (type === 'timeout-receive') return '施工延滞'
  return '手续滞后'
}

// 4. ECharts 交互可视化图表渲染
function renderCharts() {
  if (!window.echarts) {
    hasEcharts.value = false
    return
  }
  hasEcharts.value = true

  // --- 图表一：各保温管型号供需堆叠柱状图 ---
  if (chartContainer1.value) {
    if (!chartInstance1) {
      chartInstance1 = window.echarts.init(chartContainer1.value)
    }

    // 提取型号维度的数据
    const modelsMap = {}
    summaryRows.value.forEach(row => {
      const modelId = row.pipe_model_id
      const modelName = row.pipe_model_name
      if (!modelsMap[modelId]) {
        modelsMap[modelId] = {
          name: modelName,
          inventory: 0,
          pending: 0,
          netGap: 0
        }
      }
      modelsMap[modelId].inventory += row.station_inventory_qty || 0
      modelsMap[modelId].pending += row.pending_arrival_qty || 0
      modelsMap[modelId].netGap += row.net_gap_qty || 0
    })

    const mList = Object.values(modelsMap)
    
    const option1 = {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      legend: {
        data: ['现场库存', '在途在管', '三日净缺口'],
        bottom: 0,
        textStyle: { color: '#475569', fontWeight: 600 }
      },
      grid: {
        top: '15%',
        left: '4%',
        right: '4%',
        bottom: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: mList.map(x => x.name),
        axisLabel: { color: '#64748b', fontSize: 11, rotate: 15 }
      },
      yAxis: {
        type: 'value',
        name: '米 (m)',
        nameTextStyle: { color: '#64748b', fontWeight: 600 },
        axisLabel: { color: '#64748b' },
        splitLine: { lineStyle: { type: 'dashed', color: '#f1f5f9' } }
      },
      series: [
        {
          name: '现场库存',
          type: 'bar',
          stack: 'total',
          emphasis: { focus: 'series' },
          data: mList.map(x => x.inventory),
          itemStyle: { color: '#10b981', borderRadius: [2, 2, 0, 0] }
        },
        {
          name: '在途在管',
          type: 'bar',
          stack: 'total',
          emphasis: { focus: 'series' },
          data: mList.map(x => x.pending),
          itemStyle: { color: '#06b6d4', borderRadius: [2, 2, 0, 0] }
        },
        {
          name: '三日净缺口',
          type: 'bar',
          stack: 'total',
          emphasis: { focus: 'series' },
          data: mList.map(x => x.netGap),
          itemStyle: { color: '#ea580c', borderRadius: [2, 2, 0, 0] }
        }
      ]
    }
    chartInstance1.setOption(option1, { notMerge: false, lazyUpdate: true })
  }

  // --- 图表二：换热站缺口 TOP 10 排名大盘 ---
  if (chartContainer2.value) {
    if (!chartInstance2) {
      chartInstance2 = window.echarts.init(chartContainer2.value)
    }

    // 提取换热站维度的数据
    const stationsMap = {}
    summaryRows.value.forEach(row => {
      const stationId = row.station_id
      const stationNameStr = row.station_name
      if (!stationsMap[stationId]) {
        stationsMap[stationId] = {
          name: stationNameStr,
          hardGap: 0,
          netGap: 0
        }
      }
      stationsMap[stationId].netGap += row.net_gap_qty || 0
      if (row.future_plan_qty > row.station_inventory_qty) {
        stationsMap[stationId].hardGap += (row.future_plan_qty - row.station_inventory_qty)
      }
    })

    // 按硬缺口+净缺口总量排序并切取前10
    const topStations = Object.values(stationsMap)
      .filter(x => x.hardGap > 0 || x.netGap > 0)
      .sort((a, b) => (b.hardGap + b.netGap) - (a.hardGap + a.netGap))
      .slice(0, 10)

    const option2 = {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      legend: {
        data: ['三日硬缺口', '三日净缺口'],
        bottom: 0,
        textStyle: { color: '#475569', fontWeight: 600 }
      },
      grid: {
        top: '15%',
        left: '4%',
        right: '6%',
        bottom: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'value',
        name: '米 (m)',
        nameTextStyle: { color: '#64748b', fontWeight: 600 },
        axisLabel: { color: '#64748b' },
        splitLine: { lineStyle: { type: 'dashed', color: '#f1f5f9' } }
      },
      yAxis: {
        type: 'category',
        data: topStations.map(x => x.name).reverse(),
        axisLabel: { color: '#475569', fontSize: 11 }
      },
      series: [
        {
          name: '三日硬缺口',
          type: 'bar',
          data: topStations.map(x => x.hardGap).reverse(),
          itemStyle: { color: '#ef4444', borderRadius: [0, 4, 4, 0] }
        },
        {
          name: '三日净缺口',
          type: 'bar',
          data: topStations.map(x => x.netGap).reverse(),
          itemStyle: { color: '#ea580c', borderRadius: [0, 4, 4, 0] }
        }
      ]
    }
    chartInstance2.setOption(option2, { notMerge: false, lazyUpdate: true })
  }
}

// 自动响应式重绘
function handleResize() {
  chartInstance1?.resize()
  chartInstance2?.resize()
}

// 联动重绘 Watcher
watch([summaryRows, pivotMode], () => {
  nextTick(() => {
    renderCharts()
  })
}, { deep: true })

onMounted(() => {
  loadDashboardData()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance1?.dispose()
  chartInstance2?.dispose()
})
</script>

<style scoped>
.tube-page-root {
  min-height: 100vh;
  background: var(--bg, #f8fafc);
}

.tube-page-main {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-top: 18px;
  padding-bottom: 36px;
}

/* 顶部栏 */
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.date-context-badge {
  display: flex;
  gap: 16px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid #e2e8f0;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 13px;
  color: #475569;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

.date-context-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}

.dot.green { background: #10b981; }
.dot.blue { background: #3b82f6; }

.page-error {
  margin: 0;
  color: var(--danger, #ef4444);
  font-weight: 600;
  background: #fef2f2;
  padding: 10px 16px;
  border-radius: 8px;
  border: 1px solid #fca5a5;
}

/* 第一区：KPI 磨砂卡片大盘 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
}

.stat-card {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -1px rgba(0, 0, 0, 0.02);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 20px -3px rgba(0, 0, 0, 0.06), 0 4px 6px -2px rgba(0, 0, 0, 0.04);
}

.stat-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 4px;
  background: #cbd5e1;
}

.stat-card:nth-child(1)::before { background: #3b82f6; }
.stat-card:nth-child(2)::before { background: #06b6d4; }
.stat-card:nth-child(3)::before { background: #10b981; }
.stat-card:nth-child(4)::before { background: #ef4444; }

.stat-card__icon {
  position: absolute;
  right: 18px;
  top: 18px;
  font-size: 26px;
  opacity: 0.15;
}

.stat-card__label {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
  margin-bottom: 10px;
}

.stat-card__value {
  font-size: 24px;
  font-weight: 800;
  color: #1e293b;
  font-variant-numeric: tabular-nums;
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.stat-card__unit {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 500;
}

.stat-card__separator {
  margin: 0 6px;
  color: #cbd5e1;
  font-size: 18px;
  font-weight: 300;
}

.highlight-blue { color: #2563eb; }
.highlight-cyan { color: #0891b2; }
.highlight-green { color: #059669; }
.highlight-red { color: #dc2626; }
.highlight-orange { color: #ea580c; }

/* 红色警告闪烁呼吸灯 */
.stat-card.alert-pulsing::after {
  content: '';
  position: absolute;
  right: 8px;
  top: 8px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ef4444;
  box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
  animation: pulse-red-light 1.5s infinite;
}

@keyframes pulse-red-light {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

.blink {
  animation: blink-text 1.2s infinite;
}

@keyframes blink-text {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.65; }
}

.stat-card__progress {
  margin-top: 16px;
}

.progress-bar-bg {
  height: 6px;
  background: #f1f5f9;
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.progress-bar-fill.blue { background: #3b82f6; }
.progress-bar-fill.cyan { background: #06b6d4; }
.progress-bar-fill.green { background: #10b981; }
.progress-bar-fill.red { background: #ef4444; }

.progress-bar-text {
  margin-top: 6px;
  font-size: 11px;
  color: #64748b;
  font-weight: 500;
  display: flex;
  justify-content: space-between;
}

/* 第二区：ECharts 全局可视化图表大盘 */
.charts-grid {
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  padding: 20px;
}

.charts-section-header {
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 12px;
  margin-bottom: 16px;
}

.charts-section-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: #1e293b;
}

.charts-tip {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 500;
}

.charts-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 900px) {
  .charts-container {
    grid-template-columns: 1fr;
  }
}

.chart-wrapper {
  background: #f8fafc;
  border: 1px solid #f1f5f9;
  border-radius: 8px;
  padding: 16px;
  position: relative;
  display: flex;
  flex-direction: column;
}

.chart-title {
  font-size: 13px;
  font-weight: 800;
  color: #334155;
  margin-bottom: 12px;
}

.echarts-dom {
  height: 280px;
  width: 100%;
}

.chart-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(248, 250, 252, 0.9);
  color: #ef4444;
  font-size: 13px;
  font-weight: 600;
}

/* 第三区：时效超时与风险扫描中心（全宽大气网格，不再挤在角落） */
.alert-section-fluid {
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.alert-header-fluid-accent {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f1f5f9;
  padding: 16px 20px;
  flex-wrap: wrap;
  gap: 12px;
}

.alert-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.alert-title-group h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: #1e293b;
}

.alert-badge {
  font-size: 11px;
  background: #fef2f2;
  color: #ef4444;
  padding: 3px 8px;
  border-radius: 12px;
  font-weight: 600;
}

.alert-fluid-count {
  font-size: 13px;
  color: #475569;
  font-weight: 500;
}

.alert-fluid-count.danger {
  color: #ef4444;
}

.alert-list-grid-container {
  padding: 20px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  max-height: 480px;
  overflow-y: auto;
}

/* 横向流式卡片设计 */
.alert-grid-item-card {
  background: #f8fafc;
  border-radius: 8px;
  padding: 14px;
  border-left: 4px solid #cbd5e1;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 8px;
}

.alert-grid-item-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.alert-grid-item-card.abnormal { border-left-color: #ef4444; background: #fff5f5; }
.alert-grid-item-card.timeout-arrival { border-left-color: #ef4444; background: #fff5f5; }
.alert-grid-item-card.timeout-receive { border-left-color: #ea580c; background: #fffaf0; }
.alert-grid-item-card.timeout-warehouse { border-left-color: #3b82f6; background: #eff6ff; }

.alert-grid-item-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alert-grid-item-card__title {
  font-size: 13px;
  font-weight: 800;
  color: #1e293b;
}

.alert-grid-item-card__badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 700;
  background: #e2e8f0;
  color: #475569;
}

.alert-grid-item-card.abnormal .alert-grid-item-card__badge { background: #fca5a5; color: #991b1b; }
.alert-grid-item-card.timeout-arrival .alert-grid-item-card__badge { background: #fca5a5; color: #991b1b; }
.alert-grid-item-card.timeout-receive .alert-grid-item-card__badge { background: #fed7aa; color: #c2410c; }
.alert-grid-item-card.timeout-warehouse .alert-grid-item-card__badge { background: #bfdbfe; color: #1d4ed8; }

.alert-grid-item-card__desc {
  font-size: 12px;
  color: #334155;
  font-weight: 700;
  margin: 0;
}

.alert-grid-item-card__detail {
  font-size: 11px;
  color: #64748b;
  line-height: 1.5;
  background: rgba(255, 255, 255, 0.6);
  padding: 8px 10px;
  border-radius: 4px;
}

.alert-grid-item-card__footer {
  font-size: 10px;
  color: #94a3b8;
  font-weight: 500;
  border-top: 1px solid rgba(226, 232, 240, 0.5);
  padding-top: 6px;
  margin-top: 2px;
}

/* 宽屏下的全链路健康状态 */
.alerts-fluid-empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 48px 20px;
  color: #94a3b8;
}

.empty-fluid-icon {
  font-size: 44px;
  margin-bottom: 12px;
  animation: pulse-health 2s infinite;
}

@keyframes pulse-health {
  0%, 100% { transform: scale(1); opacity: 0.9; }
  50% { transform: scale(1.06); opacity: 1; }
}

.alerts-fluid-empty-state h4 {
  margin: 0 0 6px 0;
  color: #334155;
  font-size: 15px;
  font-weight: 800;
}

.alerts-fluid-empty-state p {
  margin: 0;
  font-size: 13px;
}

/* 第四区：多维数据透视表 */
.pivot-section-fluid {
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.pivot-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  border-bottom: 1px solid #f1f5f9;
  padding: 16px 20px;
}

.pivot-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.pivot-title-group h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: #1e293b;
}

.pivot-badge {
  font-size: 11px;
  background: #f1f5f9;
  color: #64748b;
  padding: 3px 8px;
  border-radius: 12px;
  font-weight: 500;
}

/* Tab 标签化工作台按钮 */
.tab-workbench {
  display: flex;
  background: #f1f5f9;
  padding: 4px;
  border-radius: 8px;
}

.tab-btn {
  border: none;
  background: transparent;
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-btn.active {
  background: #ffffff;
  color: #3b82f6;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

/* 过滤栏 */
.search-filter-bar {
  display: flex;
  gap: 16px;
  padding: 12px 20px;
  background: #f8fafc;
  border-bottom: 1px solid #f1f5f9;
  align-items: center;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #475569;
}

.filter-item select {
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  font-size: 13px;
  color: #334155;
  outline: none;
}

.filter-item select:focus {
  border-color: #3b82f6;
}

.link-btn {
  background: transparent !important;
  border: none !important;
  color: #3b82f6 !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  cursor: pointer;
  padding: 0 !important;
}

.link-btn:hover {
  text-decoration: underline;
}

/* 数据透视表格 */
.pivot-table-container {
  overflow-x: auto;
  padding: 0;
}

.pivot-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 900px;
}

.pivot-table th, 
.pivot-table td {
  padding: 12px 14px;
  border-bottom: 1px solid #f1f5f9;
  font-size: 13px;
  line-height: 1.5;
}

.pivot-table th {
  background: #f8fafc;
  color: #475569;
  font-weight: 800;
  user-select: none;
  white-space: nowrap;
}

.pivot-table th.sortable {
  cursor: pointer;
}

.pivot-table th.sortable:hover {
  background: #e2e8f0;
  color: #1e293b;
}

.pivot-row:hover {
  background: #f8fafc;
}

.pivot-row td {
  font-variant-numeric: tabular-nums;
  color: #334155;
}

/* 单元格强制对齐与防折行 */
.left-align { text-align: left; }
.right-align { text-align: right; }
.center-align { text-align: center; }

.text-col {
  min-width: 140px;
  max-width: 180px;
}

.num-col {
  width: 85px;
}

.cell-ellipsis {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.font-bold {
  font-weight: 700;
}

/* 报警高亮列 */
.highlight-th-green { background: #f0fdf4 !important; color: #166534 !important; }
.highlight-th-red { background: #fef2f2 !important; color: #991b1b !important; }
.highlight-th-orange { background: #fff7ed !important; color: #9a3412 !important; }

.highlight-cell-green { background: rgba(240, 253, 244, 0.5); font-weight: 600; color: #15803d !important; }
.highlight-cell-red { background: rgba(254, 242, 242, 0.5); font-weight: 600; }
.highlight-cell-orange { background: rgba(255, 247, 237, 0.5); font-weight: 600; }

.danger-text { color: #ef4444 !important; }
.warning-text { color: #ea580c !important; }

.empty-row td {
  padding: 36px;
  color: #94a3b8;
  font-weight: 500;
}
</style>
