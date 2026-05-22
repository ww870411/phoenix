<template>
  <div class="tube-page-root">
    <AppHeader />
    <main class="tube-page-main container">
      <Breadcrumbs :items="breadcrumbItems" />
      <header class="topbar">
        <div>
          <h2>需求侧管理入口</h2>
          <p class="sub">
            面向现场负责人，完成换热站基准量查看、未来三日计划填报、实际使用量填报，以及待确认到货记录查看。涉及数量口径时，当前页面统一以“米”为计量单位。
          </p>
        </div>
        <div class="topbar-actions">
          <button type="button" class="btn ghost" @click="goProjectPages">
            返回功能页
          </button>
        </div>
      </header>

      <p v-if="errorMessage" class="page-error">{{ errorMessage }}</p>

    <section class="card elevated">
      <div class="panel-title-row">
        <h2>筛选条件</h2>
        <p v-if="actionMessage" :class="['action-message', actionMessage.type]">
          {{ actionMessage.text }}
        </p>
      </div>

      <div v-if="optionsError" class="error-box">
        {{ optionsError }}
      </div>

      <div class="filter-grid">
        <label class="field">
          <span>换热站</span>
          <select v-model="selectedStationId" :disabled="optionsLoading || !stationOptions.length">
            <option value="" disabled>请选择换热站</option>
            <option v-for="station in stationOptions" :key="station.station_id" :value="station.station_id">
              {{ station.station_name }}
            </option>
          </select>
        </label>

        <label class="field">
          <span>业务日期</span>
          <input v-model="bizDate" type="date" :disabled="!isGlobalAdmin" />
        </label>
      </div>

      <div class="meta-row">
        <span class="meta-chip">可访问换热站：{{ stationOptions.length }}</span>
        <span class="meta-chip">型号数：{{ pipeModelOptions.length }}</span>
        <span class="meta-chip">角色：{{ currentGroupLabel }}</span>
        <span class="meta-chip">业务日期：{{ bizDate || '未设置' }}</span>
        <span class="meta-chip">计划起始日期：{{ anchorDate || '未设置' }}</span>
        <span class="meta-chip">计划可编辑天数：{{ planEditableDays }}</span>
      </div>
    </section>

    <section class="card elevated">
      <div class="panel-title-row">
        <h2>基准量台账</h2>
        <span class="panel-hint">展示设计总量与计划采购总量，便于对照计划与使用情况。计量单位：米。</span>
      </div>

      <div v-if="baselineLoading" class="loading-text">正在加载基准量...</div>
      <div v-else-if="baselineError" class="error-box">{{ baselineError }}</div>
      <div v-else-if="!baselineRows.length" class="empty-box">当前换热站暂无基准量记录。</div>
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>型号</th>
              <th>设计总量（米）</th>
              <th>计划采购总量（米）</th>
              <th>备注</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in baselineRows" :key="row.pipeModelId">
              <td>{{ row.pipeModelName }}</td>
              <td>{{ formatNumber(row.designQuantity) }}</td>
              <td>{{ formatNumber(row.purchaseQuantity) }}</td>
              <td>{{ row.remarks || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="card elevated">
      <div class="panel-title-row">
        <div>
          <h2>未来三日计划填报</h2>
          <span class="panel-hint">按计划起始日期自动生成连续三天计划，支持逐型号填报。计量单位：米。</span>
        </div>
        <button
          type="button"
          class="primary-button"
          :disabled="planLoading || savePlanLoading || !selectedStationId || !canSubmitCurrentProject || planEditableDays <= 0"
          @click="savePlanMatrix"
        >
          {{ savePlanLoading ? '提交中...' : '提交三日计划量' }}
        </button>
      </div>

      <div v-if="planLoading" class="loading-text">正在加载三日计划...</div>
      <div v-else-if="planError" class="error-box">{{ planError }}</div>
      <div v-else-if="!planRows.length" class="empty-box">当前暂无可填报型号。</div>
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>型号</th>
              <th
                v-for="(date, index) in planDates"
                :key="date"
                :class="{ 'editable-plan-date': isPlanDateEditable(index) }"
              >
                {{ date }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in planRows" :key="row.pipeModelId">
              <td>{{ row.pipeModelName }}</td>
              <td
                v-for="(date, index) in planDates"
                :key="`${row.pipeModelId}-${date}`"
                :class="{ 'editable-plan-date-cell': isPlanDateEditable(index) }"
              >
                <div class="cell-editor" :class="{ 'editable-plan-date-cell': isPlanDateEditable(index) }">
                  <input
                    v-model.number="row.values[date].plannedQty"
                    type="number"
                    min="0"
                    step="1"
                    :disabled="!isPlanDateEditable(index) || !canSubmitCurrentProject"
                  />
                  <input
                    v-model.trim="row.values[date].remarks"
                    type="text"
                    maxlength="120"
                    placeholder="备注"
                    :disabled="!isPlanDateEditable(index) || !canSubmitCurrentProject"
                  />
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="card elevated">
      <div class="panel-title-row">
        <div>
          <h2>{{ bizDate || '未设置' }}实际使用量</h2>
          <span class="panel-hint">逐型号填写当前业务日期对应的实际使用数量。计量单位：米。</span>
        </div>
        <button
          type="button"
          class="primary-button"
          :disabled="usageLoading || saveUsageLoading || !selectedStationId || !canSubmitCurrentProject"
          @click="saveUsageSheet"
        >
          {{ saveUsageLoading ? '提交中...' : '提交实际使用量' }}
        </button>
      </div>

      <div v-if="usageLoading" class="loading-text">正在加载实际使用数据...</div>
      <div v-else-if="usageError" class="error-box">{{ usageError }}</div>
      <div v-else-if="!usageRows.length" class="empty-box">当前暂无可填报型号。</div>
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>型号</th>
              <th>实际使用量（米）</th>
              <th>备注</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in usageRows" :key="row.pipeModelId">
              <td>{{ row.pipeModelName }}</td>
              <td>
                <input
                  v-model.number="row.usedQty"
                  class="number-input"
                  type="number"
                  min="0"
                  step="1"
                />
              </td>
              <td>
                <input
                  v-model.trim="row.remarks"
                  type="text"
                  maxlength="120"
                  placeholder="备注"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="card elevated">
      <div class="panel-title-row">
        <h2>待确认到货记录</h2>
        <span class="panel-hint">只展示当前换热站处于“已发货待到货”状态的记录。计量单位：米。</span>
      </div>

      <div v-if="pendingLoading" class="loading-text">正在加载待确认到货...</div>
      <div v-else-if="pendingError" class="error-box">{{ pendingError }}</div>
      <div v-else-if="!pendingRows.length" class="empty-box">当前没有待确认到货记录。</div>
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>发货单号</th>
              <th>供给主体</th>
              <th>型号</th>
              <th>发货量（米）</th>
              <th>发货时间</th>
              <th>备注</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in pendingRows" :key="row.deliveryId">
              <td>{{ row.deliveryCode || row.deliveryId }}</td>
              <td>{{ row.supplyEntityName }}</td>
              <td>{{ row.pipeModelName }}</td>
              <td>{{ formatNumber(row.shippedQty) }}</td>
              <td>{{ row.shippedAt || '—' }}</td>
              <td>{{ row.remarks || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useAuthStore } from '../../daily_report_25_26/store/auth'
import { AppHeader, Breadcrumbs, useTubePageShell } from './shared'
import {
  getTubeDemandManagementBaseline,
  getTubeDemandManagementOptions,
  getTubeDemandManagementPendingArrivals,
  getTubeDemandManagementPlanMatrix,
  getTubeDemandManagementUsageSheet,
  saveTubeDemandManagementPlanMatrix,
  saveTubeDemandManagementUsageSheet
} from '../../daily_report_25_26/services/api'

const PROJECT_KEY = 'insulation_pipe_supply_2026'

const auth = useAuthStore()
const {
  errorMessage,
  breadcrumbItems,
  goProjectPages
} = useTubePageShell('需求侧管理入口')

const optionsLoading = ref(false)
const optionsError = ref('')
const stationOptions = ref([])
const pipeModelOptions = ref([])
const currentGroup = ref('')

const selectedStationId = ref('')
const bizDate = ref('')
const anchorDate = ref('')
const usageDate = ref('')
const planEditableDays = ref(3)

const baselineLoading = ref(false)
const baselineError = ref('')
const baselineRows = ref([])

const planLoading = ref(false)
const planError = ref('')
const planDates = ref([])
const planRows = ref([])
const savePlanLoading = ref(false)

const usageLoading = ref(false)
const usageError = ref('')
const usageRows = ref([])
const saveUsageLoading = ref(false)

const pendingLoading = ref(false)
const pendingError = ref('')
const pendingRows = ref([])

const actionMessage = ref(null)
const canSubmitCurrentProject = computed(() => auth.canSubmitFor(PROJECT_KEY))
const isGlobalAdmin = computed(() => currentGroup.value === 'Global_admin')

const currentGroupLabel = computed(() => {
  if (!currentGroup.value) {
    return '未识别'
  }
  if (currentGroup.value === 'Global_admin') {
    return '全局管理员'
  }
  return currentGroup.value
})

function isPlanDateEditable(index) {
  const editableDays = Number(planEditableDays.value ?? 0)
  if (editableDays <= 0) {
    return false
  }
  return index >= planDates.value.length - editableDays
}

function getTodayString(offsetDays = 0) {
  const today = new Date()
  today.setDate(today.getDate() + offsetDays)
  return today.toISOString().slice(0, 10)
}

function setActionMessage(type, text) {
  actionMessage.value = { type, text }
}

function clearActionMessage() {
  actionMessage.value = null
}

function formatNumber(value) {
  const numericValue = Number(value || 0)
  return Number.isFinite(numericValue) ? numericValue.toLocaleString('zh-CN') : '0'
}

function normalizeBaselineRows(rows) {
  return (rows || []).map((row) => ({
    pipeModelId: row.pipe_model_id || row.pipeModelId,
    pipeModelName: row.pipe_model_name || row.pipeModelName || row.model_name || '未命名型号',
    designQuantity: row.design_total_qty || row.designQuantity || row.design_qty || 0,
    purchaseQuantity: row.purchase_total_qty || row.purchaseQuantity || row.purchase_qty || row.purchase_plan_qty || 0,
    remarks: row.remarks || row.remark || ''
  }))
}

function normalizePlanRows(rows, dates) {
  return (rows || []).map((row) => {
    const valueMap = {}
    const sourceMap = row.values || row.plan_values || {}
    const remarksMap = row.remarks || row.remark_map || {}
    dates.forEach((date) => {
      const sourceValue = sourceMap[date]
      valueMap[date] = {
        plannedQty: Number(
          typeof sourceValue === 'number'
            ? sourceValue
            : sourceValue?.plan_qty ?? sourceValue?.planned_qty ?? sourceValue?.plannedQty ?? 0,
        ),
        remarks:
          remarksMap[date] ||
          sourceValue?.remark ||
          sourceValue?.remarks ||
          ''
      }
    })
    return {
      pipeModelId: row.pipe_model_id || row.pipeModelId,
      pipeModelName: row.pipe_model_name || row.pipeModelName || row.model_name || '未命名型号',
      values: valueMap
    }
  })
}

function normalizeUsageRows(rows) {
  return (rows || []).map((row) => ({
    pipeModelId: row.pipe_model_id || row.pipeModelId,
    pipeModelName: row.pipe_model_name || row.pipeModelName || row.model_name || '未命名型号',
    usedQty: Number(row.usage_qty ?? row.used_qty ?? row.usedQty ?? 0),
    remarks: row.remark || row.remarks || ''
  }))
}

function normalizePendingRows(rows) {
  return (rows || []).map((row) => ({
    deliveryId: row.delivery_id || row.deliveryId,
    deliveryCode: row.delivery_code || row.deliveryCode || '',
    supplyEntityName: row.supply_entity_name || row.supplyEntityName || '未命名供给主体',
    pipeModelName: row.pipe_model_name || row.pipeModelName || '未命名型号',
    shippedQty: row.shipped_qty || row.shippedQty || 0,
    shippedAt: row.shipped_at || row.shippedAt || '',
    remarks: row.remarks || ''
  }))
}

function normalizeOptionsPayload(response) {
  return {
    stationOptions: response.station_options || response.stations || [],
    pipeModelOptions: response.pipe_model_options || response.pipe_models || [],
    currentGroup: response.current_group || response.user?.group || '',
    bizDate: response.biz_date || '',
    planStartDate: response.plan_start_date || '',
    planEditableDays: Number(response.plan_editable_days ?? 3),
    defaultAnchorDate: response.default_anchor_date || response.default_plan_anchor_date || '',
    defaultUsageDate: response.default_usage_date || response.default_usage_sheet_date || ''
  }
}

async function loadOptions() {
  optionsLoading.value = true
  optionsError.value = ''
  try {
    const response = await getTubeDemandManagementOptions(PROJECT_KEY)
    const normalized = normalizeOptionsPayload(response)
    stationOptions.value = normalized.stationOptions
    pipeModelOptions.value = normalized.pipeModelOptions
    currentGroup.value = normalized.currentGroup
    if (!bizDate.value) {
      bizDate.value = normalized.bizDate || getTodayString(-1)
    }
    planEditableDays.value = Number.isFinite(normalized.planEditableDays) ? normalized.planEditableDays : 3

    if (!selectedStationId.value && stationOptions.value.length) {
      selectedStationId.value = stationOptions.value[0].station_id
    }
    if (!anchorDate.value) {
      anchorDate.value = normalized.planStartDate || normalized.defaultAnchorDate || getTodayString()
    }
    usageDate.value = normalized.bizDate || normalized.defaultUsageDate || getTodayString(-1)
  } catch (error) {
    optionsError.value = error?.message || '加载需求侧配置失败'
  } finally {
    optionsLoading.value = false
  }
}

async function loadBaseline() {
  if (!selectedStationId.value) {
    baselineRows.value = []
    return
  }
  baselineLoading.value = true
  baselineError.value = ''
  try {
    const response = await getTubeDemandManagementBaseline(PROJECT_KEY, selectedStationId.value)
    baselineRows.value = normalizeBaselineRows(response.rows)
  } catch (error) {
    baselineError.value = error?.message || '加载基准量失败'
    baselineRows.value = []
  } finally {
    baselineLoading.value = false
  }
}

async function loadPlanMatrix() {
  if (!selectedStationId.value || !anchorDate.value) {
    planDates.value = []
    planRows.value = []
    return
  }
  planLoading.value = true
  planError.value = ''
  try {
    const response = await getTubeDemandManagementPlanMatrix(PROJECT_KEY, selectedStationId.value, anchorDate.value)
    const dates = response.plan_dates || []
    planDates.value = dates
    planRows.value = normalizePlanRows(response.rows, dates)
  } catch (error) {
    planError.value = error?.message || '加载三日计划失败'
    planDates.value = []
    planRows.value = []
  } finally {
    planLoading.value = false
  }
}

async function loadUsageSheet() {
  if (!selectedStationId.value || !usageDate.value) {
    usageRows.value = []
    return
  }
  usageLoading.value = true
  usageError.value = ''
  try {
    const response = await getTubeDemandManagementUsageSheet(PROJECT_KEY, selectedStationId.value, usageDate.value)
    usageRows.value = normalizeUsageRows(response.rows)
  } catch (error) {
    usageError.value = error?.message || '加载实际使用数据失败'
    usageRows.value = []
  } finally {
    usageLoading.value = false
  }
}

async function loadPendingArrivals() {
  if (!selectedStationId.value) {
    pendingRows.value = []
    return
  }
  pendingLoading.value = true
  pendingError.value = ''
  try {
    const response = await getTubeDemandManagementPendingArrivals(PROJECT_KEY, selectedStationId.value)
    pendingRows.value = normalizePendingRows(response.rows)
  } catch (error) {
    pendingError.value = error?.message || '加载待确认到货失败'
    pendingRows.value = []
  } finally {
    pendingLoading.value = false
  }
}

async function reloadStationData() {
  clearActionMessage()
  await Promise.all([
    loadBaseline(),
    loadPlanMatrix(),
    loadUsageSheet(),
    loadPendingArrivals()
  ])
}

async function savePlanMatrix() {
  if (!selectedStationId.value || !planDates.value.length || planEditableDays.value <= 0) {
    return
  }
  savePlanLoading.value = true
  clearActionMessage()
  try {
    const records = []
    planRows.value.forEach((row) => {
      planDates.value.forEach((date, index) => {
        if (!isPlanDateEditable(index)) {
          return
        }
        const cell = row.values[date]
        records.push({
          plan_date: date,
          pipe_model_id: row.pipeModelId,
          plan_qty: Number(cell.plannedQty || 0),
          remark: cell.remarks || ''
        })
      })
    })
    await saveTubeDemandManagementPlanMatrix(PROJECT_KEY, {
      station_id: selectedStationId.value,
      anchor_date: anchorDate.value,
      records
    })
    setActionMessage('success', '三日计划量已提交。')
    await loadPlanMatrix()
  } catch (error) {
    setActionMessage('error', error?.message || '提交三日计划量失败')
  } finally {
    savePlanLoading.value = false
  }
}

async function saveUsageSheet() {
  if (!selectedStationId.value || !usageDate.value) {
    return
  }
  saveUsageLoading.value = true
  clearActionMessage()
  try {
    const records = usageRows.value.map((row) => ({
      pipe_model_id: row.pipeModelId,
      usage_qty: Number(row.usedQty || 0),
      remark: row.remarks || ''
    }))
    await saveTubeDemandManagementUsageSheet(PROJECT_KEY, {
      station_id: selectedStationId.value,
      usage_date: usageDate.value,
      records
    })
    setActionMessage('success', '实际使用量已提交。')
    await loadUsageSheet()
  } catch (error) {
    setActionMessage('error', error?.message || '提交实际使用量失败')
  } finally {
    saveUsageLoading.value = false
  }
}

watch(selectedStationId, () => {
  reloadStationData()
})

watch(bizDate, (value) => {
  usageDate.value = value || ''
})

watch(usageDate, (value, oldValue) => {
  if (!selectedStationId.value || !value || value === oldValue) {
    return
  }
  loadUsageSheet()
})

onMounted(async () => {
  await loadOptions()
  await reloadStationData()
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
  gap: 16px;
  align-items: center;
  margin-bottom: 16px;
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

.filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}


.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: #334155;
  font-size: 14px;
}

.field select,
.field input,
.cell-editor input,
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

.field select:focus,
.field input:focus,
.cell-editor input:focus,
.number-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.meta-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 16px;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: #eef2ff;
  color: #334155;
  font-size: 13px;
}

.table-wrap {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 780px;
}

.data-table th,
.data-table td {
  border-bottom: 1px solid #e2e8f0;
  padding: 12px;
  text-align: left;
  vertical-align: top;
}

.data-table th {
  color: #334155;
  background: #f8fafc;
  font-weight: 600;
}

.cell-editor {
  display: grid;
  gap: 8px;
  min-width: 180px;
}

.editable-plan-date {
  background: #dbeafe;
  color: #1d4ed8;
}

.editable-plan-date-cell {
  background: #eff6ff;
}

.editable-plan-date-cell input {
  background: #f8fbff;
}

.primary-button {
  border-radius: 10px;
  padding: 10px 16px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.primary-button {
  border: 1px solid #2563eb;
  background: #2563eb;
  color: #fff;
}

.primary-button:disabled,
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.loading-text,
.empty-box,
.error-box {
  padding: 14px 16px;
  border-radius: 10px;
  font-size: 14px;
}

.loading-text,
.empty-box {
  background: #f8fafc;
  color: #475569;
}

.error-box {
  background: #fff1f2;
  color: #be123c;
}

.action-message {
  margin: 0;
  font-size: 14px;
}

.action-message.success {
  color: #15803d;
}

.action-message.error {
  color: #be123c;
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
}
</style>
