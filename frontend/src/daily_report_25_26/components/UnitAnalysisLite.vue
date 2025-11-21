<template>
  <section class="analysis-lite card">
    <header class="analysis-lite__header">
      <div>
        <h3>本单位数据分析（仅当前单位）</h3>
        <p class="analysis-lite__hint">默认折叠，展开后按时间段生成汇总对比</p>
      </div>
      <div class="analysis-lite__actions">
        <button class="btn ghost" type="button" @click="toggleAnalysisFold">
          {{ analysisFolded ? '展开' : '收起' }}
        </button>
        <button
          class="btn ghost"
          type="button"
          :disabled="analysisResult.rows.length === 0"
          @click="downloadAnalysisExcel"
        >
          导出本单位汇总
        </button>
      </div>
    </header>

    <div v-if="analysisFolded" class="analysis-lite__fold-hint">
      点击“展开”即可针对当前单位（{{ unitLabel }}）按时间段生成汇总对比。
    </div>

    <div v-else class="analysis-lite__body">
      <div v-if="analysisSchemaLoading" class="page-state">分析配置加载中…</div>
      <div v-else-if="analysisSchemaError" class="page-state error">{{ analysisSchemaError }}</div>
      <template v-else>
        <div class="analysis-lite__form">
          <div class="analysis-lite__field">
            <label>时间范围（累计）</label>
            <div class="analysis-lite__dates">
              <input type="date" v-model="analysisStartDate" />
              <span>~</span>
              <input type="date" v-model="analysisEndDate" />
            </div>
          </div>
          <div class="analysis-lite__field">
            <div class="analysis-lite__field-header">
              <label>指标选择（多选）</label>
              <div class="analysis-lite__field-actions">
                <button class="btn ghost xs" type="button" @click="selectAllAnalysisMetrics">
                  全选
                </button>
                <button class="btn ghost xs" type="button" @click="clearAnalysisMetrics">
                  清空
                </button>
              </div>
            </div>
            <div v-if="analysisMetricGroups.length" class="analysis-lite__grid">
              <div
                v-for="group in analysisMetricGroups"
                :key="`metric-group-${group.key}`"
                class="analysis-lite__group-card"
              >
                <div class="analysis-lite__group-header">
                  <strong>{{ group.label || '指标' }}</strong>
                  <span class="analysis-lite__hint">共 {{ (group.options || []).length }} 项</span>
                </div>
                <div class="analysis-lite__metrics-grid">
                  <label
                    v-for="metric in group.options"
                    :key="`metric-${group.key}-${metric.value}`"
                    class="chip checkbox"
                  >
                    <input
                      type="checkbox"
                      :value="metric.value"
                      :checked="selectedMetricKeys.has(metric.value)"
                      @change="toggleAnalysisMetric(metric.value)"
                    />
                    <span class="chip-label">
                      <span v-if="getMetricSelectionOrder(metric.value)" class="chip-order">
                        {{ getMetricSelectionOrder(metric.value) }}
                      </span>
                      <span>{{ metric.label }}</span>
                    </span>
                  </label>
                </div>
              </div>
            </div>
            <div v-else-if="analysisMetricOptions.length" class="analysis-lite__metrics-grid">
              <label
                v-for="metric in analysisMetricOptions"
                :key="`metric-${metric.value}`"
                class="chip checkbox"
              >
                <input
                  type="checkbox"
                  :value="metric.value"
                  :checked="selectedMetricKeys.has(metric.value)"
                  @change="toggleAnalysisMetric(metric.value)"
                />
                <span class="chip-label">
                  <span v-if="getMetricSelectionOrder(metric.value)" class="chip-order">
                    {{ getMetricSelectionOrder(metric.value) }}
                  </span>
                  <span>{{ metric.label }}</span>
                </span>
              </label>
            </div>
            <p v-else class="analysis-lite__hint">暂无可选指标，请检查数据分析配置。</p>
          </div>
          <div class="analysis-lite__form-actions">
            <button class="btn primary" type="button" :disabled="analysisLoading" @click="runUnitAnalysis">
              {{ analysisLoading ? '生成中…' : '生成汇总对比' }}
            </button>
            <span class="analysis-lite__unit-label">当前单位：{{ unitLabel }}</span>
          </div>
        </div>

        <div v-if="analysisFormError" class="page-state error">{{ analysisFormError }}</div>
        <div v-else-if="analysisLoading" class="page-state">正在生成汇总，请稍候…</div>
        <div v-else-if="!analysisResult.rows.length" class="page-state muted">
          运行后将在此显示本单位的汇总对比结果。
        </div>
        <div v-else class="analysis-lite__result">
          <div v-if="analysisResult.warnings.length" class="analysis-lite__warnings">
            <strong>提示：</strong>
            <ul>
              <li v-for="(warn, i) in analysisResult.warnings" :key="`warn-${i}`">{{ warn }}</li>
            </ul>
          </div>
          <table class="analysis-lite__table">
            <colgroup>
              <col style="width: 32%" />
              <col style="width: 22%" />
              <col style="width: 22%" />
              <col style="width: 24%" />
            </colgroup>
            <thead>
              <tr>
                <th>指标</th>
                <th>本期</th>
                <th>同期</th>
                <th>同比</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in analysisResult.rows" :key="row.key">
                <td class="analysis-lite__metric">
                  {{ row.label }}
                  <span v-if="row.value_type === 'temperature'" class="tag tag--subtle">气温</span>
                  <span v-else-if="row.value_type === 'constant'" class="tag tag--subtle">常量</span>
                </td>
                <td>
                  <div class="analysis-lite__value">
                    <span class="analysis-lite__number">
                      {{ formatNumber(row.total_current ?? row.current, row.decimals || 2) }}
                    </span>
                    <span v-if="row.unit" class="analysis-lite__unit">{{ row.unit }}</span>
                  </div>
                </td>
                <td>
                  <div class="analysis-lite__value">
                    <span class="analysis-lite__number">
                      {{ formatNumber(row.total_peer ?? row.peer, row.decimals || 2) }}
                    </span>
                    <span v-if="row.unit" class="analysis-lite__unit">{{ row.unit }}</span>
                  </div>
                </td>
                <td :class="resolveDeltaClass(row)">
                  {{ formatDelta(resolveRowDelta(row)) }}
                </td>
              </tr>
            </tbody>
          </table>

          <section v-if="hasTimelineData" class="analysis-lite__timeline">
            <header class="analysis-lite__timeline-header">
              <div>
                <h3>区间明细（逐日）</h3>
                <p class="analysis-lite__hint">展示所选指标的逐日数据与趋势</p>
              </div>
            </header>
            <div v-if="analysisTimelineMetrics.length" class="analysis-lite__timeline-metrics">
              <button
                v-for="metric in analysisTimelineMetrics"
                :key="`timeline-chip-${metric.key}`"
                type="button"
                class="chip chip--toggle"
                :class="{ active: activeTimelineMetricKeys.includes(metric.key) }"
                @click="toggleTimelineMetric(metric.key)"
              >
                <span>{{ metric.label }}</span>
                <span v-if="metric.unit" class="chip-hint">（{{ metric.unit }}）</span>
              </button>
            </div>
            <div class="analysis-lite__timeline-grid">
              <RevoGrid
                class="timeline-grid"
                theme="material"
                :readonly="true"
                :columns="analysisTimelineGrid.columns"
                :source="analysisTimelineGrid.rows"
                :autoSizeColumn="true"
                :rowSize="30"
              />
            </div>
            <div class="analysis-lite__timeline-chart">
              <TrendChart v-if="timelineChartOption" :option="timelineChartOption" height="360px" />
              <div v-else class="page-state muted">请选择至少一个包含逐日数据的指标生成趋势图</div>
            </div>
          </section>
        </div>
      </template>
    </div>
  </section>
</template>

<script setup>
import RevoGrid from '@revolist/vue3-datagrid'
import {
  computed,
  defineComponent,
  h,
  onBeforeUnmount,
  onMounted,
  ref,
  shallowRef,
  watch,
} from 'vue'
import * as XLSX from 'xlsx'
import { getDashboardBizDate, getUnitAnalysisMetrics, runDataAnalysis } from '../services/api'

const props = defineProps({
  projectKey: { type: String, required: true },
  unitKey: { type: String, required: true },
  unitName: { type: String, default: '' },
  sheetKey: { type: String, required: true },
  pageConfig: { type: String, default: '' },
  bizDate: { type: String, required: true },
})

const analysisFolded = ref(true)
const analysisSchema = ref(null)
const analysisSchemaLoading = ref(false)
const analysisSchemaError = ref('')
const analysisStartDate = ref(props.bizDate || '')
const analysisEndDate = ref(props.bizDate || '')
const selectedMetricKeys = ref(new Set())
const analysisLoading = ref(false)
const analysisFormError = ref('')
const analysisResult = ref({ rows: [], warnings: [], meta: null })
const analysisTimelineGrid = ref({ columns: [], rows: [] })
const analysisTimelineMetrics = ref([])
const activeTimelineMetricKeys = ref([])
const analysisDefaultBizDate = ref('')
const analysisDefaultDateApplied = ref(false)

const analysisMetricGroups = computed(() => analysisSchema.value?.groups || [])
const analysisMetricOptions = computed(() => {
  if (!analysisMetricGroups.value.length) {
    return (analysisSchema.value?.options || []).slice().sort((a, b) => (a.label || '').localeCompare(b.label || ''))
  }
  return analysisMetricGroups.value.flatMap((group) =>
    (group.options || []).slice().sort((a, b) => (a.label || '').localeCompare(b.label || '')),
  )
})
const metricDecimalsMap = computed(() => analysisSchema.value?.decimals || {})
const analysisUnitDict = computed(() => analysisSchema.value?.unit_dict || {})
function normalizeUnitValue(value) {
  if (typeof value !== 'string') return ''
  return value.trim()
}
function stripSheetSuffix(value) {
  const normalized = normalizeUnitValue(value)
  if (!normalized) return ''
  if (normalized.endsWith('_Sheet')) return normalized.slice(0, -6)
  return normalized
}
const analysisUnitKey = computed(() => {
  if (analysisSchema.value?.unit_key) return normalizeUnitValue(analysisSchema.value.unit_key)
  const dict = analysisUnitDict.value || {}
  const entries = Object.entries(dict).map(([k, v]) => [normalizeUnitValue(k), normalizeUnitValue(String(v ?? ''))])
  const candidates = [
    normalizeUnitValue(props.unitKey),
    normalizeUnitValue(props.unitName),
    normalizeUnitValue(props.sheetKey),
    stripSheetSuffix(props.unitKey),
    stripSheetSuffix(props.sheetKey),
  ].filter(Boolean)
  // 精确匹配 key
  for (const candidate of candidates) {
    const exactKey = entries.find(([key]) => key.toLowerCase() === candidate.toLowerCase())
    if (exactKey) return exactKey[0]
  }
  // 精确匹配 label
  for (const candidate of candidates) {
    const exactLabel = entries.find(([, label]) => label.toLowerCase() === candidate.toLowerCase())
    if (exactLabel) return exactLabel[0]
  }
  // 包含式模糊匹配
  for (const candidate of candidates) {
    const fuzzy = entries.find(
      ([key, label]) =>
        (candidate && key.includes(candidate)) || (candidate && label.includes(candidate)),
    )
    if (fuzzy) return fuzzy[0]
  }
  // 回退：props 提供的 key 或 sheetKey
  if (candidates.length) return candidates[0]
  // 最后回退：unit_dict 首项
  if (entries.length) return entries[0][0]
  return ''
})
const unitLabel = computed(() => {
  const key = analysisUnitKey.value
  const dict = analysisUnitDict.value || {}
  if (key && dict[key]) return dict[key]
  return props.unitName || props.unitKey || props.sheetKey || '未知单位'
})

const analysisTimelineMetricMap = computed(() => {
  const map = new Map()
  analysisTimelineMetrics.value.forEach((metric) => {
    if (metric?.key) {
      map.set(metric.key, metric)
    }
  })
  return map
})

const hasTimelineData = computed(
  () =>
    Array.isArray(analysisTimelineGrid.value?.columns) &&
    analysisTimelineGrid.value.columns.length > 1 &&
    Array.isArray(analysisTimelineGrid.value?.rows) &&
    analysisTimelineGrid.value.rows.length > 0,
)

const timelineCategories = computed(() =>
  analysisTimelineGrid.value.rows
    .filter((row) => row?.date && row.date !== '总计')
    .map((row) => row.date),
)

const activeTimelineMetrics = computed(() =>
  activeTimelineMetricKeys.value.map((key) => analysisTimelineMetricMap.value.get(key)).filter(Boolean),
)

const timelinePalette = [
  { current: '#2563eb', peer: '#93c5fd' },
  { current: '#f97316', peer: '#fdba74' },
  { current: '#0ea5e9', peer: '#7dd3fc' },
  { current: '#a855f7', peer: '#d8b4fe' },
  { current: '#22c55e', peer: '#86efac' },
]
const TEMPERATURE_KEYWORDS = ['气温', '温度']

const analysisTemperatureMetricCandidates = computed(() => {
  const groups = Array.isArray(analysisSchema.value?.groups) ? analysisSchema.value.groups : []
  const candidates = []
  groups.forEach((group) => {
    if (!group || group.key !== 'temperature') return
    ;(group.options || []).forEach((option) => {
      if (option?.value) {
        candidates.push(option.value)
      }
    })
  })
  return Array.from(new Set(candidates))
})
const analysisTemperatureMetricKey = computed(() => analysisTemperatureMetricCandidates.value[0] || null)

const TrendChart = defineComponent({
  name: 'TrendChart',
  props: {
    option: { type: Object, required: true },
    height: { type: [Number, String], default: '320px' },
    autoresize: { type: Boolean, default: true },
  },
  setup(componentProps) {
    const container = ref(null)
    const chart = shallowRef(null)
    const latestOption = shallowRef(null)
    const styleHeight = computed(() =>
      typeof componentProps.height === 'number' ? `${componentProps.height}px` : componentProps.height || '320px',
    )

    const dispose = () => {
      if (chart.value) {
        chart.value.dispose()
        chart.value = null
      }
    }

    const ensureChart = () => {
      if (!container.value || !window.echarts) return
      if (!chart.value) {
        chart.value = window.echarts.init(container.value)
      }
      if (latestOption.value) {
        chart.value.setOption(latestOption.value, { notMerge: true, lazyUpdate: false })
      }
    }

    const handleResize = () => {
      if (chart.value) chart.value.resize()
    }

    onMounted(() => {
      ensureChart()
      if (componentProps.autoresize) {
        window.addEventListener('resize', handleResize)
      }
    })

    onBeforeUnmount(() => {
      if (componentProps.autoresize) {
        window.removeEventListener('resize', handleResize)
      }
      dispose()
    })

    watch(
      () => componentProps.option,
      (option) => {
        latestOption.value = option || null
        ensureChart()
      },
      { deep: true, immediate: true },
    )

    return () =>
      h('div', {
        ref: container,
        class: 'timeline-chart',
        style: { height: styleHeight.value },
      })
  },
})

const timelineChartOption = computed(() => {
  const categories = timelineCategories.value
  const metrics = activeTimelineMetrics.value
  if (!categories.length || !metrics.length) return null

  const series = []
  const legend = []
  const seriesMeta = {}
  const axisSlots = assignTimelineAxisSlots(metrics, analysisTemperatureMetricKey.value)
  const hasRightAxis = axisSlots.some((slot) => slot.axis === 'right')

  const makeAxisBase = () => ({
    type: 'value',
    axisLabel: { color: '#475569' },
    splitLine: { lineStyle: { type: 'dashed', color: 'rgba(148, 163, 184, 0.35)' } },
  })

  const yAxis = hasRightAxis
    ? [
        makeAxisBase(),
        {
          ...makeAxisBase(),
          position: 'right',
          axisLabel: { color: '#475569' },
        },
      ]
    : makeAxisBase()

  metrics.forEach((metric, index) => {
    if (!metric) return
    const palette = timelinePalette[index % timelinePalette.length]
    const decimals = Number.isInteger(metric.decimals) ? metric.decimals : 2
    const timelineMap = {}
    ;(metric.timeline || []).forEach((entry) => {
      if (entry?.date) {
        timelineMap[entry.date] = {
          current: normalizeChartValue(entry.current, decimals),
          peer: normalizeChartValue(entry.peer, decimals),
        }
      }
    })
    const currentName = `${metric.label}（本期）`
    const peerName = `${metric.label}（同期）`
    const currentData = categories.map((date) => timelineMap[date]?.current ?? null)
    const peerData = categories.map((date) => timelineMap[date]?.peer ?? null)
    const axisSlot = axisSlots[index] || { axis: 'left' }
    const yAxisIndex = hasRightAxis && axisSlot.axis === 'right' ? 1 : 0

    series.push({
      name: currentName,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      showSymbol: categories.length <= 31,
      data: currentData,
      yAxisIndex,
      lineStyle: { width: 3, color: palette.current },
      areaStyle: {
        opacity: 0.18,
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: withAlpha(palette.current, 0.45) },
            { offset: 1, color: 'rgba(255,255,255,0)' },
          ],
        },
      },
      emphasis: { focus: 'series' },
    })
    series.push({
      name: peerName,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      showSymbol: categories.length <= 31,
      data: peerData,
      yAxisIndex,
      lineStyle: { width: 2, color: palette.peer, type: 'dashed' },
      emphasis: { focus: 'series' },
    })
    legend.push(currentName, peerName)
    seriesMeta[currentName] = {
      unit: metric.unit || '',
      type: 'current',
      label: metric.label,
      getEntry: (date) => timelineMap[date],
    }
    seriesMeta[peerName] = {
      unit: metric.unit || '',
      type: 'peer',
      label: metric.label,
      getEntry: (date) => timelineMap[date],
    }
  })

  const tooltipFormatter = (params = []) => {
    if (!Array.isArray(params) || !params.length) return ''
    const dateLabel = params[0].axisValue ?? ''
    const lines = [`<div class="chart-tooltip__title">${dateLabel}</div>`]
    params.forEach((item) => {
      const meta = seriesMeta[item.seriesName] || {}
      const unit = meta.unit ? ` ${meta.unit}` : ''
      const value =
        item.data === null || item.data === undefined ? '—' : formatNumber(item.data, 2)
      const delta = meta.type === 'current' ? formatChartDelta(meta.getEntry?.(dateLabel)) : ''
      const colorChip =
        typeof item.color === 'string'
          ? item.color
          : Array.isArray(item.color)
            ? item.color[0]
            : '#2563eb'
      lines.push(
        `<div class="chart-tooltip__item"><span class="chart-tooltip__dot" style="background:${colorChip}"></span>${item.seriesName}：${value}${unit}${delta}</div>`,
      )
    })
    return lines.join('')
  }

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: 'rgba(15, 23, 42, 0.94)',
      borderWidth: 0,
      textStyle: { color: '#f8fafc' },
      formatter: tooltipFormatter,
      extraCssText:
        'box-shadow: 0 10px 40px rgba(15,23,42,0.35); border-radius: 12px; padding: 12px 16px;',
    },
    legend: {
      type: 'scroll',
      top: 0,
      icon: 'roundRect',
      inactiveColor: '#cbd5f5',
      data: legend,
    },
    grid: { left: 48, right: 24, top: 72, bottom: 90 },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      {
        type: 'slider',
        height: 18,
        bottom: 30,
        borderColor: 'transparent',
        backgroundColor: 'rgba(148, 163, 184, 0.15)',
      },
    ],
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: categories,
      axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.5)' } },
      axisLabel: { color: '#475569' },
      axisPointer: {
        label: {
          show: true,
          backgroundColor: '#0f172a',
          color: '#f8fafc',
        },
      },
    },
    yAxis,
    series,
  }
})

function toggleAnalysisFold() {
  analysisFolded.value = !analysisFolded.value
  if (!analysisFolded.value) {
    ensureAnalysisDefaultDates()
    ensureAnalysisSchema()
  }
}

function shiftDateByDays(dateStr, offsetDays) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  if (Number.isNaN(date.getTime())) return ''
  date.setDate(date.getDate() + offsetDays)
  return formatLocalYYYYMMDD(date)
}

function formatLocalYYYYMMDD(dateInput) {
  const date = dateInput instanceof Date ? dateInput : new Date(dateInput)
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function formatDateYYYYMMDD(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (Number.isNaN(d.getTime())) return String(dateStr)
  return formatLocalYYYYMMDD(d)
}

function applyAnalysisDateWindow(endDate) {
  if (!endDate) return
  const normalizedEnd = formatDateYYYYMMDD(endDate) || endDate
  const start = shiftDateByDays(normalizedEnd, -6) || normalizedEnd
  analysisStartDate.value = start
  analysisEndDate.value = normalizedEnd
}

async function loadAnalysisDefaultBizDate() {
  if (analysisDefaultBizDate.value) {
    return analysisDefaultBizDate.value
  }
  try {
    const payload = await getDashboardBizDate(props.projectKey)
    const value = typeof payload?.set_biz_date === 'string' ? payload.set_biz_date.trim() : ''
    if (value) {
      analysisDefaultBizDate.value = value
      return analysisDefaultBizDate.value
    }
  } catch (err) {
    // ignore
  }
  analysisDefaultBizDate.value = props.bizDate
  return props.bizDate
}

async function ensureAnalysisDefaultDates() {
  if (analysisDefaultDateApplied.value) return
  const base = await loadAnalysisDefaultBizDate()
  applyAnalysisDateWindow(base)
  analysisDefaultDateApplied.value = true
}

async function ensureAnalysisSchema() {
  if (analysisSchema.value || analysisSchemaLoading.value) return analysisSchema.value
  analysisSchemaLoading.value = true
  analysisSchemaError.value = ''
  try {
    const payload = await getUnitAnalysisMetrics(props.projectKey, {
      unit_key: props.unitKey || props.sheetKey,
    })
    if (!payload?.ok) {
      throw new Error(payload?.message || '分析配置加载失败')
    }
    analysisSchema.value = payload
    if (!selectedMetricKeys.value.size) {
      const defaultTemp = analysisTemperatureMetricKey.value
      selectedMetricKeys.value = defaultTemp ? new Set([defaultTemp]) : new Set()
    }
  } catch (err) {
    analysisSchemaError.value = err instanceof Error ? err.message : '分析配置加载失败'
  } finally {
    analysisSchemaLoading.value = false
  }
  return analysisSchema.value
}

function toggleAnalysisMetric(key) {
  const next = new Set(selectedMetricKeys.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  selectedMetricKeys.value = next
}

function selectAllAnalysisMetrics() {
  const next = new Set()
  analysisMetricOptions.value.forEach((item) => next.add(item.value))
  selectedMetricKeys.value = next
}

function clearAnalysisMetrics() {
  selectedMetricKeys.value = new Set()
}

function resetAnalysisResult() {
  analysisResult.value = { rows: [], warnings: [], meta: null }
  analysisFormError.value = ''
  resetAnalysisTimeline()
}

function resetAnalysisTimeline() {
  analysisTimelineGrid.value = { columns: [], rows: [] }
  analysisTimelineMetrics.value = []
  activeTimelineMetricKeys.value = []
}

function resolveRowDelta(row) {
  if (row.total_delta !== undefined && row.total_delta !== null) return row.total_delta
  return row.delta
}

function resolveDeltaClass(row) {
  const delta = resolveRowDelta(row)
  if (delta === null || delta === undefined || Number.isNaN(Number(delta))) return ''
  return Number(delta) >= 0 ? 'delta-up' : 'delta-down'
}

function formatNumber(value, decimals = 2) {
  if (value === null || value === undefined) return '—'
  const num = Number(value)
  if (Number.isNaN(num)) return '—'
  return num.toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

function formatDelta(value) {
  if (value === null || value === undefined) return '—'
  const num = Number(value)
  if (Number.isNaN(num)) return '—'
  const sign = num > 0 ? '+' : ''
  return `${sign}${num.toFixed(2)}%`
}

function formatPercentValue(value) {
  if (value === null || value === undefined) return null
  const num = Number(value)
  if (Number.isNaN(num)) return null
  return `${num.toFixed(2)}%`
}

function applyDecimals(value, decimals = 2) {
  if (value === null || value === undefined) return null
  const num = Number(value)
  if (Number.isNaN(num)) return null
  return Number(num.toFixed(decimals))
}

function createDeltaCellPayload(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return { text: '—', delta: null }
  }
  const deltaNumber = Number(value)
  return {
    text: formatPercentValue(deltaNumber) || '—',
    delta: deltaNumber,
  }
}

const timelineDeltaCellTemplate = (createElement, propsArg) => {
  const rawValue = propsArg?.model?.[propsArg.prop]
  const text =
    typeof rawValue === 'object' && rawValue !== null
      ? rawValue.text ?? '—'
      : typeof rawValue === 'string'
        ? rawValue
        : '—'
  const deltaNumber =
    typeof rawValue === 'object' && rawValue !== null && typeof rawValue.delta === 'number'
      ? rawValue.delta
      : null
  const style = { color: deltaNumber === null ? '#475569' : deltaNumber >= 0 ? '#b91c1c' : '#0f9d58' }
  return createElement('span', { style }, text || '—')
}

function normalizeAnalysisRows(rows) {
  if (!Array.isArray(rows)) return []
  return rows.map((row) => ({
    ...row,
    decimals: metricDecimalsMap.value?.[row.key] ?? row.decimals ?? 2,
  }))
}

function toggleTimelineMetric(metricKey) {
  const list = [...activeTimelineMetricKeys.value]
  const index = list.indexOf(metricKey)
  if (index >= 0) {
    list.splice(index, 1)
  } else {
    list.push(metricKey)
  }
  activeTimelineMetricKeys.value = list
}

function getMetricSelectionOrder(metricKey) {
  const order = Array.from(selectedMetricKeys.value)
  const index = order.indexOf(metricKey)
  if (index === -1) return ''
  return String(index + 1)
}

function extractTimelineCellText(value) {
  if (value && typeof value === 'object') {
    return value.text ?? ''
  }
  return value ?? ''
}

function normalizeChartValue(value, decimals = 2) {
  if (value === null || value === undefined) return null
  const num = Number(value)
  if (Number.isNaN(num)) return null
  return Number(num.toFixed(decimals))
}

function withAlpha(hex, alpha) {
  if (typeof hex !== 'string' || !hex.startsWith('#')) return hex
  const value = hex.slice(1)
  if (value.length !== 6) return hex
  const r = parseInt(value.slice(0, 2), 16)
  const g = parseInt(value.slice(2, 4), 16)
  const b = parseInt(value.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function formatChartDelta(entry) {
  if (!entry || entry.peer === null || entry.peer === undefined) return ''
  const current = Number(entry.current)
  const peer = Number(entry.peer)
  if (!Number.isFinite(current) || !Number.isFinite(peer) || peer === 0) {
    return ''
  }
  const delta = ((current - peer) / peer) * 100
  if (!Number.isFinite(delta)) return ''
  const sign = delta >= 0 ? '+' : ''
  return `<span class="chart-tooltip__delta">${sign}${delta.toFixed(2)}%</span>`
}

function isAnalysisTemperatureMetric(metric) {
  if (!metric) return false
  if (analysisTemperatureMetricCandidates.value.includes(metric.key)) return true
  if (metric.value_type === 'temperature') return true
  const label = metric.label || ''
  return TEMPERATURE_KEYWORDS.some((keyword) => label.includes(keyword))
}

function assignTimelineAxisSlots(metrics, temperatureKey) {
  if (!Array.isArray(metrics) || !metrics.length) return []
  const hasTemp = metrics.length >= 2 && metrics.some((metric) => {
    if (!metric) return false
    if (temperatureKey && metric.key === temperatureKey) return true
    return isAnalysisTemperatureMetric(metric)
  })
  return metrics.map((metric, index) => {
    const slot = { key: metric?.key || `__timeline_metric_${index}`, axis: 'left' }
    if (metrics.length >= 2) {
      if (hasTemp && isAnalysisTemperatureMetric(metric)) {
        slot.axis = 'right'
      } else if (!hasTemp && index >= 1) {
        slot.axis = 'right'
      }
    }
    return slot
  })
}

function buildTimelineGrid(rows) {
  const dateSet = new Set()
  const metrics = []
  rows.forEach((row) => {
    if (Array.isArray(row.timeline) && row.timeline.length) {
      metrics.push(row)
      row.timeline.forEach((entry) => {
        if (entry?.date) {
          dateSet.add(entry.date)
        }
      })
    }
  })
  const sortedDates = Array.from(dateSet).sort()
  if (!sortedDates.length || !metrics.length) {
    return { columns: [], rows: [] }
  }
  const metricState = metrics.map((row) => ({
    key: row.key,
    label: row.label,
    timeline: row.timeline,
    decimals: row.decimals ?? 2,
    valueType: row.value_type || 'analysis',
    totalCurrent: row.total_current ?? null,
    totalPeer: row.total_peer ?? null,
    sumCurrent: 0,
    sumPeer: 0,
  }))
  const columns = [{ prop: 'date', name: '日期', size: 110 }]
  metricState.forEach((row) => {
    columns.push({ prop: `${row.key}__current`, name: `${row.label}(本期)`, size: 140 })
    columns.push({ prop: `${row.key}__peer`, name: `${row.label}(同期)`, size: 140 })
    columns.push({
      prop: `${row.key}__delta`,
      name: `${row.label}(同比%)`,
      size: 120,
      cellTemplate: timelineDeltaCellTemplate,
    })
  })
  const gridRows = sortedDates.map((date) => {
    const record = { date }
    metricState.forEach((row) => {
      const entry = row.timeline.find((item) => item.date === date)
      const current = entry?.current ?? null
      const peer = entry?.peer ?? null
      if (current !== null) {
        row.sumCurrent += Number(current)
      }
      if (peer !== null) {
        row.sumPeer += Number(peer)
      }
      record[`${row.key}__current`] = current !== null ? applyDecimals(current, row.decimals) : null
      record[`${row.key}__peer`] = peer !== null ? applyDecimals(peer, row.decimals) : null
      const deltaValue =
        peer !== null && peer !== 0 && current !== null ? ((current - peer) / peer) * 100 : null
      record[`${row.key}__delta`] = createDeltaCellPayload(deltaValue)
    })
    return record
  })
  const totalRecord = { date: '总计' }
  metricState.forEach((row) => {
    let totalCurrent = row.totalCurrent
    let totalPeer = row.totalPeer
    if (totalCurrent == null) {
      if (row.valueType === 'constant' && row.timeline && row.timeline.length) {
        totalCurrent = row.timeline[0]?.current ?? null
      } else {
        totalCurrent = row.sumCurrent || null
      }
    }
    if (totalPeer == null) {
      if (row.valueType === 'constant' && row.timeline && row.timeline.length) {
        totalPeer = row.timeline[0]?.peer ?? null
      } else {
        totalPeer = row.sumPeer || null
      }
    }
    totalRecord[`${row.key}__current`] = totalCurrent !== null ? applyDecimals(totalCurrent, row.decimals) : null
    totalRecord[`${row.key}__peer`] = totalPeer !== null ? applyDecimals(totalPeer, row.decimals) : null
    const totalDelta =
      totalPeer !== null && totalPeer !== 0 && totalCurrent !== null
        ? ((totalCurrent - totalPeer) / totalPeer) * 100
        : null
    totalRecord[`${row.key}__delta`] = createDeltaCellPayload(totalDelta)
  })
  gridRows.push(totalRecord)
  return { columns, rows: gridRows }
}

function buildTimelineSheetData(timeline) {
  if (!timeline || !Array.isArray(timeline.columns) || !timeline.columns.length) return null
  const columns = timeline.columns
  const header = columns.map((col) => col.name || col.prop)
  const rows = (timeline.rows || []).map((record) => columns.map((col) => extractTimelineCellText(record[col.prop])))
  return [header, ...rows]
}

function buildSummarySheetData(rows) {
  const header = ['指标', '本期', '同期', '同比', '单位']
  const source = Array.isArray(rows) ? rows : []
  const mapped = source.map((row) => [
    row.label,
    formatExportNumber(row.total_current ?? row.current, row.decimals || 2),
    formatExportNumber(row.total_peer ?? row.peer, row.decimals || 2),
    formatPercentValue(resolveRowDelta(row)) || '',
    row.unit || '',
  ])
  return [header, ...mapped]
}

function buildMetaSheetData(meta) {
  const data = [
    ['单位', meta?.unit_label || unitLabel.value],
    ['分析模式', meta?.analysis_mode_label || '累计数据'],
    ['日期范围', meta && meta.start_date && meta.end_date ? `${meta.start_date} ~ ${meta.end_date}` : ''],
    ['生成时间', new Date().toLocaleString()],
    ['指标数量', selectedMetricKeys.value.size],
  ]
  return data
}

function buildUnitSheetData(result) {
  const sheetData = []
  buildSummarySheetData(result?.rows).forEach((row) => sheetData.push(row))
  const timelineData = buildTimelineSheetData(result?.timeline)
  if (timelineData && timelineData.length) {
    sheetData.push([])
    sheetData.push(['区间明细'])
    timelineData.forEach((row) => sheetData.push(row))
  }
  sheetData.push([])
  sheetData.push(['查询信息'])
  buildMetaSheetData(result?.meta).forEach((row) => sheetData.push(row))
  return sheetData
}

function sanitizeSheetName(name) {
  if (!name) return 'Sheet'
  return name.replace(/[\\/?*\\[\\]:]/g, '_').slice(0, 31) || 'Sheet'
}

function downloadAnalysisExcel() {
  if (!analysisResult.value.rows.length) return
  const wb = XLSX.utils.book_new()
  const unitName = analysisResult.value.meta?.unit_label || unitLabel.value
  const sheet = XLSX.utils.aoa_to_sheet(
    buildUnitSheetData({
      rows: analysisResult.value.rows,
      timeline: analysisTimelineGrid.value,
      meta: analysisResult.value.meta,
    }),
  )
  XLSX.utils.book_append_sheet(wb, sheet, sanitizeSheetName(unitName))
  const filename = `本单位数据分析_${unitName}_${Date.now()}.xlsx`
  XLSX.writeFile(wb, filename)
}

function reorderMetricKeys(keys, temperatureKey, availableKeys = []) {
  if (!keys || !keys.length) return []
  const filtered = keys.filter((key) => !availableKeys.length || availableKeys.includes(key))
  if (!filtered.length) return []
  if (!temperatureKey) return filtered.slice(0, 2)
  const hasTemp = filtered.includes(temperatureKey)
  const withoutTemp = filtered.filter((key) => key !== temperatureKey)
  if (!hasTemp) return filtered.slice(0, 2)
  if (!withoutTemp.length) return [temperatureKey]
  const ordered = withoutTemp.slice(0, 1)
  ordered.push(temperatureKey)
  return ordered
}

watch(
  analysisTimelineMetrics,
  (metrics) => {
    const available = metrics.map((item) => item.key).filter(Boolean)
    if (!available.length) {
      activeTimelineMetricKeys.value = []
      return
    }
    const ordered = reorderMetricKeys(activeTimelineMetricKeys.value, analysisTemperatureMetricKey.value, available)
    if (ordered.length) {
      activeTimelineMetricKeys.value = ordered
      return
    }
    if (analysisTemperatureMetricKey.value && available.includes(analysisTemperatureMetricKey.value)) {
      const other = available.find((key) => key !== analysisTemperatureMetricKey.value)
      activeTimelineMetricKeys.value = other ? [other, analysisTemperatureMetricKey.value] : [analysisTemperatureMetricKey.value]
      return
    }
    activeTimelineMetricKeys.value = [available[0]]
  },
  { immediate: true },
)

function applyAnalysisTimelineFromRows(rows) {
  const timeline = buildTimelineGrid(rows)
  analysisTimelineGrid.value = timeline
  analysisTimelineMetrics.value = rows.filter((row) => Array.isArray(row.timeline) && row.timeline.length)
}

function formatExportNumber(value, decimals = 2) {
  if (value === null || value === undefined || value === '—') return ''
  const num = Number(value)
  if (Number.isNaN(num)) return value
  return Number(num.toFixed(decimals))
}

function normalizeAnalysisMeta(responseMeta) {
  const start = responseMeta?.start_date || analysisStartDate.value
  const end = responseMeta?.end_date || analysisEndDate.value
  return {
    unit_key: analysisUnitKey.value,
    unit_label: responseMeta?.unit_label || unitLabel.value,
    analysis_mode_label: responseMeta?.analysis_mode_label || '累计数据',
    start_date: start,
    end_date: end,
  }
}

async function runUnitAnalysis() {
  analysisFormError.value = ''
  const schemaReady = await ensureAnalysisSchema()
  if (!schemaReady) {
    analysisFormError.value = analysisSchemaError.value || '分析配置未加载成功'
    return
  }
  if (!selectedMetricKeys.value.size) {
    analysisFormError.value = '请至少选择一个指标。'
    return
  }
  if (!analysisStartDate.value || !analysisEndDate.value) {
    analysisFormError.value = '请选择起止日期。'
    return
  }
  const unitKey = analysisUnitKey.value
  if (!unitKey) {
    analysisFormError.value = '缺少单位信息，请检查配置。'
    return
  }
  resetAnalysisResult()
  analysisLoading.value = true
  try {
    const payload = {
      metrics: Array.from(selectedMetricKeys.value),
      analysis_mode: 'range',
      start_date: analysisStartDate.value,
      end_date: analysisEndDate.value,
      unit_key: unitKey,
    }
    // data_entry 页面传入的 config 指向填报模板，不适用于分析接口，这里不透传 config 以使用后端默认配置
    const response = await runDataAnalysis(props.projectKey, payload)
    if (!response?.ok) {
      throw new Error(response?.message || '生成汇总失败')
    }
    const rows = normalizeAnalysisRows(response.rows)
    analysisResult.value = {
      rows,
      warnings: Array.isArray(response.warnings) ? response.warnings : [],
      meta: normalizeAnalysisMeta(response),
    }
    applyAnalysisTimelineFromRows(rows)
  } catch (err) {
    analysisFormError.value = err instanceof Error ? err.message : '生成汇总失败'
    resetAnalysisTimeline()
  } finally {
    analysisLoading.value = false
  }
}

watch(
  () => props.bizDate,
  (value) => {
    if (value) {
      analysisDefaultDateApplied.value = false
      applyAnalysisDateWindow(value)
      resetAnalysisResult()
    }
  },
)

watch(
  () => props.unitKey,
  () => {
    analysisSchema.value = null
    selectedMetricKeys.value = new Set()
    analysisDefaultDateApplied.value = false
    resetAnalysisResult()
    if (!analysisFolded.value) {
      ensureAnalysisDefaultDates()
      ensureAnalysisSchema()
    }
  },
)

watch(
  () => analysisStartDate.value,
  (value, oldValue) => {
    if (!value) return
    if (analysisEndDate.value && value > analysisEndDate.value) {
      analysisEndDate.value = value
    }
    if (value !== oldValue) resetAnalysisResult()
  },
)

watch(
  () => analysisEndDate.value,
  (value, oldValue) => {
    if (!value) return
    if (value !== oldValue) resetAnalysisResult()
  },
)

watch(
  () => selectedMetricKeys.value,
  () => {
    resetAnalysisResult()
  },
  { deep: true },
)
</script>

<style scoped>
.analysis-lite {
  margin-top: 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.analysis-lite__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.analysis-lite__hint {
  color: var(--neutral-500);
  font-size: 13px;
  margin: 4px 0 0;
}

.analysis-lite__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.analysis-lite__fold-hint {
  border: 1px dashed var(--border);
  border-radius: var(--radius);
  padding: 12px;
  color: var(--neutral-600);
  font-size: 14px;
}

.analysis-lite__form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  border: 1px dashed var(--border);
  border-radius: var(--radius);
  padding: 12px;
}

.analysis-lite__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.analysis-lite__field-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.analysis-lite__field-actions {
  display: flex;
  gap: 8px;
}

.analysis-lite__dates {
  display: flex;
  align-items: center;
  gap: 8px;
}

.analysis-lite__dates input {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 8px;
}

.analysis-lite__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
  max-height: 360px;
  overflow-y: auto;
  padding-right: 6px;
}

.analysis-lite__group-card {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.analysis-lite__metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px;
  max-height: 320px;
  overflow-y: auto;
  padding-right: 4px;
}

.analysis-lite__form-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.analysis-lite__unit-label {
  color: var(--neutral-500);
  font-size: 14px;
}

.analysis-lite__result {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.analysis-lite__warnings {
  padding: 10px;
  border: 1px solid var(--warning-200, #f59e0b33);
  border-radius: var(--radius);
  background: var(--warning-50, #fff7ed);
  color: var(--warning-700, #b45309);
  font-size: 14px;
}

.analysis-lite__warnings ul {
  margin: 4px 0 0 16px;
  padding: 0;
}

.analysis-lite__table {
  width: 100%;
  border-collapse: collapse;
}

.analysis-lite__table th,
.analysis-lite__table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  text-align: left;
  font-size: 14px;
}

.analysis-lite__table th {
  background: var(--neutral-50);
  color: var(--neutral-700);
}

.analysis-lite__metric {
  display: flex;
  align-items: center;
  gap: 6px;
}

.analysis-lite__value {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.analysis-lite__number {
  font-weight: 600;
}

.analysis-lite__unit {
  font-size: 12px;
  color: var(--neutral-500);
}

.analysis-lite__timeline {
  display: flex;
  flex-direction: column;
  gap: 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px;
}

.analysis-lite__timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.analysis-lite__timeline-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.analysis-lite__timeline-grid {
  width: 100%;
  overflow: hidden;
}

.analysis-lite__timeline-chart {
  border: 1px solid var(--neutral-100);
  border-radius: var(--radius);
  padding: 12px;
  background: #fff;
}

.chip--toggle {
  border-radius: 999px;
  border: 1px solid var(--neutral-200);
  background: var(--neutral-50);
  color: var(--neutral-700);
  transition: all 0.2s ease;
}

.chip--toggle .chip-hint {
  font-size: 12px;
  color: var(--neutral-500);
}

.chip--toggle.active {
  border-color: var(--primary-400);
  background: rgba(37, 99, 235, 0.08);
  color: var(--primary-700);
  font-weight: 600;
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.12);
}

.tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 6px;
  border-radius: 999px;
  font-size: 12px;
}

.tag--subtle {
  background: var(--neutral-100);
  color: var(--neutral-600);
}

.delta-up {
  color: var(--danger-600, #d93025);
}

.delta-down {
  color: var(--success-600, #0f9d58);
}
</style>
