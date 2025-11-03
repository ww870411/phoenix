import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  approveWorkflow,
  clearAuthToken,
  fetchSession,
  getWorkflowStatus,
  login as apiLogin,
  logout as apiLogout,
  publishWorkflow,
  setAuthToken,
} from '../services/api'

const STORAGE_KEY = 'phoenix_auth'

function readStorage() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw)
  } catch (err) {
    console.warn('读取登录缓存失败', err)
    return null
  }
}

function writeStorage(payload) {
  try {
    if (!payload) {
      sessionStorage.removeItem(STORAGE_KEY)
      return
    }
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  } catch (err) {
    console.warn('写入登录缓存失败', err)
  }
}

export const useAuthStore = defineStore('phoenix-auth', () => {
  const token = ref(null)
  const user = ref(null)
  const permissions = ref(null)
  const expiresIn = ref(0)
  const initialized = ref(false)
  const loading = ref(false)
  const lastError = ref('')

  function persist() {
    if (!token.value || !user.value) {
      writeStorage(null)
      return
    }
    writeStorage({
      token: token.value,
      user: user.value,
      permissions: permissions.value,
      expiresIn: expiresIn.value,
    })
  }

  function restoreFromStorage() {
    const cached = readStorage()
    if (!cached || !cached.token) {
      clearSession()
      return
    }
    token.value = cached.token
    user.value = cached.user || null
    permissions.value = cached.permissions || null
    expiresIn.value = cached.expiresIn || 0
    setAuthToken(cached.token)
  }

  function clearSession() {
    token.value = null
    user.value = null
    permissions.value = null
    expiresIn.value = 0
    clearAuthToken()
    persist()
  }

  async function bootstrap() {
    if (initialized.value) return
    restoreFromStorage()
    if (token.value) {
      try {
        const session = await fetchSession()
        user.value = session?.user ?? null
        permissions.value = session?.permissions ?? null
        persist()
      } catch (err) {
        console.warn('刷新登录状态失败', err)
        clearSession()
      }
    }
    initialized.value = true
  }

  async function login(username, password) {
    loading.value = true
    lastError.value = ''
    try {
      const response = await apiLogin({ username, password })
      token.value = response?.access_token ?? null
      user.value = response?.user ?? null
      permissions.value = response?.permissions ?? null
      expiresIn.value = response?.expires_in ?? 0
      if (!token.value) {
        throw new Error('登录响应缺少令牌')
      }
      setAuthToken(token.value)
      persist()
    } catch (err) {
      clearSession()
      lastError.value = err instanceof Error ? err.message : String(err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      await apiLogout()
    } finally {
      clearSession()
      initialized.value = false
    }
  }

  const isAuthenticated = computed(() => Boolean(token.value))
  const pageAccess = computed(() => new Set(permissions.value?.page_access || []))
  const sheetRuleMap = computed(() => permissions.value?.sheet_rules || {})
  const actionFlags = computed(() => permissions.value?.actions || {})
  const allowedUnits = computed(() => new Set(permissions.value?.units_access || []))

  function hasPageAccess(pageKey) {
    return pageAccess.value.has(pageKey)
  }

  function filterPages(pages) {
    if (!Array.isArray(pages)) return []
    return pages.filter((page) => hasPageAccess(page.page_key))
  }

  function sheetMatchesUnit(sheet, unit) {
    if (!unit) return false
    const sheetKey = String(sheet?.sheet_key || '').toLowerCase()
    const normalizedUnit = String(unit).toLowerCase()
    if (sheetKey.startsWith(normalizedUnit)) return true
    const unitName = String(sheet?.unit_name || '').toLowerCase()
    return unitName.includes(normalizedUnit)
  }

  function filterSheetsByRule(pageKey, sheets) {
    const rule = sheetRuleMap.value?.[pageKey]
    if (!rule || rule.mode === 'all') {
      return sheets
    }
    if (rule.mode === 'explicit') {
      const allow = new Set((rule.sheets || []).map((key) => String(key)))
      return sheets.filter((sheet) => allow.has(sheet.sheet_key))
    }
    if (rule.mode === 'by_unit') {
      const userUnit = user.value?.unit || ''
      const extraSheets = new Set((rule.sheets || []).map((key) => String(key)))
      // 允许显式授权表单与单位前缀匹配共同生效
      return sheets.filter(
        (sheet) => extraSheets.has(sheet.sheet_key) || sheetMatchesUnit(sheet, userUnit)
      )
    }
    return sheets
  }

  const canSubmit = computed(() => Boolean(actionFlags.value.can_submit))
  const canApprove = computed(() => Boolean(actionFlags.value.can_approve))
  const canPublish = computed(() => Boolean(actionFlags.value.can_publish))

  function canApproveUnit(unit) {
    if (!canApprove.value) return false
    if (!allowedUnits.value.size) return true
    return allowedUnits.value.has(unit)
  }

  async function loadWorkflowStatus(projectKey) {
    return getWorkflowStatus(projectKey)
  }

  async function approveUnit(projectKey, unit) {
    if (!canApproveUnit(unit)) {
      throw new Error('当前账号无权审批该单位')
    }
    return approveWorkflow(projectKey, { unit })
  }

  async function publish(projectKey) {
    if (!canPublish.value) {
      throw new Error('当前账号无发布权限')
    }
    return publishWorkflow(projectKey)
  }

  return {
    token,
    user,
    permissions,
    initialized,
    loading,
    lastError,
    isAuthenticated,
    canSubmit,
    canApprove,
    canPublish,
    allowedUnits,
    bootstrap,
    login,
    logout,
    filterPages,
    filterSheetsByRule,
    hasPageAccess,
    canApproveUnit,
    loadWorkflowStatus,
    approveUnit,
    publish,
  }
})
