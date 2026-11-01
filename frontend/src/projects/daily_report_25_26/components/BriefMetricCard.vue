<template>
  <article class="metric-card">
    <div class="metric-top">
      <h4>{{ metric.label }}</h4>
      <span v-if="metric.trend.yoy_run >= 3" class="continuity">连续 {{ metric.trend.yoy_run }} 日</span>
    </div>

    <div class="metric-value">
      {{ fmt(metric.value, metric.digits) }}
      <span>{{ metric.unit }}</span>
    </div>

    <p class="metric-change">
      <BriefComparisonText :text="changeText(metric)" />
    </p>

    <p v-if="metric.trend.text" class="metric-trend">
      <BriefComparisonText :text="metric.trend.text" />
    </p>

    <!-- 弹窗触发按钮 (替换原本的 details 折叠) -->
    <div class="metric-action-bar">
      <button type="button" class="metric-modal-btn" @click="openModal">
        <span class="btn-text">趋势走势与依据明细</span>
        <span class="btn-arrow">›</span>
      </button>
    </div>

    <!-- 模态弹窗：展示比较依据、近七日走势图与逐日数据表 -->
    <Teleport to="body">
      <div
        v-if="opened"
        :class="['editorial-modal-backdrop', `theme-${briefTheme}`]"
        @click.self="closeModal"
      >
        <div
          class="editorial-modal-dialog"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="`modal-title-${metric.key}`"
        >
          <!-- 弹窗报头 -->
          <div class="modal-header">
            <div class="modal-header-main">
              <span class="modal-edition-tag">指标专项内参</span>
              <h3 :id="`modal-title-${metric.key}`" class="modal-title">
                {{ metric.label }} · 趋势分析与数据依据
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

          <!-- 弹窗正文 -->
          <div class="modal-body">
            <!-- 核心数据看板栏 -->
            <div class="modal-stat-summary">
              <div class="stat-pill">
                <span class="pill-label">本期实际</span>
                <strong class="pill-val">{{ fmt(metric.value, metric.digits) }} <small>{{ metric.unit }}</small></strong>
              </div>
              <div class="stat-pill">
                <span class="pill-label">同期基准</span>
                <strong class="pill-val">{{ fmt(metric.peer, metric.digits) }} <small>{{ metric.unit }}</small></strong>
              </div>
              <div class="stat-pill">
                <span class="pill-label">同比变动</span>
                <span class="pill-change"><BriefComparisonText :text="changeText(metric)" /></span>
              </div>
              <div v-if="metric.trend.yoy_run >= 3" class="stat-pill">
                <span class="pill-label">趋势状态</span>
                <span class="continuity-label">连续 {{ metric.trend.yoy_run }} 日同比同向</span>
              </div>
            </div>

            <!-- 比较依据与日均描述 -->
            <div class="modal-analysis-text">
              <p class="desc-line">
                <BriefComparisonText :text="metric.description" />
              </p>
              <p class="averages-line">
                近七日日均：本期 <strong>{{ fmt(metric.trend.current_average, metric.digits) }}</strong> {{ metric.unit }}，
                同期 <strong>{{ fmt(metric.trend.peer_average, metric.digits) }}</strong> {{ metric.unit }}。
              </p>
            </div>

            <!-- ECharts 趋势对比图 -->
            <div class="modal-chart-box">
              <div class="box-heading">
                <span class="box-badge">走势图</span>
                <span class="box-title">近七日连续趋势比对（实线：本期 / 虚线：同期）</span>
              </div>
              <div class="chart-container">
                <BriefTrendChart :metric="metric" />
              </div>
            </div>

            <!-- 逐日数据明细台账 -->
            <div class="modal-table-box">
              <div class="box-heading">
                <span class="box-badge">逐日表</span>
                <span class="box-title">近七日逐日数据对照台账</span>
              </div>
              <div class="table-scroll-wrap">
                <table class="modal-ledger-table">
                  <thead>
                    <tr>
                      <th>本期日期</th>
                      <th class="num-col">本期数值 ({{ metric.unit }})</th>
                      <th>同期对照日</th>
                      <th class="num-col">同期数值 ({{ metric.unit }})</th>
                      <th class="num-col">同期差额</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="point in metric.points" :key="point.date">
                      <td class="date-col">{{ point.date }}</td>
                      <td class="num-col bold-val">{{ fmt(point.value, metric.digits) }}</td>
                      <td class="date-col peer-col">{{ point.peer_date }}</td>
                      <td class="num-col">{{ fmt(point.peer, metric.digits) }}</td>
                      <td class="num-col">
                        <BriefComparisonText
                          v-if="point.value != null && point.peer != null"
                          :text="calcDeltaText(point.value - point.peer, metric.digits)"
                          :delta="point.value - point.peer"
                          :digits="metric.digits"
                        />
                        <span v-else>—</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <!-- 弹窗页脚操作栏 -->
          <div class="modal-footer">
            <span class="footer-tip">按 Esc 键或点击外部遮罩均可快速关闭</span>
            <button type="button" class="modal-confirm-btn" @click="closeModal">完成阅览</button>
          </div>
        </div>
      </div>
    </Teleport>
  </article>
</template>

<script setup>
import { defineAsyncComponent, inject, onBeforeUnmount, ref } from 'vue'
import { formatBriefNumber as fmt, changeText } from '../composables/dailyBriefPresentation'
import BriefComparisonText from './BriefComparisonText.vue'

defineProps({
  metric: { type: Object, required: true },
})

// 响应父级注入的报纸主题，默认 broadsheet
const briefTheme = inject('briefTheme', ref('broadsheet'))

const opened = ref(false)
const BriefTrendChart = defineAsyncComponent(() => import('./BriefTrendChart.vue'))

function calcDeltaText(delta, digits) {
  if (delta == null || !Number.isFinite(delta)) return '—'
  return `${delta > 0 ? '+' : ''}${fmt(delta, digits)}`
}

function onKeyDown(e) {
  if (e.key === 'Escape' && opened.value) {
    closeModal()
  }
}

function openModal() {
  opened.value = true
  document.addEventListener('keydown', onKeyDown)
}

function closeModal() {
  opened.value = false
  document.removeEventListener('keydown', onKeyDown)
}

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeyDown)
})
</script>

<style scoped>
.metric-card {
  padding: 12px 14px 10px;
  border: 1px solid #e3e8ec;
  border-radius: 12px;
  background: #fff;
  min-width: 0;
  overflow-wrap: anywhere;
  display: flex;
  flex-direction: column;
}

.metric-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

h4 {
  margin: 0;
  color: #344956;
  font-size: 14px;
  font-weight: 600;
}

.continuity {
  font-size: 11px;
  color: #376875;
  background: #edf5f5;
  padding: 3px 7px;
  border-radius: 5px;
}

.metric-value {
  margin: 6px 0;
  color: #152f3d;
  font-size: clamp(25px, 6vw, 30px);
  font-weight: 650;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}

.metric-value span {
  font-size: 12px;
  color: #71808b;
  font-weight: 400;
}

p {
  line-height: 1.6;
  margin: 6px 0;
  font-size: 13px;
}

.metric-change {
  color: #344e5c;
}

.metric-trend {
  color: #74828d;
  font-size: 12px;
  margin-bottom: 8px;
}

/* 弹窗唤起操作条 */
.metric-action-bar {
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.metric-modal-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 6px 0;
  background: transparent;
  border: none;
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  color: #275e70;
  cursor: pointer;
  transition: color 0.15s ease, opacity 0.15s ease;
}

.metric-modal-btn:hover {
  opacity: 0.8;
}

.btn-arrow {
  font-size: 14px;
}

/* ==========================================================================
   模态弹窗系统 (Teleported Modal)
   ========================================================================== */
.editorial-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 2100;
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

.editorial-modal-dialog {
  width: 100%;
  max-width: 680px;
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

/* 弹窗正文滚动区 */
.modal-body {
  padding: 18px 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* 数据看板小胶囊 */
.modal-stat-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 10px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.03);
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.stat-pill {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.pill-label {
  font-size: 11px;
  opacity: 0.7;
}

.pill-val {
  font-size: 16px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.pill-val small {
  font-size: 11px;
  font-weight: 400;
  opacity: 0.8;
}

.pill-change {
  font-size: 12px;
}

.continuity-label {
  font-size: 11px;
  font-weight: 600;
  color: #9e2a2b;
}

/* 分析文本 */
.modal-analysis-text {
  padding: 10px 12px;
  border-left: 3px solid currentColor;
  background: rgba(0, 0, 0, 0.02);
  font-size: 13px;
  line-height: 1.65;
}

.desc-line {
  margin: 0 0 6px;
}

.averages-line {
  margin: 0;
  opacity: 0.85;
}

/* 图表与表格外框 */
.modal-chart-box, .modal-table-box {
  border: 1px solid rgba(0, 0, 0, 0.1);
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.45);
}

.box-heading {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}

.box-badge {
  font-size: 10px;
  font-weight: 700;
  background: currentColor;
  color: #fff;
  padding: 1px 5px;
  border-radius: 2px;
}

.theme-broadsheet .box-badge {
  background-color: #9e2a2b;
  color: #fff;
}

.theme-financial .box-badge {
  background-color: #14232c;
  color: #fff1e5;
}

.theme-modernist .box-badge {
  background-color: #2563eb;
  color: #fff;
}

.box-title {
  font-size: 12px;
  font-weight: 700;
}

.chart-container {
  height: 200px;
  width: 100%;
}

/* 台账表格 */
.table-scroll-wrap {
  overflow-x: auto;
}

.modal-ledger-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  line-height: 1.5;
}

.modal-ledger-table th {
  border-bottom: 1.5px solid currentColor;
  padding: 6px 4px;
  text-align: left;
  font-size: 11px;
  font-weight: 700;
  opacity: 0.75;
}

.modal-ledger-table td {
  border-bottom: 1px solid rgba(0, 0, 0, 0.07);
  padding: 6px 4px;
}

.modal-ledger-table .num-col {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.modal-ledger-table .bold-val {
  font-weight: 700;
}

.modal-ledger-table .date-col {
  font-family: -apple-system, BlinkMacSystemFont, monospace;
  font-size: 11px;
}

.modal-ledger-table .peer-col {
  opacity: 0.75;
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

@media (max-width: 600px) {
  .modal-stat-summary {
    grid-template-columns: 1fr 1fr;
  }
  .modal-footer {
    flex-direction: column;
    gap: 8px;
  }
}
</style>
