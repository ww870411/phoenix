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
    // 保护正在输入的输入框或文本域，防止打字/输入法切换时被动刷新
    const activeEl = document.activeElement
    if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || activeEl.isContentEditable)) {
      return
    }
    // 如果页面上有任何遮罩弹窗处于打开状态，也避免刷新干扰用户
    if (document.querySelector('.block-modal-overlay') || document.querySelector('.modal-overlay')) {
      return
    }
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

  const managementMode = computed(() => configSummary.value?.management_mode || 'section_1')

  const modeLabels = computed(() => {
    return {
      section_1: '需求主体',
      section1Id: '需求主体ID',
      section1Name: '需求主体名称',
      section1Code: '需求主体编码',
      region: configSummary.value?.labels?.section_2 || '所属区域',
      section: configSummary.value?.labels?.section_3 || '所属标段',
    }
  })

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
    managementMode,
    modeLabels,
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
    label: '✅ 库管已确认',
    class: 'status-completed',
    icon: '✅',
    color: '#10b981',
  },
  cancelled: {
    label: '❌ 已撤销订单',
    class: 'status-cancelled',
    icon: '❌',
    color: '#64748b',
  },
  pending_diff_approve: {
    label: '⚠️ 待差异审批',
    class: 'status-pending-receive',
    icon: '⚠️',
    color: '#f97316',
  }
}

export function getDeliveryStatus(status, isTimeout = false) {
  if (isTimeout) {
    return {
      label: '🕒 超时自动确认',
      class: 'status-pending-warehouse',
      icon: '🕒',
      color: '#a855f7',
    }
  }
  return DELIVERY_STATUS_DICT[status] || {
    label: `未知状态 (${status || '—'})`,
    class: 'status-unknown',
    icon: '❓',
    color: '#94a3b8'
  }
}

/**
 * 穿透跳转至“综合数据查询中心”的“责任主体与人员管辖矩阵”对应人员位置
 * @param {import('vue-router').Router} router Vue Router 实例
 * @param {string|object} userTarget 用户名、经办人姓名、主体名称或包含相关字段的对象
 * @param {string} [projectKey='insulation_pipe_supply_2026'] 项目代号
 */
export function navigateToUserInDirectory(router, userTarget, projectKey = 'insulation_pipe_supply_2026') {
  if (!userTarget || !router) return
  let queryVal = ''
  if (typeof userTarget === 'string') {
    queryVal = userTarget.trim()
  } else if (typeof userTarget === 'object') {
    queryVal = userTarget.username || userTarget.operator || userTarget.contact_name || userTarget.person_name || userTarget.name || ''
  }
  if (!queryVal || queryVal === '—' || queryVal === 'GUEST' || queryVal === '供给端系统' || queryVal === '系统管理员') {
    if (queryVal !== '系统管理员') return
  }

  router.push({
    path: `/projects/${encodeURIComponent(projectKey)}/pages/comprehensive_query`,
    query: {
      tab: 'directory',
      view_mode: 'by_category',
      highlight_user: queryVal,
      _t: Date.now()
    }
  })
}

/**
 * 解析保温管型号规格的主径 DN 与外护管径 (如 DN1400/1600 -> { main: 1400, outer: 1600 })
 * @param {string} modelCode 型号字符串
 * @returns {{ main: number, outer: number }}
 */
export function parsePipeModelDiameters(modelCode) {
  if (!modelCode) return { main: 0, outer: 0 }
  const str = String(modelCode).trim()
  const parts = str.split('/')
  const leftStr = parts[0] || ''
  const rightStr = parts[1] || ''
  const leftMatch = leftStr.match(/(?:[ΦφDN])?\s*(\d+(?:\.\d+)?)/i)
  const rightMatch = rightStr.match(/(?:[ΦφDN])?\s*(\d+(?:\.\d+)?)/i)
  const main = leftMatch ? parseFloat(leftMatch[1]) || 0 : 0
  const outer = rightMatch ? parseFloat(rightMatch[1]) || 0 : 0
  return { main, outer }
}

/**
 * 按照保温管口径大小进行严格降序排序 (大管径在前，小管径在后)
 * @param {Array} modelList 包含 pipe_model_id / pipeModelId / pipe_model_name / pipeModelName 的数组
 * @returns {Array} 降序排列后的新数组
 */
export function sortPipeModelsByDiameterDesc(modelList) {
  return [...(modelList || [])].sort((a, b) => {
    const codeA = a?.pipe_model_id || a?.pipeModelId || a?.pipe_model_name || a?.pipeModelName || a
    const codeB = b?.pipe_model_id || b?.pipeModelId || b?.pipe_model_name || b?.pipeModelName || b
    const dA = parsePipeModelDiameters(codeA)
    const dB = parsePipeModelDiameters(codeB)
    if (dB.main !== dA.main) {
      return dB.main - dA.main
    }
    if (dB.outer !== dA.outer) {
      return dB.outer - dA.outer
    }
    return String(codeA || '').localeCompare(String(codeB || ''))
  })
}


