import { test } from 'node:test'
import assert from 'node:assert/strict'
import { calculateDeviceRuntime } from '../src/projects/daily_report_25_26/utils/dispatchRuntime.js'
import { dayTime } from '../src/projects/daily_report_25_26/utils/dispatchLifecycle.js'

const event = (day, time, action, status) => ({ day, time, action, status, timestamp: time === null ? null : dayTime(day) + (Number(time.split(':')[0]) * 60 + Number(time.split(':')[1])) * 60000 })
const device = (snapshots, events) => ({ snapshots: snapshots.map(([day, status]) => ({ day, status })), events })

test('3月23日10:30并汽17:30停炉计7小时，不按备用快照覆盖操作计时', () => {
  const r = calculateDeviceRuntime(device([['2026-03-23', '备用']], [event('2026-03-23', '10:30', '并汽', '运行'), event('2026-03-23', '17:30', '停炉', '停运')]), { start: '2026-03-23', end: '2026-03-23' })
  assert.equal(r.hours, 7)
  assert.equal(r.actionHours, 7)
  assert.equal(r.snapshotHours, 0)
})

test('同轮有并汽时优先并汽，点火到并汽的准备阶段不计', () => {
  const r = calculateDeviceRuntime(device([['2026-10-30', '运行']], [event('2026-10-30', '09:20', '点火', '启动中'), event('2026-10-30', '14:40', '并汽', '运行')]), { start: '2026-10-30', end: '2026-10-30' })
  assert.ok(Math.abs(r.hours - (9 + 20 / 60)) < 1e-9)
})

test('同轮先并热网后并列，优先从并列时刻而非较早的并热网计时', () => {
  const r = calculateDeviceRuntime(device([['2026-10-31', '运行']], [event('2026-10-31', '15:40', '并热网', '运行'), event('2026-10-31', '15:46', '并列', '运行')]), { start: '2026-10-31', end: '2026-10-31' })
  assert.ok(Math.abs(r.hours - (8 + 14 / 60)) < 1e-9)
})

test('仅有启动记录时从启动计时，跨日分摊至停止时刻', () => {
  const r = calculateDeviceRuntime(device([['2026-03-23', '启动中'], ['2026-03-24', '备用']], [event('2026-03-23', '10:30', '点火', '启动中'), event('2026-03-24', '17:30', '停炉', '停运')]), { start: '2026-03-23', end: '2026-03-24' })
  assert.deepEqual(r.days.map(d => d.hours), [13.5, 17.5])
  assert.equal(r.hours, 31)
})

test('同一设备多轮启停分别判断优先级，不误用另一轮的并网时刻', () => {
  const r = calculateDeviceRuntime(device([['2026-03-23', '备用'], ['2026-03-24', '备用']], [
    event('2026-03-23', '09:00', '启动', '启动中'), event('2026-03-23', '14:00', '并列', '运行'), event('2026-03-23', '18:00', '停机', '停运'),
    event('2026-03-24', '09:00', '冲转', '启动中'), event('2026-03-24', '12:00', '停机', '停运'),
  ]), { start: '2026-03-23', end: '2026-03-24' })
  assert.deepEqual(r.days.map(d => d.hours), [4, 3])
})

test('跨日启动后并网，优先并网而不把前一天启动准备算运行', () => {
  const r = calculateDeviceRuntime(device([['2026-03-23', '启动中'], ['2026-03-24', '备用']], [event('2026-03-23', '09:00', '启动', '启动中'), event('2026-03-24', '10:00', '并网', '运行'), event('2026-03-24', '12:00', '停机', '停运')]), { start: '2026-03-23', end: '2026-03-24' })
  assert.deepEqual(r.days.map(d => d.hours), [0, 2])
  assert.equal(r.unknownHours, 0)
})

test('仅有停止动作则按停止时刻回推当日起始运行时间', () => {
  const r = calculateDeviceRuntime(device([['2026-03-23', '备用']], [event('2026-03-23', '17:30', '停炉', '停运')]), { start: '2026-03-23', end: '2026-03-23' })
  assert.equal(r.hours, 17.5)
  assert.match(r.days[0].basis, /回推/)
})

test('无定时动作按日报运行估24小时，缺日报与状态矛盾不伪造时长', () => {
  const r = calculateDeviceRuntime(device([['2026-03-23', '运行']], []), { start: '2026-03-23', end: '2026-03-24' })
  assert.equal(r.snapshotHours, 24)
  assert.equal(r.unknownHours, 24)
  const conflict = calculateDeviceRuntime(device([['2026-03-23', '运行'], ['2026-03-24', '备用']], [event('2026-03-23', '10:00', '并汽', '运行')]), { start: '2026-03-23', end: '2026-03-24' })
  assert.equal(conflict.hours, 14)
  assert.equal(conflict.days[1].unknownHours, 24)
})

test('时刻无效及同刻相反动作保留未知时长，午夜结束不多计一天', () => {
  const invalid = calculateDeviceRuntime(device([['2026-03-23', '运行']], [event('2026-03-23', null, '并汽', '运行')]), { start: '2026-03-23', end: '2026-03-23' })
  assert.equal(invalid.hours, 0)
  assert.equal(invalid.unknownHours, 24)
  const mixed = calculateDeviceRuntime(device([], [event('2026-03-23', '10:00', '并汽', '运行'), event('2026-03-23', '10:00', '停炉', '停运')]), { start: '2026-03-23', end: '2026-03-23' })
  assert.equal(mixed.unknownHours, 24)
  const midnight = calculateDeviceRuntime(device([], [event('2026-03-23', '00:00', '并汽', '运行')]), { start: '2026-03-23', end: '2026-03-23' })
  assert.equal(midnight.hours, 24)
})
