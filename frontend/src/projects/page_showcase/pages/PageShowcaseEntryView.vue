<template>
  <div class="page-showcase-root">
    <AppHeader />
    <main class="page-showcase-main container">
      <Breadcrumbs :items="breadcrumbItems" />
      <header class="topbar">
        <div>
          <h2>页面展示</h2>
          <p class="sub">自动读取项目目录中的静态 HTML 页面，并按文件名生成卡片。</p>
        </div>
        <div class="topbar-actions">
          <button class="btn ghost" type="button" @click="goProjects">返回项目列表</button>
        </div>
      </header>

      <section class="card elevated">
        <div v-if="loading" class="state">正在读取页面列表...</div>
        <div v-else-if="errorMessage" class="state error">{{ errorMessage }}</div>
        <div v-else-if="pages.length === 0" class="state">当前目录下暂无可展示的 HTML 页面。</div>
        <div v-else class="card-grid">
          <button
            v-for="page in pages"
            :key="page.file_name"
            type="button"
            class="page-card card clickable elevated"
            @click="openPage(page)"
          >
            <div class="page-card__title">{{ page.page_name }}</div>
            <div class="page-card__meta">大小：{{ formatSize(page.size_bytes) }}</div>
            <div class="page-card__meta">更新时间：{{ formatDateTime(page.updated_at) }}</div>
          </button>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import '../../daily_report_25_26/styles/theme.css'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'
import { listPageShowcasePages } from '../../daily_report_25_26/services/api'

const route = useRoute()
const router = useRouter()
const projectKey = computed(() => String(route.params.projectKey || 'page_showcase'))
const pages = ref([])
const loading = ref(false)
const errorMessage = ref('')

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '页面展示', to: null },
])

function goProjects() {
  router.push('/projects')
}

function formatSize(sizeBytes) {
  const size = Number(sizeBytes || 0)
  if (!Number.isFinite(size) || size <= 0) return '0 B'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

function formatDateTime(value) {
  if (!value) return '未知'
  const text = String(value)
  return text.replace('T', ' ')
}

function openPage(page) {
  const fileName = String(page?.file_name || '')
  if (!fileName) return
  router.push(`/projects/${encodeURIComponent(projectKey.value)}/view/${encodeURIComponent(fileName)}`)
}

async function loadPages() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await listPageShowcasePages(projectKey.value)
    pages.value = Array.isArray(response?.pages) ? response.pages : []
  } catch (error) {
    console.error(error)
    errorMessage.value = error instanceof Error ? error.message : '读取页面列表失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadPages()
})
</script>

<style scoped>
.page-showcase-root {
  min-height: 100vh;
  background: #f8fafc;
}

.page-showcase-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 18px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.topbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.topbar-actions {
  display: flex;
  gap: 10px;
}

.state {
  padding: 40px 12px;
  text-align: center;
  color: var(--neutral-600);
}

.state.error {
  color: var(--danger, #d93026);
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.page-card {
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 20px;
}

.page-card__title {
  font-size: 18px;
  font-weight: 600;
  color: var(--primary-700);
  word-break: break-word;
}

.page-card__meta {
  font-size: 13px;
  color: var(--neutral-500);
  word-break: break-all;
}

@media (max-width: 640px) {
  .page-showcase-main {
    padding: 14px 14px 20px;
  }

  .topbar {
    flex-direction: column;
  }

  .topbar-actions {
    width: 100%;
  }
}
</style>
