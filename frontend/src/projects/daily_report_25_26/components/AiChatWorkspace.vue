<template>
  <div class="ai-chat-floating">
    <transition name="fade-scale">
      <button
        v-if="!expanded"
        type="button"
        class="ai-chat-floating__launcher"
        @click="expanded = true"
        :aria-label="title"
      >
        <span class="ai-chat-floating__launcher-icon">✨</span>
        <span class="ai-chat-floating__launcher-text">智能助手</span>
      </button>

      <div v-else class="ai-chat-workspace">
        <div class="ai-chat-workspace__header">
          <div class="ai-chat-workspace__title-area">
            <h4>{{ title }}</h4>
            <div class="ai-chat-workspace__modes">
              <button
                type="button"
                class="mode-pill"
                :class="{ active: activeMode === 'free' }"
                :disabled="isLoading"
                @click="switchMode('free')"
              >
                自由对话
              </button>
              <button
                type="button"
                class="mode-pill"
                :class="{ active: activeMode === 'query_context' }"
                :disabled="isLoading || !queryModeEnabled"
                @click="switchMode('query_context')"
              >
                数据分析
              </button>
            </div>
          </div>
          <button type="button" class="btn-close" @click="expanded = false">×</button>
        </div>

        <div class="ai-chat-workspace__messages" ref="messageContainer">
          <div v-if="currentMessages.length === 0" class="ai-chat-workspace__empty">
            <div class="empty-icon">🤖</div>
            <p>{{ activeMode === 'free' ? freeDescription : queryDescription }}</p>
          </div>
          
          <div
            v-for="(message, idx) in currentMessages"
            :key="`${activeMode}-${idx}`"
            class="ai-chat-workspace__message-wrapper"
            :class="message.role === 'user' ? 'is-user' : 'is-assistant'"
          >
            <div class="ai-chat-workspace__bubble">
              <div class="ai-chat-workspace__content">{{ message.content }}</div>
            </div>
          </div>

          <div v-if="isLoading" class="ai-chat-workspace__message-wrapper is-assistant">
            <div class="ai-chat-workspace__bubble is-loading">
              <span class="dot"></span><span class="dot"></span><span class="dot"></span>
            </div>
          </div>
        </div>

        <div class="ai-chat-workspace__footer">
          <div v-if="currentError" class="ai-chat-workspace__error">
            ⚠️ {{ currentError }}
          </div>
          <div class="ai-chat-workspace__composer">
            <textarea
              v-model="inputText"
              class="ai-chat-workspace__input"
              rows="1"
              maxlength="2000"
              :disabled="isLoading"
              :placeholder="activeMode === 'free' ? freePlaceholder : queryPlaceholder"
              @keydown.enter="handleEnter"
            ></textarea>
            <button 
              type="button" 
              class="btn-send" 
              :disabled="isLoading || !inputText.trim()" 
              @click="sendMessage"
            >
              <span v-if="!isLoading">↑</span>
              <span v-else class="spinner"></span>
            </button>
          </div>
          <div class="ai-chat-workspace__footer-actions">
            <button type="button" class="btn-text" @click="resetCurrentConversation">清除会话</button>
            <span class="session-tag" v-if="currentSessionId">ID: {{ currentSessionId.slice(0, 8) }}</span>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed, reactive, ref, nextTick, watch } from 'vue'

const props = defineProps({
  title: { type: String, default: 'Phoenix AI' },
  freeDescription: { type: String, default: '你好！我是 Phoenix AI，有什么可以帮你的？' },
  queryDescription: { type: String, default: '已准备好，请围绕当前查询结果提问。' },
  freePlaceholder: { type: String, default: '问点什么...' },
  queryPlaceholder: { type: String, default: '分析一下这份数据...' },
  queryModeEnabled: { type: Boolean, default: false },
  buildQueryContext: { type: Function, default: null },
  sendChat: { type: Function, required: true },
})

const expanded = ref(false)
const activeMode = ref('free')
const inputText = ref('')
const messageContainer = ref(null)

const conversations = reactive({
  free: { messages: [], sessionId: '', loading: false, error: '' },
  query_context: { messages: [], sessionId: '', loading: false, error: '' },
})

const currentConversation = computed(() => conversations[activeMode.value])
const currentMessages = computed(() => currentConversation.value.messages)
const currentSessionId = computed(() => currentConversation.value.sessionId)
const currentError = computed(() => currentConversation.value.error)
const isLoading = computed(() => Boolean(currentConversation.value.loading))

function scrollToBottom() {
  nextTick(() => {
    if (messageContainer.value) {
      messageContainer.value.scrollTop = messageContainer.value.scrollHeight
    }
  })
}

watch(currentMessages, () => scrollToBottom(), { deep: true })
watch(expanded, (val) => { if (val) scrollToBottom() })

function switchMode(mode) {
  if (mode === 'query_context' && !props.queryModeEnabled) return
  activeMode.value = mode
}

function resetCurrentConversation() {
  const target = conversations[activeMode.value]
  target.messages = []
  target.sessionId = ''
  target.error = ''
  inputText.value = ''
}

function handleEnter(e) {
  if (e.shiftKey) return
  e.preventDefault()
  sendMessage()
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || isLoading.value) return

  const target = conversations[activeMode.value]
  let contextPayload = null
  
  if (activeMode.value === 'query_context') {
    try {
      contextPayload = await Promise.resolve(props.buildQueryContext?.())
    } catch (error) {
      const msg = error?.message || String(error)
      target.error = `构建查询上下文失败：${msg}`
      return
    }
    if (!contextPayload) {
      target.error = '请先执行数据查询后再进行分析。'
      return
    }
  }

  target.loading = true
  target.error = ''
  target.messages.push({ role: 'user', content: text })
  inputText.value = ''

  try {
    const payload = await props.sendChat({
      mode: activeMode.value,
      message: text,
      session_id: target.sessionId || undefined,
      history: target.messages.map(m => ({ role: m.role, content: m.content })),
      context: contextPayload || undefined,
    })
    
    target.sessionId = payload?.session_id || target.sessionId
    target.messages.push({ 
      role: 'assistant', 
      content: payload?.answer || '抱歉，我没能生成回复。' 
    })
  } catch (error) {
    const msg = error.message || String(error)
    target.error = msg.includes('Failed to fetch') ? '网络连接失败，请检查后端状态。' : msg
    target.messages.push({ role: 'assistant', content: `❌ 出错了：${target.error}` })
  } finally {
    target.loading = false
  }
}
</script>

<style scoped>
.ai-chat-floating { position: fixed; right: 24px; bottom: 24px; z-index: 2000; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }

/* 启动器图标 */
.ai-chat-floating__launcher { 
  width: 64px; height: 64px; border: none; border-radius: 32px; 
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); 
  color: #fff; display: flex; flex-direction: column; align-items: center; justify-content: center;
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.3); cursor: pointer; transition: transform 0.2s;
}
.ai-chat-floating__launcher:hover { transform: scale(1.05); }
.ai-chat-floating__launcher-icon { font-size: 24px; margin-bottom: 2px; }
.ai-chat-floating__launcher-text { font-size: 11px; font-weight: 600; text-transform: uppercase; opacity: 0.9; }

/* 主工作区 */
.ai-chat-workspace { 
  width: 380px; height: 600px; max-height: calc(100vh - 100px);
  background: #ffffff; border-radius: 20px; display: flex; flex-direction: column;
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.15); border: 1px solid #f1f5f9; overflow: hidden;
}

/* 头部 */
.ai-chat-workspace__header { 
  padding: 16px 20px; background: #fff; border-bottom: 1px solid #f1f5f9;
  display: flex; justify-content: space-between; align-items: center;
}
.ai-chat-workspace__title-area h4 { margin: 0; font-size: 16px; color: #1e293b; }
.ai-chat-workspace__modes { display: flex; gap: 4px; margin-top: 8px; }
.mode-pill { 
  padding: 4px 10px; border-radius: 12px; font-size: 11px; border: 1px solid #e2e8f0;
  background: #f8fafc; color: #64748b; cursor: pointer; transition: all 0.2s;
}
.mode-pill.active { background: #eff6ff; color: #2563eb; border-color: #bfdbfe; font-weight: 600; }
.btn-close { 
  background: #f1f5f9; border: none; width: 28px; height: 28px; border-radius: 14px;
  font-size: 20px; color: #64748b; cursor: pointer; display: flex; align-items: center; justify-content: center;
}

/* 消息列表 */
.ai-chat-workspace__messages { 
  flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 16px;
  background: #fdfdfd; scroll-behavior: smooth;
}
.ai-chat-workspace__empty { 
  flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: #94a3b8; text-align: center; padding: 0 40px;
}
.empty-icon { font-size: 48px; margin-bottom: 12px; opacity: 0.5; }

.ai-chat-workspace__message-wrapper { display: flex; width: 100%; }
.ai-chat-workspace__message-wrapper.is-user { justify-content: flex-end; }
.ai-chat-workspace__message-wrapper.is-assistant { justify-content: flex-start; }

.ai-chat-workspace__bubble { 
  max-width: 85%; padding: 12px 16px; border-radius: 18px; font-size: 14px; line-height: 1.5;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}
.ai-chat-workspace__content { white-space: pre-wrap; word-break: break-word; }
.is-user .ai-chat-workspace__bubble { 
  background: #2563eb; color: #ffffff; border-bottom-right-radius: 4px;
}
.is-assistant .ai-chat-workspace__bubble { 
  background: #f1f5f9; color: #1e293b; border-bottom-left-radius: 4px;
}

/* 输入区 */
.ai-chat-workspace__footer { padding: 16px 20px; background: #fff; border-top: 1px solid #f1f5f9; }
.ai-chat-workspace__composer { 
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 24px;
  display: flex; align-items: flex-end; padding: 8px 8px 8px 16px; transition: border-color 0.2s;
}
.ai-chat-workspace__composer:focus-within { border-color: #3b82f6; background: #fff; }
.ai-chat-workspace__input { 
  flex: 1; border: none; background: transparent; padding: 8px 0; max-height: 120px;
  resize: none; font-size: 14px; color: #1e293b; outline: none;
}
.btn-send { 
  width: 32px; height: 32px; border-radius: 16px; border: none;
  background: #2563eb; color: #fff; cursor: pointer; font-size: 18px;
  display: flex; align-items: center; justify-content: center; margin-left: 8px; flex-shrink: 0;
}
.btn-send:disabled { background: #cbd5e1; cursor: not-allowed; }

.ai-chat-workspace__footer-actions { 
  display: flex; justify-content: space-between; align-items: center; margin-top: 10px; padding: 0 4px;
}
.btn-text { background: none; border: none; color: #94a3b8; font-size: 12px; cursor: pointer; }
.btn-text:hover { color: #64748b; }
.session-tag { font-size: 10px; color: #cbd5e1; font-family: monospace; }

.ai-chat-workspace__error { font-size: 12px; color: #ef4444; margin-bottom: 8px; background: #fef2f2; padding: 6px 10px; border-radius: 8px; }

/* 动画与 Loading */
.fade-scale-enter-active, .fade-scale-leave-active { transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1); }
.fade-scale-enter-from, .fade-scale-leave-to { opacity: 0; transform: scale(0.9) translateY(20px); }

.is-loading .dot { 
  display: inline-block; width: 6px; height: 6px; background: #64748b; 
  border-radius: 3px; margin-right: 3px; animation: wave 1.3s infinite; 
}
.is-loading .dot:nth-child(2) { animation-delay: -1.1s; }
.is-loading .dot:nth-child(3) { animation-delay: -0.9s; }

@keyframes wave { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-4px); } }

.spinner { width: 14px; height: 14px; border: 2px solid #fff; border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* 滚动条 */
.ai-chat-workspace__messages::-webkit-scrollbar { width: 4px; }
.ai-chat-workspace__messages::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 2px; }
</style>
