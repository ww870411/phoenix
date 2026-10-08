// -*- coding: utf-8 -*-
/**
 * 前端系统消息中心 API 客户端 (System Message & Inbox Client)
 */

import { useAuthStore } from '../../daily_report_25_26/store/auth'

const rawBase =
  typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE
    ? import.meta.env.VITE_API_BASE
    : ''

const API_BASE = (() => {
  const base = rawBase ? String(rawBase).replace(/\/$/, '') : ''
  if (!base) return '/api/v1'
  return /(\/api)(\/|$)/.test(base) ? base : `${base}/api/v1`
})()

const PROJECT_KEY = 'insulation_pipe_supply_2026'

function getHeaders() {
  const auth = useAuthStore()
  const token = auth.token || (typeof localStorage !== 'undefined' ? localStorage.getItem('phoenix_auth_token') : '')
  const headers = {
    'Content-Type': 'application/json',
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

async function handleResponse(res) {
  if (!res.ok) {
    let errDetail = '网络请求失败'
    try {
      const errJson = await res.json()
      errDetail = errJson.detail || errJson.message || errDetail
    } catch (e) {
      errDetail = `${res.status} ${res.statusText}`
    }
    throw new Error(errDetail)
  }
  return await res.json()
}

/**
 * 获取当前登录用户的收件箱消息列表
 */
export async function getMyInboxMessages(params = {}) {
  const query = new URLSearchParams()
  if (params.page) query.set('page', String(params.page))
  if (params.page_size) query.set('page_size', String(params.page_size))
  if (params.unread_only) query.set('unread_only', 'true')
  if (params.msg_type) query.set('msg_type', params.msg_type)

  const url = `${API_BASE}/projects/${PROJECT_KEY}/system-messages/my?${query.toString()}`
  const res = await fetch(url, {
    method: 'GET',
    headers: getHeaders(),
  })
  return handleResponse(res)
}

/**
 * 获取当前用户的未读消息数
 */
export async function getMyUnreadCount() {
  const url = `${API_BASE}/projects/${PROJECT_KEY}/system-messages/unread-count`
  const res = await fetch(url, {
    method: 'GET',
    headers: getHeaders(),
  })
  return handleResponse(res)
}

/**
 * 标记单条消息为已读
 */
export async function markMessageRead(messageId) {
  const url = `${API_BASE}/projects/${PROJECT_KEY}/system-messages/${messageId}/read`
  const res = await fetch(url, {
    method: 'POST',
    headers: getHeaders(),
  })
  return handleResponse(res)
}

/**
 * 一键将所有消息标记为已读
 */
export async function markAllMessagesRead() {
  const url = `${API_BASE}/projects/${PROJECT_KEY}/system-messages/read-all`
  const res = await fetch(url, {
    method: 'POST',
    headers: getHeaders(),
  })
  return handleResponse(res)
}

/**
 * 发送站内私信 (预留未来联络功能)
 */
export async function sendDirectMessage(payload) {
  const url = `${API_BASE}/projects/${PROJECT_KEY}/system-messages/send-direct`
  const res = await fetch(url, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(payload),
  })
  return handleResponse(res)
}

/**
 * 发送系统广播 (预留管理员功能)
 */
export async function sendBroadcastMessage(payload) {
  const url = `${API_BASE}/projects/${PROJECT_KEY}/system-messages/broadcast`
  const res = await fetch(url, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(payload),
  })
  return handleResponse(res)
}
