<template>
  <div class="tube-page-root">
    <AppHeader />
    <main class="tube-page-main container">
      <Breadcrumbs :items="breadcrumbItems" />
      <header class="topbar">
        <div>
          <h2>供给侧管理入口</h2>
          <p class="sub">
            面向供给主体，完成需求与缺口查看、发货登记、发货进度查询与发货撤销。涉及数量口径时，当前页面统一以“米”为计量单位。
          </p>
        </div>
        <div class="topbar-actions">
          <button type="button" class="btn ghost" @click="goProjectPages">返回功能页</button>
        </div>
      </header>

      <p v-if="errorMessage" class="page-error">{{ errorMessage }}</p>

      <section class="card elevated">
        <div class="panel-title-row">
          <div>
            <h2>保温管供需明细</h2>
            <span class="panel-hint">{{ supplyDemandTableHint }}</span>
          </div>
          <div class="toolbar-actions">
            <p v-if="actionMessage" :class="['action-message', actionMessage.type]">{{ actionMessage.text }}</p>
            <button type="button" class="btn ghost" :disabled="summaryLoading" @click="loadDemandSummary">刷新明细</button>
          </div>
        </div>

        <div v-if="optionsError" class="error-box">{{ optionsError }}</div>

        <div class="supply-demand-toolbar">
          <label class="field field-compact">
            <span>当前供给主体</span>
            <input :value="currentSupplyEntityLabel" type="text" disabled />
          </label>

          <label class="field field-compact">
            <span>业务日期</span>
            <input :value="bizDate" type="date" disabled />
          </label>

          <label class="field field-compact">
            <span>计划起始日期</span>
            <input :value="planStartDate" type="date" disabled />
          </label>

          <label class="field field-compact">
            <span>视图模式</span>
            <select v-model="supplyDemandViewMode" :disabled="summaryLoading || optionsLoading">
              <option v-for="option in supplyDemandViewOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>

          <div class="field field-compact">
            <span>型号筛选</span>
            <details class="multi-select-dropdown">
              <summary class="multi-select-summary">{{ selectedPipeModelSummaryLabel }}</summary>
              <div class="multi-select-panel">
                <div class="multi-select-actions">
                  <button type="button" class="btn ghost btn-xs" @click.prevent="selectAllPipeModels">全部型号</button>
                  <button type="button" class="btn ghost btn-xs" @click.prevent="clearPipeModelSelection">清空勾选</button>
                </div>
                <label v-for="pipe in pipeModelOptions" :key="pipe.pipe_model_id" class="checkbox-option">
                  <input v-model="selectedPipeModelIds" type="checkbox" :value="pipe.pipe_model_id" />
                  <span>{{ pipe.pipe_model_name }}</span>
                </label>
              </div>
            </details>
          </div>
        </div>

        <div v-if="summaryLoading" class="loading-text">正在加载需求汇总...</div>
        <div v-else-if="summaryError" class="error-box">{{ summaryError }}</div>
        <div v-else-if="!supplyDemandTableRows.length" class="empty-box">当前没有可展示的供需明细数据。</div>
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>{{ supplyDemandViewMode === 'summary' ? '统计范围' : '换热站' }}</th>
                <th>型号</th>
                <th>设计总量（米）</th>
                <th>计划采购总量（米）</th>
                <th>未来三日计划（米）</th>
                <th>已发货待到货（米）</th>
                <th>已到货待接收（米）</th>
                <th>已接收待库管（米）</th>
                <th>三日净缺口（米）</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in supplyDemandTableRows" :key="row.rowKey">
                <td>{{ row.scopeLabel }}</td>
                <td>{{ row.pipeModelName }}</td>
                <td>{{ formatNumber(row.designQty) }}</td>
                <td>{{ formatNumber(row.purchasePlanQty) }}</td>
                <td>{{ formatNumber(row.futurePlanQty) }}</td>
                <td>{{ formatNumber(row.pendingArrivalQty) }}</td>
                <td>{{ formatNumber(row.pendingReceiveQty) }}</td>
                <td>{{ formatNumber(row.pendingWarehouseQty) }}</td>
                <td :class="{ 'danger-text': row.netGapQty > 0 }">{{ formatNumber(row.netGapQty) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card elevated">
        <div class="panel-title-row">
          <div>
            <h2>发货登记</h2>
            <span class="panel-hint">新增发货后，记录将进入“已发货待到货”状态。计量单位：米。</span>
          </div>
          <button
            type="button"
            class="primary-button"
            :disabled="submitDeliveryLoading || !canSubmitCurrentProject || !selectedSupplyEntityId"
            @click="submitDelivery"
          >
            {{ submitDeliveryLoading ? '提交中...' : '提交发货记录' }}
          </button>
        </div>

        <div class="filter-grid">
          <label class="field">
            <span>供给主体</span>
            <input
              v-if="!canSwitchSupplyEntity"
              :value="currentDeliverySupplyEntityLabel"
              type="text"
              disabled
            />
            <select v-else v-model="deliveryForm.supplyEntityId" :disabled="!selectedSupplyEntityId || !canSwitchSupplyEntity">
              <option v-for="entity in supplyEntityOptions" :key="entity.entity_id" :value="entity.entity_id">
                {{ entity.entity_name }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>换热站</span>
            <select v-model="deliveryForm.stationId">
              <option value="" disabled>请选择换热站</option>
              <option v-for="station in stationOptions" :key="station.station_id" :value="station.station_id">
                {{ station.station_name }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>保温管型号</span>
            <select v-model="deliveryForm.pipeModelId">
              <option value="" disabled>请选择型号</option>
              <option v-for="pipe in pipeModelOptions" :key="pipe.pipe_model_id" :value="pipe.pipe_model_id">
                {{ pipe.pipe_model_name }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>发货量（米）</span>
            <input v-model.number="deliveryForm.shippedQty" type="number" min="0" step="1" />
          </label>

          <label class="field">
            <span>发货时间</span>
            <input v-model="deliveryForm.shippedAt" type="datetime-local" />
          </label>

          <label class="field">
            <span>联系人</span>
            <input v-model.trim="deliveryForm.shipContactName" type="text" maxlength="50" placeholder="发货联系人" />
          </label>

          <label class="field">
            <span>联系电话</span>
            <input v-model.trim="deliveryForm.shipContactPhone" type="text" maxlength="30" placeholder="联系电话" />
          </label>

          <label class="field field-span-2">
            <span>备注</span>
            <input v-model.trim="deliveryForm.shipRemark" type="text" maxlength="120" placeholder="发货备注" />
          </label>
        </div>
      </section>

      <section class="card elevated">
        <div class="panel-title-row">
          <div>
            <h2>发货记录</h2>
            <span class="panel-hint">仅“已发货待到货”状态允许撤销。计量单位：米。</span>
          </div>
          <button type="button" class="btn ghost" :disabled="deliveriesLoading" @click="loadDeliveries">刷新记录</button>
        </div>

        <div v-if="deliveriesLoading" class="loading-text">正在加载发货记录...</div>
        <div v-else-if="deliveriesError" class="error-box">{{ deliveriesError }}</div>
        <div v-else-if="!deliveryRows.length" class="empty-box">当前没有发货记录。</div>
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>单号</th>
                <th>供给主体</th>
                <th>换热站</th>
                <th>型号</th>
                <th>发货量（米）</th>
                <th>发货时间</th>
                <th>在途时长</th>
                <th>状态</th>
                <th>备注</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in deliveryRows" :key="row.deliveryId">
                <td>{{ row.deliveryCode }}</td>
                <td>{{ row.supplyEntityName }}</td>
                <td>{{ row.stationName }}</td>
                <td>{{ row.pipeModelName }}</td>
                <td>{{ formatNumber(row.shippedQty) }}</td>
                <td>{{ row.shippedAtDisplay || '—' }}</td>
                <td>{{ formatDeliveryElapsedDisplay(row) }}</td>
                <td>
                  <span :class="['status-chip', `status-${row.status}`]">{{ row.statusLabel }}</span>
                </td>
                <td>{{ row.shipRemark || row.cancelReason || '—' }}</td>
                <td>
                  <button
                    v-if="row.status === 'pending_arrival'"
                    type="button"
                    class="btn danger-ghost"
                    :disabled="cancelLoadingIds[row.deliveryId]"
                    @click="cancelDelivery(row)"
                  >
                    {{ cancelLoadingIds[row.deliveryId] ? '撤销中...' : '撤销发货' }}
                  </button>
                  <span v-else class="muted-text">不可撤销</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useAuthStore } from '../../daily_report_25_26/store/auth'
import { AppHeader, Breadcrumbs, useTubePageShell, useTubeRealtimeRefresh } from './shared'
import {
  cancelTubeSupplyManagementDelivery,
  createTubeSupplyManagementDelivery,
  getTubeSupplyManagementDeliveries,
  getTubeSupplyManagementDemandSummary,
  getTubeSupplyManagementOptions,
} from '../../daily_report_25_26/services/api'

const PROJECT_KEY = 'insulation_pipe_supply_2026'
const auth = useAuthStore()

const {
  loading,
  errorMessage,
  breadcrumbItems,
  goProjectPages,
} = useTubePageShell('供给侧管理入口')

const optionsLoading = ref(false)
const optionsError = ref('')
const supplyEntityOptions = ref([])
const stationOptions = ref([])
const pipeModelOptions = ref([])
const currentGroup = ref('')
const currentSupplyEntityIds = ref([])
const bizDate = ref('')
const planStartDate = ref('')

const selectedSupplyEntityId = ref('')
const supplyDemandViewMode = ref('summary')
const selectedPipeModelIds = ref([])

const summaryLoading = ref(false)
const summaryError = ref('')
const summaryRows = ref([])

const deliveriesLoading = ref(false)
const deliveriesError = ref('')
const deliveryRows = ref([])
const cancelLoadingIds = ref({})
const nowTick = ref(Date.now())
let nowTimer = null

const submitDeliveryLoading = ref(false)
const actionMessage = ref(null)

const deliveryForm = ref(createDefaultDeliveryForm())

const canSubmitCurrentProject = computed(() => auth.canSubmitFor(PROJECT_KEY))
const canSwitchSupplyEntity = computed(() => currentGroup.value === 'Global_admin')

const currentGroupLabel = computed(() => {
  if (!currentGroup.value) return '未识别'
  if (currentGroup.value === 'Global_admin') return '全局管理员'
  if (currentGroup.value === 'tube_supplier') return '供给主体'
  return currentGroup.value
})

const currentSupplyEntityLabel = computed(() => {
  const matched = supplyEntityOptions.value.find((item) => item.entity_id === selectedSupplyEntityId.value)
  return matched?.entity_name || '未识别'
})

const currentDeliverySupplyEntityLabel = computed(() => {
  const matched = supplyEntityOptions.value.find((item) => item.entity_id === deliveryForm.value.supplyEntityId)
  return matched?.entity_name || currentSupplyEntityLabel.value
})

const supplyDemandViewOptions = computed(() => [
  { value: 'summary', label: '整理汇总' },
  { value: 'all_details', label: '全部换热站明细' },
  ...stationOptions.value.map((station) => ({
    value: station.station_id,
    label: station.station_name,
  })),
])

const activePipeModelIds = computed(() => {
  if (!selectedPipeModelIds.value.length) {
    return pipeModelOptions.value.map((item) => item.pipe_model_id)
  }
  return selectedPipeModelIds.value
})

const selectedPipeModelSummaryLabel = computed(() => {
  const total = pipeModelOptions.value.length
  const selectedCount = activePipeModelIds.value.length
  if (!total || selectedCount === total) {
    return '全部型号'
  }
  if (selectedCount === 1) {
    const matched = pipeModelOptions.value.find((item) => item.pipe_model_id === activePipeModelIds.value[0])
    return matched?.pipe_model_name || '已选1个型号'
  }
  return `已选${selectedCount}个型号`
})

const pipeModelFilteredSummaryRows = computed(() => {
  const activeIds = new Set(activePipeModelIds.value)
  return summaryRows.value.filter((row) => activeIds.has(row.pipeModelId))
})

const filteredSummaryRows = computed(() => {
  if (supplyDemandViewMode.value === 'summary' || supplyDemandViewMode.value === 'all_details') {
    return pipeModelFilteredSummaryRows.value
  }
  return pipeModelFilteredSummaryRows.value.filter((row) => row.stationId === supplyDemandViewMode.value)
})

const aggregatedSummaryRows = computed(() => {
  const grouped = new Map()
  filteredSummaryRows.value.forEach((row) => {
    const existing = grouped.get(row.pipeModelId) || {
      rowKey: `summary-${row.pipeModelId}`,
      scopeLabel: '汇总',
      pipeModelId: row.pipeModelId,
      pipeModelName: row.pipeModelName,
      designQty: 0,
      purchasePlanQty: 0,
      futurePlanQty: 0,
      pendingArrivalQty: 0,
      pendingReceiveQty: 0,
      pendingWarehouseQty: 0,
      netGapQty: 0,
    }
    existing.designQty += Number(row.designQty || 0)
    existing.purchasePlanQty += Number(row.purchasePlanQty || 0)
    existing.futurePlanQty += Number(row.futurePlanQty || 0)
    existing.pendingArrivalQty += Number(row.pendingArrivalQty || 0)
    existing.pendingReceiveQty += Number(row.pendingReceiveQty || 0)
    existing.pendingWarehouseQty += Number(row.pendingWarehouseQty || 0)
    existing.netGapQty += Number(row.netGapQty || 0)
    grouped.set(row.pipeModelId, existing)
  })
  return Array.from(grouped.values()).sort((a, b) => a.pipeModelName.localeCompare(b.pipeModelName, 'zh-CN'))
})

const supplyDemandTableRows = computed(() => {
  if (supplyDemandViewMode.value === 'summary') {
    return aggregatedSummaryRows.value
  }
  return filteredSummaryRows.value.map((row) => ({
    ...row,
    rowKey: `${row.stationId}-${row.pipeModelId}`,
    scopeLabel: row.stationName,
  }))
})

const supplyDemandTableHint = computed(() => {
  if (supplyDemandViewMode.value === 'summary') {
    return '当前以“整理汇总”方式按型号统计各项供需数量。计量单位：米。'
  }
  if (supplyDemandViewMode.value === 'all_details') {
    return '当前展示全部换热站的逐站逐型号明细。计量单位：米。'
  }
  const matched = stationOptions.value.find((item) => item.station_id === supplyDemandViewMode.value)
  return `当前仅展示 ${matched?.station_name || '所选换热站'} 的各型号供需记录。计量单位：米。`
})

function createDefaultDeliveryForm() {
  return {
    supplyEntityId: '',
    stationId: '',
    pipeModelId: '',
    shippedQty: 0,
    shippedAt: toDateTimeLocalString(new Date()),
    shipContactName: '',
    shipContactPhone: '',
    shipRemark: '',
  }
}

function clearActionMessage() {
  actionMessage.value = null
}

function setActionMessage(type, text) {
  actionMessage.value = { type, text }
}

function selectAllPipeModels() {
  selectedPipeModelIds.value = pipeModelOptions.value.map((item) => item.pipe_model_id)
}

function clearPipeModelSelection() {
  selectedPipeModelIds.value = []
}

function formatNumber(value) {
  const numeric = Number(value ?? 0)
  if (!Number.isFinite(numeric)) return '0'
  if (Math.abs(numeric - Math.round(numeric)) < 0.0001) return String(Math.round(numeric))
  return numeric.toFixed(2)
}

function toDateTimeLocalString(input) {
  const source = input instanceof Date ? input : new Date(input)
  if (Number.isNaN(source.getTime())) return ''
  const pad = (value) => String(value).padStart(2, '0')
  return `${source.getFullYear()}-${pad(source.getMonth() + 1)}-${pad(source.getDate())}T${pad(source.getHours())}:${pad(source.getMinutes())}`
}

function formatDateTimeDisplay(value) {
  if (!value) return ''
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    const normalized = String(value).replace('T', ' ')
    return normalized.slice(0, 16)
  }
  return toDateTimeLocalString(parsed).replace('T', ' ')
}

function normalizeOptionsPayload(response) {
  return {
    currentGroup: response.user?.group || '',
    supplyEntities: response.supply_entities || [],
    stations: response.stations || [],
    pipeModels: response.pipe_models || [],
    bizDate: response.biz_date || '',
    planStartDate: response.plan_start_date || '',
    currentSupplyEntityIds: response.current_supply_entity_ids || [],
  }
}

function normalizeSummaryRows(rows) {
  return (rows || []).map((row) => ({
    stationId: row.station_id || '',
    stationName: row.station_name || row.station_id || '未命名换热站',
    pipeModelId: row.pipe_model_id || '',
    pipeModelName: row.pipe_model_name || row.pipe_model_id || '未命名型号',
    designQty: Number(row.design_qty ?? 0),
    purchasePlanQty: Number(row.purchase_plan_qty ?? 0),
    futurePlanQty: Number(row.future_plan_qty ?? 0),
    pendingArrivalQty: Number(row.pending_arrival_qty ?? 0),
    pendingReceiveQty: Number(row.pending_receive_qty ?? 0),
    pendingWarehouseQty: Number(row.pending_warehouse_qty ?? 0),
    netGapQty: Number(row.net_gap_qty ?? 0),
  }))
}

function getStatusLabel(status) {
  if (status === 'pending_arrival') return '已发货待到货'
  if (status === 'pending_receive') return '已到货待接收'
  if (status === 'pending_warehouse') return '已接收待库管确认'
  if (status === 'completed') return '已完成'
  if (status === 'cancelled') return '已撤销'
  return status || '未知状态'
}

function normalizeDeliveryRows(rows) {
  return (rows || []).map((row) => ({
    deliveryId: Number(row.id ?? 0),
    deliveryCode: row.delivery_code || `DEL-${String(row.id ?? '').padStart(5, '0')}`,
    supplyEntityId: row.supply_entity_id || '',
    supplyEntityName: row.supply_entity_name || row.supply_entity_id || '—',
    stationId: row.station_id || '',
    stationName: row.station_name || row.station_id || '—',
    pipeModelId: row.pipe_model_id || '',
    pipeModelName: row.pipe_model_name || row.pipe_model_id || '—',
    shippedQty: Number(row.shipped_qty ?? 0),
    shippedAt: row.shipped_at || '',
    shippedAtDisplay: formatDateTimeDisplay(row.shipped_at || ''),
    deliveryElapsedLabel: row.delivery_elapsed_label || '',
    shipContactName: row.ship_contact_name || '',
    shipContactPhone: row.ship_contact_phone || '',
    shipRemark: row.ship_remark || '',
    status: row.status || '',
    statusLabel: getStatusLabel(row.status || ''),
    cancelReason: row.cancel_reason || '',
  }))
}

async function loadOptions() {
  optionsLoading.value = true
  optionsError.value = ''
  try {
    const response = await getTubeSupplyManagementOptions(PROJECT_KEY)
    const normalized = normalizeOptionsPayload(response)
    currentGroup.value = normalized.currentGroup
    supplyEntityOptions.value = normalized.supplyEntities
    stationOptions.value = normalized.stations
    pipeModelOptions.value = normalized.pipeModels
    currentSupplyEntityIds.value = normalized.currentSupplyEntityIds
    bizDate.value = normalized.bizDate
    planStartDate.value = normalized.planStartDate
    const availableSupplyEntityIds = normalized.currentSupplyEntityIds
    if (!availableSupplyEntityIds.includes(selectedSupplyEntityId.value)) {
      selectedSupplyEntityId.value = availableSupplyEntityIds[0] || ''
    } else if (!canSwitchSupplyEntity.value && normalized.currentSupplyEntityIds.length) {
      selectedSupplyEntityId.value = normalized.currentSupplyEntityIds[0]
    } else if (!selectedSupplyEntityId.value && normalized.currentSupplyEntityIds.length) {
      selectedSupplyEntityId.value = normalized.currentSupplyEntityIds[0]
    }
    if (!canSwitchSupplyEntity.value && selectedSupplyEntityId.value) {
      deliveryForm.value.supplyEntityId = selectedSupplyEntityId.value
    } else if (!deliveryForm.value.supplyEntityId && selectedSupplyEntityId.value) {
      deliveryForm.value.supplyEntityId = selectedSupplyEntityId.value
    }
    const stationIdSet = new Set(stationOptions.value.map((item) => String(item.station_id || '')))
    const pipeModelIdSet = new Set(pipeModelOptions.value.map((item) => String(item.pipe_model_id || '')))
    if (!stationIdSet.has(deliveryForm.value.stationId)) {
      deliveryForm.value.stationId = stationOptions.value[0]?.station_id || ''
    }
    if (!pipeModelIdSet.has(deliveryForm.value.pipeModelId)) {
      deliveryForm.value.pipeModelId = pipeModelOptions.value[0]?.pipe_model_id || ''
    }
    selectedPipeModelIds.value = selectedPipeModelIds.value.filter((item) => pipeModelIdSet.has(String(item || '')))
    if (!selectedPipeModelIds.value.length) {
      selectAllPipeModels()
    }
  } catch (error) {
    optionsError.value = error?.message || '读取供给侧配置失败'
  } finally {
    optionsLoading.value = false
  }
}

async function loadDemandSummary() {
  summaryLoading.value = true
  summaryError.value = ''
  try {
    const response = await getTubeSupplyManagementDemandSummary(PROJECT_KEY)
    summaryRows.value = normalizeSummaryRows(response.rows)
  } catch (error) {
    summaryError.value = error?.message || '读取供给侧需求汇总失败'
    summaryRows.value = []
  } finally {
    summaryLoading.value = false
  }
}

async function refreshRealtimeConfig() {
  await loadOptions()
  await Promise.all([loadDemandSummary(), loadDeliveries()])
}

async function loadDeliveries() {
  deliveriesLoading.value = true
  deliveriesError.value = ''
  try {
    const response = await getTubeSupplyManagementDeliveries(PROJECT_KEY, {
      supplyEntityId: selectedSupplyEntityId.value,
    })
    deliveryRows.value = normalizeDeliveryRows(response.rows)
  } catch (error) {
    deliveriesError.value = error?.message || '读取供给侧发货记录失败'
    deliveryRows.value = []
  } finally {
    deliveriesLoading.value = false
  }
}

async function submitDelivery() {
  if (!deliveryForm.value.supplyEntityId || !deliveryForm.value.stationId || !deliveryForm.value.pipeModelId) {
    setActionMessage('error', '请先完整选择供给主体、换热站和保温管型号。')
    return
  }
  if (Number(deliveryForm.value.shippedQty || 0) <= 0) {
    setActionMessage('error', '发货量必须大于 0。')
    return
  }
  if (!deliveryForm.value.shippedAt) {
    setActionMessage('error', '请填写发货时间。')
    return
  }

  submitDeliveryLoading.value = true
  clearActionMessage()
  try {
    const response = await createTubeSupplyManagementDelivery(PROJECT_KEY, {
      supply_entity_id: deliveryForm.value.supplyEntityId,
      station_id: deliveryForm.value.stationId,
      pipe_model_id: deliveryForm.value.pipeModelId,
      shipped_qty: Number(deliveryForm.value.shippedQty || 0),
      shipped_at: new Date(deliveryForm.value.shippedAt).toISOString(),
      ship_contact_name: deliveryForm.value.shipContactName || '',
      ship_contact_phone: deliveryForm.value.shipContactPhone || '',
      ship_remark: deliveryForm.value.shipRemark || '',
    })
    const deliveryCode = response?.delivery_code || response?.deliveryCode || ''
    setActionMessage('success', deliveryCode ? `发货记录 ${deliveryCode} 已提交。` : '发货记录已提交。')
    const currentSupplyEntityId = deliveryForm.value.supplyEntityId
    deliveryForm.value = createDefaultDeliveryForm()
    deliveryForm.value.supplyEntityId = currentSupplyEntityId
    await Promise.all([loadDemandSummary(), loadDeliveries()])
  } catch (error) {
    setActionMessage('error', error?.message || '提交发货记录失败')
  } finally {
    submitDeliveryLoading.value = false
  }
}

async function cancelDelivery(row) {
  if (!row?.deliveryId) return
  cancelLoadingIds.value = {
    ...cancelLoadingIds.value,
    [row.deliveryId]: true,
  }
  clearActionMessage()
  try {
    await cancelTubeSupplyManagementDelivery(PROJECT_KEY, row.deliveryId, {
      cancel_reason: '供给侧主动撤销发货',
    })
    setActionMessage('success', `发货记录 ${row.deliveryCode} 已撤销。`)
    await Promise.all([loadDemandSummary(), loadDeliveries()])
  } catch (error) {
    setActionMessage('error', error?.message || '撤销发货记录失败')
  } finally {
    cancelLoadingIds.value = {
      ...cancelLoadingIds.value,
      [row.deliveryId]: false,
    }
  }
}

watch(selectedSupplyEntityId, (value) => {
  if (value) {
    deliveryForm.value.supplyEntityId = value
    const matchedEntity = supplyEntityOptions.value.find((item) => item.entity_id === value)
    if (matchedEntity) {
      if (!deliveryForm.value.shipContactName) {
        deliveryForm.value.shipContactName = matchedEntity.contact_name || ''
      }
      if (!deliveryForm.value.shipContactPhone) {
        deliveryForm.value.shipContactPhone = matchedEntity.contact_phone || ''
      }
    }
  }
})

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

function formatDeliveryElapsedDisplay(row) {
  if (!row || row.status === 'cancelled') return '—'
  return row.deliveryElapsedLabel || formatElapsedLabel(row.shippedAt) || '—'
}

watch(
  () => deliveryForm.value.supplyEntityId,
  (value) => {
    if (canSwitchSupplyEntity.value && value && value !== selectedSupplyEntityId.value) {
      selectedSupplyEntityId.value = value
      return
    }
    if (!canSwitchSupplyEntity.value && selectedSupplyEntityId.value && value !== selectedSupplyEntityId.value) {
      deliveryForm.value.supplyEntityId = selectedSupplyEntityId.value
    }
  },
)

watch(selectedSupplyEntityId, () => {
  if (selectedSupplyEntityId.value) {
    loadDeliveries()
  }
})

onMounted(async () => {
  nowTimer = setInterval(() => {
    nowTick.value = Date.now()
  }, 60000)
  await refreshRealtimeConfig()
})

useTubeRealtimeRefresh(refreshRealtimeConfig)

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
.topbar-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.page-error { margin: 0; color: var(--danger); }

.panel-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.panel-title-row h2 {
  margin: 0;
  color: #0f172a;
  font-size: 18px;
}

.panel-hint {
  color: #64748b;
  font-size: 13px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.supply-demand-toolbar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: #334155;
  font-size: 14px;
}

.field-compact {
  min-width: 0;
}

.field-span-2 {
  grid-column: span 2;
}

.field span {
  font-size: 13px;
  color: #475569;
  font-weight: 600;
}

.field select,
.field input,
.number-input {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
  color: #0f172a;
  background: #fff;
  box-sizing: border-box;
}

.field input[disabled] {
  color: #475569;
  background: #f8fafc;
}

.field select:focus,
.field input:focus,
.number-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.meta-chip,
.status-chip {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 600;
}

.meta-chip {
  background: #eef2ff;
  color: #334155;
}

.status-chip {
  background: #e2e8f0;
  color: #334155;
}

.status-pending_arrival { background: #dbeafe; color: #1d4ed8; }
.status-pending_receive { background: #fef3c7; color: #92400e; }
.status-pending_warehouse { background: #ede9fe; color: #6d28d9; }
.status-completed { background: #dcfce7; color: #166534; }
.status-cancelled { background: #fee2e2; color: #b91c1c; }

.loading-text,
.empty-box {
  padding: 14px 16px;
  text-align: center;
  color: #475569;
  background: #f8fafc;
  border-radius: 10px;
  font-size: 14px;
}

.error-box {
  border-radius: 10px;
  background: #fff1f2;
  color: #be123c;
  padding: 14px 16px;
  font-size: 14px;
}

.table-wrap {
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fff;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 880px;
}

.data-table th,
.data-table td {
  border-bottom: 1px solid #e2e8f0;
  padding: 12px;
  text-align: left;
  vertical-align: top;
  font-size: 14px;
}

.data-table th {
  color: #334155;
  font-weight: 600;
  background: #f8fafc;
}

.data-table tr:last-child td {
  border-bottom: none;
}

.primary-button {
  border-radius: 10px;
  padding: 10px 16px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
  border: 1px solid #2563eb;
  background: #2563eb;
  color: #fff;
  font-weight: 600;
  white-space: nowrap;
}

.primary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn {
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 10px 14px;
  background: #fff;
  color: #0f172a;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn.ghost {
  background: #fff;
}

.btn.btn-xs {
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 12px;
}

.btn.danger-ghost {
  border-color: #fecaca;
  color: #b91c1c;
  background: #fff5f5;
}

.action-message {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.action-message.success { color: #166534; }
.action-message.error { color: #be123c; }
.danger-text { color: #b91c1c; font-weight: 700; }
.muted-text { color: #64748b; }

.multi-select-dropdown {
  position: relative;
}

.multi-select-summary {
  list-style: none;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 10px 12px;
  background: #fff;
  color: #0f172a;
  font-size: 14px;
  cursor: pointer;
  user-select: none;
}

.multi-select-summary::-webkit-details-marker {
  display: none;
}

.multi-select-dropdown[open] .multi-select-summary {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.multi-select-panel {
  position: absolute;
  z-index: 20;
  top: calc(100% + 6px);
  left: 0;
  width: 100%;
  min-width: 220px;
  max-height: 260px;
  overflow: auto;
  border: 1px solid #dbe2ea;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12);
  padding: 10px;
  box-sizing: border-box;
}

.multi-select-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.checkbox-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 6px;
  border-radius: 8px;
  cursor: pointer;
}

.checkbox-option:hover {
  background: #f8fafc;
}

.checkbox-option input {
  width: 16px;
  height: 16px;
  margin: 0;
  flex: 0 0 auto;
}

@media (max-width: 900px) {
  .field-span-2 {
    grid-column: span 1;
  }
}

@media (max-width: 720px) {
  .tube-page-main {
    padding-bottom: 16px;
  }

  .topbar,
  .panel-title-row {
    flex-direction: column;
    align-items: stretch;
  }

  .topbar-actions {
    width: 100%;
  }

  .toolbar-actions {
    width: 100%;
    justify-content: stretch;
  }

  .topbar-actions .btn,
  .toolbar-actions .btn,
  .panel-title-row .btn,
  .panel-title-row .primary-button {
    width: 100%;
    justify-content: center;
  }

  .multi-select-panel {
    position: static;
    width: 100%;
    margin-top: 6px;
    box-shadow: none;
  }
}
</style>
