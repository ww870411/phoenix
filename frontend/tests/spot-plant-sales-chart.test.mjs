import assert from 'node:assert/strict'
import test from 'node:test'
import { computed, ref } from 'vue'
import { readFileSync } from 'node:fs'
import { addPlantSalesToOption } from '../src/projects/daily_report_25_26/utils/spotPlantSalesChart.js'

function option(right = false) {
  return { yAxis: [{ show: true }, { show: right }], grid: { right: '2%' },
    series: [{ name: '实时电价' }], tooltip: { formatter: () => '原电价提示' } }
}

test('开启后增加两厂曲线、独立电量轴和图例，0保留、缺失断开', () => {
  const result = addPlantSalesToOption(option(true), [
    { beihai_total_sales: 0, xianghai_total_sales: 5 },
    { beihai_total_sales: null, xianghai_total_sales: 7 },
  ], { enabled: true, fields: ['beihai_total_sales', 'xianghai_total_sales'] })
  assert.equal(result.series.length, 3)
  assert.deepEqual(result.series[1].data, [0, null])
  assert.deepEqual(result.series[2].data, [5, 7])
  assert.equal(result.series[1].connectNulls, false)
  assert.equal(result.series[1].yAxisIndex, 2)
  assert.equal(result.yAxis[2].name, '上网电量 (MWh)')
  assert.equal(result.yAxis[2].offset, 66)
  assert.deepEqual(result.legend.data, ['北海上网电量', '香海上网电量'])
  const tip = result.tooltip.formatter([{ seriesName: '实时电价', dataIndex: 0 }])
  assert.match(tip, /原电价提示/)
  assert.match(tip, /北海上网电量: 0 MWh/)
})

test('关闭后保持原图；日月合计和时段均值使用各自字段，过滤时按原横轴断开', () => {
  const original = option()
  addPlantSalesToOption(original, [], { enabled: false })
  assert.equal(original.yAxis.length, 2)
  assert.equal(original.series.length, 1)
  for (const [fields, suffix] of [
    [['beihai_sales', 'xianghai_sales'], '（日合计）'],
    [['beihai_sales', 'xianghai_sales'], '（月合计）'],
    [['avg_beihai_sales', 'avg_xianghai_sales'], '（时段均值）'],
  ]) {
    const result = addPlantSalesToOption(option(), [{ [fields[0]]: 10, [fields[1]]: 20, negative: true },
      { [fields[0]]: 30, negative: false }], { enabled: true, fields, suffix, include: r => r.negative })
    assert.deepEqual(result.series[1].data, [10, null])
    assert.equal(result.series[1].name, `北海上网电量${suffix}`)
    assert.equal(result.yAxis[2].offset, 0)
  }
})

test('复选框由当前范围是否有原始电量决定，加载或失败时不可操作', () => {
  const page = readFileSync(new URL('../src/projects/daily_report_25_26/pages/SpotElectricityView.vue', import.meta.url), 'utf8')
  const declarations = page.match(/^const (?:hasPlantSalesData|canShowPlantSales) = .*$/gm).join('\n')
  const summary = ref(null), loading = ref(false), loadError = ref('')
  const available = new Function('computed', 'summary', 'loading', 'loadError', `${declarations}; return canShowPlantSales`)(computed, summary, loading, loadError)
  assert.equal(available.value, false)
  summary.value = { has_plant_sales_data: true }
  assert.equal(available.value, true)
  loading.value = true
  assert.equal(available.value, false)
  loading.value = false; loadError.value = '查询失败'
  assert.equal(available.value, false)
  loadError.value = ''; summary.value = { has_plant_sales_data: false }
  assert.equal(available.value, false)
})

test('切换日期时旧响应不能覆盖新范围的电量状态或提前结束加载', async () => {
  const page = readFileSync(new URL('../src/projects/daily_report_25_26/pages/SpotElectricityView.vue', import.meta.url), 'utf8')
  const source = page.slice(page.indexOf('let dataRequest = 0'), page.indexOf('// 渲染 ECharts'))
  const pending = []
  const deps = {
    projectKey: 'daily_report_25_26', selectedDate: ref('2026-01-12'), rangeStartDate: ref(''), rangeEndDate: ref(''),
    viewMode: ref('single'), onlyNegative: ref(false), loading: ref(false), loadError: ref(''),
    summary: ref(null), points: ref([]), dailyTrends: ref([]), monthlyTrends: ref([]), periodTrends: ref([]), showPlantSales: ref(false),
    getSpotElectricitySummary: () => new Promise(resolve => pending.push(resolve)),
    getSpotElectricityPoints: async (_p, options) => ({ ok: true, items: [{ trade_date: options.startDate }] }),
    nextTick: async () => {}, renderChart: () => {}, setTimeout: () => {}, chartInstance: null, chartRef: ref(null),
  }
  const fetchData = new Function('deps', `const { ${Object.keys(deps).join(',')} }=deps; ${source}; return fetchData`)(deps)
  const first = fetchData()
  deps.selectedDate.value = '2026-01-13'
  const second = fetchData()
  pending[0]({ ok: true, data: { has_plant_sales_data: true } })
  await first
  assert.equal(deps.loading.value, true)
  assert.equal(deps.summary.value, null)
  pending[1]({ ok: true, data: { has_plant_sales_data: false } })
  await second
  assert.equal(deps.loading.value, false)
  assert.equal(deps.summary.value.has_plant_sales_data, false)
  assert.equal(deps.points.value[0].trade_date, '2026-01-13')
})
