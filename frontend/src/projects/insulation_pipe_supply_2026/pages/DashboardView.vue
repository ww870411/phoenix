<template>
  <div class="tube-page-root">
    <AppHeader />
    <main class="tube-page-main container">
      <Breadcrumbs :items="breadcrumbItems" />
      <header class="topbar">
        <div>
          <h2>全局数据看板</h2>
          <p class="sub">首版先接通配置摘要与测试主体统计，为后续汇总卡和图形展示打底。</p>
        </div>
        <div class="topbar-actions">
          <button class="btn ghost" type="button" @click="goProjectPages">返回功能页</button>
          <button class="btn primary" type="button" :disabled="loading" @click="reloadConfigSummary">
            {{ loading ? '刷新中...' : '刷新配置摘要' }}
          </button>
        </div>
      </header>

      <p v-if="errorMessage" class="page-error">{{ errorMessage }}</p>

      <section class="card elevated summary-grid">
        <div class="summary-item">
          <div class="summary-label">供给主体</div>
          <div class="summary-value">{{ configSummary?.summary?.supply_entity_count ?? 0 }}</div>
        </div>
        <div class="summary-item">
          <div class="summary-label">需求主体</div>
          <div class="summary-value">{{ configSummary?.summary?.demand_entity_count ?? 0 }}</div>
        </div>
        <div class="summary-item">
          <div class="summary-label">保温管型号</div>
          <div class="summary-value">{{ configSummary?.summary?.pipe_model_count ?? 0 }}</div>
        </div>
        <div class="summary-item">
          <div class="summary-label">施工单位</div>
          <div class="summary-value">{{ configSummary?.summary?.construction_unit_count ?? 0 }}</div>
        </div>
      </section>

      <section class="card elevated">
        <div class="card-header">首版定位</div>
        <ul class="info-list">
          <li>只查看，不承载发货、确认或修改操作。</li>
          <li>汇总优先，图形便利，警示为辅。</li>
          <li>后续将在此接入库存、缺口、状态和风险聚合接口。</li>
        </ul>
      </section>
    </main>
  </div>
</template>

<script setup>
import { AppHeader, Breadcrumbs, useTubePageShell } from './shared'

const {
  loading,
  errorMessage,
  configSummary,
  breadcrumbItems,
  goProjectPages,
  reloadConfigSummary,
} = useTubePageShell('全局数据看板')
</script>

<style scoped>
.tube-page-root { min-height: 100vh; background: var(--bg); }
.tube-page-main { display: flex; flex-direction: column; gap: 16px; padding-top: 18px; padding-bottom: 24px; }
.topbar-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.page-error { margin: 0; color: var(--danger); }
.summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }
.summary-item { padding: 10px 4px; }
.summary-label { font-size: 13px; color: var(--muted); }
.summary-value { margin-top: 8px; font-size: 30px; font-weight: 800; color: var(--primary-700); }
.info-list { margin: 0; padding-left: 18px; line-height: 1.7; }
</style>
