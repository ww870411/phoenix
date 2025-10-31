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
