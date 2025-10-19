<template>
  <nav class="breadcrumbs" aria-label="Breadcrumb">
    <template v-for="(item, idx) in items" :key="idx">
      <a
        v-if="item.to && idx < items.length - 1"
        href="#"
        class="crumb-link"
        @click.prevent="go(item.to)"
      >
        {{ item.label }}
      </a>
      <span v-else class="current">{{ item.label }}</span>
      <span v-if="idx < items.length - 1" class="separator">»</span>
    </template>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ensureProjectsLoaded, getProjectNameById } from '../composables/useProjects'

const route = useRoute()
const router = useRouter()
ensureProjectsLoaded().catch(() => {})

const items = computed(() => {
  const name = route.name
  const p = route.params || {}
  const q = route.query || {}
  const projectKey = p.projectKey
  const sheetKey = p.sheetKey
  const biz = q.biz_date
  const projectLabel = getProjectNameById(projectKey)

  // 基于路由名与参数构造面包屑
  // login 页不显示面包屑
  if (name === 'projects') {
    return [
      { label: '项目', to: null },
    ]
  }
  if (name === 'dashboard') {
    return [
      { label: '项目', to: '/projects' },
      { label: String(projectLabel || ''), to: null },
    ]
  }
  if (name === 'data-entry') {
    return [
      { label: '项目', to: '/projects' },
      {
        label: String(projectLabel || ''),
        to: projectKey ? `/projects/${encodeURIComponent(projectKey)}/sheets` : null,
      },
      { label: '数据填报', to: null },
    ]
  }
  // 其他兜底：不显示或仅显示当前
  return [ { label: '导航', to: null } ]
})

function go(path) {
  router.push(path)
}
</script>

<style scoped>
.breadcrumbs {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  margin: 6px 0 18px 0;
  font-size: 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  color: var(--muted);
}
.crumb-link {
  color: var(--primary-700);
  text-decoration: none;
  padding: 4px 8px;
  border-radius: 999px;
  transition: all 0.18s ease-in-out;
}
.crumb-link:hover {
  background: rgba(59, 130, 246, 0.12);
  color: var(--primary-800);
}
.separator {
  color: #cbd5e1;
  font-size: 18px;
  font-weight: 600;
  user-select: none;
}
.current {
  color: var(--text);
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.05);
}
</style>
