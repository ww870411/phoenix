import { onBeforeUnmount, ref, watch } from 'vue'
import { fetchDynamicPlanActuals, fetchDynamicPlanCumulativeActuals } from '../services/api'

// 查询描述包含模式、单位、指标、月份及单位；变化时立即清空旧数据并取消旧请求。
export function useDynamicPlanActuals(projectKey, query) {
  const data = ref(null)
  const loading = ref(false)
  const error = ref('')
  let controller
  let requestId = 0
  watch(query, async (params) => {
    const id = ++requestId
    controller?.abort()
    data.value = null
    error.value = ''
    loading.value = false
    if (!params) return
    controller = new AbortController()
    loading.value = true
    try {
      const isBatch = Array.isArray(params.metrics)
      const result = await (isBatch ? fetchDynamicPlanCumulativeActuals : fetchDynamicPlanActuals)(projectKey, params, controller.signal)
      if (id !== requestId) return
      const matches = isBatch
        ? result.year_month === params.year_month && (result.available === false || params.metrics.every(metric => result.metrics?.[metric.item]?.unit === metric.unit))
        : result.item === params.item && result.granularity === params.granularity && result.unit === params.unit
      if (!result.ok || result.company !== params.company || !matches) {
        throw new Error('实际数据响应与当前选择不一致')
      }
      data.value = result
    } catch (err) {
      if (id === requestId && err.name !== 'AbortError') error.value = err.message || '实际值读取失败'
    } finally {
      if (id === requestId) loading.value = false
    }
  }, { immediate: true, flush: 'sync' })
  onBeforeUnmount(() => {
    ++requestId
    controller?.abort()
  })
  return { data, loading, error }
}

export function singleMetricSelection(keys, preferred = '') {
  return keys.includes(preferred) ? [preferred] : keys.slice(0, 1)
}

export function monthDates(month) {
  const [year, monthNumber] = month.split('-').map(Number)
  return Array.from({ length: new Date(year, monthNumber, 0).getDate() },
    (_, index) => `${month}-${String(index + 1).padStart(2, '0')}`)
}

export function actualBarSeries(metric, keys, actuals, color, axisIndex = 0) {
  return {
    name: `${metric.item_cn}·实际 (${metric.unit || '—'})`,
    type: 'bar', yAxisIndex: axisIndex, barMaxWidth: 28, z: 1,
    data: keys.map((key) => actuals?.values?.[key] ?? null),
    itemStyle: { color, opacity: 0.5, borderRadius: [3, 3, 0, 0] },
  }
}

export function aggregateDecomposedPlan(metric, dates, cutoff, allMetrics) {
  // 按已生成的日分解值截取，同一指标的单耗按固定供暖面积口径累计。
  if (!cutoff || !dates?.length || dates[0].slice(0, 7) !== cutoff.slice(0, 7)) return null
  const indices = dates.flatMap((day, index) => day <= cutoff ? [index] : [])
  if (indices.length !== Number(cutoff.slice(8, 10))) return null
  const sum = (entry) => {
    const values = indices.map(index => entry?.daily_plans?.[index])
    return values.every(value => typeof value === 'number' && Number.isFinite(value))
      ? values.reduce((total, value) => total + value, 0) : null
  }
  if (metric.item === 'rate_overall_efficiency') {
    const value = item => sum(allMetrics.find(entry => entry.item === item))
    const heat = value('amount_heat_supply'), power = value('amount_power_sales')
    const purchasedHeat = value('consumption_outer_purchased_heat'), coal = value('consumption_std_coal')
    return [heat, power, purchasedHeat, coal].every(value => value != null) && coal !== 0
      ? (heat + 36 * power - purchasedHeat) / (29.308 * coal) * 100 : null
  }
  // 当前计划的比率标记用于单耗；未知非累加比率不冒充累计合计。
  if ((metric.unit === '%' || metric.is_ratio) && !metric.is_rate && !metric.item_cn?.includes('单耗')) return null
  return sum(metric)
}
