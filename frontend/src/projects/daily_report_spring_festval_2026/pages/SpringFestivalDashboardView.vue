<template>
  <div :class="['spring-dashboard-page', `spring-dashboard-page--${themeMode}`]">
    <AppHeader />
    <div v-if="themeMode === 'festival'" class="festival-background-overlay" aria-hidden="true"></div>
    <div v-if="themeMode === 'festival'" class="festival-decorations" aria-hidden="true">
      <!-- 左右挂饰 -->
      <div class="festival-side-ornament festival-side-ornament--left">🧨</div>
      <div class="festival-side-ornament festival-side-ornament--right">🧨</div>
      <!-- 顶部灯笼群 -->
      <div class="festival-lantern-group">
        <span class="festival-lantern festival-lantern--1">🏮</span>
        <span class="festival-lantern festival-lantern--2">🏮</span>
        <span class="festival-lantern festival-lantern--3">🏮</span>
      </div>
      <!-- 卷轴标题修饰 -->
      <div class="festival-title-wrapper">
        <div class="festival-scroll-decor"></div>
        <span class="festival-title-mark">福启新岁 · 万象更新</span>
      </div>
    </div>
    <main ref="dashboardCaptureRef" class="container spring-dashboard-main">
      <Breadcrumbs :items="breadcrumbItems" />

      <section class="card elevated">
        <header class="card-header">
          <h2>春节数据看板</h2>
          <p class="sub">数据来源：上传 xlsx 提取 JSON + 数据库气温</p>
        </header>
        <div v-if="errorMessage" class="state error">{{ errorMessage }}</div>
        <div v-else-if="loading" class="state">正在生成看板数据…</div>
        <div v-else-if="!hasPayload" class="state">
          暂无可用数据，请先返回上传页提取 JSON。
        </div>
        <div v-else class="toolbar">
          <label class="toolbar-label">
            日期：
            <select v-model="selectedDate" class="date-select">
              <option v-for="item in availableDates" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>
          <label class="toolbar-label">
            风格：
            <select v-model="themeMode" class="theme-select">
              <option value="default">默认风格</option>
              <option value="festival">春节氛围</option>
            </select>
          </label>
          <button class="btn" type="button" @click="debugVisible = !debugVisible">
            {{ debugVisible ? '隐藏调试信息' : '显示调试信息' }}
          </button>
          <button class="btn" type="button" :disabled="downloadingPdf" @click="downloadDashboardPdf">
            {{ downloadingPdf ? '正在生成PDF…' : '下载PDF' }}
          </button>
          <button class="btn" type="button" @click="goBackToEntry">返回上传页</button>
        </div>
      </section>

      <section v-if="hasPayload && debugVisible" class="card elevated debug-panel">
        <header class="card-header">
          <h3>调试信息</h3>
          <p class="sub">用于定位“有 JSON 但卡片/图表空白”的命中情况</p>
        </header>
        <pre class="json-preview">{{ debugInfoText }}</pre>
      </section>

      <!-- 摘要卡片区 -->
      <section v-if="hasPayload" class="summary-grid">
        <article class="summary-card summary-card--primary card elevated">
          <div class="summary-card__label">当日平均气温（及同比增量）</div>
          <div class="summary-card__value">
            {{ formatMetric(tempCard.current, '℃', 1) }}
            <span class="summary-card__delta-inline">{{ formatIncrement(tempCard.delta, '℃', 1) }}</span>
          </div>
        </article>
        <article class="summary-card summary-card--success card elevated">
          <div class="summary-card__label">当日集团标煤消耗（剔除庄河改造锅炉房）</div>
          <div class="summary-card__value">
            {{ formatMetric(coalCard.current, '吨', 0) }}
            <span class="summary-card__delta-inline">{{ formatIncrement(coalCard.delta, '吨', 0) }}</span>
          </div>
        </article>
        <article class="summary-card summary-card--warning card elevated">
          <div class="summary-card__label">当日集团总投诉量</div>
          <div class="summary-card__value">
            {{ formatMetric(totalComplaintCard.current, '件', 0) }}
            <span class="summary-card__delta-inline">{{ formatIncrement(totalComplaintCard.delta, '件', 0) }}</span>
          </div>
        </article>
        <article class="summary-card summary-card--danger card elevated">
          <div class="summary-card__label">当日集团净投诉量</div>
          <div class="summary-card__value">
            {{ formatMetric(netComplaintCard.current, '件', 0) }}
            <span class="summary-card__delta-inline">{{ formatIncrement(netComplaintCard.delta, '件', 0) }}</span>
          </div>
        </article>
      </section>

      <!-- 图表与明细区 -->
      <section v-if="hasPayload" class="content-grid">
        <section class="card elevated">
          <header class="card-header">
            <h3>气温变化情况（向后预测3日，含同期）</h3>
          </header>
          <EChart :option="temperatureTrendOption" :height="320" />
        </section>

        <section class="card elevated">
          <header class="card-header">
            <h3>当日各口径耗原煤量对比</h3>
          </header>
          <EChart :option="coalTrendOption" :height="320" />
          <div class="table-scroll">
            <table class="mini-table">
              <thead>
                <tr>
                  <th rowspan="2">日期</th>
                  <th rowspan="2">气温</th>
                  <th colspan="2">集团汇总</th>
                  <th colspan="2">主城区</th>
                  <th colspan="2">金州</th>
                  <th colspan="2">北方</th>
                  <th colspan="2">金普</th>
                  <th colspan="2">庄河</th>
                </tr>
                <tr>
                  <th>本期</th>
                  <th>同期</th>
                  <th>本期</th>
                  <th>同期</th>
                  <th>本期</th>
                  <th>同期</th>
                  <th>本期</th>
                  <th>同期</th>
                  <th>本期</th>
                  <th>同期</th>
                  <th>本期</th>
                  <th>同期</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in coalVisibleRows" :key="row.date">
                  <td>{{ row.date }}</td>
                  <td>{{ formatMetric(row.temperature, '℃', 1) }}</td>
                  <td>{{ formatMetric(row.groupCurrent, '吨', 0) }}</td>
                  <td>{{ formatMetric(row.groupPrior, '吨', 0) }}</td>
                  <td>{{ formatMetric(row.mainCityCurrent, '吨', 0) }}</td>
                  <td>{{ formatMetric(row.mainCityPrior, '吨', 0) }}</td>
                  <td>{{ formatMetric(row.jinzhouCurrent, '吨', 0) }}</td>
                  <td>{{ formatMetric(row.jinzhouPrior, '吨', 0) }}</td>
                  <td>{{ formatMetric(row.beifangCurrent, '吨', 0) }}</td>
                  <td>{{ formatMetric(row.beifangPrior, '吨', 0) }}</td>
                  <td>{{ formatMetric(row.jinpuCurrent, '吨', 0) }}</td>
                  <td>{{ formatMetric(row.jinpuPrior, '吨', 0) }}</td>
                  <td>{{ formatMetric(row.zhuangheCurrent, '吨', 0) }}</td>
                  <td>{{ formatMetric(row.zhuanghePrior, '吨', 0) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="card elevated">
          <header class="card-header">
            <h3>投诉量分项</h3>
          </header>
          <div class="complaint-dual-charts">
            <section class="complaint-chart-panel">
              <header class="complaint-chart-panel__title">本日总投诉量（本期/同期）+ 本期气温</header>
              <EChart :option="complaintTotalTrendOption" :height="280" />
            </section>
            <section class="complaint-chart-panel">
              <header class="complaint-chart-panel__title">本日净投诉量（本期/同期）+ 本期气温</header>
              <EChart :option="complaintNetTrendOption" :height="280" />
            </section>
          </div>
          <table class="mini-table">
            <thead>
              <tr>
                <th>日期</th>
                <th>气温</th>
                <th>总投诉量（本期）</th>
                <th>总投诉量（同期）</th>
                <th>净投诉量（本期）</th>
                <th>净投诉量（同期）</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in complaintVisibleRows" :key="row.date">
                <td>{{ row.date }}</td>
                <td>{{ formatMetric(row.temperature, '℃', 1) }}</td>
                <td>{{ formatMetric(row.totalCurrent, '件', 0) }}</td>
                <td>{{ formatMetric(row.totalPrior, '件', 0) }}</td>
                <td>{{ formatMetric(row.netCurrent, '件', 0) }}</td>
                <td>{{ formatMetric(row.netPrior, '件', 0) }}</td>
              </tr>
            </tbody>
          </table>
        </section>
      </section>

      <!-- 底部设备明细 -->
      <section v-if="hasPayload" class="card elevated">
        <header class="card-header">
          <h3>各单位运行设备数量明细表</h3>
          <p class="sub">仅显示业务日期数据，单位：台</p>
        </header>
        <div class="table-scroll">
          <table class="mini-table">
            <thead>
              <tr>
                <th>口径</th>
                <th>炉机组态</th>
                <th>调峰水炉</th>
                <th>燃煤锅炉</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in deviceStatusRows" :key="row.scope">
                <td>{{ row.scope }}</td>
                <td>
                  <div v-if="row.steamGroup.length" class="device-combo-cell">
                    <div v-for="item in row.steamGroup" :key="item.label" class="combo-item">
                      <span class="combo-label" :style="{ color: item.color, backgroundColor: `${item.color}20` }">{{ item.label }}</span>
                      <span class="combo-value">
                        <span :style="{ color: item.color }">{{ item.current }}</span>
                        <span class="combo-sep">/</span>
                        <span :style="{ color: item.color }">{{ item.prior }}</span>
                      </span>
                    </div>
                  </div>
                  <span v-else>—</span>
                </td>
                <td>
                  <div v-if="row.waterGroup.length" class="device-combo-cell">
                    <div v-for="item in row.waterGroup" :key="item.label" class="combo-item">
                      <span class="combo-label" :style="{ color: item.color, backgroundColor: `${item.color}20` }">{{ item.label }}</span>
                      <span class="combo-value">
                        <span :style="{ color: item.color }">{{ item.current }}</span>
                        <span class="combo-sep">/</span>
                        <span :style="{ color: item.color }">{{ item.prior }}</span>
                      </span>
                    </div>
                  </div>
                  <span v-else>—</span>
                </td>
                <td>
                  <div v-if="row.houseGroup.length" class="device-combo-cell">
                    <div v-for="item in row.houseGroup" :key="item.label" class="combo-item">
                      <span class="combo-label" :style="{ color: item.color, backgroundColor: `${item.color}20` }">{{ item.label }}</span>
                      <span class="combo-value">
                        <span :style="{ color: item.color }">{{ item.current }}</span>
                        <span class="combo-sep">/</span>
                        <span :style="{ color: item.color }">{{ item.prior }}</span>
                      </span>
                    </div>
                  </div>
                  <span v-else>—</span>
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
import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'
import { ensureProjectsLoaded, getProjectNameById } from '../../daily_report_25_26/composables/useProjects'
import { getLatestExtractedJson, getLatestExtractedPayload, getTemperatureTrendByDate } from '../services/api'

const route = useRoute()
const router = useRouter()
const TARGET_PROJECT_KEY = 'daily_report_spring_festval_2026'
const THEME_STORAGE_KEY = 'spring_festival_dashboard_theme_mode'
const projectKey = computed(() => String(route.params.projectKey || ''))
const storageKey = computed(() => `spring_festival_payload_${projectKey.value}`)

const loading = ref(false)
const errorMessage = ref('')
const downloadingPdf = ref(false)
const chartLibraryReady = ref(true)
const debugVisible = ref(false)
const extractedPayload = ref(null)
const selectedDate = ref('')
const themeMode = ref('default')
const temperatureMainMap = ref({})
const temperaturePeerMap = ref({})
const dashboardCaptureRef = ref(null)

const EChart = defineComponent({
  name: 'SpringFestivalEChart',
  props: {
    option: { type: Object, required: true },
    height: { type: [Number, String], default: 300 },
  },
  setup(props) {
    const container = ref(null)
    const latestOption = shallowRef(null)
    let chart = null
    const applyOption = () => {
      if (!chart || !latestOption.value) return
      chart.setOption(latestOption.value, { notMerge: true, lazyUpdate: true })
    }
    const ensureChart = () => {
      if (!container.value || !window.echarts) return
      if (!chart) chart = window.echarts.init(container.value)
      applyOption()
    }
    const resize = () => chart?.resize()
    onMounted(() => {
      ensureChart()
      window.addEventListener('resize', resize)
    })
    onBeforeUnmount(() => {
      window.removeEventListener('resize', resize)
      if (chart) {
        chart.dispose()
        chart = null
      }
    })
    watch(
      () => props.option,
      (value) => {
        latestOption.value = value || null
        ensureChart()
      },
      { immediate: true, deep: true },
    )
    return () =>
      h('div', {
        ref: container,
        style: { height: typeof props.height === 'number' ? `${props.height}px` : props.height },
      })
  },
})

const hasPayload = computed(() => Boolean(extractedPayload.value?.byDate))
const availableDates = computed(() => {
  const dates = extractedPayload.value?.dates
  if (Array.isArray(dates) && dates.length) {
    const normalized = dates.map((item) => normalizeDateLabel(item))
    return [...new Set(normalized)].sort()
  }
  const byDateKeys = Object.keys(extractedPayload.value?.byDate || {})
  return byDateKeys.map((item) => normalizeDateLabel(item)).sort()
})
const selectedDateBucket = computed(() => {
  if (!selectedDate.value || !hasPayload.value) return {}
  const bucket = extractedPayload.value.byDate?.[selectedDate.value]
  if (bucket && typeof bucket === 'object') return bucket
  const fallbackKey = Object.keys(extractedPayload.value.byDate || {}).find(
    (key) => String(key).trim() === String(selectedDate.value).trim(),
  )
  return fallbackKey ? (extractedPayload.value.byDate?.[fallbackKey] || {}) : {}
})
const projectName = computed(() => getProjectNameById(projectKey.value) || projectKey.value)
const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: projectName.value, to: `/projects/${encodeURIComponent(projectKey.value)}` },
  { label: '春节数据看板', to: null },
])

function normalizeText(value) {
  return String(value || '').replace(/\s+/g, '')
}

function findScopeBucket(dateBucket) {
  const candidates = ['全口径', '集团汇总', '集团全口径']
  for (const key of Object.keys(dateBucket || {})) {
    if (candidates.includes(key)) return dateBucket[key]
  }
  const firstKey = Object.keys(dateBucket || {})[0]
  return firstKey ? dateBucket[firstKey] : {}
}

function pickScopeBucket(dateBucket, candidateNames = []) {
  const buckets = dateBucket || {}
  for (const candidate of candidateNames) {
    if (buckets[candidate] && typeof buckets[candidate] === 'object') {
      return buckets[candidate]
    }
  }
  return {}
}

function findMetricPayload(scopeBucket, matcher) {
  const entries = Object.entries(scopeBucket || {})
  for (const [name, payload] of entries) {
    if (matcher(normalizeText(name))) {
      return { metricName: name, payload }
    }
  }
  return null
}

function findMetricMatchAcrossScopes(dateBucket, matcher) {
  const scopes = Object.entries(dateBucket || {})
  const preferredScopeNames = ['全口径', '集团汇总', '集团全口径', '集团', '全集团']
  const sortedScopes = [
    ...scopes.filter(([name]) => preferredScopeNames.includes(String(name))),
    ...scopes.filter(([name]) => !preferredScopeNames.includes(String(name))),
  ]
  for (const [scopeName, scopeBucket] of sortedScopes) {
    const matched = findMetricPayload(scopeBucket, matcher)
    if (!matched || typeof matched.payload !== 'object') continue
    const payload = matched.payload
    if (payload.current !== null && payload.current !== undefined) return { scopeName, metricName: matched.metricName, payload }
    if (payload.prior !== null && payload.prior !== undefined) return { scopeName, metricName: matched.metricName, payload }
  }
  return { scopeName: null, metricName: null, payload: {} }
}

function safeNumber(value) {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : null
}

function computeIncrement(current, prior) {
  if (!Number.isFinite(current) || !Number.isFinite(prior)) return null
  return Number(current) - Number(prior)
}

const COAL_SCOPE_CONFIGS = [
  { key: 'group', label: '集团汇总', candidates: ['集团汇总', '全口径', '集团全口径', '集团', '全集团'] },
  { key: 'mainCity', label: '主城区', candidates: ['主城区'] },
  { key: 'jinzhou', label: '金州', candidates: ['金州', '金州热电'] },
  { key: 'beifang', label: '北方', candidates: ['北方', '北方热电'] },
  { key: 'jinpu', label: '金普', candidates: ['金普', '金普公司'] },
  { key: 'zhuanghe', label: '庄河', candidates: ['庄河', '庄河环海'], useZhangtunPrior: true },
]

const DEVICE_SCOPE_CONFIGS = [
  {
    label: '北海电厂（含北海水炉）',
    aggregateCandidates: [
      ['北海热电联产', '北海电厂', '北海热电厂'],
      ['北海水炉'],
    ],
  },
  { label: '香海电厂', candidates: ['香海电厂', '香海热电厂'] },
  { label: '金州', candidates: ['金州', '金州热电'] },
  { label: '北方', candidates: ['北方', '北方热电'] },
  { label: '金普', candidates: ['金普', '金普公司', '金普热电'] },
  { label: '庄河', candidates: ['庄河', '庄河环海'] },
]

const coalCard = computed(() => {
  const matched = findMetricMatchAcrossScopes(
    selectedDateBucket.value,
    (name) => name.includes('原煤消耗量') && name.includes('剔除庄河改造'),
  )
  const payload = matched.payload || {}
  const current = safeNumber(payload?.current)
  const prior = safeNumber(payload?.prior)
  return { current, prior, delta: computeIncrement(current, prior) }
})

const totalComplaintCard = computed(() => {
  const matched = findMetricMatchAcrossScopes(selectedDateBucket.value, (name) => name.includes('总投诉量'))
  const payload = matched.payload || {}
  const current = safeNumber(payload?.current)
  const prior = safeNumber(payload?.prior)
  return { current, prior, delta: computeIncrement(current, prior) }
})

const netComplaintCard = computed(() => {
  const matched = findMetricMatchAcrossScopes(selectedDateBucket.value, (name) => name.includes('净投诉量'))
  const payload = matched.payload || {}
  const current = safeNumber(payload?.current)
  const prior = safeNumber(payload?.prior)
  return { current, prior, delta: computeIncrement(current, prior) }
})

const tempCard = computed(() => {
  const main = safeNumber(temperatureMainMap.value?.[selectedDate.value])
  const peer = safeNumber(temperaturePeerMap.value?.[selectedDate.value])
  const delta = (main !== null && peer !== null) ? (main - peer) : null
  return { current: main, prior: peer, delta }
})

const temperatureWindowDates = computed(() => {
  const baseDate = parseDateKey(selectedDate.value)
  if (!baseDate) return []
  const labels = []
  for (let offset = -3; offset <= 3; offset += 1) {
    labels.push(formatDateKey(addDays(baseDate, offset)))
  }
  return labels
})

const coalScopeRows = computed(() => {
  const dateBucket = selectedDateBucket.value || {}
  return COAL_SCOPE_CONFIGS.map((scope) => {
    const scopeBucket = pickScopeBucket(dateBucket, scope.candidates)
    const matchedCurrent = findMetricPayload(scopeBucket, (name) => name.includes('原煤消耗量'))
    const matchedPrior = scope.label === '庄河'
        ? (findMetricPayload(scopeBucket, (name) => name.includes('其中：张屯原煤消耗量') || (name.includes('其中') && name.includes('张屯原煤消耗量'))) || matchedCurrent)
        : matchedCurrent
    return { scope: scope.label, current: safeNumber(matchedCurrent?.payload?.current), prior: safeNumber(matchedPrior?.payload?.prior) }
  })
})

const coalRows = computed(() =>
  availableDates.value.map((date) => {
    const normalizedDate = normalizeDateLabel(date)
    const dateBucket = extractedPayload.value?.byDate?.[normalizedDate] || {}
    const res = { date: normalizedDate, temperature: safeNumber(temperatureMainMap.value?.[normalizedDate]) }
    COAL_SCOPE_CONFIGS.forEach(s => {
      const sb = pickScopeBucket(dateBucket, s.candidates)
      const mc = findMetricPayload(sb, (name) => name.includes('原煤消耗量'))
      const mp = s.label === '庄河' ? (findMetricPayload(sb, (n) => n.includes('张屯原煤消耗量')) || mc) : mc
      res[`${s.key}Current`] = safeNumber(mc?.payload?.current)
      res[`${s.key}Prior`] = safeNumber(mp?.payload?.prior)
    })
    return res
  })
)

const coalVisibleRows = computed(() => coalRows.value.filter(r => shouldShowActualByBizDate(r.date)))

const coalTrendOption = computed(() => ({
  tooltip: { 
    trigger: 'axis',
    formatter: (params) => {
      let res = params[0].axisValue + '<br/>'
      params.forEach(item => {
        const val = safeNumber(item.value)
        res += `${item.marker}${item.seriesName}: ${val !== null ? Math.round(val).toLocaleString() : '—'} 吨<br/>`
      })
      return res
    }
  },
  legend: { top: 0 },
  grid: { left: 50, right: 20, bottom: 48, top: 28 },
  xAxis: { type: 'category', data: coalScopeRows.value.map(i => i.scope) },
  yAxis: { type: 'value', name: '吨' },
  series: [
    { 
      name: '本期', 
      type: 'bar', 
      itemStyle: { color: '#1d4ed8' }, 
      data: coalScopeRows.value.map(i => i.current), 
      label: { 
        show: true, 
        position: 'top',
        formatter: (p) => safeNumber(p.value) !== null ? Math.round(p.value).toLocaleString() : ''
      } 
    },
    { 
      name: '同期', 
      type: 'bar', 
      itemStyle: { color: '#f59e0b' }, 
      data: coalScopeRows.value.map(i => i.prior), 
      label: { 
        show: true, 
        position: 'top',
        formatter: (p) => safeNumber(p.value) !== null ? Math.round(p.value).toLocaleString() : ''
      } 
    }
  ]
}))

const complaintRows = computed(() =>
  availableDates.value.map((date) => {
    const bucket = extractedPayload.value?.byDate?.[date] || {}
    const total = findMetricMatchAcrossScopes(bucket, (name) => name.includes('总投诉量')).payload || {}
    const net = findMetricMatchAcrossScopes(bucket, (name) => name.includes('净投诉量')).payload || {}
    return { date, temperature: safeNumber(temperatureMainMap.value?.[normalizeDateLabel(date)]), totalCurrent: safeNumber(total?.current), netCurrent: safeNumber(net?.current), totalPrior: safeNumber(total?.prior), netPrior: safeNumber(net?.prior) }
  })
)

const complaintVisibleRows = computed(() => complaintRows.value.filter(r => shouldShowActualByBizDate(r.date)))

function resolveDeviceMetric(dateBucket, scopeConfig, metricMatcher) {
  if (Array.isArray(scopeConfig.aggregateCandidates)) {
    let cur = 0, pri = 0
    scopeConfig.aggregateCandidates.forEach(cand => {
      const matched = findMetricPayload(pickScopeBucket(dateBucket, cand), metricMatcher)
      cur += safeNumber(matched?.payload?.current) || 0
      pri += safeNumber(matched?.payload?.prior) || 0
    })
    return { current: cur, prior: pri }
  }
  const matched = findMetricPayload(pickScopeBucket(dateBucket, scopeConfig.candidates), metricMatcher)
  return { current: safeNumber(matched?.payload?.current), prior: safeNumber(matched?.payload?.prior) }
}

const deviceStatusRows = computed(() => {
  const dateBucket = selectedDateBucket.value || {}
  const build = (l, c, cur, pri) => ({ label: l, color: c, current: cur || 0, prior: pri || 0 })
  const filter = (items) => items.filter(i => !(i.current <= 0 && i.prior <= 0))
  return DEVICE_SCOPE_CONFIGS.map(sc => {
    const s = resolveDeviceMetric(dateBucket, sc, (n) => n.includes('运行汽炉数'))
    const t = resolveDeviceMetric(dateBucket, sc, (n) => n.includes('运行汽轮机数'))
    const w = resolveDeviceMetric(dateBucket, sc, (n) => n.includes('运行水炉数'))
    const h = resolveDeviceMetric(dateBucket, sc, (n) => n.includes('锅炉房锅炉数'))
    return {
      scope: sc.label,
      steamGroup: filter([build('炉', '#f97316', s.current, s.prior), build('机', '#3b82f6', t.current, t.prior)]),
      waterGroup: filter([build('水', '#06b6d4', w.current, w.prior)]),
      houseGroup: filter([build('锅', '#8b5cf6', h.current, h.prior)])
    }
  })
})

function shouldShowActualByBizDate(d) {
  const r = parseDateKey(d), b = parseDateKey(selectedDate.value)
  return (!r || !b) ? true : r.getTime() <= b.getTime()
}

const complaintChartAxisDates = computed(() => [...new Set(availableDates.value.map(normalizeDateLabel))].sort())
function formatAxisMonthDay(d) { const p = normalizeDateLabel(d).split('-'); return p.length === 3 ? `${p[1]}-${p[2]}` : d }

const complaintTotalTrendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { top: 0 },
  grid: { left: 40, right: 36, bottom: 40, top: 44 },
  xAxis: { type: 'category', data: complaintChartAxisDates.value, axisLabel: { formatter: formatAxisMonthDay } },
  yAxis: [{ type: 'value', name: '件', splitLine: { show: false } }, { type: 'value', name: '℃', splitLine: { show: false } }],
  series: [
    { 
      name: '总投诉量（本期）', 
      type: 'bar', 
      itemStyle: { color: '#60a5fa' }, 
      data: complaintChartAxisDates.value.map(d => shouldShowActualByBizDate(d) ? complaintRows.value.find(r => normalizeDateLabel(r.date) === d)?.totalCurrent : null),
      label: { show: true, position: 'top' }
    },
    { 
      name: '总投诉量（同期）', 
      type: 'bar', 
      itemStyle: { color: '#fbbf24' }, 
      data: complaintChartAxisDates.value.map(d => shouldShowActualByBizDate(d) ? complaintRows.value.find(r => normalizeDateLabel(r.date) === d)?.totalPrior : null),
      label: { show: true, position: 'top' }
    },
    { name: '本期气温', type: 'line', yAxisIndex: 1, smooth: true, itemStyle: { color: '#22c55e' }, data: complaintChartAxisDates.value.map(d => shouldShowActualByBizDate(d) ? complaintRows.value.find(r => normalizeDateLabel(r.date) === d)?.temperature : null) }
  ]
}))

const complaintNetTrendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { top: 0 },
  grid: { left: 40, right: 36, bottom: 40, top: 44 },
  xAxis: { type: 'category', data: complaintChartAxisDates.value, axisLabel: { formatter: formatAxisMonthDay } },
  yAxis: [{ type: 'value', name: '件', splitLine: { show: false } }, { type: 'value', name: '℃', splitLine: { show: false } }],
  series: [
    { 
      name: '净投诉量（本期）', 
      type: 'bar', 
      itemStyle: { color: '#60a5fa' }, 
      data: complaintChartAxisDates.value.map(d => shouldShowActualByBizDate(d) ? complaintRows.value.find(r => normalizeDateLabel(r.date) === d)?.netCurrent : null),
      label: { show: true, position: 'top' }
    },
    { 
      name: '净投诉量（同期）', 
      type: 'bar', 
      itemStyle: { color: '#fbbf24' }, 
      data: complaintChartAxisDates.value.map(d => shouldShowActualByBizDate(d) ? complaintRows.value.find(r => normalizeDateLabel(r.date) === d)?.netPrior : null),
      label: { show: true, position: 'top' }
    },
    { name: '本期气温', type: 'line', yAxisIndex: 1, smooth: true, itemStyle: { color: '#22c55e' }, data: complaintChartAxisDates.value.map(d => shouldShowActualByBizDate(d) ? complaintRows.value.find(r => normalizeDateLabel(r.date) === d)?.temperature : null) }
  ]
}))

const temperatureTrendOption = computed(() => {
  const labels = temperatureWindowDates.value
  const biz = normalizeDateLabel(selectedDate.value)
  return {
    tooltip: { 
      trigger: 'axis',
      formatter: (params) => {
        let res = params[0].axisValue + '<br/>'
        params.forEach(item => {
          const val = safeNumber(item.value)
          res += `${item.marker}${item.seriesName}: ${val !== null ? val.toFixed(1) : '—'} ℃<br/>`
        })
        return res
      }
    },
    legend: { top: 0 },
    grid: { left: 40, right: 20, bottom: 56, top: 40 },
    xAxis: { type: 'category', data: labels },
    yAxis: { type: 'value', name: '℃' },
    series: [
      { 
        name: '本期', 
        type: 'line', 
        smooth: true, 
        data: labels.map(l => safeNumber(temperatureMainMap.value[l])), 
        label: { 
          show: true, 
          position: 'top',
          formatter: (p) => safeNumber(p.value) !== null ? p.value.toFixed(1) : ''
        }, 
        markLine: { 
          symbol: 'none', 
          lineStyle: { type: 'dashed', color: 'rgba(37, 99, 235, 0.32)' }, 
          label: { show: false },
          data: [{ xAxis: biz }] 
        } 
      },
      { 
        name: '同期', 
        type: 'line', 
        smooth: true, 
        data: labels.map(l => safeNumber(temperaturePeerMap.value[l])), 
        label: { 
          show: true, 
          position: 'bottom',
          formatter: (p) => safeNumber(p.value) !== null ? p.value.toFixed(1) : ''
        } 
      }
    ]
  }
})

const debugInfoText = computed(() => JSON.stringify({ projectKey: projectKey.value, selectedDate: selectedDate.value, availableDates: availableDates.value, temperature: { windowDates: temperatureWindowDates.value } }, null, 2))

function formatMetric(v, u, d = 2) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '—'
  return `${Number(v).toLocaleString('zh-CN', { minimumFractionDigits: d, maximumFractionDigits: d })}${u ? ` ${u}` : ''}`
}

function formatIncrement(v, u = '', d = 2) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '(—)'
  const n = Object.is(Number(v), -0) ? 0 : Number(v)
  return `(${n >= 0 ? '+' : ''}${n.toLocaleString('zh-CN', { minimumFractionDigits: d, maximumFractionDigits: d })}${u})`
}

function buildDailyAverageMap(b) {
  const m = {}
  Object.entries(b || {}).forEach(([d, v]) => {
    const s = Array.isArray(v) ? v : [v]
    const nums = s.map(i => (i && typeof i === 'object') ? Number(i.avg || i.average || i.value) : Number(i)).filter(Number.isFinite)
    if (nums.length) m[d] = nums.reduce((a, b) => a + b, 0) / nums.length
  })
  return m
}

function resolveSectionByIndex(s, idx, ...keys) {
  const m = {}
  Object.keys(s || {}).forEach(k => { const mt = String(k).match(/^(\d+)\./); if (mt) m[mt[1]] = k })
  const k = m[String(idx)] || String(idx)
  if (s?.[k]) return s[k]
  for (const l of keys) if (s?.[l]) return s[l]
  return {}
}

async function loadTemperatureFromDatabase() {
  if (!selectedDate.value) return
  const p = await getTemperatureTrendByDate(selectedDate.value)
  const sec = resolveSectionByIndex(p?.data?.sections || p?.sections || p?.data || {}, '1', '逐小时气温')
  temperatureMainMap.value = normalizeMapKeys(buildDailyAverageMap(sec['本期']))
  const peerRaw = normalizeMapKeys(buildDailyAverageMap(sec['同期']))
  const mapped = {}
  Object.entries(peerRaw).forEach(([d, v]) => {
    const dt = new Date(d); if (!Number.isNaN(dt.getTime())) { dt.setFullYear(dt.getFullYear() + 1); mapped[normalizeDateLabel(dt)] = v }
  })
  temperaturePeerMap.value = mapped
}

function normalizeDateLabel(t) { const d = new Date(String(t || '').trim()); if (Number.isNaN(d.getTime())) return String(t || ''); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` }
function parseDateKey(t) { const n = normalizeDateLabel(t); const d = new Date(`${n}T00:00:00`); return Number.isNaN(d.getTime()) ? null : d }
function formatDateKey(d) { return (d instanceof Date && !Number.isNaN(d.getTime())) ? `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` : '' }
function addDays(d, o) { const r = new Date(d); r.setDate(r.getDate() + o); return r }

function getBeijingYesterdayDateKey() {
  const now = new Date()
  const [y, m, d] = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai' }).format(now).split('-').map(Number)
  const yest = addDays(new Date(Date.UTC(y, m - 1, d)), -1)
  return `${yest.getUTCFullYear()}-${String(yest.getUTCMonth() + 1).padStart(2, '0')}-${String(yest.getUTCDate()).padStart(2, '0')}`
}

function pickDefaultSelectedDate(dates) {
  const s = [...new Set((dates || []).map(normalizeDateLabel))].sort()
  if (!s.length) return ''
  const y = getBeijingYesterdayDateKey()
  if (s.includes(y)) return y
  const t = parseDateKey(y).getTime()
  let n = s[0], dist = Infinity
  s.forEach(i => { const d = Math.abs(parseDateKey(i).getTime() - t); if (d < dist) { dist = d; n = i } })
  return n
}

function normalizeMapKeys(raw) { const m = {}; Object.entries(raw || {}).forEach(([k, v]) => m[normalizeDateLabel(k)] = v); return m }

onMounted(async () => {
  chartLibraryReady.value = Boolean(window.echarts)
  await ensureProjectsLoaded().catch(() => {})
  const cached = localStorage.getItem(THEME_STORAGE_KEY)
  if (cached === 'default' || cached === 'festival') themeMode.value = cached
  extractedPayload.value = getLatestExtractedPayload() || JSON.parse(sessionStorage.getItem(storageKey.value) || localStorage.getItem(storageKey.value) || 'null')
  if (!extractedPayload.value) { const r = await getLatestExtractedJson(projectKey.value); if (r?.ok) extractedPayload.value = r.payload }
})

async function downloadDashboardPdf() {
  const target = dashboardCaptureRef.value
  if (!target || !window.html2canvas || !window.jspdf) return
  downloadingPdf.value = true
  try {
    const canvas = await window.html2canvas(target, { scale: 3, useCORS: true, backgroundColor: '#f5f7fb', onclone: (cloned) => { const b = Array.from(cloned.querySelectorAll('.toolbar .btn')).find(i => i.textContent.includes('下载PDF')); if (b) b.style.display = 'none' } })
    const imgData = canvas.toDataURL('image/jpeg', 0.95)
    const pdf = new window.jspdf.jsPDF({ orientation: 'p', unit: 'mm', format: [210, (canvas.height * (210 - 12)) / canvas.width + 12] })
    pdf.addImage(imgData, 'JPEG', 6, 6, 210 - 12, (canvas.height * (210 - 12)) / canvas.width)
    pdf.save(`春节数据看板_${selectedDate.value}.pdf`)
  } finally { downloadingPdf.value = false }
}

function goBackToEntry() { router.push(`/projects/${encodeURIComponent(projectKey.value)}`) }

watch(() => availableDates.value, (d) => { if (d.length && (!selectedDate.value || !d.includes(selectedDate.value))) selectedDate.value = pickDefaultSelectedDate(d) }, { immediate: true })
watch(() => selectedDate.value, async (v) => { if (v) { loading.value = true; try { await loadTemperatureFromDatabase() } finally { loading.value = false } } }, { immediate: true })
watch(() => themeMode.value, (v) => localStorage.setItem(THEME_STORAGE_KEY, v))
</script>

<style scoped>
.spring-dashboard-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px 0 24px;
  width: 100%;
}

.spring-dashboard-page--default {
  background: #f3f6fb;
}

/* ============================================================ */
/* 全局基础布局骨架（确保宽度与间距） */
/* ============================================================ */

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  width: 100%;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-radius: 14px;
  color: #ffffff;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.14);
  padding: 16px;
}

.summary-card__label { font-size: 13px; color: rgba(255, 255, 255, 0.86); }
.summary-card__value { font-size: 24px; font-weight: 600; }
.summary-card__delta-inline { margin-left: 8px; font-size: 16px; font-weight: 500; }

.summary-card--primary { background: linear-gradient(135deg, #2563eb, #60a5fa); }
.summary-card--success { background: linear-gradient(135deg, #10b981, #34d399); }
.summary-card--warning { background: linear-gradient(135deg, #f59e0b, #fbbf24); }
.summary-card--danger { background: linear-gradient(135deg, #ef4444, #fb7185); }

.content-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
  width: 100%;
}

.complaint-dual-charts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  width: 100%;
  margin-bottom: 12px;
}

.mini-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
}

.table-scroll {
  width: 100%;
  overflow-x: auto;
}

.mini-table th, .mini-table td {
  border: 1px solid #e4e7ec;
  padding: 8px 10px;
  font-size: 12px;
  text-align: center;
}

.mini-table th { background: #f8fafc; }

.toolbar { display: flex; gap: 12px; align-items: center; margin-top: 12px; }
.toolbar-label { display: inline-flex; gap: 8px; align-items: center; font-size: 14px; }
.date-select, .theme-select { padding: 6px 10px; border: 1px solid #d0d7de; border-radius: 8px; }

/* 业务组件通用样式 */
.device-combo-cell { display: inline-flex; flex-direction: column; align-items: center; gap: 4px; }
.combo-item { display: flex; align-items: center; justify-content: space-between; gap: 4px; min-width: 56px; line-height: 1; }
.combo-label { display: inline-flex; align-items: center; justify-content: center; min-width: 16px; height: 16px; padding: 0 4px; border-radius: 8px; font-size: 10px; font-weight: 600; }
.combo-value { display: inline-flex; align-items: center; gap: 2px; font-size: 12px; font-weight: 600; }
.combo-sep { color: #64748b; }

/* ============================================================ */
/* 春节模式视觉增强 (festival) - 严格隔离 */
/* ============================================================ */

.spring-dashboard-page--festival {
  min-height: 100vh;
  background-color: #991b1b;
  background-image: 
    radial-gradient(circle at 50% 50%, rgba(220, 38, 38, 0.5), transparent 80%),
    linear-gradient(135deg, #7f1d1d 0%, #450a0a 100%);
  background-attachment: fixed;
  position: relative;
  overflow-x: hidden;
}

.festival-background-overlay {
  position: fixed;
  inset: 0;
  opacity: 0.15;
  pointer-events: none;
  z-index: 0;
  /* 使用真实图片素材 */
  background-image: url("/images/festival-pattern.jpg");
  background-repeat: repeat;
  background-size: 360px; /* 适当放大以展示纹理细节 */
  mix-blend-mode: overlay; /* 让纹理叠在红色背景上 */
  filter: sepia(1) saturate(2) hue-rotate(5deg); /* 微调图片色调偏金 */
}

.festival-decorations { position: fixed; inset: 0; pointer-events: none; z-index: 10; }
.festival-side-ornament { position: absolute; top: 100px; font-size: 48px; animation: ornament-sway 4s ease-in-out infinite alternate; }
.festival-side-ornament--left { left: 20px; }
.festival-side-ornament--right { right: 20px; animation-delay: -2s; }

@keyframes ornament-sway { from { transform: rotate(-3deg); } to { transform: rotate(3deg); } }

.festival-lantern-group { position: absolute; top: 60px; left: 10%; display: flex; gap: 30px; }
.festival-lantern { font-size: 32px; animation: lantern-sway 3s ease-in-out infinite alternate; transform-origin: top center; }
@keyframes lantern-sway { from { transform: rotate(-5deg); } to { transform: rotate(5deg); } }

.festival-title-wrapper { position: absolute; top: 72px; left: 50%; transform: translateX(-50%); display: flex; align-items: center; flex-direction: column; }
.festival-scroll-decor { width: 320px; height: 50px; background: #b91c1c; border: 2px solid #d4af37; border-radius: 25px / 10px; position: absolute; z-index: -1; }
.festival-title-mark { color: #fde68a; font-size: 16px; font-weight: 900; padding: 12px 40px; text-shadow: 1px 1px 3px rgba(0,0,0,0.5); letter-spacing: 2px; }

.spring-dashboard-page--festival .spring-dashboard-main { position: relative; z-index: 5; }

/* 春节模式卡片皮肤 */
.spring-dashboard-page--festival .card:not(.summary-card) {
  background: #fffdf9;
  border: 1px solid #d4af37;
  box-shadow: 0 8px 30px rgba(69, 10, 10, 0.2);
}

.spring-dashboard-page--festival .card-header h2,
.spring-dashboard-page--festival .card-header h3 { color: #991b1b; }

.spring-dashboard-page--festival .mini-table th { background: #991b1b; color: #fde68a; border-color: #d4af37; }
.spring-dashboard-page--festival .mini-table td { border-color: #fde68a; background: #fff; }

.spring-dashboard-page--festival .summary-card { border: 1px solid rgba(255, 255, 255, 0.4); }
.spring-dashboard-page--festival .summary-card--primary { background: linear-gradient(135deg, #991b1b, #ef4444); }
.spring-dashboard-page--festival .summary-card--success { background: linear-gradient(135deg, #065f46, #10b981); }
.spring-dashboard-page--festival .summary-card--warning { background: linear-gradient(135deg, #92400e, #f59e0b); }
.spring-dashboard-page--festival .summary-card--danger { background: linear-gradient(135deg, #7f1d1d, #f43f5e); }

@media (max-width: 1440px) {
  .summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 768px) {
  .summary-grid { grid-template-columns: 1fr; }
  .complaint-dual-charts { grid-template-columns: 1fr; }
  .festival-side-ornament { display: none; }
}
</style>
