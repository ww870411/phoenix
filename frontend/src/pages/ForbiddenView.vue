<template>
  <div class="forbidden-page">
    <AppHeader />
    <main class="forbidden-main">
      <div class="forbidden-container">
        <Breadcrumbs :items="breadcrumbItems" />

        <div class="card elevated forbidden-card">
          <div class="forbidden-icon-badge">
            <span class="icon">🔒</span>
          </div>

          <h2 class="forbidden-title">访问受限 (403 Forbidden)</h2>

          <p class="forbidden-desc">
            抱歉，您当前登录的角色 <strong>「{{ userGroupText }}」</strong> 尚未获得
            <span v-if="targetResourceText"><strong>「{{ targetResourceText }}」</strong></span>
            <span v-else>该页面</span>
            的访问权限。
          </p>

          <div class="forbidden-actions">
            <button class="btn primary btn-countdown" type="button" @click="handleImmediateReturn">
              <span class="btn-text">⬅️ 立即返回{{ returnTargetShortLabel }}</span>
              <span class="countdown-badge">{{ countdown }}s</span>
            </button>
            <button v-if="hasProjectLobbyOption" class="btn ghost" type="button" @click="goToProjectSelect">
              🏠 返回项目选择大厅
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '../projects/daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../projects/daily_report_25_26/components/Breadcrumbs.vue'
import { useAuthStore } from '../projects/daily_report_25_26/store/auth'
import { getProjectNameById, ensureProjectsLoaded } from '../projects/daily_report_25_26/composables/useProjects'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const countdown = ref(5)
let timer = null

const projectKey = computed(() => String(route.query.projectKey || '').trim())
const pageKey = computed(() => String(route.query.pageKey || '').trim())
const fromPath = computed(() => String(route.query.from || '').trim())

const PAGE_NAME_MAP = {
  admin_console: '全局管理后台',
  admin_file_editor: '后台文件编辑器',
  big_screen: '数字指挥大屏',
  dashboard: '全局数据看板',
  history_query: '历史数据查询',
  gis_map: '焊口与表计 GIS 地图标注',
  global_management: '全局管理入口',
  demand_management: '需求侧管理入口',
  supply_management: '供给侧管理入口',
  warehouse_management: '库管员管理入口',
  data_entry: '每日数据填报页面',
  data_approval: '数据审批页面',
  data_show: '数据展示页面',
  constant_data: '常量指标页面',
  data_analysis: '数据分析页面',
  debug_runtime_eval: '运行时表达式调试工具',
  mini_entry: '（春节期间）数据看板生成页面',
  projects_monthly_data_show_import_workspace: '月报导入工作台',
  projects_monthly_data_show_query_tool: '月报数据查询工具',
  workspace: '工作台主页',
}

const userGroupText = computed(() => {
  return auth.user?.group || auth.session?.group || '当前账号角色'
})

const targetResourceText = computed(() => {
  if (pageKey.value && PAGE_NAME_MAP[pageKey.value]) {
    return PAGE_NAME_MAP[pageKey.value]
  }
  if (projectKey.value && !pageKey.value) {
    return getProjectNameById(projectKey.value) || projectKey.value
  }
  return pageKey.value || ''
})

const returnTargetUrl = computed(() => {
  if (projectKey.value && auth.hasProjectAccess(projectKey.value)) {
    return `/projects/${encodeURIComponent(projectKey.value)}/pages`
  }
  return '/projects'
})

const returnTargetShortLabel = computed(() => {
  if (projectKey.value && auth.hasProjectAccess(projectKey.value)) {
    return '页面选择'
  }
  return '项目选择大厅'
})

const hasProjectLobbyOption = computed(() => {
  return returnTargetUrl.value !== '/projects'
})

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '403 访问受限', to: null },
])

function handleImmediateReturn() {
  clearCountdown()
  router.replace(returnTargetUrl.value)
}

function goToProjectSelect() {
  clearCountdown()
  router.replace('/projects')
}

function clearCountdown() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

function startCountdown() {
  clearCountdown()
  countdown.value = 5
  timer = setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) {
      clearCountdown()
      router.replace(returnTargetUrl.value)
    }
  }, 1000)
}

onMounted(() => {
  ensureProjectsLoaded().catch(() => {})
  startCountdown()
})

onUnmounted(() => {
  clearCountdown()
})
</script>

<style scoped>
.forbidden-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
}

.forbidden-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
}

.forbidden-container {
  width: 100%;
  max-width: 520px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.forbidden-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  padding: 44px 36px 36px 36px;
  text-align: center;
  box-shadow: 0 12px 30px -10px rgba(15, 23, 42, 0.08), 0 4px 6px -2px rgba(15, 23, 42, 0.04);
}

.forbidden-icon-badge {
  width: 72px;
  height: 72px;
  margin: 0 auto 20px auto;
  border-radius: 20px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  display: flex;
  align-items: center;
  justify-content: center;
}

.forbidden-icon-badge .icon {
  font-size: 36px;
}

.forbidden-title {
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 14px 0;
  letter-spacing: -0.02em;
}

.forbidden-desc {
  font-size: 15px;
  color: #64748b;
  line-height: 1.6;
  margin: 0 0 28px 0;
}

.forbidden-desc strong {
  color: #0284c7;
  font-weight: 600;
}

.forbidden-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 320px;
  margin: 0 auto;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 20px;
  font-size: 14px;
  font-weight: 600;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.18s ease;
  border: 1px solid transparent;
  white-space: nowrap;
}

.btn.primary {
  background: #0284c7;
  color: #ffffff;
  box-shadow: 0 4px 10px rgba(2, 132, 199, 0.2);
}

.btn.primary:hover {
  background: #0369a1;
  box-shadow: 0 6px 14px rgba(2, 132, 199, 0.28);
}

.countdown-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 30px;
  height: 20px;
  padding: 0 6px;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.22);
  border: 1px solid rgba(255, 255, 255, 0.35);
  font-size: 12px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 0.02em;
}

.btn.ghost {
  background: #f8fafc;
  border-color: #cbd5e1;
  color: #334155;
}

.btn.ghost:hover {
  background: #f1f5f9;
  color: #0f172a;
}

@media (max-width: 640px) {
  .forbidden-card {
    padding: 32px 20px 24px 20px;
    border-radius: 16px;
  }
  .forbidden-title {
    font-size: 19px;
  }
  .forbidden-desc {
    font-size: 13px;
  }
  .forbidden-actions {
    max-width: 100%;
  }
}
</style>
