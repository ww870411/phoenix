// 按北京时间自然日分摊运行时长。明确区分操作计时、日报估算与无法确定的时间。
import { DAY_MS, dayTime, formatTime } from './dispatchLifecycle.js'

const STARTUP = new Set(['点火', '点炉', '启动', '冲转'])
const PRIMARY_ONLINE = new Set(['并汽', '并网', '并列'])
const STOP = new Set(['停机', '停炉', '停运', '灭火', '解列', '跳闸'])
function activeStatus(status, includeStartup) {
  if (status === '运行') return true
  if (status === '启动中') return includeStartup
  if (['停运', '备用', '检修'].includes(status)) return false
  return null
}

function runtimeEvents(events) {
  const result = []
  let cycle = []
  const finish = () => {
    const online = cycle.some(e => e.status === '运行')
    const primary = cycle.find(e => PRIMARY_ONLINE.has(e.action))
    for (const event of cycle) result.push({ ...event,
      runtimeActive: STARTUP.has(event.action) ? !online : primary && event.status === '运行' && event.timestamp < primary.timestamp ? false : activeStatus(event.status, true), startupCounts: !online })
    cycle = []
  }
  for (const event of [...events].sort((a, b) => a.timestamp - b.timestamp)) {
    cycle.push(event)
    if (event.status === '停运') finish()
  }
  finish()
  return result
}

export function calculateDeviceRuntime(device, range) {
  const start = dayTime(range.start), end = dayTime(range.end) + DAY_MS
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return { hours: 0, actionHours: 0, snapshotHours: 0, unknownHours: 0, days: [] }
  const snapshots = new Map(device.snapshots.map(s => [s.day, s]))
  const invalidDays = new Set(device.events.filter(e => !Number.isFinite(e.timestamp)).map(e => e.day))
  const byDay = new Map()
  for (const event of runtimeEvents(device.events.filter(e => Number.isFinite(e.timestamp) && e.timestamp >= start && e.timestamp < end))) {
    if (!Number.isFinite(event.timestamp) || event.timestamp < start || event.timestamp >= end) continue
    if (!byDay.has(event.day)) byDay.set(event.day, [])
    byDay.get(event.day).push(event)
  }
  let carry = null, fromAction = false, startupCounts = true
  const days = []
  for (let begin = start; begin < end; begin += DAY_MS) {
    const day = formatTime(begin), snapshot = snapshots.get(day)
    const events = (byDay.get(day) || []).sort((a, b) => a.timestamp - b.timestamp)
    const reasons = new Set()
    let state = carry, actionBased = fromAction, cursor = begin
    let actionMs = 0, snapshotMs = 0, unknownMs = 0
    if (!fromAction || state === null) {
      if (events.length) {
        // 当日第一条为停止动作，回推停止前在运；第一条为启动/并入，则从该动作起计。
        const firstActive = events[0].runtimeActive
        state = firstActive === null ? null : STOP.has(events[0].action)
        if (new Set(events.filter(e => e.timestamp === events[0].timestamp).map(e => e.runtimeActive)).size > 1) state = null
        actionBased = true
        reasons.add(STOP.has(events[0].action) ? '按停止时刻回推当日停止前在运' : '按当日操作时刻分段计时')
      } else {
        state = activeStatus(snapshot?.status, startupCounts)
        actionBased = false
        if (state !== null) reasons.add('当日无定时操作，按日报状态估算全天')
      }
    } else reasons.add('按此前已记录的操作状态延续')
    const add = until => {
      const duration = until - cursor
      if (state === null) unknownMs += duration
      else if (state) {
        if (actionBased) actionMs += duration
        else snapshotMs += duration
      }
      cursor = until
    }
    for (let i = 0; i < events.length;) {
      const time = events[i].timestamp
      add(time)
      const concurrent = []
      while (i < events.length && events[i].timestamp === time) concurrent.push(events[i++])
      const statuses = new Set(concurrent.map(e => e.runtimeActive))
      state = statuses.size === 1 ? [...statuses][0] : null
      startupCounts = concurrent.every(e => e.startupCounts)
      actionBased = true
      if (concurrent.some(e => STARTUP.has(e.action))) reasons.add(startupCounts ? '本轮缺少并汽/并网/并列等记录，按启动动作计时' : '本轮有并入/投运记录，启动准备阶段不计时')
      if (state === null) reasons.add('同一时刻操作状态矛盾，后续时长待核对')
    }
    add(begin + DAY_MS)
    const snapshotState = activeStatus(snapshot?.status, startupCounts)
    let conflict = Boolean(snapshot?.conflict)
    if (snapshotState !== null && state !== null && snapshotState !== state) {
      conflict = true
      reasons.add('日报状态与操作延续不一致，需核对缺失动作')
      if (!events.length && actionBased) {
        // 没有停止时刻却从运行变为备用时，不能把24小时全计为运行或全计为停止。
        actionMs = snapshotMs = 0
        unknownMs = DAY_MS
      }
      carry = null
      fromAction = false
    } else { carry = state; fromAction = actionBased }
    if (invalidDays.has(day)) {
      actionMs = snapshotMs = 0
      unknownMs = DAY_MS
      carry = null; fromAction = false; conflict = true
      reasons.add('当日有时刻缺失或无效的主设备操作，时长待核对')
    }
    days.push({ day, hours: (actionMs + snapshotMs) / 3600000, actionHours: actionMs / 3600000,
      snapshotHours: snapshotMs / 3600000, unknownHours: unknownMs / 3600000, conflict,
      basis: [...reasons].join('；') || '缺少操作及日报状态，时长待核对' })
  }
  return days.reduce((result, day) => ({ ...result, hours: result.hours + day.hours,
    actionHours: result.actionHours + day.actionHours, snapshotHours: result.snapshotHours + day.snapshotHours,
    unknownHours: result.unknownHours + day.unknownHours }), { hours: 0, actionHours: 0, snapshotHours: 0, unknownHours: 0, days })
}
