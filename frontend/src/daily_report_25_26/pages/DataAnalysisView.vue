<template>
  <div class="data-analysis-view">
    <AppHeader />
    <main class="analysis-main">
      <Breadcrumbs :items="breadcrumbItems" />

      <section class="card elevated analysis-block">
        <header class="card-header">
          <div>
            <h2>{{ pageDisplayName }}</h2>
            <p class="analysis-subtitle"></p>
          </div>
          <span class="analysis-tag">Beta</span>
        </header>

        <div v-if="loading" class="page-state">配置加载中，请稍候…</div>
        <div v-else-if="errorMessage" class="page-state error">{{ errorMessage }}</div>

        <template v-else>
          <div class="form-layout">
            <div class="form-grid form-grid--top">
              <div class="form-panel form-panel--compact">
                <div class="panel-header">
                  <h3>单位选择（多选）</h3>
                  <span class="panel-hint">已选 {{ selectedUnits.length }} / {{ unitOptions.length }}</span>
                </div>
                <div class="chip-group">
                  <label
                    v-for="unit in unitOptions"
                    :key="unit.value"
                    class="chip checkbox"
                  >
                    <input
                      type="checkbox"
                      :checked="selectedUnits.includes(unit.value)"
                      @change="handleUnitSelection(unit.value, $event.target.checked)"
                    />
                    <span class="chip-label">
                      <span v-if="getUnitSelectionOrder(unit.value)" class="chip-order">
                        {{ getUnitSelectionOrder(unit.value) }}
                      </span>
                      <span>{{ unit.label }}</span>
                    </span>
                  </label>
                </div>
              </div>

              <div class="form-panel form-panel--compact">
                <div class="panel-header">
                  <h3>分析模式</h3>
                  <span class="panel-hint">切换单日或区间累计</span>
                </div>
                <div class="chip-group compact">
                  <label
                    v-for="mode in analysisModes"
                    :key="mode.value"
                    class="chip radio"
                  >
                    <input
                      type="radio"
                      name="analysisMode"
                      :value="mode.value"
                      v-model="analysisMode"
                    />
                    <span>{{ mode.label }}</span>
                  </label>
                </div>
                <div class="date-subsection">
                  <div class="panel-header">
                    <h4>日期范围</h4>
                    <span class="panel-hint">与分析模式联动</span>
                  </div>
                  <div class="date-grid">
                    <label class="date-field">
                      <span>起始日期</span>
                      <input type="date" v-model="startDate" />
                    </label>
                    <label class="date-field">
                      <span>结束日期</span>
                      <input type="date" v-model="endDate" :disabled="analysisMode === 'daily'" />
                    </label>
                  </div>
                  <p class="panel-hint">
                    {{ analysisMode === 'daily' ? '单日模式会自动将结束日期同步为起始日期。' : '累计模式支持跨日期区间。' }}
                  </p>
                </div>
              </div>
            </div>

            <div class="form-panel form-panel--metrics">
              <div class="panel-header">
                <h3>指标选择（多选）</h3>
                <div class="panel-actions">
                  <button class="btn ghost xs" type="button" @click="selectAllMetrics">
                    全选
                  </button>
                  <button class="btn ghost xs" type="button" @click="clearMetrics">
                    清空
                  </button>
                </div>
              </div>
              <p class="panel-hint">
                已选择 {{ selectedMetrics.size }} 项
              </p>
              <div class="metrics-panel-body">
                <div v-if="resolvedMetricGroups.length" class="metrics-groups">
                  <div
                    v-for="group in resolvedMetricGroups"
                    :key="group.key"
                    class="metrics-group"
                    :class="{ 'metrics-group--disabled': group.disabled }"
                  >
                    <div class="metrics-group-header">
                      <div class="metrics-group-title">
                        <h4>{{ group.label }}</h4>
                        <span class="panel-hint">共 {{ group.options.length }} 项</span>
                      </div>
                      <div class="metrics-group-actions">
                        <span v-if="group.key === 'constant'" class="group-badge">常量</span>
                        <span
                          v-else-if="group.key === 'adjustment'"
                          class="group-badge group-badge--outline"
                        >
                          调整
                        </span>
                        <span
                          v-else-if="group.key === 'temperature'"
                          class="group-badge group-badge--temp"
                        >
                          气温
                        </span>
                      </div>
                    </div>
                    <p v-if="group.disabled" class="panel-hint warning">
                      当前视图不支持该组，请切换单位或分析模式。
                    </p>
                    <div class="metrics-grid">
                      <label
                        v-for="metric in group.options"
                        :key="`${group.key}-${metric.value}`"
                        class="chip checkbox"
                      >
                        <input
                          type="checkbox"
                          :value="metric.value"
                          :checked="selectedMetrics.has(metric.value)"
                          :disabled="group.disabled || queryLoading"
                          @change="toggleMetric(metric.value)"
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
                <div v-else class="panel-hint">
                  暂无可选指标，请检查配置文件。
                </div>
              </div>
            </div>

          </div>

          <div v-if="formError" class="page-state error">{{ formError }}</div>

          <div class="form-actions">
            <button
              class="btn primary"
              type="button"
              :disabled="queryLoading"
              @click="runAnalysis"
            >
              {{ queryLoading ? '生成中…' : '生成分析结果' }}
            </button>
            <button class="btn ghost" type="button" :disabled="queryLoading" @click="resetSelections">
              重置选择
            </button>
          </div>
        </template>
      </section>

      <section class="card elevated result-block">
        <header class="card-header">
          <div>
            <h3>分析结果预览</h3>
            <p class="analysis-subtitle">
              <template v-if="lastQueryMeta">
                {{ lastQueryMeta.analysis_mode_label || analysisModeLabel }} ｜ 单位：{{ lastQueryMeta.unit_label }}
                <template v-if="lastQueryMeta.start_date">
                  ｜ 日期：
                  <span>
                    <template v-if="lastQueryMeta.end_date && lastQueryMeta.end_date !== lastQueryMeta.start_date">
                      {{ lastQueryMeta.start_date }} ~ {{ lastQueryMeta.end_date }}
                    </template>
                    <template v-else>
                      {{ lastQueryMeta.start_date }}
                    </template>
                  </span>
                </template>
              </template>
              <template v-else>
                单位：{{ activeUnitLabel }} ｜ 指标数：{{ selectedMetrics.size }}
              </template>
            </p>
          </div>
          <button
            class="btn ghost"
            type="button"
            :disabled="!resultUnitKeys.length || queryLoading"
            @click="downloadExcel"
          >
            下载 Excel
          </button>
        </header>

        <div v-if="queryLoading" class="page-state">正在生成分析结果，请稍候…</div>
        <div v-else-if="!previewRows.length" class="page-state muted">
          <template v-if="resultUnitKeys.length">
            当前单位暂无可显示的数据，请尝试切换其它单位或调整指标。
          </template>
          <template v-else>
            请选择单位、指标与日期后点击“生成分析结果”，即可在此查看组合预览。
          </template>
        </div>
        <div v-else>
          <div v-if="resultUnitKeys.length > 1" class="unit-switch">
            <span class="unit-switch__label">切换单位：</span>
            <div class="unit-switch__chips">
              <button
                v-for="unitKey in resultUnitKeys"
                :key="`result-unit-${unitKey}`"
                type="button"
                class="unit-toggle"
                :class="{ active: activeUnit === unitKey }"
                @click="handleSwitchUnit(unitKey)"
              >
                {{ resolveUnitLabel(unitKey) }}
              </button>
            </div>
          </div>
          <div class="info-banner" v-if="infoBanner">{{ infoBanner }}</div>
          <ul v-if="queryWarnings.length" class="warning-list">
            <li v-for="(warning, idx) in queryWarnings" :key="`warn-${idx}`">
              ⚠ {{ warning }}
            </li>
          </ul>
          <table class="result-table">
            <thead>
              <tr>
                <th>指标</th>
                <th>当前值</th>
                <th>同期/对照</th>
                <th>同比</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in previewRows"
                :key="row.key"
                :class="{ 'result-row--missing': row.missing }"
              >
                <td>
                  <div class="metric-label">
                    <span>{{ row.label }}</span>
                    <span v-if="row.value_type === 'temperature'" class="tag tag--subtle">气温</span>
                    <span v-else-if="row.value_type === 'constant'" class="tag tag--subtle">常量</span>
                    <span v-if="row.missing" class="tag tag--subtle">缺失</span>
                  </div>
                </td>
                <td>
                  <div class="value-cell">
                    <span class="value-number">{{ formatNumber(resolveValue(row, 'current'), row.decimals || 2) }}</span>
                    <span v-if="row.unit" class="value-unit">{{ row.unit }}</span>
                  </div>
                </td>
                <td>
                  <div class="value-cell">
                    <span class="value-number">{{ formatNumber(resolveValue(row, 'peer'), row.decimals || 2) }}</span>
                    <span v-if="row.unit" class="value-unit">{{ row.unit }}</span>
                  </div>
                </td>
                <td :class="resolveDelta(row) === null ? '' : resolveDelta(row) >= 0 ? 'delta-up' : 'delta-down'">
                  {{ formatDelta(resolveDelta(row)) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-if="hasTimelineGrid" class="card elevated result-block">
        <header class="card-header">
          <div>
            <h3>区间明细（逐日）</h3>
          </div>
        </header>
        <div class="timeline-grid-wrapper">
          <RevoGrid
            class="timeline-grid"
            theme="material"
            :readonly="true"
            :columns="timelineGrid.columns"
            :source="timelineGrid.rows"
            :autoSizeColumn="true"
          />
        </div>
        <div class="timeline-chart-panel">
          <div class="timeline-chart-toolbar" v-if="timelineMetrics.length">
            <div class="timeline-chart-toolbar__info">
              <h4>趋势洞察</h4>
              <span class="panel-hint">切换单位与指标，即时对比本期与同期</span>
            </div>
            <div class="timeline-chart-toolbar__metrics">
              <button
                v-for="metric in timelineMetrics"
                :key="`timeline-metric-${metric.key}`"
                type="button"
                class="chip chip--toggle"
                :class="{ active: isTimelineMetricActive(metric.key) }"
                @click="toggleTimelineMetric(metric.key)"
              >
                <span>{{ metric.label }}</span>
                <span v-if="metric.unit" class="chip-hint">（{{ metric.unit }}）</span>
              </button>
            </div>
          </div>
          <TrendChart v-if="timelineChartOption" :option="timelineChartOption" height="360px" />
          <div v-else class="timeline-chart-empty">
            请选择至少一个包含逐日数据的指标以生成趋势图
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import RevoGrid from '@revolist/vue3-datagrid'
import * as XLSX from 'xlsx'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { getProjectNameById } from '../composables/useProjects'
import { getDataAnalysisSchema, getDashboardBizDate, runDataAnalysis } from '../services/api'

const TrendChart = defineComponent({
  name: 'TrendChart',
  props: {
    option: { type: Object, required: true },
    height: { type: [Number, String], default: '320px' },
    autoresize: { type: Boolean, default: true },
  },
  setup(props) {
    const container = ref(null)
    const chart = shallowRef(null)
    const latestOption = shallowRef(null)
    const styleHeight = computed(() =>
      typeof props.height === 'number' ? `${props.height}px` : props.height || '320px',
    )

    const dispose = () => {
      if (chart.value) {
        chart.value.dispose()
        chart.value = null
      }
    }

    const ensureChart = () => {
      if (!container.value) return
      if (!window.echarts) {
        console.warn('[data-analysis] ECharts 全局对象未加载，请检查入口文件是否引入 CDN 脚本')
        return
      }
      if (!chart.value) {
        chart.value = window.echarts.init(container.value)
      }
      if (latestOption.value) {
        chart.value.setOption(latestOption.value, { notMerge: false, lazyUpdate: true })
      }
    }

    const handleResize = () => {
      if (chart.value) {
        chart.value.resize()
      }
    }

    onMounted(() => {
      ensureChart()
      if (props.autoresize) {
        window.addEventListener('resize', handleResize)
      }
    })

    onBeforeUnmount(() => {
      if (props.autoresize) {
        window.removeEventListener('resize', handleResize)
      }
      dispose()
    })

    watch(
      () => props.option,
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

const route = useRoute()
const projectKey = computed(() => String(route.params.projectKey ?? ''))
const pageKey = computed(() => String(route.params.pageKey ?? ''))
const pageConfig = computed(() => (typeof route.query.config === 'string' ? route.query.config : ''))
const pageDisplayName = computed(() => {
  const raw = typeof route.query.pageName === 'string' ? route.query.pageName.trim() : ''
  return raw || '数据分析页面'
})
const projectName = computed(() => getProjectNameById(projectKey.value) ?? projectKey.value)
const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: projectName.value, to: `/projects/${encodeURIComponent(projectKey.value)}/pages` },
  { label: pageDisplayName.value, to: null },
])

const loading = ref(false)
const errorMessage = ref('')
const schema = ref(null)

function resolveUnitOptions(payload) {
  if (!payload) return []
  const dict = payload.unit_dict || {}
  const displayOpts = Array.isArray(payload.display_unit_options) ? payload.display_unit_options : null
  if (displayOpts && displayOpts.length) return displayOpts
  const displayKeys = Array.isArray(payload.display_unit_keys) ? payload.display_unit_keys : null
  if (displayKeys && displayKeys.length) {
    return displayKeys
      .map((key) => ({
        value: key,
        label: dict?.[key] || key,
      }))
      .filter((item) => item.value)
  }
  if (Array.isArray(payload.unit_options) && payload.unit_options.length) {
    return payload.unit_options
  }
  return Object.entries(dict).map(([value, label]) => ({ value, label }))
}

function normalizeMetricOptions(options) {
  if (!Array.isArray(options)) return []
  return options
    .map((item) => ({
      value: item?.value ?? '',
      label: item?.label ?? item?.value ?? '',
    }))
    .filter((item) => item.value)
}

function resolveMetricGroups(payload) {
  const groups = []
  if (!payload) return groups
  const provided = Array.isArray(payload.metric_groups) ? payload.metric_groups : []
  for (const group of provided) {
    if (!group || !group.options) continue
    const normalized = normalizeMetricOptions(group.options)
    if (!normalized.length) continue
    groups.push({
      key: group.key || group.label || 'metrics',
      label: group.label || group.key || '指标',
      options: normalized,
    })
  }
  if (!groups.length) {
    const fallback = normalizeMetricOptions(payload.metric_options || [])
    if (fallback.length) {
      groups.push({
        key: 'all',
        label: '全部指标',
        options: fallback,
      })
    }
  }
  return groups
}

const unitOptions = computed(() => resolveUnitOptions(schema.value))
const metricGroups = computed(() => resolveMetricGroups(schema.value))
const metricOptions = computed(() => metricGroups.value.flatMap((group) => group.options))
const unitDict = computed(() => schema.value?.unit_dict || {})
const metricDict = computed(() => schema.value?.metric_dict || {})
const metricDecimalsMap = computed(() => schema.value?.metric_decimals || {})
const viewMapping = computed(() => schema.value?.view_mapping || {})
const metricGroupViews = computed(() => schema.value?.metric_group_views || {})

const selectedUnits = ref([])
const activeUnit = ref('')
const unitResults = ref({})
const selectedMetrics = ref(new Set())
const analysisMode = ref('daily')
const analysisModes = computed(() => {
  const modes = Array.isArray(schema.value?.analysis_modes) ? schema.value.analysis_modes : []
  if (modes.length) return modes
  return [
    { value: 'daily', label: '单日数据' },
    { value: 'range', label: '累计数据' },
  ]
})
const hasConstantMetrics = computed(() =>
  metricGroups.value.some((group) => group.key === 'constant'),
)
const hasTimelineGrid = computed(
  () => analysisMode.value === 'range' && timelineGrid.value.rows.length > 0,
)

const defaultBizDate = ref('')
const startDate = ref('')
const endDate = ref('')
const previewRows = ref([])
const infoBanner = ref('')
const formError = ref('')
const queryWarnings = ref([])
const lastQueryMeta = ref(null)
const queryLoading = ref(false)
const timelineGrid = ref({ columns: [], rows: [] })
const activeTimelineMetricKeys = ref([])

const timelineMetrics = computed(() =>
  previewRows.value.filter((row) => Array.isArray(row.timeline) && row.timeline.length),
)

const timelineCategories = computed(() =>
  timelineGrid.value.rows
    .filter((row) => row?.date && row.date !== '总计')
    .map((row) => row.date),
)

watch(
  timelineMetrics,
  (metrics) => {
    const available = metrics.map((item) => item.key).filter(Boolean)
    if (!available.length) {
      activeTimelineMetricKeys.value = []
      return
    }
    const retained = activeTimelineMetricKeys.value.filter((key) => available.includes(key))
    activeTimelineMetricKeys.value =
      retained.length > 0 ? retained : available.slice(0, Math.min(2, available.length))
  },
  { immediate: true },
)

const timelinePalette = [
  { current: '#2563eb', peer: '#93c5fd' },
  { current: '#f97316', peer: '#fdba74' },
  { current: '#0ea5e9', peer: '#7dd3fc' },
  { current: '#a855f7', peer: '#d8b4fe' },
  { current: '#22c55e', peer: '#86efac' },
]

const timelineChartOption = computed(() => {
  if (!hasTimelineGrid.value || !timelineCategories.value.length) return null
  const metricMap = new Map()
  timelineMetrics.value.forEach((metric) => {
    metricMap.set(metric.key, metric)
  })
  const activeMetrics = activeTimelineMetricKeys.value
    .map((key) => metricMap.get(key))
    .filter(Boolean)
  if (!activeMetrics.length) return null

  const categories = timelineCategories.value
  const series = []
  const legend = []
  const seriesMeta = {}

  activeMetrics.forEach((metric, index) => {
    const palette = timelinePalette[index % timelinePalette.length]
    const decimals = metric.decimals ?? 2
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

    series.push({
      name: currentName,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      showSymbol: categories.length <= 31,
      data: currentData,
      yAxisIndex: 0,
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
      yAxisIndex: 0,
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
        item.data === null || item.data === undefined
          ? '—'
          : formatNumber(item.data, 2)
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
      extraCssText: 'box-shadow: 0 10px 40px rgba(15,23,42,0.35); border-radius: 12px; padding: 12px 16px;',
    },
    legend: {
      type: 'scroll',
      top: 0,
      icon: 'roundRect',
      inactiveColor: '#cbd5f5',
      data: legend,
    },
    grid: { left: 48, right: 24, top: 70, bottom: 90 },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', height: 18, bottom: 30, borderColor: 'transparent', backgroundColor: 'rgba(148,163,184,0.15)' },
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
    yAxis: {
      type: 'value',
      axisLabel: { color: '#475569' },
      splitLine: { lineStyle: { type: 'dashed', color: 'rgba(148, 163, 184, 0.35)' } },
    },
    series,
  }
})

function toggleTimelineMetric(metricKey) {
  const list = [...activeTimelineMetricKeys.value]
  const index = list.indexOf(metricKey)
  if (index >= 0) {
    if (list.length === 1) {
      return
    }
    list.splice(index, 1)
  } else {
    list.push(metricKey)
  }
  activeTimelineMetricKeys.value = list
}

function isTimelineMetricActive(metricKey) {
  return activeTimelineMetricKeys.value.includes(metricKey)
}

const shortConfig = computed(() => {
  if (!pageConfig.value) return ''
  const idx = pageConfig.value.lastIndexOf('/')
  return idx >= 0 ? pageConfig.value.slice(idx + 1) : pageConfig.value
})

function resolveUnitLabel(unitKey) {
  if (!unitKey) return '—'
  return unitDict.value[unitKey] || unitKey
}

const activeUnitLabel = computed(() => resolveUnitLabel(activeUnit.value || selectedUnits.value[0] || ''))
const analysisModeLabel = computed(() => {
  const found = analysisModes.value.find((item) => item.value === analysisMode.value)
  return found?.label || (analysisMode.value === 'daily' ? '单日数据' : '累计数据')
})

const viewLabelMap = { daily: '单日数据', range: '累计数据' }
const unitViewNames = computed(() => {
  const names = new Set()
  const mapping = viewMapping.value || {}
  Object.values(mapping).forEach((entry) => {
    if (entry && typeof entry === 'object') {
      Object.keys(entry).forEach((view) => {
        if (view) names.add(view)
      })
    }
  })
  return names
})
function resolveViewNameForUnit(unitKey) {
  const label = resolveUnitLabel(unitKey)
  const modeLabel = viewLabelMap[analysisMode.value] || analysisModeLabel.value
  const target = viewMapping.value[modeLabel]
  if (target && typeof target === 'object') {
    for (const [viewName, units] of Object.entries(target)) {
      if (Array.isArray(units) && units.includes(label)) {
        return viewName
      }
    }
  }
  return analysisMode.value === 'daily' ? 'company_daily_analysis' : 'company_sum_analysis'
}

const activeViewName = computed(() => resolveViewNameForUnit(activeUnit.value || selectedUnits.value[0] || ''))
const resultUnitKeys = computed(() => {
  const ordered = selectedUnits.value.filter((key) => unitResults.value[key])
  const leftovers = Object.keys(unitResults.value).filter((key) => !ordered.includes(key))
  return [...ordered, ...leftovers]
})

const resolvedMetricGroups = computed(() => {
  const activeView = activeViewName.value
  const unitViews = unitViewNames.value
  return metricGroups.value.map((group) => {
    const allowedViews = metricGroupViews.value?.[group.key] || []
    const referencesUnitView = allowedViews.some((view) => unitViews.has(view))
    const disabled =
      allowedViews.length > 0 &&
      referencesUnitView &&
      !['constant', 'temperature'].includes(group.key) &&
      !allowedViews.includes(activeView)
    return { ...group, disabled }
  })
})

const availableMetricKeys = computed(() => {
  const bucket = new Set()
  resolvedMetricGroups.value.forEach((group) => {
    if (group.disabled || !Array.isArray(group.options)) return
    group.options.forEach((option) => {
      if (option?.value) bucket.add(option.value)
    })
  })
  return bucket
})

const breadcrumbProjectPath = computed(
  () => `/projects/${encodeURIComponent(projectKey.value)}/pages/${encodeURIComponent(pageKey.value)}`,
)

async function loadSchema() {
  loading.value = true
  errorMessage.value = ''
  try {
    const payload = await getDataAnalysisSchema(projectKey.value, { config: pageConfig.value })
    if (!payload?.ok) {
      throw new Error(payload?.message || '配置加载失败')
    }
    schema.value = payload
    const availableUnits = resolveUnitOptions(payload)
    const defaultUnit = availableUnits?.[0]?.value || ''
    selectedUnits.value = defaultUnit ? [defaultUnit] : []
    activeUnit.value = defaultUnit || ''
    selectedMetrics.value = new Set()
    analysisMode.value = payload.analysis_modes?.[0]?.value || 'daily'
    await ensureDefaultBizDate()
    applyDateDefaults(payload.date_defaults)
    clearPreviewState()
  } catch (err) {
    errorMessage.value = err?.message || '数据分析配置加载失败'
  } finally {
    loading.value = false
  }
}

async function loadDefaultBizDate() {
  const today = new Date().toISOString().slice(0, 10)
  try {
    const payload = await getDashboardBizDate(projectKey.value)
    const fromApi =
      typeof payload?.set_biz_date === 'string' ? payload.set_biz_date.trim() : ''
    defaultBizDate.value = fromApi || today
  } catch (err) {
    console.warn('[data-analysis] 获取业务日期失败', err)
    defaultBizDate.value = today
  }
  return defaultBizDate.value
}

async function ensureDefaultBizDate() {
  if (defaultBizDate.value) {
    return defaultBizDate.value
  }
  return loadDefaultBizDate()
}

function applyDateDefaults(defaults = {}) {
  const fallbackDate = defaultBizDate.value || new Date().toISOString().slice(0, 10)
  const start =
    typeof defaults?.起始日期 === 'string' && defaults.起始日期 ? defaults.起始日期 : fallbackDate
  startDate.value = start
  endDate.value =
    typeof defaults?.结束日期 === 'string' && defaults.结束日期 ? defaults.结束日期 : start
}

function toggleMetric(key) {
  const next = new Set(selectedMetrics.value)
  if (next.has(key)) {
    next.delete(key)
  } else {
    next.add(key)
  }
  selectedMetrics.value = next
}

function selectAllMetrics() {
  if (!availableMetricKeys.value.size) {
    formError.value = '当前视图暂无可选指标。'
    return
  }
  selectedMetrics.value = new Set(availableMetricKeys.value)
}

function clearMetrics() {
  selectedMetrics.value = new Set()
}

function clearPreviewState() {
  previewRows.value = []
  infoBanner.value = ''
  queryWarnings.value = []
  lastQueryMeta.value = null
  timelineGrid.value = { columns: [], rows: [] }
  unitResults.value = {}
  if (!selectedUnits.value.includes(activeUnit.value)) {
    activeUnit.value = selectedUnits.value[0] || ''
  }
}

function resetSelections() {
  if (unitOptions.value.length) {
    selectedUnits.value = [unitOptions.value[0].value]
    activeUnit.value = selectedUnits.value[0]
  } else {
    selectedUnits.value = []
    activeUnit.value = ''
  }
  selectedMetrics.value = new Set()
  applyDateDefaults(schema.value?.date_defaults || {})
  formError.value = ''
  clearPreviewState()
}

async function runAnalysis() {
  formError.value = ''
  const targetUnits = Array.from(new Set(selectedUnits.value.filter((unit) => unit && typeof unit === 'string')))
  if (!targetUnits.length) {
    formError.value = '请选择至少一个单位。'
    return
  }
  if (!selectedMetrics.value.size) {
    formError.value = '至少选择一个指标。'
    return
  }
  if (!startDate.value || !endDate.value) {
    formError.value = '请选择起止日期。'
    return
  }
  clearPreviewState()
  queryLoading.value = true
  try {
    const runMetrics = Array.from(selectedMetrics.value)
    const requestBase = {
      metrics: runMetrics,
      analysis_mode: analysisMode.value,
      start_date: startDate.value,
      end_date: endDate.value,
    }
    const aggregatedResults = {}
    const errors = []
    for (const unitKey of targetUnits) {
      const payload = { ...requestBase, unit_key: unitKey }
      try {
        const response = await runDataAnalysis(projectKey.value, payload, { config: pageConfig.value })
        if (!response?.ok) {
          throw new Error(response?.message || '分析查询失败')
        }
        const decoratedRows = Array.isArray(response.rows)
          ? response.rows.map((row) => ({
              ...row,
              decimals: metricDecimalsMap.value?.[row.key] ?? 2,
            }))
          : []
        const meta = {
          unit_key: unitKey,
          unit_label: response.unit_label || resolveUnitLabel(unitKey),
          analysis_mode_label: response.analysis_mode_label || analysisModeLabel.value,
          view: response.view || resolveViewNameForUnit(unitKey),
          start_date: response.start_date || startDate.value,
          end_date: response.end_date || endDate.value,
        }
        aggregatedResults[unitKey] = {
          rows: decoratedRows,
          warnings: Array.isArray(response.warnings) ? response.warnings : [],
          timeline: buildTimelineGrid(decoratedRows),
          infoBanner: buildInfoBannerFromMeta(meta),
          meta,
        }
      } catch (err) {
        errors.push(`${resolveUnitLabel(unitKey)}：${err instanceof Error ? err.message : String(err)}`)
      }
    }
    const populatedKeys = Object.keys(aggregatedResults)
    if (!populatedKeys.length) {
      throw new Error(errors.join('；') || '分析查询失败')
    }
    unitResults.value = aggregatedResults
    const nextActiveCandidate =
      activeUnit.value && aggregatedResults[activeUnit.value] && targetUnits.includes(activeUnit.value)
        ? activeUnit.value
        : targetUnits.find((unit) => aggregatedResults[unit]) || ''
    applyActiveUnitResult(nextActiveCandidate || '')
    formError.value = errors.length ? errors.join('；') : ''
  } catch (err) {
    formError.value = err instanceof Error ? err.message : '分析查询失败'
    clearPreviewState()
  } finally {
    queryLoading.value = false
  }
}

function buildInfoBannerFromMeta(meta) {
  if (!meta) return ''
  const dateRange =
    meta.start_date && meta.end_date
      ? meta.start_date === meta.end_date
        ? meta.start_date
        : `${meta.start_date} ~ ${meta.end_date}`
      : meta.start_date || meta.end_date || ''
  return [
    meta.analysis_mode_label,
    `单位：${meta.unit_label}`,
    dateRange ? `日期：${dateRange}` : null,
  ]
    .filter(Boolean)
    .join(' ｜ ')
}

function applyActiveUnitResult(unitKey) {
  if (!unitKey || !unitResults.value[unitKey]) {
    previewRows.value = []
    infoBanner.value = ''
    queryWarnings.value = []
    lastQueryMeta.value = null
    timelineGrid.value = { columns: [], rows: [] }
    activeUnit.value = ''
    return
  }
  const result = unitResults.value[unitKey]
  previewRows.value = result.rows
  infoBanner.value = result.infoBanner
  queryWarnings.value = result.warnings
  lastQueryMeta.value = result.meta
  timelineGrid.value = result.timeline
  activeUnit.value = unitKey
}

function ensureActiveUnitFromSelection() {
  if (activeUnit.value && selectedUnits.value.includes(activeUnit.value)) {
    return
  }
  activeUnit.value = selectedUnits.value[0] || ''
}

function handleSwitchUnit(unitKey) {
  if (!unitKey || unitKey === activeUnit.value) return
  if (!unitResults.value[unitKey]) return
  applyActiveUnitResult(unitKey)
}

function handleUnitSelection(unitKey, checked) {
  const next = [...selectedUnits.value]
  const exists = next.indexOf(unitKey)
  if (checked && exists === -1) {
    next.push(unitKey)
  } else if (!checked && exists !== -1) {
    next.splice(exists, 1)
  }
  selectedUnits.value = next
}

function getUnitSelectionOrder(unitKey) {
  const index = selectedUnits.value.indexOf(unitKey)
  if (index === -1) return ''
  return String(index + 1)
}

function getMetricSelectionOrder(metricKey) {
  const order = Array.from(selectedMetrics.value)
  const index = order.indexOf(metricKey)
  if (index === -1) return ''
  return String(index + 1)
}

function formatNumber(value, decimals = 2) {
  if (value === null || value === undefined) return '—'
  const num = Number(value)
  if (Number.isNaN(num)) return '—'
  return num.toLocaleString('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

function formatDelta(value) {
  if (value === null || value === undefined) return '—'
  const num = Number(value)
  if (Number.isNaN(num)) return '—'
  const sign = num > 0 ? '+' : ''
  return `${sign}${num.toFixed(2)}%`
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

function resolveValue(row, field) {
  const totalKey = `total_${field}`
  if (analysisMode.value === 'range' && row[totalKey] !== undefined && row[totalKey] !== null) {
    return row[totalKey]
  }
  return row[field]
}

function resolveDelta(row) {
  if (analysisMode.value === 'range' && row.total_delta !== undefined && row.total_delta !== null) {
    return row.total_delta
  }
  return row.delta
}

function applyDecimals(value, decimals = 2) {
  if (value === null || value === undefined) return null
  const num = Number(value)
  if (Number.isNaN(num)) return null
  return Number(num.toFixed(decimals))
}

function formatPercentValue(value) {
  if (value === null || value === undefined) return null
  const num = Number(value)
  if (Number.isNaN(num)) return null
  return `${num.toFixed(2)}%`
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

function getDeltaColor(deltaNumber) {
  if (deltaNumber === null || deltaNumber === undefined || Number.isNaN(deltaNumber)) {
    return 'var(--neutral-600, #5f6368)'
  }
  return deltaNumber >= 0 ? 'var(--danger-600, #d93025)' : 'var(--success-600, #0f9d58)'
}

const timelineDeltaCellTemplate = (createElement, props) => {
  const rawValue = props?.model?.[props.prop]
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
  const style = { color: getDeltaColor(deltaNumber) }
  return createElement('span', { style }, text || '—')
}

function extractTimelineCellText(value) {
  if (value && typeof value === 'object') {
    return value.text ?? ''
  }
  return value ?? ''
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
    sumCurrent: 0,
    sumPeer: 0,
    valueType: row.value_type || 'analysis',
    totalCurrent: row.total_current ?? null,
    totalPeer: row.total_peer ?? null,
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
      const currentFormatted = current !== null ? applyDecimals(current, row.decimals) : null
      const peerFormatted = peer !== null ? applyDecimals(peer, row.decimals) : null
      record[`${row.key}__current`] = currentFormatted
      record[`${row.key}__peer`] = peerFormatted
      const hasPeer = peer !== null && peer !== undefined
      const deltaValue = hasPeer && peer !== 0 ? (((current ?? 0) - peer) / peer) * 100 : null
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
      } else if (row.valueType === 'analysis') {
        totalCurrent = row.sumCurrent || null
      } else {
        totalCurrent = row.sumCurrent || null
      }
    }
    if (totalPeer == null) {
      if (row.valueType === 'constant' && row.timeline && row.timeline.length) {
        totalPeer = row.timeline[0]?.peer ?? null
      } else if (row.valueType === 'analysis') {
        totalPeer = row.sumPeer || null
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

function formatExportNumber(value, decimals = 2) {
  if (value === null || value === undefined || value === '—') return ''
  const num = Number(value)
  if (Number.isNaN(num)) return value
  return Number(num.toFixed(decimals))
}

function buildSummarySheetData(rows) {
  const header = ['指标', '本期', '同期', '同比', '单位', '类型']
  const source = Array.isArray(rows) ? rows : []
  const mapped = source.map((row) => [
    row.label,
    formatExportNumber(resolveValue(row, 'current'), row.decimals || 2),
    formatExportNumber(resolveValue(row, 'peer'), row.decimals || 2),
    formatPercentValue(resolveDelta(row)) || '',
    row.unit || '',
    row.value_type || '',
  ])
  return [header, ...mapped]
}

function buildTimelineSheetData(timeline) {
  if (!timeline || !Array.isArray(timeline.columns) || !timeline.columns.length) return null
  const columns = timeline.columns
  const header = columns.map((col) => col.name || col.prop)
  const rows = (timeline.rows || []).map((record) =>
    columns.map((col) => extractTimelineCellText(record[col.prop])),
  )
  return [header, ...rows]
}

function buildMetaSheetData(meta) {
  const data = [
    ['项目', pageDisplayName.value],
    ['单位', meta?.unit_label || activeUnitLabel.value],
    ['分析模式', meta?.analysis_mode_label || analysisModeLabel.value],
    [
      '日期范围',
      meta && meta.start_date && meta.end_date ? `${meta.start_date} ~ ${meta.end_date}` : `${startDate.value} ~ ${endDate.value}`,
    ],
    ['生成时间', new Date().toLocaleString()],
    ['指标数量', selectedMetrics.value.size],
  ]
  return data
}

function buildUnitSheetData(result) {
  const sheetData = []
  const summary = buildSummarySheetData(result?.rows)
  summary.forEach((row) => sheetData.push(row))
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

function resolveSheetName(baseName, usedNames) {
  const sanitized = sanitizeSheetName(baseName)
  if (!usedNames.has(sanitized)) {
    usedNames.add(sanitized)
    return sanitized
  }
  let counter = 2
  while (true) {
    const candidate = sanitizeSheetName(`${sanitized}_${counter}`)
    if (!usedNames.has(candidate)) {
      usedNames.add(candidate)
      return candidate
    }
    counter += 1
  }
}

function downloadExcel() {
  if (!resultUnitKeys.value.length) return
  const wb = XLSX.utils.book_new()
  const usedSheetNames = new Set()
  resultUnitKeys.value.forEach((unitKey) => {
    const result = unitResults.value[unitKey]
    if (!result) return
    const unitName = result.meta?.unit_label || resolveUnitLabel(unitKey)
    const sheet = XLSX.utils.aoa_to_sheet(buildUnitSheetData(result))
    const sheetName = resolveSheetName(unitName, usedSheetNames)
    XLSX.utils.book_append_sheet(wb, sheet, sheetName)
  })
  const filename = `数据分析_${analysisMode.value === 'range' ? '累计' : '单日'}_${Date.now()}.xlsx`
  XLSX.writeFile(wb, filename)
}

watch(
  () => analysisMode.value,
  (mode) => {
    if (mode === 'daily') {
      endDate.value = startDate.value
    }
    clearPreviewState()
  },
)

watch(
  () => startDate.value,
  (value, oldValue) => {
    if (!value) return
    if (analysisMode.value === 'daily') {
      endDate.value = value
    } else if (endDate.value && value > endDate.value) {
      endDate.value = value
    }
    if (value !== oldValue) {
      clearPreviewState()
    }
  },
)

watch(
  () => endDate.value,
  (value, oldValue) => {
    if (!value) return
    if (analysisMode.value === 'daily' && value !== startDate.value) {
      startDate.value = value
    }
    if (value !== oldValue) {
      clearPreviewState()
    }
  },
)

watch(
  selectedUnits,
  () => {
    ensureActiveUnitFromSelection()
    clearPreviewState()
  },
  { deep: true },
)

watch(
  () => selectedMetrics.value,
  () => {
    clearPreviewState()
  },
  { deep: true },
)

watch(
  resolvedMetricGroups,
  () => {
    if (!selectedMetrics.value.size) return
    const allowed = availableMetricKeys.value
    if (!allowed.size) {
      selectedMetrics.value = new Set()
      clearPreviewState()
      return
    }
    const filtered = new Set([...selectedMetrics.value].filter((key) => allowed.has(key)))
    if (filtered.size !== selectedMetrics.value.size) {
      selectedMetrics.value = filtered
      clearPreviewState()
    }
  },
  { deep: true },
)

onMounted(() => {
  loadSchema()
})
</script>

<style scoped>
.analysis-main {
  padding: 24px;
  max-width: 1100px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.analysis-block {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.analysis-subtitle {
  margin-top: 6px;
  font-size: 14px;
  color: var(--neutral-500);
}

.analysis-tag {
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--primary-50);
  color: var(--primary-600);
  font-size: 12px;
  font-weight: 600;
  align-self: flex-start;
}

.form-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.form-grid--top {
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  align-items: stretch;
}

.form-panel {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-panel--metrics {
  width: 100%;
}

.form-panel--compact {
  min-height: 220px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.panel-header h3 {
  font-size: 16px;
  font-weight: 600;
}

.panel-hint {
  font-size: 13px;
  color: var(--neutral-500);
}

.panel-hint.warning {
  color: var(--warning-600, #b45309);
}

.panel-hint.muted {
  color: var(--neutral-400);
}

.panel-actions {
  display: flex;
  gap: 8px;
}

.chip-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 6px 14px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  cursor: pointer;
  user-select: none;
}

.chip input {
  accent-color: var(--primary-600);
}

.chip.radio {
  background: var(--card-bg);
}

.chip.checkbox {
  border-radius: var(--radius);
}

.chip-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.chip-order {
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background: var(--primary-50);
  color: var(--primary-700);
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--primary-100);
}

.chip.compact {
  padding: 4px 10px;
}

.metrics-panel-body {
  max-height: 420px;
  overflow-y: auto;
  padding-right: 6px;
}

.metrics-groups {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.metrics-group {
  border: 1px dashed var(--border);
  border-radius: var(--radius);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.metrics-group--disabled {
  opacity: 0.6;
}

.metrics-group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.metrics-group-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.metrics-group-header h4 {
  font-size: 14px;
  font-weight: 600;
  margin: 0;
}

.metrics-group-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.group-badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--neutral-100);
  color: var(--neutral-600);
}

.group-badge--outline {
  border: 1px solid var(--primary-200);
  color: var(--primary-600);
  background: transparent;
}

.group-badge--temp {
  background: var(--info-50, #eff6ff);
  color: var(--info-600, #2563eb);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px;
  max-height: 280px;
  overflow-y: auto;
  padding-right: 4px;
}

.date-subsection {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--border-light, rgba(0, 0, 0, 0.05));
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.date-subsection .panel-header {
  padding: 0;
}

.date-subsection h4 {
  font-size: 14px;
  margin: 0;
  font-weight: 600;
}

.date-subsection .date-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.date-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: var(--neutral-600);
}

.date-field input {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 8px;
}

.mode-desc {
  font-size: 13px;
  color: var(--neutral-600);
  margin-top: -4px;
}

.form-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.result-block {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-table {
  width: 100%;
  border-collapse: collapse;
}

.result-table th,
.result-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  text-align: left;
  font-size: 14px;
}

.result-table th {
  background: var(--neutral-50);
  color: var(--neutral-700);
}

.warning-list {
  margin: 4px 0 0;
  padding-left: 18px;
  color: var(--warning-600, #b45309);
  font-size: 13px;
}

.unit-switch {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.unit-switch__label {
  color: var(--neutral-500);
  font-size: 14px;
}

.unit-switch__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.unit-toggle {
  border: 1px solid var(--neutral-200);
  background: var(--neutral-50);
  color: var(--neutral-700);
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.unit-toggle:hover {
  border-color: var(--primary-300);
  color: var(--primary-700);
}

.unit-toggle.active {
  background: var(--primary-50);
  border-color: var(--primary-400);
  color: var(--primary-700);
  font-weight: 600;
}

.timeline-grid-wrapper {
  width: 100%;
  overflow: hidden;
}

.timeline-grid {
  height: 420px;
}

.timeline-chart-panel {
  margin-top: 20px;
  padding: 16px;
  border: 1px solid var(--neutral-100);
  border-radius: var(--radius);
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.timeline-chart-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.timeline-chart-toolbar__info h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.timeline-chart-toolbar__metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
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

.timeline-chart-empty {
  padding: 18px;
  border: 1px dashed var(--neutral-200);
  border-radius: var(--radius);
  text-align: center;
  color: var(--neutral-500);
  font-size: 14px;
}

.chart-tooltip__title {
  font-weight: 700;
  margin-bottom: 8px;
}

.chart-tooltip__item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  line-height: 1.6;
}

.chart-tooltip__dot {
  display: inline-flex;
  width: 10px;
  height: 10px;
  border-radius: 999px;
}

.chart-tooltip__delta {
  margin-left: 6px;
  color: var(--danger-100, #fecdd3);
  font-weight: 600;
}

.metric-label {
  display: flex;
  align-items: center;
  gap: 6px;
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

.value-cell {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.value-number {
  font-weight: 600;
}

.value-unit {
  font-size: 12px;
  color: var(--neutral-500);
}

.result-row--missing .value-number {
  color: var(--neutral-400);
}

.delta-up {
  color: var(--danger-600, #d93025);
}

.delta-down {
  color: var(--success-600, #0f9d58);
}

.page-state {
  padding: 24px;
  text-align: center;
  border-radius: var(--radius);
}

.page-state.error {
  color: var(--danger-600, #d93025);
  background: var(--danger-50, #fdeaea);
}

.page-state.muted {
  color: var(--neutral-500);
}

.info-banner {
  padding: 12px 16px;
  border-radius: var(--radius);
  background: var(--primary-50);
  color: var(--primary-700);
  font-size: 14px;
  margin-bottom: 12px;
}

.btn.xs {
  font-size: 12px;
  padding: 4px 10px;
}
</style>
