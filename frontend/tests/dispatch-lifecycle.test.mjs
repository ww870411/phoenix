// 生命周期依据语义、完整分页、实际ECharts渲染与组件请求竞争回归。
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { ref, computed } from 'vue'
import * as echarts from 'echarts'
import { buildLifecycle, buildLifecycleOption, buildLifecycleDateTicks, defaultLifecycleRange, DAY_MS, dayTime, formatTime, loadLifecycleReports, shiftDay, STATE_COLORS, LIFECYCLE_SUBJECTS, lifecycleSubjectName, compareLifecycleSubjects } from '../src/projects/daily_report_25_26/utils/dispatchLifecycle.js'
import { buildLifecycleExport, renderLifecycleSvg, lifecyclePngScale } from '../src/projects/daily_report_25_26/utils/dispatchLifecycleExport.js'
import { calculateDeviceRuntime } from '../src/projects/daily_report_25_26/utils/dispatchRuntime.js'

function report(day, status = '备用', events = []) {
  return { biz_date: day, file_name: `${day}生产信息.docx`, boiler_turbine_status: [{ unit_or_plant: '北海热电联产', standard_name: '#4汽炉', facility_type: '锅炉', status, table_status: '备用', main_events: events }], operations_and_tickets: events.map(e => ({ ...e, source_description: '10:30#4汽炉并汽,17:30 粉仓烧空停炉。' })) }
}
const operations = [{ time: '17:30', action: '停炉', status: '停运', raw_description: '#4汽炉停炉' }, { time: '10:30', action: '并汽', status: '运行', raw_description: '#4汽炉并汽' }]

test('六个主体按指定顺序显示，别名不改动原始归属，导出顺序一致', () => {
  const data = report('2026-10-30')
  data.boiler_turbine_status = ['北方热电', '香海电厂', '北海水炉', '金州热电', '燃气锅炉', '北海热电联产'].map(plant => ({ unit_or_plant: plant, standard_name: '#1汽炉', facility_type: '锅炉', status: '备用' }))
  const model = buildLifecycle([data], '2026-10-30', '2026-10-30')
  const expected = ['北海热电厂', '北海水路', '燃气锅炉', '香海热电厂', '金州热电', '北方热电']
  assert.deepEqual(model.devices.map(d => lifecycleSubjectName(d.plant)), expected)
  assert.equal(model.devices[0].plant, '北海热电联产')
  const spec = buildLifecycleExport([...model.devices].reverse(), { start: '2026-10-30', end: '2026-10-30' }, { subjects: null, type: 'ALL' }, 1)
  assert.deepEqual(spec.option.yAxis.data.map(label => label.split('\n')[0]), expected)
  assert.match(spec.filename, /全部主体/)
})

test('默认范围从2026年10月起真实第一条记录至最新记录，不受日期排序影响', () => {
  assert.deepEqual(defaultLifecycleRange(['2026-10-31', '2026-03-23', '2026-10-30', '2026-10-22', '2026-09-30', '2026-10-99']), { start: '2026-10-22', end: '2026-10-31' })
  assert.deepEqual(defaultLifecycleRange(['2026-10-01', '2027-01-02']), { start: '2026-10-01', end: '2027-01-02' })
  assert.equal(defaultLifecycleRange(['2026-03-23']), null)
  assert.equal(defaultLifecycleRange(), null)
})

test('日刻度默认每天显示，节点保留时分，长范围初始窗口可按宽度调整', () => {
  const model = buildLifecycle([report('2026-03-23', '备用', operations)], '2026-03-01', '2026-03-31')
  const option = buildLifecycleOption(model.devices, model.start, model.end, 7)
  assert.equal(option.xAxis.interval, 1)
  assert.equal(option.xAxis.axisLabel.hideOverlap, false)
  assert.equal(option.xAxis.axisLabel.formatter(0), '03-01')
  assert.equal(option.xAxis.axisLabel.formatter(1), '03-02')
  assert.equal(option.xAxis.axisLabel.formatter(0.5), '')
  assert.equal(option.dataZoom[0].endValue, 7)
  assert.equal(option.series[1].data[0].value[0], 22 + 10.5 / 24)
})

test('真实格式的复合操作成为两个按时刻排序的节点，日报状态保持独立', () => {
  const model = buildLifecycle([report('2026-03-23', '备用', operations)], '2026-03-23', '2026-03-23')
  const device = model.devices[0]
  assert.deepEqual(device.events.map(e => [e.time, e.kind]), [['10:30', 'online'], ['17:30', 'stop']])
  assert.equal(device.snapshots[0].status, '备用')
  assert.equal(device.segments[0].status, '备用')
  assert.match(device.events[0].sourceDescription, /粉仓烧空/)
  assert.equal(model.end - model.start, DAY_MS)
})

test('相同状态仅在连续有日报时合并，缺报日不填色', () => {
  const model = buildLifecycle([report('2026-03-26'), report('2026-03-23'), report('2026-03-24')], '2026-03-23', '2026-03-26')
  assert.equal(model.reportDays, 3)
  assert.equal(model.devices[0].segments.length, 2)
  assert.equal(model.devices[0].segments[0].end, dayTime('2026-03-25'))
  assert.equal(model.devices[0].segments[1].start, dayTime('2026-03-26'))
})

test('跨厂同号设备分行，不把日报状态裁决生成操作节点', () => {
  const data = report('2026-10-30')
  data.boiler_turbine_status.push({ unit_or_plant: '北方热电', standard_name: '#4汽炉', facility_type: '锅炉', status: '运行', table_status: '备用', status_confirmed: true, status_source: 'events' })
  const model = buildLifecycle([data], '2026-10-30', '2026-10-30')
  assert.equal(model.devices.length, 2)
  assert.equal(model.devices.flatMap(d => d.events).length, 0)
  assert.equal(model.devices.find(d => d.plant === '北方热电').snapshots[0].status, '运行')
})

test('无效时间保留于文字详情，不伪造图上的操作时刻', () => {
  const data = report('2026-03-23', '备用', [{ time: '26:00', action: '点火', status: '启动中', raw_description: '#4汽炉点火' }])
  const model = buildLifecycle([data], '2026-03-23', '2026-03-23')
  assert.equal(model.devices[0].events[0].timestamp, null)
  assert.equal(buildLifecycleOption(model.devices, model.start, model.end).series[1].data.length, 0)
})

test('日报内的次日主设备操作按真实发生日定位，并与次日报重复记录去重', () => {
  const event = { time: '03:00', action: '并列', status: '运行', raw_description: '#4汽炉并列', event_date: '2026-11-01' }
  const first = report('2026-10-31', '备用', [event])
  const second = report('2026-11-01', '运行', [event])
  const model = buildLifecycle([first, second], '2026-10-31', '2026-11-01')
  assert.equal(model.devices[0].events.length, 1)
  assert.equal(model.devices[0].events[0].day, '2026-11-01')
  assert.equal(model.devices[0].events[0].timestamp, dayTime('2026-11-01') + 3 * 3600000)
  assert.equal(buildLifecycle([first], '2026-10-31', '2026-10-31').devices[0].events.length, 0)
})

test('待确认差异保留标记，已确认差异按有效状态展示', () => {
  const data = report('2026-03-23')
  data.status_conflicts = [{ device: '北海热电联产|#4汽炉', resolution: null }]
  const first = buildLifecycle([data], '2026-03-23', '2026-03-23')
  assert.equal(first.devices[0].conflicts.length, 1)
  assert.equal(first.devices[0].segments[0].conflict, true)
  data.status_conflicts[0].resolution = 'table'
  assert.equal(buildLifecycle([data], '2026-03-23', '2026-03-23').devices[0].conflicts.length, 0)
})

test('日期采用北京时间，区间包括结束日，非法日期与逆序被拒绝', async () => {
  assert.equal(formatTime(dayTime('2026-03-23')), '2026-03-23')
  assert.equal(shiftDay('2026-03-01', -1), '2026-02-28')
  assert.ok(Number.isNaN(dayTime('2026-02-30')))
  const model = buildLifecycle([report('2026-03-22'), report('2026-03-23'), report('2026-03-24')], '2026-03-23', '2026-03-23')
  assert.equal(model.reportDays, 1)
  await assert.rejects(loadLifecycleReports(() => {}, '项目', '2026-03-24', '2026-03-23'), /起止日期/)
})

test('超过一页的时间阶段完整加载，不受默认50条限制', async () => {
  const calls = []
  const rows = Array.from({ length: 503 }, (_, id) => ({ id }))
  const result = await loadLifecycleReports(async (project, params) => {
    calls.push(params)
    return { ok: true, total: rows.length, items: rows.slice(params.offset, params.offset + params.limit) }
  }, 'daily_report_25_26', '2025-01-01', '2026-12-31')
  assert.equal(result.length, 503)
  assert.deepEqual(calls.map(c => c.offset), [0, 500])
  assert.equal(calls[0].start_date, '2025-01-01')
})

test('分页中断或后端失败明确报错，不把不完整记录当完整轨迹', async () => {
  await assert.rejects(loadLifecycleReports(async () => ({ ok: true, total: 1, items: [] }), '项目', '2026-03-23', '2026-03-23'), /完整/)
  await assert.rejects(loadLifecycleReports(async () => ({ ok: false, message: '查询失败' }), '项目', '2026-03-23', '2026-03-23'), /查询失败/)
})

test('ECharts真实SVG渲染正常，悬浮原文按文本转义', () => {
  const model = buildLifecycle([report('2026-03-23', '备用', operations)], '2026-03-23', '2026-03-23')
  const option = buildLifecycleOption(model.devices, model.start, model.end)
  const chart = echarts.init(null, null, { renderer: 'svg', ssr: true, width: 1100, height: 260 })
  try {
    chart.setOption(option)
    const svg = chart.renderToSVGString()
    assert.match(svg, /北海热电厂/)
    assert.match(svg, /停炉/)
    assert.match(svg, /并汽/)
    assert.doesNotMatch(option.tooltip.formatter({ data: { event: { timestamp: model.start, action: '<script>', sourceDescription: '<img>', fileName: '来源' }, deviceKey: '设备' } }), /<script>|<img>/)
  } finally { chart.dispose() }
})

test('单图日期栏在滑块百分比拖动、平移及缩放后持续有日期并对齐', () => {
  const model = buildLifecycle([report('2026-03-23', '备用', operations)], '2026-03-01', '2026-03-31')
  const option = buildLifecycleOption(model.devices, model.start, model.end, 7)
  const body = echarts.init(null, null, { renderer: 'svg', ssr: true, width: 1100, height: 300 })
  try {
    option.xAxis.axisLabel.show = false
    option.grid.top = 12
    body.setOption(option)
    assert.doesNotMatch(body.renderToSVGString(), /03-01/)
    for (const action of [
      { type: 'dataZoom', start: 62.7, end: 89.3 },
      { type: 'dataZoom', dataZoomIndex: 0, startValue: 20, endValue: 27 },
      { type: 'dataZoom', batch: [{ dataZoomIndex: 0, start: 68, end: 92 }] },
    ]) {
      body.dispatchAction(action)
      const ticks = buildLifecycleDateTicks(body, model.start, model.end)
      assert.ok(ticks.length > 0)
      assert.ok(ticks.some(t => t.label === '03-23'))
      for (const tick of ticks) assert.equal(tick.left, body.convertToPixel({ xAxisIndex: 0 }, tick.day))
    }
    body.resize({ width: 560 })
    assert.ok(buildLifecycleDateTicks(body, model.start, model.end).length > 0)
  } finally { body.dispose() }
})

test('完整导出保留筛选设备、全阶段和说明，不使用屏幕缩放窗口', () => {
  const model = buildLifecycle([report('2026-03-23', '备用', operations)], '2026-03-01', '2026-03-31')
  const spec = buildLifecycleExport(model.devices, { start: '2026-03-01', end: '2026-03-31' }, { subjects: ['北海热电厂'], type: '锅炉', onlyActive: true }, 1)
  assert.equal(spec.option.dataZoom.length, 0)
  assert.equal(spec.option.xAxis.max, 31)
  assert.equal(spec.option.yAxis.data.length, 1)
  assert.ok(spec.width >= 31 * 56)
  assert.match(spec.filename, /北海热电厂_锅炉_有操作或差异/)
  const svg = renderLifecycleSvg(spec)
  for (const text of ['主设备启停生命周期', '2026-03-01', '2026-03-31', '03-01', '03-31', '并汽', '停炉', '来源：已入库生产调度日报']) assert.ok(svg.includes(text), text)
  assert.match(svg, /7\.00h/)
  assert.match(svg, /日报估算/)
  assert.throws(() => buildLifecycleExport([], { start: '2026-03-01', end: '2026-03-31' }, {}, 0), /没有可导出/)
})

test('PNG按图像大小选择清晰分辨率，过大阶段可完整导出SVG', () => {
  assert.equal(lifecyclePngScale(1200, 600), 2)
  assert.ok(lifecyclePngScale(8000, 2500) >= 1)
  assert.throws(() => lifecyclePngScale(30000, 2500), /SVG/)
})

test('快速查询其他阶段时旧响应不会覆盖新结果，失败时清空旧图', async () => {
  const source = readFileSync(new URL('../src/projects/daily_report_25_26/components/DispatchLifecycle.vue', import.meta.url), 'utf8')
  const script = source.match(/<script setup>([\s\S]*?)<\/script>/)[1].replace(/import[^\n]+\n/g, '')
  const waiting = []
  const downloads = []
  const deps = { ref, computed, watch() {}, onBeforeUnmount() {}, nextTick: async () => {}, defineProps: () => ({ projectKey: '项目', latestDate: '' }),
    queryDispatchData: () => new Promise((resolve, reject) => waiting.push({ resolve, reject })), buildLifecycle, buildLifecycleOption, DAY_MS, dayTime, loadLifecycleReports, shiftDay, STATE_COLORS,
    LIFECYCLE_SUBJECTS, lifecycleSubjectName, compareLifecycleSubjects, calculateDeviceRuntime,
    buildLifecycleExport, renderLifecycleSvg, document: { fonts: { ready: Promise.resolve() } },
    downloadLifecycleBlob: (blob, filename) => downloads.push({ blob, filename }) }
  const factory = new Function('deps', `const {${Object.keys(deps).join(',')}} = deps;${script};return {startDate,endDate,loadRange,loadedRange,reports,error,exportGraph,canExport,selectedSubjects,toggleSubject,visibleDevices,subjectOptions,totalRuntime,type,chartScroll,dateAxisViewport,syncHorizontalScroll};`)
  const view = factory(deps)
  view.startDate.value = '2026-03-23'; view.endDate.value = '2026-03-23'
  const first = view.loadRange()
  view.startDate.value = '2026-10-30'; view.endDate.value = '2026-10-30'
  const second = view.loadRange()
  const secondReport = report('2026-10-30')
  secondReport.boiler_turbine_status.push({ unit_or_plant: '北方热电', standard_name: '#1汽炉', facility_type: '锅炉', status: '运行' })
  waiting[1].resolve({ ok: true, total: 1, items: [secondReport] })
  await second
  waiting[0].resolve({ ok: true, total: 1, items: [report('2026-03-23')] })
  await first
  assert.equal(view.loadedRange.value.start, '2026-10-30')
  assert.equal(view.reports.value[0].biz_date, '2026-10-30')
  view.chartScroll.value = { scrollLeft: 150 }
  view.dateAxisViewport.value = { scrollLeft: 0 }
  view.syncHorizontalScroll()
  assert.equal(view.dateAxisViewport.value.scrollLeft, 150)
  view.startDate.value = '2026-10-29'
  assert.equal(Boolean(view.canExport.value), false)
  await view.exportGraph('svg')
  assert.equal(downloads.length, 0)
  view.startDate.value = '2026-10-30'
  assert.equal(view.visibleDevices.value.length, 2)
  assert.equal(view.totalRuntime.value, 24)
  view.toggleSubject('北方热电', false)
  assert.deepEqual(view.selectedSubjects.value, ['北海热电厂'])
  assert.equal(view.visibleDevices.value.length, 1)
  assert.equal(view.totalRuntime.value, 0)
  view.toggleSubject('北海热电厂', false)
  assert.equal(view.visibleDevices.value.length, 0)
  assert.equal(Boolean(view.canExport.value), false)
  view.toggleSubject('北海热电厂', true)
  view.toggleSubject('北方热电', true)
  assert.equal(view.selectedSubjects.value, null)
  assert.equal(view.visibleDevices.value.length, 2)
  view.selectedSubjects.value = ['北方热电', '北海热电厂']
  view.type.value = '锅炉'
  await view.exportGraph('svg')
  assert.equal(downloads.length, 1)
  assert.match(downloads[0].filename, /2026-10-30_2026-10-30_北海热电厂、北方热电_锅炉_全部设备.svg/)
  assert.match(await downloads[0].blob.text(), /主设备启停生命周期/)
  const failed = view.loadRange()
  waiting[2].reject(new Error('读取失败'))
  await failed
  assert.equal(view.loadedRange.value, null)
  assert.equal(view.error.value, '读取失败')
})
