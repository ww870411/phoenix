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
          <span class="muted">当前日期：{{ options?.biz_date || '--' }}</span>
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
            <thead>
              <tr>
                <th>选择</th>
                <th>编号</th>
                <th>供给主体</th>
                <th>换热站</th>
                <th>型号</th>
                <th>发货量（米）</th>
                <th>到货量（米）</th>
                <th>接收量（米）</th>
                <th>状态</th>
                <th>发货时间</th>
                <th>在途时长</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in deliveries"
                :key="row.id"
                :class="{ selected: String(row.id) === selectedDeliveryId }"
                @click="selectDelivery(row)"
              >
                <td>
                  <button class="btn ghost tiny" type="button" @click.stop="selectDelivery(row)">选中</button>
                </td>
                <td>{{ row.id }}</td>
                <td>{{ row.supply_entity_name }}</td>
                <td>{{ row.station_name }}</td>
                <td>{{ row.pipe_model_name }}</td>
                <td>{{ formatAmount(row.shipped_qty) }}</td>
                <td>{{ formatAmount(row.arrived_qty) }}</td>
                <td>{{ formatAmount(row.received_qty) }}</td>
                <td>
                  <span class="status-pill" :class="statusClass(row.status)">
                    {{ deliveryStatusLabelMap[row.status] || row.status || '--' }}
                  </span>
                </td>
                <td>{{ formatDateTime(row.shipped_at) }}</td>
                <td>{{ formatElapsedLabel(row.shipped_at) || row.delivery_elapsed_label || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card elevated">
        <div class="card-header">选中记录处置</div>
        <div v-if="!selectedDelivery" class="page-state">请选择一条台账记录后再执行确认操作。</div>
        <div v-else class="action-panel">
          <div class="action-summary">
            <div><span>供给主体</span><strong>{{ selectedDelivery.supply_entity_name }}</strong></div>
            <div><span>换热站</span><strong>{{ selectedDelivery.station_name }}</strong></div>
            <div><span>型号</span><strong>{{ selectedDelivery.pipe_model_name }}</strong></div>
            <div><span>当前状态</span><strong>{{ deliveryStatusLabelMap[selectedDelivery.status] || selectedDelivery.status }}</strong></div>
            <div><span>到货状态</span><strong>{{ selectedDelivery.arrived_qty ? '已到货' : '待到货' }}</strong></div>
            <div><span>接收状态</span><strong>{{ selectedDelivery.received_qty ? '已接收' : '待接收' }}</strong></div>
            <div><span>在途时长</span><strong>{{ formatElapsedLabel(selectedDelivery.shipped_at) || selectedDelivery.delivery_elapsed_label || '—' }}</strong></div>
          </div>

          <div v-if="selectedDelivery.status === 'pending_warehouse'" class="form-grid">
            <label class="field field-wide">
              <span>库管备注</span>
              <textarea v-model="warehouseForm.remark" class="textarea" rows="3" placeholder="可填写手续闭环说明"></textarea>
            </label>
            <div class="form-actions">
              <button class="btn primary" type="button" :disabled="actionLoading" @click="submitWarehouse">完成库管确认</button>
            </div>
          </div>

          <div v-else class="page-state compact">当前仅展示前序状态信息，库管确认需在记录到达“已接收待库管”后执行。</div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { AppHeader, Breadcrumbs, useTubePageShell } from './shared'
import {
  confirmTubeWarehouseDeliveryArrival,
  confirmTubeWarehouseDeliveryReceipt,
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

const filters = reactive({
  stationId: '',
  supplyEntityId: '',
  pipeModelId: '',
  status: '',
})

const arrivalForm = reactive({
  arrivedQty: '',
  remark: '',
})

const receiptForm = reactive({
  receivedQty: '',
  remark: '',
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

function formatDateTime(value) {
  if (!value) return '--'
  return String(value).replace('T', ' ').slice(0, 19)
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
  arrivalForm.arrivedQty = String(row.arrived_qty ?? row.shipped_qty ?? '')
  arrivalForm.remark = row.arrived_remark || ''
  receiptForm.receivedQty = String(row.received_qty ?? row.arrived_qty ?? row.shipped_qty ?? '')
  receiptForm.remark = row.received_remark || ''
  warehouseForm.remark = row.warehouse_remark || ''
}

function selectDelivery(row) {
  selectedDeliveryId.value = String(row.id)
  syncActionForms(row)
}

async function loadOptions() {
  const payload = await getTubeWarehouseManagementOptions(projectKey)
  options.value = payload
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
    })
    deliveries.value = Array.isArray(payload?.rows) ? payload.rows : []
    const keepSelected = deliveries.value.find((row) => String(row.id) === selectedDeliveryId.value)
    if (keepSelected) {
      syncActionForms(keepSelected)
    } else if (deliveries.value.length > 0) {
      selectDelivery(deliveries.value[0])
    } else {
      selectedDeliveryId.value = ''
    }
  } catch (error) {
    pageError.value = error?.message || '读取库管台账失败'
    deliveries.value = []
    selectedDeliveryId.value = ''
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
  loadDeliveries()
}

async function submitArrival() {
  if (!selectedDelivery.value) return
  const arrivedQty = Number(arrivalForm.arrivedQty)
  if (!Number.isFinite(arrivedQty) || arrivedQty <= 0) {
    pageError.value = '请先填写有效的到货数量'
    return
  }
  actionLoading.value = true
  pageError.value = ''
  pageMessage.value = ''
  try {
    await confirmTubeWarehouseDeliveryArrival(projectKey, selectedDelivery.value.id, {
      arrived_qty: arrivedQty,
      remark: arrivalForm.remark || '',
    })
    pageMessage.value = '到货确认已提交'
    await loadDeliveries()
  } catch (error) {
    pageError.value = error?.message || '确认到货失败'
  } finally {
    actionLoading.value = false
  }
}

async function submitReceipt() {
  if (!selectedDelivery.value) return
  const receivedQty = Number(receiptForm.receivedQty)
  if (!Number.isFinite(receivedQty) || receivedQty <= 0) {
    pageError.value = '请先填写有效的接收数量'
    return
  }
  actionLoading.value = true
  pageError.value = ''
  pageMessage.value = ''
  try {
    await confirmTubeWarehouseDeliveryReceipt(projectKey, selectedDelivery.value.id, {
      received_qty: receivedQty,
      remark: receiptForm.remark || '',
    })
    pageMessage.value = '施工接收确认已提交'
    await loadDeliveries()
  } catch (error) {
    pageError.value = error?.message || '确认施工接收失败'
  } finally {
    actionLoading.value = false
  }
}

async function submitWarehouse() {
  if (!selectedDelivery.value) return
  actionLoading.value = true
  pageError.value = ''
  pageMessage.value = ''
  try {
    await confirmTubeWarehouseDeliveryWarehouse(projectKey, selectedDelivery.value.id, {
      remark: warehouseForm.remark || '',
    })
    pageMessage.value = '库管确认已提交'
    await loadDeliveries()
  } catch (error) {
    pageError.value = error?.message || '库管确认失败'
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

onBeforeUnmount(() => {
  if (nowTimer) {
    clearInterval(nowTimer)
    nowTimer = null
  }
})
</script>

<style scoped>
.tube-page-root { min-height: 100vh; background: var(--bg); }
.tube-page-main { display: flex; flex-direction: column; gap: 16px; padding-top: 18px; padding-bottom: 24px; }
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
.stats-card { margin-top: 0; }
.stats-grid { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; }
.stat-box { border: 1px solid rgba(15, 23, 42, 0.1); background: rgba(255, 255, 255, 0.7); border-radius: 12px; padding: 14px 12px; display: flex; flex-direction: column; gap: 8px; }
.stat-box span { color: var(--muted); font-size: 13px; }
.stat-box strong { font-size: 22px; color: var(--text); }
.table-wrap { overflow-x: auto; border: 1px solid rgba(15, 23, 42, 0.08); border-radius: 14px; background: #fff; }
.table { width: 100%; border-collapse: collapse; min-width: 1120px; }
.table th, .table td { padding: 12px 14px; border-bottom: 1px solid rgba(15, 23, 42, 0.08); text-align: left; vertical-align: middle; white-space: nowrap; }
.table thead th { background: rgba(37, 99, 235, 0.06); color: var(--text); font-weight: 600; }
.table tbody tr { cursor: pointer; transition: background 0.15s ease; }
.table tbody tr:hover { background: rgba(59, 130, 246, 0.05); }
.table tbody tr.selected { background: rgba(59, 130, 246, 0.1); }
.tiny { padding: 6px 10px; font-size: 12px; }
.status-pill { display: inline-flex; align-items: center; padding: 5px 10px; border-radius: 999px; font-size: 12px; line-height: 1; border: 1px solid transparent; }
.status-warn { background: #fff7ed; color: #c2410c; border-color: #fed7aa; }
.status-info { background: #eff6ff; color: #1d4ed8; border-color: #bfdbfe; }
.status-secondary { background: #f5f3ff; color: #6d28d9; border-color: #ddd6fe; }
.status-success { background: #ecfdf5; color: #047857; border-color: #a7f3d0; }
.status-danger { background: #fef2f2; color: #b91c1c; border-color: #fecaca; }
.status-neutral { background: #f8fafc; color: #475569; border-color: #e2e8f0; }
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
</style>
