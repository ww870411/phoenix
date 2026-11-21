<template>
  <div class="shp-algo-view">
    <AppHeader />
    <main class="shp-main container">
      <Breadcrumbs :items="breadcrumbItems" />

      <header class="topbar card elevated">
        <div class="topbar-info">
          <div class="title-row">
            <h2>算法与取数口径说明</h2>
            <span class="role-badge">通俗版业务手册 · 仅限 Global_admin</span>
          </div>
          <p class="subtitle">
            按「监测主体 × 核心指标」清晰拆解每个数字从哪里来、怎么算、表计坏了或没传数时系统如何自动补救与隔离，方便运行排查与汇报对账。
          </p>
        </div>
        <div class="topbar-actions">
          <button class="btn secondary" type="button" @click="goBackPages">
            ⬅️ 返回功能页
          </button>
          <button class="btn primary" type="button" @click="goWorkbench">
            📊 前往全量数据统计与报告
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
          <span>📐 各主体取数与降级补救逻辑</span>
          <span class="tab-count">{{ entityCategories.length }} 类业务专题</span>
        </button>
        <button
          type="button"
          :class="['main-tab-btn', { active: activeMainTab === 'apis' }]"
          @click="activeMainTab = 'apis'"
        >
          <span>🔌 源站数据接口与调度方式（技术参考）</span>
          <span class="tab-count">{{ sourceEndpoints.length }} 类接口</span>
        </button>
      </nav>

      <!-- 标签页 1：各主体指标取数与降级补救说明 -->
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
              {{ cat.badgeText || (cat.hasHourly ? '逐小时/日度统计' : '专项规则') }}
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
              <h3>{{ activeCategory.icon }} {{ activeCategory.title }} —— 取数全流程说明</h3>
              <p class="pipeline-summary">{{ activeCategory.summary }}</p>
            </div>
            <div class="filter-controls">
              <input
                v-model="metricKeyword"
                type="search"
                class="ctrl-input"
                placeholder="搜索指标、表计或补救方法…"
              />
            </div>
          </div>

          <div class="meta-strip">
            <div class="meta-item">
              <span class="meta-label">对应台账范围</span>
              <span class="meta-text">{{ activeCategory.dictTables }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">源站取数来源</span>
              <span class="meta-text">{{ activeCategory.sourceApis }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">采集频次与方式</span>
              <span class="meta-text">{{ activeCategory.fact15mTable }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">支撑页面/报表</span>
              <span class="meta-text">{{ activeCategory.factOutputTable }}</span>
            </div>
          </div>

          <div v-if="activeCategory.keyNote" class="note-callout">
            <strong>💡 核心原则（必看）：</strong>{{ activeCategory.keyNote }}
          </div>
        </article>

        <!-- 该主体的指标算法列表 -->
        <article class="card elevated metrics-card">
          <div class="section-head">
            <h3>逐项指标拆解（当前显示 {{ filteredMetrics.length }} 项）</h3>
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
                  <div class="box-title">📥 取数逻辑（数从哪来、怎么算）</div>
                  <p class="formula-expr">{{ m.formula }}</p>
                  <p class="formula-steps">{{ m.steps }}</p>
                  <div v-if="m.example" class="formula-example">
                    <span class="ex-label">算例：</span>{{ m.example }}
                  </div>
                </div>

                <div class="guard-box">
                  <div class="guard-row">
                    <span class="guard-label">🔄 缺数/坏表时的降级补救策略</span>
                    <p class="guard-text">{{ m.fallback }}</p>
                  </div>
                  <div class="guard-row">
                    <span class="guard-label">🛡️ 异常识别与安全隔离边界</span>
                    <p class="guard-text">{{ m.cleaning }}</p>
                  </div>
                  <div class="guard-row">
                    <span class="guard-label">📌 页面查看与来源标记说明</span>
                    <p class="guard-text">{{ m.sourceTags }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </article>

        <!-- 双轨累计核心原理解析 + 交互试算小工具 -->
        <article class="card elevated explainer-card">
          <div class="section-head">
            <h3>🔬 两种小时累计计算方法对照（试算演示）</h3>
            <span class="subtitle-inline">为什么有“表”和“积”两种来源？如何把非整点抄表变成精准的 1 小时耗量</span>
          </div>

          <div class="explainer-grid">
            <div class="explainer-panel">
              <h4>方法 A（首选）：整点表底线性插值作差 <code>METER_DIFF / 表</code></h4>
              <ol class="step-list">
                <li><strong>取表底轨迹：</strong>系统每小时整点后拉取各站约 15 分钟一次的累计表底读数（供热、流量、补水、电表）。</li>
                <li><strong>精确对齐整点：</strong>因为源站抄表常落在 <code>09:50 / 10:05</code> 这类非整点时刻，系统按时间比例精确推算出 <code>10:00</code> 与 <code>11:00</code> 的整点表底。</li>
                <li><strong>相减并判坏表：</strong><code>小时累计 = 结束整点表底 - 开始整点表底</code>；若表底倒走或超过本站合理上限 1.5 倍，则立即拦截丢弃并触发降级补救。</li>
              </ol>
            </div>

            <div class="explainer-panel">
              <h4>方法 B（缺表底时自动接管）：15 分钟瞬时流量积分 <code>INTEGRAL_15M / 积</code></h4>
              <ol class="step-list">
                <li><strong>收集小时内瞬时值：</strong>当某站缺少累计表底（如约 135 站无 <code>f254</code> 补水累计表）或累计表突跳时，收集该小时内多条瞬时热量（<code>GJ/h</code>）或瞬时补水流量（<code>t/h</code>）。</li>
                <li><strong>先滤坏点再算面积：</strong>先剔除超物理极限的坏点，再用“梯形面积累加”把每两段采样之间的用量算出来。</li>
                <li><strong>等比折算整小时：</strong>若该小时仅采到部分分钟，按覆盖时长等比折算回标准 1 小时，保证不因采样缺失而低估。</li>
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
                <h5>1. 表底插值试算（方法 A：首选）</h5>
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
                  <div>10:00 插值表底：<strong>{{ calcResult.interp10 }} GJ</strong> <span class="muted">(= 09:50值 + 10/15 × 差值)</span></div>
                  <div>11:00 插值表底：<strong>{{ calcResult.interp11 }} GJ</strong> <span class="muted">(= 10:50值 + 10/15 × 差值)</span></div>
                  <div class="calc-highlight">10时累计供热量：<strong>{{ calcResult.meterDiff }} GJ</strong></div>
                </div>
              </div>

              <div class="calc-col">
                <h5>2. 15分钟瞬时梯形积分试算（方法 B：降级兜底）</h5>
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
                  <div>按 <code>60分钟 / 45分钟</code> 等比外推至整 1 小时：</div>
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
            <h3>🛡️ 源站接入架构与采集保护原则</h3>
            <span class="subtitle-inline">外网直连：<code>http://124.93.31.19:6688</code> ｜ 内网原址：<code>http://192.168.1.206:6688</code></span>
          </div>

          <div class="rules-grid">
            <div class="rule-box">
              <h4>1. 路线 B 错峰轻量采集</h4>
              <p>
                换热站已彻底停用高频实时接口（<code>/zx_hrz/</code> 与 <code>/get_yw_data/1</code>），统一改为每小时整点后错峰并发拉取历史宽表 <code>/hrz_ls_zb/</code>（超时 45 秒，最大 4 并发），一次兼得表底差值、瞬时补水积分 <code>f209</code> 与代表断面。
              </p>
            </div>
            <div class="rule-box">
              <h4>2. 大包防断流与短连接</h4>
              <p>
                全网商户接口（约 142KB）与历史宽表在长连接下偶发于 13KB 处截断，统一采用短连接（<code>Connection: close</code>）、绕过系统代理并自动退避重试与分片降级。
              </p>
            </div>
            <div class="rule-box">
              <h4>3. 鉴权分界与算完即清</h4>
              <p>
                约 85% 接口可免 Cookie 直连；仅居民室温（<code>/jumin/</code>、<code>/sw_ls_export/</code>）及商业日报（<code>/getall_bb_shrb/</code>）需配置 <code>Session Cookie</code>。5 分钟临时采样仅保留最近 2 小时，整点积分定格后即自动清理。
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
                <option value="all">全部状态</option>
                <option value="no_cookie">免 Cookie（在用）</option>
                <option value="cookie">需 Session Cookie</option>
                <option value="deprecated">已停用（切换路线 B）</option>
                <option value="forbidden">严禁调用 / 失效</option>
              </select>
              <input
                v-model="apiKeyword"
                type="search"
                class="ctrl-input"
                placeholder="搜索路径、主体、字段或用途…"
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
              :class="['metric-item', { 'api-danger-item': ep.auth === 'forbidden', 'api-muted-item': ep.auth === 'deprecated' }]"
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
            <h3>🚀 平台自动调度与手动重校准入口</h3>
            <span class="subtitle-inline">由旁路平台自动守护或管理员在界面按需触发，不改造源站系统</span>
          </div>

          <div class="ops-grid">
            <div class="ops-card">
              <h4>1. 自动定时任务</h4>
              <ul class="step-list">
                <li><strong>上游与商户采集（默认每 5 分钟）：</strong>并发拉取上游（<code>/gk_get_data/</code>）与商业用户（<code>/get_sh_data/</code>），每小时整点附带采集居民室温（<code>/jumin/</code>）；跨小时后积分定格并自动清理 2 小时前临时采样。</li>
                <li><strong>换热站整点表底校准（每小时整点后 :05）：</strong>242 座站受控并发拉取 <code>/hrz_ls_zb/</code>，同时产出累计热量/流量/水表/电表差值、<code>f209</code> 补水积分与代表断面。</li>
                <li><strong>商业日结与每日回看审计（每日 08:30 / 02:30）：</strong>次日 08:30 拉取 <code>/getall_bb_shrb/</code> 日结表底；凌晨自动执行前一日异常回看检测修正。</li>
              </ul>
            </div>

            <div class="ops-card">
              <h4>2. 手动触发与历史重算方式</h4>
              <ul class="step-list">
                <li><strong>页面入口：</strong>各报表右上角“⚡ 立即采集当前时段”、日报页“📏 校准当日表底”、以及本页旁“异常数据监测”页的“🔧 立即回看检测与修正”。</li>
                <li><strong>全量历史回溯脚本：</strong><code>python backend/scripts/backfill_smart_heating_history.py --start 2026-11-01 --end YYYY-MM-DD --steps stations</code>（5 天窗口分片并直接复用生产校准引擎）。</li>
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
  { label: '智慧供热平台精算模块', to: '/projects/smart_heating_platform/pages' },
  { label: '算法说明', to: null },
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
  if (a === 'no_cookie') return '免 Cookie（在用）'
  if (a === 'cookie') return '需 Session Cookie'
  if (a === 'deprecated') return '已停用（改走路线 B）'
  return '严禁 / 失效'
}

const sourceEndpoints = [
  {
    id: 'ep-hrz-ls-zb',
    group: 'history',
    method: 'POST',
    path: '/hrz_ls_zb/',
    auth: 'no_cookie',
    entity: '242 座换热站（当前唯一主采集源）',
    scale: '按单站单次返回 ~96 条/天 × 361 列',
    fields: 'create_time, f1..f5(一次温压流), f209(瞬时补水流量t/h), f220(totF 累计流量), f221(totJ 累计热量), f222(瞬时热GJ/h), f253(电量累计kWh), f254(补水累计t)',
    dataDesc: '每小时整点后自动并发拉取，一次同时产出累计表底差值、缺失水表/热表时的瞬时积分补救值以及小时代表断面。',
    usage: 'POST {base}/hrz_ls_zb/  Body: name=<站名>&start_date=YYYY-MM-DD HH:MM:SS&end_date=...&isdownload=1',
    scheduleAndTable: '每小时整点后 :05 自动校准（历史批量按 5 天窗口分片重算）→ fact_station_hourly',
    notes: '传 isdownload=1 时压力 f1/f4 已换算为 MPa；单站请求超时设为 45 秒以兼容“中天央著”等高频上报大站。',
  },
  {
    id: 'ep-gk-get',
    group: 'realtime',
    method: 'POST',
    path: '/gk_get_data/',
    auth: 'no_cookie',
    entity: '上游热源 / 首站 / 混水 / 分网 / 大户',
    scale: '1 次请求获取全网 137 个点位（含《工况一览》82 核心点）',
    fields: 'dc_dict / sz_dict / yw2_dict / yw_dict / sh_dict：WENDU, YALI, LIULIANG, RELIANG, FUHE, PINLV, SHIJIAN / update_time',
    dataDesc: '同时覆盖北海/香海电厂、4 座首站、5 混水点、12 项分网汇总及造船大户，是上游工况实时采集唯一来源。',
    usage: 'POST {base}/gk_get_data/（空表单即可）',
    scheduleAndTable: '每 5 分钟并发采集 → 整点后梯形积分并保留代表断面 → fact_upstream_hourly',
    notes: '自动区分蒸汽测点（高温上限 600℃、高压 15 MPa）与热水测点，停运备机流量<=1 时 0℃ 不误报故障。',
  },
  {
    id: 'ep-sh-data',
    group: 'realtime',
    method: 'POST',
    path: '/get_sh_data/0 与 /get_sh_data/{mn_id}',
    auth: 'no_cookie',
    entity: '464 户商业用户实时运行参数',
    scale: '0 为全网 1 次返回 468 条；2..16 按主干网分片降级拉取',
    fields: 'name, xinhaoqiangdu(0=在线), gongshuiliuliang, gongshuiwendu, huishuiwendu, gongshuiyali, huishuiyali, shunshireliang, famenkaidu, shedingfamen',
    dataDesc: '每 5~15 分钟提供全部商业户瞬时热量与流量用于梯形积分产出每小时用量。',
    usage: '优先 POST {base}/get_sh_data/0（短连接，断流时自动降级循环主干网 2..16）',
    scheduleAndTable: '每 5 分钟并发采集 → 整点后梯形积分至 fact_merchant_hourly',
    notes: '自动归一化别名并剔除 4 户测试占位户；蒸汽商户原值单位为 kg/h 与 MJ/h，入库自动 ÷1000 折算并屏蔽 -200℃ 未接回温。',
  },
  {
    id: 'ep-jumin',
    group: 'realtime',
    method: 'POST',
    path: '/jumin/',
    auth: 'cookie',
    entity: '2,097 户居民室温测温终端',
    scale: '1 次请求返回全量 ~2,100 户',
    fields: 'id(设备号), village_name(门牌), station_name(含15组站名别名), wd1(室温℃), upload_time, zdxh(型号)',
    dataDesc: '居民室内温度唯一数据源，经台账核验、7 天鲜度与超温过滤后归口到 242 座换热站。',
    usage: 'POST {base}/jumin/  Body: department_name=0&filter_level=0&isDownload=1（需 Cookie）',
    scheduleAndTable: '每小时整点 :00 自动采集 → fact_temp_hourly（自动滚动保留最近 48 小时）',
    notes: '未入台账终端、超过 7 天未更新的僵尸终端及 <=5℃ 或 >40℃ 极端值均不计入均温与达标率。',
  },
  {
    id: 'ep-sh-ls-zb',
    group: 'history',
    method: 'POST',
    path: '/sh_ls_zb/',
    auth: 'no_cookie',
    entity: '商业用户 5 分钟历史瞬时序列',
    scale: '单商户约 288 条/天',
    fields: 'tmDate, fTempSupply, fTempReturn, fFlowF(瞬时流量), fFlowJ(瞬时热量), GongShuiYaLi, HuiShuiYaLi',
    dataDesc: '在实时采集遗漏或停机补采期间，按 5 分钟历史序列梯形积分还原商业户逐小时热量与流量。',
    usage: 'POST {base}/sh_ls_zb/  Body: name=<商户名>&start_date=...&end_date=...&isdownload=1',
    scheduleAndTable: '真空期补采与历史回溯脚本 → fact_merchant_hourly (INTEGRAL_5M)',
    notes: '仅含瞬时量不含累计表底，蒸汽商户同样自动 ÷1000 折算。',
  },
  {
    id: 'ep-ry-dcls-szls',
    group: 'history',
    method: 'POST',
    path: '/ry_dcls_xx/get_history 与 /ry_szls_xx/get_history',
    auth: 'no_cookie',
    entity: '电厂与首站历史补采序列',
    scale: '电厂 5 分钟/条；首站 10 分钟/条',
    fields: 'tmDate, WENDU, YALI, LIULIANG, RELIANG, PINLV, FUHE',
    dataDesc: '用于自动填补上游电厂与首站因网络波动导致的整点真空期漏采。',
    usage: 'POST  Body: start_date=MM/DD/YYYY&end_date=MM/DD/YYYY&station_name=<点位名>&dc_station_id(或sz_station_id)=<组号>',
    scheduleAndTable: '自动真空期补采与历史回溯脚本 → fact_upstream_hourly',
    notes: '日期入参必须为 MM/DD/YYYY 格式；yw2_dict 混水点在源站无独立历史表。',
  },
  {
    id: 'ep-bb-shrb',
    group: 'daily_ref',
    method: 'POST',
    path: '/getall_bb_shrb/',
    auth: 'cookie',
    entity: '商业用户月度日报（按日累计表底与日单耗）',
    scale: '2 次请求返回全月全部商业用户逐日表底列',
    fields: 'id(merchant_id), Data0(上月末表底), Data1..Data31(每日累计表底或日单耗)',
    dataDesc: '用于次日对 464 户商业用户作精确日表底作差结算，并在日报汇总“正常/缺记录/表底倒走”三类状态。',
    usage: 'POST {base}/getall_bb_shrb/  Body: selectof1=0&selectof2=0&selectof3=0|1&options4=YYYYM&lastDay=月末日（需 Cookie）',
    scheduleAndTable: '每日 08:30 自动采集前一日 → fact_merchant_daily',
    notes: '止表底小于起表底时不硬凑数值，明确标注“表读数倒走”。',
  },
  {
    id: 'ep-deprecated-zx',
    group: 'realtime',
    method: 'POST',
    path: '/zx_hrz/ 与 /get_yw_data/1（已停用）',
    auth: 'deprecated',
    entity: '原换热站实时与二次网分区接口',
    scale: '已于路线 B 升级后停止定时调用',
    fields: '曾用于拉取换热站实时断面 e1..e16 与 580 个二次分区',
    dataDesc: '为彻底减轻源站数据库压力并避免实时接口缺少累计表底与跨天漂移，换热站采集已全面切换至 /hrz_ls_zb/，二次分区停采仅留静态台账。',
    usage: '调度器中已停止轮询；/hrz_ls_zb/ 中的 f209 已等价替代原 e14 瞬时补水',
    scheduleAndTable: '停用（零请求负载）',
    notes: '原依赖 /zx_hrz/ e14 的 135 站瞬时补水现已改由 /hrz_ls_zb/ 中的 f209 统一采集与积分。',
  },
  {
    id: 'ep-forbidden',
    group: 'forbidden',
    method: 'POST/GET',
    path: '/terminal_control/、/ewph_tj/、/wd_biao/、/fhrb/、/fhrjl_ssxx/',
    auth: 'forbidden',
    entity: '严禁触碰的控制接口 / 造假 / 失效页面',
    scale: '安全红线清单',
    fields: '阀门下发控制指令 / 虚增室温看板 / 500报错 / 5.35MB大页',
    dataDesc: '严禁向现场设备下发控制指令或采集已知重复虚增室温的失效接口。',
    usage: '全部严禁进入自动调度或脚本白名单',
    scheduleAndTable: '严格隔离（只读旁路红线）',
    notes: '本平台严格坚持只读旁路采集，绝不干扰源站与现场设备控制状态。',
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
  { value: 'cumulative', label: '累计用量指标' },
  { value: 'snapshot', label: '运行断面/工况' },
  { value: 'derived', label: '对账/榜单/衍生' },
]

function kindText(kind) {
  if (kind === 'cumulative') return '累计用量'
  if (kind === 'snapshot') return '运行断面'
  return '对账与衍生'
}

const entityCategories = [
  {
    key: 'station',
    icon: '🏭',
    title: '换热站（242 座核心站）',
    scale: '供热 · 补水 · 耗电 · 温压',
    hasHourly: true,
    badgeText: '每小时整点校准',
    brief: '所有站级热量、流量、补水与电耗的真实取数、坏表隔离及缺失补救规则。',
    dictTables: '242 座站标准台账（含所属服务中心、主干/支线网及供热面积）',
    sourceApis: '历史宽表接口（/hrz_ls_zb/，每小时整点后错峰拉取）',
    fact15mTable: '每小时 :05 批量校准一次（无需 5 分钟高频盯源站）',
    factOutputTable: '驾驶舱 · 逐小时运行报告 · 每日运行报告 · Excel 导出',
    summary: '换热站是全网热、水、电计量的基础单元。系统在每个整点结束后统一抓取各站近 1 小时约 15 分钟一次的完整抄表轨迹，优先用「前后整点累计表底相减」算出精确耗量；当累计表底缺失或坏表跳变时，能用瞬时量积分补救的自动补救，不能补救的坚决隔离置空而不混入假高值。',
    keyNote: '计算站点实际供热量一律以「一次网计量」为准！系统绝不使用二次网各分区的参考热量来替代一次网结算，防止二网表计失真扭曲全网热耗。',
    metrics: [
      {
        id: 'st-hour-heat',
        kind: 'cumulative',
        name: '小时供热量（及日供热量累加）',
        unit: 'GJ',
        field: '表底作差 优先 / 瞬时积分 兜底',
        formula: '① 首选：结束整点表底(f221) - 开始整点表底(f221)  |  ② 兜底：瞬时热量(f222) 15 分钟梯形积分',
        steps: '系统先按前后抄表时间线性推算出整点时刻（如 10:00 和 11:00）的累计热量表底，再相减得到本小时实际供热量。对于台账确认存在固定刻度倍率的站（如南山苑等 4 座站固定 ÷10），系统会在清洗值中自动折算到位，同时保留未折算原值以供“原始对照”模式查看。',
        example: '10:00 表底 1200.0 GJ、11:00 表底 1248.6 GJ，小时供热量即为 48.6 GJ；若南山苑表底差显示 125.0 GJ，清洗精算自动 ÷10 修正为 12.5 GJ。',
        fallback: '若某小时缺少整点表底，或累计表出现倒走/突然暴涨（超过按本站供热面积核定极限负荷 1.5 倍，或明显背离瞬时热量 4 倍以上），系统会自动放弃坏表差值，降级改用该小时内清洗后的瞬时热量（f222）梯形积分兜底。',
        cleaning: '计算瞬时积分前，系统先自动剔除瞬时热量 f222 < 0 或超过面积极限 1.5 倍的毛刺尖峰；仅突发跳变或临时缺表时页面才显示红标提示，常规倍率修正不再满屏标红。',
        sourceTags: '页面标记「表」= 表底直减最准 ｜ 「积 / 补」= 缺表或跳变后改用瞬时积分兜底 ｜ 双缺则留空「-」',
      },
      {
        id: 'st-hour-water',
        kind: 'cumulative',
        name: '小时补水量（及日补水累加）',
        unit: 't（吨）',
        field: '累计水表 f254 优先 / 瞬时流量 f209 积分补齐',
        formula: '① 首选：累计水表差(f254)  |  ② 缺表/跳变补救：自来水瞬时补水流量(f209) 15 分钟梯形积分',
        steps: '全网仅约 90 余座站配有远传累计补水表（f254），其余约 135 座站只上传了瞬时补水流量（f209，对应原实时口径 e14）。因此系统优先取 f254 整点表底差值；一旦发现 f254 缺失或出现单次跳变/倒走，立即自动切换为对清洗后的瞬时补水流量 f209 做时间加权积分，将缺失站点的补水完整追回。',
        example: '「泛华领域」站无累计水表 f254，但其瞬时补水 f209 稳定在约 12.5 t/h，系统自动逐时积分后全天准确统计出约 300 吨补水，不再漏统。',
        fallback: '若某小时内的 f209 瞬时采样混有坏表毛刺（>100 t/h 或 <0），系统会先把异常点滤除后再对正常采样点积分，避免坏表把一小时补水拉成几千吨。',
        cleaning: '系统同时按站面积核定单小时补水上限（每万㎡ 5 吨，最低保底 80 t/h），若发现整天呈现锯齿状反复倒走（例如「外国语学院」某类坏表）或连续跳变，会直接将其当日补水量置空隔离，绝不让假高水污染榜单和日报。',
        sourceTags: '页面标记「表」= f254 累计水表 ｜ 「积」= 无 f254 时用 f209 瞬时积分补齐 ｜ 仍有一小部分机械水表无远传（f254空且f209恒0）需现场加装远传',
      },
      {
        id: 'st-hour-elec',
        kind: 'cumulative',
        name: '小时耗电量（及日电耗累加）',
        unit: 'kWh（度）',
        field: '仅累计电表 f253 整点作差（无瞬时功率可替代）',
        formula: '结束整点累计电表(f253) - 开始整点累计电表(f253)，按面积校验单小时上限',
        steps: '目前源站只提供一个累计电能字段（f253），没有提供瞬时电功率（kW）或电流字段。对电表正常走字的站点，系统按整点线性插值作差得到小时用电量（kWh）。',
        example: '10:00 电表读数 18240.0 kWh、11:00 为 18312.5 kWh，小时耗电 = 72.5 kWh；正常有表站日均单耗约 89 kWh/万㎡。',
        fallback: '重要边界：因为源站不存在瞬时电功率字段，当某个站的 f253 未上传、恒为 0、冻结不动或报 10 亿死值时，软件侧无法凭空推算，该站电耗只能留空显示“-”，并在异常监测中心点名列出排查清单。',
        cleaning: '系统对每座站按面积核定合理小时电耗上限（每万㎡ 12 kWh，保底 35 kWh/h，放宽 1.5 倍拦截线）。一旦监测到电表整天出现 2 次以上锯齿倒走并突然暴涨上万度（如「信兴花园」「长江杰座」），系统会整日隔离置空其耗电量并自动从高耗榜与日报汇总中剔除。',
        sourceTags: '正常站直接展示 kWh ｜ 「-」表示源站无有效电表或坏表已屏蔽（可在异常监测中心查看全网 126 座无电表站明细）',
      },
      {
        id: 'st-hour-flow',
        kind: 'cumulative',
        name: '小时一网流量 & 供回水温压力代表断面',
        unit: 't / ℃ / MPa / GJ/h',
        field: '累计流量 f220 + 小时末清洗断面 (e1/e3/e4/e7/e8/e11/e14)',
        formula: '累计流量首选 f220 作差（缺则 f2 积分）；温压瞬时取该小时末最新有效采样',
        steps: '一网累计流量优先取累计流量表 f220 作差（缺失回退瞬时流量 f2 积分）；供回水温度、供回水压力、瞬时热量与瞬时补水取该小时末尾最新一次采样值展示。',
        example: '某站 10:45 一次供温 74.2℃、回温 41.5℃、供压 0.45 MPa、回压 0.31 MPa，即作为 10 时代表工况展示。',
        fallback: '当某站出现临时通讯掉线（该小时无记录），自动沿用最近 6 小时内最后一次在线正常工况并标 `*` 提示；长期停运站保持离线空值不造数。',
        cleaning: '自动拦截温度 <=0℃ 或 >150℃ 断路值、压力 <0 或 >2.5 MPa 越限值，以及有流量时供水温度 <= 回水温度的物理倒挂，触发时平滑回退上一有效工况。',
        sourceTags: 'REAL（实时直采）｜ 带 * 提示（沿用前序有效工况或异常屏蔽修正）',
      },
      {
        id: 'st-heat-index',
        kind: 'derived',
        name: '折算热指标 & 万平耗热/补水/电耗单耗',
        unit: 'W/㎡ / GJ/万㎡ / t/万㎡ / kWh/万㎡',
        field: '瞬时热指标 + 单位面积耗量强度',
        formula: '热指标(W/㎡) = 瞬时热量(GJ/h) × 277777.78 ÷ 供热面积(㎡)；万平耗量 = 累计耗量 ÷ 面积(万㎡)',
        steps: '将每小时 1 GJ/h 换算为 277,777.78 瓦后除以本站供热面积，即得衡量当前供热强度的实时热指标（W/㎡）；将累计热量、补水或电耗除以面积（万㎡），即可横向对比大站与小站的节能水平。',
        example: '10 万㎡ 站点瞬时热量 14.4 GJ/h，折算热指标 = 40.0 W/㎡；小时耗热 14.4 GJ，万平耗热 = 1.44 GJ/万㎡·h。',
        fallback: '当个别站台账尚未补录供热面积（当前 4 座站缺失）时，单耗指标显示“-”并在报表头部显式提示“缺失面积站数”。',
        cleaning: '全网使用清洗后数据计算；可在报告顶部一键切换「净化精算」与「原始对照」查看清洗前后的数值差异。',
        sourceTags: '衍生指标（随页面“净化精算 / 原始对照”模式联动重算）',
      },
    ],
  },
  {
    key: 'group',
    icon: '🏛️',
    title: '全网 / 中心 / 驾驶舱榜单聚合',
    scale: '全网 · 9大中心 · 热源网 · 主干/支线',
    hasHourly: true,
    badgeText: '统一聚合口径',
    brief: '宏观汇总时的流量加权均温算法、连续 72 小时走势及驾驶舱 Top 5 健康榜单筛选门槛。',
    dictTables: '9 大服务中心 · 9 大热源大网 · 15 条主干网 · 41 条支线网',
    sourceApis: '基于 242 座换热站与室温实时事实表统一聚合计算（跨页面同口径）',
    fact15mTable: '全网 / 中心 / 驾驶舱接口共用一套后端精算汇总器',
    factOutputTable: '运行驾驶舱 · 逐小时运行报告 · 每日运行报告 · 导出 Excel',
    summary: '无论是在领导驾驶舱看全网总盘，还是在逐小时/每日报告按服务中心、主干热网、支线热网分组对比，系统均使用完全相同的汇总逻辑，保证同一个中心在不同页面看到的每一度电、每一吨水、每一度温度分毫不差。',
    keyNote: '全网和各中心的平均供水/回水温度绝不能简单算数平均！如果把已经停运、温差只有 1℃ 的小站跟流量 2000 吨的大站 1:1 平均，温度会被严重拉偏。系统严格按各站一次网瞬时流量大小进行「流量加权平均」。',
    metrics: [
      {
        id: 'gp-weighted-temp',
        kind: 'derived',
        name: '流量加权平均供温 / 回温 / 温差',
        unit: '℃',
        field: 'avg_sup_temp / avg_ret_temp / avg_temp_diff',
        formula: '加权供温 = Σ(单站供温 × 单站流量) ÷ Σ单站流量（仅纳入流量 > 0 的在运站）',
        steps: '系统仅筛选当前有一次网流量（e1 > 0）且供回温合理的运行站，流量越大的站权重越高；平均回压采用非空站点回压的算数平均值。',
        example: '大站流量 200 t/h 供温 80℃、小站流量 20 t/h 供温 50℃ → 加权供温 = (200×80 + 20×50) ÷ 220 = 77.27℃，远比简单平均 65℃ 真实。',
        fallback: '若分组内全部站点均已停泵无流量，温度汇总显示“-”。',
        cleaning: '若某个站点一次温压已被清洗器修正，上层汇总会自动带上异常批注，提示受哪几座站修正影响。',
        sourceTags: '物理流量加权聚合（跨页一致）',
      },
      {
        id: 'gp-watchlist',
        kind: 'derived',
        name: '驾驶舱「焦点榜单 Top 5」健康准入门槛',
        unit: 'Top 5（高热 / 高补水 / 高电耗 / 节能低耗）',
        field: 'watchlists (high_heat / high_water / high_elec / benchmark)',
        formula: '严格剔除故障站、坏表站与近零/停运站后，仅在健康在运站中按强度排名取前 5',
        steps: '为了不让“坏表飙高”“停运凑0.01低能耗”霸占领导驾驶舱榜单，所有进榜站点必须同时满足健康体检：① 在线且当日无跳变/异常标签；② 有真实热耗与流量（热量≥0.5 GJ 且热指标≥5 W/㎡、流量>0.5 t/h）；③ 温压合理不倒挂、一二网不严重失调；④ 若看水/电榜则还须排除当日坏水/坏电表。',
        example: '例如「信兴花园」电表锯齿虚高已被隔离置空，不进 ⚡高电耗榜；「正源」「远洋风景」近零负荷停供站不进 🏆节能低耗榜。',
        fallback: '驾驶舱右上角“实时室温”独立展示当前全网最新真实测温快照，榜单卡片不再混排室温。',
        cleaning: '「昨日同期对比」与「连续 72 小时负荷走势」均自动对齐整点并叠加气象实况室外温度曲线。',
        sourceTags: '仅健康在运站参与排行（防假高/假低误导决策）',
      },
    ],
  },
  {
    key: 'daily_reconcile',
    icon: '📋',
    title: '每日运行报告与人工日报对账',
    scale: '自然日(0~24h) · 生产班次(8点~次日8点) · 热/水/电双轨',
    hasHourly: false,
    badgeText: '双轨偏差核对',
    brief: '站级日累积计算、止表底时刻对齐，以及与生产日报手工填报耗热/耗水/耗电的双轨对比规则。',
    dictTables: '9 大服务中心 ↔ 生产日报填报分支对照映射',
    sourceApis: '系统站时精算库 + 生产日报库（日耗热 / 日补水 / 日外购电）',
    fact15mTable: '实时查询动态汇总（支持切换「自然日」与「生产班次」口径）',
    factOutputTable: '每日运行报告 · 多日横向导出 Excel',
    summary: '每日运行报告将系统自动化采集算出的「日耗热量、日补水量、日耗电量」与各服务中心每天在《生产日报》中手工填报的数据逐一摆在一起对比，帮助管理层一眼发现哪些中心存在漏表、表计倍率误差或填报偏差。',
    keyNote: '手工日报中部分单位的耗电量按「万 kWh」填报，系统会自动检测单位并 ×10000 统一折算为 kWh（度），确保双轨处于同一量纲直接相减。',
    metrics: [
      {
        id: 'dr-period-meter',
        kind: 'cumulative',
        name: '自然日 vs 生产班次 & 起止表底核对',
        unit: 'GJ / t / kWh / h',
        field: 'start_tot_j / end_tot_j / hours_count',
        formula: '日耗量 = 24 小时清洗累计之和；止表底 = 结算结束整点时刻（次日00:00 或当日08:00）读数',
        steps: '① 「自然日」统计当日 00:00~次日 00:00；「生产班次」统计昨日 08:00~今日 08:00；② 242 站表的「有效热量小时数」仅计真正读到热量的小时，不再把空站显示成“24h / 0 GJ”；③ 止表底严格取结算窗口结束那个整点的读数，让“止表底 - 起表底”可直接验算日供热量。',
        example: '11-18 自然日止表底取 11-19 00:00 的 totJ；若某站仅 18 个小时有热量读数，小时数列即如实显示 18h。',
        fallback: '若结算结束时刻（例如今日尚未过完 24:00）表底未出，止表底留空，日累计仍实时滚动累加已结束小时。',
        cleaning: '所有异常小时已在底层完成坏表隔离与降级积分，日报页可点击切换“原始值对照”核验差异。',
        sourceTags: '自然日 00:00~24:00 ｜ 生产班次 08:00~次日08:00',
      },
      {
        id: 'dr-dual-track',
        kind: 'derived',
        name: '全网及 9 中心热 / 水 / 电三轨偏差对比',
        unit: '% / GJ / t / kWh',
        field: '偏差率 = (系统统计值 - 手工填报值) ÷ 手工填报值 × 100%',
        formula: '供热偏差（>±10%橙警）｜ 补水偏差（>±10%橙警）｜ 电耗偏差（>±10%橙警）',
        steps: '系统分别提取手工生产日报中各分公司的「站耗热量(GJ)」「站补水量(t)」「外购电量(自动由万kWh折算为kWh)」，与本系统按 9 大中心汇总出的热/水/电逐一比对并算差值与偏差率。',
        example: '11-18 全网补水经 f209 追回后系统 4,583.95 t vs 手工 5,242.0 t，偏差仅 -12.55%；电耗因全网仅 116/242 站有电表（其余 126 站源站未传或死值），系统 88,052.9 kWh vs 手工 199,800 kWh，偏低 -55.93%。',
        fallback: '若某天手工日报尚未提交或某中心未填报该项，对应偏差显示“-”不乱告警。',
        cleaning: '当中心补水/电耗偏差显著偏低时，请结合「异常数据监测」页的「取数诊断」查看是该中心哪些站无远传水表或无电表。',
        sourceTags: '偏差超过 ±10% 自动标橙预警（可在导出 Excel 中同步高亮并附说明）',
      },
    ],
  },
  {
    key: 'upstream',
    icon: '⚡',
    title: '上游热源 / 首站 / 网口',
    scale: '82 核心监测点（全网 137 点）',
    hasHourly: true,
    badgeText: '每5分钟高密采',
    brief: '覆盖电厂、首站、混水与网口，自动区分蒸汽高温高压点与热水点阈值。',
    dictTables: '上游点位台账（区分核心《工况一览》82 点与扩展字典点）',
    sourceApis: '实时全网工况接口（/gk_get_data/）+ 缺采时自动调用电厂/首站历史接口补采',
    fact15mTable: '每 5 分钟并发采集一次（保留 2 小时算完即清）',
    factOutputTable: '驾驶舱 · 逐小时报告上游热源表 · 24小时趋势图',
    summary: '上游电厂与首站没有累计表底接口，系统每 5 分钟拉取一次瞬时温度、压力、流量与瞬时热量，跨小时后通过时间加权梯形积分得到每小时供热量与流量；如遇网络断采，系统支持自动调用历史接口把漏掉的小时补回来。',
    keyNote: '电厂大量点位是高温高压蒸汽（几百度、数兆帕），如果拿热水管网 150℃ 上限去卡电厂就会满屏报错。系统会自动识别主汽、进汽、抽汽、排汽、蒸汽等测点，将安全范围放宽到 600℃ / 15 MPa；同时停运备用机组（流量 ≤1）温度为 0℃ 时不误报故障。',
    metrics: [
      {
        id: 'up-hour-heat-flow',
        kind: 'cumulative',
        name: '上游小时供热量与累计流量（积分）',
        unit: 'GJ / t',
        field: 'hour_heat_gj / hour_flow_t',
        formula: '对本小时内多点清洗后瞬时热量(RELIANG)与瞬时流量(LIULIANG)做梯形积分并折算至 1 小时',
        steps: '汇总每小时内的 5~15 分钟实时采样，计算相邻点之间的梯形面积并按实际覆盖时长折算到 60 分钟；历史漏采期间自动从电厂（5分钟粒度）/ 首站（10分钟粒度）历史接口补算。',
        example: '10:00 负荷 210 GJ/h、10:15 负荷 230 GJ/h，折算整小时约 220.0 GJ。',
        fallback: '某小时仅有 1 次有效采样时直接按“瞬时值 × 1 小时”估算；源站空值则占位标记不乱估算。',
        cleaning: '热水点温度 <-10℃ 或 >150℃（且在运带流量时 <=0℃）、压力 >2.5 MPa 触发越限屏蔽；蒸汽点温度 >=600℃ 或压力 >15 MPa 触发越限屏蔽。',
        sourceTags: '15分钟/5分钟积分 ｜ 触发温度压力越限时回退最近 6 小时前序正常值并标 `*`',
      },
      {
        id: 'up-snapshot',
        kind: 'snapshot',
        name: '上游代表温度 / 压力 / 瞬时流量',
        unit: '℃ / MPa / t/h',
        field: 'temp_clean / pressure_clean / flow_clean / heat_clean',
        formula: '取本小时内最新一次经过阈值校验与停机判断后的运行断面',
        steps: '记录小时末最新实况供阳面展示；若源站时间（source_time）滞后采集时间超过 2 小时，自动向异常监测中心派发通讯滞后提示。',
        example: '某首站网口 14:55 供温 86.2℃，即作为 14 时断面展示。',
        fallback: '传感器断路或超限值立即屏蔽并沿用 6 小时内前序正常值，原始异常读数仍保留在原始对照中备查。',
        cleaning: '停运冷备管线（流量 <=1 且温度=0℃）视为正常停机，不触发断路误报。',
        sourceTags: '实时直采 ｜ 前序回退保持（标 `*`）',
      },
    ],
  },
  {
    key: 'merchant',
    icon: '🏬',
    title: '商业用户 / 商户（464 户）',
    scale: '464 户标准商户（含蒸汽户自动折算）',
    hasHourly: true,
    badgeText: '小时积分 + 日结表底',
    brief: '5分钟实时积分算出每小时用量 + 次日 08:30 拉取日结表底作差核算。',
    dictTables: '464 户商业用户标准台账（含介质 rdry、主干/支线网分类）',
    sourceApis: '全网商户实时接口（/get_sh_data/）+ 5分钟历史接口（/sh_ls_zb/）+ 商业日报接口（/getall_bb_shrb/）',
    fact15mTable: '每 5 分钟实时积分 + 每日 08:30 采集前一日累计日结表底',
    factOutputTable: '逐小时报告商业用户表 · 每日报告 464 商业用户表与三类状态统计',
    summary: '商业用户采取“小时看瞬时积分、日度看日结表底”的双轨体制：白天运行靠每 5~15 分钟的瞬时热量与流量梯形积分出逐小时数据（缺失时用 5 分钟历史序列补算）；次日早上 08:30 再从源站商业日报中拉取按天记录的累计表底作差结算，方便财务与运行双核对。',
    keyNote: '源站实时接口中多出了 4 户未入账的“测试商户”占位记录，系统阳面严格将其隔离不计入 464 户；另有多家「蒸汽商户」源站原值单位是 kg/h 与 MJ/h，入库时系统会自动 ÷1000 统一折算为 t/h 与 GJ/h，并主动屏蔽蒸汽回水未接传感器导致的 -200℃ 假读数。',
    metrics: [
      {
        id: 'mc-hour-heat',
        kind: 'cumulative',
        name: '商业户小时供热量 & 流量（积分）',
        unit: 'GJ / t',
        field: 'hour_heat_gj / hour_flow_t',
        formula: '实时 5~15 分钟瞬时热量梯形积分；缺失时回退 /sh_ls_zb/ 5 分钟历史积分',
        steps: '系统每 5 分钟采集全网商户瞬时参数（若整网大包断流则自动改按 15 条主干网分段拉取保活），跨小时积分出每户耗热量与耗水量；单户信号强度非 0 判为离线，沿用最近 6 小时正常工况。',
        example: '「1896酒店」某小时瞬时热量平稳在 0.69 GJ/h 左右，积分后计入 0.69 GJ。',
        fallback: '若实时停采，可通过历史回溯按 /sh_ls_zb/ 每 5 分钟一条的精确轨迹无损重算该小时用量。',
        cleaning: '对蒸汽商户自动 ÷1000 折算单位（常规固定折算不再误标红）；带流量 >0.5 时供温 <= 回温触发物理倒挂审计；瞬间功率 >500 GJ/h 或 <0 屏蔽回退。',
        sourceTags: 'INTEGRAL_15M（实时积分）｜ INTEGRAL_5M（历史5分钟补采）',
      },
      {
        id: 'mc-daily-cons',
        kind: 'cumulative',
        name: '商业户次日日结耗热量（表底作差三分类）',
        unit: 'GJ / 日',
        field: 'daily_consumption / calc_status',
        formula: '当日日耗 = 今日累计表底 - 昨日累计表底（1日减上月末表底）',
        steps: '每日 08:30 拉取商业用户日表底数据。日报页按 464 户台账严格划分为三类清晰状态：①「正常」（可准确作差）；②「缺日耗记录」（源站接口当天未返回该户或缺起/止表底）；③「表读数倒走」（止表底 < 起表底，不凑假数）。',
        example: '15 日累计表底 840.5 GJ、14 日 828.0 GJ，即结算 15 日耗热 12.5 GJ；若 15 日表底小于 14 日则标红“表读数倒走”。',
        fallback: '注意：今日白天的日结表底要等次日 08:30 才出结果，因此查看“今日”日报时商户日结会提示待次日结算。',
        cleaning: '未配置有效 Session Cookie 时跳过日报接口拉取（小时瞬时积分免 Cookie 仍正常工作）。',
        sourceTags: '正常 ｜ 缺日耗记录（标橙提示）｜ 表读数倒走（标红提示）',
      },
    ],
  },
  {
    key: 'temp_device',
    icon: '🌡️',
    title: '居民室温 & 已停采二次分区说明',
    scale: '2,097 台账终端（另有 580 个二次分区停采留账）',
    hasHourly: true,
    badgeText: '7天鲜度 · 48h滚动',
    brief: '居民测温整点直采、防僵尸户与黑户规则，及二次分区停采后的口径边界。',
    dictTables: '2,097 户室温标准台账（含 15 组站名别名自动归口） + 580 个二次分区静态台账',
    sourceApis: '居民室温接口（/jumin/，需有效 Cookie，每小时整点采集一次）',
    fact15mTable: '每小时整点采集一次，数据自动滚动保留最近 48 小时以控制存储容量',
    factOutputTable: '驾驶舱当前室温卡片 · 单站室温下钻抽屉 · 异常数据监测',
    summary: '居民室内温度由各户测温盒上传至源站，系统每小时整点拉取一次，严格经过「已入台账 + 最近 7 天内有上报 + 室温在 (5℃, 40℃] 合理范围」三重过滤后，才参与计算全网及单站平均室温、≥18℃ 达标率与舒适度分布。',
    keyNote: '① 未录入标准台账的源站多出终端会被阳面剔除并在异常中心提示核对；② 超过 7 天未更新的设备判为“离线僵尸户”绝不拉低均温；③ 580 个二次网分区已停止实时落库以减轻源站负担，仅在静态台账中保留清单对照。',
    metrics: [
      {
        id: 'tm-clean',
        kind: 'snapshot',
        name: '居民有效均温、达标率（≥18℃）与舒适率',
        unit: '℃ / % / 户',
        field: 'avg_room_temp / temp_pass_rate_pct / temp_comfort_rate_pct',
        formula: '有效门槛 = 已入台账 且 (距今 ≤ 7 天内上传) 且 (5℃ < 室温 ≤ 40℃)',
        steps: '三重过滤全部通过的有效终端才进入分站及全网统计：≥18℃ 占比为达标率，20~25℃ 占比为舒适率。驾驶舱“当前室温分布”固定读取库中最新一次有效测温断面展示，不随切换历史日期而变成空。',
        example: '当前断面在册 2,097 户，有效可用 2,084 户（另有 6 户源站未传、7 户温度超限剔除、8 户未入台账隔离），即按 2,084 户算均温与达标率。',
        fallback: '异常或离线超 7 天的测温点会被置为无效（不做假温度插值），原始读数和最后上报时间仍可在单站明细抽屉与异常监测页查看。',
        cleaning: '为控制数据库膨胀，室温明细表仅滚动保留最近 48 小时记录；若未配置或 Cookie 过期，每小时抓取会提示失败且无法更新最新室温。',
        sourceTags: '仅有效台账样本参与统计（无效与未入台账终端均透明可查）',
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

.meta-code,
.meta-text {
  font-size: 12.5px;
  color: #1e293b;
  word-break: break-word;
  line-height: 1.45;
}
.meta-code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
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

.api-muted-item {
  border-color: #cbd5e1;
  background: #f8fafc;
  opacity: 0.92;
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

.auth-deprecated {
  background: #e2e8f0;
  color: #475569;
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
