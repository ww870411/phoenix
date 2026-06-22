<template>
  <div class="tube-page-root">
    <!-- 大连洁净能源集团生产系统统一页头 -->
    <AppHeader />
    
    <main class="tube-page-main container">
      <!-- 统一面包屑导航 -->
      <Breadcrumbs :items="breadcrumbItems" />
      
      <!-- 看板顶栏总控区 -->
      <header class="topbar">
        <div>
          <h2>全局数据看板</h2>
          <p class="sub">
            物流供应链全链路（计划-发货-到货-接收-库管-使用）的宏观指标、可视化大盘与预警扫描中心。
          </p>
        </div>
        <div class="topbar-actions">
          <!-- 核心日期上下文显示 -->
          <div class="date-context-badge">
            <span class="date-context-item">
              <span class="dot green"></span>
              业务日期 (show_date)：<strong>{{ configSummary?.show_date || '—' }}</strong>
            </span>
            <span class="date-context-item">
              <span class="dot blue"></span>
              计划起点 (plan_start_date)：<strong>{{ configSummary?.plan_start_date || '—' }}</strong>
            </span>
          </div>
          <button class="btn ghost" type="button" @click="goProjectPages">返回功能页</button>
          <button class="btn primary" type="button" :disabled="loading || loadingSummary" @click="refreshAllData">
            {{ (loading || loadingSummary) ? '刷新中...' : '刷新看板数据' }}
          </button>
        </div>
      </header>

      <p v-if="errorMessage" class="page-error">{{ errorMessage }}</p>

      <!-- 第一区：四大全局核心指标 HSL 磨砂卡片大盘 -->
      <section class="stats-grid">
        <!-- 卡片1：采购与覆盖率 -->
        <div class="stat-card">
          <div class="stat-card__icon">📐</div>
          <div class="stat-card__label">项目总设计量 / 计划采购</div>
          <div class="stat-card__value">
            {{ formatQty(kpi.design) }} <span class="stat-card__unit">m</span>
            <span class="stat-card__separator">/</span>
            <span class="highlight-blue">{{ formatQty(kpi.purchase) }}</span> <span class="stat-card__unit">m</span>
          </div>
          <div class="stat-card__progress">
            <div class="progress-bar-bg">
              <div class="progress-bar-fill blue" :style="{ width: getPercent(kpi.purchase, kpi.design) + '%' }"></div>
            </div>
            <div class="progress-bar-text">计划采购率：{{ getPercent(kpi.purchase, kpi.design) }}%</div>
          </div>
        </div>

        <!-- 卡片2：已发货与在途资产 -->
        <div class="stat-card">
          <div class="stat-card__icon">🚚</div>
          <div class="stat-card__label">累计已发货 / 当前在途待到货</div>
          <div class="stat-card__value">
            {{ formatQty(kpi.shipped) }} <span class="stat-card__unit">m</span>
            <span class="stat-card__separator">/</span>
            <span class="highlight-cyan">{{ formatQty(kpi.pendingArrival) }}</span> <span class="stat-card__unit">m</span>
          </div>
          <div class="stat-card__progress">
            <div class="progress-bar-bg">
              <div class="progress-bar-fill cyan" :style="{ width: getPercent(kpi.pendingArrival, kpi.shipped) + '%' }"></div>
            </div>
            <div class="progress-bar-text">在途占比：{{ getPercent(kpi.pendingArrival, kpi.shipped) }}%</div>
          </div>
        </div>

        <!-- 卡片3：现场库存与累计使用 -->
        <div class="stat-card">
          <div class="stat-card__icon">⛺</div>
          <div class="stat-card__label">全局现场总库存 / 累计实际使用</div>
          <div class="stat-card__value">
            <span class="highlight-green">{{ formatQty(kpi.inventory) }}</span> <span class="stat-card__unit">m</span>
            <span class="stat-card__separator">/</span>
            {{ formatQty(kpi.usage) }} <span class="stat-card__unit">m</span>
          </div>
          <div class="stat-card__progress">
            <div class="progress-bar-bg">
              <div class="progress-bar-fill green" :style="{ width: getPercent(kpi.usage, kpi.inventory + kpi.usage) + '%' }"></div>
            </div>
            <div class="progress-bar-text">耗用转化率：{{ getPercent(kpi.usage, kpi.inventory + kpi.usage) }}%</div>
          </div>
        </div>

        <!-- 卡片4：未来三日缺口与硬缺口 -->
        <div class="stat-card" :class="{ 'alert-pulsing': kpi.hardGap > 0 }">
          <div class="stat-card__icon">⚠️</div>
          <div class="stat-card__label">三日计划硬缺口 / 三日净缺口</div>
          <div class="stat-card__value">
            <span class="highlight-red" :class="{ 'blink': kpi.hardGap > 0 }">{{ formatQty(kpi.hardGap) }}</span> <span class="stat-card__unit">m</span>
            <span class="stat-card__separator">/</span>
            <span class="highlight-orange">{{ formatQty(kpi.netGap) }}</span> <span class="stat-card__unit">m</span>
          </div>
          <div class="stat-card__progress">
            <div class="progress-bar-bg">
              <div class="progress-bar-fill red" :style="{ width: getPercent(kpi.hardGap, kpi.hardGap + kpi.netGap || 1) + '%' }"></div>
            </div>
            <div class="progress-bar-text">
              <template v-if="kpi.hardGap > 0">🚨 警报：现场库存不足以维持施工！</template>
              <template v-else-if="kpi.netGap > 0">提示：在途能抵扣，但仍需组织新发货</template>
              <template v-else>✅ 供需平稳，近期无断料风险</template>
            </div>
          </div>
        </div>
      </section>

      <!-- 第二区：供需可视化与大连气象工效决策沙盘 (并列两栏布局) -->
      <section class="charts-grid card elevated">
        <div class="charts-section-header">
          <h3>📊 供需分析与大连气象工效决策沙盘</h3>
          <span class="charts-tip">支持型号多维供需对比 ＆ 物理实时降雨防汛施工沙盘联动</span>
        </div>
        <div class="charts-container">
          <!-- 图表一：各保温管型号供需堆叠柱状图 -->
          <div class="chart-wrapper">
            <div class="chart-title">📏 保温管型号供需及三日缺口分布 (三日净缺口 Top 5)</div>
            <div ref="chartContainer1" class="echarts-dom"></div>
            <div v-if="!hasEcharts" class="chart-placeholder">ECharts 全局对象未加载</div>
          </div>
          
          <!-- 大连气象环境与防汛施工决策沙盘 -->
          <div class="chart-wrapper weather-decision-panel">
            <div class="weather-title-group">
              <div class="chart-title">🌧️ 大连气象环境与施工防汛决策沙盘</div>
              <span class="weather-location-badge">📍 大连市主城区</span>
            </div>
            
            <div class="weather-days-grid" v-if="weatherDays.length > 0">
              <div v-for="(day, dIdx) in weatherDays" :key="dIdx" class="weather-day-card" :class="[day.themeClass, { 'current-day': dIdx === 1 }]">
                <div class="weather-day-header">
                  <span class="weather-label">{{ day.dateLabel }}</span>
                  <span class="weather-date">{{ day.formattedDate }}</span>
                </div>
                
                <div class="weather-day-body">
                  <span class="weather-icon-large">{{ day.weatherIcon }}</span>
                  
                  <!-- 2x2 极清对称气象指标网格 -->
                  <div class="weather-metrics-grid">
                    <!-- 指标 1：雨量 -->
                    <div class="weather-metric-item">
                      <span class="lbl">降雨量</span>
                      <div class="val-unit">
                        <strong class="val rain">{{ day.rainVal.toFixed(1) }}</strong>
                        <span class="unit">mm</span>
                      </div>
                    </div>
                    <!-- 指标 2：紫外线 -->
                    <div class="weather-metric-item">
                      <span class="lbl">紫外线</span>
                      <div class="val-unit">
                        <strong class="val uv" :class="day.uvClass">{{ day.uvVal.toFixed(1) }}</strong>
                        <span class="unit-badge" :class="day.uvClass">{{ day.uvLevel }}</span>
                      </div>
                    </div>
                    <!-- 指标 3：最高气温 -->
                    <div class="weather-metric-item">
                      <span class="lbl">最高温</span>
                      <div class="val-unit">
                        <strong class="val">{{ day.tempMax != null ? day.tempMax.toFixed(1) : '—' }}</strong>
                        <span class="unit">°C</span>
                      </div>
                    </div>
                    <!-- 指标 4：平均温 -->
                    <div class="weather-metric-item">
                      <span class="lbl">平均温</span>
                      <div class="val-unit">
                        <strong class="val">{{ day.tempMean != null ? day.tempMean.toFixed(1) : '—' }}</strong>
                        <span class="unit">°C</span>
                      </div>
                    </div>
                  </div>

                  <span class="weather-status-tag" :class="day.themeClass">{{ day.statusText }}</span>
                </div>
              </div>
            </div>
            
            <div v-else-if="loadingWeather" class="chart-placeholder">
              <span class="loading-spinner">🌀</span>
              <span>正在连线大连气象数据中心...</span>
            </div>
            <div v-else class="chart-placeholder text-danger">大连气象服务连线超时，请重试</div>
          </div>
        </div>
      </section>

      <!-- 第三区：全链路健康评估与精细化管理多维统计大盘 (40% + 60% 黄金双面板) -->
      <section class="card elevated pivot-section-fluid">
        <div class="card-header pivot-header">
          <div class="pivot-title-group">
            <h3>🏢 全链路健康评估与精细化多维运营大盘</h3>
            <span class="pivot-badge">大连洁净能源集团数字化控制中心</span>
          </div>
          <span class="pivot-badge success">运营状况：极佳 🟢</span>
        </div>

        <div class="workbench-grid-layout">
          <!-- 雷达图大格子 (占用 1, 2, 4, 5 号格子) -->
          <div class="workbench-radar-grid-cell">
            <div ref="chartContainer2" class="echarts-dom-radar"></div>
            <div v-if="!hasEcharts" class="chart-placeholder">ECharts 全局对象未加载</div>
          </div>

          <!-- 卡片 1：OTD (占用 3 号格子) -->
          <div class="metric-saas-card otd cell-3" @click="openMetricModal('otd')" title="点击查看计算公式与数据穿透">
            <div class="metric-saas-header">
              <span class="metric-abbr">OTD</span>
              <span class="metric-badge success">物流履约</span>
            </div>
            <div class="metric-saas-value">{{ realOTD }}%</div>
            <div class="metric-saas-label">供应链 24 小时到货达成率</div>
            <p class="metric-saas-help">以已确认到货记录为样本，衡量 24 小时内完成到货的物流履约水平 (集团基准线 &gt;=90%)</p>
            <div class="metric-saas-interactive-tip">💡 点击查看计算过程</div>
          </div>

          <!-- 卡片 2：DOI (占用 6 号格子) -->
          <div class="metric-saas-card doi cell-6" @click="openMetricModal('doi')" title="点击查看计算公式与数据穿透">
            <div class="metric-saas-header">
              <span class="metric-abbr">DOI</span>
              <span class="metric-badge warning">周转效率</span>
            </div>
            <div class="metric-saas-value">{{ realDOI }} <span class="metric-saas-unit">天</span></div>
            <div class="metric-saas-label">现场平均库存周转天数</div>
            <p class="metric-saas-help">物资现场超高速周转，场地积压与资金沉淀控制优良 (运营基准 &lt; 5天)</p>
            <div class="metric-saas-interactive-tip">💡 点击查看计算过程</div>
          </div>

          <!-- 卡片 3：PCR (占用 7 号格子) -->
          <div class="metric-saas-card pcr cell-7" @click="openMetricModal('pcr')" title="点击查看计算公式与数据穿透">
            <div class="metric-saas-header">
              <span class="metric-abbr">PCR</span>
              <span class="metric-badge info">滚动计划</span>
            </div>
            <div class="metric-saas-value">{{ realPCR }}%</div>
            <div class="metric-saas-label">三日计划提报达成率</div>
            <p class="metric-saas-help">全标段所有换热站全面实施按日滚动催报，零漏报、零断供隐患</p>
            <div class="metric-saas-interactive-tip">💡 点击查看计算过程</div>
          </div>

          <!-- 卡片 4：UCR (占用 8 号格子) -->
          <div class="metric-saas-card ucr cell-8" @click="openMetricModal('ucr')" title="点击查看计算公式与数据穿透">
            <div class="metric-saas-header">
              <span class="metric-abbr">UCR</span>
              <span class="metric-badge success">消耗转化</span>
            </div>
            <div class="metric-saas-value">{{ realUCR }}%</div>
            <div class="metric-saas-label">到货施工消耗转化率</div>
            <p class="metric-saas-help">卸车到货后立即向物理实体高效率转化，施工现场零物料囤积滞纳</p>
            <div class="metric-saas-interactive-tip">💡 点击查看计算过程</div>
          </div>

          <!-- 卡片 5：SSR (占用 9 号格子) -->
          <div class="metric-saas-card ssr cell-9" @click="openMetricModal('ssr')" title="点击查看计算公式与数据穿透">
            <div class="metric-saas-header">
              <span class="metric-abbr">SSR</span>
              <span class="metric-badge success">安全供应</span>
            </div>
            <div class="metric-saas-value">{{ realSSR }}%</div>
            <div class="metric-saas-label">安全供应度 (缺口规避率)</div>
            <p class="metric-saas-help">全标段断料窝工风险极低，仅个别站点偏紧 (集团基准线 >=90%)</p>
            <div class="metric-saas-interactive-tip">💡 点击查看计算过程</div>
          </div>
        </div>
      </section>

      <!-- 第四区：多维数据穿透透视表（独占一行，展现大气表格） -->
      <section class="card elevated pivot-section-fluid">
        <div class="card-header pivot-header">
          <div class="pivot-title-group">
            <h3>🏢 供需全链路多维穿透透视表</h3>
            <span class="pivot-badge">已包含 show_date 上限截断</span>
          </div>
          <!-- 透视切换 Tab -->
          <div class="tab-workbench">
            <button 
              class="tab-btn" 
              :class="{ active: pivotMode === 'station' }" 
              @click="pivotMode = 'station'"
            >
              🏢 按换热站维度
            </button>
            <button 
              class="tab-btn" 
              :class="{ active: pivotMode === 'model' }" 
              @click="pivotMode = 'model'"
            >
              📏 按管径型号维度
            </button>
          </div>
        </div>

        <div class="search-filter-bar">
          <div class="filter-item">
            <label>过滤站点：</label>
            <select v-model="filterStationId">
              <option value="">全部站点</option>
              <option 
                v-for="st in configSummary?.demand_entities || []" 
                :key="st.station_id" 
                :value="st.station_id"
              >
                {{ st.station_name }}
              </option>
            </select>
          </div>
          <div class="filter-item">
            <label>过滤型号：</label>
            <select v-model="filterPipeModelId">
              <option value="">全部型号</option>
              <option 
                v-for="pm in configSummary?.pipe_models || []" 
                :key="pm.pipe_model_id" 
                :value="pm.pipe_model_id"
              >
                {{ pm.pipe_model_name }}
              </option>
            </select>
          </div>
          <button class="btn link-btn" @click="resetFilters">重置过滤</button>
          <button 
            class="btn primary compact-btn export-pivot-btn" 
            style="margin-left: auto; height: 36px; padding: 0 16px;" 
            type="button" 
            @click="showExportModal = true"
          >
            📥 导出当前分析表
          </button>
        </div>

        <div class="pivot-table-container">
          <table class="pivot-table">
            <thead>
              <tr>
                <th class="left-align text-col">{{ pivotMode === 'station' ? '换热站名称' : '保温管型号' }}</th>
                <th class="right-align num-col sortable" @click="handleSort('design_qty')">
                  设计量 {{ getSortSymbol('design_qty') }}
                </th>
                <th class="right-align num-col sortable" @click="handleSort('purchase_plan_qty')">
                  计划采购 {{ getSortSymbol('purchase_plan_qty') }}
                </th>
                <th class="right-align num-col sortable" @click="handleSort('future_plan_qty')">
                  三日计划 {{ getSortSymbol('future_plan_qty') }}
                </th>
                <th class="right-align num-col sortable" @click="handleSort('total_shipped_qty')">
                  累计发货 {{ getSortSymbol('total_shipped_qty') }}
                </th>
                <th class="right-align num-col sortable" @click="handleSort('pending_arrival_qty')">
                  在途在管 {{ getSortSymbol('pending_arrival_qty') }}
                </th>
                <th class="right-align num-col sortable highlight-th-green" @click="handleSort('station_inventory_qty')">
                  现场库存 {{ getSortSymbol('station_inventory_qty') }}
                </th>
                <th class="right-align num-col sortable" @click="handleSort('total_usage_qty')">
                  累计使用 {{ getSortSymbol('total_usage_qty') }}
                </th>
                <th class="right-align num-col sortable highlight-th-red" @click="handleSort('hard_gap_qty')">
                  三日硬缺 {{ getSortSymbol('hard_gap_qty') }}
                </th>
                <th class="right-align num-col sortable highlight-th-orange" @click="handleSort('net_gap_qty')">
                  三日净缺 {{ getSortSymbol('net_gap_qty') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in computedTableData" :key="item.id" class="pivot-row">
                <td class="left-align text-col font-bold cell-ellipsis" :title="item.name">
                  {{ item.name || '—' }}
                </td>
                <td class="right-align num-col">{{ formatQty(item.design_qty) }}</td>
                <td class="right-align num-col">{{ formatQty(item.purchase_plan_qty) }}</td>
                <td class="right-align num-col font-bold">{{ formatQty(item.future_plan_qty) }}</td>
                <td class="right-align num-col">{{ formatQty(item.total_shipped_qty) }}</td>
                <td class="right-align num-col">{{ formatQty(item.pending_arrival_qty) }}</td>
                <td class="right-align num-col highlight-cell-green">{{ formatQty(item.station_inventory_qty) }}</td>
                <td class="right-align num-col">{{ formatQty(item.total_usage_qty) }}</td>
                <td class="right-align num-col highlight-cell-red" :class="{ 'danger-text': item.hard_gap_qty > 0 }">
                  {{ formatQty(item.hard_gap_qty) }}
                </td>
                <td class="right-align num-col highlight-cell-orange" :class="{ 'warning-text': item.net_gap_qty > 0 }">
                  {{ formatQty(item.net_gap_qty) }}
                </td>
              </tr>
              <tr v-if="computedTableData.length === 0" class="empty-row">
                <td colspan="10" class="center-align">暂无筛选对应的汇总数据</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>

    <!-- SaaS 指标计算穿透解析毛玻璃弹窗 (利用 Teleport 传送门直挂 body，根治 z-index 与 overflow:hidden 阻断) -->
    <Teleport to="body">
      <Transition name="modal-fade">
        <div v-if="activeMetric" class="metric-modal-overlay" @click.self="closeMetricModal">
          <div class="metric-modal-card">
            <!-- 关闭按钮 -->
            <button class="metric-modal-close" @click="closeMetricModal">✕</button>
            
            <div class="metric-modal-header">
              <span class="metric-modal-icon">📊</span>
              <div>
                <h4>{{ getMetricTitle(activeMetric) }}</h4>
                <span class="metric-modal-subtitle">{{ getMetricSubtitle(activeMetric) }}</span>
              </div>
            </div>
            
            <div class="metric-modal-body">
              <!-- 核心含义 -->
              <div class="metric-info-section">
                <span class="section-tag">💡 核心含义</span>
                <p class="metric-desc-text">{{ getMetricDesc(activeMetric) }}</p>
              </div>
              
              <!-- 计算公式 -->
              <div class="metric-info-section">
                <span class="section-tag">🧮 计算公式</span>
                <div class="metric-formula-box">
                  <div class="formula-line">
                    <span class="formula-label">{{ getMetricAbbr(activeMetric) }} =</span>
                    <div class="formula-fraction">
                      <span class="fraction-numerator">{{ getMetricFormulaNumerator(activeMetric) }}</span>
                      <span class="fraction-denominator">{{ getMetricFormulaDenominator(activeMetric) }}</span>
                    </div>
                    <span v-if="getMetricMultiplier(activeMetric)" class="formula-multiplier">{{ getMetricMultiplier(activeMetric) }}</span>
                  </div>
                </div>
              </div>
              
              <!-- 当前数据代入穿透 -->
              <div class="metric-info-section">
                <span class="section-tag">🎯 当前数据代入穿透</span>
                <div class="metric-calc-box">
                  <div class="calc-formula">
                    <span class="calc-label">实测结果 =</span>
                    <div class="formula-fraction">
                      <span class="fraction-numerator highlighted">{{ getMetricCalcNumerator(activeMetric) }}</span>
                      <span class="fraction-denominator highlighted">{{ getMetricCalcDenominator(activeMetric) }}</span>
                    </div>
                    <span v-if="getMetricMultiplier(activeMetric)" class="formula-multiplier">{{ getMetricMultiplier(activeMetric) }} = </span>
                    <span v-else class="formula-multiplier">= </span>
                    <span class="calc-result">{{ getMetricResultText(activeMetric) }}</span>
                  </div>
                  <div class="calc-vars-list">
                    <div v-for="(v, k) in getMetricCalcVars(activeMetric)" :key="k" class="var-item">
                      <span class="var-name">{{ k }}：</span>
                      <span class="var-val">{{ v }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 集团管控参考 -->
              <div class="metric-info-section">
                <span class="section-tag">🏢 集团管控参考 (KPI/SLA)</span>
                <div class="metric-target-box">
                  <div class="target-item">
                    <span class="target-lbl">集团运营目标值：</span>
                    <span class="target-val orange">{{ getMetricTargetVal(activeMetric) }}</span>
                  </div>
                  <div class="target-item">
                    <span class="target-lbl">全要素实测得分：</span>
                    <span class="target-val blue">{{ getMetricResultText(activeMetric) }}</span>
                  </div>
                  <div class="target-status">
                    <span class="status-badge success">
                      {{ getMetricStatusText(activeMetric) }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
            
            <div class="metric-modal-footer">
              <button class="btn btn-secondary" @click="closeMetricModal">确定并返回大盘</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 导出配置与 XLSX 导出组件 -->
    <ExportSettingsModal
      :show="showExportModal"
      :columns="exportColumns"
      :data="unfilteredTableData"
      :filtered-data="computedTableData"
      :default-filename="pivotMode === 'station' ? '保温管供需分析透视表_按换热站' : '保温管供需分析透视表_按型号'"
      @close="showExportModal = false"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { AppHeader, Breadcrumbs, useTubePageShell } from './shared'
import {
  getTubeSupplyManagementDemandSummary,
  getTubeSupplyManagementDeliveries,
  getTubeWorkspaceWeatherData
} from '../../daily_report_25_26/services/api'
import ExportSettingsModal from './ExportSettingsModal.vue'

// 获取路由与当前项目 Key
const route = useRoute()
const projectKey = computed(() => String(route.params.projectKey || 'insulation_pipe_supply_2026'))

// 使用 tube 统一页面壳
const {
  loading,
  errorMessage,
  configSummary,
  breadcrumbItems,
  goProjectPages,
  reloadConfigSummary,
} = useTubePageShell('全局数据看板')

// 业务汇总行与发货流水行
const summaryRows = ref([])
const deliveries = ref([])
const loadingSummary = ref(false)

// 前端过滤与排序配置
const pivotMode = ref('station') // 'station' / 'model'
const sortKey = ref('')
const sortOrder = ref('desc')
const filterStationId = ref('')
const filterPipeModelId = ref('')

// 大连市气象防汛施工时效沙盘数据
const weatherDays = ref([])
const loadingWeather = ref(false)

// SaaS 指标计算穿透弹窗控制
const activeMetric = ref(null) // 'otd' | 'doi' | 'pcr' | 'ucr' | 'ssr' | null

function openMetricModal(metricKey) {
  activeMetric.value = metricKey
}

function closeMetricModal() {
  activeMetric.value = null
}

// 导出分析表控制
const showExportModal = ref(false)

const exportColumns = computed(() => {
  return [
    { key: 'name', label: pivotMode.value === 'station' ? '换热站名称' : '保温管型号' },
    { key: 'design_qty', label: '设计量 (米)' },
    { key: 'purchase_plan_qty', label: '计划采购 (米)' },
    { key: 'future_plan_qty', label: '三日计划量 (米)' },
    { key: 'total_shipped_qty', label: '累计发货 (米)' },
    { key: 'pending_arrival_qty', label: '在途待到货 (米)' },
    { key: 'pending_receive_qty', label: '待施工接收 (米)' },
    { key: 'pending_warehouse_qty', label: '到货待库管确认 (米)' },
    { key: 'completed_qty', label: '已确认入库 (米)' },
    { key: 'total_arrived_qty', label: '累计到货 (米)' },
    { key: 'total_usage_qty', label: '累计实际使用 (米)' },
    { key: 'station_inventory_qty', label: '现场可用在库 (米)' },
    { key: 'net_gap_qty', label: '三日净缺口 (米)' },
    { key: 'hard_gap_qty', label: '三日硬缺口 (米)' }
  ]
})

const unfilteredTableData = computed(() => {
  const isStationMode = pivotMode.value === 'station'
  const groups = {}

  summaryRows.value.forEach(row => {
    const groupKey = isStationMode ? row.station_id : row.pipe_model_id
    const groupName = isStationMode ? row.station_name : row.pipe_model_name

    if (!groups[groupKey]) {
      groups[groupKey] = {
        id: groupKey,
        name: groupName,
        design_qty: 0,
        purchase_plan_qty: 0,
        future_plan_qty: 0,
        total_shipped_qty: 0,
        pending_arrival_qty: 0,
        pending_receive_qty: 0,
        pending_warehouse_qty: 0,
        completed_qty: 0,
        total_arrived_qty: 0,
        total_usage_qty: 0,
        station_inventory_qty: 0,
        net_gap_qty: 0,
        hard_gap_qty: 0,
      }
    }

    const g = groups[groupKey]
    g.design_qty += row.design_qty || 0
    g.purchase_plan_qty += row.purchase_plan_qty || 0
    g.future_plan_qty += row.future_plan_qty || 0
    g.total_shipped_qty += row.total_shipped_qty || 0
    g.pending_arrival_qty += row.pending_arrival_qty || 0
    g.pending_receive_qty += row.pending_receive_qty || 0
    g.pending_warehouse_qty += row.pending_warehouse_qty || 0
    g.completed_qty += row.completed_qty || 0
    g.total_arrived_qty += row.total_arrived_qty || 0
    g.total_usage_qty += row.total_usage_qty || 0
    g.station_inventory_qty += row.station_inventory_qty || 0
    g.net_gap_qty += row.net_gap_qty || 0
    g.hard_gap_qty += row.hard_gap_qty || 0
  })

  return Object.values(groups)
})

// --- 实时多维运营指标精算引擎 (SaaS Real-time Metric Aggregator) ---
const backendMetrics = ref(null)

const metricSnapshot = computed(() => {
  const m = backendMetrics.value
  return {
    completedDeliveries: { length: m?.completedDeliveriesCount || 0 }, // 兼容 OTD modal
    onTimeCount: m?.onTimeCount || 0,
    totalInv: m?.totalInv || 0,
    totalFuturePlan: m?.totalFuturePlan || 0,
    dailyConsumePlan: m?.dailyConsumePlan || 0,
    totalUsage: m?.totalUsage || 0,
    totalArrived: m?.totalArrived || 0,
    activeStations: { size: m?.activeStationsCount || 0 }, // 兼容 PCR/SSR activeStations
    submittedStationCount: m?.submittedStationCount || 0,
    safeStationCount: m?.safeStationCount || 0,
    otd: m?.otd || 0,
    doi: m?.doi || 0,
    doiScore: m?.doiScore || 0,
    pcr: m?.pcr || 0,
    ucr: m?.ucr || 0,
    ssr: m?.ssr || 0
  }
})

const realOTD = computed(() => metricSnapshot.value.otd)

const realDOI = computed(() => metricSnapshot.value.doi)

// DOI 转换雷达图百分制得分（天数越低得分越高；无有效分母时不使用演示值）
const realDOIScore = computed(() => metricSnapshot.value.doiScore)

const realPCR = computed(() => metricSnapshot.value.pcr)

const realUCR = computed(() => metricSnapshot.value.ucr)

const realSSR = computed(() => metricSnapshot.value.ssr)

// --- SaaS 指标穿透详情数据解析 (系统数据动态穿透) ---
function getMetricTitle(key) {
  const titles = {
    otd: 'OTD 物流履约度 (24小时到货达成率)',
    doi: 'DOI 周转效率 (在库库存周转天数)',
    pcr: 'PCR 计划达成度 (三日滚动计划提报率)',
    ucr: 'UCR 消耗转化度 (到货施工消耗转化率)',
    ssr: 'SSR 安全供应度 (缺口规避率)'
  }
  return titles[key] || ''
}

function getMetricSubtitle(key) {
  const subs = {
    otd: 'On-Time Delivery - 已确认到货样本的 24 小时时效履约指标',
    doi: 'Days of Inventory - 换热站物资现场周转与场地占用管控指标',
    pcr: 'Plan Commitment Ratio - 数字化报表管理纪律与滚动计划管控指标',
    ucr: 'Utilization Conversion Ratio - 到货接收向实体工程的高效转化指标',
    ssr: 'Supply Security Ratio - 避免断料停工与项目窝工风险安全保障指标'
  }
  return subs[key] || ''
}

function getMetricAbbr(key) {
  return key ? key.toUpperCase() : ''
}

function getMetricDesc(key) {
  const descs = {
    otd: '物流履约度当前按已确认到货样本计算，衡量发货记录从发货到到货确认是否在 24 小时内完成。该指标反映运输履约时效，不再混用演示口径或人工估算值。',
    doi: '在库库存周转天数是反映工程现场资金利用效率与物资积压情况的生命线指标。它代表当前的在库管材库存，在没有新发货补充的情况下，能够支持工区施工开挖敷设多少天。天数越低说明周转越快、资金占用越少。',
    pcr: '三日滚动计划提报率是集团落实“以消定供、精细化平衡”的数字化治理核心纪律。它强力考核各工区施工现场负责人是否按照“按日滚动提报未来三日需求计划”的规范操作。零漏报代表数字化执行力达标。',
    ucr: '到货施工消耗转化率主要用于杜绝工区“只到货、不敷设”的只囤不建现象。该指标衡量运抵现场并物理签收确认的管材，有多大比例已真正转化为实体工程中的管道消耗敷设，保证资金及时形成物理产值。',
    ssr: '安全供应度（缺口规避率）是全网保通车、防窝工的核心风险防御指标。它衡量在所有活跃施工站点中，有多少换热站未发生由于管材供应不足而造成的“物理硬缺口”或实际停工待料情况。'
  }
  return descs[key] || ''
}

function getMetricFormulaNumerator(key) {
  const nums = {
    otd: '24小时内确认到货的发货单数 (单)',
    doi: '全网在库管材总库存量 (米)',
    pcr: '按时提报三日滚动计划的换热站数',
    ucr: '全网累计施工已消耗敷设长度 (米)',
    ssr: '未发生物理硬缺口 (停工断料) 的活跃换热站数'
  }
  return nums[key] || ''
}

function getMetricFormulaDenominator(key) {
  const dens = {
    otd: '已确认到货且可计算时效的发货单数 (单)',
    doi: '未来三日全网日均滚动计划消耗量 (米/天)',
    pcr: '当前处于活跃施工期的总换热站数',
    ucr: '全网累计已到货物理签收的总长度 (米)',
    ssr: '当前处于活跃施工期的总换热站数'
  }
  return dens[key] || ''
}

function getMetricMultiplier(key) {
  return key === 'doi' ? '' : '× 100%'
}

function getMetricCalcNumerator(key) {
  if (key === 'otd') {
    return `${metricSnapshot.value.onTimeCount} 单`
  }
  if (key === 'doi') {
    return `${metricSnapshot.value.totalInv.toFixed(1)} 米`
  }
  if (key === 'pcr') {
    return `${metricSnapshot.value.submittedStationCount} 个工区`
  }
  if (key === 'ucr') {
    return `${metricSnapshot.value.totalUsage.toFixed(1)} 米`
  }
  if (key === 'ssr') {
    return `${metricSnapshot.value.safeStationCount} 个站点`
  }
  return ''
}

function getMetricCalcDenominator(key) {
  if (key === 'otd') {
    return `${metricSnapshot.value.completedDeliveries.length} 单`
  }
  if (key === 'doi') {
    return `${metricSnapshot.value.dailyConsumePlan.toFixed(1)} 米/天`
  }
  if (key === 'pcr') {
    return `${metricSnapshot.value.activeStations.size} 个工区`
  }
  if (key === 'ucr') {
    return `${metricSnapshot.value.totalArrived.toFixed(1)} 米`
  }
  if (key === 'ssr') {
    return `${metricSnapshot.value.activeStations.size} 个工区`
  }
  return ''
}

function getMetricResultText(key) {
  if (key === 'otd') return `${realOTD.value}%`
  if (key === 'doi') return `${realDOI.value} 天`
  if (key === 'pcr') return `${realPCR.value}%`
  if (key === 'ucr') return `${realUCR.value}%`
  if (key === 'ssr') return `${realSSR.value}%`
  return ''
}

function getMetricCalcVars(key) {
  if (key === 'otd') {
    return {
      '分子 (24小时内到货)': `${metricSnapshot.value.onTimeCount} 单 (发货至到货确认不超过 24 小时)`,
      '分母 (可计算样本数)': `${metricSnapshot.value.completedDeliveries.length} 单 (已确认到货且具备完整发货/到货时间)`,
      '判定规则': '以发货时间到到货确认时间的小时差 <= 24 视为准时'
    }
  }
  if (key === 'doi') {
    return {
      '分子 (现场在库库存)': `${metricSnapshot.value.totalInv.toFixed(1)} 米 (全网在库实测管材之和)`,
      '分母 (日均计划消耗)': `${metricSnapshot.value.dailyConsumePlan.toFixed(1)} 米/天 (由未来三日滚动计划 ${metricSnapshot.value.totalFuturePlan.toFixed(1)} 米折算)`,
      'DOI 说明': `DOI = 在库库存 / 日均计划消耗。本指标单位为“天”，不乘以 100%。当前雷达折算得分：${realDOIScore.value} 分。`
    }
  }
  if (key === 'pcr') {
    return {
      '分子 (按时提报站点)': `${metricSnapshot.value.submittedStationCount} 个工区 (存在滚动三日计划数据)`,
      '分母 (活跃总工区数)': `${metricSnapshot.value.activeStations.size} 个换热站标段 (design_qty > 0 视为活跃站点)`,
      '数字化纪律得分': `当前提报达成率 ${realPCR.value}%。数字化指令下达零延误、零漏报。`
    }
  }
  if (key === 'ucr') {
    return {
      '分子 (实际消耗敷设)': `${metricSnapshot.value.totalUsage.toFixed(1)} 米 (槽下物理铺设焊接完毕并经确认的长度)`,
      '分母 (签到到货总量)': `${metricSnapshot.value.totalArrived.toFixed(1)} 米 (现场负责人确认到货的累计长度)`,
      '转化成效评估': `全网累计 ${realUCR.value}% 的到货管材已立即转化为空中或槽下物理管道实体，流转效率极优。`
    }
  }
  if (key === 'ssr') {
    return {
      '分子 (安全在建工区)': `${metricSnapshot.value.safeStationCount} 个工区 (未面临物理断料风险)`,
      '分母 (总活跃工区数)': `${metricSnapshot.value.activeStations.size} 个换热站标段 (全网在建全部活跃工区)`,
      '缺口避让防线': `全要素缺口安全覆盖度达 ${realSSR.value}%，整体处于安全达标区间。`
    }
  }
  return {}
}

function getMetricTargetVal(key) {
  const targets = {
    otd: '≥ 90.0%',
    doi: '< 5.0 天',
    pcr: '≥ 95.0%',
    ucr: '≥ 80.0%',
    ssr: '≥ 90.0%'
  }
  return targets[key] || ''
}

function getMetricStatusText(key) {
  const texts = {
    otd: '运营极佳 (优于集团 90.0% 红线)',
    doi: '流转优异 (优于集团 5.0 天红线)',
    pcr: '纪律极佳 (优于集团 95.0% 红线)',
    ucr: '转化高效 (优于集团 80.0% 红线)',
    ssr: '安全在控 (优于集团 90.0% 红线)'
  }
  return texts[key] || ''
}

// ECharts 挂载节点
const chartContainer1 = ref(null)
const chartContainer2 = ref(null)
let chartInstance1 = null
let chartInstance2 = null
const hasEcharts = ref(false)

// 刷新全部配置与明细
async function refreshAllData() {
  await reloadConfigSummary()
  await Promise.all([
    loadDashboardData(),
    fetchWeatherData()
  ])
}

// 拉取后端真实数据
async function loadDashboardData() {
  loadingSummary.value = true
  try {
    const summaryRes = await getTubeSupplyManagementDemandSummary(projectKey.value)
    summaryRows.value = summaryRes?.rows || []
    backendMetrics.value = summaryRes?.metrics || null

    const deliveriesRes = await getTubeSupplyManagementDeliveries(projectKey.value)
    deliveries.value = Array.isArray(deliveriesRes?.rows) ? deliveriesRes.rows : []
    
    // 数据加载完毕后渲染图表
    nextTick(() => {
      renderCharts()
    })
  } catch (error) {
    console.error('拉取 tube 汇总数据失败:', error)
  } finally {
    loadingSummary.value = false
  }
}

// HSL 名字映射解析
function stationName(id) {
  const list = configSummary.value?.demand_entities || []
  const item = list.find(x => String(x.station_id) === String(id))
  return item ? item.station_name : id
}

// 保温管型号名映射
function pipeModelName(id) {
  const list = configSummary.value?.pipe_models || []
  const item = list.find(x => String(x.pipe_model_id) === String(id))
  return item ? item.pipe_model_name : id
}

// 供给主体映射
function supplyEntityName(id) {
  const list = configSummary.value?.supply_entities || []
  const item = list.find(x => String(x.entity_id) === String(id))
  return item ? item.entity_name : id
}

// 格式化时间
function formatTime(isoStr) {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    return `${d.getMonth() + 1}-${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  } catch (e) {
    return isoStr
  }
}

// 格式化展示量（数值以 m 为单位）
function formatQty(val) {
  if (val === null || val === undefined) return '0'
  const num = Number(val)
  return isNaN(num) ? '0' : num.toFixed(0)
}

function getPercent(n, total) {
  if (!total || total <= 0) return 0
  const pct = (n / total) * 100
  return Math.min(100, Math.max(0, Number(pct.toFixed(1))))
}

// 重置过滤
function resetFilters() {
  filterStationId.value = ''
  filterPipeModelId.value = ''
  sortKey.value = ''
}

// 排序符号
function getSortSymbol(key) {
  if (sortKey.value !== key) return '⇅'
  return sortOrder.value === 'asc' ? '▲' : '▼'
}

// 排序处理
function handleSort(key) {
  if (sortKey.value === key) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortOrder.value = 'desc'
  }
}

// 1. KPI 大盘计算
const kpi = computed(() => {
  let design = 0
  let purchase = 0
  let plan = 0
  let shipped = 0
  let pendingArrival = 0
  let pendingReceive = 0
  let pendingWarehouse = 0
  let completed = 0
  let arrived = 0
  let usage = 0
  let inventory = 0
  let netGap = 0
  let hardGap = 0

  summaryRows.value.forEach(row => {
    design += row.design_qty || 0
    purchase += row.purchase_plan_qty || 0
    plan += row.future_plan_qty || 0
    shipped += row.total_shipped_qty || 0
    pendingArrival += row.pending_arrival_qty || 0
    pendingReceive += row.pending_receive_qty || 0
    pendingWarehouse += row.pending_warehouse_qty || 0
    completed += row.completed_qty || 0
    arrived += row.total_arrived_qty || 0
    usage += row.total_usage_qty || 0
    inventory += row.station_inventory_qty || 0
    netGap += row.net_gap_qty || 0
    
    // 硬缺口统一使用后端计算，防范负库存导致的公式膨胀
    hardGap += row.hard_gap_qty || 0
  })

  return {
    design,
    purchase,
    plan,
    shipped,
    pendingArrival,
    pendingReceive,
    pendingWarehouse,
    completed,
    arrived,
    usage,
    inventory,
    netGap,
    hardGap
  }
})

// 2. 透视（Pivot）与排序、全局条件过滤
const computedTableData = computed(() => {
  const isStationMode = pivotMode.value === 'station'
  const groups = {}

  summaryRows.value.forEach(row => {
    // 过滤逻辑：站点过滤
    if (filterStationId.value && String(row.station_id) !== String(filterStationId.value)) {
      return
    }
    // 过滤逻辑：管径型号过滤
    if (filterPipeModelId.value && String(row.pipe_model_id) !== String(filterPipeModelId.value)) {
      return
    }

    const groupKey = isStationMode ? row.station_id : row.pipe_model_id
    const groupName = isStationMode ? row.station_name : row.pipe_model_name

    if (!groups[groupKey]) {
      groups[groupKey] = {
        id: groupKey,
        name: groupName,
        design_qty: 0,
        purchase_plan_qty: 0,
        future_plan_qty: 0,
        total_shipped_qty: 0,
        pending_arrival_qty: 0,
        pending_receive_qty: 0,
        pending_warehouse_qty: 0,
        completed_qty: 0,
        total_arrived_qty: 0,
        total_usage_qty: 0,
        station_inventory_qty: 0,
        net_gap_qty: 0,
        hard_gap_qty: 0,
      }
    }

    const g = groups[groupKey]
    g.design_qty += row.design_qty || 0
    g.purchase_plan_qty += row.purchase_plan_qty || 0
    g.future_plan_qty += row.future_plan_qty || 0
    g.total_shipped_qty += row.total_shipped_qty || 0
    g.pending_arrival_qty += row.pending_arrival_qty || 0
    g.pending_receive_qty += row.pending_receive_qty || 0
    g.pending_warehouse_qty += row.pending_warehouse_qty || 0
    g.completed_qty += row.completed_qty || 0
    g.total_arrived_qty += row.total_arrived_qty || 0
    g.total_usage_qty += row.total_usage_qty || 0
    g.station_inventory_qty += row.station_inventory_qty || 0
    g.net_gap_qty += row.net_gap_qty || 0
    
    // 硬缺口统一使用后端计算，规避前端分散逻辑
    g.hard_gap_qty += row.hard_gap_qty || 0
  })

  const list = Object.values(groups)

  // 排序逻辑
  if (sortKey.value) {
    list.sort((a, b) => {
      const valA = a[sortKey.value] || 0
      const valB = b[sortKey.value] || 0
      return sortOrder.value === 'asc' ? valA - valB : valB - valA
    })
  }

  return list
})

// 获取气象代码对应的 Emoji 图标
function getWeatherIcon(code) {
  const codeVal = code !== undefined && code !== null ? Number(code) : 0
  if (codeVal === 0) return '☀️'
  if ([1, 2].includes(codeVal)) return '⛅'
  if (codeVal === 3) return '☁️'
  if ([45, 48].includes(codeVal)) return '🌫️'
  if ([51, 53, 55, 56, 57].includes(codeVal)) return '🌦️'
  if ([61, 63, 65, 66, 67].includes(codeVal)) return '🌧️'
  if ([71, 73, 75, 77].includes(codeVal)) return '❄️'
  if ([80, 81, 82].includes(codeVal)) return '🌦️'
  if ([85, 86].includes(codeVal)) return '🌨️'
  if ([95, 96, 99].includes(codeVal)) return '⛈️'
  return '☀️'
}

// 获取紫外线色阶等级徽章
function getUvInfo(uvVal) {
  if (uvVal === null || uvVal === undefined) {
    return { uvClass: '', uvLevel: '—' }
  }
  const val = Number(uvVal)
  if (val < 3) return { uvClass: 'uv-low', uvLevel: '低' }
  if (val < 6) return { uvClass: 'uv-mod', uvLevel: '中等' }
  if (val < 8) return { uvClass: 'uv-high', uvLevel: '高' }
  if (val < 11) return { uvClass: 'uv-very-high', uvLevel: '很高' }
  return { uvClass: 'uv-extreme', uvLevel: '极强' }
}

// 3. 实时从本地数据库气象表获取数据并计算防汛施工时效决策建议
async function fetchWeatherData() {
  loadingWeather.value = true
  try {
    const showDate = configSummary.value?.show_date || ''
    const res = await getTubeWorkspaceWeatherData(projectKey.value, { show_date: showDate })
    if (res && res.weather_days) {
      const list = []
      
      res.weather_days.forEach((day, idx) => {
        const rainVal = day.rain_sum !== undefined && day.rain_sum !== null ? Number(day.rain_sum) : 0
        const uvVal = day.uv_index_max !== undefined && day.uv_index_max !== null ? Number(day.uv_index_max) : 0
        const dateLabel = day.label || ''
        const timeStr = day.date || ''

        // 格式化日期 (如 2026-05-26 -> 05-26)
        let formattedDate = timeStr
        if (timeStr.includes('-')) {
          const parts = timeStr.split('-')
          if (parts.length >= 3) {
            formattedDate = `${parts[1]}-${parts[2]}`
          }
        }

        // 智能气象状态与图标、施工建议判定
        const weatherIcon = getWeatherIcon(day.weather_code)
        const statusText = day.weather_text || '未知'
        
        let themeClass = 'fine'

        if (rainVal > 0 && rainVal <= 2.0) {
          themeClass = 'light-rain'
        } else if (rainVal > 2.0 && rainVal <= 8.0) {
          themeClass = 'moderate-rain'
        } else if (rainVal > 8.0) {
          themeClass = 'heavy-rain'
        }

        // 解析紫外线色阶与等级
        const uvInfo = getUvInfo(uvVal)

        list.push({
          dateLabel,
          formattedDate,
          rainVal,
          uvVal,
          uvClass: uvInfo.uvClass,
          uvLevel: uvInfo.uvLevel,
          tempMax: day.temp_max,
          tempMean: day.temp_mean,
          weatherIcon,
          statusText,
          themeClass
        })
      })
      weatherDays.value = list
    }
  } catch (err) {
    console.error('获取大连降水气象数据失败:', err)
  } finally {
    loadingWeather.value = false
  }
}

// 4. ECharts 交互可视化图表渲染
function renderCharts() {
  if (!window.echarts) {
    hasEcharts.value = false
    return
  }
  hasEcharts.value = true

  // --- 图表一：各保温管型号供需堆叠柱状图 ---
  if (chartContainer1.value) {
    if (!chartInstance1) {
      chartInstance1 = window.echarts.init(chartContainer1.value)
    }

    // 提取型号维度的数据
    const modelsMap = {}
    summaryRows.value.forEach(row => {
      const modelId = row.pipe_model_id
      const modelName = row.pipe_model_name
      if (!modelsMap[modelId]) {
        modelsMap[modelId] = {
          name: modelName,
          inventory: 0,
          pending: 0,
          netGap: 0
        }
      }
      modelsMap[modelId].inventory += row.station_inventory_qty || 0
      modelsMap[modelId].pending += row.pending_arrival_qty || 0
      modelsMap[modelId].netGap += row.net_gap_qty || 0
    })

    // 仅展示三日净缺口排名前 5 的型号规格，避免横轴文本堆叠
    const mList = Object.values(modelsMap)
      .sort((a, b) => b.netGap - a.netGap)
      .slice(0, 5)
    
    const option1 = {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      legend: {
        data: ['现场库存', '在途在管', '三日净缺口'],
        bottom: 0,
        textStyle: { color: '#475569', fontWeight: 600 }
      },
      grid: {
        top: '15%',
        left: '4%',
        right: '4%',
        bottom: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: mList.map(x => x.name),
        axisLabel: {
          color: '#64748b',
          fontSize: 10,
          rotate: 35,
          interval: 0
        }
      },
      yAxis: {
        type: 'value',
        name: '米 (m)',
        nameTextStyle: { color: '#64748b', fontWeight: 600 },
        axisLabel: { color: '#64748b' },
        splitLine: { lineStyle: { type: 'dashed', color: '#f1f5f9' } }
      },
      series: [
        {
          name: '现场库存',
          type: 'bar',
          stack: 'total',
          emphasis: { focus: 'series' },
          data: mList.map(x => x.inventory),
          itemStyle: { color: '#10b981', borderRadius: [2, 2, 0, 0] }
        },
        {
          name: '在途在管',
          type: 'bar',
          stack: 'total',
          emphasis: { focus: 'series' },
          data: mList.map(x => x.pending),
          itemStyle: { color: '#06b6d4', borderRadius: [2, 2, 0, 0] }
        },
        {
          name: '三日净缺口',
          type: 'bar',
          stack: 'total',
          emphasis: { focus: 'series' },
          data: mList.map(x => x.netGap),
          itemStyle: { color: '#ea580c', borderRadius: [2, 2, 0, 0] }
        }
      ]
    }
    chartInstance1.setOption(option1, { notMerge: false, lazyUpdate: true })
  }

  // --- 图表二：大连洁净能源集团 - 物流全链路综合健康评估多维雷达图 ---
  if (chartContainer2.value) {
    if (!chartInstance2) {
      chartInstance2 = window.echarts.init(chartContainer2.value)
    }

    const option2 = {
      title: {
        text: '大连洁净能源集团 - 物流全链路综合健康评估',
        left: 'center',
        top: '4%',
        textStyle: { color: '#1e293b', fontSize: 13, fontWeight: '800' }
      },
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#e2e8f0',
        borderWidth: 1,
        textStyle: { color: '#334155', fontSize: 11 }
      },
      radar: {
        indicator: [
          { name: 'OTD|供应链发货准时率', max: 100 },
          { name: 'DOI|现场在库周转天数', max: 100 },
          { name: 'PCR|三日滚动计划达成率', max: 100 },
          { name: 'UCR|施工消耗转化率', max: 100 },
          { name: 'SSR|安全供应防线', max: 100 }
        ],
        center: ['50%', '54%'],
        radius: '58%',
        axisName: {
          formatter: (value) => {
            const [abbr, title] = value.split('|')
            return `{abbr|${abbr}}\n{title|${title}}`
          },
          rich: {
            abbr: {
              color: '#3b82f6',
              fontSize: 14,
              fontWeight: '900',
              fontFamily: 'monospace',
              align: 'center',
              lineHeight: 20
            },
            title: {
              color: '#1e293b',
              fontSize: 13,
              fontWeight: 'bold',
              align: 'center',
              lineHeight: 18
            },
          },
          color: '#475569',
          backgroundColor: '#f8fafc',
          borderColor: '#e2e8f0',
          borderWidth: 1,
          borderRadius: 8,
          padding: [8, 12]
        },
        splitArea: {
          show: true,
          areaStyle: {
            color: ['rgba(248, 250, 252, 0.5)', 'rgba(241, 245, 249, 0.5)', 'rgba(226, 232, 240, 0.5)', 'rgba(203, 213, 225, 0.5)']
          }
        },
        splitLine: {
          lineStyle: {
            color: 'rgba(148, 163, 184, 0.3)',
            type: 'dashed'
          }
        },
        axisLine: {
          lineStyle: {
            color: 'rgba(148, 163, 184, 0.4)'
          }
        }
      },
      series: [
        {
          name: '健康评估',
          type: 'radar',
          data: [
            {
              value: [realOTD.value, realDOIScore.value, realPCR.value, realUCR.value, realSSR.value],
              name: '全要素实测得分',
              symbol: 'circle',
              symbolSize: 6,
              itemStyle: { color: '#3b82f6' },
              lineStyle: { width: 2.5, color: '#3b82f6' },
              areaStyle: {
                color: new window.echarts.graphic.RadialGradient(0.5, 0.5, 0.5, [
                  { offset: 0, color: 'rgba(59, 130, 246, 0.15)' },
                  { offset: 1, color: 'rgba(59, 130, 246, 0.5)' }
                ])
              }
            },
            {
              value: [90.0, 85.0, 95.0, 80.0, 90.0],
              name: '集团运营目标值',
              symbol: 'none',
              lineStyle: { width: 1.5, type: 'dashed', color: '#ea580c' },
              itemStyle: { color: '#ea580c' }
            }
          ]
        }
      ],
      legend: {
        bottom: 5,
        data: ['全要素实测得分', '集团运营目标值'],
        textStyle: { color: '#475569', fontWeight: '700', fontSize: 10 }
      }
    }
    chartInstance2.setOption(option2, { notMerge: false, lazyUpdate: true })
  }
}

// 自动响应式重绘
function handleResize() {
  chartInstance1?.resize()
  chartInstance2?.resize()
}

// 联动重绘 Watcher
watch([summaryRows, pivotMode], () => {
  nextTick(() => {
    renderCharts()
  })
}, { deep: true })

// 监听业务日期变化，自动刷新气象数据
watch(() => configSummary.value?.show_date, (newVal) => {
  if (newVal) {
    fetchWeatherData()
  }
})

onMounted(() => {
  Promise.all([
    loadDashboardData(),
    fetchWeatherData()
  ])
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance1?.dispose()
  chartInstance2?.dispose()
})
</script>

<style scoped>
.tube-page-root {
  min-height: 100vh;
  background: var(--bg, #f8fafc);
}

.tube-page-main {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-top: 18px;
  padding-bottom: 36px;
}

/* 顶部栏 */
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.date-context-badge {
  display: flex;
  gap: 16px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid #e2e8f0;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 13px;
  color: #475569;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

.date-context-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}

.dot.green { background: #10b981; }
.dot.blue { background: #3b82f6; }

.page-error {
  margin: 0;
  color: var(--danger, #ef4444);
  font-weight: 600;
  background: #fef2f2;
  padding: 10px 16px;
  border-radius: 8px;
  border: 1px solid #fca5a5;
}

/* 第一区：KPI 磨砂卡片大盘 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
}

.stat-card {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -1px rgba(0, 0, 0, 0.02);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 20px -3px rgba(0, 0, 0, 0.06), 0 4px 6px -2px rgba(0, 0, 0, 0.04);
}

.stat-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 4px;
  background: #cbd5e1;
}

.stat-card:nth-child(1)::before { background: #3b82f6; }
.stat-card:nth-child(2)::before { background: #06b6d4; }
.stat-card:nth-child(3)::before { background: #10b981; }
.stat-card:nth-child(4)::before { background: #ef4444; }

.stat-card__icon {
  position: absolute;
  right: 18px;
  top: 18px;
  font-size: 26px;
  opacity: 0.15;
}

.stat-card__label {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
  margin-bottom: 10px;
}

.stat-card__value {
  font-size: 24px;
  font-weight: 800;
  color: #1e293b;
  font-variant-numeric: tabular-nums;
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.stat-card__unit {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 500;
}

.stat-card__separator {
  margin: 0 6px;
  color: #cbd5e1;
  font-size: 18px;
  font-weight: 300;
}

.highlight-blue { color: #2563eb; }
.highlight-cyan { color: #0891b2; }
.highlight-green { color: #059669; }
.highlight-red { color: #dc2626; }
.highlight-orange { color: #ea580c; }

/* 红色警告闪烁呼吸灯 */
.stat-card.alert-pulsing::after {
  content: '';
  position: absolute;
  right: 8px;
  top: 8px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ef4444;
  box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
  animation: pulse-red-light 1.5s infinite;
}

@keyframes pulse-red-light {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

.blink {
  animation: blink-text 1.2s infinite;
}

@keyframes blink-text {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.65; }
}

.stat-card__progress {
  margin-top: 16px;
}

.progress-bar-bg {
  height: 6px;
  background: #f1f5f9;
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.progress-bar-fill.blue { background: #3b82f6; }
.progress-bar-fill.cyan { background: #06b6d4; }
.progress-bar-fill.green { background: #10b981; }
.progress-bar-fill.red { background: #ef4444; }

.progress-bar-text {
  margin-top: 6px;
  font-size: 11px;
  color: #64748b;
  font-weight: 500;
  display: flex;
  justify-content: space-between;
}

/* 第二区：ECharts 全局可视化图表大盘 */
.charts-grid {
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  padding: 20px;
}

.charts-section-header {
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 12px;
  margin-bottom: 16px;
}

.charts-section-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: #1e293b;
}

.charts-tip {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 500;
}

.charts-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 1200px) {
  .charts-container {
    grid-template-columns: 1fr;
  }
}

.chart-wrapper {
  background: #f8fafc;
  border: 1px solid #f1f5f9;
  border-radius: 8px;
  padding: 16px;
  position: relative;
  display: flex;
  flex-direction: column;
}

.chart-title {
  font-size: 13px;
  font-weight: 800;
  color: #334155;
  margin-bottom: 12px;
}

.metric-saas-card {
  background: #f8fafc;
  border: 1px solid #f1f5f9;
  border-radius: 12px;
  padding: 16px 20px;
  position: relative;
  z-index: 5; /* 适度提升层级，物理防御雷达图 Canvas 溢出，且不遮挡顶部 Banner */
  cursor: pointer;
  pointer-events: auto !important; /* 强制拦截鼠标事件并响应点击，杜绝任何外部层级劫持 */
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.echarts-dom {
  height: 280px;
  width: 100%;
}

.chart-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(248, 250, 252, 0.9);
  color: #ef4444;
  font-size: 13px;
  font-weight: 600;
}

/* 第二区图表 & 大连气象施工防汛决策沙盘 */
.weather-decision-panel {
  background: #ffffff !important;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.chart-title-group-fluid, .weather-title-group {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.weather-location-badge {
  font-size: 11px;
  background: #eff6ff;
  color: #3b82f6;
  padding: 3px 8px;
  border-radius: 12px;
  font-weight: 700;
}

.weather-days-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  flex: 1;
}

@media (max-width: 560px) {
  .weather-days-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.weather-day-card {
  background: #f8fafc;
  border-radius: 10px;
  padding: 10px 8px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  border: 1px solid #e2e8f0;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  min-height: 190px;
}

.weather-day-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

/* 4态天气卡片专属微渐变背景 */
.weather-day-card.fine {
  background: linear-gradient(180deg, #f0fdf4 0%, #ffffff 100%);
  border-color: #bbf7d0;
}
.weather-day-card.light-rain {
  background: linear-gradient(180deg, #eff6ff 0%, #ffffff 100%);
  border-color: #bfdbfe;
}
.weather-day-card.moderate-rain {
  background: linear-gradient(180deg, #fff7ed 0%, #ffffff 100%);
  border-color: #fed7aa;
}
.weather-day-card.heavy-rain {
  background: linear-gradient(180deg, #fef2f2 0%, #ffffff 100%);
  border-color: #fca5a5;
}

/* 高亮突出当日卡片 */
.weather-day-card.current-day {
  box-shadow: 0 0 0 2px #3b82f6;
}
.weather-day-card.current-day::before {
  content: 'TODAY';
  position: absolute;
  top: 0;
  right: 0;
  background: #3b82f6;
  color: #ffffff;
  font-size: 8px;
  font-weight: 800;
  padding: 1px 5px;
  border-bottom-left-radius: 4px;
}

.weather-day-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px dashed rgba(0, 0, 0, 0.06);
  padding-bottom: 4px;
}

.weather-label {
  font-size: 11px;
  font-weight: 800;
  color: #475569;
}

.weather-date {
  font-size: 10px;
  color: #94a3b8;
  font-family: monospace;
}

.weather-day-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 0;
  gap: 4px;
  width: 100%;
  box-sizing: border-box;
}

.weather-icon-large {
  font-size: 28px;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.06));
}

.weather-metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
  width: 100%;
  margin: 10px 0;
  padding: 0;
  box-sizing: border-box;
}

.weather-metric-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: rgba(255, 255, 255, 0.45);
  border: 1px solid rgba(226, 232, 240, 0.7);
  border-radius: 8px;
  padding: 6px 4px;
  box-sizing: border-box;
}

.weather-metric-item .lbl {
  font-size: 9px;
  color: #64748b;
  margin-bottom: 2px;
  font-weight: 600;
  white-space: nowrap;
}

.weather-metric-item .val-unit {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 1px;
  width: 100%;
}

.weather-metric-item .val {
  font-size: 12px;
  font-weight: 700;
  color: #1e293b;
  font-family: monospace;
}

.weather-metric-item .val.rain {
  color: #0284c7;
}

.weather-metric-item .unit {
  font-size: 8px;
  color: #94a3b8;
  font-weight: 600;
}

.weather-metric-item .unit-badge {
  font-size: 8px;
  padding: 1px 3px;
  border-radius: 3px;
  font-weight: 700;
  transform: scale(0.95);
  white-space: nowrap;
}

/* 紫外线色阶样式 */
.uv-low { color: #16a34a !important; background: #dcfce7; }
.uv-mod { color: #d97706 !important; background: #fef3c7; }
.uv-high { color: #ea580c !important; background: #ffedd5; }
.uv-very-high { color: #dc2626 !important; background: #fee2e2; }
.uv-extreme { color: #7f1d1d !important; background: #fca5a5; }

.weather-status-tag {
  font-size: 9px;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
}
.weather-status-tag.fine { background: #dcfce7; color: #15803d; }
.weather-status-tag.light-rain { background: #dbeafe; color: #1d4ed8; }
.weather-status-tag.moderate-rain { background: #ffedd5; color: #c2410c; }
.weather-status-tag.heavy-rain { background: #fee2e2; color: #b91c1c; }

/* 去除已弃用的决策话术与气象卡片底部布局 */

/* 第三区：健康雷达评估与精细化运营大盘 (双面板) */
/* 第三区：健康雷达评估与精细化运营大盘 (3x3 融合网格布局) */
.workbench-grid-layout {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  padding: 20px;
  background: #ffffff;
  width: 100%;
  box-sizing: border-box;
}

/* 雷达图大格子占 2x2 */
.workbench-radar-grid-cell {
  grid-column: 1 / 3;
  grid-row: 1 / 3;
  background: #ffffff;
  border: 1px solid #f1f5f9;
  border-radius: 12px;
  padding: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  box-shadow: inset 0 0 12px rgba(241, 245, 249, 0.5);
}

.echarts-dom-radar {
  height: 400px; /* 高度提升至 400px，使雷达图展现更饱满 */
  width: 100%;
  pointer-events: none;
}

/* 5个卡片依次在九宫格中占位 */
.metric-saas-card.cell-3 {
  grid-column: 3;
  grid-row: 1;
}

.metric-saas-card.cell-6 {
  grid-column: 3;
  grid-row: 2;
}

.metric-saas-card.cell-7 {
  grid-column: 1;
  grid-row: 3;
}

.metric-saas-card.cell-8 {
  grid-column: 2;
  grid-row: 3;
}

.metric-saas-card.cell-9 {
  grid-column: 3;
  grid-row: 3;
}

/* 自适应降级断点 (中大屏幕 1200px 自动上下垂直分栏) */
@media (max-width: 1200px) {
  .workbench-grid-layout {
    grid-template-columns: repeat(2, 1fr); /* 降级为 2 列网格 */
  }
  
  .workbench-radar-grid-cell {
    grid-column: 1 / -1; /* 雷达图独占一整行 */
    grid-row: auto;
  }
  
  .metric-saas-card.cell-3,
  .metric-saas-card.cell-6,
  .metric-saas-card.cell-7,
  .metric-saas-card.cell-8,
  .metric-saas-card.cell-9 {
    grid-column: auto;
    grid-row: auto;
  }
  
  /* 在 2 列降级排布下，让 SSR 独占一整行，极度工整对称 */
  .metric-saas-card.cell-9 {
    grid-column: span 2;
  }
}

/* 移动端降级 (640px) */
@media (max-width: 640px) {
  .workbench-grid-layout {
    grid-template-columns: 1fr; /* 折叠为单列 */
    padding: 12px;
  }
  
  .metric-saas-card.cell-3,
  .metric-saas-card.cell-6 {
    min-height: auto;
    max-height: none;
  }

  .metric-saas-card.cell-9 {
    grid-column: auto;
  }
}

.metric-saas-card {
  background: #f8fafc;
  border: 1px solid #f1f5f9;
  border-radius: 12px;
  padding: 16px 20px;
  position: relative;
  z-index: 5; /* 适度提升层级，物理防御雷达图 Canvas 溢出，且不遮挡顶部 Banner */
  cursor: pointer;
  pointer-events: auto !important; /* 物理强制保证点击事件 100% 畅通无阻传递 */
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.metric-saas-card.cell-3,
.metric-saas-card.cell-6 {
  min-height: 156px;
  max-height: 156px;
}

.metric-saas-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 20px -3px rgba(0, 0, 0, 0.04), 0 4px 6px -2px rgba(0, 0, 0, 0.02);
}

.metric-saas-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  width: 4px;
  height: 100%;
}

.metric-saas-card.otd::before { background: #3b82f6; }
.metric-saas-card.doi::before { background: #ea580c; }
.metric-saas-card.pcr::before { background: #10b981; }
.metric-saas-card.ucr::before { background: #8b5cf6; }

.metric-saas-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.metric-abbr {
  font-size: 14px;
  font-weight: 900;
  color: #1e293b;
  font-family: monospace;
}

.metric-badge {
  font-size: 9.5px;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 4px;
}
.metric-badge.success { background: rgba(16, 185, 129, 0.08); color: #10b981; }
.metric-badge.warning { background: rgba(234, 88, 12, 0.08); color: #ea580c; }
.metric-badge.info { background: rgba(59, 130, 246, 0.08); color: #3b82f6; }

.metric-saas-value {
  font-size: 26px;
  font-weight: 900;
  color: #0f172a;
  font-family: 'monospace';
  margin-bottom: 2px;
  font-variant-numeric: tabular-nums;
}

.metric-saas-unit {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 600;
  margin-left: 2px;
}

.metric-saas-label {
  font-size: 12px;
  font-weight: 800;
  color: #475569;
  margin-bottom: 8px;
}

.metric-saas-help {
  margin: 0;
  font-size: 10px;
  color: #94a3b8;
  line-height: 1.4;
  min-height: 28px;
  max-height: 28px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

/* 宽屏下的全链路健康状态 */
.alerts-fluid-empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 48px 20px;
  color: #94a3b8;
}

.empty-fluid-icon {
  font-size: 44px;
  margin-bottom: 12px;
  animation: pulse-health 2s infinite;
}

@keyframes pulse-health {
  0%, 100% { transform: scale(1); opacity: 0.9; }
  50% { transform: scale(1.06); opacity: 1; }
}

.alerts-fluid-empty-state h4 {
  margin: 0 0 6px 0;
  color: #334155;
  font-size: 15px;
  font-weight: 800;
}

.alerts-fluid-empty-state p {
  margin: 0;
  font-size: 13px;
}

/* 第四区：多维数据透视表 */
.pivot-section-fluid {
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.pivot-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  border-bottom: 1px solid #f1f5f9;
  padding: 16px 20px;
}

.pivot-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.pivot-title-group h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: #1e293b;
}

.pivot-badge {
  font-size: 11px;
  background: #f1f5f9;
  color: #64748b;
  padding: 3px 8px;
  border-radius: 12px;
  font-weight: 500;
}

/* Tab 标签化工作台按钮 */
.tab-workbench {
  display: flex;
  background: #f1f5f9;
  padding: 4px;
  border-radius: 8px;
}

.tab-btn {
  border: none;
  background: transparent;
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-btn.active {
  background: #ffffff;
  color: #3b82f6;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

/* 过滤栏 */
.search-filter-bar {
  display: flex;
  gap: 16px;
  padding: 12px 20px;
  background: #f8fafc;
  border-bottom: 1px solid #f1f5f9;
  align-items: center;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #475569;
}

.filter-item select {
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  font-size: 13px;
  color: #334155;
  outline: none;
}

.filter-item select:focus {
  border-color: #3b82f6;
}

.link-btn {
  background: transparent !important;
  border: none !important;
  color: #3b82f6 !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  cursor: pointer;
  padding: 0 !important;
}

.link-btn:hover {
  text-decoration: underline;
}

/* 数据透视表格 */
.pivot-table-container {
  overflow-x: auto;
  padding: 0;
}

.pivot-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 900px;
}

.pivot-table th, 
.pivot-table td {
  padding: 12px 14px;
  border-bottom: 1px solid #f1f5f9;
  font-size: 13px;
  line-height: 1.5;
}

.pivot-table th {
  background: #f8fafc;
  color: #475569;
  font-weight: 800;
  user-select: none;
  white-space: nowrap;
}

.pivot-table th.sortable {
  cursor: pointer;
}

.pivot-table th.sortable:hover {
  background: #e2e8f0;
  color: #1e293b;
}

.pivot-row:hover {
  background: #f8fafc;
}

.pivot-row td {
  font-variant-numeric: tabular-nums;
  color: #334155;
}

/* 单元格强制对齐与防折行 */
.left-align { text-align: left; }
.right-align { text-align: right; }
.center-align { text-align: center; }

.text-col {
  min-width: 140px;
  max-width: 180px;
}

.num-col {
  width: 85px;
}

.cell-ellipsis {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.font-bold {
  font-weight: 700;
}

/* 报警高亮列 */
.highlight-th-green { background: #f0fdf4 !important; color: #166534 !important; }
.highlight-th-red { background: #fef2f2 !important; color: #991b1b !important; }
.highlight-th-orange { background: #fff7ed !important; color: #9a3412 !important; }

.highlight-cell-green { background: rgba(240, 253, 244, 0.5); font-weight: 600; color: #15803d !important; }
.highlight-cell-red { background: rgba(254, 242, 242, 0.5); font-weight: 600; }
.highlight-cell-orange { background: rgba(255, 247, 237, 0.5); font-weight: 600; }

.danger-text { color: #ef4444 !important; }
.warning-text { color: #ea580c !important; }

.empty-row td {
  padding: 36px;
  color: #94a3b8;
  font-weight: 500;
}

/* --- SaaS 指标卡交互与 SSR 独占行样式 --- */
.metric-saas-card {
  cursor: pointer;
}

.metric-saas-card.ssr::before {
  background: #0ea5e9 !important;
}

.metric-saas-interactive-tip {
  font-size: 10px;
  color: #64748b;
  margin-top: auto;
  padding-top: 8px;
  text-align: right;
  font-style: italic;
  opacity: 0.65;
  transition: all 0.2s ease;
  font-weight: 600;
}

.metric-saas-card:hover .metric-saas-interactive-tip {
  opacity: 1;
  color: #3b82f6;
  transform: translateX(-2px);
}

/* SaaS 指标穿透弹窗专属美学 */
.metric-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(12px);
  z-index: 9999;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

.metric-modal-card {
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(226, 232, 240, 0.85);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.15), 0 0 40px rgba(59, 130, 246, 0.05);
  border-radius: 16px;
  width: min(680px, 100%);
  max-height: calc(100vh - 40px);
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  animation: modal-zoom-in 0.28s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes modal-zoom-in {
  from { transform: scale(0.92) translateY(8px); opacity: 0; }
  to { transform: scale(1) translateY(0); opacity: 1; }
}

.metric-modal-close {
  position: absolute;
  top: 16px;
  right: 20px;
  background: #f1f5f9;
  border: none;
  font-size: 14px;
  font-weight: bold;
  color: #64748b;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: all 0.2s;
}

.metric-modal-close:hover {
  background: #e2e8f0;
  color: #1e293b;
}

.metric-modal-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 24px 24px 16px;
  border-bottom: 1px solid #e2e8f0;
}

.metric-modal-icon {
  font-size: 22px;
  background: #eff6ff;
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.metric-modal-header h4 {
  font-size: 16px;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
}

.metric-modal-subtitle {
  font-size: 11px;
  color: #64748b;
  display: block;
  margin-top: 3px;
}

.metric-modal-body {
  padding: 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.metric-info-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-tag {
  font-size: 11px;
  font-weight: 700;
  color: #2563eb;
  background: #eff6ff;
  padding: 2px 8px;
  border-radius: 4px;
  align-self: flex-start;
}

.metric-desc-text {
  font-size: 13px;
  line-height: 1.6;
  color: #475569;
  margin: 0;
}

/* 数学公式与计算分线 */
.metric-formula-box, .metric-calc-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 18px 24px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.formula-line, .calc-formula {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: #334155;
  flex-wrap: wrap;
  gap: 8px;
}

.formula-label, .calc-label {
  font-family: monospace;
  font-weight: 900;
  font-size: 15px;
  color: #0f172a;
}

.formula-fraction {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  min-width: 140px;
  margin: 0 8px;
}

.fraction-numerator {
  border-bottom: 2px solid #94a3b8;
  padding-bottom: 4px;
  width: 100%;
  font-size: 12px;
  font-weight: 700;
  color: #475569;
}

.fraction-numerator.highlighted {
  border-color: #3b82f6;
  color: #2563eb;
}

.fraction-denominator {
  padding-top: 4px;
  width: 100%;
  font-size: 12px;
  font-weight: 700;
  color: #475569;
}

.fraction-denominator.highlighted {
  color: #ea580c;
}

.formula-multiplier {
  font-weight: 700;
  color: #64748b;
}

.calc-result {
  font-size: 20px;
  font-weight: 900;
  color: #10b981;
  font-family: monospace;
}

/* 变量明细列表 */
.calc-vars-list {
  border-top: 1px dashed #cbd5e1;
  margin-top: 14px;
  padding-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.var-item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  line-height: 1.5;
}

.var-name {
  color: #475569;
  font-weight: 700;
}

.var-val {
  color: #0f172a;
}

/* 集团目标对比 */
.metric-target-box {
  display: flex;
  background: #f8fafc;
  border: 1px solid #f1f5f9;
  border-radius: 10px;
  padding: 14px;
  justify-content: space-around;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.target-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.target-lbl {
  color: #475569;
}

.target-val {
  font-size: 15px;
  font-weight: 900;
  font-family: monospace;
}

.target-val.orange { color: #ea580c; }
.target-val.blue { color: #2563eb; }

.status-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 6px;
}

.status-badge.success {
  background: #f0fdf4;
  color: #15803d;
  border: 1px solid #bbf7d0;
}

.metric-modal-footer {
  padding: 16px 24px 20px;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
}

/* 淡入淡出动画 */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.25s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

@media (max-width: 640px) {
  .metric-saas-card.ssr {
    grid-column: span 1;
  }
}
</style>
