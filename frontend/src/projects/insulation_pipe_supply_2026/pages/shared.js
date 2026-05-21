import '../../daily_report_25_26/styles/theme.css'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'
import { getTubeWorkspaceConfigSummary } from '../../daily_report_25_26/services/api'

export { AppHeader, Breadcrumbs }

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

  return {
    loading,
    errorMessage,
    configSummary,
    breadcrumbItems,
    goProjectPages,
    reloadConfigSummary: loadConfigSummary,
  }
}
