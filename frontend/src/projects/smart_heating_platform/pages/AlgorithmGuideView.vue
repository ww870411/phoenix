<template>
  <div class="shp-algo-view">
    <AppHeader />
    <main class="shp-main container">
      <Breadcrumbs :items="breadcrumbItems" />

      <header class="topbar card elevated">
        <div class="topbar-info">
          <div class="title-row">
            <h2>主体每小时指标算法与源站接口参考手册</h2>
            <span class="role-badge">参考解释 · 仅限 Global_admin</span>
          </div>
          <p class="subtitle">
            切换上方标签可分别查阅：① 各统计主体每小时代表断面与累计耗量公式、清洗口径与试算器；② 授权源站全量接口清单、返回字段、限速规范与本平台调用方式。
          </p>
        </div>
        <div class="topbar-actions">
          <button class="btn secondary" type="button" @click="goBackPages">
            ⬅️ 返回功能页
          </button>
          <button class="btn primary" type="button" @click="goWorkbench">
            📊 前往运行工作台
          </button>
        </div>
      </header>

      <!-- 顶层双标签页切换 -->
      <nav class="main-tab-bar card elevated" aria-label="参考手册标签切换">
        <button
          type="button"
          :class="['main-tab-btn', { active: activeMainTab === 'algorithms' }]"
          @click="activeMainTab = 'algorithms'"
        >
          <span>📐 主体每小时指标算法</span>
          <span class="tab-count">{{ entityCategories.length }} 类主体</span>
        </button>
        <button
          type="button"
          :class="['main-tab-btn', { active: activeMainTab === 'apis' }]"
          @click="activeMainTab = 'apis'"
        >
          <span>🔌 源站接口清单与使用方式</span>
          <span class="tab-count">{{ sourceEndpoints.length }} 个接口/规范</span>
        </button>
      </nav>

      <!-- 标签页 1：原有主体每小时指标算法 -->
      <template v-if="activeMainTab === 'algorithms'">
      <!-- 主体分类选择器 -->
      <section class="entity-selector-grid" aria-label="主体分类选择">
        <button
          v-for="cat in entityCategories"
          :key="cat.key"
          type="button"
          :class="['card elevated entity-card', { active: selectedKey === cat.key }]"
          @click="selectCategory(cat.key)"
        >
          <div class="entity-card-top">
            <span class="entity-icon">{{ cat.icon }}</span>
            <span :class="['entity-badge', cat.hasHourly ? 'badge-hourly' : 'badge-daily']">
              {{ cat.hasHourly ? '有逐小时算法' : '仅日度结算' }}
            </span>
          </div>
          <strong class="entity-title">{{ cat.title }}</strong>
          <span class="entity-scale">{{ cat.scale }}</span>
          <p class="entity-brief">{{ cat.brief }}</p>
        </button>
      </section>

      <!-- 当前选中主体详情 -->
      <section v-if="activeCategory" class="detail-stack">
        <!-- 主体数据链路摘要 -->
        <article class="card elevated pipeline-card">
          <div class="pipeline-head">
            <div>
              <h3>{{ activeCategory.icon }} {{ activeCategory.title }} —— 数据流转与口径总览</h3>
              <p class="pipeline-summary">{{ activeCategory.summary }}</p>
            </div>
            <div class="filter-controls">
              <input
                v-model="metricKeyword"
                type="search"
                class="ctrl-input"
                placeholder="筛选指标名称/字段/公式…"
              />
            </div>
          </div>

          <div class="meta-strip">
            <div class="meta-item">
              <span class="meta-label">基础台账字典表</span>
              <code class="meta-code">{{ activeCategory.dictTables }}</code>
            </div>
            <div class="meta-item">
              <span class="meta-label">源站采集接口</span>
              <code class="meta-code">{{ activeCategory.sourceApis }}</code>
            </div>
            <div class="meta-item">
              <span class="meta-label">15分钟采样层</span>
              <code class="meta-code">{{ activeCategory.fact15mTable }}</code>
            </div>
            <div class="meta-item">
              <span class="meta-label">小时/日度产出表</span>
              <code class="meta-code">{{ activeCategory.factOutputTable }}</code>
            </div>
          </div>

          <div v-if="activeCategory.keyNote" class="note-callout">
            <strong>💡 核心口径提示：</strong>{{ activeCategory.keyNote }}
          </div>
        </article>

        <!-- 该主体的逐小时指标算法列表 -->
        <article class="card elevated metrics-card">
          <div class="section-head">
            <h3>指标逐项算法明细（共 {{ filteredMetrics.length }} 项）</h3>
            <div class="kind-pills">
              <button
                v-for="k in kindOptions"
                :key="k.value"
                type="button"
                :class="['kind-pill', { active: kindFilter === k.value }]"
                @click="kindFilter = k.value"
              >
                {{ k.label }}
              </button>
            </div>
          </div>

          <div v-if="filteredMetrics.length === 0" class="empty-box">
            当前筛选条件下暂无匹配的指标。
          </div>

          <div v-else class="metric-list">
            <div v-for="m in filteredMetrics" :key="m.id" class="metric-item">
              <div class="metric-header">
                <div class="metric-title-wrap">
                  <span :class="['kind-tag', `kind-${m.kind}`]">{{ kindText(m.kind) }}</span>
                  <h4 class="metric-name">{{ m.name }}</h4>
                  <span v-if="m.unit" class="metric-unit">单位：{{ m.unit }}</span>
                </div>
                <code class="metric-field">{{ m.field }}</code>
              </div>

              <div class="metric-body-grid">
                <div class="formula-box">
                  <div class="box-title">📐 主算法与计算公式</div>
                  <p class="formula-expr">{{ m.formula }}</p>
                  <p class="formula-steps">{{ m.steps }}</p>
                  <div v-if="m.example" class="formula-example">
                    <span class="ex-label">举例：</span>{{ m.example }}
                  </div>
                </div>

                <div class="guard-box">
                  <div class="guard-row">
                    <span class="guard-label">🔄 降级 / 兜底策略</span>
                    <p class="guard-text">{{ m.fallback }}</p>
                  </div>
                  <div class="guard-row">
                    <span class="guard-label">🧹 异常清洗与阴面拦截</span>
                    <p class="guard-text">{{ m.cleaning }}</p>
                  </div>
                  <div class="guard-row">
                    <span class="guard-label">🏷️ 数值来源标记</span>
                    <p class="guard-text mono-text">{{ m.sourceTags }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </article>

        <!-- 双轨累计核心原理解析 + 交互试算小工具 -->
        <article class="card elevated explainer-card">
          <div class="section-head">
            <h3>🔬 核心累计算法直观对比：整点表底差值 vs 15分钟梯形积分</h3>
            <span class="subtitle-inline">适用于所有“小时累计耗量”指标，理解系统如何把瞬时值/非整点抄表变成精确整点小时值</span>
          </div>

          <div class="explainer-grid">
            <div class="explainer-panel">
              <h4>方法 A（首选校准）：整点表底线性插值作差 <code>METER_DIFF</code></h4>
              <ol class="step-list">
                <li><strong>抓历史表底：</strong>系统错峰轮询 <code>/hrz_ls_zb/</code>，拿到某站前后约 15 分钟一次的累计表底（<code>f221=totJ</code>、<code>f220=totF</code>、<code>f254=补水</code>、<code>f253=电量</code>）。</li>
                <li><strong>对齐整点：</strong>对目标整点 <code>H:00</code>（允许前后 ±90 秒直接命中；否则用两侧跨度 ≤50 分钟的点做线性插值；单侧 10 分钟内取最近值）。</li>
                <li><strong>相减与防跳变：</strong><code>小时累计 = V(H+1:00) - V(H:00)</code>；若出现倒走/清零（<code>&lt; -0.01</code>）或超负荷极限 1.5 倍，则判定表底跳变（<code>METER_JUMP</code>）并写入阴面督办。</li>
              </ol>
            </div>

            <div class="explainer-panel">
              <h4>方法 B（实时估算/兜底）：15分钟梯形面积积分 <code>INTEGRAL_15M</code></h4>
              <ol class="step-list">
                <li><strong>高频采集瞬时速率：</strong>在每小时的 <code>:00 / :15 / :30 / :45</code> 抓取瞬时热量（<code>GJ/h</code>）或瞬时流量（<code>t/h</code>）。</li>
                <li><strong>计算相邻梯形面积：</strong>相邻两点 <code>(t₀, v₀)</code> 与 <code>(t₁, v₁)</code> 之间面积为 <code>max(0, (v₀ + v₁)/2) × (Δt / 3600)</code>。</li>
                <li><strong>折算标准 1 小时：</strong>若本小时尚未走完（例如只采到前 30 分钟的 3 个点），将累计面积按 <code>× (3600 / 已覆盖总秒数)</code> 等比外推至整 1 小时；若只有 1 个点，直接按 <code>v₀ × 1.0h</code> 估算。</li>
              </ol>
            </div>
          </div>

          <!-- 交互试算器 -->
          <div class="calculator-box">
            <div class="calc-head">
              <strong>🧮 现场试算器（以“10:00 ~ 11:00 某换热站小时供热量”为例）</strong>
              <button class="btn secondary btn-xs" type="button" @click="resetCalculator">恢复示例数据</button>
            </div>
            <div class="calc-grid">
              <div class="calc-col">
                <h5>1. 表底插值试算（方法 A）</h5>
                <div class="calc-inputs">
                  <label>
                    <span>09:50 表底 (GJ)</span>
                    <input v-model.number="calc.jPrevLeft" type="number" step="0.1" class="ctrl-input" />
                  </label>
                  <label>
                    <span>10:05 表底 (GJ)</span>
                    <input v-model.number="calc.jPrevRight" type="number" step="0.1" class="ctrl-input" />
                  </label>
                  <label>
                    <span>10:50 表底 (GJ)</span>
                    <input v-model.number="calc.jNextLeft" type="number" step="0.1" class="ctrl-input" />
                  </label>
                  <label>
                    <span>11:05 表底 (GJ)</span>
                    <input v-model.number="calc.jNextRight" type="number" step="0.1" class="ctrl-input" />
                  </label>
                </div>
                <div class="calc-result">
                  <div>10:00 插值表底：<strong>{{ calcResult.interp10 }} GJ</strong> <span class="muted">(= left + 10/15 × (right - left))</span></div>
                  <div>11:00 插值表底：<strong>{{ calcResult.interp11 }} GJ</strong> <span class="muted">(= left + 10/15 × (right - left))</span></div>
                  <div class="calc-highlight">10时累计供热量：<strong>{{ calcResult.meterDiff }} GJ</strong></div>
                </div>
              </div>

              <div class="calc-col">
                <h5>2. 15分钟梯形积分试算（方法 B，4个瞬时热量采样 GJ/h）</h5>
                <div class="calc-inputs">
                  <label>
                    <span>10:00 瞬时 (GJ/h)</span>
                    <input v-model.number="calc.s0" type="number" step="0.1" class="ctrl-input" />
                  </label>
                  <label>
                    <span>10:15 瞬时 (GJ/h)</span>
                    <input v-model.number="calc.s15" type="number" step="0.1" class="ctrl-input" />
                  </label>
                  <label>
                    <span>10:30 瞬时 (GJ/h)</span>
                    <input v-model.number="calc.s30" type="number" step="0.1" class="ctrl-input" />
                  </label>
                  <label>
                    <span>10:45 瞬时 (GJ/h)</span>
                    <input v-model.number="calc.s45" type="number" step="0.1" class="ctrl-input" />
                  </label>
                </div>
                <div class="calc-result">
                  <div>三段梯形面积之和（覆盖 45 分钟）：<strong>{{ calcResult.rawArea }} GJ</strong></div>
                  <div>按 <code>3600 / 2700</code> 外推到整 1 小时：</div>
                  <div class="calc-highlight">积分估算供热量：<strong>{{ calcResult.integralEst }} GJ</strong></div>
                </div>
              </div>
            </div>
          </div>
        </article>
      </section>
      </template>

      <!-- 标签页 2：源站接口清单、获取的数据与使用方式 -->
      <template v-else-if="activeMainTab === 'apis'">
        <!-- 使用规范与调用红线总览 -->
        <section class="card elevated api-guide-card">
          <div class="section-head">
            <h3>🛡️ 源站接入环境与通用调用规范</h3>
            <span class="subtitle-inline">外网直连：<code>http://124.93.31.19:6688</code> ｜ 内网原址：<code>http://192.168.1.206:6688</code></span>
          </div>

          <div class="rules-grid">
            <div class="rule-box">
              <h4>1. 受控并行采集保护</h4>
              <p>
                默认使用受控多线程并发（<code>max_workers = 4</code>，可在设置页 <code>1~16</code> 调节）与单作业独立锁，各调度任务互不阻塞；每次请求保持失败退避重试与 <code>Connection: close</code>。
              </p>
            </div>
            <div class="rule-box">
              <h4>2. 大包断流与代理绕过</h4>
              <p>
                全网商户接口（约 142KB）与历史宽表接口在长连接下偶发于 13KB 处截断（<code>RemoteProtocolError</code>）。请求需携带 <code>Connection: close</code>、禁用系统代理（<code>trust_env=False</code>），并配置失败退避重试与并发分片降级。
              </p>
            </div>
            <div class="rule-box">
              <h4>3. 鉴权分界与算完即清</h4>
              <p>
                约 85% 的实时与历史 JSON 接口可<strong>免 Cookie 直接调用</strong>；仅居民室温（<code>/jumin/</code>、<code>/sw_ls_export/</code>）及商业日报（<code>/getall_bb_shrb/</code>）需携带 <code>Session Cookie</code>。5 分钟采样明细采用<strong>2 小时算完即清</strong>（仅留当前小时 + 上一小时）。
              </p>
            </div>
          </div>
        </section>

        <!-- 接口筛选条与卡片清单 -->
        <section class="card elevated metrics-card">
          <div class="section-head">
            <h3>源站接口全量清单（命中 {{ filteredEndpoints.length }} / {{ sourceEndpoints.length }} 项）</h3>
            <div class="api-filter-row">
              <div class="kind-pills">
                <button
                  v-for="g in apiGroups"
                  :key="g.value"
                  type="button"
                  :class="['kind-pill', { active: apiGroupFilter === g.value }]"
                  @click="apiGroupFilter = g.value"
                >
                  {{ g.label }}
                </button>
              </div>
              <select v-model="apiAuthFilter" class="ctrl-input compact-select">
                <option value="all">全部鉴权类型</option>
                <option value="no_cookie">仅免 Cookie</option>
                <option value="cookie">需 Session Cookie</option>
                <option value="forbidden">严禁调用 / 失效</option>
              </select>
              <input
                v-model="apiKeyword"
                type="search"
                class="ctrl-input"
                placeholder="搜索路径、主体、返回字段或用途…"
              />
            </div>
          </div>

          <div v-if="filteredEndpoints.length === 0" class="empty-box">
            当前筛选条件下无匹配接口。
          </div>

          <div v-else class="metric-list">
            <div
              v-for="ep in filteredEndpoints"
              :key="ep.id"
              :class="['metric-item', { 'api-danger-item': ep.auth === 'forbidden' }]"
            >
              <div class="metric-header">
                <div class="metric-title-wrap">
                  <span :class="['method-tag', `method-${ep.method.toLowerCase()}`]">{{ ep.method }}</span>
                  <code class="api-path-code">{{ ep.path }}</code>
                  <span :class="['auth-pill', `auth-${ep.auth}`]">{{ authLabel(ep.auth) }}</span>
                  <span class="kind-tag kind-cumulative">{{ groupLabel(ep.group) }}</span>
                </div>
                <span class="api-entity-tag">对应主体：{{ ep.entity }}</span>
              </div>

              <div class="metric-body-grid">
                <div class="formula-box">
                  <div class="box-title">📦 获取的数据与核心字段</div>
                  <p class="formula-steps"><strong>返回规模：</strong>{{ ep.scale }}</p>
                  <p class="formula-expr">{{ ep.fields }}</p>
                  <p class="formula-steps">{{ ep.dataDesc }}</p>
                </div>

                <div class="guard-box">
                  <div class="guard-row">
                    <span class="guard-label">⚙️ 请求入参与使用方式</span>
                    <p class="guard-text mono-text">{{ ep.usage }}</p>
                  </div>
                  <div class="guard-row">
                    <span class="guard-label">🕒 调度周期与落库表</span>
                    <p class="guard-text">{{ ep.scheduleAndTable }}</p>
                  </div>
                  <div class="guard-row">
                    <span class="guard-label">⚠️ 实测注意事项 / 避坑指南</span>
                    <p class="guard-text">{{ ep.notes }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- 本平台调度与运维触发方式 -->
        <section class="card elevated api-guide-card">
          <div class="section-head">
            <h3>🚀 本旁路平台采集与历史回溯调用方式</h3>
            <span class="subtitle-inline">无需直接改源站代码，统一由旁路平台调度或管理员手动触发</span>
          </div>

          <div class="ops-grid">
            <div class="ops-card">
              <h4>1. 自动定时调度（`scheduler_service.py`）</h4>
              <ul class="step-list">
                <li><strong>高频并行采样（默认每 5 分钟）：</strong>并发拉取上游（<code>/gk_get_data/</code>）与商业用户（<code>/get_sh_data/</code>），整点 <code>:00</code> 附带 <code>/jumin/</code>；跨小时定格积分并自动清理 2 小时前采样明细。</li>
                <li><strong>换热站整点表底校准（默认每小时 :05）：</strong>路线 B 下彻底不拉换热站实时与二次分区，每小时整点后受控并行拉取 <code>/hrz_ls_zb/</code> 产出上一小时精确表底差值与代表断面。</li>
                <li><strong>商业日结采集（每日 08:30）：</strong>调用 <code>/getall_bb_shrb/</code> 落盘前一日商业耗量。</li>
              </ul>
            </div>

            <div class="ops-card">
              <h4>2. 手动触发接口与历史回溯命令</h4>
              <ul class="step-list">
                <li><strong>页面入口：</strong>工作台右上角“⚡ 立即采集当前时段”按钮，或日报页“📏 校准当日表底”。</li>
                <li><strong>平台 API：</strong><code>POST /api/v1/projects/smart_heating_platform/reports/collect-now</code>，<code>action</code> 可选 <code>snapshot</code> / <code>calib</code> / <code>merchant</code> / <code>merchant_hourly_backfill</code>。</li>
                <li><strong>全量历史回溯脚本：</strong><code>python backend/scripts/backfill_smart_heating_history.py --start 2026-11-01 --end YYYY-MM-DD --steps all</code>（支持断点续传）。</li>
              </ul>
            </div>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'

const router = useRouter()

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '智慧供热旁路精算与质检平台', to: '/projects/smart_heating_platform/pages' },
  { label: '主体每小时指标算法说明书', to: null },
])

function goBackPages() {
  router.push('/projects/smart_heating_platform/pages')
}

function goWorkbench() {
  router.push('/projects/smart_heating_platform/pages/hourly_report')
}

const activeMainTab = ref('algorithms')
const selectedKey = ref('station')
const metricKeyword = ref('')
const kindFilter = ref('all')

const apiGroupFilter = ref('all')
const apiAuthFilter = ref('all')
const apiKeyword = ref('')

const apiGroups = [
  { value: 'all', label: '全部接口' },
  { value: 'realtime', label: '实时批量采集' },
  { value: 'history', label: '历史回溯补采' },
  { value: 'daily_ref', label: '商业日结与参考' },
  { value: 'forbidden', label: '禁用 / 失效接口' },
]

function groupLabel(g) {
  if (g === 'realtime') return '实时批量采集'
  if (g === 'history') return '历史回溯补采'
  if (g === 'daily_ref') return '商业日结与参考'
  return '禁用 / 失效红线'
}

function authLabel(a) {
  if (a === 'no_cookie') return '免 Cookie'
  if (a === 'cookie') return '需 Session Cookie'
  return '严禁 / 失效'
}

const sourceEndpoints = [
  {
    id: 'ep-gk-get',
    group: 'realtime',
    method: 'POST',
    path: '/gk_get_data/',
    auth: 'no_cookie',
    entity: '上游热源 / 首站 / 混水 / 分网 / 大户',
    scale: '1 次请求获取全网 137 个点位（含《工况一览》82 核心点）',
    fields: 'dc_dict(58) / sz_dict(54) / yw2_dict(19) / yw_dict(4) / sh_dict(2)：WENDU, YALI, LIULIANG, RELIANG, FUHE, PINLV, SHIJIAN / update_time',
    dataDesc: '同时覆盖北海/香海电厂、4 座首站、5 混水点、12 项分网汇总及造船大户，是实时上游主采集源（替代原 HTML 页 /gk_ssxx/）。',
    usage: 'POST {base}/gk_get_data/（空表单即可）',
    scheduleAndTable: '每 5 分钟并发采集 → fact_upstream_15min（保留 2 小时）→ 整点后梯形积分至 fact_upstream_hourly',
    notes: 'sh_dict 时间字段为 update_time 而非 SHIJIAN；蒸汽测点高温阈值需按 >=600℃ 判定，停运备机流量<=1 时 0℃ 不误报故障。',
  },
  {
    id: 'ep-yw-data',
    group: 'realtime',
    method: 'POST',
    path: '/get_yw_data/1',
    auth: 'no_cookie',
    entity: '242 座换热站一次网及时间戳',
    scale: '1 次请求返回全网全部 242 座站',
    fields: 'name, update_time, f1(一网供压MPa), f2(一网供流t/h), f3(一网供温℃), f4(一网回压MPa), f5(一网回温℃), f222(一网瞬时热量GJ/h)',
    dataDesc: '补齐 /zx_hrz/ 无时间戳与 5 座无分区站缺失的一网断面；在 /zx_hrz/ 未覆盖的站上作为辅助来源。',
    usage: 'POST {base}/get_yw_data/1  Body: yw_selected=1',
    scheduleAndTable: '每 15 分钟采集 → 联合 /zx_hrz/ 写入 fact_station_15min',
    notes: '源站中该接口偶发存在全网级时间戳滞后，因此换热站是否掉线以 /zx_hrz/ 的 online 布尔值为核心判据，不直接据此判全网离线。',
  },
  {
    id: 'ep-zx-hrz',
    group: 'realtime',
    method: 'POST',
    path: '/zx_hrz/',
    auth: 'no_cookie',
    entity: '237 座换热站 + 580 个二次网分区',
    scale: '按 center_id 60~68 循环 9 次获取全网站与分区',
    fields: 'online, e1(一网供流), e3/e4(一网供回温), e7/e8(一网供回压), e11(一网瞬时热), e13(一网回流), e14(自来水补水), e16(水位), Nx[{name, data:{e2,e5,e6,e9,e10,e12,e15}}]',
    dataDesc: '换热站与二次网最完整实时来源；一二网热平衡校核直接对比 e11 与 Σe12。',
    usage: 'POST {base}/zx_hrz/  Body: branch_id=60..68（注意 branch_id=0 会返回 HTTP 500）',
    scheduleAndTable: '每 15 分钟采集 → fact_station_15min & fact_zone_15min → 聚合 hourly',
    notes: '“香炉礁”站水位 e16 在 Nx[0].data.e16 中；单站 e14 > 100 t/h 判满量程坏表屏蔽；二网 e12 严禁用于阳面热耗累加。',
  },
  {
    id: 'ep-sh-data',
    group: 'realtime',
    method: 'POST',
    path: '/get_sh_data/0 与 /get_sh_data/{mn_id}',
    auth: 'no_cookie',
    entity: '464 户商业用户实时运行参数',
    scale: '0 为全网 1 次返回 468 条；2..16 按主干网分片拉取',
    fields: 'name, xinhaoqiangdu(0=在线), gongshuiliuliang, huishuliuliang, gongshuiwendu, huishuiwendu, gongshuiyali, huishuiyali, shunshireliang, famenkaidu, shedingfamen',
    dataDesc: '实测发现的商业用户批量实时接口，每 15 分钟提供全部商业户瞬时热量与流量用于计算小时积分。',
    usage: '优先 POST {base}/get_sh_data/0 (sh_selected=0, Header Connection: close)；断流时自动降级循环 mn_id=2..16',
    scheduleAndTable: '每 5 分钟并发采集 → fact_merchant_15min（保留 2 小时）→ 整点后梯形积分至 fact_merchant_hourly',
    notes: '全网返回含 4 户未入账测试户与 1 组别名（国际航运中心大厦）；rdry="蒸汽" 商户原值为 kg/h 与 MJ/h，入库自动 ÷1000 折算并屏蔽 -200℃ 回温。',
  },
  {
    id: 'ep-jumin',
    group: 'realtime',
    method: 'POST',
    path: '/jumin/',
    auth: 'cookie',
    entity: '2,097 户居民室温测温终端',
    scale: '1 次请求免分页返回全量 ~2,100 户',
    fields: 'id(IMEI/ICCID), village_name(门牌), station_name(含15组非标别名), wd1(室温℃), upload_time, zdxh(型号), remark, Beizhu',
    dataDesc: '居民室内真实温度唯一合法数据源，需配合基础台账与 15 组别名视图完成 100% 归口换热站。',
    usage: 'POST {base}/jumin/  Body: department_name=0&filter_level=0&isDownload=1（需 Cookie）',
    scheduleAndTable: '每小时整点 :00 自动采集 → fact_temp_hourly（自动滚动清理 >48 小时数据）',
    notes: '未入台账 3 户在阳面剔除并写入阴面督办；upload_time 超过 7 天或室温 <=5℃/>40℃ 均从均温与达标率剔除；室温表默认仅滚动保留最近 48 小时。',
  },
  {
    id: 'ep-hrz-ls-zb',
    group: 'history',
    method: 'POST',
    path: '/hrz_ls_zb/',
    auth: 'no_cookie',
    entity: '换热站 15 分钟历史序列与累计表底',
    scale: '按单站单次返回 ~93 条/天 × 361 列（5 年历史深库）',
    fields: 'create_time, f1..f5, f220(totF 累计流量t), f221(totJ 累计热量GJ), f222(flowJ 瞬时热), f253(IT1 电能累计kWh), f254(IU1 补水累计t)',
    dataDesc: '核心表底校准与历史补采数据源；整点线性插值计算表底差值，覆盖瞬时积分估算值。',
    usage: 'POST {base}/hrz_ls_zb/  Body: name=<站名>&start_date=YYYY-MM-DD HH:MM:SS&end_date=...&isdownload=1',
    scheduleAndTable: '每小时整点后 :05 受控并行校准（路线 B 主来源）→ fact_station_hourly',
    notes: '传 isdownload=1 时压力 f1/f4 已为 MPa；单站 5 天包体约 2.6MB，历史批量回溯建议 5 天分段 + 0.8s 间隔。',
  },
  {
    id: 'ep-sh-ls-zb',
    group: 'history',
    method: 'POST',
    path: '/sh_ls_zb/',
    auth: 'no_cookie',
    entity: '商业用户 5 分钟历史瞬时序列',
    scale: '单商户约 288 条/天（5 分钟 1 条）',
    fields: 'tmDate, fTempSupply, fTempReturn, fFlowF(供水流量t/h或kg/h), fFlowJ(瞬时热量GJ/h或MJ/h), ShunShiHuiShuiLiuLiang, GongShuiYaLi, HuiShuiYaLi',
    dataDesc: '实测发现的隐藏商业用户历史接口，可按时间段回溯计算任意历史小时的商业用热量积分。',
    usage: 'POST {base}/sh_ls_zb/  Body: name=<商户名>&start_date=YYYY-MM-DD HH:MM:SS&end_date=...&isdownload=1',
    scheduleAndTable: '手动 merchant_hourly_backfill 或全量历史补采 → fact_merchant_hourly (INTEGRAL_5M)',
    notes: '该接口不返回累计表底 totJ/totF，仅含瞬时流量与瞬时热量，适合梯形积分；同样需对蒸汽商户 ÷1000 折算。',
  },
  {
    id: 'ep-ry-dcls-szls',
    group: 'history',
    method: 'POST',
    path: '/ry_dcls_xx/get_history 与 /ry_szls_xx/get_history',
    auth: 'no_cookie',
    entity: '电厂（58点）与首站（54点）历史序列',
    scale: '电厂约 5 分钟 1 条（288 条/天）；首站约 10 分钟 1 条（144 条/天）',
    fields: 'tmDate, WENDU, YALI, LIULIANG, RELIANG；首站另含 PINLV, FUHE；电厂含 ZONGLIULIANG/ZONGRELIANG（实测为0）',
    dataDesc: '用于填补热源电厂与首站停机漏采期间的历史逐小时断面与梯形积分。',
    usage: 'POST  Body: start_date=MM/DD/YYYY&end_date=MM/DD/YYYY&station_name=<点位名>&dc_station_id(或sz_station_id)=<组号>',
    scheduleAndTable: '历史回溯脚本 backfill_smart_heating_history.py → fact_upstream_hourly',
    notes: '注意日期格式必须为 MM/DD/YYYY，传 YYYY-MM-DD 会报 HTTP 500；北海 dc_station_id=1，香海=2；yw2_dict 混水汇总点无对应历史表。',
  },
  {
    id: 'ep-sw-ls-export',
    group: 'history',
    method: 'POST',
    path: '/sw_ls_export/',
    auth: 'cookie',
    entity: '居民单户历史室温序列',
    scale: '按户请求，20 天约 200~250 条点位（T401 约每 2 小时上报 1 次）',
    fields: 'year(上报时间 YYYY-MM-DD HH:MM:SS), value(室温 ℃)',
    dataDesc: '按终端硬件编码逐户导出历史室温轨迹；实测 /sw_ls_zb/ 返回空数组 []，应统一使用 /sw_ls_export/。',
    usage: 'POST {base}/sw_ls_export/  Body: user_id=<temp_device_id>&start_date=YYYY-MM-DD HH:MM:SS&end_date=...（需 Cookie）',
    scheduleAndTable: '历史回溯脚本按 2,097 户慢速单线程补采 → fact_temp_hourly',
    notes: '需将最近一次有效上报沿用覆盖后续小时并在距业务小时 >7 天时自动置为失效，保持与实时 /jumin/ 相同鲜度口径。',
  },
  {
    id: 'ep-bb-shrb',
    group: 'daily_ref',
    method: 'POST',
    path: '/getall_bb_shrb/',
    auth: 'cookie',
    entity: '商业用户月度日报（按日表底与日单耗）',
    scale: '2 次请求返回全月所有商业用户每天的数据列',
    fields: 'id(merchant_id), Data0(上月末表底), Data1..Data31(每日累计表底或日单耗)',
    dataDesc: '商业用户日度财务与生产结算基准源：selectof3=0 为累计表底，selectof3=1 为日单位耗热。',
    usage: 'POST {base}/getall_bb_shrb/  Body: selectof1=0&selectof2=0&selectof3=0|1&options4=YYYYM&lastDay=月末日（需 Cookie）',
    scheduleAndTable: '每日 08:30 采集前一日（及整月补采）→ fact_merchant_daily',
    notes: '必须传 options4（如 202611）与 lastDay，否则源站 Flask 报 500（曾导致连通性探测误判 Cookie 失效）。',
  },
  {
    id: 'ep-sz-dc-nhpm',
    group: 'daily_ref',
    method: 'GET/POST',
    path: '/get_sz_data/1、/get_dc_data/1、/<xx>_nhpm/',
    auth: 'no_cookie',
    entity: '首站/电厂分组索引 与 9中心昨日能耗排名',
    scale: '3 类辅助参考接口',
    fields: 'get_sz/dc_data 返回点位及所属 id（用于历史接口分组入参）；<xx>_nhpm 返回 res1[{l, name_nhtj}] 与 yesterday_day',
    dataDesc: '用于获取电厂/首站所属 station_id 组号以及昨日各站万平能耗排名对照。',
    usage: 'POST /get_sz_data/1 (sz_selected=1)；POST /get_dc_data/1 (dc_selected=1)；GET /hl_nhpm/（hl/bg/sx/xlj/xgj/ch/df/zs/dg）',
    scheduleAndTable: '按需/历史回溯前置索引查询，不重复写入实时主库',
    notes: '日常 15 分钟采集已由 /gk_get_data/ 一次囊括首站与电厂实时值，无需重复请求。',
  },
  {
    id: 'ep-forbidden',
    group: 'forbidden',
    method: 'POST/GET',
    path: '/terminal_control/、/ewph_tj/、/wd_biao/、/fhrb/、/fhrjl_ssxx/',
    auth: 'forbidden',
    entity: '严禁触碰的控制接口 / 造假 / 失效页面',
    scale: '安全红线清单（禁止自动采集）',
    fields: 'control指令 / 阀门下发 / 虚增室温看板 / 500报错 / 5.35MB大页',
    dataDesc: '① /terminal_control/、/ewph_tj/ 会向现场 PLC/阀门下发控制指令；② /wd_biao/ 后端重复追加虚增 2,250 户；③ /fhrb/ 返回 500；④ /fhrjl_ssxx/ 单页 5.35MB。',
    usage: '全部严禁写入任何自动调度器、探测函数或回溯脚本',
    scheduleAndTable: '严格隔离（白名单旁路原则）',
    notes: '本平台仅限只读采集已核验的 JSON/导出接口，绝不改动源站库表及控制状态。',
  },
]

const filteredEndpoints = computed(() => {
  const kw = apiKeyword.value.trim().toLowerCase()
  return sourceEndpoints.filter((ep) => {
    if (apiGroupFilter.value !== 'all' && ep.group !== apiGroupFilter.value) return false
    if (apiAuthFilter.value !== 'all' && ep.auth !== apiAuthFilter.value) return false
    if (!kw) return true
    const text = `${ep.path} ${ep.entity} ${ep.fields} ${ep.dataDesc} ${ep.usage} ${ep.notes}`.toLowerCase()
    return text.includes(kw)
  })
})

const kindOptions = [
  { value: 'all', label: '全部指标' },
  { value: 'cumulative', label: '小时累计量' },
  { value: 'snapshot', label: '小时代表断面' },
  { value: 'derived', label: '衍生/聚合指标' },
]

function kindText(kind) {
  if (kind === 'cumulative') return '小时累计量'
  if (kind === 'snapshot') return '小时代表断面'
  return '衍生/聚合指标'
}

const entityCategories = [
  {
    key: 'station',
    icon: '🏭',
    title: '换热站（全站及一次网）',
    scale: '242 座物理站',
    hasHourly: true,
    brief: '含小时累计热量/流量/补水/电量，及一网供回温压、折算热指标等。',
    dictTables: 'dict_heating_station',
    sourceApis: '/hrz_ls_zb/（路线 B 唯一主采集源：整点表底差值 + 代表断面 + 坏表底积分兜底）',
    fact15mTable: '已停用实时拉取（不再写入 fact_station_15min）',
    factOutputTable: 'fact_station_hourly',
    summary: '换热站是全网核心核算单元（路线 B）。不再高频拉取实时接口，改为每小时整点后（默认 :05）受控并行拉取 /hrz_ls_zb/，直接按整点线性插值计算表底差值（METER_DIFF）并提取小时末代表断面，坏表底时自动用历史 f222 积分兜底。',
    keyNote: '严禁使用二次网各分区热量之和 Σe12 作为阳面换热站热量！阳面统一采用一次网表底 totJ (f221) 差值或一次网瞬时热量 e11 积分，Σe12 仅留作一二网热平衡失真审计。',
    metrics: [
      {
        id: 'st-hour-heat',
        kind: 'cumulative',
        name: '小时累计供热量',
        unit: 'GJ',
        field: 'hour_heat_gj / hour_heat_source',
        formula: '首选：totJ(H+1:00) - totJ(H:00)；兜底：trapezoidal_hour_integral(e11_clean)',
        steps: '① 表底校准任务拉取 /hrz_ls_zb/ 中的累计热量 f221 (totJ)，按前后点线性插值对齐到 H:00 与 H+1:00；② 校验差值在 [0, max_hourly_heat × 1.5] 内（单站极限负荷上限取 max(250, 面积 × 0.00045)）；③ 通过即锁定 hour_heat_source="METER_DIFF"，后续15分钟采集不会覆盖该表底结果。',
        example: '若 10:00 插值 totJ = 1200.0 GJ，11:00 插值 totJ = 1248.6 GJ，则 10时供热量 = 48.6 GJ（标记为“表”）。',
        fallback: '若尚未到校准时间、某整点表底缺失，或表底出现倒走(<-0.01)/跳变(>上限1.5倍)，自动使用本小时内 15 分钟 e11_clean（或 f222）梯形积分结果（INTEGRAL_15M / FALLBACK_INTEGRAL_15M）。',
        cleaning: '表底倒走/跳变会触发 METER_JUMP 阴面督办单；一二网热量偏差 |(Σe12 - e11)/e11| > 20% 时触发 HEAT_IMBALANCE 督办，但阳面仍坚持一网口径。',
        sourceTags: 'METER_DIFF（表底差值）｜ INTEGRAL_15M（15分钟积分）｜ FALLBACK_INTEGRAL_15M（跳变降级积分）',
      },
      {
        id: 'st-hour-flow',
        kind: 'cumulative',
        name: '小时累计一网流量',
        unit: 't',
        field: 'hour_flow_t / hour_flow_source',
        formula: '首选：totF(H+1:00) - totF(H:00)；兜底：trapezoidal_hour_integral(e1_clean)',
        steps: '① 优先取 /hrz_ls_zb/ 中 f220 (totF) 的整点插值表底差值，上限放宽至 max_hourly_heat × 12；② 缺失或异常时，对本小时内 :00/:15/:30/:45 的一次网瞬时流量 e1_clean 执行梯形积分并折算至 3600 秒。',
        example: '10:00~10:45 四个时刻 e1_clean 分别为 120, 122, 124, 122 t/h，覆盖 2700 秒积分面积为 91.5 t，外推整小时 = 91.5 × (3600/2700) = 122.0 t。',
        fallback: '表底未取到或校验不通过时回退为 15 分钟 e1_clean 梯形积分（INTEGRAL_15M）。',
        cleaning: '若换热站通讯临时离线（online=false），先沿用最近 6 小时内最后一次在线有效 e1_clean 平滑估值再积分；长期无历史有效值则置空。',
        sourceTags: 'METER_DIFF ｜ INTEGRAL_15M',
      },
      {
        id: 'st-hour-water',
        kind: 'cumulative',
        name: '小时累计补水量',
        unit: 't',
        field: 'hour_water_t / hour_water_source',
        formula: '首选：f254(H+1:00) - f254(H:00)；兜底：trapezoidal_hour_integral(e14_clean)',
        steps: '① 表底校准阶段从 /hrz_ls_zb/ 提取 f254（补水累计表底）做整点线性插值差值（单站小时上限 200 t/h）；② 实时阶段对 e14_clean（自来水瞬时补水）做 15 分钟梯形积分。',
        example: '10:00 补水表底 512.4 t，11:00 补水表底 513.9 t，小时补水量 = 1.5 t。',
        fallback: '表底缺失时保留 15 分钟 e14_clean 梯形积分（INTEGRAL_15M）。',
        cleaning: '单站自来水瞬时补水 e14_raw < 0 或 > 100 t/h 判为坏表满量程死值（如 500/1545.2 t/h），立即屏蔽并回退前序有效值（无前值则置空），同时派发 SENSOR_OUT_OF_RANGE 督办。',
        sourceTags: 'METER_DIFF ｜ INTEGRAL_15M',
      },
      {
        id: 'st-hour-elec',
        kind: 'cumulative',
        name: '小时累计耗电量',
        unit: 'kWh',
        field: 'hour_elec_kwh / hour_elec_source',
        formula: 'f253(H+1:00) - f253(H:00)',
        steps: '仅来源于 /hrz_ls_zb/ 中的电能累计表底 f253。经整点线性插值后作差（单站小时校验上限 5000 kWh）。',
        example: '10:00 电能表底 18240.0 kWh，11:00 为 18312.5 kWh，小时耗电 = 72.5 kWh。',
        fallback: '由于实时接口不返回瞬时功率，表底缺失或校验失败时 hour_elec_kwh 保持为空，hour_elec_source="NONE"。',
        cleaning: '校验 delta < -0.01 或 > 5000 × 1.5 时丢弃异常差值。',
        sourceTags: 'METER_DIFF ｜ NONE',
      },
      {
        id: 'st-instant-snapshot',
        kind: 'snapshot',
        name: '小时代表断面（供回温 / 压力 / 瞬时流量 / 瞬时热量 / 水位）',
        unit: '℃ / MPa / t/h / GJ/h / mm',
        field: 'e1_clean, e3_clean, e4_clean, e7_clean, e8_clean, e11_clean, e14_clean, e16_raw',
        formula: '取本小时内最新一次（sample_bucket 最大）经过五重清洗后的 15 分钟采样断面',
        steps: '每次采集落入 fact_station_15min 后立即按 biz_hour 汇总至 fact_station_hourly：取本小时最后一条清洗断面作为该小时代表瞬时值（若未达整点结束则随采集滚动更新，走完即定格在 :45 断面）。其中“香炉礁”站水位 e16 若顶层缺失会按规范从 Nx[0].data.e16 提取。',
        example: '10:00、10:15、10:30、10:45 均已采集，则 10时断面展示 10:45 清洗后的供温 e3_clean、回温 e4_clean 等值。',
        fallback: '若本小时内实时接口漏采但执行过表底校准，则从 /hrz_ls_zb/ 本小时末尾点 f1~f5、f222 补全代表断面。',
        cleaning: '① 离线：online=false 时回退 6 小时内最近在线值（标记 *）；② 越限：水温 <=0℃ 或 >150℃，压力 <0 或 >2.5MPa 屏蔽并回退；③ 倒挂：e1>1 且 供温<=回温 时回退前序正常温差。',
        sourceTags: 'REAL ｜ INTERP_TEMP_OFFLINE ｜ MASKED_PREV_HOLD ｜ OFFLINE_PERMANENT',
      },
      {
        id: 'st-heat-index',
        kind: 'derived',
        name: '单站实时折算热指标',
        unit: 'W/㎡',
        field: 'heat_index_wm2',
        formula: 'e11 × 277777.78 / covered_area',
        steps: '单位换算关系：1 GJ/h = 10⁹ J ÷ 3600 s = 277,777.78 W。将单站当前小时代表一网瞬时热量 e11（GJ/h）换算为瓦（W），再除以该站在 dict_heating_station 中的供热面积 covered_area（㎡）。',
        example: '某站面积 100,000 ㎡，e11 = 14.4 GJ/h，则热指标 = 14.4 × 277777.78 / 100000 = 40.0 W/㎡。',
        fallback: '若该站尚属“缺失面积站”（covered_area 为空或 0）或 e11 为空，则返回空值展示“-”。',
        cleaning: '使用净化后的 e11_clean 计算，避免坏表或离线 0 值拉偏。',
        sourceTags: '实时衍生计算（前端“净化精算/原始对照”随 mode 切换）',
      },
      {
        id: 'st-room-temp',
        kind: 'derived',
        name: '单站平均室温 & 室温达标率',
        unit: '℃ / %',
        field: 'avg_room_temp / temp_pass_rate_pct',
        formula: 'avg_room_temp = AVG(temp_clean)；达标率 = COUNT(temp_clean ≥ 18.0) / COUNT(有效终端) × 100%',
        steps: '筛选本小时 fact_temp_hourly 中归属该 station_id、且同时满足 is_registered=TRUE 和 is_online_valid=TRUE 的终端，对 temp_clean 求算术平均及 ≥18℃ 达标占比。',
        example: '某站下有 12 户有效测温终端（另有 1 户掉线超 7 天已剔除），11 户 ≥18℃，均温 21.4℃，达标率 = 11/12 × 100% = 91.7%。',
        fallback: '该站无有效归口测温终端时返回空（-）。',
        cleaning: '未入台账终端、掉线超 7 天终端、≤5℃ 或 >40℃ 极端值均已在清洗层将 is_online_valid 置为 FALSE，不参与计算。',
        sourceTags: '基于 fact_temp_hourly 有效样本实时聚合',
      },
    ],
  },
  {
    key: 'upstream',
    icon: '⚡',
    title: '上游热源 / 首站 / 网口',
    scale: '82 核心监测点',
    hasHourly: true,
    brief: '覆盖电厂、首站、网口五大字典区，区分蒸汽/高温点与热水点阈值。',
    dictTables: 'dict_upstream_point',
    sourceApis: '/gk_get_data/（五大内存字典：dc_dict / sz_dict / yw2_dict / yw_dict / sh_dict）',
    fact15mTable: 'fact_upstream_15min',
    factOutputTable: 'fact_upstream_hourly',
    summary: '上游工况点位无独立历史累计表底分页接口，因此每 15 分钟从 /gk_get_data/ 抓取一次瞬时温度、压力、流量、热量，在小时层同时保留最新瞬时断面与 15 分钟梯形积分累计量。',
    keyNote: '系统会自动识别蒸汽/烟气/高温汽温测点（名称含主汽、进汽、抽汽、排汽、蒸汽、调门、母管，或 dc_dict 非水类点），将其高温阈值放宽至 600℃、高压上限放宽至 15 MPa，防止把电厂高温蒸汽误判为传感器故障。',
    metrics: [
      {
        id: 'up-hour-heat',
        kind: 'cumulative',
        name: '小时供热量（积分）',
        unit: 'GJ',
        field: 'hour_heat_gj',
        formula: 'trapezoidal_hour_integral([(t_i, heat_clean_i)])',
        steps: '汇总该测点在当前 biz_hour 内最多 4 次 15 分钟采样（:00/:15/:30/:45）的清洗后瞬时热量 heat_clean（RELIANG），计算相邻采样梯形面积之和，并按覆盖总秒数等比归一化到标准 1 小时（3600 秒）。',
        example: '仅采集到 10:00 (210 GJ/h) 与 10:15 (230 GJ/h) 两点，平均负荷 220 GJ/h × 0.25h = 55 GJ，归一化到 1 小时 = 55 × (3600/900) = 220.0 GJ。',
        fallback: '若本小时仅采到 1 个有效点，直接按 heat_clean × 1.0h 估算；全部为空则返回 None。',
        cleaning: '上游 RELIANG 若为“-”或空串经 to_float 安全转为 None 不参与积分。',
        sourceTags: 'INTEGRAL_15M（15分钟梯形积分）',
      },
      {
        id: 'up-hour-flow',
        kind: 'cumulative',
        name: '小时累计流量（积分）',
        unit: 't',
        field: 'hour_flow_t',
        formula: 'trapezoidal_hour_integral([(t_i, flow_clean_i)])',
        steps: '与小时供热量一致，基于本小时内 15 分钟采样的瞬时流量 flow_clean（LIULIANG）执行时间加权梯形面积积分并折算到 1 小时。',
        example: '4 个采样点流量均值约为 1850 t/h，覆盖完整时段则小时流量约 1850.0 t。',
        fallback: '单点采样时直接取 flow_clean × 1.0h。',
        cleaning: '停运备机若流量 <= 1.0 且温度为 0℃，视为正常停机而非断路故障，不触发温度越限误报。',
        sourceTags: 'INTEGRAL_15M（15分钟梯形积分）',
      },
      {
        id: 'up-snapshot',
        kind: 'snapshot',
        name: '小时代表温度 / 压力 / 瞬时流量 / 瞬时热量',
        unit: '℃ / MPa / t/h / GJ/h',
        field: 'temp_clean, pressure_clean, flow_clean, heat_clean',
        formula: '取本小时内最后一次采样（sample_bucket DESC 第 1 条）的清洗断面',
        steps: '按 (data_zone, source_name) 分组并按 sample_bucket 升序排列，取 items[-1] 的 temp/pressure/flow/heat 原始值与净化值写入 fact_upstream_hourly，同时关联 dict_upstream_point 标记是否属于《工况一览》82 个核心点（is_core_gk）。',
        example: '某网口在 14:45 的温度清洗值为 86.2℃，则 14时断面温度展示 86.2℃。',
        fallback: '温度或压力触发传感器越限时，自动从最近 6 小时前序正常记录回退并标注 *（MASKED_PREV_HOLD）。',
        cleaning: '① 水温 >150℃ 或 <-10℃ 或带流量<=0℃ 判越限；汽温 >=600℃ 或 <-10℃ 或带流量<=0℃ 判越限；② 水压 [0, 2.5] MPa、汽压 [0, 15.0] MPa 外判越限；③ 源时间 source_time 滞后采集时间 > 2 小时记通讯滞后（COMM_OFFLINE）。',
        sourceTags: 'REAL ｜ MASKED_PREV_HOLD',
      },
    ],
  },
  {
    key: 'zone',
    icon: '🔀',
    title: '二次网供热分区（已停用实时采集）',
    scale: '580 个分区（仅保留静态字典台账，不再参与采集与统计）',
    hasHourly: false,
    brief: '按业务决策已停用二次分区实时采集与下钻展示，仅保留 dict_secondary_zone 静态台账。',
    dictTables: 'dict_secondary_zone',
    sourceApis: '已停用采集',
    fact15mTable: '已停用（每轮 2 小时滚动清理历史残留）',
    factOutputTable: '已停用（仅保留静态台账）',
    summary: '由于阳面核心能耗核算严格以一次网为准、二次分区不参与任何上层统计与汇总，系统已彻底停用二次分区的采集落库与前端下钻子表，以降低数据库写入压力。',
    keyNote: '台账中已标识为“常离线”的分区（dict_secondary_zone.is_online = FALSE）在小时层保持 OFFLINE_PERMANENT，不做虚假插值；所有分区的二次网热量 e12 仅用于与站一次网 e11 做热平衡审计比对，严禁向上汇总。',
    metrics: [
      {
        id: 'zn-snapshot',
        kind: 'snapshot',
        name: '二网瞬时流量 / 供回水温度 / 供回水压力 / 瞬时补水',
        unit: 't/h / ℃ / MPa / t/h',
        field: 'e2_clean, e5_clean, e6_clean, e9_clean, e10_clean, e15_clean',
        formula: 'SELECT DISTINCT ON (secondary_zone_id) ... ORDER BY secondary_zone_id, sample_bucket DESC',
        steps: '从当前 biz_hour 所属的 fact_zone_15min 记录中，按采样时间倒序取最新一条清洗后记录作为该分区本小时代表断面，并统计 sample_count 采样次数。',
        example: '某站“低区”在 16:00~16:45 共采集 4 次，小时断面展示 16:45 清洗后的二网供温 e5_clean=46.5℃、回温 e6_clean=39.1℃。',
        fallback: '若在线分区发生物理温差倒挂，优先回退 6 小时内最近一次有效断面（MASKED_PREV_HOLD）。',
        cleaning: '① 物理倒挂1：当二网流量 e2 > 1.0 t/h 且 e5 <= e6 时，回退 e5/e6 并派发 TEMP_INVERSION；② 物理倒挂2（违反热力学第二定律）：当一网供温 e3 > 10℃ 且二网供温 e5 > e3 + 0.5℃ 时，回退 e5 并派发 TEMP_INVERSION。',
        sourceTags: 'REAL ｜ MASKED_PREV_HOLD ｜ OFFLINE_PERMANENT',
      },
      {
        id: 'zn-e12-audit',
        kind: 'derived',
        name: '二网热量审计比对项（e12_audit 与热平衡偏差）',
        unit: 'GJ/h / %',
        field: 'e12_raw（分区） / heat_balance_diff_pct（站级）',
        formula: 'heat_balance_diff_pct = (Σe12_raw - e11_raw) / e11_raw × 100%',
        steps: '将同一换热站下所有分区原始 e12_raw 求和得到 Σe12，在站级计算相对一次网热量 e11_raw 的偏差百分比，用于排查二网热量表失真或掉零问题。',
        example: '若某站一网 e11=10.0 GJ/h，二网两分区 Σe12=14.2 GJ/h，则偏差 = +42.0%（超 ±20% 触发 HEAT_IMBALANCE 督办）。',
        fallback: '当 e11_raw <= 0.05 且站点在线但 Σe12 > 0.2 时，直接针对一网表计掉零发起督办。',
        cleaning: '阳面主报表严禁引用 e12 参与任何热耗结算，仅在站下钻子表与阴面督办单展示。',
        sourceTags: '仅阴面/下钻审计参考（RAW）',
      },
    ],
  },
  {
    key: 'temp_device',
    icon: '🌡️',
    title: '居民室温测温终端',
    scale: '2,097 户入账终端（含 15 组站名别名归一化）',
    hasHourly: true,
    brief: '整点抓取居民户内温度，剔除未入账新增户、长离线僵尸户与超限异常户。',
    dictTables: 'dict_temp_device + v_temp_station_alias_map',
    sourceApis: '/jumin/（需有效 Session Cookie，整点 :00 自动采集一次）',
    fact15mTable: '无（按小时整点直采，不进 15 分钟表）',
    factOutputTable: 'fact_temp_hourly',
    summary: '居民室温变化平缓且 /jumin/ 接口需携带 Cookie，系统在每小时整点 :00 触发（或手动触发）全量拉取一次。通过标准台账与 15 组站名别名视图实现 100% 归口到 242 座换热站。',
    keyNote: '源站若在标准 2,097 户之外临时新增终端（例如多出 3 户），阳面会严格标记 is_registered=FALSE 并从均温与达标率中剔除，同时在阴面派发 SOFTWARE_DEFECT 提醒核实入账。',
    metrics: [
      {
        id: 'tm-clean',
        kind: 'snapshot',
        name: '单户小时清洗室温',
        unit: '℃',
        field: 'temp_clean / is_online_valid',
        formula: '准入条件：is_registered == TRUE AND (采集时间 - upload_time ≤ 7天) AND (5.0 < wd1 ≤ 40.0)',
        steps: '① 用终端 id 查 dict_temp_device，未命中则 is_registered=FALSE；② 检查 upload_time 距当前采集是否超过 7×86400 秒；③ 检查原始温度 wd1 是否在 (5.0, 40.0] ℃ 区间内。三项全部通过才保留 temp_clean 并置 is_online_valid=TRUE。',
        example: '终端 A 昨晚上传 21.6℃，在 2,097 户台账内 → temp_clean=21.6，有效；终端 B 上传时间是 12 天前 → is_online_valid=FALSE，不计入均温。',
        fallback: '异常户的 temp_clean 置为 NULL，不做插值伪造，但原始 temp_raw 与备注 remark_snapshot 完整留痕供下钻排查。',
        cleaning: '① 未入账终端 → 归属高校软件问题(SOFTWARE_DEFECT)；② 掉线>7天 → 僵尸户剔除(COMM_OFFLINE)；③ 室温<=5℃或>40℃或空 → 传感器超限剔除(SENSOR_OUT_OF_RANGE)。',
        sourceTags: 'is_online_valid=TRUE（有效样本）｜ FALSE（已剔除留痕）',
      },
      {
        id: 'tm-dist',
        kind: 'derived',
        name: '全网 / 分站室温分布与舒适率',
        unit: '户 / %',
        field: 'avg_room_temp / temp_pass_rate_pct / temp_comfort_rate_pct / room_dist',
        formula: '均温 = SUM(有效temp_clean)/N；达标率 = Count(≥18℃)/N；舒适率 = Count(20≤T≤25℃)/N',
        steps: '基于当前 biz_hour 中所有有效样本（is_registered=TRUE 且 is_online_valid=TRUE），按温度落入 <18℃、18~20℃、20~25℃、>25℃ 四个区间计数，并计算算术平均室温与达标/舒适比例。',
        example: '全网有效样本 1,950 户，其中 ≥18℃ 共 1,890 户（96.9%），20~25℃ 共 1,560 户（80.0%）。',
        fallback: '若尚未配置有效 Cookie 导致本小时未采 /jumin/，前端展示“暂无样本 / -”。',
        cleaning: '严格排除未入账 3 户与僵尸/坏表户，防止 -199℃ 或长期未更新的停供户拉低均温。',
        sourceTags: '基于 fact_temp_hourly 实时聚合',
      },
    ],
  },
  {
    key: 'group',
    icon: '🏛️',
    title: '聚合管理主体（中心 / 大网 / 主干 / 支线 / 全网）',
    scale: '全网、9大中心、9大rdfz热源网、15条主干网、41条支线网',
    hasHourly: true,
    brief: '由下属换热站与归口测温户按统一口径（面积累加、流量加权温差）实时聚合。',
    dictTables: 'dict_service_center / dict_main_network / dict_branch_network / dict_heating_station',
    sourceApis: '无独立源接口（基于本站与测温事实表按归属外键动态汇总）',
    fact15mTable: '继承 fact_station_15min 清洗结果',
    factOutputTable: '由 fact_station_hourly 与 fact_temp_hourly 实时聚合产出',
    summary: '所有宏观管理主体（全网汇总、9大服务中心、9大热源大网 rdfz、15条主干网、41条支线网）均共用后端 _compute_weighted_temp_and_kpis() 统一精算聚合器，确保任意层级、任意页面的口径 100% 一致。',
    keyNote: '供/回水平均温度绝不采用简单算术平均（否则小流量停运站会把全网均温拉歪），而是严格按各站“一网瞬时流量 e1”进行流量加权平均！',
    metrics: [
      {
        id: 'gp-heat-water-elec',
        kind: 'cumulative',
        name: '分组小时累计供热 / 补水 / 耗电',
        unit: 'GJ / t / kWh',
        field: 'hour_heat_gj / hour_water_t / hour_elec_kwh',
        formula: 'SUM(组内各站 hour_heat_gj)；补水优先取 hour_water_t，缺失时回退取 e14_clean',
        steps: '按 center_id / rdfz / main_network_id / branch_network_id 将 242 座站的小时累计耗量直接求和。若某个站该小时尚无表底或积分记录，不计入累加。',
        example: '华乐中心共管辖 28 座站，将其本小时 hour_heat_gj 相加即得华乐中心小时供热量。',
        fallback: '若整个分组尚无任何站的补水表底积分 hour_water_t，单站层自动回退取代表瞬时补水 e14_clean 参与汇总。',
        cleaning: '底层已过滤坏表与倒挂，保证上层聚合不被单站极值污染。',
        sourceTags: '基于底层 METER_DIFF / INTEGRAL_15M 加总',
      },
      {
        id: 'gp-area-intensity',
        kind: 'derived',
        name: '分组在网面积、折算热指标 & 万平耗热/补水',
        unit: '万㎡ / W/㎡ / GJ/万㎡·h / t/万㎡',
        field: 'covered_area_wan / heat_index_wm2 / heat_per_wan_gj / water_per_wan_t',
        formula: '热指标 = SUM(e11) × 277777.78 / SUM(covered_area)；万平耗热 = SUM(hour_heat_gj) / (SUM(area)/10000)',
        steps: '① 统计分组内有面积站的 covered_area 之和并记录缺失面积站数 missing_area_count；② 折算热指标反映当前瞬时供热强度（W/㎡）；③ 万平耗热反映本小时实际单位面积累计耗热量（GJ/万㎡·h）。',
        example: '某中心面积 500 万㎡，本小时耗热 750 GJ、瞬时负荷 720 GJ/h → 万平耗热 = 750/500 = 1.50 GJ/万㎡·h，热指标 = 720×277777.78/5000000 = 40.0 W/㎡。',
        fallback: '若组内总面积为 0，热指标与万平指标返回 None。',
        cleaning: '32 座待补录面积的站暂时按 0 计入面积并在界面显式提示“xx站待补面积”，可在台账中心在线补录。',
        sourceTags: '实时聚合衍生计算',
      },
      {
        id: 'gp-weighted-temp',
        kind: 'derived',
        name: '流量加权平均供/回温与温差',
        unit: '℃',
        field: 'avg_sup_temp / avg_ret_temp / avg_temp_diff',
        formula: 'T_供 = Σ(e3_i × e1_i) / Σe1_i；T_回 = Σ(e4_i × e1_i) / Σe1_i（仅统计 e1_i > 0 的站）',
        steps: '仅纳入一网瞬时流量 e1 > 0 t/h 且温度非空的站点，以各自流量 e1 作为权重计算一次网供水加权均温与回水加权均温，两者相减即得加权平均温差。',
        example: 'A 站流量 100 t/h、供温 80℃；B 站流量 10 t/h、供温 50℃ → 流量加权供温 = (100×80 + 10×50)/110 = 77.27℃（而非简单平均 65℃）。',
        fallback: '若组内所有站流量均 <= 0 或缺失，返回 None。',
        cleaning: '回压 avg_ret_pressure 采用非空 e8 的算术平均值（单位 MPa）。',
        sourceTags: '流量加权物理聚合',
      },
    ],
  },
  {
    key: 'merchant',
    icon: '🏬',
    title: '商业用户 / 商户（逐小时 + 日度双轨）',
    scale: '464 户标准商户（挂接在 41 条支线网下）',
    hasHourly: true,
    brief: '每 15 分钟批量抓取全网瞬时热量/流量做梯形积分产出每小时值，并可按 /sh_ls_zb/ 5 分钟历史补采。',
    dictTables: 'dict_merchant',
    sourceApis: '/get_sh_data/0（免Cookie，断流降级/get_sh_data/2..16）+ /sh_ls_zb/（5分钟历史）+ /getall_bb_shrb/（日表底）',
    fact15mTable: 'fact_merchant_15min',
    factOutputTable: 'fact_merchant_hourly（小时精算） + fact_merchant_daily（日结表底）',
    summary: '实测源站发现：POST /get_sh_data/0 可免 Cookie 一次拉回全部商户瞬时运行参数（含瞬时热量 shunshireliang 与流量 gongshuiliuliang），/sh_ls_zb/ 提供约 5 分钟一条的历史瞬时序列（无累计表底），两者结合梯形积分产出逐小时供热量与流量；次日 08:30 再与 /getall_bb_shrb/ 日表底作差核对。',
    keyNote: '源站 /get_sh_data/ 返回 468 条记录，系统会自动将别名“国际航运中心大厦”归一化到台账“航运中心大厦”，并将多出的 4 户测试占位符（测试商户/测试商户1/商1户/商户测试）在阳面标记 is_registered=FALSE 剔除、写入阴面督办提醒。',
    metrics: [
      {
        id: 'mc-hour-heat',
        kind: 'cumulative',
        name: '商业户小时供热量（积分）',
        unit: 'GJ',
        field: 'hour_heat_gj / hour_heat_source',
        formula: 'trapezoidal_hour_integral([(t_i, heat_clean_i)])；历史补采使用 /sh_ls_zb/ 5 分钟 fFlowJ 梯形积分',
        steps: '① 每 15 分钟从 /get_sh_data/0（大包被 NAT 截断时自动降级按主干网 2..16 分片）抓取瞬时热量 shunshireliang (GJ/h)；② 经离线/越限清洗后存入 fact_merchant_15min；③ 按时间加权梯形面积积分并折算至 3600 秒写入 fact_merchant_hourly。',
        example: '1896酒店在 22:00~22:45 瞬时热量稳定在 0.68~0.70 GJ/h，梯形积分折算整小时约 0.69 GJ。',
        fallback: '若当小时实时采样缺失，可通过 /sh_ls_zb/ 拉取 5 分钟 fFlowJ 序列补算（hour_heat_source="INTEGRAL_5M"）。',
        cleaning: '① 4 户测试商户在阳面剔除并写入 SOFTWARE_DEFECT；② xinhaoqiangdu != 0 判离线并回退 6 小时前序有效值；③ 蒸汽商户（rdry="蒸汽"）接口原值为 kg/h 与 MJ/h，入库自动 ÷1000 折算为 t/h 与 GJ/h 并屏蔽 -200℃ 未接回温；④ 折算瞬时热量 <0 或 >500 GJ/h 屏蔽回退。',
        sourceTags: 'INTEGRAL_15M（15分钟实时积分）｜ INTEGRAL_5M（历史5分钟补采）',
      },
      {
        id: 'mc-hour-flow',
        kind: 'cumulative',
        name: '商业户小时供水流量（积分）',
        unit: 't',
        field: 'hour_flow_t / hour_flow_source',
        formula: 'trapezoidal_hour_integral([(t_i, flow_clean_i)])',
        steps: '汇总本小时内各采样时刻的清洗后一网供水流量 flow_clean（gongshuiliuliang 或历史 fFlowF），执行梯形积分并折算到 1 小时。',
        example: '某商户供水流量约 4.1 t/h，覆盖完整小时后 hour_flow_t ≈ 4.10 t。',
        fallback: '未入台账测试户不计算小时流量（置空）。',
        cleaning: '与热量共用离线平滑机制；带流量 > 0.5 t/h 时若出现供温 <= 回温，触发物理倒挂 TEMP_INVERSION 督办。',
        sourceTags: 'INTEGRAL_15M ｜ INTEGRAL_5M',
      },
      {
        id: 'mc-snapshot',
        kind: 'snapshot',
        name: '商业户小时代表断面（供回温 / 压力 / 阀门开度 / 瞬时热量）',
        unit: '℃ / MPa / % / GJ/h',
        field: 'flow_clean, temp_sup_clean, temp_ret_clean, pres_sup_clean, pres_ret_clean, heat_clean, valve_open, valve_set',
        formula: '取本小时内最新一次（sample_bucket DESC）经过清洗的商业户断面',
        steps: '从 fact_merchant_15min 按 source_name 聚合并取最后一条有效采样写入 fact_merchant_hourly，同时保留阀门开度 valve_open 与设定开度 valve_set 供运行调控参考。',
        example: '1896酒店 22 时断面展示供温 76.2℃、回温 34.9℃、供流 4.1 t/h、瞬时热量 0.7 GJ/h、阀门开度 93%/80%。',
        fallback: '离线时回退 6 小时内最后一次 xinhaoqiangdu == "0" 的有效断面（INTERP_TEMP_OFFLINE）。',
        cleaning: '水温 <-10℃ 或 >150℃（或带流量 <=0℃）、压力 <0 或 >2.5MPa 均屏蔽并回退前序有效值。',
        sourceTags: 'REAL ｜ INTERP_TEMP_OFFLINE ｜ MASKED_PREV_HOLD ｜ OFFLINE_PERMANENT',
      },
      {
        id: 'mc-daily-cons',
        kind: 'cumulative',
        name: '商业户日结算耗热量（次日日结表底口径）',
        unit: 'GJ / 日',
        field: 'daily_consumption / daily_unit_heat',
        formula: 'daily_consumption = tot[Data{D}] - tot[Data{D-1}]（要求 Data{D} ≥ Data{D-1}）；1号跨月对比 Data0',
        steps: '由于 /sh_ls_zb/ 无累计表底，每日 08:30 仍保留调用 /getall_bb_shrb/ 获取月度日报中按日记录的累计表底与日单耗，与 24 小时积分结果互相校核。',
        example: '15 日累计表底为 840.5 GJ，14 日为 828.0 GJ，则 15 日耗热量 = 12.5 GJ。',
        fallback: '若目标日表底小于前一日（换表/清零）或为空，则 daily_consumption 置为 None，保留 raw_payload。',
        cleaning: '仅保留匹配 dict_merchant 的 464 户标准商户；未配置有效 Cookie 时跳过日结采集。',
        sourceTags: '日度表底作差（fact_merchant_daily）',
      },
    ],
  },
]

const activeCategory = computed(() =>
  entityCategories.find((c) => c.key === selectedKey.value) || entityCategories[0]
)

const filteredMetrics = computed(() => {
  const list = activeCategory.value?.metrics || []
  const kw = metricKeyword.value.trim().toLowerCase()
  return list.filter((m) => {
    if (kindFilter.value !== 'all' && m.kind !== kindFilter.value) return false
    if (!kw) return true
    const haystack = `${m.name} ${m.field} ${m.formula} ${m.steps} ${m.cleaning}`.toLowerCase()
    return haystack.includes(kw)
  })
})

function selectCategory(key) {
  selectedKey.value = key
  kindFilter.value = 'all'
}

// 交互试算器状态
const calc = reactive({
  jPrevLeft: 1196.0,
  jPrevRight: 1202.0,
  jNextLeft: 1244.0,
  jNextRight: 1250.0,
  s0: 46.0,
  s15: 48.0,
  s30: 50.0,
  s45: 48.0,
})

function resetCalculator() {
  calc.jPrevLeft = 1196.0
  calc.jPrevRight = 1202.0
  calc.jNextLeft = 1244.0
  calc.jNextRight = 1250.0
  calc.s0 = 46.0
  calc.s15 = 48.0
  calc.s30 = 50.0
  calc.s45 = 48.0
}

const calcResult = computed(() => {
  const ratio = 10 / 15 // 目标整点在 09:50 和 10:05 之间占 10/15
  const i10 = Number(calc.jPrevLeft) + ratio * (Number(calc.jPrevRight) - Number(calc.jPrevLeft))
  const i11 = Number(calc.jNextLeft) + ratio * (Number(calc.jNextRight) - Number(calc.jNextLeft))
  const meterDiff = i11 - i10

  const pts = [calc.s0, calc.s15, calc.s30, calc.s45].map((v) => Math.max(0, Number(v) || 0))
  let area = 0
  for (let i = 0; i < pts.length - 1; i += 1) {
    area += ((pts[i] + pts[i + 1]) / 2) * 0.25 // 15 分钟 = 0.25 小时
  }
  const est = area * (3600 / 2700) // 3段共45分钟(2700秒)，等比外推到整1小时

  return {
    interp10: i10.toFixed(2),
    interp11: i11.toFixed(2),
    meterDiff: meterDiff.toFixed(2),
    rawArea: area.toFixed(2),
    integralEst: est.toFixed(2),
  }
})
</script>

<style scoped>
.shp-algo-view {
  min-height: 100vh;
  background: #f1f5f9;
  color: #0f172a;
}

.shp-main {
  max-width: 1320px;
  margin: 0 auto;
  padding: 20px 24px 48px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.card.elevated {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
}

.topbar {
  padding: 20px 24px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.title-row h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
}

.role-badge {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  padding: 3px 10px;
  font-size: 12px;
  font-weight: 600;
}

.subtitle {
  margin: 8px 0 0;
  color: #475569;
  font-size: 13.5px;
  line-height: 1.6;
}

.topbar-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.btn {
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s ease;
}

.btn-xs {
  padding: 5px 10px;
  font-size: 12px;
}

.btn.primary {
  background: #2563eb;
  color: #ffffff;
}

.btn.primary:hover {
  background: #1d4ed8;
}

.btn.secondary {
  background: #f8fafc;
  border-color: #cbd5e1;
  color: #1e293b;
}

.btn.secondary:hover {
  background: #e2e8f0;
}

.entity-selector-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.entity-card {
  text-align: left;
  padding: 16px 18px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: all 0.15s ease;
  border: 1.5px solid #e2e8f0;
}

.entity-card:hover {
  border-color: #93c5fd;
  transform: translateY(-1px);
}

.entity-card.active {
  border-color: #2563eb;
  background: linear-gradient(135deg, #eff6ff 0%, #ffffff 100%);
  box-shadow: 0 6px 20px rgba(37, 99, 235, 0.12);
}

.entity-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.entity-icon {
  font-size: 22px;
}

.entity-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
}

.badge-hourly {
  background: #dcfce7;
  color: #166534;
}

.badge-daily {
  background: #fef3c7;
  color: #92400e;
}

.entity-title {
  font-size: 15.5px;
  color: #0f172a;
}

.entity-scale {
  font-size: 12px;
  font-weight: 600;
  color: #2563eb;
}

.entity-brief {
  margin: 0;
  font-size: 12.5px;
  color: #64748b;
  line-height: 1.5;
}

.detail-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pipeline-card,
.metrics-card,
.explainer-card {
  padding: 20px 24px;
}

.pipeline-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}

.pipeline-head h3,
.section-head h3 {
  margin: 0;
  font-size: 17px;
  color: #0f172a;
}

.pipeline-summary {
  margin: 6px 0 0;
  font-size: 13.5px;
  color: #475569;
  line-height: 1.6;
}

.ctrl-input {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 7px 12px;
  font-size: 13px;
  min-width: 220px;
  background: #fff;
}

.meta-strip {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.meta-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  font-size: 11.5px;
  color: #64748b;
}

.meta-code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  color: #1e293b;
  word-break: break-word;
}

.note-callout {
  margin-top: 14px;
  padding: 10px 14px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  font-size: 13px;
  color: #78350f;
  line-height: 1.6;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.subtitle-inline {
  font-size: 12.5px;
  color: #64748b;
}

.kind-pills {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.kind-pill {
  padding: 5px 12px;
  border-radius: 999px;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.kind-pill.active {
  background: #1d4ed8;
  border-color: #1d4ed8;
  color: #ffffff;
}

.metric-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.metric-item {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 16px 18px;
  background: #fcfdff;
}

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding-bottom: 10px;
  border-bottom: 1px dashed #e2e8f0;
}

.metric-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.metric-name {
  margin: 0;
  font-size: 15.5px;
  font-weight: 700;
}

.metric-unit {
  font-size: 12px;
  color: #64748b;
  background: #f1f5f9;
  padding: 2px 8px;
  border-radius: 6px;
}

.kind-tag {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
}

.kind-cumulative {
  background: #dbeafe;
  color: #1e40af;
}

.kind-snapshot {
  background: #e0e7ff;
  color: #3730a3;
}

.kind-derived {
  background: #fce7f3;
  color: #9d174d;
}

.metric-field {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  color: #0f766e;
  background: #f0fdfa;
  border: 1px solid #ccfbf1;
  padding: 3px 8px;
  border-radius: 6px;
}

.metric-body-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  gap: 14px;
}

.formula-box {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 14px;
}

.box-title {
  font-size: 12px;
  font-weight: 700;
  color: #334155;
  margin-bottom: 6px;
}

.formula-expr {
  margin: 0 0 8px;
  padding: 8px 10px;
  background: #0f172a;
  color: #e2e8f0;
  border-radius: 6px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12.5px;
  line-height: 1.5;
  word-break: break-word;
}

.formula-steps {
  margin: 0;
  font-size: 13px;
  color: #334155;
  line-height: 1.65;
}

.formula-example {
  margin-top: 8px;
  padding: 8px 10px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 6px;
  font-size: 12.5px;
  color: #166534;
  line-height: 1.55;
}

.ex-label {
  font-weight: 700;
}

.guard-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.guard-row {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 9px 12px;
}

.guard-label {
  display: block;
  font-size: 12px;
  font-weight: 700;
  color: #334155;
  margin-bottom: 3px;
}

.guard-text {
  margin: 0;
  font-size: 12.5px;
  color: #475569;
  line-height: 1.55;
}

.mono-text {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11.5px;
}

.explainer-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.explainer-panel {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px 16px;
}

.explainer-panel h4 {
  margin: 0 0 10px;
  font-size: 14.5px;
  color: #0f172a;
}

.step-list {
  margin: 0;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: #334155;
  line-height: 1.6;
}

.calculator-box {
  margin-top: 16px;
  border: 1px solid #bfdbfe;
  background: #f8fbff;
  border-radius: 10px;
  padding: 14px 16px;
}

.calc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
  font-size: 14px;
}

.calc-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.calc-col {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
}

.calc-col h5 {
  margin: 0 0 10px;
  font-size: 13px;
  color: #1e293b;
}

.calc-inputs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.calc-inputs label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11.5px;
  color: #475569;
}

.calc-inputs .ctrl-input {
  min-width: 0;
  width: 100%;
  box-sizing: border-box;
  padding: 5px 8px;
}

.calc-result {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #cbd5e1;
  font-size: 12.5px;
  color: #334155;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.calc-highlight {
  margin-top: 4px;
  font-size: 13.5px;
  color: #1d4ed8;
}

.muted {
  color: #64748b;
  font-size: 11.5px;
}

.empty-box {
  text-align: center;
  padding: 30px;
  color: #64748b;
}

@media (max-width: 1024px) {
  .entity-selector-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .meta-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .metric-body-grid,
  .explainer-grid,
  .calc-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .entity-selector-grid,
  .meta-strip,
  .rules-grid,
  .ops-grid {
    grid-template-columns: 1fr;
  }
}

.main-tab-bar {
  padding: 10px 14px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.main-tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border-radius: 9px;
  border: 1.5px solid #cbd5e1;
  background: #f8fafc;
  color: #334155;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}

.main-tab-btn:hover {
  border-color: #93c5fd;
  background: #eff6ff;
  color: #1d4ed8;
}

.main-tab-btn.active {
  background: #0f172a;
  border-color: #0f172a;
  color: #ffffff;
}

.tab-count {
  font-size: 11.5px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.22);
}

.main-tab-btn.active .tab-count {
  background: rgba(255, 255, 255, 0.2);
  color: #f8fafc;
}

.api-guide-card {
  padding: 20px 24px;
}

.rules-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.rule-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px 16px;
}

.rule-box h4 {
  margin: 0 0 6px;
  font-size: 14px;
  color: #0f172a;
}

.rule-box p {
  margin: 0;
  font-size: 12.8px;
  color: #475569;
  line-height: 1.6;
}

.api-filter-row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.compact-select {
  min-width: 140px;
}

.api-danger-item {
  border-color: #fecaca;
  background: #fffafa;
}

.method-tag {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.method-post {
  background: #dbeafe;
  color: #1e40af;
}

.method-get\/post,
.method-post\/get {
  background: #ede9fe;
  color: #5b21b6;
}

.api-path-code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.auth-pill {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
}

.auth-no_cookie {
  background: #dcfce7;
  color: #166534;
}

.auth-cookie {
  background: #fef3c7;
  color: #92400e;
}

.auth-forbidden {
  background: #fee2e2;
  color: #991b1b;
}

.api-entity-tag {
  font-size: 12.5px;
  font-weight: 600;
  color: #475569;
}

.ops-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.ops-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px 16px;
}

.ops-card h4 {
  margin: 0 0 8px;
  font-size: 14px;
  color: #0f172a;
}

@media (max-width: 1024px) {
  .rules-grid,
  .ops-grid {
    grid-template-columns: 1fr;
  }
}
</style>
