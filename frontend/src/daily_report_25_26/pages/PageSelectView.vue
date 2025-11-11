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
            <div class="page-card-desc">{{ pageDescription(page) }}</div>
          </button>
        </div>
      </section>
      <section v-if="showWorkflowCard" class="card elevated status-block">
        <header class="card-header status-header">
          <div class="status-heading">
            <h3>审批进度</h3>
            <p class="status-subtitle">
              当前业务日期：{{ workflowBizDateText }} ｜ 当前数据展示日期：{{ workflowDisplayDateText }}
            </p>
          </div>
          <button
            v-if="publishButtonVisible"
            class="btn primary"
            type="button"
            :disabled="actionPending || publishDisabled"
            @click="publishDaily"
          >
            {{ publishStatus?.status === 'published' ? '已发布' : actionPending ? '发布中…' : '发布日报' }}
          </button>
        </header>
        <div v-if="workflowLoading" class="page-state">审批进度加载中，请稍候…</div>
        <div v-else-if="workflowError" class="page-state error">{{ workflowError }}</div>
        <div v-else class="status-content">
          <table class="status-table">
            <thead>
              <tr>
                <th>单位</th>
                <th>状态</th>
                <th>审批人</th>
                <th>审批时间</th>
                <th v-if="actionsColumnVisible">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="unit in workflowUnits" :key="unit.unit">
                <td>{{ unit.unit }}</td>
                <td>
                  <span :class="['status-badge', unit.status]">{{ statusLabel(unit.status) }}</span>
                </td>
                <td>{{ unit.approved_by || '待审批' }}</td>
                <td>{{ formatDateTime(unit.approved_at) || '—' }}</td>
                <td v-if="actionsColumnVisible">
                  <button
                    v-if="unit.status !== 'approved' && canApproveUnit(unit.unit)"
                    class="btn ghost"
                    type="button"
                    :disabled="actionPending"
                    @click="approveUnit(unit.unit)"
                  >
                    批准
                  </button>
                  <button
                    v-else-if="unit.status === 'approved' && canRevokeUnit(unit.unit)"
                    class="btn ghost"
                    type="button"
                    :disabled="actionPending"
                    @click="revokeUnit(unit.unit)"
                  >
                    取消批准
                  </button>
                  <span v-else>—</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="publish-state">
            <span>发布状态：</span>
            <span :class="['status-badge', publishStatus?.status || 'pending']">
              {{ statusLabel(publishStatus?.status) }}
            </span>
            <span v-if="publishStatus?.published_by">
              ｜ 发布人：{{ publishStatus.published_by }}
            </span>
            <span v-if="publishStatus?.published_at">
              ｜ 时间：{{ formatDateTime(publishStatus.published_at) }}
            </span>
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
import { listPages } from '../services/api'
import { ensureProjectsLoaded, getProjectNameById } from '../composables/useProjects'
import { useAuthStore } from '../store/auth'

const route = useRoute()
const router = useRouter()
const projectKey = String(route.params.projectKey ?? '')

const auth = useAuthStore()
const PAGE_DESCRIPTION_MAP = Object.freeze({
  dashboard: '查看整体数据仪表盘',
  data_show: '浏览固定数据展示表',
  data_approval: '处理审批流程进度',
  data_entry: '填写并提交日报数据',
  constant_data: '维护常量指标数据',
  data_analysis: '数据自由组合提取',
  debug_runtime_eval: '运行时表达式调试工具，仅限技术人员',
})
const canApproveUnit = auth.canApproveUnit
const canRevokeUnit = auth.canRevokeUnit
const rawPages = ref([])
const pages = ref([])
const loading = ref(false)
const errorMessage = ref('')
const workflow = ref(null)
const workflowLoading = ref(false)
const workflowError = ref('')
const actionPending = ref(false)

onMounted(async () => {
  await loadPages()
  await refreshWorkflow()
})

async function loadPages() {
  loading.value = true
  errorMessage.value = ''
  try {
    await ensureProjectsLoaded()
    const response = await listPages(projectKey)
    rawPages.value = Array.isArray(response?.pages) ? response.pages : []
    pages.value = auth.filterPages(rawPages.value)
    if (!pages.value.length) {
      errorMessage.value = '暂无可访问的页面，请联系管理员确认权限。'
    }
  } catch (err) {
    console.error(err)
    errorMessage.value = '读取页面列表失败，请稍后再试。'
  } finally {
    loading.value = false
  }
}

async function refreshWorkflow() {
  workflowLoading.value = true
  workflowError.value = ''
  try {
    const response = await auth.loadWorkflowStatus(projectKey)
    workflow.value = response || null
  } catch (err) {
    console.error(err)
    workflowError.value = err instanceof Error ? err.message : '获取审批进度失败'
  } finally {
    workflowLoading.value = false
  }
}

watch(
  () => auth.permissions,
  () => {
    pages.value = auth.filterPages(rawPages.value)
    if (!pages.value.length && rawPages.value.length) {
      errorMessage.value = '当前账号无可访问页面，请联系管理员。'
    } else if (pages.value.length) {
      errorMessage.value = ''
    }
  },
  { deep: true },
)

const projectName = computed(() => getProjectNameById(projectKey) ?? projectKey)

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: projectName.value, to: null },
])

const workflowUnits = computed(() => {
  const units = workflow.value?.units
  if (!Array.isArray(units)) return []
  const blacklist = new Set(['系统管理员', 'Group'])
  return units.filter((item) => item?.unit && !blacklist.has(item.unit))
})

const publishStatus = computed(() => workflow.value?.publish || null)
const workflowBizDate = computed(() => workflow.value?.biz_date || '')
const workflowDisplayDate = computed(() => workflow.value?.display_date || '')
const workflowBizDateText = computed(() => formatDate(workflowBizDate.value))
const workflowDisplayDateText = computed(() => formatDate(workflowDisplayDate.value))
const actionsColumnVisible = computed(() => auth.canApprove || auth.canRevoke)
const publishButtonVisible = computed(() => auth.canPublish)
const publishDisabled = computed(
  () => publishStatus.value?.status === 'published' || workflowLoading.value,
)

const showWorkflowCard = computed(() => {
  return (
    workflowLoading.value ||
    Boolean(workflowError.value) ||
    workflowUnits.value.length > 0 ||
    auth.canApprove ||
    auth.canRevoke ||
    auth.canPublish
  )
})

function statusLabel(status) {
  if (status === 'approved') return '已审批'
  if (status === 'published') return '已发布'
  return '待处理'
}

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/

function formatDate(value) {
  if (!value) return '—'
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed) return '—'
    if (DATE_RE.test(trimmed)) return trimmed
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function formatDateTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${d} ${hh}:${mm}`
}

async function approveUnit(unit) {
  if (actionPending.value) return
  actionPending.value = true
  workflowError.value = ''
  try {
    const response = await auth.approveUnit(projectKey, unit)
    workflow.value = response || workflow.value
  } catch (err) {
    console.error(err)
    workflowError.value = err instanceof Error ? err.message : '审批失败'
  } finally {
    actionPending.value = false
  }
}

async function revokeUnit(unit) {
  if (actionPending.value) return
  actionPending.value = true
  workflowError.value = ''
  try {
    const response = await auth.revokeUnit(projectKey, unit)
    workflow.value = response || workflow.value
  } catch (err) {
    console.error(err)
    workflowError.value = err instanceof Error ? err.message : '取消批准失败'
  } finally {
    actionPending.value = false
  }
}

async function publishDaily() {
  if (actionPending.value || publishDisabled.value) return
  actionPending.value = true
  workflowError.value = ''
  try {
    const response = await auth.publish(projectKey)
    workflow.value = response || workflow.value
  } catch (err) {
    console.error(err)
    workflowError.value = err instanceof Error ? err.message : '发布失败'
  } finally {
    actionPending.value = false
  }
}

function pageDescription(page) {
  if (!page) return '点击进入功能页面'
  const desc =
    page?.page_description ||
    page?.description ||
    page?.pageDesc ||
    page?.page_desc ||
    ''
  if (typeof desc === 'string' && desc.trim()) {
    return desc.trim()
  }
  const key = String(page?.page_key || page?.page_url || '').toLowerCase()
  if (key && PAGE_DESCRIPTION_MAP[key]) {
    return PAGE_DESCRIPTION_MAP[key]
  }
  return '点击进入功能页面'
}

function openPage(page) {
  // 支持“专用调试页面”：若后端 pages 的键是形如 "/debug/..."，则直接导航到该路径
  if (typeof page?.page_url === 'string' && page.page_url.startsWith('/')) {
    return router.push({ path: page.page_url })
  }
  const base = `/projects/${encodeURIComponent(projectKey)}/pages/${encodeURIComponent(page.page_key)}`
  const normalizedKey = String(page?.page_key ?? page?.page_url ?? '').toLowerCase()
  const isDashboard = normalizedKey === 'dashboard'
  if (isDashboard) {
    router.push({
      path: `${base}/dashboard`,
      query: { pageName: page.page_name },
    })
    return
  }
  const isDataAnalysis = normalizedKey === 'data_analysis'
  if (isDataAnalysis) {
    router.push({
      path: `${base}/data-analysis`,
      query: { config: page.config_file, pageName: page.page_name },
    })
    return
  }
  const isDisplay = typeof page?.config_file === 'string' && /展示用/.test(page.config_file)
  if (isDisplay) {
    router.push({
      path: `${base}/display`,
      query: { config: page.config_file, pageName: page.page_name },
    })
  } else {
    router.push({
      path: `${base}/sheets`,
      query: { config: page.config_file, pageName: page.page_name },
    })
  }
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

.status-block {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.status-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.status-heading h3 {
  margin: 0;
  font-size: 18px;
}

.status-subtitle {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--neutral-500);
}

.status-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-table {
  width: 100%;
  border-collapse: collapse;
}

.status-table th,
.status-table td {
  border-bottom: 1px solid #e5e7eb;
  padding: 8px 12px;
  text-align: left;
  font-size: 13px;
}

.status-table th {
  color: var(--neutral-500);
  font-weight: 600;
  background: #f9fafb;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  background: #e5e7eb;
  color: #374151;
}

.status-badge.approved,
.status-badge.published {
  background: rgba(16, 185, 129, 0.15);
  color: #047857;
}

.status-badge.pending {
  background: rgba(251, 191, 36, 0.15);
  color: #b45309;
}

.publish-state {
  font-size: 13px;
  color: var(--neutral-600);
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.btn.ghost {
  border: 1px solid var(--primary-200);
  background: transparent;
  color: var(--primary-600);
}

.btn.ghost:hover {
  background: rgba(59, 130, 246, 0.1);
}
</style>
