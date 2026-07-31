<template>
  <div class="history-query-view page-layout">
    <AppHeader />
    <main class="page-main container">
      <!-- 统一面包屑导航 -->
      <Breadcrumbs :items="breadcrumbItems" />
      
      <div v-if="loading && !configSummary" class="loading-state">系统数据加载中...</div>
      <div v-else-if="errorMessage" class="error-state">{{ errorMessage }}</div>
      <div v-else class="page-content">
        <!-- 头部导航或说明 -->
        <header class="page-title-row">
          <div class="title-wrap">
            <h2>📊 历史数据查询</h2>
            <p class="subtitle">历史时段内需求主体的计划、实际消耗及到货运输历史明细与透视</p>
          </div>
          <button class="btn ghost back-btn" type="button" @click="goProjectPages">
            ← 返回项目主页
          </button>
        </header>

        <section class="card elevated section-card">
          <div class="card-header-row">
            <div>
              <div class="card-header">📊 需求主体填报与到货历史数据查询</div>
              <p class="sub block-sub">查询各需求主体每日保温管计划量、实际消耗、确认到货量及运输在途时长，包含时段内汇总统计。</p>
            </div>
          </div>
          
          <!-- 过滤查询栏 -->
          <div class="filter-panel" style="display: flex; gap: 15px; margin-bottom: 20px; align-items: center; background: #f8fafc; border: 1px solid #e2e8f0; padding: 16px; border-radius: 8px; flex-wrap: wrap;">
            <div class="filter-item" style="display: flex; flex-direction: column; gap: 5px;">
              <label style="font-size: 12px; color: #64748b; font-weight: 500;">选择需求主体</label>
              <select v-model="historyFilter.section1Id" class="select" style="min-width: 180px; background: #fff; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px; height: 32px; padding: 0 8px; font-size: 13px;">
                <option value="">— 全部需求主体 —</option>
                <option v-for="st in demandEntities" :key="st.section_1_id" :value="st.section_1_id">
                  {{ st.section_1_name }}
                </option>
              </select>
            </div>
            
            <div class="filter-item" style="display: flex; flex-direction: column; gap: 5px;">
              <label style="font-size: 12px; color: #64748b; font-weight: 500;">开始日期</label>
              <input v-model="historyFilter.startDate" class="input" type="date" style="height: 32px; background: #fff; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px; padding: 0 8px; font-size: 13px;" />
            </div>
            
            <div class="filter-item" style="display: flex; flex-direction: column; gap: 5px;">
              <label style="font-size: 12px; color: #64748b; font-weight: 500;">结束日期</label>
              <input v-model="historyFilter.endDate" class="input" type="date" style="height: 32px; background: #fff; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px; padding: 0 8px; font-size: 13px;" />
            </div>

            <div class="filter-item" style="display: flex; gap: 8px; align-self: flex-end; margin-left: auto;">
              <button class="btn primary" style="height: 32px; padding: 0 16px; border-radius: 6px; font-size: 13px; display: flex; align-items: center; gap: 5px; cursor: pointer;" @click="handleHistoryQuery">
                🔍 查询
              </button>
              <button class="btn ghost" :disabled="historyExportLoading" style="height: 32px; padding: 0 16px; border-radius: 6px; font-size: 13px; display: flex; align-items: center; gap: 5px; border-color: #cbd5e1; cursor: pointer; background: #fff;" @click="handleHistoryExport">
                <span>{{ historyExportLoading ? '正在导出...' : '📥 导出明细' }}</span>
              </button>
            </div>
          </div>

          <!-- 历史数据明细列表 -->
          <div v-if="historyLoading" class="loading-placeholder" style="padding: 40px; text-align: center; color: #64748b;">数据加载中...</div>
          <div v-else-if="historyRows.length === 0" class="empty-placeholder" style="padding: 40px; text-align: center; color: #777;">未查询到任何历史记录。</div>
          <div v-else>
            <div class="table-wrap" style="max-height: 550px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px;">
              <table class="table editor-table" style="margin: 0; width: 100%; border-collapse: collapse;">
                <thead>
                  <tr style="background: #f8fafc; border-bottom: 1px solid #e2e8f0; position: sticky; top: 0; z-index: 10;">
                    <th style="text-align: left; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">日期</th>
                    <th style="text-align: left; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">需求主体</th>
                    <th style="text-align: left; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">管材型号</th>
                    <th style="text-align: right; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">当日计划量 (米)</th>
                    <th style="text-align: right; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">当日使用量 (米)</th>
                    <th style="text-align: right; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">当日损耗量 (米)</th>
                    <th style="text-align: right; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">确认到货量 (米)</th>
                    <th style="text-align: left; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">运输在途时间</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in historyRows" :key="idx" style="border-bottom: 1px solid #e2e8f0; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#f8fafc'" onmouseout="this.style.backgroundColor='transparent'">
                    <td style="padding: 12px 16px; vertical-align: middle; color: #475569; font-size: 13px; font-weight: 500;">{{ row.biz_date }}</td>
                    <td style="padding: 12px 16px; vertical-align: middle; color: #1e293b; font-size: 13px; font-weight: 600;">{{ row.section_1_name || row.section_1_id }}</td>
                    <td style="padding: 12px 16px; vertical-align: middle; color: #334155; font-size: 13px;">{{ row.pipe_model_name || row.pipe_model_id }}</td>
                    <td style="text-align: right; padding: 12px 16px; vertical-align: middle; font-weight: 500; font-size: 13px; color: #475569;">{{ formatQty(row.plan_qty) }}</td>
                    <td style="text-align: right; padding: 12px 16px; vertical-align: middle; font-weight: 500; font-size: 13px; color: #16a34a;">{{ formatQty(row.usage_qty) }}</td>
                    <td style="text-align: right; padding: 12px 16px; vertical-align: middle; font-weight: 500; font-size: 13px; color: #dc2626;">{{ formatQty(row.loss_qty) }}</td>
                    <td style="text-align: right; padding: 12px 16px; vertical-align: middle; font-weight: 500; font-size: 13px; color: #2563eb;">{{ formatQty(row.arrived_qty) }}</td>
                    <td style="padding: 12px 16px; vertical-align: middle; color: #475569; font-size: 13px;">
                      {{ row.arrived_batch_count > 0 ? formatSeconds(row.total_transit_seconds / row.arrived_batch_count) : '-' }}
                    </td>
                  </tr>
                  
                  <!-- 汇总统计行 -->
                  <tr style="background: #f1f5f9; font-weight: bold; border-top: 2px solid #cbd5e1; position: sticky; bottom: 0; z-index: 5;">
                    <td colspan="3" style="padding: 14px 16px; font-size: 13px; color: #1e293b; background: #f1f5f9;">📊 历史时段内汇总统计</td>
                    <td style="text-align: right; padding: 14px 16px; font-size: 13px; color: #1e293b; background: #f1f5f9;">{{ formatQty(totalPlan) }}</td>
                    <td style="text-align: right; padding: 14px 16px; font-size: 13px; color: #16a34a; background: #f1f5f9;">{{ formatQty(totalUsage) }}</td>
                    <td style="text-align: right; padding: 14px 16px; font-size: 13px; color: #dc2626; background: #f1f5f9;">{{ formatQty(totalLoss) }}</td>
                    <td style="text-align: right; padding: 14px 16px; font-size: 13px; color: #2563eb; background: #f1f5f9;">{{ formatQty(totalArrived) }}</td>
                    <td style="padding: 14px 16px; font-size: 13px; color: #1e293b; background: #f1f5f9;">{{ overallAvgTransit }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- 决策辅助透视 -->
            <div v-if="historyRows.length > 0" style="margin-top: 15px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px 16px; border-radius: 6px; font-size: 13px; color: #334155; line-height: 1.8;">
              <div style="font-weight: 700; color: #0f172a; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
                <span>💡 历史时段决策透视数据：</span>
              </div>
              <div style="display: flex; flex-wrap: wrap; gap: 10px 30px;">
                <span>🟢 物资综合保障率：<strong style="color: #0f172a;">{{ fulfillmentRate }}</strong> (计划 {{ formatQty(totalPlan) }} 米 / 到货 {{ formatQty(totalArrived) }} 米)</span>
                <span>📅 计划消耗契合度：<strong style="color: #0f172a;">{{ planUsageAlignment }}</strong> (实际消耗 {{ formatQty(totalUsage) }} 米 / 计划 {{ formatQty(totalPlan) }} 米)</span>
                <span>🔴 施工综合损耗率：<strong style="color: #dc2626;">{{ lossRate }}</strong> (消耗 {{ formatQty(totalUsage) }} 米 / 损耗 {{ formatQty(totalLoss) }} 米)</span>
                <span>🔵 施工消耗强度：<strong style="color: #2563eb;">{{ dailyConsumption }} 米/天</strong> (实际施工 {{ activeDays }} 天)</span>
                <span>🚚 物流配送效率区间：最快 <strong style="color: #16a34a;">{{ minTransit }}</strong> / 最慢 <strong style="color: #ea580c;">{{ maxTransit }}</strong> (平均 {{ overallAvgTransit }})</span>
              </div>
            </div>

          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { AppHeader, Breadcrumbs, useTubePageShell } from './shared'
import { getTubeHistoryData, exportTubeHistoryData } from '../../daily_report_25_26/services/api'

const PROJECT_KEY = 'insulation_pipe_supply_2026'

const {
  loading,
  errorMessage,
  configSummary,
  breadcrumbItems,
  goProjectPages,
} = useTubePageShell('历史数据查询')

const demandEntities = computed(() => configSummary.value?.demand_entities || [])

// 历史数据查询相关 Ref 变量
const historyRows = ref([])
const historyLoading = ref(false)
const historyExportLoading = ref(false)

const getPastDateStr = (days) => {
  const d = new Date()
  d.setDate(d.getDate() - days)
  return d.toISOString().split('T')[0]
}
const getTodayStr = () => {
  return new Date().toISOString().split('T')[0]
}

const historyFilter = ref({
  section1Id: '',
  startDate: getPastDateStr(30),
  endDate: getTodayStr(),
})

// 历史数据查询核心逻辑
async function handleHistoryQuery() {
  historyLoading.value = true
  try {
    const res = await getTubeHistoryData(PROJECT_KEY, {
      section1Id: historyFilter.value.section1Id,
      startDate: historyFilter.value.startDate,
      endDate: historyFilter.value.endDate,
    })
    if (res && res.ok) {
      historyRows.value = res.rows || []
    }
  } catch (error) {
    console.error('查询历史数据失败:', error)
    alert(error?.message || '查询历史数据失败')
  } finally {
    historyLoading.value = false
  }
}

async function handleHistoryExport() {
  if (historyExportLoading.value) return
  historyExportLoading.value = true
  try {
    const blob = await exportTubeHistoryData(PROJECT_KEY, {
      section1Id: historyFilter.value.section1Id,
      startDate: historyFilter.value.startDate,
      endDate: historyFilter.value.endDate,
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const now = new Date()
    const y = now.getFullYear()
    const m = String(now.getMonth() + 1).padStart(2, '0')
    const d = String(now.getDate()).padStart(2, '0')
    const hh = String(now.getHours()).padStart(2, '0')
    const mm = String(now.getMinutes()).padStart(2, '0')
    const ss = String(now.getSeconds()).padStart(2, '0')
    const timestamp = `${y}${m}${d}_${hh}${mm}${ss}`
    link.setAttribute('download', `history_records_${timestamp}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('导出历史数据失败:', error)
    alert(error?.message || '导出历史数据失败')
  } finally {
    historyExportLoading.value = false
  }
}

function formatQty(val) {
  if (val === null || val === undefined || val === 0) return '-'
  return Number(val).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

function formatSeconds(totalSeconds) {
  if (!totalSeconds || totalSeconds <= 0) return '-'
  const secondsInt = Math.max(Math.floor(totalSeconds), 0)
  const days = Math.floor(secondsInt / 86400)
  const remainder1 = secondsInt % 86400
  const hours = Math.floor(remainder1 / 3600)
  const remainder2 = remainder1 % 3600
  const minutes = Math.floor(remainder2 / 60)
  const seconds = remainder2 % 60
  
  if (days > 0) return `${days}天${hours}小时${minutes}分`
  if (hours > 0) return `${hours}小时${minutes}分`
  if (minutes > 0) return `${minutes}分${seconds}秒`
  return `${seconds}秒`
}

const totalPlan = computed(() => historyRows.value.reduce((sum, r) => sum + (r.plan_qty || 0), 0))
const totalUsage = computed(() => historyRows.value.reduce((sum, r) => sum + (r.usage_qty || 0), 0))
const totalLoss = computed(() => historyRows.value.reduce((sum, r) => sum + (r.loss_qty || 0), 0))
const totalArrived = computed(() => historyRows.value.reduce((sum, r) => sum + (r.arrived_qty || 0), 0))
const overallAvgTransit = computed(() => {
  const totalSeconds = historyRows.value.reduce((sum, r) => sum + (r.total_transit_seconds || 0), 0)
  const totalBatches = historyRows.value.reduce((sum, r) => sum + (r.arrived_batch_count || 0), 0)
  if (totalBatches > 0) {
    return `${formatSeconds(totalSeconds / totalBatches)} (共${totalBatches}批)`
  }
  return '-'
})

const fulfillmentRate = computed(() => {
  if (totalPlan.value === 0) return '-'
  return (totalArrived.value / totalPlan.value * 100).toFixed(1) + '%'
})

const planUsageAlignment = computed(() => {
  if (totalPlan.value === 0) return '-'
  return (totalUsage.value / totalPlan.value * 100).toFixed(1) + '%'
})

const lossRate = computed(() => {
  const sum = totalUsage.value + totalLoss.value
  if (sum === 0) return '-'
  return (totalLoss.value / sum * 100).toFixed(1) + '%'
})

const activeDays = computed(() => {
  const dates = new Set()
  historyRows.value.forEach(r => {
    if (r.usage_qty > 0 && r.biz_date) {
      dates.add(r.biz_date)
    }
  })
  return dates.size
})

const dailyConsumption = computed(() => {
  if (activeDays.value === 0) return '-'
  return (totalUsage.value / activeDays.value).toFixed(1)
})

const minTransit = computed(() => {
  const val = historyRows.value.reduce((min, r) => {
    if (r.min_transit_seconds !== null && r.min_transit_seconds !== undefined) {
      return min === null ? r.min_transit_seconds : Math.min(min, r.min_transit_seconds)
    }
    return min
  }, null)
  return formatSeconds(val)
})

const maxTransit = computed(() => {
  const val = historyRows.value.reduce((max, r) => {
    if (r.max_transit_seconds !== null && r.max_transit_seconds !== undefined) {
      return max === null ? r.max_transit_seconds : Math.max(max, r.max_transit_seconds)
    }
    return max
  }, null)
  return formatSeconds(val)
})

onMounted(() => {
  // 默认自动查询一次最近30天
  handleHistoryQuery()
})
</script>

<style scoped>
.page-layout {
  min-height: 100vh;
  background: var(--neutral-50);
  display: flex;
  flex-direction: column;
}

.page-main {
  flex: 1;
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

.page-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title-row h2 {
  font-size: 24px;
  color: var(--neutral-800);
  margin: 0 0 6px 0;
}

.page-title-row .subtitle {
  font-size: 14px;
  color: var(--neutral-500);
  margin: 0;
}

.section-card {
  padding: 24px;
}

.card-header {
  font-size: 16px;
  font-weight: 700;
  color: var(--neutral-800);
  margin-bottom: 8px;
}

.block-sub {
  font-size: 13px;
  color: var(--neutral-500);
  margin: 0 0 20px 0;
}

.table-wrap {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.editor-table th, .editor-table td {
  border-bottom: 1px solid #e2e8f0;
}

.loading-state, .error-state {
  text-align: center;
  padding: 60px 0;
  color: var(--neutral-600);
}

.error-state {
  color: var(--danger);
}
</style>
