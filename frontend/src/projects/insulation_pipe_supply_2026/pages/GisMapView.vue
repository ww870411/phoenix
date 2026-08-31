<template>
  <div class="gis-map-view page-layout">
    <AppHeader />
    <main class="page-main gis-container">
      <!-- 面包屑导航 -->
      <Breadcrumbs :items="breadcrumbItems" />

      <div class="page-content">
        <!-- 页头标题与搜索工具栏 -->
        <header class="page-title-row">
          <div class="title-wrap">
            <h2>🗺️ GIS空间地图系统</h2>
            <p class="subtitle">基于高德地图的保温管线轨迹分布、焊口探伤状态与监控表计在线标注与编辑系统</p>
          </div>
          
          <!-- 地点搜索框区 -->
          <div class="search-location-bar">
            <div class="search-input-wrap">
              <span class="search-icon">🔍</span>
              <input 
                v-model="searchKeyword" 
                type="text" 
                class="search-input" 
                placeholder="搜索城市或区域地名 (如: 香炉礁、大连港...)" 
                @keyup.enter="handleSearchLocation"
              />
              <button 
                class="btn primary search-btn" 
                type="button" 
                :disabled="searchLoading"
                @click="handleSearchLocation"
              >
                {{ searchLoading ? '搜索中...' : '定位搜索' }}
              </button>
            </div>
            <button class="btn ghost back-btn" type="button" @click="goProjectPages">
              ← 返回项目主页
            </button>
          </div>
        </header>

        <!-- 地图与面板主容器 -->
        <div class="gis-main-container card elevated">
          <!-- 顶部指标统计栏 -->
          <div class="gis-stats-bar">
            <div class="stat-item">
              <span class="stat-label">管线覆盖长度</span>
              <span class="stat-value text-blue">5.6 <small>km</small></span>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-label">标注焊口总数</span>
              <span class="stat-value text-emerald">{{ totalWeldsCount }} <small>个</small></span>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-label">探伤合格率</span>
              <span class="stat-value text-indigo">{{ passRate }}%</span>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-label">监控表计点位</span>
              <span class="stat-value text-amber">{{ totalMetersCount }} <small>处</small></span>
            </div>
          </div>

          <!-- 地图提示条 (点选模式激活或有待保存草稿点位时) -->
          <div v-if="isPickingPoint || hasDraftMarker" class="pick-point-banner">
            <span v-if="hasDraftMarker">
              📍 <strong>精准锚点点位已在地图呈现</strong>！坐标：<span class="text-mono">{{ formModel.lng }}, {{ formModel.lat }}</span>。请在右侧补充名称和编号后点击保存到数据库。
            </span>
            <span v-else>
              🎯 <strong>鼠标点选模式已开启</strong>：请在左侧高德地图上点击目标位置，针尖图标将准确指向点击落点！
            </span>
          </div>

          <!-- 图例说明与控制条 -->
          <div class="legend-bar">
            <span class="legend-title">🗺️ 地图图例与控制：</span>
            <span class="legend-item"><i class="dot dot-passed"></i> 🔩 焊口 (合格)</span>
            <span class="legend-item"><i class="dot dot-pending"></i> 🔩 焊口 (待探伤)</span>
            <span class="legend-item"><i class="dot dot-failed"></i> 🔩 焊口 (待复焊)</span>
            <span class="legend-item"><i class="dot dot-meter"></i> ⏱️ 表计</span>
            <span class="legend-item"><i class="dot dot-tee"></i> 🔀 三通</span>
            <span class="legend-item"><i class="dot dot-compensator"></i> 〰️ 补偿器</span>
            <span class="legend-item"><i class="dot dot-elbow"></i> ↪️ 弯头</span>
            <span class="legend-item"><i class="dot dot-valve"></i> 🚰 阀门</span>
            <span class="legend-item"><i class="line-sample"></i> 管线轨迹</span>

            <!-- 显隐切换与多维筛选控制按钮组 -->
            <div class="control-btn-group">
              <!-- 多维筛选浓缩按钮与弹出面板 -->
              <div class="filter-popover-wrapper">
                <button 
                  :class="['btn', hasActiveFilter ? 'primary' : 'ghost', 'small-btn']" 
                  type="button" 
                  @click="showFilterPopover = !showFilterPopover"
                >
                  🌪️ 筛选与过滤 <span v-if="hasActiveFilter" class="filter-count-badge">已启用</span> ▾
                </button>

                <!-- 点击展开的高级多选弹框/下拉面板 -->
                <div v-if="showFilterPopover" class="filter-popover-panel card elevated">
                  <div class="popover-header">
                    <span>🔍 高级多维多选筛选</span>
                    <button class="close-popover-btn" type="button" @click="showFilterPopover = false">✕</button>
                  </div>

                  <div class="popover-body">
                    <!-- 1. 点位分类多选 (6种类型) -->
                    <div class="filter-section-group">
                      <div class="group-title">📌 标注点位分类：</div>
                      <div class="checkbox-grid">
                        <label class="checkbox-label">
                          <input type="checkbox" value="weld" v-model="selectedTypes" @change="onFilterChange" /> 🔩 焊口
                        </label>
                        <label class="checkbox-label">
                          <input type="checkbox" value="meter" v-model="selectedTypes" @change="onFilterChange" /> ⏱️ 表计
                        </label>
                        <label class="checkbox-label">
                          <input type="checkbox" value="tee" v-model="selectedTypes" @change="onFilterChange" /> 🔀 三通
                        </label>
                        <label class="checkbox-label">
                          <input type="checkbox" value="compensator" v-model="selectedTypes" @change="onFilterChange" /> 〰️ 补偿器
                        </label>
                        <label class="checkbox-label">
                          <input type="checkbox" value="elbow" v-model="selectedTypes" @change="onFilterChange" /> ↪️ 弯头
                        </label>
                        <label class="checkbox-label">
                          <input type="checkbox" value="valve" v-model="selectedTypes" @change="onFilterChange" /> 🚰 阀门
                        </label>
                      </div>
                    </div>

                    <!-- 2. 施工标段多选 -->
                    <div v-if="existingSectionOptions.length > 0" class="filter-section-group">
                      <div class="group-title-row">
                        <span class="group-title">🏗️ 施工标段 (打勾多选)：</span>
                        <button class="text-link-btn" type="button" @click="toggleAllSections">
                          {{ selectedSections.length === existingSectionOptions.length ? '清空' : '全选' }}
                        </button>
                      </div>
                      <div class="checkbox-grid">
                        <label v-for="sec in existingSectionOptions" :key="sec" class="checkbox-label">
                          <input type="checkbox" :value="sec" v-model="selectedSections" @change="onFilterChange" /> {{ sec }}
                        </label>
                      </div>
                    </div>

                    <!-- 3. 管线名称/编号多选 -->
                    <div v-if="existingPipelineOptions.length > 0" class="filter-section-group">
                      <div class="group-title-row">
                        <span class="group-title">🚰 管线名称/编号 (打勾多选)：</span>
                        <button class="text-link-btn" type="button" @click="toggleAllPipelines">
                          {{ selectedPipelines.length === existingPipelineOptions.length ? '清空' : '全选' }}
                        </button>
                      </div>
                      <div class="checkbox-grid">
                        <label v-for="pipe in existingPipelineOptions" :key="pipe" class="checkbox-label">
                          <input type="checkbox" :value="pipe" v-model="selectedPipelines" @change="onFilterChange" /> {{ pipe }}
                        </label>
                      </div>
                    </div>

                    <!-- 4. 点位记录时间范围筛选 (默认不限) -->
                    <div class="filter-section-group">
                      <div class="group-title-row">
                        <span class="group-title">📅 记录时间范围 (默认不限)：</span>
                        <button v-if="startDateFilter || endDateFilter" class="text-link-btn text-danger" type="button" @click="clearDateFilter">
                          清空时间
                        </button>
                      </div>
                      <div class="date-filter-grid">
                        <input 
                          type="date" 
                          v-model="startDateFilter" 
                          class="date-input-compact"
                          title="选择起始日期"
                          @change="onFilterChange"
                        />
                        <span class="date-separator">~</span>
                        <input 
                          type="date" 
                          v-model="endDateFilter" 
                          class="date-input-compact"
                          title="选择结束日期"
                          @change="onFilterChange"
                        />
                      </div>
                    </div>
                  </div>

                  <div class="popover-footer">
                    <button class="btn ghost small-btn" type="button" @click="resetAllFilters">重置默认</button>
                    <button class="btn primary small-btn" type="button" @click="showFilterPopover = false">确定完成</button>
                  </div>
                </div>
              </div>

              <!-- 导出当前筛选表格 XLSX 按钮 -->
              <button 
                v-if="canExtractXlsx"
                class="btn ghost small-btn control-action-btn" 
                type="button" 
                :disabled="filteredMarkers.length === 0"
                title="按当前多维筛选结果导出 Excel 文件"
                @click="exportFilteredMarkersToXlsx"
              >
                📥 导出表格
              </button>

              <!-- 管道连线显隐按钮 -->
              <button 
                :class="['btn', showPipeline ? 'primary' : 'ghost', 'small-btn', 'control-action-btn']" 
                type="button" 
                @click="togglePipelineVisibility"
              >
                {{ showPipeline ? '👁️ 管线连线' : '🙈 隐藏连线' }}
              </button>
            </div>
          </div>

          <!-- 地图与右侧面板网格布局 -->
          <div class="gis-body-grid">
            <!-- 地图视图区 -->
            <div class="map-wrapper">
              <div v-if="mapLoading" class="map-loading-overlay">
                <div class="spinner"></div>
                <div class="loading-text">高德地图加载中，正在读取管网点位数据...</div>
              </div>
              <div v-if="mapError" class="map-error-overlay">
                ⚠️ 地图加载失败：{{ mapError }}
              </div>
              <div id="amap-container" class="amap-box"></div>
            </div>

            <!-- 右侧标注管理面板 -->
            <div class="gis-side-panel">
              <div class="panel-tabs">
                <button 
                  :class="['tab-btn', activeSideTab === 'list' ? 'active' : '']" 
                  type="button" 
                  @click="activeSideTab = 'list'"
                >
                  📋 数据库点位 ({{ filteredMarkers.length }})
                </button>
                <button 
                  :class="['tab-btn', activeSideTab === 'form' ? 'active' : '']" 
                  type="button" 
                  @click="handleFormTabClick"
                >
                  {{ editingId ? '✏️ 编辑点位' : '➕ 新增点位' }}
                </button>
              </div>

              <!-- Tab 1: 点位列表与顺序调整区 -->
              <div v-if="activeSideTab === 'list'" class="panel-content">

                <div class="marker-item-list">
                  <div 
                    v-for="(item, idx) in filteredMarkers" 
                    :key="item.id" 
                    :id="'marker-card-' + item.id"
                    :class="['marker-card', item.id === selectedMarkerId ? 'selected-card-highlight' : '']"
                    @click="focusMarkerOnMap(item)"
                  >
                    <div class="marker-card-header">
                      <span :class="['badge', 'badge-' + (item.type || 'weld')]">
                        {{ getMarkerTypeLabel(item.type) }}
                      </span>
                      <span class="marker-code">{{ item.code }}</span>
                      <span :class="['status-tag', item.statusClass]">{{ item.statusText }}</span>
                    </div>
                    <div class="marker-card-body">
                      <div v-if="item.sectionName" class="info-row">
                        <span class="label">施工标段：</span>
                        <span class="val text-indigo font-bold">{{ item.sectionName }}</span>
                      </div>
                      <div class="info-row">
                        <span class="label">管线名称/编号：</span>
                        <span class="val text-blue font-bold">{{ item.pipelineName || '未指定管线' }}</span>
                      </div>
                      <div class="info-row">
                        <span class="label">名称描述：</span>
                        <span class="val">{{ item.name }}</span>
                      </div>
                      <div v-if="item.parentCode" class="info-row">
                        <span class="label">父节点：</span>
                        <span class="val text-amber font-bold" :title="getParentNodeTitle(item.parentCode)">
                          {{ getParentNodeDisplay(item.parentCode) }}
                        </span>
                      </div>
                      <div class="info-row">
                        <span class="label">经纬度坐标：</span>
                        <span class="val text-mono">{{ item.lng.toFixed(6) }}, {{ item.lat.toFixed(6) }}</span>
                      </div>
                      <div v-if="item.spec" class="info-row">
                        <span class="label">关联保温管：</span>
                        <span class="val">{{ item.spec }}</span>
                      </div>
                      <div v-if="item.createdAt" class="info-row">
                        <span class="label">录入时间：</span>
                        <span class="val text-mono text-slate-500">{{ item.createdAt }}</span>
                      </div>
                    </div>

                    <!-- 点位操作与连线顺序调整按钮列 -->
                    <div class="marker-card-actions">
                      <div v-if="item.type === 'weld' || item.type === 'tee'" class="order-btn-group">
                        <button class="order-btn" title="上移连线顺序" type="button" @click.stop="moveWeldOrder(idx, 'up')">⬆️</button>
                        <button class="order-btn" title="下移连线顺序" type="button" @click.stop="moveWeldOrder(idx, 'down')">⬇️</button>
                      </div>
                      <button class="action-btn edit-btn" type="button" @click.stop="startEditMarker(item)">
                        ✏️ 编辑
                      </button>
                      <button class="action-btn delete-btn" type="button" @click.stop="deleteMarker(item)">
                        🗑️ 删除
                      </button>
                    </div>
                  </div>
                  <div v-if="filteredMarkers.length === 0" class="empty-tip">
                    暂无符合过滤条件的标注点位
                  </div>
                </div>
              </div>

              <!-- Tab 2: 新增/编辑表单区 -->
              <div v-if="activeSideTab === 'form'" class="panel-content">
                <div class="form-header-bar">
                  <h4>{{ editingId ? `✏️ 编辑修改点位 (${formModel.code || ''})` : '➕ 录入新增标注点位' }}</h4>
                  <button v-if="editingId || hasDraftMarker" class="btn ghost small-btn" type="button" @click="startAddNewMarker">
                    ➕ 切换为新增点位
                  </button>
                </div>

                <form class="add-marker-form" @submit.prevent="saveMarkerData">
                  <div class="form-group">
                    <label>标注点位类型 <span class="required">*</span></label>
                    <select v-model="formModel.type" class="select-input" required @change="updateDraftMarkerIcon">
                      <option value="weld">🔩 焊口</option>
                      <option value="meter">⏱️ 表计</option>
                      <option value="tee">🔀 三通</option>
                      <option value="compensator">〰️ 补偿器</option>
                      <option value="elbow">↪️ 弯头</option>
                      <option value="valve">🚰 阀门</option>
                    </select>
                  </div>

                  <!-- 施工标段 (可从系统已有标段中选择，也可自主输入) -->
                  <div class="form-group">
                    <label>施工标段 <span class="required">*</span></label>
                    <input 
                      v-model="formModel.sectionName" 
                      type="text" 
                      class="text-input" 
                      list="existing-sections-list"
                      placeholder="选择或输入标段 (例: 标段1 (香炉礁主线段))" 
                      required 
                    />
                    <datalist id="existing-sections-list">
                      <option v-for="sec in existingSectionOptions" :key="sec" :value="sec" />
                    </datalist>
                  </div>

                  <!-- 管线名称/编号 (可从已有管线中选择，也可自主输入) -->
                  <div class="form-group">
                    <label>管线名称/编号 <span class="required">*</span></label>
                    <input 
                      v-model="formModel.pipelineName" 
                      type="text" 
                      class="text-input" 
                      list="existing-pipelines-list"
                      placeholder="例: 香炉礁供暖主干线 或 鞍山路预制管线" 
                      required 
                    />
                    <datalist id="existing-pipelines-list">
                      <option v-for="pipe in existingPipelineOptions" :key="pipe" :value="pipe" />
                    </datalist>
                    <small class="field-tip">属于同一管线名称/编号的焊口与三通将自动连成管线轨迹网络</small>
                  </div>

                  <!-- 父节点 (焊口与三通均可设定父节点，类似 Git Commit Parent) -->
                  <div v-if="formModel.type === 'weld' || formModel.type === 'tee'" class="form-group">
                    <label>父节点 (Parent Code)</label>
                    <input 
                      v-model="formModel.parentCode" 
                      type="text" 
                      class="text-input" 
                      list="existing-parents-list"
                      placeholder="例: W-DL-001 或 T-DL-001 (置空则作为起点)" 
                    />
                    <datalist id="existing-parents-list">
                      <option v-for="pNode in existingParentNodeOptions" :key="pNode.code" :value="pNode.code">
                        {{ pNode.type === 'tee' ? '🔀 三通' : '🔩 焊口' }} - {{ pNode.name }}
                      </option>
                    </datalist>
                    <small class="field-tip">指向上一焊口或三通父节点。三通节点连接父节点后再继续分出多条路线线段！</small>
                    <div v-if="autoSuggestedParentCode" class="smart-tip-box" style="margin-top:4px; font-size:12px; color:#059669; background:#ecfdf5; padding:4px 8px; border-radius:4px; border:1px solid #a7f3d0;">
                      ✨ 已根据物理坐标为您默认生成最合理父节点：<strong>{{ autoSuggestedParentCode }}</strong>
                    </div>
                  </div>

                  <div class="form-group">
                    <label>点位编号/标识 <span class="required">*</span></label>
                    <input 
                      v-model="formModel.code" 
                      type="text" 
                      class="text-input" 
                      placeholder="例: W-DL-005 或 M-DL-003" 
                      required 
                      @input="updateDraftMarkerIcon"
                    />
                  </div>

                  <div class="form-group">
                    <label>名称描述 <span class="required">*</span></label>
                    <input 
                      v-model="formModel.name" 
                      type="text" 
                      class="text-input" 
                      placeholder="例: 香炉礁换热站主管道焊口" 
                      required 
                    />
                  </div>

                  <!-- 经纬度与地图点选、手机 GPS 定位高品质卡片区域 -->
                  <div class="location-card-box">
                    <div class="location-card-header">
                      <label class="location-card-title">📍 经纬度地理坐标 <span class="required">*</span></label>
                    </div>

                    <!-- 经纬度双输入框网格 -->
                    <div class="coord-inputs-grid">
                      <div class="coord-input-item">
                        <span class="coord-prefix">经度 (Lng)</span>
                        <input 
                          v-model.number="formModel.lng" 
                          type="number" 
                          step="0.000001" 
                          class="text-input text-mono coord-field" 
                          placeholder="例如: 121.604771" 
                          required 
                          @change="manualUpdateCoordinates"
                        />
                      </div>
                      <div class="coord-input-item">
                        <span class="coord-prefix">纬度 (Lat)</span>
                        <input 
                          v-model.number="formModel.lat" 
                          type="number" 
                          step="0.000001" 
                          class="text-input text-mono coord-field" 
                          placeholder="例如: 38.928491" 
                          required 
                          @change="manualUpdateCoordinates"
                        />
                      </div>
                    </div>

                    <!-- 快捷定位与落点操作按钮组 -->
                    <div class="location-action-btns">
                      <button 
                        :class="['btn', isPickingPoint ? 'warning' : 'ghost', 'coord-btn']" 
                        type="button" 
                        @click="togglePickPointMode"
                      >
                        {{ isPickingPoint ? '✕ 取消地图取点' : '🎯 点击地图设点' }}
                      </button>
                      <button 
                        class="btn primary coord-btn" 
                        type="button" 
                        :disabled="locatingGps"
                        title="利用手机/浏览器 GPS 芯片获取现场经纬度"
                        @click="getCurrentGpsLocation"
                      >
                        {{ locatingGps ? '🌀 定位中...' : '📍 获取手机 GPS 位置' }}
                      </button>
                    </div>

                    <div class="coord-tip-card">
                      💡 提示：现场打点建议点击“获取手机 GPS 位置”自动抓取高精度坐标；也可点击“地图设点”在地图上点击取点。
                    </div>
                  </div>

                  <div v-if="formModel.type === 'weld'" class="form-group">
                    <label>探伤/质检状态</label>
                    <select v-model="formModel.status" class="select-input" @change="updateDraftMarkerIcon">
                      <option value="passed">✅ 探伤合格</option>
                      <option value="pending">⏳ 待探伤</option>
                      <option value="failed">❌ 待复焊/不合格</option>
                    </select>
                  </div>

                  <div v-if="formModel.type === 'meter'" class="form-group">
                    <label>表计类型/状态</label>
                    <select v-model="formModel.status" class="select-input" @change="updateDraftMarkerIcon">
                      <option value="normal">🟢 运行正常</option>
                      <option value="warning">🟡 读数预警</option>
                      <option value="maintenance">🔴 维护保养中</option>
                    </select>
                  </div>

                  <div class="form-group">
                    <label>关联保温管规格型号</label>
                    <input 
                      v-model="formModel.spec" 
                      type="text" 
                      class="text-input" 
                      placeholder="例: DN400 预制直埋保温管" 
                    />
                  </div>

                  <div class="form-group">
                    <label>备注说明</label>
                    <textarea 
                      v-model="formModel.remarks" 
                      class="textarea-input" 
                      rows="2"
                      placeholder="施工队长、探伤记录、检测细节等..."
                    ></textarea>
                  </div>

                  <div class="form-submit-row">
                    <button class="btn primary full-width" type="submit" :disabled="saving">
                      💾 {{ saving ? '保存中...' : (editingId ? '更新数据并保存' : '保存点位数据') }}
                    </button>
                    <button v-if="editingId || hasDraftMarker" class="btn ghost full-width" type="button" @click="cancelEditing">
                      取消编辑/清除草稿
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../daily_report_25_26/store/auth'
import { AppHeader, Breadcrumbs } from './shared.js'
import { getAuthToken } from '../../daily_report_25_26/services/api.js'

const auth = useAuthStore()
const projectKey = 'insulation_pipe_supply_2026'
const canExtractXlsx = computed(() => auth.canExtractXlsxFor(projectKey))
const router = useRouter()
const selectedMarkerId = ref(null)

// 高德地图注册认证密钥 (支持从后端获取全局配置)
const DEFAULT_AMAP_KEY = 'f49ff8e523dd739fecc6d8bfb4209f22'
const DEFAULT_AMAP_SECURITY_CODE = '7573fa30e86735d98bafb40466822b3a'

const currentAmapKey = ref(DEFAULT_AMAP_KEY)
const currentAmapSecurityCode = ref(DEFAULT_AMAP_SECURITY_CODE)

// 大连市香炉礁默认中心点坐标
const CENTER_LNG = 121.606771
const CENTER_LAT = 38.930491

// 面包屑
const breadcrumbItems = [
  { label: '项目列表', to: '/projects' },
  { label: '保温管物流链系统', to: '/projects/insulation_pipe_supply_2026/pages' },
  { label: 'GIS空间地图系统' }
]

const mapLoading = ref(true)
const mapError = ref('')
const searchKeyword = ref('')
const searchLoading = ref(false)
const showPipeline = ref(true)
const saving = ref(false)

let mapInstance = null
let amapObject = null
let draftMarkerObject = null

const activeSideTab = ref('list')

// 浓缩多维筛选 Popover 显隐与选中的数组
const showFilterPopover = ref(false)
const ALL_TYPES = ['weld', 'meter', 'tee', 'compensator', 'elbow', 'valve']
const selectedTypes = ref([...ALL_TYPES]) // 标注类型多选：默认全选 6 种点位
const selectedSections = ref([]) // 施工标段多选：为空表示不限/全选
const selectedPipelines = ref([]) // 管道名称多选：为空表示不限/全选

const isPickingPoint = ref(false)
const locatingGps = ref(false)
const editingId = ref(null)
const hasDraftMarker = ref(false)

// 点位实时数据列表，全量从 PostgreSQL 数据库异步拉取
const markersList = ref([])

// 点位记录时间范围筛选变量 (默认不限: '')
const startDateFilter = ref('')
const endDateFilter = ref('')

// 是否激活了任何过滤规则
const hasActiveFilter = computed(() => {
  if (selectedTypes.value.length < ALL_TYPES.length) return true
  if (selectedSections.value.length > 0) return true
  if (selectedPipelines.value.length > 0) return true
  if (startDateFilter.value || endDateFilter.value) return true
  return false
})

// 官方系统设定的标段列表 (动态从 tube_config.json 读取)
const systemSections = ref([])

// 动态合并【系统设定的官方标段 (标段1, 标段2...)】+【当前已存在打点数据的标段】进行去重
const existingSectionOptions = computed(() => {
  const set = new Set(systemSections.value)
  markersList.value.forEach(m => {
    if (m.sectionName && m.sectionName.trim()) {
      set.add(m.sectionName.trim())
    }
  })
  return Array.from(set)
})

// 动态从当前已存在的打点数据中去重提取【管道名称/编号列表】
const existingPipelineOptions = computed(() => {
  const set = new Set()
  markersList.value.forEach(m => {
    if (m.pipelineName && m.pipelineName.trim()) {
      set.add(m.pipelineName.trim())
    }
  })
  return Array.from(set)
})

// 统计计算属性
const totalWeldsCount = computed(() => markersList.value.filter(m => m.type === 'weld').length)
const totalMetersCount = computed(() => markersList.value.filter(m => m.type === 'meter').length)
const passRate = computed(() => {
  const welds = markersList.value.filter(m => m.type === 'weld')
  if (welds.length === 0) return 100
  const passed = welds.filter(w => w.status === 'passed').length
  return Math.round((passed / welds.length) * 100)
})

// 组合多维多选筛选后的点位清单 (按勾选的类型、标段、管道名称、记录时间范围过滤)
const filteredMarkers = computed(() => {
  return markersList.value.filter(m => {
    // 1. 类型多选过滤
    if (selectedTypes.value.length > 0 && !selectedTypes.value.includes(m.type)) {
      return false
    }
    // 2. 施工标段多选过滤 (若有勾选，必须在勾选项中)
    if (selectedSections.value.length > 0) {
      const sec = (m.sectionName || '').trim()
      if (!selectedSections.value.includes(sec)) {
        return false
      }
    }
    // 3. 管道名称多选过滤 (若有勾选，必须在勾选项中)
    if (selectedPipelines.value.length > 0) {
      const pipe = (m.pipelineName || '').trim()
      if (!selectedPipelines.value.includes(pipe)) {
        return false
      }
    }
    // 4. 点位记录时间范围过滤 (默认不限: startDateFilter ~ endDateFilter)
    if (startDateFilter.value || endDateFilter.value) {
      if (!m.createdAt) return false
      // m.createdAt 格式示例 "2026-07-30 15:30:00"
      const createdDateStr = m.createdAt.slice(0, 10)
      if (startDateFilter.value && createdDateStr < startDateFilter.value) {
        return false
      }
      if (endDateFilter.value && createdDateStr > endDateFilter.value) {
        return false
      }
    }
    return true
  })
})

// 过滤器变动时重新渲染地图
const onFilterChange = () => {
  renderMapElements()
}

// 单独清空时间范围过滤
const clearDateFilter = () => {
  startDateFilter.value = ''
  endDateFilter.value = ''
  renderMapElements()
}

// 重置全部过滤器到默认状态
const resetAllFilters = () => {
  selectedTypes.value = [...ALL_TYPES]
  selectedSections.value = []
  selectedPipelines.value = []
  startDateFilter.value = ''
  endDateFilter.value = ''
  renderMapElements()
}

// 切换标段全选 / 清空
const toggleAllSections = () => {
  if (selectedSections.value.length === existingSectionOptions.value.length) {
    selectedSections.value = []
  } else {
    selectedSections.value = [...existingSectionOptions.value]
  }
  renderMapElements()
}

// 切换管道名称全选 / 清空
const toggleAllPipelines = () => {
  if (selectedPipelines.value.length === existingPipelineOptions.value.length) {
    selectedPipelines.value = []
  } else {
    selectedPipelines.value = [...existingPipelineOptions.value]
  }
  renderMapElements()
}

// 导出当前多维筛选过滤后的数据为纯正 Excel (.xlsx) 表格文件
const exportFilteredMarkersToXlsx = () => {
  const rows = filteredMarkers.value
  if (!rows || rows.length === 0) {
    alert('当前筛选条件下没有可供导出的点位数据！')
    return
  }

  // 1. 构造 Excel XML/HTML 格式表头与表格
  const headers = [
    '点位编号',
    '标注类型',
    '施工标段',
    '管线名称/编号',
    '父节点',
    '名称描述',
    '经度 (Lng)',
    '纬度 (Lat)',
    '质检/运行状态',
    '关联保温管规格',
    '轨迹连线顺序',
    '录入时间',
    '备注说明'
  ]

  let tableHtml = '<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">'
  tableHtml += '<head><meta charset="utf-8"><!--[if gte mso 9]><xml><x:ExcelWorkbook><x:ExcelWorksheets><x:ExcelWorksheet>'
  tableHtml += '<x:Name>GIS空间地图点位</x:Name>'
  tableHtml += '<x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions></x:ExcelWorksheet></x:ExcelWorksheets></x:ExcelWorkbook></xml><![endif]--></head><body>'
  tableHtml += '<table border="1" style="border-collapse:collapse; font-family:Microsoft Yahei, sans-serif;">'

  // 表头行
  tableHtml += '<tr style="background-color:#0284c7; color:#ffffff; font-weight:bold; text-align:center;">'
  headers.forEach(h => {
    tableHtml += `<th style="padding:8px 12px;">${h}</th>`
  })
  tableHtml += '</tr>'

  // 数据数据行
  rows.forEach((r, idx) => {
    const bg = idx % 2 === 0 ? '#ffffff' : '#f8fafc'
    const typeLabel = MARKER_TYPE_CONFIG[r.type]?.label || '点位'
    tableHtml += `<tr style="background-color:${bg};">`
    tableHtml += `<td style="padding:6px 10px; mso-number-format:'\\@';">${r.code || ''}</td>`
    tableHtml += `<td style="padding:6px 10px; text-align:center;">${typeLabel}</td>`
    tableHtml += `<td style="padding:6px 10px; color:#4f46e5; font-weight:600;">${r.sectionName || ''}</td>`
    tableHtml += `<td style="padding:6px 10px; color:#0284c7; font-weight:600;">${r.pipelineName || ''}</td>`
    tableHtml += `<td style="padding:6px 10px; color:#d97706; text-align:center;">${r.parentCode || ''}</td>`
    tableHtml += `<td style="padding:6px 10px;">${r.name || ''}</td>`
    tableHtml += `<td style="padding:6px 10px; text-align:right;">${r.lng}</td>`
    tableHtml += `<td style="padding:6px 10px; text-align:right;">${r.lat}</td>`
    tableHtml += `<td style="padding:6px 10px; text-align:center;">${r.statusText || r.status || ''}</td>`
    tableHtml += `<td style="padding:6px 10px;">${r.spec || ''}</td>`
    tableHtml += `<td style="padding:6px 10px; text-align:center;">${r.sortOrder || 0}</td>`
    tableHtml += `<td style="padding:6px 10px; text-align:center;">${r.createdAt || ''}</td>`
    tableHtml += `<td style="padding:6px 10px;">${r.remarks || ''}</td>`
    tableHtml += '</tr>'
  })

  tableHtml += '</table></body></html>'

  // 2. 导出 Blob 并触发浏览器无感下载
  const blob = new Blob([tableHtml], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;charset=utf-8'
  })

  const dateStr = new Date().toISOString().slice(0, 10)
  const fileName = `GIS空间地图系统_筛选结果_${dateStr}.xlsx`

  if (window.navigator && window.navigator.msSaveOrOpenBlob) {
    window.navigator.msSaveOrOpenBlob(blob, fileName)
  } else {
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = fileName
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(link.href)
  }
}

// 表单 Model
const formModel = ref({
  type: 'weld',
  sectionName: '',
  pipelineName: '',
  code: '',
  name: '',
  lng: '',
  lat: '',
  status: 'passed',
  spec: '',
  remarks: ''
})

// 返回主页
const goProjectPages = () => {
  router.push('/projects/insulation_pipe_supply_2026/pages')
}

// 缓存 Marker 及 Polyline 实例数组
let mapMarkerObjects = []
let pipelinePolylines = []
let searchPromptMarker = null

// 从 Storage 安全获取 token，规避 Pinia getActivePinia() 未初始化导致 Vue 组件崩溃的 P0 陷阱
const getSafeAuthToken = () => {
  if (typeof window === 'undefined') return null
  try {
    const rawLocal = localStorage.getItem('phoenix_auth')
    if (rawLocal) {
      const parsed = JSON.parse(rawLocal)
      if (parsed && parsed.token) return parsed.token
    }
    const rawSession = sessionStorage.getItem('phoenix_auth')
    if (rawSession) {
      const parsed = JSON.parse(rawSession)
      if (parsed && parsed.token) return parsed.token
    }
  } catch (e) {
    // 忽略异常
  }
  return typeof getAuthToken === 'function' ? getAuthToken() : null
}

// 构建标准的 Bearer Auth Headers
const buildAuthHeaders = (extraHeaders = {}) => {
  const token = getSafeAuthToken()
  const headers = { ...extraHeaders }
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  return headers
}

// 本地防爆 fetch 封装
const authAwareFetch = async (url, options = {}) => {
  const response = await fetch(url, options)
  if (response.status === 401) {
    console.warn('GIS 地图会话未带凭证或未登录')
  }
  return response
}

// 从后端 PostgreSQL 数据库读取真实打点数据
const fetchGisMarkers = async () => {
  try {
    const headers = buildAuthHeaders({ 'Accept': 'application/json' })
    const res = await authAwareFetch('/api/v1/projects/insulation_pipe_supply_2026/gis/markers', {
      headers
    })
    const json = await res.json()
    if (json.ok && Array.isArray(json.data)) {
      markersList.value = json.data
      if (Array.isArray(json.systemSections)) {
        systemSections.value = json.systemSections
      }
      renderMapElements()
    } else {
      console.error('拉取数据库标注数据异常:', json)
    }
  } catch (err) {
    console.error('网络请求数据库标注失败:', err)
  }
}

// 获取当前手机/浏览器高精度 GPS 定位并自动填入点位表单
const getCurrentGpsLocation = () => {
  if (!mapInstance || !amapObject) {
    alert('地图尚未初始化完成，请稍候重试！')
    return
  }

  locatingGps.value = true

  // 1. 优先使用高德地图 Geolocation 高精度融合定位插件
  amapObject.plugin('AMap.Geolocation', () => {
    try {
      const geolocation = new amapObject.Geolocation({
        enableHighAccuracy: true, // 使用高精度芯片定位
        timeout: 9000,            // 超时 9 秒
        buttonPosition: 'RB',     // 停靠位置
        zoomToAccuracy: false,
        showMarker: false,        // 不生成高德默认打点
        showCircle: false
      })

      geolocation.getCurrentPosition((status, result) => {
        if (status === 'complete' && result && result.position) {
          locatingGps.value = false
          const lng = Number(result.position.lng.toFixed(6))
          const lat = Number(result.position.lat.toFixed(6))
          
          formModel.value.lng = lng
          formModel.value.lat = lat
          activeSideTab.value = 'form'

          mapInstance.setZoomAndCenter(17, [lng, lat])
          renderOrUpdateDraftMarker(lng, lat)
        } else {
          fallbackNativeGeolocation()
        }
      })
    } catch (e) {
      fallbackNativeGeolocation()
    }
  })
}

// 原生 HTML5 浏览器定位回退方案
const fallbackNativeGeolocation = () => {
  if (typeof window === 'undefined' || !window.navigator || !window.navigator.geolocation) {
    locatingGps.value = false
    alert('您的设备或浏览器不支持原生 GPS 定位，请手动点击地图取点。')
    return
  }

  window.navigator.geolocation.getCurrentPosition(
    (pos) => {
      locatingGps.value = false
      const lng = Number(pos.coords.longitude.toFixed(6))
      const lat = Number(pos.coords.latitude.toFixed(6))

      formModel.value.lng = lng
      formModel.value.lat = lat
      activeSideTab.value = 'form'

      mapInstance.setZoomAndCenter(17, [lng, lat])
      renderOrUpdateDraftMarker(lng, lat)
    },
    (err) => {
      locatingGps.value = false
      let errMsg = '获取手机 GPS 定位失败。'
      if (err.code === 1) errMsg = '定位请求被拒绝，请在手机浏览器设置中允许地理位置权限。'
      else if (err.code === 2) errMsg = '位置不可用，请确保手机 GPS 已开启。'
      else if (err.code === 3) errMsg = '定位请求超时。'
      alert(errMsg + ' 建议直接在地图上点击取点。')
    },
    { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
  )
}

// 切换管道连线显隐
const togglePipelineVisibility = () => {
  showPipeline.value = !showPipeline.value
  renderMapElements()
}

// 调整焊口在连线中的顺序并同步给地图
const moveWeldOrder = (index, direction) => {
  const list = markersList.value
  if (direction === 'up' && index > 0) {
    const temp = list[index]
    list[index] = list[index - 1]
    list[index - 1] = temp
  } else if (direction === 'down' && index < list.length - 1) {
    const temp = list[index]
    list[index] = list[index + 1]
    list[index + 1] = temp
  }
  renderMapElements()
}

// 动态从后端拉取加密解密后的高德地图 Key 配置
const fetchGisMapConfig = async () => {
  try {
    const headers = buildAuthHeaders({ 'Accept': 'application/json' })
    const res = await authAwareFetch('/api/v1/projects/insulation_pipe_supply_2026/gis/config', { headers })
    const json = await res.json()
    if (json && json.ok && json.api_key) {
      currentAmapKey.value = json.api_key
      currentAmapSecurityCode.value = json.security_code || ''
    }
  } catch (err) {
    console.warn('动态拉取高德地图配置失败，回退默认配置:', err)
  }
}

// 异步加载高德地图 JS SDK 2.0
const loadAMapScript = () => {
  return new Promise((resolve, reject) => {
    if (window.AMap) {
      resolve(window.AMap)
      return
    }

    window._AMapSecurityConfig = {
      securityJsCode: currentAmapSecurityCode.value || DEFAULT_AMAP_SECURITY_CODE
    }

    const script = document.createElement('script')
    script.type = 'text/javascript'
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${currentAmapKey.value || DEFAULT_AMAP_KEY}&plugin=AMap.Scale,AMap.ToolBar,AMap.ControlBar,AMap.Geocoder,AMap.PlaceSearch`
    script.onerror = () => reject(new Error('高德地图 SDK 网络请求失败，请检查 API Key 或网络'))
    script.onload = () => {
      if (window.AMap) {
        resolve(window.AMap)
      } else {
        reject(new Error('高德地图对象加载异常'))
      }
    }
    document.head.appendChild(script)
  })
}

// 初始化高德地图
const initMap = async () => {
  mapLoading.value = true
  mapError.value = ''
  try {
    // 动态拉取后台加密配置的高德 Key
    await fetchGisMapConfig()
    amapObject = await loadAMapScript()

    mapInstance = new amapObject.Map('amap-container', {
      viewMode: '2D',
      zoom: 14,
      center: [CENTER_LNG, CENTER_LAT]
    })

    mapInstance.addControl(new amapObject.Scale())
    mapInstance.addControl(new amapObject.ToolBar({ position: 'RB' }))
    mapInstance.on('click', handleMapClick)

    // 地图加载完成后从 PostgreSQL 数据库拉取打点
    await fetchGisMarkers()

    mapLoading.value = false
  } catch (err) {
    console.error(err)
    mapLoading.value = false
    mapError.value = err.message || '初始化地图失败'
  }
}

// 6 种点位类型的标准化图标、视觉颜色与主题定义
const MARKER_TYPE_CONFIG = {
  weld: { label: '焊口', icon: '🔩', color: '#2563eb', pointerColor: '#1d4ed8', bgColor: '#2563eb' },
  meter: { label: '表计', icon: '⏱️', color: '#0284c7', pointerColor: '#0369a1', bgColor: '#0284c7' },
  tee: { label: '三通', icon: '🔀', color: '#d97706', pointerColor: '#b45309', bgColor: '#d97706' },
  compensator: { label: '补偿器', icon: '〰️', color: '#059669', pointerColor: '#047857', bgColor: '#059669' },
  elbow: { label: '弯头', icon: '↪️', color: '#7c3aed', pointerColor: '#6d28d9', bgColor: '#7c3aed' },
  valve: { label: '阀门', icon: '🚰', color: '#e11d48', pointerColor: '#be123c', bgColor: '#e11d48' },
}

function getMarkerTypeLabel(type) {
  return MARKER_TYPE_CONFIG[type]?.label || '点位'
}

function getMarkerTypeIcon(type) {
  return MARKER_TYPE_CONFIG[type]?.icon || '📌'
}

// 辅助展示父节点富文本信息
function getParentNodeDisplay(parentCode) {
  if (!parentCode) return ''
  const parent = markersList.value.find(m => m.code === parentCode)
  if (parent) {
    const icon = getMarkerTypeIcon(parent.type)
    return `${icon} ${parent.code} (${parent.name})`
  }
  return parentCode
}

function getParentNodeTitle(parentCode) {
  if (!parentCode) return ''
  const parent = markersList.value.find(m => m.code === parentCode)
  if (parent) {
    return `父节点: ${parent.code} | 名称: ${parent.name} | 管线: ${parent.pipelineName}`
  }
  return `父节点: ${parentCode}`
}

// 提取当前可作为【上级节点】的点位列表 (仅包含焊口与三通)
const existingParentNodeOptions = computed(() => {
  return markersList.value.filter(m => m.type === 'weld' || m.type === 'tee')
})

// 自动推荐的上级节点 Code
const autoSuggestedParentCode = ref('')

// 智能推导算法：根据传入的经纬度坐标 (lng, lat)，在现有焊口与三通中自动计算距离最近的点位作为推荐上级
const findNearestParentNode = (lng, lat, ignoreCode = '') => {
  if (!lng || !lat || !markersList.value.length) return ''
  
  // 筛选出非当前的焊口与三通
  const candidates = markersList.value.filter(m => (m.type === 'weld' || m.type === 'tee') && m.code !== ignoreCode)
  if (candidates.length === 0) return ''

  let minDistance = Infinity
  let nearestCode = ''

  candidates.forEach(m => {
    const dLng = m.lng - lng
    const dLat = m.lat - lat
    // 欧式经纬度近似距离计算
    const dist = dLng * dLng + dLat * dLat
    if (dist < minDistance) {
      minDistance = dist
      nearestCode = m.code
    }
  })

  return nearestCode
}

// 构造精密的下尖大头针（GIS Pin Marker）HTML
const createPinMarkerElement = (bgColor, pointerColor, iconSymbol, labelCode, isDraft = false) => {
  const containerDiv = document.createElement('div')
  containerDiv.className = isDraft ? 'gis-pin-marker draft-pin-animated' : 'gis-pin-marker'

  containerDiv.innerHTML = `
    <div class="pin-head" style="background-color: ${bgColor};">
      <span>${iconSymbol}</span> <span>${labelCode}</span>
    </div>
    <div class="pin-pointer" style="border-top-color: ${pointerColor};"></div>
  `
  return containerDiv
}

// 按【管线名称/编号】分组独立绘制 Polyline 管线轨迹 (仅焊口与三通参与连线，三通引出分支)
const renderMapElements = () => {
  if (!mapInstance || !amapObject) return

  mapMarkerObjects.forEach(m => mapInstance.remove(m))
  mapMarkerObjects = []

  pipelinePolylines.forEach(p => mapInstance.remove(p))
  pipelinePolylines = []

  // 1. 按【管线名称/编号】分组绘制 Polyline 连线 (仅焊口 weld 和三通 tee 参与连线)
  if (showPipeline.value) {
    const pipeGroups = {}
    
    filteredMarkers.value.forEach(m => {
      // 核心业务规则：只有焊口 (weld) 和三通 (tee) 参与管线连线
      if ((m.type === 'weld' || m.type === 'tee') && m.pipelineName && m.pipelineName.trim()) {
        const pipeKey = m.pipelineName.trim()
        if (!pipeGroups[pipeKey]) {
          pipeGroups[pipeKey] = []
        }
        pipeGroups[pipeKey].push(m)
      }
    })

    const pipeColors = ['#0284c7', '#4f46e5', '#7c3aed', '#059669', '#d97706', '#dc2626']
    let colorIdx = 0

    Object.keys(pipeGroups).forEach(pipeName => {
      const allConnectNodes = pipeGroups[pipeName]
      if (allConnectNodes.length < 2) return

      // 按 sortOrder 排序
      allConnectNodes.sort((a, b) => (a.sortOrder || 0) - (b.sortOrder || 0))

      // 构建该管线下所有连线节点的 ID/Code 索引字典
      const nodeMap = new Map()
      // 全局字典：便于跨管线引用三通
      markersList.value.forEach(n => {
        if (n.type === 'weld' || n.type === 'tee') {
          nodeMap.set(n.code, n)
        }
      })

      // 检查当前管线是否已有显式配置了父节点的节点
      const hasAnyParentConfig = allConnectNodes.some(n => n.parentCode && nodeMap.has(n.parentCode))

      const segments = []
      let lastNodePos = null

      allConnectNodes.forEach(n => {
        const currentPos = [n.lng, n.lat]
        // 核心拓扑规则：若节点显式声明了 parentCode 且匹配到上级，按拓扑连线
        if ((n.type === 'weld' || n.type === 'tee') && n.parentCode && nodeMap.has(n.parentCode)) {
          const parentNode = nodeMap.get(n.parentCode)
          segments.push([[parentNode.lng, parentNode.lat], currentPos])
        } else if (!hasAnyParentConfig && lastNodePos) {
          // 仅当整条管线没有任何 parentCode 配置时，才按 sortOrder 顺次连接
          segments.push([lastNodePos, currentPos])
        }
        lastNodePos = currentPos
      })

      const currentColor = pipeColors[colorIdx % pipeColors.length]
      colorIdx++

      segments.forEach(path => {
        const polyline = new amapObject.Polyline({
          path: path,
          isOutline: true,
          outlineColor: '#0f172a',
          borderWeight: 2,
          strokeColor: currentColor,
          strokeOpacity: 0.92,
          strokeWeight: 6,
          strokeStyle: 'solid',
          lineJoin: 'round',
          lineCap: 'round',
          zIndex: 50,
        })
        mapInstance.add(polyline)
        pipelinePolylines.push(polyline)
      })
    })
  }

  // 2. 渲染 6 种类型的 Marker 点位
  filteredMarkers.value.forEach(item => {
    const cfg = MARKER_TYPE_CONFIG[item.type] || MARKER_TYPE_CONFIG.weld
    let bgColor = cfg.bgColor
    let pointerColor = cfg.pointerColor
    let iconSymbol = cfg.icon

    if (item.type === 'weld') {
      if (item.status === 'pending') {
        bgColor = '#d97706'
        pointerColor = '#b45309'
      } else if (item.status === 'failed') {
        bgColor = '#dc2626'
        pointerColor = '#b91c1c'
      }
    } else if (item.type === 'valve') {
      if (item.status === 'closed') {
        bgColor = '#d97706'
        pointerColor = '#b45309'
      }
    }

    const pinElement = createPinMarkerElement(bgColor, pointerColor, iconSymbol, item.code)

    const marker = new amapObject.Marker({
      position: [item.lng, item.lat],
      content: pinElement,
      draggable: true,
      anchor: 'bottom-center',
      offset: new amapObject.Pixel(0, 0),
      title: `按住针脚可直接拖拽调整 ${item.code} 坐标`
    })

    marker.on('click', () => {
      openInfoWindow(item, [item.lng, item.lat])
    })

    marker.on('dragend', async (e) => {
      const newLngRaw = typeof e.lnglat.getLng === 'function' ? e.lnglat.getLng() : e.lnglat.lng
      const newLatRaw = typeof e.lnglat.getLat === 'function' ? e.lnglat.getLat() : e.lnglat.lat

      const newLng = Number(newLngRaw.toFixed(6))
      const newLat = Number(newLatRaw.toFixed(6))

      // 备份旧坐标
      const oldLng = item.lng
      const oldLat = item.lat

      // 弹出确认询问框
      const isConfirmed = confirm(
        `📍 点位 [${item.code} - ${item.name}] 坐标发生变更：\n\n` +
        `原坐标：${oldLng}, ${oldLat}\n` +
        `新落点：${newLng}, ${newLat}\n\n` +
        `是否确认保存该点位的新坐标？`
      )

      if (!isConfirmed) {
        // 用户取消：大头针图标归位复原至旧坐标
        marker.setPosition([oldLng, oldLat])
        return
      }

      // 用户确认：更新数据模型与表单，并持久化到 PostgreSQL 数据库
      item.lng = newLng
      item.lat = newLat

      if (editingId.value === item.id) {
        formModel.value.lng = item.lng
        formModel.value.lat = item.lat
      }

      try {
        const headers = buildAuthHeaders({ 'Content-Type': 'application/json' })
        await authAwareFetch(`/api/v1/projects/insulation_pipe_supply_2026/gis/markers/${item.id}`, {
          method: 'PUT',
          headers,
          body: JSON.stringify({
            type: item.type,
            sectionName: item.sectionName || '',
            pipelineName: item.pipelineName || '',
            code: item.code,
            name: item.name,
            lng: item.lng,
            lat: item.lat,
            status: item.status,
            spec: item.spec || '',
            remarks: item.remarks || '',
            sortOrder: item.sortOrder || 0,
            parentCode: item.parentCode || ''
          })
        })
      } catch (err) {
        console.error('拖拽同步数据库失败:', err)
        alert('同步数据库坐标失败: ' + err.message)
      }

      renderMapElements()
    })

    mapInstance.add(marker)
    mapMarkerObjects.push(marker)
  })
}

// 渲染/更新草稿 Marker
const renderOrUpdateDraftMarker = (lng, lat) => {
  if (!mapInstance || !amapObject) return

  hasDraftMarker.value = true

  const symbol = formModel.value.type === 'weld' ? '🔩' : '⏱️'
  const codeText = formModel.value.code || '待保存点位'
  const draftColor = '#d97706'

  if (draftMarkerObject) {
    draftMarkerObject.setPosition([lng, lat])
    const contentDiv = createPinMarkerElement(draftColor, draftColor, symbol, codeText, true)
    draftMarkerObject.setContent(contentDiv)
  } else {
    const draftPinEl = createPinMarkerElement(draftColor, draftColor, symbol, codeText, true)

    draftMarkerObject = new amapObject.Marker({
      position: [lng, lat],
      content: draftPinEl,
      anchor: 'bottom-center',
      draggable: true,
      offset: new amapObject.Pixel(0, 0),
      title: '待保存草稿针点（可在右侧表单修改详情）'
    })

    draftMarkerObject.on('dragend', (e) => {
      const dLng = typeof e.lnglat.getLng === 'function' ? e.lnglat.getLng() : e.lnglat.lng
      const dLat = typeof e.lnglat.getLat === 'function' ? e.lnglat.getLat() : e.lnglat.lat

      formModel.value.lng = Number(dLng.toFixed(6))
      formModel.value.lat = Number(dLat.toFixed(6))
    })

    mapInstance.add(draftMarkerObject)
  }

  openInfoWindow({
    type: formModel.value.type,
    code: codeText,
    pipelineName: formModel.value.pipelineName,
    name: formModel.value.name || '待保存实时点位',
    statusText: '📍 草稿点位，保存后写入数据库',
    remarks: '草稿落点就绪，可在右侧编辑详情。'
  }, [lng, lat])
}

// 清除草稿 Marker
const clearDraftMarker = () => {
  const markerToRemove = draftMarkerObject
  draftMarkerObject = null
  hasDraftMarker.value = false

  if (!markerToRemove || !mapInstance) return

  try {
    mapInstance.remove(markerToRemove)
  } catch (err) {
    // 地图覆盖物异常不能中断新增、取消或编辑点位的主流程。
    console.warn('清理 GIS 草稿点位失败，已跳过地图覆盖物移除：', err)
  }
}

// 更改表单字段时更新草稿 Marker 内容
const updateDraftMarkerIcon = () => {
  if (hasDraftMarker.value && formModel.value.lng && formModel.value.lat) {
    renderOrUpdateDraftMarker(formModel.value.lng, formModel.value.lat)
  }
}

// 辅助函数：将选中的数据卡片平滑居中滚动露出在右侧列表中
const scrollToTargetCard = (markerId) => {
  if (!markerId) return
  nextTick(() => {
    // 延迟 60ms 确保 Tab 切换及 Vue v-if DOM 渲染装载就绪
    setTimeout(() => {
      const targetCardEl = document.getElementById(`marker-card-${markerId}`)
      const containerEl = document.querySelector('.panel-content')

      if (targetCardEl) {
        // 1. 优先触发标准的 scrollIntoView 强行垂直居中
        targetCardEl.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' })

        // 2. 双保险：在滚动容器中进行绝对 scrollTop 偏移计算，确保 100% 暴露在视野中央
        if (containerEl) {
          const containerRect = containerEl.getBoundingClientRect()
          const cardRect = targetCardEl.getBoundingClientRect()
          const relativeTop = cardRect.top - containerRect.top + containerEl.scrollTop
          const targetScrollTop = relativeTop - (containerEl.clientHeight / 2) + (cardRect.height / 2)

          containerEl.scrollTo({
            top: Math.max(0, targetScrollTop),
            behavior: 'smooth'
          })
        }
      }
    }, 60)
  })
}

// 弹出高德地图 InfoWindow 信息窗口并联动右侧表格卡片居中定位高亮
const openInfoWindow = (item, position) => {
  if (!mapInstance || !amapObject) return

  if (item && item.id) {
    selectedMarkerId.value = item.id
    // 若当前未处于表单编辑界面，才联动滚动侧边栏卡片
    if (activeSideTab.value !== 'form') {
      activeSideTab.value = 'list'
      if (selectedTypes.value.length > 0 && !selectedTypes.value.includes(item.type)) {
        selectedTypes.value.push(item.type)
      }
      scrollToTargetCard(item.id)
    }
  }

  const cfg = MARKER_TYPE_CONFIG[item.type] || MARKER_TYPE_CONFIG.weld
  const typeTitle = item.type === 'search' ? '📍 搜索结果' : `${cfg.icon} ${cfg.label}`

  const infoHtml = `
    <div style="padding:10px 6px; font-family: sans-serif; min-width:240px;">
      <h4 style="margin:0 0 6px 0; font-size:14px; color:#0f172a; display:flex; align-items:center; gap:6px;">
        ${typeTitle} <span style="color:#0284c7;">${item.code}</span>
      </h4>
      ${item.sectionName ? `<p style="margin:4px 0; font-size:12px; color:#4f46e5;"><strong>施工标段：</strong>${item.sectionName}</p>` : ''}
      ${item.pipelineName ? `<p style="margin:4px 0; font-size:12px; color:#0284c7;"><strong>管线名称/编号：</strong>${item.pipelineName}</p>` : ''}
      ${item.parentCode ? `<p style="margin:4px 0; font-size:12px; color:#d97706;"><strong>父节点：</strong>${getParentNodeDisplay(item.parentCode)}</p>` : ''}
      <p style="margin:4px 0; font-size:12px; color:#475569;"><strong>名称描述：</strong>${item.name}</p>
      <p style="margin:4px 0; font-size:12px; color:#475569;"><strong>状态：</strong><span style="font-weight:600; color:${item.status === 'passed' ? '#10b981' : '#0284c7'};">${item.statusText}</span></p>
      ${item.spec ? `<p style="margin:4px 0; font-size:12px; color:#475569;"><strong>关联保温管：</strong>${item.spec}</p>` : ''}
      ${item.createdAt ? `<p style="margin:4px 0; font-size:11px; color:#64748b;"><strong>录入时间：</strong>${item.createdAt}</p>` : ''}
      <p style="margin:4px 0; font-size:11px; color:#64748b; font-family:monospace;"><strong>精准坐标：</strong>${Number(position[0]).toFixed(6)}, ${Number(position[1]).toFixed(6)}</p>
      ${item.remarks ? `<p style="margin:6px 0 0 0; font-size:11px; color:#94a3b8; border-top:1px dashed #e2e8f0; padding-top:4px;">${item.remarks}</p>` : ''}
      ${item.id ? `
        <div style="margin-top:10px; padding-top:8px; border-top:1px solid #f1f5f9; display:flex; justify-content:flex-end; gap:8px;">
          <button id="infowindow-edit-btn-${item.id}" type="button" style="background:#0284c7; color:#ffffff; border:none; border-radius:4px; padding:4px 10px; font-size:11px; font-weight:600; cursor:pointer;">✏️ 编辑此点位</button>
        </div>
      ` : ''}
    </div>
  `

  const infoWindow = new amapObject.InfoWindow({
    content: infoHtml,
    offset: new amapObject.Pixel(0, -35)
  })

  infoWindow.open(mapInstance, position)

  if (item.id) {
    setTimeout(() => {
      const editBtn = document.getElementById(`infowindow-edit-btn-${item.id}`)
      if (editBtn) {
        editBtn.addEventListener('click', () => {
          infoWindow.close()
          startEditMarker(item)
        })
      }
    }, 60)
  }
}

// 辅助函数：在地图上展示搜索 Marker 提示弹窗
const showSearchMarkerOnMap = (title, position) => {
  if (!mapInstance || !amapObject) return

  if (searchPromptMarker) {
    mapInstance.remove(searchPromptMarker)
  }

  const searchPinEl = createPinMarkerElement('#0284c7', '#0284c7', '🔍', '定位点')

  searchPromptMarker = new amapObject.Marker({
    position: position,
    content: searchPinEl,
    anchor: 'bottom-center',
    title: `搜索定位: ${title}`
  })
  mapInstance.add(searchPromptMarker)

  openInfoWindow({
    type: 'search',
    code: '搜索定位',
    name: title,
    statusText: '定位成功',
    remarks: '大头针底端已精确对准搜索地点原点'
  }, position)
}

// 地名搜索定位 (双引擎：Geocoder + PlaceSearch)
const handleSearchLocation = () => {
  const kw = searchKeyword.value.trim()
  if (!kw || !amapObject || !mapInstance) return
  searchLoading.value = true

  amapObject.plugin(['AMap.Geocoder', 'AMap.PlaceSearch'], () => {
    const geocoder = new amapObject.Geocoder({
      city: '0411'
    })

    geocoder.getLocation(kw, (status, result) => {
      if (status === 'complete' && result.geocodes && result.geocodes.length) {
        searchLoading.value = false
        const target = result.geocodes[0].location
        const lng = typeof target.getLng === 'function' ? target.getLng() : target.lng
        const lat = typeof target.getLat === 'function' ? target.getLat() : target.lat

        mapInstance.setZoomAndCenter(15, [lng, lat])
        showSearchMarkerOnMap(result.geocodes[0].formattedAddress || kw, [lng, lat])
      } else {
        const placeSearch = new amapObject.PlaceSearch({
          city: '0411'
        })

        placeSearch.search(kw, (pStatus, pResult) => {
          searchLoading.value = false
          if (pStatus === 'complete' && pResult.poiList && pResult.poiList.pois && pResult.poiList.pois.length) {
            const poi = pResult.poiList.pois[0]
            const lng = typeof poi.location.getLng === 'function' ? poi.location.getLng() : poi.location.lng
            const lat = typeof poi.location.getLat === 'function' ? poi.location.getLat() : poi.location.lat

            mapInstance.setZoomAndCenter(16, [lng, lat])
            showSearchMarkerOnMap(`${poi.name} (${poi.address || poi.cityname || ''})`, [lng, lat])
          } else {
            alert(`未搜寻到地点 "${kw}"，请检查地名拼写（示例：香炉礁、大连港、周水子、中山区等）`)
          }
        })
      }
    })
  })
}

// 点击地图拾取坐标：生成草稿针并自动智能推导上级节点
const handleMapClick = (e) => {
  if (!isPickingPoint.value) return

  const lng = typeof e.lnglat.getLng === 'function' ? e.lnglat.getLng() : e.lnglat.lng
  const lat = typeof e.lnglat.getLat === 'function' ? e.lnglat.getLat() : e.lnglat.lat

  formModel.value.lng = Number(lng.toFixed(6))
  formModel.value.lat = Number(lat.toFixed(6))

  // 在新增点位模式且类型为焊口时，自动基于物理坐标智能推导最近的上级节点 (焊口或三通)
  if (!editingId.value && formModel.value.type === 'weld') {
    const suggested = findNearestParentNode(formModel.value.lng, formModel.value.lat)
    if (suggested) {
      autoSuggestedParentCode.value = suggested
      formModel.value.parentCode = suggested
    }
  }

  renderOrUpdateDraftMarker(formModel.value.lng, formModel.value.lat)

  activeSideTab.value = 'form'
  isPickingPoint.value = false

  if (mapInstance) {
    mapInstance.setDefaultCursor('pointer')
  }
}

// 切换/开启鼠标点选模式
const togglePickPointMode = () => {
  isPickingPoint.value = !isPickingPoint.value
  if (isPickingPoint.value) {
    if (mapInstance) {
      mapInstance.setDefaultCursor('crosshair')
    }
  } else {
    if (mapInstance) {
      mapInstance.setDefaultCursor('pointer')
    }
  }
}

// 聚焦到选中的 Marker 并更新高亮
const focusMarkerOnMap = (item) => {
  if (!mapInstance) return
  selectedMarkerId.value = item?.id || null
  mapInstance.setZoomAndCenter(16, [item.lng, item.lat])
  openInfoWindow(item, [item.lng, item.lat])
}

// 手动点击表单 Tab 时的无缝处理
const handleFormTabClick = () => {
  activeSideTab.value = 'form'
  // 若既非编辑模式也未开辟草稿填报，自动初始化新增表单
  if (!editingId.value && !formModel.value.code && !formModel.value.lng) {
    startAddNewMarker()
  }
}

// 启动新增模式
const startAddNewMarker = () => {
  editingId.value = null
  autoSuggestedParentCode.value = ''
  clearDraftMarker()
  activeSideTab.value = 'form'
  formModel.value = {
    type: 'weld',
    sectionName: '',
    pipelineName: '',
    code: '',
    name: '',
    lng: '',
    lat: '',
    status: 'passed',
    spec: '',
    remarks: '',
    parentCode: ''
  }
}

// 启动编辑现有点位模式 (保持原始 created_at 与 parentCode 不变)
const startEditMarker = (item) => {
  if (!item) return
  editingId.value = item.id
  selectedMarkerId.value = item.id
  autoSuggestedParentCode.value = ''

  formModel.value = {
    type: item.type || 'weld',
    sectionName: item.sectionName || '',
    pipelineName: item.pipelineName || '',
    code: item.code || '',
    name: item.name || '',
    lng: item.lng,
    lat: item.lat,
    status: item.status || 'passed',
    spec: item.spec || '',
    remarks: item.remarks || '',
    sortOrder: item.sortOrder || 0,
    parentCode: item.parentCode || ''
  }

  // 1. 先切换到编辑表单，保证地图草稿清理异常不会阻断编辑入口。
  activeSideTab.value = 'form'

  // 2. 再清理可能遗留的新增草稿点位；该操作内部已隔离地图覆盖物异常。
  clearDraftMarker()

  // 3. 双保险：在 nextTick 延迟中重置滚动条置顶，确保 Vue 视图彻底完成表单渲染呈现
  nextTick(() => {
    const sideContentEl = document.querySelector('.gis-side-panel .panel-content')
    if (sideContentEl) {
      sideContentEl.scrollTo({ top: 0, behavior: 'smooth' })
    }
  })

  // 4. 地图联动平移定位
  if (mapInstance && item.lng && item.lat) {
    mapInstance.setZoomAndCenter(16, [item.lng, item.lat])
  }
}

// 取消编辑并清除草稿点位
const cancelEditing = () => {
  editingId.value = null
  clearDraftMarker()
  activeSideTab.value = 'list'
}

// 保存 (新增或更新) 点位到 PostgreSQL 数据库 (带 Bearer Token 鉴权头)
const saveMarkerData = async () => {
  if (!formModel.value.lng || !formModel.value.lat) {
    alert('请设置点位的经纬度坐标！')
    return
  }

  saving.value = true
  const payload = {
    type: formModel.value.type,
    sectionName: formModel.value.sectionName,
    pipelineName: formModel.value.pipelineName,
    code: formModel.value.code,
    name: formModel.value.name,
    lng: Number(formModel.value.lng),
    lat: Number(formModel.value.lat),
    status: formModel.value.status,
    spec: formModel.value.spec,
    remarks: formModel.value.remarks,
    sortOrder: formModel.value.sortOrder || 0,
    parentCode: formModel.value.parentCode || ''
  }

  try {
    let url = '/api/v1/projects/insulation_pipe_supply_2026/gis/markers'
    let method = 'POST'
    if (editingId.value) {
      url += `/${editingId.value}`
      method = 'PUT'
    }

    const headers = buildAuthHeaders({
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    })

    const res = await authAwareFetch(url, {
      method: method,
      headers,
      body: JSON.stringify(payload)
    })
    const json = await res.json()
    saving.value = false

    if (json.ok) {
      clearDraftMarker()
      await fetchGisMarkers()
      activeSideTab.value = 'list'
      editingId.value = null
    } else {
      alert(json.detail || '保存到数据库失败')
    }
  } catch (err) {
    saving.value = false
    alert('保存点位发生网络异常: ' + err.message)
  }
}

// 从 PostgreSQL 数据库彻底删除点位 (带 Bearer Token 鉴权头)
const deleteMarker = async (item) => {
  if (!confirm(`确定要从数据库中彻底删除 ${item.type === 'weld' ? '焊口' : '表计'} 点位 "${item.code}" 吗？`)) {
    return
  }

  try {
    const headers = buildAuthHeaders()
    const res = await authAwareFetch(`/api/v1/projects/insulation_pipe_supply_2026/gis/markers/${item.id}`, {
      method: 'DELETE',
      headers
    })
    const json = await res.json()
    if (json.ok) {
      await fetchGisMarkers()
    } else {
      alert(json.detail || '删除数据库记录失败')
    }
  } catch (err) {
    alert('删除点位发生网络异常: ' + err.message)
  }
}

onMounted(() => {
  initMap()
})

onUnmounted(() => {
  clearDraftMarker()
  if (mapInstance) {
    mapInstance.destroy()
  }
})
</script>

<style scoped>
.gis-map-view {
  min-height: 100vh;
  background-color: #f8fafc;
  display: flex;
  flex-direction: column;
}

.page-main {
  flex: 1;
}

.gis-container {
  width: 96%;
  max-width: 1720px;
  margin: 0 auto;
  padding: 16px 24px 32px 24px;
  box-sizing: border-box;
}

.page-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  gap: 16px;
  flex-wrap: wrap;
}

.title-wrap h2 {
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 4px 0;
}

.subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

/* 搜索栏与返回按钮 */
.search-location-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.search-input-wrap {
  display: flex;
  align-items: center;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 2px 4px 2px 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.search-icon {
  color: #94a3b8;
  font-size: 14px;
  margin-right: 6px;
}

.search-input {
  border: none;
  outline: none;
  font-size: 13px;
  color: #0f172a;
  min-width: 240px;
}

.search-btn {
  height: 32px;
  padding: 0 12px;
  font-size: 13px;
  border-radius: 6px;
}

.gis-main-container {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06);
  display: flex;
  flex-direction: column;
}

/* 顶部指标统计栏 */
.gis-stats-bar {
  display: flex;
  align-items: center;
  padding: 14px 20px;
  background: #f1f5f9;
  border-bottom: 1px solid #e2e8f0;
  gap: 24px;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  line-height: 1.2;
}

.stat-value small {
  font-size: 12px;
  font-weight: 500;
}

.text-blue { color: #0284c7; }
.text-emerald { color: #059669; }
.text-indigo { color: #4f46e5; }
.text-amber { color: #d97706; }
.text-mono { font-family: monospace; }
.font-bold { font-weight: 700; }

.stat-divider {
  width: 1px;
  height: 28px;
  background: #cbd5e1;
}

.stat-actions {
  margin-left: auto;
}

.pick-point-banner {
  background: #fef3c7;
  color: #92400e;
  border-bottom: 1px solid #fde68a;
  padding: 10px 20px;
  font-size: 13px;
}

/* 图例说明条与连线控制 */
.legend-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 20px;
  background: #ffffff;
  border-bottom: 1px solid #f1f5f9;
  font-size: 12px;
  color: #475569;
  flex-wrap: wrap;
}

.legend-title {
  font-weight: 600;
  color: #0f172a;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.control-btn-group {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
}

.filter-popover-wrapper {
  position: relative;
}

.filter-count-badge {
  background: #ef4444;
  color: #ffffff;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 10px;
  margin-left: 2px;
}

/* 高级多维筛选下拉 Popover 悬浮面板 */
.filter-popover-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 320px;
  max-width: calc(100vw - 32px);
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  box-shadow: 0 10px 25px rgba(15, 23, 42, 0.18);
  z-index: 1000;
  overflow: hidden;
  box-sizing: border-box;
}

.popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.close-popover-btn {
  background: transparent;
  border: none;
  font-size: 14px;
  color: #94a3b8;
  cursor: pointer;
}

.close-popover-btn:hover {
  color: #0f172a;
}

.popover-body {
  padding: 12px 14px;
  max-height: 380px;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: 14px;
  box-sizing: border-box;
}

.date-filter-grid {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  width: 100%;
  box-sizing: border-box;
}

.date-input-compact {
  flex: 1;
  min-width: 0;
  height: 28px;
  padding: 2px 4px;
  font-size: 11px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #f8fafc;
  color: #334155;
  outline: none;
  box-sizing: border-box;
  transition: all 0.2s;
}

.date-input-compact:focus {
  border-color: #0284c7;
  background: #ffffff;
  box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.15);
}

.date-input-compact::-webkit-calendar-picker-indicator {
  cursor: pointer;
  opacity: 0.7;
  padding: 0;
  margin: 0;
}

.date-separator {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.filter-section-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.group-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.group-title {
  font-size: 12px;
  font-weight: 700;
  color: #334155;
}

.text-link-btn {
  background: transparent;
  border: none;
  color: #0284c7;
  font-size: 11px;
  cursor: pointer;
  padding: 0;
}

.text-link-btn:hover {
  text-decoration: underline;
}

.checkbox-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-left: 4px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #475569;
  cursor: pointer;
}

.checkbox-label input {
  cursor: pointer;
}

.popover-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.dot-passed { background: #10b981; }
.dot-pending { background: #f59e0b; }
.dot-failed { background: #ef4444; }
.dot-meter { background: #3b82f6; }
.dot-draft { background: #d97706; border: 1px solid #b45309; }

.line-sample {
  width: 24px;
  height: 4px;
  background: #0284c7;
  border-radius: 2px;
  display: inline-block;
}

.field-tip {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
}

/* 专业 GIS 大头针 Marker 样式 */
:deep(.gis-pin-marker) {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: grab;
}

:deep(.gis-pin-marker:active) {
  cursor: grabbing;
}

:deep(.pin-head) {
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 700;
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.3);
  border: 1.5px solid #ffffff;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 4px;
  font-family: "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji", "Consolas", sans-serif;
}

:deep(.pin-pointer) {
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 8px solid #10b981;
  margin-top: -1px;
}

:deep(.draft-pin-animated) {
  animation: bouncePin 1.2s infinite ease-in-out;
}

@keyframes bouncePin {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}

/* 主主体布局 */
.gis-body-grid {
  display: grid;
  grid-template-columns: 1fr 360px;
  height: calc(100vh - 240px);
  min-height: 680px;
}

.map-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 680px;
}

.amap-box {
  width: 100%;
  height: 100%;
  min-height: 680px;
}

.map-loading-overlay, .map-error-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(255, 255, 255, 0.88);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 10;
}

.map-error-overlay {
  color: #dc2626;
  font-weight: 600;
  padding: 20px;
  text-align: center;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid #e2e8f0;
  border-top-color: #0284c7;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 12px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-size: 13px;
  color: #475569;
}

/* 右侧侧边栏 */
.gis-side-panel {
  border-left: 1px solid #e2e8f0;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-tabs {
  display: flex;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}

.tab-btn {
  flex: 1;
  padding: 12px 8px;
  border: none;
  background: transparent;
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.tab-btn.active {
  color: #0284c7;
  border-bottom-color: #0284c7;
  background: #ffffff;
}

.panel-content {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  max-height: calc(100vh - 300px);
}

.filter-box-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 12px;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.filter-label {
  font-size: 11px;
  font-weight: 600;
  color: #475569;
  white-space: nowrap;
  min-width: 80px;
}

.small-select {
  font-size: 12px;
  padding: 4px 6px;
  height: 28px;
}

.text-indigo {
  color: #4f46e5;
}

.form-header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.form-header-bar h4 {
  margin: 0;
  font-size: 14px;
  color: #0f172a;
  font-weight: 700;
}

.select-input, .text-input, .textarea-input {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 13px;
  color: #1e293b;
  background: #ffffff;
  outline: none;
  box-sizing: border-box;
}

.select-input:focus, .text-input:focus, .textarea-input:focus {
  border-color: #0284c7;
  box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.15);
}

.marker-item-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.marker-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  background: #ffffff;
  cursor: pointer;
  transition: all 0.2s;
}

.marker-card.selected-card-highlight {
  border-color: #0284c7;
  background-color: #f0f9ff;
  box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.25), 0 4px 12px rgba(2, 132, 199, 0.15);
  transform: translateY(-2px);
}

.marker-card:hover {
  border-color: #38bdf8;
  box-shadow: 0 2px 8px rgba(2, 132, 199, 0.12);
  transform: translateY(-1px);
}

.marker-card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  color: #ffffff;
}

.badge-weld { background: #0284c7; }
.badge-meter { background: #6366f1; }

.marker-code {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.status-tag {
  margin-left: auto;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.tag-success { background: #dcfce7; color: #15803d; }
.tag-warning { background: #fef3c7; color: #b45309; }
.tag-danger { background: #fee2e2; color: #b91c1c; }
.tag-info { background: #e0e7ff; color: #4338ca; }

.marker-card-body {
  font-size: 12px;
  color: #475569;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-row {
  display: flex;
  justify-content: space-between;
}

.info-row .label { color: #64748b; }
.info-row .val { font-weight: 500; text-align: right; }

/* 点位卡片操作按钮列 */
.marker-card-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed #f1f5f9;
}

.order-btn-group {
  display: flex;
  gap: 4px;
  margin-right: auto;
}

.order-btn {
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 10px;
  padding: 1px 5px;
  cursor: pointer;
}

.order-btn:hover {
  background: #e2e8f0;
}

.action-btn {
  background: transparent;
  border: none;
  font-size: 11px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  transition: background 0.2s;
}

.edit-btn { color: #0284c7; }
.edit-btn:hover { background: #e0f2fe; }

.delete-btn { color: #dc2626; }
.delete-btn:hover { background: #fee2e2; }

.empty-tip {
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
  padding: 24px 0;
}

/* 新增与编辑表单样式 */
.add-marker-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.location-group-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 10px;
  border-radius: 8px;
}

.location-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-group label {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.required {
  color: #ef4444;
}

.form-row-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.form-submit-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 6px;
}

.btn {
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s;
}

.btn.primary {
  background: #0284c7;
  color: #ffffff;
}

.btn.primary:hover {
  background: #0369a1;
}

.btn.warning {
  background: #f59e0b;
  color: #ffffff;
}

.btn.warning:hover {
  background: #d97706;
}

.btn.ghost {
  background: #ffffff;
  border-color: #cbd5e1;
  color: #475569;
}

.btn.ghost:hover {
  background: #f1f5f9;
}

.btn.small-btn {
  padding: 4px 8px;
  font-size: 11px;
}

/* 经纬度定位区域专属高颜值卡片排版 */
.location-card-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
}

.location-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.location-card-title {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.coord-inputs-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.coord-input-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.coord-prefix {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
}

.coord-field {
  font-size: 12px;
  padding: 6px 8px;
  background: #ffffff;
  border-radius: 6px;
}

.location-action-btns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.coord-btn {
  padding: 7px 6px;
  font-size: 11px;
  font-weight: 600;
  justify-content: center;
}

.coord-tip-card {
  font-size: 11px;
  color: #0369a1;
  background: #e0f2fe;
  border-left: 3px solid #0284c7;
  padding: 6px 10px;
  border-radius: 4px;
  line-height: 1.45;
}

.btn.full-width {
  width: 100%;
}

/* 移动端 (手机屏幕 <= 768px) 全响应式自适应与全宽度 Full-Bleed 铺满 */
@media (max-width: 768px) {
  /* 1. 取消外层容器固定外边距与大内边距 */
  .gis-container {
    width: 100%;
    max-width: 100%;
    margin: 0;
    padding: 6px 4px 20px 4px;
  }

  /* 2. 取消主卡片边框与圆角限制，在手机端 100% 铺满横向视野 */
  .gis-main-container {
    border-radius: 6px;
    margin: 0;
    width: 100%;
    border-left: none;
    border-right: none;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
  }

  .page-title-row {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
    padding: 0 6px;
  }

  .subtitle {
    font-size: 12px;
  }

  .coord-inputs-grid {
    grid-template-columns: 1fr;
  }

  .location-action-btns {
    grid-template-columns: 1fr;
  }

  .search-location-bar {
    flex-direction: column;
    width: 100%;
    gap: 8px;
  }

  .search-input-wrap {
    width: 100%;
  }

  .search-input {
    min-width: 0;
    width: 100%;
  }

  .back-btn {
    width: 100%;
  }

  .gis-stats-bar {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px 10px;
    padding: 10px;
  }

  .stat-divider {
    display: none;
  }

  .legend-bar {
    flex-wrap: wrap;
    gap: 6px;
    padding: 8px 10px;
  }

  /* 手机端按钮组允许自动弹性收缩，防止溢出屏幕 */
  .control-btn-group {
    margin-left: 0;
    width: 100%;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
  }

  .control-action-btn {
    flex: 1 1 auto;
    min-width: 0;
    font-size: 11px;
    padding: 4px 6px;
    white-space: nowrap;
    text-align: center;
    justify-content: center;
  }

  /* 手机端悬浮筛选框转为居中弹框，防止溢出屏幕 */
  .filter-popover-panel {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 92vw;
    max-width: 380px;
    max-height: 82vh;
    box-shadow: 0 20px 50px rgba(15, 23, 42, 0.4);
    z-index: 2000;
  }

  /* 地图视口与列表充分利用手机全宽度 */
  .gis-body-grid {
    grid-template-columns: 1fr;
    height: auto;
    min-height: auto;
    width: 100%;
  }

  .map-wrapper, .amap-box {
    width: 100%;
    height: 380px;
    min-height: 380px;
    overflow: hidden;
  }

  .gis-side-panel {
    width: 100%;
    border-left: none;
    border-top: 2px solid #cbd5e1;
  }

  .panel-content {
    padding: 10px 8px;
    max-height: 520px;
  }

  .location-card-box {
    padding: 10px;
  }
}

/* 隐藏高德地图在移动端撑爆宽度的版权与Logo节点 */
:deep(.amap-logo), :deep(.amap-copyright) {
  display: none !important;
  opacity: 0 !important;
  pointer-events: none !important;
}

/* 移动端强行全屏锁死溢出，防双指放大与偏斜 */
.gis-map-view, .gis-container, .gis-main-container {
  max-width: 100vw !important;
  overflow-x: hidden !important;
  box-sizing: border-box !important;
}
</style>
