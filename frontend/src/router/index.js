import { createRouter, createWebHistory } from 'vue-router'

// 暂无业务路由占位，后续接入各项目模块路由
const routes = []

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

export default router
