import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { comparisonLabels } from '../src/projects/daily_report_25_26/composables/analysisPresentation.js'


test('结果元数据优先于当前查询模式，并兼容旧结果模式名称', () => {
  assert.deepEqual(comparisonLabels({ analysis_mode: 'daily' }, 'range'), { current: '当日值', peer: '同期当日值', previous: '上期当日值' })
  assert.equal(comparisonLabels({ analysis_mode: 'range' }, 'daily').current, '本期累计')
  assert.equal(comparisonLabels({ analysis_mode_label: '累计数据' }).peer, '同期累计')
  assert.equal(comparisonLabels(null, 'daily').current, '当日值')
})


// 加载页面中实际使用的格式化与导出函数，覆盖 0 小数位和默认小数位。
const source = readFileSync(new URL('../src/projects/daily_report_25_26/pages/DataAnalysisView.vue', import.meta.url), 'utf8')
const names = ['formatNumber', 'formatExportNumber', 'resolveValue', 'resolveDelta', 'resolveTotalCurrentFromRow', 'buildSummarySheetData', 'buildRingSheetData']
const functions = names.map(name => {
  const start = source.indexOf(`function ${name}(`)
  return source.slice(start, source.indexOf('\nfunction ', start + 10))
}).join('\n')
function pageFunctions(mode) {
  return new Function('comparisonLabels', 'analysisMode', 'computeRelativeRate', 'formatPercentValue', `${functions}; return { ${names.join(', ')} };`)(
    comparisonLabels, { value: mode }, (a, b) => b ? ((a - b) / b) * 100 : null, value => value == null ? '' : `${value}%`,
  )
}

test('页面数字格式化保留 0 位、2 位及默认小数位', () => {
  const page = pageFunctions('daily')
  assert.equal(page.formatNumber(12.6, 0), '13')
  assert.equal(page.formatNumber(12.6, 2), '12.60')
  assert.equal(page.formatNumber(12.6), '12.60')
  assert.equal(page.formatNumber(null, 0), '—')
})

test('同比 Excel 表头和数字保持结果口径，缺省与 0 位区分', () => {
  const page = pageFunctions('daily')
  const rows = [
    { key: 'a', label: '台数', current: 12.6, peer: 10.2, decimals: 0 },
    { key: 'b', label: '煤量', current: 12.678, peer: 10.123 },
  ]
  const sheet = page.buildSummarySheetData(rows, { analysis_mode: 'daily' })
  assert.deepEqual(sheet[0].slice(1, 3), ['当日值', '同期当日值'])
  assert.deepEqual(sheet[1].slice(1, 3), [13, 10])
  assert.deepEqual(sheet[2].slice(1, 3), [12.68, 10.12])
  assert.equal(page.buildSummarySheetData(rows, { analysis_mode: 'range' })[0][1], '本期累计')
})

test('环比 Excel 单日和累计表头及整数精度一致', () => {
  const page = pageFunctions('daily')
  const result = { meta: { analysis_mode: 'daily' }, rows: [{ key: 'a', label: '台数', total_current: 12.6, decimals: 0 }], ringCompare: { prevTotals: { a: 10.2 }, range: {} } }
  const sheet = page.buildRingSheetData(result)
  assert.deepEqual(sheet[0].slice(1, 3), ['上期当日值', '当日值'])
  assert.deepEqual(sheet[1].slice(1, 3), [10, 13])
  result.meta.analysis_mode = 'range'
  assert.deepEqual(page.buildRingSheetData(result)[0].slice(1, 3), ['上期累计', '本期累计'])
})
