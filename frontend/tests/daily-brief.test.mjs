import test from 'node:test'
import assert from 'node:assert/strict'
import { canAccessDailyBrief, withDailyBriefPage, formatBriefNumber, changeText, briefDeltaClass, briefComparisonParts, selectBriefMetricPanels } from '../src/projects/daily_report_25_26/composables/dailyBriefPresentation.js'

test('仅本子项目的 Global_admin 能看到入口', () => {
  assert.equal(canAccessDailyBrief('daily_report_25_26', { group: 'Global_admin' }), true)
  for (const user of [null, { group: 'admin' }, { group: 'unit_admin' }, { group: 'global_admin' }]) {
    assert.equal(canAccessDailyBrief('daily_report_25_26', user), false)
  }
  assert.equal(canAccessDailyBrief('other', { group: 'Global_admin' }), false)
})

test('入口不依赖种子修改、不重复、不泄露给其他角色', () => {
  const pages = [{ page_key: 'dashboard' }, { page_key: 'daily_brief' }]
  const result = withDailyBriefPage(pages, 'daily_report_25_26', { group: 'Global_admin' })
  assert.equal(result[0].page_name, '每日简报')
  assert.equal(result.filter(page => page.page_key === 'daily_brief').length, 1)
  assert.deepEqual(withDailyBriefPage(pages, 'daily_report_25_26', { group: 'unit_admin' }), [{ page_key: 'dashboard' }])
  assert.equal(pages.length, 2)
})

test('空值及非有限值不能被格式化为零', () => {
  for (const value of [null, undefined, '', NaN, Infinity]) assert.equal(formatBriefNumber(value), '—')
  assert.equal(formatBriefNumber(0), '0.00')
  assert.equal(formatBriefNumber(1234.567, 2), '1,234.57')
})

test('同比描述使用事实用语，负基数不拼接百分比', () => {
  const metric = { digits: 2, unit: '万元', comparison: { delta: 2, percent: null, direction: 'up' } }
  assert.equal(changeText(metric), '同比增加 2.00 万元')
  assert.equal(changeText({ ...metric, comparison: { delta: null } }), '同比 —')
  assert.equal(changeText({ ...metric, comparison: { delta: 0, direction: 'flat' } }), '同比持平')
})

test('同一句的同比增加、连续高于和日间减少分别着色', () => {
  const text = '标煤耗量1,648.31吨，同比增加38.29吨（2.4%），已连续5日高于同期，较前日连续3日减少。'
  const parts = briefComparisonParts(text)
  assert.equal(parts.map(part => part.text).join(''), text)
  assert.deepEqual(parts.filter(part => part.className).map(part => part.className), ['change-up', 'change-up', 'change-down'])
  assert.equal(parts[0].className, '')
})

test('同比减少与低于同期为绿色，持平和显示为零的差额为黑色', () => {
  const parts = briefComparisonParts('同比减少29件（44.6%），已连续3日低于同期；同比持平；较昨日增加 0.00 元/MWh。')
  assert.deepEqual(parts.filter(part => part.className).map(part => part.className), ['change-down', 'change-down', 'change-flat', 'change-flat'])
  assert.equal(briefDeltaClass(1), 'change-up')
  assert.equal(briefDeltaClass(-1), 'change-down')
  assert.equal(briefDeltaClass(-0.001), 'change-flat')
  assert.equal(briefDeltaClass(null), '')
})

test('库存量、负电价与调度操作不当成增减量着色', () => {
  for (const text of ['港口库存：5,594.54 吨', '实时价格范围 -100.00—574.65 元/MWh', '08:00 1号炉启动']) {
    assert.equal(briefComparisonParts(text).some(part => part.className), false)
  }
})

test('主版六项与专刊八项按键选取，不受接口顺序影响', () => {
  const primary = ['eco_comparable_marginal_profit', 'amount_power_generation', 'consumption_std_coal',
    'rate_heat_per_10k_m2', 'amount_daily_service_complaints', 'amount_daily_net_complaints']
  const supplement = ['eco_marginal_profit', 'amount_heat_supply', 'amount_hot_water_sales', 'amount_steam_sales',
    'amount_power_sales', 'amount_daily_net_complaints_per_10k_m2', 'rate_water_per_10k_m2', 'rate_power_per_10k_m2']
  const data = [...primary, ...supplement, 'rate_std_coal_per_heat', 'consumption_station_heat']
    .reverse().map((key, index) => ({ key, value: index + 1, unit: `单位${index}` }))
  const panels = selectBriefMetricPanels(data)
  assert.deepEqual(panels.primary.map(metric => metric.key), primary)
  assert.deepEqual(panels.supplement.map(metric => metric.key), supplement)
  assert.equal(panels.primary[1], data.find(metric => metric.key === 'amount_power_generation'))
  assert.equal(panels.primary[3], data.find(metric => metric.key === 'rate_heat_per_10k_m2'))
  assert.equal(data.length, 16)
})

test('缺少指标不借用其他指标值或退回按位置切片', () => {
  const panels = selectBriefMetricPanels([{ key: 'consumption_station_heat', value: 123 }, { key: 'amount_heat_supply', value: 456 }])
  assert.deepEqual(panels.primary, [])
  assert.deepEqual(panels.supplement.map(metric => metric.key), ['amount_heat_supply'])
  assert.deepEqual(selectBriefMetricPanels(null), { primary: [], supplement: [] })
})
