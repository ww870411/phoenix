<template>
  <div v-if="!isAuthorized" class="tube-unauthorized-container">
    <div class="tube-unauthorized-card">
      <div class="unauthorized-icon">🔒</div>
      <h2 class="unauthorized-title">访问受限 (403 Forbidden)</h2>
      <p class="unauthorized-desc">
        当前登录角色 <strong>「{{ userGroupLabel }}」</strong> 尚未获得页面 <strong>「{{ pageTitle }}」</strong> 的访问权限。
      </p>
      <div class="unauthorized-actions">
        <button class="btn primary" type="button" @click="goToPageSelect">⬅️ 返回功能页面选择</button>
        <button class="btn ghost" type="button" @click="goToProjectSelect">🏠 返回项目选择大厅</button>
      </div>
    </div>
  </div>
  <component :is="currentComponent" v-else-if="currentComponent" />
  <div v-else class="tube-route-state">未找到对应页面。</div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../daily_report_25_26/store/auth'

import DashboardView from './DashboardView.vue'
import BigScreenDashboardView from './BigScreenDashboardView.vue'
import DemandManagementView from './DemandManagementView.vue'
import GlobalManagementView from './GlobalManagementView.vue'
import SupplyManagementView from './SupplyManagementView.vue'
import WarehouseManagementView from './WarehouseManagementView.vue'
import HistoryQueryView from './HistoryQueryView.vue'
import GisMapView from './GisMapView.vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const pageKey = computed(() => String(route.params.pageKey || '').trim())

const pageComponentMap = {
  dashboard: DashboardView,
  big_screen: BigScreenDashboardView,
  comprehensive_query: HistoryQueryView,
  history_query: HistoryQueryView, // 兼容历史路由
  gis_map: GisMapView,
  global_management: GlobalManagementView,
  demand_management: DemandManagementView,
  supply_management: SupplyManagementView,
  warehouse_management: WarehouseManagementView,
}

const pageTitleMap = {
  dashboard: '全局数据看板',
  big_screen: '数字指挥大屏',
  comprehensive_query: '综合数据查询中心',
  history_query: '综合数据查询中心',
  gis_map: '焊口与表计 GIS 地图标注',
  global_management: '全局管理入口',
  demand_management: '需求侧管理入口',
  supply_management: '供给侧管理入口',
  warehouse_management: '库管员管理入口',
}

const pageTitle = computed(() => pageTitleMap[pageKey.value] || pageKey.value)
const userGroupLabel = computed(() => auth.user?.group || auth.session?.group || '未分配角色')

// 严格基于 permissions/insulation_pipe_supply_2026.json 中的 page_access 进行校验
const isAuthorized = computed(() => {
  if (!pageKey.value) return false
  return auth.hasPageAccess('insulation_pipe_supply_2026', pageKey.value)
})

const currentComponent = computed(() => {
  if (!isAuthorized.value) return null
  return pageComponentMap[pageKey.value] || null
})

function goToPageSelect() {
  router.replace('/projects/insulation_pipe_supply_2026/pages')
}

function goToProjectSelect() {
  router.replace('/projects')
}
</script>

<style scoped>
.tube-route-state {
  min-height: 40vh;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  font-size: 14px;
  padding: 24px;
}

.tube-unauthorized-container {
  min-height: 70vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
}

.tube-unauthorized-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04);
  border-radius: 16px;
  padding: 40px 32px;
  max-width: 480px;
  width: 100%;
  text-align: center;
}

.unauthorized-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.unauthorized-title {
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 12px 0;
}

.unauthorized-desc {
  font-size: 14px;
  color: #64748b;
  line-height: 1.6;
  margin: 0 0 28px 0;
}

.unauthorized-desc strong {
  color: #0284c7;
}

.unauthorized-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10px 18px;
  font-size: 14px;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.18s ease;
  border: 1px solid transparent;
}

.btn.primary {
  background: #0284c7;
  color: #ffffff;
}

.btn.primary:hover {
  background: #0369a1;
}

.btn.ghost {
  background: #f8fafc;
  border-color: #cbd5e1;
  color: #475569;
}

.btn.ghost:hover {
  background: #f1f5f9;
  color: #0f172a;
}
</style>
