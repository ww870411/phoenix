// 修正页面统一使用项目名称、真实导航层级及明确的空值展示。
export function correctionBreadcrumbs(projectName) {
  return [
    { label: '项目选择', to: '/projects' },
    { label: projectName, to: '/projects/daily_report_25_26/pages' },
    { label: '数据修正申请记录', to: null },
  ]
}

export function correctionValue(value) {
  return value == null || String(value).trim() === '' ? '空值' : String(value)
}

export function correctionColumn(column) {
  const name = String(column || '')
  if (name.includes('同期')) return '同期值'
  if (name.includes('本期')) return '本期值'
  return name || '数据值'
}
