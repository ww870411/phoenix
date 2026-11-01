<template>
  <div class="subject-content">
    <!-- 主版面按指标键呈现六项生产经营指标 -->
    <div class="subject-metrics">
      <BriefMetricCard
        v-for="metric in metricPanels.primary"
        :key="metric.key"
        :metric="metric"
      />
    </div>

    <!-- 弹窗触发专栏条 (替换原本的 details 折叠) -->
    <div v-if="metricPanels.supplement.length" class="more-metrics-banner">
      <button
        type="button"
        class="more-metrics-trigger"
        @click="openModal"
      >
        <span class="banner-badge">专栏副刊</span>
        <span class="banner-text">
          查阅其余 {{ metricPanels.supplement.length }} 项重点指标（实际利润、供热与销售量、水电单耗等）
        </span>
        <span class="banner-arrow">››</span>
      </button>
    </div>

    <!-- 模态弹窗：展示其余全部指标专刊 -->
    <Teleport to="body">
      <div
        v-if="modalVisible"
        :class="['editorial-modal-backdrop', `theme-${briefTheme}`]"
        @click.self="closeModal"
      >
        <div
          class="editorial-modal-dialog more-metrics-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="more-metrics-title"
        >
          <!-- 弹窗报头 -->
          <div class="modal-header">
            <div class="modal-header-main">
              <span class="modal-edition-tag">大连洁净能源 · 集团经营总览副刊</span>
              <h3 id="more-metrics-title" class="modal-title">
                集团经营重点与单耗指标专刊
              </h3>
            </div>
            <button
              type="button"
              class="modal-close-btn"
              title="关闭窗口 (Esc)"
              @click="closeModal"
            >
              ✕
            </button>
          </div>

          <!-- 弹窗导读提示 -->
          <div class="modal-lead-note">
            <span class="lead-tag">编印说明</span>
            <p>
              本专刊收录了全集团实际边际利润、供热量、高温水销售量、售汽量、售电量、万平方米净投诉量及供暖水电单耗。点击任一指标卡片底部的明细链接，可进一步查阅近七日走势图与逐日对比数据。
            </p>
          </div>

          <!-- 弹窗正文：卡片网格列表 -->
          <div class="modal-body">
            <div class="dialog-metrics-grid">
              <BriefMetricCard
                v-for="metric in metricPanels.supplement"
                :key="metric.key"
                :metric="metric"
              />
            </div>
          </div>

          <!-- 弹窗页脚 -->
          <div class="modal-footer">
            <span class="footer-tip">按 Esc 键或点击外部遮罩均可退出副刊</span>
            <button type="button" class="modal-confirm-btn" @click="closeModal">返回主报版面</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, ref } from 'vue'
import BriefMetricCard from './BriefMetricCard.vue'
import { selectBriefMetricPanels } from '../composables/dailyBriefPresentation'

const props = defineProps({
  subject: { type: Object, required: true },
})
const metricPanels = computed(() => selectBriefMetricPanels(props.subject.metrics))

const briefTheme = inject('briefTheme', ref('broadsheet'))
const modalVisible = ref(false)

function onKeyDown(e) {
  if (e.key === 'Escape' && modalVisible.value) {
    closeModal()
  }
}

function openModal() {
  modalVisible.value = true
  document.addEventListener('keydown', onKeyDown)
}

function closeModal() {
  modalVisible.value = false
  document.removeEventListener('keydown', onKeyDown)
}

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeyDown)
})
</script>

<style scoped>
.subject-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.subject-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

/* 专刊触发条 */
.more-metrics-banner {
  margin-top: 4px;
}

.more-metrics-trigger {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  background: rgba(0, 0, 0, 0.03);
  border: 1px dashed rgba(0, 0, 0, 0.18);
  border-radius: 4px;
  font: inherit;
  font-size: 13px;
  color: inherit;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.more-metrics-trigger:hover {
  background: rgba(0, 0, 0, 0.06);
  border-style: solid;
}

.banner-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 7px;
  background-color: var(--accent-color, #9e2a2b);
  color: #ffffff !important;
  border-radius: 2px;
  white-space: nowrap;
  flex-shrink: 0;
}

.theme-financial .banner-badge {
  background-color: #14232c;
  color: #fff1e5 !important;
}

.banner-text {
  flex: 1;
  font-weight: 600;
  line-height: 1.4;
}

.banner-arrow {
  font-size: 15px;
  font-weight: 700;
}

/* ==========================================================================
   专刊模态弹窗系统 (Teleported Modal)
   ========================================================================== */
.editorial-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 2050;
  background: rgba(18, 22, 28, 0.55);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px 16px;
  overflow-y: auto;
  box-sizing: border-box;
}

.editorial-modal-backdrop *,
.editorial-modal-backdrop *::before,
.editorial-modal-backdrop *::after {
  box-sizing: border-box;
}

.more-metrics-dialog {
  width: 100%;
  max-width: 900px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
  overflow: hidden;
}

/* 主题适配 */
.theme-broadsheet .editorial-modal-dialog {
  background-color: #faf7ef;
  color: #1f2529;
  border: 1px solid #d5cebf;
  font-family: 'Source Han Serif SC', 'Noto Serif CJK SC', 'SimSun', serif;
}

.theme-financial .editorial-modal-dialog {
  background-color: #fff1e5;
  color: #14232c;
  border: 1px solid rgba(20, 35, 44, 0.25);
  font-family: 'Georgia', 'Times New Roman', serif;
}

.theme-modernist .editorial-modal-dialog {
  background-color: #ffffff;
  color: #0f172a;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* 弹窗头部 */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 20px 12px;
  border-bottom: 2px solid currentColor;
}

.modal-header-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.modal-edition-tag {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
  opacity: 0.7;
}

.modal-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.3;
}

.modal-close-btn {
  background: transparent;
  border: none;
  font-size: 18px;
  font-weight: 600;
  color: inherit;
  cursor: pointer;
  padding: 4px 8px;
  opacity: 0.65;
  transition: opacity 0.15s ease;
}

.modal-close-btn:hover {
  opacity: 1;
}

/* 导读小注 */
.modal-lead-note {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 20px;
  background: rgba(0, 0, 0, 0.02);
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  font-size: 12px;
  line-height: 1.6;
}

.lead-tag {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 5px;
  border: 1px solid currentColor;
  flex-shrink: 0;
}

.modal-lead-note p {
  margin: 0;
  opacity: 0.8;
}

/* 弹窗卡片网格 */
.modal-body {
  padding: 20px;
  overflow-y: auto;
}

.dialog-metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 14px;
}

/* 弹窗页脚 */
.modal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  background: rgba(0, 0, 0, 0.02);
}

.footer-tip {
  font-size: 11px;
  opacity: 0.6;
}

.modal-confirm-btn {
  border: 1px solid currentColor;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  padding: 6px 18px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.modal-confirm-btn:hover {
  background: currentColor;
  color: #fff;
}

@media (max-width: 680px) {
  .subject-metrics {
    grid-template-columns: 1fr;
  }
  .dialog-metrics-grid {
    grid-template-columns: 1fr;
  }
  .modal-lead-note {
    flex-direction: column;
  }
}
</style>
