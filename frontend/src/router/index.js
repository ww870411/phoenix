import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../daily_report_25_26/store/auth'

const routes = [
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/login',
    component: () => import('../daily_report_25_26/pages/LoginView.vue'),
  },
  {
    path: '/projects',
    component: () => import('../daily_report_25_26/pages/ProjectSelectView.vue'),
  },
  {
    path: '/projects/:projectKey/pages',
    component: () => import('../daily_report_25_26/pages/PageSelectView.vue'),
  },
  {
    path: '/projects/:projectKey/pages/:pageKey/sheets',
    component: () => import('../daily_report_25_26/pages/Sheets.vue'),
  },
  {
    path: '/projects/:projectKey/pages/:pageKey/sheets/:sheetKey',
    component: () => import('../daily_report_25_26/pages/DataEntryView.vue'),
  },
  {
    path: '/projects/:projectKey/pages/:pageKey/approval/:sheetKey',
    component: () => import('../daily_report_25_26/pages/ApprovalView.vue'),
  },
  {
    path: '/projects/:projectKey/pages/:pageKey/display',
    component: () => import('../daily_report_25_26/pages/DisplayView.vue'),
  },
  {
    path: '/projects/:projectKey/pages/:pageKey/display/:sheetKey',
    component: () => import('../daily_report_25_26/pages/DisplayRuntimeView.vue'),
  },
  {
    path: '/debug/runtime-eval',
    component: () => import('../daily_report_25_26/pages/RuntimeEvalDebug.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.bootstrap()
  if (to.path !== '/login' && !auth.isAuthenticated) {
    return '/login'
  }
  if (to.path === '/login' && auth.isAuthenticated) {
    return '/projects'
  }
  return true
})

export default router
