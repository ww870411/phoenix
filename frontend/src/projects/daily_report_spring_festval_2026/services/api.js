import {
  extractSpringFestivalJson as extractByDateJson,
  getDashboardData,
  getDashboardTemperatureTrend,
  getAuthToken,
} from '../../daily_report_25_26/services/api'

let latestExtractedPayload = null

export async function extractSpringFestivalJson(projectKey, file, options = {}) {
  return extractByDateJson(projectKey, file, options)
}

export async function getTemperatureTrendByDate(projectKey, showDate = '', options = {}) {
  const encoded = encodeURIComponent(projectKey || 'daily_report_spring_festval_2026')
  const token = getAuthToken()
  const headers = {}
  const attempts = []
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  const search = new URLSearchParams({
    show_date: showDate || '',
    start_date: options.startDate || '',
    end_date: options.endDate || '',
  })
  const springUrl = `/api/v1/projects/${encoded}/spring-dashboard/temperature/trend?${search.toString()}`
  try {
    const response = await fetch(springUrl, {
      headers,
      signal: options.signal,
    })
    if (!response.ok) {
      const message = await response.text()
      throw new Error(message || `获取气温趋势失败: ${response.status}`)
    }
    const payload = await response.json()
    attempts.push({ layer: 'spring_light', ok: true, status: response.status, url: springUrl })
    return { ...(payload || {}), _debug: { source: 'spring_light', attempts } }
  } catch (err) {
    attempts.push({ layer: 'spring_light', ok: false, url: springUrl, error: String(err?.message || err) })
    try {
      // 回退1：使用 daily_report_25_26 的轻量温度接口（若后端已加载该接口）
      const payload = await getDashboardTemperatureTrend('daily_report_25_26', {
        showDate,
        startDate: options.startDate || '',
        endDate: options.endDate || '',
        signal: options.signal,
      })
      attempts.push({ layer: 'daily_light', ok: true, project: 'daily_report_25_26' })
      return { ...(payload || {}), _debug: { source: 'daily_light', attempts } }
    } catch (fallbackErr) {
      attempts.push({ layer: 'daily_light', ok: false, project: 'daily_report_25_26', error: String(fallbackErr?.message || fallbackErr) })
      // 回退2：最终兜底到历史稳定接口 /dashboard（无需新增后端路由）
      const payload = await getDashboardData('daily_report_25_26', { showDate, signal: options.signal })
      attempts.push({ layer: 'daily_dashboard_full', ok: true, project: 'daily_report_25_26' })
      return { ...(payload || {}), _debug: { source: 'daily_dashboard_full', attempts } }
    }
  }
}

export async function getLatestExtractedJson(projectKey) {
  const encoded = encodeURIComponent(projectKey || 'daily_report_spring_festval_2026')
  const token = getAuthToken()
  const headers = {}
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  const response = await fetch(`/api/v1/projects/${encoded}/spring-festival/latest-json`, { headers })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `读取最近提取数据失败: ${response.status}`)
  }
  return response.json()
}

export function setLatestExtractedPayload(payload) {
  latestExtractedPayload = payload || null
}

export function getLatestExtractedPayload() {
  return latestExtractedPayload
}
