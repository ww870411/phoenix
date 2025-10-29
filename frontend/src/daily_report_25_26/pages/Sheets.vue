<template>
  <div class="sheets-view">
    <AppHeader />
    <main class="sheets-main">
      <Breadcrumbs :items="breadcrumbItems" />
      <section class="card elevated sheets-block">
        <header class="card-header">
          <h2>{{ pageDisplayName }}</h2>
          <p class="sheet-subtitle">项目：{{ projectName }}</p>
        </header>
        <div v-if="loading" class="sheet-state">表格列表加载中，请稍候…</div>
        <div v-else-if="errorMessage" class="sheet-state error">{{ errorMessage }}</div>
        <div v-else>
          <div v-for="group in groupedSheets" :key="group.groupKey" class="sheet-group">
            <h3 class="group-title">{{ group.groupName }}</h3>
            <div class="card-grid">
              <button
                v-for="sheet in group.items"
                :key="sheet.sheet_key"
                type="button"
                class="card elevated sheet-card"
                @click="openSheet(sheet)"
              >
                <div class="sheet-card-title">{{ sheet.sheet_name }}</div>
                <div class="sheet-card-desc">填报单位：{{ sheet.unit_name || '未配置' }}</div>
              </button>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { listSheets } from '../services/api'
import { ensureProjectsLoaded, getProjectNameById } from '../composables/useProjects'

const route = useRoute()
const router = useRouter()

const projectKey = computed(() => String(route.params.projectKey ?? ''))
const pageKey = computed(() => String(route.params.pageKey ?? ''))
const pageConfig = computed(() => {
  const raw = route.query.config
  return typeof raw === 'string' ? raw : ''
})
const pageDisplayName = computed(() => {
  const raw = route.query.pageName
  if (typeof raw === 'string' && raw.trim()) {
    return raw.trim()
  }
  return pageKey.value || '页面'
})

const sheets = ref([])
const groupedSheets = computed(() => {
  const groups = new Map()
  for (const s of sheets.value) {
    const name = (s.unit_name && String(s.unit_name).trim()) || '未分组'
    if (!groups.has(name)) groups.set(name, [])
    groups.get(name).push(s)
  }
  const result = []
  for (const [name, items] of groups.entries()) {
    result.push({ groupKey: name, groupName: name, items })
  }
  // 严格保持配置文件（后端返回）的单位出现顺序，不再排序
  return result
})
const loading = ref(false)
const errorMessage = ref('')

const projectName = computed(() => getProjectNameById(projectKey.value) ?? projectKey.value)

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: projectName.value, to: `/projects/${encodeURIComponent(projectKey.value)}/pages` },
  { label: pageDisplayName.value, to: null },
])

function ensureValidRoute() {
  if (!projectKey.value || !pageKey.value) {
    router.replace('/projects')
    return false
  }
  if (!pageConfig.value) {
    errorMessage.value = '页面缺少模板配置文件参数，无法继续。'
    return false
  }
  return true
}

async function loadSheets() {
  if (!ensureValidRoute()) {
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    await ensureProjectsLoaded()
    const response = await listSheets(projectKey.value, pageConfig.value)
    const catalog = response?.content || response // 兼容旧结构
    const entries = catalog && typeof catalog === 'object' ? Object.entries(catalog) : []
    sheets.value = entries.map(([sheetKey, meta]) => ({
      sheet_key: sheetKey,
      sheet_name: meta?.sheet_name ?? sheetKey,
      unit_name: meta?.unit_name ?? '',
    }))
    if (!sheets.value.length) {
      errorMessage.value = '该页面暂未配置任何表格。'
    }
  } catch (err) {
    console.error(err)
    errorMessage.value =
      '无法获取表格清单，请确认后端接口 /api/v1/projects/{project_key}/data_entry/sheets 已完成配置。'
  } finally {
    loading.value = false
  }
}

function openSheet(sheet) {
  const isApproval = typeof pageDisplayName.value === 'string' && pageDisplayName.value.includes('审批')
  const base = `/projects/${encodeURIComponent(projectKey.value)}/pages/${encodeURIComponent(pageKey.value)}`
  const path = isApproval
    ? `${base}/approval/${encodeURIComponent(sheet.sheet_key)}`
    : `${base}/sheets/${encodeURIComponent(sheet.sheet_key)}`
  router.push({ path, query: { config: pageConfig.value, pageName: pageDisplayName.value } })
}

onMounted(loadSheets)
watch([projectKey, pageKey, pageConfig], loadSheets)
</script>

<style scoped>
.sheets-main {
  padding: 24px;
  max-width: 960px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sheets-block {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.sheet-subtitle {
  margin-top: 8px;
  font-size: 14px;
  color: var(--neutral-500);
}

.sheet-state {
  padding: 40px 0;
  text-align: center;
  color: var(--neutral-600);
}

.sheet-state.error {
  color: var(--danger);
}

.sheet-card {
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: transform 0.2s ease;
}

.sheet-card:hover {
  transform: translateY(-2px);
}

.sheet-card-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--primary-700);
}

.sheet-card-desc {
  font-size: 14px;
  color: var(--neutral-500);
}
</style>
