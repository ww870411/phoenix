// 日报快照与定时操作分开建模；不将快照覆盖日解释为真实运行时长。
import { graphic } from 'echarts'

export const DAY_MS = 86400000
export const STATE_COLORS = { 运行: '#059669', 启动中: '#e79919', 停运: '#dc5263', 备用: '#8496ad', 检修: '#8b67c6', 未知: '#cbd5e1' }
export const LIFECYCLE_SUBJECTS = [
  { name: '北海热电厂', aliases: ['北海热电联产', '北海电厂', '北海热电厂'] },
  { name: '北海水路', aliases: ['北海水炉', '北海水路'] },
  { name: '燃气锅炉', aliases: ['燃气锅炉'] },
  { name: '香海热电厂', aliases: ['香海电厂', '香海热电厂'] },
  { name: '金州热电', aliases: ['金州热电'] },
  { name: '北方热电', aliases: ['北方热电'] },
]

export function lifecycleSubjectName(plant) {
  return LIFECYCLE_SUBJECTS.find(subject => subject.aliases.includes(plant))?.name || plant
}

export function compareLifecycleSubjects(a, b) {
  const first = lifecycleSubjectName(a), second = lifecycleSubjectName(b)
  const rank = name => { const index = LIFECYCLE_SUBJECTS.findIndex(s => s.name === name); return index < 0 ? LIFECYCLE_SUBJECTS.length : index }
  return rank(first) - rank(second) || first.localeCompare(second, 'zh-CN')
}

export function sortLifecycleDevices(devices) {
  return [...devices].sort((a, b) => compareLifecycleSubjects(a.plant, b.plant) || a.type.localeCompare(b.type, 'zh-CN') || Number(a.name.match(/\d+/)?.[0] || 0) - Number(b.name.match(/\d+/)?.[0] || 0))
}
const START_ACTIONS = new Set(['点火', '点炉', '启动', '冲转'])
const STOP_ACTIONS = new Set(['停运', '停炉', '停机', '灭火', '解列', '跳闸'])
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))

export function dayTime(day) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day || '')) return NaN
  const time = Date.parse(`${day}T00:00:00+08:00`)
  return Number.isFinite(time) && formatTime(time).slice(0, 10) === day ? time : NaN
}

export function formatTime(time, withClock = false) {
  if (!Number.isFinite(time)) return '时间不明'
  return new Date(time + 8 * 3600000).toISOString().slice(0, withClock ? 16 : 10).replace('T', ' ')
}

export function shiftDay(day, count) {
  return formatTime(dayTime(day) + count * DAY_MS)
}

export function defaultLifecycleRange(dates = []) {
  // 以真实业务日期为准，不用固定10月1日或“最新日期减30天”补造起点。
  const eligible = dates.filter(day => day >= '2026-10-01' && Number.isFinite(dayTime(day))).sort()
  return eligible.length ? { start: eligible[0], end: eligible.at(-1) } : null
}

export async function loadLifecycleReports(query, projectKey, startDate, endDate) {
  if (!Number.isFinite(dayTime(startDate)) || !Number.isFinite(dayTime(endDate)) || startDate > endDate) throw new Error('请选择有效的起止日期，开始日期不能晚于结束日期')
  const reports = []
  let total = Infinity
  while (reports.length < total) {
    const result = await query(projectKey, { start_date: startDate, end_date: endDate, limit: 500, offset: reports.length })
    if (result?.ok === false || !Array.isArray(result?.items)) throw new Error(result?.message || '生命周期数据读取失败')
    total = Number.isFinite(Number(result.total)) ? Number(result.total) : reports.length + result.items.length
    if (!result.items.length && reports.length < total) throw new Error('日报数据未完整返回，请刷新重试')
    reports.push(...result.items)
  }
  return reports
}

export function buildLifecycle(reports, startDate, endDate) {
  const start = dayTime(startDate), end = dayTime(endDate) + DAY_MS
  const devices = new Map(), reportDays = new Set()
  for (const report of [...reports].sort((a, b) => a.biz_date.localeCompare(b.biz_date))) {
    const day = dayTime(report.biz_date)
    if (!Number.isFinite(day) || day < start || day >= end) continue
    reportDays.add(report.biz_date)
    const conflicts = new Map((report.status_conflicts || []).map(c => [c.device, c]))
    for (const facility of report.boiler_turbine_status || []) {
      const plant = facility.unit_or_plant || '其他', name = facility.standard_name || facility.raw_name
      if (!name) continue
      const key = `${plant}|${name}`
      if (!devices.has(key)) devices.set(key, { key, plant, name, type: facility.facility_type || '锅炉', snapshots: [], events: [], segments: [], conflicts: [] })
      const device = devices.get(key), conflict = conflicts.get(key)
      const snapshot = { day: report.biz_date, start: day, end: day + DAY_MS, status: facility.status || '未知',
        tableStatus: facility.table_status || facility.status, source: facility.status_source || 'table', fileName: report.file_name,
        confirmed: Boolean(facility.status_confirmed), conflict: Boolean(conflict && !conflict.resolution) }
      device.snapshots.push(snapshot)
      if (conflict && !conflict.resolution) device.conflicts.push({ ...conflict, day: report.biz_date, fileName: report.file_name })
      for (const event of facility.main_events || []) {
        const eventDay = event.event_date || report.biz_date
        const eventDayTime = dayTime(eventDay)
        if (Number.isFinite(eventDayTime) && (eventDayTime < start || eventDayTime >= end)) continue
        const timeMatch = /^(\d{1,2}):(\d{2})$/.exec(String(event.time || ''))
        const validTime = timeMatch && Number(timeMatch[1]) < 24 && Number(timeMatch[2]) < 60
        const time = validTime && Number.isFinite(eventDayTime) ? eventDayTime + (Number(timeMatch[1]) * 60 + Number(timeMatch[2])) * 60000 : null
        const id = `${key}|${eventDay}|${event.time}|${event.action}|${event.raw_description}`
        if (device.events.some(e => e.id === id)) continue
        const operation = (report.operations_and_tickets || []).find(e => (e.time === event.time || e.event_clock === event.time) && (e.raw_description === event.raw_description || e.main_description?.includes(event.raw_description)))
        device.events.push({ ...event, id, deviceKey: key, day: Number.isFinite(eventDayTime) ? eventDay : report.biz_date, timestamp: time,
          sourceDescription: operation?.source_description || event.raw_description, fileName: report.file_name,
          kind: START_ACTIONS.has(event.action) ? 'start' : STOP_ACTIONS.has(event.action) ? 'stop' : 'online' })
      }
    }
  }
  for (const device of devices.values()) {
    // 只合并连续有日报且状态/确认口径一致的日格；缺报日期永不补齐。
    for (const snapshot of device.snapshots) {
      const last = device.segments.at(-1)
      if (last && last.end === snapshot.start && last.status === snapshot.status && last.conflict === snapshot.conflict && last.source === snapshot.source) {
        last.end = snapshot.end
        last.days.push(snapshot.day)
      } else device.segments.push({ ...snapshot, days: [snapshot.day] })
    }
    device.events.sort((a, b) => a.day.localeCompare(b.day) || (a.timestamp ?? Infinity) - (b.timestamp ?? Infinity))
  }
  const rows = sortLifecycleDevices([...devices.values()])
  return { devices: rows, reportDays: reportDays.size, start, end }
}

export function buildLifecycleDateTicks(chart, start, end) {
  // 从唯一主图读取公开坐标变换；横向拖动、百分比缩放都不再依赖空图联动。
  const left = 145, right = chart.getWidth() - 25
  const min = chart.convertFromPixel({ xAxisIndex: 0 }, left)
  const max = chart.convertFromPixel({ xAxisIndex: 0 }, right)
  if (!Number.isFinite(min) || !Number.isFinite(max)) return []
  const ticks = []
  for (let day = Math.max(0, Math.ceil(min - 1e-8)); day <= Math.min(Math.floor(max + 1e-8), (end - start) / DAY_MS - 1); day++) {
    ticks.push({ day, left: chart.convertToPixel({ xAxisIndex: 0 }, day), label: formatTime(start + day * DAY_MS).slice(5) })
  }
  return ticks
}

export function buildLifecycleOption(devices, start, end, visibleDays = 14) {
  const totalDays = (end - start) / DAY_MS
  const visibleEnd = Math.min(totalDays, Math.max(1, visibleDays))
  const bands = [], points = []
  devices.forEach((device, row) => {
    device.segments.forEach(segment => bands.push({ value: [(segment.start - start) / DAY_MS, row, (segment.end - start) / DAY_MS], deviceKey: device.key, segment,
      itemStyle: { color: STATE_COLORS[segment.status] || STATE_COLORS.未知 } }))
    device.events.filter(e => e.timestamp !== null).forEach(event => points.push({ value: [(event.timestamp - start) / DAY_MS, row], event, deviceKey: device.key,
      symbol: event.kind === 'start' ? 'triangle' : event.kind === 'stop' ? 'rect' : 'diamond',
      itemStyle: { color: STATE_COLORS[event.status] || '#334155', borderColor: '#fff', borderWidth: 2 },
      label: { show: devices.reduce((n, d) => n + d.events.length, 0) <= 24, position: 'top', distance: 4, formatter: event.action, fontSize: 10, color: '#334155' } }))
  })
  return {
    backgroundColor: '#fff',
    animation: false,
    grid: { left: 145, right: 25, top: 36, bottom: 64 },
    tooltip: { trigger: 'item', confine: true, formatter: params => {
      const { event, segment, deviceKey } = params.data || {}
      if (event) return `${escapeHtml(deviceKey)}<br/><b>${escapeHtml(formatTime(event.timestamp, true))} · ${escapeHtml(event.action)}</b><br/>${escapeHtml(event.sourceDescription)}<br/>来源：${escapeHtml(event.fileName || '调度日报')}`
      if (segment) return `${escapeHtml(deviceKey)}<br/><b>${escapeHtml(segment.status)} · 日报记载状态</b><br/>${segment.days[0]} 至 ${segment.days.at(-1)}（${segment.days.length}份日报）<br/>${segment.conflict ? '存在待确认差异，点击查看' : segment.source === 'events' ? '已确认以事件为准' : segment.source.startsWith('status:') ? '人工指定状态' : '以日报表格为准'}<br/>色带不代表该时段持续处于此状态`
      return ''
    } },
    // 以北京时间起点的日偏移为坐标，避免数值轴按UTC整日对齐导致08:00刻度。
    xAxis: { type: 'value', min: 0, max: totalDays, position: 'top', interval: 1,
      axisLabel: { formatter: day => !Number.isInteger(day) || day >= totalDays ? '' : formatTime(start + day * DAY_MS).slice(5), color: '#64748b', hideOverlap: false },
      axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: true, lineStyle: { color: '#e8eef5' } } },
    yAxis: { type: 'category', inverse: true, data: devices.map(d => `${lifecycleSubjectName(d.plant)}\n${d.name}`),
      axisLabel: { color: '#334155', fontSize: 11, lineHeight: 16 }, axisLine: { show: false }, axisTick: { show: false },
      splitArea: { show: true, areaStyle: { color: ['#f8fafc', '#fff'] } } },
    dataZoom: [{ type: 'slider', xAxisIndex: 0, filterMode: 'none', height: 18, bottom: 14, borderColor: '#e2e8f0',
      startValue: 0, endValue: visibleEnd, minValueSpan: 1,
      showDetail: false, brushSelect: false }, { type: 'inside', xAxisIndex: 0, filterMode: 'none', minValueSpan: 1, zoomOnMouseWheel: false, moveOnMouseWheel: false }],
    series: [{ name: '日报状态', type: 'custom', encode: { x: [0, 2], y: 1 }, data: bands,
      renderItem(params, api) {
        const from = api.coord([api.value(0), api.value(1)]), to = api.coord([api.value(2), api.value(1)])
        const height = Math.min(22, api.size([0, 1])[1] * 0.46)
        const shape = graphic.clipRectByRect({ x: from[0] + 1, y: from[1] - height / 2, width: Math.max(1, to[0] - from[0] - 2), height }, params.coordSys)
        const item = bands[params.dataIndex]
        return shape ? { type: 'rect', shape: { ...shape, r: 3 }, style: { fill: item.itemStyle.color, opacity: 0.28,
          stroke: item.segment.conflict ? '#d97706' : item.itemStyle.color, lineWidth: item.segment.conflict ? 2 : 0,
          lineDash: item.segment.conflict ? [4, 3] : undefined } } : null
      } },
    { name: '操作节点', type: 'scatter', data: points, symbolSize: 15, z: 4, labelLayout: { hideOverlap: true }, encode: { x: 0, y: 1 } }],
  }
}
