<template>
  <div class="display-view">
    <AppHeader />
    <main class="display-main">
      <Breadcrumbs :items="breadcrumbItems" />
      <section class="card elevated display-block">
        <header class="card-header">
          <h2>{{ pageDisplayName }}</h2>
          <p class="display-subtitle">项目：{{ projectName }} ｜ 数据源：{{ shortConfig }}</p>
        </header>

        <div class="card-grid">
          <button class="card elevated display-card" @click="select('overview')">
            <div class="display-card-title">仪表盘总览（占位）</div>
            <div class="display-card-desc">展示关键指标的当日与趋势概览（后续基于数据源渲染）。</div>
          </button>

          <button class="card elevated display-card" @click="select('tableA')">
            <div class="display-card-title">展示表一（占位）</div>
            <div class="display-card-desc">固定展示表：供热/发电等核心指标汇总。</div>
          </button>

          <button class="card elevated display-card" @click="select('tableB')">
            <div class="display-card-title">展示表二（占位）</div>
            <div class="display-card-desc">固定展示表：单位维度对比与趋势。</div>
          </button>

          <button class="card elevated display-card" @click="select('tableC')">
            <div class="display-card-title">展示表三（占位）</div>
            <div class="display-card-desc">固定展示表：煤炭库存/能耗相关指标概览。</div>
          </button>
        </div>

        <div v-if="selected" class="placeholder-panel">
          <h3 class="panel-title">{{ selectedTitle }}</h3>
          <p class="panel-tip">占位渲染：后续将根据“数据源”文件定义的字段，渲染只读网格/图表。</p>
          <ul class="panel-list">
            <li>数据来源：{{ config }}</li>
            <li>项目：{{ projectKey }}</li>
            <li>页面：{{ pageKey }}（{{ pageDisplayName }}）</li>
          </ul>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { getProjectNameById } from '../composables/useProjects'

const route = useRoute()
const projectKey = String(route.params.projectKey ?? '')
const pageKey = String(route.params.pageKey ?? '')
const config = computed(() => (typeof route.query.config === 'string' ? route.query.config : ''))
const pageDisplayName = computed(() => (typeof route.query.pageName === 'string' && route.query.pageName.trim() ? route.query.pageName.trim() : pageKey || '展示页面'))
const projectName = computed(() => getProjectNameById(projectKey) ?? projectKey)

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: projectName.value, to: `/projects/${encodeURIComponent(projectKey)}/pages` },
  { label: pageDisplayName.value, to: null },
])

const shortConfig = computed(() => {
  const v = config.value || ''
  const idx = v.lastIndexOf('/')
  return idx >= 0 ? v.slice(idx + 1) : v
})

const selected = ref('')
function select(key) {
  selected.value = key
}

const selectedTitle = computed(() => {
  switch (selected.value) {
    case 'overview':
      return '仪表盘总览（占位）'
    case 'tableA':
      return '展示表一（占位）'
    case 'tableB':
      return '展示表二（占位）'
    case 'tableC':
      return '展示表三（占位）'
    default:
      return ''
  }
})
</script>

<style scoped>
.display-main { padding: 24px; max-width: 960px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }
.display-block { display: flex; flex-direction: column; gap: 24px; }
.display-subtitle { margin-top: 8px; font-size: 14px; color: var(--neutral-500); }
.display-card { text-align: left; cursor: pointer; display: flex; flex-direction: column; gap: 6px; transition: transform 0.2s ease; }
.display-card:hover { transform: translateY(-2px); }
.display-card-title { font-size: 18px; font-weight: 600; color: var(--primary-700); }
.display-card-desc { font-size: 14px; color: var(--neutral-500); }
.placeholder-panel { margin-top: 8px; padding: 16px; border: 1px dashed var(--border); border-radius: var(--radius); background: var(--card-bg); }
.panel-title { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
.panel-list { margin-left: 18px; }
</style>
