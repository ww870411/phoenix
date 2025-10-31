<template>
  <div class="login-wrap">
    <div class="card elevated" style="width:380px;">
      <h1 class="title" style="text-align:center;">登录</h1>
      <form @submit.prevent="onSubmit" style="display:flex;flex-direction:column;gap:12px;">
        <label class="field">
          <span>用户名</span>
          <input v-model="username" type="text" placeholder="输入用户名" required />
        </label>
        <label class="field">
          <span>密码</span>
          <input v-model="password" type="password" placeholder="输入密码" required />
        </label>
        <button class="btn primary" type="submit" :disabled="isLoading">
          {{ isLoading ? '登录中...' : '登录' }}
        </button>
        <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
      </form>
    </div>
  </div>
  <footer class="footer">© 2025 供暖集团 · 凤凰计划</footer>
</template>

<script setup>
import '../styles/theme.css'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'

const auth = useAuthStore()
const router = useRouter()
const username = ref('')
const password = ref('')
const errorMessage = ref('')
const isLoading = computed(() => auth.loading)

async function onSubmit() {
  if (isLoading.value) return
  errorMessage.value = ''
  try {
    await auth.login(username.value, password.value)
    await router.replace('/projects')
  } catch (err) {
    console.error(err)
    const message = err instanceof Error ? err.message : '登录失败，请稍后再试'
    errorMessage.value = message
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
.error {
  margin: 0;
  font-size: 13px;
  color: #d14343;
  text-align: center;
}
.footer {
  text-align: center;
  padding: 12px 0 20px;
  color: #777;
  font-size: 12px;
}
</style>
