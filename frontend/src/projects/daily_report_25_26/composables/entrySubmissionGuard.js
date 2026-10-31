// 缓存和已加载网格必须同时对应表格、业务日期及配置。
export function entryContextKey(sheetKey, bizDate, config) {
  return JSON.stringify([sheetKey, bizDate, config || ''])
}

export function requireEntryQuery(result) {
  if (!result || result.ok === false || !Array.isArray(result.rows) || !Array.isArray(result.columns)) {
    throw new Error(result?.message || '未读取到完整的报表数据，请重试')
  }
  return result
}

export function requireSubmissionSuccess(result) {
  if (result?.ok !== true || !Number.isFinite(result.inserted) || result.inserted <= 0) {
    throw new Error(result?.message && result.ok !== true ? result.message : '服务器未确认写入记录，请核对后重试')
  }
  return result
}
