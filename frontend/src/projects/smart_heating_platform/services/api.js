// -*- coding: utf-8 -*-
/**
 * 智慧供热旁路精算与质检平台（smart_heating_platform）前端 API 客户端
 */

import { useAuthStore } from '../../daily_report_25_26/store/auth'
import { getAuthToken } from '../../daily_report_25_26/services/api'

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

const PROJECT_BASE = `${API_BASE}/projects/smart_heating_platform`

function buildHeaders(json = true) {
  const auth = useAuthStore()
  const token = auth.token || getAuthToken()
  const headers = {}
  if (json) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

async function requestJson(path, options = {}) {
  const response = await globalThis.fetch(`${PROJECT_BASE}${path}`, {
    ...options,
    headers: {
      ...buildHeaders(true),
      ...(options.headers || {}),
    },
  })
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`
    try {
      const data = await response.json()
      message = data?.detail || data?.message || message
    } catch {
      // ignore
    }
    throw new Error(message)
  }
  return response.json()
}

export async function downloadPlatformExcel(path, fallbackName) {
  const response = await globalThis.fetch(`${PROJECT_BASE}${path}`, {
    method: 'GET',
    headers: buildHeaders(false),
  })
  if (!response.ok) {
    throw new Error(`导出失败 (${response.status})`)
  }
  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fallbackName
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

function toQuery(params = {}) {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') {
      qs.set(k, String(v))
    }
  })
  const text = qs.toString()
  return text ? `?${text}` : ''
}

// 1. 采集配置与 Cookie 设置
export function fetchCollectorSettings() {
  return requestJson('/settings/collector', { method: 'GET' })
}
export function saveCollectorSettings(payload) {
  return requestJson('/settings/collector', { method: 'PUT', body: JSON.stringify(payload) })
}
export function testCollectorSettings(payload = {}) {
  return requestJson('/settings/collector/test', { method: 'POST', body: JSON.stringify(payload) })
}

// 2. 阳面逐小时运行报告 & 每日精算日报
export function fetchHourlyReport(params = {}, options = {}) {
  return requestJson(`/reports/hourly${toQuery(params)}`, { method: 'GET', ...options })
}
export function fetchEntityTrend24h(params = {}, options = {}) {
  return requestJson(`/reports/hourly/entity-trend${toQuery(params)}`, { method: 'GET', ...options })
}
export function fetchUpstreamTrend24h(params = {}, options = {}) {
  return requestJson(`/reports/hourly/upstream-trend${toQuery(params)}`, { method: 'GET', ...options })
}
export function fetchStationTempDevices(params = {}, options = {}) {
  return requestJson(`/reports/hourly/station-temps${toQuery(params)}`, { method: 'GET', ...options })
}
export function fetchDailyReport(params = {}, options = {}) {
  return requestJson(`/reports/daily${toQuery(params)}`, { method: 'GET', ...options })
}
export function triggerManualCollect(payload = {}) {
  return requestJson('/reports/collect-now', { method: 'POST', body: JSON.stringify(payload) })
}
export function triggerHeatAuditFix(payload = {}) {
  return requestJson('/reports/collect-now', {
    method: 'POST',
    body: JSON.stringify({ action: 'heat_audit_fix', ...payload }),
  })
}
export function fetchCollectorRuns(limit = 20) {
  return requestJson(`/reports/runs${toQuery({ limit })}`, { method: 'GET' })
}
export function fetchGapStatus(params = {}) {
  return requestJson(`/reports/gap-status${toQuery(params)}`, { method: 'GET' })
}

// 3. 阴面异常督办中心
export function fetchFaultSummary(params = {}, options = {}) {
  return requestJson(`/faults/summary${toQuery(params)}`, { method: 'GET', ...options })
}
export function fetchFaultTickets(params = {}, options = {}) {
  return requestJson(`/faults/tickets${toQuery(params)}`, { method: 'GET', ...options })
}
export function updateFaultTicketStatus(ticketId, payload) {
  return requestJson(`/faults/tickets/${encodeURIComponent(ticketId)}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

// 4. 标准台账中心
export function fetchDictOverview() {
  return requestJson('/dicts/overview', { method: 'GET' })
}
export function fetchDictItems(entity, params = {}) {
  return requestJson(`/dicts/items/${encodeURIComponent(entity)}${toQuery(params)}`, { method: 'GET' })
}
export function patchStationDict(stationId, payload) {
  return requestJson(`/dicts/stations/${encodeURIComponent(stationId)}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}
export function patchMerchantDict(merchantId, payload) {
  return requestJson(`/dicts/merchants/${encodeURIComponent(merchantId)}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}
