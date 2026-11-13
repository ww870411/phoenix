import assert from 'node:assert/strict'
import test from 'node:test'
import { buildContinuousTimeline, formatPointPeriod } from '../src/projects/daily_report_25_26/utils/spotContinuousSeries.js'

test('formatPointPeriod 正确转换 1..96 时点为标准 15 分钟时刻', () => {
  assert.deepEqual(formatPointPeriod(1), {
    time_label: '00:15',
    period_start_time: '00:00:00',
    period_end_time: '00:15:00',
  })
  assert.deepEqual(formatPointPeriod(96), {
    time_label: '24:00',
    period_start_time: '23:45:00',
    period_end_time: '24:00:00',
  })
})

test('buildContinuousTimeline 连续时原样保留全部原始值且无缺失标记', () => {
  const raw = [
    { trade_date: '2026-10-10', point_index: 95, time_label: '23:45', day_ahead_price: 210, real_time_price: 220, price_spread: 10 },
    { trade_date: '2026-10-10', point_index: 96, time_label: '24:00', day_ahead_price: 190, real_time_price: 185, price_spread: -5 },
    { trade_date: '2026-10-11', point_index: 1, time_label: '00:15', day_ahead_price: 180, real_time_price: 170, price_spread: -10 },
  ]
  const timeline = buildContinuousTimeline(raw)
  assert.equal(timeline.length, 3)
  assert.deepEqual(timeline.map(i => i.__missing), [false, false, false])
  assert.deepEqual(timeline.map(i => i.axisLabel), [
    '2026-10-10 23:45',
    '2026-10-10 24:00',
    '2026-10-11 00:15',
  ])
  assert.equal(timeline[0].day_ahead_price, 210)
})

test('buildContinuousTimeline 中间存在缺失时段或整天缺失时自动插入 null 占位点以便断线', () => {
  const raw = [
    { trade_date: '2026-10-10', point_index: 95, time_label: '23:45', day_ahead_price: 300, real_time_price: 310, price_spread: 10 },
    // 跳过 2026-10-10 #96 和 2026-10-11 #1
    { trade_date: '2026-10-11', point_index: 2, time_label: '00:30', day_ahead_price: 280, real_time_price: 260, price_spread: -20 },
  ]
  const timeline = buildContinuousTimeline(raw)
  assert.equal(timeline.length, 4)
  assert.equal(timeline[0].__missing, false)
  assert.equal(timeline[1].__missing, true)
  assert.equal(timeline[1].trade_date, '2026-10-10')
  assert.equal(timeline[1].point_index, 96)
  assert.equal(timeline[1].time_label, '24:00')
  assert.equal(timeline[1].day_ahead_price, null)
  assert.equal(timeline[2].__missing, true)
  assert.equal(timeline[2].trade_date, '2026-10-11')
  assert.equal(timeline[2].point_index, 1)
  assert.equal(timeline[2].time_label, '00:15')
  assert.equal(timeline[2].real_time_price, null)
  assert.equal(timeline[3].__missing, false)
  assert.equal(timeline[3].day_ahead_price, 280)
})

test('buildContinuousTimeline 空数组安全返回空数组', () => {
  assert.deepEqual(buildContinuousTimeline([]), [])
  assert.deepEqual(buildContinuousTimeline(null), [])
})
