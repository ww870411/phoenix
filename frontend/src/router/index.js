import { createRouter, createWebHistory } from 'vue-router'

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
    path: '/projects/:projectKey/pages/:pageKey/display',
    component: () => import('../daily_report_25_26/pages/DisplayView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

export default router
