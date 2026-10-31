// 页面和 Excel 共用查询结果口径。
export function comparisonLabels(meta, fallbackMode = 'daily') {
  const mode = meta?.analysis_mode ||
    (meta?.analysis_mode_label === '单日数据' ? 'daily' : meta?.analysis_mode_label === '累计数据' ? 'range' : fallbackMode)
  return mode === 'daily'
    ? { current: '当日值', peer: '同期当日值', previous: '上期当日值' }
    : { current: '本期累计', peer: '同期累计', previous: '上期累计' }
}

