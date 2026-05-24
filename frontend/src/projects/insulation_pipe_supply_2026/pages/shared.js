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
