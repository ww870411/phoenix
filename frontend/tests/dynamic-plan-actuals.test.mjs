import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { ref, computed, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import * as Vue from 'vue'
import { renderToString } from 'vue/server-renderer'
import { compile } from '@vue/compiler-dom'

const base = '../src/projects/daily_report_25_26/'
const composable = readFileSync(new URL(`${base}composables/useDynamicPlanActuals.js`, import.meta.url), 'utf8')
  .replace(/^import .*\n/gm, '').replace(/export /g, '')
function helpers(fetchDynamicPlanActuals = () => {}, fetchDynamicPlanCumulativeActuals = () => {}) {
  const cleanup = []
  const deps = { ref, watch, onBeforeUnmount: fn => cleanup.push(fn), fetchDynamicPlanActuals, fetchDynamicPlanCumulativeActuals }
  const result = new Function('deps', `const {${Object.keys(deps)}}=deps;${composable};
    return {useDynamicPlanActuals,singleMetricSelection,actualBarSeries,monthDates,aggregateDecomposedPlan};`)(deps)
  return { ...result, cleanup }
}

const source = readFileSync(new URL(`${base}pages/DynamicPlanMetricsView.vue`, import.meta.url), 'utf8')
const pageScript = source.match(/<script setup>([\s\S]*?)<\/script>/)[1].replace(/^import .*\n/gm, '')
function page() {
  const h = helpers()
  const options = []
  const deps = { ref, computed, watch, nextTick, onBeforeUnmount() {}, onMounted() {},
    useRoute: () => ({ params: {}, query: {} }), useAuthStore: () => ({}),
    getProjectNameById: () => '', ...h,
    echarts: { init: () => ({ setOption: option => options.push(option), resize() {} }) },
    useDynamicPlanActuals: () => ({ data: ref(null), error: ref(''), loading: ref(false) }) }
  const result = new Function('deps', `const {${Object.keys(deps)}}=deps;${pageScript};
    return {showActualValues,chartSelectedMetricKeys,selectedMetricKeys,metricsList,focusedMetricKey,
      handleChartMetricSelection,focusMetric,selectAllChartMetrics,resetToDefaultChartMetrics,getDefaultChartMetricKeys,
      actualQuery,isDynamicDecomposeEnabled,dynamicTargetMonth,displayedMonths,activeChartTab,
      actualData,chartContainerRef,renderChart,primaryFilterMetrics,secondaryFilterMetrics,
      showCumulativeActual,latestPublishedDate,canShowDynamicActuals,cumulativeQuery,cumulativeData,dynamicDecompData,
      decompDetailData,activeDecompositionMetrics,formatCell,formatNumber,getDailyDetailActual,getDailyDetailActualTotal,options:deps.options};`)({ ...deps, options })
  result.latestPublishedDate.value = '2026-11-03'
  return result
}
const metrics = [
  { item: 'amount_heat_supply', item_cn: '供热量', unit: 'GJ' },
  { item: 'amount_power_generation', item_cn: '发电量', unit: '万kWh' },
  { item: 'consumption_std_coal', item_cn: '标煤耗量', unit: '吨' },
]

test('默认关闭实际值；启用后保留一个，选择另一指标立即替换', async () => {
  assert.ok(source.includes('显示逐日实际值'))
  const view = page()
  assert.deepEqual(view.getDefaultChartMetricKeys(metrics), ['consumption_std_coal'])
  assert.deepEqual(view.getDefaultChartMetricKeys(metrics.slice(0, 2)), ['amount_heat_supply'])
  assert.deepEqual(view.getDefaultChartMetricKeys([]), [])
  assert.deepEqual(view.getDefaultChartMetricKeys(null), [])
  view.metricsList.value = metrics
  view.selectedMetricKeys.value = metrics.map(m => m.item)
  view.chartSelectedMetricKeys.value = metrics.map(m => m.item)
  view.resetToDefaultChartMetrics()
  assert.deepEqual(view.chartSelectedMetricKeys.value, ['consumption_std_coal'])
  view.chartSelectedMetricKeys.value = metrics.map(m => m.item)
  assert.deepEqual(view.primaryFilterMetrics.value.map(m => m.item), ['consumption_std_coal', 'amount_heat_supply', 'amount_power_generation'])
  assert.deepEqual(view.secondaryFilterMetrics.value.map(m => m.item), ['consumption_std_coal', 'amount_heat_supply', 'amount_power_generation'])
  assert.equal(view.showActualValues.value, false)
  view.showActualValues.value = true
  assert.deepEqual(view.chartSelectedMetricKeys.value, ['amount_heat_supply'])
  view.handleChartMetricSelection('consumption_std_coal', true)
  assert.deepEqual(view.chartSelectedMetricKeys.value, ['consumption_std_coal'])
  view.showActualValues.value = false
  view.handleChartMetricSelection('amount_power_generation', true)
  assert.equal(view.chartSelectedMetricKeys.value.length, 2)
  await nextTick()
})

test('表格聚焦、全选、默认重置和外部赋值都无法突破单指标限制', async () => {
  const view = page()
  view.metricsList.value = metrics
  view.selectedMetricKeys.value = metrics.map(m => m.item)
  view.showActualValues.value = true
  await nextTick()
  view.focusMetric(metrics[2])
  assert.deepEqual(view.chartSelectedMetricKeys.value, ['consumption_std_coal'])
  view.selectAllChartMetrics()
  assert.equal(view.chartSelectedMetricKeys.value.length, 1)
  view.resetToDefaultChartMetrics()
  assert.equal(view.chartSelectedMetricKeys.value.length, 1)
  view.chartSelectedMetricKeys.value = metrics.map(m => m.item)
  assert.equal(view.chartSelectedMetricKeys.value.length, 1)
  view.handleChartMetricSelection('amount_power_generation', true)
  assert.equal(view.focusedMetricKey.value, '')
  await nextTick()
})

test('月度与日度查询切换粒度和范围；气温不完整也可查实际，环形图不混入实际', async () => {
  const view = page()
  view.metricsList.value = metrics
  view.selectedMetricKeys.value = metrics.map(m => m.item)
  view.chartSelectedMetricKeys.value = ['consumption_std_coal']
  view.displayedMonths.value = ['2026-11', '2026-12']
  view.showActualValues.value = true
  assert.equal(view.actualQuery.value.granularity, 'month')
  assert.equal(view.actualQuery.value.end_month, '2026-12')
  view.isDynamicDecomposeEnabled.value = true
  view.latestPublishedDate.value = '2026-12-02'
  view.dynamicTargetMonth.value = '2026-12'
  view.showActualValues.value = true
  assert.equal(view.actualQuery.value.granularity, 'day')
  assert.equal(view.actualQuery.value.start_month, '2026-12')
  assert.equal(view.actualQuery.value.end_month, '2026-12')
  view.isDynamicDecomposeEnabled.value = false
  view.activeChartTab.value = 'donut_distribution'
  assert.equal(view.actualQuery.value, null)
  await nextTick()
})

test('异步实际查询立即清空旧值、取消旧请求并拦截乱序响应', async () => {
  const requests = []
  const h = helpers((project, params, signal) => new Promise(resolve => requests.push({ params, signal, resolve })))
  const params = { company: 'Group', item: 'consumption_std_coal', unit: '吨', granularity: 'month' }
  const query = ref(params)
  const view = h.useDynamicPlanActuals('daily_report_25_26', query)
  query.value = { ...params, company: 'BeiHai' }
  assert.equal(requests[0].signal.aborted, true)
  assert.equal(view.data.value, null)
  requests[1].resolve({ ok: true, ...requests[1].params, values: { '2026-11': 4 } })
  await nextTick()
  assert.equal(view.data.value.company, 'BeiHai')
  requests[0].resolve({ ok: true, ...params, values: { '2026-11': 999 } })
  await nextTick()
  assert.equal(view.data.value.company, 'BeiHai')
  query.value = null
  assert.equal(view.data.value, null)
  assert.equal(view.loading.value, false)
  h.cleanup.forEach(fn => fn())
})

test('错误响应不展示旧实际，卸载时取消当前请求', async () => {
  const requests = []
  const h = helpers((project, params, signal) => new Promise(resolve => requests.push({ params, signal, resolve })))
  const query = ref({ company: 'Group', item: 'consumption_std_coal', unit: '吨', granularity: 'day' })
  const view = h.useDynamicPlanActuals('daily_report_25_26', query)
  requests[0].resolve({ ok: true, ...requests[0].params, company: 'BeiHai' })
  await nextTick()
  assert.equal(view.data.value, null)
  assert.match(view.error.value, /不一致/)
  query.value = { ...query.value, item: 'amount_heat_supply' }
  h.cleanup.forEach(fn => fn())
  assert.equal(requests[1].signal.aborted, true)
  requests[1].resolve({ ok: true, ...requests[1].params })
  await nextTick()
  assert.equal(view.data.value, null)
})

test('柱形只取所选指标实际，日期对齐，保留零与空值，兼容闰年', () => {
  const h = helpers()
  const dates = h.monthDates('2028-02')
  assert.equal(dates.length, 29)
  const series = h.actualBarSeries(metrics[2], dates, { values: { '2028-02-01': 0, '2028-02-02': 5 } }, '#abc')
  assert.deepEqual(series.data.slice(0, 3), [0, 5, null])
  assert.equal(series.type, 'bar')
  assert.equal(series.yAxisIndex, 0)
})

test('真实图表月走势叠加实际柱形，柱状页并列对比；缺气温时保留日实际', async () => {
  const view = page()
  view.metricsList.value = [{ ...metrics[2], values: { '2026-11': 100, '2026-12': 200 } }]
  view.selectedMetricKeys.value = ['consumption_std_coal']
  view.chartSelectedMetricKeys.value = ['consumption_std_coal']
  view.displayedMonths.value = ['2026-11', '2026-12']
  view.showActualValues.value = true
  view.actualData.value = { latest_published_date: '2026-11-03', values: { '2026-11': 20 } }
  view.chartContainerRef.value = {}
  view.renderChart()
  let chart = view.options.at(-1)
  assert.deepEqual(chart.series.map(series => series.type), ['line', 'bar'])
  assert.deepEqual(chart.series[1].data, [20, null])
  assert.match(chart.series[0].name, /计划/)
  view.activeChartTab.value = 'dynamic_bar'
  view.renderChart()
  chart = view.options.at(-1)
  assert.deepEqual(chart.series.map(series => series.type), ['bar', 'bar'])
  assert.equal(chart.series[0].stack, undefined)
  assert.equal(chart.series[1].stack, undefined)
  view.isDynamicDecomposeEnabled.value = true
  view.actualData.value = { latest_published_date: '2026-11-03', values: { '2026-11-01': 0, '2026-11-02': 5 } }
  view.renderChart()
  chart = view.options.at(-1)
  assert.equal(chart.xAxis.data.length, 30)
  assert.match(chart.series[0].name, /·测算/)
  assert.doesNotMatch(chart.series[0].name, /计划/)
  assert.deepEqual(chart.series[1].data.slice(0, 3), [0, 5, null])
  assert.ok(chart.series[0].data.every(value => value === null))
  assert.doesNotMatch(chart.tooltip.formatter([{ dataIndex: 0, seriesName: chart.series[1].name, value: 0, color: '#abc' }]), /无k|undefined/)
  await nextTick()
})

test('逐日支持历史月份，累计仅限发布月份；互斥及单选规则保持生效', async () => {
  const view = page()
  view.metricsList.value = metrics
  view.selectedMetricKeys.value = metrics.map(metric => metric.item)
  view.chartSelectedMetricKeys.value = metrics.map(metric => metric.item)
  view.isDynamicDecomposeEnabled.value = true
  assert.equal(view.canShowDynamicActuals.value, true)
  view.showActualValues.value = true
  assert.equal(view.chartSelectedMetricKeys.value.length, 1)
  view.showCumulativeActual.value = true
  assert.equal(view.showActualValues.value, false)
  view.selectAllChartMetrics()
  assert.equal(view.chartSelectedMetricKeys.value.length, 3)
  assert.equal(view.cumulativeQuery.value.metrics.length, 3)
  view.showActualValues.value = true
  assert.equal(view.showCumulativeActual.value, false)
  assert.equal(view.chartSelectedMetricKeys.value.length, 1)
  view.dynamicTargetMonth.value = '2026-12'
  assert.equal(view.canShowDynamicActuals.value, false)
  assert.equal(view.showActualValues.value, true)
  view.showCumulativeActual.value = true
  assert.equal(view.showCumulativeActual.value, false)
  assert.equal(view.cumulativeQuery.value, null)
  view.showActualValues.value = true
  assert.equal(view.showActualValues.value, true)
  assert.equal(view.actualQuery.value.start_month, '2026-12')
  view.dynamicTargetMonth.value = '2026-10'
  assert.equal(view.showActualValues.value, true)
  assert.equal(view.actualQuery.value.start_month, '2026-10')
  view.dynamicTargetMonth.value = '2026-11'
  view.showCumulativeActual.value = true
  view.latestPublishedDate.value = null
  assert.equal(view.showCumulativeActual.value, false)
  await nextTick()
})

test('累计柱形按指标成对、按单位分轴，测算仅加总月初至发布日的逐日值', async () => {
  const view = page()
  const h = helpers()
  const dates = h.monthDates('2026-11')
  const plans = [
    { ...metrics[2], daily_plans: dates.map((_, index) => index < 3 ? index + 1 : 1000) },
    { ...metrics[0], daily_plans: dates.map(() => 10) },
  ]
  view.metricsList.value = metrics
  view.selectedMetricKeys.value = metrics.map(metric => metric.item)
  view.chartSelectedMetricKeys.value = plans.map(metric => metric.item)
  view.isDynamicDecomposeEnabled.value = true
  view.dynamicDecompData.value = { has_full_month: true, dates, metrics: plans }
  view.showCumulativeActual.value = true
  view.cumulativeData.value = { latest_published_date: '2026-11-03', metrics: {
    consumption_std_coal: { values: { '2026-11': 5 } }, amount_heat_supply: { values: { '2026-11': 29 } },
  } }
  view.chartContainerRef.value = {}
  view.renderChart()
  const chart = view.options.at(-1)
  assert.deepEqual(chart.xAxis[0].data, ['标煤耗量', '供热量'])
  assert.deepEqual(chart.yAxis.map(axis => axis.name), ['GJ', '吨'])
  assert.deepEqual(chart.series.map(series => series.data), [[null, 29], [null, 30], [5, null], [6, null]])
  assert.deepEqual(chart.legend.data, ['累计实际', '累计测算值'])
  assert.deepEqual(chart.series.map(series => [series.name, series.itemStyle.color]), [
    ['累计实际', '#2563eb'], ['累计测算值', '#f97316'],
    ['累计实际', '#2563eb'], ['累计测算值', '#f97316'],
  ])
  assert.ok(chart.series.every(series => series.type === 'bar' && series.stack === undefined))
  assert.equal(chart.series[2].xAxisIndex, chart.series[3].xAxisIndex)
  assert.equal(chart.series[2].yAxisIndex, chart.series[3].yAxisIndex)
  const rendered = echarts.init(null, null, { renderer: 'svg', ssr: true, width: 1000, height: 400 })
  try {
    rendered.setOption(chart)
    const svg = rendered.renderToSVGString()
    assert.match(svg, /标煤耗量/)
    assert.match(svg, /累计实际/)
  } finally { rendered.dispose() }
  await nextTick()
})

test('计划单耗累加，比率按分子分母重算，缺日值和零分母保持空值', () => {
  const h = helpers()
  const dates = h.monthDates('2026-11')
  const entry = (item, value) => ({ item, daily_plans: dates.map(() => value) })
  const rate = { ...entry('rate_heat_per_10k_m2', 2), is_ratio: true, is_rate: true }
  assert.equal(h.aggregateDecomposedPlan(rate, dates, '2026-11-03', []), 6)
  rate.daily_plans[1] = null
  assert.equal(h.aggregateDecomposedPlan(rate, dates, '2026-11-03', []), null)
  const efficiency = { ...entry('rate_overall_efficiency', 999), unit: '%' }
  const all = [entry('amount_heat_supply', 100), entry('amount_power_sales', 2),
    entry('consumption_outer_purchased_heat', 10), entry('consumption_std_coal', 8)]
  assert.equal(h.aggregateDecomposedPlan(efficiency, dates, '2026-11-03', all), (300 + 36 * 6 - 30) / (29.308 * 24) * 100)
  all.at(-1).daily_plans.fill(0)
  assert.equal(h.aggregateDecomposedPlan(efficiency, dates, '2026-11-03', all), null)
  assert.equal(h.aggregateDecomposedPlan(efficiency, dates, '2026-12-03', all), null)
})

test('批量累计查询只接收当前指标集合，切换取消旧请求并拦截乱序返回', async () => {
  const requests = []
  const h = helpers(() => assert.fail('累计模式不应逐指标发送每日查询'),
    (project, params, signal) => new Promise(resolve => requests.push({ params, signal, resolve })))
  const query = ref({ company: 'Group', year_month: '2026-11', metrics: [{ item: 'consumption_std_coal', unit: '吨' }] })
  const view = h.useDynamicPlanActuals('daily_report_25_26', query)
  query.value = { ...query.value, metrics: [{ item: 'amount_heat_supply', unit: 'GJ' }] }
  assert.equal(requests[0].signal.aborted, true)
  requests[1].resolve({ ok: true, available: true, company: 'Group', year_month: '2026-11',
    metrics: { amount_heat_supply: { unit: 'GJ', values: { '2026-11': 30 } } } })
  await nextTick()
  assert.equal(view.data.value.metrics.amount_heat_supply.values['2026-11'], 30)
  requests[0].resolve({ ok: true, available: false, company: 'Group', year_month: '2026-11', metrics: {} })
  await nextTick()
  assert.equal(view.data.value.metrics.amount_heat_supply.values['2026-11'], 30)
  h.cleanup.forEach(fn => fn())
})

const tableTemplate = source.match(/<table class="decomp-matrix-table">[\s\S]*?<\/table>/)[0]
const tableRender = new Function('Vue', compile(tableTemplate, { mode: 'function', prefixIdentifiers: true }).code)(Vue)
const renderDetailTable = view => renderToString(Vue.createSSRApp({ setup: () => view, render: tableRender }))
const tableRows = html => [...html.matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr>/g)].map(row =>
  [...row[1].matchAll(/<td\b[^>]*>([\s\S]*?)<\/td>/g)].map(cell => cell[1].replace(/<[^>]*>/g, '').trim()))

test('逐日明细真实渲染测算及实际列：零值保留，未发布留空，汇总只含已发布日期', async () => {
  const view = page()
  const dates = helpers().monthDates('2026-11')
  const metric = { ...metrics[2], month_plan: 60, daily_plans: dates.map(() => 2) }
  view.metricsList.value = [metric]
  view.selectedMetricKeys.value = [metric.item]
  view.chartSelectedMetricKeys.value = [metric.item]
  view.isDynamicDecomposeEnabled.value = true
  view.showActualValues.value = true
  view.dynamicDecompData.value = { has_full_month: true, metrics: [metric], dates,
    day_labels: dates.map(day => day.slice(5)), temperatures: dates.map(() => 10), hdd20_series: dates.map(() => 10) }
  view.actualData.value = { company: 'Group', item: metric.item, unit: metric.unit, granularity: 'day',
    latest_published_date: '2026-11-02', values: { '2026-11-01': 0, '2026-11-02': 5, '2026-11-03': 999 } }
  const html = await renderDetailTable(view)
  assert.match(html, /标煤耗量·测算/)
  assert.doesNotMatch(html, /标煤耗量·计划/)
  assert.match(html, /月度计划值/)
  assert.match(html, /标煤耗量·实际完成/)
  const rows = tableRows(html)
  assert.deepEqual(rows[1].slice(-2), ['2', '0'])
  assert.deepEqual(rows[2].slice(-2), ['2', '5'])
  assert.deepEqual(rows[3].slice(-2), ['2', '—'])
  assert.equal(view.getDailyDetailActualTotal(metric), 5)
  view.actualData.value.values['2026-11-02'] = null
  assert.equal(view.getDailyDetailActualTotal(metric), null)
  assert.equal(view.getDailyDetailActual(metrics[0], '2026-11-01'), null)
  view.showActualValues.value = false
  const withoutActual = await renderDetailTable(view)
  assert.doesNotMatch(withoutActual, /·实际完成/)
  assert.match(withoutActual, /标煤耗量·测算/)
  await nextTick()
})

test('历史月明细可显示整月实际，气温不完整仍展示实际，切换月份不带入旧值', async () => {
  const view = page()
  const dates = helpers().monthDates('2026-11')
  const metric = metrics[2]
  view.metricsList.value = [metric]
  view.selectedMetricKeys.value = [metric.item]
  view.chartSelectedMetricKeys.value = [metric.item]
  view.isDynamicDecomposeEnabled.value = true
  view.latestPublishedDate.value = '2026-12-03'
  view.showActualValues.value = true
  view.actualData.value = { company: 'Group', item: metric.item, unit: metric.unit, granularity: 'day',
    latest_published_date: '2026-12-03', values: Object.fromEntries(dates.map(day => [day, 1])) }
  assert.equal(view.canShowDynamicActuals.value, false)
  assert.equal(view.actualQuery.value.start_month, '2026-11')
  assert.equal(view.getDailyDetailActual(metric, '2026-11-30'), 1)
  assert.equal(view.getDailyDetailActualTotal(metric), 30)
  const rows = tableRows(await renderDetailTable(view))
  assert.deepEqual(rows[1].slice(-2), ['—', '1'])
  assert.deepEqual(rows[30].slice(-2), ['—', '1'])
  view.dynamicTargetMonth.value = '2026-10'
  assert.equal(view.showActualValues.value, true)
  assert.equal(view.getDailyDetailActual(metric, '2026-11-30'), null)
  assert.equal(view.getDailyDetailActualTotal(metric), null)
  await nextTick()
})
