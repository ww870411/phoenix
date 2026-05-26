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

      <!-- 磨砂玻璃态数据微看板 (Quick Dashboard) -->
      <section class="card elevated quick-dashboard-card" v-if="selectedSupplyEntityId">
        <div class="meta-dashboard">
          <div class="meta-card">
            <span class="meta-label">当前供给主体</span>
            <strong class="meta-value">{{ currentSupplyEntityLabel }}</strong>
          </div>
          <div class="meta-card">
            <span class="meta-label">展示/业务日期</span>
            <strong class="meta-value">{{ showDate || '—' }}</strong>
          </div>
          <div class="meta-card">
            <span class="meta-label">待提交车次明细</span>
            <strong class="meta-value highlight-num">{{ draftDeliveryItems.length }} 条</strong>
          </div>
          <div class="meta-card highlight">
            <span class="meta-label">计划起始日期</span>
            <strong class="meta-value">{{ planStartDate || '—' }}</strong>
          </div>
          <div class="meta-card highlight">
            <span class="meta-label">发货记录总数</span>
            <strong class="meta-value">{{ deliveryRows.length }} 笔</strong>
          </div>
        </div>
      </section>

      <!-- 选项卡导航 (Responsive Tabs Header) -->
      <div class="tube-tabs-header-wrap" v-if="selectedSupplyEntityId">
        <div class="tube-tabs-header">
          <button 
            type="button" 
            :class="{ active: activeTab === 'demand' }" 
            @click="activeTab = 'demand'"
          >
            🎯 需求与缺口看板
          </button>
          <button 
            type="button" 
            :class="{ active: activeTab === 'register' }" 
            @click="activeTab = 'register'"
          >
            🚚 批量发货与车次装配
          </button>
          <button 
            type="button" 
            :class="{ active: activeTab === 'history' }" 
            @click="activeTab = 'history'"
          >
            📋 物流发货记录
          </button>
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
                    <th>{{ supplyDemandViewMode === 'summary' ? '统计范围' : '换热站' }}</th>
                    <th>型号</th>
                    <th>设计总量（米）</th>
                    <th>计划采购总量（米）</th>
                    <th>未来三日计划（米）</th>
                    <th>已发货待到货（米）</th>
                    <th>已到货待接收（米）</th>
                    <th>已接收待库管（米）</th>
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
                    <option v-for="entity in supplyEntityOptions" :key="entity.entity_id" :value="entity.entity_id">
                      {{ entity.entity_name }}
                    </option>
                  </select>
                </label>

                <div class="form-row-2col">
                  <label class="field">
                    <span>装车换热站</span>
                    <select v-model="deliveryForm.stationId">
                      <option value="" disabled>请选择换热站</option>
                      <option v-for="station in stationOptions" :key="station.station_id" :value="station.station_id">
                        {{ station.station_name }}
                      </option>
                    </select>
                  </label>

                  <label class="field">
                    <span>保温管型号</span>
                    <select v-model="deliveryForm.pipeModelId">
                      <option value="" disabled>请选择型号</option>
                      <option v-for="pipe in pipeModelOptions" :key="pipe.pipe_model_id" :value="pipe.pipe_model_id">
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
                      v-if="currentGroup === 'Global_admin'" 
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
                        : '当前将自动新建运输车次号；同一车次下可累积不同换热站/型号明细一并出发。'
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
                  :disabled="submitDeliveryLoading || !canSubmitCurrentProject || !selectedSupplyEntityId || !draftDeliveryItems.length"
                  @click="submitDeliveryBatch"
                >
                  {{ submitDeliveryLoading ? '🚀 提交当前车次中...' : '🚀 一键提交当前发货车次' }}
                </button>
              </div>

              <p v-if="actionMessage" :class="['action-message', actionMessage.type]">{{ actionMessage.text }}</p>

              <div class="batch-box-premium">
                <div v-if="!draftDeliveryItems.length" class="empty-box-split">
                  <div class="empty-icon-bubble">📦</div>
                  <strong class="empty-title">当前发车车厢为空</strong>
                  <span class="empty-subtitle">请从左侧选择换热站、型号、发货米数，并点击“加入当前发货车次”进行装载。</span>
                </div>
                <div v-else class="draft-items-card-list">
                  <div 
                    v-for="(item, index) in draftDeliveryItems" 
                    :key="`${item.stationId}-${item.pipeModelId}-${index}`" 
                    class="draft-item-card"
                  >
                    <div class="draft-card-header">
                      <span class="station-tag">📍 {{ item.stationName }}</span>
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

            <div v-if="deliveriesLoading" class="loading-text">正在加载发货记录...</div>
            <div v-else-if="deliveriesError" class="error-box">{{ deliveriesError }}</div>
            <div v-else-if="!deliveryRows.length" class="empty-box">当前没有发货记录。</div>
            <div v-else class="table-wrap">
              <table class="data-table delivery-record-table">
                <colgroup>
                  <col class="col-order" />
                  <col class="col-shipment" />
                  <col class="col-plate" />
                  <col class="col-supply" />
                  <col class="col-station" />
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
                    <th>换热站</th>
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
                    <td class="cell-text" :title="row.stationName">{{ row.stationName }}</td>
                    <td class="cell-text" :title="row.pipeModelName">{{ row.pipeModelName }}</td>
                    <td class="cell-number">{{ formatNumber(row.shippedQty) }}</td>
                    <td class="cell-number">{{ formatNullableNumber(row.arrivedQty) }}</td>
                    <td class="cell-number">{{ formatNullableNumber(row.receivedQty) }}</td>
                    <td class="cell-nowrap cell-datetime">{{ row.shippedAtDisplay || '—' }}</td>
                    <td class="cell-nowrap cell-elapsed">{{ formatDeliveryElapsedDisplay(row) }}</td>
                    <td>
                      <div class="status-chip-group">
                        <span :class="['status-chip', `status-${row.status}`]">{{ row.statusLabel }}</span>
                        <span v-if="row.abnormalFlag" class="status-chip status-abnormal">{{ getAbnormalLabel(row) }}</span>
                      </div>
                    </td>
                    <td class="cell-text cell-remark" :title="row.shipRemark || row.cancelReason || '—'">{{ row.shipRemark || row.cancelReason || '—' }}</td>
                    <td>
                      <div class="action-stack">
                        <button
                          v-if="currentGroup === 'Global_admin'"
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
                          v-if="row.status === 'pending_arrival'"
                          type="button"
                          class="btn danger-ghost"
                          :disabled="cancelLoadingIds[row.deliveryId]"
                          @click="cancelDelivery(row)"
                        >
                          {{ cancelLoadingIds[row.deliveryId] ? '撤销中...' : '撤销发货' }}
                        </button>
                        <span v-else-if="currentGroup !== 'Global_admin'" class="muted-text">不可撤销</span>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>

      </div>
    </main>

    <!-- 超级管理员数据编辑覆盖模态窗 -->
    <div v-if="showSuperEditModal" class="modal-overlay">
      <div class="modal-card elevated" style="max-width: 680px; width: 90%; background: #ffffff; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);">
        <div class="modal-header" style="padding: 20px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
          <h3 style="margin: 0; font-size: 18px; font-weight: 700; color: #1e293b;">⚙️ 超级数据编辑覆盖 (Global_admin 专属)</h3>
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
              <span style="font-size: 13px; font-weight: 600; color: #475569;">装车接收换热站</span>
              <select v-model="superEditForm.stationId" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;">
                <option v-for="st in stationOptions" :key="st.station_id" :value="st.station_id">
                  {{ st.station_name }}
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
              <select v-model="superEditForm.status" class="input" style="padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;">
                <option value="pending_arrival">在途 (pending_arrival)</option>
                <option value="arrived">已到货待接收 (arrived)</option>
                <option value="received">现场已接收待库管确认 (received)</option>
                <option value="pending_warehouse">现场已接收待库管确认 (pending_warehouse)</option>
                <option value="completed">已入库已结清 (completed)</option>
                <option value="cancelled">已撤销废弃 (cancelled)</option>
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
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useAuthStore } from '../../daily_report_25_26/store/auth'
import { AppHeader, Breadcrumbs, useTubePageShell, useTubeRealtimeRefresh } from './shared'
import ExportSettingsModal from './ExportSettingsModal.vue'
import {
  cancelTubeSupplyManagementDelivery,
  createTubeSupplyManagementDeliveryBatch,
  getTubeSupplyManagementDeliveries,
  getTubeSupplyManagementDemandSummary,
  getTubeSupplyManagementOptions,
  superUpdateTubeSupplyManagementDelivery,
} from '../../daily_report_25_26/services/api'

const PROJECT_KEY = 'insulation_pipe_supply_2026'
const auth = useAuthStore()

const {
  loading,
  errorMessage,
  breadcrumbItems,
  goProjectPages,
} = useTubePageShell('供给侧管理入口')

const optionsLoading = ref(false)
const optionsError = ref('')
const supplyEntityOptions = ref([])
const stationOptions = ref([])
const pipeModelOptions = ref([])
const currentGroup = ref('')
const currentSupplyEntityIds = ref([])
const showDate = ref('')
const planStartDate = ref('')

const selectedSupplyEntityId = ref('')
const activeTab = ref('demand')
const supplyDemandViewMode = ref('summary')
const selectedPipeModelIds = ref([])

const summaryLoading = ref(false)
const summaryError = ref('')
const summaryRows = ref([])

const deliveriesLoading = ref(false)
const deliveriesError = ref('')
const deliveryRows = ref([])
const allDeliveryRows = ref([])
const showExportModal = ref(false)
const exportColumns = [
  { key: 'deliveryCode', label: '订单号' },
  { key: 'shipmentNo', label: '运输车次号' },
  { key: 'vehiclePlateNo', label: '车牌号' },
  { key: 'supplyEntityName', label: '供给主体' },
  { key: 'stationName', label: '装车接收换热站' },
  { key: 'pipeModelName', label: '保温管规格型号' },
  { key: 'shippedQty', label: '发货量（米）' },
  { key: 'arrivedQty', label: '到货量（米）' },
  { key: 'receivedQty', label: '接收量（米）' },
  { key: 'shippedAtDisplay', label: '发货时间' },
  { key: 'statusLabel', label: '状态' },
  { key: 'shipRemark', label: '备注' }
]
const cancelLoadingIds = ref({})
const nowTick = ref(Date.now())
let nowTimer = null

const submitDeliveryLoading = ref(false)
const actionMessage = ref(null)
const draftDeliveryItems = ref([])

const deliveryForm = ref(createDefaultDeliveryForm())

const canSubmitCurrentProject = computed(() => auth.canSubmitFor(PROJECT_KEY))
const canSwitchSupplyEntity = computed(() => currentGroup.value === 'Global_admin')

const currentGroupLabel = computed(() => {
  if (!currentGroup.value) return '未识别'
  if (currentGroup.value === 'Global_admin') return '全局管理员'
  if (currentGroup.value === 'tube_supplier') return '供给主体'
  return currentGroup.value
})

const currentSupplyEntityLabel = computed(() => {
  const matched = supplyEntityOptions.value.find((item) => item.entity_id === selectedSupplyEntityId.value)
  return matched?.entity_name || '未识别'
})

const currentDeliverySupplyEntityLabel = computed(() => {
  const matched = supplyEntityOptions.value.find((item) => item.entity_id === deliveryForm.value.supplyEntityId)
  return matched?.entity_name || currentSupplyEntityLabel.value
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

const supplyDemandViewOptions = computed(() => [
  { value: 'summary', label: '整理汇总' },
  { value: 'all_details', label: '全部换热站明细' },
  ...stationOptions.value.map((station) => ({
    value: station.station_id,
    label: station.station_name,
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
  if (supplyDemandViewMode.value === 'summary' || supplyDemandViewMode.value === 'all_details') {
    return pipeModelFilteredSummaryRows.value
  }
  return pipeModelFilteredSummaryRows.value.filter((row) => row.stationId === supplyDemandViewMode.value)
})

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
  return Array.from(grouped.values()).sort((a, b) => a.pipeModelName.localeCompare(b.pipeModelName, 'zh-CN'))
})

const supplyDemandTableRows = computed(() => {
  if (supplyDemandViewMode.value === 'summary') {
    return aggregatedSummaryRows.value
  }
  return filteredSummaryRows.value.map((row) => ({
    ...row,
    rowKey: `${row.stationId}-${row.pipeModelId}`,
    scopeLabel: row.stationName,
  }))
})

const supplyDemandTableHint = computed(() => {
  if (supplyDemandViewMode.value === 'summary') {
    return '当前以“整理汇总”方式按型号统计各项供需数量。计量单位：米。'
  }
  if (supplyDemandViewMode.value === 'all_details') {
    return '当前展示全部换热站的逐站逐型号明细。计量单位：米。'
  }
  const matched = stationOptions.value.find((item) => item.station_id === supplyDemandViewMode.value)
  return `当前仅展示 ${matched?.station_name || '所选换热站'} 的各型号供需记录。计量单位：米。`
})

function createDefaultDeliveryForm() {
  return {
    supplyEntityId: '',
    stationId: '',
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

function getStationName(stationId) {
  const matched = stationOptions.value.find((item) => item.station_id === stationId)
  return matched?.station_name || stationId || '—'
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
    stations: response.stations || [],
    pipeModels: response.pipe_models || [],
    showDate: response.show_date || response.biz_date || '',
    planStartDate: response.plan_start_date || '',
    currentSupplyEntityIds: response.current_supply_entity_ids || [],
  }
}

function normalizeSummaryRows(rows) {
  return (rows || []).map((row) => ({
    stationId: row.station_id || '',
    stationName: row.station_name || row.station_id || '未命名换热站',
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
  if (status === 'pending_arrival') return '已发货待到货'
  if (status === 'pending_receive') return '已到货待接收'
  if (status === 'pending_warehouse') return '已接收待库管确认'
  if (status === 'completed') return '已完成'
  if (status === 'cancelled') return '已撤销'
  return status || '未知状态'
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
    stationId: row.station_id || '',
    stationName: row.station_name || row.station_id || '—',
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
    stationId: deliveryForm.value.stationId || '',
    stationName: getStationName(deliveryForm.value.stationId),
    pipeModelId: deliveryForm.value.pipeModelId || '',
    pipeModelName: getPipeModelName(deliveryForm.value.pipeModelId),
    shippedQty: Number(deliveryForm.value.shippedQty || 0),
    shipRemark: deliveryForm.value.shipRemark || '',
  }
}

function validateCurrentDeliveryForm() {
  if (!deliveryForm.value.supplyEntityId || !deliveryForm.value.stationId || !deliveryForm.value.pipeModelId) {
    setActionMessage('error', '请先完整选择供给主体、换热站和保温管型号。')
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
    stationOptions.value = normalized.stations
    pipeModelOptions.value = normalized.pipeModels
    currentSupplyEntityIds.value = normalized.currentSupplyEntityIds
    showDate.value = normalized.showDate
    planStartDate.value = normalized.planStartDate
    const availableSupplyEntityIds = normalized.currentSupplyEntityIds
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
    const stationIdSet = new Set(stationOptions.value.map((item) => String(item.station_id || '')))
    const pipeModelIdSet = new Set(pipeModelOptions.value.map((item) => String(item.pipe_model_id || '')))
    if (!stationIdSet.has(deliveryForm.value.stationId)) {
      deliveryForm.value.stationId = stationOptions.value[0]?.station_id || ''
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
  await Promise.all([loadDemandSummary(), loadDeliveries()])
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
  deliveryForm.value.stationId = ''
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
    station_id: item.stationId,
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
  cancelLoadingIds.value = {
    ...cancelLoadingIds.value,
    [row.deliveryId]: true,
  }
  clearActionMessage()
  try {
    await cancelTubeSupplyManagementDelivery(PROJECT_KEY, row.deliveryId, {
      cancel_reason: '供给侧主动撤销发货',
    })
    setActionMessage('success', `发货记录 ${row.deliveryCode} 已撤销。`)
    await Promise.all([loadDemandSummary(), loadDeliveries()])
  } catch (error) {
    setActionMessage('error', error?.message || '撤销发货记录失败')
  } finally {
    cancelLoadingIds.value = {
      ...cancelLoadingIds.value,
      [row.deliveryId]: false,
    }
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
    const matchedEntity = supplyEntityOptions.value.find((item) => item.entity_id === value)
    if (matchedEntity) {
      if (!deliveryForm.value.shipContactName) {
        deliveryForm.value.shipContactName = matchedEntity.contact_name || ''
      }
      if (!deliveryForm.value.shipContactPhone) {
        deliveryForm.value.shipContactPhone = matchedEntity.contact_phone || ''
      }
    }
    loadDeliveries()
  }
}, { immediate: true })

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
  await refreshRealtimeConfig()
})

useTubeRealtimeRefresh(refreshRealtimeConfig)

onBeforeUnmount(() => {
  if (nowTimer) {
    clearInterval(nowTimer)
    nowTimer = null
  }
})

const showSuperEditModal = ref(false)
const superEditSaving = ref(false)
const superEditError = ref('')
const superEditForm = ref({
  deliveryId: 0,
  stationId: '',
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
})

function openSuperEdit(row) {
  superEditError.value = ''
  let formattedTime = ''
  if (row.shippedAt) {
    const d = new Date(row.shippedAt)
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const date = String(d.getDate()).padStart(2, '0')
    const hours = String(d.getHours()).padStart(2, '0')
    const minutes = String(d.getMinutes()).padStart(2, '0')
    formattedTime = `${year}-${month}-${date}T${hours}:${minutes}`
  }
  
  superEditForm.value = {
    deliveryId: row.deliveryId,
    stationId: row.stationId || '',
    pipeModelId: row.pipeModelId || '',
    shippedQty: row.shippedQty || 0,
    shippedAt: formattedTime,
    vehiclePlateNo: row.vehiclePlateNo || '',
    shipRemark: row.shipRemark || '',
    status: row.status || '',
    orderNo: row.deliveryCode || '',
    shipmentNo: row.shipmentNo || '',
    arrivedQty: row.arrivedQty ?? null,
    receivedQty: row.receivedQty ?? null,
  }
  showSuperEditModal.value = true
}

async function saveSuperEdit() {
  superEditError.value = ''
  superEditSaving.value = true
  try {
    const shippedAtIso = superEditForm.value.shippedAt ? new Date(superEditForm.value.shippedAt).toISOString() : new Date().toISOString()
    await superUpdateTubeSupplyManagementDelivery(PROJECT_KEY, superEditForm.value.deliveryId, {
      station_id: superEditForm.value.stationId,
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
</script>

<style scoped>
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

.delivery-record-table .col-station {
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

  .topbar,
  .panel-title-row {
    flex-direction: column;
    align-items: stretch;
  }

  .topbar-actions {
    width: 100%;
  }

  .toolbar-actions {
    width: 100%;
    justify-content: stretch;
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

/* Vue Tabs 高端样式切换 */
.tube-tabs-header-wrap {
  background: rgba(241, 245, 249, 0.8) !important;
  border-radius: 14px !important;
  padding: 6px !important;
  margin-top: 8px !important;
  margin-bottom: 16px !important;
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

.station-tag {
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
</style>
