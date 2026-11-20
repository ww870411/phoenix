// -*- coding: utf-8 -*-
/**
 * smart_heating_platform 本地日期工具（避免 UTC 时区转换导致差一天）
 */

export const MIN_PLATFORM_DATE = '2026-11-01'

export function todayLocalIso() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function shiftIsoDate(dateStr, deltaDays) {
  const base = /^\d{4}-\d{2}-\d{2}$/.test(String(dateStr || '')) ? String(dateStr) : todayLocalIso()
  const [y, m, d] = base.split('-').map(Number)
  const dt = new Date(y, m - 1, d + deltaDays)
  return `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`
}
