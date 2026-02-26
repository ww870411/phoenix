<template>
  <div class="editor-window">
    <header class="window-head">
      <div>
        <h1>后台文件编辑器</h1>
        <p class="path">{{ filePath || '未指定文件路径' }}</p>
        <p v-if="isJsonFile" class="mode mode-json">JSON 专用模式：已启用语法校验</p>
      </div>
      <div class="actions">
        <span v-if="isDirty" class="dirty">未保存</span>
        <button
          v-if="isJsonFile"
          class="btn ghost"
          type="button"
          :disabled="loading || saving"
          @click="formatJson"
        >
          格式化 JSON
        </button>
        <button class="btn ghost" type="button" @click="closeWithoutSave">不保存关闭</button>
        <button
          class="btn primary"
          type="button"
          :disabled="saving || !isDirty || !filePath || !jsonValidation.valid"
          @click="saveAndClose"
        >
          {{ saving ? '保存中…' : '保存并关闭' }}
        </button>
      </div>
    </header>

    <main class="window-body">
      <div v-if="loading" class="state">文件读取中…</div>
      <template v-else>
        <textarea
          ref="editorRef"
          v-model="content"
          class="editor"
          placeholder="无法读取文件内容"
        />
        <div v-if="isJsonFile && !jsonValidation.valid" class="json-error-panel">
          <div class="json-error-title">
            JSON 语法错误
            <span v-if="jsonValidation.line">
              （第 {{ jsonValidation.line }} 行，第 {{ jsonValidation.column }} 列）
            </span>
          </div>
          <div class="json-error-message">{{ jsonValidation.error }}</div>
          <button
            v-if="jsonValidation.line"
            class="btn ghost locate-btn"
            type="button"
            @click="jumpToJsonError"
          >
            定位到错误位置
          </button>
          <pre v-if="jsonValidation.lineText" class="json-error-line">{{ jsonValidation.lineText }}</pre>
          <pre v-if="jsonValidation.pointerLine" class="json-error-pointer">{{ jsonValidation.pointerLine }}</pre>
        </div>
      </template>
      <footer class="window-foot">
        <span>字数：{{ content.length }}</span>
        <span v-if="isJsonFile && !jsonValidation.valid" class="error-text">
          JSON 错误{{ jsonValidation.line ? `（第 ${jsonValidation.line} 行，第 ${jsonValidation.column} 列）` : '' }}：
          {{ jsonValidation.error }}
        </span>
        <span v-else>{{ message }}</span>
      </footer>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'
import { readAdminFile, saveAdminFile } from '../services/api'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const filePath = ref('')
const content = ref('')
const originalContent = ref('')
const loading = ref(false)
const saving = ref(false)
const message = ref('')
const editorRef = ref(null)

const isDirty = computed(() => content.value !== originalContent.value)
const isJsonFile = computed(() => String(filePath.value || '').toLowerCase().endsWith('.json'))

function parseJsonPosition(errorMessage, source) {
  const text = String(errorMessage || '')
  const matched = text.match(/position\s+(\d+)/i)
  if (!matched) return { line: null, column: null }
  const index = Number(matched[1])
  if (!Number.isFinite(index) || index < 0) return { line: null, column: null }
  const safe = String(source || '').slice(0, index)
  const lines = safe.split('\n')
  return {
    line: lines.length,
    column: (lines[lines.length - 1] || '').length + 1,
  }
}

const jsonValidation = computed(() => {
  if (!isJsonFile.value) return { valid: true, error: '', line: null, column: null }
  try {
    JSON.parse(content.value || '')
    return {
      valid: true,
      error: '',
      line: null,
      column: null,
      lineText: '',
      pointerLine: '',
    }
  } catch (err) {
    const messageText = err instanceof Error ? err.message : 'JSON 语法错误'
    const { line, column } = parseJsonPosition(messageText, content.value || '')
    const rows = String(content.value || '').split('\n')
    const lineText =
      line && line > 0 && line <= rows.length
        ? rows[line - 1]
        : ''
    const pointerLine =
      lineText && column && column > 0
        ? `${' '.repeat(Math.max(0, column - 1))}^`
        : ''
    return { valid: false, error: messageText, line, column, lineText, pointerLine }
  }
})

async function loadFile() {
  const raw = String(route.query.path || '')
  filePath.value = raw
  if (!raw) {
    message.value = '缺少文件路径参数'
    return
  }
  loading.value = true
  message.value = ''
  try {
    const payload = await readAdminFile(raw)
    content.value = String(payload?.content || '')
    originalContent.value = content.value
  } catch (err) {
    console.error(err)
    message.value = err instanceof Error ? err.message : '读取失败'
  } finally {
    loading.value = false
  }
}

async function saveAndClose() {
  if (!filePath.value || !isDirty.value) {
    window.close()
    return
  }
  if (!jsonValidation.value.valid) {
    message.value = 'JSON 语法错误，请修复后再保存。'
    jumpToJsonError()
    return
  }
  saving.value = true
  message.value = ''
  try {
    await saveAdminFile(filePath.value, content.value)
    originalContent.value = content.value
    message.value = '保存成功'
    if (window.opener) {
      window.opener.postMessage({ type: 'admin-file-saved', path: filePath.value }, window.location.origin)
    }
    window.close()
  } catch (err) {
    console.error(err)
    message.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    saving.value = false
  }
}

function closeWithoutSave() {
  if (isDirty.value) {
    const ok = window.confirm('存在未保存改动，确认不保存并关闭？')
    if (!ok) return
  }
  window.close()
}

function formatJson() {
  if (!isJsonFile.value) return
  try {
    const parsed = JSON.parse(content.value || '')
    content.value = `${JSON.stringify(parsed, null, 2)}\n`
    message.value = 'JSON 已格式化'
  } catch (err) {
    message.value = err instanceof Error ? `JSON 无法格式化：${err.message}` : 'JSON 无法格式化'
  }
}

function jumpToJsonError() {
  const line = Number(jsonValidation.value?.line || 0)
  const column = Number(jsonValidation.value?.column || 0)
  if (!line || !column) return
  const source = String(content.value || '')
  const rows = source.split('\n')
  const clampedLine = Math.max(1, Math.min(line, rows.length || 1))
  const targetLineText = rows[clampedLine - 1] || ''
  const clampedColumn = Math.max(1, Math.min(column, targetLineText.length + 1))

  let absolute = 0
  for (let i = 0; i < clampedLine - 1; i += 1) {
    absolute += rows[i].length + 1
  }
  absolute += clampedColumn - 1

  const editor = editorRef.value
  if (!editor) return
  editor.focus()
  editor.setSelectionRange(absolute, absolute)
}

function onKeydown(event) {
  const isSaveKey = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's'
  if (!isSaveKey) return
  event.preventDefault()
  if (!saving.value && isDirty.value) saveAndClose()
}

onMounted(async () => {
  await auth.bootstrap()
  if (!auth.isAuthenticated || !auth.canAccessAdminConsole) {
    router.replace('/projects')
    return
  }
  window.addEventListener('keydown', onKeydown)
  await loadFile()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.editor-window {
  min-height: 100vh;
  background: #f8fafc;
  color: #0f172a;
  padding: 14px;
  display: grid;
  gap: 10px;
}

.window-head {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.window-head h1 {
  margin: 0;
  font-size: 18px;
}

.path {
  margin: 6px 0 0;
  color: #475569;
  font-size: 12px;
}

.mode {
  margin: 6px 0 0;
  font-size: 12px;
}

.mode-json {
  color: #0f766e;
}

.actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dirty {
  color: #b45309;
  background: #fef3c7;
  border: 1px solid #fcd34d;
  border-radius: 999px;
  font-size: 12px;
  padding: 2px 8px;
}

.window-body {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px;
  display: grid;
  gap: 8px;
}

.state {
  padding: 20px 0;
  color: #475569;
}

.editor {
  width: 100%;
  min-height: calc(100vh - 190px);
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 10px;
  font-family: Consolas, 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
}

.locate-btn {
  margin-top: 8px;
}

.window-foot {
  font-size: 12px;
  color: #64748b;
  display: flex;
  justify-content: space-between;
}

.error-text {
  color: #b91c1c;
}

.json-error-panel {
  border: 1px solid #fecaca;
  background: #fef2f2;
  border-radius: 8px;
  padding: 10px;
  color: #7f1d1d;
}

.json-error-title {
  font-size: 12px;
  font-weight: 700;
}

.json-error-message {
  margin-top: 6px;
  font-size: 12px;
}

.json-error-line,
.json-error-pointer {
  margin: 6px 0 0;
  background: #fff;
  border: 1px solid #fecaca;
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 12px;
  line-height: 1.4;
  overflow: auto;
}

.json-error-pointer {
  margin-top: 4px;
  color: #dc2626;
}

.btn {
  height: 32px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid transparent;
  cursor: pointer;
}

.btn.primary {
  background: #2563eb;
  color: #fff;
}

.btn.ghost {
  background: #fff;
  color: #334155;
  border-color: #cbd5e1;
}
</style>
