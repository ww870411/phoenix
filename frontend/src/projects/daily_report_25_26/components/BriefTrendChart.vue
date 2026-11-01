<template>
  <div ref="chartEl" class="brief-trend-chart" role="img" :aria-label="`${metric.label}近七日及同期趋势，详细数值见下方逐日数据`"></div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])
const props = defineProps({ metric: { type: Object, required: true } })
const chartEl = ref(null)
let chart, observer
function render() {
  if (!chart) return
  chart.setOption({
    animation: false,
    color: ['#175d72', '#a3aebd'],
    tooltip: { trigger: 'axis', confine: true },
    legend: { top: 0, left: 0, textStyle: { fontSize: 11 }, data: ['本期', '同期'] },
    grid: { top: 38, left: 6, right: 12, bottom: 6, containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: props.metric.points.map(p => p.date.slice(5)), axisLabel: { fontSize: 10, interval: 1 } },
    yAxis: { type: 'value', scale: true, splitNumber: 3, axisLabel: { fontSize: 10 } },
    series: [
      { name: '本期', type: 'line', data: props.metric.points.map(p => p.value), connectNulls: false, symbolSize: 5, lineStyle: { width: 2.5 } },
      { name: '同期', type: 'line', data: props.metric.points.map(p => p.peer), connectNulls: false, symbolSize: 4, lineStyle: { type: 'dashed', width: 2 } },
    ],
  }, true)
}
onMounted(() => {
  chart = echarts.init(chartEl.value)
  render()
  observer = new ResizeObserver(() => chart?.resize())
  observer.observe(chartEl.value)
})
watch(() => props.metric, render)
onBeforeUnmount(() => { observer?.disconnect(); chart?.dispose(); chart = null })
</script>

<style scoped>
.brief-trend-chart { height: 190px; width: 100%; min-width: 0; }
</style>
