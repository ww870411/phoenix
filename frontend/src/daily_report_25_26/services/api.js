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

const normalized = (path) => `${API_BASE}${path}`

const projectPath = (projectKey) => normalized(`/projects/${encodeURIComponent(projectKey)}`)

let cachedProjects = null

export async function listProjects(force = false) {
  if (!force && Array.isArray(cachedProjects)) {
    return cachedProjects
  }

  const response = await fetch(normalized('/projects'))
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
  const response = await fetch(`${projectPath(projectKey)}/pages`)
  if (!response.ok) {
    throw new Error(`加载页面配置失败: ${response.status}`)
  }
  return response.json()
}

export async function listSheets(projectKey, configFile) {
  const search = configFile ? `?config=${encodeURIComponent(configFile)}` : ''
  const response = await fetch(`${projectPath(projectKey)}/data_entry/sheets${search}`)
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
      headers: JSON_HEADERS,
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
  const response = await fetch(
    `${projectPath(projectKey)}/data_entry/sheets/${encodeURIComponent(sheetKey)}/query${search}`,
    {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify(payload),
    },
  )
  if (!response.ok) {
    throw new Error(`查询数据失败: ${response.status}`)
  }
  return response.json()
}

export function resetProjectCache() {
  cachedProjects = null
}
