import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../projects/daily_report_25_26/store/auth'

const routes = [
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/login',
    component: () => import('../pages/LoginView.vue'),
  },
  {
    path: '/projects',
    component: () => import('../pages/ProjectSelectView.vue'),
  },
  {
    path: '/projects/:projectKey',
    component: () => import('../pages/ProjectEntryView.vue'),
  },
  {
    path: '/projects/page_showcase/view/:fileName',
    component: () => import('../projects/page_showcase/pages/PageShowcaseViewerView.vue'),
  },
  {
    path: '/projects/monthly_data_show/import-workspace',
    component: () => import('../projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue'),
  },
  {
    path: '/projects/monthly_data_show/query-tool',
    component: () => import('../projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue'),
  },
  {
    path: '/projects/:projectKey/spring-dashboard',
    component: () => import('../projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue'),
  },
  {
    path: '/projects/:projectKey/pages',
    component: () => import('../projects/daily_report_25_26/pages/PageSelectView.vue'),
  },
  {
    path: '/projects/insulation_pipe_supply_2026/pages/:pageKey',
    component: () => import('../projects/insulation_pipe_supply_2026/pages/TubeProjectPageRouterView.vue'),
  },
  {
    path: '/projects/:projectKey/pages/:pageKey/sheets',
    component: () => import('../projects/daily_report_25_26/pages/Sheets.vue'),
  },
  {
    path: '/projects/:projectKey/pages/:pageKey/dashboard',
    component: () => import('../projects/daily_report_25_26/pages/DashBoard.vue'),
  },
  {
    path: '/projects/:projectKey/pages/:pageKey/sheets/:sheetKey',
    component: () => import('../projects/daily_report_25_26/pages/DataEntryView.vue'),
  },
  {
    path: '/projects/:projectKey/pages/:pageKey/approval/:sheetKey',
    component: () => import('../projects/daily_report_25_26/pages/ApprovalView.vue'),
  },
  {
    path: '/projects/:projectKey/pages/:pageKey/display',
    component: () => import('../projects/daily_report_25_26/pages/DisplayView.vue'),
  },
  {
    path: '/projects/:projectKey/pages/:pageKey/data-analysis',
    component: () => import('../projects/daily_report_25_26/pages/DataAnalysisView.vue'),
  },
  {
    path: '/admin-console',
    component: () => import('../projects/daily_report_25_26/pages/AdminConsoleView.vue'),
  },
  {
    path: '/admin-file-editor',
    component: () => import('../projects/daily_report_25_26/pages/AdminFileEditorWindow.vue'),
  },
  {
    path: '/projects/:projectKey/pages/:pageKey/display/:sheetKey',
    component: () => import('../projects/daily_report_25_26/pages/DisplayRuntimeView.vue'),
  },
  {
    path: '/debug/runtime-eval',
    component: () => import('../projects/daily_report_25_26/pages/RuntimeEvalDebug.vue'),
  },
  {
    path: '/forbidden',
    component: () => import('../pages/ForbiddenView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

function makeForbiddenRedirect(to, projectKey = '', pageKey = '') {
  return {
    path: '/forbidden',
    query: {
      projectKey: projectKey || '',
      pageKey: pageKey || '',
      from: to.fullPath || to.path,
    },
  }
}

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.bootstrap()

  // 1. 基础登录状态守卫
  if (to.path === '/') {
    return auth.isAuthenticated ? '/projects' : '/login'
  }
  if (to.path !== '/login' && to.path !== '/dashboard' && !auth.isAuthenticated) {
    return '/login'
  }
  if (to.path === '/login' && auth.isAuthenticated) {
    return '/projects'
  }
  if (to.path === '/projects' || to.path === '/login' || to.path === '/forbidden') {
    return true
  }

  // 2. 全局管理后台权限校验
  if (to.path === '/admin-console' || to.path === '/admin-file-editor') {
    if (!auth.canAccessAdminConsole) {
      return makeForbiddenRedirect(to, '', 'admin_console')
    }
    return true
  }

  // 3. 独立非参数化子项目页面权限校验
  if (to.path.startsWith('/projects/monthly_data_show/')) {
    const isImportWorkspace = to.path === '/projects/monthly_data_show/import-workspace'
    const isQueryTool = to.path === '/projects/monthly_data_show/query-tool'

    if (isImportWorkspace) {
      if (!auth.hasPageAccess('monthly_data_show', 'projects_monthly_data_show_import_workspace')) {
        return makeForbiddenRedirect(to, 'monthly_data_show', 'projects_monthly_data_show_import_workspace')
      }
      return true
    }

    if (isQueryTool) {
      if (!auth.hasPageAccess('monthly_data_show', 'projects_monthly_data_show_query_tool')) {
        return makeForbiddenRedirect(to, 'monthly_data_show', 'projects_monthly_data_show_query_tool')
      }
      return true
    }
  }

  if (to.path.startsWith('/projects/page_showcase/')) {
    if (!auth.hasPageAccess('page_showcase', 'workspace')) {
      return makeForbiddenRedirect(to, 'page_showcase', 'workspace')
    }
    return true
  }

  if (to.path === '/debug/runtime-eval') {
    if (!auth.hasPageAccess('daily_report_25_26', 'debug_runtime_eval')) {
      return makeForbiddenRedirect(to, 'daily_report_25_26', 'debug_runtime_eval')
    }
    return true
  }

  // 4. 春节看板专属路由校验
  if (to.path.endsWith('/spring-dashboard')) {
    const projectKey = String(to.params.projectKey || 'daily_report_spring_festval_2026')
    if (!auth.hasPageAccess(projectKey, 'mini_entry')) {
      return makeForbiddenRedirect(to, projectKey, 'mini_entry')
    }
    return true
  }

  // 5. 保温管物流链专属子路由校验
  if (to.path.startsWith('/projects/insulation_pipe_supply_2026/pages/')) {
    const pageKey = String(to.params.pageKey || '').trim()
    if (!auth.hasPageAccess('insulation_pipe_supply_2026', pageKey)) {
      return makeForbiddenRedirect(to, 'insulation_pipe_supply_2026', pageKey)
    }
    return true
  }

  // 6. 通用项目子页面路由（含 sheets、dashboard、data-entry、approval、display、data-analysis 等）
  const projectKey = String(to.params.projectKey || '').trim()
  const pageKey = String(to.params.pageKey || '').trim()

  if (projectKey && pageKey) {
    if (!auth.hasProjectAccess(projectKey)) {
      return makeForbiddenRedirect(to, projectKey, '')
    }
    if (!auth.hasPageAccess(projectKey, pageKey)) {
      return makeForbiddenRedirect(to, projectKey, pageKey)
    }
    return true
  }

  // 7. 项目二级页面选择大厅与单入口校验
  if (projectKey && (to.path === `/projects/${projectKey}/pages` || to.path === `/projects/${projectKey}`)) {
    if (!auth.hasProjectAccess(projectKey)) {
      return makeForbiddenRedirect(to, projectKey, '')
    }
    return true
  }

  return true
})

router.onError((error, to) => {
  const message = String(error?.message || error || '')
  const isDynamicImportError =
    message.includes('Failed to fetch dynamically imported module') ||
    (error?.name === 'TypeError' && message.includes('fetch'))

  if (isDynamicImportError && typeof window !== 'undefined') {
    console.warn('[Router] 检测到动态模块加载中断或过期，正在自动重试并同步最新模块...', error)
    const storageKey = 'phoenix_last_dynamic_import_retry'
    const lastRetry = sessionStorage.getItem(storageKey)
    const now = Date.now()
    if (!lastRetry || now - Number(lastRetry) > 6000) {
      sessionStorage.setItem(storageKey, String(now))
      const targetUrl = to?.fullPath || window.location.href
      window.location.href = targetUrl
    }
  }
})

export default router
