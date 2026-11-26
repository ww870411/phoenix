// 主城区供热联合评价模型 Excel (.xlsx) 样式化导出工具（复用商务表格渲染基座）
import XLSX from 'xlsx-js-style'
import {
  appendSectionTable,
  makeCell,
  makeNumberCell,
  makeRateCell,
  renderStyledRowsToSheet,
  resolveSheetName,
} from './styledExcelBase.js'

const MODE_LABELS = {
  single: '单日诊断',
  rolling: '周期滚动对比',
  range: '自定义时段',
}

function makeSignedPercentCell(rawValue, options = {}) {
  const num = rawValue === null || rawValue === undefined ? null : Number(rawValue)
  if (num === null || !Number.isFinite(num)) {
    return makeCell('—', { align: 'center', color: '94A3B8', bold: false })
  }
  const text = `${num > 0 ? '+' : ''}${num.toFixed(2)}%`
  return makeRateCell(num, text, options)
}

function makeComplaintIndexCell(rawValue, options = {}) {
  const num = rawValue === null || rawValue === undefined ? null : Number(rawValue)
  if (num === null || !Number.isFinite(num)) {
    return makeCell('—', { align: 'center', color: '94A3B8', bold: false })
  }
  return makeNumberCell(num, 1, {
    align: options.align || 'right',
    bold: true,
    color: num > 100 ? 'DC2626' : '15803D',
  })
}

function makeQuadrantCell(quadrant) {
  const code = String(quadrant?.code || '').trim()
  const name = String(quadrant?.name || '暂无定性')
  const palette = {
    I: { color: 'B91C1C', bg: 'FEE2E2' },
    II: { color: 'B45309', bg: 'FEF3C7' },
    III: { color: '15803D', bg: 'DCFCE7' },
    IV: { color: '1D4ED8', bg: 'DBEAFE' },
  }[code] || { color: '64748B', bg: 'F1F5F9' }
  return makeCell(name, { align: 'center', bold: true, color: palette.color, bg: palette.bg })
}

function makeBandStatusCell(bandStatus) {
  const status = String(bandStatus?.status || '')
  const label = String(bandStatus?.label || '—')
  if (status === 'within_band') {
    return makeCell(label, { align: 'center', bold: true, color: '15803D', bg: 'DCFCE7' })
  }
  if (status === 'above_p95') {
    return makeCell(label, { align: 'center', bold: true, color: 'B91C1C', bg: 'FEE2E2' })
  }
  if (status === 'below_p5') {
    return makeCell(label, { align: 'center', bold: true, color: '1D4ED8', bg: 'DBEAFE' })
  }
  return makeCell(label, { align: 'center', bold: false, color: '64748B', bg: 'F1F5F9' })
}

function makeCompletenessCell(row) {
  if (row?.is_complete) {
    return makeCell('完整', { align: 'center', bold: true, color: '15803D', bg: 'DCFCE7' })
  }
  const reasons = Array.isArray(row?.missing_reasons) && row.missing_reasons.length
    ? row.missing_reasons.join('；')
    : '缺数'
  return makeCell(reasons, { align: 'left', bold: true, color: 'B45309', bg: 'FEF3C7' })
}

function buildSubtitleText(payload, options = {}) {
  const mode = options.mode || payload?.mode || 'single'
  const modeLabel = MODE_LABELS[mode] || mode
  const anchor = payload?.anchor_date || payload?.default_biz_date || '—'
  const validDays = payload?.valid_day_count ?? payload?.summary?.valid_days ?? 0
  const area10k = payload?.area_source?.area_10k_m2
  const areaText = area10k != null ? `${Number(area10k).toFixed(2)} 万㎡` : '未维护'
  const generatedAt = options.generatedAt || new Date().toLocaleString()
  return `评价模式：${modeLabel}   |   基准锚点：${anchor}   |   有效测算：${validDays} 天   |   主城区收费面积：${areaText}   |   导出时间：${generatedAt}`
}

function buildSummaryKvRows(summary, payload) {
  const areaM2 = payload?.area_source?.area_m2
  const area10k = payload?.area_source?.area_10k_m2
  const hddToday = summary?.avg_hdd20_today != null ? Number(summary.avg_hdd20_today).toFixed(2) : '—'
  const hddPrev3 = summary?.avg_hdd20_prev3 != null ? Number(summary.avg_hdd20_prev3).toFixed(2) : '—'
  return [
    [
      makeCell('评价范围 / 有效天数', { align: 'left', bold: true, color: '0F172A' }),
      makeCell(summary?.label || '—', { align: 'left', bold: true }),
      makeNumberCell(summary?.valid_days, 0),
      makeCell('天', { align: 'center', color: '475569' }),
      makeCell('主城区收费面积（GongRe）', { align: 'left', bold: true, color: '0F172A' }),
      makeNumberCell(areaM2, 2),
      makeCell(area10k != null ? `㎡（${Number(area10k).toFixed(2)} 万㎡）` : '㎡', { align: 'center', color: '475569' }),
    ],
    [
      makeCell('平均气温与 HDD20 需求', { align: 'left', bold: true, color: '0F172A' }),
      makeCell(`当日 / 前3日 HDD20：${hddToday} / ${hddPrev3}`, { align: 'left', color: '334155' }),
      makeNumberCell(summary?.avg_temp, 2),
      makeCell('℃', { align: 'center', color: '475569' }),
      makeCell('实际 / 参考日均单耗', { align: 'left', bold: true, color: '0F172A' }),
      makeNumberCell(summary?.actual_unit_heat_avg, 2),
      makeCell(
        summary?.ref_unit_heat_avg != null ? `参考 ${Number(summary.ref_unit_heat_avg).toFixed(2)} GJ/万㎡·日` : 'GJ/万㎡·日',
        { align: 'center', color: '475569' },
      ),
    ],
    [
      makeCell('气象修正供热偏差率', { align: 'left', bold: true, color: '0F172A' }),
      makeSignedPercentCell(summary?.heat_deviation_pct),
      makeNumberCell(summary?.actual_heat_gj, 0),
      makeCell('实际总耗热(GJ)', { align: 'center', color: '475569' }),
      makeNumberCell(summary?.ref_heat_gj, 0, { bold: false, color: '334155' }),
      makeNumberCell(summary?.heat_delta_gj, 0, { signed: true }),
      makeBandStatusCell(summary?.band_status),
    ],
    [
      makeCell('用户投诉强度指数', { align: 'left', bold: true, color: '0F172A' }),
      makeComplaintIndexCell(summary?.complaint_index, { align: 'center' }),
      makeNumberCell(summary?.actual_complaints, 0),
      makeCell('实际投诉(件)', { align: 'center', color: '475569' }),
      makeNumberCell(summary?.ref_complaints, 1, { bold: false, color: '334155' }),
      makeNumberCell(summary?.complaint_delta, 1, { signed: true }),
      makeCell('基准线 = 100', { align: 'center', color: '475569' }),
    ],
    [
      makeCell('四象限联合诊断', { align: 'left', bold: true, color: '0F172A' }),
      makeQuadrantCell(summary?.quadrant),
      makeCell(summary?.quadrant?.diagnosis || '—', { align: 'left', bold: true, color: '0F172A' }),
      makeCell('管控建议', { align: 'center', bold: true, color: '334155' }),
      makeCell(summary?.quadrant?.action || '—', { align: 'left', color: '334155' }),
      makeCell('', { align: 'left' }),
      makeCell('', { align: 'left' }),
    ],
  ]
}

/**
 * 构建样式化的「联合评价诊断汇总」Worksheet。
 */
export function buildJointEvaluationSummarySheet(payload, options = {}) {
  const mode = options.mode || payload?.mode || 'single'
  const summary = payload?.summary || null
  const trajectorySummary = payload?.trajectory_summary || null
  const periods = Array.isArray(payload?.periods) ? payload.periods : []
  const maxCols = 7

  const rowSpecs = [
    {
      type: 'banner',
      height: 34,
      mergeFullRow: true,
      cells: [makeCell('主城区供热联合评价模型（测试）诊断报表')],
    },
    {
      type: 'subtitle',
      height: 22,
      mergeFullRow: true,
      cells: [makeCell(buildSubtitleText(payload, options))],
    },
    { type: 'blank', height: 8, cells: [] },
  ]

  const primaryTitle = mode === 'single'
    ? `📊 核心诊断结论（单日：${summary?.label || payload?.anchor_date || '—'}）`
    : `📊 核心诊断结论（区间聚合：${summary?.valid_days ?? 0} 个有效日）`
  appendSectionTable(
    rowSpecs,
    primaryTitle,
    ['诊断维度', '核心结论 / 指数', '关键实测值', '口径 / 单位', '对照基准 / 诊断项', '差额 / 测算值', '状态 / 经验带'],
    summary ? buildSummaryKvRows(summary, payload) : [],
  )
  // 将最后一行（四象限联合诊断）右侧 3 列合并用于完整展示管控建议
  const lastSummaryRowIdx = rowSpecs.length - 1
  if (summary && rowSpecs[lastSummaryRowIdx]) {
    rowSpecs[lastSummaryRowIdx].merges = [{ startCol: 4, endCol: 6 }]
    rowSpecs[lastSummaryRowIdx].height = 30
  }

  // 单日诊断附带多日轨迹时，增加轨迹累计对照表以明晰口径差异
  if (mode === 'single' && trajectorySummary && Number(trajectorySummary.valid_days || 0) > 1) {
    rowSpecs.push({ type: 'blank', height: 10, cells: [] })
    appendSectionTable(
      rowSpecs,
      `📈 附带轨迹累计对照（近 ${trajectorySummary.valid_days} 个有效日先累计后求比）`,
      ['轨迹口径', '有效天数', '实际总耗热(GJ)', '参考总耗热(GJ)', '供热偏差率', '投诉强度指数', '区间象限'],
      [[
        makeCell(trajectorySummary.label || '轨迹区间合计', { align: 'center', bold: true }),
        makeNumberCell(trajectorySummary.valid_days, 0),
        makeNumberCell(trajectorySummary.actual_heat_gj, 0),
        makeNumberCell(trajectorySummary.ref_heat_gj, 0, { bold: false, color: '334155' }),
        makeSignedPercentCell(trajectorySummary.heat_deviation_pct),
        makeComplaintIndexCell(trajectorySummary.complaint_index),
        makeQuadrantCell(trajectorySummary.quadrant),
      ]],
    )
  }

  // 滚动对比多期汇总表
  if (mode === 'rolling' && periods.length > 0) {
    rowSpecs.push({ type: 'blank', height: 10, cells: [] })
    const periodRows = periods.map((p) => [
      makeCell(p.label || '—', { align: 'left', bold: true, color: '0F172A' }),
      makeNumberCell(p.valid_days, 0),
      makeNumberCell(p.avg_temp, 2),
      makeNumberCell(p.actual_unit_heat_avg, 2),
      makeSignedPercentCell(p.heat_deviation_pct),
      makeComplaintIndexCell(p.complaint_index),
      makeQuadrantCell(p.quadrant),
    ])
    if (summary && periods.length > 1) {
      periodRows.push({
        isTotal: true,
        cells: [
          makeCell(`区间合计 (${summary.valid_days}天)`, { align: 'center', bold: true }),
          makeNumberCell(summary.valid_days, 0),
          makeNumberCell(summary.avg_temp, 2),
          makeNumberCell(summary.actual_unit_heat_avg, 2),
          makeSignedPercentCell(summary.heat_deviation_pct),
          makeComplaintIndexCell(summary.complaint_index),
          makeQuadrantCell(summary.quadrant),
        ],
      })
    }
    appendSectionTable(
      rowSpecs,
      '🔁 滚动周期对比汇总',
      ['周期区间', '有效天数', '平均气温(℃)', '实际单耗(GJ/万㎡·日)', '供热偏差率', '投诉强度指数', '象限归属'],
      periodRows,
    )
  }

  // 底部模型口径说明
  rowSpecs.push({ type: 'blank', height: 10, cells: [] })
  rowSpecs.push({
    type: 'section',
    height: 24,
    mergeFullRow: true,
    cells: [makeCell('ℹ️ 模型口径与数据范围说明')],
  })
  const spec = payload?.model_spec || {}
  const metaPairs = [
    ['模型公式', spec.equation || '参考日单耗 = 3.3730 + 0.5137 × 当日HDD20 + 0.3521 × 前3日平均HDD20 + 月份修正量'],
    ['有效窗口', spec.valid_window_rule || '每年 11月5日 — 次年3月31日（自动剔除 11.1–11.4 与 4.1–4.5）'],
    ['数据归口', spec.data_scope?.company_scope || 'ZhuChengQu（实际耗热与省市平台投诉均由 GongRe 统一归口）'],
    ['剔除天数', payload?.excluded_count ? `${payload.excluded_count} 天（${(payload.excluded_dates || []).join('、')}）` : '0 天'],
  ]
  metaPairs.forEach(([k, v]) => {
    rowSpecs.push({
      type: 'meta',
      height: 21,
      merges: [{ startCol: 1, endCol: maxCols - 1 }],
      cells: [makeCell(k, { align: 'center', bold: true }), makeCell(v, { align: 'left' })],
    })
  })

  return renderStyledRowsToSheet(rowSpecs, maxCols, { firstColMinWidth: 22, otherColMinWidth: 14 })
}

/**
 * 构建样式化的「逐日联合评价明细」Worksheet。
 */
export function buildJointEvaluationDetailSheet(payload, options = {}) {
  const rows = Array.isArray(payload?.daily_rows) ? payload.daily_rows : []
  const mode = options.mode || payload?.mode || 'single'
  const totalSource = mode === 'single' ? (payload?.trajectory_summary || payload?.summary) : payload?.summary
  const headers = [
    '日期',
    '日均气温(℃)',
    '当日HDD20',
    '前3日均值HDD20',
    '实际单耗(GJ/万㎡·日)',
    '参考单耗(GJ/万㎡·日)',
    '实际耗热(GJ)',
    '参考耗热(GJ)',
    '供热偏差率(%)',
    '实际投诉(件)',
    '参考投诉(件)',
    '投诉强度指数',
    '象限归属',
    '数据完整性',
  ]

  const rowSpecs = [
    {
      type: 'banner',
      height: 34,
      mergeFullRow: true,
      cells: [makeCell('主城区供热联合评价 · 逐日测算明细')],
    },
    {
      type: 'subtitle',
      height: 22,
      mergeFullRow: true,
      cells: [makeCell(buildSubtitleText(payload, options))],
    },
    { type: 'blank', height: 8, cells: [] },
  ]

  const formattedRows = rows.map((r) => [
    makeCell(r.date || '—', { align: 'center', bold: true, color: '0F172A' }),
    makeNumberCell(r.avg_temp, 2, { bold: false, color: '334155' }),
    makeNumberCell(r.hdd20_today, 2, { bold: false, color: '334155' }),
    makeNumberCell(r.hdd20_prev3, 2, { bold: false, color: '334155' }),
    makeNumberCell(r.actual_unit_heat, 2),
    makeNumberCell(r.ref_unit_heat, 2, { bold: false, color: '334155' }),
    makeNumberCell(r.actual_heat_gj, 0),
    makeNumberCell(r.ref_heat_gj, 0, { bold: false, color: '334155' }),
    makeSignedPercentCell(r.heat_deviation_pct),
    makeNumberCell(r.actual_complaints, 0),
    makeNumberCell(r.ref_complaints, 1, { bold: false, color: '334155' }),
    makeComplaintIndexCell(r.complaint_index),
    makeQuadrantCell(r.quadrant),
    makeCompletenessCell(r),
  ])

  if (totalSource && rows.length > 0) {
    formattedRows.push({
      isTotal: true,
      cells: [
        makeCell(`合计 / 区间(${totalSource.valid_days ?? rows.length}天)`, { align: 'center', bold: true }),
        makeNumberCell(totalSource.avg_temp, 2),
        makeNumberCell(totalSource.avg_hdd20_today, 2),
        makeNumberCell(totalSource.avg_hdd20_prev3, 2),
        makeNumberCell(totalSource.actual_unit_heat_avg, 2),
        makeNumberCell(totalSource.ref_unit_heat_avg, 2),
        makeNumberCell(totalSource.actual_heat_gj, 0),
        makeNumberCell(totalSource.ref_heat_gj, 0),
        makeSignedPercentCell(totalSource.heat_deviation_pct),
        makeNumberCell(totalSource.actual_complaints, 0),
        makeNumberCell(totalSource.ref_complaints, 1),
        makeComplaintIndexCell(totalSource.complaint_index),
        makeQuadrantCell(totalSource.quadrant),
        makeCell('区间累计口径', { align: 'center', bold: true, color: '334155' }),
      ],
    })
  }

  appendSectionTable(
    rowSpecs,
    '📅 逐日测算明细',
    headers,
    formattedRows,
    { headerHeight: 30 },
  )

  return renderStyledRowsToSheet(rowSpecs, headers.length, { firstColMinWidth: 16, otherColMinWidth: 13 })
}

/**
 * 构建包含「联合评价诊断汇总」与「逐日联合评价明细」的完整 Workbook。
 */
export function buildJointEvaluationWorkbook(payload, options = {}) {
  const wb = XLSX.utils.book_new()
  const usedNames = new Set()
  const generatedAt = options.generatedAt || new Date().toLocaleString()
  const ctx = { ...options, generatedAt }

  const wsSummary = buildJointEvaluationSummarySheet(payload, ctx)
  XLSX.utils.book_append_sheet(wb, wsSummary, resolveSheetName('联合评价诊断汇总', usedNames))

  const wsDetail = buildJointEvaluationDetailSheet(payload, ctx)
  XLSX.utils.book_append_sheet(wb, wsDetail, resolveSheetName('逐日联合评价明细', usedNames))

  return wb
}

/**
 * 触发浏览器下载样式化后的主城区供热联合评价 Excel (.xlsx) 文件。
 */
export function exportJointEvaluationExcelFile(payload, options = {}) {
  const rows = Array.isArray(payload?.daily_rows) ? payload.daily_rows : []
  if (!rows.length && !payload?.summary) return false

  const wb = buildJointEvaluationWorkbook(payload, options)
  const mode = options.mode || payload?.mode || 'single'
  const modeTag = MODE_LABELS[mode] || mode
  const stamp = payload?.anchor_date || new Date().toISOString().slice(0, 10)
  XLSX.writeFile(wb, `主城区供热联合评价_${modeTag}_${stamp}.xlsx`)
  return true
}
