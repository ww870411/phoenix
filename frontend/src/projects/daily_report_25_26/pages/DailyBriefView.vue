<template>
  <div class="brief-page">
    <main class="brief-main">
      <nav class="brief-nav"><RouterLink to="/projects/daily_report_25_26/pages">‹ 返回功能页面</RouterLink><span>管理员专属</span></nav>
      <header class="brief-header">
        <p class="eyebrow">经营 · 生产 / 每日速览</p>
        <h1>每日简报<span class="title-dot"></span></h1>
        <div class="date-bar">
          <label for="brief-date">业务日期</label>
          <select id="brief-date" :value="selectedDate" :disabled="loading || !dates.length" @change="selectDate($event.target.value)">
            <option v-if="!dates.length" value="">{{ loading ? '读取日期…' : '暂无数据日期' }}</option>
            <option v-for="day in dates" :key="day" :value="day">{{ day }}{{ day === latest ? ' · 最新发布' : '' }}</option>
          </select>
          <button type="button" :disabled="loading" @click="load()">{{ loading ? '读取中…' : '刷新' }}</button>
        </div>
      </header>

      <div v-if="loading" class="state" role="status">正在整理日报…</div>
      <div v-else-if="error" class="state error" role="alert"><p>{{ error }}</p><button type="button" @click="recover">重试</button></div>
      <div v-else-if="!brief?.date" class="state">{{ brief?.message || '暂无可展示的简报。' }}</div>
      <template v-else>
        <div class="publication-note">{{ brief.date }} · 同期 {{ brief.peer_date }}</div>
        <section class="digest" aria-labelledby="digest-title">
          <div class="section-heading"><span class="section-no">01</span><h2 id="digest-title">今日摘要</h2></div>
          <p class="weather-note"><BriefComparisonText :text="brief.weather.summary" /></p>
          <div v-for="(item, index) in brief.highlights" :key="item.key" class="digest-item">
            <span class="digest-index">{{ String(index + 1).padStart(2, '0') }}</span>
            <div><p><BriefComparisonText :text="item.text" /></p><p v-if="item.detail" class="digest-detail"><BriefComparisonText :text="item.detail" /></p></div>
          </div>
        </section>

        <section aria-labelledby="group-title">
          <div class="section-heading"><span class="section-no">02</span><h2 id="group-title">集团总览</h2></div>
          <BriefSubjectSection :key="`${brief.date}-Group`" :subject="brief.group" />
        </section>

        <section class="plan-section" aria-labelledby="plan-title">
          <div class="section-heading"><span class="section-no">03</span><h2 id="plan-title">标煤计划对照</h2></div>
          <template v-if="brief.plan.monthly">
            <div v-if="groupPlan" class="plan-facts">
              <div><span>集团全月静态计划</span><strong>{{ fmt(groupPlan.plan_value) }} <small>吨</small></strong></div>
              <div><span>月初至 {{ brief.date.slice(5) }} 已报实际</span><strong>{{ fmt(groupPlan.actual_value) }} <small>吨</small></strong></div>
              <div><span>累计实际 / 全月计划</span><strong>{{ fmt(groupPlan.completion_percent, 1) }} <small>%</small></strong></div>
            </div>
            <p v-if="brief.plan.daily?.plan_value != null">集团动态日计划：{{ fmt(brief.plan.daily.plan_value) }} 吨；当日实际与日计划差额 <BriefComparisonText :text="`${signed(dailyPlanDelta)} 吨`" :delta="dailyPlanDelta" />。</p>
            <details class="plan-units"><summary>各口径月计划与已报实际</summary>
              <div v-for="row in brief.plan.monthly.items" :key="row.company" class="plan-unit">
                <h3>{{ row.company_cn }}</h3><p>全月计划 {{ fmt(row.plan_value) }} 吨 · 已报实际 {{ fmt(row.actual_value) }} 吨</p>
                <p class="muted">实际 / 全月计划 {{ fmt(row.completion_percent, 1) }}%</p>
              </div>
            </details>
          </template>
          <p v-else>{{ brief.plan.summary || '计划数据暂不可用。' }}</p>
        </section>

        <section aria-labelledby="extra-title">
          <div class="section-heading"><span class="section-no">04</span><h2 id="extra-title">现货 · 调度 · 库存</h2></div>
          <article v-for="block in brief.supplements" :key="`${brief.date}-${block.title}`" class="supplement">
            <div class="supplement-heading"><h3>{{ block.title }}</h3><span v-if="statusLabel(block.status)">{{ statusLabel(block.status) }}</span></div>
            <p v-if="block.summary">{{ block.summary }}</p>
            <ul v-if="block.facts?.length"><li v-for="(fact, index) in block.facts" :key="index"><BriefComparisonText :text="fact" /></li></ul>
            <RouterLink :to="blockLink(block.title)">打开{{ block.title }}查询页 ›</RouterLink>
          </article>
        </section>

        <footer class="brief-footer">大连洁净能源集团 · 日报简报<br>整理时间 {{ generatedTime }}</footer>
      </template>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchDailyBrief } from '../services/api'
import BriefSubjectSection from '../components/BriefSubjectSection.vue'
import BriefComparisonText from '../components/BriefComparisonText.vue'
import { formatBriefNumber as fmt } from '../composables/dailyBriefPresentation'

const route = useRoute(), router = useRouter()
const brief = ref(null), loading = ref(false), error = ref('')
const dates = ref([]), latest = ref('')
const selectedDate = computed(() => brief.value?.date || String(route.query.date || ''))
const groupPlan = computed(() => brief.value?.plan?.monthly?.items?.find(row => row.company === 'Group'))
const dailyPlanDelta = computed(() => {
  const value = brief.value?.group?.metrics.find(m => m.key === 'consumption_std_coal')?.value
  const plan = brief.value?.plan?.daily?.plan_value
  return value != null && plan != null ? value - plan : null
})
const generatedTime = computed(() => {
  const value = brief.value?.generated_at
  return value ? new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false }) : '—'
})
let controller, requestId = 0
async function load() {
  controller?.abort()
  controller = new AbortController()
  const id = ++requestId
  loading.value = true
  error.value = ''
  try {
    const result = await fetchDailyBrief(String(route.query.date || ''), { signal: controller.signal })
    if (id !== requestId) return
    brief.value = result
    dates.value = result.available_dates || result.published_dates || []
    latest.value = result.latest_published_date || ''
  } catch (cause) {
    if (id === requestId && cause.name !== 'AbortError') error.value = cause.message || '读取失败，请稍后重试。'
  } finally {
    if (id === requestId) loading.value = false
  }
}
function selectDate(value) { router.replace({ query: { ...route.query, date: value } }) }
function recover() {
  if (route.query.date) {
    const query = { ...route.query }
    delete query.date
    router.replace({ query })
  } else load()
}
function signed(value) { return value == null ? '—' : `${value > 0 ? '+' : ''}${fmt(value)}` }
function statusLabel(status) { return ({ partial: '部分记录', missing: '暂无记录', unavailable: '暂不可用' })[status] || '' }
function blockLink(title) {
  const base = '/projects/daily_report_25_26/pages'
  if (title === '电力现货') return `${base}/spot_electricity`
  if (title === '生产调度') return `${base}/dispatch_info`
  return `${base}/dashboard/dashboard`
}
watch(() => route.query.date, load, { immediate: true })
onBeforeUnmount(() => { ++requestId; controller?.abort() })
</script>

<style scoped>
.brief-page { min-height: 100vh; background: #f3f5f6; color: #233d4a; font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif; overflow-wrap: anywhere; }
.brief-page *, .brief-page *::before, .brief-page *::after { box-sizing: border-box; }
.brief-main { width: 100%; max-width: 820px; padding: 10px 20px 24px; margin: 0 auto; }
.brief-nav { display: flex; justify-content: space-between; align-items: center; gap: 12px; font-size: 12px; }
a { color: #275e70; text-decoration: none; }
.brief-nav a { display: inline-flex; min-height: 44px; align-items: center; }
.brief-nav > span { color: #84919a; }
.brief-header { padding: 10px 0 12px; }
.eyebrow { letter-spacing: 2px; color: #71808a; font-size: 11px; margin: 0 0 6px; }
h1 { margin: 0; font-size: 30px; font-weight: 650; letter-spacing: 2px; color: #153b4b; }
.title-dot { display: inline-block; height: 8px; width: 8px; margin: 0 0 5px 10px; border-radius: 50%; background: #bd8b51; }
.date-bar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 12px; }
.date-bar label { color: #657580; font-size: 12px; }
select, button { min-height: 44px; border: 1px solid #d8e0e4; border-radius: 9px; background: #fff; color: #2c4d5b; font: inherit; font-size: 13px; padding: 0 12px; max-width: 100%; }
select { min-width: 0; flex: 1; }
button { cursor: pointer; }
button:disabled, select:disabled { opacity: .6; cursor: wait; }
a:focus-visible, button:focus-visible, select:focus-visible, summary:focus-visible { outline: 2px solid #24697f; outline-offset: 3px; }
.publication-note { border-left: 2px solid #bd986a; padding-left: 10px; margin: 0 0 14px; line-height: 1.7; font-size: 11px; color: #798791; }
section { margin-bottom: 18px; min-width: 0; }
.section-heading { display: flex; align-items: center; gap: 8px; margin: 0 0 10px; flex-wrap: wrap; }
.section-no { color: #a1adb5; font-size: 11px; font-variant-numeric: tabular-nums; }
h2 { font-size: 17px; font-weight: 600; margin: 0; color: #244858; }
.digest { background: #eaf0f1; border: 1px solid #e0e7e9; border-radius: 12px; padding: 14px 16px; }
.digest-item { display: flex; gap: 10px; padding: 8px 0; border-bottom: 1px solid #dae4e6; }
.digest-index { color: #93a4ae; font-size: 11px; padding-top: 5px; }
.digest-item p { margin: 0; font-size: 14px; line-height: 1.7; }
.digest-item .digest-detail { color: #6e8490; font-size: 12px; margin-top: 3px; }
.weather-note { font-size: 12px; line-height: 1.7; color: #53717e; margin: 0 0 6px; }
.plan-section { padding: 14px 16px; background: #fff; border: 1px solid #e3e8ec; border-radius: 12px; }
.plan-facts { display: grid; gap: 8px; }
.plan-facts > div { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 7px; }
.plan-facts span { font-size: 12px; color: #72828b; }
.plan-facts strong { font-size: 18px; font-variant-numeric: tabular-nums; font-weight: 600; }
small { color: #8a979f; font-size: 11px; font-weight: 400; }
p { font-size: 13px; line-height: 1.65; margin: 8px 0; }
.muted { color: #86939c; font-size: 12px; }
summary { cursor: pointer; min-height: 44px; align-content: center; color: #496978; font-size: 13px; }
.plan-unit { border-top: 1px solid #eef1f3; padding: 7px 0; }
h3 { font-size: 14px; margin: 0; font-weight: 600; }
.plan-unit p { margin: 4px 0; }
.supplement { background: #fff; padding: 12px 16px; border: 1px solid #e3e8ec; border-radius: 12px; margin-bottom: 8px; }
.supplement-heading { display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.supplement-heading > span { font-size: 10px; color: #88949b; }
.supplement ul { margin: 8px 0; padding-left: 17px; font-size: 13px; line-height: 1.65; color: #59717d; }
.supplement li + li { margin-top: 4px; }
.supplement a { display: inline-flex; align-items: center; min-height: 44px; font-size: 12px; }
.brief-footer { text-align: center; color: #a3adb4; font-size: 11px; line-height: 1.8; margin-top: 14px; }
.state { padding: 48px 16px; border-radius: 16px; background: #fff; text-align: center; font-size: 13px; line-height: 1.8; color: #6f8590; }
.error { color: #975838; }
@media (max-width: 600px) {
  .brief-main { padding: 6px 12px 20px; }
  .brief-header { padding-top: 6px; }
  h1 { font-size: 28px; }
  .digest, .plan-section, .supplement { padding: 12px; }
}
@media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto; } }
</style>
