<template>
  <div class="dispatch-info-view">
    <AppHeader />
    <main class="dispatch-main">
      <Breadcrumbs :items="breadcrumbItems" />

      <!-- 顶部 Banner 卡片 -->
      <section class="card elevated banner-card">
        <div class="banner-content">
          <div class="banner-title-row">
            <div class="banner-icon">📋</div>
            <div>
              <h2 class="banner-title">生产调度信息全景看板</h2>
            </div>
          </div>
          <div class="banner-meta">
            <span class="meta-tag">
              <span class="dot live"></span>
              库内已录入：<strong>{{ availableDates.length }}</strong> 天日报
            </span>
            <span v-if="latestDate" class="meta-tag">
              最新业务日期：<strong>{{ latestDate }}</strong>
            </span>
          </div>
        </div>
      </section>

      <!-- 1. 顶部：信息提取与入库工作台 (仅 Global_admin 可见，默认折叠收回) -->
      <section v-if="isGlobalAdmin" class="card elevated extract-card">
        <header class="section-header" @click="isExtractPanelExpanded = !isExtractPanelExpanded">
          <div class="header-left">
            <span class="header-icon">⚙️</span>
            <h3>调度信息智能提取工作台</h3>
            <span class="badge-sub">支持 DOCX / PDF 批量解析</span>
          </div>
          <button class="btn ghost btn-sm" type="button">
            {{ isExtractPanelExpanded ? '收起面板 ▲' : '展开提取面板 ▼' }}
          </button>
        </header>

        <div v-show="isExtractPanelExpanded" class="extract-body">
          <!-- 本地文件 / 文件夹上传区 -->
          <div class="upload-container">
            <!-- 隐藏的原生输入控件 -->
            <input
              ref="fileInputRef"
              type="file"
              multiple
              accept=".docx,.pdf"
              class="hidden-input"
              @change="handleFileInputChange"
            />
            <input
              ref="folderInputRef"
              type="file"
              webkitdirectory
              directory
              multiple
              class="hidden-input"
              @change="handleFolderInputChange"
            />

            <!-- 核心选择按钮区：文件与文件夹独立分离 -->
            <div class="upload-buttons-row">
              <div class="upload-btn-card" @click="triggerFileInput">
                <span class="btn-card-icon">📄</span>
                <div class="btn-card-info">
                  <span class="btn-card-title">选择文件</span>
                  <span class="btn-card-desc">支持按住 Ctrl/Shift 选择多个 DOCX / PDF</span>
                </div>
              </div>
              <div class="upload-btn-card primary-folder" @click="triggerFolderInput">
                <span class="btn-card-icon">📁</span>
                <div class="btn-card-info">
                  <span class="btn-card-title">选择整个文件夹</span>
                  <span class="btn-card-desc">自动扫描该文件夹及全部子目录下的全部调度文档</span>
                </div>
              </div>
            </div>

            <!-- 拖拽扫描辅助区 -->
            <div
              class="drop-zone"
              @dragover.prevent
              @dragenter.prevent
              @drop.prevent="handleFileDrop"
            >
              <div class="drop-prompt">
                <span class="drop-icon">📥</span>
                <p class="drop-title">或直接将单个文件、多个文件或整个文件夹拖拽至此处</p>
                <p class="drop-hint">支持深度递归解析文件夹内所有 .docx 和 .pdf 文件</p>
                <div v-if="selectedFiles.length > 0" class="upload-actions">
                  <button
                    class="btn ghost btn-sm text-danger"
                    type="button"
                    @click="clearSelectedFiles"
                  >
                    清空已选文件 (当前 {{ selectedFiles.length }} 个)
                  </button>
                </div>
              </div>
            </div>

            <!-- 已选文件简要列表 -->
            <div v-if="selectedFiles.length > 0" class="file-list-preview">
              <div class="list-title-bar">
                <span class="list-title">已准备就绪的待解析文件 (共 {{ selectedFiles.length }} 个)：</span>
                <span class="list-badge-docx">DOCX: {{ selectedDocxCount }} 个</span>
                <span class="list-badge-pdf">PDF: {{ selectedPdfCount }} 个</span>
              </div>
              <div class="file-chips">
                <span
                  v-for="(f, idx) in selectedFiles.slice(0, 20)"
                  :key="idx"
                  class="file-chip"
                >
                  <span :class="['chip-ext', f.name.toLowerCase().endsWith('.pdf') ? 'pdf' : 'docx']">
                    {{ f.name.toLowerCase().endsWith('.pdf') ? 'PDF' : 'DOCX' }}
                  </span>
                  <span class="chip-name" :title="f.name">{{ f.name }}</span>
                </span>
                <span v-if="selectedFiles.length > 20" class="chip-more">
                  ...等共 {{ selectedFiles.length }} 个文档
                </span>
              </div>
            </div>
          </div>

          <!-- 执行提取控制栏 -->
          <div class="extract-action-bar">
            <button
              class="btn primary btn-extract"
              type="button"
              :disabled="isExtracting || selectedFiles.length === 0"
              @click="startExtraction"
            >
              <span v-if="isExtracting" class="spinner"></span>
              {{ isExtracting ? '正在解析提取中，请稍候…' : '🚀 开始智能批量提取' }}
            </button>
          </div>

          <!-- 提取状态与错误通知 -->
          <div v-if="extractError" class="alert error-alert">
            ⚠️ 提取异常：{{ extractError }}
          </div>

          <!-- 提取完成后的结果看板与一键入库控制栏 -->
          <div v-if="extractSummary" class="extract-summary-card">
            <div class="summary-header">
              <span class="summary-title">🎉 提取完成报告</span>
              <span class="summary-stat">
                成功解析：<strong>{{ extractSummary.success_count }}</strong> / {{ extractSummary.total_files }} 篇 ｜
                涉及日期：<strong>{{ extractDateRangeText }}</strong>
              </span>
            </div>

            <!-- 冲突检测提示 -->
            <div v-if="extractSummary.conflict_dates && extractSummary.conflict_dates.length > 0" class="conflict-alert">
              <span class="conflict-icon">⚠️</span>
              <div class="conflict-desc">
                <strong>发现冲突预警：</strong>
                本次提取的数据中，有 <strong>{{ extractSummary.conflict_dates.length }}</strong> 天（如：{{ extractSummary.conflict_dates.slice(0, 5).join('、') }}{{ extractSummary.conflict_dates.length > 5 ? '…' : '' }}）在数据库中已有记录。
                点击“一键保存入库”时系统将提示是否覆盖更新。
              </div>
            </div>

            <div v-if="importStatusConflicts.length" class="status-review">
              <h4>机炉状态需确认（{{ importStatusConflicts.length }} 项）</h4>
              <p>表格与当日最后一条有效主设备事件不一致。事件可能与表格统计时点不同，请逐项选择；辅机投运不参与主机状态推断。</p>
              <div v-for="conflict in importStatusConflicts" :key="conflict.id" class="status-review-item">
                <strong>{{ conflict.bizDate }} · {{ conflict.device }}</strong>
                <p>原表格：{{ conflict.table_status }} <span v-if="conflict.table_text">（{{ conflict.table_text }}）</span></p>
                <p v-for="(event, index) in conflict.events" :key="index">{{ event.time }} · {{ event.raw_description }}</p>
                <label>入库依据：
                  <select v-model="statusResolutions[conflict.id]" class="form-select">
                    <option value="">请选择</option>
                    <option value="table">以原表格为准：{{ conflict.table_status }}</option>
                    <option value="events">以最后一条主设备事件为准：{{ conflict.event_status }}</option>
                  </select>
                </label>
              </div>
            </div>
            <div v-for="item in extractSummary.items" :key="item.file_name + item.biz_date">
              <p v-for="warning in item.extraction_warnings" :key="warning" class="alert">{{ item.biz_date }} · {{ warning }}</p>
            </div>

            <!-- 操作按钮组合：下载 JSON、清理残留、一键入库 -->
            <div class="summary-actions">
              <button class="btn secondary" type="button" @click="downloadResultJson">
                📥 下载标准 JSON ({{ extractSummary.success_count }} 篇)
              </button>
              <button
                class="btn primary btn-save-db"
                type="button"
                :disabled="isSavingDb || hasUnresolvedStatusConflicts"
                @click="triggerSaveToDb"
              >
                <span v-if="isSavingDb" class="spinner"></span>
                {{ isSavingDb ? '正在入库…' : '💾 一键保存入库' }}
              </button>
              <button
                v-if="extractSummary.token"
                class="btn ghost text-muted"
                type="button"
                @click="cleanupTemp"
              >
                🧹 清理服务器残留临时文件
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- 2. 下半部分：调度信息多维查询与综合参考展板 -->
      <section class="card elevated dashboard-card">
        <!-- 综合过滤工具栏 -->
        <div class="query-toolbar">
          <div class="toolbar-left">
            <div class="filter-item">
              <label>📅 业务日期：</label>
              <div class="date-select-group">
                <button
                  class="btn icon-btn"
                  type="button"
                  title="前一天"
                  :disabled="!hasPrevDate"
                  @click="shiftDate(-1)"
                >
                  ◀
                </button>
                <select v-model="currentBizDate" class="form-select date-select" @change="onDateChanged">
                  <option v-if="!currentBizDate" value="">请选择业务日期</option>
                  <option v-for="d in availableDates" :key="d" :value="d">
                    {{ d }}
                  </option>
                </select>
                <button
                  class="btn icon-btn"
                  type="button"
                  title="后一天"
                  :disabled="!hasNextDate"
                  @click="shiftDate(1)"
                >
                  ▶
                </button>
                <button
                  class="btn ghost btn-sm"
                  type="button"
                  :disabled="currentBizDate === latestDate"
                  @click="jumpToLatestDate"
                >
                  最新一天
                </button>
              </div>
            </div>

            <div class="filter-item search-item">
              <label>🔍 关键字：</label>
              <div class="search-input-group">
                <input
                  v-model="searchKeyword"
                  type="text"
                  class="form-input search-input"
                  placeholder="检索单位、事件、抢修工单、DN1100、地点…"
                  @keyup.enter="handleSearch"
                />
                <button class="btn secondary btn-sm" type="button" @click="handleSearch">
                  搜索
                </button>
                <button
                  v-if="searchKeyword"
                  class="btn ghost btn-sm"
                  type="button"
                  @click="clearSearch"
                >
                  清除
                </button>
              </div>
            </div>
          </div>

          <div class="toolbar-right">
            <button class="btn ghost btn-sm" type="button" :disabled="isLoadingData" @click="fetchCurrentData">
              🔄 刷新
            </button>
          </div>
        </div>

        <!-- 初次载入且无任何已有数据时，展示全屏初始加载状态 -->
        <div v-if="isLoadingData && !currentReport" class="state-container">
          <div class="spinner large"></div>
          <p>正在读取调度综合数据…</p>
        </div>

        <div v-else-if="!currentReport" class="state-container empty">
          <span class="empty-icon">📭</span>
          <p class="empty-title">当前日期暂无已入库的调度数据</p>
          <p class="empty-hint">请在上方的智能提取工作台上传文件或文件夹开始提取入库</p>
        </div>

        <!-- 调度数据展示全景展板（就地无感平滑更新，绝不销毁DOM和引起滚动条塌陷） -->
        <div v-else :class="['dashboard-body', { 'is-fetching': isLoadingData }]">
          <!-- 切换日期时的平滑半透明遮罩与微提示，视口不跳动 -->
          <div v-if="isLoadingData" class="fetching-overlay">
            <div class="fetching-pill">
              <span class="spinner fetching-spinner"></span>
              <span>正在读取 {{ currentBizDate }} 调度数据…</span>
            </div>
          </div>
          <!-- 报告抬头元数据 -->
          <div class="report-meta-header">
            <div class="meta-main">
              <h3 class="report-title">
                主城区调度生产日报 · {{ currentReport.biz_date }}
              </h3>
              <div class="meta-tags">
                <span class="tag-officer">👤 值班人员：{{ currentReport.duty_officers || '未标明' }}</span>
                <span v-if="currentReport.publish_date" class="tag-pub">
                  📅 发布日期：{{ currentReport.publish_date }}
                </span>
                <span class="tag-file">📄 来源文档：{{ currentReport.file_name || '系统导入' }}</span>
              </div>
            </div>
            <!-- 天气看板 -->
            <div class="weather-box">
              <div class="weather-icon">🌡️</div>
              <div class="weather-details">
                <div class="weather-desc">天气日期：{{ currentReport.weather?.forecast_date || '未提供' }}（文档预报）</div>
                <div class="weather-temp">
                  {{ formatTemp(currentReport.weather?.temp_min, currentReport.weather?.temp_max) }}
                </div>
                <div class="weather-desc">
                  {{ currentReport.weather?.weather_desc || '天气未提供' }} ｜
                  {{ currentReport.weather?.wind || '风况未提供' }} ｜
                  相对湿度：{{ currentReport.weather?.humidity === 0 ? 0 : currentReport.weather?.humidity || '未提供' }}
                </div>
              </div>
            </div>
          </div>

          <div v-if="currentReport.status_conflicts?.length" class="status-review">
            <strong>机炉表格与事件存在差异</strong>
            <p v-for="conflict in currentReport.status_conflicts" :key="conflict.id">
              {{ conflict.device }}：原表 {{ conflict.table_status }}，事件推断 {{ conflict.event_status }}；
              {{ conflict.resolution ? `导入时选择以${conflict.resolution === 'events' ? '事件' : '表格'}为准` : '历史记录尚未确认，暂按原表格展示，请重新上传核对' }}。
            </p>
          </div>
          <!-- 宏观核心产耗指标卡片网格 -->
          <p v-for="warning in currentReport.extraction_warnings" :key="warning" class="status-review">{{ warning }}</p>
          <div class="kpi-grid">
            <div class="kpi-card coal-card">
              <div class="kpi-title">
                <span>当日总耗煤量</span>
                <span class="kpi-unit">吨</span>
              </div>
              <div class="kpi-value">
                {{ formatNum(currentReport.total_coal_consumed) }}
              </div>
              <div class="kpi-sub">
                <span>北海: {{ formatNum(currentReport.production_stats?.beihai_actual_coal) }} t</span>
                <span>香海: {{ formatNum(currentReport.production_stats?.xianghai_actual_coal) }} t</span>
              </div>
            </div>

            <div class="kpi-card power-card">
              <div class="kpi-title">
                <span>当日总发电量</span>
                <span class="kpi-unit">万度</span>
              </div>
              <div class="kpi-value text-power">
                {{ formatNum(currentReport.total_power_generated) }}
              </div>
              <div class="kpi-sub">
                <span>北海: {{ formatNum(currentReport.production_stats?.beihai_actual_power) }}</span>
                <span>香海: {{ formatNum(currentReport.production_stats?.xianghai_actual_power) }}</span>
              </div>
            </div>

            <div class="kpi-card heat-card">
              <div class="kpi-title">
                <span>当日总供热量</span>
                <span class="kpi-unit">GJ</span>
              </div>
              <div class="kpi-value text-heat">
                {{ formatNum(currentReport.total_heat_supplied) }}
              </div>
              <div class="kpi-sub">
                <span>北海: {{ formatNum(currentReport.production_stats?.beihai_actual_heat) }}</span>
                <span>香海: {{ formatNum(currentReport.production_stats?.xianghai_actual_heat) }}</span>
              </div>
            </div>

            <div class="kpi-card water-card">
              <div class="kpi-title">
                <span>累计补水量</span>
                <span class="kpi-unit">吨</span>
              </div>
              <div class="kpi-value text-water">
                {{ formatNum(currentReport.total_water_replenished) }}
              </div>
              <div class="kpi-sub">
                <span>#1首站: {{ formatNum(currentReport.water_replenishment?.first_station_1_water_tons) }} t</span>
                <span>#2首站: {{ formatNum(currentReport.water_replenishment?.first_station_2_water_tons) }} t</span>
              </div>
            </div>
          </div>

          <!-- 全量平铺数据板块流（一览通览各核心维度） -->
          <div class="dashboard-sections-flow">
            <!-- 板块 1: 机炉拓扑状态视图 -->
            <section class="dashboard-section-block">
              <div class="section-block-header">
                <div class="section-block-title">
                  <span class="section-block-icon">🏭</span>
                  <h4>机炉运行拓扑矩阵</h4>
                  <span class="section-badge">共 {{ currentReport.boiler_turbine_status?.length || 0 }} 台设备</span>
                </div>
              </div>
              <div class="facilities-grid">
                <div
                  v-for="group in groupedFacilities"
                  :key="group.plant"
                  class="plant-facilities-card"
                >
                  <div class="plant-card-header">
                    <span class="plant-name">{{ group.plant }}</span>
                    <span class="plant-running-summary">{{ group.runningSummary }}</span>
                  </div>

                  <!-- 1. 燃气锅炉：仅一个“锅炉”统一标头，下方设备分为左(1-5)右(6-10)严格等宽两列显示 -->
                  <div v-if="group.isSplitBoilers" class="plant-unified-group">
                    <div class="col-header">
                      <span class="col-icon">🔥</span>
                      <span class="col-title">锅炉</span>
                      <span class="col-stat">({{ group.runningBoilers }}/{{ group.boilers.length }} 运行)</span>
                    </div>

                    <div class="plant-split-columns">
                      <!-- 左列: 1-5号锅炉 -->
                      <div class="plant-col col-left">
                        <div class="facility-badges">
                          <div
                            v-for="(fac, fIdx) in group.boilersLeft"
                            :key="fIdx"
                            :class="['fac-badge', fac.status === '运行' ? 'status-run' : fac.status === '备用' ? 'status-standby' : fac.status === '启动中' ? 'status-starting' : 'status-repair']"
                          >
                            <span class="fac-name" :title="fac.standard_name || fac.raw_name">{{ fac.standard_name || fac.raw_name }}</span>
                            <div class="fac-meta">
                              <span
                                v-if="fac.startTime"
                                class="fac-start-pill"
                                :title="`【${fac.startTime} 主设备事件】\n${fac.startDesc}`"
                              >
                                {{ fac.startTime }} {{ fac.eventAction }}
                              </span>
                              <span class="fac-status-tag">{{ fac.status }}</span>
                            </div>
                          </div>
                        </div>
                      </div>

                      <!-- 右列: 6-10号锅炉 (严格等宽) -->
                      <div class="plant-col col-right">
                        <div class="facility-badges">
                          <div
                            v-for="(fac, fIdx) in group.boilersRight"
                            :key="fIdx"
                            :class="['fac-badge', fac.status === '运行' ? 'status-run' : fac.status === '备用' ? 'status-standby' : fac.status === '启动中' ? 'status-starting' : 'status-repair']"
                          >
                            <span class="fac-name" :title="fac.standard_name || fac.raw_name">{{ fac.standard_name || fac.raw_name }}</span>
                            <div class="fac-meta">
                              <span
                                v-if="fac.startTime"
                                class="fac-start-pill"
                                :title="`【${fac.startTime} 主设备事件】\n${fac.startDesc}`"
                              >
                                {{ fac.startTime }} {{ fac.eventAction }}
                              </span>
                              <span class="fac-status-tag">{{ fac.status }}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 2. 常规主体分栏：左机右炉严格等宽分列 (或仅炉单列全宽) -->
                  <div v-else :class="['plant-split-columns', { 'single-column': group.turbines.length === 0 || group.boilers.length === 0 }]">
                    <!-- 左栏: 汽机 (机组) -->
                    <div v-if="group.turbines.length > 0" class="plant-col col-left col-turbine">
                      <div class="col-header">
                        <span class="col-icon">⚡</span>
                        <span class="col-title">机组</span>
                        <span class="col-stat">({{ group.runningTurbines }}/{{ group.turbines.length }} 运行)</span>
                      </div>
                      <div class="facility-badges">
                        <div
                          v-for="(fac, fIdx) in group.turbines"
                          :key="fIdx"
                          :class="['fac-badge', fac.status === '运行' ? 'status-run' : fac.status === '备用' ? 'status-standby' : fac.status === '启动中' ? 'status-starting' : 'status-repair']"
                        >
                          <span class="fac-name" :title="fac.standard_name || fac.raw_name">{{ fac.standard_name || fac.raw_name }}</span>
                          <div class="fac-meta">
                            <span
                              v-if="fac.startTime"
                              class="fac-start-pill"
                              :title="`【${fac.startTime} 主设备事件】\n${fac.startDesc}`"
                            >
                              {{ fac.startTime }} {{ fac.eventAction }}
                            </span>
                            <span class="fac-status-tag">{{ fac.status }}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- 右栏: 锅炉 (有汽机时严格等宽居右) -->
                    <div v-if="group.boilers.length > 0" :class="['plant-col', 'col-boiler', { 'col-right': group.turbines.length > 0 }]">
                      <div class="col-header">
                        <span class="col-icon">🔥</span>
                        <span class="col-title">锅炉</span>
                        <span class="col-stat">({{ group.runningBoilers }}/{{ group.boilers.length }} 运行)</span>
                      </div>
                      <div class="facility-badges">
                        <div
                          v-for="(fac, fIdx) in group.boilers"
                          :key="fIdx"
                          :class="['fac-badge', fac.status === '运行' ? 'status-run' : fac.status === '备用' ? 'status-standby' : fac.status === '启动中' ? 'status-starting' : 'status-repair']"
                        >
                          <span class="fac-name" :title="fac.standard_name || fac.raw_name">{{ fac.standard_name || fac.raw_name }}</span>
                          <div class="fac-meta">
                            <span
                              v-if="fac.startTime"
                              class="fac-start-pill"
                              :title="`【${fac.startTime} 主设备事件】\n${fac.startDesc}`"
                            >
                              {{ fac.startTime }} {{ fac.eventAction }}
                            </span>
                            <span class="fac-status-tag">{{ fac.status }}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- 其他设备（若有） -->
                    <div v-if="group.others.length > 0" class="plant-col col-other">
                      <div class="col-header">
                        <span class="col-icon">⚙️</span>
                        <span class="col-title">其他设备</span>
                        <span class="col-stat">({{ group.others.length }} 台)</span>
                      </div>
                      <div class="facility-badges">
                        <div
                          v-for="(fac, fIdx) in group.others"
                          :key="fIdx"
                          :class="['fac-badge', fac.status === '运行' ? 'status-run' : fac.status === '备用' ? 'status-standby' : fac.status === '启动中' ? 'status-starting' : 'status-repair']"
                        >
                          <span class="fac-name" :title="fac.standard_name || fac.raw_name">{{ fac.standard_name || fac.raw_name }}</span>
                          <div class="fac-meta">
                            <span
                              v-if="fac.startTime"
                              class="fac-start-pill"
                              :title="`【${fac.startTime} 主设备事件】\n${fac.startDesc}`"
                            >
                              {{ fac.startTime }} {{ fac.eventAction }}
                            </span>
                            <span class="fac-status-tag">{{ fac.status }}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <!-- 板块 2: 首站运行工况表 -->
            <section class="dashboard-section-block">
              <div class="section-block-header">
                <div class="section-block-title">
                  <span class="section-block-icon">💧</span>
                  <h4>首站工况与温压差</h4>
                  <span class="section-badge">共 {{ currentReport.first_stations?.length || 0 }} 个首站</span>
                </div>
              </div>
              <div class="table-container">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>电厂主体</th>
                      <th>首站名称</th>
                      <th>循环泵方式</th>
                      <th>循环流量 (t/h)</th>
                      <th>供/回压力 (MPa)</th>
                      <th>压差 (MPa)</th>
                      <th>供/回温度 (℃)</th>
                      <th>温差 (℃)</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(st, sIdx) in currentReport.first_stations" :key="sIdx">
                      <td><strong>{{ st.plant }}</strong></td>
                      <td>{{ st.station_name }}</td>
                      <td>{{ st.pump_count ? `${st.pump_count} 台循环泵` : '—' }}</td>
                      <td class="text-num">{{ formatNum(st.flow_rate_th) }}</td>
                      <td class="text-num">
                        {{ st.supply_pressure_mpa != null ? `${st.supply_pressure_mpa} / ${st.return_pressure_mpa}` : '—' }}
                      </td>
                      <td class="text-num">
                        <span v-if="st.pressure_diff_mpa != null" class="badge-blue">
                          {{ st.pressure_diff_mpa }}
                        </span>
                        <span v-else>—</span>
                      </td>
                      <td class="text-num">
                        {{ st.supply_temp_c != null ? `${st.supply_temp_c} / ${st.return_temp_c}` : '—' }}
                      </td>
                      <td class="text-num">
                        <span v-if="st.temp_diff_c != null" class="badge-orange">
                          {{ st.temp_diff_c }} ℃
                        </span>
                        <span v-else>—</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            <!-- 板块 3: 蒸汽网口与燃煤库存 -->
            <section class="dashboard-section-block">
              <div class="section-block-header">
                <div class="section-block-title">
                  <span class="section-block-icon">♨️</span>
                  <h4>蒸汽网口与燃煤库存</h4>
                </div>
              </div>
              <div class="sub-split-grid">
                <!-- 蒸汽网口卡片 -->
                <div class="card elevated inner-card">
                  <h4 class="card-title">💨 蒸汽网口运行情况</h4>
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th>网口名称</th>
                        <th>运行状态</th>
                        <th>压力 (MPa)</th>
                        <th>流量 (t/h)</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(stm, smIdx) in currentReport.steam_networks" :key="smIdx">
                        <td>{{ stm.network_name }}</td>
                        <td>
                          <span :class="['status-pill', stm.status === '投运' ? 'run' : 'stop']">
                            {{ stm.status }}
                          </span>
                        </td>
                        <td class="text-num">{{ stm.pressure_mpa != null ? stm.pressure_mpa : '—' }}</td>
                        <td class="text-num">{{ stm.flow_th != null ? stm.flow_th : '—' }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <!-- 燃煤库存表 -->
                <div class="card elevated inner-card">
                  <h4 class="card-title">🪨 燃煤进耗存统计</h4>
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th>单位 / 口径</th>
                        <th>进煤 (吨)</th>
                        <th>耗煤 (吨)</th>
                        <th>存煤 (吨)</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(coal, cIdx) in currentReport.coal_stats" :key="cIdx">
                        <td><strong>{{ coal.standard_org || coal.category }}</strong></td>
                        <td class="text-num">{{ formatNum(coal.in_coal_tons) }}</td>
                        <td class="text-num">{{ formatNum(coal.consumed_coal_tons) }}</td>
                        <td class="text-num">{{ formatNum(coal.storage_coal_tons) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </section>

            <!-- 板块 4: 调度事件 -->
            <section class="dashboard-section-block">
              <div class="section-block-header">
                <div class="section-block-title">
                  <span class="section-block-icon">📋</span>
                  <h4>调度事件</h4>
                  <span class="section-badge">共 {{ filteredEvents.length }} 条记录</span>
                </div>
              </div>
              <div class="events-toolbar">
                <div class="org-filter-pills">
                  <button
                    :class="['filter-pill', { active: eventOrgFilter === 'ALL' }]"
                    type="button"
                    @click="eventOrgFilter = 'ALL'"
                  >
                    全部主体
                  </button>
                  <button
                    v-for="org in availableEventOrgs"
                    :key="org"
                    :class="['filter-pill', { active: eventOrgFilter === org }]"
                    type="button"
                    @click="eventOrgFilter = org"
                  >
                    {{ org }}
                  </button>
                </div>

                <label class="checkbox-label">
                  <input v-model="onlyWorkTickets" type="checkbox" />
                  仅看抢修工作票
                </label>
              </div>

              <div v-if="filteredEvents.length === 0" class="empty-events">
                无匹配的操作或抢修记录
              </div>

              <div v-else class="event-timeline">
                <div
                  v-for="(ev, eIdx) in filteredEvents"
                  :key="eIdx"
                  :class="['event-card', { 'is-ticket': ev.is_ticket }]"
                >
                  <div class="event-header">
                    <div class="event-meta-left">
                      <span v-if="ev.time" class="event-time">⏰ {{ ev.time }}</span>
                      <span class="event-org">{{ ev.responsible_org }}</span>
                      <span v-if="ev.is_ticket" class="badge-ticket">🎫 抢修工作票</span>
                      <span v-else class="badge-op">🔧 运行操作</span>
                      <span v-if="ev.pipe_size" class="badge-pipe">
                        管径: {{ ev.pipe_size }}
                      </span>
                    </div>
                    <span v-if="ev.time_range" class="event-duration">
                      工期：{{ ev.time_range }}
                    </span>
                  </div>
                  <div class="event-content">
                    {{ ev.raw_description }}
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>
      </section>

      <!-- 覆盖确认对话框 -->
      <div v-if="showOverwriteModal" class="modal-backdrop" @click.self="showOverwriteModal = false">
        <div class="modal-card">
          <div class="modal-header">
            <h3>⚠️ 存在同日数据冲突确认 (共 {{ conflictDatesToConfirm.length }} 天)</h3>
            <button class="modal-close-icon" type="button" title="关闭" @click="showOverwriteModal = false">✕</button>
          </div>
          <div class="modal-body">
            <div class="conflict-summary-banner">
              检测到当前待入库数据中，有 <strong class="text-danger">{{ conflictDatesToConfirm.length }}</strong> 天在数据库中已有记录。
              <div v-if="conflictDatesToConfirm.length > 0" class="conflict-range-text">
                涉及跨度：{{ conflictDatesToConfirm[0] }} 至 {{ conflictDatesToConfirm[conflictDatesToConfirm.length - 1] }}
              </div>
            </div>

            <p class="section-hint">冲突日期明细（可滚动翻阅）：</p>
            <div class="conflict-date-list">
              <span v-for="cd in conflictDatesToConfirm" :key="cd" class="conflict-date-chip">
                {{ cd }}
              </span>
            </div>
            <p class="modal-warn">覆盖更新将使用当前提取的内容替换数据库已有记录，此操作不可撤销，是否确认覆盖？</p>
          </div>
          <div class="modal-footer">
            <button class="btn ghost" type="button" @click="showOverwriteModal = false">
              取消入库
            </button>
            <button class="btn primary btn-danger" type="button" @click="confirmOverwriteSave">
              确认覆盖更新 (共 {{ conflictDatesToConfirm.length }} 篇)
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { getProjectNameById, ensureProjectsLoaded } from '../composables/useProjects'
import { useAuthStore } from '../store/auth'
import {
  extractDispatchFiles,
  getDispatchDownloadJsonUrl,
  downloadDispatchJson,
  cleanupDispatchTemp,
  saveDispatchData,
  queryDispatchData,
  fetchDispatchDates
} from '../services/dispatchApi'

const auth = useAuthStore()
const statusResolutions = ref({})
const importStatusConflicts = computed(() => (extractSummary.value?.items || []).flatMap(item =>
  (item.status_conflicts || []).map(conflict => ({ ...conflict, bizDate: item.biz_date }))
))
const hasUnresolvedStatusConflicts = computed(() => importStatusConflicts.value.some(
  conflict => !['table', 'events'].includes(statusResolutions.value[conflict.id])
))
const route = useRoute()
const projectKey = computed(() => route.params.projectKey || 'daily_report_25_26')
const projectName = computed(() => getProjectNameById(projectKey.value) || '2026-2027供暖期生产日报')

const pageDisplayName = computed(() => {
  const raw = route.query.pageName
  if (typeof raw === 'string' && raw.trim()) {
    return raw.trim()
  }
  return '调度信息'
})

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: projectName.value, to: `/projects/${encodeURIComponent(projectKey.value)}/pages` },
  { label: pageDisplayName.value, to: null },
])

// 权限判定：仅 Global_admin 可见提取工作台
const isGlobalAdmin = computed(() => {
  const grp = String(auth.user?.group || auth.user?.role || '').trim()
  return grp === 'Global_admin' || grp.toLowerCase() === 'global_admin' || Boolean(auth.canAccessAdminConsole)
})

// 提取工作台状态 (默认收回)
const isExtractPanelExpanded = ref(false)
const selectedFiles = ref([])
const isExtracting = ref(false)
const extractError = ref('')
const extractSummary = ref(null)

const fileInputRef = ref(null)
const folderInputRef = ref(null)

const selectedDocxCount = computed(() => {
  return selectedFiles.value.filter((f) => f.name.toLowerCase().endsWith('.docx')).length
})

const selectedPdfCount = computed(() => {
  return selectedFiles.value.filter((f) => f.name.toLowerCase().endsWith('.pdf')).length
})

// 入库与覆盖弹窗状态
const isSavingDb = ref(false)
const showOverwriteModal = ref(false)
const conflictDatesToConfirm = ref([])

// 调度看板状态
const availableDates = ref([])
const currentBizDate = ref('')
const searchKeyword = ref('')
const isLoadingData = ref(false)
const currentReport = ref(null)

// 事件过滤状态
const eventOrgFilter = ref('ALL')
const onlyWorkTickets = ref(false)

const latestDate = computed(() => availableDates.value[0] || '')

const extractDateRangeText = computed(() => {
  if (!extractSummary.value || !extractSummary.value.items || extractSummary.value.items.length === 0) return '—'
  const dates = extractSummary.value.items.map((x) => x.biz_date).filter(Boolean)
  if (!dates.length) return '—'
  return `${dates[0]} 至 ${dates[dates.length - 1]}`
})

const hasPrevDate = computed(() => {
  if (!currentBizDate.value || !availableDates.value.length) return false
  const idx = availableDates.value.indexOf(currentBizDate.value)
  return idx < availableDates.value.length - 1
})

const hasNextDate = computed(() => {
  if (!currentBizDate.value || !availableDates.value.length) return false
  const idx = availableDates.value.indexOf(currentBizDate.value)
  return idx > 0
})

const STATUS_PRIORITY = {
  '启动中': 1.5,
  '运行': 1,
  '备用': 2,
  '检修': 3
}

function getStatusWeight(status) {
  const s = String(status || '').trim()
  return STATUS_PRIORITY[s] || 99
}

/**
 * 设备多级排序：
 * 1. 优先按运行状态：运行 > 启动中 > 备用 > 检修 > 其他
 * 2. 同状态下按设备序号自然数字升序：#1, #2, #3 ... #10
 */
function sortFacilitiesByStatusAndNumber(facList) {
  return [...facList].sort((a, b) => {
    // 第一级：运行 > 备用 > 检修
    const weightA = getStatusWeight(a.status)
    const weightB = getStatusWeight(b.status)
    if (weightA !== weightB) {
      return weightA - weightB
    }

    // 第二级：同状态下按设备编号数字升序
    const nameA = a.standard_name || a.raw_name || ''
    const nameB = b.standard_name || b.raw_name || ''
    const numA = parseInt((nameA.match(/\d+/) || [0])[0], 10)
    const numB = parseInt((nameB.match(/\d+/) || [0])[0], 10)
    if (numA !== numB) {
      return numA - numB
    }

    // 第三级：兜底字符拼音比对
    return nameA.localeCompare(nameB, 'zh-CN')
  })
}

const groupedFacilities = computed(() => {
  if (!currentReport.value || !Array.isArray(currentReport.value.boiler_turbine_status)) return []
  const map = {}
  for (const rawFac of currentReport.value.boiler_turbine_status) {
    const plant = rawFac.unit_or_plant || '其他'
    if (!map[plant]) {
      map[plant] = []
    }
    // 后端只提供直接作用于主设备的事件，辅机投运不会生成主机标签。
    const startInfo = rawFac.main_events?.at(-1)
    map[plant].push({
      ...rawFac,
      startTime: startInfo ? startInfo.time : null,
      startDesc: startInfo?.raw_description || '',
      eventAction: startInfo?.action || ''
    })
  }

  return Object.keys(map).map((k) => {
    const allItems = map[k]
    const boilers = sortFacilitiesByStatusAndNumber(
      allItems.filter(
        (f) => f.facility_type === '锅炉' || (f.standard_name || f.raw_name || '').includes('炉')
      )
    )
    const turbines = sortFacilitiesByStatusAndNumber(
      allItems.filter(
        (f) => f.facility_type === '汽机' || (f.standard_name || f.raw_name || '').includes('机')
      )
    )
    const others = sortFacilitiesByStatusAndNumber(
      allItems.filter(
        (f) => !boilers.includes(f) && !turbines.includes(f)
      )
    )

    const runningBoilers = boilers.filter((f) => f.status === '运行').length
    const runningTurbines = turbines.filter((f) => f.status === '运行').length

    // 燃气锅炉等大型锅炉主体：分两列等宽显示（左侧 1-5，右侧 6-10）
    const isSplitBoilers = turbines.length === 0 && (k.includes('燃气') || boilers.length > 5)
    let boilersLeft = []
    let boilersRight = []
    let runningBoilersLeft = 0
    let runningBoilersRight = 0

    if (isSplitBoilers) {
      boilersLeft = sortFacilitiesByStatusAndNumber(
        boilers.filter((f) => {
          const num = parseInt(((f.standard_name || f.raw_name || '').match(/\d+/) || [0])[0], 10)
          return num >= 1 && num <= 5
        })
      )
      boilersRight = sortFacilitiesByStatusAndNumber(
        boilers.filter((f) => {
          const num = parseInt(((f.standard_name || f.raw_name || '').match(/\d+/) || [0])[0], 10)
          return num > 5
        })
      )
      runningBoilersLeft = boilersLeft.filter((f) => f.status === '运行').length
      runningBoilersRight = boilersRight.filter((f) => f.status === '运行').length
    }

    let runningSummary = ''
    if (turbines.length > 0 && boilers.length > 0) {
      runningSummary = `运行：${runningTurbines}机 ${runningBoilers}炉`
    } else if (turbines.length > 0) {
      runningSummary = `运行：${runningTurbines}机`
    } else if (boilers.length > 0) {
      runningSummary = `运行：${runningBoilers}炉`
    } else {
      const runningCount = allItems.filter((f) => f.status === '运行').length
      runningSummary = `运行：${runningCount}台`
    }

    const startingCount = allItems.filter(f => f.status === '启动中').length
    if (startingCount) runningSummary += ` · 启动中 ${startingCount} 台`
    return {
      plant: k,
      items: allItems,
      boilers,
      turbines,
      others,
      runningBoilers,
      runningTurbines,
      runningSummary,
      isSplitBoilers,
      boilersLeft,
      boilersRight,
      runningBoilersLeft,
      runningBoilersRight
    }
  })
})

const availableEventOrgs = computed(() => {
  if (!currentReport.value || !Array.isArray(currentReport.value.operations_and_tickets)) return []
  const set = new Set()
  for (const ev of currentReport.value.operations_and_tickets) {
    if (ev.responsible_org) set.add(ev.responsible_org)
  }
  return Array.from(set)
})

const filteredEvents = computed(() => {
  if (!currentReport.value || !Array.isArray(currentReport.value.operations_and_tickets)) return []
  return currentReport.value.operations_and_tickets.filter((ev) => {
    if (eventOrgFilter.value !== 'ALL' && ev.responsible_org !== eventOrgFilter.value) {
      return false
    }
    if (onlyWorkTickets.value && !ev.is_ticket) {
      return false
    }
    if (searchKeyword.value) {
      const kw = searchKeyword.value.toLowerCase()
      const desc = (ev.raw_description || '').toLowerCase()
      const org = (ev.responsible_org || '').toLowerCase()
      const pipe = (ev.pipe_size || '').toLowerCase()
      if (!desc.includes(kw) && !org.includes(kw) && !pipe.includes(kw)) {
        return false
      }
    }
    return true
  })
})

onMounted(async () => {
  ensureProjectsLoaded().catch(() => {})
  await loadAvailableDates()
  if (availableDates.value.length > 0) {
    currentBizDate.value = availableDates.value[0]
    await fetchCurrentData()
  }
})

async function loadAvailableDates() {
  try {
    const res = await fetchDispatchDates(projectKey.value)
    if (res?.ok && Array.isArray(res.dates)) {
      availableDates.value = res.dates
    }
  } catch (err) {
    console.error('Failed to load dispatch dates:', err)
  }
}

function triggerFileInput() {
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
    fileInputRef.value.click()
  }
}

function triggerFolderInput() {
  if (folderInputRef.value) {
    folderInputRef.value.value = ''
    folderInputRef.value.click()
  }
}

function handleFileInputChange(e) {
  const files = Array.from(e.target.files || [])
  addFiles(files)
}

function handleFolderInputChange(e) {
  const files = Array.from(e.target.files || [])
  const valid = files.filter((f) => {
    const n = f.name.toLowerCase()
    return n.endsWith('.docx') || n.endsWith('.pdf')
  })
  if (valid.length === 0) {
    alert('所选文件夹中未找到有效的 .docx 或 .pdf 调度文件')
    return
  }
  addFiles(valid)
}

// 递归扫描拖拽的文件/文件夹 Entry
async function scanEntry(entry) {
  if (!entry) return []
  if (entry.isFile) {
    return new Promise((resolve) => {
      entry.file((file) => {
        const name = (file.name || '').toLowerCase()
        if (name.endsWith('.docx') || name.endsWith('.pdf')) {
          resolve([file])
        } else {
          resolve([])
        }
      }, () => resolve([]))
    })
  } else if (entry.isDirectory) {
    const reader = entry.createReader()
    return new Promise((resolve) => {
      const allFiles = []
      const readNext = () => {
        reader.readEntries(async (entries) => {
          if (!entries || entries.length === 0) {
            resolve(allFiles)
          } else {
            for (const childEntry of entries) {
              const childFiles = await scanEntry(childEntry)
              allFiles.push(...childFiles)
            }
            readNext()
          }
        }, () => resolve(allFiles))
      }
      readNext()
    })
  }
  return []
}

async function handleFileDrop(e) {
  const items = e.dataTransfer.items
  if (items && items.length > 0) {
    const collectedFiles = []
    for (let i = 0; i < items.length; i++) {
      const entry = items[i].webkitGetAsEntry ? items[i].webkitGetAsEntry() : null
      if (entry) {
        const files = await scanEntry(entry)
        collectedFiles.push(...files)
      }
    }
    if (collectedFiles.length > 0) {
      addFiles(collectedFiles)
      return
    }
  }
  const files = Array.from(e.dataTransfer.files || [])
  addFiles(files)
}

function addFiles(files) {
  const valid = files.filter((f) => {
    const n = f.name.toLowerCase()
    return n.endsWith('.docx') || n.endsWith('.pdf')
  })
  if (valid.length === 0) {
    alert('所选内容中未包含 .docx 或 .pdf 调度文件')
    return
  }
  // 去重添加
  const existingNames = new Set(selectedFiles.value.map((f) => f.name))
  const newFiles = valid.filter((f) => !existingNames.has(f.name))
  selectedFiles.value = [...selectedFiles.value, ...newFiles]
}

function clearSelectedFiles() {
  selectedFiles.value = []
  if (fileInputRef.value) fileInputRef.value.value = ''
  if (folderInputRef.value) folderInputRef.value.value = ''
}

async function startExtraction() {
  if (selectedFiles.value.length === 0) {
    extractError.value = '请先选择待提取的调度文件或文件夹'
    return
  }

  isExtracting.value = true
  extractError.value = ''
  extractSummary.value = null
  statusResolutions.value = {}

  try {
    const formData = new FormData()
    for (const f of selectedFiles.value) {
      formData.append('files', f)
    }

    const res = await extractDispatchFiles(projectKey.value, formData, auth.token)
    if (res?.ok) {
      extractSummary.value = res
      statusResolutions.value = Object.fromEntries(importStatusConflicts.value.map(c => [c.id, '']))
    } else {
      throw new Error(res?.message || '提取失败')
    }
  } catch (err) {
    extractError.value = err.message || '提取过程发生异常'
  } finally {
    isExtracting.value = false
  }
}

async function downloadResultJson() {
  if (!extractSummary.value?.token) return
  try {
    await downloadDispatchJson(projectKey.value, extractSummary.value.token, auth.token)
  } catch (err) {
    alert('下载文件失败: ' + err.message)
  }
}

async function cleanupTemp() {
  if (!extractSummary.value?.token) return
  try {
    await cleanupDispatchTemp(projectKey.value, extractSummary.value.token)
    alert('临时文件已成功清理！')
    extractSummary.value.token = null
  } catch (err) {
    alert('清理失败：' + err.message)
  }
}

async function triggerSaveToDb() {
  if (!extractSummary.value) return
  if (hasUnresolvedStatusConflicts.value) return
  isSavingDb.value = true
  try {
    const payload = {
      token: extractSummary.value.token,
      reports: extractSummary.value.items,
      overwrite: false,
      status_resolutions: statusResolutions.value
    }
    const res = await saveDispatchData(projectKey.value, payload)
    if (res.has_conflict) {
      conflictDatesToConfirm.value = res.conflict_dates || []
      showOverwriteModal.value = true
    } else if (res.ok) {
      alert(`保存成功！新增 ${res.inserted} 条，更新 ${res.updated} 条。`)
      await loadAvailableDates()
      if (res.items?.[0]?.biz_date) {
        currentBizDate.value = res.items[0].biz_date
      }
      await fetchCurrentData()
    } else {
      throw new Error(res.message || '请确认全部状态冲突后重试')
    }
  } catch (err) {
    alert('入库失败：' + err.message)
  } finally {
    isSavingDb.value = false
  }
}

async function confirmOverwriteSave() {
  if (hasUnresolvedStatusConflicts.value) return
  showOverwriteModal.value = false
  isSavingDb.value = true
  try {
    const payload = {
      token: extractSummary.value.token,
      reports: extractSummary.value.items,
      overwrite: true,
      status_resolutions: statusResolutions.value
    }
    const res = await saveDispatchData(projectKey.value, payload)
    if (res.ok) {
      alert(`覆盖入库完成！新增 ${res.inserted} 条，更新覆盖 ${res.updated} 条。`)
      await loadAvailableDates()
      await fetchCurrentData()
    } else {
      throw new Error(res.message || '覆盖保存失败，请重新核对')
    }
  } catch (err) {
    alert('覆盖保存失败：' + err.message)
  } finally {
    isSavingDb.value = false
  }
}

async function fetchCurrentData() {
  if (!currentBizDate.value) return
  isLoadingData.value = true
  try {
    const res = await queryDispatchData(projectKey.value, {
      biz_date: currentBizDate.value
    })
    if (res?.items && res.items.length > 0) {
      currentReport.value = res.items[0]
    } else {
      currentReport.value = null
    }
  } catch (err) {
    console.error('Fetch dispatch data failed:', err)
  } finally {
    isLoadingData.value = false
  }
}

function onDateChanged() {
  fetchCurrentData()
}

function shiftDate(step) {
  const idx = availableDates.value.indexOf(currentBizDate.value)
  if (idx === -1) return
  const nextIdx = idx - step
  if (nextIdx >= 0 && nextIdx < availableDates.value.length) {
    currentBizDate.value = availableDates.value[nextIdx]
    fetchCurrentData()
  }
}

function jumpToLatestDate() {
  if (latestDate.value) {
    currentBizDate.value = latestDate.value
    fetchCurrentData()
  }
}

function handleSearch() {
  // 关键字过滤通过 computed filteredEvents 实时响应
}

function clearSearch() {
  searchKeyword.value = ''
}

function formatNum(val) {
  if (val == null || isNaN(val)) return '—'
  return Number(val).toLocaleString()
}

function formatTemp(minT, maxT) {
  if (minT == null && maxT == null) return '—'
  if (minT == null) return `${maxT} ℃`
  if (maxT == null) return `${minT} ℃`
  return `${minT} ~ ${maxT} ℃`
}
</script>

<style scoped>
.dispatch-info-view {
  min-height: 100vh;
  background-color: #f4f6f9;
  display: flex;
  flex-direction: column;
}

.dispatch-main {
  flex: 1;
  padding: 1.25rem 2rem 3rem;
  max-width: 1440px;
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

/* Banner */
.banner-card {
  padding: 1.25rem 1.75rem;
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  color: #fff;
  border-radius: 12px;
}
.banner-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}
.banner-title-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.banner-icon {
  font-size: 2.2rem;
}
.banner-title {
  margin: 0;
  font-size: 1.45rem;
  font-weight: 700;
  color: #f8fafc;
}
.banner-subtitle {
  margin: 0.25rem 0 0;
  font-size: 0.9rem;
  color: #94a3b8;
}
.banner-meta {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.meta-tag {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  padding: 0.4rem 0.8rem;
  font-size: 0.85rem;
  color: #cbd5e1;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}
.dot.live {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #10b981;
  box-shadow: 0 0 6px #10b981;
}

/* 提取工作台 */
.extract-card {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
}
.section-header {
  padding: 1rem 1.5rem;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.header-icon {
  font-size: 1.25rem;
}
.section-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: #1e293b;
}
.badge-sub {
  font-size: 0.75rem;
  background: #e2e8f0;
  color: #475569;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}
.extract-body {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

/* 模式 Tab */
.mode-tabs {
  display: flex;
  gap: 0.75rem;
}
.mode-tab {
  padding: 0.5rem 1rem;
  border: 1px solid #cbd5e1;
  background: #fff;
  border-radius: 6px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
}
.mode-tab.active {
  background: #3b82f6;
  border-color: #3b82f6;
  color: #fff;
  font-weight: 600;
}

/* 独立选择卡片行 */
.upload-buttons-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1rem;
}
.upload-btn-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem 1.5rem;
  background: #f8fafc;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}
.upload-btn-card:hover {
  border-color: #3b82f6;
  background: #eff6ff;
  transform: translateY(-2px);
  box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.1);
}
.upload-btn-card.primary-folder {
  border-color: #93c5fd;
  background: #f0fdf4;
}
.upload-btn-card.primary-folder:hover {
  border-color: #10b981;
  background: #ecfdf5;
  box-shadow: 0 4px 6px -1px rgba(16, 185, 129, 0.15);
}
.btn-card-icon {
  font-size: 2.2rem;
}
.btn-card-info {
  display: flex;
  flex-direction: column;
}
.btn-card-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: #1e293b;
}
.btn-card-desc {
  font-size: 0.82rem;
  color: #64748b;
  margin-top: 0.2rem;
}

/* 拖拽上传 */
.drop-zone {
  border: 2px dashed #cbd5e1;
  border-radius: 8px;
  background: #f8fafc;
  padding: 1.5rem;
  text-align: center;
  transition: border-color 0.2s, background 0.2s;
}
.drop-zone:hover {
  border-color: #3b82f6;
  background: #eff6ff;
}
.hidden-input {
  display: none;
}
.drop-icon {
  font-size: 2rem;
  display: block;
  margin-bottom: 0.35rem;
}
.drop-title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: #334155;
}
.drop-hint {
  margin: 0.25rem 0 0.5rem;
  font-size: 0.82rem;
  color: #94a3b8;
}
.upload-actions {
  display: flex;
  justify-content: center;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

/* 文件预览 Chips */
.file-list-preview {
  margin-top: 0.75rem;
  background: #f1f5f9;
  border-radius: 8px;
  padding: 0.85rem 1rem;
}
.list-title-bar {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
}
.list-title {
  font-size: 0.88rem;
  color: #1e293b;
  font-weight: 700;
}
.list-badge-docx {
  font-size: 0.75rem;
  background: #dbeafe;
  color: #1d4ed8;
  padding: 0.15rem 0.5rem;
  border-radius: 12px;
  font-weight: 600;
}
.list-badge-pdf {
  font-size: 0.75rem;
  background: #fee2e2;
  color: #b91c1c;
  padding: 0.15rem 0.5rem;
  border-radius: 12px;
  font-weight: 600;
}
.file-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.6rem;
}
.file-chip {
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 0.25rem 0.5rem;
  font-size: 0.8rem;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
.chip-ext {
  color: #fff;
  font-size: 0.65rem;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  font-weight: 700;
}
.chip-ext.docx {
  background: #2563eb;
}
.chip-ext.pdf {
  background: #dc2626;
}
.chip-name {
  max-width: 180px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.chip-more {
  font-size: 0.8rem;
  color: #64748b;
  align-self: center;
}

/* 服务器目录输入 */
.server-folder-container {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.form-group-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.path-input {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
}

/* 提取控制栏 */
.extract-action-bar {
  display: flex;
  gap: 1rem;
  align-items: center;
}
.btn-extract {
  padding: 0.65rem 1.5rem;
  font-size: 0.95rem;
}

/* 提取完成摘要 */
.extract-summary-card {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
}
.summary-title {
  font-weight: 700;
  color: #166534;
  font-size: 1.05rem;
}
.summary-stat {
  font-size: 0.9rem;
  color: #14532d;
}
.conflict-alert {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 6px;
  padding: 0.75rem 1rem;
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  color: #92400e;
  font-size: 0.88rem;
}
.conflict-icon {
  font-size: 1.2rem;
}
.summary-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.btn-save-db {
  background: #10b981;
  border-color: #10b981;
}

/* 看板部分 */
.dashboard-card {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  padding: 1.5rem;
}

/* 查询工具栏 */
.query-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid #e2e8f0;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  flex-wrap: wrap;
}
.filter-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: #334155;
}
.date-select-group {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}
.date-select {
  padding: 0.45rem 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.9rem;
  background: #fff;
}
.search-input-group {
  display: flex;
  gap: 0.35rem;
}
.search-input {
  padding: 0.45rem 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  width: 260px;
}

/* 状态 */
.state-container {
  padding: 4rem 2rem;
  text-align: center;
  color: #64748b;
}
.empty-icon {
  font-size: 3rem;
  display: block;
  margin-bottom: 0.5rem;
}
.empty-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #334155;
  margin: 0;
}
.empty-hint {
  font-size: 0.85rem;
  color: #94a3b8;
  margin-top: 0.25rem;
}

/* 展板主体与就地平滑刷新蒙层（防视口高度塌陷与跳顶） */
.dashboard-body {
  position: relative;
  min-height: 400px;
  transition: opacity 0.2s ease;
}
.dashboard-body.is-fetching {
  pointer-events: none;
}
.fetching-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(2px);
  z-index: 60;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding-top: 10vh;
  border-radius: 8px;
  animation: fadeIn 0.15s ease;
}
.fetching-pill {
  position: sticky;
  top: 24px;
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
  background: rgba(15, 23, 42, 0.92);
  color: #ffffff;
  padding: 0.6rem 1.25rem;
  border-radius: 30px;
  font-size: 0.88rem;
  font-weight: 600;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.15);
}
.fetching-spinner {
  border-color: rgba(255, 255, 255, 0.25);
  border-top-color: #38bdf8;
}

/* 报告抬头 */
.report-meta-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
  padding: 1rem 0 1.25rem;
}
.report-title {
  margin: 0;
  font-size: 1.35rem;
  color: #0f172a;
}
.meta-tags {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.4rem;
  font-size: 0.85rem;
  color: #475569;
}
.weather-box {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: #f1f5f9;
  border-radius: 8px;
  padding: 0.6rem 1rem;
  border: 1px solid #e2e8f0;
}
.weather-icon {
  font-size: 1.8rem;
}
.weather-temp {
  font-size: 1.1rem;
  font-weight: 700;
  color: #0284c7;
}
.weather-desc {
  font-size: 0.8rem;
  color: #64748b;
}

/* KPI 卡片网格 */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.kpi-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
}
.kpi-title {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  color: #64748b;
  font-weight: 600;
}
.kpi-unit {
  font-size: 0.75rem;
  color: #94a3b8;
}
.kpi-value {
  font-size: 1.8rem;
  font-weight: 800;
  color: #1e293b;
  margin: 0.35rem 0;
}
.text-power { color: #d97706; }
.text-heat { color: #dc2626; }
.text-water { color: #0284c7; }
.kpi-sub {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #64748b;
}

/* 全量平铺数据板块流 */
.dashboard-sections-flow {
  display: flex;
  flex-direction: column;
  gap: 1.75rem;
}

.dashboard-section-block {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 1.25rem 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.section-block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 0.85rem;
  margin-bottom: 1.15rem;
}

.section-block-title {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.section-block-title h4 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
  color: #1e293b;
}

.section-block-icon {
  font-size: 1.25rem;
  line-height: 1;
}

.section-badge {
  font-size: 0.78rem;
  color: #475569;
  background: #f1f5f9;
  padding: 0.2rem 0.6rem;
  border-radius: 12px;
  font-weight: 600;
}

/* 机炉拓扑卡片 */
.facilities-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
  gap: 1rem;
}
.plant-facilities-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1.1rem;
}
.plant-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 0.6rem;
  margin-bottom: 0.85rem;
}
.plant-name {
  font-weight: 700;
  color: #1e293b;
  font-size: 1rem;
}
.plant-running-summary {
  font-size: 0.82rem;
  font-weight: 700;
  color: #15803d;
  background: #dcfce7;
  padding: 0.2rem 0.55rem;
  border-radius: 6px;
  border: 1px solid #bbf7d0;
}

/* 左机右炉 / 燃气分列分栏容器（严格 50/50 绝对等宽，卡片尺寸像素级对等） */
.plant-split-columns {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 1.5rem;
  width: 100%;
  box-sizing: border-box;
  position: relative;
}
.plant-split-columns.single-column {
  grid-template-columns: minmax(0, 1fr);
  gap: 0;
}
.plant-split-columns:not(.single-column)::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: calc(50% - 0.5px);
  width: 0;
  border-left: 1px dashed #e2e8f0;
  pointer-events: none;
}
.plant-col {
  display: flex;
  flex-direction: column;
  min-width: 0; /* 核心：防止内部元素把单列撑宽，确保双列绝对 50/50 等宽 */
  width: 100%;
  box-sizing: border-box;
}
.col-right {
  /* 彻底消除原不对称的 padding-left 与 border-left，确保左右卡片内容宽度 100% 绝对一致 */
  border-left: none;
  padding-left: 0;
  box-sizing: border-box;
}
.plant-split-columns.single-column .col-right {
  border-left: none;
  padding-left: 0;
}
.col-header {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.6rem;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid #f1f5f9;
}
.col-icon {
  font-size: 0.95rem;
}
.col-title {
  font-size: 0.88rem;
  font-weight: 700;
  color: #1e293b;
}
.col-stat {
  font-size: 0.75rem;
  color: #64748b;
  margin-left: 0.2rem;
}

/* 当日启动标签 */
.fac-start-pill {
  background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%);
  color: #ffffff;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.12rem 0.45rem;
  border-radius: 4px;
  box-shadow: 0 1px 2px rgba(234, 88, 12, 0.3);
  white-space: nowrap;
  cursor: help;
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
}
.facility-badges {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}
.fac-badge {
  /* 名称和元信息各占一行，所有设备预留相同高度，启动标签不再挤压名称。 */
  display: grid;
  grid-template-rows: 1.3rem 1.5rem;
  gap: 0.2rem;
  min-width: 0;
  padding: 0.38rem 0.65rem;
  border-radius: 6px;
  font-size: 0.82rem;
  font-weight: 600;
  border: 1px solid transparent;
}
.fac-name {
  font-weight: 700;
  color: #1e293b;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.fac-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem;
  min-width: 0;
}
.fac-meta .fac-start-pill {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}
.status-run {
  background: #dcfce7;
  color: #15803d;
  border-color: #bbf7d0;
}
.status-standby {
  background: #fef9c3;
  color: #a16207;
  border-color: #fde047;
}
.status-starting { background: #ffedd5; color: #9a3412; border-color: #fdba74; }
.status-review { margin: 1rem 0; padding: 1rem; border: 1px solid #fdba74; background: #fff7ed; border-radius: 8px; overflow-wrap: anywhere; }
.status-review-item { padding: 0.8rem 0; border-top: 1px solid #fed7aa; }
.status-review select { max-width: 100%; }
.status-repair {
  background: #fee2e2;
  color: #b91c1c;
  border-color: #fecaca;
}
.fac-status-tag {
  font-size: 0.75rem;
  white-space: nowrap;
  flex-shrink: 0;
  margin-left: auto;
}

/* 首站与通用数据表格 */
.table-container {
  overflow-x: auto;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}
.data-table th, .data-table td {
  padding: 0.65rem 0.85rem;
  border: 1px solid #e2e8f0;
  text-align: left;
}
.data-table th {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
}
.data-table td.text-num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.badge-blue {
  background: #e0f2fe;
  color: #0369a1;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-weight: 600;
}
.badge-orange {
  background: #ffedd5;
  color: #c2410c;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-weight: 600;
}
.status-pill {
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}
.status-pill.run { background: #dcfce7; color: #15803d; }
.status-pill.stop { background: #fee2e2; color: #b91c1c; }

/* 蒸汽与燃煤子网格 */
.sub-split-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 1.25rem;
}
.inner-card {
  padding: 1rem;
}
.card-title {
  margin: 0 0 0.75rem;
  font-size: 1rem;
  color: #1e293b;
}

/* 事件流 */
.events-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.org-filter-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.filter-pill {
  padding: 0.3rem 0.7rem;
  border: 1px solid #cbd5e1;
  background: #fff;
  border-radius: 16px;
  font-size: 0.82rem;
  cursor: pointer;
  transition: all 0.2s;
}
.filter-pill.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}
.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.85rem;
  color: #334155;
  cursor: pointer;
}
.event-timeline {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.event-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-left: 4px solid #94a3b8;
  border-radius: 6px;
  padding: 0.85rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.event-card.is-ticket {
  border-left-color: #ea580c;
  background: #fff7ed;
}
.event-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.event-meta-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.event-time {
  font-weight: 700;
  color: #0f172a;
  font-size: 0.85rem;
}
.event-org {
  background: #e2e8f0;
  color: #334155;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-size: 0.78rem;
  font-weight: 600;
}
.badge-ticket {
  background: #ea580c;
  color: #fff;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}
.badge-op {
  background: #64748b;
  color: #fff;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}
.badge-pipe {
  background: #0284c7;
  color: #fff;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}
.event-duration {
  font-size: 0.8rem;
  color: #9a3412;
  font-weight: 600;
}
.event-content {
  font-size: 0.9rem;
  color: #1e293b;
  line-height: 1.5;
}
.empty-events {
  padding: 2.5rem;
  text-align: center;
  color: #94a3b8;
  font-size: 0.9rem;
}

/* 模态弹窗 */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}
.modal-card {
  background: #fff;
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  width: 100%;
  max-width: 540px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  overflow: hidden;
  animation: modalPop 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes modalPop {
  from { opacity: 0; transform: scale(0.96) translateY(10px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #f1f5f9;
}
.modal-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: #dc2626;
  font-weight: 600;
}
.modal-close-icon {
  background: transparent;
  border: none;
  font-size: 1.1rem;
  color: #94a3b8;
  cursor: pointer;
  padding: 0.25rem;
  line-height: 1;
  border-radius: 4px;
}
.modal-close-icon:hover {
  color: #334155;
  background: #f1f5f9;
}
.modal-body {
  font-size: 0.9rem;
  color: #334155;
  flex: 1 1 auto;
  overflow-y: auto;
  padding: 0.75rem 0.25rem 0.75rem 0;
  margin: 0.25rem 0;
}
.conflict-summary-banner {
  background: #fef2f2;
  border: 1px solid #fee2e2;
  border-radius: 8px;
  padding: 0.65rem 0.85rem;
  color: #991b1b;
  font-size: 0.88rem;
  margin-bottom: 0.6rem;
}
.conflict-range-text {
  font-size: 0.8rem;
  color: #b91c1c;
  margin-top: 0.25rem;
  font-weight: 500;
}
.section-hint {
  font-size: 0.82rem;
  color: #64748b;
  margin: 0.4rem 0 0.3rem;
}
.conflict-date-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  max-height: 140px;
  overflow-y: auto;
  padding: 0.5rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}
.conflict-date-chip {
  background: #fee2e2;
  color: #b91c1c;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-weight: 600;
  font-size: 0.8rem;
  font-family: monospace;
}
.modal-warn {
  color: #b91c1c;
  font-weight: 600;
  font-size: 0.85rem;
  margin: 0.75rem 0 0;
  background: #fff1f2;
  border-left: 3px solid #e11d48;
  padding: 0.4rem 0.6rem;
  border-radius: 0 4px 4px 0;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  flex-shrink: 0;
  padding-top: 0.85rem;
  border-top: 1px solid #f1f5f9;
}
.btn-danger {
  background: #dc2626;
  border-color: #dc2626;
}
.btn-danger:hover {
  background: #b91c1c;
  border-color: #b91c1c;
}

/* 按钮与小组件 */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  padding: 0.45rem 0.85rem;
  font-size: 0.88rem;
  transition: all 0.2s;
}
.btn.primary { background: #2563eb; color: #fff; }
.btn.primary:hover { background: #1d4ed8; }
.btn.secondary { background: #f1f5f9; border-color: #cbd5e1; color: #334155; }
.btn.secondary:hover { background: #e2e8f0; }
.btn.ghost { background: transparent; color: #475569; }
.btn.ghost:hover { background: #f1f5f9; }
.btn.icon-btn { padding: 0.45rem 0.65rem; background: #f1f5f9; border: 1px solid #cbd5e1; }
.btn.btn-sm { padding: 0.25rem 0.55rem; font-size: 0.8rem; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.text-danger { color: #dc2626 !important; }

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}
.spinner.large {
  width: 32px;
  height: 32px;
  border: 3px solid #cbd5e1;
  border-top-color: #3b82f6;
  margin: 0 auto 1rem;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ---------------- 移动端窄屏手机响应式排版适配 ---------------- */
@media (max-width: 768px) {
  .dispatch-main {
    padding: 0.65rem 0.75rem 2.5rem;
    gap: 0.85rem;
  }

  /* 顶部 Banner 卡片紧凑化 */
  .banner-card {
    padding: 0.85rem 1rem;
    border-radius: 8px;
  }
  .banner-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.6rem;
  }
  .banner-title-row {
    gap: 0.6rem;
  }
  .banner-icon {
    font-size: 1.6rem;
  }
  .banner-title {
    font-size: 1.15rem;
  }
  .banner-meta {
    flex-wrap: wrap;
    gap: 0.4rem;
  }
  .meta-tag {
    font-size: 0.78rem;
    padding: 0.3rem 0.6rem;
  }

  /* 提取工作台面板紧凑化 */
  .extract-card {
    border-radius: 8px;
  }
  .section-header {
    padding: 0.75rem 1rem;
  }
  .section-header h3 {
    font-size: 0.98rem;
  }
  .badge-sub {
    font-size: 0.7rem;
    padding: 0.15rem 0.4rem;
  }
  .extract-body {
    padding: 0.85rem;
    gap: 0.85rem;
  }

  /* 核心：上传按钮在手机下变为单列，展开所有文字说明，不再挤压变形 */
  .upload-buttons-row {
    grid-template-columns: 1fr;
    gap: 0.65rem;
    margin-bottom: 0.75rem;
  }
  .upload-btn-card {
    padding: 0.85rem 1rem;
    gap: 0.75rem;
  }
  .btn-card-icon {
    font-size: 1.6rem;
  }
  .btn-card-title {
    font-size: 0.95rem;
  }
  .btn-card-desc {
    font-size: 0.75rem;
  }

  .drop-zone {
    padding: 1rem 0.5rem;
  }
  .drop-icon {
    font-size: 1.6rem;
  }
  .drop-title {
    font-size: 0.85rem;
  }
  .drop-hint {
    font-size: 0.75rem;
  }

  .file-list-preview {
    padding: 0.65rem 0.75rem;
  }
  .list-title {
    font-size: 0.8rem;
  }
  .chip-name {
    max-width: 120px;
  }

  .btn-extract {
    width: 100%;
    justify-content: center;
    padding: 0.6rem 1rem;
    font-size: 0.9rem;
  }

  .summary-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.4rem;
  }
  .summary-title {
    font-size: 0.95rem;
  }
  .summary-stat {
    font-size: 0.82rem;
  }
  .summary-actions {
    flex-direction: column;
    width: 100%;
    gap: 0.5rem;
  }
  .summary-actions .btn {
    width: 100%;
    justify-content: center;
  }

  /* 看板大卡片与查询过滤条 */
  .dashboard-card {
    padding: 0.85rem 0.75rem;
    border-radius: 8px;
  }
  .query-toolbar {
    padding-bottom: 0.85rem;
    gap: 0.75rem;
  }
  .toolbar-left {
    flex-direction: column;
    align-items: stretch;
    gap: 0.75rem;
    width: 100%;
  }
  .filter-item {
    width: 100%;
    flex-wrap: wrap;
    gap: 0.4rem;
    font-size: 0.82rem;
  }
  .date-select-group {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .date-select {
    flex: 1;
    min-width: 0;
    width: 100%;
    padding: 0.4rem 0.5rem;
    font-size: 0.85rem;
  }
  .search-item {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
    gap: 0.4rem;
  }
  .search-input-group {
    width: 100%;
    display: flex;
    gap: 4px;
  }
  .search-input {
    flex: 1;
    width: auto !important;
    min-width: 0;
    padding: 0.4rem 0.6rem;
    font-size: 0.85rem;
  }
  .toolbar-right {
    width: 100%;
    display: flex;
    justify-content: flex-end;
  }

  /* 报告抬头与天气看板 */
  .report-meta-header {
    flex-direction: column;
    align-items: stretch;
    gap: 0.75rem;
    padding: 0.5rem 0 0.85rem;
  }
  .report-title {
    font-size: 1.15rem;
  }
  .meta-tags {
    flex-direction: column;
    gap: 0.25rem;
    font-size: 0.78rem;
  }
  .weather-box {
    width: 100%;
    box-sizing: border-box;
    justify-content: flex-start;
    padding: 0.6rem 0.8rem;
  }
  .weather-icon {
    font-size: 1.4rem;
  }
  .weather-temp {
    font-size: 1rem;
  }
  .weather-desc {
    font-size: 0.75rem;
  }

  /* 宏观产耗 KPI 卡片网格：手机下变为双列网格，紧凑易读 */
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.6rem;
    margin-bottom: 1rem;
  }
  .kpi-card {
    padding: 0.75rem 0.8rem;
  }
  .kpi-title {
    font-size: 0.78rem;
  }
  .kpi-value {
    font-size: 1.35rem;
    margin: 0.2rem 0;
  }
  .kpi-sub {
    flex-direction: column;
    gap: 2px;
    font-size: 0.7rem;
  }

  /* 平铺数据板块流 */
  .dashboard-sections-flow {
    gap: 1rem;
  }
  .dashboard-section-block {
    padding: 0.85rem 0.75rem;
    border-radius: 8px;
  }
  .section-block-header {
    margin-bottom: 0.85rem;
    padding-bottom: 0.65rem;
  }
  .section-block-title h4 {
    font-size: 0.95rem;
  }

  /* 机炉拓扑卡片：解除 minmax(380px, 1fr) 溢出限制，单列全宽适配 */
  .facilities-grid {
    grid-template-columns: 1fr !important;
    gap: 0.75rem;
  }
  .plant-facilities-card {
    padding: 0.75rem;
  }
  .plant-card-header {
    padding-bottom: 0.45rem;
    margin-bottom: 0.65rem;
  }
  .plant-name {
    font-size: 0.92rem;
  }
  .plant-running-summary {
    font-size: 0.75rem;
    padding: 0.15rem 0.4rem;
  }

  /* 单个电厂内部机炉分栏：单列垂直排列 */
  .plant-split-columns {
    grid-template-columns: minmax(0, 1fr) !important;
    gap: 0.65rem;
  }
  .plant-split-columns:not(.single-column)::after {
    display: none;
  }
  .col-right {
    border-left: none !important;
    padding-left: 0 !important;
    margin-top: 0.5rem;
    border-top: 1px dashed #e2e8f0;
    padding-top: 0.5rem;
  }
  .fac-badge {
    padding: 0.35rem 0.5rem;
    font-size: 0.78rem;
  }
  .fac-start-pill {
    font-size: 0.65rem;
    padding: 0.1rem 0.35rem;
  }

  /* 蒸汽与燃煤：解除 minmax(400px, 1fr) 溢出限制 */
  .sub-split-grid {
    grid-template-columns: 1fr !important;
    gap: 0.75rem;
  }
  .inner-card {
    padding: 0.65rem;
  }

  /* 首站、通用表格及移动端平滑滚动 */
  .table-container {
    -webkit-overflow-scrolling: touch;
  }
  .data-table {
    font-size: 0.78rem;
  }
  .data-table th,
  .data-table td {
    padding: 0.45rem 0.55rem;
    white-space: nowrap;
  }

  /* 调度事件流 */
  .events-toolbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.6rem;
  }
  .org-filter-pills {
    gap: 0.35rem;
    width: 100%;
  }
  .filter-pill {
    font-size: 0.75rem;
    padding: 0.25rem 0.55rem;
  }
  .checkbox-label {
    font-size: 0.8rem;
  }
  .event-card {
    padding: 0.65rem 0.75rem;
    gap: 0.35rem;
  }
  .event-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.35rem;
  }
  .event-meta-left {
    gap: 0.35rem;
  }
  .event-duration {
    font-size: 0.75rem;
  }
  .event-content {
    font-size: 0.82rem;
    line-height: 1.45;
  }

  /* 模态弹窗 */
  .modal-card {
    max-width: calc(100vw - 20px);
    padding: 1rem 0.85rem;
    max-height: 90vh;
  }
  .modal-header h3 {
    font-size: 0.95rem;
  }
  .modal-footer {
    flex-direction: column;
    gap: 0.5rem;
  }
  .modal-footer .btn {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .dispatch-main {
    padding: 0.5rem 0.5rem 2rem;
  }

  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.45rem;
  }

  .kpi-card {
    padding: 0.6rem 0.65rem;
  }

  .kpi-value {
    font-size: 1.25rem;
  }

  .date-select-group {
    flex-wrap: wrap;
  }

  .date-select-group .btn.ghost {
    width: 100%;
    margin-top: 2px;
  }
}
</style>
