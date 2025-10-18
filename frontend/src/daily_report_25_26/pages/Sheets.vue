<template>
  <div>
    <AppHeader />
    <div class="container">
      <header class="topbar">
        <div>
          <h2>仪表盘（表格选择与状态）</h2>
          <div class="sub">项目：{{ projectKey }}</div>
        </div>
        <div class="right" style="display:flex;align-items:center;gap:8px;">
          <label class="date">
            <span>业务日期</span>
            <input type="date" v-model="bizDate" />
          </label>
          <button class="btn ghost" style="margin-left:auto;" @click="refreshAll">
            刷新状态
          </button>
        </div>
      </header>

      <Breadcrumbs />

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
                <div
                  v-if="statusMap[sheet.sheet_key] && statusMap[sheet.sheet_key].total > 0"
                  class="sheet-meta"
                >
                  <span class="badge" :class="badgeClass(sheet)">
                    {{ statusMap[sheet.sheet_key].filled }} / {{ statusMap[sheet.sheet_key].total }}
                  </span>
                  <div class="progress" style="margin-top:6px;width:100%;">
                    <div class="progress-bar" :style="{ width: progressPct(sheet) }"></div>
                  </div>
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
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getTemplate, listSheets, queryData } from '../services/api'

const route = useRoute()
const router = useRouter()
const projectKey = String(route.params.projectKey ?? '')

if (!projectKey) {
  router.replace({ name: 'projects' })
}

const bizDate = ref(new Date().toISOString().slice(0, 10))
const sheets = ref([])
const loadError = ref('')
const statusMap = reactive({})

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
    loadError.value = '无法获取表格清单，请确认后端接口 /api/v1/projects/{project_key}/sheets 已就绪。'
    sheets.value = []
  }
}

async function refreshStatus(sheet) {
  try {
    const tpl = await getTemplate(projectKey, sheet.sheet_key)
    const columns = Array.isArray(tpl?.columns) ? tpl.columns : []
    const rows = Array.isArray(tpl?.rows) ? tpl.rows : []
    const fillableCols = columns.map((_, idx) => idx).filter((idx) => idx >= 2)
    const total = rows.length * fillableCols.length

    const queryResult = await queryData({
      project_key: projectKey,
      sheet_key: sheet.sheet_key,
      biz_date: bizDate.value,
    })
    const cells = Array.isArray(queryResult?.cells) ? queryResult.cells : []
    statusMap[sheet.sheet_key] = { filled: cells.length, total }
  } catch (err) {
    statusMap[sheet.sheet_key] = { filled: 0, total: 0 }
  }
}

async function refreshAll() {
  if (!sheets.value.length) return
  for (const sheet of sheets.value) {
    await refreshStatus(sheet)
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

function badgeClass(sheet) {
  const st = statusMap[sheet.sheet_key]
  if (!st) return 'neutral'
  if (st.total > 0 && st.filled >= st.total) return 'success'
  if (st.total > 0 && st.filled > 0) return 'warning'
  return 'neutral'
}

function progressPct(sheet) {
  const st = statusMap[sheet.sheet_key]
  if (!st || !st.total) return '0%'
  const pct = Math.min(100, Math.round((st.filled / st.total) * 100))
  return `${pct}%`
}

onMounted(async () => {
  await loadSheets()
  await refreshAll()
})

watch(bizDate, () => {
  refreshAll()
})
</script>

<style scoped>
.table-wrap { margin-top: 16px; }
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.sheet-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 12px; }
.sheet-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding: 8px 0; }
.sheet-main { display: flex; flex-direction: column; gap: 4px; }
.sheet-link { color: var(--primary-700); font-weight: 600; text-decoration: none; }
.sheet-link:hover { text-decoration: underline; }
.sheet-key { font-size: 12px; color: var(--muted); }
.sheet-meta { display: flex; flex-direction: column; gap: 6px; align-items: flex-start; min-width: 120px; }
.badge { align-self: flex-start; }
.placeholder { padding: 32px; color: var(--muted); text-align: center; }
</style>
