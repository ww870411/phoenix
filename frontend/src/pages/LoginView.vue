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
        <p class="visual-subtitle">生产经营数据智算平台</p>
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
          <div class="password-input-wrapper">
            <input v-model="password" :type="showPassword ? 'text' : 'password'" placeholder="输入密码" required />
            <button 
              type="button" 
              class="toggle-password-btn" 
              @click.stop.prevent="showPassword = !showPassword"
              tabindex="-1"
            >
              <svg v-if="showPassword" class="eye-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                <circle cx="12" cy="12" r="3"></circle>
              </svg>
              <svg v-else class="eye-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                <line x1="1" y1="1" x2="23" y2="23"></line>
              </svg>
            </button>
          </div>
        </label>
        <label class="remember-toggle">
          <input v-model="rememberMe" type="checkbox" />
          <span>记住我的登录状态</span>
        </label>
        <button class="login-button" type="submit" :disabled="isLoading">
          {{ isLoading ? '登录中...' : '登录' }}
        </button>
        <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
      </form>
      <div class="form-footer">© 2025-2026 大连洁净能源集团有限公司 · 经济运行部</div>
    </div>
  </div>
</template>

<script setup>
import '../projects/daily_report_25_26/styles/theme.css'
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../projects/daily_report_25_26/store/auth'

const auth = useAuthStore()
const router = useRouter()
const username = ref('')
const password = ref('')
const showPassword = ref(false)
const rememberMe = ref(auth.rememberLogin ?? true)
const errorMessage = ref('')
const isLoading = computed(() => auth.loading)

watch(
  () => auth.rememberLogin,
  (val) => {
    rememberMe.value = val
  },
)

async function onSubmit() {
  if (isLoading.value) return
  errorMessage.value = ''
  try {
    await auth.login(username.value, password.value, rememberMe.value)
    await router.replace('/projects')
  } catch (err) {
    console.error(err)
    const message = err instanceof Error ? err.message : '登录失败，请稍后再试'
    errorMessage.value = message
  }
}
</script>

<style scoped>
.login-page,
.login-page *,
.login-page *::before,
.login-page *::after {
  box-sizing: border-box;
}

.login-page {
  min-height: 100vh;
  display: flex;
  overflow-x: hidden;
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
  isolation: isolate;
}

.visual-shapes {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 1;
}

.shape {
  position: absolute;
  display: block;
  opacity: 0.35;
  will-change: transform;
  transform: translate(0, 0);
}

.shape-circle {
  width: 220px;
  height: 220px;
  top: 15%;
  left: 10%;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0));
  box-shadow: 0 18px 28px rgba(0, 0, 0, 0.15);
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
  box-shadow: 0 18px 28px rgba(0, 0, 0, 0.15);
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
  z-index: 2;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.2), rgba(255, 255, 255, 0.09));
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

.password-input-wrapper {
  position: relative;
  display: flex;
  width: 100%;
}

.password-input-wrapper input {
  width: 100%;
  padding-right: 40px !important;
}

.toggle-password-btn {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8692a6;
  transition: color 0.2s ease;
}

.toggle-password-btn:hover {
  color: #374151;
}

.eye-icon {
  width: 18px;
  height: 18px;
}

.remember-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #4b5563;
  user-select: none;
}

.remember-toggle input {
  width: 16px;
  height: 16px;
  accent-color: #2563eb;
  cursor: pointer;
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
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(12px, -18px); }
}

@keyframes float-medium {
  0%, 100% { transform: translate(0, 0) rotate(18deg); }
  50% { transform: translate(-16px, 12px) rotate(24deg); }
}

@keyframes float-fast {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-12px, 16px); }
}

@keyframes slow-rotate {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .shape {
    animation: none;
  }
}

@media (max-width: 1024px) {
  .login-page {
    flex-direction: column;
    justify-content: center;
    padding: 36px 24px calc(28px + env(safe-area-inset-bottom, 0px));
    gap: 24px;
    background: linear-gradient(155deg, #1e4eb8 0%, #2f63c7 42%, #5b97ee 78%, #8bc2f9 100%);
  }

  .visual-panel {
    flex: none;
    width: 100%;
    padding: 0;
    min-height: auto;
    overflow: visible;
  }

  .visual-shapes {
    position: fixed;
    inset: 0;
  }

  .form-panel {
    flex: none;
    width: 100%;
    padding: 0;
    background: transparent;
    justify-content: center;
    gap: 20px;
  }

  .visual-overlay {
    width: 100%;
    max-width: 460px;
    background: transparent;
    border: none;
    box-shadow: none;
    padding: 4px 12px;
  }

  .visual-title {
    font-size: 28px;
    margin: 0 0 8px;
    text-shadow: 0 2px 12px rgba(15, 23, 42, 0.22);
  }

  .visual-subtitle {
    font-size: 16px;
    margin: 0 0 10px;
    opacity: 0.95;
  }

  .visual-description {
    display: inline-block;
    font-size: 12px;
    letter-spacing: 0.16em;
    padding: 4px 14px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.16);
    border: 1px solid rgba(255, 255, 255, 0.28);
    opacity: 0.96;
  }

  .login-form {
    background: rgba(255, 255, 255, 0.97);
    box-shadow: 0 22px 50px rgba(15, 23, 42, 0.24), 0 0 0 1px rgba(255, 255, 255, 0.65) inset;
  }

  .form-footer {
    position: static;
    transform: none;
    white-space: normal;
    width: 100%;
    line-height: 1.5;
    color: rgba(255, 255, 255, 0.85);
    text-shadow: 0 1px 4px rgba(15, 23, 42, 0.18);
  }
}

@media (max-width: 640px) {
  .login-page {
    min-height: 100dvh;
    padding: 24px 16px calc(20px + env(safe-area-inset-bottom, 0px));
    gap: 18px;
  }

  .shape-circle {
    width: 170px;
    height: 170px;
    top: -40px;
    left: -40px;
    opacity: 0.26;
  }

  .shape-square {
    width: 84px;
    height: 84px;
    bottom: 14%;
    left: -18px;
    opacity: 0.22;
  }

  .shape-triangle {
    top: 12%;
    right: -12px;
    border-left-width: 38px;
    border-right-width: 38px;
    border-bottom-width: 68px;
    opacity: 0.2;
  }

  .shape-ring {
    width: 190px;
    height: 190px;
    bottom: -65px;
    right: -55px;
    border-width: 18px;
    opacity: 0.25;
  }

  .visual-overlay {
    max-width: 400px;
    padding: 0 6px;
  }

  .visual-title {
    font-size: 24px;
    margin: 0 0 6px;
  }

  .visual-subtitle {
    font-size: 14px;
    margin: 0 0 10px;
  }

  .visual-description {
    font-size: 11px;
    padding: 3px 12px;
  }

  .form-panel {
    gap: 18px;
  }

  .login-form {
    max-width: 400px;
    padding: 26px 22px 28px;
    border-radius: 22px;
    gap: 15px;
  }

  .form-header {
    margin-bottom: 4px;
  }

  .form-title {
    font-size: 21px;
  }

  .field input {
    width: 100%;
    min-height: 46px;
    font-size: 16px;
    background: #f8fafc;
    border-radius: 10px;
  }

  .field input:focus {
    background: #ffffff;
  }

  .password-input-wrapper input {
    padding-right: 44px !important;
  }

  .toggle-password-btn {
    width: 36px;
    height: 36px;
    right: 6px;
  }

  .login-button {
    width: 100%;
    min-height: 48px;
    border-radius: 10px;
    box-shadow: 0 10px 24px rgba(37, 99, 235, 0.28);
  }

  .form-footer {
    font-size: 12px;
  }
}

@media (max-width: 360px) {
  .login-page {
    padding: 20px 12px calc(16px + env(safe-area-inset-bottom, 0px));
    gap: 14px;
  }

  .visual-title {
    font-size: 21px;
  }

  .login-form {
    padding: 22px 18px 24px;
    border-radius: 18px;
  }
}
</style>
