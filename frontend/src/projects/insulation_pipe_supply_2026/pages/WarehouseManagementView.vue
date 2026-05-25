<template>
  <div class="tube-page-root">
    <AppHeader />
    <main class="tube-page-main container">
      <Breadcrumbs :items="breadcrumbItems" />

      <header class="topbar">
        <div>
          <h2>库管员管理入口</h2>
          <p class="sub">用于接收发货、确认施工接收并完成库管手续闭环。</p>
        </div>
        <div class="topbar-actions">
          <button class="btn ghost" type="button" @click="goProjectPages">返回功能页</button>
          <button class="btn primary" type="button" :disabled="loading" @click="reloadAll">刷新台账</button>
        </div>
      </header>

      <p v-if="pageError || shellError" class="page-error">{{ pageError || shellError }}</p>
      <p v-if="pageMessage" class="page-success">{{ pageMessage }}</p>

      <section class="card elevated">
        <div class="card-header">
          <span>库管台账筛选</span>
          <span class="muted">展示日期：{{ options?.show_date || options?.biz_date || '--' }}</span>
        </div>
        <div class="filter-grid">
          <label class="field">
            <span>换热站</span>
            <select v-model="filters.stationId" class="input">
              <option value="">全部换热站</option>
              <option v-for="item in stationOptions" :key="item.station_id" :value="item.station_id">
                {{ item.station_name }}（{{ item.station_id }}）
              </option>
            </select>
          </label>
          <label class="field">
            <span>供给主体</span>
            <select v-model="filters.supplyEntityId" class="input">
              <option value="">全部供给主体</option>
              <option v-for="item in supplyEntityOptions" :key="item.entity_id" :value="item.entity_id">
                {{ item.entity_name }}（{{ item.entity_id }}）
              </option>
            </select>
          </label>
          <label class="field">
            <span>型号</span>
            <select v-model="filters.pipeModelId" class="input">
              <option value="">全部型号</option>
              <option v-for="item in pipeModelOptions" :key="item.pipe_model_id" :value="item.pipe_model_id">
                {{ item.pipe_model_name }}
              </option>
            </select>
          </label>
          <label class="field">
            <span>状态</span>
            <select v-model="filters.status" class="input">
              <option value="">全部状态</option>
              <option v-for="item in deliveryStatusOptions" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
          </label>
          <label class="field">
            <span>运输车次号</span>
            <input v-model.trim="filters.shipmentNo" class="input" type="text" placeholder="输入车次号筛选" />
          </label>
          <label class="field">
            <span>单号</span>
            <input v-model.trim="filters.orderNo" class="input" type="text" placeholder="输入订单号筛选" />
          </label>
          <label class="field">
            <span>车牌号</span>
            <input v-model.trim="filters.vehiclePlateNo" class="input" type="text" placeholder="输入车牌号筛选" />
          </label>
        </div>
        <div class="filter-actions">
          <button class="btn primary" type="button" :disabled="loading" @click="loadDeliveries">查询</button>
          <button class="btn ghost" type="button" :disabled="loading" @click="resetFilters">重置</button>
        </div>
      </section>

      <section class="card elevated stats-card">
        <div class="card-header">台账概览</div>
        <div class="stats-grid">
          <div class="stat-box">
            <span>记录总数</span>
            <strong>{{ deliverySummary.total }}</strong>
          </div>
          <div class="stat-box">
            <span>待到货</span>
            <strong>{{ deliverySummary.pendingArrival }}</strong>
          </div>
          <div class="stat-box">
            <span>待接收</span>
            <strong>{{ deliverySummary.pendingReceive }}</strong>
          </div>
          <div class="stat-box">
            <span>待库管</span>
            <strong>{{ deliverySummary.pendingWarehouse }}</strong>
          </div>
          <div class="stat-box">
            <span>已完成</span>
            <strong>{{ deliverySummary.completed }}</strong>
          </div>
          <div class="stat-box">
            <span>已撤销</span>
            <strong>{{ deliverySummary.cancelled }}</strong>
          </div>
        </div>
      </section>

      <section class="card elevated">
        <div class="card-header">库管发货台账</div>
        <div v-if="loading" class="page-state">正在读取库管台账...</div>
        <div v-else-if="deliveries.length === 0" class="page-state">当前筛选条件下没有记录。</div>
        <div v-else class="table-wrap">
          <table class="table">
            <colgroup>
              <col class="col-checkbox" />
              <col class="col-order" />
              <col class="col-shipment" />
              <col class="col-plate" />
              <col class="col-supply" />
              <col class="col-station" />
              <col class="col-model" />
              <col class="col-qty" />
              <col class="col-qty" />
              <col class="col-qty" />
              <col class="col-status" />
              <col class="col-time" />
              <col class="col-elapsed" />
            </colgroup>
            <thead>
              <tr>
                <th class="cell-checkbox">
                  <input
                    type="checkbox"
                    :checked="allPendingWarehouseSelected"
                    :indeterminate.prop="hasPartialPendingWarehouseSelection"
                    @change="toggleSelectAllPendingWarehouse($event)"
                  />
                </th>
                <th>订单号</th>
                <th>运输车次号</th>
                <th class="cell-plate-header">车牌号</th>
                <th>供给主体</th>
                <th>换热站</th>
                <th>型号</th>
                <th class="cell-number">发货量（米）</th>
                <th class="cell-number">到货量（米）</th>
                <th class="cell-number">接收量（米）</th>
                <th class="cell-status">状态</th>
                <th class="cell-datetime">发货时间</th>
                <th class="cell-elapsed">在途时长</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in deliveries"
                :key="row.id"
                :class="{ checked: isDeliverySelected(row.id), active: String(row.id) === selectedDeliveryId }"
                @click="toggleDeliverySelection(row)"
              >
                <td class="cell-checkbox">
                  <input
                    v-if="row.status === 'pending_warehouse'"
                    type="checkbox"
                    :checked="isDeliverySelected(row.id)"
                    @click.stop
                    @change="toggleDeliverySelection(row)"
                  />
                </td>
                <td class="cell-code-wrapper">
                  <span class="cell-code">{{ row.order_no || row.delivery_code || row.id }}</span>
                </td>
                <td class="cell-code-wrapper">
                  <span class="cell-code">{{ row.shipment_no || '—' }}</span>
                </td>
                <td class="cell-plate">
                  <span class="plate-badge">{{ row.vehicle_plate_no || '—' }}</span>
                </td>
                <td class="cell-supply" :title="row.supply_entity_name">{{ row.supply_entity_name }}</td>
                <td class="cell-station" :title="row.station_name">{{ row.station_name }}</td>
                <td class="cell-model" :title="row.pipe_model_name">{{ row.pipe_model_name }}</td>
                <td class="cell-number">{{ formatAmount(row.shipped_qty) }}</td>
                <td class="cell-number">{{ formatOptionalAmount(row.arrived_qty) }}</td>
                <td class="cell-number">{{ formatOptionalAmount(row.received_qty) }}</td>
                <td class="cell-status">
                  <div class="status-pill-group">
                    <span class="status-pill" :class="statusClass(row.status)">
                      {{ deliveryStatusLabelMap[row.status] || row.status || '--' }}
                    </span>
                    <span v-if="row.abnormal_flag" class="status-pill status-abnormal">
                      {{ getAbnormalLabel(row) }}
                    </span>
                  </div>
                </td>
                <td class="cell-datetime">{{ formatDateTime(row.shipped_at) }}</td>
                <td class="cell-elapsed">{{ formatDeliveryElapsedDisplay(row) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card elevated">
        <div class="card-header">选中记录处置</div>
        <div v-if="!selectedDeliveries.length" class="page-state">请至少勾选一条台账记录后再执行确认操作。</div>
        <div v-else class="action-panel">
          <div class="action-summary">
            <div><span>已选记录</span><strong>{{ selectedDeliveryAggregate.totalRecords }} 条</strong></div>
            <div><span>总发货长度</span><strong>{{ formatAmount(selectedDeliveryAggregate.totalShippedQty) }} 米</strong></div>
            <div><span>总接收长度</span><strong>{{ formatAmount(selectedDeliveryAggregate.totalReceivedQty) }} 米</strong></div>
            <div><span>平均在途时长</span><strong>{{ selectedDeliveryAggregate.averageElapsedLabel }}</strong></div>
          </div>

          <div v-if="pendingWarehouseSelectedDeliveries.length" class="form-grid">
            <label class="field field-wide">
              <span>库管备注</span>
              <textarea v-model="warehouseForm.remark" class="textarea" rows="3" placeholder="可填写手续闭环说明"></textarea>
            </label>
            <div class="form-actions">
              <button class="btn primary" type="button" :disabled="actionLoading" @click="submitWarehouse">
                {{ actionLoading ? '提交中...' : `完成库管确认（${pendingWarehouseSelectedDeliveries.length}条）` }}
              </button>
            </div>
          </div>

          <div v-else class="page-state compact">当前勾选记录中没有“已接收待库管”状态数据，无法执行批量库管确认。</div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { AppHeader, Breadcrumbs, useTubePageShell, useTubeRealtimeRefresh } from './shared'
import {
  confirmTubeWarehouseDeliveryWarehouse,
  getTubeWarehouseManagementDeliveries,
  getTubeWarehouseManagementOptions,
} from '../../daily_report_25_26/services/api'

const projectKey = 'insulation_pipe_supply_2026'
const { breadcrumbItems, goProjectPages, errorMessage: shellError } = useTubePageShell('库管员管理入口')

const loading = ref(false)
const actionLoading = ref(false)
const pageError = ref('')
const pageMessage = ref('')
const options = ref(null)
const deliveries = ref([])
const selectedDeliveryId = ref('')
const selectedDeliveryIds = ref([])

const filters = reactive({
  stationId: '',
  supplyEntityId: '',
  pipeModelId: '',
  status: '',
  shipmentNo: '',
  orderNo: '',
  vehiclePlateNo: '',
})

const warehouseForm = reactive({
  remark: '',
})
const nowTick = ref(Date.now())
let nowTimer = null

const stationOptions = computed(() => options.value?.stations || [])
const supplyEntityOptions = computed(() => options.value?.supply_entities || [])
const pipeModelOptions = computed(() => options.value?.pipe_models || [])
const deliveryStatusOptions = computed(() => options.value?.delivery_status_options || [])
const deliveryStatusLabelMap = computed(() => {
  const result = {}
  for (const item of deliveryStatusOptions.value) {
    result[item.value] = item.label
  }
  return result
})

const selectedDelivery = computed(() => deliveries.value.find((row) => String(row.id) === selectedDeliveryId.value) || null)
const selectedDeliveries = computed(() => {
  const selectedIdSet = new Set(selectedDeliveryIds.value)
  return deliveries.value.filter((row) => selectedIdSet.has(String(row.id)))
})
const pendingWarehouseSelectedDeliveries = computed(() => selectedDeliveries.value.filter((row) => row.status === 'pending_warehouse'))
const pendingWarehouseDeliveryIds = computed(() => deliveries.value.filter((row) => row.status === 'pending_warehouse').map((row) => String(row.id)))
const allPendingWarehouseSelected = computed(() => {
  if (!pendingWarehouseDeliveryIds.value.length) return false
  const selectedIdSet = new Set(selectedDeliveryIds.value)
  return pendingWarehouseDeliveryIds.value.every((id) => selectedIdSet.has(id))
})
const hasPartialPendingWarehouseSelection = computed(() => {
  if (!pendingWarehouseDeliveryIds.value.length) return false
  const selectedIdSet = new Set(selectedDeliveryIds.value)
  const selectedCount = pendingWarehouseDeliveryIds.value.filter((id) => selectedIdSet.has(id)).length
  return selectedCount > 0 && selectedCount < pendingWarehouseDeliveryIds.value.length
})

const selectedDeliveryAggregate = computed(() => {
  const shipmentSet = new Set()
  const orderSet = new Set()
  const stationSet = new Set()
  const pipeModelSet = new Set()
  const vehiclePlateSet = new Set()
  const statusCountMap = new Map()
  let totalShippedQty = 0
  let totalArrivedQty = 0
  let totalReceivedQty = 0
  let elapsedCount = 0
  let elapsedTotalMs = 0
  let maxElapsedMs = 0

  for (const row of selectedDeliveries.value) {
    if (row.shipment_no) shipmentSet.add(row.shipment_no)
    if (row.order_no || row.delivery_code || row.id) orderSet.add(row.order_no || row.delivery_code || String(row.id))
    if (row.station_name || row.station_id) stationSet.add(row.station_name || row.station_id)
    if (row.pipe_model_name || row.pipe_model_id) pipeModelSet.add(row.pipe_model_name || row.pipe_model_id)
    if (row.vehicle_plate_no) vehiclePlateSet.add(row.vehicle_plate_no)
    const statusKey = row.status || 'unknown'
    statusCountMap.set(statusKey, Number(statusCountMap.get(statusKey) || 0) + 1)
    totalShippedQty += Number(row.shipped_qty || 0)
    totalArrivedQty += Number(row.arrived_qty || 0)
    totalReceivedQty += Number(row.received_qty || 0)
    const elapsedMs = getDeliveryElapsedMs(row)
    if (elapsedMs !== null) {
      elapsedCount += 1
      elapsedTotalMs += elapsedMs
      if (elapsedMs > maxElapsedMs) {
        maxElapsedMs = elapsedMs
      }
    }
  }

  const statusSummaryLabel =
    Array.from(statusCountMap.entries())
      .map(([status, count]) => `${deliveryStatusLabelMap.value[status] || status} ${count}条`)
      .join(' / ') || '—'

  return {
    totalRecords: selectedDeliveries.value.length,
    pendingWarehouseCount: pendingWarehouseSelectedDeliveries.value.length,
    shipmentCount: shipmentSet.size,
    orderCount: orderSet.size,
    stationCount: stationSet.size,
    pipeModelCount: pipeModelSet.size,
    totalShippedQty,
    totalArrivedQty,
    totalReceivedQty,
    averageElapsedLabel: elapsedCount ? formatDurationMs(elapsedTotalMs / elapsedCount) : '—',
    maxElapsedLabel: elapsedCount ? formatDurationMs(maxElapsedMs) : '—',
    statusSummaryLabel,
    pipeModelLabel: summarizeCollection(Array.from(pipeModelSet)),
    shipmentLabel: summarizeCollection(Array.from(shipmentSet)),
    vehiclePlateLabel: summarizeCollection(Array.from(vehiclePlateSet)),
  }
})

const deliverySummary = computed(() => {
  const summary = {
    total: deliveries.value.length,
    pendingArrival: 0,
    pendingReceive: 0,
    pendingWarehouse: 0,
    completed: 0,
    cancelled: 0,
  }
  for (const row of deliveries.value) {
    if (row.status === 'pending_arrival') summary.pendingArrival += 1
    else if (row.status === 'pending_receive') summary.pendingReceive += 1
    else if (row.status === 'pending_warehouse') summary.pendingWarehouse += 1
    else if (row.status === 'completed') summary.completed += 1
    else if (row.status === 'cancelled') summary.cancelled += 1
  }
  return summary
})

function formatAmount(value) {
  const num = Number(value)
  if (!Number.isFinite(num) || num === 0) return '0'
  return Number.isInteger(num) ? String(num) : num.toFixed(2).replace(/\.00$/, '')
}

function formatOptionalAmount(value) {
  const num = Number(value)
  if (!Number.isFinite(num) || num === 0) return '—'
  return Number.isInteger(num) ? String(num) : num.toFixed(2).replace(/\.00$/, '')
}

function formatDateTime(value) {
  if (!value) return '--'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return String(value).replace('T', ' ').slice(0, 19)
  }
  const pad = (part) => String(part).padStart(2, '0')
  return `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())} ${pad(parsed.getHours())}:${pad(parsed.getMinutes())}:${pad(parsed.getSeconds())}`
}

function formatElapsedLabel(shippedAt) {
  if (!shippedAt) return ''
  const start = new Date(shippedAt)
  if (Number.isNaN(start.getTime())) return ''
  const diffMs = Math.max(nowTick.value - start.getTime(), 0)
  const totalSeconds = Math.floor(diffMs / 1000)
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  if (days > 0) return `${days}天${hours}小时${minutes}分`
  if (hours > 0) return `${hours}小时${minutes}分`
  if (minutes > 0) return `${minutes}分`
  return `${totalSeconds}秒`
}

function formatDurationMs(durationMs) {
  const totalSeconds = Math.max(Math.floor(Number(durationMs || 0) / 1000), 0)
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  if (days > 0) return `${days}天${hours}小时${minutes}分`
  if (hours > 0) return `${hours}小时${minutes}分`
  if (minutes > 0) return `${minutes}分`
  return `${seconds}秒`
}

function getDeliveryElapsedMs(row) {
  if (!row || row.status === 'cancelled' || !row.shipped_at) return null
  const shippedAt = new Date(row.shipped_at)
  if (Number.isNaN(shippedAt.getTime())) return null
  const arrivedConfirmAtVal = row.arrivedConfirmAt ?? row.arrived_confirm_at
  const endValue = arrivedConfirmAtVal ? new Date(arrivedConfirmAtVal) : new Date(nowTick.value)
  if (Number.isNaN(endValue.getTime())) return null
  return Math.max(endValue.getTime() - shippedAt.getTime(), 0)
}

function summarizeCollection(values, visibleCount = 3) {
  const normalizedValues = (values || []).filter(Boolean)
  if (!normalizedValues.length) return '—'
  if (normalizedValues.length <= visibleCount) {
    return normalizedValues.join('、')
  }
  const visibleValues = normalizedValues.slice(0, visibleCount)
  return `${visibleValues.join('、')} 等${normalizedValues.length}项`
}

function formatDeliveryElapsedDisplay(row) {
  if (!row || row.status === 'cancelled') return '—'
  return row.delivery_elapsed_label || formatElapsedLabel(row.shipped_at) || '—'
}

function getAbnormalLabel(row) {
  if (!row?.abnormal_flag) return ''
  const shippedQty = Number(row.shipped_qty ?? 0)
  const arrivedQty = row.arrived_qty == null ? null : Number(row.arrived_qty)
  const receivedQty = row.received_qty == null ? null : Number(row.received_qty)
  if (receivedQty != null && arrivedQty != null && receivedQty < arrivedQty) return '少接收'
  if (arrivedQty != null && arrivedQty < shippedQty) return '少到货'
  return '异常'
}

function statusClass(status) {
  if (status === 'pending_arrival') return 'status-warn'
  if (status === 'pending_receive') return 'status-info'
  if (status === 'pending_warehouse') return 'status-secondary'
  if (status === 'completed') return 'status-success'
  if (status === 'cancelled') return 'status-danger'
  return 'status-neutral'
}

function syncActionForms(row) {
  if (!row) return
  warehouseForm.remark = row.warehouse_remark || ''
}

function isDeliverySelected(deliveryId) {
  return selectedDeliveryIds.value.includes(String(deliveryId))
}

function selectDelivery(row) {
  selectedDeliveryId.value = String(row.id)
  syncActionForms(row)
}

function toggleDeliverySelection(row) {
  const deliveryId = String(row.id)
  
  // 非“待库管”状态的行，点击行时仅作为“查看单条详情备注”，不参与多选勾选
  if (row.status !== 'pending_warehouse') {
    selectedDeliveryId.value = deliveryId
    syncActionForms(row)
    return
  }
  
  // 待库管状态的行进行多选切换
  if (isDeliverySelected(deliveryId)) {
    selectedDeliveryIds.value = selectedDeliveryIds.value.filter((id) => id !== deliveryId)
    if (selectedDeliveryId.value === deliveryId) {
      selectedDeliveryId.value = selectedDeliveryIds.value[0] || ''
      const nextSelected = deliveries.value.find((item) => String(item.id) === selectedDeliveryId.value)
      if (nextSelected) {
        syncActionForms(nextSelected)
      }
    }
    return
  }
  selectedDeliveryIds.value = [...selectedDeliveryIds.value, deliveryId]
  selectDelivery(row)
}

function toggleSelectAllPendingWarehouse(event) {
  const checked = Boolean(event?.target?.checked)
  if (checked) {
    const selectedIdSet = new Set(selectedDeliveryIds.value)
    for (const deliveryId of pendingWarehouseDeliveryIds.value) {
      selectedIdSet.add(deliveryId)
    }
    selectedDeliveryIds.value = Array.from(selectedIdSet)
    if (!selectedDeliveryId.value && pendingWarehouseSelectedDeliveries.value.length) {
      selectDelivery(pendingWarehouseSelectedDeliveries.value[0])
    }
    return
  }
  const pendingSet = new Set(pendingWarehouseDeliveryIds.value)
  selectedDeliveryIds.value = selectedDeliveryIds.value.filter((id) => !pendingSet.has(id))
  if (selectedDeliveryId.value && !selectedDeliveryIds.value.includes(selectedDeliveryId.value)) {
    selectedDeliveryId.value = selectedDeliveryIds.value[0] || ''
    const nextSelected = deliveries.value.find((item) => String(item.id) === selectedDeliveryId.value)
    if (nextSelected) {
      syncActionForms(nextSelected)
    }
  }
}

async function loadOptions() {
  const payload = await getTubeWarehouseManagementOptions(projectKey)
  options.value = payload
  const stationIdSet = new Set(stationOptions.value.map((item) => String(item.station_id || '')))
  const supplyEntityIdSet = new Set(supplyEntityOptions.value.map((item) => String(item.entity_id || '')))
  const pipeModelIdSet = new Set(pipeModelOptions.value.map((item) => String(item.pipe_model_id || '')))
  const deliveryStatusValueSet = new Set(deliveryStatusOptions.value.map((item) => String(item.value || '')))
  if (filters.stationId && !stationIdSet.has(filters.stationId)) {
    filters.stationId = ''
  }
  if (filters.supplyEntityId && !supplyEntityIdSet.has(filters.supplyEntityId)) {
    filters.supplyEntityId = ''
  }
  if (filters.pipeModelId && !pipeModelIdSet.has(filters.pipeModelId)) {
    filters.pipeModelId = ''
  }
  if (filters.status && !deliveryStatusValueSet.has(filters.status)) {
    filters.status = ''
  }
  if (!filters.stationId && stationOptions.value.length === 1) {
    filters.stationId = stationOptions.value[0].station_id
  }
}

async function loadDeliveries() {
  loading.value = true
  pageError.value = ''
  try {
    const payload = await getTubeWarehouseManagementDeliveries(projectKey, {
      stationId: filters.stationId,
      supplyEntityId: filters.supplyEntityId,
      pipeModelId: filters.pipeModelId,
      status: filters.status,
      shipmentNo: filters.shipmentNo,
      orderNo: filters.orderNo,
      vehiclePlateNo: filters.vehiclePlateNo,
    })
    deliveries.value = Array.isArray(payload?.rows) ? payload.rows : []
    const availableIdSet = new Set(deliveries.value.map((row) => String(row.id)))
    selectedDeliveryIds.value = selectedDeliveryIds.value.filter((id) => availableIdSet.has(id))
    const keepSelected = deliveries.value.find((row) => String(row.id) === selectedDeliveryId.value)
    if (keepSelected) {
      syncActionForms(keepSelected)
    } else if (selectedDeliveryIds.value.length > 0) {
      const firstSelected = deliveries.value.find((row) => String(row.id) === selectedDeliveryIds.value[0])
      if (firstSelected) {
        selectDelivery(firstSelected)
      }
    } else if (deliveries.value.length > 0) {
      selectedDeliveryId.value = ''
    } else {
      selectedDeliveryId.value = ''
    }
  } catch (error) {
    pageError.value = error?.message || '读取库管台账失败'
    deliveries.value = []
    selectedDeliveryId.value = ''
    selectedDeliveryIds.value = []
  } finally {
    loading.value = false
  }
}

async function reloadAll() {
  try {
    await loadOptions()
  } catch (error) {
    pageError.value = error?.message || '读取库管页面选项失败'
    return
  }
  await loadDeliveries()
}

function resetFilters() {
  filters.stationId = ''
  filters.supplyEntityId = ''
  filters.pipeModelId = ''
  filters.status = ''
  filters.shipmentNo = ''
  filters.orderNo = ''
  filters.vehiclePlateNo = ''
  loadDeliveries()
}

async function submitWarehouse() {
  if (!pendingWarehouseSelectedDeliveries.value.length) return
  actionLoading.value = true
  pageError.value = ''
  pageMessage.value = ''
  
  const targets = [...pendingWarehouseSelectedDeliveries.value]
  const promises = targets.map((row) =>
    confirmTubeWarehouseDeliveryWarehouse(projectKey, row.id, {
      remark: warehouseForm.remark || '',
    })
  )
  
  try {
    const results = await Promise.allSettled(promises)
    const fulfilled = results.filter((r) => r.status === 'fulfilled')
    const rejected = results.filter((r) => r.status === 'rejected')
    
    if (rejected.length === 0) {
      pageMessage.value = `批量库管确认处理成功！已完美处理 ${fulfilled.length} 条记录。`
      warehouseForm.remark = ''
      selectedDeliveryIds.value = [] // 批量处置成功后清空勾选
    } else {
      const errorMsg = rejected.map((r) => {
        return r.reason?.message || '网络连接或权限异常'
      }).join('; ')
      pageError.value = `部分处置成功！成功 ${fulfilled.length} 条，失败 ${rejected.length} 条。失败反馈: ${errorMsg}`
    }
    await loadDeliveries()
  } catch (error) {
    pageError.value = error?.message || '库管确认批量接口执行异常'
  } finally {
    actionLoading.value = false
  }
}

watch(
  selectedDelivery,
  (row) => {
    if (row) syncActionForms(row)
  },
  { immediate: true },
)

onMounted(async () => {
  nowTimer = setInterval(() => {
    nowTick.value = Date.now()
  }, 60000)
  await reloadAll()
})

useTubeRealtimeRefresh(reloadAll)

onBeforeUnmount(() => {
  if (nowTimer) {
    clearInterval(nowTimer)
    nowTimer = null
  }
})
</script>

<style scoped>
.tube-page-root { min-height: 100vh; background: var(--bg); }
.tube-page-main { display: flex; flex-direction: column; gap: 16px; padding-top: 18px; padding-bottom: 24px; max-width: 1440px; margin: 0 auto; width: 100%; box-sizing: border-box; padding-left: 24px; padding-right: 24px; }
.topbar { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.topbar h2 { margin: 0 0 6px; font-size: 22px; }
.topbar .sub { margin: 0; color: var(--muted); line-height: 1.6; }
.topbar-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.page-error { margin: 0; color: var(--danger); }
.page-success { margin: 0; color: #0f766e; }
.page-state { padding: 28px 12px; text-align: center; color: var(--muted); }
.page-state.compact { padding: 14px 12px; text-align: left; }
.card-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; font-weight: 600; margin-bottom: 14px; }
.muted { color: var(--muted); font-weight: 400; }
.filter-grid, .form-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.field { display: flex; flex-direction: column; gap: 8px; }
.field span { font-size: 13px; color: var(--muted); }
.field-wide { grid-column: 1 / -1; }
.input, .textarea { width: 100%; box-sizing: border-box; border: 1px solid rgba(15, 23, 42, 0.16); border-radius: 10px; padding: 10px 12px; font: inherit; background: #fff; color: var(--text); }
.textarea { resize: vertical; }
.filter-actions, .form-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 14px; flex-wrap: wrap; }
.form-actions { grid-column: 1 / -1; align-items: center; }
.stats-card { margin-top: 0; }
.stats-grid { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; }
.stat-box {
  border: 1px solid rgba(15, 23, 42, 0.08) !important;
  background: rgba(255, 255, 255, 0.65) !important;
  backdrop-filter: blur(12px) !important;
  -webkit-backdrop-filter: blur(12px) !important;
  border-radius: 12px !important;
  padding: 16px 14px !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 8px !important;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -1px rgba(0, 0, 0, 0.02) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  position: relative !important;
  overflow: hidden !important;
  box-sizing: border-box;
}

.stat-box::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 4px;
  background: #3b82f6;
}

.stat-box:nth-child(1)::before { background: #3b82f6; }
.stat-box:nth-child(2)::before { background: #f59e0b; }
.stat-box:nth-child(3)::before { background: #ea580c; }
.stat-box:nth-child(4)::before { background: #8b5cf6; }
.stat-box:nth-child(5)::before { background: #10b981; }
.stat-box:nth-child(6)::before { background: #64748b; }

.stat-box:hover {
  transform: translateY(-4px) !important;
  background: rgba(255, 255, 255, 0.85) !important;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.06), 0 4px 6px -2px rgba(0, 0, 0, 0.03) !important;
}

.stat-box span {
  color: #64748b !important;
  font-size: 13px !important;
  font-weight: 500 !important;
}

.stat-box strong {
  font-size: 24px !important;
  color: #1e293b !important;
  font-weight: 700 !important;
  font-family: "Inter", "Outfit", sans-serif !important;
}
.table-wrap {
  overflow-x: auto;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02), 0 10px 15px -3px rgba(0, 0, 0, 0.04);
}
.table {
  width: 100%;
  border-collapse: collapse;
  min-width: 1400px;
  table-layout: fixed;
}
.table th, .table td {
  padding: 14px 12px !important;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  text-align: left;
  vertical-align: middle !important;
}

/* colgroup 列宽物理比例控制 */
.col-checkbox { width: 50px !important; }
.col-order { width: 130px !important; }
.col-shipment { width: 120px !important; }
.col-plate { width: 100px !important; }
.col-supply { width: 160px !important; }
.col-station { width: 160px !important; }
.col-model { width: 130px !important; }
.col-qty { width: 105px !important; }
.col-status { width: 150px !important; }
.col-time { width: 160px !important; }
.col-elapsed { width: 110px !important; }

/* 单元格精细对齐与样式 */
.cell-checkbox {
  text-align: center !important;
  justify-content: center !important;
  width: 50px !important;
  padding: 14px 6px !important;
}
.cell-checkbox input[type="checkbox"] {
  cursor: pointer;
  width: 16px;
  height: 16px;
  border-radius: 4px;
  accent-color: #3b82f6;
  vertical-align: middle;
}
.cell-code-wrapper {
  text-align: left !important;
  white-space: nowrap !important;
}
.cell-code {
  font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace !important;
  font-size: 12.5px !important;
  background: #f1f5f9;
  color: #475569;
  padding: 3px 8px !important;
  border-radius: 6px;
  border: 1px solid rgba(15, 23, 42, 0.05);
  font-weight: 500;
  display: inline-block;
}
.cell-plate {
  min-width: 90px !important;
  width: 100px !important;
  text-align: center !important;
  white-space: nowrap !important;
}
.cell-plate-header {
  text-align: center !important;
}
.plate-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #eff6ff;
  color: #1e40af;
  border: 1px solid #bfdbfe;
  font-family: "Inter", "Outfit", -apple-system, sans-serif;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
  letter-spacing: 0.5px;
}
.cell-supply, .cell-station {
  max-width: 160px !important;
  min-width: 120px !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  color: #334155 !important;
  font-size: 13px !important;
}
.cell-model {
  max-width: 130px !important;
  min-width: 100px !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  font-weight: 500;
  color: #0f172a;
}
.cell-number {
  text-align: right !important;
  font-variant-numeric: tabular-nums;
  font-family: "JetBrains Mono", "Fira Code", monospace;
  font-size: 13.5px !important;
  font-weight: 600 !important;
  color: #0f172a !important;
  white-space: nowrap !important;
}
th.cell-number {
  text-align: right !important;
  font-family: inherit !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  color: #1e293b !important;
}
.cell-status {
  min-width: 140px !important;
  width: 150px !important;
  white-space: nowrap !important;
}
.cell-datetime {
  font-family: "Inter", -apple-system, sans-serif !important;
  font-size: 13px !important;
  color: #475569 !important;
  white-space: nowrap !important;
}
.cell-elapsed {
  font-family: "Inter", -apple-system, sans-serif !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  color: #2563eb !important;
  white-space: nowrap !important;
}

.table thead th {
  background: #f8fafc !important;
  color: #1e293b !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  letter-spacing: 0.5px;
  border-bottom: 2px solid #e2e8f0 !important;
  white-space: nowrap !important;
}
.table tbody tr {
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.table tbody tr:hover {
  background: rgba(59, 130, 246, 0.02) !important;
}
.table tbody tr.checked {
  background: rgba(59, 130, 246, 0.04) !important;
}
.table tbody tr.active {
  background: rgba(59, 130, 246, 0.08) !important;
}
.table tbody tr.active td {
  border-bottom-color: rgba(59, 130, 246, 0.15);
}
.table tbody tr.active td:first-child {
  position: relative;
}
.table tbody tr.active td:first-child::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 4px;
  background: #2563eb;
}

.tiny { padding: 6px 10px; font-size: 12px; }
.status-pill { display: inline-flex; align-items: center; padding: 5px 10px; border-radius: 999px; font-size: 12px; line-height: 1; border: 1px solid transparent; font-weight: 500; }
.status-pill-group { display: inline-flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.status-warn { background: #fff7ed; color: #c2410c; border-color: #fed7aa; }
.status-info { background: #eff6ff; color: #1d4ed8; border-color: #bfdbfe; }
.status-secondary { background: #f5f3ff; color: #6d28d9; border-color: #ddd6fe; }
.status-success { background: #ecfdf5; color: #047857; border-color: #a7f3d0; }
.status-danger { background: #fef2f2; color: #b91c1c; border-color: #fecaca; }
.status-neutral { background: #f8fafc; color: #475569; border-color: #e2e8f0; }
.status-abnormal {
  background: #fff1f2 !important;
  color: #e11d48 !important;
  border-color: #ffe4e6 !important;
  font-weight: 600 !important;
  animation: abnormal-pulse 2s infinite ease-in-out;
}
@keyframes abnormal-pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.03); }
  100% { transform: scale(1); }
}
.action-panel { display: flex; flex-direction: column; gap: 16px; }
.action-summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.action-summary > div { display: flex; flex-direction: column; gap: 8px; padding: 12px 14px; border-radius: 12px; background: rgba(248, 250, 252, 0.85); border: 1px solid rgba(15, 23, 42, 0.08); }
.action-summary span { color: var(--muted); font-size: 13px; }
.action-summary strong { font-size: 15px; }

@media (max-width: 1180px) {
  .filter-grid, .form-grid, .stats-grid, .action-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 720px) {
  .filter-grid, .form-grid, .stats-grid, .action-summary { grid-template-columns: 1fr; }
  .topbar { flex-direction: column; }
  .topbar-actions, .filter-actions, .form-actions { width: 100%; justify-content: stretch; }
  .topbar-actions .btn, .filter-actions .btn, .form-actions .btn { width: 100%; }
}

/* 按钮 Premium 居中与防折行加固 */
.btn, .primary-button, .button {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  text-align: center !important;
  white-space: nowrap !important;
  word-break: keep-all !important;
  box-sizing: border-box !important;
}
</style>
