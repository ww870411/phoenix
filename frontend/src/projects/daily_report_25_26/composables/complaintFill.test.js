import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { complaintFillCenters, complaintFillMetrics, prepareComplaintFill } from './complaintFill.js'

const config = JSON.parse(readFileSync(new URL('../../../../../backend_data/projects/daily_report_25_26/config/数据结构_基本指标表.json', import.meta.url), 'utf8'))
const keys = ['GongRe_Sheet', 'GongRe_branches_detail_Sheet']
function fixture() {
  const metrics = Object.fromEntries(complaintFillMetrics.map(([, key], index) => [key, index]))
  metrics.unresolved_complaints = 45
  const stats = { complete: true, business_date: '2026-11-02', group: metrics, centers: complaintFillCenters.map((name, index) => ({ name, metrics: Object.fromEntries(Object.keys(metrics).map(key => [key, index])) })) }
  const sheets = Object.fromEntries(keys.map(key => [key, { columns: config[key]['列名'], baseColumns: config[key]['列名'], rows: structuredClone(config[key]['数据']) }]))
  return { stats, sheets }
}

test('真实模板严格匹配两张表的 67 个本期指标', () => {
  const { stats, sheets } = fixture()
  const before = structuredClone(sheets)
  const plan = prepareComplaintFill(stats, sheets, stats.business_date)
  assert.equal(plan.length, 67)
  assert.equal(plan.filter(item => item.sheetKey === keys[0] && item.colIndex === 2).length, 7)
  assert.equal(plan.filter(item => item.sheetKey === keys[1] && item.colIndex === 3).length, 60)
  assert.equal(plan.find(item => item.sheetKey === keys[0] && sheets[keys[0]].rows[item.rowIndex][0] === '当日省市平台投诉量').value, '0')
  assert.equal(plan.find(item => item.sheetKey === keys[0] && sheets[keys[0]].rows[item.rowIndex][0] === '截至该日未办结投诉量').value, '45')
  assert.equal(plan.find(item => item.sheetKey === keys[1] && sheets[keys[1]].rows[item.rowIndex][0] === '当日净投诉量' && sheets[keys[1]].rows[item.rowIndex][1] === '管网中心').value, '9')
  assert.deepEqual(sheets, before)
})

test('不完整统计、重复行、日期不一致均中止', () => {
  const { stats, sheets } = fixture()
  assert.throws(() => prepareComplaintFill({ ...stats, complete: false }, sheets, stats.business_date))
  assert.throws(() => prepareComplaintFill(stats, sheets, '2026-11-03'))
  sheets[keys[0]].rows.push([...sheets[keys[0]].rows.find(row => row[0] === '当日净投诉量')])
  assert.throws(() => prepareComplaintFill(stats, sheets, stats.business_date), /匹配到 2 行/)
})

test('缺少中心或无法确认本期列时拒绝生成回填计划', () => {
  const { stats, sheets } = fixture()
  assert.throws(() => prepareComplaintFill({ ...stats, centers: stats.centers.slice(1) }, sheets, stats.business_date), /中心统计结果不完整/)
  sheets[keys[1]].baseColumns[3] = '其他日期'
  sheets[keys[1]].columns[3] = '其他日期'
  assert.throws(() => prepareComplaintFill(stats, sheets, stats.business_date), /无法确认/)
})
