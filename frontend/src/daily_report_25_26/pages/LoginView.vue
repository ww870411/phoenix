<template>
  <div class="login-wrap">
    <div class="card elevated" style="width:380px;">
      <h1 class="title" style="text-align:center;">凤凰计划 · 登录</h1>
      <form @submit.prevent="onSubmit" style="display:flex;flex-direction:column;gap:12px;">
        <label class="field">
          <span>用户名</span>
          <input v-model="username" type="text" placeholder="输入用户名" required />
        </label>
        <label class="field">
          <span>密码</span>
          <input v-model="password" type="password" placeholder="输入密码" required />
        </label>
        <button class="btn primary" type="submit" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
    </div>
  </div>
  <footer class="footer">© 2025 供暖集团 · 凤凰计划</footer>
</template>

<script setup>
import '../styles/theme.css'
import { ref } from 'vue';
import { useRouter } from 'vue-router';

const username = ref('');
const password = ref('');
const loading = ref(false);
const router = useRouter();

async function onSubmit() {
  if (loading.value) return;
  loading.value = true;
  try {
    // 简化：前端本地模拟登录态
    // 真实项目应调用后端认证并获取令牌
    localStorage.setItem('phoenix_token', `mock-${Date.now()}`);
    await router.replace('/projects');
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(1200px 600px at 10% 10%, #e2eaff, transparent 60%),
              radial-gradient(1000px 500px at 90% 10%, #dbeafe, transparent 60%),
              linear-gradient(135deg, #eef2ff 0%, #fefefe 100%);
}
.title {
  font-size: 20px;
  margin: 0 0 16px 0;
  text-align: center;
}
.field { display: flex; flex-direction: column; gap: 6px; }
.field span { font-size: 13px; color: #333; }
.footer {
  text-align: center;
  padding: 12px 0 20px;
  color: #777;
  font-size: 12px;
}
</style>
