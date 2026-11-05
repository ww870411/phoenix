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
        <div v-else class="groups-container">
          <div
            v-for="group in categorizedGroups"
            :key="group.key"
            class="page-group-section"
            :class="`group-${group.key}`"
          >
            <div class="group-header">
              <div class="group-title-row">
                <span class="group-indicator" :class="`indicator-${group.key}`"></span>
                <h3 class="group-title">{{ group.title }}</h3>
              </div>
              <p v-if="group.description" class="group-desc">{{ group.description }}</p>
            </div>

            <div class="card-grid">
              <component
                :is="isClickable ? 'button' : 'div'"
                v-for="page in group.pages"
                :key="page.page_key"
                :type="isClickable ? 'button' : undefined"
                :class="[
                  'card elevated page-card',
                  { 'is-static': !isClickable },
                  getCardCustomClass(group.key, page)
                ]"
                @click="isClickable ? openPage(page) : undefined"
              >
                <div class="page-card-title">
                  <ScaleBalanceIcon
                    v-if="isReviewHallPage(page)"
                    :size="20"
                    class="page-card-title-icon"
                  />
                  <span class="page-card-title-text">{{ formatCardTitle(page) }}</span>
                  <span
                    v-if="isPrimaryEntryCard(page)"
                    class="primary-entry-tag"
                  >
                    核心填报
                  </span>
                </div>
                <div class="page-card-desc">{{ pageDescription(page) }}</div>
              </component>
            </div>
          </div>
        </div>
      </section>
      <section v-if="showWorkflowCardForProject" class="card elevated status-block">
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
import ScaleBalanceIcon from '../../insulation_pipe_supply_2026/components/ScaleBalanceIcon.vue'
import { withDailyBriefPage } from '../composables/dailyBriefPresentation'

const route = useRoute()
const router = useRouter()
const projectKey = String(route.params.projectKey ?? '')

function isReviewHallPage(page) {
  const key = String(page?.page_key || page?.page_url || '').toLowerCase()
  const name = String(page?.page_name || '')
  return key === 'joint_review_hall' || name.includes('会审')
}

function formatCardTitle(page) {
  const name = String(page?.page_name || '')
  if (isReviewHallPage(page)) {
    // 剥离原生 Emoji ⚖️，由统一的矢量全彩 ScaleBalanceIcon 稳定渲染，杜绝跨系统黑白字体退化与毛刺
    return name.replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{FE00}-\u{FE0F}]/gu, '').trim()
  }
  return name
}

const auth = useAuthStore()
const PAGE_DESCRIPTION_MAP = Object.freeze({
  big_screen: '深色科技大屏、数字孪生飞线调度与实时发运战报',
  dashboard: '查看整体数据仪表盘',
  daily_brief: '每日生产状况内参',
  data_show: '浏览数据展示表',
  data_approval: '每日数据审核批准',
  data_entry: '填写并提交日报数据',
  constant_data: '维护常量指标数据',
  data_analysis: '数据自由组合提取',
  dynamic_plan: '基于气温情景进行计划分解测算，仅供运行分析',
  spot_electricity: '15分钟日前/实时电价与走势',
  global_management: '核心运行参数设定',
  dispatch_info: '主城区生产调度全景工况监控',
  smart_heating: '首站环路、电厂机组与换热站一次网实时监测',
  debug_runtime_eval: '运行时表达式调试工具，仅限技术人员',
})
function filterVisiblePages(list) {
  return (Array.isArray(list) ? list : []).filter((page) => {
    const key = String(page?.page_key || '').trim().toLowerCase()
    return key
  })
}

function withAdminExclusivePages(pageList, pKey, user) {
  let list = withDailyBriefPage(pageList, pKey, user)
  const isGlobalAdmin = pKey === 'daily_report_25_26' && user?.group === 'Global_admin'
  list = (Array.isArray(list) ? list : []).filter((p) => p.page_key !== 'smart_heating')
  if (isGlobalAdmin) {
    list.push({
      page_key: 'smart_heating',
      page_name: '智慧供热实时工况',
      page_description: '首站环路、电厂机组与换热站一次网实时监测',
      page_url: `/projects/${pKey}/pages/smart_heating`,
    })
  }
  return list
}
const canApproveUnit = (unit) => auth.canApproveUnit(unit, projectKey)
const canRevokeUnit = (unit) => auth.canRevokeUnit(unit, projectKey)
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
  if (!isWorkflowExempt.value) {
    await refreshWorkflow()
  }
})

async function loadPages() {
  loading.value = true
  errorMessage.value = ''
  try {
    await ensureProjectsLoaded()
    const response = await listPages(projectKey)
    rawPages.value = Array.isArray(response?.pages) ? response.pages : []
    pages.value = withAdminExclusivePages(filterVisiblePages(auth.filterPages(projectKey, rawPages.value)), projectKey, auth.user)
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
    pages.value = withAdminExclusivePages(
      filterVisiblePages(auth.filterPages(projectKey, rawPages.value)),
      projectKey,
      auth.user,
    )
    if (!pages.value.length && rawPages.value.length) {
      errorMessage.value = '当前账号无可访问页面，请联系管理员。'
    } else if (pages.value.length) {
      errorMessage.value = ''
    }
  },
  { deep: true },
)

const GROUP_DEFINITIONS = [
  {
    key: 'entry_approval',
    title: '报表填报与审批',
    description: '日常数据上报、分级审核与指标基准维护',
    pageKeys: ['data_entry', 'data_approval', 'constant_data'],
  },
  {
    key: 'monitoring_dashboard',
    title: '生产监控与看板',
    description: '全景数据看板、报表展示与调度电价监控',
    pageKeys: ['dashboard', 'data_show', 'dispatch_info', 'spot_electricity', 'smart_heating'],
  },
  {
    key: 'analysis_management',
    title: '分析与系统管理',
    description: '每日简报、多维计划图谱、自由分析与算法字典',
    pageKeys: ['daily_brief', 'period_report', 'dynamic_plan', 'data_analysis', 'global_management'],
  },
]

function isPrimaryEntryCard(page) {
  const key = String(page?.page_key || page?.page_url || '').trim().toLowerCase()
  return key === 'data_entry'
}

function getCardCustomClass(groupKey, page) {
  const key = String(page?.page_key || page?.page_url || '').trim().toLowerCase()
  if (key === 'dashboard') {
    return 'card-primary-dashboard'
  }
  if (groupKey === 'entry_approval') {
    if (key === 'data_entry') {
      return 'card-primary-entry'
    }
    return 'card-blue-group'
  }
  return ''
}

const categorizedGroups = computed(() => {
  const currentPages = Array.isArray(pages.value) ? pages.value : []
  if (!currentPages.length) return []

  if (projectKey !== 'daily_report_25_26') {
    return [
      {
        key: 'all',
        title: '全部功能页面',
        description: '',
        pages: currentPages,
      },
    ]
  }

  const pageMap = new Map()
  currentPages.forEach((p) => {
    const k = String(p?.page_key || p?.page_url || '').trim().toLowerCase()
    pageMap.set(k, p)
  })

  const usedKeys = new Set()
  const result = []

  for (const def of GROUP_DEFINITIONS) {
    const groupPages = []
    for (const key of def.pageKeys) {
      if (pageMap.has(key)) {
        groupPages.push(pageMap.get(key))
        usedKeys.add(key)
      }
    }
    if (groupPages.length > 0) {
      result.push({
        ...def,
        pages: groupPages,
      })
    }
  }

  const remainingPages = currentPages.filter((p) => {
    const k = String(p?.page_key || p?.page_url || '').trim().toLowerCase()
    return !usedKeys.has(k)
  })
  if (remainingPages.length > 0) {
    result.push({
      key: 'other',
      title: '其他功能',
      description: '其他功能与辅助页面',
      pages: remainingPages,
    })
  }

  return result
})

const projectName = computed(() => getProjectNameById(projectKey) ?? projectKey)
const isWorkflowExempt = computed(() => {
  const exempt = ['monthly_data_show', 'insulation_pipe_supply_2026']
  return exempt.includes(projectKey)
})
const isClickable = computed(() => {
  return true
})

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
const canApproveCurrentProject = computed(() => auth.canApproveFor(projectKey))
const canRevokeCurrentProject = computed(() => auth.canRevokeFor(projectKey))
const canPublishCurrentProject = computed(() => auth.canPublishFor(projectKey))
const actionsColumnVisible = computed(
  () => canApproveCurrentProject.value || canRevokeCurrentProject.value,
)
const publishButtonVisible = computed(() => canPublishCurrentProject.value)
const publishDisabled = computed(
  () => publishStatus.value?.status === 'published' || workflowLoading.value,
)

const showWorkflowCardForProject = computed(() => {
  if (isWorkflowExempt.value) return false
  return (
    workflowLoading.value ||
    Boolean(workflowError.value) ||
    workflowUnits.value.length > 0 ||
    canApproveCurrentProject.value ||
    canRevokeCurrentProject.value ||
    canPublishCurrentProject.value
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
  const currentProjectKey = String(route.params.projectKey || projectKey || '').trim()

  // 支持“专用调试页面”：若后端 pages 的键是形如 "/debug/..."，则直接导航到该路径
  if (typeof page?.page_url === 'string' && page.page_url.startsWith('/')) {
    return router.push({ path: page.page_url })
  }
  if (currentProjectKey === 'insulation_pipe_supply_2026') {
    return router.push({
      path: `/projects/${encodeURIComponent(currentProjectKey)}/pages/${encodeURIComponent(page.page_key)}`,
    })
  }
  const base = `/projects/${encodeURIComponent(currentProjectKey)}/pages/${encodeURIComponent(page.page_key)}`
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
  const isSpotElectricity = normalizedKey === 'spot_electricity'
  if (isSpotElectricity) {
    const targetName = page?.page_name && page.page_name !== '电力市场数据' ? page.page_name : '电力现货市场数据'
    router.push({
      path: `${base}`,
      query: { pageName: targetName },
    })
    return
  }
  const isDynamicPlan = normalizedKey === 'dynamic_plan'
  if (isDynamicPlan) {
    router.push({
      path: `${base}`,
      query: { pageName: '计划情景分解模型（测试）' },
    })
    return
  }
  const isGlobalManagement = normalizedKey === 'global_management'
  if (isGlobalManagement) {
    router.push({
      path: `${base}`,
      query: { pageName: page.page_name || '全局管理中心' },
    })
    return
  }
  const isDispatchInfo = normalizedKey === 'dispatch_info'
  if (isDispatchInfo) {
    router.push({
      path: `${base}`,
      query: { pageName: page.page_name || '调度信息' },
    })
    return
  }
  const isSmartHeating = normalizedKey === 'smart_heating'
  if (isSmartHeating) {
    router.push({
      path: `${base}`,
      query: { pageName: page.page_name || '智慧供热实时工况' },
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
  font-family: inherit;
  font-size: inherit;
  line-height: inherit;
  color: inherit;
  appearance: none;
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 5px;
  height: 88px; /* 紧凑统一高度 */
  box-sizing: border-box;
  padding: 12px 14px;
  border-radius: 10px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.page-card:hover {
  transform: translateY(-2px);
}

.page-card.is-static {
  cursor: default;
}
.page-card.is-static:hover {
  transform: none;
}

.page-card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--primary-700);
  display: flex;
  align-items: center;
  gap: 6px;
  line-height: 1.3;
  flex-shrink: 0;
}

.page-card-title-icon {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
}

.page-card-title-text {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.page-card-desc {
  font-size: 12px;
  color: #666;
  line-height: 1.4;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
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

/* 分组布局与标题样式 */
.groups-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-group-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.group-header {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding-bottom: 6px;
  border-bottom: 1px solid #eef2f6;
}

.group-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.group-indicator {
  width: 4px;
  height: 16px;
  border-radius: 2px;
  background: var(--neutral-400);
}

.indicator-entry_approval {
  background: linear-gradient(180deg, #60a5fa, #3b82f6);
}

.indicator-monitoring_dashboard {
  background: linear-gradient(180deg, #fb923c, #f97316);
}

.indicator-analysis_management {
  background: linear-gradient(180deg, #a78bfa, #8b5cf6);
}

.group-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
}

.group-desc {
  margin: 0;
  font-size: 12px;
  color: #64748b;
  padding-left: 12px;
}

/* 第一组普通卡片：柔和清雅浅蓝渐变 */
.page-card.card-blue-group {
  background: linear-gradient(135deg, #f8fbff 0%, #eff6ff 100%);
  border: 1px solid #dbeafe;
}

.page-card.card-blue-group:hover {
  background: linear-gradient(135deg, #f0f7ff 0%, #e0effe 100%);
  border-color: #bfdbfe;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.08);
  transform: translateY(-2px);
}

.page-card.card-blue-group .page-card-title {
  color: #1d4ed8;
}

.page-card.card-blue-group .page-card-desc {
  color: #3b82f6;
  opacity: 0.9;
}

/* 第一组核心卡片：每日数据填报（轻快通透渐变蓝） */
.page-card.card-primary-entry {
  background: linear-gradient(135deg, #3b82f6 0%, #4f8ff7 45%, #60a5fa 100%);
  border: 1px solid #60a5fa;
  box-shadow: 0 3px 12px rgba(59, 130, 246, 0.18);
  position: relative;
}

.page-card.card-primary-entry:hover {
  background: linear-gradient(135deg, #2563eb 0%, #3b82f6 45%, #60a5fa 100%);
  box-shadow: 0 6px 18px rgba(59, 130, 246, 0.28);
  transform: translateY(-2px);
  border-color: #93c5fd;
}

.page-card.card-primary-entry .page-card-title {
  color: #ffffff;
}

.page-card.card-primary-entry .page-card-desc {
  color: rgba(255, 255, 255, 0.92);
}

.primary-entry-tag {
  font-size: 10px;
  font-weight: 500;
  padding: 1px 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.25);
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.5);
  margin-left: auto;
  white-space: nowrap;
  flex-shrink: 0;
}

/* 第二组核心卡片：数据看板（轻快温润渐变橙） */
.page-card.card-primary-dashboard {
  background: linear-gradient(135deg, #f97316 0%, #fb923c 50%, #fba053 100%);
  border: 1px solid #fb923c;
  box-shadow: 0 3px 12px rgba(249, 115, 22, 0.18);
  position: relative;
}

.page-card.card-primary-dashboard:hover {
  background: linear-gradient(135deg, #ea580c 0%, #f97316 50%, #fb923c 100%);
  box-shadow: 0 6px 18px rgba(249, 115, 22, 0.28);
  transform: translateY(-2px);
  border-color: #fdba74;
}

.page-card.card-primary-dashboard .page-card-title {
  color: #ffffff;
}

.page-card.card-primary-dashboard .page-card-desc {
  color: rgba(255, 255, 255, 0.94);
}
</style>
