<template>
  <div class="report-app" :class="{ 'dark-theme': isDark, 'is-fullscreen': isFullscreen }">
    <!-- ==================== 1. 顶部控制工具栏（全屏模式下自动彻底隐藏） ==================== -->
    <header v-show="!isFullscreen" class="top-toolbar">
      <div class="toolbar-inner">
        <!-- 左侧：返回 -->
        <div class="toolbar-left">
          <RouterLink to="/projects/daily_report_25_26/pages" class="btn-back" title="返回功能菜单">
            <svg class="icon-svg" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
            <span>返回菜单</span>
          </RouterLink>
          <span class="toolbar-divider"></span>
          <!-- 日期选择与生成 -->
          <div class="date-picker-box">
            <label class="date-label">开始 <input v-model="start" type="date" :disabled="loading" class="date-input" /></label>
            <label class="date-label">结束 <input v-model="end" type="date" :disabled="loading" class="date-input" /></label>
            <button class="btn-primary" :disabled="loading || !start || !end" @click="generateReport">
              <span v-if="loading" class="spinner"></span>
              {{ loading ? '正在统计…' : '生成汇报' }}
            </button>
          </div>
        </div>

        <!-- 右侧：缩放控制器 / 深浅色 / 上期开关 / 全屏 / 数据源 / 导出 -->
        <div class="toolbar-right">
          <!-- 缩放控制器 -->
          <div class="zoom-controller" title="微调页面缩放比例以适配不同投影仪与屏幕">
            <span class="zoom-text">缩放</span>
            <button class="btn-zoom" @click="changeZoom(-5)" title="缩小 5%">−</button>
            <span class="zoom-value">{{ zoomLevel }}%</span>
            <button class="btn-zoom" @click="changeZoom(5)" title="放大 5%">+</button>
            <button class="btn-zoom-reset" @click="zoomLevel = 100" title="恢复100%">重置</button>
          </div>

          <!-- 深浅色切换 -->
          <button class="btn-tool" @click="isDark = !isDark" :title="isDark ? '切换浅色公文纸质模式' : '切换深色大屏投影模式'">
            <span>{{ isDark ? '🌙 深色模式' : '☀️ 浅色模式' }}</span>
          </button>

          <!-- 含上期(环比)动态开关 -->
          <button
            class="btn-tool btn-toggle-prev"
            :class="{ active: includePrev }"
            @click="includePrev = !includePrev"
            title="测试供暖初期无上期数据时的自适应排版"
          >
            <span class="status-dot" :class="{ 'dot-on': includePrev }"></span>
            <span>{{ includePrev ? '含上期(环比)' : '隐藏上期' }}</span>
          </button>

          <!-- 大屏全屏播放按钮 -->
          <button class="btn-tool btn-fullscreen-highlight" @click="toggleFullscreen" title="进入全屏大屏汇报模式（顶部工具栏将自动隐藏，主视口放大撑满屏幕）">
            <svg class="icon-svg" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" /></svg>
            <span>大屏全屏</span>
          </button>

          <!-- 数据源 JSON -->
          <button class="btn-tool" @click="showJsonModal = true" title="查看当前计算出的底层数据源结构">数据源 JSON</button>
          <!-- 下载文本材料 -->
          <button class="btn-tool" @click="downloadReport" title="下载汇报纯文稿">下载讲稿</button>
        </div>
      </div>
    </header>

    <!-- 错误横幅提示 -->
    <div v-if="error" class="error-banner" role="alert">
      <span>⚠️ {{ error }}</span>
      <button class="btn-close-error" @click="error = ''">✕</button>
    </div>

    <!-- ==================== 2. 主舞台视口（全屏宽屏分辨率自适应，占满可用空间） ==================== -->
    <div ref="viewportRef" class="report-viewport" :style="{ zoom: zoomLevel / 100 }">
      <main class="report-stage">

        <!-- 紧靠主要内容的“汇报标题与章节导航标签栏”（全屏下常驻） -->
        <div class="stage-nav-bar">
          <div class="stage-title-wrap">
            <div class="stage-badge-row">
              <span class="badge badge-season">{{ reportState.meta?.season || '25-26供暖期' }}</span>
              <span class="badge-dept">{{ reportState.meta?.department || '经济运行部' }} · 生产调度汇报</span>
              <span class="badge-period">周期：{{ reportState.meta?.start }} 至 {{ reportState.meta?.end }}（共 {{ reportState.meta?.days }} 天）</span>
            </div>
            <h1 class="stage-main-title">{{ reportState.meta?.weekTitle }}</h1>
          </div>

          <!-- 5 个章节导航药丸胶囊 -->
          <nav class="chapter-nav-pills" aria-label="汇报章节">
            <button
              v-for="(name, idx) in chapters"
              :key="name"
              class="chapter-nav-pill"
              :class="{ active: currentSlide === idx }"
              @click="currentSlide = idx"
            >
              <span class="pill-index">0{{ idx + 1 }}</span>
              <span class="pill-title">{{ name }}</span>
            </button>
          </nav>
        </div>

        <!-- 章节 0: 第一章 一、基本概况 -->
        <section v-show="currentSlide === 0" class="slide-panel">
          <div class="chapter-header theme-border-sky">
            <div class="ch-left">
              <span class="chapter-badge badge-sky">第一章 / 共五章</span>
              <div>
                <h2 class="chapter-title doc-serif-title">一、基本概况：气象走势与生产经营总体表现</h2>
                <p class="chapter-subtitle">左侧为根据当期气象与经营异动自适应生成的调度会宣读正文，右侧为核心指标卡片与多维对标概览</p>
              </div>
            </div>
            <div class="ch-right">
              <span class="info-pill pill-rose">最低气温：<strong>{{ reportState.weather?.minTempMainCity }}</strong></span>
              <span class="info-pill pill-emerald">边际利润：<strong>{{ fmt(reportState.kpis?.profitActual) }} 万元</strong></span>
            </div>
          </div>

          <div class="spread-grid">
            <!-- 左侧：Word 汇报精读区 -->
            <article class="doc-reading-pane">
              <div class="doc-header">
                <span class="doc-tag">会议宣读稿</span>
                <h3 class="doc-heading doc-serif-title">气象走势与生产经营总览</h3>
                <span class="doc-subtag">重点高亮 · 真实因势撰稿</span>
              </div>
              <div class="doc-body doc-scrollable">
                <p
                  v-for="(paragraph, i) in currentNarrative.paragraphs"
                  :key="i"
                  class="doc-paragraph"
                  v-html="paragraph"
                ></p>

                <!-- 动态提炼解读框 -->
                <div v-if="currentNarrative.callout" class="doc-callout">
                  <div class="callout-title">{{ currentNarrative.callout.title }}</div>
                  <ul class="callout-list">
                    <li v-for="(item, i) in currentNarrative.callout.items" :key="i" v-html="item"></li>
                  </ul>
                </div>
              </div>
              <footer class="doc-footer">
                <span>数据来源：集团生产调度数据库 & 气象监测系统</span>
                <span>章节页码：1 / 5</span>
              </footer>
            </article>

            <!-- 右侧：4 大核心 KPI 卡片 + 经营对标柱图 -->
            <div class="evidence-pane">
              <div class="kpi-grid">
                <div class="kpi-card border-top-sky">
                  <div class="kpi-label">周期平均气温</div>
                  <div class="kpi-num">{{ reportState.weather?.avgTemp }} <small>℃</small></div>
                  <div class="kpi-footnote">
                    <div>同比：<strong :class="(reportState.weather?.yoyDiff || 0) < 0 ? 'text-rose' : 'text-emerald'">{{ (reportState.weather?.yoyDiff || 0) > 0 ? '+' : '' }}{{ reportState.weather?.yoyDiff }}℃</strong></div>
                    <div v-if="includePrev">环比：<strong class="text-amber">{{ (reportState.weather?.momDiff || 0) > 0 ? '+' : '' }}{{ reportState.weather?.momDiff }}℃</strong></div>
                  </div>
                </div>

                <div class="kpi-card border-top-amber">
                  <div class="kpi-label">集团标煤耗量</div>
                  <div class="kpi-num">{{ fmt(reportState.kpis?.coalTotal) }} <small>吨</small></div>
                  <div class="kpi-footnote">
                    <div>同比：<strong :class="reportState.kpis?.coalYoYRate?.startsWith('+') ? 'text-rose' : 'text-emerald'">{{ reportState.kpis?.coalYoYRate }}</strong></div>
                    <div v-if="includePrev">环比：<strong class="text-amber">{{ reportState.kpis?.coalMoMRate }}</strong></div>
                  </div>
                </div>

                <div class="kpi-card border-top-emerald">
                  <div class="kpi-label">集团直接收入</div>
                  <div class="kpi-num">{{ fmt(reportState.kpis?.revenueTotal) }} <small>万元</small></div>
                  <div class="kpi-footnote">
                    <div>同比：<strong class="text-emerald">{{ (reportState.kpis?.revenueYoYDiff || 0) >= 0 ? '+' : '' }}{{ fmt(reportState.kpis?.revenueYoYDiff) }}万 ({{ reportState.kpis?.revenueYoYRate }})</strong></div>
                    <div>同期：<strong class="text-muted">{{ fmt(reportState.kpis?.revenueSync) }} 万元</strong></div>
                  </div>
                </div>

                <div class="kpi-card border-top-indigo">
                  <div class="kpi-label">产销边际利润</div>
                  <div class="kpi-num">{{ fmt(reportState.kpis?.profitActual) }} <small>万元</small></div>
                  <div class="kpi-footnote">
                    <div>同比：<strong :class="(reportState.kpis?.profitYoYDiff || 0) >= 0 ? 'text-emerald' : 'text-amber'">{{ (reportState.kpis?.profitYoYDiff || 0) >= 0 ? '+' : '' }}{{ fmt(reportState.kpis?.profitYoYDiff) }}万 ({{ reportState.kpis?.profitYoYRate }})</strong></div>
                    <div>可比煤价：<strong class="text-muted">{{ fmt(reportState.kpis?.profitComparable) }} 万元</strong></div>
                  </div>
                </div>
              </div>

              <!-- 集团核心经营指标对比图（自适应高度与宽度） -->
              <div class="card chart-card flex-1">
                <div class="card-head">
                  <div>
                    <h3 class="card-title">集团核心经营指标多维对标概览</h3>
                    <p class="card-subtitle">次序：① 本期实际 → ② 本期计划 → ③ 去年同期 {{ includePrev ? '→ ④ 上期对照' : '' }}</p>
                  </div>
                  <span class="tag-badge">单位：万元 / 百吨</span>
                </div>
                <div ref="chartOverviewRef" class="chart-container"></div>
              </div>
            </div>
          </div>
        </section>

        <!-- 章节 1: 第二章 二、标煤耗量与外购热 -->
        <section v-show="currentSlide === 1" class="slide-panel">
          <div class="chapter-header theme-border-amber">
            <div class="ch-left">
              <span class="chapter-badge badge-amber">第二章 / 共五章</span>
              <div>
                <h2 class="chapter-title doc-serif-title">二、标煤耗量情况与各单位运行方式分析</h2>
                <p class="chapter-subtitle">左侧通报各单位炉机运行方式及增减归因，右侧展示四维对标柱图与标煤明细表</p>
              </div>
            </div>
            <div class="ch-right">
              <span class="info-pill pill-amber">可比口径标煤实际变动：<strong>{{ (reportState.kpis?.coalComparableInc || 0) > 0 ? '+' : '' }}{{ fmt(reportState.kpis?.coalComparableInc) }} 吨</strong></span>
            </div>
          </div>

          <div class="spread-grid">
            <article class="doc-reading-pane">
              <div class="doc-header">
                <span class="doc-tag badge-amber">会议宣读稿</span>
                <h3 class="doc-heading doc-serif-title">标煤耗量与运行方式正文</h3>
                <span class="doc-subtag">机炉方式 · 清洁热还原</span>
              </div>
              <div class="doc-body doc-scrollable">
                <p
                  v-for="(paragraph, i) in currentNarrative.paragraphs"
                  :key="i"
                  class="doc-paragraph"
                  v-html="paragraph"
                ></p>

                <div v-if="currentNarrative.callout" class="doc-callout">
                  <div class="callout-title">{{ currentNarrative.callout.title }}</div>
                  <ul class="callout-list">
                    <li v-for="(item, i) in currentNarrative.callout.items" :key="i" v-html="item"></li>
                  </ul>
                </div>
              </div>
              <footer class="doc-footer">
                <span>对应原简报：第一部分第2段及表1</span>
                <span>章节页码：2 / 5</span>
              </footer>
            </article>

            <div class="evidence-pane">
              <div class="card chart-card">
                <div class="card-head">
                  <h3 class="card-title">各主力单位标煤耗量对比图</h3>
                  <span class="card-subtitle">单位：吨（次序：本期 → 计划 → 同期 {{ includePrev ? '→ 上期' : '' }}）</span>
                </div>
                <div ref="chartCoalRef" class="chart-container"></div>
              </div>

              <!-- 表 1 -->
              <div class="card table-card flex-1">
                <div class="card-head">
                  <h3 class="card-title">表1：标煤耗量及外购热量情况明细表</h3>
                  <span class="card-subtitle">标煤单位：吨 | 庄河外购热单位：GJ</span>
                </div>
                <div class="table-responsive">
                  <table class="report-table">
                    <thead>
                      <tr>
                        <th>单位名称</th>
                        <th class="text-center">单位</th>
                        <th class="text-right">本期</th>
                        <th class="text-right text-sky">本期计划</th>
                        <th class="text-right">同期</th>
                        <th v-if="includePrev" class="text-right text-amber">上期</th>
                        <th class="text-right">同比增减</th>
                        <th class="text-right">同比增减率</th>
                        <th>运行备注</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="row in reportState.coalTable" :key="row.name" :class="{ 'row-total': row.isTotal, 'row-ext': row.isExtHeat }">
                        <td class="font-bold">{{ row.name }}</td>
                        <td class="text-center text-muted">{{ row.unit }}</td>
                        <td class="text-right font-bold">{{ fmt(row.curr) }}</td>
                        <td class="text-right text-sky">{{ fmt(row.plan) }}</td>
                        <td class="text-right">{{ fmt(row.sync) }}</td>
                        <td v-if="includePrev" class="text-right text-amber">{{ fmt(row.prev) }}</td>
                        <td class="text-right font-bold" :class="(row.yoy || 0) > 0 ? 'text-rose' : 'text-emerald'">{{ (row.yoy || 0) > 0 ? '+' : '' }}{{ fmt(row.yoy) }}</td>
                        <td class="text-right" :class="row.yoyRate?.startsWith('+') ? 'text-rose' : 'text-emerald'">{{ row.yoyRate }}</td>
                        <td class="text-muted text-xs">{{ row.note || '—' }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- 章节 2: 第三章 三、产销边际利润 -->
        <section v-show="currentSlide === 2" class="slide-panel">
          <div class="chapter-header theme-border-emerald">
            <div class="ch-left">
              <span class="chapter-badge badge-emerald">第三章 / 共五章</span>
              <div>
                <h2 class="chapter-title doc-serif-title">三、直接收入、成本拆解与产销边际利润分析</h2>
                <p class="chapter-subtitle">左侧呈现收入增量、边际利润四大归因，右侧为对标图与树状明细对标表</p>
              </div>
            </div>
            <div class="ch-right">
              <span class="info-pill pill-emerald">实际边际利润：<strong>{{ fmt(reportState.kpis?.profitActual) }} 万元</strong></span>
              <span class="info-pill pill-indigo">可比煤价利润：<strong>{{ fmt(reportState.kpis?.profitComparable) }} 万元</strong></span>
            </div>
          </div>

          <div class="spread-grid">
            <article class="doc-reading-pane">
              <div class="doc-header">
                <span class="doc-tag badge-emerald">会议宣读稿</span>
                <h3 class="doc-heading doc-serif-title">收入成本归因与边际利润正文</h3>
                <span class="doc-subtag">四大要素拆解 · 真实利润驱动</span>
              </div>
              <div class="doc-body doc-scrollable">
                <p
                  v-for="(paragraph, i) in currentNarrative.paragraphs"
                  :key="i"
                  class="doc-paragraph"
                  v-html="paragraph"
                ></p>

                <div v-if="currentNarrative.callout" class="doc-callout">
                  <div class="callout-title">{{ currentNarrative.callout.title }}</div>
                  <ul class="callout-list">
                    <li v-for="(item, i) in currentNarrative.callout.items" :key="i" v-html="item"></li>
                  </ul>
                </div>
              </div>
              <footer class="doc-footer">
                <span>对应原简报：第一部分第3-5段及表2</span>
                <span>章节页码：3 / 5</span>
              </footer>
            </article>

            <div class="evidence-pane">
              <div class="card chart-card">
                <div class="card-head">
                  <h3 class="card-title">收入、成本与边际利润结构对比图</h3>
                  <span class="card-subtitle">单位：万元（本期 vs 计划 vs 同期）</span>
                </div>
                <div ref="chartProfitRef" class="chart-container"></div>
              </div>

              <!-- 表 2：树状层级明细表 -->
              <div class="card table-card flex-1">
                <div class="card-head">
                  <h3 class="card-title">表2：集团产销边际利润及分单位可比煤价边际利润表</h3>
                  <span class="card-subtitle">单位：万元</span>
                </div>
                <div class="table-responsive">
                  <table class="report-table">
                    <thead>
                      <tr>
                        <th>项目名称</th>
                        <th class="text-center">单位</th>
                        <th class="text-right">本期</th>
                        <th class="text-right text-sky">本期计划</th>
                        <th class="text-right">同期</th>
                        <th v-if="includePrev" class="text-right text-amber">上期</th>
                        <th class="text-right">同比增减</th>
                        <th class="text-right">同比差异率</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="row in reportState.profitTable"
                        :key="row.name"
                        :class="{
                          'row-header': row.isHeader,
                          'row-sub': row.isSub,
                          'row-total': row.isTotal,
                          'row-unit-comp': row.isUnitComp
                        }"
                      >
                        <td :style="{ paddingLeft: row.isSub ? '24px' : row.isUnitComp ? '18px' : '8px' }">
                          <span v-if="row.isSub" class="sub-indicator">└ </span>
                          <span :class="{ 'font-bold': row.isHeader || row.isTotal }">{{ row.name }}</span>
                        </td>
                        <td class="text-center text-muted">{{ row.unit }}</td>
                        <td class="text-right font-bold">{{ fmt(row.curr) }}</td>
                        <td class="text-right text-sky">{{ fmt(row.plan) }}</td>
                        <td class="text-right">{{ fmt(row.sync) }}</td>
                        <td v-if="includePrev" class="text-right text-amber">{{ fmt(row.prev) }}</td>
                        <td class="text-right font-bold" :class="(row.yoy || 0) > 0 ? (row.isHeader && row.name.includes('成本') ? 'text-rose' : 'text-emerald') : 'text-amber'">
                          {{ (row.yoy || 0) > 0 ? '+' : '' }}{{ fmt(row.yoy) }}
                        </td>
                        <td class="text-right">{{ row.rate }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- 章节 3: 第四章 四、供暖三项单耗 -->
        <section v-show="currentSlide === 3" class="slide-panel">
          <div class="chapter-header theme-border-indigo">
            <div class="ch-left">
              <span class="chapter-badge badge-indigo">第四章 / 共五章</span>
              <div>
                <h2 class="chapter-title doc-serif-title">四、供暖热、电、水三项单耗分单位对标与管网查漏预警</h2>
                <p class="chapter-subtitle">左侧为热/电/水单耗点评与一次网防失水督办，右侧支持热、电、水视图一键切换</p>
              </div>
            </div>
            <!-- 三项单耗切换 Tabs -->
            <div class="unit-tabs">
              <button
                v-for="t in [
                  { key: 'heat', label: '热单耗 (GJ/万㎡)' },
                  { key: 'elec', label: '电单耗 (kWh/万㎡)' },
                  { key: 'water', label: '水单耗 (吨/万㎡)' }
                ]"
                :key="t.key"
                class="btn-unit-tab"
                :class="{ active: activeUnitTab === t.key }"
                @click="switchUnitTab(t.key)"
              >
                {{ t.label }}
              </button>
            </div>
          </div>

          <div class="spread-grid">
            <article class="doc-reading-pane">
              <div class="doc-header">
                <span class="doc-tag badge-indigo">会议宣读稿</span>
                <h3 class="doc-heading doc-serif-title">单耗诊断与查漏预警正文</h3>
                <span class="doc-subtag">管网安全 · 精准对标</span>
              </div>
              <div class="doc-body doc-scrollable">
                <p
                  v-for="(paragraph, i) in currentNarrative.paragraphs"
                  :key="i"
                  class="doc-paragraph"
                  v-html="paragraph"
                ></p>

                <div v-if="currentNarrative.callout" class="doc-callout">
                  <div class="callout-title">{{ currentNarrative.callout.title }}</div>
                  <ul class="callout-list">
                    <li v-for="(item, i) in currentNarrative.callout.items" :key="i" v-html="item"></li>
                  </ul>
                </div>
              </div>
              <footer class="doc-footer">
                <span>对应原简报：表3、表4、表5及单耗诊断正文</span>
                <span>章节页码：4 / 5</span>
              </footer>
            </article>

            <div class="evidence-pane">
              <div class="card chart-card">
                <div class="card-head">
                  <h3 class="card-title">{{ currentUnitData.title }}</h3>
                  <span class="card-subtitle">单位：{{ currentUnitData.unit }}（注：电锅炉等极端值已在图表中做合理适配）</span>
                </div>
                <div ref="chartUnitRef" class="chart-container"></div>
              </div>

              <div class="card table-card flex-1">
                <div class="card-head">
                  <h3 class="card-title">{{ currentUnitData.title }}</h3>
                  <span class="card-subtitle">点击右上角按钮可切换 热 / 电 / 水 视图</span>
                </div>
                <div class="table-responsive">
                  <table class="report-table">
                    <thead>
                      <tr>
                        <th>单位名称</th>
                        <th class="text-right">本期</th>
                        <th class="text-right text-sky">本期计划</th>
                        <th class="text-right">同期</th>
                        <th v-if="includePrev" class="text-right text-amber">上期</th>
                        <th class="text-right">同比差异</th>
                        <th class="text-right">同比增减率</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="row in currentUnitData.rows" :key="row.name" :class="{ 'row-total': row.isTotal }">
                        <td class="font-bold">{{ row.name }}</td>
                        <td class="text-right font-bold">{{ fmt(row.curr) }}</td>
                        <td class="text-right text-sky">{{ fmt(row.plan) }}</td>
                        <td class="text-right">{{ fmt(row.sync) }}</td>
                        <td v-if="includePrev" class="text-right text-amber">{{ fmt(row.prev) }}</td>
                        <td class="text-right font-bold" :class="(row.diff || 0) > 0 ? 'text-rose' : 'text-emerald'">
                          {{ (row.diff || 0) > 0 ? '+' : '' }}{{ fmt(row.diff) }}
                        </td>
                        <td class="text-right" :class="row.rate?.startsWith('+') ? 'text-rose' : 'text-emerald'">{{ row.rate }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- 章节 4: 第五章 五、月度计划与工作展望 -->
        <section v-show="currentSlide === 4" class="slide-panel">
          <div class="chapter-header theme-border-rose">
            <div class="ch-left">
              <span class="chapter-badge badge-rose">第五章 / 共五章</span>
              <div>
                <h2 class="chapter-title doc-serif-title">五、月度标煤与外购热计划完成进度及下周工作展望</h2>
                <p class="chapter-subtitle">左侧为控煤达标研判与下周核心调度指令，右侧为计划执行图表与剩余日均额度表</p>
              </div>
            </div>
            <div class="ch-right">
              <span class="info-pill pill-rose">月度预警：控煤目标任务紧迫，需强化气温联动精准调控</span>
            </div>
          </div>

          <div class="spread-grid">
            <article class="doc-reading-pane">
              <div class="doc-header">
                <span class="doc-tag badge-rose">会议宣读稿</span>
                <h3 class="doc-heading doc-serif-title">月度完成研判与调度展望正文</h3>
                <span class="doc-subtag">进度督办 · 调度指令</span>
              </div>
              <div class="doc-body doc-scrollable">
                <p
                  v-for="(paragraph, i) in currentNarrative.paragraphs"
                  :key="i"
                  class="doc-paragraph"
                  v-html="paragraph"
                ></p>

                <div v-if="currentNarrative.callout" class="doc-callout">
                  <div class="callout-title">{{ currentNarrative.callout.title }}</div>
                  <ol class="callout-ordered-list">
                    <li v-for="(item, i) in currentNarrative.callout.items" :key="i" v-html="item"></li>
                  </ol>
                  <div class="callout-signature">
                    经济运行部 · 生产调度中心
                  </div>
                </div>
              </div>
              <footer class="doc-footer">
                <span>对应原简报：表6、下周展望正文及工作部署</span>
                <span>章节页码：5 / 5</span>
              </footer>
            </article>

            <div class="evidence-pane">
              <div class="card chart-card">
                <div class="card-head">
                  <h3 class="card-title">月度累计已完成 vs 月度计划对比图</h3>
                  <span class="card-subtitle">单位：吨（标煤）</span>
                </div>
                <div ref="chartPlanRef" class="chart-container"></div>
              </div>

              <!-- 表 6：月度计划完成情况表 -->
              <div class="card table-card flex-1">
                <div class="card-head">
                  <h3 class="card-title">表6：标煤耗量与外购热量计划完成情况表</h3>
                  <span class="card-subtitle">剩余日均 = (月计划 - 已完成) ÷ 月内剩余天数</span>
                </div>
                <div class="table-responsive">
                  <table class="report-table">
                    <thead>
                      <tr>
                        <th>考核单位</th>
                        <th class="text-center">单位</th>
                        <th class="text-right text-sky">月计划</th>
                        <th class="text-right">已完成(月累)</th>
                        <th class="text-right">剩余日均可用</th>
                        <th style="width: 140px;">月度耗用进度</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="row in reportState.monthlyPlan" :key="row.name" :class="{ 'row-total': row.isTotal }">
                        <td class="font-bold">{{ row.name }}</td>
                        <td class="text-center text-muted">{{ row.unit }}</td>
                        <td class="text-right text-sky font-bold">{{ fmt(row.plan) }}</td>
                        <td class="text-right font-bold">{{ fmt(row.done) }}</td>
                        <td class="text-right" :class="Number(row.remDaily) < 0 ? 'text-rose font-bold' : ''">
                          {{ fmt(row.remDaily) }}
                        </td>
                        <td>
                          <div class="progress-box">
                            <div class="progress-bar-bg">
                              <div
                                class="progress-bar-fill"
                                :class="row.percent > 90 ? 'fill-rose' : row.percent > 80 ? 'fill-amber' : 'fill-sky'"
                                :style="{ width: `${Math.min(100, row.percent || 0)}%` }"
                              ></div>
                            </div>
                            <span class="progress-text">{{ row.percent != null ? `${row.percent}%` : '—' }}</span>
                          </div>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </section>

      </main>
    </div>

    <!-- ==================== 3. 底部翻页控制栏 ==================== -->
    <footer class="report-footer">
      <div class="footer-inner">
        <div class="footer-left">
          <span class="page-indicator">第 {{ currentSlide + 1 }} / 5 页</span>
          <span class="footer-hint">支持键盘 <kbd>←</kbd> <kbd>→</kbd> 方向键翻页 · 全屏下按 <kbd>ESC</kbd> 退出全屏</span>
        </div>

        <!-- 5 个圆点指示器 -->
        <div class="footer-center">
          <button
            v-for="(name, idx) in chapters"
            :key="idx"
            class="slide-dot"
            :class="{ active: currentSlide === idx }"
            :title="`跳转至第 ${idx + 1} 章：${name}`"
            @click="currentSlide = idx"
          ></button>
        </div>

        <div class="footer-right">
          <button class="btn-page" :disabled="currentSlide === 0" @click="currentSlide--">← 上一章</button>
          <button class="btn-page btn-page-next" :disabled="currentSlide === 4" @click="currentSlide++">下一章 →</button>
        </div>
      </div>
    </footer>

    <!-- ==================== 弹窗：数据源 JSON 查看 ==================== -->
    <div v-if="showJsonModal" class="modal-mask" @click.self="showJsonModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <div>
            <h3 class="modal-title">平台自动化 JSON 数据契约</h3>
            <p class="modal-subtitle">当前加载的数据对象结构（含本期、计划、同期与上期数据）</p>
          </div>
          <button class="btn-close" @click="showJsonModal = false">✕</button>
        </div>
        <pre class="json-viewer">{{ JSON.stringify(reportState, null, 2) }}</pre>
        <div class="modal-footer">
          <button class="btn-tool" @click="copyJson">复制 JSON</button>
          <button class="btn-primary" @click="showJsonModal = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { fetchPeriodReport } from '../services/api'
import {
  REPORT_CHAPTERS as chapters,
  reportNumber as fmt,
  assemblePeriodPresentation,
  DEFAULT_PERIOD_MOCK,
  generateChapterNarrative
} from '../composables/periodReportPresentation'

// 基础响应式状态
const start = ref('')
const end = ref('')
const includePrev = ref(true)
const loading = ref(false)
const error = ref('')
const currentSlide = ref(0)
const activeUnitTab = ref('heat')
const isDark = ref(false)
const isFullscreen = ref(false)
const zoomLevel = ref(100)
const showJsonModal = ref(false)

// 视图展示数据
const reportState = ref(DEFAULT_PERIOD_MOCK)

// DOM 引用
const viewportRef = ref(null)
const chartOverviewRef = ref(null)
const chartCoalRef = ref(null)
const chartProfitRef = ref(null)
const chartUnitRef = ref(null)
const chartPlanRef = ref(null)

// ECharts 实例缓存与 ResizeObserver
let chartOverviewInstance = null
let chartCoalInstance = null
let chartProfitInstance = null
let chartUnitInstance = null
let chartPlanInstance = null
let resizeObserver = null

// 当前激活的单耗数据集
const currentUnitData = computed(() => {
  return reportState.value?.unitConsumption?.[activeUnitTab.value] || DEFAULT_PERIOD_MOCK.unitConsumption.heat
})

// 当前章节的自适应公文正文与解读卡片
const currentNarrative = computed(() => {
  if (reportState.value?.narrative?.chapters?.[currentSlide.value]) {
    return reportState.value.narrative.chapters[currentSlide.value]
  }
  const defaultN = generateChapterNarrative(reportState.value)
  return defaultN.chapters[currentSlide.value] || { paragraphs: [], callout: null }
})

// 缩放步进调整
function changeZoom(delta) {
  zoomLevel.value = Math.max(70, Math.min(130, zoomLevel.value + delta))
}

// 单耗 Tab 切换
function switchUnitTab(key) {
  activeUnitTab.value = key
  nextTick(() => {
    drawUnitChart()
  })
}

// 全屏控制与全屏变化监听
async function toggleFullscreen() {
  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen()
    } else {
      await document.documentElement.requestFullscreen()
    }
  } catch {
    error.value = '浏览器未允许全屏，请直接按键盘 F11 切换全屏'
  }
}

function handleFullscreenChange() {
  isFullscreen.value = Boolean(document.fullscreenElement)
  nextTick(() => {
    handleResize()
  })
}

// 下载纯文稿材料
function downloadReport() {
  const lines = [
    `【生产运行调度汇报材料】`,
    `统计区间：${reportState.value.meta?.start || start.value} 至 ${reportState.value.meta?.end || end.value}`,
    `汇报部门：${reportState.value.meta?.department || '经济运行部'}`,
    `生成日期：${reportState.value.meta?.reportDate || new Date().toLocaleDateString('zh-CN')}\n`
  ]

  const narr = reportState.value.narrative || generateChapterNarrative(reportState.value)
  narr.chapters.forEach((ch, idx) => {
    lines.push(`\n${ch.title}：`)
    ch.paragraphs.forEach(p => {
      lines.push(p.replace(/<[^>]+>/g, ''))
    })
    if (ch.callout) {
      lines.push(ch.callout.title)
      ch.callout.items.forEach(it => {
        lines.push('• ' + it.replace(/<[^>]+>/g, ''))
      })
    }
  })

  const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `生产运行调度汇报讲稿_${reportState.value.meta?.start || '周期'}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

function copyJson() {
  navigator.clipboard.writeText(JSON.stringify(reportState.value, null, 2))
  alert('已复制 JSON 数据至剪贴板')
}

// ==================== 图表绘制体系（ECharts） ====================
function getChartColors() {
  return isDark.value
    ? {
        text: '#cbd5e1',
        grid: 'rgba(71, 85, 105, 0.3)',
        bar1: '#38bdf8',
        bar2: '#34d399',
        bar3: '#a78bfa',
        bar4: '#fbbf24'
      }
    : {
        text: '#475569',
        grid: 'rgba(226, 232, 240, 0.8)',
        bar1: '#0284c7',
        bar2: '#10b981',
        bar3: '#6366f1',
        bar4: '#f59e0b'
      }
}

// 1. 概况四维图
function drawOverviewChart() {
  if (!chartOverviewRef.value) return
  chartOverviewInstance?.dispose()
  chartOverviewInstance = echarts.init(chartOverviewRef.value)

  const c = getChartColors()
  const hasPrev = includePrev.value
  const categories = ['标煤耗量(百吨)', '直接收入', '直接成本', '实际边际利润', '可比煤价利润']
  const k = reportState.value.kpis || {}

  const coalCur = k.coalTotal ? Math.round(k.coalTotal / 100) : 565
  const coalPlan = k.coalPlan ? Math.round(k.coalPlan / 100) : 459
  const coalSync = k.coalSync ? Math.round(k.coalSync / 100) : 392
  const coalPrev = k.coalPrev ? Math.round(k.coalPrev / 100) : 456

  const series = [
    {
      name: '本期实际',
      type: 'bar',
      barMaxWidth: 28,
      itemStyle: { color: c.bar1, borderRadius: [4, 4, 0, 0] },
      data: [coalCur, k.revenueTotal, 5588, k.profitActual, k.profitComparable]
    },
    {
      name: '本期计划',
      type: 'bar',
      barMaxWidth: 28,
      itemStyle: { color: c.bar4, borderRadius: [4, 4, 0, 0] },
      data: [coalPlan, k.revenuePlan || 7850, 5000, k.profitPlan || 2850, 2650]
    },
    {
      name: '去年同期',
      type: 'bar',
      barMaxWidth: 28,
      itemStyle: { color: c.bar2, borderRadius: [4, 4, 0, 0] },
      data: [coalSync, k.revenueSync, 4627, k.profitSync, 3211]
    }
  ]

  if (hasPrev) {
    series.push({
      name: '上期数值',
      type: 'bar',
      barMaxWidth: 28,
      itemStyle: { color: c.bar3, borderRadius: [4, 4, 0, 0] },
      data: [coalPrev, k.revenuePrev, 4740, k.profitPrev, 2150]
    })
  }

  chartOverviewInstance.setOption({
    animation: false,
    tooltip: { trigger: 'axis' },
    legend: { textStyle: { color: c.text, fontSize: 12 }, top: 0 },
    grid: { left: 45, right: 15, top: 35, bottom: 25 },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: { color: c.text, fontSize: 12 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: c.text, fontSize: 11 },
      splitLine: { lineStyle: { color: c.grid } }
    },
    series
  })
}

// 2. 标煤对比图
function drawCoalChart() {
  if (!chartCoalRef.value) return
  chartCoalInstance?.dispose()
  chartCoalInstance = echarts.init(chartCoalRef.value)

  const c = getChartColors()
  const rows = (reportState.value.coalTable || []).filter(r => !r.isTotal && !r.isExtHeat)
  const names = rows.map(r => r.name)
  const hasPrev = includePrev.value

  const series = [
    {
      name: '本期实际',
      type: 'bar',
      barMaxWidth: 24,
      itemStyle: { color: c.bar1, borderRadius: [4, 4, 0, 0] },
      data: rows.map(r => r.curr)
    },
    {
      name: '本期计划',
      type: 'bar',
      barMaxWidth: 24,
      itemStyle: { color: c.bar4, borderRadius: [4, 4, 0, 0] },
      data: rows.map(r => r.plan)
    },
    {
      name: '去年同期',
      type: 'bar',
      barMaxWidth: 24,
      itemStyle: { color: c.bar2, borderRadius: [4, 4, 0, 0] },
      data: rows.map(r => r.sync)
    }
  ]

  if (hasPrev) {
    series.push({
      name: '上期对照',
      type: 'bar',
      barMaxWidth: 24,
      itemStyle: { color: c.bar3, borderRadius: [4, 4, 0, 0] },
      data: rows.map(r => r.prev)
    })
  }

  chartCoalInstance.setOption({
    animation: false,
    tooltip: { trigger: 'axis' },
    legend: { textStyle: { color: c.text, fontSize: 12 }, top: 0 },
    grid: { left: 55, right: 15, top: 35, bottom: 25 },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: { color: c.text, fontSize: 12 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: c.text, fontSize: 11 },
      splitLine: { lineStyle: { color: c.grid } }
    },
    series
  })
}

// 3. 产销边际利润图
function drawProfitChart() {
  if (!chartProfitRef.value) return
  chartProfitInstance?.dispose()
  chartProfitInstance = echarts.init(chartProfitRef.value)

  const c = getChartColors()
  const rows = (reportState.value.profitTable || []).filter(r => r.inChart)
  const names = rows.map(r => r.name.replace('产销边际利润（实际）', '实际利润').replace('可比煤价边际利润（集团）', '可比利润'))

  const series = [
    {
      name: '本期实际',
      type: 'bar',
      barMaxWidth: 24,
      itemStyle: { color: c.bar1, borderRadius: [4, 4, 0, 0] },
      data: rows.map(r => r.curr)
    },
    {
      name: '计划基准',
      type: 'bar',
      barMaxWidth: 24,
      itemStyle: { color: c.bar4, borderRadius: [4, 4, 0, 0] },
      data: rows.map(r => r.plan)
    },
    {
      name: '去年同期',
      type: 'bar',
      barMaxWidth: 24,
      itemStyle: { color: c.bar2, borderRadius: [4, 4, 0, 0] },
      data: rows.map(r => r.sync)
    }
  ]

  if (includePrev.value) {
    series.push({
      name: '上期数值',
      type: 'bar',
      barMaxWidth: 24,
      itemStyle: { color: c.bar3, borderRadius: [4, 4, 0, 0] },
      data: rows.map(r => r.prev)
    })
  }

  chartProfitInstance.setOption({
    animation: false,
    tooltip: { trigger: 'axis' },
    legend: { textStyle: { color: c.text, fontSize: 12 }, top: 0 },
    grid: { left: 55, right: 15, top: 35, bottom: 25 },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: { color: c.text, fontSize: 12 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: c.text, fontSize: 11 },
      splitLine: { lineStyle: { color: c.grid } }
    },
    series
  })
}

// 4. 三项单耗图
function drawUnitChart() {
  if (!chartUnitRef.value) return
  chartUnitInstance?.dispose()
  chartUnitInstance = echarts.init(chartUnitRef.value)

  const c = getChartColors()
  const rows = (currentUnitData.value.rows || []).filter(r => !r.isTotal && !r.excludeFromChart)
  const names = rows.map(r => r.name)

  const series = [
    {
      name: '本期单耗',
      type: 'bar',
      barMaxWidth: 24,
      itemStyle: { color: c.bar1, borderRadius: [4, 4, 0, 0] },
      data: rows.map(r => r.curr)
    },
    {
      name: '计划基准',
      type: 'bar',
      barMaxWidth: 24,
      itemStyle: { color: c.bar4, borderRadius: [4, 4, 0, 0] },
      data: rows.map(r => r.plan)
    },
    {
      name: '同期单耗',
      type: 'bar',
      barMaxWidth: 24,
      itemStyle: { color: c.bar2, borderRadius: [4, 4, 0, 0] },
      data: rows.map(r => r.sync)
    }
  ]

  if (includePrev.value) {
    series.push({
      name: '上期单耗',
      type: 'bar',
      barMaxWidth: 24,
      itemStyle: { color: c.bar3, borderRadius: [4, 4, 0, 0] },
      data: rows.map(r => r.prev)
    })
  }

  chartUnitInstance.setOption({
    animation: false,
    tooltip: { trigger: 'axis' },
    legend: { textStyle: { color: c.text, fontSize: 12 }, top: 0 },
    grid: { left: 55, right: 15, top: 35, bottom: 25 },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: { color: c.text, fontSize: 12 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: c.text, fontSize: 11 },
      splitLine: { lineStyle: { color: c.grid } }
    },
    series
  })
}

// 5. 月度计划柱图
function drawPlanChart() {
  if (!chartPlanRef.value) return
  chartPlanInstance?.dispose()
  chartPlanInstance = echarts.init(chartPlanRef.value)

  const c = getChartColors()
  const rows = (reportState.value.monthlyPlan || []).filter(r => !r.isTotal && r.unit === '吨')
  const names = rows.map(r => r.name)

  chartPlanInstance.setOption({
    animation: false,
    tooltip: { trigger: 'axis' },
    legend: { textStyle: { color: c.text, fontSize: 12 }, top: 0 },
    grid: { left: 55, right: 15, top: 35, bottom: 25 },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: { color: c.text, fontSize: 12 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: c.text, fontSize: 11 },
      splitLine: { lineStyle: { color: c.grid } }
    },
    series: [
      {
        name: '累计已完成',
        type: 'bar',
        barMaxWidth: 26,
        itemStyle: { color: c.bar1, borderRadius: [4, 4, 0, 0] },
        data: rows.map(r => r.done)
      },
      {
        name: '月度计划额度',
        type: 'bar',
        barMaxWidth: 26,
        itemStyle: { color: c.bar4, borderRadius: [4, 4, 0, 0] },
        data: rows.map(r => r.plan)
      }
    ]
  })
}

function renderCurrentSlideChart() {
  nextTick(() => {
    if (currentSlide.value === 0) drawOverviewChart()
    else if (currentSlide.value === 1) drawCoalChart()
    else if (currentSlide.value === 2) drawProfitChart()
    else if (currentSlide.value === 3) drawUnitChart()
    else if (currentSlide.value === 4) drawPlanChart()
  })
}

// ==================== 接口交互与生命周期 ====================
async function generateReport() {
  error.value = ''
  if (!start.value || !end.value) {
    error.value = '请选择完整的开始与结束日期'
    return
  }
  if (start.value > end.value) {
    error.value = '开始日期不能晚于结束日期'
    return
  }

  loading.value = true
  try {
    const rawData = await fetchPeriodReport({
      start: start.value,
      end: end.value,
      include_prev: String(includePrev.value)
    })
    reportState.value = assemblePeriodPresentation(rawData)
    currentSlide.value = 0
    renderCurrentSlideChart()
  } catch (err) {
    error.value = err.message || '获取周期分析数据失败'
  } finally {
    loading.value = false
  }
}

function handleKeydown(event) {
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName)) return
  if (event.key === 'ArrowRight' && currentSlide.value < 4) {
    event.preventDefault()
    currentSlide.value++
  } else if (event.key === 'ArrowLeft' && currentSlide.value > 0) {
    event.preventDefault()
    currentSlide.value--
  }
}

function handleResize() {
  chartOverviewInstance?.resize()
  chartCoalInstance?.resize()
  chartProfitInstance?.resize()
  chartUnitInstance?.resize()
  chartPlanInstance?.resize()
}

watch(currentSlide, () => {
  renderCurrentSlideChart()
})

watch([isDark, includePrev], () => {
  renderCurrentSlideChart()
})

onMounted(async () => {
  window.addEventListener('keydown', handleKeydown)
  window.addEventListener('resize', handleResize)
  document.addEventListener('fullscreenchange', handleFullscreenChange)

  // 绑定 ResizeObserver 实时监听视口尺寸，确保在任何分辨率伸缩时图表完全贴合
  if (viewportRef.value && window.ResizeObserver) {
    resizeObserver = new ResizeObserver(() => {
      handleResize()
    })
    resizeObserver.observe(viewportRef.value)
  }

  // 默认数据初始化公文故事
  reportState.value.narrative = generateChapterNarrative(reportState.value)

  try {
    const meta = await fetchPeriodReport({})
    if (meta?.latestDate) {
      end.value = meta.latestDate
      const d = new Date(`${end.value}T12:00:00Z`)
      d.setUTCDate(d.getUTCDate() - 8)
      start.value = d.toISOString().slice(0, 10)
    } else {
      start.value = '2026-01-16'
      end.value = '2026-01-24'
    }
  } catch {
    start.value = '2026-01-16'
    end.value = '2026-01-24'
  }

  renderCurrentSlideChart()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('resize', handleResize)
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
  resizeObserver?.disconnect()
  chartOverviewInstance?.dispose()
  chartCoalInstance?.dispose()
  chartProfitInstance?.dispose()
  chartUnitInstance?.dispose()
  chartPlanInstance?.dispose()
})
</script>

<style scoped>
/* ==================== 整体设计系统与主题变量 ==================== */
.report-app {
  --bg-page: #f1f5f9;
  --bg-header: rgba(255, 255, 255, 0.96);
  --bg-card: #ffffff;
  --bg-sub: #f8fafc;
  --bg-doc-paper: #fffdf9;
  --border-color: #e2e8f0;
  --border-doc: #cbd5e1;
  --text-main: #0f172a;
  --text-secondary: #334155;
  --text-muted: #64748b;
  --accent-primary: #0284c7;
  --accent-bg: rgba(2, 132, 199, 0.08);
  --table-head-bg: #f8fafc;
  --table-row-hover: #f1f5f9;
  --table-total-bg: #eff6ff;
  --doc-highlight-bg: #fef3c7;
  --doc-highlight-text: #92400e;
  --shadow-card: 0 4px 20px -2px rgba(15, 23, 42, 0.06), 0 1px 3px 0 rgba(15, 23, 42, 0.04);

  background-color: var(--bg-page);
  color: var(--text-main);
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden; /* 桌面大屏满屏贴合，消除页面全局滚动白边 */
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
  transition: background-color 0.25s ease, color 0.25s ease;
}

/* 深色模式变量 */
.report-app.dark-theme {
  --bg-page: #070b14;
  --bg-header: rgba(15, 23, 42, 0.94);
  --bg-card: rgba(15, 23, 42, 0.88);
  --bg-sub: rgba(30, 41, 59, 0.65);
  --bg-doc-paper: rgba(15, 23, 42, 0.96);
  --border-color: rgba(51, 65, 85, 0.75);
  --border-doc: rgba(71, 85, 105, 0.8);
  --text-main: #f8fafc;
  --text-secondary: #cbd5e1;
  --text-muted: #94a3b8;
  --accent-primary: #38bdf8;
  --accent-bg: rgba(56, 189, 248, 0.12);
  --table-head-bg: rgba(30, 41, 59, 0.85);
  --table-row-hover: rgba(30, 41, 59, 0.45);
  --table-total-bg: rgba(14, 165, 233, 0.15);
  --doc-highlight-bg: rgba(245, 158, 11, 0.18);
  --doc-highlight-text: #fcd34d;
  --shadow-card: 0 10px 30px -10px rgba(0, 0, 0, 0.6);
}

/* ==================== 1. 顶部操作工具栏（全屏下隐藏，无宽度死卡） ==================== */
.top-toolbar {
  position: sticky;
  top: 0;
  z-index: 50;
  background-color: var(--bg-header);
  border-bottom: 1px solid var(--border-color);
  backdrop-filter: blur(12px);
  padding: 8px 24px;
  width: 100%;
  box-sizing: border-box;
  transition: all 0.25s ease;
}

.toolbar-inner {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-back {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  border-radius: 8px;
  background: var(--bg-sub);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  text-decoration: none;
  font-size: 12px;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-back:hover {
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

.toolbar-divider {
  width: 1px;
  height: 20px;
  background: var(--border-color);
}

.icon-svg {
  width: 14px;
  height: 14px;
}

.date-picker-box {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-sub);
  padding: 3px 8px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  font-size: 12px;
}

.date-label {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-muted);
}

.date-input {
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 2px 6px;
  color: var(--text-main);
  font-size: 12px;
  font-family: inherit;
}

.btn-primary {
  background: #0284c7;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #0369a1;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinner {
  width: 10px;
  height: 10px;
  border: 2px solid #fff;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.zoom-controller {
  display: flex;
  align-items: center;
  background: var(--bg-sub);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 2px 6px;
  font-size: 11px;
}

.zoom-text {
  color: var(--text-muted);
  margin-right: 4px;
}

.btn-zoom {
  background: transparent;
  border: none;
  color: var(--text-main);
  font-weight: bold;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
}

.btn-zoom:hover {
  background: var(--accent-bg);
  color: var(--accent-primary);
}

.zoom-value {
  font-weight: bold;
  color: var(--accent-primary);
  min-width: 38px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.btn-zoom-reset {
  background: var(--accent-bg);
  color: var(--accent-primary);
  border: none;
  border-radius: 4px;
  padding: 1px 5px;
  font-size: 10px;
  cursor: pointer;
  margin-left: 2px;
}

.btn-tool {
  background: var(--bg-sub);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 5px 10px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s;
}

.btn-tool:hover {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}

.btn-fullscreen-highlight {
  background: rgba(2, 132, 199, 0.1);
  color: #0284c7;
  border-color: rgba(2, 132, 199, 0.3);
}

.btn-fullscreen-highlight:hover {
  background: #0284c7;
  color: #fff;
}

.btn-toggle-prev.active {
  background: rgba(16, 185, 129, 0.12);
  border-color: rgba(16, 185, 129, 0.3);
  color: #047857;
}

.report-app.dark-theme .btn-toggle-prev.active {
  color: #34d399;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
}

.status-dot.dot-on {
  background: #10b981;
}

/* ==================== 2. 主舞台视口与满屏自适应排版 ==================== */
.report-viewport {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  transform-origin: top center;
  transition: zoom 0.15s ease;
  overflow: hidden;
}

.report-stage {
  width: 100%;
  flex: 1;
  min-height: 0;
  margin: 0;
  padding: 10px 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-sizing: border-box;
}

/* 全屏状态下边距微调以撑满大屏 */
.report-app.is-fullscreen .report-stage {
  padding: 14px 28px;
  gap: 12px;
}

/* 靠近主内容的“汇报标题与章节导航标签栏” */
.stage-nav-bar {
  width: 100%;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 8px 18px;
  box-shadow: var(--shadow-card);
}

.stage-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.stage-badge-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
}

.badge-season {
  background: var(--accent-bg);
  color: var(--accent-primary);
  border: 1px solid var(--accent-primary);
}

.badge-dept {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

.badge-period {
  font-size: 11px;
  padding: 1px 7px;
  background: var(--bg-sub);
  border-radius: 4px;
  color: var(--text-secondary);
}

.stage-main-title {
  font-size: 18px;
  font-weight: 800;
  margin: 0;
  color: var(--text-main);
  letter-spacing: -0.01em;
}

/* 章节标签栏（全屏下仍显现！） */
.chapter-nav-pills {
  display: flex;
  align-items: center;
  background: var(--bg-sub);
  padding: 3px;
  border-radius: 10px;
  border: 1px solid var(--border-color);
  gap: 3px;
}

.chapter-nav-pill {
  background: transparent;
  border: none;
  padding: 5px 14px;
  border-radius: 7px;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: all 0.2s ease;
}

.chapter-nav-pill:hover {
  color: var(--accent-primary);
}

.chapter-nav-pill.active {
  background: #0284c7;
  color: #fff;
  box-shadow: 0 2px 6px rgba(2, 132, 199, 0.35);
}

.pill-index {
  font-size: 11px;
  opacity: 0.85;
}

/* 章节滑块容器：充满剩余高度 */
.slide-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 章节头部 */
.chapter-header {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 10px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  box-shadow: var(--shadow-card);
}

.theme-border-sky { border-left: 5px solid #0284c7; }
.theme-border-amber { border-left: 5px solid #d97706; }
.theme-border-emerald { border-left: 5px solid #059669; }
.theme-border-indigo { border-left: 5px solid #4f46e5; }
.theme-border-rose { border-left: 5px solid #e11d48; }

.ch-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chapter-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 5px;
  color: #fff;
}

.badge-sky { background: #0284c7; }
.badge-amber { background: #d97706; }
.badge-emerald { background: #059669; }
.badge-indigo { background: #4f46e5; }
.badge-rose { background: #e11d48; }

.chapter-title {
  font-size: 16px;
  font-weight: 800;
  margin: 0;
  color: var(--text-main);
}

.chapter-subtitle {
  font-size: 11px;
  color: var(--text-muted);
  margin: 2px 0 0;
}

.ch-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.info-pill {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 6px;
  background: var(--bg-sub);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.pill-rose { background: rgba(244, 63, 94, 0.1); color: #e11d48; border-color: rgba(244, 63, 94, 0.2); }
.pill-emerald { background: rgba(16, 185, 129, 0.1); color: #059669; border-color: rgba(16, 185, 129, 0.2); }
.pill-amber { background: rgba(245, 158, 11, 0.1); color: #d97706; border-color: rgba(245, 158, 11, 0.2); }
.pill-indigo { background: rgba(99, 102, 241, 0.1); color: #4f46e5; border-color: rgba(99, 102, 241, 0.2); }

/* ==================== 双栏网格排版 (Spread Grid) 自适应拉宽填满 ==================== */
.spread-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 4.8fr 7.2fr;
  gap: 14px;
  align-items: stretch;
}

@media (max-width: 1024px) {
  .spread-grid {
    grid-template-columns: 1fr;
    overflow-y: auto;
  }
}

/* 左侧：Word 汇报材料精读区（自适应撑满高度） */
.doc-reading-pane {
  background-color: var(--bg-doc-paper);
  border: 1px solid var(--border-doc);
  border-radius: 14px;
  box-shadow: var(--shadow-card);
  padding: 16px 22px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  position: relative;
  height: 100%;
  box-sizing: border-box;
}

.doc-reading-pane::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  width: 4px;
  background: linear-gradient(180deg, #0284c7, #2563eb);
  border-top-left-radius: 14px;
  border-bottom-left-radius: 14px;
}

.doc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 10px;
}

.doc-tag {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 5px;
  background: #0284c7;
  color: #fff;
}

.doc-heading {
  font-size: 16px;
  font-weight: 700;
  margin: 0;
  color: var(--text-main);
}

.doc-subtag {
  font-size: 11px;
  color: var(--text-muted);
}

.doc-serif-title {
  font-family: "Noto Serif SC", "Songti SC", "SimSun", serif;
}

.doc-body {
  flex: 1;
  min-height: 0;
}

.doc-scrollable {
  overflow-y: auto;
  padding-right: 4px;
}

.doc-paragraph {
  font-family: "Noto Serif SC", "Songti SC", "SimSun", serif;
  text-indent: 2em;
  line-height: 1.85;
  font-size: 0.95rem;
  color: var(--text-secondary);
  margin: 0 0 10px;
  text-align: justify;
}

/* 数字高亮徽标 */
:deep(.doc-key-num) {
  font-family: inherit;
  font-weight: 700;
  background-color: var(--doc-highlight-bg);
  color: var(--doc-highlight-text);
  padding: 0.05rem 0.35rem;
  border-radius: 0.25rem;
  font-variant-numeric: tabular-nums;
}

/* 解读提炼框 */
.doc-callout {
  background: var(--bg-sub);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 12px;
  margin-top: 8px;
}

.callout-title {
  font-weight: 700;
  color: #0284c7;
  margin-bottom: 4px;
}

.callout-list, .callout-ordered-list {
  margin: 0;
  padding-left: 18px;
  color: var(--text-secondary);
  line-height: 1.65;
}

.callout-signature {
  text-align: right;
  font-weight: bold;
  margin-top: 6px;
  padding-top: 4px;
  border-top: 1px dashed var(--border-color);
  color: var(--text-muted);
}

.doc-footer {
  display: flex;
  justify-content: space-between;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 10px;
}

/* 右侧证据与数据面板（满高自适应，无多余纵向留白） */
.evidence-pane {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 14px;
  box-shadow: var(--shadow-card);
  padding: 12px 18px;
  box-sizing: border-box;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.card-title {
  font-size: 14px;
  font-weight: 700;
  margin: 0;
  color: var(--text-main);
}

.card-subtitle {
  font-size: 11px;
  color: var(--text-muted);
}

.tag-badge {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 5px;
  background: var(--accent-bg);
  color: var(--accent-primary);
  font-weight: 600;
}

/* KPI 卡片网格 */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

@media (max-width: 768px) {
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
}

.kpi-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 10px 14px;
  box-shadow: var(--shadow-card);
}

.border-top-sky { border-top: 4px solid #0284c7; }
.border-top-amber { border-top: 4px solid #d97706; }
.border-top-emerald { border-top: 4px solid #059669; }
.border-top-indigo { border-top: 4px solid #4f46e5; }

.kpi-label {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 600;
}

.kpi-num {
  font-size: 24px;
  font-weight: 800;
  color: var(--text-main);
  margin: 4px 0;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.kpi-num small {
  font-size: 12px;
  font-weight: normal;
  color: var(--text-muted);
}

.kpi-footnote {
  border-top: 1px solid var(--border-color);
  padding-top: 4px;
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.5;
}

/* 图表容器：自适应撑满剩余高度 */
.chart-card {
  flex: 1.1;
  min-height: 170px;
  display: flex;
  flex-direction: column;
}

.chart-container {
  flex: 1;
  min-height: 140px;
  width: 100%;
}

/* 表格卡片：自适应撑满剩余高度 */
.table-card {
  flex: 1.3;
  min-height: 180px;
  display: flex;
  flex-direction: column;
}

.table-responsive {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: auto;
}

.report-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.report-table th, .report-table td {
  padding: 7px 10px;
  border-bottom: 1px solid var(--border-color);
}

.report-table th {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--table-head-bg);
  color: var(--text-muted);
  font-weight: 600;
  text-align: left;
}

.report-table tr:hover {
  background: var(--table-row-hover);
}

.row-total {
  background: var(--table-total-bg);
  font-weight: 800;
}

.row-header {
  background: var(--table-head-bg);
  font-weight: 700;
  border-top: 1px solid var(--border-color);
}

.row-sub {
  color: var(--text-secondary);
}

.sub-indicator {
  color: var(--text-muted);
  margin-right: 2px;
}

.row-ext {
  color: #0284c7;
}

/* 进度条 */
.progress-box {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-bar-bg {
  flex: 1;
  height: 8px;
  background: var(--border-color);
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.fill-sky { background: #0284c7; }
.fill-amber { background: #d97706; }
.fill-rose { background: #e11d48; }

.progress-text {
  font-size: 11px;
  font-weight: bold;
  color: var(--text-main);
  min-width: 44px;
  text-align: right;
}

/* 单耗 Tabs */
.unit-tabs {
  display: flex;
  background: var(--bg-sub);
  padding: 3px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  gap: 3px;
}

.btn-unit-tab {
  background: transparent;
  border: none;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-unit-tab.active {
  background: #0284c7;
  color: #fff;
}

/* 辅助高亮类 */
.text-rose { color: #e11d48; }
.text-emerald { color: #059669; }
.text-amber { color: #d97706; }
.text-sky { color: #0284c7; }
.text-muted { color: var(--text-muted); }
.text-center { text-align: center; }
.text-right { text-align: right; }
.font-bold { font-weight: bold; }
.text-xs { font-size: 11px; }
.flex-1 { flex: 1; min-height: 0; }

/* ==================== 3. 底部翻页 Footer ==================== */
.report-footer {
  position: sticky;
  bottom: 0;
  z-index: 40;
  background-color: var(--bg-header);
  border-top: 1px solid var(--border-color);
  backdrop-filter: blur(12px);
  padding: 8px 24px;
  width: 100%;
  box-sizing: border-box;
}

.footer-inner {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-indicator {
  font-size: 12px;
  font-weight: 700;
  background: var(--bg-sub);
  padding: 3px 8px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  font-variant-numeric: tabular-nums;
}

.footer-hint {
  font-size: 11px;
  color: var(--text-muted);
}

kbd {
  background: var(--bg-sub);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 1px 4px;
  font-size: 10px;
  color: var(--text-main);
  font-family: inherit;
}

.footer-center {
  display: flex;
  align-items: center;
  gap: 8px;
}

.slide-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--border-color);
  border: none;
  cursor: pointer;
  padding: 0;
  transition: all 0.25s ease;
}

.slide-dot:hover {
  background: var(--text-muted);
}

.slide-dot.active {
  width: 24px;
  border-radius: 4px;
  background: #0284c7;
}

.footer-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-page {
  background: var(--bg-sub);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 5px 14px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-page:hover:not(:disabled) {
  border-color: #0284c7;
  color: #0284c7;
}

.btn-page-next {
  background: #0284c7;
  color: #fff;
  border-color: #0284c7;
}

.btn-page-next:hover:not(:disabled) {
  background: #0369a1;
  color: #fff;
}

.btn-page:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 错误与弹窗 */
.error-banner {
  background: #fee2e2;
  color: #991b1b;
  padding: 8px 16px;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.btn-close-error {
  background: none;
  border: none;
  color: #991b1b;
  cursor: pointer;
  font-weight: bold;
}

.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.7);
  backdrop-filter: blur(4px);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.modal-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  max-width: 900px;
  width: 100%;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  padding: 18px 22px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 12px;
}

.modal-title {
  font-size: 16px;
  font-weight: 800;
  margin: 0;
  color: var(--text-main);
}

.modal-subtitle {
  font-size: 11px;
  color: var(--text-muted);
  margin: 2px 0 0;
}

.btn-close {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: var(--text-muted);
}

.json-viewer {
  background: #090d16;
  color: #38bdf8;
  font-family: monospace;
  font-size: 11px;
  padding: 14px;
  border-radius: 8px;
  overflow: auto;
  flex: 1;
  margin: 14px 0;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  border-top: 1px solid var(--border-color);
  padding-top: 12px;
}

/* 宽屏超大分辨率优化（1680px、1920px、2560px 等，消除空旷留白，字号与图表呼吸感自适应放大，便于场下观看） */
@media (min-width: 1680px) {
  .stage-main-title { font-size: 20px; }
  .chapter-title { font-size: 17px; }
  .kpi-num { font-size: 26px; }
  .doc-paragraph { font-size: 1.02rem; line-height: 1.9; }
  .report-table { font-size: 13px; }
  .report-table th, .report-table td { padding: 8px 12px; }
}

@media (min-width: 1920px) {
  .report-stage { padding: 14px 32px; gap: 14px; }
  .stage-nav-bar { padding: 10px 22px; }
  .stage-main-title { font-size: 22px; }
  .chapter-nav-pill { font-size: 14px; padding: 6px 16px; }
  .chapter-title { font-size: 18px; }
  .kpi-num { font-size: 30px; }
  .doc-heading { font-size: 18px; }
  .doc-paragraph { font-size: 1.08rem; line-height: 2; margin-bottom: 12px; }
  .doc-callout { font-size: 13px; padding: 12px 16px; }
  .report-table { font-size: 13.5px; }
  .report-table th, .report-table td { padding: 9px 14px; }
}

@media (min-width: 2560px) {
  .report-stage { padding: 20px 48px; gap: 18px; }
  .stage-main-title { font-size: 26px; }
  .chapter-nav-pill { font-size: 16px; padding: 8px 20px; }
  .chapter-title { font-size: 22px; }
  .kpi-num { font-size: 36px; }
  .doc-heading { font-size: 22px; }
  .doc-paragraph { font-size: 1.2rem; line-height: 2.1; margin-bottom: 16px; }
  .doc-callout { font-size: 15px; padding: 16px 20px; }
  .report-table { font-size: 15px; }
  .report-table th, .report-table td { padding: 12px 18px; }
}
</style>
