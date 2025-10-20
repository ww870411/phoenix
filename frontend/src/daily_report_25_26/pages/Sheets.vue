<template>
  <div>
    <AppHeader />
    <div class="container">
      <Breadcrumbs class="breadcrumb-spacing" />

      <div class="table-wrap card">
        <div v-if="loadError" class="placeholder">{{ loadError }}</div>
        <div v-else class="card-grid">
          <div class="card" v-for="group in grouped" :key="group.unit">
            <div class="card-header">{{ group.unit || '未分组' }}</div>
            <ul class="sheet-list">
              <li v-for="sheet in group.items" :key="sheet.sheet_key" class="sheet-row">
                <div class="sheet-main">
                  <router-link
                    :to="{ name: 'data-entry', params: { projectKey, sheetKey: sheet.sheet_key } }"
                    class="sheet-link"
                  >
                    {{ sheet.sheet_name }}
                  </router-link>
                  <span class="sheet-key">{{ sheet.sheet_key }}</span>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import '../styles/theme.css'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listSheets } from '../services/api'
import { ensureProjectsLoaded, getProjectNameById } from '../composables/useProjects'

const route = useRoute()
const router = useRouter()
const projectKey = String(route.params.projectKey ?? '')
const projectName = computed(() => getProjectNameById(projectKey))

if (!projectKey) {
  router.replace({ name: 'projects' })
}

const sheets = ref([])
const loadError = ref('')

async function loadSheets() {
  loadError.value = ''
  try {
    const response = await listSheets(projectKey)
    const entries = Object.entries(response || {})
    sheets.value = entries.map(([sheet_key, meta]) => ({
      sheet_key,
      sheet_name: meta?.sheet_name || meta?.['表名'] || sheet_key,
      unit_name: meta?.unit_name || meta?.['单位名'] || ''
    }))
  } catch (err) {
    loadError.value = '无法获取表格清单，请确认后端接口 /api/v1/projects/{project_key}/data_entry/sheets 已就绪。'
    sheets.value = []
  }
}

const grouped = computed(() => {
  const bucket = new Map()
  for (const sheet of sheets.value) {
    const unit = sheet.unit_name || '未分组'
    if (!bucket.has(unit)) bucket.set(unit, [])
    bucket.get(unit).push(sheet)
  }
  return Array.from(bucket.entries()).map(([unit, items]) => ({ unit, items }))
})

onMounted(async () => {
  await ensureProjectsLoaded().catch(() => {})
  await loadSheets()
})
</script>

<style scoped>
.table-wrap { margin-top: 16px; }
.breadcrumb-spacing { margin-bottom: 16px; display: inline-block; }
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.sheet-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 12px; }
.sheet-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding: 8px 0; }
.sheet-main { display: flex; flex-direction: column; gap: 4px; }
.sheet-link { color: var(--primary-700); font-weight: 600; text-decoration: none; }
.sheet-link:hover { text-decoration: underline; }
.sheet-key { font-size: 12px; color: var(--muted); }
.placeholder { padding: 32px; color: var(--muted); text-align: center; }
</style>
