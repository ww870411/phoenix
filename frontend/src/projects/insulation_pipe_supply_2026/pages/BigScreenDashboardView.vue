<template>
  <div class="bigscreen-container" :class="[currentTheme]" ref="containerRef">
    <!-- 顶部科技流光控制栏 -->
    <header class="bigscreen-header">
      <div class="header-left">
        <div class="header-badge" :class="{ 'live-mode': isLiveStreamMode }">
          <span class="pulse-dot" :class="{ live: isLiveStreamMode }"></span>
          <span class="badge-text">全链追踪 · 实时调度中心</span>
        </div>
        <div class="header-time">{{ currentTimeStr }}</div>
      </div>

      <div class="header-title-box">
        <h1 class="header-title">大连洁净能源集团·2026年度老旧管网改造项目物流链智慧管理平台</h1>
        <div class="header-sub">
          <span>三大保供制造管厂直供现场</span>
          <span class="sub-sep">|</span>
          <span>全网 10 大施工标段</span>
          <span class="sub-sep">|</span>
          <span>1138项物料基准</span>
        </div>
      </div>

      <!-- 右侧：单一整合控制中心按钮 + 展开式控制面板 -->
      <div class="header-right" ref="controlMenuRef">
        <div class="control-center-wrapper">
          <!-- 触发主按钮 -->
          <button 
            class="action-btn control-trigger-btn"
            :class="{ active: isControlMenuOpen, 'live-active': isLiveStreamMode }"
            @click.stop="toggleControlMenu"
            title="点击打开/收起大屏控制中心"
          >
            <span class="btn-icon">⚙️</span>
            <span class="btn-text">调度控制中心</span>
            <span class="control-caret">{{ isControlMenuOpen ? '▲' : '▼' }}</span>
            <span v-if="isLiveStreamMode" class="mini-live-tag">实况中</span>
          </button>

          <!-- 浮层下拉控制面板 -->
          <transition name="control-dropdown">
            <div v-if="isControlMenuOpen" class="control-menu-popover" @click.stop>
              <div class="popover-header">
                <span class="popover-title">🎮 调度与大屏控制台</span>
                <button class="popover-close-btn" @click="isControlMenuOpen = false" title="关闭">✕</button>
              </div>

              <div class="popover-group">
                <div class="group-title">数据与视图模式</div>
                <div class="group-buttons-grid">
                  <!-- 接入真实数据流 -->
                  <button 
                    class="action-btn live-stream-btn" 
                    :class="{ active: isLiveStreamMode }" 
                    @click="toggleLiveStreamMode"
                    :title="isLiveStreamMode ? '已接入真实数据流（只读安全感知），点击断开' : '点击接入真实数据库实时数据流，展示真实数据状态与实时发运累计'"
                  >
                    <span class="btn-icon">{{ isLiveStreamMode ? '🟢' : '📡' }}</span>
                    <span>{{ isLiveStreamMode ? '断开实况' : '接入实况' }}</span>
                  </button>

                  <!-- 浅色/深色模式切换 -->
                  <button 
                    class="action-btn theme-toggle-btn" 
                    @click="toggleTheme"
                    :title="isDark ? '切换至明亮浅色模式' : '切换至科技深色模式'"
                  >
                    <span class="btn-icon">{{ isDark ? '☀️' : '🌙' }}</span>
                    <span>{{ isDark ? '浅色' : '深色' }}</span>
                  </button>

                  <!-- 强制刷新 -->
                  <button class="action-btn icon-btn" @click="loadRealData(true)" title="即刻强制刷新数据库全量数据">
                    <span class="btn-icon">🔄</span>
                    <span>刷新数据</span>
                  </button>

                  <!-- 全屏展示 -->
                  <button class="action-btn icon-btn" @click="toggleFullscreen" title="全屏展示">
                    <span class="btn-icon">{{ isFullscreen ? '🗗' : '⛶' }}</span>
                    <span>{{ isFullscreen ? '退出全屏' : '全屏展示' }}</span>
                  </button>
                </div>
              </div>

              <div class="popover-group">
                <div class="group-title">沙盒演示与模拟</div>
                <div class="group-buttons-grid">
                  <!-- 自动演示 -->
                  <button 
                    class="action-btn demo-btn" 
                    :class="{ active: autoDemoRunning }" 
                    @click="toggleAutoDemo"
                    title="开启/暂停沙盒自动演示流"
                  >
                    <span class="btn-icon">{{ autoDemoRunning ? '⏸️' : '▶️' }}</span>
                    <span>{{ autoDemoRunning ? '演示中' : '自动演示' }}</span>
                  </button>

                  <!-- 模拟管材 -->
                  <button class="action-btn sim-btn" @click="triggerSimulateDelivery('pipe')">
                    <span class="btn-icon">🏭</span>
                    <span>模拟管材</span>
                  </button>

                  <!-- 模拟管件 -->
                  <button class="action-btn sim-btn fitting" @click="triggerSimulateDelivery('fitting')">
                    <span class="btn-icon">📦</span>
                    <span>模拟管件</span>
                  </button>
                </div>
              </div>

              <div class="popover-footer">
                <button class="action-btn back-btn" @click="goBackToStandardDashboard" title="返回标准看板">
                  <span class="btn-icon">↩</span>
                  <span>返回标准看板</span>
                </button>
              </div>
            </div>
          </transition>
        </div>
      </div>
    </header>

    <!-- 主展示区：三栏网格体系 -->
    <main class="bigscreen-content">
      <!-- 左侧栏：全局指标体系与管材/管件双轨大盘 (100% 真实数据库计算) -->
      <section class="screen-col left-col">
        <!-- 核心指标1：管材全网发运与在途 (真实数据库聚合) -->
        <div class="panel-box pipe-kpi-panel">
          <div class="panel-header">
            <div class="panel-title">
              <span class="title-icon">📐</span>
              <span>保温管全网发运与在途</span>
            </div>
            <span class="panel-tag cyan">保温管总线</span>
          </div>

          <div class="kpi-metric-grid">
            <div class="metric-item">
              <div class="metric-label">全网规划总量</div>
              <div class="metric-val">
                <span class="num">{{ formatNumber(kpiData.pipeDesignKm) }}</span>
                <span class="unit">km</span>
              </div>
            </div>
            <div class="metric-item highlight-cyan">
              <div class="metric-label">累计发货总量</div>
              <div class="metric-val">
                <span class="num count-num">{{ formatNumber(kpiData.pipeShippedKm) }}</span>
                <span class="unit">km</span>
                <transition name="bubble-fade">
                  <span v-if="bubbles.pipeShipped" class="delta-bubble">+{{ bubbles.pipeShipped }}m</span>
                </transition>
              </div>
            </div>
            <div class="metric-item highlight-amber">
              <div class="metric-label">在途运输中</div>
              <div class="metric-val">
                <span class="num count-num">{{ formatNumber(kpiData.pipeTransitKm) }}</span>
                <span class="unit">km</span>
                <transition name="bubble-fade">
                  <span v-if="bubbles.pipeTransit" class="delta-bubble amber">+{{ bubbles.pipeTransit }}m</span>
                </transition>
              </div>
            </div>
            <div class="metric-item highlight-green">
              <div class="metric-label">现场核销/就位</div>
              <div class="metric-val">
                <span class="num">{{ formatNumber(kpiData.pipeDeliveredKm) }}</span>
                <span class="unit">km</span>
              </div>
            </div>
          </div>

          <!-- 管材保供进度充能条 -->
          <div class="energy-progress-box">
            <div class="energy-progress-info">
              <span>全网保温管保供覆盖率</span>
              <strong class="cyan-text">{{ pipeCoveragePercent }}%</strong>
            </div>
            <div class="energy-bar-track">
              <div 
                class="energy-bar-fill cyan-glow" 
                :style="{ width: pipeCoveragePercent + '%' }"
              >
                <div class="energy-bar-light"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 核心指标2：关键管件全流程跟踪 (1138 项标准化真实基准) -->
        <div class="panel-box fitting-kpi-panel">
          <div class="panel-header">
            <div class="panel-title">
              <span class="title-icon">🔩</span>
              <span>关键管件配套与直运大盘</span>
            </div>
            <span class="panel-tag gold">1138项标准化基准</span>
          </div>

          <div class="kpi-metric-grid">
            <div class="metric-item">
              <div class="metric-label">管件计划总量</div>
              <div class="metric-val">
                <span class="num">{{ kpiData.fittingTotalPcs }}</span>
                <span class="unit">件/套</span>
              </div>
            </div>
            <div class="metric-item highlight-gold">
              <div class="metric-label">累计发货管件</div>
              <div class="metric-val">
                <span class="num count-num">{{ kpiData.fittingShippedPcs }}</span>
                <span class="unit">件</span>
                <transition name="bubble-fade">
                  <span v-if="bubbles.fittingShipped" class="delta-bubble gold">+{{ bubbles.fittingShipped }}件</span>
                </transition>
              </div>
            </div>
            <div class="metric-item highlight-orange">
              <div class="metric-label">在途直运中</div>
              <div class="metric-val">
                <span class="num count-num">{{ kpiData.fittingTransitPcs }}</span>
                <span class="unit">件</span>
                <transition name="bubble-fade">
                  <span v-if="bubbles.fittingTransit" class="delta-bubble orange">+{{ bubbles.fittingTransit }}件</span>
                </transition>
              </div>
            </div>
            <div class="metric-item highlight-green">
              <div class="metric-label">现场验收就位</div>
              <div class="metric-val">
                <span class="num">{{ kpiData.fittingArrivedPcs }}</span>
                <span class="unit">件</span>
              </div>
            </div>
          </div>

          <!-- 管件配套进度条 -->
          <div class="energy-progress-box">
            <div class="energy-progress-info">
              <span>关键管件配套就绪率</span>
              <strong class="gold-text">{{ fittingCoveragePercent }}%</strong>
            </div>
            <div class="energy-bar-track">
              <div 
                class="energy-bar-fill gold-glow" 
                :style="{ width: fittingCoveragePercent + '%' }"
              >
                <div class="energy-bar-light"></div>
              </div>
            </div>
          </div>

          <!-- 真实管件分类占比速览 -->
          <div class="fitting-types-pills">
            <div class="fitting-pill" v-for="item in fittingTypeSummary" :key="item.type">
              <span class="pill-name">{{ item.type }}</span>
              <span class="pill-count">{{ item.count }}件</span>
            </div>
          </div>
        </div>

        <!-- 供应链安全保障与效率雷达 -->
        <div class="panel-box safety-panel">
          <div class="panel-header">
            <div class="panel-title">
              <span class="title-icon">🛡️</span>
              <span>保供效能与履约保障</span>
            </div>
            <span class="panel-tag green">100% 履约受控</span>
          </div>
          <div class="safety-grid">
            <div class="safety-card">
              <div class="safety-icon">🏭</div>
              <div class="safety-info">
                <div class="safety-val">{{ supplyNodes.length }} 家</div>
                <div class="safety-desc">核心制造管厂</div>
              </div>
            </div>
            <div class="safety-card">
              <div class="safety-icon">🎯</div>
              <div class="safety-info">
                <div class="safety-val">{{ sectionProgressList.length }} 个</div>
                <div class="safety-desc">施工标段现场</div>
              </div>
            </div>
            <div class="safety-card">
              <div class="safety-icon">🌿</div>
              <div class="safety-info">
                <div class="safety-val">100%</div>
                <div class="safety-desc">出厂质检合规率</div>
              </div>
            </div>
            <div class="safety-card">
              <div class="safety-icon">⏱️</div>
              <div class="safety-info">
                <div class="safety-val">0 延误</div>
                <div class="safety-desc">专线直达保障</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 中间栏：重构升级版 · 高工规整双系统拓扑中枢 (默认通透极简，发货在途/悬停显现) -->
      <section class="screen-col center-col">
        <div class="panel-box map-topology-master-panel">
          <!-- 拓扑头部导航与状态过滤 -->
          <div class="topology-header-bar">
            <div class="panel-title">
              <span class="title-icon">🌐</span>
              <span>供需流向拓扑</span>
            </div>

            <!-- 图例说明 -->
            <div class="topology-legend">
              <span class="legend-item"><span class="dot-line cyan"></span>保温管在途</span>
              <span class="legend-item"><span class="dot-line gold"></span>管件在途</span>
              <span class="legend-item"><span class="dot-point active"></span>实况节点</span>
            </div>
          </div>

          <!-- 拓扑主舞台：左管厂 (230px) + 中流向通道 (50px) + 右双系统立柱 (1fr) -->
          <div class="topology-container" ref="topologyContainerRef">
            <!-- 动态贝塞尔飞线与激光粒子 SVG 视层 (默认不显示任何线条，仅在发货在途或悬停时显现) -->
            <svg class="topology-svg" ref="svgRef">
              <defs>
                <linearGradient id="grad-pipe-line" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stop-color="#00f2fe" />
                  <stop offset="100%" stop-color="#38bdf8" />
                </linearGradient>
                <linearGradient id="grad-fitting-line" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stop-color="#fbbf24" />
                  <stop offset="100%" stop-color="#f97316" />
                </linearGradient>
              </defs>

              <!-- 专供运输管道与流光组合 (默认无发货在途时完全隐藏，保持空间通透极简) -->
              <g class="flylines-layer">
                <g 
                  v-for="line in flylines" 
                  :key="line.id"
                  class="flyline-group"
                  v-show="isLineVisible(line)"
                >
                  <!-- 管道基础轨迹 -->
                  <path 
                    :d="line.d" 
                    class="flyline-base"
                    :class="line.type"
                  />
                  <!-- 在途动态光带 -->
                  <path 
                    :d="line.d" 
                    class="flyline-stream"
                    :class="line.type"
                  />
                </g>
              </g>

              <!-- 发货时触发的单点高亮激光能量包粒子 -->
              <g class="particles-layer">
                <circle 
                  v-for="p in activeParticles" 
                  :key="p.id"
                  r="5" 
                  :fill="p.type === 'pipe' ? '#00f2fe' : '#fbbf24'"
                  class="laser-particle"
                >
                  <animateMotion 
                    :path="p.d" 
                    :dur="p.duration + 's'" 
                    begin="0s"
                    repeatCount="1"
                    fill="freeze"
                  />
                </circle>
              </g>
            </svg>

            <!-- 拓扑节点排版架构：左管厂 (230px) + 中通道 (50px) + 右双系统立柱 (1fr) -->
            <div class="topology-layout-grid">
              <!-- 1. 左侧：供给制造基地 (Supply Hub) -->
              <div class="supply-hub-col">
                <div class="hub-header">
                  <span class="hub-badge supply">🏭 保供制造基地 (3)</span>
                </div>
                <div class="supply-cards-stack">
                  <div 
                    v-for="sup in supplyNodes" 
                    :key="sup.id" 
                    class="supply-node-card"
                    :class="{ 
                      active: activeNodeIds.has(sup.id),
                      hovered: hoveredSupplierId === sup.id,
                      dimmed: (hoveredSupplierId && hoveredSupplierId !== sup.id) || (hoveredSectionId && !isSupplierOfSection(sup.id, hoveredSectionId))
                    }"
                    :id="'node-' + sup.id"
                    @mouseenter="hoveredSupplierId = sup.id"
                    @mouseleave="hoveredSupplierId = null"
                  >
                    <strong class="sup-title" :title="sup.name">{{ sup.name }}</strong>

                    <!-- 物理对齐连接端口 (右锚点) -->
                    <div class="node-port port-out" :id="'port-out-' + sup.id" title="发运输出端口">
                      <span class="port-dot"></span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 2. 中间：流向传输主通道 (Transit Corridor) -->
              <div class="transit-channel-col">
                <div class="channel-track">
                  <div class="channel-glow-line"></div>
                  <div class="channel-text">专线直达</div>
                </div>
              </div>

              <!-- 3. 右侧：10 大施工标段（按 高温水干线 与 低温水分支 两大规整立柱排布） -->
              <div class="demand-hub-col">
                <div class="demand-systems-split" @scroll="recalculateFlylines">
                  <!-- 第 1 标段立柱：5 标段 (H1 ~ H4 + L1) -->
                  <div class="system-sub-col high-system">
                    <div class="system-cards-list">
                      <div 
                        v-for="sec in col1Sections" 
                        :key="sec.id" 
                        class="demand-node-card"
                        :class="[
                          sec.system_type === 'high' ? 'high-system' : 'low-system',
                          { 
                            active: activeNodeIds.has('sec_' + sec.id),
                            highlighted: lastImpactedSectionId === sec.id || (hoveredSupplierId && isSuppliedBy(sec.id, hoveredSupplierId)),
                            dimmed: (hoveredSupplierId && !isSuppliedBy(sec.id, hoveredSupplierId)) || (hoveredSectionId && hoveredSectionId !== sec.id),
                            completed: sec.pipePercent >= 100 && sec.fittingPercent >= 100
                          }
                        ]"
                        :id="'node-sec_' + sec.id"
                        @mouseenter="hoveredSectionId = sec.id"
                        @mouseleave="hoveredSectionId = null"
                      >
                        <!-- 物理对齐连接端口 (左锚点) -->
                        <div class="node-port port-in" :id="'port-in-sec_' + sec.id" title="标段签收入口">
                          <span class="port-dot"></span>
                        </div>

                        <div class="sec-card-header">
                          <div class="sec-badge-name">
                            <span class="sec-sys-badge" :class="sec.system_type">{{ sec.system_type === 'high' ? '🔥 高温' : '💧 低温' }}</span>
                            <strong class="sec-title" :title="sec.name">{{ sec.name }}</strong>
                          </div>
                          <span class="sec-status-chip" :class="{ running: sec.construction_status === '施工中' }">
                            <span class="chip-dot"></span>
                            <span>{{ sec.construction_status }}</span>
                          </span>
                        </div>

                        <!-- 保温管与管件双轨微进度 -->
                        <div class="sec-metrics-body">
                          <div class="sec-metric-line">
                            <div class="line-info">
                              <span class="line-label pipe-tag">📐 保温管</span>
                              <span class="line-val cyan-text">{{ sec.shippedKm }} / {{ sec.designKm }} km</span>
                              <span class="line-pct cyan-text">{{ sec.pipePercent }}%</span>
                            </div>
                            <div class="micro-bar-bg">
                              <div class="micro-bar-fill cyan" :style="{ width: Math.min(sec.pipePercent, 100) + '%' }"></div>
                            </div>
                          </div>

                          <div class="sec-metric-line">
                            <div class="line-info">
                              <span class="line-label fitting-tag">🔩 管件</span>
                              <span class="line-val gold-text">{{ sec.shippedFittings }} / {{ sec.totalFittings }} 件</span>
                              <span class="line-pct gold-text">{{ sec.fittingPercent }}%</span>
                            </div>
                            <div class="micro-bar-bg">
                              <div class="micro-bar-fill gold" :style="{ width: Math.min(sec.fittingPercent, 100) + '%' }"></div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 第 2 标段立柱：5 标段 (L2 ~ L6) -->
                  <div class="system-sub-col low-system">
                    <div class="system-cards-list">
                      <div 
                        v-for="sec in col2Sections" 
                        :key="sec.id" 
                        class="demand-node-card"
                        :class="[
                          sec.system_type === 'high' ? 'high-system' : 'low-system',
                          { 
                            active: activeNodeIds.has('sec_' + sec.id),
                            highlighted: lastImpactedSectionId === sec.id || (hoveredSupplierId && isSuppliedBy(sec.id, hoveredSupplierId)),
                            dimmed: (hoveredSupplierId && !isSuppliedBy(sec.id, hoveredSupplierId)) || (hoveredSectionId && hoveredSectionId !== sec.id),
                            completed: sec.pipePercent >= 100 && sec.fittingPercent >= 100
                          }
                        ]"
                        :id="'node-sec_' + sec.id"
                        @mouseenter="hoveredSectionId = sec.id"
                        @mouseleave="hoveredSectionId = null"
                      >
                        <!-- 物理对齐连接端口 (左锚点) -->
                        <div class="node-port port-in" :id="'port-in-sec_' + sec.id" title="标段签收入口">
                          <span class="port-dot"></span>
                        </div>

                        <div class="sec-card-header">
                          <div class="sec-badge-name">
                            <span class="sec-sys-badge" :class="sec.system_type">{{ sec.system_type === 'high' ? '🔥 高温' : '💧 低温' }}</span>
                            <strong class="sec-title" :title="sec.name">{{ sec.name }}</strong>
                          </div>
                          <span class="sec-status-chip" :class="{ running: sec.construction_status === '施工中' }">
                            <span class="chip-dot"></span>
                            <span>{{ sec.construction_status }}</span>
                          </span>
                        </div>

                        <!-- 保温管与管件双轨微进度 -->
                        <div class="sec-metrics-body">
                          <div class="sec-metric-line">
                            <div class="line-info">
                              <span class="line-label pipe-tag">📐 保温管</span>
                              <span class="line-val cyan-text">{{ sec.shippedKm }} / {{ sec.designKm }} km</span>
                              <span class="line-pct cyan-text">{{ sec.pipePercent }}%</span>
                            </div>
                            <div class="micro-bar-bg">
                              <div class="micro-bar-fill cyan" :style="{ width: Math.min(sec.pipePercent, 100) + '%' }"></div>
                            </div>
                          </div>

                          <div class="sec-metric-line">
                            <div class="line-info">
                              <span class="line-label fitting-tag">🔩 管件</span>
                              <span class="line-val gold-text">{{ sec.shippedFittings }} / {{ sec.totalFittings }} 件</span>
                              <span class="line-pct gold-text">{{ sec.fittingPercent }}%</span>
                            </div>
                            <div class="micro-bar-bg">
                              <div class="micro-bar-fill gold" :style="{ width: Math.min(sec.fittingPercent, 100) + '%' }"></div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 右侧栏：实时战报动态流水与重大保供里程碑 (基于真实工程全链路数据) -->
      <section class="screen-col right-col">
        <!-- 实时工程战报流 -->
        <div class="panel-box live-feed-panel">
          <div class="panel-header">
            <div class="panel-title">
              <span class="title-icon">📢</span>
              <span>全网工程实时动态播报</span>
            </div>
            <div 
              class="live-status-pill" 
              :class="{ 'live-direct': isLiveStreamMode }"
              @click="toggleLiveStreamMode"
              style="cursor: pointer;"
              :title="isLiveStreamMode ? '已接入真实生产数据库直播（点击断开）' : '点击接入真实生产数据库实时直播流'"
            >
              <span class="live-dot" :class="{ 'live-pulse': isLiveStreamMode }"></span>
              <span>{{ isLiveStreamMode ? '实况直播 (已接通)' : '接入实况' }}</span>
            </div>
          </div>

          <!-- 统一业务分类筛选按钮与展开式点选浮层 (纯净分类选择，无条数后缀) -->
          <div class="feed-filter-unified-bar" ref="feedFilterMenuRef">
            <div class="filter-dropdown-wrapper">
              <button 
                class="unified-filter-btn" 
                :class="{ 'menu-open': isFeedFilterMenuOpen, 'is-filtered': feedFilter !== 'all' }"
                @click.stop="isFeedFilterMenuOpen = !isFeedFilterMenuOpen"
                title="点击展开/收起业务分类筛选菜单"
              >
                <div class="filter-btn-left">
                  <span class="filter-btn-icon">{{ currentFilterOption.icon }}</span>
                  <span class="filter-btn-label">业务分类:</span>
                  <strong class="filter-btn-current">{{ currentFilterOption.label }}</strong>
                </div>
                <div class="filter-btn-right">
                  <span class="filter-caret">{{ isFeedFilterMenuOpen ? '▲' : '▼' }}</span>
                </div>
              </button>

              <!-- 展开式点选面板 -->
              <transition name="filter-dropdown-anim">
                <div v-if="isFeedFilterMenuOpen" class="feed-filter-popover" @click.stop>
                  <div class="popover-tip-header">
                    <span class="popover-title-text">⚡ 选择业务动态分类</span>
                    <button 
                      v-if="feedFilter !== 'all'" 
                      class="reset-filter-link" 
                      @click="selectFeedFilter('all')"
                    >重置全部</button>
                  </div>
                  <div class="popover-options-grid">
                    <div 
                      v-for="opt in feedFilterOptions" 
                      :key="opt.key"
                      class="filter-option-row"
                      :class="{ active: feedFilter === opt.key }"
                      @click="selectFeedFilter(opt.key)"
                    >
                      <div class="option-tag-part">
                        <span class="option-dot" :style="{ background: opt.color, boxShadow: '0 0 6px ' + opt.color }"></span>
                        <span class="option-icon">{{ opt.icon }}</span>
                        <span class="option-title">{{ opt.label }}</span>
                      </div>
                      <div class="option-meta-part">
                        <span v-if="feedFilter === opt.key" class="option-check">✓</span>
                      </div>
                    </div>
                  </div>
                </div>
              </transition>
            </div>
          </div>

          <!-- 战报消息动态上浮列表 -->
          <div class="feed-list-wrapper">
            <transition-group name="feed-item" tag="div" class="feed-list">
              <div 
                v-for="feed in filteredFeedList" 
                :key="feed.id" 
                class="feed-card"
                :class="[feed.category_key || 'dispatch', { 'just-arrived': feed.isNew }]"
                @click="handleFeedClick(feed)"
                title="点击在中心拓扑图上聚焦并触发该业务动态直达路线"
                style="cursor: pointer;"
              >
                <!-- Row 1: 分类标签 + 经办人 + 发生时间 -->
                <div class="feed-card-header">
                  <div class="header-left-meta">
                    <span class="feed-category-tag" :class="feed.category_key || 'dispatch'">
                      {{ feed.category }}
                    </span>
                    <span v-if="feed.operator" class="feed-operator-tag" :title="'经办人: ' + feed.operator">
                      👤 {{ feed.operator }}
                    </span>
                  </div>
                  <span class="feed-time">{{ feed.time }}</span>
                </div>

                <!-- Row 2: 动态标题 / 厂家发运流向 -->
                <div class="feed-card-headline">
                  <template v-if="feed.category_key === 'dispatch'">
                    <div class="route-line-box">
                      <span class="route-source" :title="feed.supplier">{{ feed.supplier }}</span>
                      <span class="route-arrow">──►</span>
                      <span class="route-target" :title="feed.target">{{ feed.target }}</span>
                    </div>
                  </template>
                  <template v-else>
                    <div class="action-headline-box" :title="feed.headline">
                      <span class="action-headline-text">{{ feed.headline }}</span>
                    </div>
                  </template>
                </div>

                <!-- Row 3: 规格与数量明细栏 (左侧规格截断，右侧高亮数量，永不串行) -->
                <div class="feed-spec-box">
                  <div class="spec-text-col" :title="feed.specification">
                    <span class="spec-name">{{ feed.specification }}</span>
                  </div>
                  <div class="spec-qty-col">
                    <span class="spec-amount-badge" :class="feed.type">{{ feed.amount }}</span>
                  </div>
                </div>

                <!-- Row 4: 单号/车牌 + 正向动态评价 -->
                <div class="feed-card-footer">
                  <span class="feed-code-tag" :title="feed.shipmentCode">
                    <span class="code-icon">🔖</span>
                    <span class="code-val">{{ feed.shipmentCode }}</span>
                  </span>
                  <span class="feed-pos-tag" :title="feed.positiveTag">✨ {{ feed.positiveTag }}</span>
                </div>
              </div>
            </transition-group>
          </div>
        </div>

        <!-- 关键保供里程碑与正向成果榜 -->
        <div class="panel-box milestone-panel">
          <div class="panel-header">
            <div class="panel-title">
              <span class="title-icon">🏆</span>
              <span>保供里程碑与正向成果</span>
            </div>
            <span class="panel-tag gold">今日战报</span>
          </div>

          <div class="milestone-list">
            <div class="milestone-item" v-for="(m, idx) in milestones" :key="idx">
              <div class="milestone-badge">0{{ idx + 1 }}</div>
              <div class="milestone-content">
                <div class="m-title">{{ m.title }}</div>
                <div class="m-desc">{{ m.desc }}</div>
              </div>
              <div class="m-time">{{ m.time }}</div>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  getTubeWorkspaceConfigSummary,
  getTubeBigScreenData
} from '../../daily_report_25_26/services/api'

const router = useRouter()
const route = useRoute()
const projectKey = computed(() => String(route.params.projectKey || 'insulation_pipe_supply_2026'))

// --- 主题切换状态 ---
const currentTheme = ref(localStorage.getItem('phoenix_tube_bigscreen_theme') || 'dark')
const isDark = computed(() => currentTheme.value === 'dark')

function toggleTheme() {
  currentTheme.value = currentTheme.value === 'dark' ? 'light' : 'dark'
  localStorage.setItem('phoenix_tube_bigscreen_theme', currentTheme.value)
  recalculateFlylines()
}

// --- 基础状态 ---
const containerRef = ref(null)
const topologyContainerRef = ref(null)
const svgRef = ref(null)
const isFullscreen = ref(false)
const configSummary = ref(null)
const realShowDate = ref('')
const currentTimeStr = ref('')
const isControlMenuOpen = ref(false)
const controlMenuRef = ref(null)
const isFeedFilterMenuOpen = ref(false)
const feedFilterMenuRef = ref(null)

function toggleControlMenu() {
  isControlMenuOpen.value = !isControlMenuOpen.value
}

function handleGlobalClick(e) {
  if (isControlMenuOpen.value && controlMenuRef.value && !controlMenuRef.value.contains(e.target)) {
    isControlMenuOpen.value = false
  }
  if (isFeedFilterMenuOpen.value && feedFilterMenuRef.value && !feedFilterMenuRef.value.contains(e.target)) {
    isFeedFilterMenuOpen.value = false
  }
}
let timerClock = null
let autoDemoTimer = null
let autoSyncTimer = null
let liveStreamTimer = null
let resizeObserver = null
let rAFId = null
const autoDemoRunning = ref(false)
const feedFilter = ref('all')

const feedFilterOptions = [
  { key: 'all', label: '全部', icon: '🌐', color: '#00f2fe' },
  { key: 'dispatch', label: '厂家发货', icon: '🚚', color: '#38bdf8' },
  { key: 'arrival', label: '确认到货', icon: '📍', color: '#60a5fa' },
  { key: 'receive', label: '施工单位收货', icon: '🏗️', color: '#f59e0b' },
  { key: 'warehouse', label: '库管核销', icon: '🛡️', color: '#10b981' },
  { key: 'usage', label: '施工量确认', icon: '📐', color: '#a855f7' },
  { key: 'plan', label: '需求量申报', icon: '📋', color: '#f43f5e' },
]

function getFeedCountByCategory(categoryKey) {
  if (categoryKey === 'all') return liveFeedList.value.length
  return liveFeedList.value.filter(item => item.category_key === categoryKey || item.type === categoryKey).length
}

const currentFilterOption = computed(() => {
  return feedFilterOptions.find(o => o.key === feedFilter.value) || feedFilterOptions[0]
})

function selectFeedFilter(key) {
  feedFilter.value = key
  isFeedFilterMenuOpen.value = false
}
const lastImpactedSectionId = ref(null)
const activeSectionTab = ref('all') // 'all' | 'high' | 'low'

// --- 生产实况 · 真实数据流直连模式 (Live Stream Mode) ---
const isLiveStreamMode = ref(false)
const knownFeedIds = ref(new Set())
let initialDataLoaded = false

// --- 交互悬停聚焦状态 (Hover Focus) ---
const hoveredSupplierId = ref(null)
const hoveredSectionId = ref(null)
const activeShipmentLineIds = ref(new Set()) // 默认全部静止基准线，仅在真实发货或鼠标悬停时按需激活
const isAnyHovered = computed(() => !!hoveredSupplierId.value || !!hoveredSectionId.value)

// --- 权威默认数据源 (保证第一帧即刻渲染完整节点与飞线) ---
const defaultSupplyNodes = [
  {
    id: 'sup_kaiyuan',
    raw_id: 'kaiyuan',
    code: 'SA',
    name: '大连开元热力管道',
    assigned_sections: ['高温水 1、2 标'],
    assigned_section_ids: ['high_lot_1', 'high_lot_2']
  },
  {
    id: 'sup_xinruide',
    raw_id: 'xinruide',
    code: 'SB',
    name: '河北鑫瑞得管道',
    assigned_sections: ['低温水 1、2、3 标'],
    assigned_section_ids: ['low_lot_1', 'low_lot_2', 'low_lot_3']
  },
  {
    id: 'sup_吴近',
    raw_id: '吴近',
    code: 'SC',
    name: '能源集团保温管厂',
    assigned_sections: ['高水 3、4 标 / 低水 4、5、6 标'],
    assigned_section_ids: ['high_lot_3', 'high_lot_4', 'low_lot_4', 'low_lot_5', 'low_lot_6']
  }
]

const defaultSectionList = [
  { id: 'high_lot_1', name: '高温水_标段1', code: 'H1', system_type: 'high', construction_status: '施工中', designKm: 18.5, shippedKm: 12.0, pipePercent: 64.9, totalFittings: 400, shippedFittings: 280, fittingPercent: 70.0 },
  { id: 'high_lot_2', name: '高温水_标段2', code: 'H2', system_type: 'high', construction_status: '未开工', designKm: 15.2, shippedKm: 0.0, pipePercent: 0.0, totalFittings: 350, shippedFittings: 0, fittingPercent: 0.0 },
  { id: 'high_lot_3', name: '高温水_标段3', code: 'H3', system_type: 'high', construction_status: '未开工', designKm: 14.8, shippedKm: 0.0, pipePercent: 0.0, totalFittings: 320, shippedFittings: 0, fittingPercent: 0.0 },
  { id: 'high_lot_4', name: '高温水_标段4', code: 'H4', system_type: 'high', construction_status: '未开工', designKm: 16.0, shippedKm: 0.0, pipePercent: 0.0, totalFittings: 360, shippedFittings: 0, fittingPercent: 0.0 },
  { id: 'low_lot_1', name: '低温水_标段1', code: 'L1', system_type: 'low', construction_status: '未开工', designKm: 8.6, shippedKm: 0.0, pipePercent: 0.0, totalFittings: 180, shippedFittings: 0, fittingPercent: 0.0 },
  { id: 'low_lot_2', name: '低温水_标段2', code: 'L2', system_type: 'low', construction_status: '未开工', designKm: 9.1, shippedKm: 0.0, pipePercent: 0.0, totalFittings: 195, shippedFittings: 0, fittingPercent: 0.0 },
  { id: 'low_lot_3', name: '低温水_标段3', code: 'L3', system_type: 'low', construction_status: '未开工', designKm: 11.2, shippedKm: 0.0, pipePercent: 0.0, totalFittings: 240, shippedFittings: 0, fittingPercent: 0.0 },
  { id: 'low_lot_4', name: '低温水_标段4', code: 'L4', system_type: 'low', construction_status: '未开工', designKm: 10.5, shippedKm: 0.0, pipePercent: 0.0, totalFittings: 220, shippedFittings: 0, fittingPercent: 0.0 },
  { id: 'low_lot_5', name: '低温水_标段5', code: 'L5', system_type: 'low', construction_status: '未开工', designKm: 7.8, shippedKm: 0.0, pipePercent: 0.0, totalFittings: 160, shippedFittings: 0, fittingPercent: 0.0 },
  { id: 'low_lot_6', name: '低温水_标段6', code: 'L6', system_type: 'low', construction_status: '未开工', designKm: 8.2, shippedKm: 0.0, pipePercent: 0.0, totalFittings: 175, shippedFittings: 0, fittingPercent: 0.0 }
]

// 真实实体库引用
let rawSupplyEntities = []
let rawDemandEntities = []
let rawPipeModels = []

// --- 核心指标状态 (由后端数据库精准聚合统计) ---
const kpiData = reactive({
  pipeDesignKm: 0.0,
  pipeShippedKm: 0.0,
  pipeTransitKm: 0.0,
  pipeDeliveredKm: 0.0,
  fittingTotalPcs: 0,
  fittingShippedPcs: 0,
  fittingTransitPcs: 0,
  fittingArrivedPcs: 0
})

// 飘字气泡 (Delta Bubbles)
const bubbles = reactive({
  pipeShipped: null,
  pipeTransit: null,
  fittingShipped: null,
  fittingTransit: null
})

// 活跃高亮节点集合
const activeNodeIds = ref(new Set())

// 激光飞线与粒子状态
const flylines = ref([])
const activeParticles = ref([])

// 实时战报流列表（100% 绑定底层真实业务数据库单据记录）
const liveFeedList = ref([])

// 过滤后的战报流
const filteredFeedList = computed(() => {
  if (feedFilter.value === 'all') return liveFeedList.value
  return liveFeedList.value.filter(item => item.category_key === feedFilter.value || item.type === feedFilter.value)
})

// 管材保供百分比
const pipeCoveragePercent = computed(() => {
  if (!kpiData.pipeDesignKm || kpiData.pipeDesignKm <= 0) return 0
  return Math.min(Math.round((kpiData.pipeShippedKm / kpiData.pipeDesignKm) * 1000) / 10, 100)
})

// 管件保供百分比
const fittingCoveragePercent = computed(() => {
  if (!kpiData.fittingTotalPcs || kpiData.fittingTotalPcs <= 0) return 0
  return Math.min(Math.round((kpiData.fittingShippedPcs / kpiData.fittingTotalPcs) * 1000) / 10, 100)
})

// 热门管件类型汇总
const fittingTypeSummary = ref([])

// 拓扑节点定义 (3 大真实管厂)
const supplyNodes = ref([...defaultSupplyNodes])

// 真实 10 大标段健康矩阵数据
const sectionProgressList = ref([...defaultSectionList])

// 高温水与低温水系统立柱分离（均衡分配为两列各 5 个标段，避免底部留白）
const highWaterSections = computed(() => sectionProgressList.value.filter(s => s.system_type === 'high'))
const lowWaterSections = computed(() => sectionProgressList.value.filter(s => s.system_type === 'low'))
const col1Sections = computed(() => sectionProgressList.value.slice(0, 5))
const col2Sections = computed(() => sectionProgressList.value.slice(5, 10))

function setSectionTab(tab) {
  activeSectionTab.value = tab
  recalculateFlylines()
}

// 供需隶属判断辅助函数
function isSuppliedBy(secId, supId) {
  const sup = supplyNodes.value.find(s => s.id === supId)
  if (!sup) return false
  const assigned = sup.assigned_section_ids || []
  return assigned.includes(secId)
}

function getSupplierStats(sup) {
  const assigned = sup.assigned_section_ids || []
  const matched = sectionProgressList.value.filter(s => assigned.includes(s.id))
  if (matched.length === 0) {
    return {
      designKm: '0.00',
      shippedKm: '0.00',
      pipePercent: 0,
      totalFittings: 0,
      shippedFittings: 0,
      fittingPercent: 0
    }
  }
  const designKm = matched.reduce((acc, s) => acc + (Number(s.designKm) || 0), 0)
  const shippedKm = matched.reduce((acc, s) => acc + (Number(s.shippedKm) || 0), 0)
  const totalFittings = matched.reduce((acc, s) => acc + (Number(s.totalFittings) || 0), 0)
  const shippedFittings = matched.reduce((acc, s) => acc + (Number(s.shippedFittings) || 0), 0)
  const pipePercent = designKm > 0 ? Number(((shippedKm / designKm) * 100).toFixed(1)) : 0
  const fittingPercent = totalFittings > 0 ? Number(((shippedFittings / totalFittings) * 100).toFixed(1)) : 0

  return {
    designKm: designKm.toFixed(2),
    shippedKm: shippedKm.toFixed(2),
    pipePercent: Math.min(pipePercent, 100),
    totalFittings,
    shippedFittings,
    fittingPercent: Math.min(fittingPercent, 100)
  }
}

function isSupplierOfSection(supId, secId) {
  return isSuppliedBy(secId, supId)
}

function isLineVisible(line) {
  // 1. 鼠标悬停管厂或标段时临时显现专供直达线路
  if (hoveredSupplierId.value && line.fromId === hoveredSupplierId.value) return true
  if (hoveredSectionId.value && line.toId === 'sec_' + hoveredSectionId.value) return true
  // 2. 有发货在途运输时显现该条运输路线
  if (activeShipmentLineIds.value.has(line.id)) return true
  return false
}

// 重大保供里程碑
const milestones = ref([
  {
    title: '全网管材规划总量达 120.00 km',
    desc: '统筹覆盖 10 个高温水及低温水标段，三大制造基地全面开工供货',
    time: '2026-08-10'
  },
  {
    title: '1138 项标准化管件采购计划全面受控',
    desc: '涵盖弯头、变径管、三通、补偿器及球阀，累计计划配套 1138 件/套',
    time: '2026-08-10'
  },
  {
    title: '开元、鑫瑞得、能源集团管厂三大基地全线直运',
    desc: '专线直发 10 大施工标段现场，保供直运闭环签收',
    time: '实时'
  }
])

// --- 点击战报卡片即时在拓扑图上发射激光飞线并高亮相关节点 ---
function handleFeedClick(feed) {
  if (!feed) return
  const sup = supplyNodes.value.find(s => s.name === feed.supplier || (feed.supplier && feed.supplier.includes(s.name)) || s.raw_id === feed.supplier)
  const sec = sectionProgressList.value.find(s => s.name === feed.target || (feed.target && feed.target.includes(s.name)) || s.id === feed.target)
  const fromId = sup ? sup.id : (supplyNodes.value[0]?.id || 'sup_kaiyuan')
  const toId = sec ? ('sec_' + sec.id) : ('sec_' + (sectionProgressList.value[0]?.id || 'high_lot_1'))

  // 1. 发射专属激光飞线
  shootLaserParticle(fromId, toId, feed.type || 'pipe')

  // 2. 临时高亮对应管厂与标段节点
  if (sup) hoveredSupplierId.value = sup.id
  if (sec) hoveredSectionId.value = sec.id
  setTimeout(() => {
    hoveredSupplierId.value = null
    hoveredSectionId.value = null
  }, 2500)
}

// --- 切换真实数据实时流直连模式 ---
function toggleLiveStreamMode() {
  isLiveStreamMode.value = !isLiveStreamMode.value
  if (isLiveStreamMode.value) {
    // 1. 关闭沙盒自动演示
    if (autoDemoRunning.value) toggleAutoDemo()
    // 2. 立即拉取并完全对齐数据库最新全量真实数据
    loadRealData(true)
    // 3. 启动高频心跳轮询（每 3 秒检测数据库增量发货/签收动态）
    if (liveStreamTimer) clearInterval(liveStreamTimer)
    liveStreamTimer = setInterval(pollLiveRealData, 3000)

    // 4. 即刻触发实况接入动画（高亮首张卡片并向中心拓扑图发射一道连接激活飞线）
    if (liveFeedList.value && liveFeedList.value.length > 0) {
      const topFeed = liveFeedList.value[0]
      topFeed.isNew = true
      handleFeedClick(topFeed)
      setTimeout(() => {
        topFeed.isNew = false
      }, 3500)
    }
  } else {
    // 关闭实时流监听，恢复常规 20 秒静默轮询
    if (liveStreamTimer) clearInterval(liveStreamTimer)
    liveStreamTimer = null
  }
}

// --- 高频轮询并感知数据库最新产生的真实发货与累计状态 (只读安全感知) ---
async function pollLiveRealData() {
  try {
    const res = await getTubeBigScreenData(projectKey.value)
    if (!res || !res.ok) return

    // 1. 检查是否有新增真实发货单据
    if (Array.isArray(res.live_feed_list)) {
      const newArrivals = []
      res.live_feed_list.forEach(feed => {
        if (!knownFeedIds.value.has(feed.id)) {
          knownFeedIds.value.add(feed.id)
          if (initialDataLoaded) {
            newArrivals.push(feed)
          }
        }
      })

      // 如果检测到现场或管厂提交了新的真实单据
      if (newArrivals.length > 0) {
        newArrivals.forEach(feed => {
          feed.isNew = true
          // 查找匹配管厂与标段
          const sup = supplyNodes.value.find(s => s.name === feed.supplier || feed.supplier.includes(s.name) || s.raw_id === feed.supplier)
          const sec = sectionProgressList.value.find(s => s.name === feed.target || feed.target.includes(s.name) || s.id === feed.target)
          const fromId = sup ? sup.id : (supplyNodes.value[0]?.id || 'sup_kaiyuan')
          const toId = sec ? ('sec_' + sec.id) : ('sec_' + (sectionProgressList.value[0]?.id || 'high_lot_1'))

          shootLaserParticle(fromId, toId, feed.type)

          if (feed.type === 'pipe') {
            const meters = parseInt(feed.amount) || 120
            bubbles.pipeShipped = meters
            bubbles.pipeTransit = meters
          } else {
            const pcs = parseInt(feed.amount) || 2
            bubbles.fittingShipped = pcs
            bubbles.fittingTransit = pcs
          }
          setTimeout(() => {
            bubbles.pipeShipped = null
            bubbles.pipeTransit = null
            bubbles.fittingShipped = null
            bubbles.fittingTransit = null
          }, 2400)
        })

        // 更新战报列表
        liveFeedList.value = res.live_feed_list
        setTimeout(() => {
          liveFeedList.value.forEach(f => f.isNew = false)
        }, 3500)
      } else {
        liveFeedList.value = res.live_feed_list
      }
    }

    // 2. 实时同步全网真实大盘与累计指标
    if (res.kpi) {
      kpiData.pipeDesignKm = Number(res.kpi.pipeDesignKm || 0)
      kpiData.pipeShippedKm = Number(res.kpi.pipeShippedKm || 0)
      kpiData.pipeTransitKm = Number(res.kpi.pipeTransitKm || 0)
      kpiData.pipeDeliveredKm = Number(res.kpi.pipeDeliveredKm || 0)
      kpiData.fittingTotalPcs = Number(res.kpi.fittingTotalPcs || 1138)
      kpiData.fittingShippedPcs = Number(res.kpi.fittingShippedPcs || 0)
      kpiData.fittingTransitPcs = Number(res.kpi.fittingTransitPcs || 0)
      kpiData.fittingArrivedPcs = Number(res.kpi.fittingArrivedPcs || 0)
    }

    // 3. 实时同步 10 大标段真实进度
    if (Array.isArray(res.section_progress_list) && res.section_progress_list.length > 0) {
      sectionProgressList.value = res.section_progress_list
    }

    // 4. 实时同步管件类型汇总
    if (Array.isArray(res.fitting_type_summary)) {
      fittingTypeSummary.value = res.fitting_type_summary
    }

  } catch (err) {
    console.warn('实时心跳拉取异常:', err)
  }
}

// --- 高性能规整流向几何计算 (定向直达专线，绝不产生杂乱交叉) ---
function recalculateFlylines() {
  if (rAFId) cancelAnimationFrame(rAFId)
  rAFId = requestAnimationFrame(() => {
    rAFId = null
    if (!topologyContainerRef.value) return
    const container = topologyContainerRef.value
    const containerRect = container.getBoundingClientRect()
    if (containerRect.width <= 0 || containerRect.height <= 0) return

    // 1. 批量读取港口坐标，单次回流
    const supRects = new Map()
    supplyNodes.value.forEach(sup => {
      const el = document.getElementById('port-out-' + sup.id)
      if (el) {
        const r = el.getBoundingClientRect()
        supRects.set(sup.id, {
          x: r.left + r.width / 2 - containerRect.left,
          y: r.top + r.height / 2 - containerRect.top
        })
      }
    })

    const secRects = new Map()
    sectionProgressList.value.forEach(sec => {
      const el = document.getElementById('port-in-sec_' + sec.id)
      if (el) {
        const r = el.getBoundingClientRect()
        secRects.set(sec.id, {
          x: r.left + r.width / 2 - containerRect.left,
          y: r.top + r.height / 2 - containerRect.top
        })
      }
    })

    // 2. 批量构建规整专属定向飞线 (精准直连负责标段，不再盲目全连)
    const newFlylines = []
    supplyNodes.value.forEach((sup, sIdx) => {
      const p1 = supRects.get(sup.id)
      if (!p1) return
      const assignedIds = sup.assigned_section_ids || []

      sectionProgressList.value.forEach((sec) => {
        // 仅在属于当前激活 Tab 且符合真实责任划分时绘制管道
        const inActiveTab = activeSectionTab.value === 'all' || activeSectionTab.value === sec.system_type
        const isMatched = assignedIds.includes(sec.id)

        if (inActiveTab && isMatched) {
          const p2 = secRects.get(sec.id)
          if (p2) {
            const dx = Math.max(Math.abs(p2.x - p1.x), 40)
            const cx1 = p1.x + dx * 0.45
            const cy1 = p1.y
            const cx2 = p2.x - dx * 0.45
            const cy2 = p2.y
            const d = `M ${p1.x} ${p1.y} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${p2.x} ${p2.y}`
            newFlylines.push({
              id: `flyline-${sup.id}-${sec.id}`,
              fromId: sup.id,
              toId: 'sec_' + sec.id,
              type: sIdx === 1 ? 'fitting' : 'pipe',
              d
            })
          }
        }
      })
    })

    flylines.value = newFlylines
  })
}

// 触发一道激光粒子飞行动画并在途显现线路
function shootLaserParticle(fromId, toId, type = 'pipe') {
  let targetLine = flylines.value.find(l => l.fromId === fromId && l.toId === toId)
  if (!targetLine) {
    targetLine = flylines.value.find(l => l.toId === toId) || flylines.value[0]
  }
  if (!targetLine) return

  const particleId = 'p_' + Date.now() + '_' + Math.floor(Math.random() * 1000)
  const duration = 1.3

  // 1. 点亮显现在途运输线路
  activeShipmentLineIds.value.add(targetLine.id)
  activeNodeIds.value.add(fromId)
  activeNodeIds.value.add(toId)

  activeParticles.value.push({
    id: particleId,
    d: targetLine.d,
    type,
    duration
  })

  // 2. 激光粒子到达后移除粒子与高亮
  setTimeout(() => {
    activeParticles.value = activeParticles.value.filter(p => p.id !== particleId)
    activeNodeIds.value.delete(fromId)
    activeNodeIds.value.delete(toId)
  }, duration * 1000 + 100)

  // 3. 在途运输持续 4.0 秒后线路平滑隐去，完全恢复通透极简状态
  setTimeout(() => {
    activeShipmentLineIds.value.delete(targetLine.id)
  }, 4000)
}

// --- 核心业务：触发发货事件（支持真实数据或交互模拟）---
function triggerSimulateDelivery(type = 'pipe') {
  const timeNow = new Date().toTimeString().split(' ')[0]
  
  // 1. 真实供给主体
  const chosenSup = rawSupplyEntities.length > 0 
    ? rawSupplyEntities[Math.floor(Math.random() * rawSupplyEntities.length)]
    : { entity_id: 'kaiyuan', entity_name: '大连开元热力管道股份有限公司' }
  const supName = chosenSup.entity_name || '大连开元热力管道股份有限公司'
  const supNodeId = `sup_${chosenSup.entity_id}`

  // 2. 真实需求标段 (10 大标段)
  const secTarget = sectionProgressList.value.length > 0 
    ? sectionProgressList.value[Math.floor(Math.random() * sectionProgressList.value.length)]
    : { id: 'high_lot_1', name: '高温水_标段1', designKm: 18.5, shippedKm: 12.0, totalFittings: 400, shippedFittings: 280 }
  const secNodeId = `sec_${secTarget.id}`

  if (type === 'pipe') {
    const models = rawPipeModels.length > 0 ? rawPipeModels : ['DN600', 'DN800', 'DN1000', 'DN1200', 'DN500']
    const model = models[Math.floor(Math.random() * models.length)]
    const meters = [120, 240, 360, 480][Math.floor(Math.random() * 4)]

    // 1. 战报卡片加入队列
    const newFeed = {
      id: 'sim_p_' + Date.now(),
      type: 'pipe',
      supplier: supName,
      target: secTarget.name,
      specification: `${model} 预制直埋保温管`,
      amount: `${meters} 米`,
      shipmentCode: 'DL-P-' + Math.floor(1000 + Math.random() * 9000),
      time: timeNow,
      positiveTag: `直达现场 +${meters}米 🚀`,
      isNew: true
    }
    liveFeedList.value.unshift(newFeed)
    if (liveFeedList.value.length > 25) liveFeedList.value = liveFeedList.value.slice(0, 25)

    // 2. 指标联动递增 (CountUp)
    const kmDelta = meters / 1000
    kpiData.pipeShippedKm = Math.round((kpiData.pipeShippedKm + kmDelta) * 100) / 100
    kpiData.pipeTransitKm = Math.round((kpiData.pipeTransitKm + kmDelta) * 100) / 100

    // 3. 气泡飘字
    bubbles.pipeShipped = meters
    bubbles.pipeTransit = meters
    setTimeout(() => {
      bubbles.pipeShipped = null
      bubbles.pipeTransit = null
    }, 2400)

    // 4. 标段能量槽充能
    lastImpactedSectionId.value = secTarget.id
    secTarget.shippedKm = Math.min(Math.round((secTarget.shippedKm + kmDelta) * 100) / 100, secTarget.designKm || 999)
    if (secTarget.designKm > 0) {
      secTarget.pipePercent = Math.min(Math.round((secTarget.shippedKm / secTarget.designKm) * 1000) / 10, 100)
    }

    // 5. 发射激光飞线粒子
    shootLaserParticle(supNodeId, secNodeId, 'pipe')

  } else {
    // 管件发运
    const fittings = ['90°大口径弯头', '同心变径管', '异径三通', '直埋波纹补偿器', '直埋焊接球阀', '固定支架节']
    const fittingName = fittings[Math.floor(Math.random() * fittings.length)]
    const pcs = [2, 4, 6, 8, 12][Math.floor(Math.random() * 5)]

    const newFeed = {
      id: 'sim_f_' + Date.now(),
      type: 'fitting',
      supplier: supName,
      target: secTarget.name,
      specification: fittingName,
      amount: `${pcs} 件套`,
      shipmentCode: 'FT-FAST-' + Math.floor(1000 + Math.random() * 9000),
      time: timeNow,
      positiveTag: `关键管件专车直达 +${pcs}件 ✨`,
      isNew: true
    }
    liveFeedList.value.unshift(newFeed)
    if (liveFeedList.value.length > 25) liveFeedList.value = liveFeedList.value.slice(0, 25)

    // 指标联动
    kpiData.fittingShippedPcs += pcs
    kpiData.fittingTransitPcs += pcs

    // 气泡飘字
    bubbles.fittingShipped = pcs
    bubbles.fittingTransit = pcs
    setTimeout(() => {
      bubbles.fittingShipped = null
      bubbles.fittingTransit = null
    }, 2400)

    // 标段管件充能
    lastImpactedSectionId.value = secTarget.id
    secTarget.shippedFittings += pcs
    if (secTarget.totalFittings > 0) {
      secTarget.fittingPercent = Math.min(Math.round((secTarget.shippedFittings / secTarget.totalFittings) * 1000) / 10, 100)
    }

    // 激光飞线
    shootLaserParticle(supNodeId, secNodeId, 'fitting')
  }

  // 3秒后移除新到标记
  setTimeout(() => {
    liveFeedList.value.forEach(f => f.isNew = false)
  }, 3000)
}

// 开启/关闭自动轮播演示
function toggleAutoDemo() {
  autoDemoRunning.value = !autoDemoRunning.value
  if (autoDemoRunning.value) {
    autoDemoTimer = setInterval(() => {
      const type = Math.random() > 0.45 ? 'pipe' : 'fitting'
      triggerSimulateDelivery(type)
    }, 4500)
  } else {
    if (autoDemoTimer) clearInterval(autoDemoTimer)
    autoDemoTimer = null
  }
}

// 全屏切换
function toggleFullscreen() {
  if (!document.fullscreenElement) {
    if (containerRef.value?.requestFullscreen) {
      containerRef.value.requestFullscreen()
      isFullscreen.value = true
    }
  } else {
    if (document.exitFullscreen) {
      document.exitFullscreen()
      isFullscreen.value = false
    }
  }
}

// 返回常规看板
function goBackToStandardDashboard() {
  router.push(`/projects/${encodeURIComponent(projectKey.value)}/pages/dashboard`)
}

// 格式化数字
function formatNumber(val) {
  if (val === null || val === undefined) return '0.00'
  return Number(val).toFixed(2)
}

// 时钟更新
function updateClock() {
  const d = new Date()
  const year = d.getFullYear()
  const mon = String(d.getMonth() + 1).padStart(2, '0')
  const date = String(d.getDate()).padStart(2, '0')
  const hour = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  const sec = String(d.getSeconds()).padStart(2, '0')
  const weekDay = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'][d.getDay()]
  currentTimeStr.value = `${year}-${mon}-${date} ${hour}:${min}:${sec} ${weekDay}`
}

// 加载 100% 真实项目与数据库数据 (只读感知，不写数据库)
async function loadRealData(isForce = false) {
  try {
    const res = await getTubeBigScreenData(projectKey.value)
    if (res && res.ok) {
      realShowDate.value = res.show_date || ''
      
      // 1. KPI 绑定
      if (res.kpi) {
        kpiData.pipeDesignKm = Number(res.kpi.pipeDesignKm || 0)
        kpiData.pipeShippedKm = Number(res.kpi.pipeShippedKm || 0)
        kpiData.pipeTransitKm = Number(res.kpi.pipeTransitKm || 0)
        kpiData.pipeDeliveredKm = Number(res.kpi.pipeDeliveredKm || 0)
        kpiData.fittingTotalPcs = Number(res.kpi.fittingTotalPcs || 1138)
        kpiData.fittingShippedPcs = Number(res.kpi.fittingShippedPcs || 0)
        kpiData.fittingTransitPcs = Number(res.kpi.fittingTransitPcs || 0)
        kpiData.fittingArrivedPcs = Number(res.kpi.fittingArrivedPcs || 0)
      }

      // 2. 管件真实分类统计
      if (Array.isArray(res.fitting_type_summary)) {
        fittingTypeSummary.value = res.fitting_type_summary
      }

      // 3. 真实 10 大标段健康矩阵
      if (Array.isArray(res.section_progress_list) && res.section_progress_list.length > 0) {
        sectionProgressList.value = res.section_progress_list
      }

      // 4. 真实全网动态战报流水 (100% 呈现数据库最新真实单据)
      if (Array.isArray(res.live_feed_list)) {
        liveFeedList.value = res.live_feed_list
        res.live_feed_list.forEach(f => knownFeedIds.value.add(f.id))
      }

      // 5. 真实拓扑节点 (3 大管厂)
      if (Array.isArray(res.supply_nodes)) {
        supplyNodes.value = res.supply_nodes
      }

      // 6. 真实里程碑
      if (Array.isArray(res.milestones)) {
        milestones.value = res.milestones
      }

      // 7. 保存底层字典供交互使用
      if (Array.isArray(res.supply_entities_raw)) {
        rawSupplyEntities = res.supply_entities_raw
      }
      if (Array.isArray(res.demand_entities_raw)) {
        rawDemandEntities = res.demand_entities_raw
      }
      if (Array.isArray(res.pipe_models)) {
        rawPipeModels = res.pipe_models
      }

      initialDataLoaded = true
      recalculateFlylines()
    }
  } catch (err) {
    console.warn('读取真实大屏聚合数据接口异常，使用配置与内置字典:', err)
    const summary = await getTubeWorkspaceConfigSummary(projectKey.value).catch(() => null)
    if (summary) {
      configSummary.value = summary
      rawSupplyEntities = summary.supply_entities || []
      rawDemandEntities = summary.demand_entities || []
      rawPipeModels = (summary.pipe_models || []).map(m => m.pipe_model_name || m.id || m)
    }
    initialDataLoaded = true
    recalculateFlylines()
  }
}

onMounted(() => {
  updateClock()
  timerClock = setInterval(updateClock, 1000)
  loadRealData()

  // 监听尺寸变化自适应重算飞线 (rAF 节流)
  if (topologyContainerRef.value && window.ResizeObserver) {
    resizeObserver = new ResizeObserver(() => {
      recalculateFlylines()
    })
    resizeObserver.observe(topologyContainerRef.value)
  }

  // 初始加载测量
  setTimeout(recalculateFlylines, 100)
  setTimeout(recalculateFlylines, 400)

  // 每 20 秒静默拉取数据库最新发货与核销状态
  autoSyncTimer = setInterval(loadRealData, 20000)
  window.addEventListener('resize', recalculateFlylines, { passive: true })
  window.addEventListener('click', handleGlobalClick)
})

onBeforeUnmount(() => {
  if (timerClock) clearInterval(timerClock)
  if (autoDemoTimer) clearInterval(autoDemoTimer)
  if (autoSyncTimer) clearInterval(autoSyncTimer)
  if (liveStreamTimer) clearInterval(liveStreamTimer)
  if (resizeObserver) resizeObserver.disconnect()
  if (rAFId) cancelAnimationFrame(rAFId)
  window.removeEventListener('resize', recalculateFlylines)
  window.removeEventListener('click', handleGlobalClick)
})
</script>

<style scoped>
/* ==========================================================================
   2026 预制直埋保温管智慧供应链数字指挥大屏 (工业规整立柱布局 + 生产实况实时直连)
   ========================================================================== */

/* --- 默认深色科技主题 (Dark Theme) --- */
.bigscreen-container {
  width: 100vw;
  height: 100vh;
  max-height: 100vh;
  overflow: hidden;
  background: #060913;
  color: #e2e8f0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  transform: translateZ(0);
}

/* --- 顶栏 Header --- */
.bigscreen-header {
  height: 70px;
  min-height: 70px;
  max-height: 70px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: relative;
  background: #090e1a;
  border-bottom: 1px solid rgba(0, 242, 254, 0.2);
  z-index: 1000;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 330px;
}

.header-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  background: rgba(0, 242, 254, 0.1);
  border: 1px solid rgba(0, 242, 254, 0.3);
  border-radius: 20px;
  font-size: 12px;
  color: #00f2fe;
  transition: all 0.3s ease;
}

.header-badge.live-mode {
  background: rgba(16, 185, 129, 0.15);
  border-color: rgba(16, 185, 129, 0.5);
  color: #10b981;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #00f2fe;
  box-shadow: 0 0 6px #00f2fe;
  animation: pulse-ring 2s infinite;
}

.pulse-dot.live {
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
}

.header-time {
  font-family: 'Consolas', monospace;
  font-size: 13px;
  color: #94a3b8;
  letter-spacing: 0.5px;
}

.header-title-box {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  z-index: 5;
  white-space: nowrap;
  pointer-events: auto;
}

.header-title {
  margin: 0;
  font-size: 21px;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: #ffffff;
  text-shadow: 0 2px 12px rgba(0, 242, 254, 0.35);
}

.header-sub {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.sub-sep {
  opacity: 0.4;
}

.header-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  z-index: 1050;
}

.control-center-wrapper {
  position: relative;
}

/* 调度控制中心触发主按钮 */
.control-trigger-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 16px;
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(0, 242, 254, 0.4);
  border-radius: 20px;
  color: #00f2fe;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3), inset 0 0 10px rgba(0, 242, 254, 0.1);
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.control-trigger-btn:hover,
.control-trigger-btn.active {
  background: rgba(0, 242, 254, 0.15);
  border-color: #00f2fe;
  box-shadow: 0 0 16px rgba(0, 242, 254, 0.4);
  color: #ffffff;
}

.control-trigger-btn.live-active {
  border-color: #10b981;
  color: #10b981;
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.3);
}

.control-caret {
  font-size: 10px;
  opacity: 0.7;
}

.mini-live-tag {
  font-size: 10px;
  background: rgba(16, 185, 129, 0.25);
  border: 1px solid rgba(16, 185, 129, 0.6);
  color: #10b981;
  padding: 1px 6px;
  border-radius: 8px;
}

/* 下拉菜单浮层 Popover */
.control-menu-popover {
  position: absolute;
  top: calc(100% + 12px);
  right: 0;
  width: 320px;
  background: rgba(9, 14, 26, 0.96);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(0, 242, 254, 0.3);
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.8), 0 0 20px rgba(0, 242, 254, 0.15);
  z-index: 1100;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.popover-title {
  font-size: 13px;
  font-weight: 700;
  color: #e2e8f0;
}

.popover-close-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 13px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.popover-close-btn:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.1);
}

.popover-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.group-title {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  letter-spacing: 0.5px;
}

.group-buttons-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.group-buttons-grid .action-btn {
  width: 100%;
  justify-content: center;
  padding: 7px 10px;
  font-size: 12px;
}

.popover-footer {
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.popover-footer .back-btn {
  width: 100%;
  justify-content: center;
  padding: 7px 12px;
}

/* 下拉动画 */
.control-dropdown-enter-active,
.control-dropdown-leave-active {
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.control-dropdown-enter-from,
.control-dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.96);
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: #0f172a;
  color: #f1f5f9;
  transition: all 0.2s ease;
}

.action-btn:hover {
  background: #1e293b;
  border-color: #00f2fe;
}

/* 核心：生产实况直连按钮 */
.live-stream-btn {
  background: rgba(16, 185, 129, 0.12);
  border-color: rgba(16, 185, 129, 0.4);
  color: #10b981;
  font-weight: 600;
}

.live-stream-btn:hover {
  background: rgba(16, 185, 129, 0.25);
  border-color: #10b981;
}

.live-stream-btn.active {
  background: #10b981;
  border-color: #10b981;
  color: #04130d;
  font-weight: 700;
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.5);
}

.theme-toggle-btn {
  background: rgba(0, 242, 254, 0.1);
  border-color: rgba(0, 242, 254, 0.35);
  color: #00f2fe;
}

.demo-btn {
  background: rgba(0, 242, 254, 0.12);
  border-color: rgba(0, 242, 254, 0.4);
  color: #00f2fe;
}

.demo-btn.active {
  background: rgba(59, 130, 246, 0.25);
  border-color: #3b82f6;
  color: #93c5fd;
}

.sim-btn {
  background: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.4);
  color: #93c5fd;
}

.sim-btn.fitting {
  background: rgba(251, 191, 36, 0.15);
  border-color: rgba(251, 191, 36, 0.4);
  color: #fde047;
}

.icon-btn {
  padding: 5px 9px;
  font-size: 14px;
}

.back-btn {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.3);
  color: #fca5a5;
}

/* --- 主内容网格 Content Layout --- */
.bigscreen-content {
  flex: 1;
  min-height: 0;
  height: calc(100vh - 70px);
  display: grid;
  grid-template-columns: 330px 1fr 370px;
  gap: 16px;
  padding: 14px 22px 18px;
  box-sizing: border-box;
  overflow: hidden;
}

.screen-col {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow: hidden;
}

.left-col {
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
}

/* --- 通用卡片样式 Panel Box --- */
.panel-box {
  background: #0b1322;
  border: 1px solid rgba(0, 242, 254, 0.18);
  border-radius: 9px;
  padding: 15px 16px;
  position: relative;
  box-sizing: border-box;
}

.panel-box::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 14px;
  height: 2px;
  background: #00f2fe;
}

.panel-box::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 2px;
  height: 14px;
  background: #00f2fe;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #f8fafc;
}

.title-icon {
  font-size: 15px;
}

.panel-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.panel-tag.cyan {
  background: rgba(0, 242, 254, 0.12);
  color: #38bdf8;
  border: 1px solid rgba(0, 242, 254, 0.3);
  font-weight: 600;
}

.panel-tag.gold {
  background: rgba(251, 191, 36, 0.12);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.3);
  font-weight: 600;
}

.panel-tag.green {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

/* --- KPI Metric Grid --- */
.kpi-metric-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 12px;
}

.metric-item {
  background: #111c30;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  padding: 9px 11px;
  position: relative;
  overflow: hidden;
}

.metric-label {
  font-size: 11px;
  color: #94a3b8;
  margin-bottom: 3px;
}

.metric-val {
  display: flex;
  align-items: baseline;
  gap: 4px;
  position: relative;
}

.metric-val .num {
  font-size: 19px;
  font-weight: 700;
  font-family: 'DIN Alternate', 'Helvetica Neue', Arial, sans-serif;
  color: #f1f5f9;
}

.metric-val .unit {
  font-size: 11px;
  color: #64748b;
}

.highlight-cyan .num {
  color: #00f2fe;
}

.highlight-amber .num {
  color: #fbbf24;
}

.highlight-green .num {
  color: #10b981;
}

.highlight-gold .num {
  color: #fbbf24;
}

.highlight-orange .num {
  color: #f97316;
}

/* 飘字气泡 (Delta Bubble) */
.delta-bubble {
  position: absolute;
  top: -16px;
  right: 0;
  font-size: 12px;
  font-weight: 700;
  color: #00ff87;
  background: rgba(0, 255, 135, 0.2);
  padding: 1px 6px;
  border-radius: 10px;
  border: 1px solid #00ff87;
  pointer-events: none;
}

.delta-bubble.amber {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.2);
  border-color: #fbbf24;
}

.delta-bubble.gold {
  color: #fde047;
  background: rgba(253, 224, 71, 0.2);
  border-color: #fde047;
}

.delta-bubble.orange {
  color: #f97316;
  background: rgba(249, 115, 22, 0.2);
  border-color: #f97316;
}

.bubble-fade-enter-active,
.bubble-fade-leave-active {
  transition: all 0.5s ease-out;
}

.bubble-fade-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.bubble-fade-leave-to {
  opacity: 0;
  transform: translateY(-12px);
}

/* --- 能量槽充能 Progress --- */
.energy-progress-box {
  margin-top: 4px;
}

.energy-progress-info {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #94a3b8;
  margin-bottom: 4px;
}

.cyan-text {
  color: #00f2fe;
}

.gold-text {
  color: #fbbf24;
}

.energy-bar-track {
  width: 100%;
  height: 10px;
  background: #111c30;
  border-radius: 5px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.energy-bar-fill {
  height: 100%;
  border-radius: 5px;
  position: relative;
  transition: width 0.8s ease-out;
}

.energy-bar-fill.cyan-glow {
  background: linear-gradient(90deg, #0052d4, #00f2fe);
}

.energy-bar-fill.gold-glow {
  background: linear-gradient(90deg, #d97706, #fbbf24);
}

.energy-bar-light {
  position: absolute;
  top: 0;
  right: 0;
  width: 10px;
  height: 100%;
  background: #ffffff;
}

/* --- 管件类型 Pills --- */
.fitting-types-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.fitting-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #111c30;
  border: 1px solid rgba(251, 191, 36, 0.25);
  border-radius: 5px;
  padding: 4px 8px;
  font-size: 11px;
}

.pill-name {
  color: #cbd5e1;
}

.pill-count {
  color: #fbbf24;
  font-weight: 600;
}

/* --- 安全与效率雷达面板 --- */
.safety-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.safety-card {
  display: flex;
  align-items: center;
  gap: 9px;
  background: #111c30;
  border: 1px solid rgba(16, 185, 129, 0.2);
  border-radius: 6px;
  padding: 8px 10px;
}

.safety-icon {
  font-size: 17px;
}

.safety-val {
  font-size: 14px;
  font-weight: 700;
  color: #10b981;
}

.safety-desc {
  font-size: 10.5px;
  color: #64748b;
}

/* ==========================================================================
   中间栏：数字孪生全景拓扑中枢 (规整双立柱架构 + 在途/交互按需显现)
   ========================================================================== */

.map-topology-master-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 12px 14px;
}

.topology-header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  flex-shrink: 0;
  gap: 12px;
}

.topo-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.topo-sub-tag {
  font-size: 11px;
  color: #64748b;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 2px 8px;
  border-radius: 4px;
}

/* 系统切换 Tabs */
.system-tabs {
  display: flex;
  gap: 6px;
}

.sys-tab-btn {
  background: #111c30;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  padding: 3px 10px;
  font-size: 11px;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.2s ease;
}

.sys-tab-btn:hover {
  border-color: #00f2fe;
  color: #f1f5f9;
}

.sys-tab-btn.active {
  background: rgba(0, 242, 254, 0.2);
  border-color: #00f2fe;
  color: #00f2fe;
  font-weight: 600;
}

.sys-tab-btn.high.active {
  background: rgba(239, 68, 68, 0.2);
  border-color: #ef4444;
  color: #fca5a5;
}

.sys-tab-btn.low.active {
  background: rgba(56, 189, 248, 0.2);
  border-color: #38bdf8;
  color: #7dd3fc;
}

.topology-legend {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
  color: #94a3b8;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.dot-line {
  width: 12px;
  height: 3px;
  border-radius: 2px;
}

.dot-line.cyan {
  background: #00f2fe;
}

.dot-line.gold {
  background: #fbbf24;
}

.dot-point.active {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #00ff87;
}

/* 拓扑主体舞台容器 */
.topology-container {
  flex: 1;
  min-height: 0;
  position: relative;
  border: 1px solid rgba(0, 242, 254, 0.2);
  border-radius: 8px;
  background: #070d19;
  overflow: hidden;
  box-sizing: border-box;
  transform: translateZ(0);
}

.topology-svg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 20;
  will-change: transform;
}

/* 动态飞线组合层 (默认无发货在途时完全隐藏，出现时平滑渐显) */
.flyline-group {
  transition: opacity 0.35s ease;
}

.flyline-base {
  fill: none;
  stroke-width: 1.5;
  opacity: 0.45;
}

.flyline-base.pipe {
  stroke: #00f2fe;
}

.flyline-base.fitting {
  stroke: #fbbf24;
}

.flyline-stream {
  fill: none;
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-dasharray: 6 10;
  opacity: 0.95;
  animation: flow-travel 1.4s linear infinite;
  will-change: stroke-dashoffset;
}

.flyline-stream.pipe {
  stroke: url(#grad-pipe-line);
}

.flyline-stream.fitting {
  stroke: url(#grad-fitting-line);
}

@keyframes flow-travel {
  from {
    stroke-dashoffset: 32;
  }
  to {
    stroke-dashoffset: 0;
  }
}

.laser-particle {
  pointer-events: none;
}

/* 拓扑主排版三栏布局 (左: 230px, 中: 50px 通道, 右: 1fr) */
.topology-layout-grid {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: grid;
  grid-template-columns: 260px 45px 1fr;
  padding: 10px;
  box-sizing: border-box;
  z-index: 10;
  gap: 0;
}

/* 1. 供给制造基地列 */
.supply-hub-col {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.hub-header {
  margin-bottom: 8px;
  flex-shrink: 0;
}

.hub-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  display: inline-block;
}

.hub-badge.supply {
  background: rgba(0, 242, 254, 0.15);
  color: #00f2fe;
  border: 1px solid rgba(0, 242, 254, 0.3);
}

.supply-cards-stack {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-around;
  gap: 16px;
}

.supply-node-card {
  background: linear-gradient(135deg, rgba(17, 34, 60, 0.85) 0%, rgba(11, 20, 36, 0.95) 100%);
  border: 1px solid rgba(0, 242, 254, 0.22);
  border-left: 4px solid #00f2fe;
  border-radius: 8px;
  padding: 18px 20px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  min-height: 76px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-sizing: border-box;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
}

.supply-node-card:nth-child(2) {
  border-left-color: #fbbf24;
  border-color: rgba(251, 191, 36, 0.22);
  background: linear-gradient(135deg, rgba(38, 30, 18, 0.75) 0%, rgba(15, 25, 45, 0.95) 100%);
}

.supply-node-card:nth-child(3) {
  border-left-color: #00ff87;
  border-color: rgba(0, 255, 135, 0.22);
  background: linear-gradient(135deg, rgba(16, 38, 30, 0.75) 0%, rgba(15, 25, 45, 0.95) 100%);
}

.supply-node-card:hover,
.supply-node-card.active,
.supply-node-card.hovered {
  border-color: #00f2fe;
  transform: translateX(4px);
  box-shadow: 0 6px 20px rgba(0, 242, 254, 0.18);
}

.supply-node-card:nth-child(2):hover,
.supply-node-card:nth-child(2).hovered {
  border-color: #fbbf24;
  box-shadow: 0 6px 20px rgba(251, 191, 36, 0.18);
}

.supply-node-card:nth-child(3):hover,
.supply-node-card:nth-child(3).hovered {
  border-color: #00ff87;
  box-shadow: 0 6px 20px rgba(0, 255, 135, 0.18);
}

.supply-node-card.dimmed {
  opacity: 0.3;
}

.sup-title {
  font-size: 15px;
  font-weight: 700;
  color: #ffffff;
  white-space: normal;
  line-height: 1.4;
  letter-spacing: 0.3px;
  word-break: break-word;
  padding-right: 12px;
}

/* 2. 中间传输通道 */
.transit-channel-col {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.channel-track {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  opacity: 0.6;
}

.channel-glow-line {
  width: 2px;
  height: 80px;
  background: linear-gradient(180deg, transparent, #00f2fe, transparent);
}

.channel-text {
  writing-mode: vertical-rl;
  font-size: 9.5px;
  color: #64748b;
  letter-spacing: 2px;
}

/* 3. 需求标段矩阵列：规整的高温水/低温水双立柱体系 (加大高度与饱满间距) */
.demand-hub-col {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding-left: 6px;
}

.demand-systems-split {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  overflow: hidden;
}

.system-sub-col {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.system-cards-list {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 10px;
  overflow: hidden;
}

.demand-node-card {
  flex: 1;
  min-height: 0;
  background: #0f192b;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 10px 14px;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 5px;
  cursor: pointer;
  transition: transform 0.2s ease, opacity 0.25s ease, border-color 0.25s ease;
  box-sizing: border-box;
}

.demand-node-card.high-system {
  border-left: 3.5px solid #ef4444;
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.08) 0%, #0f192b 40%);
}

.demand-node-card.low-system {
  border-left: 3.5px solid #0ea5e9;
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.08) 0%, #0f192b 40%);
}

.demand-node-card.highlighted {
  border-color: #00f2fe;
  background: #11263d;
  transform: translateY(-1px);
}

.demand-node-card.dimmed {
  opacity: 0.35;
}

.demand-node-card.completed {
  border-color: rgba(251, 191, 36, 0.35);
}

.sec-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sec-badge-name {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.sec-sys-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 1.5px 6px;
  border-radius: 4px;
  white-space: nowrap;
  line-height: 1.3;
}

.sec-sys-badge.high {
  background: rgba(239, 68, 68, 0.22);
  border: 1px solid rgba(239, 68, 68, 0.45);
  color: #fca5a5;
}

.sec-sys-badge.low {
  background: rgba(56, 189, 248, 0.18);
  border: 1px solid rgba(56, 189, 248, 0.45);
  color: #7dd3fc;
}

.sec-code-tag {
  font-family: monospace;
  font-size: 11.5px;
  font-weight: 800;
  padding: 1.5px 6px;
  border-radius: 4px;
  white-space: nowrap;
}

.sec-code-tag.high {
  background: rgba(239, 68, 68, 0.15);
  color: #fca5a5;
}

.sec-code-tag.low {
  background: rgba(56, 189, 248, 0.15);
  color: #7dd3fc;
}

.sec-title {
  font-size: 14px;
  font-weight: 700;
  color: #ffffff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: 0.2px;
}

.sec-status-chip {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  padding: 2px 9px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.06);
  color: #cbd5e1;
  white-space: nowrap;
  font-weight: 500;
}

.sec-status-chip.running {
  background: rgba(16, 185, 129, 0.2);
  color: #00ff87;
  font-weight: 600;
}

.chip-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #94a3b8;
}

.sec-status-chip.running .chip-dot {
  background: #00ff87;
  box-shadow: 0 0 6px #00ff87;
}

/* 双轨微进度条 (加大高度与辨识度) */
.sec-metrics-body {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 0;
}

.sec-metric-line {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.line-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12.5px;
  font-weight: 600;
}

.line-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
  color: #ffffff;
  letter-spacing: 0.2px;
  line-height: 1.2;
}

.line-label.pipe-tag {
  background: rgba(56, 189, 248, 0.14);
  border: 1px solid rgba(56, 189, 248, 0.35);
  color: #ffffff;
}

.line-label.fitting-tag {
  background: rgba(245, 158, 11, 0.14);
  border: 1px solid rgba(245, 158, 11, 0.35);
  color: #ffffff;
}

.line-val {
  font-family: 'DIN Alternate', 'Helvetica Neue', Arial, monospace;
  font-size: 13px;
  font-weight: 600;
}

.line-pct {
  font-weight: 800;
  font-size: 13px;
}

.micro-bar-bg {
  width: 100%;
  height: 7px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.micro-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.8s ease;
}

.micro-bar-fill.cyan {
  background: linear-gradient(90deg, #0052d4, #00f2fe);
}

.micro-bar-fill.gold {
  background: linear-gradient(90deg, #d97706, #fbbf24);
}

/* 连接锚点 Node Ports (物理对齐) */
.node-port {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 15;
}

.node-port.port-out {
  right: -5px;
  background: #060913;
  border: 1.5px solid #00f2fe;
}

.node-port.port-in {
  left: -5px;
  background: #060913;
  border: 1.5px solid #38bdf8;
}

.port-dot {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #00ff87;
}

/* --- 右侧栏：实时战报流 Live Feed --- */
.live-feed-panel {
  flex: 1.4;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.live-status-pill {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  color: #10b981;
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 10px;
  padding: 1px 6px;
  transition: all 0.3s ease;
}

.live-status-pill.live-direct {
  background: rgba(16, 185, 129, 0.25);
  border-color: #10b981;
  color: #00ff87;
  font-weight: 600;
}

.live-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #10b981;
  animation: pulse-ring 2s infinite;
}

.live-dot.live-pulse {
  background: #00ff87;
  box-shadow: 0 0 6px #00ff87;
}

/* ==================== 统一业务分类筛选器 (折叠式下拉面板) ==================== */
.feed-filter-unified-bar {
  margin-bottom: 8px;
  flex-shrink: 0;
  position: relative;
  z-index: 40;
}

.filter-dropdown-wrapper {
  position: relative;
  width: 100%;
}

.unified-filter-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(135deg, rgba(17, 28, 48, 0.95) 0%, rgba(13, 22, 38, 0.95) 100%);
  border: 1px solid rgba(0, 242, 254, 0.25);
  border-radius: 6px;
  padding: 6px 10px;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: inset 0 0 8px rgba(0, 242, 254, 0.05);
}

.unified-filter-btn:hover {
  background: linear-gradient(135deg, rgba(22, 36, 62, 0.95) 0%, rgba(15, 27, 48, 0.95) 100%);
  border-color: #00f2fe;
  box-shadow: 0 0 10px rgba(0, 242, 254, 0.2), inset 0 0 10px rgba(0, 242, 254, 0.1);
}

.unified-filter-btn.menu-open {
  border-color: #00f2fe;
  box-shadow: 0 0 12px rgba(0, 242, 254, 0.25);
}

.unified-filter-btn.is-filtered {
  border-color: #38bdf8;
  background: linear-gradient(135deg, rgba(14, 116, 144, 0.25) 0%, rgba(15, 23, 42, 0.9) 100%);
}

.filter-btn-left {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.filter-btn-icon {
  font-size: 13px;
}

.filter-btn-label {
  color: #94a3b8;
  font-size: 11px;
}

.filter-btn-current {
  color: #00f2fe;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.filter-btn-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-btn-badge {
  font-size: 10.5px;
  background: rgba(0, 242, 254, 0.15);
  color: #38bdf8;
  border: 1px solid rgba(0, 242, 254, 0.3);
  padding: 1px 6px;
  border-radius: 10px;
  font-weight: 500;
}

.filter-caret {
  font-size: 9px;
  color: #64748b;
  transition: transform 0.2s ease;
}

/* 下拉浮层面板 */
.feed-filter-popover {
  position: absolute;
  top: calc(100% + 5px);
  left: 0;
  right: 0;
  background: rgba(10, 18, 32, 0.98);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(0, 242, 254, 0.4);
  border-radius: 8px;
  padding: 8px;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.75), 0 0 15px rgba(0, 242, 254, 0.15);
  z-index: 100;
}

.popover-tip-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 6px 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  margin-bottom: 6px;
}

.popover-title-text {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 500;
}

.reset-filter-link {
  font-size: 10.5px;
  color: #38bdf8;
  background: none;
  border: none;
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
}

.reset-filter-link:hover {
  color: #00f2fe;
}

.popover-options-grid {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.filter-option-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-option-row:hover {
  background: rgba(0, 242, 254, 0.08);
  border-color: rgba(0, 242, 254, 0.2);
}

.filter-option-row.active {
  background: rgba(0, 242, 254, 0.18);
  border-color: #00f2fe;
}

.option-tag-part {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
}

.option-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.option-icon {
  font-size: 12px;
}

.option-title {
  color: #e2e8f0;
}

.filter-option-row.active .option-title {
  color: #00f2fe;
  font-weight: 600;
}

.option-meta-part {
  display: flex;
  align-items: center;
  gap: 6px;
}

.option-badge {
  font-size: 10px;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.06);
  padding: 1px 5px;
  border-radius: 8px;
}

.filter-option-row.active .option-badge {
  background: rgba(0, 242, 254, 0.25);
  color: #00f2fe;
  font-weight: 600;
}

.option-check {
  font-size: 11px;
  color: #00f2fe;
  font-weight: bold;
}

/* 展开动画 */
.filter-dropdown-anim-enter-active,
.filter-dropdown-anim-leave-active {
  transition: all 0.2s ease;
}

.filter-dropdown-anim-enter-from,
.filter-dropdown-anim-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.feed-list-wrapper {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
}

.feed-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.feed-card {
  background: #0f192b;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 7px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  position: relative;
  transition: all 0.25s ease;
  flex-shrink: 0;
  box-sizing: border-box;
  width: 100%;
  overflow: hidden;
}

.feed-card:hover {
  background: #14223a;
  border-color: rgba(0, 242, 254, 0.3);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

/* 6 大核心业务分类卡片左侧标识色 */
.feed-card.dispatch {
  border-left: 3.5px solid #00f2fe;
}

.feed-card.arrival {
  border-left: 3.5px solid #3b82f6;
}

.feed-card.receive {
  border-left: 3.5px solid #f59e0b;
}

.feed-card.warehouse {
  border-left: 3.5px solid #10b981;
}

.feed-card.usage {
  border-left: 3.5px solid #a855f7;
}

.feed-card.plan {
  border-left: 3.5px solid #f43f5e;
}

.feed-card.just-arrived {
  background: #12223a;
  animation: card-arrive-pulse 2s ease;
}

@keyframes card-arrive-pulse {
  0% { box-shadow: 0 0 15px rgba(0, 242, 254, 0.6); }
  100% { box-shadow: none; }
}

/* Row 1: 顶栏 (分类标签 + 经办人 + 时间) */
.feed-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  width: 100%;
}

.header-left-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex: 1;
}

/* 6 大分类徽章微胶囊 */
.feed-category-tag {
  font-size: 10.5px;
  font-weight: 700;
  padding: 1.5px 6px;
  border-radius: 3px;
  white-space: nowrap;
  flex-shrink: 0;
}

.feed-category-tag.dispatch {
  background: rgba(0, 242, 254, 0.14);
  border: 1px solid rgba(0, 242, 254, 0.3);
  color: #38bdf8;
}

.feed-category-tag.arrival {
  background: rgba(59, 130, 246, 0.14);
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: #60a5fa;
}

.feed-category-tag.receive {
  background: rgba(245, 158, 11, 0.14);
  border: 1px solid rgba(245, 158, 11, 0.3);
  color: #fbbf24;
}

.feed-category-tag.warehouse {
  background: rgba(16, 185, 129, 0.14);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #34d399;
}

.feed-category-tag.usage {
  background: rgba(168, 85, 247, 0.14);
  border: 1px solid rgba(168, 85, 247, 0.3);
  color: #c084fc;
}

.feed-category-tag.plan {
  background: rgba(244, 63, 94, 0.14);
  border: 1px solid rgba(244, 63, 94, 0.3);
  color: #fb7185;
}

.feed-operator-tag {
  font-size: 10px;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 1px 5px;
  border-radius: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 90px;
}

.feed-time {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 10.5px;
  color: #64748b;
  font-weight: 500;
  flex-shrink: 0;
  white-space: nowrap;
}

/* Row 2: 标题 / 流向行 */
.feed-card-headline {
  width: 100%;
  overflow: hidden;
}

.route-line-box {
  display: flex;
  align-items: center;
  gap: 5px;
  width: 100%;
}

.route-source {
  color: #f1f5f9;
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}

.route-arrow {
  color: #00f2fe;
  font-size: 10px;
  flex-shrink: 0;
}

.route-target {
  color: #38bdf8;
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
  text-align: right;
}

.action-headline-box {
  width: 100%;
  overflow: hidden;
}

.action-headline-text {
  color: #f8fafc;
  font-size: 11.5px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

/* Row 3: 规格与数量明细栏 */
.feed-spec-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.05);
  padding: 3.5px 7px;
  border-radius: 4px;
  width: 100%;
  box-sizing: border-box;
}

.spec-text-col {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.spec-name {
  font-size: 10.5px;
  color: #cbd5e1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

.spec-qty-col {
  flex-shrink: 0;
}

.spec-amount-badge {
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
  padding: 1px 5px;
  border-radius: 3px;
}

.spec-amount-badge.pipe {
  background: rgba(0, 242, 254, 0.15);
  color: #00f2fe;
}

.spec-amount-badge.fitting {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
}

/* Row 4: 底栏 (单号/车牌 + 正向动态评价) */
.feed-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  width: 100%;
}

.feed-code-tag {
  display: flex;
  align-items: center;
  gap: 3px;
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 9.5px;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
  flex: 1;
}

.code-icon {
  font-size: 9px;
  flex-shrink: 0;
}

.code-val {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.feed-pos-tag {
  font-size: 9.5px;
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.2);
  padding: 1px 5px;
  border-radius: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 150px;
  flex-shrink: 0;
}

/* 战报动画 TransitionGroup */
.feed-item-enter-active,
.feed-item-leave-active {
  transition: all 0.35s ease-out;
}

.feed-item-enter-from {
  opacity: 0;
  transform: translateY(-12px);
}

.feed-item-leave-to {
  opacity: 0;
  transform: translateY(12px);
}

/* --- 重大里程碑 Milestone --- */
.milestone-panel {
  flex: 0.9;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.milestone-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.milestone-item {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 7px 8px;
  background: #111c30;
  border-radius: 5px;
  border-left: 2px solid #fbbf24;
  flex-shrink: 0;
}

.milestone-badge {
  font-family: monospace;
  font-weight: 700;
  font-size: 11px;
  color: #fbbf24;
}

.milestone-content {
  flex: 1;
  min-width: 0;
}

.m-title {
  font-size: 11.5px;
  font-weight: 600;
  color: #f1f5f9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.m-desc {
  font-size: 10.5px;
  color: #94a3b8;
  margin-top: 1px;
  line-height: 1.3;
}

.m-time {
  font-family: monospace;
  font-size: 10px;
  color: #64748b;
  flex-shrink: 0;
}

/* --- 精美深色科技细滚动条 Custom Scrollbars --- */
.left-col::-webkit-scrollbar,
.feed-list-wrapper::-webkit-scrollbar,
.system-cards-list::-webkit-scrollbar,
.milestone-list::-webkit-scrollbar {
  width: 4px;
  height: 4px;
}

.left-col::-webkit-scrollbar-track,
.feed-list-wrapper::-webkit-scrollbar-track,
.system-cards-list::-webkit-scrollbar-track,
.milestone-list::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 2px;
}

.left-col::-webkit-scrollbar-thumb,
.feed-list-wrapper::-webkit-scrollbar-thumb,
.system-cards-list::-webkit-scrollbar-thumb,
.milestone-list::-webkit-scrollbar-thumb {
  background: rgba(0, 242, 254, 0.25);
  border-radius: 2px;
}

/* ==========================================================================
   明亮浅色高科技模式 (Light Clean Tech Theme)
   ========================================================================== */

.bigscreen-container.light {
  background-color: #f1f5f9;
  background-image: none;
  color: #0f172a;
}

.bigscreen-container.light .bigscreen-header {
  background: #ffffff;
  border-bottom: 1px solid rgba(203, 213, 225, 0.8);
}

.bigscreen-container.light .header-badge {
  background: rgba(2, 132, 199, 0.1);
  border-color: rgba(2, 132, 199, 0.3);
  color: #0284c7;
}

.bigscreen-container.light .header-badge.live-mode {
  background: rgba(16, 185, 129, 0.15);
  border-color: rgba(16, 185, 129, 0.5);
  color: #059669;
}

.bigscreen-container.light .header-time {
  color: #475569;
}

.bigscreen-container.light .header-title {
  color: #0f172a;
  text-shadow: none;
}

.bigscreen-container.light .header-sub {
  color: #64748b;
}

.bigscreen-container.light .control-trigger-btn {
  background: #ffffff;
  border-color: #cbd5e1;
  color: #0284c7;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
}

.bigscreen-container.light .control-trigger-btn:hover,
.bigscreen-container.light .control-trigger-btn.active {
  background: #f0f9ff;
  border-color: #0284c7;
  color: #0369a1;
  box-shadow: 0 4px 12px rgba(2, 132, 199, 0.2);
}

.bigscreen-container.light .control-menu-popover {
  background: rgba(255, 255, 255, 0.98);
  border-color: #cbd5e1;
  box-shadow: 0 16px 36px -8px rgba(15, 23, 42, 0.15);
}

.bigscreen-container.light .popover-title {
  color: #0f172a;
}

.bigscreen-container.light .group-title {
  color: #64748b;
}

.bigscreen-container.light .popover-header,
.bigscreen-container.light .popover-footer {
  border-color: #e2e8f0;
}

.bigscreen-container.light .action-btn {
  background: #ffffff;
  border-color: #cbd5e1;
  color: #334155;
}

.bigscreen-container.light .action-btn:hover {
  background: #f8fafc;
  color: #0f172a;
  border-color: #94a3b8;
}

.bigscreen-container.light .live-stream-btn {
  background: rgba(16, 185, 129, 0.12);
  border-color: rgba(16, 185, 129, 0.5);
  color: #059669;
}

.bigscreen-container.light .live-stream-btn.active {
  background: #059669;
  border-color: #059669;
  color: #ffffff;
}

.bigscreen-container.light .theme-toggle-btn {
  background: rgba(2, 132, 199, 0.1);
  border-color: rgba(2, 132, 199, 0.35);
  color: #0284c7;
}

.bigscreen-container.light .demo-btn {
  background: rgba(2, 132, 199, 0.1);
  border-color: rgba(2, 132, 199, 0.35);
  color: #0284c7;
}

.bigscreen-container.light .demo-btn.active {
  background: rgba(16, 185, 129, 0.15);
  border-color: rgba(16, 185, 129, 0.5);
  color: #059669;
}

.bigscreen-container.light .sim-btn {
  background: rgba(2, 132, 199, 0.1);
  border-color: rgba(2, 132, 199, 0.3);
  color: #0284c7;
}

.bigscreen-container.light .sim-btn.fitting {
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.3);
  color: #d97706;
}

.bigscreen-container.light .back-btn {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.25);
  color: #dc2626;
}

.bigscreen-container.light .panel-box {
  background: #ffffff;
  border: 1px solid rgba(203, 213, 225, 0.8);
}

.bigscreen-container.light .panel-box::before,
.bigscreen-container.light .panel-box::after {
  background: #0284c7;
}

.bigscreen-container.light .panel-title {
  color: #0f172a;
}

.bigscreen-container.light .panel-tag.cyan {
  background: rgba(2, 132, 199, 0.12);
  color: #0284c7;
  border: 1px solid rgba(2, 132, 199, 0.35);
}

.bigscreen-container.light .panel-tag.gold {
  background: rgba(245, 158, 11, 0.12);
  color: #d97706;
  border: 1px solid rgba(245, 158, 11, 0.35);
}

.bigscreen-container.light .panel-tag.green {
  background: rgba(16, 185, 129, 0.12);
  color: #059669;
  border: 1px solid rgba(16, 185, 129, 0.35);
}

.bigscreen-container.light .topo-sub-tag {
  background: #f1f5f9;
  border-color: #e2e8f0;
  color: #64748b;
}

.bigscreen-container.light .sys-tab-btn {
  background: #ffffff;
  border-color: #cbd5e1;
  color: #64748b;
}

.bigscreen-container.light .sys-tab-btn.active {
  background: rgba(2, 132, 199, 0.15);
  border-color: #0284c7;
  color: #0284c7;
}

.bigscreen-container.light .metric-item {
  background: #f8fafc;
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.bigscreen-container.light .metric-label {
  color: #64748b;
}

.bigscreen-container.light .metric-val .num {
  color: #0f172a;
}

.bigscreen-container.light .highlight-cyan .num {
  color: #0284c7;
}

.bigscreen-container.light .highlight-amber .num {
  color: #d97706;
}

.bigscreen-container.light .highlight-green .num {
  color: #059669;
}

.bigscreen-container.light .highlight-gold .num {
  color: #d97706;
}

.bigscreen-container.light .highlight-orange .num {
  color: #ea580c;
}

.bigscreen-container.light .energy-progress-info {
  color: #475569;
}

.bigscreen-container.light .cyan-text {
  color: #0284c7;
}

.bigscreen-container.light .gold-text {
  color: #d97706;
}

.bigscreen-container.light .energy-bar-track {
  background: #e2e8f0;
  border-color: rgba(203, 213, 225, 0.6);
}

.bigscreen-container.light .energy-bar-fill.cyan-glow {
  background: linear-gradient(90deg, #0284c7, #38bdf8);
}

.bigscreen-container.light .energy-bar-fill.gold-glow {
  background: linear-gradient(90deg, #d97706, #fbbf24);
}

.bigscreen-container.light .fitting-pill {
  background: #ffffff;
  border-color: rgba(245, 158, 11, 0.3);
}

.bigscreen-container.light .pill-name {
  color: #475569;
}

.bigscreen-container.light .pill-count {
  color: #d97706;
}

.bigscreen-container.light .safety-card {
  background: #f8fafc;
  border-color: rgba(16, 185, 129, 0.3);
}

.bigscreen-container.light .safety-val {
  color: #059669;
}

.bigscreen-container.light .safety-desc {
  color: #64748b;
}

.bigscreen-container.light .topology-legend {
  color: #475569;
}

.bigscreen-container.light .dot-line.cyan {
  background: #0284c7;
}

.bigscreen-container.light .dot-line.gold {
  background: #ea580c;
}

.bigscreen-container.light .topology-container {
  background: #f8fafc;
  border-color: rgba(203, 213, 225, 0.8);
}

.bigscreen-container.light .flyline-base.pipe {
  stroke: #0284c7;
  opacity: 0.25;
}

.bigscreen-container.light .flyline-base.fitting {
  stroke: #ea580c;
  opacity: 0.25;
}

.bigscreen-container.light .flyline-stream.pipe {
  stroke: #0284c7;
}

.bigscreen-container.light .flyline-stream.fitting {
  stroke: #ea580c;
}

.bigscreen-container.light .system-sub-col {
  background: transparent;
  border: none;
}

.bigscreen-container.light .supply-node-card {
  background: #ffffff;
  border-color: rgba(203, 213, 225, 0.9);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.bigscreen-container.light .supply-node-card:nth-child(1) {
  border-left-color: #0284c7;
}

.bigscreen-container.light .supply-node-card:nth-child(2) {
  border-left-color: #d97706;
}

.bigscreen-container.light .supply-node-card:nth-child(3) {
  border-left-color: #059669;
}

.bigscreen-container.light .supply-node-card:hover,
.bigscreen-container.light .supply-node-card.active,
.bigscreen-container.light .supply-node-card.hovered {
  border-color: #0284c7;
  background: #f8fafc;
  box-shadow: 0 4px 14px rgba(2, 132, 199, 0.12);
}

.bigscreen-container.light .sup-title {
  color: #0f172a;
}

.bigscreen-container.light .demand-node-card {
  background: #ffffff;
  border-color: rgba(226, 232, 240, 0.9);
}

.bigscreen-container.light .demand-node-card.high-system {
  border-left: 3.5px solid #dc2626;
  background: linear-gradient(135deg, rgba(254, 226, 226, 0.5) 0%, #ffffff 40%);
}

.bigscreen-container.light .demand-node-card.low-system {
  border-left: 3.5px solid #0284c7;
  background: linear-gradient(135deg, rgba(224, 242, 254, 0.5) 0%, #ffffff 40%);
}

.bigscreen-container.light .demand-node-card.highlighted {
  border-color: #0284c7;
  background: #f0f9ff;
}

.bigscreen-container.light .sec-sys-badge.high {
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.35);
  color: #dc2626;
}

.bigscreen-container.light .sec-sys-badge.low {
  background: rgba(2, 132, 199, 0.12);
  border: 1px solid rgba(2, 132, 199, 0.35);
  color: #0284c7;
}

.bigscreen-container.light .sec-code-tag.high {
  background: rgba(239, 68, 68, 0.1);
  color: #b91c1c;
}

.bigscreen-container.light .sec-code-tag.low {
  background: rgba(2, 132, 199, 0.1);
  color: #0369a1;
}

.bigscreen-container.light .sec-title {
  color: #0f172a;
}

.bigscreen-container.light .line-label {
  color: #0f172a;
}

.bigscreen-container.light .line-label.pipe-tag {
  background: rgba(2, 132, 199, 0.12);
  border: 1px solid rgba(2, 132, 199, 0.35);
  color: #0369a1;
}

.bigscreen-container.light .line-label.fitting-tag {
  background: rgba(245, 158, 11, 0.15);
  border: 1px solid rgba(245, 158, 11, 0.4);
  color: #b45309;
}

.bigscreen-container.light .micro-bar-bg {
  background: #e2e8f0;
}

.bigscreen-container.light .micro-bar-fill.cyan {
  background: linear-gradient(90deg, #0284c7, #38bdf8);
}

.bigscreen-container.light .micro-bar-fill.gold {
  background: linear-gradient(90deg, #d97706, #fbbf24);
}

.bigscreen-container.light .node-port.port-out {
  background: #ffffff;
  border-color: #0284c7;
}

.bigscreen-container.light .node-port.port-in {
  background: #ffffff;
  border-color: #0284c7;
}

.bigscreen-container.light .unified-filter-btn {
  background: #ffffff;
  border-color: #cbd5e1;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.bigscreen-container.light .unified-filter-btn:hover {
  border-color: #0284c7;
  background: #f8fafc;
}

.bigscreen-container.light .filter-btn-current {
  color: #0284c7;
}

.bigscreen-container.light .filter-btn-badge {
  background: #e0f2fe;
  color: #0284c7;
  border-color: #bae6fd;
}

.bigscreen-container.light .feed-filter-popover {
  background: #ffffff;
  border-color: #cbd5e1;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.12);
}

.bigscreen-container.light .filter-option-row {
  background: transparent;
}

.bigscreen-container.light .filter-option-row:hover {
  background: #f1f5f9;
  border-color: #e2e8f0;
}

.bigscreen-container.light .filter-option-row.active {
  background: #e0f2fe;
  border-color: #0284c7;
}

.bigscreen-container.light .filter-option-row .option-title {
  color: #1e293b;
}

.bigscreen-container.light .filter-option-row.active .option-title {
  color: #0284c7;
}

.bigscreen-container.light .filter-option-row.active .option-check {
  color: #0284c7;
}

.bigscreen-container.light .feed-card {
  background: #ffffff;
  border-color: rgba(226, 232, 240, 0.9);
}

.bigscreen-container.light .feed-card.dispatch {
  border-left: 3.5px solid #0284c7;
}

.bigscreen-container.light .feed-card.arrival {
  border-left: 3.5px solid #2563eb;
}

.bigscreen-container.light .feed-card.receive {
  border-left: 3.5px solid #d97706;
}

.bigscreen-container.light .feed-card.warehouse {
  border-left: 3.5px solid #059669;
}

.bigscreen-container.light .feed-card.usage {
  border-left: 3.5px solid #9333ea;
}

.bigscreen-container.light .feed-card.plan {
  border-left: 3.5px solid #e11d48;
}

.bigscreen-container.light .feed-category-tag.dispatch {
  background: rgba(2, 132, 199, 0.12);
  border: 1px solid rgba(2, 132, 199, 0.25);
  color: #0284c7;
}

.bigscreen-container.light .feed-category-tag.arrival {
  background: rgba(37, 99, 235, 0.12);
  border: 1px solid rgba(37, 99, 235, 0.25);
  color: #2563eb;
}

.bigscreen-container.light .feed-category-tag.receive {
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.25);
  color: #d97706;
}

.bigscreen-container.light .feed-category-tag.warehouse {
  background: rgba(5, 150, 105, 0.12);
  border: 1px solid rgba(5, 150, 105, 0.25);
  color: #059669;
}

.bigscreen-container.light .feed-category-tag.usage {
  background: rgba(147, 51, 234, 0.12);
  border: 1px solid rgba(147, 51, 234, 0.25);
  color: #9333ea;
}

.bigscreen-container.light .feed-category-tag.plan {
  background: rgba(225, 29, 72, 0.12);
  border: 1px solid rgba(225, 29, 72, 0.25);
  color: #e11d48;
}

.bigscreen-container.light .feed-card.just-arrived {
  background: #f0f9ff;
}

.bigscreen-container.light .feed-operator-tag {
  background: #f1f5f9;
  border-color: #e2e8f0;
  color: #475569;
}

.bigscreen-container.light .route-source {
  color: #0f172a;
}

.bigscreen-container.light .route-arrow {
  color: #0284c7;
}

.bigscreen-container.light .route-target {
  color: #0284c7;
}

.bigscreen-container.light .action-headline-text {
  color: #0f172a;
}

.bigscreen-container.light .feed-spec-box {
  background: #f8fafc;
  border-color: #e2e8f0;
}

.bigscreen-container.light .spec-name {
  color: #334155;
}

.bigscreen-container.light .spec-amount-badge.pipe {
  background: rgba(2, 132, 199, 0.12);
  color: #0284c7;
}

.bigscreen-container.light .spec-amount-badge.fitting {
  background: rgba(217, 119, 6, 0.12);
  color: #d97706;
}

.bigscreen-container.light .feed-code-tag {
  color: #64748b;
}

.bigscreen-container.light .feed-pos-tag {
  background: #ecfdf5;
  border-color: #a7f3d0;
  color: #059669;
}

.bigscreen-container.light .milestone-item {
  background: #ffffff;
  border-left-color: #d97706;
}

.bigscreen-container.light .milestone-badge {
  color: #d97706;
}

.bigscreen-container.light .m-title {
  color: #0f172a;
}

.bigscreen-container.light .m-desc {
  color: #64748b;
}

.bigscreen-container.light .left-col::-webkit-scrollbar-track,
.bigscreen-container.light .feed-list-wrapper::-webkit-scrollbar-track,
.bigscreen-container.light .system-cards-list::-webkit-scrollbar-track,
.bigscreen-container.light .milestone-list::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.05);
}

.bigscreen-container.light .left-col::-webkit-scrollbar-thumb,
.bigscreen-container.light .feed-list-wrapper::-webkit-scrollbar-thumb,
.bigscreen-container.light .system-cards-list::-webkit-scrollbar-thumb,
.bigscreen-container.light .milestone-list::-webkit-scrollbar-thumb {
  background: rgba(2, 132, 199, 0.3);
}

/* --- 关键帧动画 Keyframes --- */
@keyframes pulse-ring {
  0% {
    opacity: 0.8;
  }
  50% {
    opacity: 0.2;
  }
  100% {
    opacity: 0.8;
  }
}

/* --- 响应式适配 --- */
@media (max-width: 1400px) {
  .bigscreen-content {
    grid-template-columns: 300px 1fr 330px;
    gap: 10px;
    padding: 8px 12px;
  }
  .header-title {
    font-size: 18px;
  }
  .topology-layout-grid {
    grid-template-columns: 200px 40px 1fr;
  }
}
</style>
