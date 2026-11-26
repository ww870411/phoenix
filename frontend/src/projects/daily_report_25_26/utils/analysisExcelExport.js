// 数据查询与分析页面 Excel (.xlsx) 样式化导出工具（复用商务表格渲染基座）
import XLSX from 'xlsx-js-style'
import { comparisonLabels } from '../composables/analysisPresentation.js'
import {
  appendSectionTable,
  makeCell,
  makeNumberCell,
  makePlanStatusCell,
  makeRateCell,
  renderStyledRowsToSheet,
  resolveSheetName,
  sanitizeSheetName,
} from './styledExcelBase.js'

export { resolveSheetName, sanitizeSheetName }

/**
 * 为单个单位的查询结果构建样式化 Worksheet。
 */
export function buildStyledUnitWorksheet(result, context = {}) {
  const meta = result?.meta || {}
  const rows = Array.isArray(result?.rows) ? result.rows : []
  const analysisMode = context.analysisMode || meta.analysis_mode || 'daily'
  const pageName = context.pageDisplayName || '数据查询与分析'
  const unitName = meta.unit_label || context.unitLabel || context.unitKey || '单位'
  const modeLabel = meta.analysis_mode_label || (analysisMode === 'range' ? '累计数据' : '单日数据')
  const startDateStr = meta.start_date || context.startDate || ''
  const endDateStr = meta.end_date || context.endDate || startDateStr
  const dateRangeText =
    startDateStr && endDateStr && startDateStr !== endDateStr
      ? `${startDateStr} ~ ${endDateStr}`
      : startDateStr || '未指定日期'
  const labels = comparisonLabels(meta, analysisMode)
  const generatedAtText = context.generatedAt || new Date().toLocaleString()

  // 计算工作表所需最大列数（主对比表 5 列、计划表 6 列、区间明细动态列数）
  const timelineColumns = Array.isArray(result?.timeline?.columns) ? result.timeline.columns : []
  const timelineRows = Array.isArray(result?.timeline?.rows) ? result.timeline.rows : []
  const planEntries = Array.isArray(context.planEntries)
    ? context.planEntries
    : (typeof context.resolvePlanEntries === 'function' ? context.resolvePlanEntries(result) : [])
  const hasPlan = Array.isArray(planEntries) && planEntries.length > 0
  const maxCols = Math.max(5, hasPlan ? 6 : 5, timelineColumns.length || 0)

  const rowSpecs = []

  // 1. 顶部合并大标题与摘要信息栏
  rowSpecs.push({
    type: 'banner',
    height: 34,
    mergeFullRow: true,
    cells: [makeCell(`${unitName} · ${pageName}报表`)],
  })
  rowSpecs.push({
    type: 'subtitle',
    height: 22,
    mergeFullRow: true,
    cells: [
      makeCell(
        `分析模式：${modeLabel}   |   统计日期：${dateRangeText}   |   指标数：${rows.length} 项   |   导出时间：${generatedAtText}`,
      ),
    ],
  })
  rowSpecs.push({ type: 'blank', height: 8, cells: [] })

  // 2. 核心指标对比汇总表
  const resolveVal = (row, field) => {
    const totalKey = `total_${field}`
    if (analysisMode === 'range' && row[totalKey] !== undefined && row[totalKey] !== null) {
      return row[totalKey]
    }
    return row[field]
  }
  const computeRate = (currRaw, refRaw) => {
    const curr = Number(currRaw)
    const ref = Number(refRaw)
    if (!Number.isFinite(curr) || !Number.isFinite(ref) || Math.abs(ref) < 1e-9) return null
    return ((curr - ref) / Math.abs(ref)) * 100
  }

  const summaryRows = rows.map((row) => {
    const decimals = row.decimals ?? 2
    const currVal = resolveVal(row, 'current')
    const peerVal = resolveVal(row, 'peer')
    const deltaRate = computeRate(currVal, peerVal)
    return [
      makeCell(row.label || row.key || '', { align: 'left', bold: true, color: '0F172A' }),
      makeNumberCell(currVal, decimals),
      makeNumberCell(peerVal, decimals, { bold: false, color: '334155' }),
      makeRateCell(deltaRate),
      makeCell(row.unit || '—', { align: 'center', color: '475569' }),
    ]
  })
  appendSectionTable(
    rowSpecs,
    '📊 核心指标对比汇总',
    ['指标', labels.current, labels.peer, '同比', '计量单位'],
    summaryRows,
  )

  // 3. 环比比较（若存在）
  const prevTotals = result?.ringCompare?.prevTotals
  const ringRange = result?.ringCompare?.range
  if (prevTotals && ringRange) {
    rowSpecs.push({ type: 'blank', height: 10, cells: [] })
    const ringRows = rows.map((row) => {
      const decimals = row.decimals ?? 2
      const curr = context.resolveTotalCurrent ? context.resolveTotalCurrent(row) : resolveVal(row, 'current')
      const prev = prevTotals[row.key]
      const rate =
        Number.isFinite(prev) && prev !== 0 && Number.isFinite(curr)
          ? ((curr - prev) / prev) * 100
          : null
      return [
        makeCell(row.label || row.key || '', { align: 'left', bold: true, color: '0F172A' }),
        makeNumberCell(prev, decimals, { bold: false, color: '334155' }),
        makeNumberCell(curr, decimals),
        makeRateCell(rate),
        makeCell(row.unit || '—', { align: 'center', color: '475569' }),
      ]
    })
    appendSectionTable(
      rowSpecs,
      '🔄 环比比较',
      ['指标', labels.previous, labels.current, '环比', '计量单位'],
      ringRows,
    )
  } else if (result?.ringCompare?.note) {
    rowSpecs.push({ type: 'blank', height: 10, cells: [] })
    rowSpecs.push({
      type: 'section',
      height: 24,
      mergeFullRow: true,
      cells: [makeCell('🔄 环比比较')],
    })
    rowSpecs.push({
      type: 'note',
      height: 22,
      mergeFullRow: true,
      cells: [makeCell(`说明：${result.ringCompare.note}`)],
    })
  }

  // 4. 月度计划比较（若存在）
  if (hasPlan) {
    rowSpecs.push({ type: 'blank', height: 10, cells: [] })
    const monthSuffix = result?.planComparison?.month_label ? `（${result.planComparison.month_label}）` : ''
    const planRows = planEntries.map((entry) => {
      const decimals = entry.decimals ?? 2
      const rateText =
        entry.completionRate === null || entry.completionRate === undefined
          ? '—'
          : `${Number(entry.completionRate).toFixed(2)}%`
      const statusText = context.formatPlanStatus ? context.formatPlanStatus(entry.completionRate) : '无数据'
      return [
        makeCell(entry.label || '', { align: 'left', bold: true, color: '0F172A' }),
        makeNumberCell(entry.actualValue, decimals),
        makeNumberCell(entry.planValue, decimals, { bold: false, color: '334155' }),
        makeCell(rateText, { align: 'center', bold: true, color: '0F172A' }),
        makePlanStatusCell(statusText),
        makeCell(entry.unit || '—', { align: 'center', color: '475569' }),
      ]
    })
    appendSectionTable(
      rowSpecs,
      `🎯 月度计划对比${monthSuffix}`,
      ['指标', '截至本期末完成', '月度计划', '完成率', '状态', '计量单位'],
      planRows,
    )
  }

  // 5. 区间逐日明细（累计模式下存在多日明细时）
  if (timelineColumns.length && timelineRows.length) {
    rowSpecs.push({ type: 'blank', height: 10, cells: [] })
    const decimalsLookup = new Map()
    rows.forEach((r) => {
      if (r?.key) decimalsLookup.set(r.key, r.decimals ?? 2)
    })

    const timelineHeaders = timelineColumns.map((col) => col.name || col.prop)
    const formattedTimelineRows = timelineRows.map((record) => {
      const isTotal = String(record?.date || '').trim() === '总计'
      const cells = timelineColumns.map((col) => {
        const prop = String(col.prop || '')
        const raw = record[prop]
        if (prop === 'date') {
          return makeCell(raw || '—', {
            align: 'center',
            bold: isTotal,
            color: isTotal ? '0F172A' : '334155',
          })
        }
        if (prop.endsWith('__delta')) {
          const text = raw && typeof raw === 'object' ? raw.text : raw
          const deltaNum = raw && typeof raw === 'object' ? raw.delta : null
          return makeRateCell(deltaNum, text)
        }
        const metricKey = prop.replace(/__(current|peer)$/, '')
        const dec = decimalsLookup.get(metricKey) ?? 2
        const isCurrent = prop.endsWith('__current')
        return makeNumberCell(raw, dec, {
          bold: isTotal || isCurrent,
          color: isTotal ? '0F172A' : (isCurrent ? '0F172A' : '475569'),
        })
      })
      return { isTotal, cells }
    })

    appendSectionTable(
      rowSpecs,
      '📅 区间逐日明细',
      timelineHeaders,
      formattedTimelineRows,
      { headerHeight: 30 },
    )
  }

  // 6. 查询信息底栏
  rowSpecs.push({ type: 'blank', height: 10, cells: [] })
  rowSpecs.push({
    type: 'section',
    height: 24,
    mergeFullRow: true,
    cells: [makeCell('ℹ️ 查询信息与口径说明')],
  })
  const metaPairs = [
    ['所属页面', pageName],
    ['统计单位', unitName],
    ['分析模式', modeLabel],
    ['日期范围', dateRangeText],
    ['指标数量', `${rows.length} 项`],
    ['生成时间', generatedAtText],
  ]
  metaPairs.forEach(([k, v]) => {
    rowSpecs.push({
      type: 'meta',
      height: 20,
      merges: [{ startCol: 1, endCol: maxCols - 1 }],
      cells: [makeCell(k, { align: 'center', bold: true }), makeCell(v, { align: 'left' })],
    })
  })

  return renderStyledRowsToSheet(rowSpecs, maxCols)
}

/**
 * 构建包含多个单位工作表的完整 Excel Workbook。
 */
export function buildAnalysisExcelWorkbook(unitKeys, unitResults, options = {}) {
  const wb = XLSX.utils.book_new()
  const usedSheetNames = new Set()
  const generatedAt = options.generatedAt || new Date().toLocaleString()

  unitKeys.forEach((unitKey) => {
    const result = unitResults[unitKey]
    if (!result) return
    const unitLabel = result.meta?.unit_label || options.resolveUnitLabel?.(unitKey) || unitKey
    const planEntries = options.resolvePlanEntries ? options.resolvePlanEntries(result) : []
    const ws = buildStyledUnitWorksheet(result, {
      ...options,
      unitKey,
      unitLabel,
      planEntries,
      generatedAt,
    })
    const sheetName = resolveSheetName(unitLabel, usedSheetNames)
    XLSX.utils.book_append_sheet(wb, ws, sheetName)
  })

  return wb
}

/**
 * 触发浏览器下载样式化后的数据分析 Excel (.xlsx) 文件。
 */
export function exportAnalysisExcelFile(unitKeys, unitResults, options = {}) {
  if (!Array.isArray(unitKeys) || !unitKeys.length) return false
  const wb = buildAnalysisExcelWorkbook(unitKeys, unitResults, options)
  if (!wb.SheetNames.length) return false

  const modeLabel = options.analysisMode === 'range' ? '累计' : '单日'
  const start = options.startDate || ''
  const end = options.endDate || start
  const datePart = start && end && start !== end ? `${start}_至_${end}` : (start || new Date().toISOString().slice(0, 10))
  const filename = `数据分析_${modeLabel}_${datePart}.xlsx`
  XLSX.writeFile(wb, filename)
  return true
}
