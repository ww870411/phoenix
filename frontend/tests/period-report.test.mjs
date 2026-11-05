import test from 'node:test'
import assert from 'node:assert/strict'
import { buildChapterPages, reportNumber } from '../src/projects/daily_report_25_26/composables/periodReportPresentation.js'
import { withDailyBriefPage } from '../src/projects/daily_report_25_26/composables/dailyBriefPresentation.js'

test('始终五章五页，七家单位全部保留在本章', () => {
  const rows = Array.from({ length: 7 }, (_, i) => ({ name: `单位${i}`, curr: i }))
  const pages = buildChapterPages([{ key: 'consumption_std_coal', title: '标煤耗量', unit: '吨', paragraphs: ['集团标煤耗量100吨。'], rows }])
  assert.equal(pages.length, 5)
  assert.deepEqual(pages.map(p => p.chapter), [0, 1, 2, 3, 4])
  assert.deepEqual(pages[1].panels[0].rows.map(r => r.curr), rows.map(r => r.curr))
  assert.equal(pages[0].kpis[0].name, '标煤耗量')
})

test('跨多月保持五页，月份作为第五章内的选项且正文不无限增长', () => {
  const plans = Array.from({ length: 12 }, (_, i) => ({ key: `plan-${i}`, title: `${i+1}月标煤计划执行`, kind: 'plan', paragraphs: [], rows: [] }))
  const pages = buildChapterPages(plans)
  assert.equal(pages.length, 5)
  assert.equal(pages[4].panels.length, 12)
  assert.ok(pages[4].paragraphs.length <= 6)
})

test('汇报入口紧随每日简报，仅继承同范围管理员可见性', () => {
  const seed = [{ page_key: 'period_report' }, { page_key: 'dashboard' }]
  assert.deepEqual(withDailyBriefPage(seed, 'daily_report_25_26', { group: 'Global_admin' }).map(p => p.page_key), ['daily_brief', 'period_report', 'dashboard'])
  assert.deepEqual(withDailyBriefPage(seed, 'daily_report_25_26', { group: 'Group_viewer' }).map(p => p.page_key), ['dashboard'])
})

test('缺数不补零，真实零与负利润保留', () => {
  assert.equal(reportNumber(null), '—')
  assert.equal(reportNumber(Infinity), '—')
  assert.equal(reportNumber(0), '0')
  assert.equal(reportNumber(-12.5), '-12.5')
})
