<template>
  <div class="tube-page-root">
    <AppHeader />
    <main class="tube-page-main container">
      <Breadcrumbs :items="breadcrumbItems" />
      
      <!-- 高级工作台头部 -->
      <header class="topbar premium-topbar">
        <div>
          <h2>现场管理工作台 (供给侧)</h2>
          <p class="sub">
            面向供给主体。提供 Tabs 标签化分类，支持查看缺口与供需明细、运输车次装配、物流发货批量登记及在途运输跟踪。数量当前统一以“米”为计量单位。
          </p>
        </div>
        <div class="topbar-actions">
          <button type="button" class="btn ghost btn-back" @click="goProjectPages">返回功能页</button>
        </div>
      </header>

      <p v-if="errorMessage" class="page-error">{{ errorMessage }}</p>

      <!-- 磨砂玻璃态数据微看板及上方独立控制行 (Quick Dashboard) -->
      <div v-if="selectedSupplyEntityId" class="quick-dashboard-section" style="margin-bottom: 16px;">
        <!-- 管理员专属：供给主体控制行 (位于卡片正上方) -->
        <div v-if="canSwitchSupplyEntity && (supplyEntityOptions.length > 0 || isCustomInputMode)" class="entity-control-bar" style="display: flex; align-items: center; justify-content: space-between; background: #f8fafc; border: 1px solid #e2e8f0; padding: 8px 16px; border-radius: 8px; margin-bottom: 10px;">
          <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
            <span style="font-size: 13px; font-weight: 700; color: #334155;">🏭 切换当前供给主体：</span>
            <template v-if="!isCustomInputMode">
              <select
                v-model="selectedSupplyEntityId"
                class="input"
                style="font-weight: bold; color: #4f46e5; border: 1px solid #c7d2fe; background: #ffffff; border-radius: 6px; padding: 4px 10px; font-size: 13.5px; cursor: pointer; min-width: 220px;"
                @change="handleSelectSupplyEntityChange($event.target.value)"
              >
                <option v-for="entity in allSupplyEntityOptions" :key="entity.entity_id" :value="entity.entity_id">
                  {{ entity.entity_name }} {{ entity.isCustom ? '（自定义）' : (entity.entity_id ? `(${entity.entity_id})` : '') }}
                </option>
                <option value="__ENTER_CUSTOM_MODE__">✍️ 手动输入自定义供给方...</option>
              </select>
            </template>

            <template v-else>
              <input
                v-model="customEntityInput"
                type="text"
                class="input"
                placeholder="请输入临时/自定义供给主体名称"
                style="font-weight: bold; color: #4f46e5; border: 1px solid #818cf8; background: #ffffff; border-radius: 6px; padding: 4px 10px; font-size: 13.5px; min-width: 240px;"
                @keyup.enter="applyCustomEntityInput"
              />
              <button
                type="button"
                class="btn btn-primary btn-sm"
                style="font-size: 12.5px; padding: 4px 12px; background: #4f46e5; color: #ffffff; border: none; border-radius: 6px; cursor: pointer;"
                @click="applyCustomEntityInput"
              >
                确定应用
              </button>
              <button
                type="button"
                class="btn btn-secondary btn-sm"
                style="font-size: 12.5px; padding: 4px 10px; background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 6px; cursor: pointer;"
                @click="cancelCustomMode"
              >
                取消
              </button>
            </template>
          </div>
          <span style="font-size: 12px; color: #64748b;">(全局管理员特权：可选择预设主体或直接手动录入临时供给主体)</span>
        </div>

        <section class="card elevated quick-dashboard-card">
          <div class="meta-dashboard">
            <div class="meta-card">
              <span class="meta-label">当前供给主体</span>
              <strong class="meta-value">{{ currentSupplyEntityLabel }}</strong>
            </div>
            <div class="meta-card">
              <span class="meta-label">展示/业务日期</span>
              <strong class="meta-value">{{ showDate || '—' }}</strong>
            </div>
          <div class="meta-card highlight">
            <span class="meta-label">计划起始日期</span>
            <strong class="meta-value">{{ planStartDate || '—' }}</strong>
          </div>
          <div class="meta-card highlight">
            <span class="meta-label">发货记录总数 (保温管+管件)</span>
            <strong class="meta-value">{{ deliveryRows.length }}+{{ fittingDeliveries.length }} 笔</strong>
          </div>
        </div>
      </section>
    </div>

      <!-- 一体化双层复合导航区 (Unified Compound Navigation Group) -->
      <div class="nav-composite-group" v-if="selectedSupplyEntityId">
        <!-- 一级物料大类分段切换栏 (Segmented Category Bar) -->
        <div class="category-segment-wrapper">
          <div class="category-segment-bar">
            <button 
              type="button" 
              class="category-segment-btn" 
              :class="{ active: activeCategory === 'pipe' }" 
              @click="handleCategoryClick('pipe')"
            >
              <span class="cat-icon">🔹</span>
              <span class="cat-label">保温管业务</span>
              <span class="cat-count">3 项功能</span>
            </button>
            <button 
              type="button" 
              class="category-segment-btn" 
              :class="{ active: activeCategory === 'fitting' }" 
              @click="handleCategoryClick('fitting')"
            >
              <span class="cat-icon">🔩</span>
              <span class="cat-label">管件业务</span>
              <span class="cat-count">2 项功能</span>
            </button>
          </div>
        </div>

        <!-- 二级选项卡导航 (Responsive Sub-Tabs Header) -->
        <div class="tube-tabs-header-wrap">
          <!-- 保温管二级子标签 -->
          <div class="tube-tabs-header" v-if="activeCategory === 'pipe'">
            <button 
              type="button" 
              :class="{ active: activeTab === 'demand' }" 
              @click="handleTabClick('demand')"
            >
              🎯 需求与缺口看板
            </button>
            <button 
              type="button" 
              :class="{ active: activeTab === 'register' }" 
              @click="handleTabClick('register')"
            >
              🚚 批量发货与车次装配
            </button>
            <button 
              type="button" 
              :class="{ active: activeTab === 'history' }" 
              @click="handleTabClick('history')"
            >
              📋 物流发货记录
            </button>
          </div>

          <!-- 管件二级子标签 -->
          <div class="tube-tabs-header" v-else-if="activeCategory === 'fitting'">
            <button 
              type="button" 
              :class="{ active: activeTab === 'fitting' }" 
              @click="handleTabClick('fitting')"
            >
              🔧 管件发货与明细记录
            </button>
            <button 
              type="button" 
              :class="{ active: activeTab === 'fitting_baseline' }" 
              @click="handleTabClick('fitting_baseline')"
            >
              📋 设计量与计划采购量
            </button>
          </div>
        </div>
      </div>

      <!-- Tab内容区域 -->
      <div class="tube-tab-content-wrap" v-if="selectedSupplyEntityId">
        
        <!-- Tab 1: 需求与缺口看板 -->
        <div v-if="activeTab === 'demand'" class="tab-pane">
          <section class="card elevated tab-card">
            <div class="panel-title-row">
              <div>
                <h2>保温管供需明细</h2>
                <span class="panel-hint">{{ supplyDemandTableHint }}</span>
              </div>
              <div class="toolbar-actions">
                <p v-if="actionMessage" :class="['action-message', actionMessage.type]">{{ actionMessage.text }}</p>
                <button type="button" class="btn ghost" :disabled="summaryLoading" @click="loadDemandSummary">刷新明细</button>
              </div>
            </div>

            <div v-if="optionsError" class="error-box">{{ optionsError }}</div>

            <div class="supply-demand-toolbar">
              <label class="field field-compact">
                <span>当前供给主体</span>
                <input :value="currentSupplyEntityLabel" type="text" disabled />
              </label>

              <label class="field field-compact">
                <span>展示日期</span>
                <input :value="showDate" type="date" disabled />
              </label>

              <label class="field field-compact">
                <span>计划起始日期</span>
                <input :value="planStartDate" type="date" disabled />
              </label>

              <label class="field field-compact">
                <span>视图模式</span>
                <select v-model="supplyDemandViewMode" :disabled="summaryLoading || optionsLoading">
                  <option v-for="option in supplyDemandViewOptions" :key="option.value" :value="option.value">
                    {{ option.label }}
                  </option>
                </select>
              </label>

              <div class="field field-compact">
                <span>型号筛选</span>
                <details class="multi-select-dropdown">
                  <summary class="multi-select-summary">{{ selectedPipeModelSummaryLabel }}</summary>
                  <div class="multi-select-panel">
                    <div class="multi-select-actions">
                      <button type="button" class="btn ghost btn-xs" @click.prevent="selectAllPipeModels">全部型号</button>
                      <button type="button" class="btn ghost btn-xs" @click.prevent="clearPipeModelSelection">清空勾选</button>
                    </div>
                    <label v-for="pipe in pipeModelOptions" :key="pipe.pipe_model_id" class="checkbox-option">
                      <input v-model="selectedPipeModelIds" type="checkbox" :value="pipe.pipe_model_id" />
                      <span>{{ pipe.pipe_model_name }}</span>
                    </label>
                  </div>
                </details>
              </div>
            </div>

            <div v-if="summaryLoading" class="loading-text">正在加载需求汇总...</div>
            <div v-else-if="summaryError" class="error-box">{{ summaryError }}</div>
            <div v-else-if="!supplyDemandTableRows.length" class="empty-box">当前没有可展示的供需明细数据。</div>
            <div v-else class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>{{ supplyDemandViewMode === 'summary' ? '统计范围' : modeLabels.section_1 }}</th>
                    <th>型号</th>
                    <th>设计总量（米）</th>
                    <th>计划采购总量（米）</th>
                    <th>未来三日计划（米）</th>
                    <th>已发货待到货（米）</th>
                    <th>已到货待接收（米）</th>
                    <th>待库管确认（米）</th>
                    <th>三日净缺口（米）</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in supplyDemandTableRows" :key="row.rowKey">
                    <td class="cell-text" :title="row.scopeLabel">{{ row.scopeLabel }}</td>
                    <td class="cell-text" :title="row.pipeModelName">{{ row.pipeModelName }}</td>
                    <td class="cell-number">{{ formatNumber(row.designQty) }}</td>
                    <td class="cell-number">{{ formatNumber(row.purchasePlanQty) }}</td>
                    <td class="cell-number">{{ formatNumber(row.futurePlanQty) }}</td>
                    <td class="cell-number">{{ formatNumber(row.pendingArrivalQty) }}</td>
                    <td class="cell-number">{{ formatNumber(row.pendingReceiveQty) }}</td>
                    <td class="cell-number">{{ formatNumber(row.pendingWarehouseQty) }}</td>
                    <td class="cell-number" :class="{ 'danger-text': row.netGapQty > 0 }">{{ formatNumber(row.netGapQty) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <!-- Tab 2: 批量发货与车次装配 (左右分栏高端布局) -->
        <div v-if="activeTab === 'register'" class="tab-pane">
          <div class="workbench-split-layout">
            <!-- 左栏：车次装填登记表单 -->
            <section class="card elevated split-left-card">
              <div class="panel-title-row">
                <div>
                  <h2>发货车次信息登记</h2>
                  <span class="panel-hint">订单号与运输车次号由系统生成；您可以累积多条保温管明细装配在同一车次中提交。</span>
                </div>
              </div>

              <div class="form-vertical-grid">
                <label class="field">
                  <span>供给主体</span>
                  <input
                    v-if="!canSwitchSupplyEntity"
                    :value="currentDeliverySupplyEntityLabel"
                    type="text"
                    disabled
                  />
                  <!-- 绑定显式单向同步事件，打破 watcher 闭环死锁 -->
                  <select v-else v-model="deliveryForm.supplyEntityId" @change="handleSupplyEntityChange($event.target.value)" :disabled="!selectedSupplyEntityId || !canSwitchSupplyEntity">
                    <option v-for="entity in allSupplyEntityOptions" :key="entity.entity_id" :value="entity.entity_id">
                      {{ entity.entity_name }} {{ entity.isCustom ? '（自定义）' : '' }}
                    </option>
                  </select>
                </label>

                <div class="form-row-2col">
                  <label class="field">
                    <span>装车需求主体</span>
                    <select v-model="deliveryForm.section1Id">
                      <option value="" disabled>请选择需求主体</option>
                      <option v-for="section1 in currentAssignedSection1Options" :key="section1.section_1_id" :value="section1.section_1_id">
                        {{ section1.section_1_name }}
                      </option>
                    </select>
                  </label>

                  <label class="field">
                    <span>保温管型号</span>
                    <select v-model="deliveryForm.pipeModelId">
                      <option value="" disabled>{{ deliveryFormPipeModelOptions.length ? '请选择型号' : '所辖水质标段暂无采购需求型号' }}</option>
                      <option v-for="pipe in deliveryFormPipeModelOptions" :key="pipe.pipe_model_id" :value="pipe.pipe_model_id">
                        {{ pipe.pipe_model_name }}
                      </option>
                    </select>
                  </label>
                </div>

                <div class="form-row-2col">
                  <label class="field">
                    <span>发货量（米）</span>
                    <input v-model.number="deliveryForm.shippedQty" type="number" min="0" step="1" />
                  </label>

                  <label class="field">
                    <span>发货时间</span>
                    <input 
                      v-if="['Global_admin', 'tube_supplier_admin'].includes(currentGroup)" 
                      v-model="deliveryForm.customShippedAt" 
                      type="datetime-local" 
                      class="input"
                    />
                    <input 
                      v-else 
                      value="提交当前车次时自动取当前时间" 
                      type="text" 
                      disabled 
                    />
                  </label>
                </div>

                <div class="form-row-2col">
                  <label class="field">
                    <span>联系人</span>
                    <input v-model.trim="deliveryForm.shipContactName" type="text" maxlength="50" placeholder="发货联系人" />
                  </label>

                  <label class="field">
                    <span>联系电话</span>
                    <input v-model.trim="deliveryForm.shipContactPhone" type="text" maxlength="30" placeholder="联系电话" />
                  </label>
                </div>

                <div class="form-row-2col">
                  <label class="field">
                    <span>车牌号（选填）</span>
                    <input
                      v-model.trim="deliveryForm.vehiclePlateNo"
                      type="text"
                      maxlength="32"
                      placeholder="同一车次只需填写一次"
                      :disabled="currentReusedShipmentPlateLocked"
                    />
                  </label>

                  <label class="field">
                    <span>运输车次号状态</span>
                    <input :value="currentShipmentDisplay" type="text" class="shipment-status-input" disabled />
                  </label>
                </div>

                <label class="field">
                  <span>备注</span>
                  <input v-model.trim="deliveryForm.shipRemark" type="text" maxlength="120" placeholder="发货备注" />
                </label>

                <div class="field">
                  <span>车次说明</span>
                  <span class="muted-text text-hint-highlight">
                    {{
                      deliveryForm.reuseCurrentShipment && deliveryForm.shipmentNo
                        ? currentReusedShipmentPlateLocked
                          ? `当前将继续装配运输车次号 ${deliveryForm.shipmentNo}，并沿用车牌号 ${deliveryForm.vehiclePlateNo}。`
                          : `当前将继续装配运输车次号 ${deliveryForm.shipmentNo}。若该车次尚未登记车牌号，可在本次一起补录。`
                        : '当前将自动新建运输车次号；同一车次下可累积不同' + modeLabels.section_1 + '/型号明细一并出发。'
                    }}
                  </span>
                </div>

                <div class="form-submit-row">
                  <button
                    type="button"
                    class="btn ghost btn-large"
                    :disabled="submitDeliveryLoading || !canSubmitCurrentProject || !selectedSupplyEntityId"
                    @click="appendDraftDelivery"
                  >
                    ➕ 加入当前发货车次
                  </button>
                </div>
              </div>
            </section>

            <!-- 右栏：待提交车次明细暂存积木 -->
            <section class="card elevated split-right-card">
              <div class="panel-title-row">
                <div>
                  <h2>待提交车次明细</h2>
                  <span class="panel-hint">当前车次下已暂存 <b>{{ draftDeliveryItems.length }}</b> 条明细，点击“一键提交当前车次”物理发车。</span>
                </div>
                <button
                  type="button"
                  class="primary-button btn-large shadow-accent"
                  :disabled="submitDeliveryLoading || !canSubmitCurrentProject || !selectedSupplyEntityId || !draftDeliveryItems.length || isReadOnlyViewer"
                  :style="isReadOnlyViewer ? { opacity: 0.5, pointerEvents: 'none !important', cursor: 'not-allowed', background: '#94a3b8 !important', borderColor: '#94a3b8 !important', color: '#ffffff !important' } : {}"
                  :title="isReadOnlyViewer ? '全局观察员角色仅具备只读权限，已被禁止提交发货' : '点击物理发车提交当前车次'"
                  @click="submitDeliveryBatch"
                >
                  {{ isReadOnlyViewer ? '🔒 观察员模式禁止提交发货' : (submitDeliveryLoading ? '🚀 提交当前车次中...' : '🚀 一键提交当前发货车次') }}
                </button>
              </div>

              <p v-if="actionMessage" :class="['action-message', actionMessage.type]">{{ actionMessage.text }}</p>

              <div class="batch-box-premium">
                <div v-if="!draftDeliveryItems.length" class="empty-box-split">
                  <div class="empty-icon-bubble">📦</div>
                  <strong class="empty-title">当前发车车厢为空</strong>
                  <span class="empty-subtitle">请从左侧选择{{ modeLabels.section_1 }}、型号、发货米数，并点击“加入当前发货车次”进行装载。</span>
                </div>
                <div v-else class="draft-items-card-list">
                  <div 
                    v-for="(item, index) in draftDeliveryItems" 
                    :key="`${item.section1Id}-${item.pipeModelId}-${index}`" 
                    class="draft-item-card"
                  >
                    <div class="draft-card-header">
                      <span class="section1-tag">📍 {{ item.section1Name }}</span>
                      <button type="button" class="btn-remove-draft" @click="removeDraftDelivery(index)" title="移除此条">✕</button>
                    </div>
                    <div class="draft-card-body">
                      <div class="info-row">
                        <span class="lbl">管材型号</span>
                        <strong class="val">{{ item.pipeModelName }}</strong>
                      </div>
                      <div class="info-row">
                        <span class="lbl">发货米数</span>
                        <strong class="val highlight-qty">{{ formatNumber(item.shippedQty) }} 米</strong>
                      </div>
                      <div class="info-row" v-if="item.shipRemark">
                        <span class="lbl">明细备注</span>
                        <span class="val remark-val">{{ item.shipRemark }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>

        <!-- Tab 3: 物流发货记录 -->
        <div v-if="activeTab === 'history'" class="tab-pane">
          <section class="card elevated tab-card">
            <div class="panel-title-row">
              <div>
                <h2>已发货物流跟踪记录</h2>
                <span class="panel-hint">仅“已发货待到货”状态允许撤销。可在表格中点击“继续该车次”为过往车辆追加追加管材发货。</span>
              </div>
              <div style="display: flex; gap: 8px;">
                <button type="button" class="btn ghost" :disabled="deliveriesLoading" @click="loadDeliveries">刷新发货台账</button>
                <button v-if="deliveryRows.length > 0" type="button" class="btn primary" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important; color: #fff !important; border: none !important; font-weight: 600;" @click="showExportModal = true">📥 导出 Excel</button>
              </div>
            </div>

            <div v-if="deliveriesLoading && !deliveryRows.length" class="loading-text">正在加载发货记录...</div>
            <div v-else-if="deliveriesError && !deliveryRows.length" class="error-box">{{ deliveriesError }}</div>
            <div v-else-if="!deliveryRows.length" class="empty-box">当前没有发货记录。</div>
            <div v-else class="table-wrap">
              <table class="data-table delivery-record-table">
                <colgroup>
                  <col class="col-order" />
                  <col class="col-shipment" />
                  <col class="col-plate" />
                  <col class="col-supply" />
                  <col class="col-section1" />
                  <col class="col-model" />
                  <col class="col-qty" />
                  <col class="col-qty" />
                  <col class="col-qty" />
                  <col class="col-time" />
                  <col class="col-elapsed" />
                  <col class="col-status" />
                  <col class="col-remark" />
                  <col class="col-actions" />
                </colgroup>
                <thead>
                  <tr>
                    <th>订单号</th>
                    <th>运输车次号</th>
                    <th>车牌号</th>
                    <th>供给主体</th>
                    <th>{{ modeLabels.section_1 }}</th>
                    <th>型号</th>
                    <th>发货量（米）</th>
                    <th>到货量（米）</th>
                    <th>接收量（米）</th>
                    <th>发货时间</th>
                    <th>在途时长</th>
                    <th>状态</th>
                    <th>备注</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in deliveryRows" :key="row.deliveryId">
                    <td class="cell-nowrap cell-code">{{ row.deliveryCode }}</td>
                    <td class="cell-nowrap cell-code">{{ row.shipmentNo || '—' }}</td>
                    <td class="cell-nowrap cell-text" :title="row.vehiclePlateNo || '—'">{{ row.vehiclePlateNo || '—' }}</td>
                    <td class="cell-text" :title="row.supplyEntityName">{{ row.supplyEntityName }}</td>
                    <td class="cell-text" :title="row.section1Name">{{ row.section1Name }}</td>
                    <td class="cell-text" :title="row.pipeModelName">{{ row.pipeModelName }}</td>
                    <td class="cell-number">{{ formatNumber(row.shippedQty) }}</td>
                    <td class="cell-number">{{ formatNullableNumber(row.arrivedQty) }}</td>
                    <td class="cell-number">{{ formatNullableNumber(row.receivedQty) }}</td>
                    <td class="cell-nowrap cell-datetime">{{ row.shippedAtDisplay || '—' }}</td>
                    <td class="cell-nowrap cell-elapsed">{{ formatDeliveryElapsedDisplay(row) }}</td>
                    <td>
                      <!-- 供给侧物流状态点击，唤起订单全生命周期时光轴 -->
                      <div class="status-chip-group" @click="openTimelineModal(row)" style="cursor: pointer;" title="点击查看订单全生命周期流转凭证">
                        <span :class="['status-chip', `status-${row.status}`]" style="cursor: pointer;">{{ row.statusLabel }}</span>
                        <span v-if="row.abnormalFlag" class="status-chip status-abnormal" style="cursor: pointer;">{{ getAbnormalLabel(row) }}</span>
                      </div>
                    </td>
                    <td class="cell-text cell-remark" :title="row.shipRemark || row.cancelReason || '—'">{{ row.shipRemark || row.cancelReason || '—' }}</td>
                    <td>
                      <div class="action-stack">
                        <button
                          v-if="['Global_admin', 'tube_supplier_admin'].includes(currentGroup)"
                          type="button"
                          class="btn primary"
                          style="background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important; color: #fff !important; border: none !important;"
                          @click="openSuperEdit(row)"
                        >
                          ⚙️ 编辑覆盖
                        </button>
                        <button
                          v-if="row.shipmentNo"
                          type="button"
                          :class="['btn', isReusingShipment(row) ? 'active-ghost' : 'ghost']"
                          @click="toggleShipmentReuse(row)"
                        >
                          {{ isReusingShipment(row) ? '取消继续车次' : '继续该车次' }}
                        </button>
                        <button
                          v-if="row.status === 'pending_arrival' && ['Global_admin', 'tube_supplier_admin', 'tube_supplier', 'dev_admin'].includes(currentGroup)"
                          type="button"
                          class="btn danger-ghost"
                          :disabled="cancelLoadingIds[row.deliveryId]"
                          @click="cancelDelivery(row)"
                        >
                          {{ cancelLoadingIds[row.deliveryId] ? '撤销中...' : '撤销发货' }}
                        </button>
                        <span v-else-if="row.status === 'cancelled'" class="muted-text" style="color: #ef4444;">已撤销</span>
                        <span v-else-if="row.status !== 'pending_arrival'" class="muted-text" title="现场已签收/入库，不允许单方面撤销">不可撤销</span>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <!-- Tab 4: 管件发货记录 -->
        <div v-if="activeTab === 'fitting'" class="tab-pane">
          <section class="card elevated tab-card">
            <div class="panel-title-row">
              <div>
                <h2>🔧 管件整车发货填报</h2>
                <span class="panel-hint">以每一车辆为一个发货批次，自由录入多行管件发货明细。系统将自动生成管件车次号及管件订单号。</span>
              </div>
              <div class="toolbar-actions" style="display: flex; gap: 8px;">
                <button type="button" class="btn ghost" @click="downloadFittingTemplate" style="background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; font-weight: 600;">📥 下载标准填报模板 (.xlsx)</button>
                <button 
                  type="button" 
                  class="btn primary" 
                  :disabled="submitFittingLoading || isReadOnlyViewer || !canSubmitCurrentProject"
                  :style="isReadOnlyViewer ? { opacity: 0.5, pointerEvents: 'none !important', cursor: 'not-allowed', background: '#94a3b8 !important', borderColor: '#94a3b8 !important', color: '#ffffff !important' } : {}"
                  :title="isReadOnlyViewer ? '全局观察员角色仅具备只读权限，已被禁止提交发货' : '点击提交整车管件发货单'"
                  @click="submitFittingForm"
                >
                  {{ isReadOnlyViewer ? '🔒 观察员模式禁止提交发货' : '🚀 提交整车管件发货单' }}
                </button>
              </div>
            </div>

            <div v-if="fittingActionMsg" :class="['action-message', fittingActionMsg.type]" style="margin-bottom: 12px;">{{ fittingActionMsg.text }}</div>

            <!-- 表头信息区（全横向紧凑网格，备注不再另起一行） -->
            <div class="form-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; background: #f8fafc; padding: 12px 16px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 14px; align-items: end;">
              <label class="field">
                <span style="font-weight: bold; color: #1e293b; font-size: 13px;">运输车牌号 <span style="color: #ef4444;">*</span></span>
                <input v-model.trim="fittingForm.vehiclePlateNo" type="text" placeholder="例如: 鲁B-88888" class="input" style="padding: 6px 10px; font-size: 13px;" />
              </label>

              <label class="field">
                <span style="font-weight: bold; color: #1e293b; font-size: 13px;">接收标段 <span style="color: #ef4444;">*</span></span>
                <select v-model="fittingForm.section1Id" class="input" style="padding: 6px 10px; font-size: 13px;">
                  <option value="">-- 请选择接收标段 --</option>
                  <option v-for="st in currentAssignedSection1Options" :key="st.section_1_id" :value="st.section_1_id">
                    {{ st.section_1_name }}
                  </option>
                </select>
              </label>

              <label class="field">
                <span style="font-size: 13px;">发货主体</span>
                <input :value="currentSupplyEntityLabel" type="text" disabled class="input" style="background: #f1f5f9; color: #64748b; padding: 6px 10px; font-size: 13px;" />
              </label>

              <label class="field">
                <span style="font-size: 13px;">发货经办人</span>
                <input v-model.trim="fittingForm.shipContactName" type="text" placeholder="选填" class="input" style="padding: 6px 10px; font-size: 13px;" />
              </label>

              <label class="field">
                <span style="font-size: 13px;">联系电话</span>
                <input v-model.trim="fittingForm.shipContactPhone" type="text" placeholder="选填" class="input" style="padding: 6px 10px; font-size: 13px;" />
              </label>

              <label class="field col-remark-field">
                <span style="font-size: 13px;">整车发货备注</span>
                <input v-model.trim="fittingForm.shipRemark" type="text" placeholder="选填" class="input" style="padding: 6px 10px; font-size: 13px;" />
              </label>
            </div>

            <!-- 明细填报 RevoGrid 电子表格 -->
            <div class="panel-sub-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 6px;">
              <h3 style="margin: 0; font-size: 14px; color: #334155; display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                📊 本车管件发货电子表格
                <span class="mobile-hide-hint" style="font-size: 12px; font-weight: normal; color: #64748b;">(双击单元格输入，直接按方向键切换，或在网格区域按下 Ctrl+V 快捷粘贴 Excel 矩阵)</span>
              </h3>
              <div style="display: flex; gap: 8px;">
                <button type="button" class="btn ghost btn-sm" @click="addFittingGridRows(5)">+ 追加 5 行空行</button>
                <button type="button" class="btn ghost btn-sm" style="color: #ef4444;" @click="clearFittingGrid">清空电子表格</button>
              </div>
            </div>

            <div class="table-wrap card" style="min-height: 280px; border: 1px solid #cbd5e1; border-radius: 6px; overflow: hidden; background: #fff;">
              <RevoGrid
                ref="fittingGridRef"
                :row-headers="true"
                :hide-attribution="true"
                :stretch="true"
                :row-size="32"
                :resize="true"
                :range="true"
                :can-focus="true"
                :apply-on-close="true"
                :columns="fittingGridColumns"
                :source="fittingGridSource"
                style="height: 320px; width: 100%;"
                @afteredit="handleFittingGridAfterEdit"
                @afterEdit="handleFittingGridAfterEdit"
              />
            </div>

            <!-- 可选标准管件下拉匹配提示词 -->
            <datalist id="fitting-type-list">
              <option v-for="t in standardFittingTypes" :key="t" :value="t" />
            </datalist>
          </section>

          <!-- 下半部分：历史管件发货记录 -->
          <section class="card elevated tab-card" style="margin-top: 20px;">
            <div class="panel-title-row">
              <div>
                <h2>📋 已提交管件发货记录台账</h2>
                <span class="panel-hint">显示已录入系统的管件发货明细，按发货时间倒序排列。</span>
              </div>
              <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                <button
                  type="button"
                  class="btn ghost btn-sm"
                  style="font-size: 12px; height: 32px; padding: 0 10px; border-color: #cbd5e1; background: #fff;"
                  @click="toggleAllFittingGroups(true)"
                >
                  📖 展开全部车次
                </button>
                <button
                  type="button"
                  class="btn ghost btn-sm"
                  style="font-size: 12px; height: 32px; padding: 0 10px; border-color: #cbd5e1; background: #fff;"
                  @click="toggleAllFittingGroups(false)"
                >
                  📕 折叠全部车次
                </button>
                <select v-model="fittingTableSectionFilter" class="input" style="min-width: 140px; font-size: 13px;" @change.prevent.stop="loadFittingDeliveries">
                  <option value="">全部接收标段</option>
                  <option v-for="st in currentAssignedSection1Options" :key="st.section_1_id" :value="st.section_1_id">
                    {{ st.section_1_name }}
                  </option>
                </select>
                <input v-model.trim="fittingSearchKw" type="text" placeholder="搜索车牌号/单号/管件类型..." class="input" style="min-width: 160px; flex: 1;" @keyup.enter="loadFittingDeliveries" />
                <button type="button" class="btn ghost" :disabled="fittingLoading" @click="loadFittingDeliveries">刷新列表</button>
                <button v-if="fittingDeliveries.length > 0" type="button" class="btn primary" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important; color: #fff !important; border: none !important; font-weight: 600;" @click="downloadFittingHistoryExcel">📥 导出台账 (.xlsx)</button>
              </div>
            </div>

            <div class="table-wrap" style="position: relative; min-height: 140px;">
              <!-- 局部平滑加载中遮罩 (不销毁 DOM) -->
              <div v-if="fittingLoading" class="loading-overlay" style="position: absolute; inset: 0; background: rgba(255,255,255,0.7); backdrop-filter: blur(2px); z-index: 10; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 600; color: #4f46e5;">
                ⚡ 正在更新台账数据...
              </div>

              <div v-if="!groupedFittingDeliveries.length && !fittingLoading" style="text-align: center; padding: 50px 0; color: #94a3b8; font-size: 13px;">
                暂无符合条件的管件发货记录。
              </div>

              <!-- 按发货车次折叠卡片列表 -->
              <div v-else style="display: flex; flex-direction: column; gap: 12px; margin-top: 10px;">
                <div 
                  v-for="group in groupedFittingDeliveries" 
                  :key="group.groupKey"
                  style="border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.02); transition: all 0.2s ease;"
                >
                  <!-- 车次汇总卡片表头 (支持点击展开/折叠) -->
                  <div 
                    class="fitting-card-header"
                    style="display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background: #f8fafc; cursor: pointer; user-select: none; border-bottom: 1px solid #e2e8f0;"
                    @click="toggleFittingGroup(group.groupKey)"
                  >
                    <div class="header-left-meta" style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                      <span style="font-size: 14px; color: #4f46e5; transition: transform 0.2s ease; font-weight: bold;" :style="{ transform: isFittingGroupExpanded(group.groupKey) ? 'rotate(90deg)' : 'rotate(0deg)' }">
                        ▶
                      </span>
                      <div style="display: flex; align-items: center; gap: 6px;">
                        <span style="font-size: 11px; color: #64748b; font-weight: 600;">车次:</span>
                        <strong style="color: #4f46e5; font-family: monospace; font-size: 14px;">{{ group.shipmentNo }}</strong>
                      </div>
                      <span class="plate-badge" style="margin-left: 2px; flex-shrink: 0;">{{ group.vehiclePlateNo }}</span>
                      <div style="font-size: 12.5px; color: #334155; display: flex; align-items: center; gap: 4px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" :title="`发往标段: ${group.section1Name}`">
                        <span style="color: #94a3b8; flex-shrink: 0;">➡️ 发往:</span>
                        <strong style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ group.section1Name }}</strong>
                      </div>
                      <span style="font-size: 11.5px; color: #64748b; font-family: monospace; flex-shrink: 0;">{{ formatDateTimeDisplay(group.shippedAt) }}</span>
                    </div>

                    <div class="header-right-meta" style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                      <div style="text-align: right;">
                        <span style="font-size: 12px; color: #64748b; margin-right: 6px;">共 {{ group.items.length }} 种管件</span>
                        <strong style="font-size: 13.5px; color: #059669;">发货总计: {{ group.totalQty }} {{ getGroupUnitLabel(group) }}</strong>
                      </div>
                      <!-- 状态 Badge -->
                      <span v-if="group.status === 'shipped' || group.status === 'pending_arrival' || !group.status" class="tag-badge primary" style="background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; font-size: 11.5px;">🚚 待到货确认</span>
                      <span v-else-if="group.status === 'arrived' || group.status === 'pending_receive'" class="tag-badge success" style="background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; font-size: 11.5px;">✅ 待施工接收</span>
                      <span v-else-if="group.status === 'construction_confirmed' || group.status === 'pending_warehouse' || group.status === 'received'" class="tag-badge warning" style="background: #f3e8ff; color: #6b21a8; border: 1px solid #d8b4fe; font-size: 11.5px;">👷 待库管确认</span>
                      <span v-else-if="group.status === 'warehouse_confirmed' || group.status === 'completed'" class="tag-badge success" style="background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; font-size: 11.5px;">🏢 库管已确认</span>
                      <span v-else-if="group.status === 'cancelled'" class="tag-badge" style="background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; font-size: 11.5px;">❌ 已撤销</span>
                      <span v-if="group.hasCancelled && group.status !== 'cancelled'" class="tag-badge" style="background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; font-size: 11.5px;">⚠️ 含已撤销明细</span>

                      <button
                        v-if="['Global_admin', 'tube_supplier_admin'].includes(currentGroup) && group.items && group.items.length > 0"
                        type="button"
                        class="btn primary btn-sm"
                        style="padding: 4px 10px; font-size: 12px; background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important; color: #fff !important; border: none !important; cursor: pointer; flex-shrink: 0;"
                        @click.stop="openSuperEditFitting(group.items[0], group)"
                        :title="group.items.length > 1 ? '编辑覆盖本车次首条明细（多明细可展开逐行编辑）' : '编辑覆盖此条发货记录'"
                      >
                        ⚙️ 编辑覆盖
                      </button>

                      <button
                        v-if="(group.status === 'shipped' || group.status === 'pending_arrival') && ['Global_admin', 'tube_supplier_admin', 'tube_supplier', 'dev_admin'].includes(currentGroup)"
                        type="button"
                        class="btn ghost btn-sm"
                        style="padding: 4px 10px; font-size: 12px; color: #b91c1c; border-color: #fecaca; background: #fef2f2; cursor: pointer; flex-shrink: 0;"
                        @click.stop="handleCancelFittingGroup(group)"
                      >
                        撤销发货
                      </button>

                      <button 
                        type="button" 
                        class="btn ghost btn-sm" 
                        style="padding: 4px 10px; font-size: 12px; color: #4f46e5; border-color: #c7d2fe; background: #eef2ff; cursor: pointer; flex-shrink: 0;"
                        @click.stop="showDeliveryDetail(group)"
                      >
                        📜 流转凭证
                      </button>
                    </div>
                  </div>

                  <!-- 明细展开区 -->
                  <div v-show="isFittingGroupExpanded(group.groupKey)" style="padding: 12px 16px; background: #ffffff;">
                    <div v-if="group.shipRemark" style="font-size: 12px; color: #475569; background: #f1f5f9; padding: 6px 12px; border-radius: 6px; margin-bottom: 10px; display: flex; align-items: center; gap: 6px;">
                      <span>📝 整车备注：</span>
                      <span style="color: #0f172a;">{{ group.shipRemark }}</span>
                    </div>

                    <div class="table-responsive-wrapper" style="overflow-x: auto; width: 100%; -webkit-overflow-scrolling: touch; margin-bottom: 4px;">
                      <table class="data-table demand-fitting-table" style="margin: 0; min-width: 720px; width: 100%; table-layout: fixed; border: 1px solid #edf2f7; border-radius: 6px; font-size: 12.5px;">
                        <thead style="background: #f8fafc;">
                          <tr>
                            <th style="width: 38px; text-align: center;">#</th>
                            <th style="width: 105px;">管件类型</th>
                            <th style="min-width: 170px;">型号 / 规格描述</th>
                            <th style="width: 90px; text-align: right;">发货件数</th>
                            <th style="width: 135px;">订单号</th>
                            <th style="width: 120px; text-align: center;">状态 / 备注</th>
                            <th v-if="['Global_admin', 'tube_supplier_admin', 'tube_supplier', 'dev_admin'].includes(currentGroup)" style="width: 140px; text-align: center;">操作</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr 
                            v-for="(item, idx) in group.items" 
                            :key="item.id"
                            :class="['mobile-fitting-item-row', { 'is-cancelled-row': item.status === 'cancelled' }]"
                            :style="item.status === 'cancelled' ? { background: '#fef2f2', opacity: '0.85' } : {}"
                          >
                            <td class="col-index" style="text-align: center; color: #94a3b8;">{{ idx + 1 }}</td>
                            <td class="col-type">
                              <span v-if="isStandardFittingType(item.fitting_type)" class="tag-badge primary" style="font-size: 11.5px;">{{ getNormalizedFittingType(item.fitting_type) }}</span>
                              <span v-else class="tag-badge warning" style="background: #fff7ed; color: #c2410c; border: 1px solid #ffedd5; font-size: 11.5px;">⚠️ {{ item.fitting_type }}</span>
                            </td>
                            <td class="col-model">
                              <strong :style="{ color: item.status === 'cancelled' ? '#94a3b8' : '#1e293b', textDecoration: item.status === 'cancelled' ? 'line-through' : 'none' }">
                                {{ item.model_spec }}
                              </strong>
                            </td>
                            <td class="col-shipped" style="text-align: right; font-weight: bold;" :style="{ color: item.status === 'cancelled' ? '#94a3b8' : '#2563eb', textDecoration: item.status === 'cancelled' ? 'line-through' : 'none' }">
                              <span class="mobile-lbl" style="display: none;">发货: </span>
                              <span>{{ item.shipped_qty }} {{ item.unit || '个' }}</span>
                            </td>
                            <td class="col-action">
                              <span class="mobile-order-lbl" style="display: none; font-size: 11px; color: #94a3b8; margin-right: 4px;">单号:</span>
                              <span style="font-family: monospace; font-size: 11.5px; color: #64748b;">{{ item.order_no }}</span>
                            </td>
                            <td class="col-status" style="text-align: center;">
                              <span v-if="item.status === 'cancelled'" class="tag-badge" style="background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; font-size: 11px;" :title="item.cancel_reason ? `撤销原因: ${item.cancel_reason}` : '已撤销'">
                                ❌ 已撤销
                              </span>
                              <span v-else-if="item.status === 'warehouse_confirmed' || item.status === 'completed'" class="tag-badge success" style="background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; font-size: 11px;">
                                🏢 库管已确认
                              </span>
                              <span v-else-if="item.status === 'construction_confirmed' || item.status === 'pending_warehouse' || item.status === 'received'" class="tag-badge warning" style="background: #f3e8ff; color: #6b21a8; border: 1px solid #d8b4fe; font-size: 11px;">
                                👷 待库管确认
                              </span>
                              <span v-else-if="item.status === 'arrived' || item.status === 'pending_receive'" class="tag-badge success" style="background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; font-size: 11px;">
                                ✅ 待施工接收
                              </span>
                              <span v-else class="tag-badge primary" style="background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; font-size: 11px;">
                                🚚 待到货
                              </span>
                              <div v-if="item.cancel_reason" class="mobile-cancel-reason" style="font-size: 10.5px; color: #b91c1c; margin-top: 2px; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" :title="'撤销原因: ' + item.cancel_reason">
                                理由: {{ item.cancel_reason }}
                              </div>
                            </td>
                            <td class="col-operate" v-if="['Global_admin', 'tube_supplier_admin', 'tube_supplier', 'dev_admin'].includes(currentGroup)" style="text-align: center;">
                              <div class="mobile-action-buttons" style="display: flex; gap: 4px; justify-content: center; align-items: center; flex-wrap: wrap;">
                                <button
                                  v-if="['Global_admin', 'tube_supplier_admin'].includes(currentGroup)"
                                  type="button"
                                  class="btn primary btn-sm"
                                  style="padding: 2px 6px; font-size: 11px; background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important; color: #fff !important; border: none !important; cursor: pointer; border-radius: 4px;"
                                  @click.stop="openSuperEditFitting(item, group)"
                                  title="编辑覆盖此项发货数据"
                                >
                                  ⚙️ 编辑
                                </button>
                                <button
                                  v-if="(item.status === 'shipped' || item.status === 'pending_arrival' || !item.status) && ['Global_admin', 'tube_supplier_admin', 'tube_supplier', 'dev_admin'].includes(currentGroup)"
                                  type="button"
                                  class="btn ghost btn-sm"
                                  style="padding: 2px 6px; font-size: 11px; color: #b91c1c; border-color: #fecaca; background: #fef2f2; cursor: pointer; border-radius: 4px;"
                                  @click.stop="handleCancelFittingItem(item, group)"
                                  title="局部撤销此项管件明细"
                                >
                                  撤销此项
                                </button>
                                <span v-else-if="item.status === 'cancelled'" style="font-size: 11px; color: #94a3b8;">—</span>
                                <span v-else style="font-size: 11px; color: #94a3b8;" title="现场已签收/入库，不可单方面撤销">不可撤销</span>
                              </div>
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>

        <!-- Tab 5: 管件基准设计量与计划采购量台账 -->
        <div v-if="activeTab === 'fitting_baseline'" class="tab-pane">
          <section class="card elevated tab-card">
            <div class="panel-title-row baseline-header-row">
              <div class="header-title-col">
                <h2>🔩 管件设计量与计划采购量台账</h2>
                <span class="panel-hint">展示各标段在基准数据库（tube.tube_fitting_baseline）中的全量标准化管件与物料基准明细。</span>
              </div>
              <div class="header-actions-col">
                <!-- 标段选择组件 (无全局 field 类干扰，纯净 Flex 对齐) -->
                <div class="section-select-group">
                  <span class="select-label">📍 查看标段:</span>
                  <select
                    v-model="selectedFittingBaselineSection1Id"
                    class="baseline-section-select"
                    @change="loadFittingBaseline"
                  >
                    <option v-for="st in currentAssignedSection1Options" :key="st.section_1_id" :value="st.section_1_id">
                      {{ st.section_1_name }}
                    </option>
                  </select>
                </div>
                <button
                  type="button"
                  class="baseline-action-btn"
                  @click="loadFittingBaseline"
                >
                  🔄 刷新数据
                </button>
                <button
                  type="button"
                  class="baseline-action-btn"
                  :disabled="!fittingBaselineRows.length"
                  @click="exportFittingBaseline"
                >
                  📥 导出 Excel
                </button>
              </div>
            </div>

            <!-- 数据统计微看板 -->
            <div class="summary-row baseline-summary" style="margin-top: 12px; margin-bottom: 12px;">
              <span class="summary-chip">📍 选定标段：<strong>{{ getSection1Name(selectedFittingBaselineSection1Id) }}</strong></span>
              <span class="summary-chip">
                🔍 命中种类：<strong>{{ filteredFittingBaselineRows.length }}</strong> / {{ fittingBaselineRows.length }} 种
              </span>
              <span class="summary-chip">
                📐 命中设计量：<strong>{{ formatNumber(fittingBaselineStats.filteredDesignQty) }}</strong>
                <small v-if="filteredFittingBaselineRows.length !== fittingBaselineRows.length" style="color: #64748b; font-weight: normal; margin-left: 4px;">(总: {{ formatNumber(fittingBaselineStats.totalDesignQty) }})</small>
              </span>
              <span class="summary-chip">
                📦 命中采购量：<strong>{{ formatNumber(fittingBaselineStats.filteredPurchaseQty) }}</strong>
                <small v-if="filteredFittingBaselineRows.length !== fittingBaselineRows.length" style="color: #64748b; font-weight: normal; margin-left: 4px;">(总: {{ formatNumber(fittingBaselineStats.totalPurchaseQty) }})</small>
              </span>
            </div>

            <!-- 🔩 多维多选下拉筛选工具栏 (Clean Multi-Select Dropdown Toolbar) -->
            <div class="fitting-filter-toolbar" @click.stop>
              <!-- 1. 系统类型下拉框 -->
              <div class="ms-dropdown-container" v-if="availableFittingFacets.systemTypes.length > 0">
                <button
                  type="button"
                  class="ms-dropdown-trigger"
                  :class="{ 'has-value': fittingFilters.systemTypes.length > 0, 'is-open': activeDropdown === 'systemTypes' }"
                  @click="toggleFittingDropdown('systemTypes', $event)"
                >
                  <span class="ms-label-icon">💧</span>
                  <span class="ms-label-text">{{ getFittingFilterSummary('systemTypes', '系统类型') }}</span>
                  <span v-if="fittingFilters.systemTypes.length > 1" class="ms-badge">{{ fittingFilters.systemTypes.length }}</span>
                  <span v-if="fittingFilters.systemTypes.length > 0" class="ms-clear-btn" title="清空" @click.stop="clearFittingFilterDimension('systemTypes')">✕</span>
                  <span class="ms-arrow">▾</span>
                </button>
                <div v-if="activeDropdown === 'systemTypes'" class="ms-dropdown-menu">
                  <div class="ms-menu-header">
                    <span class="ms-menu-title">选择系统类型</span>
                    <div class="ms-menu-actions">
                      <a href="javascript:void(0)" @click.stop="selectAllFittingFilterDimension('systemTypes', availableFittingFacets.systemTypes)">全选</a>
                      <span class="sep">|</span>
                      <a href="javascript:void(0)" @click.stop="clearFittingFilterDimension('systemTypes')">清空</a>
                    </div>
                  </div>
                  <div class="ms-menu-list">
                    <label
                      v-for="item in availableFittingFacets.systemTypes"
                      :key="item.value"
                      class="ms-menu-item"
                      :class="{ checked: isFittingFilterSelected('systemTypes', item.value) }"
                      @click.stop="toggleFittingFilterItem('systemTypes', item.value)"
                    >
                      <input
                        type="checkbox"
                        :checked="isFittingFilterSelected('systemTypes', item.value)"
                        @click.stop
                        @change="toggleFittingFilterItem('systemTypes', item.value)"
                      />
                      <span class="ms-item-name">{{ item.value }}</span>
                      <span class="ms-item-count">({{ item.count }})</span>
                    </label>
                  </div>
                </div>
              </div>

              <!-- 2. 物理类别下拉框 -->
              <div class="ms-dropdown-container" v-if="availableFittingFacets.categories.length > 0">
                <button
                  type="button"
                  class="ms-dropdown-trigger"
                  :class="{ 'has-value': fittingFilters.categories.length > 0, 'is-open': activeDropdown === 'categories' }"
                  @click="toggleFittingDropdown('categories', $event)"
                >
                  <span class="ms-label-icon">🔩</span>
                  <span class="ms-label-text">{{ getFittingFilterSummary('categories', '物理类别') }}</span>
                  <span v-if="fittingFilters.categories.length > 1" class="ms-badge">{{ fittingFilters.categories.length }}</span>
                  <span v-if="fittingFilters.categories.length > 0" class="ms-clear-btn" title="清空" @click.stop="clearFittingFilterDimension('categories')">✕</span>
                  <span class="ms-arrow">▾</span>
                </button>
                <div v-if="activeDropdown === 'categories'" class="ms-dropdown-menu">
                  <div class="ms-menu-header">
                    <span class="ms-menu-title">选择物理类别</span>
                    <div class="ms-menu-actions">
                      <a href="javascript:void(0)" @click.stop="selectAllFittingFilterDimension('categories', availableFittingFacets.categories)">全选</a>
                      <span class="sep">|</span>
                      <a href="javascript:void(0)" @click.stop="clearFittingFilterDimension('categories')">清空</a>
                    </div>
                  </div>
                  <div class="ms-menu-list">
                    <label
                      v-for="item in availableFittingFacets.categories"
                      :key="item.value"
                      class="ms-menu-item"
                      :class="{ checked: isFittingFilterSelected('categories', item.value) }"
                      @click.stop="toggleFittingFilterItem('categories', item.value)"
                    >
                      <input
                        type="checkbox"
                        :checked="isFittingFilterSelected('categories', item.value)"
                        @click.stop
                        @change="toggleFittingFilterItem('categories', item.value)"
                      />
                      <span class="ms-item-name">{{ item.value }}</span>
                      <span class="ms-item-count">({{ item.count }})</span>
                    </label>
                  </div>
                </div>
              </div>

              <!-- 3. 主径DN下拉框 -->
              <div class="ms-dropdown-container" v-if="availableFittingFacets.mainDns.length > 0">
                <button
                  type="button"
                  class="ms-dropdown-trigger"
                  :class="{ 'has-value': fittingFilters.mainDns.length > 0, 'is-open': activeDropdown === 'mainDns' }"
                  @click="toggleFittingDropdown('mainDns', $event)"
                >
                  <span class="ms-label-icon">📏</span>
                  <span class="ms-label-text">{{ getFittingFilterSummary('mainDns', '主径DN', 'DN') }}</span>
                  <span v-if="fittingFilters.mainDns.length > 1" class="ms-badge">{{ fittingFilters.mainDns.length }}</span>
                  <span v-if="fittingFilters.mainDns.length > 0" class="ms-clear-btn" title="清空" @click.stop="clearFittingFilterDimension('mainDns')">✕</span>
                  <span class="ms-arrow">▾</span>
                </button>
                <div v-if="activeDropdown === 'mainDns'" class="ms-dropdown-menu">
                  <div class="ms-menu-header">
                    <span class="ms-menu-title">选择主径口径</span>
                    <div class="ms-menu-actions">
                      <a href="javascript:void(0)" @click.stop="selectAllFittingFilterDimension('mainDns', availableFittingFacets.mainDns)">全选</a>
                      <span class="sep">|</span>
                      <a href="javascript:void(0)" @click.stop="clearFittingFilterDimension('mainDns')">清空</a>
                    </div>
                  </div>
                  <div class="ms-menu-list">
                    <label
                      v-for="item in availableFittingFacets.mainDns"
                      :key="item.value"
                      class="ms-menu-item"
                      :class="{ checked: isFittingFilterSelected('mainDns', item.value) }"
                      @click.stop="toggleFittingFilterItem('mainDns', item.value)"
                    >
                      <input
                        type="checkbox"
                        :checked="isFittingFilterSelected('mainDns', item.value)"
                        @click.stop
                        @change="toggleFittingFilterItem('mainDns', item.value)"
                      />
                      <span class="ms-item-name">DN{{ item.value }}</span>
                      <span class="ms-item-count">({{ item.count }})</span>
                    </label>
                  </div>
                </div>
              </div>

              <!-- 4. 角度下拉框 (弯头) -->
              <div class="ms-dropdown-container" v-if="shouldShowAngleAndBending && availableFittingFacets.angles.length > 0">
                <button
                  type="button"
                  class="ms-dropdown-trigger"
                  :class="{ 'has-value': fittingFilters.angles.length > 0, 'is-open': activeDropdown === 'angles' }"
                  @click="toggleFittingDropdown('angles', $event)"
                >
                  <span class="ms-label-icon">📐</span>
                  <span class="ms-label-text">{{ getFittingFilterSummary('angles', '角度', '', '°') }}</span>
                  <span v-if="fittingFilters.angles.length > 1" class="ms-badge">{{ fittingFilters.angles.length }}</span>
                  <span v-if="fittingFilters.angles.length > 0" class="ms-clear-btn" title="清空" @click.stop="clearFittingFilterDimension('angles')">✕</span>
                  <span class="ms-arrow">▾</span>
                </button>
                <div v-if="activeDropdown === 'angles'" class="ms-dropdown-menu">
                  <div class="ms-menu-header">
                    <span class="ms-menu-title">选择弯头角度</span>
                    <div class="ms-menu-actions">
                      <a href="javascript:void(0)" @click.stop="selectAllFittingFilterDimension('angles', availableFittingFacets.angles)">全选</a>
                      <span class="sep">|</span>
                      <a href="javascript:void(0)" @click.stop="clearFittingFilterDimension('angles')">清空</a>
                    </div>
                  </div>
                  <div class="ms-menu-list">
                    <label
                      v-for="item in availableFittingFacets.angles"
                      :key="item.value"
                      class="ms-menu-item"
                      :class="{ checked: isFittingFilterSelected('angles', item.value) }"
                      @click.stop="toggleFittingFilterItem('angles', item.value)"
                    >
                      <input
                        type="checkbox"
                        :checked="isFittingFilterSelected('angles', item.value)"
                        @click.stop
                        @change="toggleFittingFilterItem('angles', item.value)"
                      />
                      <span class="ms-item-name">{{ item.value }}°</span>
                      <span class="ms-item-count">({{ item.count }})</span>
                    </label>
                  </div>
                </div>
              </div>

              <!-- 5. 弯曲半径倍数下拉框 (弯头) -->
              <div class="ms-dropdown-container" v-if="shouldShowAngleAndBending && availableFittingFacets.bendingRatios.length > 0">
                <button
                  type="button"
                  class="ms-dropdown-trigger"
                  :class="{ 'has-value': fittingFilters.bendingRatios.length > 0, 'is-open': activeDropdown === 'bendingRatios' }"
                  @click="toggleFittingDropdown('bendingRatios', $event)"
                >
                  <span class="ms-label-icon">🔄</span>
                  <span class="ms-label-text">{{ getFittingFilterSummary('bendingRatios', '弯曲半径', '', 'DN') }}</span>
                  <span v-if="fittingFilters.bendingRatios.length > 1" class="ms-badge">{{ fittingFilters.bendingRatios.length }}</span>
                  <span v-if="fittingFilters.bendingRatios.length > 0" class="ms-clear-btn" title="清空" @click.stop="clearFittingFilterDimension('bendingRatios')">✕</span>
                  <span class="ms-arrow">▾</span>
                </button>
                <div v-if="activeDropdown === 'bendingRatios'" class="ms-dropdown-menu">
                  <div class="ms-menu-header">
                    <span class="ms-menu-title">选择弯曲半径倍数</span>
                    <div class="ms-menu-actions">
                      <a href="javascript:void(0)" @click.stop="selectAllFittingFilterDimension('bendingRatios', availableFittingFacets.bendingRatios)">全选</a>
                      <span class="sep">|</span>
                      <a href="javascript:void(0)" @click.stop="clearFittingFilterDimension('bendingRatios')">清空</a>
                    </div>
                  </div>
                  <div class="ms-menu-list">
                    <label
                      v-for="item in availableFittingFacets.bendingRatios"
                      :key="item.value"
                      class="ms-menu-item"
                      :class="{ checked: isFittingFilterSelected('bendingRatios', item.value) }"
                      @click.stop="toggleFittingFilterItem('bendingRatios', item.value)"
                    >
                      <input
                        type="checkbox"
                        :checked="isFittingFilterSelected('bendingRatios', item.value)"
                        @click.stop
                        @change="toggleFittingFilterItem('bendingRatios', item.value)"
                      />
                      <span class="ms-item-name">{{ item.value }}DN</span>
                      <span class="ms-item-count">({{ item.count }})</span>
                    </label>
                  </div>
                </div>
              </div>

              <!-- 6. 次径/支管DN下拉框 (三通/变径) -->
              <div class="ms-dropdown-container" v-if="shouldShowSubDn && availableFittingFacets.subDns.length > 0">
                <button
                  type="button"
                  class="ms-dropdown-trigger"
                  :class="{ 'has-value': fittingFilters.subDns.length > 0, 'is-open': activeDropdown === 'subDns' }"
                  @click="toggleFittingDropdown('subDns', $event)"
                >
                  <span class="ms-label-icon">🔀</span>
                  <span class="ms-label-text">{{ getFittingFilterSummary('subDns', '次径DN', 'DN') }}</span>
                  <span v-if="fittingFilters.subDns.length > 1" class="ms-badge">{{ fittingFilters.subDns.length }}</span>
                  <span v-if="fittingFilters.subDns.length > 0" class="ms-clear-btn" title="清空" @click.stop="clearFittingFilterDimension('subDns')">✕</span>
                  <span class="ms-arrow">▾</span>
                </button>
                <div v-if="activeDropdown === 'subDns'" class="ms-dropdown-menu">
                  <div class="ms-menu-header">
                    <span class="ms-menu-title">选择次径/支管口径</span>
                    <div class="ms-menu-actions">
                      <a href="javascript:void(0)" @click.stop="selectAllFittingFilterDimension('subDns', availableFittingFacets.subDns)">全选</a>
                      <span class="sep">|</span>
                      <a href="javascript:void(0)" @click.stop="clearFittingFilterDimension('subDns')">清空</a>
                    </div>
                  </div>
                  <div class="ms-menu-list">
                    <label
                      v-for="item in availableFittingFacets.subDns"
                      :key="item.value"
                      class="ms-menu-item"
                      :class="{ checked: isFittingFilterSelected('subDns', item.value) }"
                      @click.stop="toggleFittingFilterItem('subDns', item.value)"
                    >
                      <input
                        type="checkbox"
                        :checked="isFittingFilterSelected('subDns', item.value)"
                        @click.stop
                        @change="toggleFittingFilterItem('subDns', item.value)"
                      />
                      <span class="ms-item-name">DN{{ item.value }}</span>
                      <span class="ms-item-count">({{ item.count }})</span>
                    </label>
                  </div>
                </div>
              </div>

              <!-- 7. 公称压力下拉框 (阀门/承压) -->
              <div class="ms-dropdown-container" v-if="shouldShowPressure && availableFittingFacets.pressures.length > 0">
                <button
                  type="button"
                  class="ms-dropdown-trigger"
                  :class="{ 'has-value': fittingFilters.pressures.length > 0, 'is-open': activeDropdown === 'pressures' }"
                  @click="toggleFittingDropdown('pressures', $event)"
                >
                  <span class="ms-label-icon">🛡️</span>
                  <span class="ms-label-text">{{ getFittingFilterSummary('pressures', '公称压力') }}</span>
                  <span v-if="fittingFilters.pressures.length > 1" class="ms-badge">{{ fittingFilters.pressures.length }}</span>
                  <span v-if="fittingFilters.pressures.length > 0" class="ms-clear-btn" title="清空" @click.stop="clearFittingFilterDimension('pressures')">✕</span>
                  <span class="ms-arrow">▾</span>
                </button>
                <div v-if="activeDropdown === 'pressures'" class="ms-dropdown-menu">
                  <div class="ms-menu-header">
                    <span class="ms-menu-title">选择公称压力</span>
                    <div class="ms-menu-actions">
                      <a href="javascript:void(0)" @click.stop="selectAllFittingFilterDimension('pressures', availableFittingFacets.pressures)">全选</a>
                      <span class="sep">|</span>
                      <a href="javascript:void(0)" @click.stop="clearFittingFilterDimension('pressures')">清空</a>
                    </div>
                  </div>
                  <div class="ms-menu-list">
                    <label
                      v-for="item in availableFittingFacets.pressures"
                      :key="item.value"
                      class="ms-menu-item"
                      :class="{ checked: isFittingFilterSelected('pressures', item.value) }"
                      @click.stop="toggleFittingFilterItem('pressures', item.value)"
                    >
                      <input
                        type="checkbox"
                        :checked="isFittingFilterSelected('pressures', item.value)"
                        @click.stop
                        @change="toggleFittingFilterItem('pressures', item.value)"
                      />
                      <span class="ms-item-name">{{ item.value }}</span>
                      <span class="ms-item-count">({{ item.count }})</span>
                    </label>
                  </div>
                </div>
              </div>

              <!-- 8. 关键词搜索框 -->
              <div class="ms-search-box">
                <input
                  v-model="fittingFilters.searchKeyword"
                  type="text"
                  class="input"
                  placeholder="搜索标准名称 / 规格型号 / 备注..."
                  style="height: 34px; padding: 0 10px; font-size: 13px; border-radius: 8px;"
                />
              </div>

              <!-- 9. 重置按钮 -->
              <button
                v-if="activeFittingFilterTags.length > 0"
                type="button"
                class="btn ghost compact-btn reset-filter-btn"
                title="重置全部筛选条件"
                @click="clearAllFittingFilters"
              >
                🔄 重置
              </button>
            </div>

            <!-- 🏷️ 已选筛选条件胶囊标签行 (Active Filter Tags) -->
            <div v-if="activeFittingFilterTags.length > 0" class="active-filter-tags-row">
              <span class="active-tags-label">已筛选:</span>
              <span
                v-for="tag in activeFittingFilterTags"
                :key="tag.dim + '_' + tag.value"
                class="filter-tag-chip"
                title="点击移除此项筛选"
                @click="removeSingleFittingFilter(tag.dim, tag.value)"
              >
                {{ tag.label }}
                <span class="tag-close-icon">✕</span>
              </span>
              <button
                type="button"
                class="clear-all-link"
                @click="clearAllFittingFilters"
              >
                清空全部
              </button>
            </div>

            <div v-if="fittingBaselineLoading" class="loading-text">正在从数据库加载管件基准量...</div>
            <div v-else-if="fittingBaselineError" class="error-box">{{ fittingBaselineError }}</div>
            <div v-else-if="!filteredFittingBaselineRows.length" class="empty-box">
              {{ fittingBaselineRows.length ? '未找到符合筛选条件的管件记录。' : '当前选定标段暂无管件基准量记录。' }}
            </div>
            <!-- 限制20行数据高度并带固定表头与垂直滚动条 -->
            <div v-else class="table-wrap fitting-baseline-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th style="width: 36px; min-width: 36px; max-width: 36px; padding: 6px 2px; text-align: center; white-space: nowrap;">序号</th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'system_type' }" style="min-width: 95px; text-align: center; white-space: nowrap;" @click="handleFittingSort('system_type')">
                      系统类型
                      <span class="sort-icon">{{ fittingSortState.key === 'system_type' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'category' }" style="min-width: 105px; white-space: nowrap;" @click="handleFittingSort('category')">
                      物理类别
                      <span class="sort-icon">{{ fittingSortState.key === 'category' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'standard_name' }" style="min-width: 160px; white-space: nowrap;" @click="handleFittingSort('standard_name')">
                      标准名称
                      <span class="sort-icon">{{ fittingSortState.key === 'standard_name' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'model_spec' }" style="min-width: 170px; white-space: nowrap;" @click="handleFittingSort('model_spec')">
                      型号规格
                      <span class="sort-icon">{{ fittingSortState.key === 'model_spec' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'sub_model_spec' }" style="min-width: 110px; white-space: nowrap;" @click="handleFittingSort('sub_model_spec')">
                      细分规格
                      <span class="sort-icon">{{ fittingSortState.key === 'sub_model_spec' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'main_dn' }" style="min-width: 90px; text-align: right; white-space: nowrap;" @click="handleFittingSort('main_dn')">
                      主径DN
                      <span class="sort-icon">{{ fittingSortState.key === 'main_dn' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'sub_dn' }" style="min-width: 90px; text-align: right; white-space: nowrap;" @click="handleFittingSort('sub_dn')">
                      次径DN
                      <span class="sort-icon">{{ fittingSortState.key === 'sub_dn' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'angle' }" style="min-width: 85px; text-align: right; white-space: nowrap;" @click="handleFittingSort('angle')">
                      角度(°)
                      <span class="sort-icon">{{ fittingSortState.key === 'angle' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'bending_radius_ratio' }" style="min-width: 95px; text-align: right; white-space: nowrap;" @click="handleFittingSort('bending_radius_ratio')">
                      弯曲倍数
                      <span class="sort-icon">{{ fittingSortState.key === 'bending_radius_ratio' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th style="min-width: 130px; white-space: nowrap;">阀门/公称压力</th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'raw_model_spec' }" style="min-width: 140px; white-space: nowrap;" @click="handleFittingSort('raw_model_spec')">
                      原型号规格
                      <span class="sort-icon">{{ fittingSortState.key === 'raw_model_spec' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'raw_name' }" style="min-width: 140px; white-space: nowrap;" @click="handleFittingSort('raw_name')">
                      原名称
                      <span class="sort-icon">{{ fittingSortState.key === 'raw_name' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th style="width: 36px; min-width: 36px; max-width: 36px; padding: 6px 2px; text-align: center; white-space: nowrap;">单位</th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'design_qty' }" style="min-width: 125px; text-align: right; color: #1d4ed8; white-space: nowrap;" @click="handleFittingSort('design_qty')">
                      设计使用量
                      <span class="sort-icon">{{ fittingSortState.key === 'design_qty' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'purchase_plan_qty' }" style="min-width: 135px; text-align: right; color: #059669; white-space: nowrap;" @click="handleFittingSort('purchase_plan_qty')">
                      计划采购总量
                      <span class="sort-icon">{{ fittingSortState.key === 'purchase_plan_qty' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th style="min-width: 140px; white-space: nowrap;">说明备注</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in sortedFittingBaselineRows" :key="row.id || idx">
                    <td class="cell-text" style="width: 36px; min-width: 36px; max-width: 36px; padding: 6px 2px; text-align: center; color: #94a3b8; font-size: 11.5px;">{{ idx + 1 }}</td>
                    <td class="cell-text" style="text-align: center;">
                      <span :style="{
                        fontSize: '11.5px',
                        padding: '2px 7px',
                        borderRadius: '6px',
                        background: row.system_type === '高温水' ? '#eff6ff' : '#ecfdf5',
                        color: row.system_type === '高温水' ? '#2563eb' : '#059669',
                        fontWeight: '600'
                      }">
                        {{ row.system_type || '高温水' }}
                      </span>
                    </td>
                    <td class="cell-text" style="font-weight: 600;">{{ row.category || row.fitting_type || '管件' }}</td>
                    <td class="cell-text" :title="row.standard_name">{{ row.standard_name || '—' }}</td>
                    <td class="cell-text font-mono" style="font-weight: 500;" :title="row.model_spec">{{ row.model_spec }}</td>
                    <td class="cell-text font-mono" :title="row.sub_model_spec">{{ row.sub_model_spec || '—' }}</td>
                    <td class="cell-number">{{ row.main_dn != null ? row.main_dn : '—' }}</td>
                    <td class="cell-number">{{ row.sub_dn != null ? row.sub_dn : '—' }}</td>
                    <td class="cell-number">{{ row.angle != null ? row.angle : '—' }}</td>
                    <td class="cell-number">{{ row.bending_radius_ratio != null ? row.bending_radius_ratio : '—' }}</td>
                    <td class="cell-text">{{ [row.valve_model, row.pressure_rating].filter(Boolean).join(' / ') || '—' }}</td>
                    <td class="cell-text font-mono" :title="row.raw_model_spec">{{ row.raw_model_spec || '—' }}</td>
                    <td class="cell-text" :title="row.raw_name">{{ row.raw_name || '—' }}</td>
                    <td class="cell-text" style="width: 36px; min-width: 36px; max-width: 36px; padding: 6px 2px; text-align: center;">{{ row.unit || '个' }}</td>
                    <td class="cell-number" style="font-weight: 700; color: #1d4ed8;">{{ formatNumber(row.design_qty) }}</td>
                    <td class="cell-number" style="font-weight: 700; color: #059669;">{{ formatNumber(row.purchase_plan_qty) }}</td>
                    <td class="cell-text" :title="row.remark">{{ row.remark || '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div v-if="filteredFittingBaselineRows.length > 0" class="baseline-table-footer">
              <span class="footer-left">共 <strong>{{ filteredFittingBaselineRows.length }}</strong> 行管件基准数据</span>
            </div>
          </section>
        </div>

      </div>
    </main>



    <!-- 非标准管件类型二次确认 Modal 弹窗 -->
    <Transition name="fade">
      <div v-if="showFittingTypeConfirmModal" class="block-modal-overlay" @click.self="showFittingTypeConfirmModal = false">
        <div class="block-modal-container" style="max-width: 520px;">
          <div class="block-modal-header" style="background: linear-gradient(135deg, #f97316 0%, #ea580c 100%) !important;">
            <span class="block-warning-icon">⚠️</span>
            <h3 style="margin-top: 5px; color: #fff;">非标准管件类型二次确认</h3>
            <p class="block-warning-desc" style="color: rgba(255,255,255,0.9);">检测到本车包含非常用标准管件类型，请确认是否继续发货</p>
          </div>
          
          <div style="padding: 20px; text-align: left;">
            <p style="font-size: 13px; color: #475569; margin-bottom: 12px; line-height: 1.5;">
              系统标准管件包含：<strong style="color: #1e293b;">{{ (standardFittingTypes || []).join('、') }}</strong>。<br/>
              您填写的明细中包含 <span style="color: #ea580c; font-weight: bold;">{{ nonStandardItemsForConfirm.length }}</span> 行非常用管件类型：
            </p>
            <div style="background: #fff7ed; border: 1px solid #ffedd5; border-radius: 8px; padding: 12px; max-height: 160px; overflow-y: auto; margin-bottom: 20px;">
              <div v-for="(item, idx) in nonStandardItemsForConfirm" :key="idx" style="font-size: 13px; color: #9a3412; margin-bottom: 6px; display: flex; justify-content: space-between; border-bottom: 1px dashed #fed7aa; padding-bottom: 4px;">
                <span>• 管件类型: <strong style="color: #c2410c;">{{ item.fitting_type }}</strong> (规格: {{ item.model_spec || '未填' }})</span>
                <span style="font-weight: bold;">{{ item.shipped_qty }} {{ item.unit }}</span>
              </div>
            </div>
            <div style="display: flex; gap: 12px; justify-content: flex-end;">
              <button type="button" class="btn ghost" @click="showFittingTypeConfirmModal = false">取消，返回修改</button>
              <button type="button" class="btn primary" style="background: linear-gradient(135deg, #f97316 0%, #ea580c 100%) !important; border: none !important; font-weight: 600;" @click="handleConfirmNonStandardFitting">确认继续提交 🚀</button>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 同车牌1小时内发货智能合并提示 Modal 弹窗 -->
    <Transition name="fade">
      <div v-if="showFittingMergeConfirmModal && recentFittingShipmentData" class="block-modal-overlay" @click.self="showFittingMergeConfirmModal = false">
        <div class="block-modal-container" style="max-width: 560px;">
          <div class="block-modal-header" style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;">
            <span class="block-warning-icon">🚚</span>
            <h3 style="margin-top: 5px; color: #fff;">检测到 1 小时内同车牌发货单（即将合并）</h3>
            <p class="block-warning-desc" style="color: rgba(255,255,255,0.9);">
              车牌【{{ recentFittingShipmentData.vehicle_plate_no }}】在 {{ recentFittingShipmentData.minutes_ago }} 分钟前已有发货记录
            </p>
          </div>
          
          <div style="padding: 20px; text-align: left;">
            <div style="background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; padding: 12px 14px; margin-bottom: 14px; font-size: 13px;">
              <div style="font-weight: bold; color: #0369a1; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
                <span>📦 前序车次：{{ recentFittingShipmentData.shipment_no }}</span>
                <span style="font-size: 11px; background: #e0f2fe; color: #0284c7; padding: 2px 8px; border-radius: 99px;">在途待到货</span>
              </div>
              <div style="color: #475569; font-size: 12px; line-height: 1.6;">
                <div>发往标段：<strong style="color: #1e293b;">{{ getSection1Name(recentFittingShipmentData.section_1_id) }}</strong></div>
                <div>已装管件：<span style="color: #0369a1;">{{ recentFittingShipmentData.items_summary?.join('、') || (recentFittingShipmentData.items_count ? ('共 ' + recentFittingShipmentData.items_count + ' 项') : '') }}</span></div>
              </div>
            </div>

            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 14px; margin-bottom: 18px; font-size: 13px;">
              <div style="font-weight: bold; color: #334155; margin-bottom: 6px;">
                ➕ 本次追加管件（即将合并入该车次）：
              </div>
              <div style="color: #64748b; font-size: 12px; line-height: 1.6;">
                <div>拟发数量：<strong style="color: #0284c7;">共 {{ pendingSubmitPayload?.items?.length || 0 }} 种规格，合计 {{ pendingSubmitPayload?.items?.reduce((s, it) => s + Number(it.shipped_qty || 0), 0) }} 件</strong></div>
              </div>
            </div>

            <p style="font-size: 13px; color: #334155; margin-bottom: 18px; line-height: 1.5; font-weight: 500;">
              💡 <span style="color: #0284c7;">业务提示：</span>系统检测到同一车牌在 1 小时内再次录入发货，将<strong>自动合并</strong>入前序车次【{{ recentFittingShipmentData.shipment_no }}】，统一车次号与实体单据。若车牌录入有误，请点击【返回修改车牌】。
            </p>

            <div style="display: flex; gap: 12px; justify-content: flex-end;">
              <button
                type="button"
                class="btn ghost"
                style="color: #64748b; font-weight: 500;"
                @click="showFittingMergeConfirmModal = false"
              >
                ↩️ 返回修改车牌
              </button>
              <button
                type="button"
                class="btn primary"
                style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important; border: none !important; font-weight: 600;"
                :disabled="submitFittingLoading"
                @click="confirmMergeToRecentShipment"
              >
                🚚 确认合并发货 🚀
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 电子表格数据清洗与格式更正提示专属 Modal 弹窗 -->
    <Transition name="fade">
      <div v-if="showFittingFormatNoticeModal" class="block-modal-overlay" @click.self="showFittingFormatNoticeModal = false">
        <div class="block-modal-container" style="max-width: 480px; padding: 24px; border-radius: 16px; background: #ffffff;">
          <div style="display: flex; align-items: flex-start; gap: 14px; margin-bottom: 16px;">
            <div style="width: 42px; height: 42px; border-radius: 50%; background: #fff7ed; color: #ea580c; display: flex; align-items: center; justify-content: center; font-size: 22px; font-weight: bold; flex-shrink: 0; border: 1px solid #ffedd5;">⚠️</div>
            <div>
              <h3 style="margin: 0; font-size: 16.5px; font-weight: 700; color: #1e293b;">表格数据格式自动修整提示</h3>
              <p style="margin: 4px 0 0 0; font-size: 13px; color: #64748b; line-height: 1.4;">系统在提交前自动为您完成了表格格式归一与无效行擦除</p>
            </div>
          </div>

          <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px 16px; margin-bottom: 20px;">
            <ul style="margin: 0; padding-left: 18px; font-size: 13.5px; color: #334155; line-height: 1.65;">
              <li v-for="(msg, idx) in fittingFormatNoticeList" :key="idx">{{ msg }}</li>
            </ul>
            <p style="margin: 12px 0 0 0; font-size: 12.5px; color: #dc2626; font-weight: 600;">
              📌 提示：本次提交已暂停，请在电子表格中核对修改无误后，重新点击提交。
            </p>
          </div>

          <div style="display: flex; justify-content: flex-end;">
            <button type="button" class="btn primary" style="padding: 8px 24px; font-weight: 600; background: linear-gradient(135deg, #4f46e5 0%, #3730a3 100%) !important; border: none !important;" @click="showFittingFormatNoticeModal = false">我知道了，去核对</button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 全局统一发货撤销专属确认 Modal 弹窗（100% 免疫浏览器原生弹窗拦截，适配迅雷/360/手机端等所有浏览器） -->
    <Transition name="fade">
      <div v-if="cancelModalState.visible" class="block-modal-overlay" style="position: fixed !important; top: 0 !important; left: 0 !important; right: 0 !important; bottom: 0 !important; width: 100vw !important; height: 100vh !important; background: rgba(15, 23, 42, 0.6) !important; z-index: 99999 !important; display: flex !important; align-items: center !important; justify-content: center !important; backdrop-filter: blur(4px) !important;" @click.self="cancelModalState.loading ? null : (cancelModalState.visible = false)">
        <div class="block-modal-container" style="max-width: 520px; border-radius: 16px; background: #ffffff; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);">
          <div class="block-modal-header" style="background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%) !important; padding: 18px 20px;">
            <span class="block-warning-icon">🚫</span>
            <h3 style="margin-top: 5px; color: #fff; font-size: 17px; font-weight: 700;">{{ cancelModalState.title }}</h3>
            <p class="block-warning-desc" style="color: rgba(255,255,255,0.9); margin-top: 4px; font-size: 13px;">撤销后该发货记录将作废并同步更新台账，且不可逆转恢复</p>
          </div>
          
          <div style="padding: 20px; text-align: left;">
            <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 12px; margin-bottom: 16px;">
              <div style="font-size: 12px; color: #991b1b; font-weight: 600; margin-bottom: 4px;">待撤销目标对象：</div>
              <div style="font-size: 13.5px; color: #1e293b; font-weight: bold; word-break: break-all; line-height: 1.4;">{{ cancelModalState.targetDesc }}</div>
            </div>

            <label class="field" style="margin-bottom: 6px; display: block;">
              <span style="font-size: 13px; font-weight: bold; color: #1e293b; margin-bottom: 6px; display: block;">撤销原因说明 <span style="color: #ef4444;">* (必填，至少 2 个字符)</span></span>
              <textarea
                v-model.trim="cancelModalState.reason"
                class="input"
                rows="3"
                placeholder="请详细输入撤销该发货记录的具体原因（例如：车辆故障改派、单号录入有误、现场装载空间不足等）..."
                style="width: 100%; box-sizing: border-box; resize: vertical; padding: 8px 10px; font-size: 13px; min-height: 70px; border-radius: 6px; border: 1px solid #cbd5e1; outline: none; font-family: inherit;"
                :disabled="cancelModalState.loading"
                @keyup.enter.ctrl="confirmCancelAction"
                autofocus
              ></textarea>
            </label>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
              <span v-if="cancelModalState.errorMsg" style="font-size: 12px; color: #dc2626; font-weight: 600;">⚠️ {{ cancelModalState.errorMsg }}</span>
              <span v-else style="font-size: 11.5px; color: #94a3b8;">💡 提示：支持按 Ctrl + Enter 快捷提交</span>
              <span style="font-size: 12px; color: #64748b;">字数：{{ (cancelModalState.reason || '').length }} / 至少 2 字</span>
            </div>

            <div style="display: flex; gap: 12px; justify-content: flex-end;">
              <button type="button" class="btn ghost" :disabled="cancelModalState.loading" @click="cancelModalState.visible = false">放弃撤销</button>
              <button
                type="button"
                class="btn primary"
                :disabled="cancelModalState.loading || (cancelModalState.reason || '').trim().length < 2"
                style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important; border: none !important; font-weight: 600; padding: 8px 20px;"
                @click="confirmCancelAction"
              >
                {{ cancelModalState.loading ? '正在提交撤销...' : '🚫 确认撤销作废' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 运输单全生命周期流转轨迹时光轴 modal -->
    <Transition name="fade">
      <div v-if="deliveryDetailModalVisible && deliveryDetailModalData" class="block-modal-overlay" style="position: fixed !important; top: 0 !important; left: 0 !important; right: 0 !important; bottom: 0 !important; width: 100vw !important; height: 100vh !important; background: rgba(15, 23, 42, 0.6) !important; z-index: 99999 !important; display: flex !important; align-items: center !important; justify-content: center !important; backdrop-filter: blur(4px) !important;" @click.self="deliveryDetailModalVisible = false">
        <div class="block-modal-container" style="max-width: 600px; max-height: 85vh; overflow-y: auto;">
          <div class="block-modal-header" style="background: linear-gradient(135deg, #4f46e5 0%, #312e81 100%) !important;">
            <span class="block-warning-icon">🚚</span>
            <h3 style="margin-top: 5px; color: #fff;">订单全生命周期流转凭证</h3>
            <p class="block-warning-desc" style="color: rgba(255,255,255,0.9);">单号：{{ deliveryDetailModalData.deliveryCode || deliveryDetailModalData.deliveryId }}</p>
          </div>
          
          <!-- 信息概述 -->
          <div class="block-modal-metrics" style="grid-template-columns: repeat(3, 1fr); padding: 15px; gap: 8px; background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
            <div class="metric-block-card">
              <span class="lbl">车牌号</span>
              <span class="val" style="font-size: 13px; font-weight: bold; color: #1e293b;">{{ deliveryDetailModalData.vehiclePlateNo || '—' }}</span>
            </div>
            <div class="metric-block-card" style="grid-column: span 2;">
              <span class="lbl">规格型号</span>
              <span class="val model-val" style="font-size: 11px; line-height: 1.3;" :title="deliveryDetailModalData.pipeModelName">{{ deliveryDetailModalData.pipeModelName }}</span>
            </div>
          </div>

          <!-- 本车装载物品明细清单（区分管件模式与直管模式） -->
          <div v-if="deliveryDetailModalData.itemsList && deliveryDetailModalData.itemsList.length" style="padding: 14px 15px; background: #ffffff; border-bottom: 1px solid #e2e8f0; width: 100%; box-sizing: border-box; flex-shrink: 0 !important; min-height: 120px !important; overflow-x: auto;">
            <div style="font-size: 12.5px; font-weight: bold; color: #1e293b; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
              <span>{{ isFittingDeliveryModal ? '📦 本车次搭载管件清单及履约明细' : '📦 本车次保温管发货及履约明细' }}</span>
              <span style="font-size: 11px; color: #4f46e5; background: #eef2ff; padding: 3px 10px; border-radius: 99px; border: 1px solid #c7d2fe; font-weight: 600;">
                {{ isFittingDeliveryModal ? `共 ${deliveryDetailModalData.totalTypesCount} 种规格 / 合计 ${formatNumber(deliveryDetailModalData.shippedQty)} ${getModalUnitLabel(deliveryDetailModalData)}` : `装载总长度 ${formatNumber(deliveryDetailModalData.shippedQty)} 米` }}
              </span>
            </div>
            <table style="margin: 0; width: 100%; min-width: 480px; min-height: 70px; table-layout: fixed; border-collapse: collapse; border: 1px solid #edf2f7; border-radius: 6px; font-size: 11.5px; box-sizing: border-box;">
              <thead>
                <tr style="background: #f1f5f9; color: #475569;">
                  <th style="padding: 6px 4px; text-align: center; width: 28px;">#</th>
                  <th style="padding: 6px 6px; text-align: left; width: 110px;">{{ isFittingDeliveryModal ? '管件类型' : '物资类别' }}</th>
                  <th style="padding: 6px 6px; text-align: left; width: 140px;">{{ isFittingDeliveryModal ? '规格型号' : '保温管规格描述' }}</th>
                  <th style="padding: 6px 6px; text-align: right; width: 65px;">{{ isFittingDeliveryModal ? '发货件数' : '发货长度' }}</th>
                  <th style="padding: 6px 6px; text-align: right; width: 65px;">{{ isFittingDeliveryModal ? '实到件数' : '实到长度' }}</th>
                  <th style="padding: 6px 6px; text-align: left;">备注</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(it, idx) in deliveryDetailModalData.itemsList" :key="it.id || idx" style="border-bottom: 1px solid #f1f5f9;" :style="it.status === 'cancelled' ? { background: '#fef2f2', opacity: '0.8' } : {}">
                  <td style="padding: 6px 4px; text-align: center; color: #94a3b8;">{{ idx + 1 }}</td>
                  <td style="padding: 6px 6px; font-weight: 600; color: #0f172a; word-break: break-word;">
                    {{ isFittingDeliveryModal ? (it.fitting_type || it.fittingType || '管件') : '保温管' }}
                    <span v-if="it.status === 'cancelled'" class="tag-badge" style="background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; font-size: 10px; margin-left: 4px;">已撤销</span>
                  </td>
                  <td style="padding: 6px 6px; color: #334155; font-family: monospace; word-break: break-word;">{{ isFittingDeliveryModal ? (it.model_spec || it.modelSpec || '—') : (it.pipe_model_id || it.pipeModelName || deliveryDetailModalData.pipeModelName || '未填') }}</td>
                  <td style="padding: 6px 6px; text-align: right; font-weight: bold;" :style="{ color: it.status === 'cancelled' ? '#94a3b8' : '#2563eb', textDecoration: it.status === 'cancelled' ? 'line-through' : 'none', whiteSpace: 'nowrap' }">{{ formatNumber(it.shipped_qty || it.shippedQty) }} {{ it.unit || (isFittingDeliveryModal ? '个' : '米') }}</td>
                  <td style="padding: 6px 6px; text-align: right; font-weight: bold; white-space: nowrap;">
                    <span v-if="it.status === 'cancelled'" style="color: #ef4444; font-size: 11px;">已撤销</span>
                    <span v-else-if="Boolean(deliveryDetailModalData.arrivedConfirmAt || (it.status && it.status !== 'shipped' && it.status !== 'pending_arrival') || (deliveryDetailModalData.status && deliveryDetailModalData.status !== 'shipped' && deliveryDetailModalData.status !== 'pending_arrival'))" style="color: #059669;">
                      {{ formatNumber(it.arrived_qty !== undefined && it.arrived_qty !== null ? it.arrived_qty : (it.arrivedQty !== undefined && it.arrivedQty !== null ? it.arrivedQty : 0)) }} {{ it.unit || (isFittingDeliveryModal ? '个' : '米') }}
                    </span>
                    <span v-else style="color: #94a3b8; font-weight: normal;">—</span>
                  </td>
                  <td style="padding: 6px 6px; color: #64748b; font-style: italic; word-break: break-word;">
                    {{ it.cancel_reason ? `[撤销原因: ${it.cancel_reason}]` : (it.ship_remark || it.shipRemark || it.arrival_remark || '—') }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 时光轴内容 Timeline -->
          <div style="padding: 25px 25px 15px 35px; text-align: left; position: relative; width: 100%; box-sizing: border-box;">
            <!-- 时光轴中轴线 -->
            <div style="position: absolute; left: 17px; top: 30px; bottom: 30px; width: 2px; border-left: 2px dashed #cbd5e1;"></div>

            <!-- 1. 发货阶段 -->
            <div style="position: relative; margin-bottom: 20px;">
              <span style="position: absolute; left: -24px; top: 2px; width: 12px; height: 12px; border-radius: 99px; background: #4f46e5; border: 2px solid #fff; box-shadow: 0 0 0 2px #4f46e5; display: inline-block;"></span>
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                  <span style="font-size: 13px; font-weight: bold; color: #1e293b;">🏭 供给侧装车发货</span>
                  <span style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTimeDisplay(deliveryDetailModalData.shippedAt) }}</span>
                </div>
                <div style="font-size: 11px; color: #475569; background: #fafafa; padding: 6px 10px; border-radius: 6px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px;">
                  <div>发货数量：<strong>{{ formatNumber(deliveryDetailModalData.shippedQty) }} {{ deliveryDetailModalData.unit || '米' }}</strong></div>
                  <div>操作账号：<span>{{ deliveryDetailModalData.createdBy || '供给端系统' }}</span></div>
                  <div>经办人：<span>{{ deliveryDetailModalData.shipContactName || '—' }}</span></div>
                  <div style="grid-column: span 2;">联系电话：<span>{{ deliveryDetailModalData.shipContactPhone || '—' }}</span></div>
                  <div style="grid-column: span 2;">供给主体：<span>{{ deliveryDetailModalData.supplyEntityName || '—' }} ({{ deliveryDetailModalData.supplyEntityId || '—' }})</span></div>
                  <div style="grid-column: span 2;" v-if="deliveryDetailModalData.shipRemark">发货备注：<span style="color: #64748b; font-style: italic;">“{{ deliveryDetailModalData.shipRemark }}”</span></div>
                </div>
              </div>
            </div>

            <!-- 2. 到货确认阶段 -->
            <div style="position: relative; margin-bottom: 20px;">
              <span :style="{
                position: 'absolute', left: '-24px', top: '2px', width: '12px', height: '12px', borderRadius: '99px',
                background: deliveryDetailModalData.arrivedConfirmAt ? '#10b981' : '#cbd5e1',
                border: '2px solid #fff',
                boxShadow: '0 0 0 2px ' + (deliveryDetailModalData.arrivedConfirmAt ? '#10b981' : '#cbd5e1')
              }"></span>
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                  <span :style="{ fontSize: '13px', fontWeight: 'bold', color: deliveryDetailModalData.arrivedConfirmAt ? '#1e293b' : '#94a3b8' }">🚚 物流卸车到货确认</span>
                  <span v-if="deliveryDetailModalData.arrivedConfirmAt" style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTimeDisplay(deliveryDetailModalData.arrivedConfirmAt) }}</span>
                  <span v-else style="font-size: 11px; color: #94a3b8; font-style: italic;">等待卸车到货...</span>
                </div>
                <div v-if="deliveryDetailModalData.arrivedConfirmAt" style="font-size: 11px; color: #475569; background: #fafafa; padding: 6px 10px; border-radius: 6px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px;">
                  <div>到货确认：<strong>{{ formatNumber(deliveryDetailModalData.arrivedQty) }} {{ deliveryDetailModalData.unit || '米' }}</strong></div>
                  <div>操作账号：<span>{{ deliveryDetailModalData.arrivedConfirmBy || '—' }}</span></div>
                  <div>经办人：<span>{{ deliveryDetailModalData.arrivedConfirmName || '—' }}</span></div>
                  <div style="grid-column: span 2;" v-if="deliveryDetailModalData.arrivedConfirmPhone">联系电话：<span>{{ deliveryDetailModalData.arrivedConfirmPhone }}</span></div>
                  <div style="grid-column: span 2;">需求主体：<span>{{ deliveryDetailModalData.section1Name || '—' }} ({{ deliveryDetailModalData.section1Id || '—' }})</span></div>
                  <div style="grid-column: span 2;" v-if="deliveryDetailModalData.arrivedRemark">到货备注：<span style="color: #64748b; font-style: italic;">“{{ deliveryDetailModalData.arrivedRemark }}”</span></div>
                </div>
              </div>
            </div>

            <!-- 3. 施工接收阶段 -->
            <div style="position: relative; margin-bottom: 20px;">
              <span :style="{
                position: 'absolute', left: '-24px', top: '2px', width: '12px', height: '12px', borderRadius: '99px',
                background: deliveryDetailModalData.receivedConfirmAt || deliveryDetailModalData.status === 'pending_diff_approve' ? '#8b5cf6' : '#cbd5e1',
                border: '2px solid #fff',
                boxShadow: '0 0 0 2px ' + (deliveryDetailModalData.receivedConfirmAt || deliveryDetailModalData.status === 'pending_diff_approve' ? '#8b5cf6' : '#cbd5e1')
              }"></span>
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                  <span :style="{ fontSize: '13px', fontWeight: 'bold', color: deliveryDetailModalData.receivedConfirmAt || deliveryDetailModalData.status === 'pending_diff_approve' ? '#1e293b' : '#94a3b8' }">👷 施工单位确认领用</span>
                  <span v-if="deliveryDetailModalData.receivedConfirmAt" style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTimeDisplay(deliveryDetailModalData.receivedConfirmAt) }}</span>
                  <span v-else style="font-size: 11px; color: #94a3b8; font-style: italic;">等待施工接收...</span>
                </div>
                <div v-if="deliveryDetailModalData.receivedConfirmAt || deliveryDetailModalData.status === 'pending_diff_approve'" style="font-size: 11px; color: #475569; background: #fafafa; padding: 6px 10px; border-radius: 6px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px;">
                  <div>实收数量：<strong>{{ formatNumber(deliveryDetailModalData.receivedQty) }} 米</strong></div>
                  <div>操作账号：<span>{{ deliveryDetailModalData.receivedConfirmBy || '—' }}</span></div>
                  <div>经办人：<span>{{ deliveryDetailModalData.receivedConfirmName || '—' }}</span></div>
                  <div style="grid-column: span 2;" v-if="deliveryDetailModalData.receivedConfirmPhone">联系电话：<span>{{ deliveryDetailModalData.receivedConfirmPhone }}</span></div>
                  <div style="grid-column: span 2;">需求主体：<span>{{ deliveryDetailModalData.section1Name || '—' }} ({{ deliveryDetailModalData.section1Id || '—' }})</span></div>
                  <div style="grid-column: span 2;" v-if="deliveryDetailModalData.receivedRemark">接收备注：<span style="color: #64748b; font-style: italic;">“{{ deliveryDetailModalData.receivedRemark }}”</span></div>
                  <div style="grid-column: span 2; color: #f97316; font-weight: 500;" v-if="deliveryDetailModalData.isTimeoutReceive">
                    🕒 提示：该订单由系统触发 [12小时超时强制自动确认接收]。
                  </div>
                </div>
              </div>
            </div>

            <!-- 4. 差异审批阶段 -->
            <div v-if="deliveryDetailModalData.diffApproveBy || deliveryDetailModalData.status === 'pending_diff_approve'" style="position: relative; margin-bottom: 20px;">
              <span :style="{
                position: 'absolute', left: '-24px', top: '2px', width: '12px', height: '12px', borderRadius: '99px',
                background: deliveryDetailModalData.diffApproveBy ? '#f97316' : '#cbd5e1',
                border: '2px solid #fff',
                boxShadow: '0 0 0 2px ' + (deliveryDetailModalData.diffApproveBy ? '#f97316' : '#cbd5e1')
              }"></span>
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                  <span :style="{ fontSize: '13px', fontWeight: 'bold', color: deliveryDetailModalData.diffApproveBy ? '#1e293b' : '#94a3b8' }">🛡️ 现场负责人差异审批</span>
                  <span v-if="deliveryDetailModalData.diffApproveAt" style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTimeDisplay(deliveryDetailModalData.diffApproveAt) }}</span>
                  <span v-else style="font-size: 11px; color: #f97316; font-weight: bold; font-style: italic;">⚠️ 挂起待审批...</span>
                </div>
                <div v-if="deliveryDetailModalData.diffApproveBy" style="font-size: 11px; color: #475569; background: #fafafa; padding: 6px 10px; border-radius: 6px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px;">
                  <div>审批人：<strong>{{ deliveryDetailModalData.diffApproveBy }}</strong></div>
                  <div>审批时间：<span>{{ formatDateTimeDisplay(deliveryDetailModalData.diffApproveAt) }}</span></div>
                  <div style="grid-column: span 2;" v-if="deliveryDetailModalData.diffApproveRemark">审批意见：<span style="color: #ea580c; font-weight: 500;">{{ deliveryDetailModalData.diffApproveRemark }}</span></div>
                </div>
              </div>
            </div>

            <!-- 5. 库管入库阶段 -->
            <div style="position: relative; margin-bottom: 20px;">
              <span :style="{
                position: 'absolute', left: '-24px', top: '2px', width: '12px', height: '12px', borderRadius: '99px',
                background: deliveryDetailModalData.warehouseConfirmAt ? '#059669' : '#cbd5e1',
                border: '2px solid #fff',
                boxShadow: '0 0 0 2px ' + (deliveryDetailModalData.warehouseConfirmAt ? '#059669' : '#cbd5e1')
              }"></span>
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                  <span :style="{ fontSize: '13px', fontWeight: 'bold', color: deliveryDetailModalData.warehouseConfirmAt ? '#1e293b' : '#94a3b8' }">🏢 库管已确认</span>
                  <span v-if="deliveryDetailModalData.warehouseConfirmAt" style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTimeDisplay(deliveryDetailModalData.warehouseConfirmAt) }}</span>
                  <span v-else style="font-size: 11px; color: #94a3b8; font-style: italic;">等待库管确认...</span>
                </div>
                <div v-if="deliveryDetailModalData.warehouseConfirmAt" style="font-size: 11px; color: #475569; background: #fafafa; padding: 6px 10px; border-radius: 6px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px;">
                  <div>确认时间：<span>{{ formatDateTimeDisplay(deliveryDetailModalData.warehouseConfirmAt) }}</span></div>
                  <div>操作账号：<strong>{{ deliveryDetailModalData.warehouseConfirmBy || '—' }}</strong></div>
                  <div>经办人：<span>{{ deliveryDetailModalData.warehouseConfirmName || '—' }}</span></div>
                  <div style="grid-column: span 2;" v-if="deliveryDetailModalData.warehouseConfirmPhone">联系电话：<span>{{ deliveryDetailModalData.warehouseConfirmPhone }}</span></div>
                  <div style="grid-column: span 2;" v-if="deliveryDetailModalData.warehouseRemark">确认备注：<span style="color: #64748b; font-style: italic;">“{{ deliveryDetailModalData.warehouseRemark }}”</span></div>
                </div>
              </div>
            </div>

            <!-- 6. 管理员编辑覆盖节点 -->
            <div v-if="deliveryDetailModalData.shipRemark && (deliveryDetailModalData.shipRemark.includes('[超级修正智能补齐]') || deliveryDetailModalData.shipRemark.includes(' | 状态强改至'))" style="position: relative; margin-top: 20px;">
              <span style="position: absolute; left: -24px; top: 2px; width: 12px; height: 12px; border-radius: 99px; background: #64748b; border: 2px solid #fff; box-shadow: 0 0 0 2px #64748b"></span>
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                  <span style="font-size: 13px; font-weight: bold; color: #1e293b;">🛠️ 超级管理员覆盖修正</span>
                  <span style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTimeDisplay(deliveryDetailModalData.updatedAt || deliveryDetailModalData.shippedAt) }}</span>
                </div>
                <div style="font-size: 11px; color: #475569; background: #f1f5f9; padding: 6px 10px; border-radius: 6px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px;">
                  <div>修正人：<strong>{{ deliveryDetailModalData.updatedBy || '超级管理员' }}</strong></div>
                  <div>修改时间：<span>{{ formatDateTimeDisplay(deliveryDetailModalData.updatedAt) }}</span></div>
                  <div style="grid-column: span 2; word-break: break-all;">修正轨迹及批注：
                    <span style="color: #475569; font-style: italic; font-weight: 500;">
                      {{ 
                        deliveryDetailModalData.shipRemark.includes('[超级修正智能补齐]') 
                          ? deliveryDetailModalData.shipRemark.substring(deliveryDetailModalData.shipRemark.indexOf('[超级修正智能补齐]')).replace('[超级修正智能补齐] ', '') 
                          : deliveryDetailModalData.shipRemark.substring(deliveryDetailModalData.shipRemark.indexOf(' | 状态强改至') + 3) 
                      }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 7. 撤销/异常废弃阶段 (当单据状态为 cancelled 或存在撤销记录时展示) -->
            <div v-if="deliveryDetailModalData.status === 'cancelled' || deliveryDetailModalData.cancelledAt || deliveryDetailModalData.cancelAt || deliveryDetailModalData.cancelReason || deliveryDetailModalData.cancel_reason" style="position: relative; margin-top: 20px;">
              <span style="position: absolute; left: -24px; top: 2px; width: 12px; height: 12px; border-radius: 99px; background: #ef4444; border: 2px solid #fff; box-shadow: 0 0 0 2px #ef4444; display: inline-block;"></span>
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                  <span style="font-size: 13px; font-weight: bold; color: #b91c1c;">🚫 供给侧撤销发货</span>
                  <span style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTimeDisplay(deliveryDetailModalData.cancelledAt || deliveryDetailModalData.cancelAt || deliveryDetailModalData.updatedAt) }}</span>
                </div>
                <div style="font-size: 11px; color: #475569; background: #fef2f2; padding: 6px 10px; border-radius: 6px; border: 1px solid #fecaca; display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px;">
                  <div>撤销操作人：<strong style="color: #b91c1c;">{{ deliveryDetailModalData.cancelBy || deliveryDetailModalData.cancel_by || '供给端操作员' }}</strong></div>
                  <div>撤销时间：<span>{{ formatDateTimeDisplay(deliveryDetailModalData.cancelledAt || deliveryDetailModalData.cancelAt || deliveryDetailModalData.updatedAt) }}</span></div>
                  <div style="grid-column: span 2; word-break: break-all;">撤销原因：
                    <strong style="color: #b91c1c; font-weight: 600;">{{ deliveryDetailModalData.cancelReason || deliveryDetailModalData.cancel_reason || '供给侧主动撤销发货' }}</strong>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 底部按钮区 -->
          <div class="block-modal-actions" style="margin-top: 5px;">
            <button 
              type="button" 
              class="btn primary cancel-btn" 
              style="width: 100%; background: #4f46e5 !important; color: #fff !important; font-weight: 600;"
              @click="deliveryDetailModalVisible = false"
            >
              已阅并关闭
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <div v-if="showSuperEditModal" class="modal-overlay">
      <div class="modal-card elevated" style="max-width: 680px; width: 90%; background: #ffffff; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);">
        <div class="modal-header" style="padding: 20px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
          <h3 style="margin: 0; font-size: 18px; font-weight: 700; color: #1e293b;">⚙️ 数据编辑覆盖 (供给方管理员/全局管理员)</h3>
          <button type="button" class="close-btn" @click="showSuperEditModal = false" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #64748b;">×</button>
        </div>
        <div class="modal-body" style="padding: 20px; max-height: 60vh; overflow-y: auto;">
          <p class="section-desc" style="color: #4f46e5; font-weight: bold; margin-bottom: 20px; font-size: 14px;">
            ⚠️ 注意：此通道为您行使最高管理员权力编辑覆盖异常或错误数据，保存后将直接覆盖底层数据库，请务必核实数据后再保存！
          </p>
          <div class="field-grid" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;">
            <label class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">发货订单号 (order_no)</span>
              <input v-model.trim="superEditForm.orderNo" type="text" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" />
            </label>
            <label class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">运输车次号 (shipment_no)</span>
              <input v-model.trim="superEditForm.shipmentNo" type="text" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" />
            </label>
            <label class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">装车接收需求主体</span>
              <select v-model="superEditForm.section1Id" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;">
                <option v-for="st in currentAssignedSection1Options" :key="st.section_1_id" :value="st.section_1_id">
                  {{ st.section_1_name }}
                </option>
              </select>
            </label>
            <label class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">保温管规格型号</span>
              <select v-model="superEditForm.pipeModelId" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;">
                <option v-for="pm in pipeModelOptions" :key="pm.pipe_model_id" :value="pm.pipe_model_id">
                  {{ pm.pipe_model_name }}
                </option>
              </select>
            </label>
            <label class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">发货量（米）</span>
              <input v-model.number="superEditForm.shippedQty" type="number" min="0" step="1" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" />
            </label>
            <label class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">发货日期与时间</span>
              <input v-model="superEditForm.shippedAt" type="datetime-local" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" />
            </label>
            <label class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">运输车牌号</span>
              <input v-model.trim="superEditForm.vehiclePlateNo" type="text" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" />
            </label>
            <label class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">发货单流转状态</span>
              <select v-model="superEditForm.status" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" @change="handleSuperEditStatusChange">
                <option value="pending_arrival">🚚 在途待现场到货</option>
                <option value="pending_receive">📦 已到货待施工接收</option>
                <option value="pending_warehouse">🧱 待库管确认</option>
                <option value="completed">✅ 库管已确认</option>
                <option value="cancelled">❌ 已撤销发货废弃</option>
              </select>
            </label>
            <label class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">物理到货确认数量（米）</span>
              <input v-model.number="superEditForm.arrivedQty" type="number" min="0" step="1" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" placeholder="留空为无" />
            </label>
            <label class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">施工接收确认数量（米）</span>
              <input v-model.number="superEditForm.receivedQty" type="number" min="0" step="1" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" placeholder="留空为无" />
            </label>
            
            <!-- 仅提示推进状态时的入库时间 -->
            <div v-if="['arrived', 'received', 'pending_receive', 'pending_warehouse', 'completed'].includes(superEditForm.status)" style="grid-column: span 2; font-size: 12.5px; color: #64748b; background: #f8fafc; padding: 6px 12px; border-radius: 6px; border: 1px dashed #cbd5e1; display: flex; align-items: center; gap: 6px; margin-top: 2px;">
              <span>💡 提示：推进至后续状态时，未填写的节点将自动按点击保存时的当前时间入库。</span>
            </div>

            <!-- 动态级联时间戳输入框 -->
            <label v-if="['arrived', 'received', 'pending_receive', 'pending_warehouse', 'completed'].includes(superEditForm.status)" class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">1. 到货确认时间 (arrived_confirm_at)</span>
              <input v-model="superEditForm.arrivedConfirmAt" type="datetime-local" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" placeholder="留空保存时自动按当前点击时间入库" />
            </label>
            <label v-if="['received', 'pending_warehouse', 'completed'].includes(superEditForm.status)" class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">2. 施工接收时间 (received_confirm_at)</span>
              <input v-model="superEditForm.receivedConfirmAt" type="datetime-local" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" placeholder="留空保存时自动按当前点击时间入库" />
            </label>
            <label v-if="['completed'].includes(superEditForm.status)" class="field" style="display: flex; flex-direction: column; gap: 6px; grid-column: span 2;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">3. 库管确认时间 (warehouse_confirm_at)</span>
              <input v-model="superEditForm.warehouseConfirmAt" type="datetime-local" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" placeholder="留空保存时自动按当前点击时间入库" />
            </label>

            <label class="field" style="display: flex; flex-direction: column; gap: 6px; grid-column: span 2;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">发货备注信息</span>
              <textarea v-model.trim="superEditForm.shipRemark" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; height: 60px; resize: vertical;"></textarea>
            </label>
          </div>
          <p v-if="superEditError" style="margin-top: 16px; color: #ef4444; font-size: 13px; font-weight: 600;">⚠️ 错误提示：{{ superEditError }}</p>
        </div>
        <div class="modal-footer" style="padding: 16px 20px; border-top: 1px solid #e2e8f0; display: flex; justify-content: flex-end; gap: 12px; background: #f8fafc; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;">
          <button type="button" class="btn ghost" @click="showSuperEditModal = false" style="padding: 10px 20px; border: 1px solid #cbd5e1; background: #ffffff; color: #475569; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer;">取消覆盖</button>
          <button type="button" class="btn primary" :disabled="superEditSaving" @click="saveSuperEdit" style="padding: 10px 20px; border: none; background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%); color: #ffffff; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2);">
            {{ superEditSaving ? '正在保存覆盖...' : '💾 确认编辑覆盖' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 管件专用超级编辑覆盖弹窗 -->
    <div v-if="showSuperEditFittingModal" class="modal-overlay">
      <div class="modal-card elevated" style="max-width: 680px; width: 90%; background: #ffffff; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);">
        <div class="modal-header" style="padding: 20px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
          <h3 style="margin: 0; font-size: 18px; font-weight: 700; color: #1e293b;">⚙️ 管件数据编辑覆盖 (供给方管理员/全局管理员)</h3>
          <button type="button" class="close-btn" @click="showSuperEditFittingModal = false" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #64748b;">×</button>
        </div>
        <div class="modal-body" style="padding: 20px; max-height: 60vh; overflow-y: auto;">
          <p class="section-desc" style="color: #4f46e5; font-weight: bold; margin-bottom: 20px; font-size: 14px;">
            ⚠️ 注意：此通道为您行使最高管理员权力编辑覆盖管件发货与履约数据，保存后将直接覆盖底层数据库，请务必核实数据后再保存！
          </p>
          <div class="field-grid" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;">
            <label class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">发货订单号 (order_no)</span>
              <input v-model.trim="superEditFittingForm.orderNo" type="text" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" />
            </label>
            <label class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">运输车次号 (shipment_no)</span>
              <input v-model.trim="superEditFittingForm.shipmentNo" type="text" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" />
            </label>
            <label class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">装车接收需求主体</span>
              <select v-model="superEditFittingForm.section1Id" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;">
                <option v-for="st in currentAssignedSection1Options" :key="st.section_1_id" :value="st.section_1_id">
                  {{ st.section_1_name }}
                </option>
              </select>
            </label>
            <label class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">运输车牌号</span>
              <input v-model.trim="superEditFittingForm.vehiclePlateNo" type="text" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" />
            </label>
            <label class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">管件大类 (fitting_type)</span>
              <input v-model.trim="superEditFittingForm.fittingType" list="fitting-type-list" type="text" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" placeholder="例如: 90°弯头 / 变径管 / 三通" />
            </label>
            <label class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">管件型号 / 规格描述 (model_spec)</span>
              <input v-model.trim="superEditFittingForm.modelSpec" type="text" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" placeholder="例如: DN300*8 / DN200*6" />
            </label>
            <label class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">发货件数</span>
              <input v-model.number="superEditFittingForm.shippedQty" type="number" min="1" step="1" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" />
            </label>
            <label class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">计量单位</span>
              <input v-model.trim="superEditFittingForm.unit" type="text" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" placeholder="例如: 个 / 件 / 套" />
            </label>
            <label class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">发货日期与时间</span>
              <input v-model="superEditFittingForm.shippedAt" type="datetime-local" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" />
            </label>
            <label class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">发货单流转状态</span>
              <select v-model="superEditFittingForm.status" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" @change="handleSuperEditFittingStatusChange">
                <option value="pending_arrival">🚚 在途待现场到货</option>
                <option value="pending_receive">📦 已到货待施工接收</option>
                <option value="pending_warehouse">🧱 待库管确认</option>
                <option value="completed">✅ 库管已确认</option>
                <option value="cancelled">❌ 已撤销发货废弃</option>
              </select>
            </label>
            <label v-if="['pending_receive', 'pending_warehouse', 'completed'].includes(superEditFittingForm.status)" class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">物理到货确认件数</span>
              <input v-model.number="superEditFittingForm.arrivedQty" type="number" min="1" step="1" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" placeholder="留空默认等于发货件数" />
            </label>
            <label v-if="superEditFittingForm.status === 'cancelled'" class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">撤销原因 (cancel_reason)</span>
              <input v-model.trim="superEditFittingForm.cancelReason" type="text" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" placeholder="例如: 现场计划变更撤销" />
            </label>
            
            <!-- 仅提示推进状态时的入库时间 -->
            <div v-if="['pending_receive', 'pending_warehouse', 'completed'].includes(superEditFittingForm.status)" style="grid-column: span 2; font-size: 12.5px; color: #64748b; background: #f8fafc; padding: 6px 12px; border-radius: 6px; border: 1px dashed #cbd5e1; display: flex; align-items: center; gap: 6px; margin-top: 2px;">
              <span>💡 提示：推进至后续状态时，未填写的节点将自动按点击保存时的当前时间入库。</span>
            </div>

            <!-- 动态级联时间戳输入框 -->
            <label v-if="['pending_receive', 'pending_warehouse', 'completed'].includes(superEditFittingForm.status)" class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">1. 到货确认时间 (arrived_confirm_at)</span>
              <input v-model="superEditFittingForm.arrivedConfirmAt" type="datetime-local" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" placeholder="留空保存时自动按当前点击时间入库" />
            </label>
            <label v-if="['pending_warehouse', 'completed'].includes(superEditFittingForm.status)" class="field" style="display: flex; flex-direction: column; gap: 6px;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">2. 施工接收时间 (received_confirm_at)</span>
              <input v-model="superEditFittingForm.receivedConfirmAt" type="datetime-local" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" placeholder="留空保存时自动按当前点击时间入库" />
            </label>
            <label v-if="['completed'].includes(superEditFittingForm.status)" class="field" style="display: flex; flex-direction: column; gap: 6px; grid-column: span 2;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">3. 库管确认时间 (warehouse_confirm_at)</span>
              <input v-model="superEditFittingForm.warehouseConfirmAt" type="datetime-local" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;" placeholder="留空保存时自动按当前点击时间入库" />
            </label>

            <label class="field" style="display: flex; flex-direction: column; gap: 6px; grid-column: span 2;">
              <span style="font-size: 13px; font-weight: 600; color: #475569;">发货备注信息</span>
              <textarea v-model.trim="superEditFittingForm.shipRemark" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; height: 60px; resize: vertical;"></textarea>
            </label>
          </div>
          <p v-if="superEditFittingError" style="margin-top: 16px; color: #ef4444; font-size: 13px; font-weight: 600;">⚠️ 错误提示：{{ superEditFittingError }}</p>
        </div>
        <div class="modal-footer" style="padding: 16px 20px; border-top: 1px solid #e2e8f0; display: flex; justify-content: flex-end; gap: 12px; background: #f8fafc; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;">
          <button type="button" class="btn ghost" @click="showSuperEditFittingModal = false" style="padding: 10px 20px; border: 1px solid #cbd5e1; background: #ffffff; color: #475569; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer;">取消覆盖</button>
          <button type="button" class="btn primary" :disabled="superEditFittingSaving" @click="saveSuperEditFitting" style="padding: 10px 20px; border: none; background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%); color: #ffffff; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2);">
            {{ superEditFittingSaving ? '正在保存覆盖...' : '💾 确认编辑覆盖' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 导出配置与 XLSX 导出组件 -->
    <ExportSettingsModal
      :show="showExportModal"
      :columns="exportColumns"
      :data="allDeliveryRows"
      :filtered-data="deliveryRows"
      default-filename="保温管物流发货历史台账"
      @close="showExportModal = false"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import RevoGrid from '@revolist/vue3-datagrid'
import * as XLSX from 'xlsx-js-style'
import { useAuthStore } from '../../daily_report_25_26/store/auth'
import { AppHeader, Breadcrumbs, useTubePageShell, useTubeRealtimeRefresh, getDeliveryStatus } from './shared'
import ExportSettingsModal from './ExportSettingsModal.vue'
import {
  cancelTubeSupplyManagementDelivery,
  createTubeSupplyManagementDeliveryBatch,
  getTubeSupplyManagementDeliveries,
  getTubeSupplyManagementDemandSummary,
  getTubeSupplyManagementOptions,
  createCustomSupplyEntity,
  superUpdateTubeSupplyManagementDelivery,
  superUpdateTubeFittingDelivery,
  getFittingDeliveriesList,
  checkRecentFittingShipment,
  submitFittingDelivery,
  cancelFittingDelivery,
  getTubeDemandManagementFittingBaseline,
} from '../../daily_report_25_26/services/api'

const PROJECT_KEY = 'insulation_pipe_supply_2026'
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const VALID_TABS = ['demand', 'register', 'history', 'fitting', 'fitting_baseline']
const VALID_CATEGORIES = ['pipe', 'fitting']

// 清理历史残留的 localStorage 缓存，避免跨入口污染
try {
  localStorage.removeItem('phoenix_supply_management_active_category')
  localStorage.removeItem('phoenix_supply_management_active_tab')
  localStorage.removeItem('phoenix_supply_management_supply_entity')
} catch (e) {}

const getInitialCategoryAndTab = () => {
  // 纯粹依据当前 URL Query 参数（刷新页面时 URL 自带参数，从主菜单进入时 URL 干净则展示默认页）
  const queryTab = String(route?.query?.tab || '').trim()
  const queryCategory = String(route?.query?.category || '').trim()

  if (VALID_TABS.includes(queryTab)) {
    const inferredCategory = ['fitting', 'fitting_baseline'].includes(queryTab) ? 'fitting' : 'pipe'
    return {
      category: VALID_CATEGORIES.includes(queryCategory) ? queryCategory : inferredCategory,
      tab: queryTab,
    }
  }

  // 无 Query 时严格返回默认首页
  return { category: 'pipe', tab: 'demand' }
}

const syncTabStateToUrl = (category, tab) => {
  if (route?.query?.tab !== tab || route?.query?.category !== category) {
    router.replace({
      query: {
        ...(route?.query || {}),
        category,
        tab,
      },
    }).catch(() => {})
  }
}

const {
  loading,
  errorMessage,
  breadcrumbItems,
  goProjectPages,
  managementMode,
  modeLabels,
} = useTubePageShell('供给侧管理入口')

const optionsLoading = ref(false)
const optionsError = ref('')
const supplyEntityOptions = ref([])
const customSupplyEntities = ref([])
const isCustomInputMode = ref(false)
const customEntityInput = ref('')

const allSupplyEntityOptions = computed(() => {
  const rawFromBackend = supplyEntityOptions.value || []
  const rawFromCustom = customSupplyEntities.value || []

  const allMap = new Map()

  for (const item of rawFromBackend) {
    if (!item || !item.entity_id) continue
    allMap.set(item.entity_id, {
      ...item,
      isCustom: Boolean(item.isCustom || item.is_custom),
    })
  }

  for (const item of rawFromCustom) {
    if (!item || !item.entity_id) continue
    if (!allMap.has(item.entity_id)) {
      allMap.set(item.entity_id, {
        ...item,
        isCustom: true,
      })
    }
  }

  const allList = Array.from(allMap.values())
  const regularEntities = allList.filter((item) => !item.isCustom)
  const customEntities = allList.filter((item) => item.isCustom)

  return [...regularEntities, ...customEntities]
})
const section1Options = ref([])
const allPipeModelOptions = ref([])
const currentGroup = ref('')
const isGlobalAdmin = computed(() => {
  const g = String(currentGroup.value || '').trim().toLowerCase()
  return g === 'global_admin' || g === 'dev_admin'
})
const currentSupplyEntityIds = ref([])
const showDate = ref('')
const planStartDate = ref('')

const initialSelection = getInitialCategoryAndTab()
const selectedSupplyEntityId = ref('')
const activeCategory = ref(initialSelection.category) // 'pipe' | 'fitting'
const activeTab = ref(initialSelection.tab)
const lastPipeTab = ref(initialSelection.category === 'pipe' ? initialSelection.tab : 'demand')
const lastFittingTab = ref(initialSelection.category === 'fitting' ? initialSelection.tab : 'fitting')
const supplyDemandViewMode = ref('summary')
const selectedPipeModelIds = ref([])

const handleCategoryClick = (category) => {
  if (activeCategory.value === category) return
  activeCategory.value = category
  if (category === 'pipe') {
    activeTab.value = lastPipeTab.value || 'demand'
  } else if (category === 'fitting') {
    activeTab.value = lastFittingTab.value || 'fitting'
  }
  syncTabStateToUrl(activeCategory.value, activeTab.value)
}

const handleTabClick = (tab) => {
  activeTab.value = tab
  if (['fitting', 'fitting_baseline'].includes(tab)) {
    lastFittingTab.value = tab
  } else {
    lastPipeTab.value = tab
  }
  syncTabStateToUrl(activeCategory.value, tab)
}

// --- 管件发货记录 Tab 专用变量与逻辑 ---
const getNowISOString = () => {
  const now = new Date()
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset())
  return now.toISOString().slice(0, 16)
}

const openTimelineModal = (input) => {
  showDeliveryDetail(input)
}

const fittingForm = ref({
  vehiclePlateNo: '',
  section1Id: '',
  shipContactName: '',
  shipContactPhone: '',
  shipRemark: '',
})

const createEmptyFittingRows = (count = 8) => {
  const rows = []
  for (let i = 0; i < count; i++) {
    rows.push({
      fitting_type: '',
      model_spec: '',
      shipped_qty: '',
      unit: '',
      remark: '',
    })
  }
  return rows
}

const fittingGridSource = ref(createEmptyFittingRows(8))
const fittingGridRef = ref(null)

const showFittingTypeConfirmModal = ref(false)
const showFittingMergeConfirmModal = ref(false)
const recentFittingShipmentData = ref(null)
const showFittingFormatNoticeModal = ref(false)
const fittingFormatNoticeList = ref([])
const nonStandardItemsForConfirm = ref([])
const pendingSubmitPayload = ref(null)
const submitFittingLoading = ref(false)
const fittingActionMsg = ref(null)
const fittingLoading = ref(false)
const fittingDeliveries = ref([])
const fittingSearchKw = ref('')

const addFittingGridRows = (count = 5) => {
  fittingGridSource.value = [...fittingGridSource.value, ...createEmptyFittingRows(count)]
}

const clearFittingGrid = () => {
  fittingGridSource.value = createEmptyFittingRows(8)
}



const handleFittingGridAfterEdit = (e) => {
  if (e && e.detail) {
    const { model, prop, val } = e.detail
    if (model && prop) {
      model[prop] = val
      // 强制重设数组引用，触发 RevoGrid 重刷 cellClass 高亮
      fittingGridSource.value = [...fittingGridSource.value]
    }
  }
}

const standardFittingTypes = ref([
  '弯头',
  '三通',
  '大小头',
  '封头',
  '直缝弯管',
  '补偿器',
  '固定节'
])

const allowedFittingUnits = ref(['个', '套'])

const FITTING_ALIAS_MAP = {
  '异径管': '大小头',
  '大小头(异径管)': '大小头',
  '异径管(大小头)': '大小头',
  '波纹补偿器': '补偿器',
  '弯管': '直缝弯管'
}

function getNormalizedFittingType(typeStr) {
  if (!typeStr) return ''
  const trimmed = String(typeStr).trim()
  return FITTING_ALIAS_MAP[trimmed] || trimmed
}

function isStandardFittingType(typeStr) {
  const normalized = getNormalizedFittingType(typeStr)
  return (standardFittingTypes.value || []).includes(normalized)
}

function isValidFittingUnit(unitStr) {
  if (!unitStr) return false
  const trimmed = String(unitStr).trim()
  return (allowedFittingUnits.value || []).includes(trimmed)
}

function getGroupUnitLabel(group) {
  if (!group || !group.items || !group.items.length) return '个'
  const units = Array.from(new Set(group.items.map(it => String(it.unit || '个').trim()).filter(Boolean)))
  if (units.length === 1) return units[0]
  return '件'
}

function getModalUnitLabel(modalData) {
  if (!modalData) return '个'
  const items = modalData.itemsList || []
  if (!items.length) return modalData.unit || '个'
  const units = Array.from(new Set(items.map(it => String(it.unit || '个').trim()).filter(Boolean)))
  if (units.length === 1) return units[0]
  return '件'
}

const isInvalidQtyCell = (val) => {
  if (val === '' || val === undefined || val === null) return false
  const num = Number(val)
  return !Number.isInteger(num) || num <= 0
}

const fittingGridColumns = ref([
  { 
    prop: 'fitting_type', 
    name: '管件类型', 
    size: 180, 
    readonly: false,
    cellClass: (row) => {
      const model = (row && row.model) ? row.model : (row || {})
      const val = model.fitting_type
      const trimmed = String(val || '').trim()
      const hasContent = Boolean(model.model_spec || (model.shipped_qty !== '' && model.shipped_qty !== undefined && model.shipped_qty !== null))
      if (!trimmed && hasContent) return 'rg-cell-error'
      if (trimmed && !isStandardFittingType(trimmed)) return 'rg-cell-warning'
      return ''
    },
    cellProperties: (props) => {
      const model = (props && props.model) ? props.model : (props || {})
      const val = model.fitting_type
      const trimmed = String(val || '').trim()
      const hasContent = Boolean(model.model_spec || (model.shipped_qty !== '' && model.shipped_qty !== undefined && model.shipped_qty !== null))
      if (!trimmed && hasContent) {
        return { style: { backgroundColor: '#fee2e2', color: '#b91c1c', fontWeight: 'bold' } }
      }
      if (trimmed && !isStandardFittingType(trimmed)) {
        return { style: { backgroundColor: '#fff7ed', color: '#c2410c', fontWeight: 'bold' } }
      }
      return {}
    }
  },
  { 
    prop: 'model_spec', 
    name: '型号/规格', 
    size: 380, 
    readonly: false,
    cellClass: (row) => {
      const model = (row && row.model) ? row.model : (row || {})
      const val = model.model_spec
      const trimmed = String(val || '').trim()
      const hasContent = Boolean(model.fitting_type || (model.shipped_qty !== '' && model.shipped_qty !== undefined && model.shipped_qty !== null))
      if (!trimmed && hasContent) return 'rg-cell-error'
      return ''
    },
    cellProperties: (props) => {
      const model = (props && props.model) ? props.model : (props || {})
      const val = model.model_spec
      const trimmed = String(val || '').trim()
      const hasContent = Boolean(model.fitting_type || (model.shipped_qty !== '' && model.shipped_qty !== undefined && model.shipped_qty !== null))
      if (!trimmed && hasContent) {
        return { style: { backgroundColor: '#fee2e2', color: '#b91c1c', fontWeight: 'bold' } }
      }
      return {}
    }
  },
  { 
    prop: 'shipped_qty', 
    name: '发货数量', 
    size: 120, 
    readonly: false,
    cellClass: (row) => {
      const model = (row && row.model) ? row.model : (row || {})
      const val = model.shipped_qty
      const hasContent = Boolean(model.fitting_type || model.model_spec)
      const isInvalid = isInvalidQtyCell(val)
      const isMissing = (val === '' || val === undefined || val === null) && hasContent
      if (isMissing || isInvalid) return 'rg-cell-error'
      return ''
    },
    cellProperties: (props) => {
      const model = (props && props.model) ? props.model : (props || {})
      const val = model.shipped_qty
      const hasContent = Boolean(model.fitting_type || model.model_spec)
      const isInvalid = isInvalidQtyCell(val)
      const isMissing = (val === '' || val === undefined || val === null) && hasContent
      if (isMissing || isInvalid) {
        return { style: { backgroundColor: '#fee2e2', color: '#b91c1c', fontWeight: 'bold' } }
      }
      return {}
    }
  },
  { 
    prop: 'unit', 
    name: '单位', 
    size: 90, 
    readonly: false,
    cellClass: (row) => {
      const model = (row && row.model) ? row.model : (row || {})
      const val = model.unit
      const hasContent = Boolean(model.fitting_type || model.model_spec || (model.shipped_qty !== '' && model.shipped_qty !== undefined && model.shipped_qty !== null))
      if (hasContent && !isValidFittingUnit(val)) return 'rg-cell-error'
      return ''
    },
    cellProperties: (props) => {
      const model = (props && props.model) ? props.model : (props || {})
      const val = model.unit
      const hasContent = Boolean(model.fitting_type || model.model_spec || (model.shipped_qty !== '' && model.shipped_qty !== undefined && model.shipped_qty !== null))
      if (hasContent && !isValidFittingUnit(val)) {
        return { style: { backgroundColor: '#fee2e2', color: '#b91c1c', fontWeight: 'bold' } }
      }
      return {}
    }
  },
  { prop: 'remark', name: '明细备注', size: 200, readonly: false },
])

const deliveryDetailModalVisible = ref(false)
const deliveryDetailModalData = ref(null)

const isFittingDeliveryModal = computed(() => {
  if (!deliveryDetailModalData.value) return false
  const data = deliveryDetailModalData.value
  if (data.fitting_type || data.fittingType || data.isFittingDelivery) return true
  if (data.pipe_model_id || data.pipe_model_name || data.pipeModelId || data.pipeModelName || data.isStraightPipe) return false
  if (data.itemsList && data.itemsList.length && (data.itemsList[0].fitting_type || data.itemsList[0].fittingType)) return true
  return false
})

function showDeliveryDetail(input) {
  if (!input) return
  const isGroup = Boolean(input.items && Array.isArray(input.items))
  const itemsList = isGroup ? input.items : [input]
  const mainRow = itemsList[0] || input

  const shipmentNo = input.shipmentNo || input.shipment_no || mainRow.shipment_no || mainRow.shipmentNo || mainRow.order_no || mainRow.orderNo || String(mainRow.id || '')
  const vehiclePlateNo = input.vehiclePlateNo || input.vehicle_plate_no || mainRow.vehicle_plate_no || mainRow.vehiclePlateNo || '—'
  const shippedAt = input.shippedAt || input.shipped_at || mainRow.shipped_at || mainRow.shippedAt || ''
  const supplyEntityId = input.supplyEntityId || input.supply_entity_id || mainRow.supply_entity_id || mainRow.supplyEntityId || ''
  const supplyEntityName = input.supplyEntityName || input.supply_entity_name || mainRow.supply_entity_name || mainRow.supplyEntityName || supplyEntityId
  const section1Id = input.section1Id || input.section_1_id || mainRow.section_1_id || mainRow.section1Id || ''
  const section1Name = input.section1Name || input.section_1_name || mainRow.section_1_name || mainRow.section1Name || section1Id

  const shipContactName = mainRow.ship_contact_name || mainRow.shipContactName || input.shipContactName || mainRow.created_by || '发货负责人'
  const shipContactPhone = mainRow.ship_contact_phone || mainRow.shipContactPhone || input.shipContactPhone || '—'
  const createdBy = mainRow.created_by || mainRow.createdBy || mainRow.operator || input.createdBy || '发货操作员'
  const shipRemark = input.shipRemark || mainRow.ship_remark || mainRow.shipRemark || ''

  const arrivedConfirmAt = mainRow.arrived_at || mainRow.arrivedConfirmAt || ''
  const arrivedConfirmBy = mainRow.arrived_by || mainRow.arrivedConfirmBy || (arrivedConfirmAt ? '现场到货负责人' : '')
  const arrivedRemark = mainRow.arrival_remark || mainRow.arrivedRemark || ''

  const constructionConfirmedAt = mainRow.construction_confirmed_at || mainRow.receivedConfirmAt || ''
  const constructionConfirmedBy = mainRow.construction_confirmed_by || mainRow.receivedConfirmBy || (constructionConfirmedAt ? '施工接收负责人' : '')
  const constructionRemark = mainRow.construction_remark || mainRow.receivedRemark || ''

  const warehouseConfirmedAt = mainRow.warehouse_confirmed_at || mainRow.warehouseConfirmAt || ''
  const warehouseConfirmedBy = mainRow.warehouse_confirmed_by || mainRow.warehouseConfirmBy || (warehouseConfirmedAt ? '库管员' : '')
  const warehouseRemark = mainRow.warehouse_remark || mainRow.warehouseRemark || ''

  const totalShippedQty = itemsList.reduce((sum, it) => sum + (Number(it.shipped_qty !== undefined ? it.shipped_qty : it.shippedQty) || 0), 0)
  const totalArrivedQty = itemsList.reduce((sum, it) => {
    const val = (it.arrived_qty !== undefined && it.arrived_qty !== null) ? it.arrived_qty : (it.arrivedQty !== undefined && it.arrivedQty !== null ? it.arrivedQty : null)
    return sum + (val !== null ? Number(val) : 0)
  }, 0)

  deliveryDetailModalData.value = {
    ...mainRow,
    ...input,
    itemsList,
    totalTypesCount: itemsList.length,
    deliveryCode: shipmentNo,
    vehiclePlateNo,
    shippedAt,
    shippedQty: totalShippedQty,
    arrivedQty: totalArrivedQty,
    unit: mainRow.unit || input.unit || ((mainRow.pipe_model_id || mainRow.pipe_model_name || mainRow.pipeModelId || mainRow.pipeModelName || input.pipeModelName || input.pipe_model_id) ? '米' : (mainRow.fitting_type ? '个' : '米')),
    pipeModelName: itemsList.length === 1 ? `${mainRow.fitting_type || '管件'} (${mainRow.model_spec || '未填'})` : `多规格组合管件车次 (${itemsList.length} 种规模型号卡块)`,
    supplyEntityName,
    section1Name,
    shipContactName,
    shipContactPhone,
    createdBy,
    shipRemark,
    arrivedConfirmAt,
    arrivedAt: arrivedConfirmAt,
    arrivedConfirmBy,
    arrivedBy: arrivedConfirmBy,
    arrivedRemark,
    arrivalRemark: arrivedRemark,
    receivedConfirmAt: constructionConfirmedAt,
    constructionConfirmedAt,
    receivedConfirmBy: constructionConfirmedBy,
    constructionConfirmedBy,
    receivedRemark: constructionRemark,
    constructionRemark,
    warehouseConfirmAt: warehouseConfirmedAt,
    warehouseConfirmedAt,
    warehouseConfirmBy: warehouseConfirmedBy,
    warehouseConfirmedBy,
    cancelledAt: mainRow.cancelled_at || mainRow.cancel_at || mainRow.cancelledAt || input.cancel_at || input.cancelled_at || input.cancelAt || '',
    cancelReason: mainRow.cancel_reason || mainRow.cancelReason || input.cancel_reason || input.cancelReason || '',
    cancelBy: mainRow.cancelled_by || mainRow.cancel_by || mainRow.cancelBy || input.cancel_by || input.cancelled_by || input.cancelBy || '',
  }
  deliveryDetailModalVisible.value = true
}

const downloadFittingTemplate = () => {
  // Sheet 1: 主填报清单 (包含 A1 到 E20 完整标准边框区)
  const defaultUnit = (allowedFittingUnits.value || ['个'])[0] || '个'
  const typesText = (standardFittingTypes.value || []).join('、')
  const allowedUnitsText = (allowedFittingUnits.value || ['个', '套']).join('”、“')

  const templateRows = [
    ['管件类型 *', '型号/规格 *', '发货数量 *', '单位', '备注', '', '📌 填报规范与推荐类型说明'],
    ['弯头', '90°DN1100 R=1.5DN', 10, defaultUnit, '样例数据', '', `1. 系统推荐标准管件类型：${typesText}`],
    ['三通', 'DN1000/DN900', 5, defaultUnit, '样例数据', '', '2. 支持别名识别：填“异径管”系统将自动识别为“大小头”；填“弯管”自动识别为“直缝弯管”'],
    ['大小头', 'DN1000/DN800', 5, defaultUnit, '样例数据', '', '3. 发货数量请填写纯数字（大于 0）'],
    ['直缝弯管', 'DN1100 5°R=138.7 L=12m', 10, defaultUnit, '样例数据']
  ]

  // 补齐 20 行标准表数据格 (A1:E20)
  while (templateRows.length < 20) {
    templateRows.push(['', '', '', '', ''])
  }

  const worksheet = XLSX.utils.aoa_to_sheet(templateRows)

  // 显式为 A1:E20 区域内的单元格挂载精准全边框与对齐样式
  const thinBorder = {
    top: { style: 'thin', color: { rgb: 'CBD5E1' } },
    bottom: { style: 'thin', color: { rgb: 'CBD5E1' } },
    left: { style: 'thin', color: { rgb: 'CBD5E1' } },
    right: { style: 'thin', color: { rgb: 'CBD5E1' } }
  }
  const headerStyle = {
    font: { name: '宋体', sz: 11, bold: true, color: { rgb: '1E293B' } },
    fill: { fgColor: { rgb: 'F1F5F9' } },
    alignment: { horizontal: 'center', vertical: 'center' },
    border: {
      top: { style: 'thin', color: { rgb: '94A3B8' } },
      bottom: { style: 'medium', color: { rgb: '64748B' } },
      left: { style: 'thin', color: { rgb: '94A3B8' } },
      right: { style: 'thin', color: { rgb: '94A3B8' } }
    }
  }

  for (let r = 0; r < 20; r++) {
    for (let c = 0; c < 5; c++) {
      const cellAddress = XLSX.utils.encode_cell({ r, c })
      if (!worksheet[cellAddress]) {
        worksheet[cellAddress] = { v: '', t: 's' }
      }
      if (r === 0) {
        worksheet[cellAddress].s = headerStyle
      } else {
        worksheet[cellAddress].s = {
          font: { name: '宋体', sz: 10 },
          alignment: { vertical: 'center', horizontal: c === 2 ? 'right' : 'left' },
          border: thinBorder
        }
      }
    }
  }

  worksheet['!cols'] = [
    { wch: 16 },
    { wch: 28 },
    { wch: 12 },
    { wch: 10 },
    { wch: 25 },
    { wch: 4 },
    { wch: 65 }
  ]

  // Sheet 2: 标准管件类型参照表
  const guideData = [
    ['标准管件类型', '说明与兼容别名'],
    ...(standardFittingTypes.value || []).map(t => [t, '系统全局配置标准管件类型'])
  ]
  const guideSheet = XLSX.utils.aoa_to_sheet(guideData)
  guideSheet['!cols'] = [
    { wch: 18 },
    { wch: 45 }
  ]

  // Sheet 3: 校验规则与单位修正提示
  const ruleData = [
    ['规则与提示分类', '具体逻辑与说明'],
    ['1. 数据校验规则', '“管件类型”、“型号/规格”、“发货数量”为核心必填项；“发货数量”必须为大于 0 的有效纯数字。相同“发货车次号”和“车牌号”的多行记录在解析后会自动聚合为整车卡片。'],
    ['2. 单位强校验逻辑', `管件发货数量单位必须填写合规文本（例如：“${allowedUnitsText}”）。若留空或填写了非法单位，系统将阻断提交并提示纠错。`],
    ['3. 空行与不完整行过滤', '系统解析记录时，会自动识别并彻底剔除全空行以及关键必填项缺失的不完整数据行，确保最终生成的均为有效合规台账。'],
    ['4. 类型识别与提示逻辑', `系统自动校验匹配“${typesText}”标准管件。填报别名“异径管”自动修正识别为“大小头”，填“弯管”自动识别为“直缝弯管”。未匹配到的自定类型将提示标注为非常规件。`]
  ]
  const ruleSheet = XLSX.utils.aoa_to_sheet(ruleData)
  ruleSheet['!cols'] = [
    { wch: 24 },
    { wch: 90 }
  ]

  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, '管件发货清单填报')
  XLSX.utils.book_append_sheet(workbook, guideSheet, '7大标准管件类型对照表')
  XLSX.utils.book_append_sheet(workbook, ruleSheet, '校验规则与单位修正提示')
  XLSX.writeFile(workbook, '管件发货清单标准填报模板.xlsx')
}

const downloadFittingHistoryExcel = () => {
  if (!fittingDeliveries.value || !fittingDeliveries.value.length) {
    alert('当前没有可导出的管件发货记录')
    return
  }

  const exportData = fittingDeliveries.value.map(row => ({
    '管件车次号': row.shipment_no,
    '管件订单号': row.order_no,
    '车牌号': row.vehicle_plate_no,
    '接收标段': getSection1Name(row.section_1_id),
    '管件类型': row.fitting_type,
    '型号/规格': row.model_spec,
    '发货数量': row.shipped_qty,
    '单位': row.unit || '个',
    '发货时间': formatDateTimeDisplay(row.shipped_at),
    '发货经办人': row.ship_contact_name || '—',
    '联系电话': row.ship_contact_phone || '—',
    '备注': row.ship_remark || '—',
  }))

  const worksheet = XLSX.utils.json_to_sheet(exportData)
  worksheet['!cols'] = [
    { wch: 18 },
    { wch: 22 },
    { wch: 14 },
    { wch: 14 },
    { wch: 14 },
    { wch: 22 },
    { wch: 12 },
    { wch: 8 },
    { wch: 20 },
    { wch: 12 },
    { wch: 14 },
    { wch: 25 }
  ]

  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, '已发货管件台账')
  const dateStr = new Date().toISOString().slice(0, 10)
  XLSX.writeFile(workbook, `已发货管件历史台账_${dateStr}.xlsx`)
}

const fittingTableSectionFilter = ref('')
const expandedFittingGroupKeys = ref(new Set())

const toggleFittingGroup = (groupKey) => {
  const next = new Set(expandedFittingGroupKeys.value)
  if (next.has(groupKey)) {
    next.delete(groupKey)
  } else {
    next.add(groupKey)
  }
  expandedFittingGroupKeys.value = next
}

const isFittingGroupExpanded = (groupKey) => {
  return expandedFittingGroupKeys.value.has(groupKey)
}

const toggleAllFittingGroups = (expandAll = true) => {
  if (expandAll) {
    expandedFittingGroupKeys.value = new Set(groupedFittingDeliveries.value.map(g => g.groupKey))
  } else {
    expandedFittingGroupKeys.value = new Set()
  }
}

const groupedFittingDeliveries = computed(() => {
  const map = new Map()
  for (const item of fittingDeliveries.value) {
    const groupKey = item.shipment_key || item.shipment_no || item.order_no || `${item.vehicle_plate_no}_${item.shipped_at}_${item.id}`
    if (!map.has(groupKey)) {
      map.set(groupKey, {
        groupKey,
        shipmentNo: item.shipment_no || item.order_no || '—',
        orderNo: item.order_no || '—',
        vehiclePlateNo: item.vehicle_plate_no || '—',
        shippedAt: item.shipped_at,
        supplyEntityId: item.supply_entity_id,
        supplyEntityName: item.supply_entity_name || item.supply_entity_id || '—',
        section1Id: item.section_1_id,
        section1Name: item.section_1_name || getSection1Name(item.section_1_id) || '—',
        shipRemark: item.ship_remark || '',
        status: item.status || 'shipped',
        totalQty: 0,
        items: []
      })
    }
    const group = map.get(groupKey)
    group.items.push(item)
    group.totalQty += (Number(item.shipped_qty) || 0)
  }

  // 短板状态判定原则：若多条明细中有任何一条状态落后于其它条目，外层 group.status 展现该落后状态
  const statusRankMap = {
    'shipped': 0,
    'pending_arrival': 0,
    'arrived': 1,
    'pending_receive': 1,
    'construction_confirmed': 2,
    'pending_warehouse': 2,
    'received': 2,
    'warehouse_confirmed': 3,
    'completed': 3
  }

  const result = Array.from(map.values())
  for (const group of result) {
    const activeItems = group.items.filter(item => (item.status || 'shipped') !== 'cancelled')
    group.hasCancelled = activeItems.length !== group.items.length
    if (!activeItems.length) {
      group.status = 'cancelled'
      continue
    }
    let minRank = 999
    let minStatus = 'shipped'
    for (const item of activeItems) {
      const st = item.status || 'shipped'
      const r = statusRankMap[st] !== undefined ? statusRankMap[st] : 0
      if (r < minRank) {
        minRank = r
        minStatus = st
      }
    }
    group.status = minStatus
  }

  return result
})

const loadFittingDeliveries = async () => {
  expandedFittingGroupKeys.value = new Set()
  if (!selectedSupplyEntityId.value) {
    fittingDeliveries.value = []
    return
  }
  fittingLoading.value = true
  try {
    const data = await getFittingDeliveriesList(PROJECT_KEY, {
      supplyEntityId: selectedSupplyEntityId.value || '',
      section1Id: fittingTableSectionFilter.value || '',
      searchKeyword: fittingSearchKw.value || '',
      limit: 200,
    })
    if (data && data.ok) {
      fittingDeliveries.value = data.items || []
    }
  } catch (err) {
    console.error('加载管件发货记录失败:', err)
  } finally {
    fittingLoading.value = false
  }
}

// 全局统一撤销模态弹窗状态（彻底规避任何浏览器对 window.prompt 的拦截）
const cancelModalState = ref({
  visible: false,
  type: '', // 'fitting_group' | 'fitting_item' | 'pipe_delivery'
  title: '',
  targetDesc: '',
  reason: '',
  loading: false,
  errorMsg: '',
  payload: null,
})

const handleCancelFittingGroup = (group) => {
  const cancellableItems = (group?.items || []).filter(item => ['shipped', 'pending_arrival'].includes(item.status || 'shipped'))
  if (!cancellableItems.length) {
    fittingActionMsg.value = { type: 'error', text: '该车次管件已全部进入后续确认/入库流程或已被撤销，不可重复撤销。' }
    return
  }
  fittingActionMsg.value = null
  cancelModalState.value = {
    visible: true,
    type: 'fitting_group',
    title: '整车管件发货撤销确认',
    targetDesc: `车次号：${group.shipmentNo}（车牌：${group.vehiclePlateNo || '未填'}，发往：${group.section1Name || '未填'}，共 ${cancellableItems.length} 项在途管件）`,
    reason: '',
    loading: false,
    errorMsg: '',
    payload: { group, items: cancellableItems },
  }
}

const handleCancelFittingItem = (item, group) => {
  const st = item.status || 'shipped'
  if (!['shipped', 'pending_arrival'].includes(st)) {
    fittingActionMsg.value = { type: 'error', text: `该管件明细（${item.fitting_type} ${item.model_spec}）已进入后续确认流程或已撤销，不可撤销。` }
    return
  }
  fittingActionMsg.value = null
  const specDesc = `${item.fitting_type} ${item.model_spec}`
  cancelModalState.value = {
    visible: true,
    type: 'fitting_item',
    title: '局部管件明细撤销确认',
    targetDesc: `管件规格：${specDesc}（数量：${item.shipped_qty} ${item.unit || '个'}，订单号：${item.order_no || '—'}，所属车次：${group?.shipmentNo || '—'}）`,
    reason: '',
    loading: false,
    errorMsg: '',
    payload: { item, group },
  }
}

const confirmCancelAction = async () => {
  const cleanReason = String(cancelModalState.value.reason || '').trim()
  if (cleanReason.length < 2) {
    cancelModalState.value.errorMsg = '撤销原因至少填写 2 个字符'
    return
  }
  cancelModalState.value.errorMsg = ''
  cancelModalState.value.loading = true

  try {
    if (cancelModalState.value.type === 'fitting_group') {
      const { items } = cancelModalState.value.payload || {}
      const result = await cancelFittingDelivery(PROJECT_KEY, {
        ids: (items || []).map(item => item.id),
        remark: cleanReason,
      })
      cancelModalState.value.visible = false
      fittingActionMsg.value = { type: 'success', text: `已成功整车撤销 ${result?.updated_count || items?.length || 0} 项管件发货记录` }
      await loadFittingDeliveries()
    } else if (cancelModalState.value.type === 'fitting_item') {
      const { item } = cancelModalState.value.payload || {}
      const specDesc = `${item?.fitting_type || ''} ${item?.model_spec || ''}`
      await cancelFittingDelivery(PROJECT_KEY, {
        ids: [item.id],
        remark: cleanReason,
      })
      cancelModalState.value.visible = false
      fittingActionMsg.value = { type: 'success', text: `已成功撤销管件明细【${specDesc}】` }
      await loadFittingDeliveries()
    } else if (cancelModalState.value.type === 'pipe_delivery') {
      const { row, identifier } = cancelModalState.value.payload || {}
      cancelLoadingIds.value = {
        ...cancelLoadingIds.value,
        [row.deliveryId]: true,
      }
      try {
        await cancelTubeSupplyManagementDelivery(PROJECT_KEY, row.deliveryId, {
          cancel_reason: cleanReason,
        })
        cancelModalState.value.visible = false
        setActionMessage('success', `发货记录 ${row.deliveryCode || identifier} 已成功撤销。`)
        await Promise.all([loadDemandSummary(), loadDeliveries()])
      } finally {
        cancelLoadingIds.value = {
          ...cancelLoadingIds.value,
          [row.deliveryId]: false,
        }
      }
    }
  } catch (error) {
    cancelModalState.value.errorMsg = error.message || '撤销失败，请稍后重试'
    if (cancelModalState.value.type === 'pipe_delivery') {
      setActionMessage('error', error?.message || '撤销发货记录失败')
    } else {
      fittingActionMsg.value = { type: 'error', text: `撤销失败：${error.message || '系统异常'}` }
    }
  } finally {
    cancelModalState.value.loading = false
  }
}

const submitFittingForm = async () => {
  fittingActionMsg.value = null

  if (isReadOnlyViewer.value) {
    fittingActionMsg.value = { type: 'error', text: '🔒 只读观察员角色无权操作或提交管件发货记录！' }
    return
  }

  if (!canSubmitCurrentProject.value) {
    fittingActionMsg.value = { type: 'error', text: '当前账号没有本项目的管件发货提交权限。' }
    return
  }

  if (!fittingForm.value.vehiclePlateNo) {
    fittingActionMsg.value = { type: 'error', text: '请填写运输车牌号' }
    return
  }
  if (!fittingForm.value.section1Id) {
    fittingActionMsg.value = { type: 'error', text: '请选择接收标段' }
    return
  }

  // 0. 第一时间自动清洗：记录哪些行因为信息缺失被擦除（不再自动补充/更正单位，而是做强校验）
  let gridChanged = false
  const deletedIncompleteRowNums = []

  ;(fittingGridSource.value || []).forEach((it, idx) => {
    if (!it) return
    const rowNum = idx + 1
    const typeStr = String(it.fitting_type || '').trim()
    const specStr = String(it.model_spec || '').trim()
    const hasQty = it.shipped_qty !== '' && it.shipped_qty !== undefined && it.shipped_qty !== null

    const isAllEmpty = !typeStr && !specStr && !hasQty && !String(it.unit || '').trim()
    const isFullyFilled = Boolean(typeStr && specStr && hasQty)

    if (!isFullyFilled && !isAllEmpty) {
      // 存在至少一处空缺，直接删除清空整行内容
      deletedIncompleteRowNums.push(rowNum)
      it.fitting_type = ''
      it.model_spec = ''
      it.shipped_qty = ''
      it.unit = ''
      it.remark = ''
      gridChanged = true
    }
  })

  if (gridChanged) {
    fittingGridSource.value = [...fittingGridSource.value]
    if (fittingGridRef.value && typeof fittingGridRef.value.refresh === 'function') {
      fittingGridRef.value.refresh()
    }
  }

  // 1. 搜集所有清洗后留下的完整填写行
  const validItems = []
  const filledRows = (fittingGridSource.value || [])
    .map((it, idx) => ({
      rowNum: idx + 1,
      fitting_type: String(it?.fitting_type || '').trim(),
      model_spec: String(it?.model_spec || '').trim(),
      shipped_qty_raw: it?.shipped_qty,
      unit: String(it?.unit || '').trim(),
      remark: String(it?.remark || '').trim(),
    }))
    .filter(r => r.fitting_type && r.model_spec && r.shipped_qty_raw !== '' && r.shipped_qty_raw !== undefined && r.shipped_qty_raw !== null)

  if (!filledRows.length) {
    const errorMsg = deletedIncompleteRowNums.length > 0
      ? '检测到填写不全的行已被自动清空，表格中已无有效合规发货行'
      : '请至少在电子表格中完整填写一行有效的管件发货明细'
    fittingActionMsg.value = { type: 'error', text: errorMsg }

    if (gridChanged) {
      const notices = []
      if (deletedIncompleteRowNums.length > 0) {
        notices.push(`第 ${deletedIncompleteRowNums.join('、')} 行因【类型/型号/数量】填写空缺，已自动清空整行记录；`)
      }
      notices.push(`⚠️ ${errorMsg}`)
      fittingFormatNoticeList.value = notices
      showFittingFormatNoticeModal.value = true
    }
    return
  }

  // 2. 全盘并行强校验：检查【单位】是否为“个”或“套”，以及发货数量是否为纯正整数
  let validationError = null
  for (const row of filledRows) {
    if (!isValidFittingUnit(row.unit)) {
      const allowedText = (allowedFittingUnits.value || ['个', '套']).join('”或“')
      validationError = `表格第 ${row.rowNum} 行【单位】无效，填写内容必须为“${allowedText}”（当前填写: ${row.unit ? `“${row.unit}”` : '空'}）`
      fittingActionMsg.value = { type: 'error', text: validationError }
      break
    }

    const parsedQty = Number(row.shipped_qty_raw)
    const isPosInt = Number.isInteger(parsedQty) && parsedQty > 0
    if (!isPosInt) {
      validationError = `表格第 ${row.rowNum} 行发货数量必须为大于 0 的纯正整数数字 (当前填写: ${row.shipped_qty_raw ?? '空'})`
      fittingActionMsg.value = { type: 'error', text: validationError }
      break
    }

    validItems.push({
      fitting_type: row.fitting_type,
      model_spec: row.model_spec,
      shipped_qty: parsedQty,
      unit: row.unit,
      remark: row.remark,
    })
  }

  // 3. 汇总全盘审计情况：若包含删行或业务校验报错，全盘一次性弹窗提示 + 阻断提交
  if (gridChanged || validationError) {
    const notices = []
    if (deletedIncompleteRowNums.length > 0) {
      notices.push(`第 ${deletedIncompleteRowNums.join('、')} 行因【类型/型号/数量】填写空缺，已自动清空整行记录；`)
    }
    if (validationError) {
      notices.push(`⚠️ ${validationError}。`)
    }

    fittingFormatNoticeList.value = notices
    showFittingFormatNoticeModal.value = true
    return
  }

  const payload = {
    supply_entity_id: selectedSupplyEntityId.value || 'BH',
    vehicle_plate_no: fittingForm.value.vehiclePlateNo,
    section_1_id: fittingForm.value.section1Id,
    shipped_at: getNowISOString(),
    ship_contact_name: fittingForm.value.shipContactName,
    ship_contact_phone: fittingForm.value.shipContactPhone,
    ship_remark: fittingForm.value.shipRemark,
    items: validItems,
  }

  // 3. 检查是否包含非常用管件类型（二次确认弹窗）
  const nonStandardList = validItems.filter(it => !isStandardFittingType(it.fitting_type))
  if (nonStandardList.length > 0) {
    pendingSubmitPayload.value = payload
    nonStandardItemsForConfirm.value = nonStandardList
    showFittingTypeConfirmModal.value = true
    return
  }

  // 4. 预检 20 分钟内同车牌在途发货单
  await checkRecentAndProceed(payload)
}

const handleConfirmNonStandardFitting = async () => {
  showFittingTypeConfirmModal.value = false
  if (!pendingSubmitPayload.value) return
  await checkRecentAndProceed(pendingSubmitPayload.value)
}

const checkRecentAndProceed = async (payload) => {
  if (!payload) return
  try {
    submitFittingLoading.value = true
    const checkRes = await checkRecentFittingShipment(PROJECT_KEY, {
      vehicle_plate_no: payload.vehicle_plate_no,
      section_1_id: payload.section_1_id,
      supply_entity_id: payload.supply_entity_id,
    })
    if (checkRes && checkRes.has_recent) {
      recentFittingShipmentData.value = checkRes
      pendingSubmitPayload.value = payload
      showFittingMergeConfirmModal.value = true
      return
    }
  } catch (checkErr) {
    console.warn('预检近期发货记录异常，继续走正常发货提交:', checkErr)
  } finally {
    submitFittingLoading.value = false
  }

  await doRealSubmitFittingForm(payload)
}

const confirmMergeToRecentShipment = async () => {
  if (!pendingSubmitPayload.value || !recentFittingShipmentData.value) return
  const payload = {
    ...pendingSubmitPayload.value,
    merge_to_shipment_no: recentFittingShipmentData.value.shipment_no,
  }
  showFittingMergeConfirmModal.value = false
  await doRealSubmitFittingForm(payload)
}

const doRealSubmitFittingForm = async (directPayload = null) => {
  const basePayload = directPayload || pendingSubmitPayload.value
  if (!basePayload) return

  const payload = { ...basePayload }

  submitFittingLoading.value = true
  fittingActionMsg.value = null
  showFittingTypeConfirmModal.value = false
  showFittingMergeConfirmModal.value = false

  try {
    const data = await submitFittingDelivery(PROJECT_KEY, payload)
    if (data && data.ok) {
      const isMerged = Boolean(data.merged)
      fittingActionMsg.value = {
        type: 'success',
        text: isMerged
          ? `🎉 追加合并成功！已成功向车次 [${data.shipment_no}] 合并追加 ${data.count} 项管件明细`
          : `🎉 提交成功！已成功录入管件发货单 [${data.shipment_no}]，包含 ${data.count} 项明细`,
      }
      fittingGridSource.value = createEmptyFittingRows(8)
      fittingForm.value.vehiclePlateNo = ''
      fittingForm.value.shipRemark = ''
      fittingForm.value.shippedAt = getNowISOString()
      pendingSubmitPayload.value = null
      recentFittingShipmentData.value = null
      loadFittingDeliveries()
    } else {
      fittingActionMsg.value = { type: 'error', text: data?.detail || '提交失败' }
    }
  } catch (err) {
    fittingActionMsg.value = { type: 'error', text: `网络或系统异常: ${err.message}` }
  } finally {
    submitFittingLoading.value = false
  }
}

watch(activeTab, (tab) => {
  if (['fitting', 'fitting_baseline'].includes(tab)) {
    activeCategory.value = 'fitting'
    lastFittingTab.value = tab
    if (tab === 'fitting') {
      loadFittingDeliveries()
    } else if (tab === 'fitting_baseline') {
      if (!selectedFittingBaselineSection1Id.value && currentAssignedSection1Options.value?.length > 0) {
        selectedFittingBaselineSection1Id.value = currentAssignedSection1Options.value[0].section_1_id
      }
      loadFittingBaseline()
    }
  } else {
    activeCategory.value = 'pipe'
    lastPipeTab.value = tab
    if (tab === 'demand') {
      loadDemandSummary()
    } else if (tab === 'history') {
      loadDeliveries()
    }
  }
  syncTabStateToUrl(activeCategory.value, tab)
})

// --- 管件设计量与计划采购量 Tab 专用响应式状态与逻辑 ---
const selectedFittingBaselineSection1Id = ref('')
const fittingBaselineLoading = ref(false)
const fittingBaselineError = ref('')
const fittingBaselineRows = ref([])

// 多维多选分面筛选响应式状态
const fittingFilters = reactive({
  systemTypes: [],
  categories: [],
  mainDns: [],
  subDns: [],
  angles: [],
  bendingRatios: [],
  pressures: [],
  searchKeyword: '',
})

// 动态提取当前标段各维度的可选值列表及对应记录数
const availableFittingFacets = computed(() => {
  const rows = fittingBaselineRows.value || []
  
  const systemTypeMap = new Map()
  const categoryMap = new Map()
  const mainDnMap = new Map()
  const subDnMap = new Map()
  const angleMap = new Map()
  const bendingRatioMap = new Map()
  const pressureMap = new Map()

  rows.forEach((r) => {
    const st = String(r.system_type || '').trim()
    if (st) systemTypeMap.set(st, (systemTypeMap.get(st) || 0) + 1)

    const cat = String(r.category || r.fitting_type || '').trim()
    if (cat) categoryMap.set(cat, (categoryMap.get(cat) || 0) + 1)

    if (r.main_dn != null && !isNaN(Number(r.main_dn))) {
      const dn = Number(r.main_dn)
      mainDnMap.set(dn, (mainDnMap.get(dn) || 0) + 1)
    }

    if (r.sub_dn != null && !isNaN(Number(r.sub_dn))) {
      const sdn = Number(r.sub_dn)
      subDnMap.set(sdn, (subDnMap.get(sdn) || 0) + 1)
    }

    if (r.angle != null && !isNaN(Number(r.angle))) {
      const ang = Number(r.angle)
      angleMap.set(ang, (angleMap.get(ang) || 0) + 1)
    }

    if (r.bending_radius_ratio != null && !isNaN(Number(r.bending_radius_ratio))) {
      const br = Number(r.bending_radius_ratio)
      bendingRatioMap.set(br, (bendingRatioMap.get(br) || 0) + 1)
    }

    const pr = String(r.pressure_rating || '').trim()
    if (pr) pressureMap.set(pr, (pressureMap.get(pr) || 0) + 1)
  })

  return {
    systemTypes: Array.from(systemTypeMap.entries()).map(([value, count]) => ({ value, count })),
    categories: Array.from(categoryMap.entries()).map(([value, count]) => ({ value, count })),
    mainDns: Array.from(mainDnMap.entries()).map(([value, count]) => ({ value, count })).sort((a, b) => b.value - a.value),
    subDns: Array.from(subDnMap.entries()).map(([value, count]) => ({ value, count })).sort((a, b) => b.value - a.value),
    angles: Array.from(angleMap.entries()).map(([value, count]) => ({ value, count })).sort((a, b) => b.value - a.value),
    bendingRatios: Array.from(bendingRatioMap.entries()).map(([value, count]) => ({ value, count })).sort((a, b) => b.value - a.value),
    pressures: Array.from(pressureMap.entries()).map(([value, count]) => ({ value, count })),
  }
})

const shouldShowAngleAndBending = computed(() => {
  if (fittingFilters.categories.length > 0) {
    return fittingFilters.categories.some(c => c.includes('弯头') || c.includes('弯管'))
  }
  return (availableFittingFacets.value.angles.length > 0 || availableFittingFacets.value.bendingRatios.length > 0)
})

const shouldShowSubDn = computed(() => {
  if (fittingFilters.categories.length > 0) {
    return fittingFilters.categories.some(c => c.includes('三通') || c.includes('异径') || c.includes('变径') || c.includes('大小头'))
  }
  return availableFittingFacets.value.subDns.length > 0
})

const shouldShowPressure = computed(() => {
  if (fittingFilters.categories.length > 0) {
    return fittingFilters.categories.some(c => c.includes('阀') || c.includes('补偿') || c.includes('波纹'))
  }
  return availableFittingFacets.value.pressures.length > 0
})

const activeDropdown = ref('')

function toggleFittingDropdown(name, event) {
  if (event) event.stopPropagation()
  if (activeDropdown.value === name) {
    activeDropdown.value = ''
  } else {
    activeDropdown.value = name
  }
}

function closeFittingDropdown() {
  activeDropdown.value = ''
}

function getFittingFilterSummary(dimension, defaultLabel, prefix = '', suffix = '') {
  const selected = fittingFilters[dimension] || []
  if (selected.length === 0) {
    return defaultLabel
  }
  if (selected.length === 1) {
    return `${prefix}${selected[0]}${suffix}`
  }
  return `已选 ${selected.length} 项`
}

function selectAllFittingFilterDimension(dimension, options) {
  if (!options || !options.length) return
  fittingFilters[dimension] = options.map(opt => opt.value)
}

function toggleFittingFilterItem(dimension, value) {
  const arr = fittingFilters[dimension]
  if (!arr) return
  const index = arr.indexOf(value)
  if (index > -1) {
    arr.splice(index, 1)
  } else {
    arr.push(value)
  }
}

function isFittingFilterSelected(dimension, value) {
  return fittingFilters[dimension]?.includes(value) ?? false
}

function clearFittingFilterDimension(dimension) {
  if (fittingFilters[dimension]) {
    fittingFilters[dimension] = []
  }
}

function clearAllFittingFilters() {
  fittingFilters.systemTypes = []
  fittingFilters.categories = []
  fittingFilters.mainDns = []
  fittingFilters.subDns = []
  fittingFilters.angles = []
  fittingFilters.bendingRatios = []
  fittingFilters.pressures = []
  fittingFilters.searchKeyword = ''
}

function removeSingleFittingFilter(dim, val) {
  if (dim === 'searchKeyword') {
    fittingFilters.searchKeyword = ''
  } else if (Array.isArray(fittingFilters[dim])) {
    const idx = fittingFilters[dim].indexOf(val)
    if (idx > -1) {
      fittingFilters[dim].splice(idx, 1)
    }
  }
}

const activeFittingFilterTags = computed(() => {
  const tags = []
  fittingFilters.systemTypes.forEach(v => tags.push({ dim: 'systemTypes', label: `系统: ${v}`, value: v }))
  fittingFilters.categories.forEach(v => tags.push({ dim: 'categories', label: `类别: ${v}`, value: v }))
  fittingFilters.mainDns.forEach(v => tags.push({ dim: 'mainDns', label: `主径: DN${v}`, value: v }))
  fittingFilters.subDns.forEach(v => tags.push({ dim: 'subDns', label: `次径: DN${v}`, value: v }))
  fittingFilters.angles.forEach(v => tags.push({ dim: 'angles', label: `角度: ${v}°`, value: v }))
  fittingFilters.bendingRatios.forEach(v => tags.push({ dim: 'bendingRatios', label: `弯曲: ${v}DN`, value: v }))
  fittingFilters.pressures.forEach(v => tags.push({ dim: 'pressures', label: `压力: ${v}`, value: v }))
  if (fittingFilters.searchKeyword.trim()) {
    tags.push({ dim: 'searchKeyword', label: `搜索: "${fittingFilters.searchKeyword.trim()}"`, value: fittingFilters.searchKeyword })
  }
  return tags
})

const filteredFittingBaselineRows = computed(() => {
  let list = fittingBaselineRows.value || []

  if (fittingFilters.systemTypes.length > 0) {
    list = list.filter(r => fittingFilters.systemTypes.includes(String(r.system_type || '').trim()))
  }
  if (fittingFilters.categories.length > 0) {
    list = list.filter(r => fittingFilters.categories.includes(String(r.category || r.fitting_type || '').trim()))
  }
  if (fittingFilters.mainDns.length > 0) {
    list = list.filter(r => r.main_dn != null && fittingFilters.mainDns.includes(Number(r.main_dn)))
  }
  if (fittingFilters.subDns.length > 0) {
    list = list.filter(r => r.sub_dn != null && fittingFilters.subDns.includes(Number(r.sub_dn)))
  }
  if (fittingFilters.angles.length > 0) {
    list = list.filter(r => r.angle != null && fittingFilters.angles.includes(Number(r.angle)))
  }
  if (fittingFilters.bendingRatios.length > 0) {
    list = list.filter(r => r.bending_radius_ratio != null && fittingFilters.bendingRatios.includes(Number(r.bending_radius_ratio)))
  }
  if (fittingFilters.pressures.length > 0) {
    list = list.filter(r => fittingFilters.pressures.includes(String(r.pressure_rating || '').trim()))
  }
  if (fittingFilters.searchKeyword.trim()) {
    const kw = fittingFilters.searchKeyword.trim().toLowerCase()
    list = list.filter((r) => {
      const matchName = String(r.standard_name || '').toLowerCase().includes(kw)
      const matchSpec = String(r.model_spec || '').toLowerCase().includes(kw)
      const matchSub = String(r.sub_model_spec || '').toLowerCase().includes(kw)
      const matchRawSpec = String(r.raw_model_spec || '').toLowerCase().includes(kw)
      const matchRawName = String(r.raw_name || '').toLowerCase().includes(kw)
      const matchDn = String(r.main_dn || '').includes(kw) || String(r.sub_dn || '').includes(kw)
      const matchValve = String(r.valve_model || '').toLowerCase().includes(kw)
      const matchPressure = String(r.pressure_rating || '').toLowerCase().includes(kw)
      const matchRemark = String(r.remark || '').toLowerCase().includes(kw)
      return matchName || matchSpec || matchSub || matchRawSpec || matchRawName || matchDn || matchValve || matchPressure || matchRemark
    })
  }
  return list
})

const fittingSortState = reactive({
  key: '',
  order: 'asc',
})

function handleFittingSort(key) {
  if (fittingSortState.key === key) {
    if (fittingSortState.order === 'asc') {
      fittingSortState.order = 'desc'
    } else if (fittingSortState.order === 'desc') {
      fittingSortState.key = ''
      fittingSortState.order = 'asc'
    }
  } else {
    fittingSortState.key = key
    fittingSortState.order = 'asc'
  }
}

const sortedFittingBaselineRows = computed(() => {
  const list = [...filteredFittingBaselineRows.value]
  if (!fittingSortState.key) return list
  const { key, order } = fittingSortState
  const multiplier = order === 'asc' ? 1 : -1

  return list.sort((a, b) => {
    let valA = a[key]
    let valB = b[key]
    const isNullA = valA === null || valA === undefined || valA === ''
    const isNullB = valB === null || valB === undefined || valB === ''
    if (isNullA && isNullB) return 0
    if (isNullA) return 1
    if (isNullB) return -1

    if (typeof valA === 'number' && typeof valB === 'number') {
      return (valA - valB) * multiplier
    }
    const numA = Number(valA)
    const numB = Number(valB)
    if (!isNaN(numA) && !isNaN(numB) && typeof valA !== 'boolean' && typeof valB !== 'boolean') {
      return (numA - numB) * multiplier
    }
    return String(valA).localeCompare(String(valB), 'zh-CN', { numeric: true }) * multiplier
  })
})

const fittingBaselineStats = computed(() => {
  let totalDesignQty = 0
  let totalPurchaseQty = 0
  let filteredDesignQty = 0
  let filteredPurchaseQty = 0

  fittingBaselineRows.value.forEach((r) => {
    totalDesignQty += Number(r.design_qty || 0)
    totalPurchaseQty += Number(r.purchase_plan_qty || 0)
  })

  filteredFittingBaselineRows.value.forEach((r) => {
    filteredDesignQty += Number(r.design_qty || 0)
    filteredPurchaseQty += Number(r.purchase_plan_qty || 0)
  })

  return {
    totalDesignQty,
    totalPurchaseQty,
    filteredDesignQty,
    filteredPurchaseQty,
  }
})

async function loadFittingBaseline() {
  const validIds = currentAssignedSection1Ids.value
  if (!selectedFittingBaselineSection1Id.value || (validIds && validIds.size > 0 && !validIds.has(selectedFittingBaselineSection1Id.value))) {
    if (currentAssignedSection1Options.value && currentAssignedSection1Options.value.length > 0) {
      selectedFittingBaselineSection1Id.value = currentAssignedSection1Options.value[0].section_1_id
    } else {
      selectedFittingBaselineSection1Id.value = ''
      fittingBaselineRows.value = []
      return
    }
  }
  fittingBaselineLoading.value = true
  fittingBaselineError.value = ''
  try {
    const response = await getTubeDemandManagementFittingBaseline(PROJECT_KEY, selectedFittingBaselineSection1Id.value)
    fittingBaselineRows.value = response.rows || []
  } catch (error) {
    fittingBaselineError.value = error?.message || '加载管件基准量失败'
    fittingBaselineRows.value = []
  } finally {
    fittingBaselineLoading.value = false
  }
}

function exportFittingBaseline() {
  const rows = sortedFittingBaselineRows.value
  if (!rows.length) return

  const headers = [
    '序号', '系统类型', '物理类别', '标准名称', '型号规格', '细分规格/子型号',
    '主径DN', '次径DN', '角度(°)', '弯曲倍数', '阀门/公称压力', '原型号规格',
    '原名称', '单位', '设计使用量', '计划采购总量', '说明备注'
  ]

  const dataRows = rows.map((r, idx) => [
    idx + 1,
    r.system_type || '高温水',
    r.category || r.fitting_type || '管件',
    r.standard_name || '',
    r.model_spec || '',
    r.sub_model_spec || '',
    r.main_dn,
    r.sub_dn,
    r.angle,
    r.bending_radius_ratio,
    [r.valve_model, r.pressure_rating].filter(Boolean).join(' / ') || '',
    r.raw_model_spec || '',
    r.raw_name || '',
    r.unit || '个',
    r.design_qty != null ? r.design_qty : 0,
    r.purchase_plan_qty != null ? r.purchase_plan_qty : 0,
    r.remark || '',
  ])

  const ws = XLSX.utils.aoa_to_sheet([headers, ...dataRows])
  const wb = XLSX.utils.book_new()
  const secName = getSection1Name(selectedFittingBaselineSection1Id.value) || '标段'
  XLSX.utils.book_append_sheet(wb, ws, `${secName}管件基准量`)
  XLSX.writeFile(wb, `${secName}_管件设计与采购量台账.xlsx`)
}

const summaryLoading = ref(false)
const summaryError = ref('')
const summaryRows = ref([])

const deliveriesLoading = ref(false)
const deliveriesError = ref('')
const deliveryRows = ref([])
const allDeliveryRows = ref([])
const showExportModal = ref(false)
const exportColumns = computed(() => [
  { key: 'deliveryCode', label: '订单号' },
  { key: 'shipmentNo', label: '运输车次号' },
  { key: 'vehiclePlateNo', label: '车牌号' },
  { key: 'supplyEntityName', label: '供给主体' },
  { key: 'section1Name', label: `装车接收${modeLabels.value.section1}` },
  { key: 'pipeModelName', label: '保温管规格型号' },
  { key: 'shippedQty', label: '发货量（米）' },
  { key: 'arrivedQty', label: '到货量（米）' },
  { key: 'receivedQty', label: '接收量（米）' },
  { key: 'shippedAtDisplay', label: '发货时间' },
  { key: 'statusLabel', label: '状态' },
  { key: 'shipRemark', label: '备注' }
])
const cancelLoadingIds = ref({})
const nowTick = ref(Date.now())
let nowTimer = null

const submitDeliveryLoading = ref(false)
const actionMessage = ref(null)
const draftDeliveryItems = ref([])

const deliveryForm = ref(createDefaultDeliveryForm())

const canSubmitCurrentProject = computed(() => auth.canSubmitFor(PROJECT_KEY))
const canSwitchSupplyEntity = computed(() => ['Global_admin', 'tube_supplier_admin'].includes(currentGroup.value))
const isReadOnlyViewer = computed(() => {
  const g1 = String(currentGroup.value || '').trim().toLowerCase()
  const g2 = String(auth.user?.group || auth.session?.group || '').trim().toLowerCase()
  const u1 = String(auth.user?.username || auth.session?.username || '').trim().toLowerCase()
  
  const viewerGroups = new Set(['tube_global_viewer', 'tube_viewer', 'group_viewer', 'viewer'])
  const viewerUsers = new Set(['tube_viewer', 'viewer', 'guest'])
  
  return viewerGroups.has(g1) || viewerGroups.has(g2) || viewerUsers.has(u1)
})

const switchToCustomMode = () => {
  isCustomInputMode.value = true
  customEntityInput.value = ''
}

const cancelCustomMode = () => {
  isCustomInputMode.value = false
  customEntityInput.value = ''
}

const applyCustomEntityInput = async () => {
  const val = customEntityInput.value.trim()
  if (!val) {
    alert('请输入有效的供给主体名称')
    return
  }
  try {
    const res = await createCustomSupplyEntity(PROJECT_KEY, { entity_name: val })
    if (res && res.entity) {
      selectedSupplyEntityId.value = res.entity.entity_id || val
    } else {
      selectedSupplyEntityId.value = val
    }
  } catch (err) {
    console.warn('持久化保存自定义供给主体失败，已降级为临时视图模式:', err)
    selectedSupplyEntityId.value = val
  }
  isCustomInputMode.value = false
  handleGlobalSupplyEntityChange(selectedSupplyEntityId.value)
  // 重新刷新全局配置 options
  loadOptions()
}

const handleSelectSupplyEntityChange = (val) => {
  if (val === '__ENTER_CUSTOM_MODE__') {
    switchToCustomMode()
    return
  }
  handleGlobalSupplyEntityChange(val)
}

const handleGlobalSupplyEntityChange = (newVal) => {
  selectedSupplyEntityId.value = newVal
  deliveryForm.value.supplyEntityId = newVal
  loadDemandSummary()
  loadDeliveries()
  loadFittingDeliveries()
}

const currentGroupLabel = computed(() => {
  if (!currentGroup.value) return '未识别'
  if (currentGroup.value === 'Global_admin') return '全局管理员'
  if (currentGroup.value === 'tube_supplier_admin') return '供给方管理员'
  if (currentGroup.value === 'tube_supplier') return '供给主体'
  return currentGroup.value
})

const currentSupplyEntityLabel = computed(() => {
  const matched = allSupplyEntityOptions.value.find((item) => item.entity_id === selectedSupplyEntityId.value)
  return matched?.entity_name || selectedSupplyEntityId.value || '未识别'
})

const currentDeliverySupplyEntityLabel = computed(() => {
  const matched = allSupplyEntityOptions.value.find((item) => item.entity_id === deliveryForm.value.supplyEntityId)
  return matched?.entity_name || deliveryForm.value.supplyEntityId || currentSupplyEntityLabel.value
})

const currentShipmentDisplay = computed(() => {
  if (deliveryForm.value.reuseCurrentShipment && deliveryForm.value.shipmentNo) {
    return deliveryForm.value.shipmentNo
  }
  return '提交后由系统自动生成'
})

const currentReusedShipmentRow = computed(() => {
  if (!deliveryForm.value.reuseCurrentShipment || !deliveryForm.value.shipmentNo) {
    return null
  }
  return deliveryRows.value.find((row) => row.shipmentNo === deliveryForm.value.shipmentNo) || null
})

const currentReusedShipmentPlateLocked = computed(() => Boolean(currentReusedShipmentRow.value?.vehiclePlateNo))

const deliveryOrderNoPreview = computed(() => '提交后由系统自动生成')

const currentAssignedSection1Ids = computed(() => {
  const entity = allSupplyEntityOptions.value.find((item) => item.entity_id === selectedSupplyEntityId.value)
  if (entity && Array.isArray(entity.section_1_ids) && entity.section_1_ids.length > 0) {
    return new Set(entity.section_1_ids)
  }
  return new Set(section1Options.value.map((s) => s.section_1_id))
})

const currentAssignedSection1Options = computed(() => {
  const allowedSet = currentAssignedSection1Ids.value
  return section1Options.value.filter((s) => allowedSet.has(s.section_1_id))
})

function parsePipeModelDiameters(modelCode) {
  if (!modelCode) return { main: 0, outer: 0 }
  const str = String(modelCode).trim()
  const parts = str.split('/')
  const leftStr = parts[0] || ''
  const rightStr = parts[1] || ''
  const leftMatch = leftStr.match(/(?:[ΦφDN])?\s*(\d+(?:\.\d+)?)/i)
  const rightMatch = rightStr.match(/(?:[ΦφDN])?\s*(\d+(?:\.\d+)?)/i)
  const main = leftMatch ? parseFloat(leftMatch[1]) || 0 : 0
  const outer = rightMatch ? parseFloat(rightMatch[1]) || 0 : 0
  return { main, outer }
}

function sortPipeModelsByDiameterDesc(modelList) {
  return [...modelList].sort((a, b) => {
    const codeA = a.pipe_model_id || a.pipe_model_name
    const codeB = b.pipe_model_id || b.pipe_model_name
    const dA = parsePipeModelDiameters(codeA)
    const dB = parsePipeModelDiameters(codeB)
    if (dB.main !== dA.main) {
      return dB.main - dA.main
    }
    if (dB.outer !== dA.outer) {
      return dB.outer - dA.outer
    }
    return String(codeA || '').localeCompare(String(codeB || ''))
  })
}

const fullPipeModelOptions = computed(() => {
  const modelMap = new Map()
  allPipeModelOptions.value.forEach((item) => {
    if (item && item.pipe_model_id) {
      modelMap.set(item.pipe_model_id, item)
    }
  })
  summaryRows.value.forEach((row) => {
    if (row && row.pipeModelId && !modelMap.has(row.pipeModelId)) {
      modelMap.set(row.pipeModelId, {
        pipe_model_id: row.pipeModelId,
        pipe_model_name: row.pipeModelName || row.pipeModelId,
        unit: '米',
      })
    }
  })
  return Array.from(modelMap.values())
})

const currentAssignedPipeModelIds = computed(() => {
  const allowedSections = currentAssignedSection1Ids.value
  const modelSet = new Set()
  summaryRows.value.forEach((row) => {
    if (allowedSections.has(row.section1Id) && row.pipeModelId) {
      modelSet.add(row.pipeModelId)
    }
  })
  return modelSet
})

const pipeModelOptions = computed(() => {
  const allowedSet = currentAssignedPipeModelIds.value
  const unfiltered = fullPipeModelOptions.value.filter((item) => allowedSet.has(item.pipe_model_id))
  return sortPipeModelsByDiameterDesc(unfiltered)
})

const deliveryFormPipeModelOptions = computed(() => {
  // 发货选择中展示当前供给主体管辖水质标段的全量型号并集（按管径从大到小严格排列）
  return pipeModelOptions.value
})

const supplyDemandViewOptions = computed(() => [
  { value: 'summary', label: '整理汇总' },
  ...currentAssignedSection1Options.value.map((section1) => ({
    value: section1.section_1_id,
    label: section1.section_1_name,
  })),
])

const activePipeModelIds = computed(() => {
  if (!selectedPipeModelIds.value.length) {
    return pipeModelOptions.value.map((item) => item.pipe_model_id)
  }
  return selectedPipeModelIds.value
})

const selectedPipeModelSummaryLabel = computed(() => {
  const total = pipeModelOptions.value.length
  const selectedCount = activePipeModelIds.value.length
  if (!total || selectedCount === total) {
    return '全部型号'
  }
  if (selectedCount === 1) {
    const matched = pipeModelOptions.value.find((item) => item.pipe_model_id === activePipeModelIds.value[0])
    return matched?.pipe_model_name || '已选1个型号'
  }
  return `已选${selectedCount}个型号`
})

const pipeModelFilteredSummaryRows = computed(() => {
  const activeIds = new Set(activePipeModelIds.value)
  return summaryRows.value.filter((row) => activeIds.has(row.pipeModelId))
})

const filteredSummaryRows = computed(() => {
  const allowedSectionIds = currentAssignedSection1Ids.value
  const assignedRows = pipeModelFilteredSummaryRows.value.filter((row) => allowedSectionIds.has(row.section1Id))
  if (supplyDemandViewMode.value === 'summary') {
    return assignedRows
  }
  return assignedRows.filter((row) => row.section1Id === supplyDemandViewMode.value)
})

const getSection1Pos = (section1Id) => {
  const idx = section1Options.value.findIndex(item => item.section_1_id === section1Id)
  return idx === -1 ? 9999 : idx
}

const getPipeModelPos = (pipeModelId) => {
  const idx = pipeModelOptions.value.findIndex(item => item.pipe_model_id === pipeModelId)
  return idx === -1 ? 9999 : idx
}

const aggregatedSummaryRows = computed(() => {
  const grouped = new Map()
  filteredSummaryRows.value.forEach((row) => {
    const existing = grouped.get(row.pipeModelId) || {
      rowKey: `summary-${row.pipeModelId}`,
      scopeLabel: '汇总',
      pipeModelId: row.pipeModelId,
      pipeModelName: row.pipeModelName,
      designQty: 0,
      purchasePlanQty: 0,
      futurePlanQty: 0,
      pendingArrivalQty: 0,
      pendingReceiveQty: 0,
      pendingWarehouseQty: 0,
      netGapQty: 0,
    }
    existing.designQty += Number(row.designQty || 0)
    existing.purchasePlanQty += Number(row.purchasePlanQty || 0)
    existing.futurePlanQty += Number(row.futurePlanQty || 0)
    existing.pendingArrivalQty += Number(row.pendingArrivalQty || 0)
    existing.pendingReceiveQty += Number(row.pendingReceiveQty || 0)
    existing.pendingWarehouseQty += Number(row.pendingWarehouseQty || 0)
    existing.netGapQty += Number(row.netGapQty || 0)
    grouped.set(row.pipeModelId, existing)
  })
  return Array.from(grouped.values()).sort((a, b) => getPipeModelPos(a.pipeModelId) - getPipeModelPos(b.pipeModelId))
})

const supplyDemandTableRows = computed(() => {
  if (supplyDemandViewMode.value === 'summary') {
    return aggregatedSummaryRows.value
  }
  const list = filteredSummaryRows.value.map((row) => ({
    ...row,
    rowKey: `${row.section1Id}-${row.pipeModelId}`,
    scopeLabel: row.section1Name,
  }))
  return list.sort((a, b) => {
    const section1Diff = getSection1Pos(a.section1Id) - getSection1Pos(b.section1Id)
    if (section1Diff !== 0) {
      return section1Diff
    }
    return getPipeModelPos(a.pipeModelId) - getPipeModelPos(b.pipeModelId)
  })
})

const supplyDemandTableHint = computed(() => {
  const entityName = currentSupplyEntityLabel.value || '当前供给主体'
  if (supplyDemandViewMode.value === 'summary') {
    return `当前以“整理汇总”方式按型号统计【${entityName}】所辖需求主体的各项供需合计。计量单位：米。`
  }
  const matched = section1Options.value.find((item) => item.section_1_id === supplyDemandViewMode.value)
  return `当前仅展示 ${matched?.section_1_name || '所选需求主体'} 的各型号供需记录。计量单位：米。`
})

function createDefaultDeliveryForm() {
  return {
    supplyEntityId: '',
    section1Id: '',
    pipeModelId: '',
    shipmentNo: '',
    vehiclePlateNo: '',
    reuseCurrentShipment: false,
    shippedQty: 0,
    shipContactName: '',
    shipContactPhone: '',
    shipRemark: '',
    customShippedAt: '',
  }
}

function getSection1Name(section1Id) {
  const matched = section1Options.value.find((item) => item.section_1_id === section1Id)
  return matched?.section_1_name || section1Id || '—'
}

function getSectionLabel(section1Id) {
  return getSection1Name(section1Id)
}

function getPipeModelName(pipeModelId) {
  const matched = pipeModelOptions.value.find((item) => item.pipe_model_id === pipeModelId)
  return matched?.pipe_model_name || pipeModelId || '—'
}

function clearActionMessage() {
  actionMessage.value = null
}

function setActionMessage(type, text) {
  actionMessage.value = { type, text }
}

function selectAllPipeModels() {
  selectedPipeModelIds.value = pipeModelOptions.value.map((item) => item.pipe_model_id)
}

function clearPipeModelSelection() {
  selectedPipeModelIds.value = []
}

function formatNumber(value) {
  const numeric = Number(value ?? 0)
  if (!Number.isFinite(numeric)) return '0'
  if (Math.abs(numeric - Math.round(numeric)) < 0.0001) return String(Math.round(numeric))
  return numeric.toFixed(2)
}

function formatNullableNumber(value) {
  if (value === null || value === undefined || value === '') return '—'
  return formatNumber(value)
}

function toDateTimeLocalString(input) {
  const source = input instanceof Date ? input : new Date(input)
  if (Number.isNaN(source.getTime())) return ''
  const pad = (value) => String(value).padStart(2, '0')
  return `${source.getFullYear()}-${pad(source.getMonth() + 1)}-${pad(source.getDate())}T${pad(source.getHours())}:${pad(source.getMinutes())}`
}

function formatDateTimeDisplay(value) {
  if (!value) return ''
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    const normalized = String(value).replace('T', ' ')
    return normalized.slice(0, 16)
  }
  return toDateTimeLocalString(parsed).replace('T', ' ')
}

function normalizeOptionsPayload(response) {
  return {
    currentGroup: response.user?.group || '',
    supplyEntities: response.supply_entities || [],
    section_1s: response.section_1s || [],
    pipeModels: response.pipe_models || [],
    showDate: response.show_date || response.biz_date || '',
    planStartDate: response.plan_start_date || '',
    currentSupplyEntityIds: response.current_supply_entity_ids || [],
  }
}

function normalizeSummaryRows(rows) {
  return (rows || []).map((row) => ({
    section1Id: row.section_1_id || '',
    section1Name: row.section_1_name || row.section_1_id || '未命名需求主体',
    pipeModelId: row.pipe_model_id || '',
    pipeModelName: row.pipe_model_name || row.pipe_model_id || '未命名型号',
    designQty: Number(row.design_qty ?? 0),
    purchasePlanQty: Number(row.purchase_plan_qty ?? 0),
    futurePlanQty: Number(row.future_plan_qty ?? 0),
    pendingArrivalQty: Number(row.pending_arrival_qty ?? 0),
    pendingReceiveQty: Number(row.pending_receive_qty ?? 0),
    pendingWarehouseQty: Number(row.pending_warehouse_qty ?? 0),
    netGapQty: Number(row.net_gap_qty ?? 0),
  }))
}

function getStatusLabel(status) {
  return getDeliveryStatus(status).label
}

function normalizeDeliveryRows(rows) {
  return (rows || []).map((row) => ({
    deliveryId: Number(row.id ?? 0),
    deliveryCode: row.order_no || row.delivery_code || `DEL-${String(row.id ?? '').padStart(5, '0')}`,
    orderNo: row.order_no || row.delivery_code || '',
    shipmentNo: row.shipment_no || '',
    vehiclePlateNo: row.vehicle_plate_no || '',
    supplyEntityId: row.supply_entity_id || '',
    supplyEntityName: row.supply_entity_name || row.supply_entity_id || '—',
    section1Id: row.section_1_id || '',
    section1Name: row.section_1_name || row.section_1_id || '—',
    pipeModelId: row.pipe_model_id || '',
    pipeModelName: row.pipe_model_name || row.pipe_model_id || '—',
    shippedQty: Number(row.shipped_qty ?? 0),
    arrivedQty: row.arrived_qty == null ? null : Number(row.arrived_qty),
    receivedQty: row.received_qty == null ? null : Number(row.received_qty),
    shippedAt: row.shipped_at || '',
    shippedAtDisplay: formatDateTimeDisplay(row.shipped_at || ''),
    deliveryElapsedLabel: row.delivery_elapsed_label || '',
    shipContactName: row.ship_contact_name || '',
    shipContactPhone: row.ship_contact_phone || '',
    shipRemark: row.ship_remark || '',
    status: row.status || '',
    statusLabel: getStatusLabel(row.status || ''),
    abnormalFlag: Boolean(row.abnormal_flag),
    cancelReason: row.cancel_reason || '',
    arrivedConfirmBy: row.arrived_confirm_by || '',
    arrivedConfirmName: row.arrived_confirm_name || '',
    arrivedConfirmPhone: row.arrived_confirm_phone || '',
    arrivedConfirmAt: row.arrived_confirm_at || '',
    arrivedRemark: row.arrived_remark || '',
    receivedConfirmBy: row.received_confirm_by || '',
    receivedConfirmName: row.received_confirm_name || '',
    receivedConfirmPhone: row.received_confirm_phone || '',
    receivedConfirmAt: row.received_confirm_at || '',
    receivedRemark: row.received_remark || '',
    createdBy: row.created_by || '',
    diffApproveBy: row.diff_approve_by || '',
    diffApproveAt: row.diff_approve_at || '',
    diffApproveRemark: row.diff_approve_remark || '',
    warehouseConfirmBy: row.warehouse_confirm_by || '',
    warehouseConfirmName: row.warehouse_confirm_name || '',
    warehouseConfirmPhone: row.warehouse_confirm_phone || '',
    warehouseConfirmAt: row.warehouse_confirm_at || '',
    warehouseRemark: row.warehouse_remark || '',
    isTimeoutReceive: Boolean(row.is_timeout_receive),
    updatedBy: row.updated_by || '',
    updatedAt: row.updated_at || '',
  }))
}

function getAbnormalLabel(row) {
  if (!row?.abnormalFlag) return ''
  if (row.receivedQty != null && row.arrivedQty != null && Number(row.receivedQty) < Number(row.arrivedQty)) {
    return '少接收'
  }
  if (row.arrivedQty != null && Number(row.arrivedQty) < Number(row.shippedQty || 0)) {
    return '少到货'
  }
  return '异常'
}

function buildCurrentDraftItem() {
  return {
    section1Id: deliveryForm.value.section1Id || '',
    section1Name: getSection1Name(deliveryForm.value.section1Id),
    pipeModelId: deliveryForm.value.pipeModelId || '',
    pipeModelName: getPipeModelName(deliveryForm.value.pipeModelId),
    shippedQty: Number(deliveryForm.value.shippedQty || 0),
    shipRemark: deliveryForm.value.shipRemark || '',
  }
}

function validateCurrentDeliveryForm() {
  if (!deliveryForm.value.supplyEntityId || !deliveryForm.value.section1Id || !deliveryForm.value.pipeModelId) {
    setActionMessage('error', `请先完整选择供给主体、${modeLabels.value.section1}和保温管型号。`)
    return false
  }
  if (Number(deliveryForm.value.shippedQty || 0) <= 0) {
    setActionMessage('error', '发货量必须大于 0。')
    return false
  }
  return true
}

async function loadOptions() {
  optionsLoading.value = true
  optionsError.value = ''
  try {
    const response = await getTubeSupplyManagementOptions(PROJECT_KEY)
    const normalized = normalizeOptionsPayload(response)
    currentGroup.value = normalized.currentGroup
    supplyEntityOptions.value = normalized.supplyEntities
    section1Options.value = normalized.section_1s
    allPipeModelOptions.value = normalized.pipeModels
    currentSupplyEntityIds.value = normalized.currentSupplyEntityIds
    showDate.value = normalized.showDate
    planStartDate.value = normalized.planStartDate
    if (response && response.fitting_config) {
      if (Array.isArray(response.fitting_config.allowed_units) && response.fitting_config.allowed_units.length) {
        allowedFittingUnits.value = response.fitting_config.allowed_units
      }
      if (Array.isArray(response.fitting_config.standard_types) && response.fitting_config.standard_types.length) {
        standardFittingTypes.value = response.fitting_config.standard_types
      }
    }
    const availableSupplyEntityIds = [
      ...normalized.currentSupplyEntityIds,
      ...customSupplyEntities.value.map((c) => c.entity_id),
    ]
    if (!availableSupplyEntityIds.includes(selectedSupplyEntityId.value)) {
      selectedSupplyEntityId.value = availableSupplyEntityIds[0] || ''
    } else if (!canSwitchSupplyEntity.value && normalized.currentSupplyEntityIds.length) {
      selectedSupplyEntityId.value = normalized.currentSupplyEntityIds[0]
    } else if (!selectedSupplyEntityId.value && normalized.currentSupplyEntityIds.length) {
      selectedSupplyEntityId.value = normalized.currentSupplyEntityIds[0]
    }
    if (!canSwitchSupplyEntity.value && selectedSupplyEntityId.value) {
      deliveryForm.value.supplyEntityId = selectedSupplyEntityId.value
    } else if (!deliveryForm.value.supplyEntityId && selectedSupplyEntityId.value) {
      deliveryForm.value.supplyEntityId = selectedSupplyEntityId.value
    }
    const section1IdSet = new Set(section1Options.value.map((item) => String(item.section_1_id || '')))
    const pipeModelIdSet = new Set(pipeModelOptions.value.map((item) => String(item.pipe_model_id || '')))
    if (!section1IdSet.has(deliveryForm.value.section1Id)) {
      deliveryForm.value.section1Id = section1Options.value[0]?.section_1_id || ''
    }
    if (!pipeModelIdSet.has(deliveryForm.value.pipeModelId)) {
      deliveryForm.value.pipeModelId = pipeModelOptions.value[0]?.pipe_model_id || ''
    }
    selectedPipeModelIds.value = selectedPipeModelIds.value.filter((item) => pipeModelIdSet.has(String(item || '')))
    if (!selectedPipeModelIds.value.length) {
      selectAllPipeModels()
    }
  } catch (error) {
    optionsError.value = error?.message || '读取供给侧配置失败'
  } finally {
    optionsLoading.value = false
  }
}

async function loadDemandSummary() {
  summaryLoading.value = true
  summaryError.value = ''
  try {
    const response = await getTubeSupplyManagementDemandSummary(PROJECT_KEY)
    summaryRows.value = normalizeSummaryRows(response.rows)
  } catch (error) {
    summaryError.value = error?.message || '读取供给侧需求汇总失败'
    summaryRows.value = []
  } finally {
    summaryLoading.value = false
  }
}

async function refreshRealtimeConfig() {
  await loadOptions()
  await Promise.all([loadDemandSummary(), loadDeliveries(), loadFittingDeliveries()])
}

async function loadDeliveries() {
  deliveriesLoading.value = true
  deliveriesError.value = ''
  try {
    const response = await getTubeSupplyManagementDeliveries(PROJECT_KEY, {
      supplyEntityId: selectedSupplyEntityId.value,
    })
    deliveryRows.value = normalizeDeliveryRows(response.rows)
    allDeliveryRows.value = [...deliveryRows.value]
  } catch (error) {
    deliveriesError.value = error?.message || '读取供给侧发货记录失败'
    deliveryRows.value = []
  } finally {
    deliveriesLoading.value = false
  }
}

function appendDraftDelivery() {
  if (!validateCurrentDeliveryForm()) {
    return
  }
  draftDeliveryItems.value = [...draftDeliveryItems.value, buildCurrentDraftItem()]
  deliveryForm.value.section1Id = ''
  deliveryForm.value.pipeModelId = ''
  deliveryForm.value.shippedQty = 0
  deliveryForm.value.shipRemark = ''
  setActionMessage('success', `已加入当前车次，待提交明细共 ${draftDeliveryItems.value.length} 条。`)
}

function removeDraftDelivery(index) {
  draftDeliveryItems.value = draftDeliveryItems.value.filter((_, itemIndex) => itemIndex !== index)
}

async function submitDeliveryBatch() {
  if (!draftDeliveryItems.value.length) {
    setActionMessage('error', '请先将发货明细加入当前车次，再提交当前车次。')
    return
  }
  const items = draftDeliveryItems.value.map((item) => ({
    section_1_id: item.section1Id,
    pipe_model_id: item.pipeModelId,
    shipped_qty: Number(item.shippedQty || 0),
    ship_remark: item.shipRemark || '',
  }))
  submitDeliveryLoading.value = true
  clearActionMessage()
  try {
    const customAt = deliveryForm.value.customShippedAt
    const submittedAt = customAt ? new Date(customAt) : new Date()
    const response = await createTubeSupplyManagementDeliveryBatch(PROJECT_KEY, {
      supply_entity_id: deliveryForm.value.supplyEntityId,
      shipment_no: deliveryForm.value.reuseCurrentShipment ? deliveryForm.value.shipmentNo || '' : '',
      vehicle_plate_no: deliveryForm.value.vehiclePlateNo || '',
      shipped_at: submittedAt.toISOString(),
      ship_contact_name: deliveryForm.value.shipContactName || '',
      ship_contact_phone: deliveryForm.value.shipContactPhone || '',
      items,
    })
    const shipmentNo = response?.shipment_no || response?.shipmentNo || ''
    const shipmentVerb = response?.shipment_reused || response?.shipmentReused ? '沿用车次' : '新建车次'
    const createdRows = Array.isArray(response?.rows) ? response.rows : []
    setActionMessage(
      'success',
      `当前车次已提交 ${createdRows.length || items.length} 条明细，${shipmentVerb}${shipmentNo ? `：${shipmentNo}` : ''}。`
    )
    const currentSupplyEntityId = deliveryForm.value.supplyEntityId
    const nextForm = createDefaultDeliveryForm()
    nextForm.supplyEntityId = currentSupplyEntityId
    nextForm.shipContactName = deliveryForm.value.shipContactName || ''
    nextForm.shipContactPhone = deliveryForm.value.shipContactPhone || ''
    deliveryForm.value = nextForm
    deliveryForm.value.supplyEntityId = currentSupplyEntityId
    draftDeliveryItems.value = []
    await Promise.all([loadDemandSummary(), loadDeliveries()])
  } catch (error) {
    setActionMessage('error', error?.message || '提交当前车次失败')
  } finally {
    submitDeliveryLoading.value = false
  }
}

function isReusingShipment(row) {
  return Boolean(
    row?.shipmentNo &&
    deliveryForm.value.reuseCurrentShipment &&
    deliveryForm.value.shipmentNo &&
    deliveryForm.value.shipmentNo === row.shipmentNo
  )
}

function ensureShipmentSwitchAllowed(nextShipmentNo = '') {
  if (!draftDeliveryItems.value.length) {
    return true
  }
  const currentShipmentNo = deliveryForm.value.reuseCurrentShipment ? deliveryForm.value.shipmentNo || '' : ''
  if ((currentShipmentNo || '') === (nextShipmentNo || '')) {
    return true
  }
  setActionMessage('error', '当前车次已有待提交明细，请先提交或移除后再切换车次。')
  return false
}

function toggleShipmentReuse(row) {
  if (!row?.shipmentNo) return
  if (isReusingShipment(row)) {
    if (!ensureShipmentSwitchAllowed('')) {
      return
    }
    deliveryForm.value.reuseCurrentShipment = false
    deliveryForm.value.shipmentNo = ''
    deliveryForm.value.vehiclePlateNo = ''
    setActionMessage('success', '已取消继续车次，下一次提交将自动新建运输车次号。')
    return
  }
  if (!ensureShipmentSwitchAllowed(row.shipmentNo)) {
    return
  }
  deliveryForm.value.supplyEntityId = row.supplyEntityId || deliveryForm.value.supplyEntityId
  deliveryForm.value.shipmentNo = row.shipmentNo
  deliveryForm.value.vehiclePlateNo = row.vehiclePlateNo || ''
  deliveryForm.value.reuseCurrentShipment = true
  setActionMessage('success', `已切换为继续该车次 ${row.shipmentNo}。`)
}

async function cancelDelivery(row) {
  if (!row?.deliveryId) return
  const identifier = row.orderNo || row.deliveryCode || row.shipmentNo || row.deliveryId
  clearActionMessage()
  cancelModalState.value = {
    visible: true,
    type: 'pipe_delivery',
    title: '直管发货记录撤销确认',
    targetDesc: `发货单号：${identifier}（车牌：${row.vehiclePlateNo || '—'}，型号：${row.pipeModelName || '—'}，发货量：${formatNumber(row.shippedQty)} ${row.unit || '米'}）`,
    reason: '',
    loading: false,
    errorMsg: '',
    payload: { row, identifier },
  }
}

function handleSupplyEntityChange(value) {
  if (!value) return
  if (canSwitchSupplyEntity.value) {
    selectedSupplyEntityId.value = value
    loadDeliveries()
  } else {
    deliveryForm.value.supplyEntityId = selectedSupplyEntityId.value
  }
}

watch(selectedSupplyEntityId, (value) => {
  if (value) {
    deliveryForm.value.supplyEntityId = value
    fittingForm.value.supplyEntityId = value
    const matchedEntity = allSupplyEntityOptions.value.find((item) => item.entity_id === value)
    if (matchedEntity) {
      deliveryForm.value.shipContactName = matchedEntity.contact_name || ''
      deliveryForm.value.shipContactPhone = matchedEntity.contact_phone || ''
      fittingForm.value.shipContactName = matchedEntity.contact_name || ''
      fittingForm.value.shipContactPhone = matchedEntity.contact_phone || ''
    }
    const validValues = new Set(supplyDemandViewOptions.value.map((opt) => opt.value))
    if (!validValues.has(supplyDemandViewMode.value)) {
      supplyDemandViewMode.value = 'summary'
    }
    const validSectionIds = currentAssignedSection1Ids.value
    if (!validSectionIds.has(deliveryForm.value.section1Id)) {
      deliveryForm.value.section1Id = currentAssignedSection1Options.value[0]?.section_1_id || ''
    }
    if (!validSectionIds.has(fittingForm.value.section1Id)) {
      fittingForm.value.section1Id = currentAssignedSection1Options.value[0]?.section_1_id || ''
    }
    if (!validSectionIds.has(selectedFittingBaselineSection1Id.value)) {
      selectedFittingBaselineSection1Id.value = currentAssignedSection1Options.value[0]?.section_1_id || ''
    }
    if (fittingTableSectionFilter.value && !validSectionIds.has(fittingTableSectionFilter.value)) {
      fittingTableSectionFilter.value = ''
    }
    loadDeliveries()
    loadFittingDeliveries()
    if (activeTab.value === 'fitting_baseline') {
      loadFittingBaseline()
    }
  } else {
    fittingDeliveries.value = []
  }
})

watch(
  currentAssignedSection1Options,
  (options) => {
    if (!options || !options.length) {
      selectedFittingBaselineSection1Id.value = ''
      return
    }
    const validIds = new Set(options.map((s) => s.section_1_id))
    if (!selectedFittingBaselineSection1Id.value || !validIds.has(selectedFittingBaselineSection1Id.value)) {
      selectedFittingBaselineSection1Id.value = options[0]?.section_1_id || ''
      if (activeTab.value === 'fitting_baseline') {
        loadFittingBaseline()
      }
    }
  },
  { immediate: true }
)

watch(
  deliveryFormPipeModelOptions,
  (options) => {
    if (!options || !options.length) {
      deliveryForm.value.pipeModelId = ''
      return
    }
    const validIds = new Set(options.map((item) => item.pipe_model_id))
    if (!validIds.has(deliveryForm.value.pipeModelId)) {
      deliveryForm.value.pipeModelId = options[0]?.pipe_model_id || ''
    }
  },
  { immediate: true }
)

watch(
  pipeModelOptions,
  (options) => {
    if (!options || !options.length) {
      selectedPipeModelIds.value = []
      return
    }
    const validIds = new Set(options.map((item) => item.pipe_model_id))
    const currentSelected = selectedPipeModelIds.value.filter((id) => validIds.has(id))
    if (currentSelected.length === 0 || currentSelected.length !== selectedPipeModelIds.value.length) {
      selectedPipeModelIds.value = currentSelected.length > 0 ? currentSelected : options.map((item) => item.pipe_model_id)
    }
  },
  { immediate: true }
)

function formatElapsedLabel(shippedAt) {
  if (!shippedAt) return ''
  const start = new Date(shippedAt)
  if (Number.isNaN(start.getTime())) return ''
  const diffMs = Math.max(nowTick.value - start.getTime(), 0)
  const totalSeconds = Math.floor(diffMs / 1000)
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  if (days > 0) return `${days}天${hours}小时${minutes}分`
  if (hours > 0) return `${hours}小时${minutes}分`
  if (minutes > 0) return `${minutes}分`
  return `${totalSeconds}秒`
}

function formatDeliveryElapsedDisplay(row) {
  if (!row || row.status === 'cancelled') return '—'
  return row.deliveryElapsedLabel || formatElapsedLabel(row.shippedAt) || '—'
}

onMounted(async () => {
  nowTimer = setInterval(() => {
    nowTick.value = Date.now()
  }, 60000)
  document.addEventListener('click', closeFittingDropdown)
  await refreshRealtimeConfig()
})

onBeforeUnmount(() => {
  if (nowTimer) {
    clearInterval(nowTimer)
    nowTimer = null
  }
  document.removeEventListener('click', closeFittingDropdown)
})

const showSuperEditModal = ref(false)
const superEditSaving = ref(false)
const superEditError = ref('')
const superEditForm = ref({
  deliveryId: 0,
  section1Id: '',
  pipeModelId: '',
  shippedQty: 0,
  shippedAt: '',
  vehiclePlateNo: '',
  shipRemark: '',
  status: '',
  orderNo: '',
  shipmentNo: '',
  arrivedQty: null,
  receivedQty: null,
  arrivedConfirmAt: '',
  receivedConfirmAt: '',
  warehouseConfirmAt: '',
})

const showSuperEditFittingModal = ref(false)
const superEditFittingSaving = ref(false)
const superEditFittingError = ref('')
const superEditFittingForm = ref({
  deliveryId: 0,
  section1Id: '',
  supplyEntityId: '',
  fittingType: '',
  modelSpec: '',
  shippedQty: 1,
  unit: '个',
  shippedAt: '',
  vehiclePlateNo: '',
  shipContactName: '',
  shipContactPhone: '',
  shipRemark: '',
  status: 'pending_arrival',
  orderNo: '',
  shipmentNo: '',
  arrivedQty: null,
  arrivedConfirmAt: '',
  arrivedConfirmBy: '',
  arrivedRemark: '',
  receivedConfirmAt: '',
  receivedConfirmBy: '',
  receivedRemark: '',
  warehouseConfirmAt: '',
  warehouseConfirmBy: '',
  warehouseRemark: '',
  cancelAt: '',
  cancelBy: '',
  cancelReason: '',
})

function formatToDatetimeLocal(isoString) {
  if (!isoString) return ''
  try {
    const d = new Date(isoString)
    if (isNaN(d.getTime())) return ''
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const date = String(d.getDate()).padStart(2, '0')
    const hours = String(d.getHours()).padStart(2, '0')
    const minutes = String(d.getMinutes()).padStart(2, '0')
    return `${year}-${month}-${date}T${hours}:${minutes}`
  } catch (e) {
    return ''
  }
}

function smartAlignSuperTimestamps() {
  if (!superEditForm.value.shippedAt) return
  try {
    const shippedTime = new Date(superEditForm.value.shippedAt).getTime()
    if (isNaN(shippedTime)) return
    
    // 按照 12小时、6小时、2小时的等距分布进行智能凭证补录与物理顺序防呆自动对齐
    const arrivedTime = new Date(shippedTime + 12 * 60 * 60 * 1000)
    const receivedTime = new Date(arrivedTime.getTime() + 6 * 60 * 60 * 1000)
    const warehouseTime = new Date(receivedTime.getTime() + 2 * 60 * 60 * 1000)
    
    const formatTimeObj = (d) => {
      const year = d.getFullYear()
      const month = String(d.getMonth() + 1).padStart(2, '0')
      const date = String(d.getDate()).padStart(2, '0')
      const hours = String(d.getHours()).padStart(2, '0')
      const minutes = String(d.getMinutes()).padStart(2, '0')
      return `${year}-${month}-${date}T${hours}:${minutes}`
    }
    
    superEditForm.value.arrivedConfirmAt = formatTimeObj(arrivedTime)
    superEditForm.value.receivedConfirmAt = formatTimeObj(receivedTime)
    superEditForm.value.warehouseConfirmAt = formatTimeObj(warehouseTime)
    
    // 数量也自动按照发货量进行防漏对齐
    const shipQty = Number(superEditForm.value.shippedQty || 0)
    if (!superEditForm.value.arrivedQty || superEditForm.value.arrivedQty === '') {
      superEditForm.value.arrivedQty = shipQty
    }
    if (!superEditForm.value.receivedQty || superEditForm.value.receivedQty === '') {
      superEditForm.value.receivedQty = superEditForm.value.arrivedQty
    }
  } catch (e) {
    console.error('智能时间自动对齐失败:', e)
  }
}

const STATUS_RANK = {
  'pending_arrival': 0,
  'shipped': 0,
  'pending_receive': 1,
  'arrived': 1,
  'pending_diff_approve': 1.5,
  'pending_warehouse': 2,
  'received': 2,
  'completed': 3,
  'cancelled': -1,
}

let origSuperEditSnap = {
  status: '',
  rank: 0,
  arrivedConfirmAt: '',
  receivedConfirmAt: '',
  warehouseConfirmAt: '',
}

function openSuperEdit(row) {
  superEditError.value = ''
  
  const arrivedAt = formatToDatetimeLocal(row.arrivedConfirmAt)
  const receivedAt = formatToDatetimeLocal(row.receivedConfirmAt)
  const warehouseAt = formatToDatetimeLocal(row.warehouseConfirmAt)
  const st = row.status || 'pending_arrival'

  origSuperEditSnap = {
    status: st,
    rank: STATUS_RANK[st] ?? 0,
    arrivedConfirmAt: arrivedAt,
    receivedConfirmAt: receivedAt,
    warehouseConfirmAt: warehouseAt,
  }

  superEditForm.value = {
    deliveryId: row.deliveryId,
    section1Id: row.section1Id || '',
    pipeModelId: row.pipeModelId || '',
    shippedQty: row.shippedQty || 0,
    shippedAt: formatToDatetimeLocal(row.shippedAt),
    vehiclePlateNo: row.vehiclePlateNo || '',
    shipRemark: row.shipRemark || '',
    status: st,
    orderNo: row.deliveryCode || '',
    shipmentNo: row.shipmentNo || '',
    arrivedQty: row.arrivedQty ?? null,
    receivedQty: row.receivedQty ?? null,
    arrivedConfirmAt: arrivedAt,
    receivedConfirmAt: receivedAt,
    warehouseConfirmAt: warehouseAt,
  }
  showSuperEditModal.value = true
}

function handleSuperEditStatusChange() {
  const newSt = superEditForm.value.status
  const newRank = STATUS_RANK[newSt] ?? 0

  // 1. 到货时间：若目标状态到达或超过待接收，若原记录曾经历过该状态则恢复历史时间，否则后续状态默认留空
  if (newRank >= 1) {
    if (origSuperEditSnap.rank >= 1 && origSuperEditSnap.arrivedConfirmAt) {
      superEditForm.value.arrivedConfirmAt = origSuperEditSnap.arrivedConfirmAt
    } else {
      superEditForm.value.arrivedConfirmAt = ''
    }
  } else {
    superEditForm.value.arrivedConfirmAt = ''
  }

  // 2. 施工接收时间
  if (newRank >= 2 || newSt === 'pending_diff_approve') {
    if (origSuperEditSnap.rank >= 2 && origSuperEditSnap.receivedConfirmAt) {
      superEditForm.value.receivedConfirmAt = origSuperEditSnap.receivedConfirmAt
    } else {
      superEditForm.value.receivedConfirmAt = ''
    }
  } else {
    superEditForm.value.receivedConfirmAt = ''
  }

  // 3. 库管入库时间
  if (newRank >= 3) {
    if (origSuperEditSnap.rank >= 3 && origSuperEditSnap.warehouseConfirmAt) {
      superEditForm.value.warehouseConfirmAt = origSuperEditSnap.warehouseConfirmAt
    } else {
      superEditForm.value.warehouseConfirmAt = ''
    }
  } else {
    superEditForm.value.warehouseConfirmAt = ''
  }
}

async function saveSuperEdit() {
  superEditError.value = ''
  superEditSaving.value = true
  try {
    const shippedAtIso = superEditForm.value.shippedAt ? new Date(superEditForm.value.shippedAt).toISOString() : new Date().toISOString()
    const arrivedConfirmAtIso = superEditForm.value.arrivedConfirmAt ? new Date(superEditForm.value.arrivedConfirmAt).toISOString() : null
    const receivedConfirmAtIso = superEditForm.value.receivedConfirmAt ? new Date(superEditForm.value.receivedConfirmAt).toISOString() : null
    const warehouseConfirmAtIso = superEditForm.value.warehouseConfirmAt ? new Date(superEditForm.value.warehouseConfirmAt).toISOString() : null

    await superUpdateTubeSupplyManagementDelivery(PROJECT_KEY, superEditForm.value.deliveryId, {
      section_1_id: superEditForm.value.section1Id,
      pipe_model_id: superEditForm.value.pipeModelId,
      shipped_qty: Number(superEditForm.value.shippedQty || 0),
      shipped_at: shippedAtIso,
      vehicle_plate_no: superEditForm.value.vehiclePlateNo,
      ship_remark: superEditForm.value.shipRemark,
      status: superEditForm.value.status,
      order_no: superEditForm.value.orderNo,
      shipment_no: superEditForm.value.shipmentNo,
      arrived_qty: superEditForm.value.arrivedQty !== null && superEditForm.value.arrivedQty !== '' ? Number(superEditForm.value.arrivedQty) : null,
      received_qty: superEditForm.value.receivedQty !== null && superEditForm.value.receivedQty !== '' ? Number(superEditForm.value.receivedQty) : null,
      arrived_confirm_at: arrivedConfirmAtIso,
      received_confirm_at: receivedConfirmAtIso,
      warehouse_confirm_at: warehouseConfirmAtIso,
    })
    showSuperEditModal.value = false
    setActionMessage('success', '🎉 超级数据已成功编辑覆盖保存！')
    await loadDeliveries()
  } catch (error) {
    superEditError.value = error?.message || '数据编辑覆盖保存失败'
  } finally {
    superEditSaving.value = false
  }
}

const FITTING_STATUS_RANK = {
  'pending_arrival': 0,
  'shipped': 0,
  'pending_receive': 1,
  'arrived': 1,
  'pending_warehouse': 2,
  'construction_confirmed': 2,
  'received': 2,
  'completed': 3,
  'warehouse_confirmed': 3,
  'cancelled': -1,
}

let origSuperEditFittingSnap = {
  status: '',
  rank: 0,
  arrivedConfirmAt: '',
  receivedConfirmAt: '',
  warehouseConfirmAt: '',
  cancelAt: '',
}

function openSuperEditFitting(item, group = null) {
  superEditFittingError.value = ''
  
  const arrivedAt = formatToDatetimeLocal(item.arrived_confirm_at || item.arrived_at)
  const receivedAt = formatToDatetimeLocal(item.received_confirm_at || item.construction_confirmed_at)
  const warehouseAt = formatToDatetimeLocal(item.warehouse_confirm_at || item.warehouse_confirmed_at)
  const cancelAt = formatToDatetimeLocal(item.cancel_at || item.cancelled_at)
  const st = item.status || group?.status || 'pending_arrival'

  origSuperEditFittingSnap = {
    status: st,
    rank: FITTING_STATUS_RANK[st] ?? 0,
    arrivedConfirmAt: arrivedAt,
    receivedConfirmAt: receivedAt,
    warehouseConfirmAt: warehouseAt,
    cancelAt: cancelAt,
  }

  superEditFittingForm.value = {
    deliveryId: item.id,
    section1Id: item.section_1_id || group?.section_1_id || '',
    supplyEntityId: item.supply_entity_id || group?.supply_entity_id || '',
    fittingType: item.fitting_type || '',
    modelSpec: item.model_spec || '',
    shippedQty: Number(item.shipped_qty || 1),
    unit: item.unit || '个',
    shippedAt: formatToDatetimeLocal(item.shipped_at || group?.shipped_at),
    vehiclePlateNo: item.vehicle_plate_no || group?.vehicle_plate_no || '',
    shipContactName: item.ship_contact_name || group?.ship_contact_name || '',
    shipContactPhone: item.ship_contact_phone || group?.ship_contact_phone || '',
    shipRemark: item.ship_remark || group?.ship_remark || '',
    status: st,
    orderNo: item.order_no || '',
    shipmentNo: item.shipment_no || group?.shipment_no || '',
    arrivedQty: item.arrived_qty ?? null,
    arrivedConfirmAt: arrivedAt,
    arrivedConfirmBy: item.arrived_confirm_by || item.arrived_by || '',
    arrivedRemark: item.arrived_remark || item.arrival_remark || '',
    receivedConfirmAt: receivedAt,
    receivedConfirmBy: item.received_confirm_by || item.construction_confirmed_by || '',
    receivedRemark: item.received_remark || item.construction_remark || '',
    warehouseConfirmAt: warehouseAt,
    warehouseConfirmBy: item.warehouse_confirm_by || item.warehouse_confirmed_by || '',
    warehouseRemark: item.warehouse_remark || '',
    cancelAt: cancelAt,
    cancelBy: item.cancel_by || item.cancelled_by || '',
    cancelReason: item.cancel_reason || '',
  }
  showSuperEditFittingModal.value = true
}

function handleSuperEditFittingStatusChange() {
  const newSt = superEditFittingForm.value.status
  const newRank = FITTING_STATUS_RANK[newSt] ?? 0

  // 1. 到货时间：若目标状态到达或超过待接收，若原记录曾经历过该状态则恢复历史时间，否则后续状态默认留空
  if (newRank >= 1) {
    if (origSuperEditFittingSnap.rank >= 1 && origSuperEditFittingSnap.arrivedConfirmAt) {
      superEditFittingForm.value.arrivedConfirmAt = origSuperEditFittingSnap.arrivedConfirmAt
    } else {
      superEditFittingForm.value.arrivedConfirmAt = ''
    }
  } else {
    superEditFittingForm.value.arrivedConfirmAt = ''
  }

  // 2. 施工接收时间
  if (newRank >= 2) {
    if (origSuperEditFittingSnap.rank >= 2 && origSuperEditFittingSnap.receivedConfirmAt) {
      superEditFittingForm.value.receivedConfirmAt = origSuperEditFittingSnap.receivedConfirmAt
    } else {
      superEditFittingForm.value.receivedConfirmAt = ''
    }
  } else {
    superEditFittingForm.value.receivedConfirmAt = ''
  }

  // 3. 库管入库时间
  if (newRank >= 3) {
    if (origSuperEditFittingSnap.rank >= 3 && origSuperEditFittingSnap.warehouseConfirmAt) {
      superEditFittingForm.value.warehouseConfirmAt = origSuperEditFittingSnap.warehouseConfirmAt
    } else {
      superEditFittingForm.value.warehouseConfirmAt = ''
    }
  } else {
    superEditFittingForm.value.warehouseConfirmAt = ''
  }

  // 4. 撤销时间
  if (newSt === 'cancelled') {
    if (origSuperEditFittingSnap.status === 'cancelled' && origSuperEditFittingSnap.cancelAt) {
      superEditFittingForm.value.cancelAt = origSuperEditFittingSnap.cancelAt
    } else {
      superEditFittingForm.value.cancelAt = ''
    }
  } else {
    superEditFittingForm.value.cancelAt = ''
  }
}

function smartAlignSuperFittingTimestamps() {
  if (!superEditFittingForm.value.shippedAt) return
  try {
    const shippedTime = new Date(superEditFittingForm.value.shippedAt).getTime()
    if (isNaN(shippedTime)) return
    
    // 等距分布智能对齐
    const arrivedTime = new Date(shippedTime + 12 * 60 * 60 * 1000)
    const receivedTime = new Date(arrivedTime.getTime() + 6 * 60 * 60 * 1000)
    const warehouseTime = new Date(receivedTime.getTime() + 2 * 60 * 60 * 1000)
    
    const formatTimeObj = (d) => {
      const year = d.getFullYear()
      const month = String(d.getMonth() + 1).padStart(2, '0')
      const date = String(d.getDate()).padStart(2, '0')
      const hours = String(d.getHours()).padStart(2, '0')
      const minutes = String(d.getMinutes()).padStart(2, '0')
      return `${year}-${month}-${date}T${hours}:${minutes}`
    }
    
    superEditFittingForm.value.arrivedConfirmAt = formatTimeObj(arrivedTime)
    superEditFittingForm.value.receivedConfirmAt = formatTimeObj(receivedTime)
    superEditFittingForm.value.warehouseConfirmAt = formatTimeObj(warehouseTime)
    
    // 数量自动对齐
    const shipQty = Math.max(1, Math.round(Number(superEditFittingForm.value.shippedQty || 1)))
    if (!superEditFittingForm.value.arrivedQty || superEditFittingForm.value.arrivedQty === '') {
      superEditFittingForm.value.arrivedQty = shipQty
    }
  } catch (e) {
    console.error('管件智能时间自动对齐失败:', e)
  }
}

async function saveSuperEditFitting() {
  superEditFittingError.value = ''
  superEditFittingSaving.value = true
  try {
    const form = superEditFittingForm.value
    const shippedAtIso = form.shippedAt ? new Date(form.shippedAt).toISOString() : new Date().toISOString()
    const arrivedConfirmAtIso = form.arrivedConfirmAt ? new Date(form.arrivedConfirmAt).toISOString() : null
    const receivedConfirmAtIso = form.receivedConfirmAt ? new Date(form.receivedConfirmAt).toISOString() : null
    const warehouseConfirmAtIso = form.warehouseConfirmAt ? new Date(form.warehouseConfirmAt).toISOString() : null
    const cancelAtIso = form.cancelAt ? new Date(form.cancelAt).toISOString() : null

    await superUpdateTubeFittingDelivery(PROJECT_KEY, form.deliveryId, {
      section_1_id: form.section1Id,
      fitting_type: form.fittingType,
      model_spec: form.modelSpec,
      shipped_qty: Math.max(1, Math.round(Number(form.shippedQty || 1))),
      unit: form.unit || '个',
      shipped_at: shippedAtIso,
      supply_entity_id: form.supplyEntityId,
      vehicle_plate_no: form.vehiclePlateNo,
      ship_contact_name: form.shipContactName,
      ship_contact_phone: form.shipContactPhone,
      ship_remark: form.shipRemark,
      status: form.status,
      order_no: form.orderNo,
      shipment_no: form.shipmentNo,
      arrived_qty: form.arrivedQty !== null && form.arrivedQty !== '' ? Math.max(1, Math.round(Number(form.arrivedQty))) : null,
      arrived_confirm_at: arrivedConfirmAtIso,
      arrived_confirm_by: form.arrivedConfirmBy || null,
      arrived_remark: form.arrivedRemark || null,
      received_confirm_at: receivedConfirmAtIso,
      received_confirm_by: form.receivedConfirmBy || null,
      received_remark: form.receivedRemark || null,
      warehouse_confirm_at: warehouseConfirmAtIso,
      warehouse_confirm_by: form.warehouseConfirmBy || null,
      warehouse_remark: form.warehouseRemark || null,
      cancel_at: cancelAtIso,
      cancel_by: form.cancelBy || null,
      cancel_reason: form.cancelReason || null,
    })
    showSuperEditFittingModal.value = false
    fittingActionMsg.value = { type: 'success', text: '🎉 管件超级数据已成功编辑覆盖保存！' }
    await loadFittingDeliveries()
  } catch (error) {
    superEditFittingError.value = error?.message || '管件数据编辑覆盖保存失败'
  } finally {
    superEditFittingSaving.value = false
  }
}
</script>

<style scoped>
:deep(.rg-cell-error) {
  background-color: #fee2e2 !important;
  color: #b91c1c !important;
  font-weight: bold !important;
}

:deep(.rg-cell-warning) {
  background-color: #fff7ed !important;
  color: #c2410c !important;
  font-weight: bold !important;
}

:deep(.rg-cell-info) {
  color: #0284c7 !important;
}

/* Premium Usage Block Modal */
.block-modal-overlay {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  background: rgba(15, 23, 42, 0.75) !important;
  backdrop-filter: blur(4px) !important;
  z-index: 99999 !important;
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  padding: 16px !important;
  box-sizing: border-box !important;
}

.block-modal-container {
  width: 90% !important;
  max-width: 620px !important;
  max-height: 85vh !important;
  background: #ffffff !important;
  border: 1px solid rgba(226, 232, 240, 0.9) !important;
  border-radius: 16px !important;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.35) !important;
  overflow-y: auto !important;
  display: flex !important;
  flex-direction: column !important;
  position: relative !important;
  margin: auto !important;
}

.block-modal-header {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.block-warning-icon {
  font-size: 40px;
  animation: pulse-ring 2s infinite ease-in-out;
}

@keyframes pulse-ring {
  0% { transform: scale(0.95); opacity: 0.8; }
  50% { transform: scale(1.08); opacity: 1; }
  100% { transform: scale(0.95); opacity: 0.8; }
}

.block-modal-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
}

.block-warning-desc {
  margin: 0;
  font-size: 13.5px;
  color: #64748b;
  line-height: 1.5;
}

.block-modal-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.metric-block-card {
  background: #f8fafc;
  border: 1px solid #f1f5f9;
  border-radius: 8px;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.metric-block-card .lbl {
  font-size: 11px;
  color: #64748b;
  text-align: center;
}

.metric-block-card .val {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.metric-block-card .val.model-val {
  font-size: 12px;
  color: #3b82f6;
  word-break: break-all;
  text-align: center;
}

.block-modal-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.tube-page-root { min-height: 100vh; background: var(--bg); }
.tube-page-main { display: flex; flex-direction: column; gap: 16px; padding-top: 18px; padding-bottom: 24px; }
.topbar-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.page-error { margin: 0; color: var(--danger); }

.panel-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.panel-title-row h2 {
  margin: 0;
  color: #0f172a;
  font-size: 18px;
}

.active-ghost {
  border-color: #b91c1c;
  color: #b91c1c;
  background: #fee2e2;
}

.batch-box {
  margin-top: 16px;
  padding: 14px;
  border: 1px solid #dbe4f0;
  border-radius: 12px;
  background: #f8fbff;
}

.batch-box-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.compact {
  padding: 10px 12px;
}

.panel-hint {
  color: #64748b;
  font-size: 13px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.supply-demand-toolbar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: #334155;
  font-size: 14px;
}

.field-compact {
  min-width: 0;
}

.field-span-2 {
  grid-column: span 2;
}

.field span {
  font-size: 13px;
  color: #475569;
  font-weight: 600;
}

.field select,
.field input,
.number-input {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
  color: #0f172a;
  background: #fff;
  box-sizing: border-box;
}

.field input[disabled] {
  color: #475569;
  background: #f8fafc;
}

.field select:focus,
.field input:focus,
.number-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.meta-chip,
.status-chip {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 600;
}

.meta-chip {
  background: #eef2ff;
  color: #334155;
}

.status-chip {
  background: #e2e8f0;
  color: #334155;
}

.status-chip-group {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap;
  white-space: nowrap;
}

.status-pending_arrival { background: #dbeafe; color: #1d4ed8; }
.status-pending_receive { background: #fef3c7; color: #92400e; }
.status-pending_warehouse { background: #ede9fe; color: #6d28d9; }
.status-completed { background: #dcfce7; color: #166534; }
.status-cancelled { background: #fee2e2; color: #b91c1c; }
.status-abnormal { background: #fff1f2; color: #be123c; }

.loading-text,
.empty-box {
  padding: 14px 16px;
  text-align: center;
  color: #475569;
  background: #f8fafc;
  border-radius: 10px;
  font-size: 14px;
}

.error-box {
  border-radius: 10px;
  background: #fff1f2;
  color: #be123c;
  padding: 14px 16px;
  font-size: 14px;
}

.table-wrap {
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fff;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 880px;
}

.data-table th,
.data-table td {
  border-bottom: 1px solid #e2e8f0;
  padding: 12px;
  text-align: left;
  vertical-align: top;
  font-size: 14px;
}

.data-table th {
  color: #334155;
  font-weight: 600;
  background: #f8fafc;
}

.data-table tr:last-child td {
  border-bottom: none;
}

.fitting-record-table {
  min-width: 1120px;
}

.fitting-record-table th,
.fitting-record-table td {
  white-space: nowrap;
  vertical-align: middle;
}

.delivery-record-table {
  min-width: 1540px;
  table-layout: auto;
}

.delivery-record-table th,
.delivery-record-table td {
  vertical-align: middle;
  padding: 10px 12px;
}

.delivery-record-table th {
  white-space: nowrap;
}

.delivery-record-table .col-order {
  width: 140px;
  min-width: 140px;
}

.delivery-record-table .col-shipment {
  width: 150px;
  min-width: 150px;
}

.delivery-record-table .col-plate {
  width: 120px;
  min-width: 120px;
}

.delivery-record-table .col-supply {
  width: 130px;
  min-width: 130px;
}

.delivery-record-table .col-section1 {
  width: 150px;
  min-width: 150px;
}

.delivery-record-table .col-model {
  width: 170px;
  min-width: 170px;
}

.delivery-record-table .col-qty {
  width: 92px;
  min-width: 92px;
}

.delivery-record-table .col-time {
  width: 170px;
  min-width: 170px;
}

.delivery-record-table .col-elapsed {
  width: 100px;
  min-width: 100px;
}

.delivery-record-table .col-status {
  width: 180px;
  min-width: 180px;
}

.delivery-record-table .col-remark {
  width: auto;
  min-width: 240px;
}

.delivery-record-table .col-actions {
  width: 170px;
  min-width: 170px;
}

.delivery-record-table .btn {
  white-space: nowrap;
}

.cell-nowrap {
  white-space: nowrap;
}

.cell-wrap {
  white-space: normal;
  word-break: break-word;
  line-height: 1.45;
}

.cell-number {
  white-space: nowrap;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.cell-remark {
  white-space: normal;
  word-break: break-word;
  color: #334155;
  line-height: 1.5;
}

.delivery-record-table td:nth-child(12) {
  white-space: nowrap;
}

.action-stack {
  display: flex;
  flex-direction: row;
  align-items: center;
  flex-wrap: nowrap;
  gap: 8px;
}

.action-stack .muted-text {
  white-space: nowrap;
}

.primary-button {
  border-radius: 10px;
  padding: 10px 16px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
  border: 1px solid #2563eb;
  background: #2563eb;
  color: #fff;
  font-weight: 600;
  white-space: nowrap;
}

.primary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn, .primary-button {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  text-align: center !important;
  white-space: nowrap !important;
  word-break: keep-all !important;
  box-sizing: border-box !important;
}

.btn {
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 10px 14px;
  background: #fff;
  color: #0f172a;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn.ghost {
  background: #fff;
}

.btn.btn-xs {
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 12px;
}

.btn.danger-ghost {
  border-color: #fecaca;
  color: #b91c1c;
  background: #fff5f5;
}

.action-message {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.action-message.success { color: #166534; }
.action-message.error { color: #be123c; }
.danger-text { color: #b91c1c; font-weight: 700; }
.muted-text { color: #64748b; }

.multi-select-dropdown {
  position: relative;
}

.multi-select-summary {
  list-style: none;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 10px 12px;
  background: #fff;
  color: #0f172a;
  font-size: 14px;
  cursor: pointer;
  user-select: none;
}

.multi-select-summary::-webkit-details-marker {
  display: none;
}

.multi-select-dropdown[open] .multi-select-summary {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.multi-select-panel {
  position: absolute;
  z-index: 20;
  top: calc(100% + 6px);
  left: 0;
  width: 100%;
  min-width: 220px;
  max-height: 260px;
  overflow: auto;
  border: 1px solid #dbe2ea;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12);
  padding: 10px;
  box-sizing: border-box;
}

.multi-select-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.checkbox-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 6px;
  border-radius: 8px;
  cursor: pointer;
}

.checkbox-option:hover {
  background: #f8fafc;
}

.checkbox-option input {
  width: 16px;
  height: 16px;
  margin: 0;
  flex: 0 0 auto;
}

@media (max-width: 900px) {
  .field-span-2 {
    grid-column: span 1;
  }
}

@media (max-width: 720px) {
  .tube-page-main {
    padding-bottom: 16px;
  }

  /* 🏷️ 二级 Tab 选项卡横向滑动 (防止多 Tab 挤压换行) */
  .tube-tabs-header-wrap {
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    padding: 3px !important;
    border-radius: 10px !important;
  }

  .tube-tabs-header {
    width: max-content !important;
    min-width: 100% !important;
    gap: 3px !important;
  }

  .tube-tabs-header button {
    padding: 8px 12px !important;
    font-size: 12.5px !important;
    white-space: nowrap !important;
    flex: none !important;
    border-radius: 8px !important;
  }

  .topbar,
  .panel-title-row {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .topbar-actions {
    width: 100%;
  }

  .toolbar-actions {
    width: 100%;
    justify-content: stretch;
    flex-direction: column;
    gap: 6px;
  }

  .topbar-actions .btn,
  .toolbar-actions .btn,
  .panel-title-row .btn,
  .panel-title-row .primary-button {
    width: 100%;
    justify-content: center;
  }

  .multi-select-panel {
    position: static;
    width: 100%;
    margin-top: 6px;
    box-shadow: none;
  }

  .col-remark-field {
    grid-column: span 1 !important;
  }

  .mobile-hide-hint {
    display: none !important;
  }

  /* 🚚 管件车次汇总卡片头部响应式 */
  .fitting-card-header {
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 8px !important;
    padding: 10px 12px !important;
  }

  .fitting-card-header .header-left-meta {
    width: 100% !important;
    display: flex !important;
    flex-wrap: wrap !important;
    align-items: center !important;
    justify-content: flex-start !important;
    gap: 6px !important;
  }

  .fitting-card-header .header-right-meta {
    width: 100% !important;
    display: flex !important;
    flex-wrap: wrap !important;
    align-items: center !important;
    justify-content: space-between !important;
    gap: 8px !important;
    border-top: 1px dashed #e2e8f0 !important;
    padding-top: 8px !important;
    margin-top: 2px !important;
  }

  .fitting-card-header .header-right-meta .btn {
    flex-shrink: 0 !important;
  }

  /* 📱 展开后的管件明细在手机端卡片化优雅排版 */
  .table-responsive-wrapper {
    overflow-x: visible !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
  }

  .demand-fitting-table {
    min-width: 0 !important;
    border: none !important;
    table-layout: auto !important;
    background: transparent !important;
    width: 100% !important;
  }

  .demand-fitting-table thead {
    display: none !important;
  }

  .demand-fitting-table tbody {
    display: flex !important;
    flex-direction: column !important;
    gap: 10px !important;
  }

  .demand-fitting-table tbody tr.mobile-fitting-item-row {
    display: grid !important;
    grid-template-columns: 1fr auto !important;
    grid-template-areas:
      "type status"
      "model model"
      "shipped action"
      "operate operate";
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    padding: 10px 12px !important;
    gap: 6px 10px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important;
    box-sizing: border-box !important;
  }

  .demand-fitting-table tbody tr.mobile-fitting-item-row.is-cancelled-row {
    background: #fef2f2 !important;
    border-color: #fecaca !important;
  }

  .demand-fitting-table tbody td {
    border: none !important;
    padding: 0 !important;
    width: auto !important;
  }

  .demand-fitting-table tbody td.col-index {
    display: none !important;
  }

  .demand-fitting-table tbody td.col-type {
    grid-area: type !important;
    text-align: left !important;
  }

  .demand-fitting-table tbody td.col-status {
    grid-area: status !important;
    text-align: right !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: flex-end !important;
    justify-content: center !important;
  }

  .demand-fitting-table tbody td.col-model {
    grid-area: model !important;
    font-size: 13.5px !important;
    color: #1e293b !important;
    padding: 2px 0 !important;
    word-break: break-all !important;
    text-align: left !important;
  }

  .demand-fitting-table tbody td.col-shipped {
    grid-area: shipped !important;
    text-align: left !important;
    font-size: 13px !important;
  }

  .demand-fitting-table tbody td.col-shipped .mobile-lbl {
    display: inline !important;
    font-size: 11.5px !important;
    color: #64748b !important;
    font-weight: normal !important;
  }

  .demand-fitting-table tbody td.col-action {
    grid-area: action !important;
    text-align: right !important;
    font-size: 11.5px !important;
  }

  .demand-fitting-table tbody td.col-action .mobile-order-lbl {
    display: inline !important;
  }

  .demand-fitting-table tbody td.col-operate {
    grid-area: operate !important;
    text-align: right !important;
    border-top: 1px dashed #f1f5f9 !important;
    padding-top: 6px !important;
    margin-top: 2px !important;
  }

  .demand-fitting-table tbody td.col-operate .mobile-action-buttons {
    justify-content: flex-end !important;
    width: 100% !important;
    gap: 6px !important;
  }

  .demand-fitting-table tbody td.col-operate .btn {
    padding: 4px 10px !important;
    font-size: 12px !important;
  }

  /* 📜 直管发货台账横向滚动容器优化 */
  .delivery-record-table {
    min-width: 860px !important;
  }

  /* 🛡️ 时光轴弹窗在移动端的紧凑排版 */
  .block-modal-overlay {
    padding: 8px !important;
  }

  .block-modal-card {
    max-height: 92vh !important;
    width: 100% !important;
    border-radius: 12px !important;
  }
}

/* 磨砂玻璃态微数据看板 */
.quick-dashboard-card {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  padding: 0 !important;
}

.meta-dashboard {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-top: 14px;
}

.meta-card {
  background: rgba(255, 255, 255, 0.65) !important;
  backdrop-filter: blur(12px) !important;
  -webkit-backdrop-filter: blur(12px) !important;
  border: 1px solid rgba(226, 232, 240, 0.8) !important;
  border-radius: 14px !important;
  padding: 16px !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 6px !important;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -1px rgba(0, 0, 0, 0.02) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  position: relative !important;
  overflow: hidden !important;
  box-sizing: border-box;
}

.meta-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 4px;
  background: linear-gradient(180deg, #6366f1 0%, #3b82f6 100%);
}

.meta-card.highlight::before {
  background: linear-gradient(180deg, #f59e0b 0%, #d97706 100%);
}

.meta-card:hover {
  transform: translateY(-4px) !important;
  background: rgba(255, 255, 255, 0.85) !important;
  box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.08), 0 4px 6px -2px rgba(59, 130, 246, 0.04) !important;
  border-color: rgba(147, 197, 253, 0.5) !important;
}

.meta-label {
  font-size: 12px !important;
  color: #64748b !important;
  font-weight: 500 !important;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.meta-value {
  font-size: 20px !important;
  color: #1e293b !important;
  font-weight: 700 !important;
  font-family: "Inter", "Outfit", -apple-system, sans-serif !important;
}

.highlight-num {
  color: #2563eb !important;
}

/* 🧭 一体化复合双层导航容器 (Unified Compound Navigation Group) */
.nav-composite-group {
  display: flex !important;
  flex-direction: column !important;
  gap: 6px !important;
  width: 100% !important;
  margin-top: 6px !important;
  margin-bottom: 16px !important;
}

/* 🔹 一级物料大类分段控制器 (Segmented Category Bar) */
.category-segment-wrapper {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%) !important;
  border-radius: 12px !important;
  padding: 4px !important;
  margin: 0 !important;
  border: 1px solid #e2e8f0 !important;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.02) !important;
  box-sizing: border-box;
}

.category-segment-bar {
  display: flex !important;
  gap: 6px !important;
  width: 100% !important;
}

.category-segment-btn {
  flex: 1 !important;
  border: 1px solid transparent !important;
  background: transparent !important;
  padding: 8px 16px !important;
  border-radius: 8px !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  color: #64748b !important;
  cursor: pointer !important;
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1) !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 8px !important;
}

.category-segment-btn:hover {
  color: #1e293b !important;
  background: rgba(255, 255, 255, 0.7) !important;
}

.category-segment-btn.active {
  color: #1e40af !important;
  background: #ffffff !important;
  border-color: #dbeafe !important;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.12), 0 1px 2px rgba(0, 0, 0, 0.04) !important;
}

.category-segment-btn .cat-icon {
  font-size: 14.5px;
  line-height: 1;
}

.category-segment-btn .cat-label {
  font-size: 13.5px;
  letter-spacing: 0.2px;
}

.category-segment-btn .cat-count {
  font-size: 11px;
  font-weight: 500;
  padding: 1.5px 6px;
  border-radius: 20px;
  background: #e2e8f0;
  color: #64748b;
  transition: all 0.22s ease;
}

.category-segment-btn.active .cat-count {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 600;
}

/* 🏷️ 二级选项卡导航 (Responsive Sub-Tabs Header) */
.tube-tabs-header-wrap {
  background: rgba(241, 245, 249, 0.8) !important;
  border-radius: 12px !important;
  padding: 4px !important;
  margin: 0 !important;
  border: 1px solid #e2e8f0 !important;
  box-sizing: border-box;
}

.tube-tabs-header {
  display: flex !important;
  gap: 4px !important;
  width: 100% !important;
}

.tube-tabs-header button {
  flex: 1 !important;
  border: none !important;
  background: transparent !important;
  padding: 12px 16px !important;
  border-radius: 10px !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  color: #475569 !important;
  cursor: pointer !important;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 8px !important;
}

.tube-tabs-header button:hover {
  color: #1e293b !important;
  background: rgba(255, 255, 255, 0.5) !important;
}

.tube-tabs-header button.active {
  color: #2563eb !important;
  background: #ffffff !important;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
}

/* 左右分栏布局 */
@media (min-width: 1024px) {
  .workbench-split-layout {
    display: grid !important;
    grid-template-columns: 1.1fr 0.9fr !important;
    gap: 20px !important;
    align-items: start !important;
  }
}

.split-left-card, .split-right-card {
  box-sizing: border-box;
  margin: 0 !important;
}

.form-vertical-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-row-2col {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.btn-large {
  padding: 12px 20px !important;
  font-size: 15px !important;
  font-weight: 600 !important;
  border-radius: 10px !important;
  width: 100%;
}

.form-submit-row {
  margin-top: 8px;
}

.shipment-status-input {
  background: #f8fafc !important;
  color: #475569 !important;
  font-weight: 600 !important;
}

.text-hint-highlight {
  background: #f0f7ff;
  border-left: 3px solid #3b82f6;
  padding: 10px 12px;
  border-radius: 0 8px 8px 0;
  font-size: 13px !important;
  line-height: 1.5;
  color: #1e3a8a !important;
}

.shadow-accent {
  box-shadow: 0 4px 14px 0 rgba(37, 99, 235, 0.35) !important;
}

/* 待提交明细积木列表 */
.batch-box-premium {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  border-radius: 14px;
  padding: 18px;
  min-height: 280px;
  box-sizing: border-box;
}

.empty-box-split {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 10px;
  text-align: center;
  box-sizing: border-box;
}

.empty-icon-bubble {
  font-size: 48px;
  margin-bottom: 12px;
  animation: float-bubble 3s ease-in-out infinite;
}

@keyframes float-bubble {
  0% { transform: translateY(0px); }
  50% { transform: translateY(-8px); }
  100% { transform: translateY(0px); }
}

.empty-title {
  font-size: 16px;
  color: #334155;
  margin-bottom: 6px;
}

.empty-subtitle {
  font-size: 13px;
  color: #64748b;
  max-width: 240px;
  line-height: 1.5;
}

.draft-items-card-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.draft-item-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
  transition: all 0.2s ease;
  position: relative;
}

.draft-item-card:hover {
  border-color: #cbd5e1;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05);
  transform: scale(1.01);
}

.draft-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  border-bottom: 1px dashed #f1f5f9;
  padding-bottom: 8px;
}

.section1-tag {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}

.btn-remove-draft {
  border: none;
  background: #fee2e2;
  color: #ef4444;
  width: 22px;
  height: 22px;
  border-radius: 999px;
  font-size: 11px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.btn-remove-draft:hover {
  background: #ef4444;
  color: #ffffff;
}

.draft-card-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.info-row .lbl {
  color: #64748b;
}

.info-row .val {
  color: #1e293b;
  font-weight: 600;
}

.info-row .highlight-qty {
  color: #2563eb;
  font-weight: 700;
}

.info-row .remark-val {
  font-weight: 500;
  color: #475569;
  max-width: 180px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 升级表格 Hover 和 Ellipsis 防御 */
.cell-text {
  max-width: 180px !important;
  min-width: 130px !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

.cell-code {
  font-family: "Consolas", "Courier New", monospace !important;
  font-size: 13px !important;
}

.cell-remark {
  max-width: 160px !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

.data-table tbody tr {
  transition: background-color 0.2s ease;
}

.data-table tbody tr:hover {
  background: linear-gradient(90deg, rgba(37, 99, 235, 0.03) 0%, rgba(255, 255, 255, 0) 100%) !important;
}

.status-chip {
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.4);
}

/* 超级管理员编辑覆盖极简弹窗与经典半透明遮罩层 */
.modal-overlay {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  background: rgba(0, 0, 0, 0.5) !important;
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  z-index: 9999 !important;
}

.modal-card {
  background: #ffffff !important;
  border-radius: 12px !important;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25) !important;
  overflow: hidden !important;
  border: 1px solid #e2e8f0 !important;
}

/* 🔩 多维多选下拉筛选工具栏 (Clean Multi-Select Dropdown Toolbar) */
.fitting-filter-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 8px 12px;
  margin-bottom: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

.ms-dropdown-container {
  position: relative;
  display: inline-block;
}

.ms-dropdown-trigger {
  height: 34px;
  padding: 0 10px;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 7px;
  color: #334155;
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
  user-select: none;
  white-space: nowrap;
}

.ms-dropdown-trigger:hover {
  background: #f1f5f9;
  border-color: #94a3b8;
  color: #0f172a;
}

.ms-dropdown-trigger.has-value {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #1d4ed8;
  font-weight: 600;
}

.ms-dropdown-trigger.is-open {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}

.ms-label-icon {
  font-size: 13px;
}

.ms-label-text {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ms-badge {
  background: #2563eb;
  color: #ffffff;
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 10px;
  font-weight: 700;
}

.ms-clear-btn {
  font-size: 11px;
  color: #94a3b8;
  padding: 0 2px;
  border-radius: 50%;
  cursor: pointer;
}

.ms-clear-btn:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.ms-arrow {
  font-size: 10px;
  color: #64748b;
  margin-left: 2px;
}

.ms-dropdown-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  z-index: 100 !important;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
  min-width: 180px;
  max-width: 260px;
  padding: 6px 0;
  animation: slide-down-fade 0.18s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slide-down-fade {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.ms-menu-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 10px 6px 10px;
  border-bottom: 1px solid #f1f5f9;
  font-size: 11.5px;
  color: #64748b;
}

.ms-menu-title {
  font-weight: 600;
  color: #475569;
}

.ms-menu-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.ms-menu-actions a {
  color: #2563eb;
  text-decoration: none;
  font-size: 11px;
}

.ms-menu-actions a:hover {
  text-decoration: underline;
}

.ms-menu-actions .sep {
  color: #cbd5e1;
  font-size: 10px;
}

.ms-menu-list {
  max-height: 220px;
  overflow-y: auto;
  padding: 4px 0;
}

.ms-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 10px;
  font-size: 12.5px;
  color: #334155;
  cursor: pointer;
  transition: background 0.15s ease;
  user-select: none;
}

.ms-menu-item:hover {
  background: #f8fafc;
  color: #0f172a;
}

.ms-menu-item.checked {
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 500;
}

.ms-menu-item input[type="checkbox"] {
  cursor: pointer;
  accent-color: #2563eb;
  width: 14px;
  height: 14px;
}

.ms-item-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ms-item-count {
  font-size: 11px;
  color: #94a3b8;
}

.ms-search-box {
  flex: 1;
  min-width: 180px;
}

.reset-filter-btn {
  height: 34px !important;
  font-size: 12px !important;
  color: #ef4444 !important;
  border-color: #fecaca !important;
  background: #fff5f5 !important;
  padding: 0 10px !important;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.reset-filter-btn:hover {
  background: #fee2e2 !important;
  border-color: #fca5a5 !important;
}

/* 📊 表格可点击排序表头样式 */
.sortable-th {
  cursor: pointer !important;
  user-select: none !important;
  transition: all 0.18s ease !important;
  position: relative;
  white-space: nowrap !important;
}

.sortable-th:hover {
  background: #f1f5f9 !important;
  color: #1d4ed8 !important;
}

.sortable-th.sorted {
  background: #eff6ff !important;
  color: #1d4ed8 !important;
  font-weight: 700 !important;
  border-bottom: 2px solid #2563eb !important;
}

.sort-icon {
  display: inline-block;
  margin-left: 4px;
  font-size: 11px;
  color: #94a3b8;
  vertical-align: middle;
  transition: color 0.15s ease;
}

.sortable-th.sorted .sort-icon {
  color: #2563eb;
  font-weight: bold;
}

/* 🔩 管件基准量标题与顶部操作栏规范排版 */
.baseline-header-row {
  display: flex !important;
  justify-content: space-between !important;
  align-items: center !important;
  gap: 16px !important;
  flex-wrap: wrap !important;
  margin-bottom: 12px !important;
}

.header-title-col {
  flex: 1 1 auto;
  min-width: 260px;
}

.header-title-col h2 {
  margin: 0 0 4px 0 !important;
  font-size: 17px !important;
  font-weight: 700 !important;
  color: #0f172a !important;
}

.header-title-col .panel-hint {
  font-size: 12.5px !important;
  color: #64748b !important;
  margin: 0 !important;
}

.header-actions-col {
  display: inline-flex !important;
  align-items: center !important;
  gap: 8px !important;
  flex-wrap: wrap !important;
}

.section-select-group {
  display: inline-flex !important;
  align-items: center !important;
  gap: 6px !important;
  height: 34px !important;
  padding: 0 8px 0 10px !important;
  background: #f8fafc !important;
  border: 1px solid #cbd5e1 !important;
  border-radius: 8px !important;
  transition: all 0.2s ease !important;
  box-sizing: border-box !important;
}

.section-select-group:focus-within {
  border-color: #3b82f6 !important;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15) !important;
  background: #ffffff !important;
}

.section-select-group .select-label {
  font-size: 12.5px !important;
  color: #475569 !important;
  font-weight: 600 !important;
  white-space: nowrap !important;
  user-select: none !important;
}

.baseline-section-select {
  height: 28px !important;
  line-height: 28px !important;
  border: none !important;
  background: transparent !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  color: #1e293b !important;
  outline: none !important;
  cursor: pointer !important;
  padding: 0 4px !important;
  min-width: 130px !important;
}

.baseline-action-btn {
  height: 34px !important;
  line-height: 32px !important;
  padding: 0 12px !important;
  font-size: 12.5px !important;
  font-weight: 500 !important;
  border: 1px solid #cbd5e1 !important;
  background: #ffffff !important;
  border-radius: 8px !important;
  display: inline-flex !important;
  align-items: center !important;
  gap: 4px !important;
  cursor: pointer !important;
  transition: all 0.18s ease !important;
  color: #334155 !important;
  box-sizing: border-box !important;
}

.baseline-action-btn:hover:not(:disabled) {
  background: #f8fafc !important;
  border-color: #94a3b8 !important;
  color: #0f172a !important;
}

.baseline-action-btn:disabled {
  opacity: 0.5 !important;
  cursor: not-allowed !important;
}

/* 🏷️ 数据统计微看板 (Baseline Summary Micro-Dashboard) */
.baseline-summary {
  display: flex !important;
  flex-wrap: wrap !important;
  align-items: center !important;
  gap: 10px !important;
  margin-top: 6px !important;
  margin-bottom: 12px !important;
}

.baseline-summary .summary-chip {
  display: inline-flex !important;
  align-items: center !important;
  gap: 6px !important;
  padding: 6px 14px !important;
  border-radius: 8px !important;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%) !important;
  border: 1px solid #e2e8f0 !important;
  color: #475569 !important;
  font-size: 12.5px !important;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02) !important;
}

.baseline-summary .summary-chip strong {
  color: #1e293b !important;
  font-weight: 700 !important;
}

/* 🏷️ 已选筛选条件胶囊标签行 (Active Filter Tags Row) */
.active-filter-tags-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  margin-bottom: 10px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px dashed #cbd5e1;
}

.active-tags-label {
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
  margin-right: 2px;
}

.filter-tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  color: #1d4ed8;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 6px;
  padding: 2px 8px;
  cursor: pointer;
  transition: all 0.18s ease;
  user-select: none;
}

.filter-tag-chip:hover {
  background: #dbeafe;
  border-color: #93c5fd;
  color: #1e40af;
}

.tag-close-icon {
  font-size: 10px;
  color: #3b82f6;
  font-weight: bold;
}

.filter-tag-chip:hover .tag-close-icon {
  color: #ef4444;
}

.clear-all-link {
  border: none;
  background: transparent;
  color: #ef4444;
  font-size: 11.5px;
  cursor: pointer;
  text-decoration: underline;
  padding: 2px 6px;
}

.clear-all-link:hover {
  color: #b91c1c;
}

/* 📜 限制约20行高度并带粘性吸顶表头与独立滚动条的表格容器 */
.fitting-baseline-table-wrap {
  max-height: 680px !important;
  overflow-y: auto !important;
  overflow-x: auto !important;
  position: relative !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 10px !important;
  background: #ffffff !important;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.02) !important;
}

.fitting-baseline-table-wrap table {
  margin: 0 !important;
  border-collapse: separate !important;
  border-spacing: 0 !important;
  width: 100% !important;
}

.fitting-baseline-table-wrap thead th {
  position: sticky !important;
  top: 0 !important;
  z-index: 12 !important;
  background: #f8fafc !important;
  border-bottom: 2px solid #cbd5e1 !important;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
}

/* 底部状态指示栏 */
.baseline-table-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
  padding: 6px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 12px;
  color: #64748b;
}

.baseline-table-footer .footer-left strong {
  color: #0284c7;
  font-weight: 700;
}

.baseline-table-footer .footer-right {
  color: #94a3b8;
  font-size: 11.5px;
}
</style>

<!-- RevoGrid 单元格校验高亮样式全局强覆写 (穿透 Web Component / Shadow DOM 隔绝) -->
<style>
.rgCell.rg-cell-error,
revo-grid .rgCell.rg-cell-error,
div.rgCell.rg-cell-error,
.rg-cell-error {
  background-color: #fee2e2 !important;
  color: #b91c1c !important;
  font-weight: 700 !important;
  border-bottom: 2px solid #ef4444 !important;
}

.rgCell.rg-cell-warning,
revo-grid .rgCell.rg-cell-warning,
div.rgCell.rg-cell-warning,
.rg-cell-warning {
  background-color: #fff7ed !important;
  color: #c2410c !important;
  font-weight: 700 !important;
  border-bottom: 2px solid #f97316 !important;
}

.rgCell.rg-cell-info,
revo-grid .rgCell.rg-cell-info,
div.rgCell.rg-cell-info,
.rg-cell-info {
  color: #0284c7 !important;
}
</style>
