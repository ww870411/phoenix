<template>
  <article class="metric-card">
    <div class="metric-top"><h4>{{ metric.label }}</h4><span v-if="metric.trend.yoy_run >= 3" class="continuity">连续 {{ metric.trend.yoy_run }} 日</span></div>
    <div class="metric-value">{{ fmt(metric.value, metric.digits) }} <span>{{ metric.unit }}</span></div>
    <p class="metric-change"><BriefComparisonText :text="changeText(metric)" /></p>
    <p v-if="metric.trend.text" class="metric-trend"><BriefComparisonText :text="metric.trend.text" /></p>
    <details @toggle="opened = $event.target.open">
      <summary>比较依据与趋势 <span>展开</span></summary>
      <div class="metric-evidence">
        <p>同期值：{{ fmt(metric.peer, metric.digits) }} {{ metric.unit }}</p>
        <p><BriefComparisonText :text="metric.description" /></p>
        <p>近七日日均：本期 {{ fmt(metric.trend.current_average, metric.digits) }}，同期 {{ fmt(metric.trend.peer_average, metric.digits) }} {{ metric.unit }}。</p>
        <BriefTrendChart v-if="opened" :metric="metric" />
        <details class="daily-values"><summary>逐日数据</summary>
          <div v-for="point in metric.points" :key="point.date" class="daily-row">
            <span>{{ point.date }}<small>同期 {{ point.peer_date }}</small></span>
            <span>本期 {{ fmt(point.value, metric.digits) }}<small>同期 {{ fmt(point.peer, metric.digits) }}</small></span>
          </div>
        </details>
      </div>
    </details>
  </article>
</template>

<script setup>
import { defineAsyncComponent, ref } from 'vue'
import { formatBriefNumber as fmt, changeText } from '../composables/dailyBriefPresentation'
import BriefComparisonText from './BriefComparisonText.vue'
defineProps({ metric: { type: Object, required: true } })
const opened = ref(false)
// 首屏只读简报；用户展开趋势时才加载图表库。
const BriefTrendChart = defineAsyncComponent(() => import('./BriefTrendChart.vue'))
</script>

<style scoped>
.metric-card { padding: 12px 14px 0; border: 1px solid #e3e8ec; border-radius: 12px; background: #fff; min-width: 0; overflow-wrap: anywhere; }
.metric-top { display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
h4 { margin: 0; color: #344956; font-size: 14px; font-weight: 600; }
.continuity { font-size: 11px; color: #376875; background: #edf5f5; padding: 3px 7px; border-radius: 5px; }
.metric-value { margin: 6px 0; color: #152f3d; font-size: clamp(25px, 6vw, 30px); font-weight: 650; font-variant-numeric: tabular-nums; line-height: 1.2; }
.metric-value span { font-size: 12px; color: #71808b; font-weight: 400; }
p { line-height: 1.6; margin: 6px 0; font-size: 13px; }
.metric-change { color: #344e5c; }
.metric-trend { color: #74828d; font-size: 12px; margin-bottom: 8px; }
summary { cursor: pointer; min-height: 44px; align-content: center; color: #486673; font-size: 12px; }
.metric-card > details > summary { border-top: 1px solid #edf0f2; }
summary span { float: right; color: #89969e; }
details[open] > summary > span { display: none; }
.metric-evidence { padding-bottom: 10px; color: #596c78; }
.daily-row { display: flex; justify-content: space-between; gap: 12px; padding: 8px 0; border-top: 1px solid #edf0f2; font-size: 12px; }
.daily-row > span:last-child { text-align: right; font-variant-numeric: tabular-nums; }
small { display: block; margin-top: 4px; color: #89939c; font-size: 10px; }
@media (max-width: 420px) { .metric-card { padding: 10px 12px 0; } }
</style>
