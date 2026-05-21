<template>
  <div class="tube-page-root">
    <AppHeader />
    <main class="tube-page-main container">
      <Breadcrumbs :items="breadcrumbItems" />
      <header class="topbar">
        <div>
          <h2>供给侧管理入口</h2>
          <p class="sub">首版将承载需求查看、发货登记、发货进度和发货撤销能力。</p>
        </div>
        <div class="topbar-actions">
          <button class="btn ghost" type="button" @click="goProjectPages">返回功能页</button>
        </div>
      </header>

      <p v-if="errorMessage" class="page-error">{{ errorMessage }}</p>

      <section class="card elevated">
        <div class="card-header">供给主体测试主体</div>
        <div v-if="loading" class="page-state">正在读取配置摘要...</div>
        <div v-else class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>供给主体</th>
                <th>联系人</th>
                <th>联系电话</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="entity in configSummary?.supply_entities || []" :key="entity.entity_id">
                <td>{{ entity.entity_name }}</td>
                <td>{{ entity.contact_name }}</td>
                <td>{{ entity.contact_phone }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card elevated">
        <div class="card-header">首版能力占位</div>
        <ul class="info-list">
          <li>查看全部需求和缺口</li>
          <li>新增本供给主体发货记录</li>
          <li>查看本供给主体发货进度</li>
          <li>仅允许在“已发货待到货”状态撤销发货</li>
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
} = useTubePageShell('供给侧管理入口')
</script>

<style scoped>
.tube-page-root { min-height: 100vh; background: var(--bg); }
.tube-page-main { display: flex; flex-direction: column; gap: 16px; padding-top: 18px; padding-bottom: 24px; }
.topbar-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.page-error { margin: 0; color: var(--danger); }
.page-state { padding: 28px 12px; text-align: center; color: var(--muted); }
.info-list { margin: 0; padding-left: 18px; line-height: 1.7; }
</style>
