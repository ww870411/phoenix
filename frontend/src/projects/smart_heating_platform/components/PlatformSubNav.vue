<template>
  <nav class="shp-subnav card elevated" aria-label="智慧供热平台精算模块功能导航">
    <div class="subnav-links">
      <button
        v-for="item in navItems"
        :key="item.key"
        type="button"
        :class="['subnav-btn', { active: current === item.key }]"
        @click="go(item.path)"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span>{{ item.label }}</span>
      </button>
    </div>
  </nav>
</template>

<script setup>
import { useRouter } from 'vue-router'

defineProps({
  current: {
    type: String,
    required: true,
  },
})

const router = useRouter()

const navItems = [
  { key: 'hourly_report', label: '逐小时运行报告', icon: '📊', path: '/projects/smart_heating_platform/pages/hourly_report' },
  { key: 'daily_report', label: '每日运行报告', icon: '📑', path: '/projects/smart_heating_platform/pages/daily_report' },
  { key: 'dict_center', label: '8类主体台账', icon: '🗂️', path: '/projects/smart_heating_platform/pages/dict_center' },
]

function go(path) {
  router.push(path)
}
</script>

<style scoped>
.shp-subnav {
  padding: 10px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.subnav-links {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.subnav-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  color: #334155;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.subnav-btn:hover {
  background: #eff6ff;
  border-color: #93c5fd;
  color: #1d4ed8;
}

.subnav-btn.active {
  background: #1d4ed8;
  border-color: #1d4ed8;
  color: #ffffff;
}

@media (max-width: 768px) {
  .shp-subnav {
    padding: 8px 10px;
  }
  .subnav-links {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 6px;
  }
  .subnav-btn {
    justify-content: center;
    padding: 8px 6px;
    font-size: 12px;
    gap: 4px;
    white-space: nowrap;
  }
}
</style>
