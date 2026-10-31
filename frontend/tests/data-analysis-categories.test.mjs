import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { classifyAnalysisMetrics, isMetricCategorySelected, toggleMetricCategory } from '../src/projects/daily_report_25_26/constants/analysisMetricCategories.js'

const config = JSON.parse(readFileSync(new URL('../../backend_data/projects/daily_report_25_26/config/数据结构_数据分析表.json', import.meta.url), 'utf8')).data_analysis_page.指标选择
const groups = [['primary', '主要指标字典'], ['adjustment', '调整指标字典'], ['constant', '常量指标字典'], ['temperature', '气温指标字典']].map(([key, name]) => ({
  key, label: name, options: Object.entries(config[name]).map(([value, label]) => ({ value, label })),
}))
const classified = classifyAnalysisMetrics(groups)

test('实际日报配置的每个指标恰好归入一个业务子类，编码和名称均保留', () => {
  for (const [index, group] of classified.entries()) {
    const options = group.subgroups.flatMap(category => category.options)
    assert.equal(options.length, groups[index].options.length)
    assert.equal(new Set(options.map(option => option.value)).size, options.length)
    assert.deepEqual(options.toSorted((a, b) => a.value.localeCompare(b.value)), groups[index].options.toSorted((a, b) => a.value.localeCompare(b.value)))
    assert.ok(group.subgroups.every(category => category.key !== 'other'))
  }
})

test('产销、投诉、机炉运行、损耗与常量单价按业务区分', () => {
  const find = (group, key) => classified.find(g => g.key === group).subgroups.find(category => category.options.some(option => option.value === key)).label
  assert.equal(find('primary', 'amount_heat_supply'), '主要产销指标')
  assert.equal(find('primary', 'amount_daily_net_complaints'), '供热服务与投诉')
  assert.equal(find('primary', 'amount_turbine_running'), '设备运行与生产事件')
  assert.equal(find('primary', 'eco_heat_lose'), '站耗与热网损耗')
  assert.equal(find('constant', 'price_std_coal'), '能源与水热单价')
  assert.equal(find('constant', 'amount_heating_fee_area'), '供暖面积')
})

test('调整与气温保留原口径，不与名称相近的主要指标混合', () => {
  assert.equal(classified.find(g => g.key === 'adjustment').subgroups.length, 2)
  assert.equal(classified.find(g => g.key === 'temperature').subgroups[0].options.length, 3)
  assert.ok(classified.find(g => g.key === 'primary').subgroups.some(c => c.key === 'weather'))
})

test('部分选择时全选本类，全选后取消本类，不影响其他分类和已有顺序', () => {
  const options = classified[0].subgroups[0].options
  const selected = new Set(['amount_daily_net_complaints', options[0].value])
  assert.equal(isMetricCategorySelected(selected, options), false)
  const next = toggleMetricCategory(selected, options)
  assert.equal(isMetricCategorySelected(next, options), true)
  assert.deepEqual([...next].slice(0, 2), [...selected])
  assert.deepEqual([...toggleMetricCategory(next, options)], ['amount_daily_net_complaints'])
  assert.equal(selected.size, 2)
})

test('新增和未知来源指标仍可选，空分类不展示', () => {
  const result = classifyAnalysisMetrics([{ key: 'primary', label: '主要指标', options: [{ value: 'new_metric', label: '新指标' }] },
    { key: 'custom', label: '自定义指标', options: [{ value: 'custom_metric', label: '自定义' }] }])
  assert.equal(result[0].subgroups.length, 1)
  assert.equal(result[0].subgroups[0].label, '其他指标')
  assert.equal(result[1].subgroups[0].options[0].value, 'custom_metric')
  assert.equal(isMetricCategorySelected(new Set(), []), false)
})
