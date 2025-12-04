const rawBase =
  typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE
    ? import.meta.env.VITE_API_BASE
    : ''

// 兼容 VITE_API_BASE 未包含 /api/v1 的情况：自动补全标准前缀
const API_BASE = (() => {
  const base = rawBase ? String(rawBase).replace(/\/$/, '') : ''
  if (!base) return '/api/v1'
  return /(\/api)(\/|$)/.test(base) ? base : `${base}/api/v1`
})()

const JSON_HEADERS = { 'Content-Type': 'application/json' }

let authToken = null

function attachAuthHeaders(baseHeaders = {}, skipAuth = false) {
  const headers = { ...(baseHeaders || {}) }
  if (!skipAuth && authToken) {
    headers.Authorization = `Bearer ${authToken}`
  }
  return headers
}

export function setAuthToken(token) {
  authToken = token || null
}

export function getAuthToken() {
  return authToken
}

export function clearAuthToken() {
  authToken = null
  resetProjectCache()
}

const normalized = (path) => `${API_BASE}${path}`

const projectPath = (projectKey) => normalized(`/projects/${encodeURIComponent(projectKey)}`)

let cachedProjects = null

export async function login(credentials) {
  const response = await fetch(normalized('/auth/login'), {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS, true),
    body: JSON.stringify(credentials),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || '登录失败')
  }
  return response.json()
}

export async function fetchSession() {
  const response = await fetch(normalized('/auth/me'), {
    headers: attachAuthHeaders(),
  })
  if (response.status === 401) {
    clearAuthToken()
    throw new Error('登录状态已过期')
  }
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || '获取登录信息失败')
  }
  return response.json()
}

export async function logout() {
  await fetch(normalized('/auth/logout'), {
    method: 'POST',
    headers: attachAuthHeaders(),
  })
  clearAuthToken()
}

export async function listProjects(force = false) {
  if (!force && Array.isArray(cachedProjects)) {
    return cachedProjects
  }

  const response = await fetch(normalized('/projects'), {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    cachedProjects = null
    throw new Error(`加载项目列表失败: ${response.status}`)
  }

  const payload = await response.json()
  const list = Array.isArray(payload?.projects) ? payload.projects : []
  cachedProjects = list
  return list
}

export async function listPages(projectKey) {
  const response = await fetch(`${projectPath(projectKey)}/pages`, {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    throw new Error(`加载页面配置失败: ${response.status}`)
  }
  return response.json()
}

export async function listSheets(projectKey, configFile) {
  const search = configFile ? `?config=${encodeURIComponent(configFile)}` : ''
  const response = await fetch(`${projectPath(projectKey)}/data_entry/sheets${search}`, {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    throw new Error(`加载表格列表失败: ${response.status}`)
  }
  return response.json()
}

export async function getTemplate(projectKey, sheetKey, options = {}) {
  const { config } = options
  const search = config ? `?config=${encodeURIComponent(config)}` : ''
  const response = await fetch(
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
  const response = await fetch(
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
  const response = await fetch(
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
}

// 运行时表达式求值（审批渲染）
export async function evalSpec(projectKey, body) {
  const url = normalized('/projects/daily_report_25_26/runtime/spec/eval')
  const response = await fetch(url, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify(body || {}),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `runtime eval 失败: ${response.status}`)
  }
  return response.json()
}

export async function getWorkflowStatus(projectKey) {
  const response = await fetch(`${projectPath(projectKey)}/workflow/status`, {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || '获取审批进度失败')
  }
  return response.json()
}

export async function approveWorkflow(projectKey, payload) {
  const response = await fetch(`${projectPath(projectKey)}/workflow/approve`, {
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
  const response = await fetch(`${projectPath(projectKey)}/workflow/revoke`, {
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
  const response = await fetch(`${projectPath(projectKey)}/workflow/publish`, {
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
  const response = await fetch(`${projectPath(projectKey)}/dashboard${search}`, {
    headers: attachAuthHeaders(),
    signal: params.signal,
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取数据看板失败: ${response.status}`)
  }
  return response.json()
}

export async function getDashboardBizDate(projectKey) {
  const response = await fetch(`${projectPath(projectKey)}/dashboard/date`, {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取业务日期失败: ${response.status}`)
  }
  return response.json()
}

export async function publishDashboardCache(projectKey) {
  const response = await fetch(`${projectPath(projectKey)}/dashboard/cache/publish`, {
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
  const response = await fetch(`${projectPath(projectKey)}/dashboard/cache/publish/status`, {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取缓存任务状态失败: ${response.status}`)
  }
  return response.json()
}

export async function cancelCachePublishJob(projectKey) {
  const response = await fetch(`${projectPath(projectKey)}/dashboard/cache/publish/cancel`, {
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
  const response = await fetch(`${projectPath(projectKey)}/dashboard/cache/refresh${search}`, {
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
  const response = await fetch(`${projectPath(projectKey)}/dashboard/cache`, {
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
  const response = await fetch(`${projectPath(projectKey)}/dashboard/temperature/import`, {
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
  const response = await fetch(`${projectPath(projectKey)}/dashboard/temperature/import/commit`, {
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
  const response = await fetch(
    `${projectPath(projectKey)}/data_analysis/schema${search}`,
    { headers: attachAuthHeaders() },
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
  const response = await fetch(
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
  const response = await fetch(
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

export async function getAiSettings(projectKey) {
  const response = await fetch(`${projectPath(projectKey)}/data_analysis/ai_settings`, {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取智能体配置失败: ${response.status}`)
  }
  return response.json()
}

export async function updateAiSettings(projectKey, payload) {
  const response = await fetch(`${projectPath(projectKey)}/data_analysis/ai_settings`, {
    method: 'POST',
    headers: attachAuthHeaders(JSON_HEADERS),
    body: JSON.stringify({
      api_keys: Array.isArray(payload?.api_keys) ? payload.api_keys : [],
      model: payload?.model ?? '',
      instruction: payload?.instruction ?? '',
      enable_validation: payload?.enable_validation ?? true,
      allow_non_admin_report: payload?.allow_non_admin_report ?? false,
    }),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `保存智能体配置失败: ${response.status}`)
  }
  return response.json()
}

export async function getUnitAnalysisMetrics(projectKey, params = {}) {
  const { config, unit_key: unitKey } = params
  const searchParams = new URLSearchParams()
  if (config) searchParams.set('config', config)
  if (unitKey) searchParams.set('unit_key', unitKey)
  const response = await fetch(
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
  const response = await fetch(`${projectPath(projectKey)}/data_entry/validation/master-switch`, {
    headers: attachAuthHeaders(),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `获取全局校验状态失败: ${response.status}`)
  }
  return response.json()
}

export async function setValidationMasterSwitch(projectKey, enabled) {
  const response = await fetch(`${projectPath(projectKey)}/data_entry/validation/master-switch`, {
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
  const response = await fetch(
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
  const response = await fetch(
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
  const response = await fetch(
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
  const response = await fetch(
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
