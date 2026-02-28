<template>
  <div class="monthly-query-page">
    <AppHeader />
    <main class="monthly-query-main">
      <Breadcrumbs :items="breadcrumbItems" />
      <section class="card">
        <h2>月报数据查询工具</h2>
        <p class="sub">该页面用于月报入库后的查询与分析，下一阶段将按数据分析页样式接入筛选、图表与对比能力。</p>
      </section>
      <section class="card">
        <h3>规划中的能力</h3>
        <ul class="list">
          <li>按时间范围、口径、指标查询月报数据</li>
          <li>多月聚合与多口径聚合分析</li>
          <li>关键指标趋势图与同比/环比对比</li>
        </ul>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '月报导入与查询', to: '/projects/monthly_data_show/pages' },
  { label: '月报数据查询工具', to: null },
])
</script>

<style scoped>
.monthly-query-page {
  min-height: 100vh;
  background: #f8fafc;
}

.monthly-query-main {
  max-width: 1100px;
  margin: 0 auto;
  padding: 18px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px;
}

.sub {
  margin-top: 8px;
  color: #64748b;
  font-size: 13px;
}

.list {
  margin: 0;
  padding-left: 18px;
  color: #334155;
  font-size: 13px;
}
</style>
