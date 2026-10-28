// -*- coding: utf-8 -*-
/**
 * 调度信息 (DOCX / PDF 智能提取、入库与多维查询) 专眼前端 API 服务
 */

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

const API_BASE = (() => {
  const base = rawBase ? String(rawBase).replace(/\/$/, '') : ''
  if (!base) return '/api/v1'
  const normalizedBase = /(\/api)(\/|$)/.test(base) ? base : `${base}/api/v1`
  if (shouldPreferSameOriginProxy(normalizedBase)) return '/api/v1'
  return normalizedBase
})()

const JSON_HEADERS = { 'Content-Type': 'application/json' }

function getAuthHeader(customToken) {
  if (customToken) {
    return { Authorization: `Bearer ${customToken}` }
  }
  if (typeof window === 'undefined') return {}
  try {
    for (const key of ['phoenix_auth', 'phoenix_auth_state']) {
      for (const storage of [localStorage, sessionStorage]) {
        try {
          const raw = storage.getItem(key)
          if (raw) {
            const parsed = JSON.parse(raw)
            const token = parsed?.token || parsed?.access_token
            if (token) {
              return { Authorization: `Bearer ${token}` }
            }
          }
        } catch (e) {}
      }
    }
  } catch (e) {}
  return {}
}

async function parseErrorDetail(response, defaultMsg) {
  try {
    const data = await response.json()
    return data?.detail || data?.message || defaultMsg
  } catch (e) {
    return defaultMsg
  }
}

function projectUrl(projectKey, path) {
  return `${API_BASE}/projects/${encodeURIComponent(projectKey)}/dispatch${path}`
}

/**
 * 智能提取 DOCX / PDF 调度文件
 */
export async function extractDispatchFiles(projectKey = 'daily_report_25_26', formData, customToken = '') {
  const url = projectUrl(projectKey, '/extract')
  const response = await fetch(url, {
    method: 'POST',
    headers: { ...getAuthHeader(customToken) },
    body: formData,
  })
  if (!response.ok) {
    const msg = await parseErrorDetail(response, '提取调度文件失败')
    throw new Error(msg)
  }
  return response.json()
}

/**
 * 获取提取生成的 JSON 文件下载链接
 */
export function getDispatchDownloadJsonUrl(projectKey = 'daily_report_25_26', token) {
  return `${projectUrl(projectKey, '/download_json')}?token=${encodeURIComponent(token)}`
}

/**
 * 带有鉴权请求头的文件下载 (避免新标签页缺少 Authorization Header 导致 401)
 */
export async function downloadDispatchJson(projectKey = 'daily_report_25_26', token, customAuthToken = '') {
  const url = getDispatchDownloadJsonUrl(projectKey, token)
  const response = await fetch(url, {
    method: 'GET',
    headers: { ...getAuthHeader(customAuthToken) },
  })
  if (!response.ok) {
    const msg = await parseErrorDetail(response, '下载提取文件失败')
    throw new Error(msg)
  }
  const blob = await response.blob()
  const blobUrl = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = `dispatch_extracted_batch_${new Date().toISOString().slice(0, 10)}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(blobUrl)
}

/**
 * 清理服务器临时提取文件
 */
export async function cleanupDispatchTemp(projectKey = 'daily_report_25_26', token) {
  const url = projectUrl(projectKey, '/cleanup')
  const response = await fetch(url, {
    method: 'POST',
    headers: { ...JSON_HEADERS, ...getAuthHeader() },
    body: JSON.stringify({ token }),
  })
  if (!response.ok) {
    const msg = await parseErrorDetail(response, '清理临时文件失败')
    throw new Error(msg)
  }
  return response.json()
}

/**
 * 一键保存入库 (支持冲突检测与覆盖更新)
 */
export async function saveDispatchData(projectKey = 'daily_report_25_26', payload) {
  const url = projectUrl(projectKey, '/save_to_db')
  const response = await fetch(url, {
    method: 'POST',
    headers: { ...JSON_HEADERS, ...getAuthHeader() },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    const msg = await parseErrorDetail(response, '调度数据保存入库失败')
    throw new Error(msg)
  }
  return response.json()
}

/**
 * 多维综合查询已入库调度信息
 */
export async function queryDispatchData(projectKey = 'daily_report_25_26', params = {}) {
  const searchParams = new URLSearchParams()
  if (params.biz_date) searchParams.append('biz_date', params.biz_date)
  if (params.start_date) searchParams.append('start_date', params.start_date)
  if (params.end_date) searchParams.append('end_date', params.end_date)
  if (params.keyword) searchParams.append('keyword', params.keyword)
  if (params.limit != null) searchParams.append('limit', String(params.limit))
  if (params.offset != null) searchParams.append('offset', String(params.offset))

  const queryString = searchParams.toString()
  const url = `${projectUrl(projectKey, '/query')}${queryString ? `?${queryString}` : ''}`
  const response = await fetch(url, {
    method: 'GET',
    headers: { ...getAuthHeader() },
  })
  if (!response.ok) {
    const msg = await parseErrorDetail(response, '查询调度数据失败')
    throw new Error(msg)
  }
  return response.json()
}

/**
 * 获取已有调度信息的所有日期列表
 */
export async function fetchDispatchDates(projectKey = 'daily_report_25_26') {
  const url = projectUrl(projectKey, '/dates')
  const response = await fetch(url, {
    method: 'GET',
    headers: { ...getAuthHeader() },
  })
  if (!response.ok) {
    const msg = await parseErrorDetail(response, '获取已有日期列表失败')
    throw new Error(msg)
  }
  return response.json()
}

/**
 * 一键导入历史全量 162 份数据
 */
export async function importHistoricalDispatch(projectKey = 'daily_report_25_26', overwrite = false) {
  const url = projectUrl(projectKey, '/import_historical_configs')
  const response = await fetch(url, {
    method: 'POST',
    headers: { ...JSON_HEADERS, ...getAuthHeader() },
    body: JSON.stringify({ overwrite }),
  })
  if (!response.ok) {
    const msg = await parseErrorDetail(response, '导入历史数据失败')
    throw new Error(msg)
  }
  return response.json()
}
