<template>
  <header class="app-header">
    <div class="app-header__inner">
      <div class="brand" @click="goHome">
        <span class="brand-mark"></span>
        <span class="brand-name">Phoenix</span>
        <span class="brand-sub">数据填报平台</span>
      </div>
      <nav class="nav">
        <button class="btn" @click="logout">退出</button>
      </nav>
    </div>
  </header>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
function goHome() { router.push('/projects') }
function logout() {
  localStorage.removeItem('phoenix_token')
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
}
.brand { display: flex; align-items: baseline; gap: 10px; cursor: pointer; user-select: none; }
.brand-mark { width: 10px; height: 10px; border-radius: 50%; background: #93c5fd; box-shadow: 0 0 0 3px rgba(147,197,253,.25); }
.brand-name { font-weight: 800; letter-spacing: .5px; }
.brand-sub { opacity: .9; font-size: 12px; }
.nav { display: flex; gap: 8px; }
.btn {
  height: 30px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,.35);
  background: rgba(255,255,255,.08);
  color: #fff;
  cursor: pointer;
  backdrop-filter: blur(4px);
}
.btn:hover { background: rgba(255,255,255,.16); }
</style>
