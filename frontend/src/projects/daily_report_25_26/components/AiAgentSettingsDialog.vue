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
            <p>配置智能报告使用的 API Key 与模型（全局，日报+月报共用）。</p>
          </div>
          <button
            type="button"
            class="ai-settings-dialog__close"
            :disabled="saving"
            aria-label="关闭智能体设定"
            @click="closeDialog"
          >
            ×
          </button>
        </header>
        <div class="ai-settings-dialog__body">
          <div v-if="loading" class="ai-settings-dialog__loading">配置读取中，请稍候…</div>
          <template v-else>
            <div class="ai-settings-dialog__field">
              <span>API Keys（首个为当前使用的 Key）</span>
              <div class="api-key-list">
                <div
                  v-for="(key, index) in form.apiKeys"
                  :key="index"
                  class="api-key-item"
                >
                  <span class="api-key-index">
                    <span v-if="index === 0" class="api-key-badge">使用中</span>
                    <span v-else>{{ index + 1 }}.</span>
                  </span>
                  <input
                    type="text"
                    v-model="form.apiKeys[index]"
                    :disabled="saving"
                    autocomplete="off"
                    placeholder="输入 API Key"
                  />
                  <button
                    v-if="index > 0"
                    type="button"
                    class="btn ghost xs"
                    :disabled="saving"
                    @click="setApiKeyActive(index)"
                    title="设为当前使用"
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    class="btn ghost xs"
                    :disabled="saving"
                    @click="removeApiKey(index)"
                    title="删除"
                  >
                    ×
                  </button>
                </div>
                <button
                  type="button"
                  class="btn ghost xs add-key-btn"
                  :disabled="saving"
                  @click="addApiKey"
                >
                  + 添加 API Key
                </button>
              </div>
            </div>
            <label class="ai-settings-dialog__field">
              <span>模型</span>
              <input
                type="text"
                v-model="form.model"
                :disabled="saving"
                autocomplete="off"
              />
            </label>
            <div class="ai-settings-dialog__field">
              <span>智能体提示词（默认折叠）</span>
              <details class="prompt-collapse">
                <summary>日报提示词（instruction_daily）</summary>
                <textarea
                  rows="8"
                  v-model="form.instructionDaily"
                  :disabled="saving"
                  placeholder="日报默认提示词。"
                ></textarea>
              </details>
              <details class="prompt-collapse">
                <summary>月报提示词（instruction_monthly）</summary>
                <textarea
                  rows="8"
                  v-model="form.instructionMonthly"
                  :disabled="saving"
                  placeholder="月报默认提示词。"
                ></textarea>
              </details>
            </div>
            <div class="ai-settings-dialog__field">
              <span>报告生成模式（全局，日报+月报共用）</span>
              <div class="report-mode-options">
                <label class="report-mode-option">
                  <input
                    type="radio"
                    name="reportMode"
                    value="full"
                    v-model="form.reportMode"
                    :disabled="saving"
                  />
                  <div class="report-mode-content">
                    <span class="report-mode-label">完整模式</span>
                    <span class="report-mode-desc">完整阶段分析与修订，结果更稳健。</span>
                  </div>
                </label>
                <label class="report-mode-option">
                  <input
                    type="radio"
                    name="reportMode"
                    value="fast"
                    v-model="form.reportMode"
                    :disabled="saving"
                  />
                  <div class="report-mode-content">
                    <span class="report-mode-label">极速模式</span>
                    <span class="report-mode-desc">快速生成，适合高频查看。</span>
                  </div>
                </label>
              </div>
            </div>
            <label class="ai-settings-dialog__toggle">
              <input
                type="checkbox"
                v-model="form.validationEnabled"
                :disabled="saving"
              />
              <span>启用检查核实（全局，日报+月报第4阶段）</span>
            </label>
            <label class="ai-settings-dialog__toggle">
              <input
                type="checkbox"
                :checked="form.allowNonAdmin"
                :disabled="saving"
                @change="form.allowNonAdmin = $event.target.checked"
              />
              <span>允许非管理员启用智能报告</span>
            </label>
            <p class="ai-settings-dialog__hint">保存后将同步更新 backend_data/shared/ai_settings.json。</p>
          </template>
          <p v-if="errorMessage" class="ai-settings-dialog__alert ai-settings-dialog__alert--error">
            {{ errorMessage }}
          </p>
          <p
            v-else-if="successMessage"
            class="ai-settings-dialog__alert ai-settings-dialog__alert--success"
          >
            {{ successMessage }}
          </p>
        </div>
        <footer class="ai-settings-dialog__actions">
          <button
            type="button"
            class="btn ghost"
            :disabled="saving"
            @click="closeDialog"
          >
            取消
          </button>
          <button
            type="button"
            class="btn primary"
            :disabled="loading || saving"
            @click="handleSave"
          >
            {{ saving ? '保存中…' : '保存' }}
          </button>
        </footer>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  canManage: { type: Boolean, default: false },
  loadSettings: { type: Function, required: true },
  saveSettings: { type: Function, required: true },
})

const emit = defineEmits(['update:modelValue'])

const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const form = reactive({
  apiKeys: [],
  model: '',
  instructionDaily: '',
  instructionMonthly: '',
  reportMode: 'full',
  validationEnabled: true,
  allowNonAdmin: false,
})

function applyPayload(payload) {
  form.apiKeys = Array.isArray(payload?.api_keys) ? [...payload.api_keys] : []
  form.model = payload?.model ?? ''
  form.instructionDaily = payload?.instruction_daily ?? payload?.instruction ?? ''
  form.instructionMonthly = payload?.instruction_monthly ?? ''
  form.reportMode = payload?.report_mode ?? 'full'
  form.validationEnabled =
    payload?.enable_validation !== undefined ? Boolean(payload.enable_validation) : true
  form.allowNonAdmin =
    payload?.allow_non_admin_report !== undefined
      ? Boolean(payload.allow_non_admin_report)
      : false
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
    if (visible) {
      loadData().catch(() => {})
    }
  },
)

function closeDialog() {
  if (saving.value) return
  emit('update:modelValue', false)
}

function addApiKey() {
  form.apiKeys.push('')
}

function setApiKeyActive(index) {
  if (index <= 0 || index >= form.apiKeys.length) return
  const item = form.apiKeys[index]
  form.apiKeys.splice(index, 1)
  form.apiKeys.unshift(item)
}

function removeApiKey(index) {
  if (index >= 0 && index < form.apiKeys.length) {
    form.apiKeys.splice(index, 1)
  }
}

async function handleSave() {
  if (!props.canManage || loading.value || saving.value) return
  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const validKeys = form.apiKeys.map((k) => k.trim()).filter((k) => k)
    const payload = await props.saveSettings({
      api_keys: validKeys,
      model: form.model || '',
      instruction_daily: form.instructionDaily || '',
      instruction_monthly: form.instructionMonthly || '',
      report_mode: form.reportMode || 'full',
      enable_validation: Boolean(form.validationEnabled),
      allow_non_admin_report: Boolean(form.allowNonAdmin),
    })
    applyPayload(payload)
    successMessage.value = '智能体配置已保存'
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : String(err)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.ai-settings-dialog__backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  z-index: 1100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
}

.ai-settings-dialog__panel {
  width: min(980px, 100%);
  max-height: calc(100vh - 36px);
  overflow: auto;
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ai-settings-dialog__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.ai-settings-dialog__header h4 {
  margin: 0;
}

.ai-settings-dialog__header p {
  margin: 4px 0 0;
  font-size: 12px;
  color: #64748b;
}

.ai-settings-dialog__close {
  border: 1px solid #cbd5e1;
  background: #fff;
  width: 30px;
  height: 30px;
  border-radius: 999px;
  cursor: pointer;
}

.ai-settings-dialog__body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ai-settings-dialog__loading {
  font-size: 13px;
  color: #64748b;
}

.ai-settings-dialog__field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12px;
  color: #334155;
}

.api-key-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.api-key-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.api-key-item input {
  flex: 1 1 auto;
  min-width: 0;
}

.api-key-index {
  width: 52px;
  color: #475569;
  font-size: 12px;
}

.api-key-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 6px;
  border-radius: 999px;
  background: #2563eb;
  color: #fff;
}

.add-key-btn {
  align-self: flex-start;
  margin-left: 52px;
}

.ai-settings-dialog__field input,
.ai-settings-dialog__field textarea {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  box-sizing: border-box;
}

.ai-settings-dialog__field textarea {
  resize: vertical;
  min-height: 120px;
  line-height: 1.5;
}

.prompt-collapse {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #fff;
  margin-top: 8px;
  width: 100%;
}

.prompt-collapse summary {
  cursor: pointer;
  user-select: none;
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
}

.prompt-collapse textarea {
  display: block;
  width: 100%;
  box-sizing: border-box;
  margin: 0;
  border: 0;
  border-top: 1px solid #e2e8f0;
  border-radius: 0 0 8px 8px;
}

.report-mode-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.report-mode-option {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  cursor: pointer;
}

.report-mode-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.report-mode-label {
  font-weight: 600;
  color: #1f2937;
}

.report-mode-desc {
  font-size: 12px;
  color: #64748b;
}

.ai-settings-dialog__toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #334155;
}

.ai-settings-dialog__hint {
  margin: 0;
  font-size: 12px;
  color: #64748b;
}

.ai-settings-dialog__alert {
  margin: 2px 0 0;
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 8px;
}

.ai-settings-dialog__alert--error {
  background: rgba(239, 68, 68, 0.1);
  color: #b91c1c;
}

.ai-settings-dialog__alert--success {
  background: rgba(16, 185, 129, 0.1);
  color: #047857;
}

.ai-settings-dialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media (max-width: 900px) {
  .api-key-item {
    flex-wrap: wrap;
  }

  .api-key-index {
    width: auto;
    min-width: 52px;
  }

  .api-key-item input {
    width: 100%;
  }
}
</style>
