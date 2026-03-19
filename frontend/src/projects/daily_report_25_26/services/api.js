const rawBase =
  typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE
    ? import.meta.env.VITE_API_BASE
    : ''

function shouldPreferSameOriginProxy(base) {
  if (!base || typeof window === 'undefined') return false
  const origin = String(window.location?.origin || '')
  const isLocalFrontend = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(origin)
  if (!isLocalFrontend) return false
  return /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?(\/api(\/v1)?)?$/i.test(base)
}

// 兼容 VITE_API_BASE 未包含 /api/v1 的情况：自动补全标准前缀
const API_BASE = (() => {
  const base = rawBase ? String(rawBase).replace(/\/$/, '') : ''
  if (!base) return '/api/v1'
  const normalizedBase = /(\/api)(\/|$)/.test(base) ? base : `${base}/api/v1`
  // 本机开发优先同源 /api 代理，规避 localhost:5173 -> 127.0.0.1:8001 的 CORS 问题。
  if (shouldPreferSameOriginProxy(normalizedBase)) return '/api/v1'
  return normalizedBase
})()

const JSON_HEADERS = { 'Content-Type': 'application/json' }

let authToken = null
let cachedProjects = null
let cachedProjectsToken = null

function attachAuthHeaders(baseHeaders = {}, skipAuth = false) {
  const headers = { ...(baseHeaders || {}) }
  if (!skipAuth && authToken) {
    headers.Authorization = `Bearer ${authToken}`
  }
  return headers
}

export function setAuthToken(token) {
  const normalized = token || null
  const changed = normalized !== authToken
  authToken = normalized
  if (changed) {
    resetProjectCache()
  }
}

export function getAuthToken() {
  return authToken
}

export const AUTH_EXPIRED_EVENT = 'phoenix-auth-expired'

export function clearAuthToken() {
  authToken = null
  resetProjectCache()
}

function notifyAuthExpired() {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT))
}

async function authAwareFetch(url, options = {}, config = {}) {
  const { skipUnauthorizedHandling = false } = config
  const response = await globalThis.fetch(url, options)
  if (!skipUnauthorizedHandling && response.status === 401) {
    clearAuthToken()
    notifyAuthExpired()
  }
  return response
}

async function ensureSuperResponseOk(response, fallbackMessage) {
  if (response.ok) return
  const message = await response.text()
  throw new Error(message || fallbackMessage)
}

const normalized = (path) => `${API_BASE}${path}`

const projectPath = (projectKey) => normalized(`/projects/${encodeURIComponent(projectKey)}`)

function buildDev8001FallbackUrl(url) {
  const rawUrl = String(url || '')
  if (!rawUrl) return ''
  if (/^https?:\/\/127\.0\.0\.1:8001\//i.test(rawUrl) || /^https?:\/\/localhost:8001\//i.test(rawUrl)) {
    return ''
  }
  if (rawUrl.startsWith('/api/')) {
    return `http://127.0.0.1:8001${rawUrl}`
  }
  if (/^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?\/api\//i.test(rawUrl)) {
    return rawUrl.replace(/^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?/i, 'http://127.0.0.1:8001')
  }
  return ''
}

function buildSameOriginApiUrl(url) {
  const rawUrl = String(url || '')
  if (!rawUrl) return ''
  if (rawUrl.startsWith('/api/')) return rawUrl
  const match = rawUrl.match(/^https?:\/\/[^/]+(\/api\/.*)$/i)
  return match ? match[1] : ''
}

async function fetchWithDevChatFallback(url, options = {}) {
  const sameOriginUrl = buildSameOriginApiUrl(url)
  if (sameOriginUrl && typeof window !== 'undefined' && /localhost:5173|127\.0\.0\.1:5173/i.test(window.location.origin)) {
    try {
      return await authAwareFetch(sameOriginUrl, options)
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      if (!/Failed to fetch/i.test(message || '')) {
        throw error
      }
    }
  }
  try {
    return await authAwareFetch(url, options)
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    const fallbackUrl = buildDev8001FallbackUrl(url)
    if (!fallbackUrl || !/Failed to fetch/i.test(message || '')) {
      throw error
    }
    return authAwareFetch(fallbackUrl, options)
  }
}

export async function login(credentials) {
  const response = await authAwareFetch(
    normalized('/auth/login'),
    {
      method: 'POST',
      headers: attachAuthHeaders(JSON_HEADERS, true),
      body: JSON.stringify(credentials),
    },
    { skipUnauthorizedHandling: true },
  )
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || '登录失败')
  }
  return response.json()
}

export async function fetchSession() {
  const response = await authAwareFetch(normalized('/auth/me'), {
    headers: attachAuthHeaders(),
  })
  if (response.status === 401) {
    throw new Error('登录状态已过期')
  }
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || '获取登录信息失败')
  }
  return response.json()
}

export async function logout() {
  await authAwareFetch(normalized('/auth/logout'), {
    method: 'POST',
    headers: attachAuthHeaders(),
  })
  clearAuthToken()
}

export async function listProjects(force = false) {
  if (!force && Array.isArray(cachedProjects) && cachedProjectsToken === authToken) {
    return cachedProjects
  }

  const response = await authAwareFetch(normalized('/projects'), {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    resetProjectCache()
    throw new Error(`加载项目列表失败: ${response.status}`)
  }

  const payload = await response.json()
  const list = Array.isArray(payload?.projects) ? payload.projects : []
  cachedProjects = list
  cachedProjectsToken = authToken
  return list
}

export async function listPages(projectKey) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/pages`, {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    throw new Error(`加载页面配置失败: ${response.status}`)
  }
  return response.json()
}

export async function extractSpringFestivalJson(projectKey, file, options = {}) {
  if (!file) {
    throw new Error('请先选择 xlsx 文件')
  }
  const formData = new FormData()
  formData.append('file', file)
  if (options.sheetName) formData.append('sheet_name', options.sheetName)
  formData.append('keep_diff_cell', String(options.keepDiffCell ?? true))
  formData.append('compute_diff', String(options.computeDiff ?? true))
  formData.append('normalize_metric', String(options.normalizeMetric ?? true))

  const response = await authAwareFetch(`${projectPath(projectKey)}/spring-festival/extract-json`, {
    method: 'POST',
    headers: attachAuthHeaders({}, false),
    body: formData,
  })
  if (!response.ok) {
    let message = ''
    try {
      const payload = await response.json()
      const detail = payload?.detail
      if (typeof detail === 'string') {
        message = detail
      } else if (detail && typeof detail === 'object') {
        const base = detail.message || '解析 Excel 失败'
        const issues = Array.isArray(detail?.validation?.issues) ? detail.validation.issues : []
        message = issues.length ? `${base}：${issues.join('；')}` : base
      }
    } catch {
      message = await response.text()
    }
    throw new Error(message || `解析 Excel 失败: ${response.status}`)
  }
  return response.json()
}

export async function getMonthlyDataPullWorkspace(projectKey) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/monthly-data-pull/workspace`, {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `读取导表工作目录失败: ${response.status}`)
  }
  return response.json()
}

export async function listMonthlyDataPullFiles(projectKey, bucket) {
  const response = await authAwareFetch(
    `${projectPath(projectKey)}/monthly-data-pull/files?bucket=${encodeURIComponent(bucket || '')}`,
    { headers: attachAuthHeaders() },
  )
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `读取目录文件失败: ${response.status}`)
  }
  return response.json()
}

export async function uploadMonthlyDataPullFiles(projectKey, bucket, files = []) {
  if (!Array.isArray(files) || files.length === 0) {
    throw new Error('请先选择要上传的文件')
  }
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }
  const response = await authAwareFetch(
    `${projectPath(projectKey)}/monthly-data-pull/files/upload?bucket=${encodeURIComponent(bucket || '')}`,
    {
      method: 'POST',
      headers: attachAuthHeaders({}, false),
      body: formData,
    },
  )
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `上传文件失败: ${response.status}`)
  }
  return response.json()
}

export async function analyzeMonthlyDataPullMapping(projectKey, file) {
  if (!file) throw new Error('请先选择映射文件')
  const formData = new FormData()
  formData.append('file', file)
  const response = await authAwareFetch(`${projectPath(projectKey)}/monthly-data-pull/analyze-mapping`, {
    method: 'POST',
    headers: attachAuthHeaders({}, false),
    body: formData,
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `解析映射失败: ${response.status}`)
  }
  return response.json()
}

export async function getMonthlyDataPullSheets(projectKey, bucket, file) {
  if (!file) throw new Error('请先选择文件')
  const formData = new FormData()
  formData.append('file', file)
  const response = await authAwareFetch(
    `${projectPath(projectKey)}/monthly-data-pull/get-sheets?bucket=${encodeURIComponent(bucket || '')}`,
    {
      method: 'POST',
      headers: attachAuthHeaders({}, false),
      body: formData,
    },
  )
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `读取工作表失败: ${response.status}`)
  }
  return response.json()
}

export async function executeMonthlyDataPull(projectKey, payload) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/monthly-data-pull/execute`, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify(payload || {}),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `执行导表失败: ${response.status}`)
  }
  return response.json()
}

export async function clearMonthlyDataPullWorkspace(projectKey) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/monthly-data-pull/clear-workspace`, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({}),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `清空目录失败: ${response.status}`)
  }
  return response.json()
}

export async function downloadMonthlyDataPullOutputsZip(projectKey) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/monthly-data-pull/download-outputs-zip`, {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `打包下载失败: ${response.status}`)
  }
  const blob = await response.blob()
  const disposition = response.headers.get('content-disposition') || ''
  const matched = disposition.match(/filename="?([^"]+)"?/i)
  return {
    blob,
    filename: matched?.[1] || 'monthly_data_pull_outputs.zip',
  }
}

export function buildMonthlyDataPullDownloadUrl(projectKey, filename) {
  return `${projectPath(projectKey)}/monthly-data-pull/download/${encodeURIComponent(filename || '')}`
}

export async function downloadMonthlyDataPullOutputFile(projectKey, filename) {
  const response = await authAwareFetch(buildMonthlyDataPullDownloadUrl(projectKey, filename), {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `下载文件失败: ${response.status}`)
  }
  const blob = await response.blob()
  const disposition = response.headers.get('content-disposition') || ''
  const matched = disposition.match(/filename="?([^"]+)"?/i)
  return {
    blob,
    filename: matched?.[1] || filename || 'download.bin',
  }
}

export async function inspectMonthlyDataShowFile(projectKey, file) {
  if (!file) throw new Error('请先选择文件')
  const formData = new FormData()
  formData.append('file', file)
  const response = await authAwareFetch(`${projectPath(projectKey)}/monthly-data-show/inspect`, {
    method: 'POST',
    headers: attachAuthHeaders({}, false),
    body: formData,
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `读取可选项失败: ${response.status}`)
  }
  return response.json()
}

export async function extractMonthlyDataShowCsv(
  projectKey,
  file,
  companies = [],
  fields = [],
  sourceColumns = [],
  extractionRuleIds = [],
  reportYear = null,
  reportMonth = null,
  constantsEnabled = false,
  constantRules = [],
) {
  if (!file) throw new Error('请先选择文件')
  const formData = new FormData()
  formData.append('file', file)
  for (const company of companies || []) {
    formData.append('companies', company)
  }
  for (const field of fields || []) {
    formData.append('fields', field)
  }
  for (const sourceColumn of sourceColumns || []) {
    formData.append('source_columns', sourceColumn)
  }
  for (const ruleId of extractionRuleIds || []) {
    formData.append('extraction_rule_ids', ruleId)
  }
  if (Number.isInteger(reportYear)) {
    formData.append('report_year', String(reportYear))
  }
  if (Number.isInteger(reportMonth)) {
    formData.append('report_month', String(reportMonth))
  }
  formData.append('constants_enabled', String(Boolean(constantsEnabled)))
  formData.append('constant_rules_json', JSON.stringify(Array.isArray(constantRules) ? constantRules : []))
  const response = await authAwareFetch(`${projectPath(projectKey)}/monthly-data-show/extract-csv`, {
    method: 'POST',
    headers: attachAuthHeaders({}, false),
    body: formData,
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `提取 CSV 失败: ${response.status}`)
  }
  const blob = await response.blob()
  const disposition = response.headers.get('content-disposition') || ''
  const matched = disposition.match(/filename=\"?([^\"]+)\"?/i)
  const semiCalculatedCompleted = Number.parseInt(response.headers.get('x-monthly-semi-calculated-completed') || '0', 10)
  const jinpuHeatingAreaAdjusted = Number.parseInt(response.headers.get('x-monthly-jinpu-heating-area-adjusted') || '0', 10)
  const itemExcludeHits = Number.parseInt(response.headers.get('x-monthly-item-exclude-hits') || '0', 10)
  const itemRenameHits = Number.parseInt(response.headers.get('x-monthly-item-rename-hits') || '0', 10)
  const constantsInjected = Number.parseInt(response.headers.get('x-monthly-constants-injected') || '0', 10)
  const extractedTotalRows = Number.parseInt(response.headers.get('x-monthly-extracted-total-rows') || '0', 10)
  return {
    blob,
    filename: matched?.[1] || 'monthly_data_show_extract.csv',
    stats: {
      semiCalculatedCompleted: Number.isFinite(semiCalculatedCompleted) ? semiCalculatedCompleted : 0,
      jinpuHeatingAreaAdjusted: Number.isFinite(jinpuHeatingAreaAdjusted) ? jinpuHeatingAreaAdjusted : 0,
      itemExcludeHits: Number.isFinite(itemExcludeHits) ? itemExcludeHits : 0,
      itemRenameHits: Number.isFinite(itemRenameHits) ? itemRenameHits : 0,
      constantsInjected: Number.isFinite(constantsInjected) ? constantsInjected : 0,
      extractedTotalRows: Number.isFinite(extractedTotalRows) ? extractedTotalRows : 0,
    },
  }
}

export async function importMonthlyDataShowCsv(projectKey, file) {
  if (!file) throw new Error('请先选择 CSV 文件')
  const formData = new FormData()
  formData.append('file', file)
  const response = await authAwareFetch(`${projectPath(projectKey)}/monthly-data-show/import-csv`, {
    method: 'POST',
    headers: attachAuthHeaders({}, false),
    body: formData,
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `CSV 入库失败: ${response.status}`)
  }
  return response.json()
}

export async function getMonthlyDataShowQueryOptions(projectKey) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/monthly-data-show/query-options`, {
    headers: attachAuthHeaders(),
    cache: 'no-store',
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `读取查询筛选项失败: ${response.status}`)
  }
  return response.json()
}

export async function queryMonthlyDataShow(projectKey, payload = {}) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/monthly-data-show/query`, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify(payload || {}),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `查询月报数据失败: ${response.status}`)
  }
  return response.json()
}

export async function queryMonthlyDataShowComparison(projectKey, payload = {}) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/monthly-data-show/query-comparison`, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify(payload || {}),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `查询月报同比环比失败: ${response.status}`)
  }
  return response.json()
}

export async function queryMonthlyDataShowAiChat(projectKey, payload = {}) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/monthly-data-show/ai-chat/query`, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify(payload || {}),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `月报对话查询失败: ${response.status}`)
  }
  return response.json()
}

export async function queryMonthlyDataShowDialogChat(projectKey, payload = {}) {
  const requestUrl = `${projectPath(projectKey)}/monthly-data-show/ai-chat/dialog`
  const response = await fetchWithDevChatFallback(requestUrl, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify(payload || {}),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `月报页面聊天失败: ${response.status} (${requestUrl})`)
  }
  return response.json()
}

export async function startMonthlyDataShowAiReport(projectKey, payload = {}) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/monthly-data-show/ai-report/start`, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify(payload || {}),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `启动月报 AI 报告失败: ${response.status}`)
  }
  return response.json()
}

export async function getMonthlyDataShowAiReport(projectKey, jobId) {
  if (!jobId) throw new Error('缺少月报 AI 报告任务 ID')
  const response = await authAwareFetch(
    `${projectPath(projectKey)}/monthly-data-show/ai-report/${encodeURIComponent(jobId)}`,
    {
      headers: attachAuthHeaders(),
    },
  )
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取月报 AI 报告失败: ${response.status}`)
  }
  return response.json()
}

export async function listSheets(projectKey, configFile) {
  const search = configFile ? `?config=${encodeURIComponent(configFile)}` : ''
  const response = await authAwareFetch(`${projectPath(projectKey)}/data_entry/sheets${search}`, {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    throw new Error(`加载表格列表失败: ${response.status}`)
  }
  return response.json()
}

export async function getSheetsSubmissionStatus(projectKey, configFile) {
  const search = configFile ? `?config=${encodeURIComponent(configFile)}` : ''
  const response = await authAwareFetch(
    `${projectPath(projectKey)}/data_entry/sheets/submission-status${search}`,
    {
      headers: attachAuthHeaders(),
    },
  )
  if (!response.ok) {
    // 静默失败，返回空状态
    console.warn('获取填报状态失败', response.status)
    return { ok: true, status: {} }
  }
  return response.json()
}

export async function getTemplate(projectKey, sheetKey, options = {}) {
  const { config } = options
  const search = config ? `?config=${encodeURIComponent(config)}` : ''
  const response = await authAwareFetch(
    `${projectPath(projectKey)}/data_entry/sheets/${encodeURIComponent(sheetKey)}/template${search}`,
    {
      headers: attachAuthHeaders(),
    },
  )
  if (!response.ok) {
    throw new Error(`加载模板失败: ${response.status}`)
  }
  return response.json()
}

export async function submitData(projectKey, sheetKey, payload, options = {}) {
  const { config } = options
  const search = config ? `?config=${encodeURIComponent(config)}` : ''
  const response = await authAwareFetch(
    `${projectPath(projectKey)}/data_entry/sheets/${encodeURIComponent(sheetKey)}/submit${search}`,
    {
      method: 'POST',
      headers: attachAuthHeaders(JSON_HEADERS),
      body: JSON.stringify(payload),
    },
  )
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || '提交数据失败')
  }
  return response.json()
}

export async function queryData(projectKey, sheetKey, payload, options = {}) {
  const { config } = options
  const search = config ? `?config=${encodeURIComponent(config)}` : ''
  // 附加请求ID（若外部未提供）
  const requestId = payload && payload.request_id
    ? String(payload.request_id)
    : `${Date.now()}_${Math.random().toString(36).slice(2,8)}`
  const enriched = { ...(payload || {}), request_id: requestId }
  const response = await authAwareFetch(
    `${projectPath(projectKey)}/data_entry/sheets/${encodeURIComponent(sheetKey)}/query${search}`,
    {
      method: 'POST',
      headers: attachAuthHeaders(JSON_HEADERS),
      body: JSON.stringify(enriched),
    },
  )
  if (!response.ok) {
    throw new Error(`查询数据失败: ${response.status}`)
  }
  const data = await response.json()
  return { ...data, __request_id: requestId }
}

export function resetProjectCache() {
  cachedProjects = null
  cachedProjectsToken = null
}

// 运行时表达式求值（审批渲染）
export async function evalSpec(projectKey, body, options = {}) {
  const url = normalized('/projects/daily_report_25_26/runtime/spec/eval')
  const response = await authAwareFetch(url, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify(body || {}),
    signal: options?.signal,
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `runtime eval 失败: ${response.status}`)
  }
  return response.json()
}

export async function evalSpecsBatch(projectKey, body, options = {}) {
  const url = normalized('/projects/daily_report_25_26/runtime/spec/eval-batch')
  const response = await authAwareFetch(url, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify(body || {}),
    signal: options?.signal,
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `runtime batch eval 失败: ${response.status}`)
  }
  return response.json()
}

export async function getWorkflowStatus(projectKey) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/workflow/status`, {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || '获取审批进度失败')
  }
  return response.json()
}

export async function approveWorkflow(projectKey, payload) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/workflow/approve`, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify(payload || {}),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || '提交审批状态失败')
  }
  return response.json()
}

export async function revokeWorkflow(projectKey, payload) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/workflow/revoke`, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify(payload || {}),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || '取消批准失败')
  }
  return response.json()
}

export async function publishWorkflow(projectKey) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/workflow/publish`, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({ confirm: true }),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || '发布日报失败')
  }
  return response.json()
}

export async function getDashboardData(projectKey, params = {}) {
  const showDate =
    typeof params.showDate === 'string' ? params.showDate : ''
  const search = `?show_date=${encodeURIComponent(showDate)}`
  const response = await authAwareFetch(`${projectPath(projectKey)}/dashboard${search}`, {
    headers: attachAuthHeaders(),
    signal: params.signal,
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取数据看板失败: ${response.status}`)
  }
  return response.json()
}

export async function getDashboardTemperatureTrend(projectKey, params = {}) {
  const showDate =
    typeof params.showDate === 'string' ? params.showDate : ''
  const startDate =
    typeof params.startDate === 'string' ? params.startDate : ''
  const endDate =
    typeof params.endDate === 'string' ? params.endDate : ''
  const search = new URLSearchParams({
    show_date: showDate,
    start_date: startDate,
    end_date: endDate,
  })
  const response = await authAwareFetch(`${projectPath(projectKey)}/dashboard/temperature/trend?${search.toString()}`, {
    headers: attachAuthHeaders(),
    signal: params.signal,
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取气温趋势失败: ${response.status}`)
  }
  return response.json()
}

export async function getDashboardBizDate(projectKey) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/dashboard/date`, {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取业务日期失败: ${response.status}`)
  }
  return response.json()
}

export async function publishDashboardCache(projectKey, params = {}) {
  const rawDays = Number(params?.days)
  const days = Number.isFinite(rawDays) ? Math.max(1, Math.min(30, Math.floor(rawDays))) : 7
  const response = await authAwareFetch(`${projectPath(projectKey)}/dashboard/cache/publish?days=${days}`, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({}),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `发布缓存失败: ${response.status}`)
  }
  return response.json()
}

export async function getCachePublishStatus(projectKey) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/dashboard/cache/publish/status`, {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取缓存任务状态失败: ${response.status}`)
  }
  return response.json()
}

export async function cancelCachePublishJob(projectKey) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/dashboard/cache/publish/cancel`, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({}),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `发布缓存失败: ${response.status}`)
  }
  return response.json()
}

export async function refreshDashboardCache(projectKey, params = {}) {
  const showDate = typeof params.showDate === 'string' ? params.showDate : ''
  const search = `?show_date=${encodeURIComponent(showDate)}`
  const response = await authAwareFetch(`${projectPath(projectKey)}/dashboard/cache/refresh${search}`, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({}),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `刷新缓存失败: ${response.status}`)
  }
  return response.json()
}

export async function disableDashboardCache(projectKey) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/dashboard/cache`, {
    method: 'DELETE',
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `禁用缓存失败: ${response.status}`)
  }
  return response.json()
}

export async function importTemperatureData(projectKey) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/dashboard/temperature/import`, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({}),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取气温数据失败: ${response.status}`)
  }
  return response.json()
}

export async function commitTemperatureData(projectKey) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/dashboard/temperature/import/commit`, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({}),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `写入气温数据失败: ${response.status}`)
  }
  return response.json()
}

export async function getDataAnalysisSchema(projectKey, options = {}) {
  const { config } = options
  const search = config ? `?config=${encodeURIComponent(config)}` : ''
  const response = await authAwareFetch(
    `${projectPath(projectKey)}/data_analysis/schema${search}`,
    { headers: attachAuthHeaders(), cache: 'no-store' },
  )
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取数据分析配置失败: ${response.status}`)
  }
  return response.json()
}

export async function runDataAnalysis(projectKey, payload, options = {}) {
  const { config } = options
  const search = config ? `?config=${encodeURIComponent(config)}` : ''
  const response = await authAwareFetch(
    `${projectPath(projectKey)}/data_analysis/query${search}`,
    {
      method: 'POST',
      headers: attachAuthHeaders(JSON_HEADERS),
      body: JSON.stringify(payload || {}),
    },
  )
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `执行数据分析失败: ${response.status}`)
  }
  return response.json()
}

export async function getDataAnalysisAiReport(projectKey, jobId) {
  if (!jobId) {
    throw new Error('缺少智能报告任务 ID')
  }
  const response = await authAwareFetch(
    `${projectPath(projectKey)}/data_analysis/ai_report/${encodeURIComponent(jobId)}`,
    {
      headers: attachAuthHeaders(),
    },
  )
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取智能报告失败: ${response.status}`)
  }
  return response.json()
}

export async function runDataAnalysisDialogChat(projectKey, payload = {}) {
  const requestUrl = `${projectPath(projectKey)}/data_analysis/ai-chat/dialog`
  const response = await fetchWithDevChatFallback(requestUrl, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify(payload || {}),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `数据分析聊天失败: ${response.status} (${requestUrl})`)
  }
  return response.json()
}

export async function getAiSettings(projectKey) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/data_analysis/ai_settings`, {
    headers: attachAuthHeaders(),
    cache: 'no-store',
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取智能体配置失败: ${response.status}`)
  }
  return response.json()
}

export async function updateAiSettings(projectKey, payload) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/data_analysis/ai_settings`, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({
      api_keys: Array.isArray(payload?.api_keys) ? payload.api_keys : [],
      model: payload?.model ?? '',
      provider: payload?.provider ?? 'gemini',
      newapi_base_url: payload?.newapi_base_url ?? '',
      newapi_api_keys: Array.isArray(payload?.newapi_api_keys) ? payload.newapi_api_keys : [],
      newapi_model: payload?.newapi_model ?? '',
      providers: Array.isArray(payload?.providers) ? payload.providers : [],
      active_provider_id: payload?.active_provider_id ?? '',
      instruction_daily: payload?.instruction_daily ?? payload?.instruction,
      instruction_monthly: payload?.instruction_monthly,
      report_mode: payload?.report_mode ?? 'full',
      enable_validation: payload?.enable_validation ?? true,
      allow_non_admin_report: payload?.allow_non_admin_report ?? false,
      show_chat_bubble: payload?.show_chat_bubble ?? true,
    }),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `保存智能体配置失败: ${response.status}`)
  }
  return response.json()
}

export async function testAiSettings(projectKey, payload) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/data_analysis/ai_settings/test`, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({
      provider: payload?.provider ?? 'gemini',
      api_keys: Array.isArray(payload?.api_keys) ? payload.api_keys : [],
      model: payload?.model ?? '',
      newapi_base_url: payload?.newapi_base_url ?? '',
      newapi_api_keys: Array.isArray(payload?.newapi_api_keys) ? payload.newapi_api_keys : [],
      newapi_model: payload?.newapi_model ?? '',
      providers: Array.isArray(payload?.providers) ? payload.providers : [],
      active_provider_id: payload?.active_provider_id ?? '',
    }),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `测试智能体配置失败: ${response.status}`)
  }
  return response.json()
}

export async function getUnitAnalysisMetrics(projectKey, params = {}) {
  const { config, unit_key: unitKey } = params
  const searchParams = new URLSearchParams()
  if (config) searchParams.set('config', config)
  if (unitKey) searchParams.set('unit_key', unitKey)
  const response = await authAwareFetch(
    `${projectPath(projectKey)}/data_entry/analysis/metrics?${searchParams.toString()}`,
    { headers: attachAuthHeaders() },
  )
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取本单位分析指标失败: ${response.status}`)
  }
  return response.json()
}

export async function getValidationMasterSwitch(projectKey) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/data_entry/validation/master-switch`, {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取全局校验状态失败: ${response.status}`)
  }
  return response.json()
}

export async function setValidationMasterSwitch(projectKey, enabled) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/data_entry/validation/master-switch`, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({ validation_enabled: Boolean(enabled) }),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `更新全局校验状态失败: ${response.status}`)
  }
  return response.json()
}

export async function getSheetValidationSwitch(projectKey, sheetKey, options = {}) {
  const { config } = options
  const search = config ? `?config=${encodeURIComponent(config)}` : ''
  const response = await authAwareFetch(
    `${projectPath(projectKey)}/data_entry/sheets/${encodeURIComponent(sheetKey)}/validation-switch${search}`,
    {
      headers: attachAuthHeaders(),
    },
  )
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取表级校验状态失败: ${response.status}`)
  }
  return response.json()
}

export async function setSheetValidationSwitch(projectKey, sheetKey, enabled, options = {}) {
  const { config } = options
  const search = config ? `?config=${encodeURIComponent(config)}` : ''
  const response = await authAwareFetch(
    `${projectPath(projectKey)}/data_entry/sheets/${encodeURIComponent(sheetKey)}/validation-switch${search}`,
    {
      method: 'POST',
      headers: attachAuthHeaders(JSON_HEADERS),
      body: JSON.stringify({ validation_enabled: Boolean(enabled) }),
    },
  )
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `更新表级校验状态失败: ${response.status}`)
  }
  return response.json()
}

export async function getSheetAiSwitch(projectKey, sheetKey, options = {}) {
  const { config } = options
  const search = config ? `?config=${encodeURIComponent(config)}` : ''
  const response = await authAwareFetch(
    `${projectPath(projectKey)}/data_entry/sheets/${encodeURIComponent(sheetKey)}/ai-switch${search}`,
    {
      headers: attachAuthHeaders(),
    },
  )
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取表级 AI 开关失败: ${response.status}`)
  }
  return response.json()
}

export async function setSheetAiSwitch(projectKey, sheetKey, enabled, options = {}) {
  const { config } = options
  const search = config ? `?config=${encodeURIComponent(config)}` : ''
  const response = await authAwareFetch(
    `${projectPath(projectKey)}/data_entry/sheets/${encodeURIComponent(sheetKey)}/ai-switch${search}`,
    {
      method: 'POST',
      headers: attachAuthHeaders(JSON_HEADERS),
      body: JSON.stringify({ ai_report_enabled: Boolean(enabled) }),
    },
  )
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `更新表级 AI 开关失败: ${response.status}`)
  }
  return response.json()
}

export async function getAdminOverview(projectKey = 'daily_report_25_26') {
  const search = `?project_key=${encodeURIComponent(projectKey)}`
  const response = await authAwareFetch(normalized(`/admin/overview${search}`), {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取管理后台概览失败: ${response.status}`)
  }
  return response.json()
}

export async function listAdminProjects() {
  const response = await authAwareFetch(normalized('/admin/projects'), {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取项目列表失败: ${response.status}`)
  }
  return response.json()
}

export async function listAdminFileDirectories() {
  const response = await authAwareFetch(normalized('/admin/files/directories'), {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取目录列表失败: ${response.status}`)
  }
  return response.json()
}

export async function listAdminFiles(directory) {
  const search = `?directory=${encodeURIComponent(directory || '')}`
  const response = await authAwareFetch(normalized(`/admin/files${search}`), {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取文件列表失败: ${response.status}`)
  }
  return response.json()
}

export async function readAdminFile(path) {
  const search = `?path=${encodeURIComponent(path || '')}`
  const response = await authAwareFetch(normalized(`/admin/files/content${search}`), {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `读取文件失败: ${response.status}`)
  }
  return response.json()
}

export async function saveAdminFile(path, content) {
  const response = await authAwareFetch(normalized('/admin/files/content'), {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({ path, content }),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `保存文件失败: ${response.status}`)
  }
  return response.json()
}

export async function listAdminDbTables() {
  const response = await authAwareFetch(normalized('/admin/db/tables'), {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取数据库表失败: ${response.status}`)
  }
  return response.json()
}

export async function queryAdminDbTable(payload = {}) {
  const response = await authAwareFetch(normalized('/admin/db/table/query'), {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({
      table: payload?.table || '',
      limit: payload?.limit ?? 200,
      offset: payload?.offset ?? 0,
      search: payload?.search ?? '',
      filters: Array.isArray(payload?.filters) ? payload.filters : [],
      order_by: payload?.order_by ?? '',
      order_dir: payload?.order_dir ?? 'asc',
    }),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `查询数据表失败: ${response.status}`)
  }
  return response.json()
}

export async function batchUpdateAdminDbTable(payload = {}) {
  const response = await authAwareFetch(normalized('/admin/db/table/batch-update'), {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({
      table: payload?.table || '',
      updates: Array.isArray(payload?.updates) ? payload.updates : [],
    }),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `保存数据表修改失败: ${response.status}`)
  }
  return response.json()
}

export async function getAdminValidationMasterSwitch() {
  const response = await authAwareFetch(normalized('/admin/validation/master-switch'), {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取全局校验状态失败: ${response.status}`)
  }
  return response.json()
}

export async function setAdminValidationMasterSwitch(enabled) {
  const response = await authAwareFetch(normalized('/admin/validation/master-switch'), {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({ validation_enabled: Boolean(enabled) }),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `更新全局校验状态失败: ${response.status}`)
  }
  return response.json()
}

export async function getAdminAiSettings() {
  const response = await authAwareFetch(normalized('/admin/ai-settings'), {
    headers: attachAuthHeaders(),
    cache: 'no-store',
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取 AI 设置失败: ${response.status}`)
  }
  return response.json()
}

export async function updateAdminAiSettings(payload) {
  const response = await authAwareFetch(normalized('/admin/ai-settings'), {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({
      api_keys: Array.isArray(payload?.api_keys) ? payload.api_keys : [],
      model: payload?.model ?? '',
      provider: payload?.provider ?? 'gemini',
      newapi_base_url: payload?.newapi_base_url ?? '',
      newapi_api_keys: Array.isArray(payload?.newapi_api_keys) ? payload.newapi_api_keys : [],
      newapi_model: payload?.newapi_model ?? '',
      providers: Array.isArray(payload?.providers) ? payload.providers : [],
      active_provider_id: payload?.active_provider_id ?? '',
      instruction_daily: payload?.instruction_daily ?? payload?.instruction,
      instruction_monthly: payload?.instruction_monthly,
      report_mode: payload?.report_mode ?? 'full',
      enable_validation: payload?.enable_validation ?? true,
      allow_non_admin_report: payload?.allow_non_admin_report ?? false,
      show_chat_bubble: payload?.show_chat_bubble ?? true,
    }),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `保存 AI 设置失败: ${response.status}`)
  }
  return response.json()
}

export async function testAdminAiSettings(payload) {
  const response = await authAwareFetch(normalized('/admin/ai-settings/test'), {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({
      provider: payload?.provider ?? 'gemini',
      api_keys: Array.isArray(payload?.api_keys) ? payload.api_keys : [],
      model: payload?.model ?? '',
      newapi_base_url: payload?.newapi_base_url ?? '',
      newapi_api_keys: Array.isArray(payload?.newapi_api_keys) ? payload.newapi_api_keys : [],
      newapi_model: payload?.newapi_model ?? '',
      providers: Array.isArray(payload?.providers) ? payload.providers : [],
      active_provider_id: payload?.active_provider_id ?? '',
    }),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `测试 AI 设置失败: ${response.status}`)
  }
  return response.json()
}

export async function publishAdminDashboardCache(params = {}) {
  const rawDays = Number(params?.days)
  const days = Number.isFinite(rawDays) ? Math.max(1, Math.min(30, Math.floor(rawDays))) : 7
  const response = await authAwareFetch(normalized(`/admin/cache/publish?days=${days}`), {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({}),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `发布缓存失败: ${response.status}`)
  }
  return response.json()
}

export async function getAdminCachePublishStatus() {
  const response = await authAwareFetch(normalized('/admin/cache/publish/status'), {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取缓存任务状态失败: ${response.status}`)
  }
  return response.json()
}

export async function cancelAdminCachePublishJob() {
  const response = await authAwareFetch(normalized('/admin/cache/publish/cancel'), {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({}),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `停止缓存任务失败: ${response.status}`)
  }
  return response.json()
}

export async function disableAdminCache() {
  const response = await authAwareFetch(normalized('/admin/cache'), {
    method: 'DELETE',
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `禁用缓存失败: ${response.status}`)
  }
  return response.json()
}

export async function refreshAdminCache(params = {}) {
  const showDate = typeof params?.showDate === 'string' ? params.showDate : ''
  const response = await authAwareFetch(
    normalized(`/admin/cache/refresh?show_date=${encodeURIComponent(showDate)}`),
    {
      method: 'POST',
      headers: attachAuthHeaders(JSON_HEADERS),
      body: JSON.stringify({}),
    },
  )
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `刷新缓存失败: ${response.status}`)
  }
  return response.json()
}

export async function getProjectDashboardBizDate(projectKey) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/dashboard/date`, {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取业务日期失败: ${response.status}`)
  }
  return response.json()
}

export async function importProjectTemperatureData(projectKey) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/dashboard/temperature/import`, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({}),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取气温数据失败: ${response.status}`)
  }
  return response.json()
}

export async function commitProjectTemperatureData(projectKey) {
  const response = await authAwareFetch(`${projectPath(projectKey)}/dashboard/temperature/import/commit`, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({}),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `写入气温数据失败: ${response.status}`)
  }
  return response.json()
}

export async function getAdminSystemMetrics() {
  const response = await authAwareFetch(normalized('/admin/system/metrics'), {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取系统指标失败: ${response.status}`)
  }
  return response.json()
}

export async function postAdminAuditEvents(events = []) {
  const response = await authAwareFetch(normalized('/audit/events'), {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({ events: Array.isArray(events) ? events : [] }),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `上报审计日志失败: ${response.status}`)
  }
  return response.json()
}

export async function getAdminAuditEvents(params = {}) {
  const search = new URLSearchParams()
  if (params.days != null) search.set('days', String(params.days))
  if (params.username) search.set('username', String(params.username))
  if (params.category) search.set('category', String(params.category))
  if (params.action) search.set('action', String(params.action))
  if (params.keyword) search.set('keyword', String(params.keyword))
  if (params.limit != null) search.set('limit', String(params.limit))
  const response = await authAwareFetch(normalized(`/admin/audit/events?${search.toString()}`), {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取审计日志失败: ${response.status}`)
  }
  return response.json()
}

export async function getAdminAuditStats(params = {}) {
  const search = new URLSearchParams()
  if (params.days != null) search.set('days', String(params.days))
  const response = await authAwareFetch(normalized(`/admin/audit/stats?${search.toString()}`), {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取审计统计失败: ${response.status}`)
  }
  return response.json()
}

export async function execSuperCommand(payload) {
  const response = await authAwareFetch(normalized('/admin/super/terminal/exec'), {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({
      command: payload?.command || '',
      cwd: payload?.cwd || '',
      timeout_seconds: payload?.timeout_seconds ?? 20,
    }),
  })
  await ensureSuperResponseOk(response, `命令执行失败: ${response.status}`)
  return response.json()
}

export async function listSuperFiles(path) {
  const response = await authAwareFetch(normalized(`/admin/super/files/list?path=${encodeURIComponent(path || '')}`), {
    headers: attachAuthHeaders(),
  })
  await ensureSuperResponseOk(response, `目录读取失败: ${response.status}`)
  return response.json()
}

export async function readSuperFile(path) {
  const response = await authAwareFetch(normalized(`/admin/super/files/read?path=${encodeURIComponent(path || '')}`), {
    headers: attachAuthHeaders(),
  })
  await ensureSuperResponseOk(response, `文件读取失败: ${response.status}`)
  return response.json()
}

export async function writeSuperFile(path, content) {
  const response = await authAwareFetch(normalized('/admin/super/files/write'), {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({ path, content }),
  })
  await ensureSuperResponseOk(response, `文件写入失败: ${response.status}`)
  return response.json()
}

export async function makeSuperDirectory(path) {
  const response = await authAwareFetch(normalized('/admin/super/files/mkdir'), {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({ path }),
  })
  await ensureSuperResponseOk(response, `创建目录失败: ${response.status}`)
  return response.json()
}

export async function moveSuperPath(source, destination) {
  const response = await authAwareFetch(normalized('/admin/super/files/move'), {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({ source, destination }),
  })
  await ensureSuperResponseOk(response, `移动失败: ${response.status}`)
  return response.json()
}

export async function deleteSuperPath(path) {
  const response = await authAwareFetch(normalized(`/admin/super/files?path=${encodeURIComponent(path || '')}`), {
    method: 'DELETE',
    headers: attachAuthHeaders(),
  })
  await ensureSuperResponseOk(response, `删除失败: ${response.status}`)
  return response.json()
}

export async function uploadSuperFiles(targetDir, files = []) {
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }
  const response = await authAwareFetch(
    normalized(`/admin/super/files/upload?target_dir=${encodeURIComponent(targetDir || '')}`),
    {
      method: 'POST',
      headers: attachAuthHeaders({}, false),
      body: formData,
    },
  )
  await ensureSuperResponseOk(response, `上传失败: ${response.status}`)
  return response.json()
}
