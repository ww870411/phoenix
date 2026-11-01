<template>
  <div class="subject-content">
    <div class="subject-metrics"><BriefMetricCard v-for="metric in subject.metrics.slice(0, 5)" :key="metric.key" :metric="metric" /></div>
    <details class="more-metrics"><summary>实际利润、供热量、售电量及单耗</summary>
      <div class="subject-metrics"><BriefMetricCard v-for="metric in subject.metrics.slice(5)" :key="metric.key" :metric="metric" /></div>
    </details>
  </div>
</template>

<script setup>
import BriefMetricCard from './BriefMetricCard.vue'
defineProps({ subject: { type: Object, required: true } })
</script>

<style scoped>
.subject-metrics { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.more-metrics { margin-top: 6px; }
summary { min-height: 44px; align-content: center; font-size: 13px; cursor: pointer; color: #486673; }
@media (max-width: 600px) { .subject-metrics { grid-template-columns: minmax(0, 1fr); } }
</style>
