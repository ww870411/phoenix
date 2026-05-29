import '../../daily_report_25_26/styles/theme.css'
import { computed, onActivated, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'
import { getTubeWorkspaceConfigSummary } from '../../daily_report_25_26/services/api'

export { AppHeader, Breadcrumbs }

export function useTubeRealtimeRefresh(refreshFn, options = {}) {
  let refreshPromise = null

  async function runRefresh() {
    if (refreshPromise) {
      return refreshPromise
    }
    refreshPromise = Promise.resolve(refreshFn()).finally(() => {
      refreshPromise = null
    })
    return refreshPromise
  }

  function triggerRefresh() {
    runRefresh().catch(() => {})
  }

  function handleVisibilityChange() {
    if (document.visibilityState === 'visible') {
      triggerRefresh()
    }
  }

  function handleWindowFocus() {
    triggerRefresh()
  }

  onMounted(() => {
    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('focus', handleWindowFocus)
  })

  onActivated(() => {
    triggerRefresh()
  })

  onBeforeUnmount(() => {
    document.removeEventListener('visibilitychange', handleVisibilityChange)
    window.removeEventListener('focus', handleWindowFocus)
  })

  return {
    triggerTubeRealtimeRefresh: runRefresh,
  }
}

export function useTubePageShell(currentLabel) {
  const route = useRoute()
  const router = useRouter()
  const projectKey = computed(() => String(route.params.projectKey || 'insulation_pipe_supply_2026'))
  const loading = ref(false)
  const errorMessage = ref('')
  const configSummary = ref(null)

  const breadcrumbItems = computed(() => [
    { label: '项目选择', to: '/projects' },
    { label: '2026年度保温管物流链管理系统', to: `/projects/${encodeURIComponent(projectKey.value)}/pages` },
    { label: currentLabel, to: null },
  ])

  function goProjectPages() {
    router.push(`/projects/${encodeURIComponent(projectKey.value)}/pages`)
  }

  async function loadConfigSummary() {
    loading.value = true
    errorMessage.value = ''
    try {
      configSummary.value = await getTubeWorkspaceConfigSummary(projectKey.value)
    } catch (error) {
      console.error(error)
      errorMessage.value = error instanceof Error ? error.message : '读取 tube 配置摘要失败'
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    loadConfigSummary()
  })

  useTubeRealtimeRefresh(loadConfigSummary)

  return {
    loading,
    errorMessage,
    configSummary,
    breadcrumbItems,
    goProjectPages,
    reloadConfigSummary: loadConfigSummary,
  }
}

// --- 统一物流状态字典与动作配置 (Unified Logistics Status Dictionary) ---
export const DELIVERY_STATUS_DICT = {
  pending_arrival: {
    label: '🚚 待确认到货',
    class: 'status-pending-arrival',
    icon: '🚚',
    color: '#eab308',
  },
  pending_receive: {
    label: '👷 待施工接收',
    class: 'status-pending-receive',
    icon: '👷',
    color: '#3b82f6',
  },
  pending_warehouse: {
    label: '🏢 待库管确认',
    class: 'status-pending-warehouse',
    icon: '🏢',
    color: '#a855f7',
  },
  completed: {
    label: '✅ 已入库结清',
    class: 'status-completed',
    icon: '✅',
    color: '#10b981',
  },
  cancelled: {
    label: '❌ 已撤销订单',
    class: 'status-cancelled',
    icon: '❌',
    color: '#64748b',
  }
}

export function getDeliveryStatus(status) {
  return DELIVERY_STATUS_DICT[status] || {
    label: `未知状态 (${status || '—'})`,
    class: 'status-unknown',
    icon: '❓',
    color: '#94a3b8'
  }
}
