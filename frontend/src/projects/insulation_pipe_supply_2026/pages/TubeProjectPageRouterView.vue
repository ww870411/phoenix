<template>
  <component :is="currentComponent" v-if="currentComponent" />
  <div v-else class="tube-route-state">未找到对应页面。</div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import DashboardView from './DashboardView.vue'
import DemandManagementView from './DemandManagementView.vue'
import GlobalManagementView from './GlobalManagementView.vue'
import SupplyManagementView from './SupplyManagementView.vue'
import WarehouseManagementView from './WarehouseManagementView.vue'

const route = useRoute()
const pageKey = computed(() => String(route.params.pageKey || '').trim())

const pageComponentMap = {
  dashboard: DashboardView,
  global_management: GlobalManagementView,
  demand_management: DemandManagementView,
  supply_management: SupplyManagementView,
  warehouse_management: WarehouseManagementView,
}

const currentComponent = computed(() => pageComponentMap[pageKey.value] || null)
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
</style>
