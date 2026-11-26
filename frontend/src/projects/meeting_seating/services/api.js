/**
 * 会议排座助手（meeting_seating）前端 API 客户端
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

const PROJECT_BASE = `${API_BASE}/projects/meeting_seating`

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
      // ignore parse errors
    }
    throw new Error(message)
  }
  return response.json()
}

export function fetchSeatingProfiles() {
  return requestJson('/profiles', { method: 'GET' })
}

export function fetchSeatingProfile(profileId) {
  return requestJson(`/profiles/${encodeURIComponent(profileId)}`, { method: 'GET' })
}

export function createSeatingProfile(payload) {
  return requestJson('/profiles', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateSeatingProfile(profileId, payload) {
  return requestJson(`/profiles/${encodeURIComponent(profileId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function renameSeatingProfile(profileId, name) {
  return requestJson(`/profiles/${encodeURIComponent(profileId)}/rename`, {
    method: 'PATCH',
    body: JSON.stringify({ name }),
  })
}

export function activateSeatingProfile(profileId) {
  return requestJson(`/profiles/${encodeURIComponent(profileId)}/activate`, {
    method: 'POST',
  })
}

export function deleteSeatingProfile(profileId) {
  return requestJson(`/profiles/${encodeURIComponent(profileId)}`, {
    method: 'DELETE',
  })
}
