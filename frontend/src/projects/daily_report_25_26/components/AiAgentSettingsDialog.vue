<template>
  <transition name="fade">
    <div
      v-if="modelValue"
      class="ai-settings-dialog__backdrop"
      role="dialog"
      aria-modal="true"
      aria-label="智能体设定"
    >
      <div class="ai-settings-dialog__panel">
        <header class="ai-settings-dialog__header">
          <div>
            <h4>智能体设定</h4>
            <p>统一维护多 Provider 配置，并选择当前生效 Provider。</p>
          </div>
          <button
            type="button"
            class="ai-settings-dialog__close"
            :disabled="saving || testing"
            aria-label="关闭智能体设定"
            @click="closeDialog"
          >
            ×
          </button>
        </header>

        <div class="ai-settings-dialog__body">
          <div v-if="loading" class="ai-settings-dialog__loading">配置读取中，请稍候…</div>
          <template v-else>
            <details class="block" open>
              <summary>基础设置</summary>
              <div class="block__content">
                <label class="field">
                  <span>当前生效 Provider</span>
                  <select v-model="form.activeProviderId" :disabled="saving || testing">
                    <option v-for="item in form.providers" :key="item.id" :value="item.id">
                      {{ item.name || item.id }}（{{ item.kind === 'gemini' ? 'Gemini' : 'New API' }}）
                    </option>
                  </select>
                </label>
              </div>
            </details>

            <details class="block" open>
              <summary>Provider 管理</summary>
              <div class="block__content">
                <div class="provider-toolbar">
                  <button
                    type="button"
                    class="btn ghost"
                    :disabled="saving || testing || !hasNewApiProviders"
                    @click="handleBatchTestNewApi"
                  >
                    {{ testingNewApiAll ? '测试全部 New API 中…' : '测试全部 New API' }}
                  </button>
                </div>
                <div
                  v-for="(provider, index) in form.providers"
                  :key="provider.uiKey"
                  class="provider-card"
                >
                  <div class="provider-card__head">
                    <div class="provider-card__title">
                      <button
                        type="button"
                        class="provider-card__toggle"
                        :disabled="saving || testing"
                        @click="toggleProviderExpanded(provider)"
                      >
                        <strong>#{{ index + 1 }}</strong>
                        <span>{{ provider.name || '未命名 Provider' }}</span>
                        <span
                          class="provider-card__active-tag"
                          :class="isActiveProvider(provider) ? 'provider-card__active-tag--active' : 'provider-card__active-tag--standby'"
                        >
                          {{ isActiveProvider(provider) ? '当前生效' : '备用' }}
                        </span>
                        <span class="provider-card__summary">
                          {{ provider.model || '未设置模型' }}
                        </span>
                        <span class="provider-card__fold">{{ provider.expanded ? '收起' : '展开' }}</span>
                      </button>
                      <span
                        v-if="providerTestResults[provider.uiKey]?.message"
                        class="provider-card__status"
                        :class="`provider-card__status--${providerTestResults[provider.uiKey]?.status || 'idle'}`"
                      >
                        {{ providerTestResults[provider.uiKey]?.message }}
                      </span>
                    </div>
                    <div class="provider-card__actions">
                      <button
                        type="button"
                        class="btn ghost xs"
                        :disabled="saving || testing || isActiveProvider(provider)"
                        @click="setActiveProvider(provider)"
                      >
                        设为当前
                      </button>
                      <button
                        type="button"
                        class="btn ghost xs"
                        :disabled="saving || testing || !canTest"
                        @click="handleTestSingleProvider(provider, index)"
                      >
                        {{ providerTestResults[provider.uiKey]?.status === 'testing' ? '测试中…' : '测试当前' }}
                      </button>
                      <button
                        v-if="provider.kind === 'newapi'"
                        type="button"
                        class="btn ghost xs"
                        :disabled="saving || testing || !getProviderSiteUrl(provider)"
                        @click="openProviderSite(provider)"
                      >
                        打开站点
                      </button>
                      <button
                        type="button"
                        class="btn ghost xs"
                        :disabled="saving || testing || form.providers.length <= 1"
                        @click="removeProvider(index)"
                      >
                        删除
                      </button>
                    </div>
                  </div>
                  <div v-if="provider.expanded" class="provider-grid">
                    <label class="field">
                      <span>标识 ID</span>
                      <input v-model="provider.id" :disabled="saving || testing" />
                    </label>
                    <label class="field">
                      <span>显示名称</span>
                      <input v-model="provider.name" :disabled="saving || testing" />
                    </label>
                    <label class="field">
                      <span>类型</span>
                      <select v-model="provider.kind" :disabled="saving || testing">
                        <option value="gemini">Gemini 官方</option>
                        <option value="newapi">New API</option>
                      </select>
                    </label>
                    <label class="field">
                      <span>模型名称</span>
                      <input v-model="provider.model" :disabled="saving || testing" />
                    </label>
                    <div class="field field--full">
                      <span>备选模型（可切换为当前模型）</span>
                      <div class="keys">
                        <div
                          v-for="(backupModel, backupIndex) in provider.backup_models"
                          :key="`${provider.uiKey}-backup-${backupIndex}`"
                          class="keys__row"
                        >
                          <input
                            v-model="provider.backup_models[backupIndex]"
                            :disabled="saving || testing"
                            placeholder="输入备选模型名称"
                          />
                          <button
                            type="button"
                            class="btn ghost xs"
                            :disabled="saving || testing || !String(backupModel || '').trim()"
                            @click="promoteBackupModel(provider, backupIndex)"
                          >
                            设为当前
                          </button>
                          <button
                            type="button"
                            class="btn ghost xs"
                            :disabled="saving || testing"
                            @click="removeBackupModel(provider, backupIndex)"
                          >
                            删除
                          </button>
                        </div>
                        <button
                          type="button"
                          class="btn ghost xs"
                          :disabled="saving || testing"
                          @click="addBackupModel(provider)"
                        >
                          + 添加备选模型
                        </button>
                      </div>
                    </div>
                    <label class="field field--full" v-if="provider.kind === 'newapi'">
                      <span>Base URL</span>
                      <input v-model="provider.base_url" :disabled="saving || testing" />
                    </label>
                    <div class="field field--full">
                      <span>API Keys（首个为当前使用）</span>
                      <div class="keys">
                        <div
                          v-for="(key, keyIndex) in provider.api_keys"
                          :key="`${provider.uiKey}-key-${keyIndex}`"
                          class="keys__row"
                        >
                          <input
                            v-model="provider.api_keys[keyIndex]"
                            :disabled="saving || testing"
                            placeholder="输入 API Key"
                          />
                          <button
                            type="button"
                            class="btn ghost xs"
                            :disabled="saving || testing || keyIndex === 0"
                            @click="promoteApiKey(provider, keyIndex)"
                          >
                            设为首位
                          </button>
                          <button
                            type="button"
                            class="btn ghost xs"
                            :disabled="saving || testing"
                            @click="removeApiKey(provider, keyIndex)"
                          >
                            删除
                          </button>
                        </div>
                        <button
                          type="button"
                          class="btn ghost xs"
                          :disabled="saving || testing"
                          @click="addApiKey(provider)"
                        >
                          + 添加 API Key
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
                <button type="button" class="btn ghost" :disabled="saving || testing" @click="addProvider">
                  + 新增 Provider
                </button>
              </div>
            </details>

            <details class="block">
              <summary>提示词设置</summary>
              <div class="block__content">
                <label class="field">
                  <span>日报提示词（instruction_daily）</span>
                  <textarea v-model="form.instructionDaily" rows="8" :disabled="saving || testing"></textarea>
                </label>
                <label class="field">
                  <span>月报提示词（instruction_monthly）</span>
                  <textarea v-model="form.instructionMonthly" rows="8" :disabled="saving || testing"></textarea>
                </label>
              </div>
            </details>

            <details class="block">
              <summary>运行策略</summary>
              <div class="block__content">
                <div class="field">
                  <span>报告生成模式</span>
                  <label class="inline"><input type="radio" value="full" v-model="form.reportMode" />完整模式</label>
                  <label class="inline"><input type="radio" value="fast" v-model="form.reportMode" />极速模式</label>
                </div>
                <label class="inline">
                  <input type="checkbox" v-model="form.validationEnabled" />
                  启用检查核实（第4阶段）
                </label>
                <label class="inline">
                  <input type="checkbox" v-model="form.allowNonAdmin" />
                  允许非管理员启用智能报告
                </label>
                <label class="inline">
                  <input type="checkbox" v-model="form.showChatBubble" />
                  显示 AI 聊天气泡
                </label>
              </div>
            </details>
          </template>

          <p v-if="errorMessage" class="alert alert--error">{{ errorMessage }}</p>
          <p v-else-if="successMessage" class="alert alert--success">{{ successMessage }}</p>
        </div>

        <footer class="ai-settings-dialog__actions">
          <button
            type="button"
            class="btn ghost"
            :disabled="saving || testing"
            @click="closeDialog"
          >
            退出（不保存）
          </button>
          <button
            type="button"
            class="btn primary"
            :disabled="loading || saving || testing"
            @click="handleSaveAndClose"
          >
            {{ saving ? '保存中…' : '保存并退出' }}
          </button>
        </footer>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  canManage: { type: Boolean, default: false },
  loadSettings: { type: Function, required: true },
  saveSettings: { type: Function, required: true },
  testSettings: { type: Function, default: null },
})

const emit = defineEmits(['update:modelValue'])
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const testingNewApiAll = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const providerTestResults = reactive({})

const form = reactive({
  providers: [],
  activeProviderId: '',
  instructionDaily: '',
  instructionMonthly: '',
  reportMode: 'full',
  validationEnabled: true,
  allowNonAdmin: false,
  showChatBubble: true,
})

const canTest = computed(() => typeof props.testSettings === 'function' && props.canManage)
const hasNewApiProviders = computed(() => form.providers.some((provider) => provider.kind === 'newapi'))
let providerUiSeed = 0

function nextProviderUiKey() {
  providerUiSeed += 1
  return `provider_ui_${providerUiSeed}`
}

function normalizeStringList(values, exclude = '') {
  const excludeValue = String(exclude || '').trim()
  const seen = new Set()
  return (Array.isArray(values) ? values : [])
    .map((item) => String(item || '').trim())
    .filter((item) => {
      if (!item || item === excludeValue || seen.has(item)) return false
      seen.add(item)
      return true
    })
}

function normalizeProvider(raw, index = 0) {
  const obj = raw && typeof raw === 'object' ? raw : {}
  const kind = obj.kind === 'newapi' ? 'newapi' : 'gemini'
  const id = String(obj.id || `provider_${index + 1}`).trim() || `provider_${index + 1}`
  const model = String(obj.model || '').trim()
  return {
    uiKey: String(obj.uiKey || obj.ui_key || '').trim() || nextProviderUiKey(),
    expanded: Boolean(obj.expanded),
    id,
    name: String(obj.name || '').trim() || (kind === 'gemini' ? 'Gemini Provider' : 'New API Provider'),
    kind,
    base_url: String(obj.base_url || '').trim(),
    model,
    api_keys: Array.isArray(obj.api_keys) ? obj.api_keys.map((k) => String(k || '').trim()).filter(Boolean) : [],
    backup_models: normalizeStringList(obj.backup_models, model),
  }
}

function resetProviderTestResults(providers = []) {
  Object.keys(providerTestResults).forEach((key) => {
    delete providerTestResults[key]
  })
  providers.forEach((provider) => {
    providerTestResults[provider.uiKey] = { status: 'idle', message: '' }
  })
}

function fallbackProviders(payload) {
  const list = []
  const geminiKeys = Array.isArray(payload?.api_keys) ? payload.api_keys : []
  list.push(
    normalizeProvider(
      {
        id: 'gemini_default',
        name: 'Gemini 官方',
        kind: 'gemini',
        model: payload?.model || '',
        api_keys: geminiKeys,
      },
      0,
    ),
  )
  const newapiKeys = Array.isArray(payload?.newapi_api_keys) ? payload.newapi_api_keys : []
  if (payload?.newapi_base_url || payload?.newapi_model || newapiKeys.length) {
    list.push(
      normalizeProvider(
        {
          id: 'newapi_default',
          name: 'New API 默认',
          kind: 'newapi',
          base_url: payload?.newapi_base_url || '',
          model: payload?.newapi_model || '',
          api_keys: newapiKeys,
          backup_models: Array.isArray(payload?.newapi_backup_models) ? payload.newapi_backup_models : [],
        },
        1,
      ),
    )
  }
  return list
}

function applyPayload(payload) {
  const rawProviders = Array.isArray(payload?.providers) ? payload.providers : []
  const nextProviders = rawProviders.length ? rawProviders.map((item, idx) => normalizeProvider(item, idx)) : fallbackProviders(payload)
  form.providers = nextProviders.length ? nextProviders : [normalizeProvider({}, 0)]
  resetProviderTestResults(form.providers)
  const wantedActive = String(payload?.active_provider_id || '').trim()
  const hasWanted = form.providers.some((p) => p.id === wantedActive)
  form.activeProviderId = hasWanted ? wantedActive : form.providers[0].id
  form.instructionDaily = payload?.instruction_daily ?? payload?.instruction ?? ''
  form.instructionMonthly = payload?.instruction_monthly ?? ''
  form.reportMode = payload?.report_mode ?? 'full'
  form.validationEnabled = payload?.enable_validation !== undefined ? Boolean(payload.enable_validation) : true
  form.allowNonAdmin = payload?.allow_non_admin_report !== undefined ? Boolean(payload.allow_non_admin_report) : false
  form.showChatBubble = payload?.show_chat_bubble !== undefined ? Boolean(payload.show_chat_bubble) : true
}

function addProvider() {
  const index = form.providers.length + 1
  const provider = normalizeProvider({ id: `provider_${index}`, expanded: false }, index - 1)
  form.providers.push(provider)
  providerTestResults[provider.uiKey] = { status: 'idle', message: '' }
}

function removeProvider(index) {
  if (form.providers.length <= 1) return
  const removed = form.providers[index]
  form.providers.splice(index, 1)
  if (removed?.uiKey) {
    delete providerTestResults[removed.uiKey]
  }
  if (!form.providers.some((p) => p.id === form.activeProviderId)) {
    form.activeProviderId = form.providers[0]?.id || ''
  } else if (removed?.id === form.activeProviderId) {
    form.activeProviderId = form.providers[0]?.id || ''
  }
}

function addApiKey(provider) {
  provider.api_keys.push('')
}

function removeApiKey(provider, index) {
  provider.api_keys.splice(index, 1)
}

function promoteApiKey(provider, index) {
  if (index <= 0 || index >= provider.api_keys.length) return
  const value = provider.api_keys[index]
  provider.api_keys.splice(index, 1)
  provider.api_keys.unshift(value)
}

function addBackupModel(provider) {
  if (!Array.isArray(provider.backup_models)) {
    provider.backup_models = []
  }
  provider.backup_models.push('')
}

function removeBackupModel(provider, index) {
  if (!Array.isArray(provider.backup_models)) return
  provider.backup_models.splice(index, 1)
}

function promoteBackupModel(provider, index) {
  if (!Array.isArray(provider.backup_models) || index < 0 || index >= provider.backup_models.length) return
  const nextPrimary = String(provider.backup_models[index] || '').trim()
  if (!nextPrimary) return
  const currentPrimary = String(provider.model || '').trim()
  provider.model = nextPrimary
  provider.backup_models.splice(index, 1)
  if (currentPrimary && currentPrimary !== nextPrimary) {
    provider.backup_models.unshift(currentPrimary)
  }
  provider.backup_models = normalizeStringList(provider.backup_models, provider.model)
}

function toggleProviderExpanded(provider) {
  provider.expanded = !provider.expanded
}

function isActiveProvider(provider) {
  return String(provider?.id || '').trim() !== '' && String(provider?.id || '').trim() === String(form.activeProviderId || '').trim()
}

function setActiveProvider(provider) {
  const providerId = String(provider?.id || '').trim()
  if (!providerId) return
  form.activeProviderId = providerId
  successMessage.value = `已切换当前 Provider：${provider.name || providerId}`
  errorMessage.value = ''
}

function getProviderSiteUrl(provider) {
  const raw = String(provider?.base_url || '').trim()
  if (!raw) return ''
  let candidate = raw
  if (!/^[a-zA-Z][a-zA-Z\d+\-.]*:\/\//.test(candidate)) {
    candidate = `https://${candidate.replace(/^\/+/, '')}`
  }
  try {
    return new URL(candidate).origin
  } catch {
    return ''
  }
}

function openProviderSite(provider) {
  const siteUrl = getProviderSiteUrl(provider)
  if (!siteUrl || typeof window === 'undefined') return
  window.open(siteUrl, '_blank', 'noopener,noreferrer')
}

function buildSavePayload() {
  const providers = form.providers
    .map((item, idx) => normalizeProvider(item, idx))
    .map((item) => ({
      id: item.id,
      name: item.name,
      kind: item.kind,
      base_url: item.base_url,
      model: item.model,
      api_keys: item.api_keys.map((k) => k.trim()).filter(Boolean),
      backup_models: normalizeStringList(item.backup_models, item.model),
    }))
  const active = providers.find((p) => p.id === form.activeProviderId) || providers[0]
  const gemini = providers.find((p) => p.kind === 'gemini')
  const newapi = providers.find((p) => p.kind === 'newapi')
  return {
    provider: active?.kind || 'gemini',
    providers,
    active_provider_id: active?.id || '',
    api_keys: gemini?.api_keys || [],
    model: gemini?.model || '',
    newapi_base_url: newapi?.base_url || '',
    newapi_api_keys: newapi?.api_keys || [],
    newapi_model: newapi?.model || '',
    newapi_backup_models: newapi?.backup_models || [],
    instruction_daily: form.instructionDaily || '',
    instruction_monthly: form.instructionMonthly || '',
    report_mode: form.reportMode || 'full',
    enable_validation: Boolean(form.validationEnabled),
    allow_non_admin_report: Boolean(form.allowNonAdmin),
    show_chat_bubble: Boolean(form.showChatBubble),
  }
}

async function loadData() {
  if (!props.canManage) return
  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const payload = await props.loadSettings()
    applyPayload(payload)
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) loadData().catch(() => {})
  },
)

function closeDialog() {
  if (saving.value || testing.value) return
  emit('update:modelValue', false)
}

async function handleSaveAndClose() {
  if (!props.canManage || loading.value || saving.value || testing.value) return
  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const payload = buildSavePayload()
    await props.saveSettings(payload)
    emit('update:modelValue', false)
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : String(err)
  } finally {
    saving.value = false
  }
}

function buildSingleProviderTestPayload(provider, index) {
  const normalized = normalizeProvider(provider, index)
  return {
    provider: normalized.kind,
    providers: [
      {
        id: normalized.id,
        name: normalized.name,
        kind: normalized.kind,
        base_url: normalized.base_url,
        model: normalized.model,
        api_keys: normalized.api_keys.map((key) => key.trim()).filter(Boolean),
        backup_models: normalizeStringList(normalized.backup_models, normalized.model),
      },
    ],
    active_provider_id: normalized.id,
    api_keys: normalized.kind === 'gemini' ? normalized.api_keys.map((key) => key.trim()).filter(Boolean) : [],
    model: normalized.kind === 'gemini' ? normalized.model : '',
    newapi_base_url: normalized.kind === 'newapi' ? normalized.base_url : '',
    newapi_api_keys: normalized.kind === 'newapi' ? normalized.api_keys.map((key) => key.trim()).filter(Boolean) : [],
    newapi_model: normalized.kind === 'newapi' ? normalized.model : '',
  }
}

async function handleBatchTestNewApi() {
  if (!canTest.value || loading.value || saving.value || testing.value || testingNewApiAll.value) return
  const targets = form.providers
    .map((provider, index) => ({ provider, index }))
    .filter(({ provider }) => provider.kind === 'newapi')
  if (!targets.length) return
  testingNewApiAll.value = true
  testing.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    let successCount = 0
    for (const { provider, index } of targets) {
      providerTestResults[provider.uiKey] = { status: 'testing', message: '连接测试中…' }
      try {
        const result = await props.testSettings(buildSingleProviderTestPayload(provider, index))
        providerTestResults[provider.uiKey] = {
          status: 'success',
          message: `测试成功${result?.model ? `：${result.model}` : ''}`,
        }
        successCount += 1
      } catch (err) {
        providerTestResults[provider.uiKey] = {
          status: 'error',
          message: err instanceof Error ? err.message : String(err),
        }
      }
    }
    successMessage.value = `New API Provider 测试完成：成功 ${successCount} / ${targets.length}`
  } finally {
    testing.value = false
    testingNewApiAll.value = false
  }
}

async function handleTestSingleProvider(provider, index) {
  if (!canTest.value || loading.value || saving.value || testing.value || testingNewApiAll.value) return
  const uiKey = provider?.uiKey
  if (!uiKey) return
  testing.value = true
  errorMessage.value = ''
  successMessage.value = ''
  providerTestResults[uiKey] = { status: 'testing', message: '连接测试中…' }
  try {
    const result = await props.testSettings(buildSingleProviderTestPayload(provider, index))
    providerTestResults[uiKey] = {
      status: 'success',
      message: `测试成功${result?.model ? `：${result.model}` : ''}`,
    }
    successMessage.value = `${provider.name || provider.id || '当前 Provider'} 测试成功`
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    providerTestResults[uiKey] = {
      status: 'error',
      message,
    }
    errorMessage.value = message
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.ai-settings-dialog__backdrop { position: fixed; inset: 0; background: rgba(15,23,42,.45); z-index: 1100; display:flex; align-items:center; justify-content:center; padding:18px; }
.ai-settings-dialog__panel { width:min(1040px,100%); max-height:calc(100vh - 36px); overflow:auto; background:#fff; border:1px solid #cbd5e1; border-radius:12px; padding:14px; display:flex; flex-direction:column; gap:12px; }
.ai-settings-dialog__header { display:flex; justify-content:space-between; gap:10px; }
.ai-settings-dialog__header h4 { margin:0; }
.ai-settings-dialog__header p { margin:4px 0 0; font-size:12px; color:#64748b; }
.ai-settings-dialog__close { border:1px solid #cbd5e1; background:#fff; width:30px; height:30px; border-radius:999px; cursor:pointer; }
.ai-settings-dialog__body { display:flex; flex-direction:column; gap:10px; }
.ai-settings-dialog__loading { font-size:13px; color:#64748b; }

.block { border:1px solid #cbd5e1; border-radius:8px; background:#fff; }
.block > summary { cursor:pointer; padding:10px 12px; font-size:13px; font-weight:700; color:#1f2937; }
.block__content { padding:10px 12px 12px; display:flex; flex-direction:column; gap:10px; }

.field { display:flex; flex-direction:column; gap:6px; font-size:12px; color:#334155; }
.field input, .field select, .field textarea { border:1px solid #cbd5e1; border-radius:8px; padding:8px 10px; font-size:13px; box-sizing:border-box; }
.field textarea { resize:vertical; min-height:120px; line-height:1.5; }
.field--full { grid-column:1 / -1; }

.provider-toolbar { display:flex; justify-content:flex-end; }
.provider-card { border:1px solid #dbe5f0; border-radius:10px; padding:10px; background:#f8fafc; display:flex; flex-direction:column; gap:10px; }
.provider-card__head { display:flex; align-items:flex-start; justify-content:space-between; gap:10px; }
.provider-card__title { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
.provider-card__toggle { border:none; background:transparent; padding:0; display:flex; align-items:center; gap:8px; flex-wrap:wrap; cursor:pointer; font:inherit; color:inherit; text-align:left; }
.provider-card__toggle:disabled { cursor:not-allowed; opacity:.7; }
.provider-card__active-tag { font-size:12px; padding:2px 8px; border-radius:999px; }
.provider-card__active-tag--active { background:#dcfce7; color:#166534; }
.provider-card__active-tag--standby { background:#f1f5f9; color:#475569; }
.provider-card__summary { font-size:12px; color:#475569; background:#e2e8f0; padding:2px 8px; border-radius:999px; }
.provider-card__fold { font-size:12px; color:#64748b; }
.provider-card__actions { display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }
.provider-card__status { font-size:12px; padding:2px 8px; border-radius:999px; }
.provider-card__status--success { background:#dcfce7; color:#166534; }
.provider-card__status--error { background:#fee2e2; color:#991b1b; }
.provider-card__status--testing { background:#dbeafe; color:#1d4ed8; }
.provider-card__status--idle { background:#e2e8f0; color:#475569; }
.provider-grid { display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap:10px; }

.keys { display:flex; flex-direction:column; gap:8px; }
.keys__row { display:flex; gap:8px; align-items:center; }
.keys__row input { flex:1 1 auto; min-width:0; }

.inline { display:inline-flex; gap:6px; align-items:center; margin-right:14px; font-size:13px; color:#1f2937; }
.alert { margin:2px 0 0; font-size:12px; padding:6px 10px; border-radius:8px; }
.alert--error { background:rgba(239,68,68,.1); color:#b91c1c; }
.alert--success { background:rgba(16,185,129,.1); color:#047857; }
.ai-settings-dialog__actions { display:flex; justify-content:flex-end; gap:8px; }

@media (max-width: 900px) {
  .provider-grid { grid-template-columns: 1fr; }
  .keys__row { flex-wrap: wrap; }
}
</style>
