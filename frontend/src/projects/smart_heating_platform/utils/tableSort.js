// -*- coding: utf-8 -*-
/**
 * 智慧供热旁路精算与质检平台 —— 统一表格表头点击排序工具
 */

import { computed, reactive } from 'vue'

/**
 * 通用值比较器：
 * - 空值（null / undefined / '' / NaN）始终排在末尾；
 * - 数值与数字串优先按数值大小比较；
 * - 其余按中英文自然序比较（支持 #1 / #2 / #10 数字混排）。
 */
export function compareSortValues(a, b, dir = 'desc') {
  const isEmpty = (v) => v === null || v === undefined || v === '' || (typeof v === 'number' && Number.isNaN(v))
  const emptyA = isEmpty(a)
  const emptyB = isEmpty(b)
  if (emptyA && emptyB) return 0
  if (emptyA) return 1
  if (emptyB) return -1

  const factor = dir === 'asc' ? 1 : -1

  if (typeof a === 'boolean' && typeof b === 'boolean') {
    if (a === b) return 0
    return (a ? 1 : 0) > (b ? 1 : 0) ? factor : -factor
  }

  const numA = typeof a === 'number' ? a : (typeof a === 'string' && /^-?\d+(\.\d+)?$/.test(a.trim()) ? Number(a) : Number.NaN)
  const numB = typeof b === 'number' ? b : (typeof b === 'string' && /^-?\d+(\.\d+)?$/.test(b.trim()) ? Number(b) : Number.NaN)
  if (!Number.isNaN(numA) && !Number.isNaN(numB)) {
    if (numA === numB) return 0
    return numA > numB ? factor : -factor
  }

  const cmp = String(a).localeCompare(String(b), 'zh-CN', { numeric: true, sensitivity: 'base' })
  return cmp * factor
}

/**
 * 为任意响应式列表创建可点击表头排序控制器。
 * 三态切换：首次点击降序 ('desc') -> 再次点击升序 ('asc') -> 第三次点击恢复默认序 ('')。
 */
export function useTableSort(rowsSource, getters = {}, defaultKey = '', defaultDir = '') {
  const state = reactive({
    key: defaultKey,
    dir: defaultDir,
  })

  function toggle(key) {
    if (!key) return
    if (state.key !== key) {
      state.key = key
      state.dir = 'desc'
      return
    }
    if (state.dir === 'desc') {
      state.dir = 'asc'
    } else if (state.dir === 'asc') {
      state.key = ''
      state.dir = ''
    } else {
      state.dir = 'desc'
    }
  }

  function reset() {
    state.key = defaultKey
    state.dir = defaultDir
  }

  const sortedRows = computed(() => {
    const raw = typeof rowsSource === 'function' ? rowsSource() : rowsSource?.value
    const list = Array.isArray(raw) ? raw : []
    if (!state.key || !state.dir) return list
    const getter = getters[state.key] || ((row) => row?.[state.key])
    return [...list].sort((a, b) => compareSortValues(getter(a), getter(b), state.dir))
  })

  return {
    state,
    toggle,
    reset,
    sortedRows,
  }
}
