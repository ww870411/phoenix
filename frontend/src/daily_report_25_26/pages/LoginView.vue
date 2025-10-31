<template>
  <div class="login-page">
    <div class="visual-panel">
      <div class="visual-shapes">
        <span class="shape shape-circle"></span>
        <span class="shape shape-square"></span>
        <span class="shape shape-triangle"></span>
        <span class="shape shape-ring"></span>
      </div>
      <div class="visual-overlay">
        <h1 class="visual-title">大连洁净能源集团</h1>
        <p class="visual-subtitle">生产数据在线填报平台</p>
        <p class="visual-description">准确 · 规范 · 高效</p>
      </div>
    </div>
    <div class="form-panel">
      <form class="login-form" @submit.prevent="onSubmit">
        <div class="form-header">
          <h3 class="form-title">用户登录</h3>
          <p class="form-subtitle">请输入您的账号信息</p>
        </div>
        <label class="field">
          <span>用户名</span>
          <input v-model="username" type="text" placeholder="输入用户名" required />
        </label>
        <label class="field">
          <span>密码</span>
          <input v-model="password" type="password" placeholder="输入密码" required />
        </label>
        <button class="login-button" type="submit" :disabled="isLoading">
          {{ isLoading ? '登录中...' : '登录' }}
        </button>
        <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
      </form>
      <div class="form-footer">© 2025 大连洁净能源集团有限公司 · 经济运行部</div>
    </div>
  </div>
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
.login-page {
  min-height: 100vh;
  display: flex;
  background: linear-gradient(135deg, #2f63c7 0%, #3f72d4 45%, #82b8f0 100%);
  color: #fff;
}

.visual-panel {
  flex: 1.3;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 40px;
  overflow: hidden;
}

.visual-shapes {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.shape {
  position: absolute;
  display: block;
  opacity: 0.35;
  filter: drop-shadow(0 18px 28px rgba(0, 0, 0, 0.25));
}

.shape-circle {
  width: 220px;
  height: 220px;
  top: 15%;
  left: 10%;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0));
  animation: float-slow 12s ease-in-out infinite;
}

.shape-square {
  width: 120px;
  height: 120px;
  bottom: 18%;
  left: 22%;
  transform: rotate(18deg);
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.18), rgba(255, 255, 255, 0));
  border: 1px solid rgba(255, 255, 255, 0.35);
  animation: float-medium 9s ease-in-out infinite;
}

.shape-triangle {
  width: 0;
  height: 0;
  top: 18%;
  right: 20%;
  border-left: 60px solid transparent;
  border-right: 60px solid transparent;
  border-bottom: 110px solid rgba(255, 255, 255, 0.2);
  filter: drop-shadow(0 12px 18px rgba(0, 0, 0, 0.2));
  animation: float-fast 7s ease-in-out infinite;
}

.shape-ring {
  width: 260px;
  height: 260px;
  bottom: -60px;
  right: -40px;
  border-radius: 50%;
  border: 24px solid rgba(255, 255, 255, 0.12);
  border-top-color: rgba(255, 255, 255, 0.32);
  animation: slow-rotate 24s linear infinite;
}

.visual-overlay {
  position: relative;
  max-width: 420px;
  z-index: 1;
  backdrop-filter: blur(10px);
  background: rgba(255, 255, 255, 0.12);
  border-radius: 20px;
  padding: 44px 38px;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.25);
  text-align: center;
}

.visual-title {
  font-size: 32px;
  margin-bottom: 18px;
  font-weight: 700;
}

.visual-subtitle {
  font-size: 20px;
  margin-bottom: 16px;
  font-weight: 500;
  opacity: 0.9;
}

.visual-description {
  font-size: 15px;
  line-height: 1.7;
  margin: 0;
  opacity: 0.85;
}

.form-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 40px 60px;
  background: rgba(255, 255, 255, 0.9);
  position: relative;
}

.login-form {
  width: 100%;
  max-width: 420px;
  background: #ffffff;
  border-radius: 20px;
  padding: 42px 38px 46px;
  box-shadow: 0 28px 60px rgba(15, 23, 42, 0.18);
  border: 1px solid rgba(15, 23, 42, 0.06);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-header {
  text-align: left;
  margin-bottom: 12px;
}

.form-title {
  margin: 0 0 6px;
  font-size: 22px;
  color: #1f2d3d;
  font-weight: 600;
}

.form-subtitle {
  margin: 0;
  font-size: 14px;
  color: #8692a6;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field span {
  font-size: 13px;
  color: #374151;
}

.field input {
  height: 42px;
  border-radius: 8px;
  border: 1px solid #d1d5db;
  padding: 0 14px;
  font-size: 14px;
  transition: border-color 0.2s ease;
}

.field input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.login-button {
  height: 44px;
  border-radius: 8px;
  background: linear-gradient(135deg, #478bf4 0%, #2563eb 100%);
  color: #fff;
  border: none;
  font-size: 16px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  font-weight: 600;
}

.login-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  box-shadow: none;
}

.login-button:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 16px 30px rgba(37, 99, 235, 0.35);
}

.error {
  margin: 0;
  font-size: 13px;
  color: #d14343;
  text-align: center;
}

.form-footer {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 12px;
  color: #5a6c82;
  letter-spacing: 0.5px;
  text-align: center;
  white-space: nowrap;
}

@keyframes float-slow {
  0%, 100% { transform: translate3d(0, 0, 0); }
  50% { transform: translate3d(12px, -18px, 0); }
}

@keyframes float-medium {
  0%, 100% { transform: translate3d(0, 0, 0) rotate(18deg); }
  50% { transform: translate3d(-16px, 12px, 0) rotate(24deg); }
}

@keyframes float-fast {
  0%, 100% { transform: translate3d(0, 0, 0); }
  50% { transform: translate3d(-12px, 16px, 0); }
}

@keyframes slow-rotate {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@media (max-width: 1024px) {
  .login-page {
    flex-direction: column;
    background: linear-gradient(135deg, #325fbf 0%, #6aa6e9 100%);
  }

  .visual-panel {
    flex: none;
    width: 100%;
    padding: 48px 24px;
    min-height: 40vh;
  }

  .form-panel {
    width: 100%;
    padding: 40px 24px 60px;
  }

  .visual-overlay {
    max-width: 520px;
  }
}

@media (max-width: 640px) {
  .login-form {
    padding: 32px 26px 36px;
  }

  .form-panel {
    padding: 32px 20px 48px;
  }

  .visual-overlay {
    padding: 32px 28px;
  }

  .visual-title {
    font-size: 26px;
  }

  .visual-subtitle {
    font-size: 18px;
  }
}
</style>
