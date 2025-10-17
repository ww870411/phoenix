<template>
  <div class="page">
    <header class="topbar">
      <h2>项目选择</h2>
    </header>
    <div class="grid">
      <div class="card" @click="enter(projects[0])">
        <div class="name">25-26daily_report</div>
        <div class="desc">生产日报统一填报项目</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router';

const router = useRouter();
const projects = [
  { key: '25-26daily_report', name: '25-26daily_report' },
];

function enter(p) {
  router.push(`/projects/${encodeURIComponent(p.key)}/dashboard`);
}
</script>

<style scoped>
.page { padding: 20px; }
.topbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }
.card { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; cursor: pointer; transition: box-shadow .2s ease, transform .1s ease; }
.card:hover { box-shadow: 0 8px 24px rgba(0,0,0,0.06); transform: translateY(-1px); }
.name { font-size: 16px; font-weight: 600; margin-bottom: 6px; }
.desc { font-size: 13px; color: #666; }
</style>

