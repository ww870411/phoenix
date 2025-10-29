<template>
  <div class="approval-container">
    <AppHeader />
    <div class="container">
      <Breadcrumbs :items="breadcrumbItems" class="breadcrumb-spacing" />
      <header class="topbar">
        <div style="display:flex;flex-direction:column;gap:6px;">
          <h2>数据审批</h2>
          <div class="sub">项目：{{ projectName }} ｜ 表：{{ sheetDisplayName }}</div>
        </div>
        <div class="right" style="display:flex;align-items:center;gap:8px;">
          <label class="date-group" title="业务日期" style="display:inline-flex;align-items:center;gap:6px;">
            <span>业务日期：</span>
            <select v-model="bizDateMode">
              <option value="regular">regular（按昨日/同期）</option>
              <option value="custom">自定义</option>
            </select>
            <input v-if="bizDateMode==='custom'" type="date" v-model="bizDate" />
          </label>
          <button class="btn ghost" @click="runEval" :disabled="loading">刷新</button>
        </div>
      </header>

      <div class="table-wrap card" v-if="columns.length">
        <RevoGrid
          :row-headers="true"
          :hide-attribution="true"
          :stretch="true"
          :auto-size-column="false"
          :row-size="30"
          :resize="true"
          :range="true"
          :columns="gridColumns"
          :source="gridSource"
          style="height: 70vh; width: 100%;"
        />
      </div>
      <div v-else class="placeholder">无审批数据</div>
      <div v-if="errorMessage" class="error">{{ errorMessage }}</div>
    </div>
  </div>
</template>

<script setup>
import '../styles/theme.css'
import RevoGrid from '@revolist/vue3-datagrid'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { evalSpec } from '../services/api'
import { ensureProjectsLoaded, getProjectNameById } from '../composables/useProjects'

const route = useRoute()
const router = useRouter()

const projectKey = computed(() => String(route.params.projectKey ?? ''))
const pageKey = computed(() => String(route.params.pageKey ?? ''))
const sheetKey = computed(() => String(route.params.sheetKey ?? ''))
const pageConfig = computed(() => {
  const raw = route.query.config
  return typeof raw === 'string' ? raw : ''
})
const pageDisplayName = computed(() => {
  const raw = route.query.pageName
  return typeof raw === 'string' && raw.trim() ? raw.trim() : (pageKey.value || '审批')
})

const projectName = computed(() => getProjectNameById(projectKey.value) ?? projectKey.value)
const sheetName = ref('')
const sheetDisplayName = computed(() => sheetName.value || sheetKey.value)
const columns = ref([])
const rows = ref([])

const gridColumns = ref([])
const gridSource = ref([])
const loading = ref(false)
const errorMessage = ref('')

const bizDateMode = ref('regular')
const bizDate = ref('')

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: projectName.value, to: `/projects/${encodeURIComponent(projectKey.value)}/pages` },
  { label: pageDisplayName.value, to: `/projects/${encodeURIComponent(projectKey.value)}/pages/${encodeURIComponent(pageKey.value)}/sheets?config=${encodeURIComponent(pageConfig.value)}&pageName=${encodeURIComponent(pageDisplayName.value)}` },
  { label: sheetDisplayName.value, to: null },
])

function ensureValidRoute() {
  if (!projectKey.value || !pageKey.value || !sheetKey.value || !pageConfig.value) {
    router.replace('/projects')
    return false
  }
  return true
}

function buildReadOnlyColumns(cols) {
  const defs = (cols || []).map((name, index) => {
    const base = {
      prop: `c${index}`,
      name: String(name ?? ''),
      autoSize: true,
      minSize: index === 0 ? 160 : 120,
      readonly: true,
    }
    return base
  })
  gridColumns.value = defs
}

function buildSource(cols, rs) {
  const src = (rs || []).map(row => {
    const rec = {}
    for (let i = 0; i < (cols?.length || 0); i++) {
      const v = Array.isArray(row) ? row[i] : ''
      rec[`c${i}`] = (v === null || v === undefined) ? '' : String(v)
    }
    return rec
  })
  gridSource.value = src
}

async function runEval() {
  if (!ensureValidRoute()) return
  loading.value = true
  errorMessage.value = ''
  try {
    await ensureProjectsLoaded()
    const body = {
      sheet_key: sheetKey.value,
      project_key: 'daily_report_25_26',
      // primary_key 可留空，后端会用模板 unit_id 补齐；如需按中心筛选可以加入 {company:'Xxx_Center'}
      config: pageConfig.value,
      biz_date: bizDateMode.value === 'regular' ? 'regular' : (bizDate.value || 'regular'),
      trace: false,
    }
    const res = await evalSpec(projectKey.value, body)
    if (!res || res.ok === false) {
      throw new Error(res?.message || 'runtime eval 失败')
    }
    sheetName.value = res.sheet_name || sheetKey.value
    columns.value = Array.isArray(res.columns) ? res.columns : []
    rows.value = Array.isArray(res.rows) ? res.rows : []
    buildReadOnlyColumns(columns.value)
    buildSource(columns.value, rows.value)
  } catch (err) {
    console.error(err)
    errorMessage.value = err?.message || String(err)
  } finally {
    loading.value = false
  }
}

onMounted(runEval)
watch([bizDateMode, bizDate], runEval)
</script>

<style scoped>
.container { padding: 16px; }
.topbar { display:flex; align-items:center; justify-content:space-between; margin-bottom: 12px; }
.sub { color: #666; font-size: 13px; }
.placeholder { color:#888; padding: 20px 0; text-align:center; }
.error { color: #c00; margin-top: 10px; }
</style>

