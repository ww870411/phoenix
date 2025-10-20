<template>
  <div>
    <AppHeader />
    <div class="container">
      <header class="topbar">
        <div>
          <h2>项目选择</h2>
          <div class="sub">请选择要进入的项目空间</div>
        </div>
      </header>

      <div class="card-grid">
        <div v-if="loading" class="placeholder">项目列表加载中…</div>
        <div v-else-if="error" class="placeholder error">{{ error }}</div>
        <div v-else-if="projectList.length === 0" class="placeholder">暂无项目，请联系管理员配置。</div>
        <template v-else>
          <div
            class="card clickable elevated"
            v-for="project in projectList"
            :key="project.project_id"
            @click="enter(project)"
          >
            <div class="card-header">{{ project.project_name }}</div>
            <div class="name">{{ project.project_id }}</div>
            <div class="desc">点击进入项目工作台</div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import '../styles/theme.css'
import AppHeader from '../components/AppHeader.vue'
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  projects,
  projectsLoading,
  projectsError,
  ensureProjectsLoaded,
} from '../composables/useProjects'

const router = useRouter()

const projectList = computed(() => projects.value)
const loading = computed(() => projectsLoading.value)
const error = computed(() => (projectsError.value ? '无法加载项目列表，请稍后重试。' : ''))

function enter(project) {
  router.push(`/projects/${encodeURIComponent(project.project_id)}/data_entry/sheets`)
}

onMounted(() => {
  ensureProjectsLoaded().catch(() => {
    /* 错误信息已在 projectsError 中记录 */
  })
})
</script>

<style scoped>
.topbar { margin-bottom: 16px; }
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.name { font-size: 16px; font-weight: 600; margin-bottom: 6px; }
.desc { font-size: 13px; color: #666; }
.placeholder { padding: 32px; color: var(--muted); text-align: center; border: 1px dashed #e2e8f0; border-radius: 12px; }
.placeholder.error { color: var(--danger-600); border-color: var(--danger-200); }
</style>
