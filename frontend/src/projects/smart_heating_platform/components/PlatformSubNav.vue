<template>
  <nav class="shp-subnav card elevated" aria-label="智慧供热旁路平台功能导航">
    <div class="subnav-links">
      <button
        v-for="item in navItems"
        :key="item.key"
        type="button"
        :class="['subnav-btn', { active: current === item.key, 'is-yin': item.yin }]"
        @click="go(item.path)"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span>{{ item.label }}</span>
        <span v-if="item.badge" :class="['nav-badge', item.yin ? 'badge-yin' : 'badge-yang']">{{ item.badge }}</span>
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
  { key: 'hourly_report', label: '逐小时运行报告', icon: '📊', badge: '阳面', path: '/projects/smart_heating_platform/pages/hourly_report', yin: false },
  { key: 'daily_report', label: '每日精算日报', icon: '📑', badge: '阳面', path: '/projects/smart_heating_platform/pages/daily_report', yin: false },
  { key: 'fault_audit', label: '异常巡检督办', icon: '🛡️', badge: '阴面', path: '/projects/smart_heating_platform/pages/fault_audit', yin: true },
  { key: 'dict_center', label: '八大主体台账', icon: '🗂️', path: '/projects/smart_heating_platform/pages/dict_center', yin: false },
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

.subnav-btn.is-yin.active {
  background: #991b1b;
  border-color: #991b1b;
  color: #ffffff;
}

.nav-badge {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 999px;
  font-weight: 600;
}

.badge-yang {
  background: #dcfce7;
  color: #166534;
}

.badge-yin {
  background: #fee2e2;
  color: #991b1b;
}

.subnav-btn.active .nav-badge {
  background: rgba(255, 255, 255, 0.22);
  color: #ffffff;
}
</style>
