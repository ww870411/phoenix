<template>
  <div class="page-select-view">
    <AppHeader />
    <main class="page-select-main">
      <Breadcrumbs :items="breadcrumbItems" />
      <section class="card elevated page-block">
        <header class="card-header">
          <h2>请选择功能页面</h2>
          <p class="page-subtitle">项目：{{ projectName }}</p>
        </header>
        <div v-if="loading" class="page-state">页面加载中，请稍候…</div>
        <div v-else-if="errorMessage" class="page-state error">{{ errorMessage }}</div>
        <div v-else class="card-grid">
          <button
            v-for="page in pages"
            :key="page.page_key"
            type="button"
            class="card elevated page-card"
            @click="openPage(page)"
          >
            <div class="page-card-title">{{ page.page_name }}</div>
            <div class="page-card-desc">模板文件：{{ page.config_file }}</div>
          </button>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { listPages } from '../services/api'
import { ensureProjectsLoaded, getProjectNameById } from '../composables/useProjects'

const route = useRoute()
const router = useRouter()
const projectKey = String(route.params.projectKey ?? '')

const pages = ref([])
const loading = ref(false)
const errorMessage = ref('')

onMounted(async () => {
  loading.value = true
  try {
    await ensureProjectsLoaded()
    const response = await listPages(projectKey)
    pages.value = Array.isArray(response?.pages) ? response.pages : []
    if (!pages.value.length) {
      errorMessage.value = '未找到可选页面，请检查后端配置。'
    }
  } catch (err) {
    console.error(err)
    errorMessage.value = '读取页面列表失败，请稍后再试。'
  } finally {
    loading.value = false
  }
})

const projectName = computed(() => getProjectNameById(projectKey) ?? projectKey)

const breadcrumbItems = computed(() => [
  { label: '登录', to: '/login' },
  { label: '项目选择', to: '/projects' },
  { label: projectName.value, to: null },
])

function openPage(page) {
  router.push({
    path: `/projects/${encodeURIComponent(projectKey)}/pages/${encodeURIComponent(page.page_key)}/sheets`,
    query: {
      config: page.config_file,
      pageName: page.page_name,
    },
  })
}
</script>

<style scoped>
.page-select-main {
  padding: 24px;
  max-width: 960px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-block {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-subtitle {
  margin-top: 8px;
  font-size: 14px;
  color: var(--neutral-500);
}

.page-state {
  padding: 40px 0;
  text-align: center;
  color: var(--neutral-600);
}

.page-state.error {
  color: var(--danger);
}

.page-card {
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: transform 0.2s ease;
}

.page-card:hover {
  transform: translateY(-2px);
}

.page-card-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--primary-700);
}

.page-card-desc {
  font-size: 14px;
  color: var(--neutral-500);
}
</style>
