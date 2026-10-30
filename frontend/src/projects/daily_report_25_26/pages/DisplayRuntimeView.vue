<template>
  <div class="display-container">
    <AppHeader />
    <div class="container">
      <Breadcrumbs :items="breadcrumbItems" class="breadcrumb-spacing" />
      <header class="topbar">
        <div class="topbar-heading">
          <h2>{{ unitGroupName ? `${unitGroupName} 数据展示` : '数据展示' }}</h2>
          <div class="sub">项目：{{ projectName }} ｜ 表：{{ sheetDisplayName }}</div>
        </div>
        <div class="right">
          <label class="trace-toggle" title="开启后返回详细求值轨迹">
            <input type="checkbox" v-model="traceEnabled" />
            <span>Trace</span>
          </label>
          <label class="date-group" title="业务日期">
            <span>业务日期：</span>
            <input type="date" v-model="bizDate" />
            <span class="hint" v-if="effectiveBizDate">当前：{{ effectiveBizDate }}</span>
            <span class="hint" v-else>当前：regular</span>
          </label>
          <button class="btn ghost" @click="runEval" :disabled="loading">刷新</button>

          <!-- 截图导出按钮组 -->
          <div class="screenshot-btn-group">
            <button
              class="btn"
              type="button"
              @click="exportAllScreenshots"
              :disabled="isCapturing || isExporting || loading"
              title="一键生成并下载3张展示表高清长截图（每表一张，直接用于微信/钉钉工作群汇报）"
              style="border-top-right-radius: 0; border-bottom-right-radius: 0; border-right: 1px solid rgba(255, 255, 255, 0.25);"
            >
              {{ isCapturing ? captureProgressText : '📷 导出截图' }}
            </button>
            <button
              class="btn"
              type="button"
              @click.stop="toggleScreenshotDropdown"
              :disabled="isCapturing || isExporting || loading"
              title="更多截图导出选项"
              style="border-top-left-radius: 0; border-bottom-left-radius: 0; padding: 0 8px; min-width: 28px;"
            >
              <span style="font-size: 10px; display: inline-block;">▼</span>
            </button>

            <!-- 截图下拉菜单 -->
            <div v-if="showScreenshotMenu" class="screenshot-dropdown-menu">
              <button type="button" class="screenshot-menu-item" @click="exportAllScreenshots">
                <div class="menu-item-title">🖼️ 一键导出全部展示表（3张）</div>
                <div class="menu-item-desc">自动截取并下载3张高清长图，推荐每日发群使用</div>
              </button>
              <button type="button" class="screenshot-menu-item" @click="exportCurrentScreenshotOnly">
                <div class="menu-item-title">📄 仅导出当前表截图（1张）</div>
                <div class="menu-item-desc">仅截取当前选中的 {{ cleanTabTitle(sheetDisplayName, unitGroupName) }}</div>
              </button>
            </div>
          </div>

          <button class="btn" @click="exportToExcel" :disabled="isExporting || isCapturing || loading">{{ isExporting ? '正在导出...' : '导出Excel' }}</button>
        </div>
      </header>

      <!-- 多表格单位现代分段标签栏 (Segmented Tabs) -->
      <div v-if="unitSheets.length > 1" class="unit-tabs-nav-wrapper">
        <div class="unit-tabs-nav" role="tablist" aria-label="单位所属展示表切换">
          <button
            v-for="s in unitSheets"
            :key="s.sheet_key"
            type="button"
            role="tab"
            :aria-selected="s.sheet_key === sheetKey"
            :class="['unit-tab-pill', { 'unit-tab-pill--active': s.sheet_key === sheetKey }]"
            @click="onSwitchSheetTab(s.sheet_key)"
          >
            <span class="tab-index" v-if="parseSheetNumber(s.sheet_name)">{{ parseSheetNumber(s.sheet_name) }}</span>
            <span class="tab-name">{{ cleanTabTitle(s.sheet_name, unitGroupName) }}</span>
          </button>
        </div>
      </div>

      <div class="table-wrap card" v-if="columns.length">
        <RevoGrid
          :row-headers="true"
          :hide-attribution="true"
          :stretch="true"
          :auto-size-column="false"
          :row-size="30"
          :resize="true"
          :range="true"
          :column-grouping="columnGrouping"
          :columns="gridColumns"
          :source="gridSource"
          style="height: 70vh; width: 100%;"
        />
      </div>
      <div v-else class="placeholder">{{ loading ? '数据载入中...' : '无展示数据' }}</div>
      <div v-if="traceEnabled && traceData" class="trace-panel card" style="margin-top:12px;">
        <details open>
          <summary style="cursor:pointer;">Trace 调试输出（仅本次响应）</summary>
          <pre class="trace-pre">{{ formattedTrace }}</pre>
        </details>
      </div>
      <div v-if="errorMessage" class="error">{{ errorMessage }}</div>

      <!-- 截图生成成功反馈 Toast -->
      <div v-if="captureToastMessage" class="capture-toast">
        <span class="toast-icon">✅</span>
        <span class="toast-text">{{ captureToastMessage }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import '../styles/theme.css'
import RevoGrid from '@revolist/vue3-datagrid'
import * as XLSX from 'xlsx-js-style'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { evalSpec, evalSpecsBatch, getTemplate, getWorkflowStatus, listSheets } from '../services/api'
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
  return typeof raw === 'string' && raw.trim() ? raw.trim() : (pageKey.value || '展示')
})

const projectName = computed(() => getProjectNameById(projectKey.value) ?? projectKey.value)
const sheetName = ref('')
const sheetDisplayName = computed(() => sheetName.value || sheetKey.value)
const unitSheets = ref([])
const unitGroupName = ref('')
const columns = ref([])
const rows = ref([])
const columnHeaders = ref([])
const columnGroups = ref([])

const gridColumns = ref([])
const gridSource = ref([])
const columnGrouping = ref(false)
const accuracy = ref(2)
const accuracyOverrides = ref({})
const numberFormat = ref({ grouping: false, locale: 'zh-CN' })
const traceEnabled = ref(false)
const traceData = ref(null)
const loading = ref(false)
const errorMessage = ref('')
const itemColumnIndex = ref(-1)

const bizDate = ref('')
const effectiveBizDate = ref('')
const initialized = ref(false)
const pendingAutoRefresh = ref(false)
const AUTO_REFRESH_DELAY_MS = 400
const EXPORT_EVAL_TIMEOUT_MS = 120000
const EXPORT_RETRY_DELAY_MS = 1200
let bizDateAutoRefreshTimer = null
let suppressNextBizDateReaction = false

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

function parseSheetNumber(name) {
  if (!name) return ''
  const m = String(name).match(/^(\d+)[\.、\s]*/)
  return m ? m[1] : ''
}

function cleanTabTitle(title, unitNameStr) {
  if (!title) return ''
  let s = String(title)
  s = s.replace(/^\d+[\.、\s]*/, '').trim()
  if (unitNameStr && s.includes(unitNameStr)) {
    const trimmed = s.replace(unitNameStr, '').trim()
    if (trimmed && trimmed !== '表' && trimmed !== '（表）' && trimmed !== '()') {
      s = trimmed
    }
  }
  s = s.replace(/^[（\(](.*?)[）\)]/, '$1').trim()
  if (!s.endsWith('表') && !s.includes('简报')) {
    s += '表'
  }
  return s || title
}

async function loadUnitSheets() {
  if (!projectKey.value || !pageConfig.value) return
  try {
    const res = await listSheets(projectKey.value, pageConfig.value)
    const catalog = res?.content || res
    if (!catalog || typeof catalog !== 'object') return

    let targetUnit = ''
    for (const [k, meta] of Object.entries(catalog)) {
      if (k === sheetKey.value) {
        targetUnit = meta?.unit_name ? String(meta.unit_name).trim() : ''
        break
      }
    }
    unitGroupName.value = targetUnit

    if (targetUnit) {
      const matched = []
      for (const [k, meta] of Object.entries(catalog)) {
        const u = meta?.unit_name ? String(meta.unit_name).trim() : ''
        if (u === targetUnit) {
          matched.push({
            sheet_key: k,
            sheet_name: meta?.sheet_name || k,
            unit_name: u,
          })
        }
      }
      unitSheets.value = matched
    } else {
      unitSheets.value = [{
        sheet_key: sheetKey.value,
        sheet_name: sheetName.value || sheetKey.value,
        unit_name: '',
      }]
    }
  } catch (err) {
    console.warn('[DisplayRuntimeView] 加载单位表格列表失败', err)
  }
}

function onSwitchSheetTab(targetKey) {
  if (!targetKey || targetKey === sheetKey.value || loading.value) {
    return
  }
  router.replace({
    path: `/projects/${encodeURIComponent(projectKey.value)}/pages/${encodeURIComponent(pageKey.value)}/display/${encodeURIComponent(targetKey)}`,
    query: route.query,
  })
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
  const colList = Array.isArray(cols) ? cols : []
  const leafDefs = colList.map((name, index) => ({
    prop: `c${index}`,
    name: String(name ?? ''),
    autoSize: true,
    minSize: index === 0 ? 160 : 120,
    readonly: true,
  }))

  const headers = columnHeaders.value
  const hasMulti = Array.isArray(headers) && headers.length >= 2 && headers[0]?.length === colList.length && headers[1]?.length === colList.length

  if (hasMulti) {
    const top = headers[0]
    const second = headers[1]
    const grouped = []
    for (let i = 0; i < leafDefs.length; i += 1) {
      const base = leafDefs[i]
      const topName = top[i] ? String(top[i]) : ''
      const secondName = second[i] ? String(second[i]) : ''
      if (secondName) {
        base.name = secondName
      } else if (topName) {
        base.name = topName
      }
      if (i < 2 || !topName || topName === '' || topName === base.name) {
        grouped.push(base)
        continue
      }
      const children = []
      let span = 0
      while (i + span < leafDefs.length) {
        const childTop = top[i + span] ? String(top[i + span]) : ''
        if (childTop !== topName) break
        const child = leafDefs[i + span]
        const childSecond = second[i + span] ? String(second[i + span]) : ''
        if (childSecond) {
          child.name = childSecond
        }
        children.push(child)
        span += 1
      }
      if (children.length) {
        grouped.push({ name: topName, children })
        i += span - 1
      } else {
        grouped.push(base)
      }
    }
    gridColumns.value = grouped
    columnGrouping.value = true
  } else {
    gridColumns.value = leafDefs
    columnGrouping.value = false
  }
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
    if (!initialized.value && !bizDate.value) {
      await loadDefaultBizDate()
    }
    const body = {
      sheet_key: sheetKey.value,
      project_key: 'daily_report_25_26',
      config: pageConfig.value,
      biz_date: bizDate.value ? bizDate.value : 'regular',
      trace: !!traceEnabled.value,
      profile: true,
    }
    const res = await evalSpec(projectKey.value, body)
    if (!res || res.ok === false) {
      throw new Error(res?.message || 'runtime eval 失败')
    }
    sheetName.value = res.sheet_name || sheetKey.value
    effectiveBizDate.value = res.biz_date || ''
    columns.value = Array.isArray(res.columns) ? res.columns : []
    rows.value = Array.isArray(res.rows) ? res.rows : []
    columnHeaders.value = Array.isArray(res.column_headers) ? res.column_headers : []
    columnGroups.value = Array.isArray(res.column_groups) ? res.column_groups : []
    if (Number.isInteger(res.accuracy)) accuracy.value = res.accuracy
    if (res.number_format && typeof res.number_format === 'object') numberFormat.value = res.number_format
    traceData.value = res.debug && res.debug._trace ? res.debug._trace : null
    if (res.debug && res.debug._perf) {
      console.info('[DisplayRuntimeView][perf]', {
        sheetKey: sheetKey.value,
        bizDate: res.biz_date || body.biz_date,
        perf: res.debug._perf,
      })
    }

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
    initialized.value = true
  }
}

async function loadDefaultBizDate() {
  try {
    const status = await getWorkflowStatus(projectKey.value)
    const displayDate = status?.display_date
    if (displayDate) {
      suppressNextBizDateReaction = true
      bizDate.value = displayDate
    }
  } catch (err) {
    console.warn('加载默认业务日期失败，回落 regular', err)
  }
}

const formattedTrace = computed(() => {
  try { return JSON.stringify(traceData.value, null, 2) } catch { return '' }
})

const isExporting = ref(false)

function normalizeExportError(err) {
  const raw = String(err?.message || err || '').trim()
  if (!raw) return '未知错误'
  if (/<\/?html/i.test(raw) || /cloudflare|gateway\\s*time-?out|error code\\s*504/i.test(raw)) {
    return '网关超时（504），导出计算未及时返回，请稍后重试'
  }
  return raw
}

async function evalSpecForExport(payload) {
  let lastError = null
  for (let attempt = 1; attempt <= 2; attempt += 1) {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), EXPORT_EVAL_TIMEOUT_MS)
    try {
      return await evalSpec(projectKey.value, payload, { signal: controller.signal })
    } catch (err) {
      lastError = err
      const message = String(err?.message || '')
      const isAbort = err?.name === 'AbortError'
      const isGatewayTimeout = /gateway\\s*time-?out|error code\\s*504|\\b504\\b/i.test(message)
      if (!isAbort && !isGatewayTimeout) break
      if (attempt < 2) {
        await new Promise((resolve) => setTimeout(resolve, EXPORT_RETRY_DELAY_MS))
      }
    } finally {
      clearTimeout(timer)
    }
  }
  if (lastError?.name === 'AbortError') {
    throw new Error(`导出请求超时（${Math.round(EXPORT_EVAL_TIMEOUT_MS / 1000)} 秒）`)
  }
  throw new Error(normalizeExportError(lastError))
}

async function evalSpecsForExport(payload) {
  let lastError = null
  for (let attempt = 1; attempt <= 2; attempt += 1) {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), EXPORT_EVAL_TIMEOUT_MS)
    try {
      return await evalSpecsBatch(projectKey.value, payload, { signal: controller.signal })
    } catch (err) {
      lastError = err
      const message = String(err?.message || '')
      const isAbort = err?.name === 'AbortError'
      const isGatewayTimeout = /gateway\s*time-?out|error code\s*504|\b504\b/i.test(message)
      if (!isAbort && !isGatewayTimeout) break
      if (attempt < 2) {
        await new Promise((resolve) => setTimeout(resolve, EXPORT_RETRY_DELAY_MS))
      }
    } finally {
      clearTimeout(timer)
    }
  }
  if (lastError?.name === 'AbortError') {
    throw new Error(`导出请求超时（${Math.round(EXPORT_EVAL_TIMEOUT_MS / 1000)} 秒）`)
  }
  throw new Error(normalizeExportError(lastError))
}

function downloadBlob(blob, fileName) {
  if (typeof saveAs === 'function') {
    saveAs(blob, fileName)
    return
  }
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName
  document.body.appendChild(a)
  a.click()
  setTimeout(() => {
    if (a.parentNode) {
      document.body.removeChild(a)
    }
    URL.revokeObjectURL(url)
  }, 2000)
}

function beautifyWorksheet(ws, opts) {
  const range = XLSX.utils.decode_range(ws['!ref'] || 'A1:A1')
  const { headerStartRow, headerEndRow, dataStartRow, unitCol, itemCol, measureCol, dataStartCol, bizDateStr } = opts

  // 1. 裁剪右侧完全空白的无效列（如表3原模板带至Q列的空白列，精准收拢至实际有数据的列）
  let maxEffectiveCol = range.s.c
  for (let c = range.s.c; c <= range.e.c; c++) {
    for (let r = range.s.r; r <= range.e.r; r++) {
      const cell = ws[XLSX.utils.encode_cell({ r, c })]
      if (cell && cell.v != null && String(cell.v).trim() !== '') {
        maxEffectiveCol = Math.max(maxEffectiveCol, c)
        break
      }
    }
  }
  range.e.c = maxEffectiveCol
  ws['!ref'] = XLSX.utils.encode_range(range)

  // 全表统一严整的浅灰细边框体系（100% 消除粗细不一与接缝毛刺）
  const BORDER_COLOR = 'CBD5E1'
  const uniformThinBorder = {
    top: { style: 'thin', color: { rgb: BORDER_COLOR } },
    bottom: { style: 'thin', color: { rgb: BORDER_COLOR } },
    left: { style: 'thin', color: { rgb: BORDER_COLOR } },
    right: { style: 'thin', color: { rgb: BORDER_COLOR } },
  }

  // 2. 先行测算最佳黄金列宽（考虑多行文本分行测算及项目列保底宽度）
  const colWidths = []
  for (let c = range.s.c; c <= range.e.c; c++) {
    let maxLen = 8
    for (let r = range.s.r; r <= range.e.r; r++) {
      if (r === 0) continue // 排除大标题行，避免被长标题撑宽
      const ref = XLSX.utils.encode_cell({ r, c })
      const cell = ws[ref]
      if (!cell || cell.v === undefined || cell.v === null) continue
      const lines = String(cell.w || cell.v || '').split('\n')
      for (const line of lines) {
        let len = 0
        for (let i = 0; i < line.length; i++) {
          len += line.charCodeAt(i) > 255 ? 2.1 : 1.1
        }
        if (len > maxLen) maxLen = len
      }
    }
    let wch = Math.max(10, Math.min(45, Math.ceil(maxLen) + 3))
    // 关键列宽裕保底，防止长字段被迫局促换行
    if (c === itemCol) {
      wch = Math.max(wch, 28) // 项目列保底28宽度，确保“万平方米省市净投诉量”、“供热标煤单耗（燃煤锅炉房）”等舒展呈现
    } else if (c === unitCol) {
      wch = Math.max(wch, 13) // 经营单位列保底13
    } else if (c === measureCol) {
      wch = Math.max(wch, 11) // 计量单位列保底11
    } else if (c >= dataStartCol) {
      wch = Math.max(wch, 12) // 数值/指标列保底12
    }
    colWidths.push({ wch })
  }
  ws['!cols'] = colWidths

  // 3. 全量遍历每一个网格（从第 0 行到最后一行、从第 0 列到最后一列），无死角构建闭合边框网格
  for (let R = range.s.r; R <= range.e.r; ++R) {
    const isTitleRow = R === 0
    const isHeader = R >= headerStartRow && R <= headerEndRow
    const isSubHeader = isHeader && R > headerStartRow
    const rowBg = (R - dataStartRow) % 2 === 0 ? 'FFFFFF' : 'F4F4F5'

    for (let C = range.s.c; C <= range.e.c; ++C) {
      const cellRef = XLSX.utils.encode_cell({ r: R, c: C })
      if (!ws[cellRef]) ws[cellRef] = { t: 's', v: '' }
      const cell = ws[cellRef]
      const val = cell.v

      if (isTitleRow) {
        // 第 0 行：标题栏与日期栏，全单元格注入统一边框
        if (C === 0) {
          cell.v = '业务日期：'
          cell.s = {
            font: { name: 'Microsoft YaHei', sz: 9.5, bold: true, color: { rgb: '52525B' } },
            fill: { fgColor: { rgb: 'E4E4E7' } },
            alignment: { horizontal: 'center', vertical: 'center' },
            border: uniformThinBorder,
          }
        } else if (C === 1) {
          cell.t = 's'
          cell.v = bizDateStr || ''
          cell.s = {
            font: { name: 'Microsoft YaHei', sz: 10, bold: true, color: { rgb: '18181B' } },
            fill: { fgColor: { rgb: 'FFFFFF' } },
            alignment: { horizontal: 'center', vertical: 'center' },
            border: uniformThinBorder,
          }
        } else {
          const isMainTitle = val && String(val).trim().length > 0
          cell.s = {
            font: {
              name: 'Microsoft YaHei',
              sz: isMainTitle ? 13 : 9.5,
              bold: isMainTitle,
              color: { rgb: '18181B' },
            },
            fill: { fgColor: { rgb: 'F4F4F5' } },
            alignment: { horizontal: 'center', vertical: 'center' },
            border: uniformThinBorder,
          }
        }
      } else if (isHeader) {
        // 表头行：统一典雅灰阶底色，深炭黑加粗文字，边框100%统一为 uniformThinBorder 杜绝粗细冲突
        cell.s = {
          font: {
            name: 'Microsoft YaHei',
            sz: isSubHeader ? 9.5 : 10,
            bold: true,
            color: { rgb: isSubHeader ? '27272A' : '18181B' },
          },
          fill: { fgColor: { rgb: isSubHeader ? 'E4E4E7' : 'D4D4D8' } },
          alignment: { horizontal: 'center', vertical: 'center', wrapText: true },
          border: uniformThinBorder,
        }
      } else if (R >= dataStartRow) {
        // 数据行：纯正灰度交替底色与对齐格式化
        let alignH = 'center'
        let isBold = false
        let fontColor = '18181B'

        if (C === unitCol) {
          alignH = 'center'
          isBold = true
          fontColor = '18181B'
        } else if (C === itemCol) {
          alignH = 'left'
          fontColor = '18181B'
        } else if (C === measureCol) {
          alignH = 'center'
          fontColor = '71717A'
        } else if (C >= dataStartCol) {
          const sVal = String(val != null ? val : '').trim()
          if (sVal.endsWith('%')) {
            alignH = 'right'
            fontColor = '18181B'
          } else if (sVal === '-' || sVal === '—' || sVal === '') {
            alignH = 'center'
            fontColor = 'A1A1AA'
          } else {
            const num = Number(sVal.replace(/,/g, ''))
            if (!Number.isNaN(num) && Number.isFinite(num)) {
              cell.t = 'n'
              cell.v = num
              cell.z = Number.isInteger(num) ? '#,##0' : '#,##0.00'
              alignH = 'right'
              fontColor = '18181B'
            } else {
              alignH = 'center'
            }
          }
        }

        cell.s = {
          font: { name: 'Microsoft YaHei', sz: 9.5, bold: isBold, color: { rgb: fontColor } },
          fill: { fgColor: { rgb: rowBg } },
          alignment: { horizontal: alignH, vertical: 'center', wrapText: true },
          border: uniformThinBorder,
        }
      }
    }
  }

  // 4. 合并单元格深度穿透修复（消除合并区域断框、缺框与背景撕裂）
  if (ws['!merges'] && Array.isArray(ws['!merges'])) {
    ws['!merges'].forEach((m) => {
      // 避免合并区域超出实际裁剪有效列
      if (m.e.c > range.e.c) m.e.c = range.e.c
      const masterRef = XLSX.utils.encode_cell({ r: m.s.r, c: m.s.c })
      const masterCell = ws[masterRef]
      const masterFill = masterCell?.s?.fill
      const masterFont = masterCell?.s?.font
      const masterAlign = masterCell?.s?.alignment

      for (let r = m.s.r; r <= m.e.r; r++) {
        for (let c = m.s.c; c <= m.e.c; c++) {
          const ref = XLSX.utils.encode_cell({ r, c })
          if (!ws[ref]) ws[ref] = { t: 's', v: '' }
          if (!ws[ref].s) ws[ref].s = {}
          if (masterFill) ws[ref].s.fill = masterFill
          if (masterFont && !ws[ref].s.font) ws[ref].s.font = masterFont
          if (masterAlign && !ws[ref].s.alignment) ws[ref].s.alignment = masterAlign
          // 确保合并区域内每个网格均具有完全一致闭合的细边框
          ws[ref].s.border = uniformThinBorder
        }
      }
    })
  }

  // 5. 动态智能行高优化（根据换行与字符自动匹配，杜绝文字被行高截断）
  const rowsHeight = []
  for (let r = 0; r <= range.e.r; r++) {
    if (r === 0) {
      rowsHeight.push({ hpt: 32 })
      continue
    }

    // 测算该行内所有单元格的最大折行行数
    let maxLinesInRow = 1
    for (let c = range.s.c; c <= range.e.c; c++) {
      const cell = ws[XLSX.utils.encode_cell({ r, c })]
      if (!cell || cell.v == null) continue
      const str = String(cell.w || cell.v || '')
      // 显式换行行数
      const explicitLines = str.split('\n').length
      // 基于列宽的折行估算
      const cw = colWidths[c]?.wch || 12
      let textVisualLen = 0
      for (let i = 0; i < str.length; i++) {
        textVisualLen += str.charCodeAt(i) > 255 ? 2.1 : 1.1
      }
      const wrappedLines = Math.ceil(textVisualLen / Math.max(8, cw - 2))
      const cellLines = Math.max(explicitLines, wrappedLines)
      if (cellLines > maxLinesInRow) {
        maxLinesInRow = cellLines
      }
    }

    const isHeader = r >= headerStartRow && r <= headerEndRow
    if (isHeader) {
      // 表头：若包含两行文本（如“25-26供暖期\n累计”等），给予充足的 42pt 行高；单行表头给予 28pt
      rowsHeight.push({ hpt: maxLinesInRow >= 2 ? 42 : 28 })
    } else {
      // 数据行：基础单行高度提升为 24pt（舒适度更佳）；若折行为多行，按行数比例自动放大，永不被挤压
      if (maxLinesInRow >= 2) {
        rowsHeight.push({ hpt: maxLinesInRow * 18 + 6 })
      } else {
        rowsHeight.push({ hpt: 24 })
      }
    }
  }
  ws['!rows'] = rowsHeight
}

const isCapturing = ref(false)
const captureProgressText = ref('')
const showScreenshotMenu = ref(false)
const captureToastMessage = ref('')
let captureToastTimer = null

function showCaptureToast(msg) {
  captureToastMessage.value = msg
  if (captureToastTimer) clearTimeout(captureToastTimer)
  captureToastTimer = setTimeout(() => {
    captureToastMessage.value = ''
    captureToastTimer = null
  }, 4000)
}

function toggleScreenshotDropdown(e) {
  if (e) e.stopPropagation()
  showScreenshotMenu.value = !showScreenshotMenu.value
}

function closeScreenshotDropdown() {
  showScreenshotMenu.value = false
}

function onDocumentClick() {
  if (showScreenshotMenu.value) {
    showScreenshotMenu.value = false
  }
}

async function ensureHtml2Canvas() {
  if (typeof window.html2canvas === 'function') {
    return window.html2canvas
  }
  return new Promise((resolve, reject) => {
    let script = document.querySelector('script[src*="html2canvas"]')
    if (!script) {
      script = document.createElement('script')
      script.src = 'https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js'
      document.head.appendChild(script)
    }
    const timer = setTimeout(() => {
      if (typeof window.html2canvas === 'function') {
        resolve(window.html2canvas)
      } else {
        reject(new Error('未检测到截图组件（html2canvas），请检查网络连接或稍后重试'))
      }
    }, 8000)

    script.addEventListener('load', () => {
      clearTimeout(timer)
      if (typeof window.html2canvas === 'function') {
        resolve(window.html2canvas)
      } else {
        reject(new Error('html2canvas 脚本加载后未找到全局对象'))
      }
    })
  })
}

function escapeHtml(str) {
  if (str == null) return ''
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

function formatCellValue(cell) {
  if (!cell || cell.v == null) return ''
  if (cell.w) return cell.w
  if (cell.t === 'n' && typeof cell.v === 'number') {
    if (Number.isInteger(cell.v)) return cell.v.toLocaleString('zh-CN')
    return cell.v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
  return String(cell.v)
}

// 截图使用独立的桌面排版宽度，不随手机视口、缩放或设备像素比改变。
const SCREENSHOT_WIDTH = 1600

// 百分比经导出格式化后可能是字符串，统一用于测宽和禁止换行。
function isScreenshotNumericValue(cell, value) {
  if (cell.t === 'n') return true
  const text = String(value ?? '').trim().replace(/[\s\u00a0\u202f]/g, '')
  return /^[+\-−]?[\d,.，．]+[%％]?$/.test(text)
}

function buildHtmlForWorksheet(ws, sheetTitle, bizDateStr) {
  const range = XLSX.utils.decode_range(ws['!ref'] || 'A1:A1')
  const merges = ws['!merges'] || []
  const startRow = 1

  const mergeStart = new Map()
  const mergeCovered = new Set()

  for (const m of merges) {
    if (m.e.r < startRow) continue
    const actualSr = Math.max(startRow, m.s.r)
    const actualEc = Math.min(range.e.c, m.e.c)
    mergeStart.set(`${actualSr},${m.s.c}`, {
      rowspan: m.e.r - actualSr + 1,
      colspan: actualEc - m.s.c + 1,
    })
    for (let r = actualSr; r <= m.e.r; r++) {
      for (let c = m.s.c; c <= actualEc; c++) {
        if (r !== actualSr || c !== m.s.c) {
          mergeCovered.add(`${r},${c}`)
        }
      }
    }
  }

  const colWidths = ws['!cols'] || []
  const rowHeights = ws['!rows'] || []
  const columnWidths = []
  for (let c = range.s.c; c <= range.e.c; c++) {
    const width = Number(colWidths[c]?.wch)
    columnWidths.push(Number.isFinite(width) && width > 0 ? width : 12)
  }
  const totalColumnWidth = columnWidths.reduce((sum, width) => sum + width, 0)
  // 先按模板比例分配宽度，再根据各列实际数字扩宽，避免长数字溢出到相邻单元格。
  const pixelWidths = columnWidths.map(width => (SCREENSHOT_WIDTH - 60) * width / totalColumnWidth)
  const measureContext = document.createElement('canvas').getContext?.('2d')
  for (let r = startRow; r <= range.e.r; r++) {
    for (let c = range.s.c; c <= range.e.c; c++) {
      const cell = ws[XLSX.utils.encode_cell({ r, c })] || {}
      const value = String(formatCellValue(cell)).trim()
      if (!value || !isScreenshotNumericValue(cell, value)) continue
      const fontSize = cell.s?.font?.sz ? Math.round(cell.s.font.sz * 1.25) : 12
      if (measureContext) measureContext.font = `${cell.s?.font?.bold ? '700' : '400'} ${fontSize}px sans-serif`
      const measured = measureContext?.measureText(value).width || 0
      const required = Math.ceil(Math.max(measured, value.length * fontSize * 0.8) + 22)
      const span = mergeStart.get(`${r},${c}`)?.colspan || 1
      const offset = c - range.s.c
      const available = pixelWidths.slice(offset, offset + span).reduce((sum, width) => sum + width, 0)
      if (required > available) pixelWidths[offset] += required - available
    }
  }
  const screenshotWidth = Math.ceil(Math.max(SCREENSHOT_WIDTH, pixelWidths.reduce((sum, width) => sum + width, 0) + 60))

  let html = `
    <div class="table-screenshot-card" style="width:${screenshotWidth}px;min-width:${screenshotWidth}px;max-width:none;background:#FFFFFF;padding:24px 30px 20px 30px;display:block;box-sizing:border-box;color:#18181B;font-family:-apple-system,BlinkMacSystemFont,'Microsoft YaHei','PingFang SC','Segoe UI',Roboto,sans-serif;-webkit-text-size-adjust:100%;text-size-adjust:100%;">
      <!-- 顶部高规格报表标头与业务元数据栏 -->
      <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:14px;padding-bottom:12px;border-bottom:2px solid #18181B;">
        <div>
          <div style="font-size:20px;font-weight:700;color:#18181B;letter-spacing:0.5px;line-height:1.2;">${escapeHtml(sheetTitle)}</div>
          <div style="font-size:12px;color:#71717A;margin-top:4px;">大连洁净能源集团生产经营数据智算平台 · 生产日报</div>
        </div>
        <div style="text-align:right;font-size:13px;color:#52525B;line-height:1.6;">
          <div>业务日期：<strong style="color:#18181B;font-size:14px;">${escapeHtml(bizDateStr || '-')}</strong></div>
        </div>
      </div>

      <!-- 表格主体 -->
      <table style="width:100%;max-width:none;border-collapse:collapse;border-spacing:0;table-layout:fixed;border:1.5px solid #94A3B8;font-size:12px;line-height:1.35;box-sizing:border-box;">
        <colgroup>
  `
  const totalPixelWidth = pixelWidths.reduce((sum, width) => sum + width, 0)
  for (const width of pixelWidths) {
    html += `<col style="width:${(width / totalPixelWidth * 100).toFixed(6)}%;" />`
  }
  html += `</colgroup><tbody>`

  for (let r = startRow; r <= range.e.r; r++) {
    const hpt = rowHeights[r]?.hpt || 24
    html += `<tr style="height:${Math.round(hpt * 1.33)}px;">`
    for (let c = range.s.c; c <= range.e.c; c++) {
      const key = `${r},${c}`
      if (mergeCovered.has(key)) continue

      const span = mergeStart.get(key)
      let attr = ''
      if (span) {
        if (span.rowspan > 1) attr += ` rowspan="${span.rowspan}"`
        if (span.colspan > 1) attr += ` colspan="${span.colspan}"`
      }

      const ref = XLSX.utils.encode_cell({ r, c })
      const cell = ws[ref] || {}
      const val = formatCellValue(cell)

      const bg = cell.s?.fill?.fgColor?.rgb ? `#${cell.s.fill.fgColor.rgb}` : (r % 2 === 0 ? '#FFFFFF' : '#F4F4F5')
      const color = cell.s?.font?.color?.rgb ? `#${cell.s.font.color.rgb}` : '#18181B'
      const align = cell.s?.alignment?.horizontal || (cell.t === 'n' ? 'right' : 'center')
      const bold = cell.s?.font?.bold ? 'font-weight:700;' : 'font-weight:400;'
      const sz = cell.s?.font?.sz ? `font-size:${Math.round(cell.s.font.sz * 1.25)}px;` : 'font-size:12px;'

      // 数值保持完整一行；文字和显式换行可按固定列宽增加行高。
      const wrapping = isScreenshotNumericValue(cell, val) ? 'white-space:nowrap;word-break:normal;' : 'white-space:pre-line;overflow-wrap:break-word;word-break:normal;'
      const style = `background-color:${bg};color:${color};text-align:${align};${bold}${sz}vertical-align:middle;border:1px solid #CBD5E1;padding:4px 8px;box-sizing:border-box;${wrapping}`
      const displayValue = isScreenshotNumericValue(cell, val) ? String(val).replace(/[\r\n]+/g, ' ') : val
      html += `<td${attr} style="${style}">${escapeHtml(displayValue).replace(/\n/g, '<br/>')}</td>`
    }
    html += `</tr>`
  }

  const exportTime = new Date().toLocaleString('zh-CN', { hour12: false })
  html += `
        </tbody>
      </table>

      <!-- 底部版权与生成时间栏 -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:10px;font-size:11px;color:#94A3B8;">
        <span>大连洁净能源集团 生产运行管理专用</span>
        <span>导出时间：${exportTime}</span>
      </div>
    </div>
  `
  return html
}

function downloadCanvasAsPng(canvas, fileName) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error('生成图片文件失败'))
        return
      }
      downloadBlob(blob, fileName)
      resolve()
    }, 'image/png')
  })
}

async function captureWorksheetToPng(ws, cleanSheetName, bizDateStr, html2canvas) {
  const container = document.createElement('div')
  container.className = 'export-screenshot-container'
  container.style.position = 'fixed'
  container.style.left = '0'
  container.style.top = '0'
  container.style.zIndex = '-99999'
  container.style.pointerEvents = 'none'
  container.style.background = '#FFFFFF'
  container.style.display = 'inline-block'
  container.style.width = `${SCREENSHOT_WIDTH}px`
  container.style.minWidth = `${SCREENSHOT_WIDTH}px`
  container.style.maxWidth = 'none'

  try {
    // 字体加载完成后再度量，避免慢速移动设备使用临时字体计算列高。
    if (document.fonts?.ready) await document.fonts.ready
    container.innerHTML = buildHtmlForWorksheet(ws, cleanSheetName, bizDateStr)
    document.body.appendChild(container)
    const card = container.querySelector('.table-screenshot-card') || container
    const bounds = card.getBoundingClientRect()
    const width = Math.ceil(bounds.width)
    const height = Math.ceil(Math.max(card.scrollHeight, bounds.height))
    const canvas = await html2canvas(card, {
      useCORS: true,
      scale: 2,
      width,
      height,
      windowWidth: width,
      windowHeight: height,
      backgroundColor: '#FFFFFF',
      scrollX: 0,
      scrollY: 0,
      logging: false,
    })

    const fileName = `${cleanSheetName}_${bizDateStr || 'export'}.png`
    await downloadCanvasAsPng(canvas, fileName)
  } finally {
    if (container.parentNode) {
      document.body.removeChild(container)
    }
  }
}

async function prepareExportWorkbook() {
  const sheetKeys = ['Group_sum_show_Sheet', 'Group_analysis_brief_report_Sheet', 'ZhuChengQu_sum_show_Sheet']
  const configPath = pageConfig.value
  const templatePath = '/25-26生产日报标准模板.xlsx'
  const origins = ['D3', 'C4', 'C3']
  const slicePoints = [3, 2, 2]

  const templatePromise = fetch(templatePath).then((res) => {
    if (!res.ok) throw new Error(`无法加载模板文件: ${res.statusText}`)
    return res.arrayBuffer()
  })
  const templateData = await templatePromise

  const jobs = sheetKeys.map((key) => ({
    sheet_key: key,
    config: configPath,
  }))

  const batchRes = await evalSpecsForExport({
    project_key: 'daily_report_25_26',
    config: configPath,
    biz_date: bizDate.value ? bizDate.value : 'regular',
    trace: false,
    jobs,
  })
  const results = Array.isArray(batchRes?.results) ? batchRes.results : []
  if (results.length !== sheetKeys.length) {
    throw new Error(`批量求值返回数量异常：期望 ${sheetKeys.length}，实际 ${results.length}`)
  }

  const workbook = XLSX.read(templateData, { type: 'array', cellStyles: true })
  const keepSheetNames = ['展示表1.集团全口径汇总表', '展示表2.分析简报', '展示表3.主城区汇总表']
  const cleanSheetNames = ['1.集团全口径汇总表', '2.分析简报', '3.主城区汇总表']

  const sheetsMap = {}
  cleanSheetNames.forEach((cleanName, idx) => {
    const origName = keepSheetNames[idx] || workbook.SheetNames[idx]
    if (workbook.Sheets[origName]) {
      sheetsMap[cleanName] = workbook.Sheets[origName]
    }
  })
  workbook.Sheets = sheetsMap
  workbook.SheetNames = Object.keys(sheetsMap)

  const beautifyConfigs = [
    {
      headerStartRow: 1,
      headerEndRow: 1,
      dataStartRow: 2,
      unitCol: 0,
      itemCol: 1,
      measureCol: 2,
      dataStartCol: 3,
    },
    {
      headerStartRow: 1,
      headerEndRow: 2,
      dataStartRow: 3,
      unitCol: -1,
      itemCol: 0,
      measureCol: 1,
      dataStartCol: 2,
    },
    {
      headerStartRow: 1,
      headerEndRow: 1,
      dataStartRow: 2,
      unitCol: -1,
      itemCol: 0,
      measureCol: 1,
      dataStartCol: 2,
    },
  ]

  cleanSheetNames.forEach((targetSheetName, index) => {
    const res = results[index]
    if (!res || res.ok === false) {
      throw new Error(`获取第 ${index + 1} 个工作表的数据失败: ${res?.message || '未知错误'}`)
    }

    const worksheet = workbook.Sheets[targetSheetName]
    if (!worksheet) {
      throw new Error(`在模板中找不到名为 "${targetSheetName}" 的Sheet`)
    }

    const slicePoint = slicePoints[index]
    const dataOnly = res.rows.map((row) => row.slice(slicePoint))

    XLSX.utils.sheet_add_aoa(worksheet, dataOnly, { origin: origins[index] })

    beautifyWorksheet(worksheet, {
      ...beautifyConfigs[index],
      bizDateStr: effectiveBizDate.value || bizDate.value || '',
    })
  })

  return { workbook, cleanSheetNames, results }
}

async function exportToExcel() {
  isExporting.value = true
  errorMessage.value = ''
  try {
    const { workbook } = await prepareExportWorkbook()
    const excelBuffer = XLSX.write(workbook, { bookType: 'xlsx', type: 'array', cellStyles: true })
    const dataBlob = new Blob([excelBuffer], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;charset=UTF-8',
    })

    const finalFileName = `生产日报-数据展示-${effectiveBizDate.value || bizDate.value || 'export'}.xlsx`
    downloadBlob(dataBlob, finalFileName)
  } catch (err) {
    console.error('导出Excel失败:', err)
    errorMessage.value = `导出失败: ${normalizeExportError(err)}`
  } finally {
    isExporting.value = false
  }
}

async function exportAllScreenshots() {
  showScreenshotMenu.value = false
  if (isCapturing.value || isExporting.value || loading.value) return
  isCapturing.value = true
  errorMessage.value = ''
  captureProgressText.value = '准备中...'

  try {
    const html2canvas = await ensureHtml2Canvas()
    captureProgressText.value = '计算报表数据...'
    const { workbook, cleanSheetNames } = await prepareExportWorkbook()
    const dateStr = effectiveBizDate.value || bizDate.value || 'today'

    for (let i = 0; i < cleanSheetNames.length; i++) {
      const targetName = cleanSheetNames[i]
      captureProgressText.value = `生成截图 (${i + 1}/${cleanSheetNames.length})...`
      const ws = workbook.Sheets[targetName]
      if (!ws) continue

      await captureWorksheetToPng(ws, targetName, dateStr, html2canvas)
      if (i < cleanSheetNames.length - 1) {
        await new Promise((r) => setTimeout(r, 450))
      }
    }

    captureProgressText.value = '下载完成！'
    showCaptureToast('3张展示表高清截图已下载完毕，可直接发送到工作群！')
    await new Promise((r) => setTimeout(r, 1500))
  } catch (err) {
    console.error('导出截图失败:', err)
    errorMessage.value = `导出截图失败: ${normalizeExportError(err)}`
  } finally {
    isCapturing.value = false
    captureProgressText.value = ''
  }
}

async function exportCurrentScreenshotOnly() {
  showScreenshotMenu.value = false
  if (isCapturing.value || isExporting.value || loading.value) return
  isCapturing.value = true
  errorMessage.value = ''
  captureProgressText.value = '生成当前截图...'

  try {
    const html2canvas = await ensureHtml2Canvas()
    const { workbook, cleanSheetNames } = await prepareExportWorkbook()
    const dateStr = effectiveBizDate.value || bizDate.value || 'today'

    let targetIndex = 0
    if (sheetKey.value.includes('brief') || sheetKey.value.includes('analysis')) {
      targetIndex = 1
    } else if (sheetKey.value.includes('ZhuChengQu') || sheetKey.value.includes('zhuchengqu')) {
      targetIndex = 2
    }
    const targetName = cleanSheetNames[targetIndex] || cleanSheetNames[0]
    const ws = workbook.Sheets[targetName]

    if (ws) {
      await captureWorksheetToPng(ws, targetName, dateStr, html2canvas)
      showCaptureToast(`已导出「${targetName}」高清长截图！`)
    }
  } catch (err) {
    console.error('导出当前截图失败:', err)
    errorMessage.value = `导出截图失败: ${normalizeExportError(err)}`
  } finally {
    isCapturing.value = false
    captureProgressText.value = ''
  }
}

function scheduleAutoRefresh() {
  if (!initialized.value || loading.value) {
    pendingAutoRefresh.value = true
    return
  }
  pendingAutoRefresh.value = false
  runEval()
}

watch(
  bizDate,
  (newVal, oldVal) => {
    if (suppressNextBizDateReaction) {
      suppressNextBizDateReaction = false
      return
    }
    if (newVal === oldVal) return
    if (bizDateAutoRefreshTimer) {
      clearTimeout(bizDateAutoRefreshTimer)
      bizDateAutoRefreshTimer = null
    }
    bizDateAutoRefreshTimer = setTimeout(() => {
      bizDateAutoRefreshTimer = null
      scheduleAutoRefresh()
    }, AUTO_REFRESH_DELAY_MS)
  },
)

watch(
  () => [initialized.value, loading.value],
  ([isReady, isLoading]) => {
    if (pendingAutoRefresh.value && isReady && !isLoading) {
      scheduleAutoRefresh()
    }
  },
)

watch(
  sheetKey,
  async (newKey, oldKey) => {
    if (newKey && newKey !== oldKey) {
      if (!unitSheets.value.some((s) => s.sheet_key === newKey)) {
        await loadUnitSheets()
      }
      runEval()
    }
  },
)

onMounted(async () => {
  window.addEventListener('click', onDocumentClick)
  await loadUnitSheets()
  runEval()
})

onBeforeUnmount(() => {
  window.removeEventListener('click', onDocumentClick)
  if (bizDateAutoRefreshTimer) {
    clearTimeout(bizDateAutoRefreshTimer)
    bizDateAutoRefreshTimer = null
  }
  if (captureToastTimer) {
    clearTimeout(captureToastTimer)
    captureToastTimer = null
  }
})
</script>

<style scoped>
.container { padding: 16px; }
.topbar { display:flex; align-items:center; justify-content:space-between; margin-bottom: 12px; }
.topbar-heading { display:flex; flex-direction:column; gap:6px; min-width:0; }
.topbar .right { display:flex; align-items:center; gap:8px; }
.trace-toggle, .date-group { display:inline-flex; align-items:center; gap:6px; }
.sub { color: #666; font-size: 13px; }
.placeholder { color:#888; padding: 20px 0; text-align:center; }
.error { color: #c00; margin-top: 10px; }
.trace-pre { max-height: 360px; overflow: auto; background: #0b0b0b; color: #d6d6d6; padding: 12px; border-radius: 6px; }
:deep(revo-grid .rg-header-cell) { white-space: pre-line; line-height: 1.3; }
.hint { font-size: 12px; color: #666; }

/* 多表格单位 Tabs 栏样式 */
.unit-tabs-nav-wrapper {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  overflow-x: auto;
  scrollbar-width: none;
}
.unit-tabs-nav-wrapper::-webkit-scrollbar {
  display: none;
}

.unit-tabs-nav {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background-color: #f1f5f9;
  padding: 4px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.05);
}

.unit-tab-pill {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid transparent;
  background: transparent;
  color: #64748b;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  user-select: none;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.unit-tab-pill:hover:not(.unit-tab-pill--active) {
  color: #1e293b;
  background-color: rgba(255, 255, 255, 0.7);
}

.unit-tab-pill--active {
  background-color: #ffffff !important;
  color: #1d4ed8 !important;
  font-weight: 600;
  border-color: #e2e8f0;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08), 0 4px 6px -1px rgba(15, 23, 42, 0.04);
}

.tab-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 5px;
  border-radius: 6px;
  background-color: #e2e8f0;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
  transition: all 0.2s ease;
}

.unit-tab-pill--active .tab-index {
  background-color: #eff6ff;
  color: #2563eb;
  border: 1px solid #bfdbfe;
}

.tab-name {
  line-height: 1.2;
}

/* 截图导出下拉按钮组 */
.screenshot-btn-group {
  position: relative;
  display: inline-flex;
  align-items: stretch;
}

.screenshot-dropdown-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  z-index: 1000;
  min-width: 280px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.12), 0 8px 10px -6px rgba(15, 23, 42, 0.08);
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.screenshot-menu-item {
  width: 100%;
  text-align: left;
  padding: 8px 12px;
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.screenshot-menu-item:hover {
  background-color: #f1f5f9;
}

.menu-item-title {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.3;
}

.menu-item-desc {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
  line-height: 1.3;
}

/* 截图下载完成 Toast 提示 */
.capture-toast {
  position: fixed;
  bottom: 32px;
  right: 32px;
  z-index: 9999;
  background: #0f172a;
  color: #ffffff;
  padding: 12px 20px;
  border-radius: 8px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.25);
  font-size: 14px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  animation: toastFadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes toastFadeIn {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 窄屏让工具栏换行，宽表仅在表格内部滚动，不撑宽整个页面。 */
@media (max-width: 768px) {
  .container { box-sizing: border-box; width: 100%; min-width: 0; padding: 12px; }
  .topbar { flex-direction: column; align-items: stretch; gap: 12px; }
  .topbar-heading h2 { font-size: 20px; line-height: 1.3; overflow-wrap: anywhere; }
  .sub { margin-top: 0; line-height: 1.5; overflow-wrap: anywhere; }
  .topbar .right { position: relative; flex-wrap: wrap; align-items: center; min-width: 0; }
  .date-group { flex: 1 1 100%; flex-wrap: wrap; min-width: 0; }
  .date-group input[type="date"] { box-sizing: border-box; min-width: 0; max-width: 100%; width: 160px; }
  .trace-toggle { order: -1; }
  .topbar .btn { white-space: nowrap; }
  .unit-tabs-nav-wrapper, .table-wrap, .trace-panel { box-sizing: border-box; width: 100%; min-width: 0; max-width: 100%; }
  .unit-tabs-nav-wrapper { -webkit-overflow-scrolling: touch; }
  .unit-tabs-nav { flex: 0 0 auto; }
  .table-wrap { padding: 8px; }
  .table-wrap :deep(revo-grid) { display: block; min-width: 0; max-width: 100%; }
  .trace-pre { white-space: pre-wrap; overflow-wrap: anywhere; }
  .breadcrumb-spacing :deep(li) { min-width: 0; max-width: 100%; overflow-wrap: anywhere; }
  .screenshot-btn-group { position: static; }
  .screenshot-dropdown-menu { left: auto; right: 0; box-sizing: border-box; min-width: 0; width: min(280px, 100%); }
  .capture-toast { left: 12px; right: 12px; bottom: 16px; box-sizing: border-box; }
}
</style>
