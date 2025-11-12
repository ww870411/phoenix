<template>
  <div class="data-analysis-view">
    <AppHeader />
    <main class="analysis-main">
      <Breadcrumbs :items="breadcrumbItems" />

      <section class="card elevated analysis-block">
        <header class="card-header">
          <div>
            <h2>{{ pageDisplayName }}</h2>
            <p class="analysis-subtitle">
              项目：{{ projectName }} ｜ 数据源：{{ shortConfig || '默认配置' }}
            </p>
          </div>
          <span class="analysis-tag">Beta</span>
        </header>

        <div v-if="loading" class="page-state">配置加载中，请稍候…</div>
        <div v-else-if="errorMessage" class="page-state error">{{ errorMessage }}</div>

        <template v-else>
          <div class="form-grid">
            <div class="form-panel">
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

            <div class="form-panel">
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
              <p class="mode-desc">
                当前模式将使用视图：
                <strong>{{ activeViewName }}</strong>
              </p>
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
                <span v-if="hasConstantMetrics">｜ 常量指标来源于 constant_data 表，按日返回固定值</span>
              </p>
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
                      <button
                        class="btn ghost xs group-toggle"
                        type="button"
                        :disabled="queryLoading"
                        @click="toggleGroupCollapse(group.key)"
                      >
                        {{ collapsedMetricGroups.has(group.key) ? '展开' : '收起' }}
                      </button>
                    </div>
                  </div>
                  <p v-if="group.disabled" class="panel-hint warning">
                    当前视图不支持该组，请切换单位或分析模式。
                  </p>
                  <p
                    v-else-if="collapsedMetricGroups.has(group.key)"
                    class="panel-hint muted"
                  >
                    已折叠，点击“展开”查看指标。
                  </p>
                  <div v-show="!collapsedMetricGroups.has(group.key)" class="metrics-grid">
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
                {{ lastQueryMeta.analysis_mode_label || analysisModeLabel }} ｜ 视图：{{ lastQueryMeta.view }} ｜
                单位：{{ lastQueryMeta.unit_label }}
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
                视图：{{ activeViewName }} ｜ 单位：{{ unitLabel }} ｜ 指标数：{{ selectedMetrics.size }}
              </template>
            </p>
          </div>
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
                    <span class="value-number">{{ formatNumber(row.current) }}</span>
                    <span v-if="row.unit" class="value-unit">{{ row.unit }}</span>
                  </div>
                </td>
                <td>
                  <div class="value-cell">
                    <span class="value-number">{{ formatNumber(row.peer) }}</span>
                    <span v-if="row.unit" class="value-unit">{{ row.unit }}</span>
                  </div>
                </td>
                <td :class="row.delta === null ? '' : row.delta >= 0 ? 'delta-up' : 'delta-down'">
                  {{ formatDelta(row.delta) }}
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
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
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

const startDate = ref('')
const endDate = ref('')
const previewRows = ref([])
const infoBanner = ref('')
const formError = ref('')
const queryWarnings = ref([])
const lastQueryMeta = ref(null)
const queryLoading = ref(false)
const collapsedMetricGroups = ref(new Set())

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
    const collapsed = new Set()
    const groups = Array.isArray(payload.metric_groups) ? payload.metric_groups : []
    groups.forEach((group, index) => {
      const key = group?.key || `group_${index}`
      if (index !== 0 && key) {
        collapsed.add(key)
      }
    })
    collapsedMetricGroups.value = collapsed
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

function toggleGroupCollapse(key) {
  const next = new Set(collapsedMetricGroups.value)
  if (next.has(key)) {
    next.delete(key)
  } else {
    next.add(key)
  }
  collapsedMetricGroups.value = next
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
    previewRows.value = Array.isArray(response.rows) ? response.rows : []
    lastQueryMeta.value = {
      analysis_mode_label: response.analysis_mode_label || analysisModeLabel.value,
      view: response.view || activeViewName.value,
      start_date: response.start_date || startDate.value,
      end_date: response.end_date || endDate.value,
      unit_label: response.unit_label || unitLabel.value,
    }
    queryWarnings.value = Array.isArray(response.warnings) ? response.warnings : []
    const dateRange =
      lastQueryMeta.value.start_date && lastQueryMeta.value.end_date
        ? lastQueryMeta.value.start_date === lastQueryMeta.value.end_date
          ? lastQueryMeta.value.start_date
          : `${lastQueryMeta.value.start_date} ~ ${lastQueryMeta.value.end_date}`
        : lastQueryMeta.value.start_date || lastQueryMeta.value.end_date || ''
    infoBanner.value = [
      lastQueryMeta.value.analysis_mode_label,
      `视图：${lastQueryMeta.value.view}`,
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

function formatNumber(value) {
  if (value === null || value === undefined) return '—'
  const num = Number(value)
  if (Number.isNaN(num)) return '—'
  return num.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function formatDelta(value) {
  if (value === null || value === undefined) return '—'
  const num = Number(value)
  if (Number.isNaN(num)) return '—'
  const sign = num > 0 ? '+' : ''
  return `${sign}${num.toFixed(2)}%`
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
  color: var(--success-600, #0f9d58);
}

.delta-down {
  color: var(--danger-600, #d93025);
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
