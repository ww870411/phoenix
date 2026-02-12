import {
  extractSpringFestivalJson as extractByDateJson,
  getAuthToken,
  getDashboardData,
} from '../../daily_report_25_26/services/api'

let latestExtractedPayload = null

export async function extractSpringFestivalJson(projectKey, file, options = {}) {
  return extractByDateJson(projectKey, file, options)
}

export async function getTemperatureTrendByDate(showDate = '') {
  return getDashboardData('daily_report_25_26', { showDate })
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
