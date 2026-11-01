import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { ref, computed, reactive } from 'vue'

const source = readFileSync(new URL('../src/projects/daily_report_25_26/components/MonthlyCoalProgressCard.vue', import.meta.url), 'utf8')
const script = source.match(/<script setup>([\s\S]*?)<\/script>/)[1].replace(/import[^\n]+\n/g, '')
function setup() {
  const props = reactive({ projectKey: 'daily_report_25_26', bizDate: '2026-11-01' }), requests = [], loadingEvents = [], cleanup = []
  const deps = { ref, computed, watch() {}, defineProps: () => props, defineEmits: () => (name, value) => loadingEvents.push(value), onBeforeUnmount: fn => cleanup.push(fn),
    fetchMonthlyCoalProgress: (project, date, signal) => new Promise((resolve, reject) => requests.push({ project, date, signal, resolve, reject })) }
  const view = new Function('deps', `const {${Object.keys(deps).join(',')}}=deps;${script};return {load,data,error,loading,number,statusLabel,displayRows,scopeLabel};`)(deps)
  return { view, props, requests, loadingEvents, cleanup }
}

test('切换业务日期立即清空旧数据，过期请求不覆盖当前月', async () => {
  const { view, props, requests, loadingEvents } = setup()
  const old = view.load()
  props.bizDate = '2026-12-01'
  const latest = view.load()
  assert.equal(requests[0].signal.aborted, true)
  assert.equal(view.data.value, null)
  requests[1].resolve({ ok: true, biz_date: '2026-12-01', items: [] })
  await latest
  requests[0].resolve({ ok: true, biz_date: '2026-11-01', items: [] })
  await old
  assert.equal(view.data.value.biz_date, '2026-12-01')
  assert.equal(loadingEvents.at(-1), false)
})

test('错误响应或日期不一致显式报错，不留下上次的计划', async () => {
  const { view, requests } = setup()
  const pending = view.load()
  requests[0].resolve({ ok: true, biz_date: '2026-10-01', items: [] })
  await pending
  assert.equal(view.data.value, null)
  assert.match(view.error.value, /响应异常/)
  assert.equal(view.loading.value, false)
})

test('数字0和缺数区分，缺计划及实际不完整有独立提示', () => {
  const { view } = setup()
  assert.equal(view.number(0), '0')
  assert.equal(view.number(null), '—')
  assert.equal(view.number(1234.567), '1,235')
  assert.equal(view.statusLabel('zero_plan'), '计划为0')
  assert.equal(view.statusLabel('incomplete_actual'), '实际数据不完整')
})

test('组件退出取消请求，释放整页导出等待状态', async () => {
  const { view, requests, cleanup, loadingEvents } = setup()
  const pending = view.load()
  cleanup[0]()
  assert.equal(requests[0].signal.aborted, true)
  requests[0].resolve({ ok: true, biz_date: '2026-11-01', items: [] })
  await pending
  assert.equal(view.data.value, null)
  assert.equal(loadingEvents.at(-1), false)
})

test('当日与本月累计共用月累计比例，供暖期切至全期比例，主体按代号匹配', () => {
  const { view, props } = setup()
  props.comparisonRows = [['集团汇总', 5, 4, 1], ['北海热电厂', 3, 2, 1], ['未知主体', 2, 1, 1]]
  view.data.value = {
    items: [{ company: 'BeiHai', actual_value: 20, plan_value: 100, completion_percent: 20 }, { company: 'Group', actual_value: 30, plan_value: 100, completion_percent: 30 }],
    season: { period: '26-27', items: [{ company: 'Group', actual_value: 60, plan_value: 1000, completion_percent: 6 }] },
  }
  props.phase = 'daily'
  assert.equal(view.displayRows.value[0].completion_percent, 30)
  assert.deepEqual(view.displayRows.value[0].comparison, [5, 4, 1])
  assert.equal(view.displayRows.value[1].completion_percent, 20)
  assert.equal(view.displayRows.value[2].status, 'missing_plan')
  props.phase = 'monthly'
  assert.equal(view.displayRows.value[0].completion_percent, 30)
  props.phase = 'seasonal'
  assert.equal(view.displayRows.value[0].completion_percent, 6)
  assert.equal(view.scopeLabel.value, '26-27供暖期')
})
