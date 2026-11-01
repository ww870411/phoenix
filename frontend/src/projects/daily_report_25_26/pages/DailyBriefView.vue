<template>
  <div :class="['brief-page', `theme-${currentTheme}`]">
    <div class="newspaper-outer">
      <!-- 顶部控制条：返回与版式试用切换标签 -->
      <header class="toolbar-nav">
        <RouterLink to="/projects/daily_report_25_26/pages" class="back-link">
          <span class="back-arrow">‹</span> 返回功能页面
        </RouterLink>

        <!-- 报刊版式切换标签 -->
        <div class="theme-switcher">
          <span class="switcher-hint">报刊版式试用：</span>
          <div class="switcher-tabs">
            <button
              v-for="item in themes"
              :key="item.id"
              type="button"
              :class="['tab-btn', { active: currentTheme === item.id }]"
              :title="item.desc"
              @click="switchTheme(item.id)"
            >
              <span class="tab-icon">{{ item.icon }}</span>
              <span class="tab-name">{{ item.name }}</span>
            </button>
          </div>
        </div>

        <div class="user-badge">
          <span class="badge-dot"></span> 管理员专阅
        </div>
      </header>

      <!-- 报纸实体页面 -->
      <main class="newspaper-sheet">
        <!-- 报头 (Masthead) -->
        <header class="newspaper-masthead">
          <!-- 报眉元信息栏 -->
          <div class="masthead-meta">
            <div class="meta-left">
              <span class="edition-tag">内部参阅 · 机密编印</span>
              <span class="city-tag">辽宁 · 大连</span>
            </div>
            <div class="meta-center">
              <span class="group-name">大连洁净能源集团 · 经营生产内参</span>
            </div>
            <div class="meta-right">
              <span class="issue-no">版号：DR-{{ brief?.date ? brief.date.replace(/-/g, '') : '2026' }}</span>
              <span class="pub-weekday">{{ formattedChineseDate }}</span>
            </div>
          </div>

          <!-- 报纸大标题主视觉 -->
          <div class="masthead-main">
            <div class="masthead-brand">
              <h1 class="newspaper-title">
                每 日 简 报
                <span class="newspaper-subtitle">DAILY OPERATIONS & BUSINESS BRIEFING</span>
              </h1>
            </div>
          </div>

          <!-- 报刊检索副栏：日期切换 + 天气概况 + 同期对照 -->
          <div class="sub-masthead-bar">
            <div class="date-selector-box">
              <label for="brief-date" class="date-label">【刊印业务日期】</label>
              <select
                id="brief-date"
                :value="selectedDate"
                :disabled="loading || !dates.length"
                class="newspaper-select"
                @change="selectDate($event.target.value)"
              >
                <option v-if="!dates.length" value="">{{ loading ? '排版读取中…' : '暂无数据日期' }}</option>
                <option v-for="day in dates" :key="day" :value="day">
                  {{ day }}{{ day === latest ? ' · 最新发刊' : '' }}
                </option>
              </select>
              <button
                type="button"
                class="newspaper-refresh-btn"
                :disabled="loading"
                @click="load()"
              >
                {{ loading ? '排版中…' : '校订重载' }}
              </button>
            </div>

            <div v-if="brief?.weather?.summary" class="weather-box">
              <span class="weather-label">今日气象：</span>
              <BriefComparisonText :text="brief.weather.summary" />
            </div>
            <div v-if="brief?.peer_date" class="peer-box">
              <span>同期基准：{{ brief.peer_date }}</span>
            </div>
          </div>
        </header>

        <!-- 页面状态提示 -->
        <div v-if="loading" class="newspaper-status loading" role="status">
          <div class="status-spinner"></div>
          <p>正在铅字排版、校验各电厂生产与计划数据…</p>
        </div>
        <div v-else-if="error" class="newspaper-status error" role="alert">
          <p>【排版通信中断】{{ error }}</p>
          <button type="button" class="newspaper-retry-btn" @click="recover">重新印刷读取</button>
        </div>
        <div v-else-if="!brief?.date" class="newspaper-status empty">
          <p>{{ brief?.message || '今日暂无发刊记录，请在上侧刊印日期中选择其他已发布日期。' }}</p>
        </div>

        <!-- 报纸内容正文 -->
        <template v-else>
          <!-- 头版通栏：每日生产与经营运行态势综述 (Executive Editorial) -->
          <section class="newspaper-section headline-editorial-section" aria-labelledby="digest-title">
            <div class="editorial-heading">
              <div class="heading-badge">运行综述</div>
              <h2 id="digest-title">今日运行态势综述 · EXECUTIVE EDITORIAL</h2>
              <div class="heading-line"></div>
              <span class="editorial-stamp-tag">{{ formattedChineseDate }}</span>
            </div>

            <div class="editorial-lead-content">
              <!-- 由后端当日指标与设备调度证据生成，不在前端拼接固定运行结论 -->
              <div class="editorial-article">
                <p v-for="(paragraph, index) in brief.overview?.paragraphs || []" :key="paragraph.key" class="editorial-para">
                  <template v-if="index === 0 && paragraph.text"><span class="drop-cap">{{ paragraph.text[0] }}</span><BriefComparisonText :text="paragraph.text.slice(1)" /></template>
                  <BriefComparisonText v-else :text="paragraph.text" />
                </p>
              </div>
            </div>
          </section>

          <!-- 报纸双栏排版大展区 (Broadsheet Two-column Spread) -->
          <div class="newspaper-columns-spread">
            <!-- 左版 (Left Column): 集团总览与核心生产指标走势 -->
            <div class="paper-col paper-col-main">
              <section class="newspaper-section" aria-labelledby="group-title">
                <div class="editorial-heading">
                  <div class="heading-badge">重点大盘</div>
                  <h2 id="group-title">集团总览与重点指标 · GROUP OVERVIEW</h2>
                  <div class="heading-line"></div>
                </div>
                <div class="section-subtext">全集团供热、发电及能耗趋势监测</div>

                <BriefSubjectSection
                  :key="`${brief.date}-Group`"
                  :subject="brief.group"
                  class="newspaper-subject-section"
                />
              </section>
            </div>

            <!-- 报纸中缝线 (Vertical Crease / Column Rule) -->
            <div class="newspaper-crease" aria-hidden="true">
              <div class="crease-line"></div>
              <span class="crease-text">大连洁净能源 · 每日简报内参 · 中缝</span>
              <div class="crease-line"></div>
            </div>

            <!-- 右版 (Right Column): 标煤计划跟踪 + 外延要闻快讯 -->
            <div class="paper-col paper-col-side">
              <!-- 标煤计划对照 -->
              <section class="newspaper-section plan-section" aria-labelledby="plan-title">
                <div class="editorial-heading">
                  <div class="heading-badge">计划跟踪</div>
                  <h2 id="plan-title">标煤计划对照 · FUEL TARGETS</h2>
                  <div class="heading-line"></div>
                </div>

                <template v-if="brief.plan.monthly">
                  <div v-if="groupPlan" class="editorial-plan-board">
                    <div class="plan-hero-stat">
                      <div class="hero-left">
                        <span class="stat-label">全月计划执行进度</span>
                        <div class="newspaper-progress-bar">
                          <div
                            class="progress-fill"
                            :style="{ width: `${Math.min(100, Math.max(0, groupPlan.completion_percent || 0))}%` }"
                          ></div>
                        </div>
                      </div>
                      <div class="hero-right">
                        <strong class="stat-rate">{{ fmt(groupPlan.completion_percent, 1) }}<small>%</small></strong>
                      </div>
                    </div>

                    <div class="plan-stat-grid">
                      <div class="stat-cell">
                        <span class="cell-label">集团全月静态计划</span>
                        <strong class="cell-val">{{ fmt(groupPlan.plan_value) }} <small>吨</small></strong>
                      </div>
                      <div class="stat-cell">
                        <span class="cell-label">月初至{{ brief.date.slice(5) }}已报实际</span>
                        <strong class="cell-val">{{ fmt(groupPlan.actual_value) }} <small>吨</small></strong>
                      </div>
                    </div>
                  </div>

                  <div v-if="brief.plan.daily?.plan_value != null" class="daily-target-note">
                    <span class="note-tag">动态日考核</span>
                    <p>
                      集团动态日计划 <strong>{{ fmt(brief.plan.daily.plan_value) }}</strong> 吨，
                      当日实际与日计划差额为
                      <BriefComparisonText :text="`${signed(dailyPlanDelta)} 吨`" :delta="dailyPlanDelta" />。
                    </p>
                  </div>

                  <!-- 弹窗触发按钮 (替换原本的 details 折叠) -->
                  <div class="plan-trigger-box">
                    <button
                      type="button"
                      class="plan-modal-btn"
                      @click="openPlanModal"
                    >
                      <span class="plan-btn-tag">台账特辑</span>
                      <span class="plan-btn-text">
                        查阅各直属单位全月计划与执行台账 (共 {{ brief.plan.monthly.items.length }} 家)
                      </span>
                      <span class="plan-btn-arrow">››</span>
                    </button>
                  </div>
                </template>
                <p v-else class="empty-plan-text">{{ brief.plan.summary || '计划数据暂不可用。' }}</p>
              </section>

              <!-- 现货 · 调度 · 库存 快报栏目 -->
              <section class="newspaper-section market-section" aria-labelledby="extra-title">
                <div class="editorial-heading">
                  <div class="heading-badge">外延快报</div>
                  <h2 id="extra-title">现货 · 调度 · 库存</h2>
                  <div class="heading-line"></div>
                </div>

                <div class="supplement-list">
                  <article
                    v-for="block in brief.supplements"
                    :key="`${brief.date}-${block.title}`"
                    class="editorial-bulletin"
                  >
                    <div class="bulletin-header">
                      <h3 class="bulletin-title">{{ block.title }}</h3>
                      <span v-if="statusLabel(block.status)" class="bulletin-status">
                        [{{ statusLabel(block.status) }}]
                      </span>
                    </div>
                    <p v-if="block.summary" class="bulletin-summary">{{ block.summary }}</p>
                    <ul v-if="block.facts?.length" class="bulletin-facts">
                      <li v-for="(fact, index) in block.facts" :key="index">
                        <BriefComparisonText :text="fact" />
                      </li>
                    </ul>
                    <div class="bulletin-footer">
                      <RouterLink :to="blockLink(block.title)" class="editorial-link">
                        查阅{{ block.title }}台账明细 ››
                      </RouterLink>
                    </div>
                  </article>
                </div>
              </section>
            </div>
          </div>

          <!-- 报尾与发行印记 (Newspaper Colophon) -->
          <footer class="newspaper-colophon">
            <div class="colophon-divider">
              <span class="divider-diamond">◆</span>
              <span class="divider-line"></span>
              <span class="divider-diamond">◆</span>
            </div>
            <div class="colophon-grid">
              <div class="colophon-left">
                <p><strong>大连洁净能源集团 · 经济运行部</strong> 每日编审</p>
                <p>生产日报系统 每日速报专刊</p>
              </div>
              <div class="colophon-center">
                <div class="press-seal">
                  <span>集团日报</span>
                  <span>审 定</span>
                </div>
              </div>
              <div class="colophon-right">
                <p>整理发布时间：{{ generatedTime }}</p>
                <p class="copyright">© 2026 W.W. ALL RIGHTS RESERVED.</p>
              </div>
            </div>
          </footer>
        </template>
      </main>
    </div>

    <!-- 模态弹窗：各直属单位全月标煤计划与执行对照台账 -->
    <Teleport to="body">
      <div
        v-if="planModalVisible && brief?.plan?.monthly?.items"
        :class="['editorial-modal-backdrop', `theme-${currentTheme}`]"
        @click.self="closePlanModal"
      >
        <div
          class="editorial-modal-dialog plan-ledger-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="plan-ledger-title"
        >
          <!-- 弹窗报头 -->
          <div class="modal-header">
            <div class="modal-header-main">
              <span class="modal-edition-tag">能源计划台账特辑</span>
              <h3 id="plan-ledger-title" class="modal-title">
                各直属单位全月标煤计划与执行台账
              </h3>
            </div>
            <button
              type="button"
              class="modal-close-btn"
              title="关闭窗口 (Esc)"
              @click="closePlanModal"
            >
              ✕
            </button>
          </div>

          <!-- 导读说明 -->
          <div class="modal-lead-note">
            <span class="lead-tag">台账说明</span>
            <p>
              业务日期：{{ brief.date }} · 统计基准：集团全月静态编制计划。本台账列出各基层单位与主城区直属单位的月计划指标、月初至今已报实际耗煤及达成进度。
            </p>
          </div>

          <!-- 弹窗正文：全幅面台账明细表 -->
          <div class="modal-body">
            <div class="table-scroll-wrap">
              <table class="modal-ledger-table plan-full-table">
                <thead>
                  <tr>
                    <th>直属单位名称</th>
                    <th class="num-col">全月静态计划</th>
                    <th class="num-col">月初至今已报实际</th>
                    <th class="num-col">达成进度</th>
                    <th class="bar-col">执行进度条</th>
                    <th class="num-col">计划差额 (实际-计划)</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="row in brief.plan.monthly.items"
                    :key="row.company"
                    :class="{ 'group-highlight-row': row.company === 'Group' }"
                  >
                    <td class="unit-name-cell">
                      <strong>{{ row.company_cn }}</strong>
                    </td>
                    <td class="num-col">{{ fmt(row.plan_value) }} <small>吨</small></td>
                    <td class="num-col bold-val">{{ fmt(row.actual_value) }} <small>吨</small></td>
                    <td class="num-col bold-val rate-col">{{ fmt(row.completion_percent, 1) }}%</td>
                    <td class="bar-col">
                      <div class="table-progress-track">
                        <div
                          class="table-progress-fill"
                          :style="{ width: `${Math.min(100, Math.max(0, row.completion_percent || 0))}%` }"
                        ></div>
                      </div>
                    </td>
                    <td class="num-col">
                      <BriefComparisonText
                        v-if="row.actual_value != null && row.plan_value != null"
                        :text="`${row.actual_value - row.plan_value > 0 ? '+' : ''}${fmt(row.actual_value - row.plan_value)} 吨`"
                        :delta="row.actual_value - row.plan_value"
                      />
                      <span v-else>—</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- 弹窗页脚 -->
          <div class="modal-footer">
            <span class="footer-tip">按 Esc 键或点击外部遮罩均可退出台账窗口</span>
            <button type="button" class="modal-confirm-btn" @click="closePlanModal">返回日报</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, provide, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchDailyBrief } from '../services/api'
import BriefSubjectSection from '../components/BriefSubjectSection.vue'
import BriefComparisonText from '../components/BriefComparisonText.vue'
import { formatBriefNumber as fmt } from '../composables/dailyBriefPresentation'

const route = useRoute()
const router = useRouter()

// 报刊版式选项
const themes = [
  { id: 'broadsheet', name: '经典大报', icon: '📰', desc: '暖米纸色 · 传统宋体双线内参' },
  { id: 'financial', name: 'FT 财经', icon: '📈', desc: '鲑鱼粉纸 · 高密度数据金融风' },
  { id: 'modernist', name: '现代画报', icon: '🖋️', desc: '冷灰极简 · 现代排印与利落线条' },
]

// 优先取 URL query，其次取 localStorage，默认 broadsheet
const initialTheme = String(route.query.style || localStorage.getItem('phoenix_brief_theme') || 'broadsheet')
const currentTheme = ref(themes.some(t => t.id === initialTheme) ? initialTheme : 'broadsheet')

// 向所有子组件与弹窗提供当前主题
provide('briefTheme', currentTheme)

function switchTheme(id) {
  currentTheme.value = id
  localStorage.setItem('phoenix_brief_theme', id)
}

const brief = ref(null)
const loading = ref(false)
const error = ref('')
const dates = ref([])
const latest = ref('')

// 计划台账弹窗显隐状态
const planModalVisible = ref(false)

function onKeyDown(e) {
  if (e.key === 'Escape' && planModalVisible.value) {
    closePlanModal()
  }
}

function openPlanModal() {
  planModalVisible.value = true
  document.addEventListener('keydown', onKeyDown)
}

function closePlanModal() {
  planModalVisible.value = false
  document.removeEventListener('keydown', onKeyDown)
}

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

// 中文星期与大报日期格式
const formattedChineseDate = computed(() => {
  const targetDate = brief.value?.date || selectedDate.value
  if (!targetDate) return ''
  try {
    const parts = targetDate.split('-')
    if (parts.length === 3) {
      const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]))
      const days = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
      return `${parts[0]}年${Number(parts[1])}月${Number(parts[2])}日 ${days[d.getDay()]}`
    }
    return targetDate
  } catch {
    return targetDate
  }
})

let controller
let requestId = 0

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
    if (id === requestId && cause.name !== 'AbortError') {
      error.value = cause.message || '读取失败，请稍后重试。'
    }
  } finally {
    if (id === requestId) loading.value = false
  }
}

function selectDate(value) {
  router.replace({ query: { ...route.query, date: value } })
}

function recover() {
  if (route.query.date) {
    const query = { ...route.query }
    delete query.date
    router.replace({ query })
  } else {
    load()
  }
}

function signed(value) {
  return value == null ? '—' : `${value > 0 ? '+' : ''}${fmt(value)}`
}

function statusLabel(status) {
  return ({ partial: '部分记录', missing: '暂无记录', unavailable: '暂不可用' })[status] || ''
}

function blockLink(title) {
  const base = '/projects/daily_report_25_26/pages'
  if (title === '电力现货') return `${base}/spot_electricity`
  if (title === '生产调度') return `${base}/dispatch_info`
  return `${base}/dashboard/dashboard`
}

watch(() => route.query.date, load, { immediate: true })
onBeforeUnmount(() => {
  ++requestId
  controller?.abort()
  document.removeEventListener('keydown', onKeyDown)
})
</script>

<style scoped>
/* ==========================================================================
   1. 基础布局与多主题变量系统
   ========================================================================== */
.brief-page {
  min-height: 100vh;
  padding: 16px 12px 48px;
  box-sizing: border-box;
  transition: background-color 0.25s ease, color 0.25s ease;
  overflow-wrap: anywhere;
}

.brief-page *,
.brief-page *::before,
.brief-page *::after {
  box-sizing: border-box;
}

.newspaper-outer {
  max-width: 1220px;
  margin: 0 auto;
}

/* ----------------- 主题 1: 经典大报 (Broadsheet) ----------------- */
.theme-broadsheet {
  background-color: #ede8dc;
  color: #1f2529;
  font-family: 'Source Han Serif SC', 'Noto Serif CJK SC', 'SimSun', 'Songti SC', serif;
  --paper-bg: #faf7ef;
  --paper-outer-border: 1px solid #d5cebf;
  --paper-ink: #1f2529;
  --paper-muted: #646b70;
  --paper-rule: #d7d0c0;
  --paper-rule-dark: #1f2529;
  --accent-color: #9e2a2b;
  --sub-accent: #876233;
  --card-bg: #fdfcf9;
  --card-border: #ded8cb;
  --card-radius: 2px;
  --heading-font: 'Source Han Serif SC', 'Noto Serif CJK SC', 'SimSun', 'Songti SC', serif;
}

/* ----------------- 主题 2: FT 财经大报 (Financial Times) ----------------- */
.theme-financial {
  background-color: #eeddd0;
  color: #14232c;
  font-family: 'Georgia', 'Times New Roman', 'Source Han Serif SC', serif;
  --paper-bg: #fff1e5;
  --paper-outer-border: 1px solid #e2cbba;
  --paper-ink: #14232c;
  --paper-muted: #5e6c75;
  --paper-rule: rgba(20, 35, 44, 0.16);
  --paper-rule-dark: #14232c;
  --accent-color: #006096;
  --sub-accent: #990f3d;
  --card-bg: rgba(255, 255, 255, 0.52);
  --card-border: rgba(20, 35, 44, 0.15);
  --card-radius: 0px;
  --heading-font: 'Georgia', 'Times New Roman', 'Source Han Serif SC', serif;
}

/* ----------------- 主题 3: 现代文印画报 (Modernist) ----------------- */
.theme-modernist {
  background-color: #e5e7eb;
  color: #0f172a;
  font-family: 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  --paper-bg: #ffffff;
  --paper-outer-border: 1px solid #d1d5db;
  --paper-ink: #0f172a;
  --paper-muted: #64748b;
  --paper-rule: #e2e8f0;
  --paper-rule-dark: #0f172a;
  --accent-color: #2563eb;
  --sub-accent: #0284c7;
  --card-bg: #f8fafc;
  --card-border: #e2e8f0;
  --card-radius: 6px;
  --heading-font: 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
}

/* ==========================================================================
   2. 顶部工具栏 (返回 + 样式试用切换器)
   ========================================================================== */
.toolbar-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 8px 14px;
  margin-bottom: 12px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
  color: var(--paper-ink);
  text-decoration: none;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.15s ease;
}

.back-link:hover {
  background-color: rgba(0, 0, 0, 0.06);
}

.back-arrow {
  font-size: 16px;
  line-height: 1;
}

/* 样式切换胶囊 */
.theme-switcher {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.switcher-hint {
  font-size: 12px;
  font-weight: 600;
  color: var(--paper-muted);
}

.switcher-tabs {
  display: inline-flex;
  background: rgba(0, 0, 0, 0.06);
  padding: 3px;
  border-radius: 6px;
  gap: 3px;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: none;
  background: transparent;
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--paper-ink);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-btn:hover {
  background: rgba(255, 255, 255, 0.6);
}

.tab-btn.active {
  background: #ffffff;
  color: #000;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12);
}

.user-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--paper-muted);
}

.badge-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background-color: #22c55e;
}

/* ==========================================================================
   3. 报纸纸张主体 (Newspaper Sheet)
   ========================================================================== */
.newspaper-sheet {
  background-color: var(--paper-bg);
  border: var(--paper-outer-border);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
  padding: 24px 32px 36px;
  border-radius: 2px;
}

/* ----------------- 报头 (Masthead) ----------------- */
.newspaper-masthead {
  margin-bottom: 24px;
}

/* 报眉元信息条 */
.masthead-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  letter-spacing: 0.5px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--paper-rule-dark);
  color: var(--paper-muted);
}

.meta-left, .meta-right {
  display: flex;
  gap: 12px;
}

.edition-tag {
  font-weight: 700;
  color: var(--accent-color);
}

.group-name {
  font-weight: 600;
  color: var(--paper-ink);
  letter-spacing: 1px;
}

/* 报纸主标题区 */
.masthead-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0 12px;
  position: relative;
}

.masthead-brand {
  flex: 1;
  text-align: center;
}

.newspaper-title {
  margin: 0;
  font-size: clamp(32px, 4.5vw, 48px);
  font-weight: 800;
  font-family: var(--heading-font);
  letter-spacing: 6px;
  color: var(--paper-ink);
  line-height: 1.1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.newspaper-subtitle {
  font-size: clamp(10px, 1.2vw, 12px);
  letter-spacing: 4px;
  font-weight: 600;
  color: var(--paper-muted);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* Oxford 报头双线 (上粗下细) */
.sub-masthead-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 8px 0;
  border-top: 3px solid var(--paper-rule-dark);
  border-bottom: 1px solid var(--paper-rule-dark);
  margin-top: 4px;
  font-size: 12px;
}

.date-selector-box {
  display: flex;
  align-items: center;
  gap: 8px;
}

.date-label {
  font-weight: 700;
  color: var(--paper-ink);
}

.newspaper-select {
  border: 1px solid var(--card-border);
  background-color: var(--card-bg);
  color: var(--paper-ink);
  font: inherit;
  font-size: 13px;
  padding: 4px 10px;
  border-radius: var(--card-radius);
  outline: none;
  cursor: pointer;
}

.newspaper-refresh-btn {
  border: 1px solid var(--paper-rule-dark);
  background-color: transparent;
  color: var(--paper-ink);
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: var(--card-radius);
  cursor: pointer;
  transition: all 0.15s ease;
}

.newspaper-refresh-btn:hover:not(:disabled) {
  background-color: var(--paper-rule-dark);
  color: var(--paper-bg);
}

.weather-box, .peer-box {
  color: var(--paper-muted);
  font-size: 12px;
}

.weather-label {
  font-weight: 700;
  color: var(--paper-ink);
}

/* ==========================================================================
   4. 状态提示 (加载 / 错误 / 空态)
   ========================================================================== */
.newspaper-status {
  padding: 48px 16px;
  text-align: center;
  border: 1px dashed var(--paper-rule);
  margin: 20px 0;
  font-size: 14px;
  color: var(--paper-muted);
}

.status-spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--paper-rule);
  border-top-color: var(--accent-color);
  border-radius: 50%;
  margin: 0 auto 14px;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.newspaper-retry-btn {
  margin-top: 12px;
  padding: 6px 16px;
  border: 1px solid var(--paper-rule-dark);
  background: transparent;
  cursor: pointer;
  font-weight: 600;
}

/* ==========================================================================
   5. 报刊排版标题 (Editorial Heading)
   ========================================================================== */
.editorial-heading {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  padding-bottom: 4px;
  border-bottom: 1.5px solid var(--paper-rule-dark);
}

.heading-badge {
  background-color: var(--accent-color);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 2px;
  letter-spacing: 0.5px;
  white-space: nowrap !important;
  flex-shrink: 0 !important;
}

.theme-financial .heading-badge {
  background-color: var(--paper-rule-dark);
  color: var(--paper-bg);
}

.editorial-heading h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  font-family: var(--heading-font);
  color: var(--paper-ink);
  letter-spacing: 0.5px;
}

.heading-line {
  flex: 1;
  height: 1px;
}

.section-subtext {
  font-size: 12px;
  color: var(--paper-muted);
  margin: -6px 0 12px;
}

/* ==========================================================================
   6. 头版通栏：社论态势综述 (Headline Editorial)
   ========================================================================== */
.headline-editorial-section {
  background-color: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--card-radius);
  padding: 20px 24px;
  margin-bottom: 24px;
  border-left: 4px solid var(--accent-color);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.03);
}

.editorial-stamp-tag {
  font-size: 11px;
  font-weight: 700;
  color: var(--paper-muted);
  letter-spacing: 0.5px;
  white-space: nowrap !important;
  flex-shrink: 0 !important;
}

.editorial-lead-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.editorial-article {
  font-size: 14.5px;
  line-height: 1.85;
  color: var(--paper-ink);
  letter-spacing: 0.3px;
}

.editorial-para {
  margin: 0 0 10px;
}

.editorial-para:last-child {
  margin-bottom: 0;
}

/* 首字下沉 (Drop Cap) */
.drop-cap {
  float: left;
  font-size: 38px;
  line-height: 0.85;
  padding-top: 4px;
  padding-right: 8px;
  padding-bottom: 2px;
  font-family: var(--heading-font);
  font-weight: 800;
  color: var(--accent-color);
}

/* ==========================================================================
   7. 报纸大双栏展出版面 (Two-column Spread)
   ========================================================================== */
.newspaper-columns-spread {
  display: flex;
  gap: 24px;
  position: relative;
}

.paper-col-main {
  flex: 1.15;
  min-width: 0;
}

.paper-col-side {
  flex: 0.95;
  min-width: 0;
}

/* 报纸中缝线 */
.newspaper-crease {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 20px;
  flex-shrink: 0;
  user-select: none;
}

.crease-line {
  flex: 1;
  width: 1px;
  background-color: var(--paper-rule);
}

.crease-text {
  writing-mode: vertical-rl;
  font-size: 10px;
  letter-spacing: 2px;
  color: var(--paper-muted);
  padding: 12px 0;
  opacity: 0.6;
}

/* ==========================================================================
   8. 标煤计划对照与台账触发
   ========================================================================== */
.plan-section {
  background-color: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--card-radius);
  padding: 16px;
  margin-bottom: 20px;
}

.editorial-plan-board {
  margin-bottom: 12px;
}

.plan-hero-stat {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 10px 12px;
  background: rgba(0, 0, 0, 0.025);
  border: 1px solid var(--paper-rule);
  margin-bottom: 10px;
}

.hero-left {
  flex: 1;
}

.stat-label {
  display: block;
  font-size: 12px;
  font-weight: 700;
  color: var(--paper-muted);
  margin-bottom: 6px;
}

.newspaper-progress-bar {
  height: 6px;
  background-color: var(--paper-rule);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: var(--accent-color);
  transition: width 0.4s ease;
}

.hero-right .stat-rate {
  font-size: 26px;
  font-weight: 800;
  color: var(--accent-color);
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.stat-rate small {
  font-size: 14px;
}

.plan-stat-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.stat-cell {
  border: 1px solid var(--paper-rule);
  padding: 8px 10px;
}

.cell-label {
  display: block;
  font-size: 11px;
  color: var(--paper-muted);
  margin-bottom: 4px;
}

.cell-val {
  font-size: 16px;
  font-weight: 700;
  color: var(--paper-ink);
  font-variant-numeric: tabular-nums;
}

.cell-val small {
  font-size: 11px;
  font-weight: 400;
  color: var(--paper-muted);
}

.daily-target-note {
  border-left: 3px solid var(--accent-color);
  padding: 6px 10px;
  margin: 10px 0;
  background: rgba(0, 0, 0, 0.02);
  font-size: 12px;
  line-height: 1.6;
}

.note-tag {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  background: var(--paper-rule-dark);
  color: var(--paper-bg);
  padding: 1px 4px;
  margin-right: 6px;
  border-radius: 2px;
}

/* 计划明细弹窗触发按钮条 */
.plan-trigger-box {
  margin-top: 12px;
}

.plan-modal-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 14px;
  background: rgba(0, 0, 0, 0.03);
  border: 1px dashed var(--paper-rule);
  border-radius: 4px;
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  color: inherit;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.plan-modal-btn:hover {
  background: rgba(0, 0, 0, 0.06);
  border-style: solid;
}

.plan-btn-tag {
  font-size: 10px;
  font-weight: 700;
  background: var(--accent-color);
  color: #fff;
  padding: 2px 5px;
  border-radius: 2px;
  flex-shrink: 0;
}

.plan-btn-text {
  flex: 1;
}

.plan-btn-arrow {
  font-size: 14px;
}

/* ==========================================================================
   9. 现货 · 调度 · 库存 外延栏目
   ========================================================================== */
.market-section {
  background-color: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: var(--card-radius);
  padding: 16px;
}

.supplement-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.editorial-bulletin {
  border-bottom: 1px dotted var(--paper-rule);
  padding-bottom: 10px;
}

.editorial-bulletin:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.bulletin-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
}

.bulletin-title {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--paper-ink);
}

.bulletin-status {
  font-size: 10px;
  color: var(--accent-color);
  font-weight: 600;
}

.bulletin-summary {
  font-size: 12px;
  line-height: 1.6;
  color: var(--paper-ink);
  margin: 4px 0 6px;
}

.bulletin-facts {
  margin: 4px 0 8px;
  padding-left: 16px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--paper-muted);
}

.bulletin-footer {
  text-align: right;
}

.editorial-link {
  font-size: 11px;
  font-weight: 600;
  color: var(--accent-color);
  text-decoration: none;
}

.editorial-link:hover {
  text-decoration: underline;
}

/* ==========================================================================
   10. 报尾与发行印记 (Colophon)
   ========================================================================== */
.newspaper-colophon {
  margin-top: 36px;
  padding-top: 16px;
  color: var(--paper-muted);
}

.colophon-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 16px;
  color: var(--paper-rule-dark);
}

.divider-line {
  height: 1px;
  flex: 1;
  background-color: var(--paper-rule);
}

.divider-diamond {
  font-size: 10px;
}

.colophon-grid {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 11px;
  line-height: 1.6;
}

.colophon-center {
  display: flex;
  justify-content: center;
}

.press-seal {
  width: 52px;
  height: 52px;
  border: 1.5px solid var(--accent-color);
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 700;
  color: var(--accent-color);
  letter-spacing: 1px;
  line-height: 1.3;
  opacity: 0.75;
}

.colophon-right {
  text-align: right;
}

.copyright {
  font-size: 10px;
  opacity: 0.7;
}

/* ==========================================================================
   11. 子组件深度样式穿透 (深入适配报纸质感)
   ========================================================================== */
:deep(.metric-card) {
  background-color: var(--card-bg) !important;
  border: 1px solid var(--card-border) !important;
  border-radius: var(--card-radius) !important;
  box-shadow: none !important;
  transition: border-color 0.15s ease;
}

:deep(.metric-card:hover) {
  border-color: var(--accent-color) !important;
}

:deep(.metric-top h4) {
  font-family: var(--heading-font);
  font-weight: 700;
  color: var(--paper-ink);
}

:deep(.continuity) {
  background: rgba(0, 0, 0, 0.04) !important;
  color: var(--accent-color) !important;
  border: 1px solid var(--card-border);
}

:deep(.metric-value) {
  color: var(--paper-ink) !important;
  font-family: var(--heading-font);
}

:deep(.metric-change) {
  color: var(--paper-muted) !important;
}

/* ==========================================================================
   12. 计划台账全幅模态弹窗系统 (Teleported Modal)
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

.plan-ledger-dialog {
  width: 100%;
  max-width: 960px;
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

/* 弹窗正文滚动区 */
.modal-body {
  padding: 18px 20px;
  overflow-y: auto;
}

.table-scroll-wrap {
  overflow-x: auto;
}

.modal-ledger-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  line-height: 1.5;
}

.modal-ledger-table th {
  border-bottom: 2px solid currentColor;
  padding: 8px 6px;
  text-align: left;
  font-size: 12px;
  font-weight: 700;
  opacity: 0.75;
}

.modal-ledger-table td {
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  padding: 9px 6px;
}

.modal-ledger-table .num-col {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.modal-ledger-table .bold-val {
  font-weight: 700;
}

.modal-ledger-table .rate-col {
  font-size: 14px;
}

.group-highlight-row {
  background: rgba(0, 0, 0, 0.035);
}

.unit-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.group-tag {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  background: var(--accent-color);
  color: #fff;
  border-radius: 2px;
}

/* 进度槽 */
.bar-col {
  width: 120px;
  padding: 9px 8px;
}

.table-progress-track {
  height: 6px;
  background-color: rgba(0, 0, 0, 0.08);
  border-radius: 3px;
  overflow: hidden;
}

.table-progress-fill {
  height: 100%;
  background-color: var(--accent-color);
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

/* ==========================================================================
   13. 响应式布局优化 (移动端自适应)
   ========================================================================== */
@media (max-width: 960px) {
  .newspaper-columns-spread {
    flex-direction: column;
  }
  .newspaper-crease {
    display: none;
  }
  .colophon-grid {
    flex-direction: column;
    text-align: center;
  }
  .colophon-right {
    text-align: center;
  }
}

@media (max-width: 640px) {
  .newspaper-sheet {
    padding: 16px 14px 24px;
  }
  .toolbar-nav {
    flex-direction: column;
    align-items: stretch;
  }
  .theme-switcher {
    justify-content: center;
  }
  .sub-masthead-bar {
    flex-direction: column;
    align-items: flex-start;
  }
  .newspaper-title {
    font-size: 28px;
    letter-spacing: 3px;
  }
  .bar-col {
    display: none;
  }
}
</style>
