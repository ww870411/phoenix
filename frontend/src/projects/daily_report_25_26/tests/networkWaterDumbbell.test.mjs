// 前端目录运行：node src/projects/daily_report_25_26/tests/networkWaterDumbbell.test.mjs
// 对组件实际请求逻辑模拟日期切换、失败及乱序响应，不访问接口或数据库。
import assert from 'node:assert/strict'
import vm from 'node:vm'
import { readFile } from 'node:fs/promises'
import { ref, computed, nextTick } from 'vue'
import * as echarts from 'echarts'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = new URL('../components/NetworkWaterDumbbellCard.vue', import.meta.url)
const source = await readFile(filename, 'utf8')
const { descriptor, errors } = parse(source)
assert.equal(errors.length, 0)
const script = compileScript(descriptor, { id: 'network-water-test' })
const template = compileTemplate({ source: descriptor.template.content, filename: filename.pathname,
  id: 'network-water-test', compilerOptions: { bindingMetadata: script.bindings } })
assert.deepEqual(template.errors, [])
const loader = source.slice(source.indexOf('const loading = ref(false)'), source.indexOf('/**', source.indexOf('const loadData =')))
const builder = source.slice(source.indexOf('const buildDumbbellOption ='), source.indexOf('const renderBothCharts ='))
assert.ok(!descriptor.template.content.includes('water-refresh-btn'), '移除板块刷新按钮')

function harness() {
  const requests = []
  let renders = 0
  const props = { projectKey: 'daily_report_25_26', bizDate: '2026-11-01' }
  const context = vm.createContext({ ref, computed, nextTick, AbortController, props,
    renderBothCharts: () => { renders++ }, console: { error() {} },
    getDashboardNetworkWaterDumbbell: (projectKey, options) => new Promise((resolve, reject) => {
      requests.push({ projectKey, ...options, resolve, reject })
    }),
  })
  vm.runInContext(`${loader}\n${builder}\nglobalThis.state = { loadData, loading, hasData, dumbbellData, errorMsg, buildDumbbellOption, formatNumber };`, context)
  return { state: context.state, requests, props, renders: () => renders }
}
function payload(date) {
  return { ok: true, biz_date: date, dimensions: {
    day: { biz_range: date, total: { current: 100 } }, season: { biz_range: date, total: { current: 100 } },
  } }
}

// 日期 A 成功后，日期 B 开始就清空旧数据；B 失败不能继续显示 A。
const first = harness()
let task = first.state.loadData()
first.requests[0].resolve(payload('2026-11-01'))
await task
assert.equal(first.state.hasData.value, true)
first.props.bizDate = '2026-11-02'
task = first.state.loadData()
assert.equal(first.state.hasData.value, false)
assert.equal(first.state.dumbbellData.value, null)
assert.equal(first.state.loading.value, true)
assert.equal(first.requests[1].showDate, '2026-11-02')
first.requests[1].reject(new Error('模拟请求失败'))
await task
assert.equal(first.state.hasData.value, false)
assert.equal(first.state.errorMsg.value, '模拟请求失败')
assert.equal(first.state.loading.value, false)

// 重试只恢复当前日期的结果，清除错误。
task = first.state.loadData()
assert.equal(first.state.errorMsg.value, '')
first.requests[2].resolve(payload('2026-11-02'))
await task
assert.equal(first.state.dumbbellData.value.biz_date, '2026-11-02')
assert.equal(first.state.hasData.value, true)

// 模拟上游忽略取消：旧请求晚到不能覆盖新日期或触发旧图重绘。
const race = harness()
const older = race.state.loadData()
race.props.bizDate = '2026-11-02'
const newer = race.state.loadData()
assert.equal(race.requests[0].signal.aborted, true)
race.requests[1].resolve(payload('2026-11-02'))
await newer
race.requests[0].resolve(payload('2026-11-01'))
await older
assert.equal(race.state.dumbbellData.value.biz_date, '2026-11-02')
assert.equal(race.renders(), 1)

// 被取消的旧请求结束，不得关闭新请求的加载状态，也不得显示旧错误。
const cancelled = harness()
const cancelledTask = cancelled.state.loadData()
cancelled.props.bizDate = '2026-11-02'
const activeTask = cancelled.state.loadData()
cancelled.requests[0].reject(Object.assign(new Error('cancelled'), { name: 'AbortError' }))
await cancelledTask
assert.equal(cancelled.state.loading.value, true)
assert.equal(cancelled.state.errorMsg.value, '')
cancelled.requests[1].resolve(payload('2026-11-02'))
await activeTask
assert.equal(cancelled.state.loading.value, false)

// 上下标尺上限均为整千，实际刻度也按整千划分，万单位最多显示一位小数。
const dimension = {
  total: { current: 13000, peer: 14000, diff: -1000, diff_rate: -7.1 },
  items: [
    { key: 'ZhuChengQu', name: '主城区', current: 12000, peer: 12897, diff: -897, diff_rate: -7 },
    { key: 'JinZhou', name: '金州热电', current: 1000, peer: 1103, diff: -103, diff_rate: -9.3 },
  ],
}
for (const isSeason of [false, true]) {
  const option = first.state.buildDumbbellOption(dimension, isSeason)
  assert.equal(option.xAxis[0].max, 15000)
  assert.equal(option.xAxis[1].max, 6000)
  for (const axis of option.xAxis) {
    for (const [value, expected] of [[0, '0'], [5000, '5000'], [10000, '1万'], [12000, '1.2万'], [13000, '1.3万'], [2051000, '205.1万']]) {
      assert.equal(axis.axisLabel.formatter(value), expected)
    }
  }
  const chart = echarts.init(null, null, { renderer: 'svg', ssr: true, width: 800, height: 450 })
  try {
    chart.setOption(option)
    option.xAxis.forEach((axis, index) => {
      const ticks = chart.getModel().getComponent('xAxis', index).axis.scale.getTicks().map(tick => tick.value)
      assert.ok(ticks.every(value => value % 1000 === 0), '实际刻度均为整千')
      assert.equal(new Set(ticks.map(axis.axisLabel.formatter)).size, ticks.length, '刻度文字不重复')
    })
  } finally { chart.dispose() }
}
const overflowDimension = structuredClone(dimension)
overflowDimension.items[1].current = 12345
const overflowOption = first.state.buildDumbbellOption(overflowDimension)
assert.equal(overflowOption.xAxis[1].max, 14000, '下方标尺扩大以容纳数值时也保持整千')
assert.equal(first.state.formatNumber(12000.4), '12,000', '数据标签继续显示整数')
console.log('通过：Vue 编译、切日立即清空、失败隐藏旧数据、重试、乱序响应隔离及取消请求的加载状态。')
