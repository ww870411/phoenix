// 共享商务风格 Excel (.xlsx) 样式化渲染基座（供数据分析与联合评价导出共用）
import XLSX from 'xlsx-js-style'

export const FONT_NAME = 'Microsoft YaHei'

export const THIN_BORDER = {
  top: { style: 'thin', color: { rgb: 'CBD5E1' } },
  bottom: { style: 'thin', color: { rgb: 'CBD5E1' } },
  left: { style: 'thin', color: { rgb: 'CBD5E1' } },
  right: { style: 'thin', color: { rgb: 'CBD5E1' } },
}

export const SOFT_BORDER = {
  top: { style: 'thin', color: { rgb: 'E2E8F0' } },
  bottom: { style: 'thin', color: { rgb: 'E2E8F0' } },
  left: { style: 'thin', color: { rgb: 'E2E8F0' } },
  right: { style: 'thin', color: { rgb: 'E2E8F0' } },
}

export const TOTAL_BORDER = {
  top: { style: 'medium', color: { rgb: '64748B' } },
  bottom: { style: 'double', color: { rgb: '0F172A' } },
  left: { style: 'thin', color: { rgb: 'CBD5E1' } },
  right: { style: 'thin', color: { rgb: 'CBD5E1' } },
}

export const BANNER_BORDER = {
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
 * 为多个工作表分配唯一且合法的工作表名称。
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
export function toRoundedNumber(value, decimals = 2) {
  if (value === null || value === undefined || value === '' || value === '—') return null
  const num = Number(value)
  if (!Number.isFinite(num)) return null
  const safeDecimals = Number.isInteger(decimals) && decimals >= 0 ? Math.min(decimals, 6) : 2
  return Number(num.toFixed(safeDecimals))
}

/**
 * 根据小数位数生成 Excel 千分位数字格式字符串。
 */
export function buildNumFmt(decimals = 2, signed = false) {
  const safeDecimals = Number.isInteger(decimals) && decimals >= 0 ? Math.min(decimals, 6) : 2
  const base = safeDecimals === 0 ? '#,##0' : `#,##0.${'0'.repeat(safeDecimals)}`
  return signed ? `+${base};-${base};${safeDecimals === 0 ? '0' : `0.${'0'.repeat(safeDecimals)}`}` : base
}

/**
 * 计算文本在 Excel 中的视觉宽度（中文字符按 2 个半角宽度计算）。
 */
export function calcDisplayWidth(text) {
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
export function makeCell(value, options = {}) {
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
export function makeNumberCell(rawValue, decimals = 2, options = {}) {
  const num = toRoundedNumber(rawValue, decimals)
  if (num === null) {
    return makeCell('—', { align: 'center', color: '94A3B8', bold: false, bg: options.bg || null })
  }
  return makeCell(num, {
    align: options.align || 'right',
    bold: options.bold !== undefined ? options.bold : true,
    color: options.color || '0F172A',
    bg: options.bg || null,
    numFmt: options.numFmt || buildNumFmt(decimals, Boolean(options.signed)),
  })
}

/**
 * 构造同比 / 环比 / 偏差率涨跌幅单元格（正数警示红、负数稳健绿、缺失中性灰）。
 */
export function makeRateCell(rateValue, formattedText, options = {}) {
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
    bg: options.bg || null,
  })
}

/**
 * 构造月度计划状态徽章单元格（按超出/达成/落后语义着色）。
 */
export function makePlanStatusCell(statusText) {
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
export function renderStyledRowsToSheet(rowSpecs, totalCols, options = {}) {
  const minCols = options.minCols ?? 5
  const colCount = Math.max(minCols, totalCols)
  const aoa = rowSpecs.map((spec) => {
    const cells = spec.cells || []
    return Array.from({ length: colCount }, (_, idx) => {
      const item = cells[idx]
      if (item && typeof item === 'object' && 'value' in item) return item.value
      return item ?? ''
    })
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

      const isMergedCell =
        spec.mergeFullRow ||
        (Array.isArray(spec.merges) && spec.merges.some((m) => c >= m.startCol && c <= m.endCol))
      if (!isMergedCell && rowType !== 'blank') {
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
          fill: { fgColor: { rgb: cellSpec.bg || 'F1F5F9' } },
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
          alignment: { horizontal: isKeyCol ? 'center' : 'left', vertical: 'center', wrapText: true },
          border: SOFT_BORDER,
        }
      } else {
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
    wch: Math.max(idx === 0 ? (options.firstColMinWidth ?? 18) : (options.otherColMinWidth ?? 12), Math.min(44, w)),
  }))

  return ws
}

/**
 * 向行规格队列追加一个标准数据板块（板块标题条 + 表头行 + 多行数据/总计行）。
 */
export function appendSectionTable(rowSpecs, title, headers, dataRows, options = {}) {
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
