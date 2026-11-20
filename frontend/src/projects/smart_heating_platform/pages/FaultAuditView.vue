<template>
  <div class="shp-page-root">
    <AppHeader />
    <main class="shp-main container">
      <Breadcrumbs :items="breadcrumbItems" />

      <header class="card elevated topbar">
        <div>
          <div class="title-row">
            <h2>异常数据监测</h2>
          </div>
          <p class="subtitle">
            自动汇总每小时清洗拦截的异常点位，按故障类型与问题类别分类记录，便于运维快速定位与核查。
          </p>
        </div>
        <div class="topbar-actions">
          <button class="btn secondary btn-sm" type="button" @click="goBackPages">
            ⬅️ 返回功能页
          </button>
          <DateStepPicker v-model="selectedDate" aria-label="选择监测日期" @change="scheduleLoadAll" />
          <select v-model.number="days" class="ctrl-input" @change="loadAll">
            <option :value="1">当天（24h）</option>
            <option :value="3">近 3 天</option>
            <option :value="7">近 7 天</option>
            <option :value="30">近 30 天</option>
          </select>
          <button class="btn primary btn-sm" type="button" :disabled="auditing" @click="handleHeatAuditFix">
            {{ auditing ? '回看修正中…' : '🔧 立即回看检测与修正' }}
          </button>
          <button class="btn secondary btn-sm" type="button" @click="exportParty('RESEARCH_INSTITUTE')">
            📥 导出下位机故障清单
          </button>
          <button class="btn secondary btn-sm" type="button" @click="exportParty('UNIVERSITY_SOFTWARE')">
            📥 导出上位机缺陷清单
          </button>
        </div>
      </header>

      <div v-if="notice.text" :class="['notice-banner', notice.type]">{{ notice.text }}</div>

      <!-- 总览统计与 ECharts 分布 -->
      <section class="summary-grid">
        <div class="summary-cards">
          <div class="card elevated stat-card">
            <span class="stat-label">时段拦截异常总数</span>
            <strong class="stat-val text-err">{{ summary.total_tickets ?? 0 }} 条</strong>
          </div>
          <div
            v-for="ow in summary.by_owner || []"
            :key="ow.owner_party"
            class="card elevated stat-card"
          >
            <span class="stat-label">{{ ow.label }}</span>
            <strong class="stat-val">{{ ow.count }} 条</strong>
          </div>
          <div class="card elevated stat-card">
            <span class="stat-label">台账待补录项</span>
            <strong class="stat-val text-warn">
              {{ summary.missing_area_stations ?? 0 }} 站缺面积 / {{ summary.missing_tag_merchants ?? 0 }} 商户缺标签
            </strong>
          </div>
        </div>
        <div class="card elevated chart-card">
          <div ref="faultChartEl" class="chart-box"></div>
        </div>
      </section>

      <!-- 异常筛选与列表 -->
      <section class="card elevated list-card">
        <div class="filter-bar">
          <select v-model="filters.owner_party" class="ctrl-input" @change="loadTickets">
            <option value="">全部问题类别</option>
            <option value="RESEARCH_INSTITUTE">下位机/传感器故障</option>
            <option value="UNIVERSITY_SOFTWARE">上位机/台账缺陷</option>
            <option value="SHARED">现场与平台协同排查</option>
          </select>
          <select v-model="filters.fault_code" class="ctrl-input" @change="loadTickets">
            <option value="">全部 6 类故障</option>
            <option value="SENSOR_OUT_OF_RANGE">1.传感器断路/越限</option>
            <option value="COMM_OFFLINE">2.通讯中断与僵尸死数</option>
            <option value="HEAT_IMBALANCE">3.一二网热平衡失真</option>
            <option value="TEMP_INVERSION">4.供回水物理倒挂</option>
            <option value="METER_JUMP">5.累计表底跳变/清零</option>
            <option value="SOFTWARE_DEFECT">6.上位机接口与台账缺陷</option>
          </select>
          <input v-model="filters.keyword" type="search" class="ctrl-input" placeholder="搜索站点、测点或异常值…" @keyup.enter="loadTickets" />
          <button class="btn secondary btn-sm" type="button" @click="loadTickets">🔍 查询</button>
        </div>

        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>发生小时</th>
                <th>主体类型</th>
                <th>站点 / 测点名称</th>
                <th>故障类型</th>
                <th>问题类别</th>
                <th>原始异常值快照</th>
                <th>清洗处置策略</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="tickets.length === 0">
                <td colspan="7" class="empty-td">当前筛选条件下暂无异常监测记录</td>
              </tr>
              <tr v-for="t in tickets" :key="t.ticket_id">
                <td class="mono">{{ t.biz_hour }}</td>
                <td>{{ t.entity_type }}</td>
                <td class="font-bold">{{ t.entity_name }}</td>
                <td>{{ t.fault_label }}</td>
                <td>
                  <span :class="['owner-pill', t.owner_party === 'UNIVERSITY_SOFTWARE' ? 'owner-uni' : 'owner-res']">
                    {{ t.owner_label }}
                  </span>
                </td>
                <td class="mono raw-cell">{{ t.raw_value_text }}</td>
                <td class="muted-cell">{{ t.clean_strategy }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import '../../daily_report_25_26/styles/theme.css'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'
import DateStepPicker from '../components/DateStepPicker.vue'
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  downloadPlatformExcel,
  fetchFaultSummary,
  fetchFaultTickets,
  triggerHeatAuditFix,
} from '../services/api'

const router = useRouter()

function goBackPages() {
  router.push('/projects/smart_heating_platform/pages')
}

function todayIso() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const selectedDate = ref(todayIso())
const days = ref(1)
const auditing = ref(false)
const summary = ref({ total_tickets: 0, by_fault_code: [], by_owner: [] })
const tickets = ref([])
const notice = reactive({ type: 'info', text: '' })
const filters = reactive({ owner_party: '', fault_code: '', keyword: '' })

const faultChartEl = ref(null)
let faultChart = null

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '智慧供热平台精算模块', to: '/projects/smart_heating_platform/pages' },
  { label: '异常数据监测', to: null },
])

let auditSeq = 0
let auditAbortCtrl = null
let auditDebounceTimer = null

function scheduleLoadAll(delayMs = 180) {
  if (auditDebounceTimer) {
    clearTimeout(auditDebounceTimer)
    auditDebounceTimer = null
  }
  auditDebounceTimer = setTimeout(() => {
    auditDebounceTimer = null
    loadAll()
  }, delayMs)
}

async function loadSummary(reqId, signal) {
  const res = await fetchFaultSummary(
    { date: selectedDate.value, days: days.value },
    signal ? { signal } : {},
  )
  if (reqId !== auditSeq) return
  if (res?.data) {
    summary.value = res.data
    await nextTick()
    if (reqId === auditSeq) renderChart()
  }
}

async function loadTickets(reqId = null, signal = undefined) {
  const standalone = reqId === null
  let effectiveId = reqId
  let effectiveSignal = signal
  if (standalone) {
    effectiveId = ++auditSeq
    if (auditAbortCtrl) auditAbortCtrl.abort()
    auditAbortCtrl = typeof AbortController !== 'undefined' ? new AbortController() : null
    effectiveSignal = auditAbortCtrl ? auditAbortCtrl.signal : undefined
  }
  try {
    const res = await fetchFaultTickets(
      {
        date: selectedDate.value,
        days: days.value,
        ...filters,
      },
      effectiveSignal ? { signal: effectiveSignal } : {},
    )
    if (effectiveId !== auditSeq) return
    if (res?.data) tickets.value = res.data
  } catch (err) {
    if (standalone && (err?.name === 'AbortError' || effectiveId !== auditSeq)) return
    throw err
  }
}

async function loadAll() {
  if (auditDebounceTimer) {
    clearTimeout(auditDebounceTimer)
    auditDebounceTimer = null
  }
  const reqId = ++auditSeq
  if (auditAbortCtrl) {
    auditAbortCtrl.abort()
  }
  auditAbortCtrl = typeof AbortController !== 'undefined' ? new AbortController() : null
  const signal = auditAbortCtrl ? auditAbortCtrl.signal : undefined
  try {
    await Promise.all([loadSummary(reqId, signal), loadTickets(reqId, signal)])
  } catch (err) {
    if (err?.name === 'AbortError' || reqId !== auditSeq) return
    notice.type = 'error'
    notice.text = `加载督办数据失败：${err.message}`
  }
}

async function handleHeatAuditFix() {
  auditing.value = true
  notice.type = 'info'
  notice.text = `正在回看检测并修正 ${selectedDate.value} 及选定范围的越限热量与倍率异常…`
  try {
    const res = await triggerHeatAuditFix({
      target_date: selectedDate.value,
      lookback_days: days.value,
    })
    const stCnt = Number(res?.fixed_station_hours || 0)
    const upCnt = Number(res?.fixed_upstream_hours || 0)
    const tktCnt = Number(res?.fault_tickets_written || 0)
    notice.type = 'success'
    notice.text = `回看检测修正完成：修正换热站 ${stCnt} 时、上游测点 ${upCnt} 时，生成/更新异常审计记录 ${tktCnt} 条。`
    await loadAll()
  } catch (err) {
    notice.type = 'error'
    notice.text = `回看检测修正失败：${err.message}`
  } finally {
    auditing.value = false
  }
}

async function exportParty(ownerParty) {
  try {
    const label = ownerParty === 'RESEARCH_INSTITUTE' ? '下位机故障' : (ownerParty === 'UNIVERSITY_SOFTWARE' ? '上位机缺陷' : '全部异常')
    await downloadPlatformExcel(
      `/faults/export?owner_party=${ownerParty}&date=${encodeURIComponent(selectedDate.value)}&days=${days.value}`,
      `智慧供热异常监测清单_${label}_${selectedDate.value}.xlsx`,
    )
  } catch (err) {
    notice.type = 'error'
    notice.text = err.message
  }
}

function renderChart() {
  if (!faultChartEl.value) return
  if (!faultChart) faultChart = echarts.init(faultChartEl.value)
  const items = summary.value.by_fault_code || []
  const isNarrow = typeof window !== 'undefined' && window.innerWidth <= 640
  faultChart.setOption({
    title: { text: '6 大类数据质量异常分布', textStyle: { fontSize: isNarrow ? 12 : 13 } },
    tooltip: { trigger: 'axis' },
    grid: { left: isNarrow ? 8 : 155, right: 24, top: 36, bottom: 24, containLabel: isNarrow },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: items.map((i) => i.label).reverse() },
    series: [
      {
        type: 'bar',
        data: items.map((i) => i.count).reverse(),
        itemStyle: { color: '#b91c1c' },
        label: { show: true, position: 'right' },
      },
    ],
  }, true)
  faultChart.resize()
}

function onResize() {
  faultChart?.resize()
}

let chartResizeObserver = null
onMounted(() => {
  window.addEventListener('resize', onResize)
  if (typeof ResizeObserver !== 'undefined' && faultChartEl.value) {
    chartResizeObserver = new ResizeObserver(() => onResize())
    chartResizeObserver.observe(faultChartEl.value)
  }
  loadAll()
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chartResizeObserver?.disconnect()
  if (auditDebounceTimer) clearTimeout(auditDebounceTimer)
  auditAbortCtrl?.abort()
  faultChart?.dispose()
})
</script>

<style scoped>
.shp-page-root { overflow-x: clip; }
.shp-main { padding: 18px 16px 40px; max-width: 1400px; width: 100%; box-sizing: border-box; margin: 0 auto; display: flex; flex-direction: column; gap: 14px; }
.shp-main > * { min-width: 0; max-width: 100%; box-sizing: border-box; }
.topbar { padding: 16px 20px; display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.title-row { display: flex; align-items: center; gap: 10px; }
.title-row h2 { margin: 0; font-size: 18px; }
.badge-yin { font-size: 12px; font-weight: 600; background: #fee2e2; color: #991b1b; padding: 2px 10px; border-radius: 999px; }
.subtitle { margin: 6px 0 0; font-size: 13px; color: #64748b; }
.topbar-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.ctrl-input { border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 10px; font-size: 13px; background: #fff; }
.notice-banner { padding: 10px 14px; border-radius: 8px; font-size: 13px; }
.notice-banner.info { background: #eff6ff; color: #1d4ed8; }
.notice-banner.success { background: #f0fdf4; color: #166534; }
.notice-banner.error { background: #fef2f2; color: #991b1b; }
.summary-grid { display: grid; grid-template-columns: 1fr 1.2fr; gap: 14px; }
@media (max-width: 960px) { .summary-grid { grid-template-columns: 1fr; } }
.summary-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; }
.stat-card { padding: 14px 16px; display: flex; flex-direction: column; gap: 4px; }
.stat-label { font-size: 12px; color: #64748b; }
.stat-val { font-size: 18px; color: #0f172a; }
.stat-sub { font-size: 12px; color: #64748b; }
.chart-card { padding: 14px 16px; min-width: 0; overflow: hidden; }
.chart-box { height: 220px; width: 100%; min-width: 0; max-width: 100%; overflow: hidden; }
.list-card { padding: 16px 20px; display: flex; flex-direction: column; gap: 12px; }
.filter-bar { display: flex; gap: 10px; flex-wrap: wrap; }
.table-wrap { overflow-x: auto; max-height: 540px; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th, .data-table td { padding: 9px 11px; border-bottom: 1px solid #e2e8f0; text-align: left; }
.data-table thead th { position: sticky; top: 0; background: #f8fafc; font-weight: 600; z-index: 4; }
.owner-pill { padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; white-space: nowrap; }
.owner-res { background: #ffedd5; color: #9a3412; }
.owner-uni { background: #e0e7ff; color: #3730a3; }
.raw-cell { color: #b91c1c; max-width: 260px; word-break: break-all; }
.muted-cell { color: #64748b; max-width: 240px; }
.empty-td { text-align: center !important; color: #64748b; padding: 28px !important; }
.font-bold { font-weight: 600; }
.text-err { color: #dc2626; }
.text-warn { color: #d97706; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }

@media (max-width: 768px) {
  .shp-main { padding: 12px 10px 28px; gap: 10px; }
  .topbar, .list-card, .chart-card { padding: 12px; }
  .title-row { flex-wrap: wrap; gap: 6px; }
  .title-row h2 { font-size: 16px; }
  .topbar-actions { width: 100%; display: grid; grid-template-columns: 1fr; gap: 8px; }
  .topbar-actions > .ctrl-input, .topbar-actions > .btn { width: 100%; justify-content: center; }
  .summary-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .stat-card { padding: 11px 12px; }
  .filter-bar > .ctrl-input { flex: 1 1 140px; min-width: 0; }
  .data-table { font-size: 12px; }
  .data-table th, .data-table td { padding: 7px 8px; }
}
</style>
