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
          <div class="form-grid">
            <div class="form-panel form-panel--compact">
              <div class="panel-header">
                <h3>单位选择（单选）</h3>
                <span class="panel-hint">共 {{ unitOptions.length }} 个可选单位</span>
              </div>
              <div class="chip-group">
                <label
                  v-for="unit in unitOptions"
                  :key="unit.value"
                  class="chip radio"
                >
                  <input
                    type="radio"
                    name="unit"
                    :value="unit.value"
                    v-model="selectedUnit"
                  />
                  <span>{{ unit.label }}</span>
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

            <div class="form-panel">
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
                        <span>{{ metric.label }}</span>
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
                单位：{{ unitLabel }} ｜ 指标数：{{ selectedMetrics.size }}
              </template>
            </p>
          </div>
          <button
            class="btn ghost"
            type="button"
            :disabled="!previewRows.length || queryLoading"
            @click="downloadExcel"
          >
            下载 Excel
          </button>
        </header>

        <div v-if="queryLoading" class="page-state">正在生成分析结果，请稍候…</div>
        <div v-else-if="!previewRows.length" class="page-state muted">
          请选择单位、指标与日期后点击“生成分析结果”，即可在此查看组合预览。
        </div>
        <div v-else>
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
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import RevoGrid from '@revolist/vue3-datagrid'
import * as XLSX from 'xlsx'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { getProjectNameById } from '../composables/useProjects'
import { getDataAnalysisSchema, runDataAnalysis } from '../services/api'

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

const selectedUnit = ref('')
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

const startDate = ref('')
const endDate = ref('')
const previewRows = ref([])
const infoBanner = ref('')
const formError = ref('')
const queryWarnings = ref([])
const lastQueryMeta = ref(null)
const queryLoading = ref(false)
const timelineGrid = ref({ columns: [], rows: [] })

const shortConfig = computed(() => {
  if (!pageConfig.value) return ''
  const idx = pageConfig.value.lastIndexOf('/')
  return idx >= 0 ? pageConfig.value.slice(idx + 1) : pageConfig.value
})

const unitLabel = computed(() => unitDict.value[selectedUnit.value] || selectedUnit.value || '—')
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
const activeViewName = computed(() => {
  const label = unitDict.value[selectedUnit.value] || selectedUnit.value
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
    selectedUnit.value = availableUnits?.[0]?.value || ''
    selectedMetrics.value = new Set()
    analysisMode.value = payload.analysis_modes?.[0]?.value || 'daily'
    applyDateDefaults(payload.date_defaults)
    clearPreviewState()
  } catch (err) {
    errorMessage.value = err?.message || '数据分析配置加载失败'
  } finally {
    loading.value = false
  }
}

function applyDateDefaults(defaults = {}) {
  const today = new Date().toISOString().slice(0, 10)
  startDate.value = typeof defaults?.起始日期 === 'string' && defaults.起始日期 ? defaults.起始日期 : today
  endDate.value = typeof defaults?.结束日期 === 'string' && defaults.结束日期 ? defaults.结束日期 : startDate.value
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
}

function resetSelections() {
  if (unitOptions.value.length) selectedUnit.value = unitOptions.value[0].value
  selectedMetrics.value = new Set()
  applyDateDefaults(schema.value?.date_defaults || {})
  formError.value = ''
  clearPreviewState()
}

async function runAnalysis() {
  formError.value = ''
  if (!selectedUnit.value) {
    formError.value = '请选择单位。'
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
  const payload = {
    unit_key: selectedUnit.value,
    metrics: Array.from(selectedMetrics.value),
    analysis_mode: analysisMode.value,
    start_date: startDate.value,
    end_date: endDate.value,
  }
  clearPreviewState()
  queryLoading.value = true
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
    previewRows.value = decoratedRows
    lastQueryMeta.value = {
      analysis_mode_label: response.analysis_mode_label || analysisModeLabel.value,
      view: response.view || activeViewName.value,
      start_date: response.start_date || startDate.value,
      end_date: response.end_date || endDate.value,
      unit_label: response.unit_label || unitLabel.value,
    }
    queryWarnings.value = Array.isArray(response.warnings) ? response.warnings : []
    timelineGrid.value = buildTimelineGrid(previewRows.value)
    const dateRange =
      lastQueryMeta.value.start_date && lastQueryMeta.value.end_date
        ? lastQueryMeta.value.start_date === lastQueryMeta.value.end_date
          ? lastQueryMeta.value.start_date
          : `${lastQueryMeta.value.start_date} ~ ${lastQueryMeta.value.end_date}`
        : lastQueryMeta.value.start_date || lastQueryMeta.value.end_date || ''
    infoBanner.value = [
      lastQueryMeta.value.analysis_mode_label,
      `单位：${lastQueryMeta.value.unit_label}`,
      dateRange ? `日期：${dateRange}` : null,
    ]
      .filter(Boolean)
      .join(' ｜ ')
  } catch (err) {
    formError.value = err?.message || '分析查询失败'
    clearPreviewState()
  } finally {
    queryLoading.value = false
  }
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
    const totalCurrent = row.sumCurrent || null
    const totalPeer = row.sumPeer || null
    totalRecord[`${row.key}__current`] = totalCurrent !== null ? applyDecimals(totalCurrent, row.decimals) : null
    totalRecord[`${row.key}__peer`] = totalPeer !== null ? applyDecimals(totalPeer, row.decimals) : null
    const totalDelta = totalPeer ? ((totalCurrent - totalPeer) / totalPeer) * 100 : null
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

function buildSummarySheetData() {
  const header = ['指标', '本期', '同期', '同比', '单位', '类型']
  const rows = previewRows.value.map((row) => [
    row.label,
    formatExportNumber(resolveValue(row, 'current'), row.decimals || 2),
    formatExportNumber(resolveValue(row, 'peer'), row.decimals || 2),
    formatPercentValue(resolveDelta(row)) || '',
    row.unit || '',
    row.value_type || '',
  ])
  return [header, ...rows]
}

function buildTimelineSheetData() {
  if (!hasTimelineGrid.value) return null
  const columns = timelineGrid.value.columns || []
  const header = columns.map((col) => col.name || col.prop)
  const rows = (timelineGrid.value.rows || []).map((record) =>
    columns.map((col) => extractTimelineCellText(record[col.prop])),
  )
  return [header, ...rows]
}

function buildMetaSheetData() {
  const data = [
    ['项目', pageDisplayName.value],
    ['单位', unitLabel.value],
    ['分析模式', analysisModeLabel.value],
    ['日期范围', lastQueryMeta.value ? `${lastQueryMeta.value.start_date} ~ ${lastQueryMeta.value.end_date}` : `${startDate.value} ~ ${endDate.value}`],
    ['生成时间', new Date().toLocaleString()],
    ['指标数量', selectedMetrics.value.size],
  ]
  return data
}

function downloadExcel() {
  if (!previewRows.value.length) return
  const wb = XLSX.utils.book_new()
  const summarySheet = XLSX.utils.aoa_to_sheet(buildSummarySheetData())
  XLSX.utils.book_append_sheet(wb, summarySheet, '汇总')
  const timelineData = buildTimelineSheetData()
  if (timelineData) {
    const timelineSheet = XLSX.utils.aoa_to_sheet(timelineData)
    XLSX.utils.book_append_sheet(wb, timelineSheet, '区间明细')
  }
  const metaSheet = XLSX.utils.aoa_to_sheet(buildMetaSheetData())
  XLSX.utils.book_append_sheet(wb, metaSheet, '查询信息')
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

watch(selectedUnit, () => {
  clearPreviewState()
})

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

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.form-panel {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
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

.timeline-grid-wrapper {
  width: 100%;
  overflow: hidden;
}

.timeline-grid {
  height: 420px;
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
