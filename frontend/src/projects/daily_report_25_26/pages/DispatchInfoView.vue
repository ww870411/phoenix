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
              <h2 class="banner-title">主城区生产调度信息智能提取与全景工况看板</h2>
              <p class="banner-subtitle">
                支持 DOCX / PDF 调度日报自动化解析、设备拓扑标准化归一、微观事件流提取与一键入库检索
              </p>
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

      <!-- 1. 顶部：信息提取与入库工作台 (可折叠) -->
      <section class="card elevated extract-card">
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
          <!-- 上传模式切换与选择 -->
          <div class="mode-tabs">
            <button
              :class="['mode-tab', { active: extractMode === 'upload' }]"
              type="button"
              @click="extractMode = 'upload'"
            >
              📤 本地文件 / 文件夹上传
            </button>
            <button
              :class="['mode-tab', { active: extractMode === 'server' }]"
              type="button"
              @click="extractMode = 'server'"
            >
              💻 服务器目录直接扫描
            </button>
          </div>

          <!-- 模式 A：本地上传 -->
          <div v-if="extractMode === 'upload'" class="upload-container">
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

          <!-- 模式 B：服务器本地路径扫描 -->
          <div v-else class="server-folder-container">
            <div class="form-group-row">
              <label>服务器文件目录绝对/相对路径：</label>
              <input
                v-model="serverFolderPath"
                type="text"
                class="form-input path-input"
                placeholder="例如：configs/ 或 D:\历史日报\2026年"
              />
            </div>
            <p class="text-muted text-sm">
              直接由后台服务遍历该路径下的全部 .docx 和 .pdf 调度文档，适用于海量历史数据直接解析。
            </p>
          </div>

          <!-- 执行提取控制栏 -->
          <div class="extract-action-bar">
            <button
              class="btn primary btn-extract"
              type="button"
              :disabled="isExtracting || (extractMode === 'upload' && selectedFiles.length === 0)"
              @click="startExtraction"
            >
              <span v-if="isExtracting" class="spinner"></span>
              {{ isExtracting ? '正在解析提取中，请稍候…' : '🚀 开始智能批量提取' }}
            </button>
            <button
              class="btn ghost"
              type="button"
              :disabled="isExtracting"
              title="载入服务器已预提取的 162 份基准数据"
              @click="quickImportHistorical"
            >
              ⚡ 一键载入历史 162 份基准全量数据
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

            <!-- 操作按钮组合：下载 JSON、清理残留、一键入库 -->
            <div class="summary-actions">
              <button class="btn secondary" type="button" @click="downloadResultJson">
                📥 下载标准 JSON ({{ extractSummary.success_count }} 篇)
              </button>
              <button
                class="btn primary btn-save-db"
                type="button"
                :disabled="isSavingDb"
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

        <!-- 加载中与空状态提示 -->
        <div v-if="isLoadingData" class="state-container">
          <div class="spinner large"></div>
          <p>正在读取调度综合数据…</p>
        </div>

        <div v-else-if="!currentReport" class="state-container empty">
          <span class="empty-icon">📭</span>
          <p class="empty-title">当前日期暂无已入库的调度数据</p>
          <p class="empty-hint">请在上方的智能提取工作台上传或直接载入历史数据入库</p>
        </div>

        <!-- 调度数据展示全景展板 -->
        <div v-else class="dashboard-body">
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
              <div class="weather-icon">🌤️</div>
              <div class="weather-details">
                <div class="weather-temp">
                  {{ formatTemp(currentReport.weather?.temp_min, currentReport.weather?.temp_max) }}
                </div>
                <div class="weather-desc">
                  {{ currentReport.weather?.weather_desc || '天气良好' }} ｜
                  {{ currentReport.weather?.wind || '微风' }} ｜
                  相对湿度：{{ currentReport.weather?.humidity || '—' }}
                </div>
              </div>
            </div>
          </div>

          <!-- 宏观核心产耗指标卡片网格 -->
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

          <!-- 分项明细标签页导航 -->
          <div class="detail-nav-tabs">
            <button
              :class="['detail-tab', { active: activeTab === 'facilities' }]"
              type="button"
              @click="activeTab = 'facilities'"
            >
              🏭 机炉运行拓扑矩阵 ({{ currentReport.boiler_turbine_status?.length || 0 }})
            </button>
            <button
              :class="['detail-tab', { active: activeTab === 'first_stations' }]"
              type="button"
              @click="activeTab = 'first_stations'"
            >
              💧 首站工况与温压差 ({{ currentReport.first_stations?.length || 0 }})
            </button>
            <button
              :class="['detail-tab', { active: activeTab === 'steam_coal' }]"
              type="button"
              @click="activeTab = 'steam_coal'"
            >
              ♨️ 蒸汽网口与燃煤库存
            </button>
            <button
              :class="['detail-tab', { active: activeTab === 'events' }]"
              type="button"
              @click="activeTab = 'events'"
            >
              📋 微观事件与抢修工作票 ({{ filteredEvents.length }})
            </button>
          </div>

          <!-- Tab 1: 机炉拓扑状态视图 -->
          <div v-show="activeTab === 'facilities'" class="tab-pane">
            <div class="facilities-grid">
              <div
                v-for="group in groupedFacilities"
                :key="group.plant"
                class="plant-facilities-card"
              >
                <div class="plant-card-header">
                  <span class="plant-name">{{ group.plant }}</span>
                  <span class="plant-summary">共 {{ group.items.length }} 台设备</span>
                </div>
                <div class="facility-badges">
                  <div
                    v-for="(fac, fIdx) in group.items"
                    :key="fIdx"
                    :class="['fac-badge', fac.status === '运行' ? 'status-run' : fac.status === '备用' ? 'status-standby' : 'status-repair']"
                  >
                    <span class="fac-name">{{ fac.standard_name || fac.raw_name }}</span>
                    <span class="fac-type-tag">{{ fac.facility_type === '锅炉' ? fac.boiler_type || '锅炉' : '汽机' }}</span>
                    <span class="fac-status-tag">{{ fac.status }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Tab 2: 首站运行工况表 -->
          <div v-show="activeTab === 'first_stations'" class="tab-pane">
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
          </div>

          <!-- Tab 3: 蒸汽网口与燃煤库存 -->
          <div v-show="activeTab === 'steam_coal'" class="tab-pane">
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
          </div>

          <!-- Tab 4: 微观事件与抢修工作票 -->
          <div v-show="activeTab === 'events'" class="tab-pane">
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
import { getProjectNameById } from '../composables/useProjects'
import { useAuthStore } from '../store/auth'
import {
  extractDispatchFiles,
  getDispatchDownloadJsonUrl,
  downloadDispatchJson,
  cleanupDispatchTemp,
  saveDispatchData,
  queryDispatchData,
  fetchDispatchDates,
  importHistoricalDispatch
} from '../services/dispatchApi'

const auth = useAuthStore()
const route = useRoute()
const projectKey = computed(() => route.params.projectKey || 'daily_report_25_26')
const projectName = computed(() => getProjectNameById(projectKey.value) ?? '2025-2026供暖期生产日报')

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: projectName.value, to: `/projects/${encodeURIComponent(projectKey.value)}/pages` },
  { label: '调度信息', to: null },
])

// 提取工作台状态
const isExtractPanelExpanded = ref(true)
const extractMode = ref('upload') // 'upload' | 'server'
const selectedFiles = ref([])
const serverFolderPath = ref('')
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
const activeTab = ref('facilities') // 'facilities' | 'first_stations' | 'steam_coal' | 'events'

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

const groupedFacilities = computed(() => {
  if (!currentReport.value || !Array.isArray(currentReport.value.boiler_turbine_status)) return []
  const map = {}
  for (const fac of currentReport.value.boiler_turbine_status) {
    const plant = fac.unit_or_plant || '其他'
    if (!map[plant]) {
      map[plant] = []
    }
    map[plant].push(fac)
  }
  return Object.keys(map).map((k) => ({
    plant: k,
    items: map[k]
  }))
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
  isExtracting.value = true
  extractError.value = ''
  extractSummary.value = null

  try {
    const formData = new FormData()
    if (extractMode.value === 'upload') {
      for (const f of selectedFiles.value) {
        formData.append('files', f)
      }
    } else {
      if (!serverFolderPath.value) {
        throw new Error('请输入有效的服务器文件目录路径')
      }
      formData.append('folder_path', serverFolderPath.value)
    }

    const res = await extractDispatchFiles(projectKey.value, formData, auth.token)
    if (res?.ok) {
      extractSummary.value = res
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

async function quickImportHistorical() {
  if (!confirm('是否立即导入 configs/10.28 dispatch_extracted_batch.json 中的 162 份基准全量数据？')) {
    return
  }
  isExtracting.value = true
  try {
    const res = await importHistoricalDispatch(projectKey.value, true)
    alert(`全量数据导入成功！共入库 ${res.total_saved} 条数据。`)
    await loadAvailableDates()
    if (availableDates.value.length > 0) {
      currentBizDate.value = availableDates.value[0]
      await fetchCurrentData()
    }
  } catch (err) {
    alert('导入失败：' + err.message)
  } finally {
    isExtracting.value = false
  }
}

async function triggerSaveToDb() {
  if (!extractSummary.value) return
  isSavingDb.value = true
  try {
    const payload = {
      token: extractSummary.value.token,
      reports: extractSummary.value.items,
      overwrite: false
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
    }
  } catch (err) {
    alert('入库失败：' + err.message)
  } finally {
    isSavingDb.value = false
  }
}

async function confirmOverwriteSave() {
  showOverwriteModal.value = false
  isSavingDb.value = true
  try {
    const payload = {
      token: extractSummary.value.token,
      reports: extractSummary.value.items,
      overwrite: true
    }
    const res = await saveDispatchData(projectKey.value, payload)
    if (res.ok) {
      alert(`覆盖入库完成！新增 ${res.inserted} 条，更新覆盖 ${res.updated} 条。`)
      await loadAvailableDates()
      await fetchCurrentData()
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
  activeTab.value = 'events'
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

/* 标签页导航 */
.detail-nav-tabs {
  display: flex;
  gap: 0.5rem;
  border-bottom: 2px solid #e2e8f0;
  margin-bottom: 1.25rem;
}
.detail-tab {
  padding: 0.75rem 1.25rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  font-size: 0.95rem;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
}
.detail-tab:hover {
  color: #1e293b;
}
.detail-tab.active {
  color: #2563eb;
  border-bottom-color: #2563eb;
}

/* 机炉拓扑卡片 */
.facilities-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1rem;
}
.plant-facilities-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1rem;
}
.plant-card-header {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 0.5rem;
  margin-bottom: 0.75rem;
}
.plant-name {
  font-weight: 700;
  color: #1e293b;
  font-size: 0.95rem;
}
.plant-summary {
  font-size: 0.8rem;
  color: #64748b;
}
.facility-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.fac-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.3rem 0.6rem;
  border-radius: 6px;
  font-size: 0.82rem;
  font-weight: 600;
  border: 1px solid transparent;
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
.status-repair {
  background: #fee2e2;
  color: #b91c1c;
  border-color: #fecaca;
}
.fac-type-tag {
  font-size: 0.7rem;
  background: rgba(0,0,0,0.06);
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
}
.fac-status-tag {
  font-size: 0.75rem;
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
</style>
