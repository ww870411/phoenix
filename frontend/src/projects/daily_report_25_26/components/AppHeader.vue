<template>
  <header class="app-header">
    <div class="app-header__inner">
      <div class="brand" @click="goHome">
        <span class="brand-mark"></span>
        <span class="brand-name">大连洁净能源集团</span>
        <span class="brand-sub">数据填报平台</span>
      </div>
      <nav class="nav">
        <button
          v-if="auth.canAccessAdminConsole"
          class="btn btn-admin"
          @click="goAdminConsole"
        >
          进入后台
        </button>
        <span v-if="userLabel" class="user-info">{{ userLabel }}</span>
        <button class="btn" @click="logout">退出</button>
      </nav>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'

const router = useRouter()
const auth = useAuthStore()

function goHome() {
  router.push('/projects')
}

function goAdminConsole() {
  router.push('/admin-console')
}

const userLabel = computed(() => {
  if (!auth?.user) return ''
  const unit = auth.user.unit ? `｜${auth.user.unit}` : ''
  return `${auth.user.username}${unit}`
})

async function logout() {
  await auth.logout()
  router.replace('/login')
}
</script>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 20;
  background: linear-gradient(90deg, #0b3b86 0%, #0e4cba 60%, #2563eb 100%);
  color: #fff;
  box-shadow: 0 6px 16px rgba(0,0,0,.12);
}
.app-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.brand { display: flex; align-items: baseline; gap: 10px; cursor: pointer; user-select: none; min-width: 0; }
.brand-mark { width: 10px; height: 10px; border-radius: 50%; background: #93c5fd; box-shadow: 0 0 0 3px rgba(147,197,253,.25); }
.brand-name { font-weight: 800; letter-spacing: .5px; white-space: nowrap; word-break: keep-all; }
.brand-sub { opacity: .9; font-size: 12px; white-space: nowrap; word-break: keep-all; }
.nav { display: flex; gap: 8px; flex-wrap: nowrap; }
.user-info {
  font-size: 13px;
  opacity: .9;
  align-self: center;
  white-space: nowrap;
}
.btn {
  height: 30px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,.35);
  background: rgba(255,255,255,.08);
  color: #fff;
  cursor: pointer;
  backdrop-filter: blur(4px);
  white-space: nowrap;
  word-break: keep-all;
  writing-mode: horizontal-tb;
}
.btn:hover { background: rgba(255,255,255,.16); }
.btn-admin {
  border-color: rgba(251, 191, 36, 0.75);
  background: rgba(251, 191, 36, 0.16);
  color: #fde68a;
}
.btn-admin:hover {
  background: rgba(251, 191, 36, 0.28);
}
@media (max-width: 640px) {
  .app-header__inner {
    padding: 8px 10px;
    gap: 8px;
  }
  .brand {
    gap: 8px;
  }
  .brand-name {
    font-size: 15px;
  }
  .brand-sub {
    font-size: 11px;
  }
  .nav {
    gap: 6px;
  }
  .btn {
    padding: 0 10px;
    font-size: 12px;
  }
}
</style>
