<template>
  <div ref="rootEl" :class="['dash-root', `theme-${themeMode}`, { 'is-fullscreen': isFullscreen }]">
    <!-- 背景氛围光晕与微网格 -->
    <div class="ambient-bg" aria-hidden="true">
      <div class="glow glow-warm"></div>
      <div class="glow glow-cool"></div>
      <div class="grid-overlay"></div>
    </div>

    <!-- 顶部指挥控制栏 -->
    <header class="cmd-header glass-panel">
      <div class="cmd-left">
        <div class="brand-badge">
          <span class="pulse-dot"></span>
          <span>实时感知 · 242站 / 464商业户 / 2097室温点</span>
        </div>
        <div class="cmd-title-wrap">
          <h1>主城区智慧供热 · 运行指挥驾驶舱</h1>
          <span class="slot-chip">{{ meta.biz_hour_label || '加载中…' }}</span>
        </div>
      </div>

      <div class="cmd-actions">
        <DateStepPicker v-model="selectedDate" aria-label="选择驾驶舱日期" @change="onDateChange" />
        <div class="hour-ctrl" role="group" aria-label="小时切换">
          <button type="button" class="step-btn" :disabled="!canStepPrev" title="上一小时" @click="stepHour(-1)">◀</button>
          <select v-model.number="selectedHour" class="hour-select" aria-label="选择小时" @change="loadDashboard">
            <option v-if="selectedHour === null" :value="null" disabled>最新…</option>
            <option v-for="h in trend24h" :key="h.hour" :value="h.hour">
              {{ h.label }}{{ h.has_data ? '' : ' (暂无)' }}
            </option>
          </select>
          <button type="button" class="step-btn" :disabled="!canStepNext" title="下一小时" @click="stepHour(1)">▶</button>
          <button type="button" class="step-btn latest-btn" :disabled="loading" @click="jumpToLatest">最新</button>
        </div>

        <button
          type="button"
          class="cmd-btn"
          :title="themeMode === 'dark' ? '切换极昼明亮汇报模式' : '切换深空智控大屏模式'"
          @click="themeMode = themeMode === 'dark' ? 'light' : 'dark'"
        >
          {{ themeMode === 'dark' ? '☀️ 明亮' : '🌙 深空' }}
        </button>
        <button type="button" class="cmd-btn" @click="toggleFullscreen">
          {{ isFullscreen ? '🗗 退出全屏' : '⛶ 全屏投屏' }}
        </button>
        <button type="button" class="cmd-btn accent" @click="goPage('/projects/smart_heating_platform/pages/hourly_report')">
          📊 详表报告
        </button>
        <button type="button" class="cmd-btn" @click="goPage('/projects/smart_heating_platform/pages/daily_report')">
          📑 每日报告
        </button>
        <button type="button" class="cmd-btn" @click="goPage('/projects/smart_heating_platform/pages')">
          ⬅️ 返回
        </button>
      </div>
    </header>

    <main class="dash-main">
      <!-- 运行简报条 -->
      <section class="brief-bar glass-panel">
        <div class="brief-main">
          <span class="brief-tag">运行简报</span>
          <p class="brief-text">{{ brief.headline || '正在同步全网运行实况…' }}</p>
        </div>
        <div v-if="brief.highlights?.length" class="brief-highlights">
          <span v-for="(hl, i) in brief.highlights" :key="i" class="hl-pill">{{ hl }}</span>
        </div>
      </section>

      <div v-if="errorMsg" class="error-strip glass-panel">⚠️ 加载失败：{{ errorMsg }}</div>

      <!-- 6 张核心对比 KPI 卡片（对比标签下移至底部，避免窄卡标题挤压） -->
      <section class="kpi-deck">
        <article class="kpi-card glass-panel tone-cool">
          <div class="kpi-head">
            <span class="kpi-label">近端室外实况气温</span>
          </div>
          <div class="kpi-value tabular">{{ fmt(kpis.outdoor_temp, '℃', 1) }}</div>
          <div class="kpi-foot">
            <span>今日 {{ fmt(meta.outdoor_min_c, '°', 1) }}~{{ fmt(meta.outdoor_max_c, '℃', 1) }}</span>
            <span :class="['delta-badge', deltaClass(comp.outdoor_diff_c, 'neutral')]">
              {{ formatSigned(comp.outdoor_diff_c, '℃', 1, '较昨 ') }}
            </span>
          </div>
        </article>

        <article class="kpi-card glass-panel tone-hero">
          <div class="kpi-head">
            <span class="kpi-label">小时精算总供热量</span>
          </div>
          <div class="kpi-value tabular">{{ fmt(kpis.hour_heat_gj, ' GJ', 1) }}</div>
          <div class="kpi-foot">
            <span>累计 <strong>{{ fmt(meta.today_cum_heat_gj, ' GJ', 0) }}</strong></span>
            <span :class="['delta-badge', deltaClass(comp.heat_diff_pct, 'heat')]">
              {{ formatSigned(comp.heat_diff_pct, '%', 1, '较昨 ') }}
            </span>
          </div>
        </article>

        <article class="kpi-card glass-panel tone-amber">
          <div class="kpi-head">
            <span class="kpi-label">实时折算热指标</span>
          </div>
          <div class="kpi-value tabular">{{ fmt(kpis.heat_index_wm2, ' W/㎡', 1) }}</div>
          <div class="kpi-foot">
            <span>万平 {{ fmt(kpis.heat_per_wan_gj, ' GJ/万㎡') }}</span>
            <span :class="['delta-badge', deltaClass(comp.heat_index_diff_pct, 'heat')]">
              {{ formatSigned(comp.heat_index_diff_pct, '%', 1, '较昨 ') }}
            </span>
          </div>
        </article>

        <article class="kpi-card glass-panel tone-emerald">
          <div class="kpi-row-ring">
            <div class="kpi-ring-text">
              <div class="kpi-head">
                <span class="kpi-label">当前居民平均室温</span>
              </div>
              <div class="kpi-value tabular">{{ fmt(currentTemp.avg_room_temp, '℃', 2) }}</div>
              <div class="kpi-foot">
                <span class="delta-badge badge-live">当前实况 {{ currentTemp.short_label || '' }}</span>
              </div>
            </div>
            <div class="ring-wrap" :title="`当前达标率 (≥18℃): ${fmt(currentTemp.temp_pass_rate_pct, '%', 1)}`">
              <svg viewBox="0 0 64 64" class="ring-svg">
                <circle cx="32" cy="32" r="26" class="ring-track" />
                <circle
                  cx="32"
                  cy="32"
                  r="26"
                  class="ring-fill"
                  :stroke-dasharray="ringCircumference"
                  :stroke-dashoffset="ringOffset"
                />
              </svg>
              <span class="ring-center tabular">{{ currentTemp.temp_pass_rate_pct != null ? `${currentTemp.temp_pass_rate_pct}%` : '-' }}</span>
            </div>
          </div>
        </article>

        <article class="kpi-card glass-panel tone-split">
          <div class="kpi-head">
            <span class="kpi-label">一网加权供 / 回温</span>
          </div>
          <div class="kpi-value tabular split-temps">
            <span class="temp-sup">{{ fmt(kpis.avg_sup_temp, '°', 1) }}</span>
            <span class="temp-sep">/</span>
            <span class="temp-ret">{{ fmt(kpis.avg_ret_temp, '℃', 1) }}</span>
          </div>
          <div class="kpi-foot">
            <span>温差 <strong>{{ fmt(kpis.avg_temp_diff, '℃', 1) }}</strong></span>
            <span class="delta-badge badge-muted">在线 {{ kpis.online_stations ?? 0 }}/{{ kpis.total_stations ?? 242 }}</span>
          </div>
        </article>

        <article :class="['kpi-card glass-panel tone-sky', { 'water-alert': (comp.water_diff_pct ?? 0) > 15 }]">
          <div class="kpi-head">
            <span class="kpi-label">小时补水 / 耗电</span>
          </div>
          <div class="kpi-value tabular split-pair">
            <span class="text-sky">{{ fmt(kpis.hour_water_t, 't', 1) }}</span>
            <span class="temp-sep">/</span>
            <span class="text-amber">{{ fmt(kpis.hour_elec_kwh, 'kWh', 0) }}</span>
          </div>
          <div class="kpi-foot">
            <span>电 {{ fmt(kpis.elec_per_wan_kwh, ' kWh/万㎡') }}</span>
            <span
              :class="[
                'delta-badge',
                deltaClass(
                  comp.elec_diff_pct != null ? comp.elec_diff_pct : comp.water_diff_pct,
                  comp.elec_diff_pct != null ? 'heat' : 'water',
                ),
              ]"
            >
              {{ comp.elec_diff_pct != null ? formatSigned(comp.elec_diff_pct, '%', 1, '电较昨 ') : formatSigned(comp.water_diff_pct, '%', 1, '水较昨 ') }}
            </span>
          </div>
        </article>
      </section>

      <!-- 主视觉分析区：左 7 列 气温与供热趋势（72h连续 / 24h / 7d） + 右 5 列 9中心能效象限 -->
      <section class="stage-grid">
        <article class="stage-card glass-panel span-7">
          <div class="card-head">
            <div>
              <h2>
                {{
                  trendView === '72h'
                    ? '近 72 小时连续气温与供热量协同趋势'
                    : (trendView === '24h' ? '当日 24 小时室外气温与供热量趋势' : '近 7 日气温变化与日供热量走势')
                }}
              </h2>
              <p class="card-sub">
                {{
                  trendView === '72h'
                    ? '连续 72 个整点小时跨天演化（虚线标注每日 00:00 分界，点击柱条可跳转对应日期与时段）'
                    : (trendView === '24h'
                        ? '柱形为今日逐时供热、虚线为昨日同期对照、青色曲线为室外气温（点击可切时段）'
                        : '近 7 天日总供热与日均/最低气温走势（今日未走完时段以虚框区分）')
                }}
              </p>
            </div>
            <div class="seg-switch">
              <button
                type="button"
                :class="['seg-btn', { active: trendView === '72h' }]"
                @click="switchTrendView('72h')"
              >
                近72小时连续
              </button>
              <button
                type="button"
                :class="['seg-btn', { active: trendView === '24h' }]"
                @click="switchTrendView('24h')"
              >
                当日24小时
              </button>
              <button
                type="button"
                :class="['seg-btn', { active: trendView === '7d' }]"
                @click="switchTrendView('7d')"
              >
                近7日逐日
              </button>
            </div>
          </div>

          <div ref="mainTrendEl" :class="['chart-hero', { 'with-scrubber': trendView === '24h' }]"></div>

          <!-- 24h 快速时段刻度条 -->
          <div v-if="trendView === '24h'" class="hour-scrubber" aria-label="24小时快速切换刻度">
            <button
              v-for="item in trend24h"
              :key="item.hour"
              type="button"
              :class="[
                'scrub-dot',
                {
                  active: Number(selectedHour) === Number(item.hour),
                  empty: !item.has_data,
                  anom: Boolean(item.anomalies?.hour_heat_gj),
                },
              ]"
              :title="`${item.label} | 供热 ${fmt(item.hour_heat_gj, ' GJ')} | 气温 ${fmt(item.outdoor_temp, '℃', 1)}`"
              @click="selectHourFromScrubber(item.hour)"
            >
              {{ String(item.hour).padStart(2, '0') }}
            </button>
          </div>
          <div v-else class="chart-foot-note">
            <span v-if="trendView === '72h'">
              连续窗口：<strong>{{ trend72h[0]?.label || '-' }}</strong> 至 <strong>{{ trend72h[trend72h.length - 1]?.label || '-' }}</strong>（支持滚轮缩放或点击任意小时跳转）
            </span>
            <span v-else>
              统计周期：近 7 日（不含历史室温序列；进行中当日为截至当前小时累计）
            </span>
          </div>
        </article>

        <article class="stage-card glass-panel span-5">
          <div class="card-head">
            <div>
              <h2>{{ centerView === 'quadrant' ? '9 大服务中心 · 能效四象限' : '9 大服务中心 · 万平耗热对比' }}</h2>
              <p class="card-sub">
                {{
                  centerView === 'quadrant'
                    ? `横轴为所选时段万平耗热，纵轴取当前最新室温实况 (${currentTemp.short_label || '-'})`
                    : '按所选时段万平耗热量从低到高排序'
                }}
              </p>
            </div>
            <div class="seg-switch">
              <button
                type="button"
                :class="['seg-btn', { active: centerView === 'quadrant' }]"
                @click="switchCenterView('quadrant')"
              >
                能效象限
              </button>
              <button
                type="button"
                :class="['seg-btn', { active: centerView === 'rank' }]"
                @click="switchCenterView('rank')"
              >
                耗热排行
              </button>
            </div>
          </div>

          <div ref="centerChartEl" class="chart-side"></div>

          <div class="quadrant-legend">
            <span class="q-chip q-best">● 节能标杆（低耗达标）</span>
            <span class="q-chip q-over">● 过热可压减（高耗高室温）</span>
            <span class="q-chip q-warn">● 失调预警（高耗低室温）</span>
            <span class="q-chip q-cold">● 偏冷待提温</span>
          </div>
        </article>
      </section>

      <!-- 底部三栏决策洞察区 -->
      <section class="bottom-grid">
        <!-- 卡片 1：9 大主干热网负荷与商业用热结构 -->
        <article class="glass-panel sub-card">
          <div class="card-head compact">
            <div>
              <h3>主干热网负荷分布（9 大网）</h3>
              <p class="card-sub">按当前小时供热量占比排序</p>
            </div>
            <span class="mini-badge">面积 {{ fmt(kpis.covered_area_wan, ' 万㎡', 1) }}</span>
          </div>

          <div class="rdfz-list">
            <div v-for="r in rdfzList" :key="r.group_key" class="rdfz-row">
              <div class="rdfz-meta">
                <span class="rdfz-name">{{ r.group_name }}</span>
                <span class="rdfz-nums tabular">
                  <strong>{{ fmt(r.hour_heat_gj, ' GJ', 1) }}</strong>
                  <em>· {{ fmt(r.heat_per_wan_gj, ' GJ/万㎡', 1) }}</em>
                  <em v-if="r.avg_room_temp != null"> · 室温{{ r.avg_room_temp }}℃</em>
                </span>
              </div>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: `${rdfzPercent(r.hour_heat_gj)}%` }"></div>
              </div>
            </div>
          </div>

          <div class="merchant-share-box">
            <div class="ms-row">
              <span>商业用户小时总耗热（{{ merchantSummary.active_heat_merchants ?? 0 }}/{{ merchantSummary.total_merchants ?? 464 }} 户用热）</span>
              <strong class="tabular">{{ fmt(merchantSummary.total_hour_heat_gj, ' GJ', 1) }}</strong>
            </div>
            <div class="ms-sub">
              <span>占 242 站小时总耗热比例</span>
              <strong class="tabular">{{ merchantSharePct }}</strong>
            </div>
          </div>
        </article>

        <!-- 卡片 2：当前居民室温分布环形舱（仅当前，不显示历史） -->
        <article class="glass-panel sub-card">
          <div class="card-head compact">
            <div>
              <h3>当前居民室温分布（仅现况）</h3>
              <p class="card-sub">当前有效样本 {{ currentTemp.valid_devices ?? 0 }} 户 · 实况 {{ currentTemp.short_label || '-' }}</p>
            </div>
            <span class="mini-badge emerald">达标 {{ fmt(currentTemp.temp_pass_rate_pct, '%', 1) }}</span>
          </div>

          <div ref="roomDonutEl" class="chart-donut"></div>

          <div class="temp-dist-pills">
            <span class="td-pill td-bad">&lt;18℃ 不达标：<strong>{{ tempDist.under_18 ?? 0 }} 户</strong></span>
            <span class="td-pill td-ok">18~20℃ 合格：<strong>{{ tempDist.ok_18_20 ?? 0 }} 户</strong></span>
            <span class="td-pill td-good">20~25℃ 舒适：<strong>{{ tempDist.comfort_20_25 ?? 0 }} 户</strong></span>
            <span class="td-pill td-hot">&gt;25℃ 过热：<strong>{{ tempDist.over_25 ?? 0 }} 户</strong></span>
          </div>

          <div class="room-foot-note">
            舒适区间（20~25℃）占比 <strong>{{ fmt(currentTemp.temp_comfort_rate_pct, '%', 1) }}</strong> · 仅反映当前最新室温分布，不回溯历史曲线
          </div>
        </article>

        <!-- 卡片 3：全网运行焦点榜单 Top 5（过滤故障与异常站，不展示室温） -->
        <article class="glass-panel sub-card">
          <div class="card-head compact">
            <div>
              <h3>全网运行焦点榜单 Top 5</h3>
              <p class="card-sub">已过滤零能耗/异常故障站点，点击可下钻当日 24h 运行曲线</p>
            </div>
          </div>

          <div class="seg-switch full">
            <button
              v-for="tab in watchTabs"
              :key="tab.key"
              type="button"
              :class="['seg-btn', { active: activeWatchTab === tab.key }]"
              @click="activeWatchTab = tab.key"
            >
              {{ tab.label }}
            </button>
          </div>

          <div class="watch-list">
            <div v-if="activeWatchItems.length === 0" class="watch-empty">当前时段暂无正常在运站点记录</div>
            <button
              v-for="(item, idx) in activeWatchItems"
              :key="item.station_id"
              type="button"
              class="watch-item"
              @click="handleWatchClick(item)"
            >
              <span :class="['rank-idx', `rank-${idx + 1}`]">{{ idx + 1 }}</span>
              <div class="watch-info">
                <strong>{{ item.name }}</strong>
                <span>{{ item.center_name }}</span>
              </div>
              <div class="watch-metric tabular">
                <template v-if="activeWatchTab === 'high_water'">
                  <strong class="text-sky">{{ fmt(item.hour_water_t, ' t/h', 2) }}</strong>
                  <span>{{ fmt(item.hour_heat_gj, ' GJ', 1) }} · {{ item.covered_area ? `${(item.covered_area / 10000).toFixed(1)}万㎡` : '-' }}</span>
                </template>
                <template v-else-if="activeWatchTab === 'high_elec'">
                  <strong class="text-amber">{{ fmt(item.hour_elec_kwh, ' kWh', 1) }}</strong>
                  <span>万平 {{ fmt(item.elec_per_wan_kwh, ' kWh', 2) }} · {{ item.covered_area ? `${(item.covered_area / 10000).toFixed(1)}万㎡` : '-' }}</span>
                </template>
                <template v-else-if="activeWatchTab === 'benchmark'">
                  <strong class="text-emerald">{{ fmt(item.heat_index_wm2, ' W/㎡', 1) }}</strong>
                  <span>{{ fmt(item.hour_heat_gj, ' GJ', 1) }} · {{ item.covered_area ? `${(item.covered_area / 10000).toFixed(1)}万㎡` : '-' }}</span>
                </template>
                <template v-else>
                  <strong class="text-amber">{{ fmt(item.heat_index_wm2, ' W/㎡', 1) }}</strong>
                  <span>{{ fmt(item.hour_heat_gj, ' GJ', 1) }} · {{ item.covered_area ? `${(item.covered_area / 10000).toFixed(1)}万㎡` : '-' }}</span>
                </template>
              </div>
            </button>
          </div>
        </article>
      </section>
    </main>

    <!-- 站点下钻抽屉（单站当日 24h 负荷曲线） -->
    <div v-if="drawer.open" class="drawer-backdrop" @click.self="drawer.open = false">
      <div class="drawer-panel glass-panel">
        <div class="drawer-head">
          <h3>{{ drawer.title }}</h3>
          <button type="button" class="cmd-btn" @click="drawer.open = false">✕ 关闭</button>
        </div>
        <div v-if="drawer.loading" class="watch-empty">正在加载下钻数据…</div>
        <template v-else-if="drawer.kind === 'station_trend'">
          <div ref="drawerChartEl" class="drawer-chart"></div>
          <div class="drawer-table-wrap">
            <table class="mini-table">
              <thead>
                <tr>
                  <th>小时</th>
                  <th>供热量 (GJ)</th>
                  <th>热指标 (W/㎡)</th>
                  <th>电耗 (kWh)</th>
                  <th>一网供温 (℃)</th>
                  <th>一网回温 (℃)</th>
                  <th>室外温 (℃)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="pt in drawer.rows" :key="pt.hour">
                  <td class="tabular">{{ pt.label }}</td>
                  <td class="tabular">{{ fmt(pt.hour_heat_gj) }}</td>
                  <td class="tabular">{{ fmt(pt.heat_index_wm2) }}</td>
                  <td class="tabular">{{ fmt(pt.hour_elec_kwh) }}</td>
                  <td class="tabular">{{ fmt(pt.avg_sup_temp) }}</td>
                  <td class="tabular">{{ fmt(pt.avg_ret_temp) }}</td>
                  <td class="tabular">{{ fmt(pt.outdoor_temp, '', 1) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import DateStepPicker from '../components/DateStepPicker.vue'
import { MIN_PLATFORM_DATE, shiftIsoDate, todayLocalIso } from '../utils/dateUtils'
import { fetchDashboardOverview, fetchEntityTrend24h } from '../services/api'

const router = useRouter()
const rootEl = ref(null)
const themeMode = ref('dark')
const isFullscreen = ref(false)

const selectedDate = ref('')
const selectedHour = ref(null)
const loading = ref(false)
const errorMsg = ref('')

const trendView = ref('72h')
const centerView = ref('quadrant')
const activeWatchTab = ref('high_heat')

const dashData = ref({
  meta: {},
  brief: {},
  kpis: {},
  comparison: {},
  current_temp: {},
  trend_72h: [],
  trend_24h: Array.from({ length: 24 }, (_, h) => ({ hour: h, label: `${String(h).padStart(2, '0')}:00`, has_data: false })),
  trend_7d: [],
  center_quadrant: [],
  rdfz_ranking: [],
  merchant_summary: {},
  temp_summary: { distribution: {}, station_rankings: [] },
  watchlists: { high_heat: [], high_water: [], high_elec: [], benchmark: [] },
})

const mainTrendEl = ref(null)
const centerChartEl = ref(null)
const roomDonutEl = ref(null)
const drawerChartEl = ref(null)
let mainTrendChart = null
let centerChart = null
let roomDonutChart = null
let drawerChart = null
let resizeObserver = null

const drawer = reactive({
  open: false,
  kind: '',
  title: '',
  loading: false,
  rows: [],
})

const watchTabs = [
  { key: 'high_heat', label: '🔥 高热指标' },
  { key: 'high_water', label: '💧 高补水' },
  { key: 'high_elec', label: '⚡ 高电耗' },
  { key: 'benchmark', label: '🏆 节能低耗' },
]

const meta = computed(() => dashData.value.meta || {})
const brief = computed(() => dashData.value.brief || {})
const kpis = computed(() => dashData.value.kpis || {})
const comp = computed(() => dashData.value.comparison || {})
const currentTemp = computed(() => dashData.value.current_temp || {})
const trend72h = computed(() => dashData.value.trend_72h || [])
const trend24h = computed(() => dashData.value.trend_24h || [])
const trend7d = computed(() => dashData.value.trend_7d || [])
const centerList = computed(() => dashData.value.center_quadrant || [])
const rdfzList = computed(() => dashData.value.rdfz_ranking || [])
const merchantSummary = computed(() => dashData.value.merchant_summary || {})
const tempDist = computed(() => currentTemp.value.distribution || {})

const activeWatchItems = computed(() => (dashData.value.watchlists || {})[activeWatchTab.value] || [])

const ringCircumference = 2 * Math.PI * 26
const ringOffset = computed(() => {
  const pct = Math.max(0, Math.min(100, Number(currentTemp.value.temp_pass_rate_pct ?? 0)))
  return ringCircumference * (1 - pct / 100)
})

const maxRdfzHeat = computed(() => Math.max(1, ...rdfzList.value.map((r) => Number(r.hour_heat_gj || 0))))
function rdfzPercent(val) {
  return Math.min(100, Math.round((Number(val || 0) / maxRdfzHeat.value) * 100))
}

const merchantSharePct = computed(() => {
  const tot = Number(kpis.value.hour_heat_gj || 0)
  const mc = Number(merchantSummary.value.total_hour_heat_gj || 0)
  if (!tot || !mc) return '-'
  return `${((mc / tot) * 100).toFixed(1)}%`
})

function fmt(val, suffix = '', fixed = 2) {
  if (val === null || val === undefined || val === '') return '-'
  const num = Number(val)
  if (Number.isNaN(num)) return '-'
  return `${num.toFixed(fixed).replace(/\.00$/, '')}${suffix}`
}

function formatSigned(val, suffix = '', fixed = 1, prefix = '') {
  if (val === null || val === undefined || Number.isNaN(Number(val))) return '暂无对比'
  const num = Number(val)
  const sign = num > 0 ? '+' : ''
  return `${prefix}${sign}${num.toFixed(fixed)}${suffix}`
}

function deltaClass(val, kind) {
  if (val === null || val === undefined) return 'badge-muted'
  const n = Number(val)
  if (kind === 'water') return n > 15 ? 'badge-danger' : n > 5 ? 'badge-warn' : 'badge-ok'
  if (kind === 'heat') return n > 10 ? 'badge-warn' : n < -10 ? 'badge-cool' : 'badge-muted'
  return 'badge-muted'
}

function goPage(path) {
  router.push(path)
}

function toggleFullscreen() {
  if (typeof document === 'undefined') return
  if (document.fullscreenElement) {
    document.exitFullscreen?.().catch(() => {
      isFullscreen.value = false
      nextTick(() => onResize())
    })
    return
  }
  if (isFullscreen.value) {
    isFullscreen.value = false
    nextTick(() => onResize())
    return
  }
  const req = rootEl.value?.requestFullscreen?.()
  if (req && typeof req.catch === 'function') {
    req.catch(() => {
      // 若浏览器受限禁用原生全屏，降级为铺满视口的固定全屏投屏模式
      isFullscreen.value = true
      nextTick(() => {
        onResize()
        setTimeout(onResize, 120)
      })
    })
  } else {
    isFullscreen.value = true
    nextTick(() => {
      onResize()
      setTimeout(onResize, 120)
    })
  }
}

function onFullscreenChange() {
  isFullscreen.value = Boolean(document.fullscreenElement)
  nextTick(() => {
    onResize()
    setTimeout(onResize, 120)
  })
}

function onKeydown(e) {
  if (e.key === 'Escape' && isFullscreen.value && !document.fullscreenElement) {
    isFullscreen.value = false
    nextTick(() => onResize())
  }
}

let reqSeq = 0
let abortCtrl = null
let debounceTimer = null

function scheduleLoad(delayMs = 160) {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    debounceTimer = null
    loadDashboard()
  }, delayMs)
}

async function loadDashboard() {
  if (debounceTimer) {
    clearTimeout(debounceTimer)
    debounceTimer = null
  }
  const id = ++reqSeq
  if (abortCtrl) abortCtrl.abort()
  abortCtrl = typeof AbortController !== 'undefined' ? new AbortController() : null
  const reqDate = selectedDate.value || ''
  const reqHour = selectedHour.value
  loading.value = true
  errorMsg.value = ''
  try {
    const params = { mode: 'clean' }
    if (reqDate) params.date = reqDate
    if (reqHour !== null && reqHour !== undefined) params.hour = reqHour
    const res = await fetchDashboardOverview(params, abortCtrl ? { signal: abortCtrl.signal } : {})
    if (id !== reqSeq) return
    if (res?.data) {
      dashData.value = res.data
      if (res.data.meta?.date && (!reqDate || reqDate === selectedDate.value)) {
        selectedDate.value = res.data.meta.date
      }
      if (
        res.data.meta?.hour !== undefined &&
        res.data.meta?.hour !== null &&
        (reqHour === null || reqHour === undefined || Number(reqHour) === Number(selectedHour.value))
      ) {
        selectedHour.value = Number(res.data.meta.hour)
      }
      await nextTick()
      if (id === reqSeq) {
        const hasRoom = centerList.value.some((c) => c.heat_per_wan_gj != null && c.avg_room_temp != null)
        if (!hasRoom && centerView.value === 'quadrant') {
          centerView.value = 'rank'
        }
        const wl = res.data.watchlists || {}
        if (!(wl[activeWatchTab.value] || []).length) {
          activeWatchTab.value = (wl.high_heat || []).length ? 'high_heat' : ((wl.high_water || []).length ? 'high_water' : 'benchmark')
        }
        renderAllCharts()
      }
    }
  } catch (err) {
    if (err?.name === 'AbortError' || id !== reqSeq) return
    errorMsg.value = err.message || '请求异常'
  } finally {
    if (id === reqSeq) loading.value = false
  }
}

function onDateChange() {
  selectedHour.value = null
  scheduleLoad(160)
}

function jumpToLatest() {
  selectedDate.value = ''
  selectedHour.value = null
  loadDashboard()
}

const canStepPrev = computed(() => {
  if (selectedHour.value === null || selectedHour.value === undefined) return false
  if (Number(selectedHour.value) > 0) return true
  return (selectedDate.value || todayLocalIso()) > MIN_PLATFORM_DATE
})

const canStepNext = computed(() => {
  if (selectedHour.value === null || selectedHour.value === undefined) return false
  if (Number(selectedHour.value) < 23) return true
  return (selectedDate.value || todayLocalIso()) < todayLocalIso()
})

function stepHour(delta) {
  if (selectedHour.value === null || selectedHour.value === undefined) return
  const curH = Number(selectedHour.value)
  const curD = selectedDate.value || todayLocalIso()
  const maxD = todayLocalIso()
  if (delta < 0) {
    if (curH > 0) {
      selectedHour.value = curH - 1
      scheduleLoad(140)
    } else {
      const prev = shiftIsoDate(curD, -1)
      if (prev >= MIN_PLATFORM_DATE) {
        selectedDate.value = prev
        selectedHour.value = 23
        scheduleLoad(140)
      }
    }
  } else if (delta > 0) {
    if (curH < 23) {
      selectedHour.value = curH + 1
      scheduleLoad(140)
    } else if (curD < maxD) {
      const nxt = shiftIsoDate(curD, 1)
      if (nxt <= maxD) {
        selectedDate.value = nxt
        selectedHour.value = 0
        scheduleLoad(140)
      }
    }
  }
}

function selectHourFromScrubber(h) {
  if (Number(selectedHour.value) === Number(h)) return
  selectedHour.value = Number(h)
  scheduleLoad(60)
}

function switchTrendView(v) {
  trendView.value = v
  nextTick(() => renderMainTrendChart())
}

function switchCenterView(v) {
  centerView.value = v
  nextTick(() => renderCenterChart())
}

function palette() {
  const isDark = themeMode.value === 'dark'
  return {
    text: isDark ? '#cbd5e1' : '#334155',
    subText: isDark ? '#94a3b8' : '#64748b',
    gridLine: isDark ? 'rgba(148, 163, 184, 0.12)' : 'rgba(15, 23, 42, 0.08)',
    tooltipBg: isDark ? 'rgba(15, 23, 42, 0.94)' : 'rgba(255, 255, 255, 0.96)',
    tooltipBorder: isDark ? 'rgba(56, 189, 248, 0.35)' : '#cbd5e1',
    tooltipText: isDark ? '#f1f5f9' : '#0f172a',
  }
}

function renderMainTrendChart() {
  if (!mainTrendEl.value) return
  if (!mainTrendChart) {
    mainTrendChart = echarts.init(mainTrendEl.value)
    mainTrendChart.getZr().on('click', (event) => {
      const pt = [event.offsetX, event.offsetY]
      if (!mainTrendChart.containPixel('grid', pt)) return
      const g = mainTrendChart.convertFromPixel({ seriesIndex: 0 }, pt)
      if (!Array.isArray(g) || Number.isNaN(g[0])) return
      const idx = Math.round(g[0])
      if (trendView.value === '24h') {
        const row = trend24h.value[idx]
        if (row && row.hour !== undefined) selectHourFromScrubber(row.hour)
      } else if (trendView.value === '72h') {
        const row = trend72h.value[idx]
        if (row && row.date && row.hour !== undefined) {
          if (selectedDate.value !== row.date || Number(selectedHour.value) !== Number(row.hour)) {
            selectedDate.value = row.date
            selectedHour.value = Number(row.hour)
            scheduleLoad(60)
          }
        }
      }
    })
  }
  const p = palette()
  const isDark = themeMode.value === 'dark'

  if (trendView.value === '72h') {
    const rows = trend72h.value
    const curDate = selectedDate.value || meta.value.date
    const curHour = selectedHour.value ?? meta.value.hour
    const midnightMarks = rows
      .filter((r) => r.is_day_start)
      .map((r) => ({
        xAxis: r.label,
        label: { formatter: r.date.slice(5), color: '#38bdf8', fontSize: 10 },
      }))

    mainTrendChart.setOption({
      tooltip: {
        trigger: 'axis',
        backgroundColor: p.tooltipBg,
        borderColor: p.tooltipBorder,
        textStyle: { color: p.tooltipText, fontSize: 12 },
      },
      legend: {
        top: 0,
        right: 4,
        textStyle: { color: p.subText, fontSize: 12 },
        data: ['小时供热量(GJ)', '室外气温(℃)', '热指标(W/㎡)'],
      },
      dataZoom: [{ type: 'inside', xAxisIndex: 0 }],
      grid: { left: 48, right: 48, top: 38, bottom: 32 },
      xAxis: {
        type: 'category',
        data: rows.map((r) => r.label),
        axisLine: { lineStyle: { color: p.gridLine } },
        axisLabel: {
          color: p.subText,
          fontSize: 10,
          interval: 5,
          formatter: (val) => String(val).slice(0, 8),
        },
      },
      yAxis: [
        {
          type: 'value',
          name: 'GJ / W/㎡',
          nameTextStyle: { color: p.subText, fontSize: 11 },
          axisLabel: { color: p.subText, fontSize: 11 },
          splitLine: { lineStyle: { color: p.gridLine } },
        },
        {
          type: 'value',
          name: '℃',
          nameTextStyle: { color: '#22d3ee', fontSize: 11 },
          axisLabel: { color: '#22d3ee', fontSize: 11 },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '小时供热量(GJ)',
          type: 'bar',
          barMaxWidth: 10,
          data: rows.map((r) => {
            const isSel = r.date === curDate && Number(r.hour) === Number(curHour)
            return {
              value: r.hour_heat_gj,
              itemStyle: {
                borderRadius: [3, 3, 0, 0],
                borderColor: isSel ? '#fbbf24' : 'transparent',
                borderWidth: isSel ? 1.5 : 0,
                color: isSel
                  ? '#fbbf24'
                  : new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                      { offset: 0, color: '#fb923c' },
                      { offset: 1, color: isDark ? 'rgba(234, 88, 12, 0.25)' : 'rgba(251, 146, 60, 0.32)' },
                    ]),
              },
            }
          }),
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: { type: 'dashed', color: 'rgba(56, 189, 248, 0.4)', width: 1 },
            data: midnightMarks,
          },
        },
        {
          name: '室外气温(℃)',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 2.5, color: '#22d3ee', shadowColor: 'rgba(34, 211, 238, 0.45)', shadowBlur: 8 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(34, 211, 238, 0.24)' },
              { offset: 1, color: 'rgba(34, 211, 238, 0.01)' },
            ]),
          },
          markPoint: {
            symbolSize: 34,
            label: { fontSize: 10, color: '#0f172a', fontWeight: 700 },
            itemStyle: { color: '#67e8f9' },
            data: [
              { type: 'max', name: '最高' },
              { type: 'min', name: '最低' },
            ],
          },
          data: rows.map((r) => r.outdoor_temp),
        },
        {
          name: '热指标(W/㎡)',
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 1.6, color: '#f59e0b' },
          data: rows.map((r) => r.heat_index_wm2),
        },
      ],
    }, true)
  } else if (trendView.value === '24h') {
    const rows = trend24h.value
    const activeLbl = selectedHour.value != null ? `${String(selectedHour.value).padStart(2, '0')}:00` : null
    mainTrendChart.setOption({
      tooltip: {
        trigger: 'axis',
        backgroundColor: p.tooltipBg,
        borderColor: p.tooltipBorder,
        textStyle: { color: p.tooltipText, fontSize: 12 },
      },
      legend: {
        top: 0,
        right: 4,
        textStyle: { color: p.subText, fontSize: 12 },
        data: ['今日供热量(GJ)', '昨日同期(GJ)', '室外气温(℃)', '热指标(W/㎡)'],
      },
      grid: { left: 48, right: 48, top: 38, bottom: 26 },
      xAxis: {
        type: 'category',
        data: rows.map((r) => r.label),
        axisLine: { lineStyle: { color: p.gridLine } },
        axisLabel: {
          color: (val) => (val === activeLbl ? '#38bdf8' : p.subText),
          fontWeight: (val) => (val === activeLbl ? 700 : 400),
          fontSize: 11,
        },
      },
      yAxis: [
        {
          type: 'value',
          name: 'GJ / W/㎡',
          nameTextStyle: { color: p.subText, fontSize: 11 },
          axisLabel: { color: p.subText, fontSize: 11 },
          splitLine: { lineStyle: { color: p.gridLine } },
        },
        {
          type: 'value',
          name: '℃',
          nameTextStyle: { color: '#38bdf8', fontSize: 11 },
          axisLabel: { color: '#38bdf8', fontSize: 11 },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '今日供热量(GJ)',
          type: 'bar',
          barMaxWidth: 20,
          data: rows.map((r) => {
            const isSel = r.label === activeLbl
            return {
              value: r.hour_heat_gj,
              itemStyle: {
                borderRadius: [5, 5, 0, 0],
                borderColor: isSel ? '#fbbf24' : 'transparent',
                borderWidth: isSel ? 2 : 0,
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, isSel
                  ? [{ offset: 0, color: '#fbbf24' }, { offset: 1, color: '#ea580c' }]
                  : [{ offset: 0, color: '#fb923c' }, { offset: 1, color: isDark ? 'rgba(234, 88, 12, 0.28)' : 'rgba(251, 146, 60, 0.35)' }]
                ),
              },
            }
          }),
        },
        {
          name: '昨日同期(GJ)',
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 1.8, type: 'dashed', color: isDark ? 'rgba(148, 163, 184, 0.72)' : '#94a3b8' },
          data: rows.map((r) => r.prev_hour_heat_gj),
        },
        {
          name: '室外气温(℃)',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          symbolSize: 6,
          itemStyle: { color: '#22d3ee' },
          lineStyle: { width: 2.6, color: '#22d3ee', shadowColor: 'rgba(34, 211, 238, 0.45)', shadowBlur: 8 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(34, 211, 238, 0.24)' },
              { offset: 1, color: 'rgba(34, 211, 238, 0.01)' },
            ]),
          },
          markPoint: {
            symbolSize: 34,
            label: { fontSize: 10, color: '#0f172a', fontWeight: 700 },
            itemStyle: { color: '#67e8f9' },
            data: [
              { type: 'max', name: '最高' },
              { type: 'min', name: '最低' },
            ],
          },
          data: rows.map((r) => r.outdoor_temp),
        },
        {
          name: '热指标(W/㎡)',
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 1.8, color: '#f59e0b' },
          data: rows.map((r) => r.heat_index_wm2),
        },
      ],
    }, true)
  } else {
    const rows = trend7d.value
    mainTrendChart.setOption({
      tooltip: {
        trigger: 'axis',
        backgroundColor: p.tooltipBg,
        borderColor: p.tooltipBorder,
        textStyle: { color: p.tooltipText, fontSize: 12 },
      },
      legend: {
        top: 0,
        right: 4,
        textStyle: { color: p.subText, fontSize: 12 },
        data: ['日供热量(GJ)', '日均气温(℃)', '日最低温(℃)'],
      },
      grid: { left: 56, right: 48, top: 38, bottom: 26 },
      xAxis: {
        type: 'category',
        data: rows.map((r) => (r.is_partial ? `${r.label}(${r.hours_count}h)` : r.label)),
        axisLine: { lineStyle: { color: p.gridLine } },
        axisLabel: { color: p.subText, fontSize: 11 },
      },
      yAxis: [
        {
          type: 'value',
          name: '日供热 (GJ)',
          nameTextStyle: { color: p.subText, fontSize: 11 },
          axisLabel: { color: p.subText, fontSize: 11 },
          splitLine: { lineStyle: { color: p.gridLine } },
        },
        {
          type: 'value',
          name: '℃',
          nameTextStyle: { color: '#22d3ee', fontSize: 11 },
          axisLabel: { color: '#22d3ee', fontSize: 11 },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '日供热量(GJ)',
          type: 'bar',
          barMaxWidth: 30,
          data: rows.map((r) => ({
            value: r.day_heat_gj,
            itemStyle: {
              borderRadius: [6, 6, 0, 0],
              borderColor: r.is_partial ? '#fb923c' : 'transparent',
              borderWidth: r.is_partial ? 1.5 : 0,
              borderType: r.is_partial ? 'dashed' : 'solid',
              opacity: r.is_partial ? 0.65 : 1,
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#fb923c' },
                { offset: 1, color: 'rgba(234, 88, 12, 0.30)' },
              ]),
            },
          })),
        },
        {
          name: '日均气温(℃)',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          itemStyle: { color: '#22d3ee' },
          lineStyle: { width: 2.6, color: '#22d3ee' },
          data: rows.map((r) => r.avg_outdoor_temp),
        },
        {
          name: '日最低温(℃)',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          lineStyle: { width: 1.6, type: 'dashed', color: '#60a5fa' },
          data: rows.map((r) => r.min_outdoor_temp),
        },
      ],
    }, true)
  }
  mainTrendChart.resize()
}

function renderCenterChart() {
  if (!centerChartEl.value) return
  if (!centerChart) centerChart = echarts.init(centerChartEl.value)
  const p = palette()
  const list = centerList.value

  if (centerView.value === 'quadrant') {
    const valid = list.filter((c) => c.heat_per_wan_gj != null && c.avg_room_temp != null)
    const avgHeatPerWan = Number(kpis.value.heat_per_wan_gj || 0) || (
      valid.length ? valid.reduce((s, c) => s + Number(c.heat_per_wan_gj), 0) / valid.length : 1.0
    )
    const targetRoom = 20.0
    centerChart.setOption({
      tooltip: {
        trigger: 'item',
        backgroundColor: p.tooltipBg,
        borderColor: p.tooltipBorder,
        textStyle: { color: p.tooltipText, fontSize: 12 },
        formatter: (param) => {
          const d = param.data?.meta
          if (!d) return ''
          return `
            <div style="font-weight:700;margin-bottom:4px;">${d.group_name}</div>
            <div>万平耗热：<b>${fmt(d.heat_per_wan_gj, ' GJ/万㎡·h')}</b></div>
            <div>当前室温：<b>${fmt(d.avg_room_temp, '℃')}</b>（达标 ${fmt(d.temp_pass_rate_pct, '%', 1)}）</div>
            <div>在网面积：${fmt(d.covered_area_wan, ' 万㎡', 1)} · 在线 ${d.online_stations}/${d.total_stations} 站</div>
          `
        },
      },
      grid: { left: 44, right: 20, top: 24, bottom: 36 },
      xAxis: {
        type: 'value',
        name: '万平耗热 (GJ/万㎡·h)',
        nameLocation: 'middle',
        nameGap: 22,
        nameTextStyle: { color: p.subText, fontSize: 11 },
        axisLabel: { color: p.subText, fontSize: 11 },
        splitLine: { lineStyle: { color: p.gridLine } },
        scale: true,
      },
      yAxis: {
        type: 'value',
        name: '室温 (℃)',
        nameTextStyle: { color: p.subText, fontSize: 11 },
        axisLabel: { color: p.subText, fontSize: 11 },
        splitLine: { lineStyle: { color: p.gridLine } },
        scale: true,
      },
      series: [
        {
          type: 'scatter',
          data: valid.map((c) => {
            const h = Number(c.heat_per_wan_gj)
            const t = Number(c.avg_room_temp)
            let color = '#38bdf8'
            if (h <= avgHeatPerWan && t >= targetRoom) color = '#34d399'
            else if (h > avgHeatPerWan && t >= targetRoom) color = '#fbbf24'
            else if (h > avgHeatPerWan && t < targetRoom) color = '#f87171'
            const size = Math.max(18, Math.min(46, Math.sqrt(Number(c.covered_area_wan || 100)) * 2.1))
            return {
              name: c.group_name,
              value: [h, t],
              symbolSize: size,
              meta: c,
              itemStyle: {
                color,
                opacity: 0.86,
                borderColor: '#ffffff',
                borderWidth: 1.4,
                shadowBlur: 10,
                shadowColor: color,
              },
            }
          }),
          label: {
            show: true,
            position: 'top',
            formatter: (pr) => String(pr.data?.name || '').replace('服务中心', ''),
            color: p.text,
            fontSize: 11,
          },
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: { type: 'dashed', color: 'rgba(148, 163, 184, 0.55)', width: 1.2 },
            label: { color: p.subText, fontSize: 10 },
            data: [
              { xAxis: avgHeatPerWan, label: { formatter: `均耗 ${avgHeatPerWan.toFixed(2)}` } },
              { yAxis: targetRoom, label: { formatter: '20℃ 舒适线' } },
            ],
          },
        },
      ],
    }, true)
  } else {
    const sorted = [...list].sort((a, b) => Number(a.heat_per_wan_gj || 0) - Number(b.heat_per_wan_gj || 0))
    centerChart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: p.tooltipBg,
        borderColor: p.tooltipBorder,
        textStyle: { color: p.tooltipText, fontSize: 12 },
      },
      grid: { left: 84, right: 44, top: 14, bottom: 24 },
      xAxis: {
        type: 'value',
        axisLabel: { color: p.subText, fontSize: 11 },
        splitLine: { lineStyle: { color: p.gridLine } },
      },
      yAxis: {
        type: 'category',
        data: sorted.map((c) => String(c.group_name || '').replace('服务中心', '')),
        axisLabel: { color: p.text, fontSize: 11 },
        axisLine: { lineStyle: { color: p.gridLine } },
      },
      series: [
        {
          name: '万平耗热(GJ/万㎡·h)',
          type: 'bar',
          barMaxWidth: 18,
          itemStyle: {
            borderRadius: [0, 5, 5, 0],
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#0284c7' },
              { offset: 1, color: '#38bdf8' },
            ]),
          },
          label: { show: true, position: 'right', color: p.text, fontSize: 11 },
          data: sorted.map((c) => c.heat_per_wan_gj),
        },
      ],
    }, true)
  }
  centerChart.resize()
}

function renderRoomDonut() {
  if (!roomDonutEl.value) return
  if (!roomDonutChart) roomDonutChart = echarts.init(roomDonutEl.value)
  const p = palette()
  const d = tempDist.value
  const passPct = currentTemp.value.temp_pass_rate_pct
  roomDonutChart.setOption({
    tooltip: {
      trigger: 'item',
      backgroundColor: p.tooltipBg,
      borderColor: p.tooltipBorder,
      textStyle: { color: p.tooltipText, fontSize: 12 },
      formatter: '{b}: {c} 户 ({d}%)',
    },
    title: {
      text: passPct != null ? `${passPct}%` : '-',
      subtext: '当前达标率',
      left: 'center',
      top: '38%',
      textStyle: { color: themeMode.value === 'dark' ? '#f8fafc' : '#0f172a', fontSize: 22, fontWeight: 700 },
      subtextStyle: { color: p.subText, fontSize: 11 },
    },
    series: [
      {
        type: 'pie',
        radius: ['54%', '78%'],
        center: ['50%', '50%'],
        itemStyle: { borderRadius: 6, borderColor: themeMode.value === 'dark' ? '#0b1426' : '#fff', borderWidth: 2 },
        label: { show: false },
        data: [
          { value: d.under_18 || 0, name: '<18℃ 不达标', itemStyle: { color: '#ef4444' } },
          { value: d.ok_18_20 || 0, name: '18~20℃ 合格', itemStyle: { color: '#f59e0b' } },
          { value: d.comfort_20_25 || 0, name: '20~25℃ 舒适', itemStyle: { color: '#10b981' } },
          { value: d.over_25 || 0, name: '>25℃ 过热', itemStyle: { color: '#38bdf8' } },
        ],
      },
    ],
  }, true)
  roomDonutChart.resize()
}

function renderAllCharts() {
  renderMainTrendChart()
  renderCenterChart()
  renderRoomDonut()
}

async function handleWatchClick(item) {
  drawer.open = true
  drawer.loading = true
  drawer.rows = []
  drawer.kind = 'station_trend'
  drawer.title = `${item.name}（${item.center_name}）— 当日 24 小时运行曲线`
  try {
    const res = await fetchEntityTrend24h({
      date: selectedDate.value || meta.value.date,
      scope: 'station',
      key: item.station_id,
      mode: 'clean',
    })
    drawer.rows = res?.data?.trend_24h || []
    drawer.loading = false
    await nextTick()
    renderDrawerChart(drawer.rows)
  } catch {
    drawer.loading = false
  }
}

function renderDrawerChart(rows) {
  if (!drawerChartEl.value) return
  if (!drawerChart) drawerChart = echarts.init(drawerChartEl.value)
  const p = palette()
  drawerChart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: p.tooltipBg, borderColor: p.tooltipBorder, textStyle: { color: p.tooltipText, fontSize: 12 } },
    legend: { top: 0, textStyle: { color: p.subText, fontSize: 11 }, data: ['供热量(GJ)', '一网供温(℃)', '一网回温(℃)'] },
    grid: { left: 42, right: 42, top: 34, bottom: 24 },
    xAxis: { type: 'category', data: rows.map((r) => r.label), axisLabel: { color: p.subText, fontSize: 11 } },
    yAxis: [
      { type: 'value', name: 'GJ', axisLabel: { color: p.subText, fontSize: 11 }, splitLine: { lineStyle: { color: p.gridLine } } },
      { type: 'value', name: '℃', axisLabel: { color: p.subText, fontSize: 11 }, splitLine: { show: false } },
    ],
    series: [
      { name: '供热量(GJ)', type: 'bar', itemStyle: { color: '#fb923c', borderRadius: [4, 4, 0, 0] }, data: rows.map((r) => r.hour_heat_gj) },
      { name: '一网供温(℃)', type: 'line', yAxisIndex: 1, smooth: true, itemStyle: { color: '#ef4444' }, data: rows.map((r) => r.avg_sup_temp) },
      { name: '一网回温(℃)', type: 'line', yAxisIndex: 1, smooth: true, itemStyle: { color: '#38bdf8' }, data: rows.map((r) => r.avg_ret_temp) },
    ],
  }, true)
  drawerChart.resize()
}

function onResize() {
  mainTrendChart?.resize()
  centerChart?.resize()
  roomDonutChart?.resize()
  drawerChart?.resize()
}

watch(themeMode, async () => {
  await nextTick()
  renderAllCharts()
  if (drawer.open && drawer.kind === 'station_trend' && drawer.rows.length) {
    renderDrawerChart(drawer.rows)
  }
})

onMounted(() => {
  window.addEventListener('resize', onResize)
  document.addEventListener('fullscreenchange', onFullscreenChange)
  window.addEventListener('keydown', onKeydown)
  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => onResize())
    if (mainTrendEl.value) resizeObserver.observe(mainTrendEl.value)
    if (centerChartEl.value) resizeObserver.observe(centerChartEl.value)
    if (roomDonutEl.value) resizeObserver.observe(roomDonutEl.value)
  }
  loadDashboard()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  window.removeEventListener('keydown', onKeydown)
  resizeObserver?.disconnect()
  if (debounceTimer) clearTimeout(debounceTimer)
  abortCtrl?.abort()
  mainTrendChart?.dispose()
  centerChart?.dispose()
  roomDonutChart?.dispose()
  drawerChart?.dispose()
})
</script>

<style scoped>
.dash-root {
  --bg-base: #060b16;
  --bg-card: rgba(15, 23, 42, 0.74);
  --border-card: rgba(148, 163, 184, 0.16);
  --text-main: #f1f5f9;
  --text-sub: #94a3b8;
  --bg-chip: rgba(30, 41, 59, 0.85);
  --bg-input: rgba(15, 23, 42, 0.92);
  --border-input: rgba(148, 163, 184, 0.28);
  min-height: 100vh;
  position: relative;
  overflow-x: clip;
  background: var(--bg-base);
  color: var(--text-main);
  padding: 14px 18px 34px;
  box-sizing: border-box;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}

.dash-root.theme-light {
  --bg-base: #f1f5f9;
  --bg-card: rgba(255, 255, 255, 0.88);
  --border-card: rgba(148, 163, 184, 0.28);
  --text-main: #0f172a;
  --text-sub: #475569;
  --bg-chip: #e2e8f0;
  --bg-input: #ffffff;
  --border-input: #cbd5e1;
}

.dash-root:not(.theme-light) :deep(.date-picker-group) {
  background: var(--bg-input);
  border-color: var(--border-input);
}

.dash-root:not(.theme-light) :deep(.date-step-btn) {
  background: transparent;
  color: var(--text-main);
  border-color: var(--border-input);
}

.dash-root:not(.theme-light) :deep(.date-step-btn:hover:not(:disabled)) {
  background: rgba(56, 189, 248, 0.16);
  color: #38bdf8;
}

.dash-root:not(.theme-light) :deep(.date-step-input) {
  background: transparent;
  color: var(--text-main);
  color-scheme: dark;
}

.ambient-bg {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(110px);
  opacity: 0.28;
}

.glow-warm {
  width: 520px;
  height: 520px;
  top: -160px;
  left: -120px;
  background: radial-gradient(circle, #f97316, transparent 70%);
}

.glow-cool {
  width: 560px;
  height: 560px;
  bottom: -180px;
  right: -120px;
  background: radial-gradient(circle, #06b6d4, transparent 70%);
}

.theme-light .glow { opacity: 0.14; }

.grid-overlay {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(to right, rgba(148, 163, 184, 0.05) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(148, 163, 184, 0.05) 1px, transparent 1px);
  background-size: 40px 40px;
}

.glass-panel {
  position: relative;
  z-index: 1;
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  border-radius: 14px;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow: 0 10px 30px -12px rgba(2, 6, 23, 0.45);
}

.theme-light .glass-panel {
  box-shadow: 0 8px 24px -10px rgba(15, 23, 42, 0.12);
}

.cmd-header {
  max-width: 1540px;
  margin: 0 auto 12px;
  padding: 12px 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.cmd-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.brand-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.03em;
  color: #38bdf8;
}

.theme-light .brand-badge { color: #0284c7; }

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
  animation: pulseGlow 2s infinite;
}

@keyframes pulseGlow {
  0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
  70% { box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
  100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.cmd-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.cmd-title-wrap h1 {
  margin: 0;
  font-size: 19px;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.slot-chip {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 999px;
  background: rgba(56, 189, 248, 0.14);
  border: 1px solid rgba(56, 189, 248, 0.35);
  color: #7dd3fc;
}

.theme-light .slot-chip {
  background: #e0f2fe;
  color: #0369a1;
  border-color: #7dd3fc;
}

.cmd-actions {
  display: flex;
  align-items: center;
  gap: 7px;
  flex-wrap: wrap;
}

.hour-ctrl {
  display: inline-flex;
  align-items: center;
  height: 34px;
  border: 1px solid var(--border-input);
  border-radius: 8px;
  overflow: hidden;
  background: var(--bg-input);
}

.step-btn {
  height: 100%;
  border: none;
  background: transparent;
  color: var(--text-main);
  padding: 0 9px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border-right: 1px solid var(--border-input);
}

.step-btn:last-child { border-right: none; }
.step-btn:hover:not(:disabled) { background: rgba(56, 189, 248, 0.16); color: #38bdf8; }
.step-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.hour-select {
  height: 100%;
  border: none;
  border-right: 1px solid var(--border-input);
  background: var(--bg-input);
  color: var(--text-main);
  padding: 0 8px;
  font-size: 12px;
  font-weight: 600;
}

.cmd-btn {
  height: 34px;
  padding: 0 11px;
  border-radius: 8px;
  border: 1px solid var(--border-input);
  background: var(--bg-input);
  color: var(--text-main);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.cmd-btn:hover { border-color: #38bdf8; color: #38bdf8; }
.cmd-btn.accent {
  background: linear-gradient(135deg, #2563eb, #0284c7);
  border-color: transparent;
  color: #ffffff;
}

.dash-main {
  max-width: 1540px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.brief-bar {
  padding: 10px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.brief-main { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

.brief-tag {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  background: linear-gradient(135deg, #f97316, #ea580c);
  color: #ffffff;
}

.brief-text { margin: 0; font-size: 13px; font-weight: 500; }

.brief-highlights { display: flex; gap: 8px; flex-wrap: wrap; }

.hl-pill {
  font-size: 11px;
  padding: 3px 9px;
  border-radius: 999px;
  background: var(--bg-chip);
  border: 1px solid var(--border-card);
  color: var(--text-sub);
}

.error-strip {
  padding: 10px 16px;
  border-color: rgba(239, 68, 68, 0.5);
  color: #fca5a5;
  font-size: 13px;
}

.kpi-deck {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.kpi-card {
  padding: 14px 15px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 8px;
  border-top: 2px solid transparent;
  transition: transform 0.18s ease, border-color 0.18s ease;
}

.kpi-card:hover { transform: translateY(-2px); }
.tone-cool { border-top-color: #22d3ee; }
.tone-hero {
  border-top-color: #fb923c;
  background: linear-gradient(155deg, rgba(249, 115, 22, 0.16), var(--bg-card) 62%);
}
.tone-amber { border-top-color: #fbbf24; }
.tone-emerald { border-top-color: #10b981; }
.tone-split { border-top-color: #a855f7; }
.tone-sky { border-top-color: #38bdf8; }
.water-alert { border-color: rgba(239, 68, 68, 0.6); }

.kpi-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 6px;
}

.kpi-label { font-size: 12px; color: var(--text-sub); font-weight: 600; white-space: nowrap; }

.delta-badge {
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 999px;
  font-weight: 600;
  white-space: nowrap;
}

.badge-muted { background: var(--bg-chip); color: var(--text-sub); }
.badge-warn { background: rgba(245, 158, 11, 0.18); color: #fbbf24; }
.badge-danger { background: rgba(239, 68, 68, 0.2); color: #f87171; }
.badge-ok { background: rgba(16, 185, 129, 0.18); color: #34d399; }
.badge-cool { background: rgba(34, 211, 238, 0.18); color: #22d3ee; }
.badge-live { background: rgba(16, 185, 129, 0.16); color: #34d399; }
.theme-light .badge-warn { color: #b45309; }
.theme-light .badge-danger { color: #b91c1c; }
.theme-light .badge-ok, .theme-light .badge-live { color: #047857; }
.theme-light .badge-cool { color: #0369a1; }

.kpi-value { font-size: 23px; font-weight: 700; line-height: 1.15; }
.kpi-foot {
  font-size: 11px;
  color: var(--text-sub);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  flex-wrap: wrap;
}

.split-temps { display: flex; align-items: baseline; gap: 4px; }
.split-pair { display: flex; align-items: baseline; gap: 4px; font-size: clamp(16px, 1.25vw, 20px); white-space: nowrap; }
.dash-root.is-fullscreen .split-pair,
.dash-root:fullscreen .split-pair { font-size: clamp(14px, 1.05vw, 19px); }
.temp-sup { color: #fb7185; }
.temp-sep { color: var(--text-sub); font-size: 16px; }
.temp-ret { color: #38bdf8; }

.kpi-row-ring { display: flex; justify-content: space-between; align-items: center; gap: 8px; height: 100%; }
.kpi-ring-text { display: flex; flex-direction: column; justify-content: space-between; gap: 7px; flex: 1; min-width: 0; }
.ring-wrap { position: relative; width: 58px; height: 58px; flex-shrink: 0; }
.ring-svg { width: 58px; height: 58px; transform: rotate(-90deg); }
.ring-track { fill: none; stroke: var(--bg-chip); stroke-width: 6; }
.ring-fill { fill: none; stroke: #10b981; stroke-width: 6; stroke-linecap: round; transition: stroke-dashoffset 0.45s ease; }
.ring-center { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; }

.tabular { font-variant-numeric: tabular-nums; }

.stage-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 12px;
  align-items: stretch;
}

.span-7 { grid-column: span 7; }
.span-5 { grid-column: span 5; }

.stage-card, .sub-card {
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
  flex-wrap: wrap;
}

.card-head h2, .card-head h3 { margin: 0; font-size: 15px; font-weight: 700; }
.card-sub { margin: 3px 0 0; font-size: 11px; color: var(--text-sub); }

.seg-switch {
  display: inline-flex;
  padding: 3px;
  border-radius: 9px;
  background: var(--bg-chip);
  border: 1px solid var(--border-card);
  gap: 2px;
}

.seg-switch.full { width: 100%; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); }

.seg-btn {
  border: none;
  background: transparent;
  color: var(--text-sub);
  font-size: 11px;
  font-weight: 600;
  padding: 5px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.seg-btn.active {
  background: linear-gradient(135deg, #0284c7, #2563eb);
  color: #ffffff;
}

.chart-hero { width: 100%; height: 295px; }
.chart-hero.with-scrubber { height: 280px; }
.chart-side { width: 100%; height: 295px; flex: 1; }
.chart-donut { width: 100%; height: 230px; flex: 1; min-height: 210px; }

.chart-foot-note, .room-foot-note {
  font-size: 11px;
  color: var(--text-sub);
  padding-top: 2px;
}

.room-foot-note {
  margin-top: auto;
  padding-top: 6px;
  border-top: 1px dashed var(--border-card);
}

.hour-scrubber {
  display: grid;
  grid-template-columns: repeat(24, minmax(0, 1fr));
  gap: 4px;
}

.scrub-dot {
  border: 1px solid var(--border-card);
  background: var(--bg-chip);
  color: var(--text-sub);
  border-radius: 5px;
  padding: 4px 0;
  font-size: 10px;
  font-weight: 600;
  cursor: pointer;
  font-variant-numeric: tabular-nums;
}

.scrub-dot.active {
  background: #f59e0b;
  color: #0f172a;
  border-color: #fbbf24;
  font-weight: 700;
}

.scrub-dot.anom:not(.active) { border-color: rgba(239, 68, 68, 0.7); color: #f87171; }
.scrub-dot.empty { opacity: 0.4; }

.quadrant-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 11px;
  color: var(--text-sub);
  margin-top: auto;
}

.q-best { color: #34d399; }
.q-over { color: #fbbf24; }
.q-warn { color: #f87171; }
.q-cold { color: #38bdf8; }

.bottom-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  align-items: stretch;
}

.mini-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--bg-chip);
  color: var(--text-sub);
  font-weight: 600;
}

.mini-badge.emerald { background: rgba(16, 185, 129, 0.16); color: #34d399; }
.theme-light .mini-badge.emerald { color: #047857; }

.rdfz-list { display: flex; flex-direction: column; gap: 7px; }
.rdfz-row { display: flex; flex-direction: column; gap: 3px; }
.rdfz-meta { display: flex; justify-content: space-between; align-items: baseline; font-size: 12px; gap: 6px; }
.rdfz-name { font-weight: 600; }
.rdfz-nums { font-size: 11px; color: var(--text-sub); }
.rdfz-nums strong { color: var(--text-main); }
.rdfz-nums em { font-style: normal; }
.bar-track { height: 6px; border-radius: 999px; background: var(--bg-chip); overflow: hidden; }
.bar-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, #0284c7, #fb923c); transition: width 0.35s ease; }

.merchant-share-box {
  margin-top: auto;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--bg-chip);
  border: 1px solid var(--border-card);
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}

.ms-row, .ms-sub { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.ms-sub { font-size: 11px; color: var(--text-sub); }

.temp-dist-pills {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}

.td-pill {
  font-size: 11px;
  padding: 7px 10px;
  border-radius: 8px;
  background: var(--bg-chip);
  color: var(--text-sub);
  display: flex;
  justify-content: space-between;
}

.td-bad strong { color: #f87171; }
.td-ok strong { color: #fbbf24; }
.td-good strong { color: #34d399; }
.td-hot strong { color: #38bdf8; }

.watch-list { display: flex; flex-direction: column; gap: 8px; flex: 1; justify-content: space-between; }
.watch-empty { text-align: center; padding: 28px 0; color: var(--text-sub); font-size: 12px; }

.watch-item {
  width: 100%;
  text-align: left;
  border: 1px solid var(--border-card);
  background: var(--bg-chip);
  color: var(--text-main);
  border-radius: 10px;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  transition: border-color 0.15s ease, transform 0.15s ease;
}

.watch-item:hover { border-color: #38bdf8; transform: translateX(2px); }

.rank-idx {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  background: rgba(148, 163, 184, 0.2);
  flex-shrink: 0;
}

.rank-1 { background: rgba(239, 68, 68, 0.25); color: #f87171; }
.rank-2 { background: rgba(249, 115, 22, 0.25); color: #fb923c; }
.rank-3 { background: rgba(245, 158, 11, 0.25); color: #fbbf24; }

.watch-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.watch-info strong { font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.watch-info span { font-size: 11px; color: var(--text-sub); }

.watch-metric { text-align: right; display: flex; flex-direction: column; gap: 2px; font-size: 12px; }
.watch-metric span { font-size: 11px; color: var(--text-sub); }

.text-danger { color: #f87171; }
.text-warn { color: #fbbf24; }
.text-sky { color: #38bdf8; }
.text-emerald { color: #34d399; }
.text-amber { color: #fb923c; }

.drawer-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.65);
  z-index: 60;
  display: flex;
  justify-content: flex-end;
}

.drawer-panel {
  width: min(680px, 95vw);
  height: 100%;
  border-radius: 0;
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.drawer-head { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.drawer-head h3 { margin: 0; font-size: 16px; }
.drawer-chart { width: 100%; height: 240px; }
.drawer-table-wrap { overflow-x: auto; }
.mini-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.mini-table th, .mini-table td { padding: 7px 9px; border-bottom: 1px solid var(--border-card); text-align: left; }
.mini-table th { color: var(--text-sub); font-weight: 600; }

/* =====================================================================
 * 16:9 全屏投屏一屏完整适配（零垂直滚动、原生像素渲染）
 * ===================================================================== */
.dash-root.is-fullscreen,
.dash-root:fullscreen {
  position: fixed;
  inset: 0;
  z-index: 999;
  width: 100vw;
  height: 100vh;
  min-height: 100vh;
  overflow: hidden;
  padding: clamp(6px, 0.95vh, 12px) clamp(12px, 1.25vw, 22px);
  display: flex;
  flex-direction: column;
  gap: clamp(6px, 0.8vh, 10px);
}

.dash-root.is-fullscreen .cmd-header,
.dash-root:fullscreen .cmd-header {
  width: 100%;
  max-width: 1920px;
  margin: 0 auto;
  padding: clamp(6px, 0.65vh, 9px) 14px;
  flex: 0 0 auto;
  flex-wrap: nowrap;
  gap: 10px;
}

.dash-root.is-fullscreen .cmd-left,
.dash-root:fullscreen .cmd-left {
  flex-direction: row;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.dash-root.is-fullscreen .brand-badge,
.dash-root:fullscreen .brand-badge {
  display: none;
}

.dash-root.is-fullscreen .cmd-title-wrap h1,
.dash-root:fullscreen .cmd-title-wrap h1 {
  font-size: clamp(15px, 1.05vw, 19px);
  white-space: nowrap;
}

.dash-root.is-fullscreen .cmd-actions,
.dash-root:fullscreen .cmd-actions {
  flex-wrap: nowrap;
  gap: 6px;
}

.dash-root.is-fullscreen .cmd-btn,
.dash-root:fullscreen .cmd-btn,
.dash-root.is-fullscreen .hour-ctrl,
.dash-root:fullscreen .hour-ctrl,
.dash-root.is-fullscreen :deep(.date-picker-group),
.dash-root:fullscreen :deep(.date-picker-group) {
  height: 30px;
  font-size: 11px;
}

.dash-root.is-fullscreen :deep(.date-step-btn),
.dash-root.is-fullscreen :deep(.date-step-input),
.dash-root:fullscreen :deep(.date-step-btn),
.dash-root:fullscreen :deep(.date-step-input) {
  height: 100%;
  font-size: 11px;
}

.dash-root.is-fullscreen .dash-main,
.dash-root:fullscreen .dash-main {
  width: 100%;
  max-width: 1920px;
  margin: 0 auto;
  flex: 1 1 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1.08fr) minmax(0, 0.92fr);
  gap: clamp(6px, 0.8vh, 10px);
}

.dash-root.is-fullscreen .brief-bar,
.dash-root:fullscreen .brief-bar {
  padding: clamp(5px, 0.55vh, 8px) 14px;
  flex-wrap: nowrap;
  gap: 10px;
  min-height: 0;
}

.dash-root.is-fullscreen .brief-main,
.dash-root:fullscreen .brief-main {
  flex-wrap: nowrap;
  min-width: 0;
  flex: 1 1 auto;
}

.dash-root.is-fullscreen .brief-text,
.dash-root:fullscreen .brief-text {
  font-size: clamp(11px, 0.72vw, 13px);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dash-root.is-fullscreen .brief-highlights,
.dash-root:fullscreen .brief-highlights {
  flex-wrap: nowrap;
  flex-shrink: 0;
  gap: 6px;
}

.dash-root.is-fullscreen .hl-pill,
.dash-root:fullscreen .hl-pill {
  font-size: clamp(10px, 0.62vw, 11px);
  padding: 2px 8px;
  white-space: nowrap;
}

.dash-root.is-fullscreen .kpi-deck,
.dash-root:fullscreen .kpi-deck {
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: clamp(6px, 0.75vw, 12px);
}

.dash-root.is-fullscreen .kpi-card,
.dash-root:fullscreen .kpi-card {
  padding: clamp(7px, 0.8vh, 11px) clamp(10px, 0.85vw, 14px);
  gap: 4px;
}

.dash-root.is-fullscreen .kpi-value,
.dash-root:fullscreen .kpi-value {
  font-size: clamp(18px, 1.3vw, 23px);
}

.dash-root.is-fullscreen .ring-wrap,
.dash-root.is-fullscreen .ring-svg,
.dash-root:fullscreen .ring-wrap,
.dash-root:fullscreen .ring-svg {
  width: clamp(42px, 4.6vh, 52px);
  height: clamp(42px, 4.6vh, 52px);
}

.dash-root.is-fullscreen .stage-grid,
.dash-root:fullscreen .stage-grid,
.dash-root.is-fullscreen .bottom-grid,
.dash-root:fullscreen .bottom-grid {
  min-height: 0;
  gap: clamp(6px, 0.75vw, 12px);
}

.dash-root.is-fullscreen .stage-card,
.dash-root:fullscreen .stage-card,
.dash-root.is-fullscreen .sub-card,
.dash-root:fullscreen .sub-card {
  padding: clamp(8px, 0.95vh, 13px) clamp(11px, 0.95vw, 16px);
  gap: clamp(4px, 0.55vh, 8px);
  min-height: 0;
  overflow: hidden;
}

.dash-root.is-fullscreen .card-head,
.dash-root:fullscreen .card-head {
  flex-shrink: 0;
  align-items: center;
}

.dash-root.is-fullscreen .card-head h2,
.dash-root.is-fullscreen .card-head h3,
.dash-root:fullscreen .card-head h2,
.dash-root:fullscreen .card-head h3 {
  font-size: clamp(13px, 0.85vw, 15px);
}

.dash-root.is-fullscreen .card-sub,
.dash-root:fullscreen .card-sub {
  display: none;
}

.dash-root.is-fullscreen .chart-hero,
.dash-root.is-fullscreen .chart-hero.with-scrubber,
.dash-root.is-fullscreen .chart-side,
.dash-root:fullscreen .chart-hero,
.dash-root:fullscreen .chart-hero.with-scrubber,
.dash-root:fullscreen .chart-side {
  height: auto;
  flex: 1 1 0;
  min-height: 0;
}

.dash-root.is-fullscreen .chart-donut,
.dash-root:fullscreen .chart-donut {
  height: auto;
  flex: 1 1 0;
  min-height: 96px;
}

.dash-root.is-fullscreen .rdfz-list,
.dash-root:fullscreen .rdfz-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: 12px;
  row-gap: clamp(3px, 0.45vh, 6px);
  align-content: start;
}

.dash-root.is-fullscreen .rdfz-meta,
.dash-root:fullscreen .rdfz-meta {
  font-size: 11px;
}

.dash-root.is-fullscreen .rdfz-name,
.dash-root:fullscreen .rdfz-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dash-root.is-fullscreen .rdfz-nums,
.dash-root:fullscreen .rdfz-nums {
  font-size: 10px;
  white-space: nowrap;
}

.dash-root.is-fullscreen .rdfz-nums em:first-of-type,
.dash-root:fullscreen .rdfz-nums em:first-of-type {
  display: none;
}

.dash-root.is-fullscreen .bar-track,
.dash-root:fullscreen .bar-track {
  height: 5px;
}

.dash-root.is-fullscreen .merchant-share-box,
.dash-root:fullscreen .merchant-share-box {
  padding: clamp(5px, 0.55vh, 8px) 10px;
  gap: 2px;
  font-size: 11px;
}

.dash-root.is-fullscreen .temp-dist-pills,
.dash-root:fullscreen .temp-dist-pills {
  gap: 4px;
}

.dash-root.is-fullscreen .td-pill,
.dash-root:fullscreen .td-pill {
  padding: clamp(4px, 0.45vh, 6px) 8px;
  font-size: 10.5px;
}

.dash-root.is-fullscreen .chart-foot-note,
.dash-root.is-fullscreen .quadrant-legend,
.dash-root.is-fullscreen .room-foot-note,
.dash-root:fullscreen .chart-foot-note,
.dash-root:fullscreen .quadrant-legend,
.dash-root:fullscreen .room-foot-note {
  padding-top: 3px;
  font-size: 10px;
  gap: 6px;
}

.dash-root.is-fullscreen .watch-list,
.dash-root:fullscreen .watch-list {
  gap: clamp(3px, 0.45vh, 6px);
  min-height: 0;
}

.dash-root.is-fullscreen .watch-item,
.dash-root:fullscreen .watch-item {
  flex: 1 1 0;
  min-height: 0;
  padding: clamp(4px, 0.45vh, 8px) 10px;
}

.dash-root.is-fullscreen .watch-info,
.dash-root.is-fullscreen .watch-metric,
.dash-root:fullscreen .watch-info,
.dash-root:fullscreen .watch-metric {
  gap: 1px;
  line-height: 1.2;
}

.dash-root.is-fullscreen .watch-metric,
.dash-root:fullscreen .watch-metric {
  font-size: clamp(11px, 0.7vw, 12px);
}

.dash-root.is-fullscreen .watch-info strong,
.dash-root:fullscreen .watch-info strong {
  font-size: clamp(11.5px, 0.72vw, 13px);
}

.dash-root.is-fullscreen .watch-info span,
.dash-root.is-fullscreen .watch-metric span,
.dash-root:fullscreen .watch-info span,
.dash-root:fullscreen .watch-metric span {
  font-size: 10px;
}

@media (max-width: 1420px) {
  .dash-root.is-fullscreen .brief-highlights,
  .dash-root:fullscreen .brief-highlights {
    display: none;
  }
}

@media (max-width: 1280px) {
  .dash-root:not(.is-fullscreen):not(:fullscreen) .kpi-deck { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .dash-root:not(.is-fullscreen):not(:fullscreen) .span-7,
  .dash-root:not(.is-fullscreen):not(:fullscreen) .span-5 { grid-column: span 12; }
}

@media (max-width: 960px) {
  .bottom-grid { grid-template-columns: 1fr; }
}

@media (max-width: 640px) {
  .dash-root { padding: 10px 10px 24px; }
  .kpi-deck { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .kpi-value { font-size: 19px; }
  .hour-scrubber { grid-template-columns: repeat(12, minmax(0, 1fr)); }
}
</style>
