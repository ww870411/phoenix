<template>
  <div class="login-wrap">
    <div class="card">
      <h1 class="title">凤凰计划 · 登录</h1>
      <form @submit.prevent="onSubmit">
        <label class="field">
          <span>用户名</span>
          <input v-model="username" type="text" placeholder="输入用户名" required />
        </label>
        <label class="field">
          <span>密码</span>
          <input v-model="password" type="password" placeholder="输入密码" required />
        </label>
        <button class="primary" type="submit" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
    </div>
  </div>
  <footer class="footer">© 2025 供暖集团 · 凤凰计划</footer>
  
</template>

<script setup>
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
  background: linear-gradient(135deg, #f0f4ff 0%, #fefefe 100%);
}
.card {
  width: 360px;
  background: #fff;
  padding: 24px 24px 16px;
  border-radius: 12px;
  box-shadow: 0 12px 30px rgba(0,0,0,0.08);
}
.title {
  font-size: 20px;
  margin: 0 0 16px 0;
  text-align: center;
}
form { display: flex; flex-direction: column; gap: 12px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field span { font-size: 13px; color: #333; }
input {
  height: 36px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 0 10px;
  outline: none;
}
input:focus { border-color: #4f46e5; box-shadow: 0 0 0 2px rgba(79,70,229,.1); }
.primary {
  margin-top: 4px;
  height: 38px;
  border: none;
  border-radius: 8px;
  color: #fff;
  background: #4f46e5;
  cursor: pointer;
}
.primary:disabled { opacity: .6; cursor: not-allowed; }
.footer {
  text-align: center;
  padding: 12px 0 20px;
  color: #777;
  font-size: 12px;
}
</style>

