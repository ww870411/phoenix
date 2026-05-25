<template>
  <div class="tube-page-root">
    <AppHeader />
    <main class="tube-page-main container">
      <Breadcrumbs :items="breadcrumbItems" />
      
      <!-- 高级工作台头部 -->
      <header class="topbar premium-topbar">
        <div>
          <h2>现场管理工作台 (需求侧)</h2>
          <p class="sub">
            面向项目现场负责人与管理人员。提供 Tabs 标签化分类，支持未来三日滚动计划的高效填报、昨日实际用量核对、物理到货确认与施工接收登记。
          </p>
        </div>
        <div class="topbar-actions">
          <button type="button" class="btn ghost btn-back" @click="goProjectPages">
            返回功能页
          </button>
          <button
            type="button"
            class="btn primary submit-status-button"
            :disabled="!selectedStationId || !canSubmitCurrentProject || submitStatusLoading"
            @click="handleStationSubmitClick"
          >
            {{ submitStatusLoading ? '提交中...' : '提交本站填报状态' }}
          </button>
        </div>
      </header>

      <p v-if="errorMessage" class="page-error">{{ errorMessage }}</p>

      <!-- 全局筛选与工作台 Meta 卡片 -->
      <section class="card elevated filter-card">
        <div class="panel-title-row">
          <h2>工作台全局筛选</h2>
          <p v-if="actionMessage" :class="['action-message', actionMessage.type]">
            {{ actionMessage.text }}
          </p>
        </div>

        <div v-if="optionsError" class="error-box">
          {{ optionsError }}
        </div>

        <div class="filter-grid compact-filter-grid">
          <label class="field">
            <span>当前管理的换热站</span>
            <select v-model="selectedStationId" :disabled="optionsLoading || !stationOptions.length">
              <option value="" disabled>请选择要操作的换热站</option>
              <option v-for="station in stationOptions" :key="station.station_id" :value="station.station_id">
                {{ station.station_name }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>展示截止日期</span>
            <input v-model="showDate" type="date" :disabled="!isGlobalAdmin" />
          </label>
        </div>

        <!-- 磨砂玻璃态微数据看板 (Quick Dashboard) -->
        <div class="meta-dashboard">
          <div class="meta-card">
            <span class="meta-label">授权范围</span>
            <strong class="meta-value">{{ stationOptions.length }} 个站</strong>
          </div>
          <div class="meta-card">
            <span class="meta-label">保温管型号</span>
            <strong class="meta-value">{{ pipeModelOptions.length }} 种</strong>
          </div>
          <div class="meta-card">
            <span class="meta-label">当前角色</span>
            <strong class="meta-value">{{ currentGroupLabel }}</strong>
          </div>
          <div class="meta-card highlight">
            <span class="meta-label">计划起始日期</span>
            <strong class="meta-value">{{ anchorDate || '未设置' }}</strong>
          </div>
          <div class="meta-card highlight">
            <span class="meta-label">消耗采集日期</span>
            <strong class="meta-value">{{ usageDate || '未设置' }}</strong>
          </div>
        </div>
      </section>

      <!-- 选项卡导航 (Responsive Tabs Header) -->
      <div class="tube-tabs-header-wrap" v-if="selectedStationId">
        <div class="tube-tabs-header">
          <button 
            type="button" 
            :class="{ active: activeTab === 'plan' }" 
            @click="activeTab = 'plan'"
          >
            🕒 三日滚动计划填报
          </button>
          <button 
            type="button" 
            :class="{ active: activeTab === 'usage' }" 
            @click="activeTab = 'usage'"
          >
            📊 每日使用消耗填报
          </button>
          <button 
            type="button" 
            :class="{ active: activeTab === 'baseline' }" 
            @click="activeTab = 'baseline'"
          >
            📋 基准设计量台账
          </button>
          <button 
            type="button" 
            :class="{ active: activeTab === 'logistics' }" 
            @click="activeTab = 'logistics'"
          >
            🚚 现场到货与接收确认
          </button>
        </div>
      </div>

      <!-- Tab内容区域 -->
      <div class="tube-tab-content-wrap" v-if="selectedStationId">
        
        <!-- Tab 1: 三日计划填报 -->
        <div v-if="activeTab === 'plan'" class="tab-pane">
          <section class="card elevated tab-card">
            <div class="panel-title-row">
              <div>
                <h2>未来三日滚动计划</h2>
                <span class="panel-hint">按起始日期连续生成三天滚动计划。建议从右侧快捷区进行批量填报。计量单位：米。</span>
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

            <!-- 批量粘贴解析利器 -->
            <div 
              class="paste-zone" 
              tabindex="0" 
              title="点击激活后直接按 Ctrl+V 粘贴"
              @paste="handleClipboardPaste"
            >
              <div class="paste-icon">📋</div>
              <div class="paste-desc">
                <strong>智能 Excel 批量粘贴录入区</strong>
                <span>在一线线下 Excel 中选中 [型号, 计划量] 数据块复制后，点击此虚线框内直接按 <b>Ctrl + V</b>，系统将智能提取并匹配填充下方表格</span>
              </div>
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
                    <td class="cell-text" :title="row.pipeModelName">{{ row.pipeModelName }}</td>
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
                          placeholder="数量"
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
        </div>

        <!-- Tab 2: 实际使用消耗填报 -->
        <div v-if="activeTab === 'usage'" class="tab-pane">
          <section class="card elevated tab-card">
            <div class="panel-title-row">
              <div>
                <h2>实际使用消耗上报</h2>
                <span class="panel-hint">登记昨日（{{ usageDate || '今日' }}）各保温管型号的实际消耗量。计量单位：米。</span>
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
                    <td class="cell-text" :title="row.pipeModelName">{{ row.pipeModelName }}</td>
                    <td>
                      <input
                        v-model.number="row.usedQty"
                        class="number-input"
                        type="number"
                        min="0"
                        step="1"
                        :disabled="usageActionLoading || !canSubmitCurrentProject"
                      />
                    </td>
                    <td>
                      <input
                        v-model.trim="row.remarks"
                        type="text"
                        maxlength="120"
                        placeholder="备注"
                        :disabled="usageActionLoading || !canSubmitCurrentProject"
                      />
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <!-- Tab 3: 基准量台账 -->
        <div v-if="activeTab === 'baseline'" class="tab-pane">
          <section class="card elevated tab-card">
            <div class="panel-title-row">
              <div>
                <h2>换热站设计与采购基准量</h2>
                <span class="panel-hint">展示当前换热站的设计总量与全局计划采购总量，供日常对照。计量单位：米。</span>
              </div>
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
                    <td class="cell-text" :title="row.pipeModelName">{{ row.pipeModelName }}</td>
                    <td class="cell-number">{{ formatNumber(row.designQuantity) }}</td>
                    <td class="cell-number">{{ formatNumber(row.purchaseQuantity) }}</td>
                    <td class="cell-text" :title="row.remarks || '—'">{{ row.remarks || '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <!-- Tab 4: 物流到货与施工确认 -->
        <div v-if="activeTab === 'logistics'" class="tab-pane">
          <section class="card elevated tab-card">
            <div class="panel-title-row">
              <div>
                <h2>到货与施工接收记录</h2>
                <span class="panel-hint">确认运输车次的安全到站，并录入施工单位的真实物理接收量。计量单位：米。</span>
              </div>
              <div class="toolbar-actions">
                <button type="button" class="btn ghost" :disabled="pendingLoading" @click="resetPendingFilters">重置筛选</button>
                <button type="button" class="primary-button" :disabled="pendingLoading || !selectedStationId" @click="applyPendingFilters">
                  {{ pendingLoading ? '查询中...' : '筛选记录' }}
                </button>
              </div>
            </div>

            <!-- 筛选排版 -->
            <div class="filter-grid compact-filter-grid">
              <label class="field field-compact">
                <span>订单号</span>
                <input v-model.trim="pendingFilters.orderNo" type="text" placeholder="输入订单号" />
              </label>
              <label class="field field-compact">
                <span>运输车次号</span>
                <input v-model.trim="pendingFilters.shipmentNo" type="text" placeholder="输入运输车次号" />
              </label>
              <label class="field field-compact">
                <span>过滤型号</span>
                <select v-model="pendingFilters.pipeModelId">
                  <option value="">全部型号</option>
                  <option v-for="model in pipeModelOptions" :key="model.pipe_model_id" :value="model.pipe_model_id">
                    {{ model.pipe_model_name || model.pipe_model_id }}
                  </option>
                </select>
              </label>
              <label class="field field-compact">
                <span>发货日期</span>
                <input v-model="pendingFilters.shippedDate" type="date" />
              </label>
              <label class="field field-compact">
                <span>确认到货日期</span>
                <input v-model="pendingFilters.arrivedDate" type="date" />
              </label>
            </div>

            <div v-if="pendingLoading" class="loading-text">正在加载物流确认记录...</div>
            <div v-else-if="pendingError" class="error-box">{{ pendingError }}</div>
            <div v-else-if="!pendingRows.length" class="empty-box">当前没有待物流确认记录。</div>
            <div v-else class="table-wrap logistics-table-wrap">
              <table class="data-table logistics-table">
                <thead>
                  <tr>
                    <th>订单号</th>
                    <th>运输车次号</th>
                    <th>车牌号</th>
                    <th>供给主体</th>
                    <th>型号</th>
                    <th>发货量（米）</th>
                    <th>发货时间</th>
                    <th>确认到货时间</th>
                    <th>在途时长</th>
                    <th class="cell-status">状态</th>
                    <th>确认量（米）</th>
                    <th>确认操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in pendingRows" :key="row.deliveryId">
                    <td class="cell-code">{{ row.deliveryCode || row.deliveryId }}</td>
                    <td class="cell-code">{{ row.shipmentNo || '—' }}</td>
                    <td class="cell-text" :title="row.vehiclePlateNo || '—'">{{ row.vehiclePlateNo || '—' }}</td>
                    <td class="cell-text" :title="row.supplyEntityName">{{ row.supplyEntityName }}</td>
                    <td class="cell-text" :title="row.pipeModelName">{{ row.pipeModelName }}</td>
                    <td class="cell-number">{{ formatNumber(row.shippedQty) }}</td>
                    <td class="cell-datetime">{{ formatDateTimeDisplay(row.shippedAt) || '—' }}</td>
                    <td class="cell-datetime">{{ formatDateTimeDisplay(row.arrivedConfirmAt) || '—' }}</td>
                    <td class="cell-elapsed">{{ formatDeliveryElapsedDisplay(row) }}</td>
                    <td class="cell-status">
                      <div class="status-pill-group">
                        <span class="status-pill" :class="row.status">
                          {{ row.statusLabel }}
                        </span>
                        <span v-if="row.abnormalFlag" class="status-pill abnormal">
                          {{ getAbnormalLabel(row) }}
                        </span>
                      </div>
                    </td>
                    <td>
                      <div v-if="row.status === 'pending_arrival'" class="stack-controls">
                        <input
                          v-model.number="row.arrivalConfirmQty"
                          type="number"
                          min="0"
                          :max="row.shippedQty"
                          step="1"
                        />
                      </div>
                      <div v-else-if="row.status === 'pending_receive'" class="stack-controls">
                        <input
                          v-model.number="row.receiptConfirmQty"
                          type="number"
                          min="0"
                          :max="row.arrivedQty"
                          step="1"
                        />
                      </div>
                      <span v-else class="cell-number">{{ formatNumber(row.receivedQty || row.arrivedQty) }}</span>
                    </td>
                    <td>
                      <div v-if="row.status === 'pending_arrival' || row.status === 'pending_receive'" class="action-stack action-inline">
                        <button
                          type="button"
                          class="primary-button action-button arrival-button"
                          :class="{ 'is-active': canClickArrival(row) }"
                          :disabled="deliveryActionLoadingKey === `arrival-${row.deliveryId}` || !canClickArrival(row)"
                          @click="confirmArrival(row)"
                        >
                          {{
                            deliveryActionLoadingKey === `arrival-${row.deliveryId}`
                              ? '确认中...'
                              : row.status === 'pending_arrival'
                                ? '确认到货'
                                : '到货已确认'
                          }}
                        </button>
                        <button
                          type="button"
                          class="primary-button action-button receipt-button"
                          :class="{ 'is-active': canClickReceipt(row) }"
                          :disabled="deliveryActionLoadingKey === `receipt-${row.deliveryId}` || !canClickReceipt(row)"
                          @click="confirmReceipt(row)"
                        >
                          {{
                            deliveryActionLoadingKey === `receipt-${row.deliveryId}`
                              ? '确认中...'
                              : row.status === 'pending_receive'
                                ? '施工接收'
                                : '等待到货'
                          }}
                        </button>
                      </div>
                      <span v-else class="action-placeholder">{{ getDeliveryStatusLabel(row.status) }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>

      </div>

      <!-- 初始未选择提示卡 -->
      <section v-else class="card elevated select-hint-card">
        <div class="hint-content">
          <div class="hint-icon">📂</div>
          <h3>请首先选择要操作的换热站</h3>
          <p>在上方“工作台全局筛选”下拉框中选择具体的换热站后，系统将为您正式解锁三日滚动计划、使用量填报及到货到货确认等多标签管理模块。</p>
        </div>
      </section>

    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useAuthStore } from '../../daily_report_25_26/store/auth'
import { AppHeader, Breadcrumbs, useTubePageShell, useTubeRealtimeRefresh } from './shared'
import {
  confirmTubeDemandManagementDeliveryArrival,
  confirmTubeDemandManagementDeliveryReceipt,
  getTubeDemandManagementBaseline,
  getTubeDemandManagementLogisticsRecords,
  getTubeDemandManagementOptions,
  getTubeDemandManagementPlanMatrix,
  getTubeDemandManagementUsageSheet,
  saveTubeDemandManagementPlanMatrix,
  saveTubeDemandManagementUsageSheet,
  submitTubeDemandManagementStationStatus
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
const activeTab = ref('plan')

// 智能 Excel 一键粘贴解析函数
function handleClipboardPaste(event) {
  if (!selectedStationId.value || activeTab.value !== 'plan') {
    return
  }
  const clipboardData = event.clipboardData || window.clipboardData
  const pastedText = clipboardData.getData('text')
  if (!pastedText) return

  // 按换行符切分行
  const lines = pastedText.split(/\r?\n/).map(line => line.trim()).filter(Boolean)
  if (!lines.length) return

  let successCount = 0
  lines.forEach(line => {
    // 按 Tab 键切分列
    const parts = line.split(/\t/).map(p => p.trim())
    if (parts.length < 2) return

    const pipeModelInput = parts[0].toUpperCase()
    const qtyValue = Number(parts[1])
    if (isNaN(qtyValue) || qtyValue < 0) return

    // 匹配前台 planRows 里的保温管型号名称或 ID
    const targetRow = planRows.value.find(row => 
      row.pipeModelName.toUpperCase() === pipeModelInput || 
      row.pipeModelId.toUpperCase() === pipeModelInput
    )

    if (targetRow) {
      planDates.value.forEach((date, dateIdx) => {
        // 如果 pasted 数据里有多列，依次按列填入
        const colValIdx = dateIdx + 1
        if (parts[colValIdx] !== undefined) {
          const partVal = Number(parts[colValIdx])
          if (!isNaN(partVal) && partVal >= 0 && isPlanDateEditable(dateIdx)) {
            targetRow.values[date].plannedQty = partVal
            successCount++
          }
        } else if (dateIdx === 0 && isPlanDateEditable(0)) {
          // 若只有两列，默认填入第一天可编辑日期
          targetRow.values[date].plannedQty = qtyValue
          successCount++
        }
      })
    }
  })

  if (successCount > 0) {
    setActionMessage('success', `智能粘贴解析成功！已为您智能匹配并自动填报 ${successCount} 个计划量单元格。`)
  } else {
    setActionMessage('error', '未在剪贴板中匹配出有效的保温管型号，请确认从 Excel 中整行复制了 [型号, 计划量] 等数据。')
  }
}

const showDate = ref('')
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
const submitStatusLoading = ref(false)

const pendingLoading = ref(false)
const pendingError = ref('')
const pendingRows = ref([])
const pendingFilters = reactive({
  orderNo: '',
  shipmentNo: '',
  pipeModelId: '',
  shippedDate: '',
  arrivedDate: '',
})
const nowTick = ref(Date.now())
let nowTimer = null

const actionMessage = ref(null)
const canSubmitCurrentProject = computed(() => auth.canSubmitFor(PROJECT_KEY))
const normalizedGroupKey = computed(() => String(currentGroup.value || '').trim())
const isGlobalAdmin = computed(() => {
  const group = normalizedGroupKey.value.toLowerCase()
  return group === 'global_admin' || group === 'globaladmin' || group === '系统管理员' || group === '管理员'
})
const canConfirmArrival = computed(() => isGlobalAdmin.value || normalizedGroupKey.value === 'tube_site_manager')
const canConfirmReceipt = computed(() => isGlobalAdmin.value || normalizedGroupKey.value === 'tube_construction_unit')
const deliveryActionLoadingKey = ref('')

const currentGroupLabel = computed(() => {
  const group = normalizedGroupKey.value
  if (!group) {
    return '未识别'
  }
  if (isGlobalAdmin.value) {
    return '全局管理员'
  }
  return group
})

function isPlanDateEditable(index) {
  const editableDays = Number(planEditableDays.value ?? 0)
  if (editableDays <= 0) {
    return false
  }
  return index >= planDates.value.length - editableDays
}

function canClickArrival(row) {
  return Boolean(canConfirmArrival.value && row?.status === 'pending_arrival')
}

function canClickReceipt(row) {
  return Boolean(canConfirmReceipt.value && row?.status === 'pending_receive')
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
    deliveryId: row.delivery_id || row.deliveryId || row.id,
    deliveryCode: row.delivery_code || row.deliveryCode || '',
    shipmentNo: row.shipment_no || row.shipmentNo || '',
    vehiclePlateNo: row.vehicle_plate_no || row.vehiclePlateNo || '',
    supplyEntityName: row.supply_entity_name || row.supplyEntityName || row.supply_entity_id || row.supplyEntityId || '—',
    pipeModelName: row.pipe_model_name || row.pipeModelName || '未命名型号',
    status: row.status || '',
    statusLabel: getDeliveryStatusLabel(row.status),
    abnormalFlag: Boolean(row.abnormal_flag || row.abnormalFlag),
    shippedQty: Number(row.shipped_qty || row.shippedQty || 0),
    arrivedQty: Number(row.arrived_qty || row.arrivedQty || row.shipped_qty || row.shippedQty || 0),
    receivedQty: Number(row.received_qty || row.receivedQty || row.arrived_qty || row.arrivedQty || row.shipped_qty || row.shippedQty || 0),
    shippedAt: row.shipped_at || row.shippedAt || '',
    arrivedConfirmAt: row.arrived_confirm_at || row.arrivedConfirmAt || '',
    deliveryElapsedLabel: row.delivery_elapsed_label || row.deliveryElapsedLabel || '',
    remarks: row.remarks || row.ship_remark || '',
    arrivalConfirmQty: Number(row.arrived_qty || row.arrivedQty || row.shipped_qty || row.shippedQty || 0),
    receiptConfirmQty: Number(row.received_qty || row.receivedQty || row.arrived_qty || row.arrivedQty || row.shipped_qty || row.shippedQty || 0),
    arrivalRemark: '',
    receiptRemark: ''
  }))
}

function getAbnormalLabel(row) {
  if (!row?.abnormalFlag) return ''
  if (row.receivedQty != null && row.arrivedQty != null && Number(row.receivedQty) < Number(row.arrivedQty)) {
    return '少接收'
  }
  if (row.arrivedQty != null && Number(row.arrivedQty) < Number(row.shippedQty || 0)) {
    return '少到货'
  }
  return '异常'
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

function formatDeliveryElapsedDisplay(row) {
  if (!row || row.status === 'cancelled') return '—'
  return row.deliveryElapsedLabel || formatElapsedLabel(row.shippedAt) || '—'
}

function formatDateTimeDisplay(value) {
  if (!value) return ''
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return String(value).replace('T', ' ').slice(0, 16)
  }
  const pad = (part) => String(part).padStart(2, '0')
  return `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())} ${pad(parsed.getHours())}:${pad(parsed.getMinutes())}`
}

function getDeliveryStatusLabel(status) {
  const mapping = {
    pending_arrival: '已发货待到货',
    pending_receive: '已到货待接收',
    pending_warehouse: '已接收待库管',
    completed: '已完成',
    cancelled: '已撤销'
  }
  return mapping[status] || status || '—'
}

function normalizeOptionsPayload(response) {
  return {
    stationOptions: response.station_options || response.stations || [],
    pipeModelOptions: response.pipe_model_options || response.pipe_models || [],
    currentGroup: response.current_group || response.user?.group || '',
    showDate: response.show_date || response.biz_date || '',
    planStartDate: response.plan_start_date || '',
    planEditableDays: Number(response.plan_editable_days ?? 3),
    defaultAnchorDate: response.default_anchor_date || response.default_plan_anchor_date || '',
    usageCollectionDate: response.usage_collection_date || '',
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
    showDate.value = normalized.showDate || getTodayString(-1)
    planEditableDays.value = Number.isFinite(normalized.planEditableDays) ? normalized.planEditableDays : 3
    const stationIdSet = new Set(stationOptions.value.map((item) => String(item.station_id || '')))
    if (!selectedStationId.value || !stationIdSet.has(selectedStationId.value)) {
      selectedStationId.value = stationOptions.value[0]?.station_id || ''
    }
    anchorDate.value = normalized.planStartDate || normalized.defaultAnchorDate || getTodayString()
    usageDate.value = normalized.usageCollectionDate || normalized.defaultUsageDate || getTodayString(-1)
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

async function loadLogisticsRecords() {
  if (!selectedStationId.value) {
    pendingRows.value = []
    pendingError.value = ''
    pendingLoading.value = false
    return
  }
  pendingLoading.value = true
  pendingError.value = ''
  try {
    const response = await getTubeDemandManagementLogisticsRecords(PROJECT_KEY, selectedStationId.value, {
      orderNo: pendingFilters.orderNo || '',
      shipmentNo: pendingFilters.shipmentNo || '',
      pipeModelId: pendingFilters.pipeModelId || '',
      shippedDate: pendingFilters.shippedDate || '',
      arrivedDate: pendingFilters.arrivedDate || '',
    })
    pendingRows.value = normalizePendingRows(response.rows)
  } catch (error) {
    pendingError.value = error?.message || '加载物流确认记录失败'
    pendingRows.value = []
  } finally {
    pendingLoading.value = false
  }
}

function applyPendingFilters() {
  loadLogisticsRecords()
}

function resetPendingFilters() {
  pendingFilters.orderNo = ''
  pendingFilters.shipmentNo = ''
  pendingFilters.pipeModelId = ''
  pendingFilters.shippedDate = ''
  pendingFilters.arrivedDate = ''
  loadLogisticsRecords()
}

async function confirmArrival(row) {
  if (!row?.deliveryId || !canClickArrival(row)) {
    return
  }
  const normalizedArrivedQty = Number(row.arrivalConfirmQty ?? row.shippedQty ?? 0)
  if (normalizedArrivedQty > Number(row.shippedQty || 0)) {
    setActionMessage('error', '确认到货量不能大于该订单的发货量。')
    return
  }
  deliveryActionLoadingKey.value = `arrival-${row.deliveryId}`
  clearActionMessage()
  try {
    await confirmTubeDemandManagementDeliveryArrival(PROJECT_KEY, row.deliveryId, {
      arrived_qty: normalizedArrivedQty,
      remark: row.arrivalRemark || ''
    })
    setActionMessage('success', `发货单 ${row.deliveryCode || row.deliveryId} 到货已确认。`)
    await loadLogisticsRecords()
  } catch (error) {
    setActionMessage('error', error?.message || '确认到货失败')
  } finally {
    deliveryActionLoadingKey.value = ''
  }
}

async function confirmReceipt(row) {
  if (!row?.deliveryId || !canClickReceipt(row)) {
    return
  }
  const limitQty = Number(row.arrivedQty ?? row.shippedQty ?? 0)
  const receivedQty = Number(row.receiptConfirmQty ?? row.arrivedQty ?? row.shippedQty ?? 0)
  if (receivedQty > limitQty) {
    setActionMessage('error', `确认施工接收量不能大于已到货量 ${limitQty} 米`)
    return
  }
  if (receivedQty < 0) {
    setActionMessage('error', `确认施工接收量不能为负数`)
    return
  }
  deliveryActionLoadingKey.value = `receipt-${row.deliveryId}`
  clearActionMessage()
  try {
    await confirmTubeDemandManagementDeliveryReceipt(PROJECT_KEY, row.deliveryId, {
      received_qty: receivedQty,
      remark: row.receiptRemark || ''
    })
    setActionMessage('success', `发货单 ${row.deliveryCode || row.deliveryId} 施工接收已确认。`)
    await loadLogisticsRecords()
  } catch (error) {
    setActionMessage('error', error?.message || '确认施工接收失败')
  } finally {
    deliveryActionLoadingKey.value = ''
  }
}

async function reloadStationData() {
  clearActionMessage()
  await Promise.all([
    loadBaseline(),
    loadPlanMatrix(),
    loadUsageSheet(),
    loadLogisticsRecords()
  ])
}

async function refreshRealtimeConfig() {
  await loadOptions()
  await reloadStationData()
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

async function handleStationSubmitClick() {
  if (!selectedStationId.value || !canSubmitCurrentProject.value) {
    return
  }
  submitStatusLoading.value = true
  clearActionMessage()
  try {
    const response = await submitTubeDemandManagementStationStatus(PROJECT_KEY, {
      station_id: selectedStationId.value,
      remark: ''
    })
    const submittedDate = response?.submission?.data_submit_date || anchorDate.value || '未设置'
    setActionMessage('success', `换热站 ${selectedStationId.value} 已标记为提交完成，提交日期为 ${submittedDate}。`)
  } catch (error) {
    setActionMessage('error', error?.message || '提交换热站填报状态失败')
  } finally {
    submitStatusLoading.value = false
  }
}

watch(selectedStationId, () => {
  reloadStationData()
})

watch(usageDate, (value, oldValue) => {
  if (!selectedStationId.value || !value || value === oldValue) {
    return
  }
  loadUsageSheet()
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
.submit-status-button {
  white-space: nowrap;
}
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

.compact-filter-grid {
  margin-bottom: 16px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  align-items: end;
}

.field-compact span {
  font-size: 12px;
  color: #64748b;
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

.logistics-table-wrap {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #ffffff;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 780px;
}

.data-table th,
.data-table td {
  border-bottom: 1px solid #e2e8f0;
  padding: 14px 16px !important;
  text-align: left;
  vertical-align: middle !important;
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

.logistics-table {
  min-width: 1460px;
}

.logistics-table th {
  white-space: nowrap;
}

.logistics-table td {
  white-space: normal;
}

.cell-code {
  min-width: 140px;
  font-family: "Consolas", "Courier New", monospace;
  font-size: 14px;
  color: #0f172a;
  word-break: break-all;
}

.cell-text {
  min-width: 160px;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

.cell-number {
  min-width: 90px;
  white-space: nowrap;
}

.cell-datetime {
  min-width: 132px;
  white-space: nowrap;
  color: #334155;
}

.cell-elapsed {
  min-width: 96px;
  white-space: nowrap;
}

.cell-status {
  min-width: 118px;
  white-space: nowrap;
}

.stack-controls {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 120px;
}

.action-inline {
  flex-direction: row;
  flex-wrap: nowrap;
  min-width: 232px;
}

.action-button {
  min-width: 118px;
}

.action-placeholder {
  color: #64748b;
  font-size: 13px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  line-height: 1.2;
  background: #eef2ff;
  color: #334155;
  white-space: nowrap;
}

.status-pill-group {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.status-pill.pending_arrival {
  background: #eff6ff;
  color: #1d4ed8;
}

.status-pill.pending_receive {
  background: #fff7ed;
  color: #c2410c;
}

.status-pill.pending_warehouse {
  background: #f0fdf4;
  color: #15803d;
}

.status-pill.completed {
  background: #ecfdf5;
  color: #047857;
}

.status-pill.cancelled {
  background: #fef2f2;
  color: #b91c1c;
}

.status-pill.abnormal {
  background: #fff1f2;
  color: #be123c;
}

.primary-button.arrival-button {
  border-color: #e5e7eb;
  background: #ffffff;
  color: #cbd5e1;
}

.primary-button.arrival-button.is-active {
  border-color: #1d4ed8;
  background: #1d4ed8;
  color: #fff;
}

.primary-button.receipt-button {
  border-color: #e5e7eb;
  background: #ffffff;
  color: #cbd5e1;
}

.primary-button.receipt-button.is-active {
  border-color: #c2410c;
  background: #c2410c;
  color: #fff;
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

.btn, .primary-button {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  text-align: center !important;
  white-space: nowrap !important;
  word-break: keep-all !important;
  box-sizing: border-box !important;
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
  opacity: 1;
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

/* 磨砂玻璃态微数据看板 (Quick Dashboard) */
.meta-dashboard {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-top: 18px;
}

.meta-card {
  background: rgba(255, 255, 255, 0.65) !important;
  backdrop-filter: blur(12px) !important;
  -webkit-backdrop-filter: blur(12px) !important;
  border: 1px solid rgba(226, 232, 240, 0.8) !important;
  border-radius: 14px !important;
  padding: 16px !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 6px !important;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -1px rgba(0, 0, 0, 0.02) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  position: relative !important;
  overflow: hidden !important;
  box-sizing: border-box;
}

.meta-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 4px;
  background: linear-gradient(180deg, #6366f1 0%, #3b82f6 100%);
}

.meta-card.highlight::before {
  background: linear-gradient(180deg, #f59e0b 0%, #d97706 100%);
}

.meta-card:hover {
  transform: translateY(-4px) !important;
  background: rgba(255, 255, 255, 0.85) !important;
  box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.08), 0 4px 6px -2px rgba(59, 130, 246, 0.04) !important;
  border-color: rgba(147, 197, 253, 0.5) !important;
}

.meta-label {
  font-size: 12px !important;
  color: #64748b !important;
  font-weight: 500 !important;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.meta-value {
  font-size: 20px !important;
  color: #1e293b !important;
  font-weight: 700 !important;
  font-family: "Inter", "Outfit", -apple-system, sans-serif !important;
}

/* 呼吸灯特效 - Excel粘贴激活区 */
.paste-zone {
  display: flex !important;
  align-items: center !important;
  gap: 16px !important;
  border: 2px dashed #cbd5e1 !important;
  border-radius: 14px !important;
  padding: 16px 20px !important;
  background: #f8fafc !important;
  cursor: pointer !important;
  margin-bottom: 20px !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  box-sizing: border-box;
}

.paste-zone:hover, .paste-zone:focus {
  outline: none !important;
  border-color: #3b82f6 !important;
  background: #eff6ff !important;
  transform: scale(1.005) !important;
  animation: pulse-glow-indigo 2s infinite !important;
}

.paste-icon {
  font-size: 28px !important;
  background: #dbeafe !important;
  padding: 10px !important;
  border-radius: 12px !important;
  color: #2563eb !important;
  transition: all 0.3s ease !important;
  display: flex;
  align-items: center;
  justify-content: center;
}

.paste-zone:hover .paste-icon, .paste-zone:focus .paste-icon {
  background: #3b82f6 !important;
  color: #ffffff !important;
}

.paste-desc {
  display: flex !important;
  flex-direction: column !important;
  gap: 4px !important;
  text-align: left !important;
}

.paste-desc strong {
  font-size: 15px !important;
  color: #1e293b !important;
}

.paste-desc span {
  font-size: 13px !important;
  color: #64748b !important;
}

.paste-zone:hover .paste-desc span {
  color: #2563eb !important;
}

@keyframes pulse-glow-indigo {
  0% {
    box-shadow: 0 0 0 0px rgba(59, 130, 246, 0.25);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(59, 130, 246, 0);
  }
  100% {
    box-shadow: 0 0 0 0px rgba(59, 130, 246, 0);
  }
}

/* 升级表格 Hover 行高亮 */
.data-table tbody tr {
  transition: background-color 0.2s ease;
}

.data-table tbody tr:hover {
  background: linear-gradient(90deg, rgba(37, 99, 235, 0.03) 0%, rgba(255, 255, 255, 0) 100%) !important;
}

/* Vue Tabs 高端样式切换 */
.tube-tabs-header-wrap {
  background: rgba(241, 245, 249, 0.8) !important;
  border-radius: 14px !important;
  padding: 6px !important;
  margin-bottom: 16px !important;
  border: 1px solid #e2e8f0 !important;
  box-sizing: border-box;
}

.tube-tabs-header {
  display: flex !important;
  gap: 4px !important;
  width: 100% !important;
}

.tube-tabs-header button {
  flex: 1 !important;
  border: none !important;
  background: transparent !important;
  padding: 12px 16px !important;
  border-radius: 10px !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  color: #475569 !important;
  cursor: pointer !important;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 8px !important;
}

.tube-tabs-header button:hover {
  color: #1e293b !important;
  background: rgba(255, 255, 255, 0.5) !important;
}

.tube-tabs-header button.active {
  color: #2563eb !important;
  background: #ffffff !important;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
}
</style>
