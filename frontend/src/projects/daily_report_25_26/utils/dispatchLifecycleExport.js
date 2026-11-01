// 从当前数据筛选构造独立完整图，不截取有滚动裁切的页面或改变屏幕图表缩放。
import * as echarts from 'echarts'
import { buildLifecycleOption, dayTime, DAY_MS, STATE_COLORS, lifecycleSubjectName, compareLifecycleSubjects, sortLifecycleDevices } from './dispatchLifecycle.js'
import { calculateDeviceRuntime } from './dispatchRuntime.js'

export function buildLifecycleExport(devices, range, filters, reportDays) {
  if (!devices.length) throw new Error('当前筛选没有可导出的设备')
  devices = sortLifecycleDevices(devices)
  const start = dayTime(range.start), end = dayTime(range.end) + DAY_MS
  const days = (end - start) / DAY_MS
  if (!Number.isFinite(days) || days < 1) throw new Error('导出日期范围无效')
  const width = Math.max(1200, days * 56 + 190), height = Math.max(500, devices.length * 55 + 330)
  const subjects = filters.subjects == null ? '全部主体' : [...filters.subjects].sort(compareLifecycleSubjects).map(lifecycleSubjectName).join('、')
  const scope = `${subjects} · ${filters.type === 'ALL' ? '全部机炉' : filters.type} · ${filters.onlyActive ? '有操作或差异的设备' : '全部设备'}`
  const events = devices.flatMap(d => d.events)
  const pending = devices.reduce((n, d) => n + d.conflicts.length, 0)
  const runtimes = devices.map(device => calculateDeviceRuntime(device, range))
  const totals = runtimes.reduce((result, runtime) => ({ hours: result.hours + runtime.hours, actionHours: result.actionHours + runtime.actionHours,
    snapshotHours: result.snapshotHours + runtime.snapshotHours, unknownHours: result.unknownHours + runtime.unknownHours }), { hours: 0, actionHours: 0, snapshotHours: 0, unknownHours: 0 })
  const option = buildLifecycleOption(devices, start, end, days)
  option.dataZoom = []
  option.tooltip = { show: false }
  option.grid = { ...option.grid, top: 210, bottom: 110 }
  option.yAxis.data = devices.map((device, index) => `${lifecycleSubjectName(device.plant)}\n${device.name} · ${runtimes[index].hours.toFixed(2)}h`)
  // 同日并汽/停炉节点较近时，标签交替放在行上下，减少静态图文字互相遮挡。
  const rowCounts = new Map()
  for (const point of option.series[1].data) {
    const row = point.value[1], index = rowCounts.get(row) || 0
    point.label = { ...point.label, show: true, position: index % 2 ? 'bottom' : 'top' }
    rowCounts.set(row, index + 1)
  }
  option.title = { text: '主设备启停生命周期', subtext: `${range.start} 至 ${range.end}  |  ${scope}`, left: 24, top: 20,
    textStyle: { fontSize: 25, color: '#18344f' }, subtextStyle: { fontSize: 13, color: '#64748b' } }
  const text = (left, top, value, size = 12, color = '#64748b') => ({ type: 'text', left, top, style: { text: value, font: `${size}px sans-serif`, fill: color } })
  const legend = Object.entries(STATE_COLORS).flatMap(([state, color], index) => [
    { type: 'rect', left: 24 + index * 85, top: 138, shape: { width: 12, height: 12, r: 2 }, style: { fill: color, opacity: 0.65 } },
    text(43 + index * 85, 138, state),
  ])
  option.graphic = [
    text(24, 88, `${reportDays} 天有日报记录  |  ${devices.length} 台设备  |  ${events.length} 条操作（${events.filter(e => e.timestamp === null).length}条时间不明，未定位到图上）  |  ${pending} 个设备日待核对`),
    text(24, 108, `推算运行 ${totals.hours.toFixed(2)} 设备小时（操作计时 ${totals.actionHours.toFixed(2)}h；日报估算 ${totals.snapshotHours.toFixed(2)}h；另有 ${totals.unknownHours.toFixed(2)}h 待核对）`),
    ...legend, text(560, 138, '▲ 启动   ◆ 并入/投运   ■ 停止   虚线框：状态待确认'),
    text(24, height - 77, '计时：同轮启停优先按并汽/并网/并列等投入时刻；缺少时按点火/启动/冲转起计，按停止时刻结算并跨日分摊。'),
    text(24, height - 52, '来源：已入库生产调度日报。浅色带为日报状态快照；无色区间为缺少该设备记录。无定时操作的日报估算单独列示。'),
    text(24, height - 25, '导出范围为当前已查询的完整阶段及设备筛选，不受页面滚动位置或时间滑块窗口影响。', 11, '#94a3b8'),
  ]
  const filename = `主设备生命周期_${range.start}_${range.end}_${scope.replace(/ · /g, '_')}`.replace(/[\\/:*?"<>|]/g, '_')
  return { width, height, option, filename }
}

export function renderLifecycleSvg(spec) {
  const chart = echarts.init(null, null, { renderer: 'svg', ssr: true, width: spec.width, height: spec.height })
  try {
    chart.setOption(spec.option)
    return chart.renderToSVGString()
  } finally { chart.dispose() }
}

export function lifecyclePngScale(width, height) {
  // 保留可读的1倍以上分辨率；超大图使用SVG而不输出模糊或被截断的PNG。
  const scale = Math.min(2, 16000 / width, 16000 / height, Math.sqrt(32000000 / (width * height)))
  if (!Number.isFinite(scale) || scale < 1) throw new Error('此图尺寸较大，请选择导出 SVG，可保留完整内容并任意放大')
  return scale
}

export async function lifecycleSvgToPng(svg, width, height) {
  const scale = lifecyclePngScale(width, height)
  const imageUrl = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml;charset=utf-8' }))
  const canvas = document.createElement('canvas')
  try {
    const image = new Image()
    await new Promise((resolve, reject) => { image.onload = resolve; image.onerror = () => reject(new Error('图像转换失败，请重试或导出SVG')); image.src = imageUrl })
    canvas.width = Math.ceil(width * scale)
    canvas.height = Math.ceil(height * scale)
    const context = canvas.getContext('2d')
    if (!context) throw new Error('浏览器无法创建图片，请导出SVG')
    context.fillStyle = '#fff'
    context.fillRect(0, 0, canvas.width, canvas.height)
    context.drawImage(image, 0, 0, canvas.width, canvas.height)
    return await new Promise((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('PNG生成失败，请导出SVG')), 'image/png'))
  } finally {
    URL.revokeObjectURL(imageUrl)
    canvas.width = canvas.height = 0
  }
}

export function downloadLifecycleBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  try { link.click() } finally { link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000) }
}
