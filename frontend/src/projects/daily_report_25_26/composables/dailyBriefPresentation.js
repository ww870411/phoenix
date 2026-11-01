// 每日简报只对 Global_admin 开放，不能用其他管理员能力代替这一身份。
export function canAccessDailyBrief(projectKey, user) {
  return projectKey === 'daily_report_25_26' && user?.group === 'Global_admin'
}

export function withDailyBriefPage(pages, projectKey, user) {
  const existing = (Array.isArray(pages) ? pages : []).filter(page => page.page_key !== 'daily_brief')
  if (!canAccessDailyBrief(projectKey, user)) return existing
  return [{ page_key: 'daily_brief', page_name: '每日简报', page_url: '/projects/daily_report_25_26/pages/daily_brief' }, ...existing]
}

export function formatBriefNumber(value, digits = 2) {
  if (value === null || value === undefined || value === '' || !Number.isFinite(Number(value))) return '—'
  return Number(value).toLocaleString('zh-CN', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

export function changeText(metric) {
  const change = metric.comparison
  if (!change || change.delta === null) return '同比 —'
  if (change.direction === 'flat') return '同比持平'
  const direction = change.direction === 'up' ? '增加' : '减少'
  const percent = change.percent === null ? '' : `（${formatBriefNumber(Math.abs(change.percent), 1)}%）`
  return `同比${direction} ${formatBriefNumber(Math.abs(change.delta), metric.digits)} ${metric.unit}${percent}`
}

export function briefDeltaClass(value, digits = 2) {
  if (value === null || value === undefined || value === '' || !Number.isFinite(Number(value))) return ''
  const delta = Number(Number(value).toFixed(digits))
  return delta > 0 ? 'change-up' : delta < 0 ? 'change-down' : 'change-flat'
}

export function briefComparisonParts(value) {
  const text = String(value || '')
  // 按每个比较短语分别着色，允许同一句中的同比增加与较前日减少使用不同颜色。
  const pattern = /(?:同比|较昨日)(?:增加|减少)[^，；。]*|(?:同比|较昨日)持平|(?:已)?连续\d+日(?:高于|低于)(?:各自)?同期|(?:较前日)?连续\d+(?:日|次日间比较)(?:增加|减少)/g
  const parts = []
  let cursor = 0
  for (const match of text.matchAll(pattern)) {
    if (match.index > cursor) parts.push({ text: text.slice(cursor, match.index), className: '' })
    const phrase = match[0]
    const amount = phrase.match(/(?:增加|减少)\s*([\d,]+(?:\.\d+)?)/)
    const isFlat = phrase.includes('持平') || (amount && Number(amount[1].replaceAll(',', '')) === 0)
    const className = isFlat ? 'change-flat' : /增加|高于/.test(phrase) ? 'change-up' : 'change-down'
    parts.push({ text: phrase, className })
    cursor = match.index + phrase.length
  }
  if (cursor < text.length) parts.push({ text: text.slice(cursor), className: '' })
  return parts
}
