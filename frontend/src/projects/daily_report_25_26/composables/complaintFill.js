// 只映射两张供热表中已有的投诉指标，按标签与中心精确匹配。
export const complaintFillMetrics = [
  ['当日省市平台投诉量', 'daily_total'],
  ['当日净投诉量', 'daily_net'],
  ['其中：1.省平台净投诉量', 'daily_province_net'],
  ['其中：2.市平台净投诉量', 'daily_city_net'],
  ['本月累计净投诉量', 'monthly_net'],
  ['本供暖期累计净投诉量', 'season_net'],
]

// 供热公司总表专属补充指标（分中心明细表无此项）
export const gongreCompanyExtraMetrics = [
  ['截至该日未办结投诉量', 'unresolved_complaints'],
]

export const complaintFillCenters = ['华乐中心', '东港中心', '春海中心', '中山中心', '北岗中心', '双兴中心', '香炉礁中心', '兴工中心', '大纺中心', '管网中心']

export function prepareComplaintFill(stats, sheets, date) {
  if (!stats?.complete || stats.business_date !== date) throw new Error('统计结果不完整或业务日期已变化，请重新上传并核对。')
  const names = new Map((stats.centers || []).map(center => [center.name, center.metrics]))
  if (stats.centers?.length !== complaintFillCenters.length || names.size !== complaintFillCenters.length || complaintFillCenters.some(name => !names.has(name))) throw new Error('服务中心统计结果不完整，未填入数据。')
  const plans = []
  for (const [key, valueIndex, group, metricsList] of [
    ['GongRe_Sheet', 2, true, [...complaintFillMetrics, ...gongreCompanyExtraMetrics]],
    ['GongRe_branches_detail_Sheet', 3, false, complaintFillMetrics],
  ]) {
    const sheet = sheets[key]
    if (!sheet || !Array.isArray(sheet.rows) || !Array.isArray(sheet.columns)) throw new Error(`无法读取 ${key} 的数据，未填入。`)
    const base = String(sheet.baseColumns?.[valueIndex] || sheet.columns[valueIndex] || '')
    const shown = String(sheet.columns[valueIndex] || '')
    if (!(base.includes('本期') || shown.includes('本期') || shown.includes(date))) throw new Error(`无法确认 ${key} 的本期列，未填入。`)
    const entities = group ? [['', stats.group]] : complaintFillCenters.map(name => [name, names.get(name)])
    for (const [center, metrics] of entities) {
      for (const [label, metric] of metricsList) {
        const matches = sheet.rows.map((row, index) => ({ row, index })).filter(({ row }) => String(row?.[0] ?? '').trim() === label && (group || String(row?.[1] ?? '').trim() === center))
        if (matches.length !== 1) throw new Error(`表 ${key} 中“${label}${center ? ' / ' + center : ''}”匹配到 ${matches.length} 行，未填入。`)
        const value = metrics?.[metric]
        if (!Number.isInteger(value) || value < 0) throw new Error(`“${label}${center ? ' / ' + center : ''}”统计值无效，未填入。`)
        plans.push({ sheetKey: key, rowIndex: matches[0].index, colIndex: valueIndex, value: String(value) })
      }
    }
  }
  return plans
}
