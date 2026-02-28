<template>
  <component v-if="entryComponent" :is="entryComponent" />
  <div v-else class="entry-loading">正在进入项目工作台...</div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import SpringFestivalEntryView from '../projects/daily_report_spring_festval_2026/pages/SpringFestivalEntryView.vue'
import MonthlyDataPullEntryView from '../projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue'

const route = useRoute()
const router = useRouter()
const projectKey = computed(() => String(route.params.projectKey || ''))

const entryComponentMap = {
  daily_report_spring_festval_2026: SpringFestivalEntryView,
  monthly_data_pull: MonthlyDataPullEntryView,
}

const entryComponent = computed(() => entryComponentMap[projectKey.value] || null)

onMounted(() => {
  if (!entryComponent.value && projectKey.value) {
    router.replace(`/projects/${encodeURIComponent(projectKey.value)}/pages`)
  }
})
</script>

<style scoped>
.entry-loading {
  min-height: 40vh;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  font-size: 14px;
}
</style>

