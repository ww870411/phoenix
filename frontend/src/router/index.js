import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../daily_report_25_26/pages/LoginView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/projects',
    name: 'projects',
    component: () => import('../daily_report_25_26/pages/ProjectSelectView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/projects/:projectKey/sheets',
    name: 'dashboard',
    component: () => import('../daily_report_25_26/pages/Sheets.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/projects/:projectKey/sheets/:sheetKey',
    name: 'data-entry',
    component: () => import('../daily_report_25_26/pages/DataEntryView.vue'),
    meta: { requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('phoenix_token');
  if (to.meta.requiresAuth && !token) {
    next({ name: 'login' });
  } else if (to.name === 'login' && token) {
    next({ name: 'projects' });
  } else {
    next();
  }
});

export default router
