<template>
  <div class="tube-page-root">
    <AppHeader />
    <main class="tube-page-main container">
      <Breadcrumbs :items="breadcrumbItems" />
      <header class="topbar">
        <div>
          <h2>库管员管理入口</h2>
          <p class="sub">首版将承载库管台账、库管确认和手续留痕，不承载其他修改操作。</p>
        </div>
        <div class="topbar-actions">
          <button class="btn ghost" type="button" @click="goProjectPages">返回功能页</button>
        </div>
      </header>

      <p v-if="errorMessage" class="page-error">{{ errorMessage }}</p>

      <section class="card elevated">
        <div class="card-header">施工单位测试主体</div>
        <div v-if="loading" class="page-state">正在读取配置摘要...</div>
        <div v-else class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>施工单位</th>
                <th>联系人</th>
                <th>绑定换热站</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="unit in configSummary?.construction_units || []" :key="unit.unit_id">
                <td>{{ unit.unit_name }}</td>
                <td>{{ unit.contact_name }}</td>
                <td>{{ resolveBoundStations(unit.unit_id).join('、') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card elevated">
        <div class="card-header">首版能力占位</div>
        <ul class="info-list">
          <li>查看库管台账</li>
          <li>执行库管确认</li>
          <li>记录手续备注</li>
          <li>不开放发货、到货、接收、计划和使用修改</li>
        </ul>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { AppHeader, Breadcrumbs, useTubePageShell } from './shared'

const {
  loading,
  errorMessage,
  configSummary,
  breadcrumbItems,
  goProjectPages,
} = useTubePageShell('库管员管理入口')

const assignmentMap = computed(() => {
  const mapping = new Map()
  for (const item of configSummary.value?.construction_assignments || []) {
    mapping.set(item.unit_id, item.station_names || [])
  }
  return mapping
})

function resolveBoundStations(unitId) {
  return assignmentMap.value.get(unitId) || []
}
</script>

<style scoped>
.tube-page-root { min-height: 100vh; background: var(--bg); }
.tube-page-main { display: flex; flex-direction: column; gap: 16px; padding-top: 18px; padding-bottom: 24px; }
.topbar-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.page-error { margin: 0; color: var(--danger); }
.page-state { padding: 28px 12px; text-align: center; color: var(--muted); }
.info-list { margin: 0; padding-left: 18px; line-height: 1.7; }
</style>
