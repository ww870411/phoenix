import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  approveWorkflow,
  clearAuthToken,
  fetchSession,
  getWorkflowStatus,
  login as apiLogin,
  logout as apiLogout,
  revokeWorkflow,
  publishWorkflow,
  setAuthToken,
} from '../services/api'

const STORAGE_KEY = 'phoenix_auth'
const DEFAULT_PERMISSION_PROJECT = 'daily_report_25_26'

function detectStorage(type) {
  if (typeof window === 'undefined') return null
  try {
    if (type === 'local') return window.localStorage
    if (type === 'session') return window.sessionStorage
  } catch (err) {
    console.warn(`${type}Storage 不可用`, err)
    return null
  }
  return null
}

const storageBuckets = {
  local: detectStorage('local'),
  session: detectStorage('session'),
}

function clearAllStorage() {
  Object.values(storageBuckets).forEach((bucket) => {
    if (bucket) {
      try {
        bucket.removeItem(STORAGE_KEY)
      } catch (err) {
        console.warn('清理缓存失败', err)
      }
    }
  })
}

function readStorage() {
  for (const key of ['local', 'session']) {
    const bucket = storageBuckets[key]
    if (!bucket) continue
    try {
      const raw = bucket.getItem(STORAGE_KEY)
      if (!raw) continue
      const parsed = JSON.parse(raw)
      return { ...parsed, __source: key }
    } catch (err) {
      console.warn('读取登录缓存失败', err)
    }
  }
  return null
}

function writeStorage(payload, remember) {
  if (!payload) {
    clearAllStorage()
    return
  }
  const targetKey = remember ? 'local' : 'session'
  const target = storageBuckets[targetKey]
  const backup = storageBuckets[remember ? 'session' : 'local']
  const serialized = JSON.stringify({ ...payload, remember })
  if (target) {
    try {
      target.setItem(STORAGE_KEY, serialized)
    } catch (err) {
      console.warn('写入登录缓存失败', err)
    }
  }
  if (backup) {
    try {
      backup.removeItem(STORAGE_KEY)
    } catch (err) {
      console.warn('清理旧缓存失败', err)
    }
  }
}

export const useAuthStore = defineStore('phoenix-auth', () => {
  const token = ref(null)
  const user = ref(null)
  const permissions = ref(null)
  const expiresIn = ref(0)
  const rememberLogin = ref(false)
  const initialized = ref(false)
  const loading = ref(false)
  const lastError = ref('')

  function persist(remember = rememberLogin.value) {
    if (!token.value || !user.value) {
      clearAllStorage()
      return
    }
    writeStorage(
      {
        token: token.value,
        user: user.value,
        permissions: permissions.value,
        expiresIn: expiresIn.value,
        remember,
      },
      remember,
    )
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
    rememberLogin.value = Boolean(
      cached.remember != null ? cached.remember : cached.__source === 'local',
    )
    setAuthToken(cached.token)
  }

  function clearSession() {
    token.value = null
    user.value = null
    permissions.value = null
    expiresIn.value = 0
    rememberLogin.value = false
    clearAuthToken()
    clearAllStorage()
  }

  async function bootstrap() {
    if (initialized.value) return
    restoreFromStorage()
    if (token.value) {
      try {
        const session = await fetchSession()
        user.value = session?.user ?? null
        permissions.value = session?.permissions ?? null
        persist(rememberLogin.value)
      } catch (err) {
        console.warn('刷新登录状态失败', err)
        clearSession()
      }
    }
    initialized.value = true
  }

  async function login(username, password, remember = false) {
    loading.value = true
    lastError.value = ''
    try {
      const response = await apiLogin({ username, password, remember_me: remember })
      token.value = response?.access_token ?? null
      user.value = response?.user ?? null
      permissions.value = response?.permissions ?? null
      expiresIn.value = response?.expires_in ?? 0
      if (!token.value) {
        throw new Error('登录响应缺少令牌')
      }
      rememberLogin.value = remember
      setAuthToken(token.value)
      persist(remember)
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
  function normalizeProjectKey(projectKey) {
    return typeof projectKey === 'string' ? projectKey.trim() : ''
  }

  function resolveProjectPermission(projectKey = DEFAULT_PERMISSION_PROJECT) {
    const normalizedProjectKey = normalizeProjectKey(projectKey)
    const projectMap =
      permissions.value && typeof permissions.value.projects === 'object'
        ? permissions.value.projects
        : {}
    const scoped = normalizedProjectKey ? projectMap?.[normalizedProjectKey] : null
    if (scoped && typeof scoped === 'object') {
      return scoped
    }
    return {
      page_access: permissions.value?.page_access || [],
      sheet_rules: permissions.value?.sheet_rules || {},
      actions: permissions.value?.actions || {},
      units_access: permissions.value?.units_access || [],
    }
  }

  function getPageAccessSet(projectKey = DEFAULT_PERMISSION_PROJECT) {
    return new Set(resolveProjectPermission(projectKey)?.page_access || [])
  }

  function getSheetRuleMap(projectKey = DEFAULT_PERMISSION_PROJECT) {
    return resolveProjectPermission(projectKey)?.sheet_rules || {}
  }

  function getActionFlags(projectKey = DEFAULT_PERMISSION_PROJECT) {
    return resolveProjectPermission(projectKey)?.actions || {}
  }

  function getAllowedUnitsSet(projectKey = DEFAULT_PERMISSION_PROJECT) {
    return new Set(resolveProjectPermission(projectKey)?.units_access || [])
  }

  const allowedUnits = computed(() => getAllowedUnitsSet(DEFAULT_PERMISSION_PROJECT))

  function hasPageAccess(projectKey, pageKey) {
    if (pageKey === undefined) {
      return getPageAccessSet(DEFAULT_PERMISSION_PROJECT).has(projectKey)
    }
    return getPageAccessSet(projectKey).has(pageKey)
  }

  function filterPages(projectKey, pages) {
    // 兼容旧签名：filterPages(pages)
    if (Array.isArray(projectKey) && pages === undefined) {
      return filterPages(DEFAULT_PERMISSION_PROJECT, projectKey)
    }
    if (!Array.isArray(pages)) return []
    return pages.filter((page) => hasPageAccess(projectKey, page.page_key))
  }

  function sheetMatchesUnit(sheet, unit) {
    if (!unit) return false
    const sheetKey = String(sheet?.sheet_key || '').toLowerCase()
    const normalizedUnit = String(unit).toLowerCase()
    if (sheetKey.startsWith(normalizedUnit)) return true
    const unitName = String(sheet?.unit_name || '').toLowerCase()
    return unitName.includes(normalizedUnit)
  }

  function filterSheetsByRule(projectKey, pageKey, sheets) {
    // 兼容旧签名：filterSheetsByRule(pageKey, sheets)
    if (Array.isArray(pageKey) && sheets === undefined) {
      return filterSheetsByRule(DEFAULT_PERMISSION_PROJECT, projectKey, pageKey)
    }
    const rule = getSheetRuleMap(projectKey)?.[pageKey]
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
        (sheet) => extraSheets.has(sheet.sheet_key) || sheetMatchesUnit(sheet, userUnit),
      )
    }
    return sheets
  }

  function canSubmitFor(projectKey = DEFAULT_PERMISSION_PROJECT) {
    return Boolean(getActionFlags(projectKey).can_submit)
  }

  function canApproveFor(projectKey = DEFAULT_PERMISSION_PROJECT) {
    return Boolean(getActionFlags(projectKey).can_approve)
  }

  function canRevokeFor(projectKey = DEFAULT_PERMISSION_PROJECT) {
    return Boolean(getActionFlags(projectKey).can_revoke)
  }

  function canPublishFor(projectKey = DEFAULT_PERMISSION_PROJECT) {
    return Boolean(getActionFlags(projectKey).can_publish)
  }

  function canManageValidationFor(projectKey = DEFAULT_PERMISSION_PROJECT) {
    return Boolean(getActionFlags(projectKey).can_manage_validation)
  }

  function canManageAiSettingsFor(projectKey = DEFAULT_PERMISSION_PROJECT) {
    return Boolean(getActionFlags(projectKey).can_manage_ai_settings)
  }

  function canExtractXlsxFor(projectKey = DEFAULT_PERMISSION_PROJECT) {
    return Boolean(getActionFlags(projectKey).can_extract_xlsx)
  }

  const canSubmit = computed(() => canSubmitFor(DEFAULT_PERMISSION_PROJECT))
  const canApprove = computed(() => canApproveFor(DEFAULT_PERMISSION_PROJECT))
  const canRevoke = computed(() => canRevokeFor(DEFAULT_PERMISSION_PROJECT))
  const canPublish = computed(() => canPublishFor(DEFAULT_PERMISSION_PROJECT))

  function canApproveUnit(unit, projectKey = DEFAULT_PERMISSION_PROJECT) {
    if (!canApproveFor(projectKey)) return false
    const scopedUnits = getAllowedUnitsSet(projectKey)
    if (!scopedUnits.size) return true
    return scopedUnits.has(unit)
  }

  function canRevokeUnit(unit, projectKey = DEFAULT_PERMISSION_PROJECT) {
    if (!canRevokeFor(projectKey)) return false
    const scopedUnits = getAllowedUnitsSet(projectKey)
    if (!scopedUnits.size) return true
    return scopedUnits.has(unit)
  }

  async function loadWorkflowStatus(projectKey) {
    return getWorkflowStatus(projectKey)
  }

  async function approveUnit(projectKey, unit) {
    if (!canApproveUnit(unit, projectKey)) {
      throw new Error('当前账号无权审批该单位')
    }
    return approveWorkflow(projectKey, { unit })
  }

  async function revokeUnit(projectKey, unit) {
    if (!canRevokeUnit(unit, projectKey)) {
      throw new Error('当前账号无权取消该单位审批')
    }
    return revokeWorkflow(projectKey, { unit })
  }

  async function publish(projectKey) {
    if (!canPublishFor(projectKey)) {
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
    rememberLogin,
    isAuthenticated,
    canSubmit,
    canApprove,
    canRevoke,
    canPublish,
    allowedUnits,
    bootstrap,
    login,
    logout,
    filterPages,
    filterSheetsByRule,
    hasPageAccess,
    canSubmitFor,
    canApproveFor,
    canRevokeFor,
    canPublishFor,
    canManageValidationFor,
    canManageAiSettingsFor,
    canExtractXlsxFor,
    canApproveUnit,
    canRevokeUnit,
    loadWorkflowStatus,
    approveUnit,
    revokeUnit,
    publish,
  }
})
