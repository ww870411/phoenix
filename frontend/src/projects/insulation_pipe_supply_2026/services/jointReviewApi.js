// -*- coding: utf-8 -*-
/**
 * 联合会审大厅前端 API 客户端 (Joint Review API Client)
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
 * 分页查询联合会审列表
 */
export async function listJointReviews(params = {}) {
  const query = new URLSearchParams()
  if (params.tab) query.set('tab', params.tab)
  if (params.order_category) query.set('order_category', params.order_category)
  if (params.section_1_id) query.set('section_1_id', params.section_1_id)
  if (params.supply_entity_id) query.set('supply_entity_id', params.supply_entity_id)
  if (params.review_status) query.set('review_status', params.review_status)
  if (params.search) query.set('search', params.search)
  if (params.page) query.set('page', String(params.page))
  if (params.limit) query.set('limit', String(params.limit))

  const url = `${API_BASE}/projects/insulation_pipe_supply_2026/joint-reviews/list?${query.toString()}`
  const res = await fetch(url, {
    method: 'GET',
    headers: getHeaders(),
  })
  return handleResponse(res)
}

/**
 * 获取单笔联合会审完整详情
 */
export async function getJointReviewDetail(reviewId) {
  const url = `${API_BASE}/projects/insulation_pipe_supply_2026/joint-reviews/${reviewId}`
  const res = await fetch(url, {
    method: 'GET',
    headers: getHeaders(),
  })
  return handleResponse(res)
}

/**
 * 提请联合会审
 */
export async function createJointReview(payload) {
  const url = `${API_BASE}/projects/insulation_pipe_supply_2026/joint-reviews/create`
  const res = await fetch(url, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(payload),
  })
  return handleResponse(res)
}

/**
 * 签署会审表决意见（同意 / 不同意）
 */
export async function voteJointReview(reviewId, payload) {
  const url = `${API_BASE}/projects/insulation_pipe_supply_2026/joint-reviews/${reviewId}/vote`
  const res = await fetch(url, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(payload),
  })
  return handleResponse(res)
}

/**
 * 发起人撤回会审
 */
export async function cancelJointReview(reviewId, payload) {
  const url = `${API_BASE}/projects/insulation_pipe_supply_2026/joint-reviews/${reviewId}/cancel`
  const res = await fetch(url, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(payload),
  })
  return handleResponse(res)
}

/**
 * 超级管理员终局裁决仲裁
 */
export async function adminArbitrateJointReview(reviewId, payload) {
  const url = `${API_BASE}/projects/insulation_pipe_supply_2026/joint-reviews/${reviewId}/admin-arbitrate`
  const res = await fetch(url, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(payload),
  })
  return handleResponse(res)
}

/**
 * 轻量获取当前登录主体待办会审通知数与概要
 */
export async function getPendingReviewNotifications() {
  const url = `${API_BASE}/projects/insulation_pipe_supply_2026/joint-reviews/notifications`
  const res = await fetch(url, {
    method: 'GET',
    headers: getHeaders(),
  })
  return handleResponse(res)
}
