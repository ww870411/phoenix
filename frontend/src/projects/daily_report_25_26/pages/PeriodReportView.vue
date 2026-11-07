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

          <!-- 控制台下拉菜单（Global_admin 全量可用，Group_admin 仅开放材料空间管理） -->
          <div v-if="canAccessConsole" ref="consoleDropdownRef" class="console-dropdown-container">
            <button
              class="btn-tool btn-console-trigger"
              :class="{ active: showConsoleDropdown }"
              @click.stop="toggleConsoleDropdown"
              :title="isGlobalAdmin ? '管理控制台（Global_admin）：数据导出、材料仓库、工作流保存与源数据查看' : '管理控制台（Group_admin）：材料空间管理'"
            >
              <span class="console-icon">⚙️</span>
              <span>控制台</span>
              <span class="dropdown-arrow" :class="{ rotated: showConsoleDropdown }">▾</span>
            </button>

            <!-- 下拉菜单浮层 -->
            <transition name="dropdown-fade">
              <div v-if="showConsoleDropdown" class="console-dropdown-menu">
                <div class="dropdown-header">
                  <span class="dropdown-tag">{{ isGlobalAdmin ? 'Global_admin' : 'Group_admin' }}</span>
                  <span class="dropdown-title">管理控制台</span>
                </div>

                <!-- 1. 材料空间（面向 Global_admin 与 Group_admin 均开放） -->
                <button
                  class="dropdown-item"
                  @click="closeConsoleDropdown(); openFileManager()"
                  title="打开 HTML 与 XLSX 汇报材料管理空间"
                >
                  <span class="item-icon">📁</span>
                  <div class="item-text">
                    <span class="item-title">材料空间管理</span>
                    <span class="item-desc">管理材料仓库中的文档与明细文件</span>
                  </div>
                </button>

                <!-- 2. 工作流目录空间（仅限 Global_admin） -->
                <button
                  v-if="isGlobalAdmin"
                  class="dropdown-item"
                  @click="closeConsoleDropdown(); openWorkflowManager()"
                  title="专门管理与浏览工作流目录下的规范文档、模板引擎与指导材料"
                >
                  <span class="item-icon">🗂️</span>
                  <div class="item-text">
                    <span class="item-title">工作流目录空间</span>
                    <span class="item-desc">管理工作流规范文档、模板引擎与资料</span>
                  </div>
                </button>

                <!-- 3. 保存至空间(HTML)（仅限 Global_admin） -->
                <button
                  v-if="isGlobalAdmin"
                  class="dropdown-item"
                  :disabled="savingHtml"
                  @click="closeConsoleDropdown(); saveCurrentReportToSpace()"
                  title="将当期分析汇报一键保存为独立 HTML 格式文件至材料仓库"
                >
                  <span class="item-icon">💾</span>
                  <div class="item-text">
                    <span class="item-title">{{ savingHtml ? '正在保存…' : '保存至空间 (HTML)' }}</span>
                    <span class="item-desc">生成自包含独立 HTML 演示汇报</span>
                  </div>
                </button>

                <!-- 4. 导出生产运行数据(XLSX)（仅限 Global_admin） -->
                <button
                  v-if="isGlobalAdmin"
                  class="dropdown-item"
                  @click="closeConsoleDropdown(); openExportXlsxModal()"
                  title="导出包含 4 个标准化 Sheet 的多维生产经营明细 XLSX 表格"
                >
                  <span class="item-icon">📊</span>
                  <div class="item-text">
                    <span class="item-title">导出数据 (XLSX)</span>
                    <span class="item-desc">生成 10 家主体 × 28 项指标全要素对标表</span>
                  </div>
                </button>

                <div v-if="isGlobalAdmin" class="dropdown-divider"></div>

                <!-- 5. 下载纯讲稿（仅限 Global_admin） -->
                <button
                  v-if="isGlobalAdmin"
                  class="dropdown-item"
                  @click="closeConsoleDropdown(); downloadReport()"
                  title="下载汇报各章节宣读公文纯文本"
                >
                  <span class="item-icon">📄</span>
                  <div class="item-text">
                    <span class="item-title">下载汇报讲稿</span>
                    <span class="item-desc">导出纯文本格式调度汇报发言稿</span>
                  </div>
                </button>

                <!-- 6. 数据源 JSON（仅限 Global_admin） -->
                <button
                  v-if="isGlobalAdmin"
                  class="dropdown-item"
                  @click="closeConsoleDropdown(); showJsonModal = true"
                  title="查看当前统计周期的底层结构化数据源"
                >
                  <span class="item-icon">🔍</span>
                  <div class="item-text">
                    <span class="item-title">底层数据源 (JSON)</span>
                    <span class="item-desc">查看前端接收到的多维计算源数据</span>
                  </div>
                </button>

                <!-- 7. 默认显示设定（仅限 Global_admin） -->
                <button
                  v-if="isGlobalAdmin"
                  class="dropdown-item"
                  @click="closeConsoleDropdown(); openDisplayConfigModal()"
                  title="设定生产运行汇报页面的默认打开内容（动态生成页或指定材料空间 HTML）"
                >
                  <span class="item-icon">⚙️</span>
                  <div class="item-text">
                    <span class="item-title">默认显示设定</span>
                    <span class="item-desc">指定首屏展示动态生成页或材料空间 HTML</span>
                  </div>
                </button>
              </div>
            </transition>
          </div>

          <!-- 模式切换快捷胶囊：当设定了默认 HTML 文档时，支持随手切换 -->
          <button
            v-if="displayConfig.mode === 'custom_html' && activeViewMode === 'generated'"
            class="btn-tool btn-back-custom"
            @click="activeViewMode = 'custom_html'"
            title="返回系统默认设定的材料空间文档展示"
          >
            <span>📌 查看默认材料文档</span>
          </button>
          <button
            v-else-if="activeViewMode === 'custom_html'"
            class="btn-tool btn-back-custom"
            @click="activeViewMode = 'generated'"
            title="切换回自选周期动态生成汇报视口"
          >
            <span>📊 切换至动态生成页</span>
          </button>
        </div>
      </div>
    </header>

    <!-- 错误横幅提示 -->
    <div v-if="error" class="error-banner" role="alert">
      <span>⚠️ {{ error }}</span>
      <button class="btn-close-error" @click="error = ''">✕</button>
    </div>

    <!-- ==================== 2.1 默认材料空间 HTML 视口（当设定为默认打开材料文档时呈现） ==================== -->
    <div v-if="activeViewMode === 'custom_html'" class="custom-html-stage">
      <div class="custom-html-banner">
        <div class="banner-left">
          <span class="badge-custom-tag">📌 默认材料文档</span>
          <span class="banner-filename">{{ displayConfig.target_file }}</span>
          <span v-if="displayConfig.updated_at" class="banner-time">更新于 {{ displayConfig.updated_at }}</span>
        </div>
        <div class="banner-right">
          <button class="btn-tool btn-highlight" @click="activeViewMode = 'generated'" title="切换查看系统自选周期的动态生成汇报分析">
            <span>📊 切换至动态生成汇报</span>
          </button>
          <button class="btn-tool" @click="openCustomHtmlInNewTab" title="在新浏览器标签页中全屏打开">
            <span>🔗 新标签页打开</span>
          </button>
          <button v-if="isGlobalAdmin" class="btn-tool" @click="openDisplayConfigModal" title="修改系统默认打开内容设置">
            <span>⚙️ 默认显示设置</span>
          </button>
        </div>
      </div>

      <div class="custom-html-container">
        <div v-if="customHtmlLoading" class="custom-loading-box">
          <div class="spinner spinner-lg"></div>
          <p class="mt-2">正在加载默认材料文档【{{ displayConfig.target_file }}】…</p>
        </div>
        <div v-else-if="customHtmlError" class="custom-error-box">
          <p>⚠️ {{ customHtmlError }}</p>
          <div class="mt-3 flex gap-2">
            <button class="btn-primary" @click="loadCustomHtml(displayConfig.target_file)">重试加载</button>
            <button class="btn-tool" @click="activeViewMode = 'generated'">切换至动态生成页</button>
          </div>
        </div>
        <iframe
          v-else
          ref="customHtmlIframeRef"
          :srcdoc="customHtmlContent"
          class="custom-html-frame"
          sandbox="allow-scripts allow-same-origin allow-popups"
        ></iframe>
      </div>
    </div>

    <!-- ==================== 2.2 动态生成汇报主舞台视口（全屏宽屏分辨率自适应，占满可用空间） ==================== -->
    <div v-else ref="viewportRef" class="report-viewport" :style="{ zoom: zoomLevel / 100 }">
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

    <!-- ==================== 弹窗：周期汇报与数据材料管理空间 ==================== -->
    <div v-if="showFileManagerModal" class="modal-mask" @click.self="showFileManagerModal = false">
      <div class="modal-card modal-card-space">
        <!-- 弹窗 Header -->
        <div class="modal-header space-modal-header">
          <div class="space-header-info">
            <div class="space-header-title-row">
              <span class="space-title-icon">📁</span>
              <h3 class="modal-title">周期汇报与数据材料仓库</h3>
              <span class="space-title-badge">空间中枢</span>
            </div>
            <p class="modal-subtitle">集中管理当期生产运行明细(XLSX)与汇报讲稿(HTML)，支持在线演示、一键下载与快速维护</p>
          </div>
          <button class="btn-close space-btn-close" title="关闭窗口" @click="showFileManagerModal = false">✕</button>
        </div>

        <!-- 空间工具栏与筛选栏 -->
        <div class="space-toolbar-row">
          <!-- 左侧操作与筛选 -->
          <div class="space-toolbar-left">
            <input
              ref="fileInputRef"
              type="file"
              accept=".html,.htm"
              style="display: none"
              @change="handleFileUpload"
            />
            <button class="btn-primary space-btn-upload" :disabled="uploadingFile" @click="triggerUpload">
              <span v-if="uploadingFile" class="spinner"></span>
              {{ uploadingFile ? '正在上传…' : '📤 上传材料' }}
            </button>
            <button class="btn-tool space-btn-refresh" :disabled="fileLoading" title="重新扫描并刷新仓库列表" @click="loadFiles">
              <span v-if="fileLoading" class="spinner"></span>
              {{ fileLoading ? '刷新中…' : '🔄 刷新' }}
            </button>
            <button class="btn-tool space-btn-folder" title="在材料仓库中创建子文件夹归档材料" @click="openNewFolderModalForSpace('material')">
              <span>📁 新建文件夹</span>
            </button>

            <!-- 分割线 -->
            <div class="space-toolbar-divider"></div>

            <!-- 分类药丸 Tab -->
            <div class="space-filter-pills">
              <button
                class="filter-pill"
                :class="{ active: fileTypeFilter === 'all' }"
                @click="fileTypeFilter = 'all'"
              >
                全部 <span class="pill-count">({{ fileStats.total }})</span>
              </button>
              <button
                class="filter-pill pill-excel"
                :class="{ active: fileTypeFilter === 'excel' }"
                @click="fileTypeFilter === 'excel'"
              >
                📊 数据明细 <span class="pill-count">({{ fileStats.excel }})</span>
              </button>
              <button
                class="filter-pill pill-report"
                :class="{ active: fileTypeFilter === 'report' }"
                @click="fileTypeFilter === 'report'"
              >
                📄 汇报讲稿 <span class="pill-count">({{ fileStats.report }})</span>
              </button>
              <button
                class="filter-pill pill-template"
                :class="{ active: fileTypeFilter === 'template' }"
                @click="fileTypeFilter === 'template'"
              >
                ⚙️ 系统母版 <span class="pill-count">({{ fileStats.template }})</span>
              </button>
            </div>
          </div>

          <!-- 右侧即时搜索框 -->
          <div class="space-toolbar-right">
            <div class="space-search-box">
              <span class="search-icon">🔍</span>
              <input
                v-model="fileSearchKeyword"
                type="text"
                class="space-search-input"
                placeholder="搜索材料文件名…"
              />
              <button
                v-if="fileSearchKeyword"
                class="search-clear-btn"
                title="清空搜索"
                @click="fileSearchKeyword = ''"
              >✕</button>
            </div>
          </div>
        </div>

        <!-- 文件表格卡片包裹 -->
        <div class="space-table-card">
          <div class="file-table-wrap space-table-scroll">
            <table class="report-table space-table">
              <thead>
                <tr>
                  <th style="width: 30%">文件材料名称</th>
                  <th style="width: 12%">分类属性</th>
                  <th style="width: 8%; text-align: center">大小</th>
                  <th style="width: 18%">时间信息 (东八区)</th>
                  <th style="width: 32%; text-align: right">操作动作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="fileLoading && fileList.length === 0">
                  <td colspan="5" class="space-empty-cell">
                    <div class="space-empty-box">
                      <span class="spinner" style="width: 24px; height: 24px"></span>
                      <span>正在扫描空间材料仓库…</span>
                    </div>
                  </td>
                </tr>
                <tr v-else-if="filteredFileList.length === 0">
                  <td colspan="5" class="space-empty-cell">
                    <div class="space-empty-box">
                      <span class="space-empty-icon">📂</span>
                      <p class="space-empty-title">
                        {{ fileSearchKeyword ? '未找到符合条件的材料文件' : '暂无相关汇报材料或生产数据明细' }}
                      </p>
                      <p class="space-empty-desc">
                        {{ fileSearchKeyword ? '可尝试缩短搜索词或切换分类筛选查看' : '您可点击上方“📤 上传材料”，或在控制台使用“导出数据(XLSX)”一键保存' }}
                      </p>
                    </div>
                  </td>
                </tr>
                <tr
                  v-for="item in filteredFileList"
                  :key="item.rel_path"
                  class="space-file-row"
                >
                  <!-- 1. 文件名称列 -->
                  <td>
                    <div class="space-file-title-cell">
                      <div class="space-file-avatar" :class="item.kind === 'excel' ? 'avatar-excel' : (item.is_template ? 'avatar-template' : 'avatar-html')">
                        <span>{{ item.kind === 'excel' ? '📊' : (item.is_template ? '⚙️' : '📄') }}</span>
                      </div>
                      <div class="space-file-name-meta">
                        <span
                          class="space-file-name"
                          :title="item.kind === 'excel' ? '点击直接下载此表格' : '点击在此窗口中打开播放'"
                          @click="item.kind === 'excel' ? downloadFile(item.rel_path) : openPlayer(item)"
                        >
                          {{ item.name }}
                        </span>
                        <div class="space-file-sub-tags">
                          <span class="file-ext-tag">{{ item.ext || (item.kind === 'excel' ? '.xlsx' : '.html') }}</span>
                          <span v-if="item.folder" class="file-folder-tag" title="所在子文件夹">📁 {{ item.folder }}</span>
                          <span v-if="displayConfig.mode === 'custom_html' && (displayConfig.target_file === item.rel_path || displayConfig.target_file === item.name)" class="badge-default-active" title="当前设定的页面默认打开文档">📌 默认打开</span>
                          <span v-if="item.is_template" class="file-sub-note">只读母版</span>
                          <span v-else-if="item.name.includes('_生产情况汇报')" class="file-sub-note">当期自动生成</span>
                        </div>
                      </div>
                    </div>
                  </td>

                  <!-- 2. 分类属性列 -->
                  <td>
                    <span v-if="item.kind === 'excel'" class="space-badge badge-excel">
                      <span class="badge-dot"></span>数据明细 (XLSX)
                    </span>
                    <span v-else-if="item.is_template" class="space-badge badge-template">
                      <span class="badge-dot"></span>系统演示模板
                    </span>
                    <span v-else-if="item.name.includes('_生产情况汇报') || item.name.includes('_生产运行调度汇报')" class="space-badge badge-report">
                      <span class="badge-dot"></span>当期分析报告
                    </span>
                    <span v-else class="space-badge badge-doc">
                      <span class="badge-dot"></span>汇报文档
                    </span>
                  </td>

                  <!-- 3. 文件大小 -->
                  <td style="text-align: center">
                    <span class="space-size-text">{{ item.size_formatted }}</span>
                  </td>

                  <!-- 4. 时间信息（东八区双行精美微排） -->
                  <td>
                    <div class="space-time-cell">
                      <div class="time-primary" title="最后修改/更新时间">
                        <span class="time-label">更新:</span>
                        <span class="time-val">{{ item.updated_at }}</span>
                      </div>
                      <div class="time-secondary" title="创建/入库时间">
                        <span class="time-label">创建:</span>
                        <span class="time-val">{{ item.created_at || item.updated_at }}</span>
                      </div>
                    </div>
                  </td>

                  <!-- 5. 管理操作列 -->
                  <td style="text-align: right">
                    <div class="space-actions-group">
                      <button
                        v-if="item.kind !== 'excel'"
                        class="space-btn-action action-play"
                        title="在当前窗口中打开沉浸式播放"
                        @click="openPlayer(item)"
                      >
                        <span>▶</span> 播放
                      </button>
                      <button
                        class="space-btn-action action-down"
                        title="下载文件至本地电脑"
                        @click="downloadFile(item.rel_path)"
                      >
                        <span>📥</span> 下载
                      </button>
                      <button
                        v-if="isGlobalAdmin && item.kind !== 'excel'"
                        class="space-btn-action action-setdefault"
                        title="将此文档设为进入页面的默认打开内容"
                        @click="quickSetAsDefault(item)"
                      >
                        <span>📌</span> 设为默认
                      </button>
                      <button
                        class="space-btn-action action-transfer"
                        title="在材料空间内部移动至其他文件夹，或传输至工作流空间"
                        @click="openTransferModal(item, 'material')"
                      >
                        <span>📦</span> 移动/传输
                      </button>
                      <button
                        v-if="!item.is_template"
                        class="space-btn-action action-rename"
                        title="重命名材料文件"
                        @click="openRenameModal(item)"
                      >
                        <span>✏️</span> 改名
                      </button>
                      <button
                        v-if="!item.is_template"
                        class="space-btn-action action-del"
                        title="删除此文件"
                        @click="deleteFile(item)"
                      >
                        <span>🗑</span>
                      </button>
                      <span v-else class="space-badge-protected" title="核心模板防误删保护中">🔒 受保护</span>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 弹窗 Footer -->
        <div class="modal-footer space-modal-footer">
          <div class="space-footer-left">
            <span class="space-path-tag" title="点击一键复制文件物理存放路径" @click="copyStoragePath">
              <span class="path-icon">💾</span>
              <span>路径: <code>backend_data/projects/daily_report_25_26/period_report/材料仓库</code></span>
              <span class="copy-hint">复制</span>
            </span>
          </div>
          <div class="space-footer-right">
            <span class="space-stats-hint">
              已显示 <strong>{{ filteredFileList.length }}</strong> / 共 {{ fileList.length }} 个材料
            </span>
            <button class="btn-primary space-btn-close-main" @click="showFileManagerModal = false">
              完成关闭
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ==================== 弹窗：工作流目录管理空间 ==================== -->
    <div v-if="showWorkflowModal" class="modal-mask" @click.self="showWorkflowModal = false">
      <div class="modal-card modal-card-space">
        <!-- 弹窗 Header -->
        <div class="modal-header space-modal-header">
          <div class="space-header-info">
            <div class="space-header-title-row">
              <span class="space-title-icon">🗂️</span>
              <h3 class="modal-title">生产汇报工作流管理中枢</h3>
              <span class="space-title-badge" style="background: linear-gradient(135deg, #8b5cf6, #0284c7)">工作流空间</span>
            </div>
            <p class="modal-subtitle">层级浏览与维护工作流规范文档(.md)、模版引擎(.html)与数据架构目录，支持子目录进入、在线阅读与即时维护</p>
          </div>
          <button class="btn-close space-btn-close" title="关闭窗口" @click="showWorkflowModal = false">✕</button>
        </div>

        <!-- 面包屑与层级导航条 -->
        <div class="workflow-breadcrumb-bar">
          <div class="breadcrumb-left">
            <button
              v-if="currentWorkflowFolder"
              class="btn-nav-back"
              title="返回上级目录"
              @click="goToParentWorkflowFolder"
            >
              <span>↩️ 返回上级</span>
            </button>
            <div class="breadcrumb-trail">
              <span
                v-for="(crumb, idx) in workflowBreadcrumbs"
                :key="crumb.path"
                class="breadcrumb-node"
                :class="{ active: idx === workflowBreadcrumbs.length - 1 }"
                @click="openWorkflowFolder(crumb.path)"
              >
                <span v-if="idx === 0" class="crumb-icon">🗂️</span>
                <span v-else class="crumb-icon">📁</span>
                <span class="crumb-name">{{ crumb.name }}</span>
                <span v-if="idx < workflowBreadcrumbs.length - 1" class="breadcrumb-sep">/</span>
              </span>
            </div>
          </div>
          <div class="breadcrumb-right">
            <span class="location-badge">
              当前层级: <code>{{ currentWorkflowFolder ? '/' + currentWorkflowFolder : '工作流根目录' }}</code>
            </span>
          </div>
        </div>

        <!-- 工作流工具栏 -->
        <div class="space-toolbar-row">
          <!-- 左侧操作 -->
          <div class="space-toolbar-left">
            <input
              ref="workflowFileInputRef"
              type="file"
              style="display: none"
              @change="handleWorkflowUpload"
            />
            <button
              class="btn-primary space-btn-upload"
              style="background: #7c3aed; border-color: #7c3aed"
              :disabled="workflowUploading"
              title="上传文档至当前所在目录"
              @click="triggerWorkflowUpload"
            >
              <span v-if="workflowUploading" class="spinner"></span>
              {{ workflowUploading ? '正在上传…' : '📤 上传至当前目录' }}
            </button>

            <button
              class="btn-tool"
              style="border-color: #c4b5fd; color: #6d28d9; background: #f5f3ff"
              title="在当前目录下创建新的子目录"
              @click="openNewFolderModal"
            >
              <span>📁 新建文件夹</span>
            </button>

            <!-- 一键打包下载目录（含所有子目录与文件） -->
            <button
              class="btn-tool space-btn-archive"
              style="border-color: #8b5cf6; color: #6d28d9; background: #f5f3ff"
              :disabled="workflowArchiving"
              :title="currentWorkflowFolder ? `一键打包下载当前目录【${currentWorkflowFolder}】及其下所有子目录和文件 (ZIP)` : '一键打包下载工作流目录中的所有子目录和文件 (ZIP)'"
              @click="handleDownloadArchive(currentWorkflowFolder)"
            >
              <span v-if="workflowArchiving" class="spinner"></span>
              <span>{{ workflowArchiving ? '正在打包…' : (currentWorkflowFolder ? '📦 打包本目录 (ZIP)' : '📦 打包下载全部 (ZIP)') }}</span>
            </button>

            <!-- 当处于子目录时，额外提供一键打包全量工作流根目录入口 -->
            <button
              v-if="currentWorkflowFolder"
              class="btn-tool"
              style="border-color: #c4b5fd; color: #7c3aed"
              :disabled="workflowArchiving"
              title="一键打包下载整个工作流的所有子目录和文件 (ZIP)"
              @click="handleDownloadArchive('')"
            >
              <span>📦 打包全部</span>
            </button>

            <button
              class="btn-tool space-btn-refresh"
              :disabled="workflowLoading"
              title="重新扫描当前目录"
              @click="loadWorkflowFiles(currentWorkflowFolder)"
            >
              <span v-if="workflowLoading" class="spinner"></span>
              {{ workflowLoading ? '扫描中…' : '🔄 刷新' }}
            </button>
          </div>

          <!-- 右侧即时搜索框 -->
          <div class="space-toolbar-right">
            <div class="space-search-box">
              <span class="search-icon">🔍</span>
              <input
                v-model="workflowSearchKeyword"
                type="text"
                class="space-search-input"
                placeholder="搜索当前目录内容…"
              />
              <button
                v-if="workflowSearchKeyword"
                class="search-clear-btn"
                title="清空搜索"
                @click="workflowSearchKeyword = ''"
              >✕</button>
            </div>
          </div>
        </div>

        <!-- 工作流表格卡片包裹 -->
        <div class="space-table-card">
          <div class="file-table-wrap space-table-scroll">
            <table class="report-table space-table">
              <thead>
                <tr>
                  <th style="width: 32%">名称</th>
                  <th style="width: 16%">类型与用途</th>
                  <th style="width: 9%; text-align: center">大小 / 统计</th>
                  <th style="width: 16%">修改时间 (北京)</th>
                  <th style="width: 27%; text-align: right">操作</th>
                </tr>
              </thead>
              <tbody>
                <!-- 加载状态 -->
                <tr v-if="workflowLoading && totalCurrentItemsCount === 0">
                  <td colspan="5" class="space-empty-cell">
                    <div class="space-empty-box">
                      <span class="spinner" style="width: 24px; height: 24px"></span>
                      <span>正在扫描目录…</span>
                    </div>
                  </td>
                </tr>

                <!-- 空状态 -->
                <tr v-else-if="totalCurrentItemsCount === 0">
                  <td colspan="5" class="space-empty-cell">
                    <div class="space-empty-box">
                      <span class="space-empty-icon">📂</span>
                      <p class="space-empty-title">
                        {{ workflowSearchKeyword ? '未找到匹配项' : '当前目录为空' }}
                      </p>
                      <p class="space-empty-desc">
                        {{ workflowSearchKeyword ? '可尝试缩短关键词或清空搜索' : '您可点击上方“📤 上传至当前目录”或“📁 新建文件夹”添加内容' }}
                      </p>
                    </div>
                  </td>
                </tr>

                <!-- 1. 渲染子目录行 (先渲染子文件夹，黄色醒目，点击即可进入) -->
                <tr
                  v-for="dir in filteredWorkflowDirectories"
                  :key="dir.rel_path || dir.relative_path || dir.name"
                  class="space-file-row space-dir-row"
                  @click="openWorkflowFolder(dir.rel_path || dir.relative_path || dir.name)"
                >
                  <!-- 文件夹名称列 -->
                  <td>
                    <div class="space-file-title-cell">
                      <div class="space-file-avatar avatar-folder">
                        <span>📁</span>
                      </div>
                      <div class="space-file-name-meta">
                        <span
                          class="space-file-name space-dir-name"
                          title="点击进入该子目录"
                        >
                          {{ dir.name }}
                        </span>
                        <div class="space-file-sub-tags">
                          <span class="file-sub-note font-mono">{{ dir.rel_path || dir.relative_path || dir.name }}</span>
                        </div>
                      </div>
                    </div>
                  </td>

                  <!-- 类型与用途 -->
                  <td>
                    <span class="space-badge badge-dir">
                      <span class="badge-dot"></span>工作流子目录
                    </span>
                  </td>

                  <!-- 包含内容统计 -->
                  <td style="text-align: center">
                    <span class="space-dir-count font-mono">{{ dir.file_count ?? dir.item_count ?? 0 }} 个文件</span>
                  </td>

                  <!-- 修改时间 -->
                  <td>
                    <span class="text-xs font-mono text-muted">{{ dir.updated_at }}</span>
                  </td>

                  <!-- 操作列 -->
                  <td style="text-align: right" @click.stop>
                    <div class="space-actions-group">
                      <button
                        class="space-btn-action action-enter"
                        title="点击进入此子目录"
                        @click="openWorkflowFolder(dir.rel_path || dir.relative_path || dir.name)"
                      >
                        <span>👉</span> 进入
                      </button>
                    </div>
                  </td>
                </tr>

                <!-- 2. 渲染当前目录下的直属文件行 -->
                <tr
                  v-for="item in filteredWorkflowFiles"
                  :key="item.rel_path || item.name"
                  class="space-file-row"
                >
                  <!-- 文件名称列 -->
                  <td>
                    <div class="space-file-title-cell">
                      <div
                        class="space-file-avatar"
                        :class="{
                          'avatar-md': item.kind === 'markdown',
                          'avatar-html': item.kind === 'html',
                          'avatar-excel': item.kind === 'excel'
                        }"
                      >
                        <span>{{ item.kind === 'markdown' ? '📑' : (item.kind === 'html' ? '🌐' : (item.kind === 'excel' ? '📊' : '📄')) }}</span>
                      </div>
                      <div class="space-file-name-meta">
                        <span
                          class="space-file-name"
                          :title="item.kind === 'markdown' ? '点击在线阅览 Markdown 文档' : (item.kind === 'html' ? '点击在线播放 HTML 演示' : '点击下载此文件')"
                          @click="item.kind === 'markdown' ? openDocReader(item) : (item.kind === 'html' ? openPlayer(item) : downloadWorkflow(item))"
                        >
                          {{ item.name }}
                        </span>
                        <div class="space-file-sub-tags">
                          <span class="file-ext-tag">{{ item.ext }}</span>
                          <span class="file-sub-note font-mono">{{ item.name }}</span>
                        </div>
                      </div>
                    </div>
                  </td>

                  <!-- 类型与用途 -->
                  <td>
                    <div class="flex flex-col gap-0.5">
                      <span v-if="item.kind === 'markdown'" class="space-badge badge-markdown">
                        <span class="badge-dot"></span>Markdown 规范
                      </span>
                      <span v-else-if="item.kind === 'html'" class="space-badge badge-report">
                        <span class="badge-dot"></span>HTML 模版引擎
                      </span>
                      <span v-else-if="item.kind === 'excel'" class="space-badge badge-excel">
                        <span class="badge-dot"></span>XLSX 生产数据
                      </span>
                      <span v-else class="space-badge badge-doc">
                        <span class="badge-dot"></span>{{ item.ext ? item.ext.toUpperCase().replace('.', '') : '文件' }}
                      </span>
                    </div>
                  </td>

                  <!-- 文件大小 -->
                  <td style="text-align: center">
                    <span class="space-size-text">{{ item.size_formatted }}</span>
                  </td>

                  <!-- 最后更新时间 (东八区) -->
                  <td>
                    <span class="text-xs font-mono text-muted">{{ item.updated_at }}</span>
                  </td>

                  <!-- 管理操作列 -->
                  <td style="text-align: right">
                    <div class="space-actions-group">
                      <button
                        v-if="item.kind === 'markdown'"
                        class="space-btn-action action-read"
                        title="在线精读查看 Markdown 规范"
                        @click="openDocReader(item)"
                      >
                        <span>👁️</span> 阅读
                      </button>
                      <button
                        v-else-if="item.kind === 'html'"
                        class="space-btn-action action-play"
                        title="在当前窗口中打开模版引擎演示播放"
                        @click="openPlayer(item)"
                      >
                        <span>▶</span> 播放
                      </button>
                      <button
                        class="space-btn-action action-down"
                        title="下载文件至本地"
                        @click="downloadWorkflow(item)"
                      >
                        <span>📥</span> 下载
                      </button>
                      <button
                        class="space-btn-action action-transfer"
                        title="在工作流空间内部移动至其他文件夹，或传输至材料空间"
                        @click="openTransferModal(item, 'workflow')"
                      >
                        <span>📦</span> 移动/传输
                      </button>
                      <button
                        class="space-btn-action action-rename"
                        title="重命名工作流文件"
                        @click="openWorkflowRename(item)"
                      >
                        <span>✏️</span> 改名
                      </button>
                      <button
                        class="space-btn-action action-del"
                        title="删除此工作流文件"
                        @click="deleteWorkflow(item)"
                      >
                        <span>🗑</span>
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 弹窗 Footer -->
        <div class="modal-footer space-modal-footer">
          <div class="space-footer-left">
            <span class="space-path-tag" title="点击一键复制工作流物理存放路径" @click="copyWorkflowPath">
              <span class="path-icon">💾</span>
              <span>路径: <code>backend_data/projects/daily_report_25_26/period_report/工作流{{ currentWorkflowFolder ? '/' + currentWorkflowFolder : '' }}</code></span>
              <span class="copy-hint">复制</span>
            </span>

            <button
              class="space-path-tag space-pack-tag"
              style="border-color: #ddd6fe; color: #7c3aed; background: #fdf4ff"
              :disabled="workflowArchiving"
              title="一键将整个工作流目录中的所有子目录与文件打包下载为 ZIP 压缩包"
              @click="handleDownloadArchive('')"
            >
              <span class="path-icon">📦</span>
              <span>{{ workflowArchiving ? '正在打包…' : '一键打包下载全部资料 (ZIP)' }}</span>
            </button>
          </div>
          <div class="space-footer-right">
            <span class="space-stats-hint">
              当前目录包含 <strong>{{ filteredWorkflowDirectories.length }}</strong> 个文件夹 · <strong>{{ filteredWorkflowFiles.length }}</strong> 个文件
            </span>
            <button class="btn-primary space-btn-close-main" @click="showWorkflowModal = false">
              完成关闭
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ==================== 弹窗：工作流新建子目录 ==================== -->
    <div v-if="showNewFolderModal" class="modal-mask" @click.self="closeNewFolderModal">
      <div class="modal-card modal-card-sm">
        <div class="modal-header">
          <div>
            <h3 class="modal-title">📁 新建子文件夹</h3>
            <p class="modal-subtitle">在当前目录创建新的分类目录，组织结构化工作流材料</p>
          </div>
          <button class="btn-close" @click="closeNewFolderModal">✕</button>
        </div>

        <div class="modal-body" style="padding: 16px 20px">
          <div class="form-group mb-3">
            <label class="form-label text-xs text-muted mb-1 block">所在位置：</label>
            <div class="text-xs font-mono text-slate-500 break-all p-2 rounded bg-slate-50 dark:bg-slate-800" style="border: 1px solid var(--border-color)">
              工作流 / {{ currentWorkflowFolder || '(根目录)' }}
            </div>
          </div>
          <div class="form-group">
            <label class="form-label text-xs font-bold mb-1 block">文件夹名称：</label>
            <input
              ref="newFolderInputRef"
              v-model="newFolderName"
              type="text"
              class="input-control font-mono text-sm"
              placeholder="请输入文件夹名称（如 4.分析指标模型）"
              @keyup.enter="confirmCreateFolder"
            />
            <p class="text-xs text-muted mt-1">文件夹名不能包含 <code>\ / : * ? " &lt; &gt; |</code> 等字符</p>
          </div>
        </div>

        <div class="modal-footer" style="padding: 12px 20px">
          <button class="btn-tool" @click="closeNewFolderModal">取消</button>
          <button
            class="btn-primary"
            :disabled="newFolderLoading || !newFolderName.trim()"
            @click="confirmCreateFolder"
          >
            <span v-if="newFolderLoading" class="spinner"></span>
            {{ newFolderLoading ? '正在创建…' : '确认创建' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ==================== 弹窗：工作流文档沉浸式阅读窗口 (Markdown / Text) ==================== -->
    <div v-if="showDocReaderModal" class="modal-mask" @click.self="closeDocReader">
      <div class="modal-card modal-card-lg doc-reader-card">
        <div class="modal-header doc-reader-header">
          <div class="doc-reader-meta">
            <div class="flex items-center gap-2">
              <span class="badge-tag badge-tag-purple">工作流规范</span>
              <h3 class="modal-title font-mono">{{ docReaderData?.name }}</h3>
              <span class="text-xs text-muted">({{ docReaderData?.size_formatted }})</span>
            </div>
            <p class="modal-subtitle font-mono text-xs">相对路径：{{ docReaderData?.rel_path }} · 最后更新：{{ docReaderData?.updated_at }}</p>
          </div>
          <div class="doc-reader-actions">
            <button class="btn-tool" title="复制文档全部纯文本内容" @click="copyDocContent">
              <span>📋 复制全文</span>
            </button>
            <button class="btn-tool" title="下载此文档" @click="downloadWorkflow({ rel_path: docReaderData?.rel_path })">
              <span>📥 下载</span>
            </button>
            <button class="btn-close space-btn-close" @click="closeDocReader">✕</button>
          </div>
        </div>

        <div class="doc-reader-body">
          <pre class="doc-reader-content">{{ docReaderData?.content }}</pre>
        </div>

        <div class="modal-footer" style="padding-top: 10px">
          <span class="text-xs text-muted">提示：本阅读器直接读取服务端最新源文件</span>
          <button class="btn-primary" @click="closeDocReader">关闭阅读</button>
        </div>
      </div>
    </div>

    <!-- ==================== 弹窗：工作流文件重命名 ==================== -->
    <div v-if="showWorkflowRenameModal" class="modal-mask" @click.self="closeWorkflowRename">
      <div class="modal-card modal-card-sm">
        <div class="modal-header">
          <div>
            <h3 class="modal-title">✏️ 重命名工作流文件</h3>
            <p class="modal-subtitle">修改工作流文档名称，系统将自动保持原扩展名格式</p>
          </div>
          <button class="btn-close" @click="closeWorkflowRename">✕</button>
        </div>

        <div class="modal-body" style="padding: 16px 20px">
          <div class="form-group mb-3">
            <label class="form-label text-xs text-muted mb-1 block">原文件：</label>
            <div class="text-xs font-mono text-slate-500 break-all p-2 rounded bg-slate-50 dark:bg-slate-800" style="border: 1px solid var(--border-color)">
              {{ workflowRenamingFile?.rel_path }}
            </div>
          </div>
          <div class="form-group">
            <label class="form-label text-xs font-bold mb-1 block">新文件名：</label>
            <div class="flex items-center gap-2">
              <input
                ref="workflowRenameInputRef"
                v-model="workflowRenameInput"
                type="text"
                class="input-control flex-1 font-mono text-sm"
                placeholder="请输入新文件名"
                @keyup.enter="confirmWorkflowRename"
              />
              <span class="text-xs font-bold text-muted font-mono px-2 py-1.5 rounded bg-slate-100 dark:bg-slate-700" style="border: 1px solid var(--border-color)">
                {{ workflowRenamingFile?.ext || '' }}
              </span>
            </div>
            <p class="text-xs text-muted mt-1">无需输入后缀，系统将自动保留 <code>{{ workflowRenamingFile?.ext }}</code> 格式</p>
          </div>
        </div>

        <div class="modal-footer" style="padding: 12px 20px">
          <button class="btn-tool" @click="closeWorkflowRename">取消</button>
          <button
            class="btn-primary"
            :disabled="workflowRenamingLoading || !workflowRenameInput.trim()"
            @click="confirmWorkflowRename"
          >
            <span v-if="workflowRenamingLoading" class="spinner"></span>
            {{ workflowRenamingLoading ? '正在重命名…' : '确认重命名' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ==================== 弹窗：文件重命名 ==================== -->
    <div v-if="showRenameModal" class="modal-mask" @click.self="closeRenameModal">
      <div class="modal-card modal-card-sm">
        <div class="modal-header">
          <div>
            <h3 class="modal-title">✏️ 重命名文件</h3>
            <p class="modal-subtitle">修改材料文件名称，系统将自动保持原扩展名格式</p>
          </div>
          <button class="btn-close" @click="closeRenameModal">✕</button>
        </div>

        <div class="modal-body" style="padding: 16px 20px">
          <div class="form-group mb-3">
            <label class="form-label text-xs text-muted mb-1 block">原文件名：</label>
            <div class="text-xs font-mono text-slate-500 break-all p-2 rounded bg-slate-50 dark:bg-slate-800" style="border: 1px solid var(--border-color)">
              {{ renamingFile?.name }}
            </div>
          </div>
          <div class="form-group">
            <label class="form-label text-xs font-bold mb-1 block">新文件名：</label>
            <div class="flex items-center gap-2">
              <input
                ref="renameInputRef"
                v-model="renameInput"
                type="text"
                class="input-control flex-1 font-mono text-sm"
                placeholder="请输入新文件名"
                @keyup.enter="confirmRenameFile"
              />
              <span class="text-xs font-bold text-muted font-mono px-2 py-1.5 rounded bg-slate-100 dark:bg-slate-700" style="border: 1px solid var(--border-color)">
                {{ renamingFile?.ext || '' }}
              </span>
            </div>
            <p class="text-xs text-muted mt-1">无需输入后缀，系统将自动保留 <code>{{ renamingFile?.ext }}</code> 格式</p>
          </div>
        </div>

        <div class="modal-footer" style="padding: 12px 20px">
          <button class="btn-tool" @click="closeRenameModal">取消</button>
          <button
            class="btn-primary"
            :disabled="renamingLoading || !renameInput.trim()"
            @click="confirmRenameFile"
          >
            <span v-if="renamingLoading" class="spinner"></span>
            {{ renamingLoading ? '正在重命名…' : '确认重命名' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ==================== 弹窗：导出生产运行多维数据配置 (XLSX) ==================== -->
    <div v-if="showExportXlsxModal" class="modal-mask" @click.self="showExportXlsxModal = false">
      <div class="modal-card modal-card-md">
        <div class="modal-header">
          <div>
            <h3 class="modal-title">📊 生产运行数据导出 (XLSX)</h3>
            <p class="modal-subtitle">生成包含 4 个标准化 Sheet 的数据明细报表，供后续 AI Agent 自动化分析或本地审阅</p>
          </div>
          <button class="btn-close" @click="showExportXlsxModal = false">✕</button>
        </div>

        <div class="export-modal-body">
          <!-- 统计周期选择 -->
          <div class="form-group-row">
            <div class="form-field flex-1">
              <label class="field-label">开始日期</label>
              <input v-model="exportStart" type="date" class="form-input" />
            </div>
            <div class="form-field flex-1">
              <label class="field-label">结束日期</label>
              <input v-model="exportEnd" type="date" class="form-input" />
            </div>
          </div>

          <!-- 环比对标选项 -->
          <div class="export-opt-box">
            <label class="checkbox-label">
              <input v-model="exportIncludePrev" type="checkbox" class="checkbox-input" />
              <span class="font-bold">包含上期值 (环比对标数据)</span>
            </label>
            <p class="opt-desc">
              💡 <strong>对标规则：</strong>若当前区间为完整自然月（如 3.1~3.31），上期将自动对齐上一个完整自然月（如 2.1~2.28）；若为非整月，向前等长追溯相同天数。
            </p>
          </div>

          <!-- 数据架构清单概览卡片 -->
          <div class="sheets-preview-card">
            <div class="card-title">📋 导出的报表包含以下 4 个结构化 Sheet：</div>
            <div class="sheet-item">
              <span class="sheet-badge">Sheet 1</span>
              <div>
                <strong>指标对标全景总表：</strong>
                <span>10家主体单位 × 28项核心指标（供热量/发电量/售电量/售汽量/高温水/标煤耗量/原煤/单耗/收入/边际利润/净投诉量等，含完整月度计划值、期间计划分解测算值、完成率、进度偏差与同环比对标）。</span>
              </div>
            </div>
            <div class="sheet-item">
              <span class="sheet-badge">Sheet 2</span>
              <div>
                <strong>设备运行与开停机：</strong>
                <span>各电厂/单位汽机与锅炉状态、开停机时序、点火并汽并网等真实调度操作记录。</span>
              </div>
            </div>
            <div class="sheet-item">
              <span class="sheet-badge">Sheet 3</span>
              <div>
                <strong>电力现货电价走势：</strong>
                <span>辽宁电力现货市场 15 分钟/96 点日前电价、实时电价与价差时序流。</span>
              </div>
            </div>
            <div class="sheet-item">
              <span class="sheet-badge">Sheet 4</span>
              <div>
                <strong>调度日志与抢修记录：</strong>
                <span>调度发令事件、管网抢修/检修工作票、责任单位与工期执行明细。</span>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer flex items-center justify-between">
          <button class="btn-tool" @click="showExportXlsxModal = false">取消</button>
          <div class="flex items-center gap-2">
            <button
              class="btn-primary btn-export-down"
              :disabled="exportingDownload || exportingSpace || !exportStart || !exportEnd"
              @click="handleExportXlsxDownload"
            >
              <span v-if="exportingDownload" class="spinner"></span>
              {{ exportingDownload ? '正在生成…' : '⬇️ 下载至本地' }}
            </button>
            <button
              class="btn-success"
              :disabled="exportingDownload || exportingSpace || !exportStart || !exportEnd"
              @click="handleExportXlsxSaveToSpace"
            >
              <span v-if="exportingSpace" class="spinner"></span>
              {{ exportingSpace ? '正在保存…' : '💾 一键保存至材料仓库' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ==================== 弹窗：HTML 汇报播放窗口 ==================== -->
    <div v-if="showPlayerModal" class="player-overlay">
      <div class="player-header">
        <div class="player-title-box">
          <span class="badge-tag badge-tag-emerald">正在播放</span>
          <h2 class="player-title">{{ currentPlayingFile?.name || 'HTML 汇报材料' }}</h2>
          <span class="text-xs text-slate-300">({{ currentPlayingFile?.size_formatted }})</span>
        </div>
        <div class="player-actions">
          <button class="btn-tool-dark" @click="openPlayerInNewTab" title="在新浏览器标签页中全尺寸打开">
            <span>🔗 新标签页打开</span>
          </button>
          <button class="btn-tool-dark" @click="toggleIframeFullscreen" title="全屏沉浸播放">
            <span>⛶ 全屏播放</span>
          </button>
          <button class="btn-tool-dark btn-close-player" @click="closePlayer" title="关闭播放器">
            <span>✕ 关闭返回</span>
          </button>
        </div>
      </div>

      <div class="player-body">
        <div v-if="playerLoading" class="player-loading">
          <div class="spinner spinner-lg"></div>
          <p class="mt-3 text-sm">正在加载汇报材料内容…</p>
        </div>
        <iframe
          v-show="!playerLoading"
          ref="playerIframeRef"
          :srcdoc="playerHtmlContent"
          class="player-iframe"
          sandbox="allow-scripts allow-same-origin allow-popups"
        ></iframe>
      </div>
    </div>

    <!-- ==================== 弹窗：页面默认打开内容设定 ==================== -->
    <div v-if="showDisplayConfigModal" class="modal-mask" @click.self="showDisplayConfigModal = false">
      <div class="modal-card modal-card-sm modal-card-config">
        <div class="modal-header">
          <div class="space-header-title-row">
            <span class="space-title-icon">⚙️</span>
            <h3 class="modal-title">设定默认展示内容</h3>
          </div>
          <button class="btn-close" @click="showDisplayConfigModal = false">✕</button>
        </div>
        <div class="modal-body p-4">
          <p class="modal-subtitle mb-3 text-xs text-muted">
            设定所有用户访问生产运行汇报页面时的首屏默认打开内容。此功能仅限 Global_admin 超管设定。
          </p>

          <div class="display-mode-selector mb-4">
            <label
              class="mode-option-card"
              :class="{ selected: configSettingMode === 'generated' }"
              @click="configSettingMode = 'generated'"
            >
              <input type="radio" value="generated" v-model="configSettingMode" class="mt-1" />
              <div class="option-text">
                <div class="option-title font-bold">📊 动态自选周期生成页（系统默认）</div>
                <div class="option-desc text-xs text-muted mt-1">加载经济运行部多维对标算法，自选任意起止日期，左文右表整页调度汇报</div>
              </div>
            </label>

            <label
              class="mode-option-card mt-3"
              :class="{ selected: configSettingMode === 'custom_html' }"
              @click="configSettingMode = 'custom_html'"
            >
              <input type="radio" value="custom_html" v-model="configSettingMode" class="mt-1" />
              <div class="option-text">
                <div class="option-title font-bold">📄 指定材料空间 HTML 文档</div>
                <div class="option-desc text-xs text-muted mt-1">首屏直接展示指定的成熟自包含汇报材料或大屏演示系统</div>
              </div>
            </label>
          </div>

          <!-- 当选择 custom_html 时显示下拉选择 -->
          <div v-if="configSettingMode === 'custom_html'" class="form-group mb-3 bg-slate-50 dark:bg-slate-800 p-3 rounded-lg border border-slate-200 dark:border-slate-700">
            <label class="form-label font-bold text-xs mb-1 block">选择要默认打开的 HTML 材料文档：</label>
            <select v-model="configSettingFile" class="form-select w-full p-2 rounded border text-sm">
              <option value="" disabled>-- 请选择材料文档 --</option>
              <option
                v-for="f in availableHtmlFiles"
                :key="f.rel_path"
                :value="f.rel_path"
              >
                {{ f.name }} ({{ f.size_formatted }})
              </option>
            </select>
            <p v-if="availableHtmlFiles.length === 0" class="text-xs text-amber-500 mt-2">
              ⚠️ 材料空间中暂无 HTML 材料文档，请先在控制台中保存或上传汇报文档。
            </p>
          </div>
        </div>

        <div class="modal-footer flex justify-end gap-2 p-3 border-t">
          <button class="btn-tool" @click="showDisplayConfigModal = false">取消</button>
          <button
            class="btn-primary"
            :disabled="savingConfig || (configSettingMode === 'custom_html' && !configSettingFile)"
            @click="submitDisplayConfig"
          >
            <span v-if="savingConfig" class="spinner mr-1"></span>
            {{ savingConfig ? '正在保存…' : '💾 保存默认设置' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ==================== 弹窗：文件移动与跨空间传输 ==================== -->
    <div v-if="showTransferModal" class="modal-mask" @click.self="showTransferModal = false">
      <div class="modal-card modal-card-transfer">
        <!-- 弹窗 Header -->
        <div class="modal-header transfer-modal-header">
          <div class="space-header-title-row">
            <span class="space-title-icon transfer-icon-badge">📦</span>
            <div>
              <div class="flex items-center gap-2">
                <h3 class="modal-title font-bold text-base">文件移动与传输中枢</h3>
                <span class="transfer-mode-pill" :class="isSameSpaceTransfer ? 'pill-internal' : 'pill-cross'">
                  {{ isSameSpaceTransfer ? '📁 空间内部整理' : '🚀 跨空间流转' }}
                </span>
              </div>
              <p class="text-xs text-muted mt-0.5">支持材料空间与工作流目录空间互相传输，或在当前空间内移动至指定文件夹归档</p>
            </div>
          </div>
          <button class="btn-close space-btn-close" title="关闭窗口" @click="showTransferModal = false">✕</button>
        </div>

        <div class="modal-body transfer-modal-body">
          <!-- 1. 流转关系示意看板 -->
          <div class="transfer-flow-card">
            <!-- 左侧源信息 -->
            <div class="flow-endpoint endpoint-source">
              <div class="endpoint-header">
                <span class="endpoint-badge source-tag">当前源文件</span>
                <span class="endpoint-space-name font-mono">{{ transferSourceSpace === 'material' ? '📁 材料空间' : '🗂️ 工作流空间' }}</span>
              </div>
              <div class="endpoint-file-row">
                <div class="file-icon-box" :class="transferTargetItem?.kind === 'excel' ? 'icon-excel' : (transferTargetItem?.kind === 'markdown' ? 'icon-md' : 'icon-html')">
                  <span>{{ transferTargetItem?.kind === 'excel' ? '📊' : (transferTargetItem?.kind === 'markdown' ? '📑' : '📄') }}</span>
                </div>
                <div class="file-info-col">
                  <span class="file-main-name font-bold" :title="transferTargetItem?.name">{{ transferTargetItem?.name }}</span>
                  <span class="file-sub-path text-muted font-mono">
                    {{ transferTargetItem?.folder ? '📁 位于: ' + transferTargetItem.folder : '🏠 位于根目录' }}
                  </span>
                </div>
              </div>
            </div>

            <!-- 中间流转动向 -->
            <div class="flow-arrow-col">
              <div class="flow-arrow-circle" :class="transferAction === 'move' ? 'circle-move' : 'circle-copy'">
                <span class="arrow-symbol">➔</span>
              </div>
              <span class="flow-action-text font-bold" :class="transferAction === 'move' ? 'text-amber-600 dark:text-amber-400' : 'text-purple-600 dark:text-purple-400'">
                {{ transferAction === 'move' ? '剪切移动' : '生成副本' }}
              </span>
            </div>

            <!-- 右侧目标终点 -->
            <div class="flow-endpoint endpoint-target">
              <div class="endpoint-header">
                <span class="endpoint-badge target-tag">目标落盘位置</span>
                <span class="endpoint-space-name font-mono" :style="{ color: transferTargetSpace === 'material' ? '#0284c7' : '#7c3aed' }">
                  {{ transferTargetSpace === 'material' ? '📁 材料空间' : '🗂️ 工作流空间' }}
                </span>
              </div>
              <div class="endpoint-file-row">
                <div class="file-icon-box icon-folder">
                  <span>📂</span>
                </div>
                <div class="file-info-col">
                  <span class="file-main-name font-bold text-sky-600 dark:text-sky-400">
                    {{ transferTargetFolder ? '📁 ' + transferTargetFolder : '🏠 根目录直属' }}
                  </span>
                  <span class="file-sub-path text-muted font-mono">
                    {{ isSameSpaceTransfer ? '（同空间归档）' : '（跨空间流转）' }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- 2. 目标空间选择卡片 -->
          <div class="transfer-section-box">
            <div class="flex items-center justify-between mb-2">
              <label class="section-label font-bold text-xs">1. 选择目标文件空间</label>
              <span v-if="!isGlobalAdmin" class="text-xs text-amber-600 dark:text-amber-400">⚠️ 工作流空间仅限 Global_admin 管理</span>
            </div>
            <div class="space-choice-grid">
              <div
                class="space-choice-card"
                :class="{ active: transferTargetSpace === 'material' }"
                @click="setTransferTargetSpace('material')"
              >
                <div class="choice-card-header">
                  <div class="flex items-center gap-2">
                    <span class="choice-icon">📁</span>
                    <span class="choice-title font-bold">材料空间 (材料仓库)</span>
                  </div>
                  <span v-if="transferTargetSpace === 'material'" class="choice-check">✓ 选定</span>
                </div>
                <p class="choice-desc text-xs text-muted">存放正式汇报材料 HTML、XLSX 导出数据明细及归档材料</p>
              </div>

              <div
                class="space-choice-card"
                :class="{
                  active: transferTargetSpace === 'workflow',
                  disabled: !isGlobalAdmin
                }"
                @click="isGlobalAdmin && setTransferTargetSpace('workflow')"
                :title="!isGlobalAdmin ? '工作流目录空间仅限 Global_admin 管理' : ''"
              >
                <div class="choice-card-header">
                  <div class="flex items-center gap-2">
                    <span class="choice-icon">🗂️</span>
                    <span class="choice-title font-bold">工作流目录空间</span>
                  </div>
                  <span v-if="transferTargetSpace === 'workflow'" class="choice-check">✓ 选定</span>
                  <span v-if="!isGlobalAdmin" class="choice-lock">🔒 超管专属</span>
                </div>
                <p class="choice-desc text-xs text-muted">存放工作流标准化规范说明文档、模板引擎系统及规则底表</p>
              </div>
            </div>
          </div>

          <!-- 3. 目标文件夹选择与新建 -->
          <div class="transfer-section-box">
            <div class="flex justify-between items-center mb-1.5">
              <label class="section-label font-bold text-xs">2. 选择存放目标子文件夹</label>
              <button
                class="btn-new-folder-inline"
                title="在当前目标空间中即时创建新的分类文件夹"
                @click="openNewFolderModalForSpace(transferTargetSpace)"
              >
                <span>➕</span> 新建子文件夹
              </button>
            </div>
            <div v-if="transferLoadingFolders" class="transfer-loading-folders">
              <span class="spinner" style="width: 14px; height: 14px"></span>
              <span>正在读取 {{ transferTargetSpace === 'material' ? '材料空间' : '工作流空间' }} 文件夹列表…</span>
            </div>
            <div v-else class="folder-select-wrap">
              <select v-model="transferTargetFolder" class="transfer-select font-mono">
                <option
                  v-for="folder in transferFolderList"
                  :key="folder.path"
                  :value="folder.path"
                >
                  {{ folder.path ? '📁 ' + folder.name : '🏠 【根目录直属】' }}
                </option>
              </select>
            </div>
          </div>

          <!-- 4. 操作模式与同名冲突策略 -->
          <div class="transfer-section-box">
            <label class="section-label font-bold text-xs mb-2 block">3. 操作方式与冲突策略</label>
            <div class="action-mode-grid">
              <div
                class="action-mode-card"
                :class="{
                  active: transferAction === 'move',
                  disabled: isTemplateItem
                }"
                @click="!isTemplateItem && (transferAction = 'move')"
                :title="isTemplateItem ? '工作流系统母版受保护，禁止移动，仅可复制' : ''"
              >
                <div class="mode-card-radio">
                  <span class="radio-dot" v-if="transferAction === 'move'"></span>
                </div>
                <div class="mode-card-content">
                  <div class="font-bold text-xs flex items-center gap-1.5">
                    <span>🚚 移动 (剪切)</span>
                    <span v-if="isTemplateItem" class="text-xs text-rose-500 font-normal">🔒 母版受保护禁移动</span>
                  </div>
                  <p class="text-xs text-muted mt-0.5">将文件转移至选定文件夹，原位置将不再保留原文件</p>
                </div>
              </div>

              <div
                class="action-mode-card"
                :class="{ active: transferAction === 'copy' }"
                @click="transferAction = 'copy'"
              >
                <div class="mode-card-radio">
                  <span class="radio-dot" v-if="transferAction === 'copy'"></span>
                </div>
                <div class="mode-card-content">
                  <div class="font-bold text-xs">📋 复制 (副本)</div>
                  <p class="text-xs text-muted mt-0.5">原文件保持不变，在选定目标文件夹中生成一份新副本</p>
                </div>
              </div>
            </div>

            <!-- 同名冲突处理 -->
            <div class="conflict-option-row mt-2.5">
              <label class="conflict-toggle-label">
                <input type="checkbox" v-model="transferOverwrite" class="conflict-checkbox" />
                <span class="font-medium text-xs">目标存在同名文件时直接覆写</span>
              </label>
              <span class="text-xs text-muted">
                {{ transferOverwrite ? '⚠️ 警告：同名文件将被直接覆盖' : '✅ 默认安全策略：同名时自动追加 _副本1、_副本2 序号' }}
              </span>
            </div>
          </div>

          <!-- 5. 目标物理路径实时预览 -->
          <div class="transfer-preview-bar">
            <span class="preview-icon">💾</span>
            <span class="preview-label">目标落盘路径:</span>
            <code class="preview-code">{{ transferTargetPreviewPath }}</code>
          </div>
        </div>

        <!-- 弹窗 Footer -->
        <div class="modal-footer transfer-modal-footer">
          <button class="btn-tool" @click="showTransferModal = false">取消</button>
          <button
            class="btn-primary transfer-submit-btn"
            :class="transferAction === 'move' ? 'btn-move' : 'btn-copy'"
            :disabled="transferringFile"
            @click="submitFileTransfer"
          >
            <span v-if="transferringFile" class="spinner"></span>
            <span>{{ transferringFile ? '正在处理中…' : (transferAction === 'move' ? '🚚 立即执行移动' : '📋 立即执行复制') }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- ==================== 弹窗：通用新建空间文件夹 ==================== -->
    <div v-if="showNewSpaceFolderModal" class="modal-mask" @click.self="showNewSpaceFolderModal = false">
      <div class="modal-card modal-card-sm">
        <div class="modal-header">
          <div class="space-header-title-row">
            <span class="space-title-icon">📁</span>
            <h3 class="modal-title">新建子文件夹</h3>
          </div>
          <button class="btn-close" @click="showNewSpaceFolderModal = false">✕</button>
        </div>
        <div class="modal-body p-4">
          <div class="text-xs text-muted mb-2">
            将在【{{ targetSpaceForNewFolder === 'material' ? '材料空间 (材料仓库)' : '工作流目录空间' }}】中创建新的子目录
          </div>
          <div class="form-group mb-3">
            <label class="form-label font-bold text-xs mb-1 block">文件夹名称：</label>
            <input
              v-model="newSpaceFolderName"
              type="text"
              class="form-input w-full p-2 rounded border text-sm"
              placeholder="例如：2026年3月汇报材料、周调度数据归档…"
              @keyup.enter="submitCreateSpaceFolder"
            />
          </div>
        </div>
        <div class="modal-footer flex justify-end gap-2 p-3 border-t">
          <button class="btn-tool" @click="showNewSpaceFolderModal = false">取消</button>
          <button
            class="btn-primary"
            :disabled="creatingSpaceFolder || !newSpaceFolderName.trim()"
            @click="submitCreateSpaceFolder"
          >
            <span v-if="creatingSpaceFolder" class="spinner mr-1"></span>
            {{ creatingSpaceFolder ? '创建中…' : '创建文件夹' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { useAuthStore } from '../store/auth'
import {
  fetchPeriodReport,
  fetchPeriodReportFiles,
  savePeriodReportHtml,
  uploadPeriodReportFile,
  fetchPeriodReportContent,
  downloadPeriodReportFile,
  deletePeriodReportFile,
  renamePeriodReportFile,
  exportPeriodReportXlsx,
  fetchWorkflowFiles,
  fetchWorkflowFileContent,
  downloadWorkflowFile,
  uploadWorkflowFile,
  renameWorkflowFile,
  deleteWorkflowFile,
  createWorkflowFolder,
  downloadWorkflowArchive,
  fetchPeriodReportDisplayConfig,
  savePeriodReportDisplayConfig,
  fetchSpaceFolders,
  createSpaceFolder,
  transferPeriodReportFile
} from '../services/api'
import {
  REPORT_CHAPTERS as chapters,
  reportNumber as fmt,
  assemblePeriodPresentation,
  DEFAULT_PERIOD_MOCK,
  generateChapterNarrative,
  generateStandalonePeriodReportHtml,
  getPeriodReportDefaultFilename
} from '../composables/periodReportPresentation'

// 用户与权限判定（控制台对 Global_admin 与 Group_admin 开放，其中 Group_admin 仅限材料空间管理）
const auth = useAuthStore()
const normalizedGroup = computed(() => {
  return String(auth.user?.group || auth.user?.role || '').trim().toLowerCase()
})
const isGlobalAdmin = computed(() => {
  return normalizedGroup.value === 'global_admin'
})
const isGroupAdmin = computed(() => {
  return normalizedGroup.value === 'group_admin'
})
const canAccessConsole = computed(() => {
  return isGlobalAdmin.value || isGroupAdmin.value
})

// 控制台下拉菜单状态
const consoleDropdownRef = ref(null)
const showConsoleDropdown = ref(false)

function toggleConsoleDropdown() {
  showConsoleDropdown.value = !showConsoleDropdown.value
}

function closeConsoleDropdown() {
  showConsoleDropdown.value = false
}

function handleClickOutside(e) {
  if (consoleDropdownRef.value && !consoleDropdownRef.value.contains(e.target)) {
    showConsoleDropdown.value = false
  }
}

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

// 页面默认显示配置与主舞台模式
const displayConfig = ref({ mode: 'generated', target_file: '', updated_at: '' })
const activeViewMode = ref('generated') // 'generated' 或 'custom_html'
const customHtmlContent = ref('')
const customHtmlLoading = ref(false)
const customHtmlError = ref('')
const customHtmlIframeRef = ref(null)

// 默认显示配置设定弹窗状态
const showDisplayConfigModal = ref(false)
const configSettingMode = ref('generated')
const configSettingFile = ref('')
const savingConfig = ref(false)

// 材料空间管理与播放器状态
const showFileManagerModal = ref(false)
const fileList = ref([])
const fileLoading = ref(false)
const savingHtml = ref(false)
const uploadingFile = ref(false)
const fileInputRef = ref(null)

// 可供选为默认展示的 HTML 文件列表
const availableHtmlFiles = computed(() => {
  return (fileList.value || []).filter(f => f.kind !== 'excel')
})

// 文件移动与跨空间传输弹窗状态
const showTransferModal = ref(false)
const transferTargetItem = ref(null)
const transferSourceSpace = ref('material') // 'material' 或 'workflow'
const transferTargetSpace = ref('material') // 'material' 或 'workflow'
const transferTargetFolder = ref('')
const transferAction = ref('move') // 'move' 或 'copy'
const transferFolderList = ref([])
const transferLoadingFolders = ref(false)
const transferringFile = ref(false)

// 通用新建空间子目录弹窗状态
const showNewSpaceFolderModal = ref(false)
const targetSpaceForNewFolder = ref('material')
const newSpaceFolderName = ref('')
const creatingSpaceFolder = ref(false)

// 空间管理搜索与类型筛选状态
const fileSearchKeyword = ref('')
const fileTypeFilter = ref('all') // 'all' | 'excel' | 'report' | 'template'

// 空间材料统计计算
const fileStats = computed(() => {
  const list = fileList.value || []
  const excelCount = list.filter(f => f.kind === 'excel').length
  const tplCount = list.filter(f => f.is_template).length
  const reportCount = list.length - excelCount - tplCount
  return {
    total: list.length,
    excel: excelCount,
    report: reportCount,
    template: tplCount
  }
})

// 空间材料计算过滤列表
const filteredFileList = computed(() => {
  let list = fileList.value || []
  if (fileTypeFilter.value === 'excel') {
    list = list.filter(f => f.kind === 'excel')
  } else if (fileTypeFilter.value === 'report') {
    list = list.filter(f => f.kind !== 'excel' && !f.is_template)
  } else if (fileTypeFilter.value === 'template') {
    list = list.filter(f => f.is_template)
  }
  const kw = fileSearchKeyword.value.trim().toLowerCase()
  if (kw) {
    list = list.filter(f => f.name.toLowerCase().includes(kw))
  }
  return list
})

// 一键复制材料仓库相对路径
function copyStoragePath() {
  const path = 'backend_data/projects/daily_report_25_26/period_report/材料仓库'
  navigator.clipboard.writeText(path)
  alert('已复制材料仓库相对路径至剪贴板：\n' + path)
}

const showPlayerModal = ref(false)
const currentPlayingFile = ref(null)
const playerHtmlContent = ref('')
const playerLoading = ref(false)
const playerIframeRef = ref(null)

// 导出生产运行数据 (XLSX) 弹窗状态
const showExportXlsxModal = ref(false)
const exportStart = ref('')
const exportEnd = ref('')
const exportIncludePrev = ref(true)
const exportingDownload = ref(false)
const exportingSpace = ref(false)

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

// ==================== 页面默认展示配置管理方法 ====================

// 加载默认展示配置
async function loadDisplayConfig() {
  try {
    const res = await fetchPeriodReportDisplayConfig()
    displayConfig.value = res || { mode: 'generated', target_file: '', updated_at: '' }
    if (displayConfig.value.mode === 'custom_html' && displayConfig.value.target_file) {
      activeViewMode.value = 'custom_html'
      await loadCustomHtml(displayConfig.value.target_file)
    } else {
      activeViewMode.value = 'generated'
    }
  } catch (err) {
    console.warn('获取默认显示配置失败', err)
    activeViewMode.value = 'generated'
  }
}

// 加载指定的 HTML 材料内容
async function loadCustomHtml(filename) {
  if (!filename) return
  customHtmlLoading.value = true
  customHtmlError.value = ''
  try {
    const res = await fetchPeriodReportContent(filename)
    customHtmlContent.value = res.content || ''
  } catch (err) {
    customHtmlError.value = '读取材料文档内容失败: ' + err.message
  } finally {
    customHtmlLoading.value = false
  }
}

// 在新标签页中打开当前默认展示的 HTML
function openCustomHtmlInNewTab() {
  if (!customHtmlContent.value) return
  const blob = new Blob([customHtmlContent.value], { type: 'text/html;charset=utf-8' })
  const blobUrl = URL.createObjectURL(blob)
  window.open(blobUrl, '_blank')
}

// 打开默认显示设置弹窗
async function openDisplayConfigModal() {
  if (!fileList.value.length) {
    await loadFiles()
  }
  configSettingMode.value = displayConfig.value.mode || 'generated'
  configSettingFile.value = displayConfig.value.target_file || (availableHtmlFiles.value[0]?.rel_path || '')
  showDisplayConfigModal.value = true
}

// 提交默认显示设定
async function submitDisplayConfig() {
  savingConfig.value = true
  try {
    const res = await savePeriodReportDisplayConfig({
      mode: configSettingMode.value,
      target_file: configSettingMode.value === 'custom_html' ? configSettingFile.value : ''
    })
    displayConfig.value = res
    showDisplayConfigModal.value = false
    alert(`🎉 默认显示内容已成功保存！\n当前模式：${res.mode === 'custom_html' ? '指定 HTML 材料' : '动态生成页'}${res.target_file ? '\n文件：' + res.target_file : ''}`)

    // 如果设置成了 custom_html，立即加载并切换展示
    if (res.mode === 'custom_html' && res.target_file) {
      activeViewMode.value = 'custom_html'
      await loadCustomHtml(res.target_file)
    } else {
      activeViewMode.value = 'generated'
    }
  } catch (err) {
    alert('保存默认显示设置失败: ' + err.message)
  } finally {
    savingConfig.value = false
  }
}

// 在材料空间列表中一键设为默认文档
async function quickSetAsDefault(fileItem) {
  if (!fileItem?.rel_path) return
  const ok = confirm(`确定要将【${fileItem.name}】设定为全站访问本页面的首屏默认打开内容吗？`)
  if (!ok) return
  try {
    const res = await savePeriodReportDisplayConfig({
      mode: 'custom_html',
      target_file: fileItem.rel_path
    })
    displayConfig.value = res
    alert(`🎉 已将【${fileItem.name}】设定为页面默认展示内容！`)
  } catch (err) {
    alert('设定失败: ' + err.message)
  }
}

// ==================== 跨空间与空间内文件移动/传输方法 ====================
const transferOverwrite = ref(false)

const isTemplateItem = computed(() => {
  return !!(transferTargetItem.value?.is_template || transferTargetItem.value?.rel_path === '模版引擎.html')
})

const isSameSpaceTransfer = computed(() => {
  return transferSourceSpace.value === transferTargetSpace.value
})

const transferTargetPreviewPath = computed(() => {
  const spaceName = transferTargetSpace.value === 'material' ? '材料仓库' : '工作流'
  const folder = transferTargetFolder.value ? `/${transferTargetFolder.value}` : ''
  const filename = transferTargetItem.value?.name || '未知文件'
  return `backend_data/projects/daily_report_25_26/period_report/${spaceName}${folder}/${filename}`
})

async function setTransferTargetSpace(space) {
  if (transferTargetSpace.value === space) return
  transferTargetSpace.value = space
  await onTransferTargetSpaceChange()
}

// 打开移动/传输弹窗
async function openTransferModal(item, sourceSpace = 'material') {
  transferTargetItem.value = item
  transferSourceSpace.value = sourceSpace
  // 默认同空间移动
  transferTargetSpace.value = sourceSpace
  transferTargetFolder.value = ''
  transferOverwrite.value = false
  if (item?.is_template || item?.rel_path === '模版引擎.html') {
    transferAction.value = 'copy'
  } else {
    transferAction.value = 'move'
  }
  showTransferModal.value = true
  await loadTransferFolders(transferTargetSpace.value)
}

// 目标空间切换时重新加载目标空间下的所有子文件夹
async function onTransferTargetSpaceChange() {
  transferTargetFolder.value = ''
  await loadTransferFolders(transferTargetSpace.value)
}

// 加载指定空间的子文件夹列表
async function loadTransferFolders(space) {
  transferLoadingFolders.value = true
  try {
    const res = await fetchSpaceFolders(space)
    transferFolderList.value = res.folders || [{ name: space === 'material' ? '材料仓库根目录' : '工作流根目录', path: '' }]
  } catch (err) {
    console.error('获取文件夹列表失败', err)
    transferFolderList.value = [{ name: space === 'material' ? '材料仓库根目录' : '工作流根目录', path: '' }]
  } finally {
    transferLoadingFolders.value = false
  }
}

// 提交文件移动/传输
async function submitFileTransfer() {
  if (!transferTargetItem.value) return
  transferringFile.value = true
  try {
    const res = await transferPeriodReportFile({
      source_space: transferSourceSpace.value,
      source_path: transferTargetItem.value.rel_path || transferTargetItem.value.name,
      target_space: transferTargetSpace.value,
      target_folder: transferTargetFolder.value,
      action: transferAction.value,
      overwrite: transferOverwrite.value
    })
    alert(`🎉 操作成功！\n${res.message}\n目标路径：${res.target_rel_path}`)
    showTransferModal.value = false

    // 联动刷新对应空间列表
    await loadFiles()
    if (showWorkflowModal.value) {
      await loadWorkflowFiles(currentWorkflowFolder.value)
    }
  } catch (err) {
    alert('操作失败: ' + err.message)
  } finally {
    transferringFile.value = false
  }
}

// 打开通用新建文件夹弹窗
function openNewFolderModalForSpace(space = 'material') {
  targetSpaceForNewFolder.value = space
  newSpaceFolderName.value = ''
  showNewSpaceFolderModal.value = true
}

// 提交创建空间子目录
async function submitCreateSpaceFolder() {
  const name = newSpaceFolderName.value.trim()
  if (!name) return
  creatingSpaceFolder.value = true
  try {
    await createSpaceFolder(targetSpaceForNewFolder.value, '', name)
    alert(`🎉 文件夹【${name}】创建成功！`)
    showNewSpaceFolderModal.value = false
    // 刷新两边空间文件夹并自动选中新建的文件夹
    if (showTransferModal.value) {
      await loadTransferFolders(transferTargetSpace.value)
      transferTargetFolder.value = name
    }
    await loadFiles()
    if (showWorkflowModal.value) {
      await loadWorkflowFiles(currentWorkflowFolder.value)
    }
  } catch (err) {
    alert('创建文件夹失败: ' + err.message)
  } finally {
    creatingSpaceFolder.value = false
  }
}

// ==================== 汇报材料 HTML 空间管理与播放器方法 ====================

// 加载空间 HTML 文件列表
async function loadFiles() {
  fileLoading.value = true
  try {
    const res = await fetchPeriodReportFiles()
    fileList.value = res.items || []
  } catch (err) {
    error.value = '加载材料空间文件列表失败: ' + err.message
  } finally {
    fileLoading.value = false
  }
}

// 打开导出 XLSX 数据配置弹窗
function openExportXlsxModal() {
  exportStart.value = start.value || reportState.value?.meta?.start || ''
  exportEnd.value = end.value || reportState.value?.meta?.end || ''
  exportIncludePrev.value = includePrev.value
  showExportXlsxModal.value = true
}

// 导出生产数据并直接下载至本地
async function handleExportXlsxDownload() {
  if (!exportStart.value || !exportEnd.value) {
    alert('请选择起止日期')
    return
  }
  exportingDownload.value = true
  try {
    await exportPeriodReportXlsx({
      start: exportStart.value,
      end: exportEnd.value,
      include_prev: exportIncludePrev.value,
      save_to_space: false
    })
  } catch (err) {
    alert('导出下载 XLSX 失败: ' + err.message)
  } finally {
    exportingDownload.value = false
  }
}

// 导出生产数据并一键保存至材料仓库空间
async function handleExportXlsxSaveToSpace() {
  if (!exportStart.value || !exportEnd.value) {
    alert('请选择起止日期')
    return
  }
  exportingSpace.value = true
  try {
    const res = await exportPeriodReportXlsx({
      start: exportStart.value,
      end: exportEnd.value,
      include_prev: exportIncludePrev.value,
      save_to_space: true
    })
    alert(`🎉 生产运行数据明细已成功保存至材料仓库！\n文件名：${res.file.name}\n大小：${res.file.size_formatted}`)
    if (showFileManagerModal.value) {
      loadFiles()
    }
    showExportXlsxModal.value = false
  } catch (err) {
    alert('保存 XLSX 至材料仓库失败: ' + err.message)
  } finally {
    exportingSpace.value = false
  }
}

// 打开材料空间弹窗
function openFileManager() {
  showFileManagerModal.value = true
  loadFiles()
}

// 一键保存当前分析材料至空间
async function saveCurrentReportToSpace() {
  if (!reportState.value) {
    alert('当前没有可导出的分析汇报数据')
    return
  }
  savingHtml.value = true
  try {
    const filename = getPeriodReportDefaultFilename(reportState.value)
    const content = generateStandalonePeriodReportHtml(reportState.value)
    const res = await savePeriodReportHtml({ filename, content })
    alert(`🎉 当期分析材料已成功保存至空间！\n文件名：${res.name}\n大小：${res.size_formatted}`)
    if (showFileManagerModal.value) {
      loadFiles()
    }
  } catch (err) {
    alert('保存 HTML 文件失败: ' + err.message)
  } finally {
    savingHtml.value = false
  }
}

// 触发文件上传
function triggerUpload() {
  fileInputRef.value?.click()
}

// 处理文件上传
async function handleFileUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.html') && !file.name.toLowerCase().endsWith('.htm')) {
    alert('仅支持上传 .html 或 .htm 格式的分析汇报文件')
    event.target.value = ''
    return
  }
  uploadingFile.value = true
  try {
    const res = await uploadPeriodReportFile(file)
    alert(`上传成功: ${res.name}`)
    await loadFiles()
  } catch (err) {
    alert('上传文件失败: ' + err.message)
  } finally {
    uploadingFile.value = false
    event.target.value = ''
  }
}

// 在当前窗口打开播放器播放指定 HTML 文件
async function openPlayer(fileItem) {
  currentPlayingFile.value = fileItem
  showPlayerModal.value = true
  playerLoading.value = true
  playerHtmlContent.value = ''
  try {
    const res = await fetchPeriodReportContent(fileItem.rel_path)
    playerHtmlContent.value = res.content
  } catch (err) {
    alert('读取汇报内容失败: ' + err.message)
    showPlayerModal.value = false
  } finally {
    playerLoading.value = false
  }
}

// 关闭播放器
function closePlayer() {
  showPlayerModal.value = false
  playerHtmlContent.value = ''
  currentPlayingFile.value = null
}

// 在新标签页中打开播放
function openPlayerInNewTab() {
  if (!playerHtmlContent.value) return
  const blob = new Blob([playerHtmlContent.value], { type: 'text/html;charset=utf-8' })
  const blobUrl = URL.createObjectURL(blob)
  window.open(blobUrl, '_blank')
}

// 全屏播放 iframe
function toggleIframeFullscreen() {
  if (playerIframeRef.value) {
    if (playerIframeRef.value.requestFullscreen) {
      playerIframeRef.value.requestFullscreen()
    }
  }
}

// 下载文件
async function downloadFile(relPath) {
  try {
    await downloadPeriodReportFile(relPath)
  } catch (err) {
    alert('下载文件失败: ' + err.message)
  }
}

// 重命名文件状态与操作
const showRenameModal = ref(false)
const renamingFile = ref(null)
const renameInput = ref('')
const renamingLoading = ref(false)
const renameInputRef = ref(null)

function openRenameModal(fileItem) {
  if (fileItem.is_template) {
    alert('系统核心模板受保护，禁止重命名')
    return
  }
  renamingFile.value = fileItem
  const ext = fileItem.ext || (fileItem.name.endsWith('.xlsx') ? '.xlsx' : '.html')
  let baseName = fileItem.name
  if (baseName.toLowerCase().endsWith(ext.toLowerCase())) {
    baseName = baseName.slice(0, -ext.length)
  }
  renameInput.value = baseName
  showRenameModal.value = true
  nextTick(() => {
    renameInputRef.value?.focus()
    renameInputRef.value?.select()
  })
}

function closeRenameModal() {
  showRenameModal.value = false
  renamingFile.value = null
  renameInput.value = ''
  renamingLoading.value = false
}

async function confirmRenameFile() {
  if (!renamingFile.value) return
  const newBase = renameInput.value.trim()
  if (!newBase) {
    alert('新文件名不能为空')
    return
  }
  const ext = renamingFile.value.ext || (renamingFile.value.name.endsWith('.xlsx') ? '.xlsx' : '.html')
  const newFullName = `${newBase}${ext}`
  if (newFullName === renamingFile.value.name) {
    closeRenameModal()
    return
  }
  renamingLoading.value = true
  try {
    const res = await renamePeriodReportFile(renamingFile.value.rel_path, newFullName)
    alert(`🎉 重命名成功！\n新文件名：${res.name}`)
    closeRenameModal()
    await loadFiles()
  } catch (err) {
    alert('重命名失败: ' + err.message)
  } finally {
    renamingLoading.value = false
  }
}

// 删除文件
async function deleteFile(fileItem) {
  if (fileItem.is_template) {
    alert('系统核心模板受保护，禁止删除')
    return
  }
  if (!confirm(`确认要删除汇报材料【${fileItem.name}】吗？此操作不可恢复。`)) {
    return
  }
  try {
    await deletePeriodReportFile(fileItem.rel_path)
    alert('删除成功')
    await loadFiles()
  } catch (err) {
    alert('删除文件失败: ' + err.message)
  }
}

// ==================== 工作流目录（Workflow Space）状态与方法 ====================
const showWorkflowModal = ref(false)
const currentWorkflowFolder = ref('')
const workflowParentFolder = ref(null)
const workflowBreadcrumbs = ref([{ name: '工作流根目录', path: '' }])
const workflowDirectories = ref([])
const workflowFiles = ref([])
const workflowFileList = ref([]) // 兼容字段
const workflowLoading = ref(false)
const workflowUploading = ref(false)
const workflowArchiving = ref(false)
const workflowSearchKeyword = ref('')
const workflowFileInputRef = ref(null)
const uploadTargetFolder = ref('')

// 新建文件夹状态
const showNewFolderModal = ref(false)
const newFolderName = ref('')
const newFolderLoading = ref(false)
const newFolderInputRef = ref(null)

// 工作流重命名状态
const showWorkflowRenameModal = ref(false)
const workflowRenamingFile = ref(null)
const workflowRenameInput = ref('')
const workflowRenamingLoading = ref(false)
const workflowRenameInputRef = ref(null)

// Markdown / 文本在线阅读视口状态
const showDocReaderModal = ref(false)
const docReaderData = ref({ name: '', rel_path: '', content: '', updated_at: '', size_formatted: '' })
const docReaderLoading = ref(false)

// 计算属性：当前层级过滤后的子文件夹
const filteredWorkflowDirectories = computed(() => {
  let list = workflowDirectories.value || []
  const kw = workflowSearchKeyword.value.trim().toLowerCase()
  if (kw) {
    list = list.filter(d => d.name.toLowerCase().includes(kw))
  }
  return list
})

// 计算属性：当前层级过滤后的直接文件
const filteredWorkflowFiles = computed(() => {
  let list = workflowFiles.value || []
  const kw = workflowSearchKeyword.value.trim().toLowerCase()
  if (kw) {
    list = list.filter(f => f.name.toLowerCase().includes(kw) || f.rel_path.toLowerCase().includes(kw))
  }
  return list
})

// 计算属性：当前层级总项目数
const totalCurrentItemsCount = computed(() => {
  return filteredWorkflowDirectories.value.length + filteredWorkflowFiles.value.length
})

// 打开工作流空间
function openWorkflowManager() {
  showWorkflowModal.value = true
  currentWorkflowFolder.value = ''
  workflowSearchKeyword.value = ''
  loadWorkflowFiles('')
}

// 加载工作流目录内容（支持指定子目录）
async function loadWorkflowFiles(folder = currentWorkflowFolder.value) {
  workflowLoading.value = true
  try {
    const res = await fetchWorkflowFiles(folder)
    currentWorkflowFolder.value = res.current_folder || ''
    workflowParentFolder.value = res.parent_folder !== undefined ? res.parent_folder : null
    workflowBreadcrumbs.value = res.breadcrumbs && res.breadcrumbs.length > 0
      ? res.breadcrumbs
      : [{ name: '工作流根目录', path: '' }]
    workflowDirectories.value = res.directories || []
    workflowFiles.value = res.files || []
    workflowFileList.value = res.files || []
  } catch (err) {
    alert('加载工作流目录失败: ' + err.message)
  } finally {
    workflowLoading.value = false
  }
}

// 进入指定子文件夹
function openWorkflowFolder(folderPath) {
  currentWorkflowFolder.value = folderPath || ''
  workflowSearchKeyword.value = ''
  loadWorkflowFiles(folderPath || '')
}

// 返回上级目录
function goToParentWorkflowFolder() {
  if (workflowParentFolder.value !== null && workflowParentFolder.value !== undefined) {
    openWorkflowFolder(workflowParentFolder.value)
  }
}

// 新建子文件夹窗口交互
function openNewFolderModal() {
  newFolderName.value = ''
  showNewFolderModal.value = true
  nextTick(() => {
    newFolderInputRef.value?.focus()
  })
}

function closeNewFolderModal() {
  showNewFolderModal.value = false
  newFolderName.value = ''
  newFolderLoading.value = false
}

async function confirmCreateFolder() {
  const name = newFolderName.value.trim()
  if (!name) {
    alert('文件夹名称不能为空')
    return
  }
  if (/[\\/:*?"<>|]/.test(name)) {
    alert('文件夹名称不能包含 \\ / : * ? " < > | 等特殊字符')
    return
  }
  newFolderLoading.value = true
  try {
    const res = await createWorkflowFolder(currentWorkflowFolder.value, name)
    alert(`🎉 文件夹【${name}】创建成功！`)
    closeNewFolderModal()
    await loadWorkflowFiles(currentWorkflowFolder.value)
  } catch (err) {
    alert('创建文件夹失败: ' + err.message)
  } finally {
    newFolderLoading.value = false
  }
}

// 一键打包下载指定或当前目录（ZIP）
async function handleDownloadArchive(targetFolder = null) {
  const folderToPack = targetFolder !== null ? targetFolder : currentWorkflowFolder.value
  const targetDesc = folderToPack ? `子目录【${folderToPack}】` : '全量工作流根目录'
  workflowArchiving.value = true
  try {
    const res = await downloadWorkflowArchive(folderToPack)
    alert(`🎉 打包下载已启动！\n打包范围：${targetDesc}\n文件名：${res.filename}`)
  } catch (err) {
    alert('打包下载失败: ' + err.message)
  } finally {
    workflowArchiving.value = false
  }
}

// 复制工作流物理路径
function copyWorkflowPath() {
  const sub = currentWorkflowFolder.value ? `/${currentWorkflowFolder.value}` : ''
  const path = `backend_data/projects/daily_report_25_26/period_report/工作流${sub}`
  navigator.clipboard.writeText(path)
  alert('已复制工作流目录相对路径至剪贴板：\n' + path)
}

// 触发工作流上传（上传至当前所在目录）
function triggerWorkflowUpload() {
  uploadTargetFolder.value = currentWorkflowFolder.value || ''
  workflowFileInputRef.value?.click()
}

// 处理工作流上传
async function handleWorkflowUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  workflowUploading.value = true
  try {
    const res = await uploadWorkflowFile(file, uploadTargetFolder.value)
    alert(`🎉 工作流文件上传成功: ${res.name}`)
    await loadWorkflowFiles(currentWorkflowFolder.value)
  } catch (err) {
    alert('上传工作流文件失败: ' + err.message)
  } finally {
    workflowUploading.value = false
    event.target.value = ''
  }
}

// 在线查看文档（Markdown / 纯文本）
async function openDocReader(fileItem) {
  showDocReaderModal.value = true
  docReaderLoading.value = true
  docReaderData.value = {
    name: fileItem.name,
    rel_path: fileItem.rel_path,
    content: '正在加载文档内容…',
    updated_at: fileItem.updated_at,
    size_formatted: fileItem.size_formatted,
  }
  try {
    const res = await fetchWorkflowFileContent(fileItem.rel_path)
    docReaderData.value = res
  } catch (err) {
    docReaderData.value.content = '加载文档内容失败: ' + err.message
  } finally {
    docReaderLoading.value = false
  }
}

// 关闭文档阅览
function closeDocReader() {
  showDocReaderModal.value = false
  docReaderData.value = { name: '', rel_path: '', content: '' }
}

// 复制阅读器内容
function copyDocContent() {
  if (docReaderData.value?.content) {
    navigator.clipboard.writeText(docReaderData.value.content)
    alert('已复制文档内容至剪贴板')
  }
}

// 下载工作流文件
async function downloadWorkflow(fileItem) {
  try {
    await downloadWorkflowFile(fileItem.rel_path)
  } catch (err) {
    alert('下载文件失败: ' + err.message)
  }
}

// 打开工作流重命名
function openWorkflowRename(fileItem) {
  workflowRenamingFile.value = fileItem
  const ext = fileItem.ext || ''
  let base = fileItem.name
  if (base.toLowerCase().endsWith(ext.toLowerCase())) {
    base = base.slice(0, -ext.length)
  }
  workflowRenameInput.value = base
  showWorkflowRenameModal.value = true
  nextTick(() => {
    workflowRenameInputRef.value?.focus()
    workflowRenameInputRef.value?.select()
  })
}

function closeWorkflowRename() {
  showWorkflowRenameModal.value = false
  workflowRenamingFile.value = null
  workflowRenameInput.value = ''
  workflowRenamingLoading.value = false
}

async function confirmWorkflowRename() {
  if (!workflowRenamingFile.value) return
  const newBase = workflowRenameInput.value.trim()
  if (!newBase) {
    alert('新文件名不能为空')
    return
  }
  const ext = workflowRenamingFile.value.ext || ''
  const newFullName = `${newBase}${ext}`
  if (newFullName === workflowRenamingFile.value.name) {
    closeWorkflowRename()
    return
  }
  workflowRenamingLoading.value = true
  try {
    const res = await renameWorkflowFile(workflowRenamingFile.value.rel_path, newFullName)
    alert(`🎉 工作流文件重命名成功！\n新名称：${res.name}`)
    closeWorkflowRename()
    await loadWorkflowFiles(currentWorkflowFolder.value)
  } catch (err) {
    alert('重命名失败: ' + err.message)
  } finally {
    workflowRenamingLoading.value = false
  }
}

// 删除工作流文件
async function deleteWorkflow(fileItem) {
  if (!confirm(`确认要删除工作流文件【${fileItem.rel_path}】吗？此操作不可恢复。`)) {
    return
  }
  try {
    await deleteWorkflowFile(fileItem.rel_path)
    alert('删除成功')
    await loadWorkflowFiles(currentWorkflowFolder.value)
  } catch (err) {
    alert('删除文件失败: ' + err.message)
  }
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

  const coalCur = k.coalTotal != null ? Math.round(k.coalTotal / 100) : null
  const coalPlan = k.coalPlan != null ? Math.round(k.coalPlan / 100) : null
  const coalSync = k.coalSync != null ? Math.round(k.coalSync / 100) : null
  const coalPrev = k.coalPrev != null ? Math.round(k.coalPrev / 100) : null

  const series = [
    {
      name: '本期实际',
      type: 'bar',
      barMaxWidth: 28,
      itemStyle: { color: c.bar1, borderRadius: [4, 4, 0, 0] },
      data: [coalCur, k.revenueTotal, k.costTotal, k.profitActual, k.profitComparable]
    },
    {
      name: '本期计划',
      type: 'bar',
      barMaxWidth: 28,
      itemStyle: { color: c.bar4, borderRadius: [4, 4, 0, 0] },
      data: [coalPlan, k.revenuePlan, k.costPlan, k.profitPlan, null]
    },
    {
      name: '去年同期',
      type: 'bar',
      barMaxWidth: 28,
      itemStyle: { color: c.bar2, borderRadius: [4, 4, 0, 0] },
      data: [coalSync, k.revenueSync, k.costSync, k.profitSync, k.profitComparableSync]
    }
  ]

  if (hasPrev) {
    series.push({
      name: '上期数值',
      type: 'bar',
      barMaxWidth: 28,
      itemStyle: { color: c.bar3, borderRadius: [4, 4, 0, 0] },
      data: [coalPrev, k.revenuePrev, k.costPrev, k.profitPrev, null]
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
    if (rawData.hasPrev !== undefined) {
      includePrev.value = Boolean(rawData.hasPrev)
    }
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
  document.addEventListener('click', handleClickOutside)

  // 绑定 ResizeObserver 实时监听视口尺寸，确保在任何分辨率伸缩时图表完全贴合
  if (viewportRef.value && window.ResizeObserver) {
    resizeObserver = new ResizeObserver(() => {
      handleResize()
    })
    resizeObserver.observe(viewportRef.value)
  }

  // 默认数据初始化公文故事
  reportState.value.narrative = generateChapterNarrative(reportState.value)

  // 1. 读取页面默认展示模式配置（若配置为某 HTML 则优先呈现该文档）
  loadDisplayConfig()
  loadFiles()

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
  document.removeEventListener('click', handleClickOutside)
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

/* ==================== 空间管理模块与播放器样式 ==================== */
/* Global_admin 控制台下拉菜单样式 */
.console-dropdown-container {
  position: relative;
  display: inline-block;
}

.btn-console-trigger {
  background: linear-gradient(135deg, #1e293b, #0f172a);
  color: #f8fafc;
  border: 1px solid #334155;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  transition: all 0.2s ease;
}

.btn-console-trigger:hover,
.btn-console-trigger.active {
  background: linear-gradient(135deg, #0f172a, #020617);
  border-color: #38bdf8;
  color: #38bdf8;
  box-shadow: 0 2px 6px rgba(56, 189, 248, 0.25);
}

.console-icon {
  font-size: 13px;
}

.dropdown-arrow {
  font-size: 11px;
  transition: transform 0.2s ease;
  display: inline-block;
}

.dropdown-arrow.rotated {
  transform: rotate(180deg);
}

.console-dropdown-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 270px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.25), 0 8px 10px -6px rgba(0, 0, 0, 0.2);
  padding: 6px;
  z-index: 120;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.dropdown-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px 8px 10px;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 4px;
}

.dropdown-title {
  font-size: 11.5px;
  font-weight: 700;
  color: var(--text-muted);
}

.dropdown-tag {
  font-size: 10px;
  font-weight: 700;
  background: #0284c7;
  color: #fff;
  padding: 1px 6px;
  border-radius: 4px;
  letter-spacing: 0.5px;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 10px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s ease, transform 0.1s ease;
}

.dropdown-item:hover:not(:disabled) {
  background: var(--bg-sub);
  transform: translateX(2px);
}

.dropdown-item:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.dropdown-item .item-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.dropdown-item .item-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.dropdown-item .item-title {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-main);
}

.dropdown-item .item-desc {
  font-size: 10.5px;
  color: var(--text-muted);
  line-height: 1.25;
}

.dropdown-divider {
  height: 1px;
  background: var(--border-color);
  margin: 4px 6px;
}

/* 过渡动画 */
.dropdown-fade-enter-active,
.dropdown-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.dropdown-fade-enter-from,
.dropdown-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.btn-save-html {
  background: #059669;
  color: #fff;
  border-color: #059669;
}
.btn-save-html:hover:not(:disabled) {
  background: #047857;
  color: #fff;
}
.btn-export-xlsx {
  background: #0d9488;
  color: #fff;
  border-color: #0d9488;
}
.btn-export-xlsx:hover {
  background: #0f766e;
  color: #fff;
}
.btn-space-manage {
  background: #0284c7;
  color: #fff;
  border-color: #0284c7;
}
.btn-space-manage:hover {
  background: #0369a1;
  color: #fff;
}

.modal-card-md {
  max-width: 680px;
}
.modal-card-lg {
  max-width: 1050px;
}

.export-modal-body {
  padding: 16px 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group-row {
  display: flex;
  gap: 14px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-main);
}

.form-input {
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-main);
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  outline: none;
}
.form-input:focus {
  border-color: #0284c7;
}

.export-opt-box {
  background: var(--bg-sub);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 12px 14px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  cursor: pointer;
  user-select: none;
}
.checkbox-input {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.opt-desc {
  margin: 6px 0 0 24px;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--text-muted);
}

.sheets-preview-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sheets-preview-card .card-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 2px;
}
.sheet-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--text-sub);
}
.sheet-badge {
  background: #e0f2fe;
  color: #0369a1;
  font-weight: 700;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  white-space: nowrap;
}

.btn-success {
  background: #059669;
  color: #fff;
  border: none;
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}
.btn-success:hover {
  background: #047857;
}
.btn-success:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-export-down {
  background: #0284c7;
}
.btn-export-down:hover {
  background: #0369a1;
}

/* ==================== 空间管理中枢深度优化样式 ==================== */
.modal-card-space {
  max-width: 1240px;
  width: 95vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  padding: 20px 24px 16px;
  border-radius: 16px;
  box-shadow: 0 25px 60px -12px rgba(0, 0, 0, 0.45);
}

.space-modal-header {
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border-color);
}
.space-header-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.space-title-icon {
  font-size: 20px;
}
.space-title-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 9999px;
  background: linear-gradient(135deg, #0284c7, #0d9488);
  color: #fff;
  letter-spacing: 0.5px;
}
.space-btn-close {
  background: var(--bg-sub);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}
.space-btn-close:hover {
  background: var(--border-color);
  color: var(--text-main);
}

/* 工具栏与筛选行 */
.space-toolbar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0 14px;
  gap: 12px;
  flex-wrap: wrap;
}
.space-toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.space-btn-upload {
  padding: 7px 14px;
  font-size: 12.5px;
  font-weight: 600;
  border-radius: 8px;
}
.space-btn-refresh {
  padding: 7px 12px;
  font-size: 12px;
  border-radius: 8px;
}
.space-toolbar-divider {
  width: 1px;
  height: 22px;
  background: var(--border-color);
  margin: 0 4px;
}

/* 分类药丸 Tab */
.space-filter-pills {
  display: flex;
  align-items: center;
  background: var(--bg-sub);
  padding: 3px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  gap: 2px;
}
.filter-pill {
  border: none;
  background: transparent;
  color: var(--text-sub);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.18s;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.filter-pill:hover {
  color: var(--text-main);
}
.filter-pill.active {
  background: var(--bg-card);
  color: var(--text-main);
  font-weight: 700;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
}
.filter-pill .pill-count {
  font-size: 10.5px;
  opacity: 0.7;
}

/* 搜索框 */
.space-toolbar-right {
  display: flex;
  align-items: center;
}
.space-search-box {
  display: flex;
  align-items: center;
  background: var(--bg-sub);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 4px 10px;
  width: 220px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.space-search-box:focus-within {
  border-color: #0284c7;
  box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.15);
}
.space-search-box .search-icon {
  font-size: 12px;
  color: var(--text-muted);
  margin-right: 6px;
}
.space-search-input {
  border: none;
  background: transparent;
  color: var(--text-main);
  font-size: 12px;
  width: 100%;
  outline: none;
}
.search-clear-btn {
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 11px;
  padding: 0 2px;
}
.search-clear-btn:hover {
  color: var(--text-main);
}

/* 表格卡片容器 */
.space-table-card {
  flex: 1;
  min-height: 320px;
  max-height: 52vh;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
}
.space-table-scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: auto;
  margin: 0;
}
.space-table {
  width: 100%;
  min-width: 1040px;
  table-layout: fixed;
  border-collapse: collapse;
}
.space-table th {
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--bg-sub);
  color: var(--text-muted);
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.3px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-color);
  text-align: left;
}
.space-file-row {
  border-bottom: 1px solid var(--border-color);
  transition: background 0.15s;
}
.space-file-row:last-child {
  border-bottom: none;
}
.space-file-row:hover {
  background: rgba(2, 132, 199, 0.04);
}
.space-table td {
  padding: 10px 14px;
  vertical-align: middle;
}

/* 文件名称列 */
.space-file-title-cell {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.space-file-avatar {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}
.avatar-excel {
  background: #dcfce7;
  color: #15803d;
  border: 1px solid #bbf7d0;
}
.avatar-html {
  background: #e0f2fe;
  color: #0369a1;
  border: 1px solid #bae6fd;
}
.avatar-template {
  background: #fef3c7;
  color: #b45309;
  border: 1px solid #fde68a;
}
.space-file-name-meta {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  flex: 1;
}
.space-file-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}
.space-file-name:hover {
  color: #0284c7;
  text-decoration: underline;
}
.space-file-sub-tags {
  display: flex;
  align-items: center;
  gap: 6px;
}
.file-ext-tag {
  font-family: monospace;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  background: var(--bg-sub);
  color: var(--text-muted);
  padding: 1px 5px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
}
.file-sub-note {
  font-size: 10.5px;
  color: var(--text-muted);
}

/* 分类徽章 */
.space-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 9999px;
  white-space: nowrap;
}
.badge-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  display: inline-block;
}
.badge-excel {
  background: #dcfce7;
  color: #15803d;
}
.badge-excel .badge-dot { background: #16a34a; }
.badge-template {
  background: #fef3c7;
  color: #b45309;
}
.badge-template .badge-dot { background: #d97706; }
.badge-report {
  background: #e0f2fe;
  color: #0369a1;
}
.badge-report .badge-dot { background: #0284c7; }
.badge-doc {
  background: var(--bg-sub);
  color: var(--text-sub);
  border: 1px solid var(--border-color);
}
.badge-doc .badge-dot { background: var(--text-muted); }

/* 文件大小 */
.space-size-text {
  font-family: monospace;
  font-size: 11.5px;
  color: var(--text-sub);
}

/* 时间列（双行卡片） */
.space-time-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-family: monospace;
}
.time-primary {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  color: var(--text-main);
  font-weight: 600;
}
.time-secondary {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  color: var(--text-muted);
}
.time-label {
  font-size: 10px;
  opacity: 0.7;
}

/* 操作按钮组 */
.space-actions-group {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  flex-wrap: nowrap;
  flex-shrink: 0;
}
.space-btn-action {
  border: 1px solid var(--border-color);
  background: var(--bg-sub);
  color: var(--text-main);
  border-radius: 6px;
  padding: 3.5px 7px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  transition: all 0.18s;
  white-space: nowrap;
  flex-shrink: 0;
  line-height: 1.2;
}
.space-btn-action:hover {
  border-color: #0284c7;
  color: #0284c7;
  transform: translateY(-1px);
}
.space-btn-action.action-play {
  background: #0284c7;
  border-color: #0284c7;
  color: #fff;
  font-weight: 600;
}
.space-btn-action.action-play:hover {
  background: #0369a1;
  border-color: #0369a1;
  color: #fff;
}
.space-btn-action.action-del {
  color: #b91c1c;
  border-color: #fca5a5;
  background: #fee2e2;
  padding: 4px 6px;
}
.space-btn-action.action-del:hover {
  background: #ef4444;
  color: #fff;
  border-color: #ef4444;
}
.space-badge-protected {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--bg-sub);
  padding: 3px 8px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
}

/* 空状态单元格 */
.space-empty-cell {
  padding: 48px 16px !important;
  text-align: center;
}
.space-empty-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.space-empty-icon {
  font-size: 36px;
  opacity: 0.5;
}
.space-empty-title {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-main);
  margin: 0;
}
.space-empty-desc {
  font-size: 11.5px;
  color: var(--text-muted);
  margin: 0;
}

/* 弹窗 Footer */
.space-modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0 0;
  margin-top: 10px;
  border-top: 1px solid var(--border-color);
}
.space-path-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  background: var(--bg-sub);
  border: 1px solid var(--border-color);
  transition: all 0.2s;
}
.space-path-tag:hover {
  border-color: #0284c7;
  color: #0284c7;
}
.space-pack-tag:hover {
  border-color: #7c3aed !important;
  color: #6d28d9 !important;
  background: #ede9fe !important;
}
.space-path-tag code {
  font-family: monospace;
  font-size: 10.5px;
}
.space-path-tag .copy-hint {
  font-size: 10px;
  background: rgba(2, 132, 199, 0.12);
  color: #0284c7;
  padding: 1px 4px;
  border-radius: 4px;
  font-weight: 600;
}
.space-footer-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.space-stats-hint {
  font-size: 11.5px;
  color: var(--text-muted);
}
.space-btn-close-main {
  padding: 7px 18px;
  font-size: 12.5px;
  font-weight: 600;
  border-radius: 8px;
}

/* 工作流专属卡片与阅读器样式 */
.workflow-breadcrumb-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: var(--bg-sub);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  margin-bottom: 12px;
}
.breadcrumb-left {
  display: flex;
  align-items: center;
  gap: 10px;
  overflow-x: auto;
}
.btn-nav-back {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s;
  white-space: nowrap;
}
.btn-nav-back:hover {
  border-color: #7c3aed;
  color: #7c3aed;
  background: #f5f3ff;
}
.breadcrumb-trail {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
}
.breadcrumb-node {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--text-muted);
  font-weight: 500;
  transition: all 0.15s;
}
.breadcrumb-node:hover {
  background: rgba(124, 58, 237, 0.08);
  color: #7c3aed;
}
.breadcrumb-node.active {
  color: var(--text-main);
  font-weight: 700;
  cursor: default;
}
.breadcrumb-node.active:hover {
  background: transparent;
}
.breadcrumb-sep {
  color: var(--text-muted);
  opacity: 0.5;
  margin-left: 4px;
}
.location-badge {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
}
.location-badge code {
  color: #7c3aed;
  font-weight: 600;
  background: rgba(124, 58, 237, 0.08);
  padding: 1px 6px;
  border-radius: 4px;
}

/* 文件夹行专属样式 */
.space-dir-row {
  cursor: pointer;
  transition: background-color 0.15s;
}
.space-dir-row:hover {
  background-color: rgba(245, 158, 11, 0.06) !important;
}
.avatar-folder {
  background: #fef3c7;
  color: #d97706;
  border: 1px solid #fde68a;
  font-size: 16px;
}
.space-dir-name {
  font-weight: 700;
  color: var(--text-main);
  cursor: pointer;
  transition: color 0.15s;
}
.space-dir-name:hover {
  color: #d97706;
  text-decoration: underline;
}
.badge-dir {
  background: #fef3c7;
  color: #b45309;
}
.badge-dir .badge-dot {
  background: #f59e0b;
}
.space-dir-count {
  font-size: 11.5px;
  color: var(--text-muted);
}
.action-enter {
  background: #fef3c7;
  color: #b45309;
  border-color: #fde68a;
  font-weight: 600;
}
.action-enter:hover {
  background: #fde68a;
  color: #92400e;
  border-color: #f59e0b;
}

.avatar-md {
  background: #ede9fe;
  color: #7c3aed;
  border: 1px solid #ddd6fe;
}
.badge-markdown {
  background: #ede9fe;
  color: #6d28d9;
}
.badge-markdown .badge-dot {
  background: #7c3aed;
}
.badge-folder {
  background: var(--bg-sub);
  color: var(--text-muted);
  border: 1px solid var(--border-color);
}
.badge-folder .badge-dot {
  background: var(--text-muted);
}
.action-read {
  background: #7c3aed;
  color: #fff;
  border-color: #7c3aed;
  font-weight: 600;
}
.action-read:hover {
  background: #6d28d9;
  border-color: #6d28d9;
  color: #fff;
}
.badge-tag-purple {
  background: #ede9fe;
  color: #6d28d9;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 9999px;
}
.doc-reader-card {
  max-width: 1000px;
  width: 92vw;
  max-height: 86vh;
  display: flex;
  flex-direction: column;
}
.doc-reader-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
}
.doc-reader-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.doc-reader-body {
  flex: 1;
  overflow-y: auto;
  padding: 18px 22px;
  background: var(--bg-sub);
  border-radius: 10px;
  margin: 14px 0;
  border: 1px solid var(--border-color);
}
.doc-reader-content {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 13.5px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--text-main);
}

.modal-card-sm {
  width: 100%;
  max-width: 440px;
}

/* 沉浸式 HTML 播放器 */
.player-overlay {
  position: fixed;
  inset: 0;
  background: #020617;
  z-index: 200;
  display: flex;
  flex-direction: column;
}

.player-header {
  height: 50px;
  min-height: 50px;
  background: rgba(15, 23, 42, 0.96);
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  color: #fff;
}

.player-title-box {
  display: flex;
  align-items: center;
  gap: 10px;
}

.player-title {
  font-size: 14px;
  font-weight: 700;
  margin: 0;
  color: #f8fafc;
}

.player-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-tool-dark {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #f8fafc;
  border-radius: 6px;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-tool-dark:hover {
  background: rgba(255, 255, 255, 0.2);
}

.btn-close-player {
  background: #dc2626;
  border-color: #ef4444;
}
.btn-close-player:hover {
  background: #b91c1c;
}

.player-body {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: #000;
}

.player-iframe {
  width: 100%;
  height: 100%;
  border: none;
  background: #fff;
}

.player-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #38bdf8;
  background: #090d16;
}

.spinner-lg {
  width: 32px;
  height: 32px;
  border-width: 3px;
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

/* ==================== 默认材料空间 HTML 页面视口样式 ==================== */
.custom-html-stage {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 58px);
  background: var(--bg-body);
  overflow: hidden;
}

.custom-html-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  font-size: 13px;
  z-index: 10;
}

.banner-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.badge-custom-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 9999px;
  font-size: 11px;
  font-weight: 700;
  background: #ecfdf5;
  color: #059669;
  border: 1px solid #a7f3d0;
}

.dark-theme .badge-custom-tag {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  border-color: rgba(16, 185, 129, 0.3);
}

.banner-filename {
  font-weight: 600;
  color: var(--text-primary);
}

.banner-time {
  font-size: 11px;
  color: var(--text-muted);
}

.banner-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-highlight {
  background: #2563eb !important;
  color: #fff !important;
  border-color: #1d4ed8 !important;
  font-weight: 600;
}

.btn-highlight:hover {
  background: #1d4ed8 !important;
}

.btn-back-custom {
  background: #f0fdf4 !important;
  color: #15803d !important;
  border-color: #bbf7d0 !important;
  font-weight: 600;
}

.dark-theme .btn-back-custom {
  background: rgba(22, 101, 52, 0.25) !important;
  color: #4ade80 !important;
  border-color: rgba(74, 222, 128, 0.3) !important;
}

.custom-html-container {
  flex: 1;
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #fff;
}

.dark-theme .custom-html-container {
  background: #0f172a;
}

.custom-html-frame {
  width: 100%;
  height: 100%;
  border: none;
  display: block;
}

.custom-loading-box, .custom-error-box {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: var(--text-muted);
  font-size: 14px;
}

/* ==================== 设定默认显示弹窗与模式选项卡 ==================== */
.display-mode-selector {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mode-option-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 14px;
  border: 1.5px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  background: var(--bg-card);
  transition: all 0.18s ease;
}

.mode-option-card:hover {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.04);
}

.mode-option-card.selected {
  border-color: #2563eb;
  background: rgba(37, 99, 235, 0.08);
}

.badge-default-active {
  display: inline-flex;
  align-items: center;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10.5px;
  font-weight: 600;
  background: #fef3c7;
  color: #b45309;
  border: 1px solid #fde68a;
  margin-left: 4px;
}

.dark-theme .badge-default-active {
  background: rgba(245, 158, 11, 0.2);
  color: #fbbf24;
  border-color: rgba(245, 158, 11, 0.35);
}

.file-folder-tag {
  display: inline-flex;
  align-items: center;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10.5px;
  background: #f1f5f9;
  color: #475569;
  margin-left: 4px;
}

.dark-theme .file-folder-tag {
  background: rgba(148, 163, 184, 0.15);
  color: #94a3b8;
}

.action-setdefault {
  color: #d97706 !important;
}

.action-setdefault:hover {
  background: #fef3c7 !important;
  color: #b45309 !important;
}

.action-transfer {
  color: #0284c7 !important;
}

.action-transfer:hover {
  background: #e0f2fe !important;
  color: #0369a1 !important;
}

/* ==================== 移动与传输文件弹窗专属美化样式 ==================== */
.modal-card-transfer {
  max-width: 660px !important;
  width: 94vw !important;
  border-radius: 16px;
  box-shadow: 0 25px 60px -12px rgba(0, 0, 0, 0.45);
  display: flex;
  flex-direction: column;
  padding: 20px 24px 18px;
  background: var(--bg-card);
}

.transfer-modal-header {
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border-color);
}

.transfer-icon-badge {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #e0f2fe, #ede9fe);
  border: 1px solid #c7d2fe;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.transfer-mode-pill {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 9999px;
  letter-spacing: 0.3px;
}
.transfer-mode-pill.pill-cross {
  background: #ede9fe;
  color: #6d28d9;
  border: 1px solid #ddd6fe;
}
.transfer-mode-pill.pill-internal {
  background: #e0f2fe;
  color: #0369a1;
  border: 1px solid #bae6fd;
}

.transfer-modal-body {
  padding: 16px 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* 流向看板 (Transfer Flow Canvas) */
.transfer-flow-card {
  display: grid;
  grid-template-columns: 1fr 68px 1fr;
  align-items: center;
  background: var(--bg-sub);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 12px 14px;
  gap: 8px;
}

.flow-endpoint {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
.endpoint-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
}
.endpoint-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
}
.endpoint-badge.source-tag {
  background: #e2e8f0;
  color: #475569;
}
.endpoint-badge.target-tag {
  background: #dbeafe;
  color: #1e40af;
}
.endpoint-space-name {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
}
.endpoint-file-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.file-icon-box {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  flex-shrink: 0;
}
.file-icon-box.icon-html {
  background: #e0f2fe;
  border: 1px solid #bae6fd;
}
.file-icon-box.icon-excel {
  background: #dcfce7;
  border: 1px solid #bbf7d0;
}
.file-icon-box.icon-md {
  background: #ede9fe;
  border: 1px solid #ddd6fe;
}
.file-icon-box.icon-folder {
  background: #fef3c7;
  border: 1px solid #fde68a;
}
.file-info-col {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}
.file-main-name {
  font-size: 12.5px;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.file-sub-path {
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.flow-arrow-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
.flow-arrow-circle {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  transition: all 0.2s;
}
.flow-arrow-circle.circle-move {
  background: #fef3c7;
  color: #b45309;
  border: 1px solid #fde68a;
}
.flow-arrow-circle.circle-copy {
  background: #ede9fe;
  color: #7c3aed;
  border: 1px solid #ddd6fe;
}
.flow-action-text {
  font-size: 10px;
  letter-spacing: 0.2px;
}

/* 分块容器与大卡片网格 */
.transfer-section-box {
  display: flex;
  flex-direction: column;
}
.section-label {
  color: var(--text-main);
  letter-spacing: 0.2px;
}
.space-choice-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.space-choice-card {
  padding: 10px 12px;
  border: 1.5px solid var(--border-color);
  background: var(--bg-card);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.18s ease;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.space-choice-card:hover:not(.disabled) {
  border-color: #0284c7;
  background: rgba(2, 132, 199, 0.04);
}
.space-choice-card.active {
  border-color: #0284c7;
  background: rgba(2, 132, 199, 0.08);
  box-shadow: 0 0 0 1px #0284c7;
}
.space-choice-card.disabled {
  opacity: 0.55;
  cursor: not-allowed;
  background: var(--bg-sub);
}
.choice-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.choice-title {
  font-size: 12.5px;
  color: var(--text-main);
}
.choice-check {
  font-size: 11px;
  font-weight: 700;
  color: #0284c7;
  background: #e0f2fe;
  padding: 1px 6px;
  border-radius: 4px;
}
.choice-lock {
  font-size: 10.5px;
  color: #b45309;
  background: #fef3c7;
  padding: 1px 5px;
  border-radius: 4px;
}
.choice-desc {
  font-size: 11px;
  line-height: 1.4;
}

/* 目标文件夹下拉与新建按钮 */
.btn-new-folder-inline {
  background: transparent;
  border: none;
  color: #0284c7;
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 6px;
  border-radius: 4px;
  transition: background 0.15s;
}
.btn-new-folder-inline:hover {
  background: rgba(2, 132, 199, 0.1);
}
.transfer-loading-folders {
  padding: 8px 12px;
  background: var(--bg-sub);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-size: 12px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 6px;
}
.folder-select-wrap {
  width: 100%;
}
.transfer-select {
  width: 100%;
  padding: 8px 12px;
  font-size: 12.5px;
  border: 1.5px solid var(--border-color);
  background: var(--bg-sub);
  color: var(--text-main);
  border-radius: 8px;
  outline: none;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.transfer-select:focus {
  border-color: #0284c7;
  box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.15);
}

/* 操作方式选择 (移动 vs 复制) */
.action-mode-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.action-mode-card {
  padding: 10px 12px;
  border: 1.5px solid var(--border-color);
  background: var(--bg-card);
  border-radius: 10px;
  cursor: pointer;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  transition: all 0.18s ease;
}
.action-mode-card:hover:not(.disabled) {
  border-color: #0284c7;
  background: rgba(2, 132, 199, 0.04);
}
.action-mode-card.active {
  border-color: #0284c7;
  background: rgba(2, 132, 199, 0.08);
  box-shadow: 0 0 0 1px #0284c7;
}
.action-mode-card.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--bg-sub);
}
.mode-card-radio {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 1px;
  flex-shrink: 0;
}
.action-mode-card.active .mode-card-radio {
  border-color: #0284c7;
}
.radio-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #0284c7;
}
.mode-card-content {
  display: flex;
  flex-direction: column;
}

/* 冲突选项 */
.conflict-option-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 10px;
  background: var(--bg-sub);
  border: 1px dashed var(--border-color);
  border-radius: 8px;
}
.conflict-toggle-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: var(--text-main);
}
.conflict-checkbox {
  cursor: pointer;
  accent-color: #0284c7;
}

/* 物理路径预览 */
.transfer-preview-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--bg-sub);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-size: 11px;
  overflow: hidden;
}
.preview-icon {
  font-size: 13px;
  flex-shrink: 0;
}
.preview-label {
  color: var(--text-muted);
  font-weight: 600;
  flex-shrink: 0;
}
.preview-code {
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

/* 底栏 */
.transfer-modal-footer {
  padding-top: 14px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.transfer-submit-btn {
  padding: 8px 18px;
  font-size: 13px;
  font-weight: 600;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}
.transfer-submit-btn.btn-move {
  background: #0284c7;
  border-color: #0284c7;
}
.transfer-submit-btn.btn-move:hover {
  background: #0369a1;
  border-color: #0369a1;
}
.transfer-submit-btn.btn-copy {
  background: #7c3aed;
  border-color: #7c3aed;
}
.transfer-submit-btn.btn-copy:hover {
  background: #6d28d9;
  border-color: #6d28d9;
}

.modal-card-sm {
  max-width: 540px !important;
  width: 90% !important;
}
</style>
