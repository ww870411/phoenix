<template>
  <div class="approval-container">
    <AppHeader />
    <div class="container">
      <Breadcrumbs :items="breadcrumbItems" class="breadcrumb-spacing" />
      <header class="topbar">
        <div style="display:flex;flex-direction:column;gap:6px;">
          <h2>数据审批</h2>
          <div class="sub">项目：{{ projectName }} ｜ 表：{{ sheetDisplayName }}</div>
        </div>
        <div class="right" style="display:flex;align-items:center;gap:8px;">
          <label title="开启后返回详细求值轨迹" style="display:inline-flex;align-items:center;gap:6px;">
            <input type="checkbox" v-model="traceEnabled" />
            <span>Trace</span>
          </label>
          <label class="date-group" title="业务日期" style="display:inline-flex;align-items:center;gap:6px;">
            <span>业务日期：</span>
            <select v-model="bizDateMode">
              <option value="regular">regular（按昨日/同期）</option>
              <option value="custom">自定义</option>
            </select>
            <input v-if="bizDateMode==='custom'" type="date" v-model="bizDate" />
          </label>
          <button class="btn ghost" @click="runEval" :disabled="loading">刷新</button>
        </div>
      </header>

      <div class="table-wrap card" v-if="columns.length">
        <RevoGrid
          :row-headers="true"
          :hide-attribution="true"
          :stretch="true"
          :auto-size-column="false"
          :row-size="30"
          :resize="true"
          :range="true"
          :columns="gridColumns"
          :source="gridSource"
          style="height: 70vh; width: 100%;"
        />
      </div>
      <div v-else class="placeholder">无审批数据</div>
      <div v-if="traceEnabled && traceData" class="trace-panel card" style="margin-top:12px;">
        <details open>
          <summary style="cursor:pointer;">Trace 调试输出（仅本次响应）</summary>
          <pre class="trace-pre">{{ formattedTrace }}</pre>
        </details>
      </div>
      <div v-if="errorMessage" class="error">{{ errorMessage }}</div>
    </div>
  </div>
</template>

<script setup>
import '../styles/theme.css'
import RevoGrid from '@revolist/vue3-datagrid'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { evalSpec, getTemplate, getWorkflowStatus } from '../services/api'
import { ensureProjectsLoaded, getProjectNameById } from '../composables/useProjects'

const route = useRoute()
const router = useRouter()

const projectKey = computed(() => String(route.params.projectKey ?? ''))
const pageKey = computed(() => String(route.params.pageKey ?? ''))
const sheetKey = computed(() => String(route.params.sheetKey ?? ''))
const pageConfig = computed(() => {
  const raw = route.query.config
  return typeof raw === 'string' ? raw : ''
})
const pageDisplayName = computed(() => {
  const raw = route.query.pageName
  return typeof raw === 'string' && raw.trim() ? raw.trim() : (pageKey.value || '审批')
})

const projectName = computed(() => getProjectNameById(projectKey.value) ?? projectKey.value)
const sheetName = ref('')
const sheetDisplayName = computed(() => sheetName.value || sheetKey.value)
const columns = ref([])
const rows = ref([])

const gridColumns = ref([])
const gridSource = ref([])
const accuracy = ref(2)
const accuracyOverrides = ref({})
const numberFormat = ref({ grouping: false, locale: 'zh-CN' })
const traceEnabled = ref(false)
const traceData = ref(null)
const loading = ref(false)
const errorMessage = ref('')
const itemColumnIndex = ref(-1)

const bizDateMode = ref('regular')
const bizDate = ref('')
const regularBizDate = ref('')

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: projectName.value, to: `/projects/${encodeURIComponent(projectKey.value)}/pages` },
  { label: pageDisplayName.value, to: `/projects/${encodeURIComponent(projectKey.value)}/pages/${encodeURIComponent(pageKey.value)}/sheets?config=${encodeURIComponent(pageConfig.value)}&pageName=${encodeURIComponent(pageDisplayName.value)}` },
  { label: sheetDisplayName.value, to: null },
])

function ensureValidRoute() {
  if (!projectKey.value || !pageKey.value || !sheetKey.value || !pageConfig.value) {
    router.replace('/projects')
    return false
  }
  return true
}

const normalizeLabel = (value) => {
  if (typeof value === 'string') return value.trim()
  if (value === null || value === undefined) return ''
  return String(value).trim()
}

function detectItemColumnIndex(cols) {
  if (!Array.isArray(cols)) return -1
  for (let i = 0; i < cols.length; i += 1) {
    const label = normalizeLabel(cols[i])
    if (!label) continue
    if (label.includes('项目') || label.includes('指标') || label.includes('内容')) {
      return i
    }
  }
  if (cols.length > 1) return 1
  return cols.length ? 0 : -1
}

const clampAccuracy = (val) => {
  const n = Number(val)
  if (!Number.isInteger(n)) return null
  if (n < 0) return 0
  if (n > 8) return 8
  return n
}

async function loadAccuracyOverrides() {
  accuracyOverrides.value = {}
  try {
    const tpl = await getTemplate(projectKey.value, sheetKey.value, { config: pageConfig.value })
    const spec = tpl?.accuracy
    const overrides = {}
    if (typeof spec === 'number') {
      const c = clampAccuracy(spec)
      if (c !== null) accuracy.value = c
    } else if (spec && typeof spec === 'object') {
      if ('default' in spec) {
        const base = clampAccuracy(spec.default)
        if (base !== null) accuracy.value = base
      }
      for (const [key, rawVal] of Object.entries(spec)) {
        if (key === 'default') continue
        const c = clampAccuracy(rawVal)
        if (c !== null) {
          overrides[normalizeLabel(key)] = c
        }
      }
    }
    accuracyOverrides.value = overrides
  } catch (err) {
    console.warn('加载 accuracy 配置失败（保持默认精度）', err)
    accuracyOverrides.value = {}
  }
}

function buildReadOnlyColumns(cols) {
  const defs = (cols || []).map((name, index) => {
    const base = {
      prop: `c${index}`,
      name: String(name ?? ''),
      autoSize: true,
      minSize: index === 0 ? 160 : 120,
      readonly: true,
    }
    return base
  })
  gridColumns.value = defs
}

function buildSource(cols, rs) {
  const accFromNF = (nf) => (nf && Number.isInteger(nf.default) ? nf.default : null)
  const baseAcc = accFromNF(numberFormat.value) ?? (Number.isInteger(accuracy.value) ? accuracy.value : 2)
  const useGrouping = !!(numberFormat.value && numberFormat.value.grouping)
  const locale = (numberFormat.value && numberFormat.value.locale) || 'zh-CN'
  const overrides = accuracyOverrides.value || {}
  const nfCache = new Map()
  const getFormatter = (digits) => {
    const key = Number.isInteger(digits) ? digits : baseAcc
    if (!nfCache.has(key)) {
      let fmt = null
      try {
        fmt = new Intl.NumberFormat(locale, {
          useGrouping,
          minimumFractionDigits: key,
          maximumFractionDigits: key,
        })
      } catch {
        fmt = null
      }
      nfCache.set(key, fmt)
    }
    return nfCache.get(key)
  }
  const formatVal = (v, digits) => {
    if (v === null || v === undefined) return ''
    const s = String(v)
    if (s.includes('%')) return s // 差异列百分比
    if (s.trim() === '' || s === '-') return s
    const n = Number(s)
    if (!Number.isFinite(n)) return s
    const fmt = getFormatter(digits)
    if (fmt) {
      try { return fmt.format(n) } catch { /* fallthrough */ }
    }
    try { return n.toFixed(digits) } catch { return s }
  }
  const labelIndex = itemColumnIndex.value >= 0 ? itemColumnIndex.value : 0
  const src = (rs || []).map(row => {
    const rec = {}
    const labelRaw = Array.isArray(row) ? row[labelIndex] : ''
    const label = normalizeLabel(labelRaw)
    const rowAcc = Number.isInteger(overrides[label]) ? overrides[label] : baseAcc
    for (let i = 0; i < (cols?.length || 0); i++) {
      const v = Array.isArray(row) ? row[i] : ''
      rec[`c${i}`] = formatVal(v, rowAcc)
    }
    return rec
  })
  gridSource.value = src
}

async function runEval() {
  if (!ensureValidRoute()) return
  loading.value = true
  errorMessage.value = ''
  accuracyOverrides.value = {}
  itemColumnIndex.value = -1
  try {
    await ensureProjectsLoaded()
    if (bizDateMode.value === 'regular') {
      await ensureRegularBizDate()
    }
    const resolvedBizDate =
      bizDateMode.value === 'regular'
        ? regularBizDate.value || 'regular'
        : bizDate.value || 'regular'
    const body = {
      sheet_key: sheetKey.value,
      project_key: 'daily_report_25_26',
      // primary_key 可留空，后端会用模板 unit_id 补齐；如需按中心筛选可以加入 {company:'Xxx_Center'}
      config: pageConfig.value,
      biz_date: resolvedBizDate,
      trace: !!traceEnabled.value,
    }
    const res = await evalSpec(projectKey.value, body)
    if (!res || res.ok === false) {
      throw new Error(res?.message || 'runtime eval 失败')
    }
    sheetName.value = res.sheet_name || sheetKey.value
    columns.value = Array.isArray(res.columns) ? res.columns : []
    rows.value = Array.isArray(res.rows) ? res.rows : []
    if (Number.isInteger(res.accuracy)) accuracy.value = res.accuracy
    if (res.number_format && typeof res.number_format === 'object') numberFormat.value = res.number_format
    traceData.value = res.debug && res.debug._trace ? res.debug._trace : null

    let overridesApplied = false
    if (res.accuracy_overrides && typeof res.accuracy_overrides === 'object') {
      const overrides = {}
      for (const [key, rawVal] of Object.entries(res.accuracy_overrides)) {
        const normKey = normalizeLabel(key)
        const accVal = clampAccuracy(rawVal)
        if (normKey && accVal !== null) {
          overrides[normKey] = accVal
        }
      }
      accuracyOverrides.value = overrides
      overridesApplied = Object.keys(overrides).length > 0
    }
    if (!overridesApplied) {
      await loadAccuracyOverrides()
    }
    itemColumnIndex.value = detectItemColumnIndex(columns.value)
    buildReadOnlyColumns(columns.value)
    buildSource(columns.value, rows.value)
  } catch (err) {
    console.error(err)
    errorMessage.value = err?.message || String(err)
  } finally {
    loading.value = false
  }
}

onMounted(runEval)
watch([bizDateMode, bizDate, traceEnabled], runEval)

const formattedTrace = computed(() => {
  try { return JSON.stringify(traceData.value, null, 2) } catch { return '' }
})

async function ensureRegularBizDate() {
  if (regularBizDate.value) return
  try {
    const status = await getWorkflowStatus(projectKey.value)
    const biz = status?.biz_date
    if (biz) {
      regularBizDate.value = biz
    }
  } catch (err) {
    console.warn('加载默认业务日期失败，将继续使用 regular', err)
  }
}
</script>

<style scoped>
.container { padding: 16px; }
.topbar { display:flex; align-items:center; justify-content:space-between; margin-bottom: 12px; }
.sub { color: #666; font-size: 13px; }
.placeholder { color:#888; padding: 20px 0; text-align:center; }
.error { color: #c00; margin-top: 10px; }
.trace-pre { max-height: 360px; overflow: auto; background: #0b0b0b; color: #d6d6d6; padding: 12px; border-radius: 6px; }
</style>
