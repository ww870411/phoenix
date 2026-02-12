<template>
  <div :class="['spring-dashboard-page', `spring-dashboard-page--${themeMode}`]">
    <AppHeader />
    <div v-if="themeMode === 'festival'" class="festival-ornaments" aria-hidden="true">
      <span class="festival-lantern festival-lantern--left">🏮</span>
      <span class="festival-title-mark">福启新岁</span>
      <span class="festival-lantern festival-lantern--right">🏮</span>
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
            <h3>投诉量分项（图与表）</h3>
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
  { label: '简化数据看板', to: null },
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
    const hasValue =
      payload.current !== null && payload.current !== undefined &&
      payload.prior !== null && payload.prior !== undefined
    if (hasValue || payload.diff !== null && payload.diff !== undefined) {
      return { scopeName, metricName: matched.metricName, payload }
    }
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
  return {
    current,
    prior,
    delta: computeIncrement(current, prior),
  }
})

const totalComplaintCard = computed(() => {
  const matched = findMetricMatchAcrossScopes(
    selectedDateBucket.value,
    (name) => name.includes('总投诉量'),
  )
  const payload = matched.payload || {}
  const current = safeNumber(payload?.current)
  const prior = safeNumber(payload?.prior)
  return {
    current,
    prior,
    delta: computeIncrement(current, prior),
  }
})

const netComplaintCard = computed(() => {
  const matched = findMetricMatchAcrossScopes(
    selectedDateBucket.value,
    (name) => name.includes('净投诉量'),
  )
  const payload = matched.payload || {}
  const current = safeNumber(payload?.current)
  const prior = safeNumber(payload?.prior)
  return {
    current,
    prior,
    delta: computeIncrement(current, prior),
  }
})

const tempCard = computed(() => {
  const main = safeNumber(temperatureMainMap.value?.[selectedDate.value])
  const peer = safeNumber(temperaturePeerMap.value?.[selectedDate.value])
  const delta = (main !== null && peer !== null) ? (main - peer) : null
  return { current: main, prior: peer, delta }
})

const temperatureWindowDates = computed(() => {
  const baseDate = parseDateKey(selectedDate.value)
  if (!baseDate) {
    return Array.from(
      new Set([
        ...Object.keys(temperatureMainMap.value || {}),
        ...Object.keys(temperaturePeerMap.value || {}),
      ]),
    ).sort()
  }
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
    const matchedCurrent = findMetricPayload(
      scopeBucket,
      (name) => name.includes('原煤消耗量'),
    )
    const matchedPrior =
      scope.label === '庄河'
        ? (findMetricPayload(
            scopeBucket,
            (name) => name.includes('其中：张屯原煤消耗量') || (name.includes('其中') && name.includes('张屯原煤消耗量')),
          ) || matchedCurrent)
        : matchedCurrent
    const currentPayload = matchedCurrent?.payload || {}
    const priorPayload = matchedPrior?.payload || {}
    return {
      scope: scope.label,
      current: safeNumber(currentPayload?.current),
      prior: safeNumber(priorPayload?.prior),
    }
  })
})

function resolveCoalMetricByScope(dateBucket, scopeConfig) {
  const scopeBucket = pickScopeBucket(dateBucket, scopeConfig.candidates || [])
  const matchedCurrent = findMetricPayload(scopeBucket, (name) => name.includes('原煤消耗量'))
  const matchedPrior =
    scopeConfig.useZhangtunPrior
      ? (findMetricPayload(
          scopeBucket,
          (name) => name.includes('其中：张屯原煤消耗量') || (name.includes('其中') && name.includes('张屯原煤消耗量')),
        ) || matchedCurrent)
      : matchedCurrent
  return {
    current: safeNumber(matchedCurrent?.payload?.current),
    prior: safeNumber(matchedPrior?.payload?.prior),
  }
}

const coalRows = computed(() =>
  availableDates.value.map((date) => {
    const normalizedDate = normalizeDateLabel(date)
    const dateBucket = extractedPayload.value?.byDate?.[normalizedDate] || extractedPayload.value?.byDate?.[date] || {}
    const metricMap = {}
    COAL_SCOPE_CONFIGS.forEach((scope) => {
      metricMap[scope.key] = resolveCoalMetricByScope(dateBucket, scope)
    })
    return {
      date: normalizedDate,
      temperature: safeNumber(temperatureMainMap.value?.[normalizedDate]),
      groupCurrent: metricMap.group?.current ?? null,
      groupPrior: metricMap.group?.prior ?? null,
      mainCityCurrent: metricMap.mainCity?.current ?? null,
      mainCityPrior: metricMap.mainCity?.prior ?? null,
      jinzhouCurrent: metricMap.jinzhou?.current ?? null,
      jinzhouPrior: metricMap.jinzhou?.prior ?? null,
      beifangCurrent: metricMap.beifang?.current ?? null,
      beifangPrior: metricMap.beifang?.prior ?? null,
      jinpuCurrent: metricMap.jinpu?.current ?? null,
      jinpuPrior: metricMap.jinpu?.prior ?? null,
      zhuangheCurrent: metricMap.zhuanghe?.current ?? null,
      zhuanghePrior: metricMap.zhuanghe?.prior ?? null,
    }
  }),
)

const coalVisibleRows = computed(() =>
  coalRows.value.filter((row) => shouldShowActualByBizDate(row.date)),
)

const coalTrendOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    formatter(params) {
      const rows = Array.isArray(params) ? params : []
      const axis = rows[0]?.axisValue || ''
      const current = rows.find((item) => item?.seriesName === '本期')
      const prior = rows.find((item) => item?.seriesName === '同期')
      const currentValue = safeNumber(current?.value)
      const priorValue = safeNumber(prior?.value)
      const currentText = Number.isFinite(currentValue)
        ? currentValue.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
        : '—'
      const priorText = Number.isFinite(priorValue)
        ? priorValue.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
        : '—'
      return `${axis}<br/>本期：${currentText} 吨<br/>同期：${priorText} 吨`
    },
  },
  legend: { top: 0 },
  grid: { left: 50, right: 20, bottom: 48, top: 28 },
  xAxis: {
    type: 'category',
    data: coalScopeRows.value.map((item) => item.scope),
    axisLabel: { margin: 12 },
  },
  yAxis: { type: 'value', name: '吨' },
  series: [
    {
      name: '本期',
      type: 'bar',
      barMaxWidth: 26,
      itemStyle: { color: '#1d4ed8' },
      data: coalScopeRows.value.map((item) => item.current),
      label: {
        show: true,
        position: 'top',
        color: '#1f2937',
        fontSize: 11,
        formatter(params) {
          const value = safeNumber(params?.value)
          if (!Number.isFinite(value)) return '—'
          return value.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
        },
      },
      labelLayout: { hideOverlap: true, moveOverlap: 'shiftY' },
    },
    {
      name: '同期',
      type: 'bar',
      barMaxWidth: 26,
      itemStyle: { color: '#f59e0b' },
      data: coalScopeRows.value.map((item) => item.prior),
      label: {
        show: true,
        position: 'top',
        color: '#334155',
        fontSize: 11,
        formatter(params) {
          const value = safeNumber(params?.value)
          if (!Number.isFinite(value)) return '—'
          return value.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
        },
      },
      labelLayout: { hideOverlap: true, moveOverlap: 'shiftY' },
    },
  ],
}))

const complaintRows = computed(() =>
  availableDates.value.map((date) => {
    const bucket = extractedPayload.value?.byDate?.[date] || {}
    const total = findMetricMatchAcrossScopes(bucket, (name) => name.includes('总投诉量')).payload || {}
    const net = findMetricMatchAcrossScopes(bucket, (name) => name.includes('净投诉量')).payload || {}
    const temperature = safeNumber(temperatureMainMap.value?.[normalizeDateLabel(date)])
    return {
      date,
      temperature,
      totalCurrent: safeNumber(total?.current),
      netCurrent: safeNumber(net?.current),
      totalPrior: safeNumber(total?.prior),
      netPrior: safeNumber(net?.prior),
    }
  }),
)

function sumFiniteNumbers(values) {
  const numbers = values.filter((item) => Number.isFinite(item))
  if (!numbers.length) return null
  return numbers.reduce((sum, item) => sum + Number(item), 0)
}

function resolveScopeMetricValuesByConfig(dateBucket, scopeConfig, metricMatcher) {
  if (Array.isArray(scopeConfig.aggregateCandidates) && scopeConfig.aggregateCandidates.length) {
    const currentValues = []
    const priorValues = []
    scopeConfig.aggregateCandidates.forEach((groupCandidates) => {
      const scopeBucket = pickScopeBucket(dateBucket, groupCandidates || [])
      const matched = findMetricPayload(scopeBucket, metricMatcher)
      currentValues.push(safeNumber(matched?.payload?.current))
      priorValues.push(safeNumber(matched?.payload?.prior))
    })
    return {
      current: sumFiniteNumbers(currentValues),
      prior: sumFiniteNumbers(priorValues),
    }
  }
  const scopeBucket = pickScopeBucket(dateBucket, scopeConfig.candidates || [])
  const matched = findMetricPayload(scopeBucket, metricMatcher)
  return {
    current: safeNumber(matched?.payload?.current),
    prior: safeNumber(matched?.payload?.prior),
  }
}

const deviceStatusRows = computed(() => {
  const dateBucket = selectedDateBucket.value || {}
  const buildComboItem = (label, color, current, prior) => ({
    label,
    color,
    current: Number.isFinite(current) ? current : 0,
    prior: Number.isFinite(prior) ? prior : 0,
  })
  const keepActiveItems = (items) =>
    items.filter((item) => !(Number(item.current) <= 0 && Number(item.prior) <= 0))

  return DEVICE_SCOPE_CONFIGS.map((scopeConfig) => {
    const steamBoiler = resolveScopeMetricValuesByConfig(dateBucket, scopeConfig, (name) => name.includes('运行汽炉数'))
    const turbine = resolveScopeMetricValuesByConfig(dateBucket, scopeConfig, (name) => name.includes('运行汽轮机数'))
    const waterBoiler = resolveScopeMetricValuesByConfig(dateBucket, scopeConfig, (name) => name.includes('运行水炉数'))
    const houseBoiler = resolveScopeMetricValuesByConfig(
      dateBucket,
      scopeConfig,
      (name) => name.includes('运行锅炉房锅炉数') || name.includes('运行燃煤锅炉房锅炉数'),
    )
    return {
      scope: scopeConfig.label,
      steamGroup: keepActiveItems([
        buildComboItem('炉', '#f97316', steamBoiler.current, steamBoiler.prior),
        buildComboItem('机', '#3b82f6', turbine.current, turbine.prior),
      ]),
      waterGroup: keepActiveItems([
        buildComboItem('水', '#06b6d4', waterBoiler.current, waterBoiler.prior),
      ]),
      houseGroup: keepActiveItems([
        buildComboItem('锅', '#8b5cf6', houseBoiler.current, houseBoiler.prior),
      ]),
    }
  })
})

function shouldShowActualByBizDate(dateText) {
  const rowDate = parseDateKey(dateText)
  const bizDate = parseDateKey(selectedDate.value)
  if (!rowDate || !bizDate) return true
  return rowDate.getTime() <= bizDate.getTime()
}

const complaintVisibleRows = computed(() =>
  complaintRows.value.filter((row) => shouldShowActualByBizDate(row.date)),
)

const complaintRowsByDate = computed(() => {
  const map = {}
  complaintRows.value.forEach((row) => {
    map[normalizeDateLabel(row.date)] = row
  })
  return map
})

const complaintChartAxisDates = computed(() => {
  const base = Array.isArray(availableDates.value) && availableDates.value.length
    ? availableDates.value
    : complaintRows.value.map((row) => row.date)
  return [...new Set(base.map((item) => normalizeDateLabel(item)))].sort()
})

function formatAxisMonthDay(dateText) {
  const normalized = normalizeDateLabel(dateText)
  const parts = normalized.split('-')
  if (parts.length !== 3) return normalized
  return `${parts[1]}-${parts[2]}`
}

const complaintTotalTrendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { top: 0, type: 'scroll', textStyle: { fontSize: 11 } },
  grid: { left: 40, right: 36, bottom: 40, top: 44 },
  xAxis: {
    type: 'category',
    data: complaintChartAxisDates.value,
    axisTick: { show: false },
    axisLabel: {
      hideOverlap: true,
      margin: 10,
      formatter(value) {
        return formatAxisMonthDay(value)
      },
    },
  },
  yAxis: [
    { type: 'value', name: '件', splitLine: { show: false } },
    { type: 'value', name: '℃', splitLine: { show: false } },
  ],
  series: [
    {
      name: '总投诉量（本期）',
      type: 'bar',
      itemStyle: { color: '#60a5fa' },
      barMaxWidth: 22,
      barCategoryGap: '42%',
      barGap: '28%',
      data: complaintChartAxisDates.value.map((date) => {
        const row = complaintRowsByDate.value[date]
        if (!row || !shouldShowActualByBizDate(date)) return null
        return row.totalCurrent
      }),
      label: { show: true, position: 'top' },
      labelLayout: { hideOverlap: true, moveOverlap: 'shiftY' },
    },
    {
      name: '总投诉量（同期）',
      type: 'bar',
      itemStyle: { color: '#fbbf24' },
      barMaxWidth: 22,
      barCategoryGap: '42%',
      barGap: '28%',
      data: complaintChartAxisDates.value.map((date) => {
        const row = complaintRowsByDate.value[date]
        if (!row || !shouldShowActualByBizDate(date)) return null
        return row.totalPrior
      }),
      label: { show: true, position: 'top' },
      labelLayout: { hideOverlap: true, moveOverlap: 'shiftY' },
    },
    {
      name: '本期气温',
      type: 'line',
      yAxisIndex: 1,
      smooth: true,
      itemStyle: { color: '#22c55e' },
      data: complaintChartAxisDates.value.map((date) => {
        const row = complaintRowsByDate.value[date]
        if (!row || !shouldShowActualByBizDate(date)) return null
        return row.temperature
      }),
    },
  ],
}))

const complaintNetTrendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { top: 0, type: 'scroll', textStyle: { fontSize: 11 } },
  grid: { left: 40, right: 36, bottom: 40, top: 44 },
  xAxis: {
    type: 'category',
    data: complaintChartAxisDates.value,
    axisTick: { show: false },
    axisLabel: {
      hideOverlap: true,
      margin: 10,
      formatter(value) {
        return formatAxisMonthDay(value)
      },
    },
  },
  yAxis: [
    { type: 'value', name: '件', splitLine: { show: false } },
    { type: 'value', name: '℃', splitLine: { show: false } },
  ],
  series: [
    {
      name: '净投诉量（本期）',
      type: 'bar',
      itemStyle: { color: '#60a5fa' },
      barMaxWidth: 22,
      barCategoryGap: '42%',
      barGap: '28%',
      data: complaintChartAxisDates.value.map((date) => {
        const row = complaintRowsByDate.value[date]
        if (!row || !shouldShowActualByBizDate(date)) return null
        return row.netCurrent
      }),
      label: { show: true, position: 'top' },
      labelLayout: { hideOverlap: true, moveOverlap: 'shiftY' },
    },
    {
      name: '净投诉量（同期）',
      type: 'bar',
      itemStyle: { color: '#fbbf24' },
      barMaxWidth: 22,
      barCategoryGap: '42%',
      barGap: '28%',
      data: complaintChartAxisDates.value.map((date) => {
        const row = complaintRowsByDate.value[date]
        if (!row || !shouldShowActualByBizDate(date)) return null
        return row.netPrior
      }),
      label: { show: true, position: 'top' },
      labelLayout: { hideOverlap: true, moveOverlap: 'shiftY' },
    },
    {
      name: '本期气温',
      type: 'line',
      yAxisIndex: 1,
      smooth: true,
      itemStyle: { color: '#22c55e' },
      data: complaintChartAxisDates.value.map((date) => {
        const row = complaintRowsByDate.value[date]
        if (!row || !shouldShowActualByBizDate(date)) return null
        return row.temperature
      }),
    },
  ],
}))

const temperatureTrendOption = computed(() => {
  const labels = temperatureWindowDates.value
  const selectedLabel = normalizeDateLabel(selectedDate.value)
  const toFixedText = (value) => (Number.isFinite(value) ? Number(value).toFixed(1) : '—')
  return {
    tooltip: {
      trigger: 'axis',
      formatter(params) {
        const rows = Array.isArray(params) ? params : []
        const axisLabel = rows[0]?.axisValue || selectedLabel
        const lines = rows.map((item) => {
          const value = Array.isArray(item?.value) ? item.value[1] : item?.value
          return `${item?.marker || ''}${item?.seriesName || ''}：${toFixedText(Number(value))}℃`
        })
        return [`${axisLabel}`, ...lines].join('<br/>')
      },
    },
    legend: { top: 0 },
    grid: { left: 40, right: 20, bottom: 56, top: 40 },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: { margin: 14 },
    },
    yAxis: { type: 'value', name: '℃' },
    series: [
      {
        name: '本期',
        type: 'line',
        smooth: true,
        data: labels.map((item) => safeNumber(temperatureMainMap.value[item])),
        label: {
          show: true,
          position: 'top',
          distance: 6,
          fontSize: 11,
          color: '#1f2937',
          formatter(params) {
            const value = Array.isArray(params?.value) ? params.value[1] : params?.value
            return `${toFixedText(Number(value))}℃`
          },
        },
        labelLayout: { hideOverlap: true, moveOverlap: 'shiftY' },
        markLine: selectedLabel
          ? {
              symbol: 'none',
              lineStyle: { type: 'dashed', color: 'rgba(37, 99, 235, 0.32)', width: 1.5 },
              label: { show: false },
              data: [{ xAxis: selectedLabel }],
            }
          : undefined,
      },
      {
        name: '同期',
        type: 'line',
        smooth: true,
        data: labels.map((item) => safeNumber(temperaturePeerMap.value[item])),
        label: {
          show: true,
          position: 'bottom',
          distance: 8,
          fontSize: 11,
          color: '#1f2937',
          formatter(params) {
            const value = Array.isArray(params?.value) ? params.value[1] : params?.value
            return `${toFixedText(Number(value))}℃`
          },
        },
        labelLayout: { hideOverlap: true, moveOverlap: 'shiftY' },
      },
    ],
  }
})

const debugInfoText = computed(() => {
  const bucket = selectedDateBucket.value || {}
  const scopes = Object.keys(bucket)
  const coalMatch = findMetricMatchAcrossScopes(
    bucket,
    (name) => name.includes('原煤消耗量') && name.includes('剔除庄河改造'),
  )
  const totalMatch = findMetricMatchAcrossScopes(bucket, (name) => name.includes('总投诉量'))
  const netMatch = findMetricMatchAcrossScopes(bucket, (name) => name.includes('净投诉量'))
  const data = {
    projectKey: projectKey.value,
    selectedDate: selectedDate.value,
    availableDates: availableDates.value,
    selectedDateScopeCount: scopes.length,
    selectedDateScopes: scopes,
    matched: {
      coal: coalMatch,
      totalComplaint: totalMatch,
      netComplaint: netMatch,
    },
    temperature: {
      mainDateCount: Object.keys(temperatureMainMap.value || {}).length,
      peerDateCount: Object.keys(temperaturePeerMap.value || {}).length,
      windowDates: temperatureWindowDates.value,
      selectedMain: temperatureMainMap.value?.[selectedDate.value] ?? null,
      selectedPeer: temperaturePeerMap.value?.[selectedDate.value] ?? null,
    },
    payloadMeta: extractedPayload.value?.meta || null,
  }
  return JSON.stringify(data, null, 2)
})

function formatMetric(value, unit, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  const number = Number(value)
  return `${number.toLocaleString('zh-CN', { minimumFractionDigits: digits, maximumFractionDigits: digits })}${unit ? ` ${unit}` : ''}`
}

function formatIncrement(value, unit = '', digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '(—)'
  const number = Number(value)
  const normalizedNumber = Object.is(number, -0) ? 0 : number
  const sign = normalizedNumber >= 0 ? '+' : ''
  return `(${sign}${normalizedNumber.toLocaleString('zh-CN', { minimumFractionDigits: digits, maximumFractionDigits: digits })}${unit ? unit : ''})`
}

function buildDailyAverageMap(bucket) {
  const map = {}
  for (const [date, values] of Object.entries(bucket || {})) {
    const source = Array.isArray(values)
      ? values
      : (values !== null && values !== undefined ? [values] : [])
    const numbers = source
      .map((item) => {
        if (item && typeof item === 'object') {
          if (item.avg !== undefined) return Number(item.avg)
          if (item.average !== undefined) return Number(item.average)
          if (item.value !== undefined) return Number(item.value)
        }
        return Number(item)
      })
      .filter((item) => Number.isFinite(item))
    if (!numbers.length) continue
    map[date] = numbers.reduce((sum, item) => sum + item, 0) / numbers.length
  }
  return map
}

function buildSectionIndexMap(sections) {
  const map = {}
  Object.keys(sections || {}).forEach((key) => {
    if (typeof key !== 'string') return
    const match = key.match(/^(\d+)\./)
    if (match && !map[match[1]]) {
      map[match[1]] = key
    }
  })
  return map
}

function resolveSectionByIndex(sections, index, ...legacyKeys) {
  const indexMap = buildSectionIndexMap(sections)
  const indexedKey = indexMap[String(index)]
  if (indexedKey && sections?.[indexedKey] && typeof sections[indexedKey] === 'object') {
    return sections[indexedKey]
  }
  for (const key of [String(index), ...legacyKeys]) {
    if (key && sections?.[key] && typeof sections[key] === 'object') {
      return sections[key]
    }
  }
  return {}
}

function resolveDashboardSections(payload) {
  const fromData = payload?.data
  if (fromData?.sections && typeof fromData.sections === 'object') {
    return fromData.sections
  }
  if (payload?.sections && typeof payload.sections === 'object') {
    return payload.sections
  }
  if (fromData && typeof fromData === 'object') {
    return fromData
  }
  return {}
}

function resolveTemperatureSection(payload) {
  const sections = resolveDashboardSections(payload)
  const section = resolveSectionByIndex(
    sections,
    '1',
    '1.逐小时气温',
    '逐小时气温',
    'calc_temperature_data',
  )
  if (section && typeof section === 'object' && (section['本期'] || section['同期'])) {
    return section
  }
  if (sections?.calc_temperature_data && typeof sections.calc_temperature_data === 'object') {
    return sections.calc_temperature_data
  }
  return {}
}

function normalizeDateLabel(dateText) {
  const date = new Date(String(dateText || '').trim())
  if (Number.isNaN(date.getTime())) return String(dateText || '')
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function parseDateKey(dateText) {
  const normalized = normalizeDateLabel(dateText)
  const date = new Date(`${normalized}T00:00:00`)
  if (Number.isNaN(date.getTime())) return null
  return date
}

function formatDateKey(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return ''
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function addDays(date, offsetDays) {
  const result = new Date(date)
  result.setDate(result.getDate() + offsetDays)
  return result
}

function getBeijingYesterdayDateKey() {
  const now = new Date()
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
  const [year, month, day] = formatter.format(now).split('-').map((item) => Number(item))
  const beijingMidnightUTC = new Date(Date.UTC(year, month - 1, day))
  const yesterdayUTC = addDays(beijingMidnightUTC, -1)
  return `${yesterdayUTC.getUTCFullYear()}-${String(yesterdayUTC.getUTCMonth() + 1).padStart(2, '0')}-${String(yesterdayUTC.getUTCDate()).padStart(2, '0')}`
}

function pickNearestDate(targetDate, candidates) {
  const target = parseDateKey(targetDate)
  if (!target) return null
  const targetTime = target.getTime()
  let nearest = null
  let nearestDistance = Number.POSITIVE_INFINITY
  candidates.forEach((item) => {
    const date = parseDateKey(item)
    if (!date) return
    const distance = Math.abs(date.getTime() - targetTime)
    if (distance < nearestDistance) {
      nearestDistance = distance
      nearest = formatDateKey(date)
    }
  })
  return nearest
}

function pickDefaultSelectedDate(dates) {
  const sortedDates = [...new Set((dates || []).map((item) => normalizeDateLabel(item)))].sort()
  if (!sortedDates.length) return ''
  const beijingYesterday = getBeijingYesterdayDateKey()
  if (sortedDates.includes(beijingYesterday)) {
    return beijingYesterday
  }
  return pickNearestDate(beijingYesterday, sortedDates) || sortedDates[sortedDates.length - 1]
}

function normalizeMapKeys(rawMap) {
  const map = {}
  Object.entries(rawMap || {}).forEach(([key, value]) => {
    map[normalizeDateLabel(key)] = value
  })
  return map
}

function mapPeerToCurrentYear(peerMap) {
  const map = {}
  Object.entries(peerMap || {}).forEach(([peerDate, value]) => {
    const mappedDate = safeMapPeerDateToCurrent(peerDate)
    map[normalizeDateLabel(mappedDate)] = value
  })
  return map
}

function ensurePeerCoverageByShift(mainMap, peerMap) {
  const result = { ...(peerMap || {}) }
  Object.keys(mainMap || {}).forEach((mainDate) => {
    if (result[mainDate] !== undefined) return
    const date = new Date(mainDate)
    if (Number.isNaN(date.getTime())) return
    date.setFullYear(date.getFullYear() - 1)
    const y = date.getFullYear()
    const m = String(date.getMonth() + 1).padStart(2, '0')
    const d = String(date.getDate()).padStart(2, '0')
    const peerDate = `${y}-${m}-${d}`
    if (peerMap?.[peerDate] !== undefined) {
      result[mainDate] = peerMap[peerDate]
    }
  })
  return result
}

async function loadTemperatureFromDatabase() {
  if (!selectedDate.value) return
  const payload = await getTemperatureTrendByDate(selectedDate.value)
  const tempSection = resolveTemperatureSection(payload)
  const mainBucket =
    tempSection && typeof tempSection === 'object' && typeof tempSection['本期'] === 'object'
      ? tempSection['本期']
      : {}
  const peerBucket =
    tempSection && typeof tempSection === 'object' && typeof tempSection['同期'] === 'object'
      ? tempSection['同期']
      : {}
  const normalizedMain = normalizeMapKeys(buildDailyAverageMap(mainBucket))
  const normalizedPeerRaw = normalizeMapKeys(buildDailyAverageMap(peerBucket))
  const mappedPeer = mapPeerToCurrentYear(normalizedPeerRaw)
  temperatureMainMap.value = normalizedMain
  temperaturePeerMap.value = ensurePeerCoverageByShift(normalizedMain, mappedPeer)
}

function safeMapPeerDateToCurrent(peerDate) {
  const parsed = new Date(peerDate)
  if (Number.isNaN(parsed.getTime())) return peerDate
  parsed.setFullYear(parsed.getFullYear() + 1)
  const y = parsed.getFullYear()
  const m = String(parsed.getMonth() + 1).padStart(2, '0')
  const d = String(parsed.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function loadPayloadFromStorage() {
  const fromMemory = getLatestExtractedPayload()
  if (fromMemory && typeof fromMemory === 'object') {
    extractedPayload.value = fromMemory
    return
  }
  const raw =
    sessionStorage.getItem(storageKey.value) ||
    localStorage.getItem(storageKey.value)
  if (!raw) {
    extractedPayload.value = null
    return
  }
  try {
    extractedPayload.value = JSON.parse(raw)
  } catch (error) {
    extractedPayload.value = null
    errorMessage.value = '本地缓存的 JSON 无法解析，请返回上传页重新生成。'
  }
}

function loadThemeModeFromStorage() {
  const cached = localStorage.getItem(THEME_STORAGE_KEY)
  if (cached === 'default' || cached === 'festival') {
    themeMode.value = cached
  }
}

async function loadPayloadFromBackend() {
  try {
    const response = await getLatestExtractedJson(projectKey.value)
    if (response?.ok && response?.payload && typeof response.payload === 'object') {
      extractedPayload.value = response.payload
      return true
    }
  } catch (error) {
    console.warn('读取后端最近提取数据失败', error)
  }
  return false
}

function isValidByDatePayload(payload) {
  return Boolean(
    payload &&
    typeof payload === 'object' &&
    payload.byDate &&
    typeof payload.byDate === 'object' &&
    Object.keys(payload.byDate).length > 0,
  )
}

function goBackToEntry() {
  router.push(`/projects/${encodeURIComponent(projectKey.value)}`)
}

async function downloadDashboardPdf() {
  if (downloadingPdf.value) return
  const target = dashboardCaptureRef.value
  if (!target) {
    errorMessage.value = '未找到可导出的看板区域，请刷新页面后重试。'
    return
  }
  const html2canvasLib = window.html2canvas
  const jsPdfLib = window.jspdf?.jsPDF
  if (!html2canvasLib || !jsPdfLib) {
    errorMessage.value = 'PDF 导出依赖未加载完成，请刷新页面后重试。'
    return
  }
  downloadingPdf.value = true
  errorMessage.value = ''
  try {
    const canvas = await html2canvasLib(target, {
      scale: 3,
      useCORS: true,
      backgroundColor: '#f5f7fb',
      onclone: (clonedDocument) => {
        const buttons = Array.from(clonedDocument.querySelectorAll('.toolbar .btn'))
        const downloadBtn = buttons.find((item) => item.textContent?.includes('下载PDF'))
        if (downloadBtn) downloadBtn.style.display = 'none'
      },
    })
    const imageData = canvas.toDataURL('image/jpeg', 0.95)
    const imageWidth = canvas.width
    const imageHeight = canvas.height
    const pdfWidth = 210
    const pagePadding = 6
    const contentWidth = pdfWidth - pagePadding * 2
    const contentHeight = (imageHeight * contentWidth) / imageWidth
    const pdfHeight = contentHeight + pagePadding * 2
    const pdf = new jsPdfLib({
      orientation: 'p',
      unit: 'mm',
      format: [pdfWidth, pdfHeight],
    })
    pdf.addImage(imageData, 'JPEG', pagePadding, pagePadding, contentWidth, contentHeight)
    const datePart = selectedDate.value || new Date().toISOString().slice(0, 10)
    pdf.save(`春节简化数据看板_${datePart}.pdf`)
  } catch (error) {
    console.error(error)
    errorMessage.value = error instanceof Error ? error.message : 'PDF 生成失败，请稍后重试。'
  } finally {
    downloadingPdf.value = false
  }
}

watch(
  () => availableDates.value,
  (dates) => {
    if (!dates.length) return
    if (!selectedDate.value || !dates.includes(selectedDate.value)) {
      selectedDate.value = pickDefaultSelectedDate(dates)
    }
    const currentBucket = extractedPayload.value?.byDate?.[selectedDate.value]
    if (!currentBucket || !Object.keys(currentBucket).length) {
      const nonEmptyDates = dates.filter((date) => {
        const bucket = extractedPayload.value?.byDate?.[date]
        return bucket && Object.keys(bucket).length > 0
      })
      if (nonEmptyDates.length) {
        selectedDate.value = pickDefaultSelectedDate(nonEmptyDates)
      }
    }
  },
  { immediate: true },
)

watch(
  () => selectedDate.value,
  async (value) => {
    if (!value) return
    loading.value = true
    errorMessage.value = ''
    try {
      await loadTemperatureFromDatabase()
    } catch (error) {
      console.error(error)
      errorMessage.value = error instanceof Error ? error.message : '读取数据库气温失败'
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)

onMounted(async () => {
  if (projectKey.value !== TARGET_PROJECT_KEY) {
    router.replace(`/projects/${encodeURIComponent(projectKey.value)}/pages`)
    return
  }
  chartLibraryReady.value = Boolean(window.echarts)
  await ensureProjectsLoaded().catch(() => {})
  loadThemeModeFromStorage()
  loadPayloadFromStorage()
  if (!hasPayload.value) {
    await loadPayloadFromBackend()
  }
  if (extractedPayload.value && !isValidByDatePayload(extractedPayload.value)) {
    errorMessage.value = '当前数据格式不符合 mini 看板要求：需要包含 byDate 对象。'
  }
  if (!extractedPayload.value) {
    errorMessage.value = '未读取到提取结果，请先在上传页重新执行“上传并提取 JSON”。'
  }
  if (!chartLibraryReady.value) {
    errorMessage.value = '图表库未加载，请刷新页面后重试。'
  }
})

watch(
  () => themeMode.value,
  (value) => {
    if (value !== 'default' && value !== 'festival') return
    localStorage.setItem(THEME_STORAGE_KEY, value)
  },
)
</script>

<style scoped>
.spring-dashboard-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px 0 24px;
}

.spring-dashboard-page--default {
  background: #f3f6fb;
}

.spring-dashboard-page--festival {
  min-height: 100vh;
  background:
    radial-gradient(circle at 12% 14%, rgba(255, 234, 186, 0.42), transparent 24%),
    radial-gradient(circle at 86% 18%, rgba(255, 213, 128, 0.3), transparent 20%),
    radial-gradient(circle at 80% 80%, rgba(249, 115, 22, 0.18), transparent 22%),
    linear-gradient(165deg, #7f1d1d 0%, #9f1239 42%, #b91c1c 100%);
}

.spring-dashboard-page--festival .spring-dashboard-main {
  padding-bottom: 30px;
}

.festival-ornaments {
  position: fixed;
  top: 72px;
  left: 50%;
  transform: translateX(-50%);
  display: inline-flex;
  align-items: center;
  gap: 12px;
  z-index: 3;
  pointer-events: none;
}

.festival-title-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 92px;
  height: 30px;
  border-radius: 16px;
  padding: 0 14px;
  background: linear-gradient(180deg, #fde68a 0%, #f59e0b 100%);
  color: #7f1d1d;
  font-size: 13px;
  font-weight: 700;
  box-shadow: 0 6px 16px rgba(127, 29, 29, 0.28);
}

.festival-lantern {
  font-size: 20px;
  line-height: 1;
  filter: drop-shadow(0 3px 6px rgba(127, 29, 29, 0.36));
}

.spring-dashboard-page--festival .spring-dashboard-main::before {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background-image:
    linear-gradient(135deg, rgba(255, 255, 255, 0.06) 1px, transparent 1px),
    linear-gradient(45deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
  background-size: 28px 28px, 28px 28px;
}

.spring-dashboard-page--festival .spring-dashboard-main > * {
  position: relative;
  z-index: 1;
}

.sub {
  margin-top: 6px;
  color: var(--muted);
  font-size: 13px;
}

.state {
  font-size: 13px;
  color: var(--muted);
}

.state.error {
  color: #b42318;
}

.toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
}

.toolbar-label {
  display: inline-flex;
  gap: 8px;
  align-items: center;
}

.date-select {
  padding: 6px 8px;
  border: 1px solid #d0d7de;
  border-radius: 8px;
}

.theme-select {
  padding: 6px 8px;
  border: 1px solid #d0d7de;
  border-radius: 8px;
}

.spring-dashboard-page--festival .toolbar .btn {
  border-color: rgba(254, 243, 199, 0.55);
  background: linear-gradient(180deg, rgba(254, 243, 199, 0.95), rgba(253, 230, 138, 0.93));
  color: #7c2d12;
}

.spring-dashboard-page--festival .date-select,
.spring-dashboard-page--festival .theme-select {
  border-color: rgba(254, 243, 199, 0.72);
  background: rgba(255, 251, 235, 0.95);
  color: #7c2d12;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-radius: 14px;
  color: #ffffff;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.14);
}

.summary-card__label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.86);
}

.summary-card__value {
  font-size: 24px;
  font-weight: 600;
}

.summary-card__delta-inline {
  margin-left: 8px;
  font-size: 16px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.96);
}

.summary-card__delta {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.9);
}

.summary-card--primary {
  background: linear-gradient(135deg, #2563eb, #60a5fa);
}

.summary-card--success {
  background: linear-gradient(135deg, #10b981, #34d399);
}

.summary-card--warning {
  background: linear-gradient(135deg, #f59e0b, #fbbf24);
}

.summary-card--danger {
  background: linear-gradient(135deg, #ef4444, #fb7185);
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
}

.complaint-dual-charts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.complaint-chart-panel {
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  padding: 10px 10px 4px;
}

.complaint-chart-panel__title {
  font-size: 13px;
  color: #334155;
  margin-bottom: 6px;
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

.device-combo-cell {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.combo-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  min-width: 56px;
  line-height: 1;
}

.combo-label {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 600;
}

.combo-value {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 12px;
  font-weight: 600;
}

.combo-sep {
  color: #64748b;
}

.mini-table th,
.mini-table td {
  border: 1px solid #e4e7ec;
  padding: 8px 10px;
  font-size: 12px;
  text-align: center;
}

.mini-table th {
  background: #f8fafc;
}

.spring-dashboard-page--festival .card:not(.summary-card) {
  background: rgba(255, 252, 242, 0.95);
  border: 1px solid rgba(254, 215, 170, 0.55);
  box-shadow: 0 10px 24px rgba(69, 10, 10, 0.2);
}

.spring-dashboard-page--festival .card-header h2,
.spring-dashboard-page--festival .card-header h3 {
  color: #7f1d1d;
}

.spring-dashboard-page--festival .sub,
.spring-dashboard-page--festival .toolbar-label {
  color: #7c2d12;
}

.spring-dashboard-page--festival .mini-table th {
  background: linear-gradient(180deg, #fef3c7 0%, #fde68a 100%);
  color: #7c2d12;
}

.spring-dashboard-page--festival .mini-table td {
  background: rgba(255, 251, 235, 0.86);
}

.spring-dashboard-page--festival .summary-card {
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 10px 24px rgba(69, 10, 10, 0.26);
}

.spring-dashboard-page--festival .summary-card--primary {
  background: linear-gradient(135deg, #1d4ed8, #60a5fa);
}

.spring-dashboard-page--festival .summary-card--success {
  background: linear-gradient(135deg, #059669, #34d399);
}

.spring-dashboard-page--festival .summary-card--warning {
  background: linear-gradient(135deg, #d97706, #fbbf24);
}

.spring-dashboard-page--festival .summary-card--danger {
  background: linear-gradient(135deg, #dc2626, #fb7185);
}

.spring-dashboard-page--festival .summary-card__label {
  color: rgba(255, 255, 255, 0.92);
}

.spring-dashboard-page--festival .summary-card__value,
.spring-dashboard-page--festival .summary-card__delta-inline {
  color: #fff;
  text-shadow: 0 1px 2px rgba(15, 23, 42, 0.2);
}

@media (max-width: 1440px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .festival-ornaments {
    top: 66px;
    gap: 8px;
  }

  .festival-title-mark {
    min-width: 80px;
    height: 26px;
    font-size: 12px;
    padding: 0 10px;
  }

  .festival-lantern {
    font-size: 18px;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .complaint-dual-charts {
    grid-template-columns: 1fr;
  }
}
</style>
