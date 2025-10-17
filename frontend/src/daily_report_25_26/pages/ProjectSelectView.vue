<template>
  <div>
    <AppHeader />
    <div class="container">
    <header class="topbar">
      <div>
        <h2>项目选择</h2>
        <div class="sub">选择需要进入的项目空间</div>
      </div>
    </header>
    <Breadcrumbs />
    <div class="card-grid">
      <div class="card clickable elevated" @click="enter(projects[0])">
        <div class="card-header">Phoenix 项目</div>
        <div class="name">daily_report_25_26</div>
        <div class="desc">生产日报统一填报项目</div>
      </div>
    </div>
    </div>
  </div>
  </template>

<script setup>
import '../styles/theme.css'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { useRouter } from 'vue-router';

const router = useRouter();
const projects = [
  // 按后端统一前缀：/api/v1/projects/daily_report_25_26
  { key: 'daily_report_25_26', name: 'daily_report_25_26' },
];

function enter(p) {
  router.push(`/projects/${encodeURIComponent(p.key)}/dashboard`);
}
</script>

<style scoped>
.topbar { margin-bottom: 16px; }
.name { font-size: 16px; font-weight: 600; margin-bottom: 6px; }
.desc { font-size: 13px; color: #666; }
</style>
