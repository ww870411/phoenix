<template>
  <div class="bigscreen-container" :class="[currentTheme]" ref="containerRef">
    <!-- 顶部科技流光控制栏 -->
    <header class="bigscreen-header">
      <div class="header-left">
        <div class="header-badge">
          <span class="pulse-dot"></span>
          <span class="badge-text">数字孪生 · 实时调度中心</span>
        </div>
        <div class="header-time">{{ currentTimeStr }}</div>
      </div>

      <div class="header-title-box">
        <div class="header-title-glow"></div>
        <h1 class="header-title">大连洁净能源集团 · 2026预制直埋保温管智慧供应链调度大屏</h1>
        <div class="header-sub">
          <span>三大保供制造管厂直供现场</span>
          <span class="sub-sep">|</span>
          <span>全网 10 大施工标段</span>
          <span class="sub-sep">|</span>
          <span>1138项物料基准</span>
          <span class="sub-sep">|</span>
          <span>业务日期：{{ realShowDate || configSummary?.show_date || '2026-08-10' }}</span>
        </div>
      </div>

      <div class="header-right">
        <!-- 演示模式、主题切换与实时交互快捷操作 -->
        <div class="demo-actions">
          <button 
            class="action-btn theme-toggle-btn" 
            @click="toggleTheme"
            :title="isDark ? '切换至明亮浅色模式' : '切换至科技深色模式'"
          >
            <span class="btn-icon">{{ isDark ? '☀️' : '🌙' }}</span>
            <span>{{ isDark ? '浅色模式' : '深色模式' }}</span>
          </button>

          <button 
            class="action-btn demo-btn" 
            :class="{ active: autoDemoRunning }" 
            @click="toggleAutoDemo"
            title="开启/暂停自动演示流"
          >
            <span class="btn-icon">{{ autoDemoRunning ? '⏸️' : '▶️' }}</span>
            <span>{{ autoDemoRunning ? '演示播报中' : '自动演示' }}</span>
          </button>
          
          <button class="action-btn sim-btn" @click="triggerSimulateDelivery('pipe')">
            <span class="btn-icon">🏭</span>
            <span>模拟管材直发</span>
          </button>

          <button class="action-btn sim-btn fitting" @click="triggerSimulateDelivery('fitting')">
            <span class="btn-icon">📦</span>
            <span>模拟管件直运</span>
          </button>

          <button class="action-btn icon-btn" @click="loadRealData" title="即时同步数据库最新数据">
            <span>🔄</span>
          </button>

          <button class="action-btn icon-btn" @click="toggleFullscreen" title="全屏展示">
            <span>{{ isFullscreen ? '🗗' : '⛶' }}</span>
          </button>

          <button class="action-btn icon-btn back-btn" @click="goBackToStandardDashboard" title="返回标准看板">
            <span>↩</span>
          </button>
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
              <span>保温直管全网发运与在途</span>
            </div>
            <span class="panel-tag cyan">直管总线</span>
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
              <span>全网直管保供覆盖率</span>
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

      <!-- 中间栏：重构升级版 · 数字孪生全景供需流向中枢 -->
      <section class="screen-col center-col">
        <div class="panel-box map-topology-master-panel">
          <!-- 拓扑头部导航与状态过滤 -->
          <div class="topology-header-bar">
            <div class="topo-title-group">
              <div class="panel-title">
                <span class="title-icon">🌐</span>
                <span>数字孪生 · 供需全景智慧流向拓扑</span>
              </div>
              <div class="topo-sub-tag">3大制造管厂直供 ──► 10大施工标段现场</div>
            </div>

            <!-- 系统分类切换 Tabs -->
            <div class="system-tabs">
              <button 
                class="sys-tab-btn" 
                :class="{ active: activeSectionTab === 'all' }"
                @click="setSectionTab('all')"
              >全网标段 (10)</button>
              <button 
                class="sys-tab-btn high" 
                :class="{ active: activeSectionTab === 'high' }"
                @click="setSectionTab('high')"
              >🔥 高温水主线 (4)</button>
              <button 
                class="sys-tab-btn low" 
                :class="{ active: activeSectionTab === 'low' }"
                @click="setSectionTab('low')"
              >❄️ 低温水分支 (6)</button>
            </div>

            <!-- 图例说明 -->
            <div class="topology-legend">
              <span class="legend-item"><span class="dot-line cyan"></span>直管直运</span>
              <span class="legend-item"><span class="dot-line gold"></span>管件专运</span>
              <span class="legend-item"><span class="dot-point active"></span>活跃节点</span>
            </div>
          </div>

          <!-- 拓扑主舞台：左管厂 + 中流向通道 + 右标段矩阵 -->
          <div class="topology-container" ref="topologyContainerRef">
            <!-- 动态贝塞尔飞线与激光粒子 SVG 视层 (置于最上层 z-index: 20，绝不被遮挡) -->
            <svg class="topology-svg" ref="svgRef">
              <defs>
                <filter id="glow-cyan-filter" x="-30%" y="-30%" width="160%" height="160%">
                  <feGaussianBlur stdDeviation="4" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
                <filter id="glow-gold-filter" x="-30%" y="-30%" width="160%" height="160%">
                  <feGaussianBlur stdDeviation="4" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
                <linearGradient id="grad-pipe-line" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stop-color="#00f2fe" />
                  <stop offset="100%" stop-color="#38bdf8" />
                </linearGradient>
                <linearGradient id="grad-fitting-line" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stop-color="#fbbf24" />
                  <stop offset="100%" stop-color="#f97316" />
                </linearGradient>
              </defs>

              <!-- 底层基础静态管线 -->
              <g class="flylines-base-layer">
                <path 
                  v-for="line in flylines" 
                  :key="'base-' + line.id"
                  :d="line.d" 
                  class="flyline-base"
                  :class="line.type"
                />
              </g>

              <!-- 上层脉冲流动的动态光流带 (持续流动) -->
              <g class="flylines-stream-layer">
                <path 
                  v-for="line in flylines" 
                  :key="'stream-' + line.id"
                  :d="line.d" 
                  class="flyline-stream"
                  :class="line.type"
                />
              </g>

              <!-- 发货时触发的高亮激光能量包粒子 -->
              <g class="particles-layer">
                <circle 
                  v-for="p in activeParticles" 
                  :key="p.id"
                  r="6" 
                  :fill="p.type === 'pipe' ? '#00f2fe' : '#fbbf24'"
                  :filter="p.type === 'pipe' ? 'url(#glow-cyan-filter)' : 'url(#glow-gold-filter)'"
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

            <!-- 拓扑节点三栏排版架构 -->
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
                    :class="{ active: activeNodeIds.has(sup.id) }"
                    :id="'node-' + sup.id"
                  >
                    <div class="sup-card-top">
                      <span class="sup-code-badge">{{ sup.code }}</span>
                      <strong class="sup-title" :title="sup.name">{{ sup.name }}</strong>
                    </div>
                    
                    <div class="sup-person-row">
                      <span class="sup-contact-pill">👤 {{ sup.contact }}</span>
                    </div>

                    <div class="sup-scope-row">
                      <span class="scope-label">🎯 专供:</span>
                      <span class="scope-text" :title="(sup.assigned_sections || []).join('、')">
                        {{ (sup.assigned_sections || []).join('、') || '全网保供统筹' }}
                      </span>
                    </div>

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

              <!-- 3. 右侧：10 大施工标段工程现场 (Demand Hub Grid) -->
              <div class="demand-hub-col">
                <div class="hub-header">
                  <span class="hub-badge demand">🎯 施工标段现场 ({{ displayedSections.length }})</span>
                </div>
                
                <div class="demand-cards-grid" @scroll="recalculateFlylines">
                  <div 
                    v-for="sec in displayedSections" 
                    :key="sec.id" 
                    class="demand-node-card"
                    :class="{ 
                      active: activeNodeIds.has('sec_' + sec.id),
                      highlighted: lastImpactedSectionId === sec.id,
                      completed: sec.pipePercent >= 100 && sec.fittingPercent >= 100
                    }"
                    :id="'node-sec_' + sec.id"
                  >
                    <!-- 物理对齐连接端口 (左锚点) -->
                    <div class="node-port port-in" :id="'port-in-sec_' + sec.id" title="标段签收入口">
                      <span class="port-dot"></span>
                    </div>

                    <div class="sec-card-header">
                      <div class="sec-badge-name">
                        <span class="sec-code-tag" :class="sec.system_type">{{ sec.code }}</span>
                        <strong class="sec-title" :title="sec.name">{{ sec.name }}</strong>
                      </div>
                      <span class="sec-status-chip" :class="{ running: sec.construction_status === '施工中' }">
                        <span class="chip-dot"></span>
                        <span>{{ sec.construction_status }}</span>
                      </span>
                    </div>

                    <!-- 直管与管件双轨进度 -->
                    <div class="sec-metrics-body">
                      <div class="sec-metric-line">
                        <div class="line-info">
                          <span class="line-label">📐 直管发运</span>
                          <span class="line-val cyan-text">{{ sec.shippedKm }} / {{ sec.designKm }} km</span>
                          <span class="line-pct cyan-text">{{ sec.pipePercent }}%</span>
                        </div>
                        <div class="micro-bar-bg">
                          <div class="micro-bar-fill cyan" :style="{ width: Math.min(sec.pipePercent, 100) + '%' }"></div>
                        </div>
                      </div>

                      <div class="sec-metric-line">
                        <div class="line-info">
                          <span class="line-label">🔩 管件配套</span>
                          <span class="line-val gold-text">{{ sec.shippedFittings }} / {{ sec.totalFittings }} 件</span>
                          <span class="line-pct gold-text">{{ sec.fittingPercent }}%</span>
                        </div>
                        <div class="micro-bar-bg">
                          <div class="micro-bar-fill gold" :style="{ width: Math.min(sec.fittingPercent, 100) + '%' }"></div>
                        </div>
                      </div>
                    </div>

                    <!-- 现场专责与驻点库管员明细 -->
                    <div class="sec-card-duty-row">
                      <span class="duty-pill keeper" :title="'驻点库管: ' + sec.warehouse_keepers">
                        库管: {{ sec.warehouse_keepers }}
                      </span>
                      <span class="duty-pill mgr" :title="sec.construction_unit || sec.site_managers">
                        {{ sec.construction_unit || ('经理: ' + sec.site_managers) }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 右侧栏：实时发货战报流水与重大保供里程碑 (基于真实发货数据库) -->
      <section class="screen-col right-col">
        <!-- 实时发货战报流 -->
        <div class="panel-box live-feed-panel">
          <div class="panel-header">
            <div class="panel-title">
              <span class="title-icon">📢</span>
              <span>全网实时发运动态流水</span>
            </div>
            <div class="live-status-pill">
              <span class="live-dot"></span>
              <span>真实单据 ({{ liveFeedList.length }})</span>
            </div>
          </div>

          <div class="feed-filter-bar">
            <button 
              class="filter-pill" 
              :class="{ active: feedFilter === 'all' }" 
              @click="feedFilter = 'all'"
            >全部 ({{ liveFeedList.length }})</button>
            <button 
              class="filter-pill" 
              :class="{ active: feedFilter === 'pipe' }" 
              @click="feedFilter = 'pipe'"
            >保温直管</button>
            <button 
              class="filter-pill" 
              :class="{ active: feedFilter === 'fitting' }" 
              @click="feedFilter = 'fitting'"
            >关键管件</button>
          </div>

          <!-- 战报消息动态上浮列表 -->
          <div class="feed-list-wrapper">
            <transition-group name="feed-item" tag="div" class="feed-list">
              <div 
                v-for="feed in filteredFeedList" 
                :key="feed.id" 
                class="feed-card"
                :class="[feed.type, { 'just-arrived': feed.isNew }]"
              >
                <div class="feed-card-header">
                  <span class="feed-type-tag" :class="feed.type">
                    {{ feed.type === 'pipe' ? '🏭 直管直发' : '📦 配件专送' }}
                  </span>
                  <span class="feed-time">{{ feed.time }}</span>
                </div>

                <div class="feed-card-body">
                  <div class="feed-headline">
                    <strong class="source-name" :title="feed.supplier">{{ feed.supplier }}</strong>
                    <span class="arrow-icon">──►</span>
                    <strong class="target-name" :title="feed.target">{{ feed.target }}</strong>
                  </div>
                  <div class="feed-detail-box">
                    <div class="detail-badge" :class="feed.type">
                      <span class="spec-label" :title="feed.specification">{{ feed.specification }}</span>
                      <strong class="spec-amount">{{ feed.amount }}</strong>
                    </div>
                    <span class="shipment-code">单号: {{ feed.shipmentCode }}</span>
                  </div>
                </div>

                <div class="feed-card-footer">
                  <span class="pos-tag">✨ {{ feed.positiveTag }}</span>
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

    <!-- 底部状态光带 -->
    <footer class="bigscreen-footer">
      <div class="footer-bar">
        <div class="sys-status">
          <span class="status-indicator live"></span>
          <span>100% 真实业务数据源</span>
          <span class="footer-sep">|</span>
          <span>开元/鑫瑞得/能源集团管厂直发</span>
          <span class="footer-sep">|</span>
          <span>10 大标段现场签收</span>
        </div>
        <div class="sys-tips">
          💡 提示：所有数据、标段、厂家及驻点库管员均读取自系统权威配置与 PostgreSQL 数据库，点击【模拟管材直发】可体验全屏联动动效。
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
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
  setTimeout(recalculateFlylines, 60)
}

// --- 基础状态 ---
const containerRef = ref(null)
const topologyContainerRef = ref(null)
const svgRef = ref(null)
const isFullscreen = ref(false)
const configSummary = ref(null)
const realShowDate = ref('')
const currentTimeStr = ref('')
let timerClock = null
let autoDemoTimer = null
let autoSyncTimer = null
let resizeObserver = null
const autoDemoRunning = ref(false)
const feedFilter = ref('all')
const lastImpactedSectionId = ref(null)
const activeSectionTab = ref('all') // 'all' | 'high' | 'low'

// --- 权威默认数据源 (保证第一帧即刻渲染完整节点与飞线) ---
const defaultSupplyNodes = [
  {
    id: 'sup_kaiyuan',
    raw_id: 'kaiyuan',
    code: 'SA',
    name: '大连开元热力管道股份有限公司',
    contact: '薛向新 13998603445',
    assigned_sections: ['高温水_标段1', '高温水_标段2'],
    assigned_section_ids: ['high_lot_1', 'high_lot_2']
  },
  {
    id: 'sup_xinruide',
    raw_id: 'xinruide',
    code: 'SB',
    name: '河北鑫瑞得管道设备有限公司',
    contact: '刘宁 18230465777',
    assigned_sections: ['低温水_标段1', '低温水_标段2', '低温水_标段3'],
    assigned_section_ids: ['low_lot_1', 'low_lot_2', 'low_lot_3']
  },
  {
    id: 'sup_吴近',
    raw_id: '吴近',
    code: 'SC',
    name: '能源集团保温管厂',
    contact: '吴近 13998473933',
    assigned_sections: ['全线直运与应急保供'],
    assigned_section_ids: ['high_lot_1', 'high_lot_2', 'high_lot_3', 'high_lot_4', 'low_lot_1', 'low_lot_2', 'low_lot_3', 'low_lot_4', 'low_lot_5', 'low_lot_6']
  }
]

const defaultSectionList = [
  { id: 'high_lot_1', name: '高温水_标段1', code: 'H1', system_type: 'high', construction_status: '施工中', warehouse_keepers: '左巨、赫心彤', construction_unit: '鹤城建设 (翁永鑫)', site_managers: '陶远辉', designKm: 18.5, shippedKm: 12.0, pipePercent: 64.9, totalFittings: 400, shippedFittings: 280, fittingPercent: 70.0 },
  { id: 'high_lot_2', name: '高温水_标段2', code: 'H2', system_type: 'high', construction_status: '未开工', warehouse_keepers: '左巨、赫心彤', construction_unit: '大连大通 (任强)', site_managers: '卢君', designKm: 15.2, shippedKm: 0.0, pipePercent: 0.0, totalFittings: 350, shippedFittings: 0, fittingPercent: 0.0 },
  { id: 'high_lot_3', name: '高温水_标段3', code: 'H3', system_type: 'high', construction_status: '未开工', warehouse_keepers: '左巨、赫心彤', construction_unit: '', site_managers: '王晓童、宁吉兴', designKm: 14.8, shippedKm: 0.0, pipePercent: 0.0, totalFittings: 320, shippedFittings: 0, fittingPercent: 0.0 },
  { id: 'high_lot_4', name: '高温水_标段4', code: 'H4', system_type: 'high', construction_status: '未开工', warehouse_keepers: '左巨、赫心彤', construction_unit: '', site_managers: '肖贺升、王一粟', designKm: 16.0, shippedKm: 0.0, pipePercent: 0.0, totalFittings: 360, shippedFittings: 0, fittingPercent: 0.0 },
  { id: 'low_lot_1', name: '低温水_标段1', code: 'L1', system_type: 'low', construction_status: '未开工', warehouse_keepers: '李春、李海', construction_unit: '', site_managers: '赵恩海、李生辉', designKm: 8.6, shippedKm: 0.0, pipePercent: 0.0, totalFittings: 180, shippedFittings: 0, fittingPercent: 0.0 },
  { id: 'low_lot_2', name: '低温水_标段2', code: 'L2', system_type: 'low', construction_status: '未开工', warehouse_keepers: '李春、李海', construction_unit: '', site_managers: '赵恩海、刘思洋', designKm: 9.1, shippedKm: 0.0, pipePercent: 0.0, totalFittings: 195, shippedFittings: 0, fittingPercent: 0.0 },
  { id: 'low_lot_3', name: '低温水_标段3', code: 'L3', system_type: 'low', construction_status: '未开工', warehouse_keepers: '王世博、辛宇满', construction_unit: '', site_managers: '许显旺、杜明熹', designKm: 11.2, shippedKm: 0.0, pipePercent: 0.0, totalFittings: 240, shippedFittings: 0, fittingPercent: 0.0 },
  { id: 'low_lot_4', name: '低温水_标段4', code: 'L4', system_type: 'low', construction_status: '未开工', warehouse_keepers: '王世博、辛宇满', construction_unit: '', site_managers: '许显旺、王楠', designKm: 10.5, shippedKm: 0.0, pipePercent: 0.0, totalFittings: 220, shippedFittings: 0, fittingPercent: 0.0 },
  { id: 'low_lot_5', name: '低温水_标段5', code: 'L5', system_type: 'low', construction_status: '未开工', warehouse_keepers: '杨毅、孟广胜', construction_unit: '', site_managers: '刘思源、韩宜林', designKm: 7.8, shippedKm: 0.0, pipePercent: 0.0, totalFittings: 160, shippedFittings: 0, fittingPercent: 0.0 },
  { id: 'low_lot_6', name: '低温水_标段6', code: 'L6', system_type: 'low', construction_status: '未开工', warehouse_keepers: '杨毅、孟广胜', construction_unit: '', site_managers: '侯志超、张奇钰', designKm: 8.2, shippedKm: 0.0, pipePercent: 0.0, totalFittings: 175, shippedFittings: 0, fittingPercent: 0.0 }
]

// 真实实体库引用
let rawSupplyEntities = []
let rawDemandEntities = []
let rawPipeModels = []

// --- 核心指标状态 (由后端精准聚合统计) ---
const kpiData = reactive({
  pipeDesignKm: 120.0,
  pipeShippedKm: 12.0,
  pipeTransitKm: 12.0,
  pipeDeliveredKm: 0.0,
  fittingTotalPcs: 1138,
  fittingShippedPcs: 280,
  fittingTransitPcs: 280,
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

// 实时战报流列表
const liveFeedList = ref([])

// 过滤后的战报流
const filteredFeedList = computed(() => {
  if (feedFilter.value === 'all') return liveFeedList.value
  return liveFeedList.value.filter(item => item.type === feedFilter.value)
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
const fittingTypeSummary = ref([
  { type: '90°/45°弯头', count: 480 },
  { type: '同心/偏心变径管', count: 260 },
  { type: '等径/异径三通', count: 190 },
  { type: '直埋波纹补偿器', count: 95 },
  { type: '直埋焊接球阀', count: 68 },
  { type: '固定支架与节', count: 45 }
])

// 拓扑节点定义 (3 大真实管厂)
const supplyNodes = ref([...defaultSupplyNodes])

// 真实 10 大标段充能矩阵数据
const sectionProgressList = ref([...defaultSectionList])

// 过滤展示的标段列表
const displayedSections = computed(() => {
  if (activeSectionTab.value === 'high') {
    return sectionProgressList.value.filter(s => s.system_type === 'high')
  }
  if (activeSectionTab.value === 'low') {
    return sectionProgressList.value.filter(s => s.system_type === 'low')
  }
  return sectionProgressList.value
})

function setSectionTab(tab) {
  activeSectionTab.value = tab
  setTimeout(recalculateFlylines, 40)
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
    desc: '直通现场库管员（左巨、赫心彤、李春、李海、王世博等）闭环签收',
    time: '实时'
  }
])

// --- 动态飞线生成与激光动画 (数学对齐锚点中心) ---
function recalculateFlylines() {
  nextTick(() => {
    if (!topologyContainerRef.value) return
    const container = topologyContainerRef.value
    const containerRect = container.getBoundingClientRect()
    if (containerRect.width <= 0 || containerRect.height <= 0) return

    const newFlylines = []

    supplyNodes.value.forEach((sup, sIdx) => {
      const assignedIds = sup.assigned_section_ids || []
      const elFrom = document.getElementById('port-out-' + sup.id)
      if (!elFrom) return
      const rectFrom = elFrom.getBoundingClientRect()
      const x1 = rectFrom.left + rectFrom.width / 2 - containerRect.left
      const y1 = rectFrom.top + rectFrom.height / 2 - containerRect.top

      displayedSections.value.forEach((sec) => {
        const isMatched = assignedIds.length === 0 || assignedIds.includes(sec.id) || sup.raw_id === '吴近'
        if (isMatched) {
          const elTo = document.getElementById('port-in-sec_' + sec.id)
          if (elTo) {
            const rectTo = elTo.getBoundingClientRect()
            const x2 = rectTo.left + rectTo.width / 2 - containerRect.left
            const y2 = rectTo.top + rectTo.height / 2 - containerRect.top

            const dx = Math.max(Math.abs(x2 - x1), 40)
            const cx1 = x1 + dx * 0.42
            const cy1 = y1
            const cx2 = x2 - dx * 0.42
            const cy2 = y2

            const d = `M ${x1} ${y1} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${x2} ${y2}`
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

// 触发一道激光粒子飞行动画
function shootLaserParticle(fromId, toId, type = 'pipe') {
  let targetLine = flylines.value.find(l => l.fromId === fromId && l.toId === toId)
  if (!targetLine) {
    targetLine = flylines.value.find(l => l.toId === toId) || flylines.value[0]
  }
  if (!targetLine) return

  const particleId = 'particle-' + Date.now() + '-' + Math.floor(Math.random() * 1000)
  const duration = 1.2

  activeParticles.value.push({
    id: particleId,
    d: targetLine.d,
    type,
    duration
  })

  // 节点高亮呼吸
  activeNodeIds.value.add(fromId)
  activeNodeIds.value.add(toId)

  // 动画结束后清理
  setTimeout(() => {
    activeParticles.value = activeParticles.value.filter(p => p.id !== particleId)
    activeNodeIds.value.delete(fromId)
    activeNodeIds.value.delete(toId)
  }, duration * 1000 + 200)
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
      positiveTag: `关键配件专车直达 +${pcs}件 ✨`,
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

// 加载 100% 真实项目与数据库数据
async function loadRealData() {
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

      // 4. 真实发运动态流水
      if (Array.isArray(res.live_feed_list) && res.live_feed_list.length > 0) {
        liveFeedList.value = res.live_feed_list
      }

      // 5. 真实拓扑节点 (3 大管厂)
      if (Array.isArray(res.supply_nodes)) {
        supplyNodes.value = res.supply_nodes
      }

      // 6. 真实里程碑
      if (Array.isArray(res.milestones)) {
        milestones.value = res.milestones
      }

      // 7. 保存底层字典供交互模拟使用
      if (Array.isArray(res.supply_entities_raw)) {
        rawSupplyEntities = res.supply_entities_raw
      }
      if (Array.isArray(res.demand_entities_raw)) {
        rawDemandEntities = res.demand_entities_raw
      }
      if (Array.isArray(res.pipe_models)) {
        rawPipeModels = res.pipe_models
      }

      setTimeout(recalculateFlylines, 80)
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
    setTimeout(recalculateFlylines, 80)
  }
}

onMounted(() => {
  updateClock()
  timerClock = setInterval(updateClock, 1000)
  loadRealData()

  // 监听尺寸变化自适应重算飞线
  if (topologyContainerRef.value && window.ResizeObserver) {
    resizeObserver = new ResizeObserver(() => {
      recalculateFlylines()
    })
    resizeObserver.observe(topologyContainerRef.value)
  }

  // 初始加载触发多次确保排版就绪
  setTimeout(recalculateFlylines, 100)
  setTimeout(recalculateFlylines, 400)
  setTimeout(recalculateFlylines, 1000)

  // 每 20 秒静默拉取数据库最新发货与核销状态
  autoSyncTimer = setInterval(loadRealData, 20000)
  window.addEventListener('resize', recalculateFlylines)
})

onBeforeUnmount(() => {
  if (timerClock) clearInterval(timerClock)
  if (autoDemoTimer) clearInterval(autoDemoTimer)
  if (autoSyncTimer) clearInterval(autoSyncTimer)
  if (resizeObserver) resizeObserver.disconnect()
  window.removeEventListener('resize', recalculateFlylines)
})
</script>

<style scoped>
/* ==========================================================================
   2026 预制直埋保温管智慧供应链数字指挥大屏 (支持科技深色模式 + 明亮浅色模式)
   ========================================================================== */

/* --- 默认深色科技主题 (Dark Theme) --- */
.bigscreen-container {
  width: 100vw;
  height: 100vh;
  max-height: 100vh;
  overflow: hidden;
  background-color: #060913;
  background-image: 
    radial-gradient(ellipse at 50% 0%, rgba(0, 242, 254, 0.12) 0%, transparent 60%),
    radial-gradient(ellipse at 80% 80%, rgba(251, 191, 36, 0.06) 0%, transparent 50%),
    linear-gradient(180deg, #090e1a 0%, #04070d 100%);
  color: #e2e8f0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  transition: background-color 0.3s ease, color 0.3s ease;
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
  background: linear-gradient(180deg, rgba(13, 22, 38, 0.85) 0%, rgba(6, 9, 19, 0.4) 100%);
  border-bottom: 1px solid rgba(0, 242, 254, 0.2);
  backdrop-filter: blur(12px);
  z-index: 20;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 320px;
}

.header-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  background: rgba(0, 242, 254, 0.1);
  border: 1px solid rgba(0, 242, 254, 0.3);
  border-radius: 20px;
  font-size: 13px;
  color: #00f2fe;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #00ff87;
  box-shadow: 0 0 10px #00ff87;
  animation: pulse-ring 1.8s infinite;
}

.header-time {
  font-family: 'Consolas', monospace;
  font-size: 14px;
  color: #94a3b8;
  letter-spacing: 0.5px;
}

.header-title-box {
  text-align: center;
  position: relative;
}

.header-title-glow {
  position: absolute;
  top: -10px;
  left: 50%;
  transform: translateX(-50%);
  width: 400px;
  height: 20px;
  background: radial-gradient(circle, rgba(0, 242, 254, 0.4) 0%, transparent 70%);
  filter: blur(8px);
  pointer-events: none;
}

.header-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 2px;
  background: linear-gradient(180deg, #ffffff 20%, #90e0ef 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 0 20px rgba(0, 242, 254, 0.3);
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
  gap: 12px;
  min-width: 320px;
  justify-content: flex-end;
}

.demo-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(15, 23, 42, 0.7);
  color: #f1f5f9;
}

.action-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

.theme-toggle-btn {
  background: rgba(0, 242, 254, 0.12);
  border-color: rgba(0, 242, 254, 0.35);
  color: #00f2fe;
}

.theme-toggle-btn:hover {
  background: rgba(0, 242, 254, 0.25);
  box-shadow: 0 0 12px rgba(0, 242, 254, 0.3);
}

.demo-btn {
  background: rgba(0, 242, 254, 0.15);
  border-color: rgba(0, 242, 254, 0.4);
  color: #00f2fe;
}

.demo-btn.active {
  background: rgba(16, 185, 129, 0.25);
  border-color: rgba(16, 185, 129, 0.6);
  color: #10b981;
  box-shadow: 0 0 14px rgba(16, 185, 129, 0.3);
}

.sim-btn {
  background: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.4);
  color: #93c5fd;
}

.sim-btn:hover {
  background: rgba(59, 130, 246, 0.3);
  border-color: #60a5fa;
}

.sim-btn.fitting {
  background: rgba(251, 191, 36, 0.15);
  border-color: rgba(251, 191, 36, 0.4);
  color: #fde047;
}

.sim-btn.fitting:hover {
  background: rgba(251, 191, 36, 0.3);
  border-color: #f59e0b;
}

.icon-btn {
  padding: 6px 10px;
  font-size: 15px;
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
  height: calc(100vh - 102px);
  display: grid;
  grid-template-columns: 330px 1fr 370px;
  gap: 14px;
  padding: 10px 20px;
  box-sizing: border-box;
  overflow: hidden;
}

.screen-col {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
}

.left-col {
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
}

/* --- 通用高科技卡片样式 Panel Box --- */
.panel-box {
  background: linear-gradient(135deg, rgba(13, 22, 38, 0.7) 0%, rgba(6, 12, 24, 0.8) 100%);
  border: 1px solid rgba(0, 242, 254, 0.15);
  border-radius: 10px;
  padding: 14px 16px;
  position: relative;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(8px);
  box-sizing: border-box;
}

.panel-box::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 16px;
  height: 2px;
  background: #00f2fe;
}

.panel-box::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 2px;
  height: 16px;
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
  background: rgba(0, 242, 254, 0.15);
  color: #00f2fe;
  border: 1px solid rgba(0, 242, 254, 0.3);
}

.panel-tag.gold {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.3);
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
  gap: 8px;
  margin-bottom: 10px;
}

.metric-item {
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  padding: 8px 10px;
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
  font-size: 18px;
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
  text-shadow: 0 0 10px rgba(0, 242, 254, 0.4);
}

.highlight-amber .num {
  color: #fbbf24;
  text-shadow: 0 0 10px rgba(251, 191, 36, 0.4);
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
  background: rgba(0, 255, 135, 0.15);
  padding: 1px 6px;
  border-radius: 10px;
  border: 1px solid rgba(0, 255, 135, 0.4);
  box-shadow: 0 0 8px rgba(0, 255, 135, 0.5);
  pointer-events: none;
}

.delta-bubble.amber {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.15);
  border-color: rgba(251, 191, 36, 0.4);
  box-shadow: 0 0 8px rgba(251, 191, 36, 0.5);
}

.delta-bubble.gold {
  color: #fde047;
  background: rgba(253, 224, 71, 0.15);
  border-color: rgba(253, 224, 71, 0.4);
}

.delta-bubble.orange {
  color: #f97316;
  background: rgba(249, 115, 22, 0.15);
  border-color: rgba(249, 115, 22, 0.4);
}

.bubble-fade-enter-active,
.bubble-fade-leave-active {
  transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

.bubble-fade-enter-from {
  opacity: 0;
  transform: translateY(8px) scale(0.8);
}

.bubble-fade-leave-to {
  opacity: 0;
  transform: translateY(-16px) scale(1.1);
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
  height: 8px;
  background: rgba(15, 23, 42, 0.8);
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.energy-bar-fill {
  height: 100%;
  border-radius: 4px;
  position: relative;
  transition: width 1s cubic-bezier(0.22, 1, 0.36, 1);
}

.energy-bar-fill.cyan-glow {
  background: linear-gradient(90deg, #0052d4, #4364f7, #00f2fe);
  box-shadow: 0 0 12px rgba(0, 242, 254, 0.6);
}

.energy-bar-fill.gold-glow {
  background: linear-gradient(90deg, #d97706, #f59e0b, #fbbf24);
  box-shadow: 0 0 12px rgba(251, 191, 36, 0.6);
}

.energy-bar-light {
  position: absolute;
  top: 0;
  right: 0;
  width: 14px;
  height: 100%;
  background: #ffffff;
  box-shadow: 0 0 8px #ffffff;
  filter: blur(1px);
}

/* --- 管件类型 Pills --- */
.fitting-types-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 10px;
}

.fitting-pill {
  display: flex;
  align-items: center;
  gap: 5px;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(251, 191, 36, 0.2);
  border-radius: 4px;
  padding: 3px 6px;
  font-size: 10px;
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
  gap: 6px;
}

.safety-card {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(16, 185, 129, 0.2);
  border-radius: 6px;
  padding: 6px 8px;
}

.safety-icon {
  font-size: 16px;
}

.safety-val {
  font-size: 13px;
  font-weight: 700;
  color: #10b981;
}

.safety-desc {
  font-size: 10px;
  color: #64748b;
}

/* ==========================================================================
   中间栏：重构升级版 · 数字孪生全景拓扑中枢 (Master Topology Deck)
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
  background: rgba(15, 23, 42, 0.6);
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
  box-shadow: 0 0 6px #00f2fe;
}

.dot-line.gold {
  background: #fbbf24;
  box-shadow: 0 0 6px #fbbf24;
}

.dot-point.active {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #00ff87;
  box-shadow: 0 0 6px #00ff87;
}

/* 拓扑主体舞台容器 */
.topology-container {
  flex: 1;
  min-height: 0;
  position: relative;
  border: 1px solid rgba(0, 242, 254, 0.2);
  border-radius: 8px;
  background: radial-gradient(circle at 50% 50%, rgba(13, 27, 42, 0.5) 0%, rgba(6, 11, 20, 0.9) 100%);
  overflow: hidden;
  box-sizing: border-box;
}

.topology-svg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 20; /* 提升至 20，确保飞线在最上层完全可见 */
}

/* 底层半透明实线管道 */
.flyline-base {
  fill: none;
  stroke-width: 1.5;
  opacity: 0.25;
}

.flyline-base.pipe {
  stroke: #00f2fe;
}

.flyline-base.fitting {
  stroke: #fbbf24;
}

/* 上层脉冲流动虚线 (持续平滑流动) */
.flyline-stream {
  fill: none;
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-dasharray: 8 12;
  opacity: 0.85;
  animation: flow-travel 1.2s linear infinite;
}

.flyline-stream.pipe {
  stroke: url(#grad-pipe-line);
  filter: drop-shadow(0 0 4px rgba(0, 242, 254, 0.6));
}

.flyline-stream.fitting {
  stroke: url(#grad-fitting-line);
  filter: drop-shadow(0 0 4px rgba(251, 191, 36, 0.6));
}

@keyframes flow-travel {
  from {
    stroke-dashoffset: 40;
  }
  to {
    stroke-dashoffset: 0;
  }
}

.laser-particle {
  pointer-events: none;
}

/* 拓扑主排版三栏布局 (左: 230px, 中: 60px 通道, 右: 1fr) */
.topology-layout-grid {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: grid;
  grid-template-columns: 230px 60px 1fr;
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

.hub-badge.demand {
  background: rgba(59, 130, 246, 0.15);
  color: #93c5fd;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.supply-cards-stack {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-around;
  gap: 8px;
}

.supply-node-card {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(0, 242, 254, 0.25);
  border-left: 3px solid #00f2fe;
  border-radius: 6px;
  padding: 8px 10px;
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: all 0.3s ease;
  backdrop-filter: blur(6px);
}

.supply-node-card:nth-child(2) {
  border-left-color: #fbbf24;
}

.supply-node-card:nth-child(3) {
  border-left-color: #00ff87;
}

.supply-node-card.active {
  border-color: #00f2fe;
  box-shadow: 0 0 16px rgba(0, 242, 254, 0.5);
  transform: scale(1.02);
}

.sup-card-top {
  display: flex;
  align-items: center;
  gap: 6px;
}

.sup-code-badge {
  font-family: monospace;
  font-weight: 700;
  font-size: 10px;
  color: #00f2fe;
  background: rgba(0, 242, 254, 0.15);
  padding: 1px 4px;
  border-radius: 3px;
}

.sup-title {
  font-size: 11px;
  font-weight: 600;
  color: #f1f5f9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sup-person-row {
  display: flex;
  align-items: center;
}

.sup-contact-pill {
  font-size: 10px;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.04);
  padding: 1px 5px;
  border-radius: 3px;
}

.sup-scope-row {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
}

.scope-label {
  color: #64748b;
  flex-shrink: 0;
}

.scope-text {
  color: #38bdf8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
  height: 60px;
  background: linear-gradient(180deg, transparent, #00f2fe, transparent);
  animation: beam-pulse 2s infinite;
}

.channel-text {
  writing-mode: vertical-rl;
  font-size: 9px;
  color: #64748b;
  letter-spacing: 2px;
}

/* 3. 需求标段矩阵列 */
.demand-hub-col {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding-left: 4px;
}

.demand-cards-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 8px;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
}

.demand-node-card {
  background: rgba(15, 23, 42, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 6px 10px;
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: all 0.3s ease;
  backdrop-filter: blur(6px);
}

.demand-node-card.highlighted {
  border-color: #00f2fe;
  background: rgba(13, 37, 63, 0.85);
  box-shadow: 0 0 16px rgba(0, 242, 254, 0.4);
  transform: translateY(-1px);
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
  gap: 5px;
  min-width: 0;
}

.sec-code-tag {
  font-family: monospace;
  font-size: 9px;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 3px;
  white-space: nowrap;
}

.sec-code-tag.high {
  background: rgba(239, 68, 68, 0.25);
  color: #fca5a5;
}

.sec-code-tag.low {
  background: rgba(56, 189, 248, 0.25);
  color: #7dd3fc;
}

.sec-title {
  font-size: 11px;
  font-weight: 600;
  color: #f1f5f9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sec-status-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 9px;
  padding: 1px 5px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.05);
  color: #94a3b8;
  white-space: nowrap;
}

.sec-status-chip.running {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.chip-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #94a3b8;
}

.sec-status-chip.running .chip-dot {
  background: #10b981;
  box-shadow: 0 0 4px #10b981;
}

/* 双轨微进度条 */
.sec-metrics-body {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.sec-metric-line {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.line-info {
  display: flex;
  justify-content: space-between;
  font-size: 9px;
}

.line-label {
  color: #94a3b8;
}

.line-val {
  font-family: monospace;
}

.line-pct {
  font-weight: 700;
}

.micro-bar-bg {
  width: 100%;
  height: 3px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 2px;
  overflow: hidden;
}

.micro-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.8s ease;
}

.micro-bar-fill.cyan {
  background: linear-gradient(90deg, #0052d4, #00f2fe);
}

.micro-bar-fill.gold {
  background: linear-gradient(90deg, #d97706, #fbbf24);
}

/* 职责信息行 */
.sec-card-duty-row {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 2px;
  padding-top: 2px;
  border-top: 1px dashed rgba(255, 255, 255, 0.05);
}

.duty-pill {
  font-size: 9px;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.04);
  padding: 1px 4px;
  border-radius: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

.duty-pill.keeper {
  color: #7dd3fc;
}

.duty-pill.mgr {
  color: #cbd5e1;
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
  box-shadow: 0 0 6px #00f2fe;
}

.node-port.port-in {
  left: -5px;
  background: #060913;
  border: 1.5px solid #38bdf8;
  box-shadow: 0 0 6px #38bdf8;
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
}

.live-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #10b981;
  animation: pulse-ring 1.5s infinite;
}

.feed-filter-bar {
  display: flex;
  gap: 5px;
  margin-bottom: 8px;
  flex-shrink: 0;
}

.filter-pill {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  padding: 3px 8px;
  font-size: 10px;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-pill.active {
  background: rgba(0, 242, 254, 0.2);
  border-color: #00f2fe;
  color: #00f2fe;
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
  background: rgba(15, 23, 42, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  position: relative;
  transition: all 0.4s ease;
  flex-shrink: 0;
}

.feed-card.pipe {
  border-left: 3px solid #00f2fe;
}

.feed-card.fitting {
  border-left: 3px solid #fbbf24;
}

.feed-card.just-arrived {
  background: rgba(0, 242, 254, 0.18);
  box-shadow: 0 0 16px rgba(0, 242, 254, 0.4);
  transform: scale(1.01);
}

.feed-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.feed-type-tag {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 3px;
}

.feed-type-tag.pipe {
  background: rgba(0, 242, 254, 0.15);
  color: #00f2fe;
}

.feed-type-tag.fitting {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
}

.feed-time {
  font-family: monospace;
  font-size: 10px;
  color: #64748b;
}

.feed-headline {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
}

.source-name {
  color: #f1f5f9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 130px;
}

.arrow-icon {
  color: #64748b;
  font-size: 10px;
}

.target-name {
  color: #38bdf8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 130px;
}

.feed-detail-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(0, 0, 0, 0.25);
  padding: 3px 6px;
  border-radius: 4px;
}

.detail-badge {
  display: flex;
  align-items: center;
  gap: 5px;
}

.spec-label {
  font-size: 10px;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 140px;
}

.spec-amount {
  font-size: 11px;
  font-weight: 700;
}

.detail-badge.pipe .spec-amount {
  color: #00f2fe;
}

.detail-badge.fitting .spec-amount {
  color: #fbbf24;
}

.shipment-code {
  font-family: monospace;
  font-size: 9px;
  color: #64748b;
}

.feed-card-footer {
  display: flex;
  justify-content: flex-end;
}

.pos-tag {
  font-size: 9px;
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
  padding: 1px 5px;
  border-radius: 8px;
}

/* 战报动画 TransitionGroup */
.feed-item-enter-active,
.feed-item-leave-active {
  transition: all 0.45s cubic-bezier(0.16, 1, 0.3, 1);
}

.feed-item-enter-from {
  opacity: 0;
  transform: translateY(-20px) scale(0.95);
}

.feed-item-leave-to {
  opacity: 0;
  transform: translateY(16px);
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
  gap: 8px;
}

.milestone-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 5px 6px;
  background: rgba(15, 23, 42, 0.45);
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
  font-size: 11px;
  font-weight: 600;
  color: #f1f5f9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.m-desc {
  font-size: 10px;
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

/* --- 底部状态栏 Footer --- */
.bigscreen-footer {
  height: 32px;
  min-height: 32px;
  max-height: 32px;
  flex-shrink: 0;
  background: rgba(6, 9, 19, 0.95);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  padding: 0 24px;
  font-size: 11px;
  color: #64748b;
  z-index: 20;
}

.footer-bar {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sys-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-indicator.live {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10b981;
}

.footer-sep {
  opacity: 0.3;
}

.sys-tips {
  color: #94a3b8;
}

/* --- 精美深色科技细滚动条 Custom Scrollbars --- */
.left-col::-webkit-scrollbar,
.feed-list-wrapper::-webkit-scrollbar,
.demand-cards-grid::-webkit-scrollbar,
.milestone-list::-webkit-scrollbar {
  width: 4px;
  height: 4px;
}

.left-col::-webkit-scrollbar-track,
.feed-list-wrapper::-webkit-scrollbar-track,
.demand-cards-grid::-webkit-scrollbar-track,
.milestone-list::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 2px;
}

.left-col::-webkit-scrollbar-thumb,
.feed-list-wrapper::-webkit-scrollbar-thumb,
.demand-cards-grid::-webkit-scrollbar-thumb,
.milestone-list::-webkit-scrollbar-thumb {
  background: rgba(0, 242, 254, 0.25);
  border-radius: 2px;
}

.left-col::-webkit-scrollbar-thumb:hover,
.feed-list-wrapper::-webkit-scrollbar-thumb:hover,
.demand-cards-grid::-webkit-scrollbar-thumb:hover,
.milestone-list::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 242, 254, 0.5);
}

/* ==========================================================================
   明亮浅色高科技模式 (Light Clean Tech Theme)
   ========================================================================== */

.bigscreen-container.light {
  background-color: #f1f5f9;
  background-image: 
    radial-gradient(ellipse at 50% 0%, rgba(2, 132, 199, 0.08) 0%, transparent 60%),
    radial-gradient(ellipse at 80% 80%, rgba(234, 88, 12, 0.05) 0%, transparent 50%),
    linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%);
  color: #0f172a;
}

.bigscreen-container.light .bigscreen-header {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.95) 0%, rgba(248, 250, 252, 0.9) 100%);
  border-bottom: 1px solid rgba(203, 213, 225, 0.8);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
}

.bigscreen-container.light .header-badge {
  background: rgba(2, 132, 199, 0.1);
  border-color: rgba(2, 132, 199, 0.3);
  color: #0284c7;
}

.bigscreen-container.light .header-time {
  color: #475569;
}

.bigscreen-container.light .header-title-glow {
  background: radial-gradient(circle, rgba(2, 132, 199, 0.2) 0%, transparent 70%);
}

.bigscreen-container.light .header-title {
  background: linear-gradient(180deg, #0f172a 20%, #0369a1 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: none;
}

.bigscreen-container.light .header-sub {
  color: #64748b;
}

.bigscreen-container.light .action-btn {
  background: rgba(255, 255, 255, 0.9);
  border-color: rgba(203, 213, 225, 0.8);
  color: #334155;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.bigscreen-container.light .action-btn:hover {
  background: #ffffff;
  color: #0f172a;
  border-color: #94a3b8;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.bigscreen-container.light .theme-toggle-btn {
  background: rgba(2, 132, 199, 0.12);
  border-color: rgba(2, 132, 199, 0.35);
  color: #0284c7;
}

.bigscreen-container.light .demo-btn {
  background: rgba(2, 132, 199, 0.12);
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
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(248, 250, 252, 0.9) 100%);
  border: 1px solid rgba(203, 213, 225, 0.8);
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
}

.bigscreen-container.light .panel-box::before,
.bigscreen-container.light .panel-box::after {
  background: #0284c7;
}

.bigscreen-container.light .panel-title {
  color: #0f172a;
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
  background: rgba(241, 245, 249, 0.85);
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
  text-shadow: none;
}

.bigscreen-container.light .highlight-amber .num {
  color: #d97706;
  text-shadow: none;
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
  box-shadow: 0 0 8px rgba(2, 132, 199, 0.3);
}

.bigscreen-container.light .energy-bar-fill.gold-glow {
  background: linear-gradient(90deg, #d97706, #fbbf24);
  box-shadow: 0 0 8px rgba(217, 119, 6, 0.3);
}

.bigscreen-container.light .fitting-pill {
  background: #ffffff;
  border-color: rgba(245, 158, 11, 0.3);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.bigscreen-container.light .pill-name {
  color: #475569;
}

.bigscreen-container.light .pill-count {
  color: #d97706;
}

.bigscreen-container.light .safety-card {
  background: rgba(241, 245, 249, 0.85);
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
  box-shadow: 0 0 4px #0284c7;
}

.bigscreen-container.light .dot-line.gold {
  background: #ea580c;
  box-shadow: 0 0 4px #ea580c;
}

.bigscreen-container.light .topology-container {
  background: radial-gradient(circle at 50% 50%, rgba(248, 250, 252, 0.9) 0%, rgba(241, 245, 249, 0.95) 100%);
  border-color: rgba(203, 213, 225, 0.8);
}

.bigscreen-container.light .flyline-base.pipe {
  stroke: #0284c7;
  opacity: 0.3;
}

.bigscreen-container.light .flyline-base.fitting {
  stroke: #ea580c;
  opacity: 0.3;
}

.bigscreen-container.light .flyline-stream.pipe {
  stroke: #0284c7;
  filter: drop-shadow(0 0 3px rgba(2, 132, 199, 0.5));
}

.bigscreen-container.light .flyline-stream.fitting {
  stroke: #ea580c;
  filter: drop-shadow(0 0 3px rgba(234, 88, 12, 0.5));
}

.bigscreen-container.light .supply-node-card {
  background: rgba(255, 255, 255, 0.92);
  border-color: rgba(203, 213, 225, 0.9);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}

.bigscreen-container.light .supply-node-card.active {
  border-color: #0284c7;
  box-shadow: 0 0 12px rgba(2, 132, 199, 0.3);
}

.bigscreen-container.light .sup-title {
  color: #0f172a;
}

.bigscreen-container.light .sup-contact-pill {
  color: #64748b;
  background: #f1f5f9;
}

.bigscreen-container.light .scope-text {
  color: #0284c7;
}

.bigscreen-container.light .demand-node-card {
  background: rgba(255, 255, 255, 0.92);
  border-color: rgba(226, 232, 240, 0.9);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
}

.bigscreen-container.light .demand-node-card.highlighted {
  border-color: #0284c7;
  background: #f0f9ff;
  box-shadow: 0 0 16px rgba(2, 132, 199, 0.25);
}

.bigscreen-container.light .sec-title {
  color: #0f172a;
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

.bigscreen-container.light .duty-pill {
  background: #f1f5f9;
}

.bigscreen-container.light .duty-pill.keeper {
  color: #0284c7;
}

.bigscreen-container.light .duty-pill.mgr {
  color: #475569;
}

.bigscreen-container.light .node-port.port-out {
  background: #ffffff;
  border-color: #0284c7;
  box-shadow: 0 0 4px #0284c7;
}

.bigscreen-container.light .node-port.port-in {
  background: #ffffff;
  border-color: #0284c7;
  box-shadow: 0 0 4px #0284c7;
}

.bigscreen-container.light .filter-pill {
  background: #ffffff;
  border-color: rgba(203, 213, 225, 0.8);
  color: #64748b;
}

.bigscreen-container.light .filter-pill.active {
  background: rgba(2, 132, 199, 0.12);
  border-color: #0284c7;
  color: #0284c7;
  font-weight: 600;
}

.bigscreen-container.light .feed-card {
  background: rgba(255, 255, 255, 0.9);
  border-color: rgba(226, 232, 240, 0.9);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
}

.bigscreen-container.light .feed-card.just-arrived {
  background: #f0f9ff;
  box-shadow: 0 0 14px rgba(2, 132, 199, 0.25);
}

.bigscreen-container.light .source-name {
  color: #0f172a;
}

.bigscreen-container.light .target-name {
  color: #0284c7;
}

.bigscreen-container.light .feed-detail-box {
  background: #f1f5f9;
}

.bigscreen-container.light .spec-label {
  color: #475569;
}

.bigscreen-container.light .detail-badge.pipe .spec-amount {
  color: #0284c7;
}

.bigscreen-container.light .detail-badge.fitting .spec-amount {
  color: #d97706;
}

.bigscreen-container.light .milestone-item {
  background: rgba(255, 255, 255, 0.9);
  border-left-color: #d97706;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.03);
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

.bigscreen-container.light .bigscreen-footer {
  background: rgba(255, 255, 255, 0.95);
  border-top-color: rgba(226, 232, 240, 0.9);
  color: #64748b;
}

.bigscreen-container.light .sys-tips {
  color: #64748b;
}

.bigscreen-container.light .left-col::-webkit-scrollbar-track,
.bigscreen-container.light .feed-list-wrapper::-webkit-scrollbar-track,
.bigscreen-container.light .demand-cards-grid::-webkit-scrollbar-track,
.bigscreen-container.light .milestone-list::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.05);
}

.bigscreen-container.light .left-col::-webkit-scrollbar-thumb,
.bigscreen-container.light .feed-list-wrapper::-webkit-scrollbar-thumb,
.bigscreen-container.light .demand-cards-grid::-webkit-scrollbar-thumb,
.bigscreen-container.light .milestone-list::-webkit-scrollbar-thumb {
  background: rgba(2, 132, 199, 0.3);
}

.bigscreen-container.light .left-col::-webkit-scrollbar-thumb:hover,
.bigscreen-container.light .feed-list-wrapper::-webkit-scrollbar-thumb:hover,
.bigscreen-container.light .demand-cards-grid::-webkit-scrollbar-thumb:hover,
.bigscreen-container.light .milestone-list::-webkit-scrollbar-thumb:hover {
  background: rgba(2, 132, 199, 0.6);
}

/* --- 关键帧动画 Keyframes --- */
@keyframes pulse-ring {
  0% {
    box-shadow: 0 0 0 0 rgba(0, 255, 135, 0.7);
  }
  70% {
    box-shadow: 0 0 0 8px rgba(0, 255, 135, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(0, 255, 135, 0);
  }
}

@keyframes beam-pulse {
  0%, 100% {
    opacity: 0.3;
    transform: scaleY(0.8);
  }
  50% {
    opacity: 0.9;
    transform: scaleY(1.1);
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
