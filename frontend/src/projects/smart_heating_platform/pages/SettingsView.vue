<template>
  <div class="shp-settings-view">
    <AppHeader />
    <main class="shp-main container">
      <Breadcrumbs :items="breadcrumbItems" />

      <header class="topbar card elevated">
        <div class="topbar-info">
          <div class="title-row">
            <h2>采集与计算选项</h2>
            <span class="role-badge">仅限 Global_admin</span>
          </div>
          <p class="subtitle">
            配置《智慧供热管理平台 v2.0》旁路采集源站地址、Session Cookie 凭据及并发保护参数，支持在线验证与随时修改。
          </p>
        </div>
        <div class="topbar-actions">
          <button class="btn secondary" type="button" @click="goBackPages">
            ⬅️ 返回功能页
          </button>
          <button class="btn secondary" type="button" :disabled="loading || testing" @click="loadSettings">
            {{ loading ? '加载中…' : '🔄 刷新状态' }}
          </button>
        </div>
      </header>

      <div v-if="notice.text" :class="['notice-banner', notice.type]">
        {{ notice.text }}
      </div>

      <!-- 运行状态摘要卡片 -->
      <section class="status-grid">
        <div class="card elevated stat-card">
          <span class="stat-label">当前生效源站</span>
          <strong class="stat-value mono">{{ settings.effective_base_url || 'http://124.93.31.19:6688' }}</strong>
          <span class="stat-sub">模式：{{ modeLabel(settings.source_mode) }}</span>
        </div>
        <div class="card elevated stat-card">
          <span class="stat-label">Session Cookie 状态</span>
          <strong :class="['stat-value', settings.has_cookie ? 'text-ok' : 'text-warn']">
            {{ settings.has_cookie ? '已配置' : '未配置' }}
          </strong>
          <span class="stat-sub mono">
            {{ settings.has_cookie ? `${settings.cookie_masked}（${settings.cookie_length} 字符）` : '仅免 Cookie 接口可用，居民室温/商户需配置' }}
          </span>
        </div>
        <div class="card elevated stat-card">
          <span class="stat-label">最近连通性检测</span>
          <strong :class="['stat-value', testSummaryClass]">
            {{ testSummaryText }}
          </strong>
          <span class="stat-sub">
            {{ settings.last_test_result?.tested_at ? `检测时间：${settings.last_test_result.tested_at}` : '尚未执行连通性测试' }}
          </span>
        </div>
        <div class="card elevated stat-card">
          <span class="stat-label">最后修改记录</span>
          <strong class="stat-value">{{ settings.updated_at || '尚未保存修改' }}</strong>
          <span class="stat-sub">{{ settings.updated_by ? `操作人：${settings.updated_by}` : '使用默认出厂参数' }}</span>
        </div>
      </section>

      <!-- 主表单区 -->
      <form class="settings-form-grid" @submit.prevent="handleSave">
        <!-- Cookie 设置卡片 -->
        <section class="card elevated form-card">
          <div class="card-header-row">
            <div>
              <h3>1. 源站 Session Cookie 凭据</h3>
              <p class="card-desc">
                用于采集需登录接口：<code>/jumin/</code>（2,097 户居民室温）与 <code>/getall_bb_shrb/</code>（464 户商业用户日耗量）。
              </p>
            </div>
            <button
              v-if="settings.has_cookie"
              class="btn danger-outline btn-sm"
              type="button"
              :disabled="saving || testing"
              @click="handleClearCookie"
            >
              🗑️ 清空已存 Cookie
            </button>
          </div>

          <div v-if="settings.has_cookie" class="saved-cookie-box">
            <span class="saved-label">当前已保存（脱敏展示）：</span>
            <code class="saved-mask">{{ settings.cookie_masked }}</code>
          </div>

          <div class="field-group">
            <label for="cookie-input">
              {{ settings.has_cookie ? '输入新 Cookie 以替换（留空则保留当前已保存的 Cookie）' : '粘贴源站 Cookie' }}
            </label>
            <textarea
              id="cookie-input"
              v-model="form.cookieInput"
              rows="4"
              class="cookie-textarea mono"
              placeholder="请粘贴浏览器开发者工具中的 Cookie 值，支持 session=.eJx... 或直接粘贴 .eJx...（系统将自动补全前缀）"
              autocomplete="off"
              spellcheck="false"
            />
            <p class="field-hint">
              安全提示：Cookie 仅保存在服务端受保护的数据目录中，页面刷新后默认以脱敏形式展示，不在响应中回传明文。
            </p>
          </div>
        </section>

        <!-- 源站地址与保护参数卡片 -->
        <section class="card elevated form-card">
          <div class="card-header-row">
            <div>
              <h3>2. 源站接入与受控并发参数</h3>
              <p class="card-desc">
                支持受控多线程并发拉取（默认 4 并发）与失败退避重试，同时保留探测间隔保护避免压垮源站容器。
              </p>
            </div>
          </div>

          <div class="field-group">
            <label>源站接入模式</label>
            <div class="radio-row">
              <label class="radio-option">
                <input v-model="form.source_mode" type="radio" value="public" />
                <span>公网直连（<code>{{ settings.public_preset_url }}</code>）</span>
              </label>
              <label class="radio-option">
                <input v-model="form.source_mode" type="radio" value="intranet" />
                <span>内网直连（<code>{{ settings.intranet_preset_url }}</code>）</span>
              </label>
              <label class="radio-option">
                <input v-model="form.source_mode" type="radio" value="custom" />
                <span>自定义地址</span>
              </label>
            </div>
          </div>

          <div v-if="form.source_mode === 'custom'" class="field-group">
            <label for="custom-url-input">自定义源站基地址</label>
            <input
              id="custom-url-input"
              v-model="form.custom_base_url"
              type="url"
              class="text-input mono"
              placeholder="例如 http://124.93.31.19:6688"
            />
          </div>

          <div class="numeric-fields">
            <div class="field-group">
              <label for="workers-input">并行采集线程数（1~16）</label>
              <input
                id="workers-input"
                v-model.number="form.max_workers"
                type="number"
                min="1"
                max="16"
                step="1"
                class="text-input"
              />
            </div>

            <div class="field-group">
              <label for="interval-input">探测/退避间隔（秒，0.5~5.0）</label>
              <input
                id="interval-input"
                v-model.number="form.request_interval_seconds"
                type="number"
                min="0.5"
                max="5.0"
                step="0.1"
                class="text-input"
              />
            </div>

            <div class="field-group">
              <label for="timeout-input">单次请求超时（秒，3~60）</label>
              <input
                id="timeout-input"
                v-model.number="form.request_timeout_seconds"
                type="number"
                min="3"
                max="60"
                step="1"
                class="text-input"
              />
            </div>

            <div class="field-group">
              <label for="snap-interval-select">上游/商户采样间隔（分钟）</label>
              <select id="snap-interval-select" v-model.number="form.snapshot_interval_minutes" class="text-input">
                <option :value="5">每 5 分钟（推荐 · 高频积分 + 2h算完即清）</option>
                <option :value="15">每 15 分钟</option>
                <option :value="30">每 30 分钟</option>
                <option :value="60">每 60 分钟（仅整点）</option>
              </select>
            </div>

            <div class="field-group">
              <label for="offset-input">整点延迟偏移（分钟，0~59）</label>
              <input
                id="offset-input"
                v-model.number="form.hourly_offset_minutes"
                type="number"
                min="0"
                max="59"
                step="1"
                class="text-input"
              />
            </div>

            <div class="field-group">
              <label for="sync-hours-input">换热站表底校准周期（小时，1~24，默认每小时 :05）</label>
              <input
                id="sync-hours-input"
                v-model.number="form.table_bottom_sync_hours"
                type="number"
                min="1"
                max="24"
                step="1"
                class="text-input"
              />
            </div>

            <div class="field-group">
              <label for="gap-start-date-input">停机真空期检查起始日期（默认 2026-11-01 至今）</label>
              <input
                id="gap-start-date-input"
                v-model="form.gap_recovery_start_date"
                type="date"
                class="text-input"
              />
            </div>

            <div class="field-group">
              <label for="heat-audit-time-input">每日热量异常回看检测与修正时刻（默认 00:00）</label>
              <input
                id="heat-audit-time-input"
                v-model="form.heat_audit_time"
                type="time"
                class="text-input"
              />
            </div>

            <div class="field-group">
              <label for="heat-audit-days-input">每次定时回看检测天数（1~30，默认近 3 天）</label>
              <input
                id="heat-audit-days-input"
                v-model.number="form.heat_audit_lookback_days"
                type="number"
                min="1"
                max="30"
                step="1"
                class="text-input"
              />
            </div>
          </div>

          <div class="field-group switch-row">
            <label class="checkbox-label">
              <input v-model="form.scheduler_enabled" type="checkbox" />
              <span>允许自动定时采集任务运行（后续时序表与采集调度器启用后生效）</span>
            </label>
          </div>

          <div class="field-group switch-row">
            <label class="checkbox-label">
              <input v-model="form.auto_gap_recovery" type="checkbox" />
              <span>启用停机真空期自动检测与补采（服务重启 10 秒后及每小时 :15 自动检测缺失整点并补全）</span>
            </label>
          </div>

          <div class="field-group switch-row">
            <label class="checkbox-label">
              <input v-model="form.auto_heat_audit_fix" type="checkbox" />
              <span>启用每日定时数据异常回看检测与自动修正（在设定时刻回看越限热量并写入异常监测台账）</span>
            </label>
          </div>

          <div class="form-actions">
            <button class="btn secondary" type="button" :disabled="testing || saving" @click="handleTest">
              {{ testing ? '探测中（串行保护）…' : '🧪 测试连通性与 Cookie' }}
            </button>
            <button class="btn primary" type="submit" :disabled="saving || testing">
              {{ saving ? '保存中…' : '💾 保存设置' }}
            </button>
          </div>
        </section>
      </form>

      <!-- 测试结果明细 -->
      <section v-if="testResult" class="card elevated result-card">
        <div class="card-header-row">
          <div>
            <h3>3. 接口连通性与 Cookie 有效性测试结果</h3>
            <p class="card-desc">
              目标地址：<code class="mono">{{ testResult.base_url }}</code> · 检测时间：{{ testResult.tested_at }}
            </p>
          </div>
        </div>
        <div class="table-wrap">
          <table class="probe-table">
            <thead>
              <tr>
                <th>探测接口</th>
                <th>结果</th>
                <th>HTTP 状态</th>
                <th>耗时</th>
                <th>返回条数</th>
                <th>明细说明</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in testResult.checks" :key="item.name">
                <td class="mono">{{ item.name }}</td>
                <td>
                  <span :class="['status-pill', item.ok ? 'pill-ok' : 'pill-err']">
                    {{ item.ok ? '可用' : '异常' }}
                  </span>
                </td>
                <td class="mono">{{ item.status_code ?? '-' }}</td>
                <td class="mono">{{ item.elapsed_ms }} ms</td>
                <td class="mono">{{ item.count }}</td>
                <td>{{ item.detail }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import '../../daily_report_25_26/styles/theme.css'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  fetchCollectorSettings,
  saveCollectorSettings,
  testCollectorSettings,
} from '../services/api'

const router = useRouter()

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const notice = reactive({ type: 'info', text: '' })

const settings = ref({
  source_mode: 'public',
  custom_base_url: '',
  effective_base_url: 'http://124.93.31.19:6688',
  public_preset_url: 'http://124.93.31.19:6688',
  intranet_preset_url: 'http://192.168.1.206:6688',
  has_cookie: false,
  cookie_masked: '',
  cookie_length: 0,
  scheduler_enabled: false,
  snapshot_interval_minutes: 5,
  hourly_offset_minutes: 0,
  max_workers: 4,
  request_interval_seconds: 0.8,
  request_timeout_seconds: 15,
  table_bottom_sync_hours: 1,
  updated_at: '',
  updated_by: '',
  last_test_result: null,
})

const form = reactive({
  source_mode: 'public',
  custom_base_url: '',
  cookieInput: '',
  scheduler_enabled: false,
  snapshot_interval_minutes: 5,
  hourly_offset_minutes: 0,
  max_workers: 4,
  request_interval_seconds: 0.8,
  request_timeout_seconds: 15,
  table_bottom_sync_hours: 1,
  auto_gap_recovery: true,
  gap_recovery_start_date: '2026-11-01',
  auto_heat_audit_fix: true,
  heat_audit_time: '00:00',
  heat_audit_lookback_days: 3,
})

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '智慧供热平台精算模块', to: '/projects/smart_heating_platform/pages' },
  { label: '采集与计算选项', to: null },
])

const testResult = computed(() => settings.value.last_test_result || null)

const testSummaryText = computed(() => {
  const res = testResult.value
  if (!res) return '未测试'
  if (res.public_ok && res.cookie_ok) return '全链路正常'
  if (res.public_ok && res.cookie_status === 'missing') return '免Cookie接口正常（缺Cookie）'
  if (res.public_ok && !res.cookie_ok) return '免Cookie正常 · Cookie已失效'
  return '源站连接异常'
})

const testSummaryClass = computed(() => {
  const res = testResult.value
  if (!res) return ''
  if (res.public_ok && res.cookie_ok) return 'text-ok'
  if (res.public_ok) return 'text-warn'
  return 'text-err'
})

function modeLabel(mode) {
  if (mode === 'intranet') return '内网直连'
  if (mode === 'custom') return '自定义地址'
  return '公网直连'
}

function applySettingsToForm(data) {
  settings.value = data
  form.source_mode = data.source_mode || 'public'
  form.custom_base_url = data.custom_base_url || ''
  form.scheduler_enabled = Boolean(data.scheduler_enabled)
  form.snapshot_interval_minutes = Number(data.snapshot_interval_minutes ?? 5)
  form.hourly_offset_minutes = Number(data.hourly_offset_minutes ?? 0)
  form.max_workers = Number(data.max_workers ?? 4)
  form.request_interval_seconds = Number(data.request_interval_seconds ?? 0.8)
  form.request_timeout_seconds = Number(data.request_timeout_seconds ?? 15)
  form.table_bottom_sync_hours = Number(data.table_bottom_sync_hours ?? 1)
  form.auto_gap_recovery = data.auto_gap_recovery !== false
  form.gap_recovery_start_date = String(data.gap_recovery_start_date || '2026-11-01')
  form.auto_heat_audit_fix = data.auto_heat_audit_fix !== false
  form.heat_audit_time = String(data.heat_audit_time || '00:00')
  form.heat_audit_lookback_days = Number(data.heat_audit_lookback_days ?? 3)
}

function setNotice(type, text) {
  notice.type = type
  notice.text = text
}

async function loadSettings() {
  loading.value = true
  try {
    const res = await fetchCollectorSettings()
    if (res?.data) {
      applySettingsToForm(res.data)
    }
  } catch (err) {
    setNotice('error', `读取采集配置失败：${err.message}`)
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  setNotice('info', '')
  try {
    const payload = {
      source_mode: form.source_mode,
      custom_base_url: form.custom_base_url,
      scheduler_enabled: form.scheduler_enabled,
      snapshot_interval_minutes: form.snapshot_interval_minutes,
      hourly_offset_minutes: form.hourly_offset_minutes,
      max_workers: form.max_workers,
      request_interval_seconds: form.request_interval_seconds,
      request_timeout_seconds: form.request_timeout_seconds,
      table_bottom_sync_hours: form.table_bottom_sync_hours,
      auto_gap_recovery: form.auto_gap_recovery,
      gap_recovery_start_date: form.gap_recovery_start_date,
      auto_heat_audit_fix: form.auto_heat_audit_fix,
      heat_audit_time: form.heat_audit_time,
      heat_audit_lookback_days: form.heat_audit_lookback_days,
    }
    const trimmedCookie = form.cookieInput.trim()
    if (trimmedCookie) {
      payload.cookie = trimmedCookie
    }
    const res = await saveCollectorSettings(payload)
    if (res?.data) {
      applySettingsToForm(res.data)
    }
    form.cookieInput = ''
    setNotice('success', trimmedCookie ? '采集设置与新 Cookie 已安全保存。' : '采集设置已保存（原 Cookie 保持不变）。')
  } catch (err) {
    setNotice('error', `保存失败：${err.message}`)
  } finally {
    saving.value = false
  }
}

async function handleClearCookie() {
  if (typeof window !== 'undefined' && !window.confirm('确认清空当前已保存的源站 Cookie 吗？清空后居民室温与商户日报将暂停采集。')) {
    return
  }
  saving.value = true
  setNotice('info', '')
  try {
    const res = await saveCollectorSettings({ clear_cookie: true })
    if (res?.data) {
      applySettingsToForm(res.data)
    }
    form.cookieInput = ''
    setNotice('success', '已清空保存的 Cookie。')
  } catch (err) {
    setNotice('error', `清空 Cookie 失败：${err.message}`)
  } finally {
    saving.value = false
  }
}

async function handleTest() {
  testing.value = true
  setNotice('info', '正在按单线程间隔安全探测源站接口与 Cookie 状态，请稍候…')
  try {
    const payload = {
      source_mode: form.source_mode,
      custom_base_url: form.custom_base_url,
    }
    if (form.cookieInput.trim()) {
      payload.cookie = form.cookieInput.trim()
    }
    const res = await testCollectorSettings(payload)
    if (res?.data) {
      settings.value = {
        ...settings.value,
        last_test_result: res.data,
      }
      if (res.data.public_ok && res.data.cookie_ok) {
        setNotice('success', '测试通过：免 Cookie 接口与 Cookie 会话接口均返回正常！')
      } else if (res.data.public_ok && res.data.cookie_status === 'missing') {
        setNotice('warn', '免 Cookie 接口连通正常，但尚未提供 Cookie（居民室温与商户接口未测）。')
      } else if (res.data.public_ok && !res.data.cookie_ok) {
        setNotice('error', '免 Cookie 接口正常，但当前 Cookie 已失效或无权访问需登录接口，请重新获取并保存。')
      } else {
        setNotice('error', '源站接口连接存在异常，请查看下方逐项测试明细。')
      }
    }
  } catch (err) {
    setNotice('error', `连通性测试失败：${err.message}`)
  } finally {
    testing.value = false
  }
}

function goBackPages() {
  router.push('/projects/smart_heating_platform/pages')
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.shp-main {
  padding: 20px 16px 40px;
  max-width: 1180px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  padding: 18px 22px;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.title-row h2 {
  margin: 0;
  font-size: 20px;
}

.role-badge {
  font-size: 12px;
  font-weight: 600;
  color: #b91c1c;
  background: #fee2e2;
  border: 1px solid #fecaca;
  padding: 2px 10px;
  border-radius: 999px;
}

.subtitle {
  margin: 6px 0 0;
  color: #475569;
  font-size: 13px;
}

.topbar-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.notice-banner {
  padding: 12px 16px;
  border-radius: 10px;
  font-size: 14px;
  border: 1px solid transparent;
}

.notice-banner.success {
  background: #ecfdf5;
  color: #065f46;
  border-color: #a7f3d0;
}

.notice-banner.warn {
  background: #fffbeb;
  color: #92400e;
  border-color: #fde68a;
}

.notice-banner.error {
  background: #fef2f2;
  color: #991b1b;
  border-color: #fecaca;
}

.notice-banner.info {
  background: #eff6ff;
  color: #1e40af;
  border-color: #bfdbfe;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 14px;
}

.stat-card {
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stat-label {
  font-size: 12px;
  color: #64748b;
}

.stat-value {
  font-size: 16px;
  color: #0f172a;
  word-break: break-all;
}

.stat-sub {
  font-size: 12px;
  color: #64748b;
  word-break: break-all;
}

.text-ok {
  color: #059669;
}

.text-warn {
  color: #d97706;
}

.text-err {
  color: #dc2626;
}

.settings-form-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-card,
.result-card {
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

.card-header-row h3 {
  margin: 0;
  font-size: 16px;
  color: #0f172a;
}

.card-desc {
  margin: 4px 0 0;
  font-size: 13px;
  color: #64748b;
}

.saved-cookie-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 13px;
}

.saved-label {
  color: #475569;
  font-weight: 500;
}

.saved-mask {
  color: #0f172a;
  word-break: break-all;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-group label {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

.cookie-textarea,
.text-input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 13px;
  color: #0f172a;
  background: #ffffff;
}

.cookie-textarea:focus,
.text-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.field-hint {
  margin: 0;
  font-size: 12px;
  color: #64748b;
}

.radio-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.radio-option {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 400;
  color: #1e293b;
  cursor: pointer;
}

.numeric-fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 14px;
}

.switch-row {
  padding-top: 4px;
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #334155;
  cursor: pointer;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
  padding-top: 6px;
}

.table-wrap {
  overflow-x: auto;
}

.probe-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.probe-table th,
.probe-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
}

.probe-table th {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
}

.status-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.pill-ok {
  background: #dcfce7;
  color: #166534;
}

.pill-err {
  background: #fee2e2;
  color: #991b1b;
}

.danger-outline {
  background: #fff;
  color: #dc2626;
  border: 1px solid #fca5a5;
}

.danger-outline:hover:not(:disabled) {
  background: #fef2f2;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

@media (max-width: 768px) {
  .shp-main {
    padding: 12px 10px 28px;
    gap: 10px;
  }
  .topbar,
  .form-card,
  .result-card {
    padding: 14px 12px;
  }
  .title-row h2 {
    font-size: 17px;
  }
  .topbar-actions {
    width: 100%;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
  .topbar-actions > .btn {
    width: 100%;
    justify-content: center;
  }
  .status-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }
  .stat-card {
    padding: 12px;
  }
  .numeric-fields {
    grid-template-columns: 1fr;
  }
  .form-actions {
    flex-direction: column;
  }
  .form-actions > .btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
