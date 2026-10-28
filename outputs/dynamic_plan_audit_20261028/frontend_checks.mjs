// 对页面原函数进行内存隔离复现，不登录、不提交表单、不修改业务数据。
import fs from 'node:fs/promises'
import vm from 'node:vm'

const root = 'D:/编程项目/phoenix'
const source = await fs.readFile(`${root}/frontend/src/projects/daily_report_25_26/pages/DynamicPlanMetricsView.vue`, 'utf8')
const checks = []
const loaderSource = source.slice(source.indexOf('async function loadDynamicDecompositionData()'), source.indexOf('\nfunction handleDynamicDecomposeToggle()'))
const pending = []
const state = {
  isDynamicDecomposeEnabled: { value: true },
  dynamicDecompLoading: { value: false },
  dynamicDecompError: { value: '' },
  dynamicDecompData: { value: null },
  currentCompany: { value: 'Group' },
  dynamicTargetMonth: { value: '2026-11' },
  projectKey: 'daily_report_25_26',
  fetchDynamicDailyDecomposition: (args) => new Promise((resolve, reject) => pending.push({ args, resolve, reject })),
  nextTick: async () => {},
  renderChart: () => {},
}
vm.createContext(state)
vm.runInContext(loaderSource, state)
const oldRequest = state.loadDynamicDecompositionData()
state.currentCompany.value = 'BeiHai'
const newRequest = state.loadDynamicDecompositionData()
pending[1].resolve({ company: 'BeiHai', has_full_month: true })
await newRequest
pending[0].resolve({ company: 'Group', has_full_month: true })
await oldRequest
checks.push({ check: 'request_race', selected: state.currentCompany.value, displayed: state.dynamicDecompData.value.company })
state.currentCompany.value = 'JinPu'
const failedRequest = state.loadDynamicDecompositionData()
pending[2].reject(new Error('模拟网络失败'))
await failedRequest
checks.push({ check: 'failure_retains_old_data', selected: state.currentCompany.value, displayed: state.dynamicDecompData.value.company, has_full_month: state.dynamicDecompData.value.has_full_month, error: state.dynamicDecompError.value })

const renderSource = source.slice(source.indexOf('function renderDynamicDecomposeChart()'), source.indexOf('\n// -------------------------------------------------------------\n// ECharts 图表渲染引擎'))
let option
const graphState = {
  echarts: { graphic: { LinearGradient: function () {} } },
  chartContainerRef: { value: {} },
  chartInstance: { setOption: (value) => { option = value }, resize: () => {} },
  dynamicDecompData: { value: { has_full_month: true, day_labels: ['11-01'], dates: ['2026-11-01'], temperatures: [10], hdd20_series: [10] } },
  activeDecompositionMetrics: { value: [
    { item: 'heat', item_cn: '供热量', unit: 'GJ', daily_plans: [1000] },
    { item: 'coal', item_cn: '标煤耗量', unit: '吨', daily_plans: [50] },
    { item: 'power', item_cn: '发电量', unit: '万kWh', daily_plans: [10] },
  ] },
  focusedMetricKey: { value: '' },
  showDecompTemperature: { value: true },
  getMetricColor: () => '#000',
  formatAxisNum: (value) => value,
}
vm.createContext(graphState)
vm.runInContext(renderSource, graphState)
graphState.renderDynamicDecomposeChart()
checks.push({ check: 'default_three_unit_axes', series: option.series.map((s) => ({ name: s.name, axis: option.yAxis[s.yAxisIndex].name })) })

await fs.writeFile(`${root}/outputs/dynamic_plan_audit_20261028/frontend_results.json`, JSON.stringify(checks, null, 2), 'utf8')
console.log(JSON.stringify(checks, null, 2))
