<template>
  <div class="page-viewer-root">
    <AppHeader />
    <main class="page-viewer-main container">
      <Breadcrumbs :items="breadcrumbItems" />
      <header class="topbar">
        <div>
          <h2>{{ fileName || '页面预览' }}</h2>
          <p class="sub">当前页面内容已通过平台鉴权加载。</p>
        </div>
        <div class="topbar-actions">
          <button class="btn ghost" type="button" @click="goList">返回页面列表</button>
          <button class="btn ghost" type="button" :disabled="!fileName" @click="openPermanentLink">生成永久链接</button>
          <button class="btn primary" type="button" :disabled="!htmlContent" @click="openInNewWindow">新窗口打开</button>
        </div>
      </header>
      <p v-if="permanentLinkMessage" class="permalink-message">{{ permanentLinkMessage }}</p>

      <section class="card elevated viewer-card">
        <div v-if="loading" class="state">正在加载页面内容...</div>
        <div v-else-if="errorMessage" class="state error">{{ errorMessage }}</div>
        <iframe
          v-else
          class="viewer-frame"
          :title="fileName || '页面预览'"
          :srcdoc="htmlContent"
        />
      </section>
    </main>
  </div>
</template>

<script setup>
import '../../daily_report_25_26/styles/theme.css'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'
import { getPageShowcaseHtml, getPageShowcasePublicUrl } from '../../daily_report_25_26/services/api'

const route = useRoute()
const router = useRouter()
const projectKey = computed(() => String(route.params.projectKey || 'page_showcase'))
const fileName = computed(() => decodeURIComponent(String(route.params.fileName || '')))
const loading = ref(false)
const errorMessage = ref('')
const htmlContent = ref('')
const permanentLinkMessage = ref('')

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '页面展示', to: `/projects/${encodeURIComponent(projectKey.value)}` },
  { label: fileName.value || '页面预览', to: null },
])

function goList() {
  router.push(`/projects/${encodeURIComponent(projectKey.value)}`)
}

function openInNewWindow() {
  if (!htmlContent.value || typeof window === 'undefined') return
  const blob = new Blob([htmlContent.value], { type: 'text/html;charset=utf-8' })
  const blobUrl = window.URL.createObjectURL(blob)
  const opened = window.open(blobUrl, '_blank', 'noopener,noreferrer')
  window.setTimeout(() => window.URL.revokeObjectURL(blobUrl), 60_000)
  if (!opened) {
    window.alert('浏览器拦截了新窗口，请允许弹窗后重试。')
  }
}

async function openPermanentLink() {
  if (!fileName.value || typeof window === 'undefined') return
  const targetUrl = getPageShowcasePublicUrl(projectKey.value, fileName.value)
  permanentLinkMessage.value = `永久链接：${targetUrl}`
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(targetUrl)
      permanentLinkMessage.value = `永久链接已复制并打开：${targetUrl}`
    }
  } catch (error) {
    console.error('copy permalink failed:', error)
  }
  const opened = window.open(targetUrl, '_blank', 'noopener,noreferrer')
  if (!opened) {
    window.alert(`浏览器拦截了新窗口，请手动打开该永久链接：\n${targetUrl}`)
  }
}

async function loadHtml() {
  if (!fileName.value) {
    errorMessage.value = '页面文件名为空'
    htmlContent.value = ''
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await getPageShowcaseHtml(projectKey.value, fileName.value)
    htmlContent.value = String(response?.html || '')
    if (!htmlContent.value) {
      errorMessage.value = '页面内容为空'
    }
  } catch (error) {
    console.error(error)
    htmlContent.value = ''
    errorMessage.value = error instanceof Error ? error.message : '读取页面内容失败'
  } finally {
    loading.value = false
  }
}

watch(
  () => [projectKey.value, fileName.value],
  () => {
    loadHtml()
  },
  { immediate: true },
)
</script>

<style scoped>
.page-viewer-root {
  min-height: 100vh;
  background: #f8fafc;
}

.page-viewer-main {
  max-width: 1320px;
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

.viewer-card {
  min-height: calc(100vh - 220px);
  padding: 0;
  overflow: hidden;
}

.viewer-frame {
  width: 100%;
  min-height: calc(100vh - 220px);
  border: 0;
  background: #fff;
}

.state {
  padding: 40px 12px;
  text-align: center;
  color: var(--neutral-600);
}

.state.error {
  color: var(--danger, #d93026);
}

.permalink-message {
  margin: -6px 0 0;
  color: var(--neutral-600);
  font-size: 13px;
  word-break: break-all;
}

@media (max-width: 640px) {
  .page-viewer-main {
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
