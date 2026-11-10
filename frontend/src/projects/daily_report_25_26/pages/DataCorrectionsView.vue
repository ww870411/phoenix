<template>
  <div class="correction-page">
    <AppHeader />
    <main class="container correction-main">
      <Breadcrumbs :items="breadcrumbItems" />
      <header class="correction-heading">
        <div class="heading-copy">
          <div class="heading-title-row">
            <h1>数据修正申请记录</h1>
            <span v-if="!loading && total > 0" class="heading-total-badge">共 {{ total }} 条</span>
          </div>
          <p>申请提交后原数据保持不变，全局管理员确认后生效并留下不可篡改的修正全过程记录。</p>
        </div>
        <div class="correction-filters">
          <div class="filter-item">
            <label for="correction-status-filter">状态筛选</label>
            <div class="select-wrap">
              <select id="correction-status-filter" v-model="status" :disabled="busy" @change="offset = 0; load()">
                <option value="">全部状态</option>
                <option v-for="(label, key) in labels" :key="key" :value="key">{{ label }}</option>
              </select>
            </div>
          </div>
          <button class="btn ghost btn-refresh" :disabled="busy" @click="load" title="刷新列表">
            <span class="refresh-icon" :class="{ 'is-spinning': loading }">↻</span>
            {{ loading ? '刷新中…' : '刷新' }}
          </button>
        </div>
      </header>

      <p v-if="error" role="alert" class="correction-notice correction-error">{{ error }}</p>
      <p v-if="message" role="status" class="correction-notice correction-success">{{ message }}</p>

      <div v-if="loading" class="correction-empty correction-loading" role="status">
        <div class="loading-spinner"></div>
        <p>正在读取申请记录…</p>
      </div>

      <div v-else-if="!error && !records.length" class="correction-empty">
        <div class="empty-icon">📋</div>
        <p class="empty-title">暂无修正申请</p>
        <p class="empty-desc">
          {{ status ? `当前没有「${labels[status]}」状态的修正申请。` : '各单位填报人在填报页面提交的修正申请将在此集中呈现与审核。' }}
        </p>
      </div>

      <div v-if="!loading && !error && records.length" class="correction-records">
        <article v-for="record in records" :key="record.id" :class="['correction-record', `correction-record--${record.status}`]">
          <header class="record-heading">
            <div class="record-title">
              <span class="request-number">申请 #{{ record.id }}</span>
              <h2>{{ record.sheet_name }}</h2>
            </div>
            <strong :class="['correction-badge', `correction-badge--${record.status}`]">{{ labels[record.status] }}</strong>
          </header>

          <dl class="record-meta">
            <div><dt>业务日期</dt><dd>{{ record.biz_date }}</dd></div>
            <div><dt>申请人</dt><dd>{{ record.applicant }}</dd></div>
            <div><dt>申请时间</dt><dd>{{ time(record.created_at) }}</dd></div>
            <div><dt>修正单元格</dt><dd><span class="cell-count-tag">{{ record.changes.length }} 个</span></dd></div>
          </dl>

          <div class="correction-reason">
            <span class="reason-label">修正原因</span>
            <div class="reason-text">{{ record.reason }}</div>
          </div>

          <div class="correction-table-scroll">
            <table class="correction-table">
              <colgroup>
                <col class="col-label">
                <col class="col-type">
                <col class="col-date">
                <col class="col-num">
                <col class="col-num">
              </colgroup>
              <thead>
                <tr>
                  <th>数据项 / 单位</th>
                  <th>列</th>
                  <th>实际数据日期</th>
                  <th class="numeric">原值</th>
                  <th class="numeric">申请修正值</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="cell in record.changes" :key="cell.cell_key">
                  <td>
                    <span class="cell-label-text">{{ cell.label }}</span>
                    <span v-if="cell.unit && !cell.label.includes(cell.unit)" class="cell-unit">计量单位：{{ cell.unit }}</span>
                  </td>
                  <td>
                    <span :class="['column-pill', { 'is-peer': cell.column && cell.column.includes('同期') }]">
                      {{ correctionColumn(cell.column) }}
                    </span>
                  </td>
                  <td class="cell-date-val">{{ cell.date }}</td>
                  <td class="numeric old-value">{{ correctionValue(cell.old_value) }}</td>
                  <td class="numeric">
                    <span class="new-value">{{ correctionValue(cell.new_value) }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="record.resolved_at" :class="['record-resolution', `record-resolution--${record.status}`]">
            <div class="resolution-head">
              <span class="resolution-dot"></span>
              <strong>{{ labels[record.status] }}</strong>
              <span class="resolution-operator">经办人：{{ record.resolved_by }} · {{ time(record.resolved_at) }}</span>
            </div>
            <div class="resolution-body">
              <span class="resolution-label">处理说明</span>
              <span class="resolution-text">{{ record.resolution_note || '无' }}</span>
            </div>
          </div>

          <div v-if="record.can_review || record.can_cancel" class="correction-actions record-actions">
            <button v-if="record.can_review" class="btn primary btn-approve" :disabled="busy" @click="open(record, 'approve')">确认修正</button>
            <button v-if="record.can_review" class="btn btn-reject" :disabled="busy" @click="open(record, 'reject')">驳回</button>
            <button v-if="record.can_cancel" class="btn ghost btn-cancel" :disabled="busy" @click="open(record, 'cancel')">取消申请</button>
          </div>
        </article>
      </div>

      <footer v-if="!loading && !error && total > 0" class="correction-pagination">
        <button class="btn ghost" :disabled="busy || offset === 0" @click="offset -= 50; load()">上一页</button>
        <span class="pagination-info">共 {{ total }} 条 · 第 {{ Math.floor(offset / 50) + 1 }} / {{ Math.ceil(total / 50) || 1 }} 页</span>
        <button class="btn ghost" :disabled="busy || offset + 50 >= total" @click="offset += 50; load()">下一页</button>
      </footer>
    </main>

    <div v-if="selection" class="correction-dialog-overlay" role="dialog" aria-modal="true" aria-labelledby="resolution-title">
      <section class="correction-dialog">
        <header class="dialog-header">
          <h2 id="resolution-title" :class="`dialog-title--${selection.action}`">
            {{ actionLabels[selection.action] }} #{{ selection.record.id }}
          </h2>
        </header>
        <div class="dialog-target">
          <div class="target-row"><span class="target-label">所属表格：</span><strong>{{ selection.record.sheet_name }}</strong></div>
          <div class="target-row"><span class="target-label">业务日期：</span><span>{{ selection.record.biz_date }}</span> · 共 {{ selection.record.changes.length }} 个单元格</div>
        </div>
        <p class="dialog-description">
          {{ selection.action === 'approve' ? '确认后将一次性写入这条申请的全部修正内容，并在业务备注中追加全过程审计信息。' : '关闭申请，原数据保持不变。' }}
        </p>
        <label class="correction-field">
          <span class="field-title">处理说明</span>
          <textarea v-model="note" maxlength="2000" rows="3" placeholder="请填写核实情况或处理意见（选填）…" />
        </label>
        <p v-if="resolutionError" class="correction-error" role="alert">{{ resolutionError }}</p>
        <div class="correction-actions dialog-actions">
          <button class="btn ghost" :disabled="resolving" @click="selection = null">返回</button>
          <button :class="['btn', selection.action === 'reject' ? 'btn-danger' : 'primary']" :disabled="resolving" @click="resolve">
            {{ resolving ? '处理中…' : actionLabels[selection.action] }}
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { dataCorrectionRequest } from '../services/api'
import { ensureProjectsLoaded, getProjectNameById } from '../composables/useProjects'
import { correctionBreadcrumbs, correctionColumn, correctionValue } from '../composables/dataCorrectionPresentation'

const projectName = computed(() => getProjectNameById('daily_report_25_26'))
const breadcrumbItems = computed(() => correctionBreadcrumbs(projectName.value))
const labels = { pending: '待审批', approved: '已确认', rejected: '已驳回', cancelled: '已取消' }
const actionLabels = { approve: '确认修正', reject: '驳回申请', cancel: '取消申请' }
const records = ref([]), status = ref(''), offset = ref(0), total = ref(0)
const loading = ref(true), resolving = ref(false), error = ref(''), message = ref('')
const selection = ref(null), note = ref(''), resolutionError = ref('')
const busy = computed(() => loading.value || resolving.value)
const time = value => String(value || '').replace('T', ' ').slice(0, 19)

async function load() {
  loading.value = true; error.value = ''; message.value = ''
  try {
    const result = await dataCorrectionRequest(`?${new URLSearchParams({ ...(status.value ? { status: status.value } : {}), offset: offset.value, limit: 50 })}`)
    // 状态筛选后结果减少或申请刚被处理时，回到最后一个有效分页。
    if (offset.value > 0 && offset.value >= result.total) {
      offset.value = Math.max(0, Math.floor((result.total - 1) / 50) * 50)
      return await load()
    }
    records.value = result.records; total.value = result.total
  } catch (e) { error.value = e.message } finally { loading.value = false }
}

function open(record, action) {
  if (busy.value) return
  selection.value = { record, action }; note.value = ''; resolutionError.value = ''
}

async function resolve() {
  if (resolving.value) return
  resolving.value = true; resolutionError.value = ''; message.value = ''
  try {
    await dataCorrectionRequest(`/${selection.value.record.id}/resolve`, { method: 'POST', body: { action: selection.value.action, note: note.value } })
    const action = selection.value.action
    selection.value = null; await load()
    if (!error.value) message.value = `${actionLabels[action]}完成。`
  } catch (e) { resolutionError.value = e.message } finally { resolving.value = false }
}

onMounted(() => {
  // 名称加载失败沿用项目名回退，不阻断记录读取。
  ensureProjectsLoaded().catch(() => {})
  load()
})
</script>

<style scoped>
.correction-page {
  min-height: 100vh;
  background: var(--bg, #f5f7fb);
  display: flex;
  flex-direction: column;
}

.correction-main {
  box-sizing: border-box;
  width: 100%;
  max-width: 1280px;
  min-width: 0;
  margin: 0 auto;
  padding: 20px 24px 36px;
  flex: 1;
}

/* 页面头部与工具栏 */
.correction-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
  flex-wrap: wrap;
  margin: 18px 0 24px;
}

.heading-copy {
  flex: 1 1 420px;
  min-width: 0;
}

.heading-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.heading-title-row h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.35;
  color: var(--text, #0f172a);
}

.heading-total-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  background: #e2e8f0;
  color: #475569;
  font-size: 12px;
  font-weight: 600;
}

.heading-copy p {
  margin: 8px 0 0;
  color: var(--muted, #64748b);
  font-size: 14px;
  line-height: 1.6;
}

.correction-filters {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--muted, #64748b);
}

.filter-item label {
  font-weight: 500;
}

.select-wrap select {
  box-sizing: border-box;
  height: 36px;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 8px;
  padding: 0 12px;
  background: white;
  font: inherit;
  font-size: 13px;
  color: var(--text, #0f172a);
  outline: none;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.select-wrap select:focus {
  border-color: var(--primary, #2563eb);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.btn-refresh {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.refresh-icon {
  font-size: 14px;
  line-height: 1;
}

.refresh-icon.is-spinning {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 提示通知条 */
.correction-notice {
  padding: 12px 18px;
  border-radius: 10px;
  line-height: 1.6;
  font-size: 14px;
  margin-bottom: 20px;
  overflow-wrap: anywhere;
  display: flex;
  align-items: center;
  gap: 8px;
}

.correction-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
}

.correction-success {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #15803d;
}

/* 空状态与加载中 */
.correction-empty {
  padding: 64px 20px;
  text-align: center;
  background: white;
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.empty-icon {
  font-size: 42px;
  margin-bottom: 12px;
  line-height: 1;
  opacity: 0.85;
}

.empty-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.empty-desc {
  margin: 8px auto 0;
  font-size: 13px;
  color: var(--muted, #64748b);
  max-width: 480px;
  line-height: 1.6;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e2e8f0;
  border-top-color: var(--primary, #2563eb);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 12px;
}

/* 记录列表 */
.correction-records {
  display: grid;
  gap: 20px;
  min-width: 0;
}

.correction-record {
  min-width: 0;
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 12px;
  background: white;
  padding: 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
}

.correction-record:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.record-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.record-title {
  min-width: 0;
}

.request-number {
  font-size: 12px;
  font-weight: 700;
  color: var(--primary-700, #1d4ed8);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  letter-spacing: 0.5px;
}

.record-title h2 {
  margin: 4px 0 0;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.45;
  color: #0f172a;
  overflow-wrap: anywhere;
}

/* 状态徽章 */
.correction-badge {
  flex-shrink: 0;
  border: 1px solid var(--border, #cbd5e1);
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 600;
  line-height: 20px;
  white-space: nowrap;
  background: #f8fafc;
  color: var(--muted, #64748b);
}

.correction-badge--pending {
  color: #1d4ed8;
  background: #eff6ff;
  border-color: #bfdbfe;
}

.correction-badge--approved {
  color: #15803d;
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.correction-badge--rejected {
  color: #b91c1c;
  background: #fef2f2;
  border-color: #fecaca;
}

.correction-badge--cancelled {
  color: #64748b;
  background: #f1f5f9;
  border-color: #cbd5e1;
}

/* 元信息卡片排布 */
.record-meta {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin: 18px 0;
  padding: 14px 18px;
  background: #f8fafc;
  border: 1px solid #eef2f6;
  border-radius: 10px;
}

.record-meta > div {
  min-width: 0;
}

.record-meta dt {
  color: var(--muted, #64748b);
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 4px;
}

.record-meta dd {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  overflow-wrap: anywhere;
  font-variant-numeric: tabular-nums;
}

.cell-count-tag {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 999px;
  background: #e0f2fe;
  color: #0369a1;
  font-size: 12px;
  font-weight: 600;
}

/* 修正原因 */
.correction-reason {
  margin: 16px 0;
  padding: 12px 16px;
  background: #f0f7ff;
  border-left: 3px solid #3b82f6;
  border-radius: 0 8px 8px 0;
}

.reason-label {
  display: block;
  margin-bottom: 4px;
  color: #1e40af;
  font-size: 12px;
  font-weight: 600;
}

.reason-text {
  font-size: 14px;
  line-height: 1.7;
  color: #1e293b;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

/* 修正明细表 */
.correction-table-scroll {
  max-width: 100%;
  overflow-x: auto;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 8px;
  background: white;
}

.correction-table {
  border-collapse: collapse;
  width: 100%;
  min-width: 680px;
  table-layout: fixed;
  text-align: left;
  font-size: 13px;
}

.col-label { width: 34%; }
.col-type { width: 14%; }
.col-date { width: 16%; }
.col-num { width: 18%; }

.correction-table th,
.correction-table td {
  padding: 12px 14px;
  border-bottom: 1px solid #eef2f6;
  line-height: 1.6;
  vertical-align: top;
  overflow-wrap: anywhere;
}

.correction-table th {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
  font-size: 12px;
  letter-spacing: 0.3px;
}

.correction-table tbody tr:last-child td {
  border-bottom: 0;
}

.cell-label-text {
  font-weight: 500;
  color: #1e293b;
}

.cell-unit {
  display: block;
  color: var(--muted, #64748b);
  font-size: 12px;
  margin-top: 3px;
}

.column-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  background: #f1f5f9;
  color: #475569;
}

.column-pill.is-peer {
  background: #fdf4ff;
  color: #9333ea;
  border: 1px solid #f0abfc;
}

.cell-date-val {
  color: #475569;
  font-variant-numeric: tabular-nums;
  font-size: 13px;
}

.correction-table .numeric {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.old-value {
  color: var(--muted, #64748b);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.new-value {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 6px;
  font-weight: 700;
  color: #1d4ed8;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

/* 审批结果 */
.record-resolution {
  padding: 14px 18px;
  margin-top: 18px;
  border-radius: 10px;
  font-size: 13px;
  overflow-wrap: anywhere;
}

.record-resolution--approved {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
}

.record-resolution--rejected {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
}

.record-resolution--cancelled {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  color: #475569;
}

.resolution-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.resolution-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}

.resolution-operator {
  margin-left: 4px;
  opacity: 0.85;
  font-size: 12px;
}

.resolution-body {
  margin-top: 8px;
  line-height: 1.7;
}

.resolution-label {
  display: inline-block;
  font-weight: 600;
  margin-right: 6px;
  opacity: 0.9;
}

.resolution-text {
  color: inherit;
}

/* 操作按钮区 */
.correction-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.record-actions {
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px solid #f1f5f9;
}

.btn-reject {
  background: white;
  border: 1px solid #fca5a5;
  color: #dc2626;
  cursor: pointer;
}

.btn-reject:hover {
  background: #fef2f2;
  border-color: #f87171;
}

.btn-danger {
  background: #dc2626;
  border-color: #dc2626;
  color: white;
  cursor: pointer;
}

.btn-danger:hover {
  background: #b91c1c;
  border-color: #b91c1c;
}

/* 分页栏 */
.correction-pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 28px;
}

.pagination-info {
  background: white;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 8px;
  padding: 6px 14px;
  font-size: 13px;
  color: var(--muted, #64748b);
  font-variant-numeric: tabular-nums;
}

/* 弹窗层 */
.correction-dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  box-sizing: border-box;
  padding: 20px;
  overflow-y: auto;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(3px);
  display: grid;
  place-items: center;
}

.correction-dialog {
  box-sizing: border-box;
  background: white;
  border-radius: 16px;
  padding: 26px;
  width: min(560px, 100%);
  max-height: calc(100dvh - 40px);
  overflow-y: auto;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.15), 0 10px 10px -5px rgba(0, 0, 0, 0.08);
}

.dialog-header h2 {
  margin: 0;
  font-size: 20px;
  line-height: 1.45;
  color: #0f172a;
}

.dialog-title--approve { color: #1d4ed8; }
.dialog-title--reject { color: #dc2626; }
.dialog-title--cancel { color: #475569; }

.dialog-target {
  padding: 12px 16px;
  margin: 16px 0;
  background: #f8fafc;
  border: 1px solid #eef2f6;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.8;
  overflow-wrap: anywhere;
}

.target-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.target-label {
  color: var(--muted, #64748b);
  font-size: 13px;
}

.dialog-description {
  color: var(--muted, #64748b);
  font-size: 14px;
  line-height: 1.7;
  margin: 14px 0;
}

.correction-field {
  display: block;
  margin-top: 16px;
}

.field-title {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #334155;
  margin-bottom: 6px;
}

.correction-field textarea {
  display: block;
  width: 100%;
  min-height: 100px;
  box-sizing: border-box;
  padding: 12px;
  border: 1px solid var(--border, #cbd5e1);
  border-radius: 8px;
  font: inherit;
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.correction-field textarea:focus {
  border-color: var(--primary, #2563eb);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.dialog-actions {
  justify-content: flex-end;
  margin-top: 22px;
}

/* 响应式断点适配 */
@media (max-width: 640px) {
  .correction-main { padding: 16px 12px 28px; }
  .correction-heading { margin: 12px 0 18px; gap: 14px; }
  .heading-copy { flex-basis: 100%; }
  .heading-copy h1 { font-size: 21px; }
  .correction-filters { width: 100%; justify-content: space-between; }
  .filter-item { flex: 1; }
  .select-wrap select { width: 100%; }
  .correction-record { padding: 16px; }
  .record-meta { grid-template-columns: repeat(2, minmax(0, 1fr)); padding: 12px; gap: 12px; }
  .record-title h2 { font-size: 16px; }
  .record-actions { justify-content: stretch; }
  .record-actions .btn { flex: 1; text-align: center; }
  .correction-dialog-overlay { padding: 12px; }
  .correction-dialog { padding: 20px; max-height: calc(100dvh - 24px); }
}
</style>
