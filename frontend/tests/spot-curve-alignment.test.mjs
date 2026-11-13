import test from 'node:test'
import assert from 'node:assert/strict'

import {
  evaluateCurveAlignment,
  buildPlantAlignmentReport,
} from '../src/projects/daily_report_25_26/utils/spotCurveAlignment.js'

test('完全同向序列输出 +1 相关系数', () => {
  const prices = [-50, 50, 150, 250, 350, 450, 300, 100]
  const rows = prices.map((p, idx) => ({
    trade_date: '2026-04-01',
    point_index: idx + 1,
    day_ahead_price: p,
    real_time_price: p,
    beihai_total_sales: 100 + p * 0.2,
  }))

  const metrics = evaluateCurveAlignment(rows, 'beihai_total_sales', 'day_ahead_price')
  assert.equal(metrics.validPoints, 8)
  assert.ok(Math.abs(metrics.correlation - 1) < 1e-9)
  assert.equal(metrics.intradayCorrelation, null)
})

test('完全反向序列输出 -1 相关系数', () => {
  const prices = [-20, 100, 250, 420, 180, 30]
  const rows = prices.map((p, idx) => ({
    trade_date: '2026-04-01',
    point_index: idx + 1,
    day_ahead_price: p,
    beihai_total_sales: 200 - p * 0.25,
  }))

  const metrics = evaluateCurveAlignment(rows, 'beihai_total_sales', 'day_ahead_price')
  assert.ok(Math.abs(metrics.correlation - (-1)) < 1e-9)
})

test('多日日内去均值相关可排除跨天基荷趋势干扰、识别日内同步性', () => {
  const rows = [
    { trade_date: '2026-04-01', point_index: 95, day_ahead_price: 100, beihai_total_sales: 300 },
    { trade_date: '2026-04-01', point_index: 96, day_ahead_price: 200, beihai_total_sales: 340 },
    { trade_date: '2026-04-03', point_index: 1, day_ahead_price: 300, beihai_total_sales: 100 },
    { trade_date: '2026-04-03', point_index: 2, day_ahead_price: 400, beihai_total_sales: 140 },
  ]

  const metrics = evaluateCurveAlignment(rows, 'beihai_total_sales', 'day_ahead_price')
  assert.equal(metrics.dayCount, 2)
  assert.ok(metrics.correlation < 0)
  assert.ok(Math.abs(metrics.intradayCorrelation - 1) < 1e-9)
})

test('全停机零波动、电价全平或空数据时安全返回 null，不产生 NaN', () => {
  const flatRows = [1, 2, 3, 4].map(idx => ({
    trade_date: '2026-04-05',
    point_index: idx,
    day_ahead_price: 250,
    real_time_price: 260,
    beihai_total_sales: 0,
    xianghai_total_sales: 100,
  }))
  const report = buildPlantAlignmentReport(flatRows)
  assert.equal(report.hasAnyMetrics, true)
  assert.equal(report.byKey.beihai.dayAhead.correlation, null)
  assert.equal(report.byKey.xianghai.realTime.correlation, null)

  assert.equal(buildPlantAlignmentReport([]).hasAnyMetrics, false)
})
