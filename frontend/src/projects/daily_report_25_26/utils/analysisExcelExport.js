// 数据查询与分析页面 Excel (.xlsx) 样式化导出工具（参照保温管物流链平台专业商务表格样式）
import XLSX from 'xlsx-js-style'
import { comparisonLabels } from '../composables/analysisPresentation.js'

const FONT_NAME = 'Microsoft YaHei'

const THIN_BORDER = {
  top: { style: 'thin', color: { rgb: 'CBD5E1' } },
  bottom: { style: 'thin', color: { rgb: 'CBD5E1' } },
  left: { style: 'thin', color: { rgb: 'CBD5E1' } },
  right: { style: 'thin', color: { rgb: 'CBD5E1' } },
}

const SOFT_BORDER = {
  top: { style: 'thin', color: { rgb: 'E2E8F0' } },
  bottom: { style: 'thin', color: { rgb: 'E2E8F0' } },
  left: { style: 'thin', color: { rgb: 'E2E8F0' } },
  right: { style: 'thin', color: { rgb: 'E2E8F0' } },
}

const TOTAL_BORDER = {
  top: { style: 'medium', color: { rgb: '64748B' } },
  bottom: { style: 'double', color: { rgb: '0F172A' } },
  left: { style: 'thin', color: { rgb: 'CBD5E1' } },
  right: { style: 'thin', color: { rgb: 'CBD5E1' } },
}

const BANNER_BORDER = {
  top: { style: 'thin', color: { rgb: 'CBD5E1' } },
  bottom: { style: 'medium', color: { rgb: '2563EB' } },
  left: { style: 'thin', color: { rgb: 'CBD5E1' } },
  right: { style: 'thin', color: { rgb: 'CBD5E1' } },
}

/**
 * 清洗工作表名称，剔除 Excel 非法字符并截断至 31 个字符以内。
 */
export function sanitizeSheetName(name) {
  if (!name) return 'Sheet'
  return String(name).replace(/[\\/?*[\]:]/g, '_').slice(0, 31) || 'Sheet'
}

/**
 * 为多个单位分配唯一且合法的工作表名称。
 */
export function resolveSheetName(baseName, usedNames) {
  const sanitized = sanitizeSheetName(baseName)
  if (!usedNames.has(sanitized)) {
    usedNames.add(sanitized)
    return sanitized
  }
  let counter = 2
  while (true) {
    const suffix = `_${counter}`
    const candidate = `${sanitized.slice(0, 31 - suffix.length)}${suffix}`
    if (!usedNames.has(candidate)) {
      usedNames.add(candidate)
      return candidate
    }
    counter += 1
  }
}

/**
 * 格式化导出的数值，保留指定小数位数；空值返回 null 以便填充占位符。
 */
function toRoundedNumber(value, decimals = 2) {
  if (value === null || value === undefined || value === '' || value === '—') return null
  const num = Number(value)
  if (!Number.isFinite(num)) return null
  const safeDecimals = Number.isInteger(decimals) && decimals >= 0 ? Math.min(decimals, 6) : 2
  return Number(num.toFixed(safeDecimals))
}

/**
 * 根据小数位数生成 Excel 千分位数字格式字符串。
 */
function buildNumFmt(decimals = 2) {
  const safeDecimals = Number.isInteger(decimals) && decimals >= 0 ? Math.min(decimals, 6) : 2
  if (safeDecimals === 0) return '#,##0'
  return `#,##0.${'0'.repeat(safeDecimals)}`
}

/**
 * 计算文本在 Excel 中的视觉宽度（中文字符按 2 个半角宽度计算）。
 */
function calcDisplayWidth(text) {
  const str = String(text ?? '')
  let width = 0
  for (const ch of str) {
    width += ch.charCodeAt(0) > 255 ? 2 : 1.05
  }
  return width
}

/**
 * 构造普通单元格规格对象。
 */
function makeCell(value, options = {}) {
  return {
    value: value === undefined || value === null ? '' : value,
    align: options.align || 'left',
    bold: Boolean(options.bold),
    color: options.color || '1E293B',
    bg: options.bg || null,
    numFmt: options.numFmt || null,
    fontSize: options.fontSize || 10,
  }
}

/**
 * 构造数值单元格（保留原生 number 类型与千分位小数格式）。
 */
function makeNumberCell(rawValue, decimals = 2, options = {}) {
  const num = toRoundedNumber(rawValue, decimals)
  if (num === null) {
    return makeCell('—', { align: 'center', color: '94A3B8', bold: false })
  }
  return makeCell(num, {
    align: 'right',
    bold: options.bold !== undefined ? options.bold : true,
    color: options.color || '0F172A',
    numFmt: buildNumFmt(decimals),
  })
}

/**
 * 构造同比 / 环比涨跌幅单元格（正数警示红、负数稳健绿、缺失中性灰）。
 */
function makeRateCell(rateValue, formattedText, options = {}) {
  const num = rateValue === null || rateValue === undefined ? null : Number(rateValue)
  const validNum = num !== null && Number.isFinite(num)
  const text = formattedText || (validNum ? `${num.toFixed(2)}%` : '—')
  if (!validNum || text === '—') {
    return makeCell('—', { align: 'center', color: '94A3B8', bold: false })
  }
  const color = num >= 0 ? 'DC2626' : '15803D'
  return makeCell(text, {
    align: 'center',
    bold: true,
    color: options.color || color,
  })
}

/**
 * 构造月度计划状态徽章单元格（按超出/达成/落后语义着色）。
 */
function makePlanStatusCell(statusText) {
  const text = String(statusText || '无数据')
  if (text.includes('超出')) {
    return makeCell(text, { align: 'center', bold: true, color: '15803D', bg: 'DCFCE7' })
  }
  if (text.includes('达成')) {
    return makeCell(text, { align: 'center', bold: true, color: '1D4ED8', bg: 'DBEAFE' })
  }
  if (text.includes('落后')) {
    return makeCell(text, { align: 'center', bold: true, color: 'B91C1C', bg: 'FEE2E2' })
  }
  return makeCell(text, { align: 'center', bold: false, color: '64748B', bg: 'F1F5F9' })
}

/**
 * 将结构化行列表转换为带样式、合并区域、自适应列宽与行高的 xlsx-js-style Worksheet。
 */
function renderStyledRowsToSheet(rowSpecs, totalCols) {
  const colCount = Math.max(5, totalCols)
  const aoa = rowSpecs.map((spec) => {
    const cells = spec.cells || []
    const row = Array.from({ length: colCount }, (_, idx) => {
      const item = cells[idx]
      if (item && typeof item === 'object' && 'value' in item) return item.value
      return item ?? ''
    })
    return row
  })

  const ws = XLSX.utils.aoa_to_sheet(aoa)
  const merges = []
  const rowHeights = []
  const colMaxWidths = Array(colCount).fill(10)

  rowSpecs.forEach((spec, r) => {
    if (spec.height) {
      rowHeights[r] = { hpx: spec.height }
    }
    if (spec.mergeFullRow) {
      merges.push({ s: { r, c: 0 }, e: { r, c: colCount - 1 } })
    } else if (Array.isArray(spec.merges)) {
      spec.merges.forEach((m) => merges.push({ s: { r, c: m.startCol }, e: { r, c: m.endCol } }))
    }

    const rowType = spec.type || 'data'
    const isZebra = rowType === 'data' && spec.zebraIndex % 2 === 1

    for (let c = 0; c < colCount; c += 1) {
      const ref = XLSX.utils.encode_cell({ r, c })
      if (!ws[ref]) ws[ref] = { v: '', t: 's' }
      const rawCellSpec = (spec.cells && spec.cells[c]) || null
      const cellSpec =
        rawCellSpec && typeof rawCellSpec === 'object' && 'value' in rawCellSpec
          ? rawCellSpec
          : makeCell(rawCellSpec ?? '')

      // 跳过横幅及板块标题合并行，避免长标题将第 0 列撑得过宽
      if (!spec.mergeFullRow && rowType !== 'blank') {
        const displayStr =
          typeof cellSpec.value === 'number' && cellSpec.numFmt
            ? `${cellSpec.value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`
            : String(cellSpec.value ?? '')
        const pad = rowType === 'header' ? 5 : 4
        const factor = rowType === 'header' ? 1.12 : 1.04
        const w = Math.ceil(calcDisplayWidth(displayStr) * factor) + pad
        if (w > colMaxWidths[c]) colMaxWidths[c] = w
      }

      if (rowType === 'blank') {
        ws[ref].s = {
          font: { name: FONT_NAME, sz: 9 },
          fill: { fgColor: { rgb: 'FFFFFF' } },
        }
        continue
      }

      if (rowType === 'banner') {
        ws[ref].s = {
          font: { name: FONT_NAME, sz: 14, bold: true, color: { rgb: '0F172A' } },
          fill: { fgColor: { rgb: 'EFF6FF' } },
          alignment: { horizontal: 'center', vertical: 'center' },
          border: BANNER_BORDER,
        }
      } else if (rowType === 'subtitle') {
        ws[ref].s = {
          font: { name: FONT_NAME, sz: 9.5, color: { rgb: '475569' } },
          fill: { fgColor: { rgb: 'F8FAFC' } },
          alignment: { horizontal: 'center', vertical: 'center' },
          border: SOFT_BORDER,
        }
      } else if (rowType === 'section') {
        ws[ref].s = {
          font: { name: FONT_NAME, sz: 10.5, bold: true, color: { rgb: '1E3A8A' } },
          fill: { fgColor: { rgb: 'DBEAFE' } },
          alignment: { horizontal: 'left', vertical: 'center' },
          border: {
            top: { style: 'thin', color: { rgb: '93C5FD' } },
            bottom: { style: 'thin', color: { rgb: '60A5FA' } },
            left: { style: 'medium', color: { rgb: '2563EB' } },
            right: { style: 'thin', color: { rgb: '93C5FD' } },
          },
        }
      } else if (rowType === 'header') {
        ws[ref].s = {
          font: { name: FONT_NAME, sz: 10, bold: true, color: { rgb: 'FFFFFF' } },
          fill: { fgColor: { rgb: '1E293B' } },
          alignment: { horizontal: 'center', vertical: 'center', wrapText: true },
          border: THIN_BORDER,
        }
      } else if (rowType === 'note') {
        ws[ref].s = {
          font: { name: FONT_NAME, sz: 9.5, color: { rgb: '92400E' } },
          fill: { fgColor: { rgb: 'FFFBEB' } },
          alignment: { horizontal: 'left', vertical: 'center', wrapText: true },
          border: SOFT_BORDER,
        }
      } else if (rowType === 'total') {
        ws[ref].s = {
          font: {
            name: FONT_NAME,
            sz: 10,
            bold: true,
            color: { rgb: cellSpec.color || '0F172A' },
          },
          fill: { fgColor: { rgb: 'F1F5F9' } },
          alignment: { horizontal: cellSpec.align || (c === 0 ? 'center' : 'right'), vertical: 'center' },
          border: TOTAL_BORDER,
        }
        if (cellSpec.numFmt && typeof ws[ref].v === 'number') {
          ws[ref].z = cellSpec.numFmt
          ws[ref].s.numFmt = cellSpec.numFmt
        }
      } else if (rowType === 'meta') {
        const isKeyCol = c === 0
        ws[ref].s = {
          font: {
            name: FONT_NAME,
            sz: 9.5,
            bold: isKeyCol,
            color: { rgb: isKeyCol ? '334155' : '0F172A' },
          },
          fill: { fgColor: { rgb: isKeyCol ? 'F1F5F9' : 'FFFFFF' } },
          alignment: { horizontal: isKeyCol ? 'center' : 'left', vertical: 'center' },
          border: SOFT_BORDER,
        }
      } else {
        // 标准数据行（data）
        const bgRgb = cellSpec.bg || (isZebra ? 'F8FAFC' : 'FFFFFF')
        ws[ref].s = {
          font: {
            name: FONT_NAME,
            sz: cellSpec.fontSize || 10,
            bold: cellSpec.bold,
            color: { rgb: cellSpec.color || '1E293B' },
          },
          fill: { fgColor: { rgb: bgRgb } },
          alignment: { horizontal: cellSpec.align || 'left', vertical: 'center', wrapText: true },
          border: SOFT_BORDER,
        }
        if (cellSpec.numFmt && typeof ws[ref].v === 'number') {
          ws[ref].z = cellSpec.numFmt
          ws[ref].s.numFmt = cellSpec.numFmt
        }
      }
    }
  })

  if (merges.length) {
    ws['!merges'] = merges
  }
  ws['!rows'] = rowHeights
  ws['!cols'] = colMaxWidths.map((w, idx) => ({
    wch: Math.max(idx === 0 ? 18 : 12, Math.min(44, w)),
  }))

  return ws
}

/**
 * 向行规格队列追加一个标准数据板块（板块标题条 + 表头行 + 多行数据/总计行）。
 */
function appendSectionTable(rowSpecs, title, headers, dataRows, options = {}) {
  rowSpecs.push({
    type: 'section',
    height: 24,
    mergeFullRow: true,
    cells: [makeCell(title)],
  })
  rowSpecs.push({
    type: 'header',
    height: options.headerHeight || 26,
    cells: headers.map((h) => makeCell(h, { align: 'center', bold: true })),
  })
  dataRows.forEach((rowInfo, idx) => {
    const isTotal = Boolean(rowInfo?.isTotal)
    const cells = Array.isArray(rowInfo) ? rowInfo : rowInfo.cells
    rowSpecs.push({
      type: isTotal ? 'total' : 'data',
      zebraIndex: idx,
      height: isTotal ? 24 : 21,
      cells,
    })
  })
}

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
