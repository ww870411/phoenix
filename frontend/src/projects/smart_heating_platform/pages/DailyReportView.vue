<template>
  <div class="shp-page-root">
    <AppHeader />
    <main class="shp-main container">
      <Breadcrumbs :items="breadcrumbItems" />
      <PlatformSubNav current="daily_report" />

      <header class="card elevated topbar">
        <div>
          <div class="title-row">
            <h2>每日生产精算日报与手工日报双轨核对</h2>
            <span class="badge-yang">阳面日结视图</span>
          </div>
          <p class="subtitle">
            结算周期：{{ meta.window_start || '-' }} ~ {{ meta.window_end || '-' }}（系统自动表底抄表/15分钟积分 vs Phoenix 手工填报对比）
          </p>
        </div>
        <div class="topbar-actions">
          <label class="inline-field">
            <span>结算日期</span>
            <input v-model="selectedDate" type="date" class="ctrl-input" @change="loadReport" />
          </label>
          <select v-model="periodMode" class="ctrl-input" @change="loadReport">
            <option value="natural">自然日（00:00 ~ 次日00:00）</option>
            <option value="shift">生产班次（昨日08:00 ~ 今日08:00）</option>
          </select>
          <button class="btn secondary btn-sm" type="button" :disabled="calibrating" @click="handleCalibrateToday">
            {{ calibrating ? '校准中(约3分钟)…' : '📏 校准当日表底' }}
          </button>
          <button class="btn primary btn-sm" type="button" @click="handleExport">
            📥 导出日报 Excel
          </button>
        </div>
      </header>

      <div v-if="notice.text" :class="['notice-banner', notice.type]">{{ notice.text }}</div>

      <!-- 日度核心 KPI -->
      <section class="kpi-grid">
        <div class="card elevated kpi-card highlight">
          <span class="kpi-label">系统日精算总供热量</span>
          <strong class="kpi-val">{{ fmt(kpis.day_heat_gj, ' GJ') }}</strong>
          <span class="kpi-sub">万平耗热量 {{ fmt(kpis.day_heat_per_wan, ' GJ/万㎡·d') }}</span>
        </div>
        <div class="card elevated kpi-card">
          <span class="kpi-label">手工日报站内耗热量</span>
          <strong class="kpi-val">{{ fmt(kpis.manual_total_heat_gj, ' GJ') }}</strong>
          <span class="kpi-sub">来源于 Phoenix 每日填报</span>
        </div>
        <div class="card elevated kpi-card">
          <span class="kpi-label">双轨汇总偏差率</span>
          <strong :class="['kpi-val', Math.abs(kpis.overall_diff_pct || 0) > 10 ? 'text-err' : 'text-ok']">
            {{ kpis.overall_diff_pct != null ? `${kpis.overall_diff_pct > 0 ? '+' : ''}${kpis.overall_diff_pct}%` : '-' }}
          </strong>
          <span class="kpi-sub">超过 ±10% 自动标红告警</span>
        </div>
        <div class="card elevated kpi-card">
          <span class="kpi-label">系统日累计总补水量</span>
          <strong class="kpi-val">{{ fmt(kpis.day_water_t, ' t') }}</strong>
          <span class="kpi-sub">按 24 小时补水表底/积分汇总</span>
        </div>
      </section>

      <!-- 三标签正文 -->
      <section class="card elevated tabs-card">
        <div class="tab-bar">
          <button type="button" :class="['tab-btn', { active: activeTab === 'compare' }]" @click="activeTab = 'compare'">
            ⚖️ 9大中心手工日报双轨核对
          </button>
          <button type="button" :class="['tab-btn', { active: activeTab === 'stations' }]" @click="activeTab = 'stations'">
            🏭 242座换热站日度能耗明细
          </button>
          <button type="button" :class="['tab-btn', { active: activeTab === 'merchants' }]" @click="activeTab = 'merchants'">
            🏬 464户商业用户日耗量
          </button>
        </div>

        <!-- Tab 1: 双轨核对 -->
        <div v-if="activeTab === 'compare'">
          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>服务中心</th>
                  <th>在网面积 (万㎡)</th>
                  <th>系统精算热量 (GJ)</th>
                  <th>手工填报热量 (GJ)</th>
                  <th>热量偏差 (GJ)</th>
                  <th>偏差率</th>
                  <th>万平耗热 (GJ/万㎡)</th>
                  <th>系统补水 (t)</th>
                  <th>手工补水 (t)</th>
                  <th>日均室温 (℃)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="c in reportData.center_comparison" :key="c.center_id" :class="{ 'row-alert': c.is_heat_alert }">
                  <td class="font-bold">{{ c.center_name }}</td>
                  <td>{{ fmt(c.covered_area_wan) }}</td>
                  <td class="font-bold">{{ fmt(c.sys_heat_gj) }}</td>
                  <td>{{ fmt(c.man_heat_gj) }}</td>
                  <td>{{ fmt(c.heat_diff_gj) }}</td>
                  <td>
                    <span v-if="c.heat_diff_pct != null" :class="['diff-pill', c.is_heat_alert ? 'pill-err' : 'pill-ok']">
                      {{ c.heat_diff_pct > 0 ? '+' : '' }}{{ c.heat_diff_pct }}%
                    </span>
                    <span v-else>-</span>
                  </td>
                  <td>{{ fmt(c.heat_per_wan_gj) }}</td>
                  <td>{{ fmt(c.sys_water_t) }}</td>
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
                  <th>换热站</th>
                  <th>服务中心</th>
                  <th>热源大网</th>
                  <th>面积 (㎡)</th>
                  <th>有效小时 / 表底小时</th>
                  <th>起表底 totJ</th>
                  <th>止表底 totJ</th>
                  <th>日供热量 (GJ)</th>
                  <th>万平耗热</th>
                  <th>日补水 (t)</th>
                  <th>日电耗 (kWh)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="s in filteredStationDaily" :key="s.station_id">
                  <td class="font-bold">{{ s.name }}</td>
                  <td>{{ s.center_name }}</td>
                  <td>{{ s.rdfz }}</td>
                  <td>{{ s.covered_area ? s.covered_area.toLocaleString() : '待补' }}</td>
                  <td>{{ s.hours_count }}h / {{ s.meter_diff_hours }}h</td>
                  <td class="mono">{{ fmt(s.start_tot_j) }}</td>
                  <td class="mono">{{ fmt(s.end_tot_j) }}</td>
                  <td class="font-bold">{{ fmt(s.day_heat_gj) }}</td>
                  <td>{{ fmt(s.heat_per_wan_gj) }}</td>
                  <td>{{ fmt(s.day_water_t) }}</td>
                  <td>{{ fmt(s.day_elec_kwh) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Tab 3: 464户商业用户 -->
        <div v-if="activeTab === 'merchants'">
          <div class="filter-bar">
            <input v-model="mcKeyword" type="search" class="ctrl-input" placeholder="筛选商户名称或热源大网…" />
            <button class="btn secondary btn-sm" type="button" :disabled="syncingMerchant" @click="handleSyncMerchants">
              {{ syncingMerchant ? '拉取中…' : '🔄 立即拉取商户日耗量' }}
            </button>
          </div>
          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>商户名称</th>
                  <th>热源大网 (rdfz)</th>
                  <th>介质 (rdry)</th>
                  <th>产权 (rdss)</th>
                  <th>价格分类 (rdjg)</th>
                  <th>改造批次 (rdgz)</th>
                  <th>日累计消耗量</th>
                  <th>日单耗参考</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="m in filteredMerchants" :key="m.merchant_id">
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
import { computed, onMounted, reactive, ref } from 'vue'
import { downloadPlatformExcel, fetchDailyReport, triggerManualCollect } from '../services/api'

function yesterdayIso() {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const selectedDate = ref(yesterdayIso())
const periodMode = ref('natural')
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
  { label: '智慧供热旁路精算与质检平台', to: '/projects/smart_heating_platform/pages' },
  { label: '每日生产精算日报', to: null },
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

function fmt(val, suffix = '') {
  if (val === null || val === undefined || val === '') return '-'
  const num = Number(val)
  if (Number.isNaN(num)) return '-'
  return `${num.toFixed(2).replace(/\.00$/, '')}${suffix}`
}

async function loadReport() {
  try {
    const res = await fetchDailyReport({ date: selectedDate.value, period_mode: periodMode.value })
    if (res?.data) reportData.value = res.data
  } catch (err) {
    notice.type = 'error'
    notice.text = `加载每日精算日报失败：${err.message}`
  }
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
    await downloadPlatformExcel(
      `/reports/daily/export?date=${encodeURIComponent(selectedDate.value)}&period_mode=${periodMode.value}`,
      `每日生产精算日报_${selectedDate.value}.xlsx`,
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
</style>
