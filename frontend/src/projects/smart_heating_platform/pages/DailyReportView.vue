<template>
  <div class="shp-page-root">
    <AppHeader />
    <main class="shp-main container">
      <Breadcrumbs :items="breadcrumbItems" />
      <PlatformSubNav current="daily_report" />

      <header class="card elevated topbar">
        <div>
          <div class="title-row">
            <h2>每日运行报告与手工日报双轨核对</h2>
          </div>
          <p class="subtitle">
            结算周期：{{ meta.window_start || '-' }} ~ {{ meta.window_end || '-' }}（系统自动表底抄表/{{ meta.snapshot_interval_minutes ?? 5 }}分钟积分 vs 日报手工填报对比）
          </p>
        </div>
        <div class="topbar-actions">
          <label class="inline-field">
            <span>结算日期</span>
            <DateStepPicker v-model="selectedDate" aria-label="选择结算日期" @change="scheduleLoadReport" />
          </label>
          <select v-model="periodMode" class="ctrl-input" @change="loadReport">
            <option value="natural">自然日（00:00 ~ 次日00:00）</option>
            <option value="shift">生产班次（昨日08:00 ~ 今日08:00）</option>
          </select>
          <div class="mode-switch" role="group" aria-label="数据口径切换">
            <button
              type="button"
              :class="['mode-btn', { active: mode === 'clean' }]"
              title="默认展示突发异常已修正后日报数据"
              @click="switchMode('clean')"
            >
              修正后数据
            </button>
            <button
              type="button"
              :class="['mode-btn', { 'raw-active': mode === 'raw' }]"
              title="一键还原未经清洗修正的原始采集汇总数据"
              @click="switchMode(mode === 'raw' ? 'clean' : 'raw')"
            >
              {{ mode === 'raw' ? '✨ 恢复修正后数据' : '🔄 一键还原原始数据' }}
            </button>
          </div>
          <button class="btn secondary btn-sm" type="button" :disabled="calibrating" @click="handleCalibrateToday">
            {{ calibrating ? '校准中(约3分钟)…' : '📏 校准当日表底' }}
          </button>
          <button
            class="btn primary btn-sm"
            type="button"
            title="导出本供暖季/近31天逐日趋势矩阵与选定日完整双轨核对 Excel"
            @click="handleExport"
          >
            📥 导出逐日统计报告
          </button>
        </div>
      </header>

      <div v-if="mode === 'raw'" class="raw-mode-banner">
        <span>⚠️ 当前已一键还原显示 <strong>原始采集数据</strong>（未修正突发跳变与表底倍率），红色标注表示存在突发跳变原始极值。</span>
        <button class="btn primary btn-sm" type="button" @click="switchMode('clean')">✨ 恢复修正后数据</button>
      </div>

      <div v-if="notice.text" :class="['notice-banner', notice.type]">{{ notice.text }}</div>

      <!-- 日度核心 KPI -->
      <section class="kpi-grid">
        <div class="card elevated kpi-card highlight">
          <span class="kpi-label">系统日精算总供热量</span>
          <strong class="kpi-val">
            <AnomalyBadgeValue placement="bottom" :text="fmt(kpis.day_heat_gj, ' GJ')" :note="kpis.anomalies?.day_heat_gj?.note" />
          </strong>
          <span class="kpi-sub">
            万平耗热量 <AnomalyBadgeValue placement="bottom" :text="fmt(kpis.day_heat_per_wan, ' GJ/万㎡·d')" :note="kpis.anomalies?.day_heat_per_wan?.note" />
          </span>
        </div>
        <div class="card elevated kpi-card">
          <span class="kpi-label">手工日报站内耗热量</span>
          <strong class="kpi-val">{{ fmt(kpis.manual_total_heat_gj, ' GJ') }}</strong>
          <span class="kpi-sub">来源于 Phoenix 每日填报</span>
        </div>
        <div class="card elevated kpi-card">
          <span class="kpi-label">双轨汇总偏差率</span>
          <strong :class="['kpi-val', Math.abs(kpis.overall_diff_pct || 0) > 10 ? 'text-err' : 'text-ok']">
            <AnomalyBadgeValue
              placement="bottom"
              :text="kpis.overall_diff_pct != null ? `${kpis.overall_diff_pct > 0 ? '+' : ''}${kpis.overall_diff_pct}%` : '-'"
              :note="kpis.anomalies?.overall_diff_pct?.note"
            />
          </strong>
          <span class="kpi-sub">超过 ±10% 自动标红告警</span>
        </div>
        <div class="card elevated kpi-card">
          <span class="kpi-label">系统日累计总补水量</span>
          <strong class="kpi-val">
            <AnomalyBadgeValue placement="bottom" :text="fmt(kpis.day_water_t, ' t')" :note="kpis.anomalies?.day_water_t?.note" />
          </strong>
          <span class="kpi-sub">按 24 小时补水表底/积分汇总</span>
        </div>
      </section>

      <!-- 三标签正文 -->
      <section class="card elevated tabs-card">
        <div class="tab-bar">
          <button type="button" :class="['tab-btn', { active: activeTab === 'compare' }]" @click="activeTab = 'compare'">
            ⚖️ 服务中心汇总日报（9）
          </button>
          <button type="button" :class="['tab-btn', { active: activeTab === 'stations' }]" @click="activeTab = 'stations'">
            🏭 换热站消耗量日报（242）
          </button>
          <button type="button" :class="['tab-btn', { active: activeTab === 'merchants' }]" @click="activeTab = 'merchants'">
            🏬 商业用户用量日报（464）
          </button>
        </div>

        <!-- Tab 1: 双轨核对 -->
        <div v-if="activeTab === 'compare'">
          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <SortableTh label="服务中心" sort-key="center_name" :sort-state="compareSort.state" @sort="compareSort.toggle" />
                  <SortableTh label="在网面积 (万㎡)" sort-key="covered_area_wan" :sort-state="compareSort.state" @sort="compareSort.toggle" />
                  <SortableTh label="系统精算热量 (GJ)" sort-key="sys_heat_gj" :sort-state="compareSort.state" @sort="compareSort.toggle" />
                  <SortableTh label="手工填报热量 (GJ)" sort-key="man_heat_gj" :sort-state="compareSort.state" @sort="compareSort.toggle" />
                  <SortableTh label="热量偏差 (GJ)" sort-key="heat_diff_gj" :sort-state="compareSort.state" @sort="compareSort.toggle" />
                  <SortableTh label="偏差率" sort-key="heat_diff_pct" :sort-state="compareSort.state" @sort="compareSort.toggle" />
                  <SortableTh label="万平耗热 (GJ/万㎡)" sort-key="heat_per_wan_gj" :sort-state="compareSort.state" @sort="compareSort.toggle" />
                  <SortableTh label="系统补水 (t)" sort-key="sys_water_t" :sort-state="compareSort.state" @sort="compareSort.toggle" />
                  <SortableTh label="手工补水 (t)" sort-key="man_water_t" :sort-state="compareSort.state" @sort="compareSort.toggle" />
                  <SortableTh label="日均室温 (℃)" sort-key="avg_room_temp" :sort-state="compareSort.state" @sort="compareSort.toggle" />
                </tr>
              </thead>
              <tbody>
                <tr v-for="c in compareSort.sortedRows.value" :key="c.center_id" :class="{ 'row-alert': c.is_heat_alert }">
                  <td class="font-bold">{{ c.center_name }}</td>
                  <td>{{ fmt(c.covered_area_wan) }}</td>
                  <td class="font-bold">
                    <AnomalyBadgeValue :text="fmt(c.sys_heat_gj)" :note="c.anomalies?.sys_heat_gj?.note" />
                  </td>
                  <td>{{ fmt(c.man_heat_gj) }}</td>
                  <td>
                    <AnomalyBadgeValue :text="fmt(c.heat_diff_gj)" :note="c.anomalies?.heat_diff_gj?.note" />
                  </td>
                  <td>
                    <AnomalyBadgeValue
                      v-if="c.heat_diff_pct != null"
                      :note="c.anomalies?.heat_diff_pct?.note"
                    >
                      <span :class="['diff-pill', c.is_heat_alert ? 'pill-err' : 'pill-ok']">
                        {{ c.heat_diff_pct > 0 ? '+' : '' }}{{ c.heat_diff_pct }}%
                      </span>
                    </AnomalyBadgeValue>
                    <span v-else>-</span>
                  </td>
                  <td>
                    <AnomalyBadgeValue :text="fmt(c.heat_per_wan_gj)" :note="c.anomalies?.heat_per_wan_gj?.note" />
                  </td>
                  <td>
                    <AnomalyBadgeValue :text="fmt(c.sys_water_t)" :note="c.anomalies?.sys_water_t?.note" />
                  </td>
                  <td>{{ fmt(c.man_water_t) }}</td>
                  <td>{{ fmt(c.avg_room_temp) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Tab 2: 242站日度能耗 -->
        <div v-if="activeTab === 'stations'">
          <div class="filter-bar">
            <input v-model="stKeyword" type="search" class="ctrl-input" placeholder="筛选换热站名称或中心…" />
          </div>
          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <SortableTh label="换热站" sort-key="name" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="服务中心" sort-key="center_name" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="主干热网" sort-key="rdfz" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="面积 (㎡)" sort-key="covered_area" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="有效小时 / 表底小时" sort-key="hours_count" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="起表底 totJ" sort-key="start_tot_j" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="止表底 totJ" sort-key="end_tot_j" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="日供热量 (GJ)" sort-key="day_heat_gj" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="万平耗热" sort-key="heat_per_wan_gj" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="日补水 (t)" sort-key="day_water_t" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="日电耗 (kWh)" sort-key="day_elec_kwh" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="日均供/回温 (℃)" sort-key="avg_sup_temp" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                </tr>
              </thead>
              <tbody>
                <tr v-for="s in stationSort.sortedRows.value" :key="s.station_id">
                  <td class="font-bold">{{ s.name }}</td>
                  <td>{{ s.center_name }}</td>
                  <td>{{ s.rdfz }}</td>
                  <td>{{ s.covered_area ? s.covered_area.toLocaleString() : '待补' }}</td>
                  <td>{{ s.hours_count }}h / {{ s.meter_diff_hours }}h</td>
                  <td class="mono">{{ fmt(s.start_tot_j) }}</td>
                  <td class="mono">{{ fmt(s.end_tot_j) }}</td>
                  <td class="font-bold">
                    <AnomalyBadgeValue :text="fmt(s.day_heat_gj)" :note="s.anomalies?.day_heat_gj?.note" />
                  </td>
                  <td>
                    <AnomalyBadgeValue :text="fmt(s.heat_per_wan_gj)" :note="s.anomalies?.heat_per_wan_gj?.note" />
                  </td>
                  <td>
                    <AnomalyBadgeValue :text="fmt(s.day_water_t)" :note="s.anomalies?.day_water_t?.note" />
                  </td>
                  <td>{{ fmt(s.day_elec_kwh) }}</td>
                  <td>
                    <AnomalyBadgeValue :text="`${fmt(s.avg_sup_temp)} / ${fmt(s.avg_ret_temp)}`" :note="s.anomalies?.avg_sup_temp?.note || s.anomalies?.avg_ret_temp?.note" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Tab 3: 464户商业用户 -->
        <div v-if="activeTab === 'merchants'">
          <div class="filter-bar">
            <input v-model="mcKeyword" type="search" class="ctrl-input" placeholder="筛选商户名称或主干热网…" />
            <button class="btn secondary btn-sm" type="button" :disabled="syncingMerchant" @click="handleSyncMerchants">
              {{ syncingMerchant ? '拉取中…' : '🔄 立即拉取商户日耗量' }}
            </button>
          </div>
          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <SortableTh label="商户名称" sort-key="name" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                  <SortableTh label="主干热网 (rdfz)" sort-key="rdfz" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                  <SortableTh label="介质 (rdry)" sort-key="rdry" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                  <SortableTh label="产权 (rdss)" sort-key="rdss" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                  <SortableTh label="价格分类 (rdjg)" sort-key="rdjg" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                  <SortableTh label="改造批次 (rdgz)" sort-key="rdgz" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                  <SortableTh label="日累计消耗量" sort-key="daily_consumption" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                  <SortableTh label="日单耗参考" sort-key="daily_unit_heat" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                </tr>
              </thead>
              <tbody>
                <tr v-for="m in merchantSort.sortedRows.value" :key="m.merchant_id">
                  <td class="font-bold">{{ m.name }}</td>
                  <td>{{ m.rdfz || '待补录' }}</td>
                  <td>{{ m.rdry || '待补录' }}</td>
                  <td>{{ m.rdss || '待补录' }}</td>
                  <td>{{ m.rdjg || '待补录' }}</td>
                  <td>{{ m.rdgz || '待补录' }}</td>
                  <td class="font-bold">{{ fmt(m.daily_consumption) }}</td>
                  <td>{{ fmt(m.daily_unit_heat) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import '../../daily_report_25_26/styles/theme.css'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'
import PlatformSubNav from '../components/PlatformSubNav.vue'
import DateStepPicker from '../components/DateStepPicker.vue'
import AnomalyBadgeValue from '../components/AnomalyBadgeValue.vue'
import SortableTh from '../components/SortableTh.vue'
import { useTableSort } from '../utils/tableSort'
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { downloadPlatformExcel, fetchDailyReport, triggerManualCollect } from '../services/api'

function yesterdayIso() {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const selectedDate = ref(yesterdayIso())
const periodMode = ref('natural')
const mode = ref('clean')
const activeTab = ref('compare')
const stKeyword = ref('')
const mcKeyword = ref('')
const calibrating = ref(false)
const syncingMerchant = ref(false)
const notice = reactive({ type: 'info', text: '' })

const reportData = ref({
  meta: {},
  kpis: {},
  center_comparison: [],
  station_daily: [],
  merchant_daily: [],
})

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '智慧供热平台精算模块', to: '/projects/smart_heating_platform/pages' },
  { label: '每日运行报告', to: null },
])

const meta = computed(() => reportData.value.meta || {})
const kpis = computed(() => reportData.value.kpis || {})

const filteredStationDaily = computed(() => {
  const kw = stKeyword.value.trim().toLowerCase()
  return (reportData.value.station_daily || []).filter((s) => {
    if (!kw) return true
    return String(s.name || '').toLowerCase().includes(kw) || String(s.center_name || '').toLowerCase().includes(kw)
  })
})

const filteredMerchants = computed(() => {
  const kw = mcKeyword.value.trim().toLowerCase()
  return (reportData.value.merchant_daily || []).filter((m) => {
    if (!kw) return true
    return String(m.name || '').toLowerCase().includes(kw) || String(m.rdfz || '').toLowerCase().includes(kw)
  })
})

const compareSort = useTableSort(() => reportData.value.center_comparison || [])
const stationSort = useTableSort(filteredStationDaily)
const merchantSort = useTableSort(filteredMerchants)

function fmt(val, suffix = '') {
  if (val === null || val === undefined || val === '') return '-'
  const num = Number(val)
  if (Number.isNaN(num)) return '-'
  return `${num.toFixed(2).replace(/\.00$/, '')}${suffix}`
}

let dailySeq = 0
let dailyAbortCtrl = null
let dailyDebounceTimer = null

function scheduleLoadReport(delayMs = 180) {
  if (dailyDebounceTimer) {
    clearTimeout(dailyDebounceTimer)
    dailyDebounceTimer = null
  }
  dailyDebounceTimer = setTimeout(() => {
    dailyDebounceTimer = null
    loadReport()
  }, delayMs)
}

async function loadReport() {
  if (dailyDebounceTimer) {
    clearTimeout(dailyDebounceTimer)
    dailyDebounceTimer = null
  }
  const reqId = ++dailySeq
  if (dailyAbortCtrl) {
    dailyAbortCtrl.abort()
  }
  dailyAbortCtrl = typeof AbortController !== 'undefined' ? new AbortController() : null
  try {
    const res = await fetchDailyReport(
      { date: selectedDate.value, period_mode: periodMode.value, mode: mode.value },
      dailyAbortCtrl ? { signal: dailyAbortCtrl.signal } : {},
    )
    if (reqId !== dailySeq) return
    if (res?.data) reportData.value = res.data
  } catch (err) {
    if (err?.name === 'AbortError' || reqId !== dailySeq) return
    notice.type = 'error'
    notice.text = `加载每日运行报告失败：${err.message}`
  }
}

onBeforeUnmount(() => {
  if (dailyDebounceTimer) clearTimeout(dailyDebounceTimer)
  dailyAbortCtrl?.abort()
})

function switchMode(nextMode) {
  mode.value = nextMode
  loadReport()
}

async function handleCalibrateToday() {
  calibrating.value = true
  notice.type = 'info'
  notice.text = `正在对 ${selectedDate.value} 全网 242 座站慢速回溯表底（单线程间隔保护），请稍候…`
  try {
    const res = await triggerManualCollect({ action: 'calib', target_date: selectedDate.value })
    notice.type = 'success'
    notice.text = `表底校准完成：共更新 ${res.updated_station_hours} 条站-小时记录，拦截表底跳变 ${res.jump_faults} 次。`
    await loadReport()
  } catch (err) {
    notice.type = 'error'
    notice.text = `表底校准失败：${err.message}`
  } finally {
    calibrating.value = false
  }
}

async function handleSyncMerchants() {
  syncingMerchant.value = true
  try {
    const res = await triggerManualCollect({ action: 'merchant', target_date: selectedDate.value })
    notice.type = res.ok ? 'success' : 'error'
    notice.text = res.ok ? `商业用户日耗量已更新 ${res.merchants_saved} 户` : (res.message || '拉取失败')
    await loadReport()
  } catch (err) {
    notice.type = 'error'
    notice.text = err.message
  } finally {
    syncingMerchant.value = false
  }
}

async function handleExport() {
  try {
    const periodTag = periodMode.value === 'shift' ? '生产班次' : '自然日'
    const modeTag = mode.value === 'raw' ? '_原始数据' : ''
    await downloadPlatformExcel(
      `/reports/daily/export?date=${encodeURIComponent(selectedDate.value)}&period_mode=${periodMode.value}&mode=${mode.value}`,
      `每日运行统计报告_${selectedDate.value}_${periodTag}${modeTag}.xlsx`,
    )
  } catch (err) {
    notice.type = 'error'
    notice.text = err.message
  }
}

onMounted(loadReport)
</script>

<style scoped>
.shp-main { padding: 18px 16px 40px; max-width: 1400px; margin: 0 auto; display: flex; flex-direction: column; gap: 14px; }
.topbar { padding: 16px 20px; display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.title-row { display: flex; align-items: center; gap: 10px; }
.title-row h2 { margin: 0; font-size: 18px; }
.badge-yang { font-size: 12px; font-weight: 600; background: #dcfce7; color: #166534; padding: 2px 10px; border-radius: 999px; }
.subtitle { margin: 6px 0 0; font-size: 13px; color: #64748b; }
.topbar-actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
.inline-field { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; }
.ctrl-input { border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 10px; font-size: 13px; background: #fff; }
.mode-switch { display: inline-flex; align-items: center; height: 34px; box-sizing: border-box; border: 1px solid #cbd5e1; border-radius: 8px; overflow: hidden; background: #f8fafc; flex-shrink: 0; }
.mode-btn { height: 100%; box-sizing: border-box; padding: 0 12px; font-size: 13px; line-height: 1; display: inline-flex; align-items: center; justify-content: center; border: none; background: #f8fafc; color: #475569; cursor: pointer; font-weight: 600; white-space: nowrap; }
.mode-btn + .mode-btn { border-left: 1px solid #e2e8f0; }
.mode-btn.active { background: #1d4ed8; color: #fff; }
.mode-btn.raw-active { background: #dc2626; color: #fff; }
.raw-mode-banner { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; padding: 10px 14px; border-radius: 10px; background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; font-size: 13px; }
.notice-banner { padding: 10px 14px; border-radius: 8px; font-size: 13px; }
.notice-banner.success { background: #ecfdf5; color: #065f46; }
.notice-banner.error { background: #fef2f2; color: #991b1b; }
.notice-banner.info { background: #eff6ff; color: #1e40af; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
.kpi-card { padding: 14px 16px; display: flex; flex-direction: column; gap: 4px; }
.kpi-card.highlight { background: linear-gradient(135deg, #eff6ff 0%, #ffffff 100%); border: 1px solid #bfdbfe; }
.kpi-label { font-size: 12px; color: #64748b; }
.kpi-val { font-size: 18px; color: #0f172a; }
.kpi-sub { font-size: 12px; color: #64748b; }
.tabs-card { padding: 16px 20px; display: flex; flex-direction: column; gap: 12px; }
.tab-bar { display: flex; gap: 8px; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px; flex-wrap: wrap; }
.tab-btn { padding: 8px 16px; border: none; border-radius: 8px; background: #f1f5f9; color: #334155; font-size: 13px; font-weight: 600; cursor: pointer; }
.tab-btn.active { background: #0f172a; color: #fff; }
.filter-bar { display: flex; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.table-wrap { overflow-x: auto; max-height: 560px; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; white-space: nowrap; }
.data-table th, .data-table td { padding: 9px 11px; border-bottom: 1px solid #e2e8f0; text-align: left; }
.data-table thead th { position: sticky; top: 0; background: #f8fafc; font-weight: 600; z-index: 4; }
.row-alert td { background: #fef2f2; }
.diff-pill { padding: 2px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.pill-ok { background: #dcfce7; color: #166534; }
.pill-err { background: #fee2e2; color: #991b1b; }
.font-bold { font-weight: 600; }
.text-ok { color: #059669; }
.text-err { color: #dc2626; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }

@media (max-width: 768px) {
  .shp-main { padding: 12px 10px 28px; gap: 10px; }
  .topbar, .tabs-card { padding: 12px; }
  .title-row { flex-wrap: wrap; gap: 6px; }
  .title-row h2 { font-size: 16px; }
  .topbar-actions { width: 100%; display: grid; grid-template-columns: 1fr; gap: 8px; }
  .inline-field { width: 100%; justify-content: space-between; }
  .inline-field .ctrl-input { flex: 1; min-width: 0; }
  .topbar-actions > .btn { width: 100%; justify-content: center; }
  .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .kpi-card { padding: 11px 12px; }
  .kpi-val { font-size: 16px; }
  .tab-bar { flex-wrap: nowrap; overflow-x: auto; -webkit-overflow-scrolling: touch; gap: 6px; }
  .tab-btn { flex-shrink: 0; padding: 7px 12px; font-size: 12px; }
  .filter-bar > .ctrl-input { flex: 1 1 160px; min-width: 0; }
  .data-table { font-size: 12px; }
  .data-table th, .data-table td { padding: 7px 8px; }
}
</style>
