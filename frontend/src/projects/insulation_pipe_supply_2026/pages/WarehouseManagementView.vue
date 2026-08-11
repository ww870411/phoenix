<template>
  <div class="tube-page-root">
    <AppHeader />
    <main class="tube-page-main container">
      <Breadcrumbs :items="breadcrumbItems" />

      <header class="topbar">
        <div>
          <h2>库管员管理入口</h2>
          <p class="sub">用于接收发货、确认施工接收并完成库管手续闭环。</p>
        </div>
        <div class="topbar-actions">
          <button class="btn ghost" type="button" @click="goProjectPages">返回功能页</button>
          <button class="btn primary" type="button" :disabled="loading" @click="reloadAll">刷新台账</button>
        </div>
      </header>

      <p v-if="pageError || shellError" class="page-error">{{ pageError || shellError }}</p>
      <p v-if="pageMessage" class="page-success">{{ pageMessage }}</p>

      <!-- Segmented Control Tabs 导航 (位于“库管台账筛选”卡片正上方) -->
      <div style="margin-top: 16px; margin-bottom: 16px; display: flex; align-items: center;">
        <div style="background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 12px; padding: 4px; display: inline-flex; gap: 4px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.03);">
          <button 
            type="button" 
            :style="activeTab === 'pipe' ? {
              background: '#ffffff',
              color: '#4f46e5',
              fontWeight: '700',
              boxShadow: '0 2px 8px rgba(79, 70, 229, 0.15)',
              border: '1px solid #c7d2fe',
              borderRadius: '8px'
            } : {
              background: 'transparent',
              color: '#64748b',
              fontWeight: '500',
              border: '1px solid transparent',
              borderRadius: '8px'
            }"
            style="padding: 10px 24px; font-size: 14.5px; cursor: pointer; transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); display: flex; align-items: center; gap: 8px;"
            @click="activeTab = 'pipe'"
          >
            <span style="font-size: 16px;">🔥</span> 保温管发货记录
          </button>
          <button 
            type="button" 
            :style="activeTab === 'fitting' ? {
              background: '#ffffff',
              color: '#2563eb',
              fontWeight: '700',
              boxShadow: '0 2px 8px rgba(37, 99, 235, 0.15)',
              border: '1px solid #bfdbfe',
              borderRadius: '8px'
            } : {
              background: 'transparent',
              color: '#64748b',
              fontWeight: '500',
              border: '1px solid transparent',
              borderRadius: '8px'
            }"
            style="padding: 10px 24px; font-size: 14.5px; cursor: pointer; transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); display: flex; align-items: center; gap: 8px;"
            @click="handleSwitchToFittingTab"
          >
            <span style="font-size: 16px;">🔧</span> 管件发货记录
          </button>
        </div>
      </div>

      <section class="card elevated">
        <div class="card-header">
          <span>库管台账筛选</span>
          <span class="muted">展示日期：{{ options?.show_date || options?.biz_date || '--' }}</span>
        </div>
        <div class="filter-grid">
          <div class="field custom-multi-select-container" ref="section1DropdownRef">
            <span>需求主体</span>
            <div class="custom-multi-select">
              <div class="select-trigger" @click="toggleDropdown('section1')" :class="{ active: activeDropdown === 'section1' }">
                <span class="trigger-text" :class="{ placeholder: filters.section1Ids.length === 0 }">
                  {{ displaySelectedSection1s }}
                </span>
                <span class="trigger-arrow">▼</span>
              </div>
              <transition name="dropdown-fade">
                <div v-if="activeDropdown === 'section1'" class="select-dropdown">
                  <div class="dropdown-actions">
                    <button type="button" class="action-btn" @click="selectAllSection1s">全选</button>
                    <button type="button" class="action-btn" @click="clearAllSection1s">清空</button>
                  </div>
                  <div class="dropdown-list">
                    <div 
                      v-for="item in section1Options" 
                      :key="item.section_1_id" 
                      class="dropdown-item"
                      :class="{ selected: filters.section1Ids.includes(item.section_1_id) }"
                      @click="toggleSection1(item.section_1_id)"
                    >
                      <input type="checkbox" :checked="filters.section1Ids.includes(item.section_1_id)" @click.stop="toggleSection1(item.section_1_id)" />
                      <span class="item-label">{{ item.section_1_name }}（{{ item.section_1_id }}）</span>
                    </div>
                  </div>
                </div>
              </transition>
            </div>
          </div>

          <div class="field custom-multi-select-container" ref="supplyDropdownRef">
            <span>供给主体</span>
            <div class="custom-multi-select">
              <div class="select-trigger" @click="toggleDropdown('supplier')" :class="{ active: activeDropdown === 'supplier' }">
                <span class="trigger-text" :class="{ placeholder: filters.supplyEntityIds.length === 0 }">
                  {{ displaySelectedSupplyEntities }}
                </span>
                <span class="trigger-arrow">▼</span>
              </div>
              <transition name="dropdown-fade">
                <div v-if="activeDropdown === 'supplier'" class="select-dropdown">
                  <div class="dropdown-actions">
                    <button type="button" class="action-btn" @click="selectAllSupplyEntities">全选</button>
                    <button type="button" class="action-btn" @click="clearAllSupplyEntities">清空</button>
                  </div>
                  <div class="dropdown-list">
                    <div 
                      v-for="item in supplyEntityOptions" 
                      :key="item.entity_id" 
                      class="dropdown-item"
                      :class="{ selected: filters.supplyEntityIds.includes(item.entity_id) }"
                      @click="toggleSupplyEntity(item.entity_id)"
                    >
                      <input type="checkbox" :checked="filters.supplyEntityIds.includes(item.entity_id)" @click.stop="toggleSupplyEntity(item.entity_id)" />
                      <span class="item-label">{{ item.entity_name }}（{{ item.entity_id }}）</span>
                    </div>
                  </div>
                </div>
              </transition>
            </div>
          </div>

          <div class="field custom-multi-select-container" ref="pipeDropdownRef">
            <span>型号</span>
            <div class="custom-multi-select">
              <div 
                class="select-trigger" 
                :class="{ active: activeDropdown === 'pipeModel', disabled: activeTab === 'fitting' }"
                :style="activeTab === 'fitting' ? { background: '#f1f5f9', cursor: 'not-allowed', opacity: 0.7, borderColor: '#e2e8f0' } : {}"
                @click="toggleDropdown('pipeModel')"
              >
                <span class="trigger-text" :class="{ placeholder: filters.pipeModelIds.length === 0 || activeTab === 'fitting' }">
                  {{ displaySelectedPipeModels }}
                </span>
                <span class="trigger-arrow">{{ activeTab === 'fitting' ? '🔒' : '▼' }}</span>
              </div>
              <transition name="dropdown-fade">
                <div v-if="activeDropdown === 'pipeModel' && activeTab !== 'fitting'" class="select-dropdown">
                  <div class="dropdown-actions">
                    <button type="button" class="action-btn" @click="selectAllPipeModels">全选</button>
                    <button type="button" class="action-btn" @click="clearAllPipeModels">清空</button>
                  </div>
                  <div class="dropdown-list">
                    <template v-for="group in groupedPipeModelOptions" :key="group.name">
                      <div class="dropdown-group-header" style="padding: 6px 10px; background: #f8fafc; font-size: 11px; font-weight: bold; color: #4f46e5; border-top: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; user-select: none;">
                        <span>♨️ {{ group.name }}</span>
                        <span style="font-size: 10px; color: #64748b; font-weight: normal;">共 {{ group.items.length }} 种规格</span>
                      </div>
                      <div 
                        v-for="item in group.items" 
                        :key="item.pipe_model_id" 
                        class="dropdown-item"
                        :class="{ selected: filters.pipeModelIds.includes(item.pipe_model_id) }"
                        @click="togglePipeModel(item.pipe_model_id)"
                      >
                        <input type="checkbox" :checked="filters.pipeModelIds.includes(item.pipe_model_id)" @click.stop="togglePipeModel(item.pipe_model_id)" />
                        <span class="item-label">{{ item.pipe_model_name }}</span>
                      </div>
                    </template>
                  </div>
                </div>
              </transition>
            </div>
          </div>

          <div class="field custom-multi-select-container" ref="statusDropdownRef">
            <span>状态</span>
            <div class="custom-multi-select">
              <div 
                class="select-trigger" 
                :class="{ active: activeDropdown === 'status', disabled: activeTab === 'fitting' }"
                :style="activeTab === 'fitting' ? { background: '#f1f5f9', cursor: 'not-allowed', opacity: 0.7, borderColor: '#e2e8f0' } : {}"
                @click="toggleDropdown('status')"
              >
                <span class="trigger-text" :class="{ placeholder: filters.statuses.length === 0 || activeTab === 'fitting' }">
                  {{ displaySelectedStatuses }}
                </span>
                <span class="trigger-arrow">{{ activeTab === 'fitting' ? '🔒' : '▼' }}</span>
              </div>
              <transition name="dropdown-fade">
                <div v-if="activeDropdown === 'status' && activeTab !== 'fitting'" class="select-dropdown">
                  <div class="dropdown-actions">
                    <button type="button" class="action-btn" @click="selectAllStatuses">全选</button>
                    <button type="button" class="action-btn" @click="clearAllStatuses">清空</button>
                  </div>
                  <div class="dropdown-list">
                    <div 
                      v-for="item in deliveryStatusOptions" 
                      :key="item.value" 
                      class="dropdown-item"
                      :class="{ selected: filters.statuses.includes(item.value) }"
                      @click="toggleStatus(item.value)"
                    >
                      <input type="checkbox" :checked="filters.statuses.includes(item.value)" @click.stop="toggleStatus(item.value)" />
                      <span class="item-label">{{ item.label }}</span>
                    </div>
                  </div>
                </div>
              </transition>
            </div>
          </div>
          <label class="field">
            <span>运输车次号</span>
            <input v-model.trim="filters.shipmentNo" class="input" type="text" placeholder="输入车次号筛选" />
          </label>
          <label class="field">
            <span>单号</span>
            <input v-model.trim="filters.orderNo" class="input" type="text" placeholder="输入订单号筛选" />
          </label>
          <label class="field">
            <span>车牌号</span>
            <input v-model.trim="filters.vehiclePlateNo" class="input" type="text" placeholder="输入车牌号筛选" />
          </label>
        </div>
        <div class="filter-actions" style="display: flex; gap: 8px;">
          <button class="btn primary" type="button" :disabled="loading" @click="loadDeliveries">查询</button>
          <button class="btn ghost" type="button" :disabled="loading" @click="resetFilters">重置</button>
          <button 
            v-if="activeTab === 'pipe' && deliveries.length > 0" 
            class="btn primary" 
            type="button" 
            style="background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important; color: #fff !important; border: none !important; font-weight: 600;" 
            @click="showExportModal = true"
          >
            📥 导出 Excel
          </button>
        </div>
      </section>

      <!-- Tab 1: 保温管发货记录 -->
      <div v-if="activeTab === 'pipe'">
        <section class="card elevated stats-card">
          <div class="card-header">台账概览</div>
        <div class="stats-grid">
          <div class="stat-box">
            <span>记录总数</span>
            <strong>{{ deliverySummary.total }}</strong>
          </div>
          <div class="stat-box">
            <span>待到货</span>
            <strong>{{ deliverySummary.pendingArrival }}</strong>
          </div>
          <div class="stat-box">
            <span>待接收</span>
            <strong>{{ deliverySummary.pendingReceive }}</strong>
          </div>
          <div class="stat-box">
            <span>待库管</span>
            <strong>{{ deliverySummary.pendingWarehouse }}</strong>
          </div>
          <div class="stat-box">
            <span>已完成</span>
            <strong>{{ deliverySummary.completed }}</strong>
          </div>
          <div class="stat-box">
            <span>已撤销</span>
            <strong>{{ deliverySummary.cancelled }}</strong>
          </div>
        </div>
      </section>

      <section class="card elevated">
        <div class="card-header">库管发货台账</div>
        <div v-if="loading" class="page-state">正在读取库管台账...</div>
        <div v-else-if="deliveries.length === 0" class="page-state">当前筛选条件下没有记录。</div>
        <div v-else class="table-wrap">
          <table class="table">
            <colgroup>
              <col class="col-checkbox" />
              <col class="col-order" />
              <col class="col-shipment" />
              <col class="col-plate" />
              <col class="col-supply" />
              <col class="col-section1" />
              <col class="col-model" />
              <col class="col-qty" />
              <col class="col-qty" />
              <col class="col-qty" />
              <col class="col-status" />
              <col class="col-time" />
              <col class="col-elapsed" />
            </colgroup>
            <thead>
              <tr>
                <th class="cell-checkbox">
                  <input
                    type="checkbox"
                    :checked="allPendingWarehouseSelected"
                    :indeterminate.prop="hasPartialPendingWarehouseSelection"
                    @change="toggleSelectAllPendingWarehouse($event)"
                  />
                </th>
                <th>订单号</th>
                <th>运输车次号</th>
                <th class="cell-plate-header">车牌号</th>
                <th>供给主体</th>
                <th>需求主体</th>
                <th>型号</th>
                <th class="cell-number">发货量（米）</th>
                <th class="cell-number">到货量（米）</th>
                <th class="cell-number">接收量（米）</th>
                <th class="cell-status">状态</th>
                <th class="cell-datetime">发货时间</th>
                <th class="cell-elapsed">在途时长</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in deliveries"
                :key="row.id"
                :class="{ checked: isDeliverySelected(row.id), active: String(row.id) === selectedDeliveryId }"
                @click="toggleDeliverySelection(row)"
              >
                <td class="cell-checkbox">
                  <input
                    v-if="row.status === 'pending_warehouse'"
                    type="checkbox"
                    :checked="isDeliverySelected(row.id)"
                    @click.stop
                    @change="toggleDeliverySelection(row)"
                  />
                </td>
                <td class="cell-code-wrapper">
                  <span class="cell-code">{{ row.order_no || row.delivery_code || row.id }}</span>
                </td>
                <td class="cell-code-wrapper">
                  <span class="cell-code">{{ row.shipment_no || '—' }}</span>
                </td>
                <td class="cell-plate">
                  <span class="plate-badge">{{ row.vehicle_plate_no || '—' }}</span>
                </td>
                <td class="cell-supply" :title="row.supply_entity_name">{{ row.supply_entity_name }}</td>
                <td class="cell-section1" :title="row.section_1_name">{{ row.section_1_name }}</td>
                <td class="cell-model" :title="row.pipe_model_name">{{ row.pipe_model_name }}</td>
                <td class="cell-number">{{ formatAmount(row.shipped_qty) }}</td>
                <td class="cell-number">{{ formatOptionalAmount(row.arrived_qty) }}</td>
                <td class="cell-number">{{ formatOptionalAmount(row.received_qty) }}</td>
                <td class="cell-status">
                  <div class="status-pill-group">
                    <span class="status-pill" :class="statusClass(row.status)">
                      {{ deliveryStatusLabelMap[row.status] || row.status || '--' }}
                    </span>
                    <span v-if="row.abnormal_flag" class="status-pill status-abnormal">
                      {{ getAbnormalLabel(row) }}
                    </span>
                  </div>
                </td>
                <td class="cell-datetime">{{ formatDateTime(row.shipped_at) }}</td>
                <td class="cell-elapsed">{{ formatDeliveryElapsedDisplay(row) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card elevated" style="padding: 24px;">
        <div class="card-header" style="border-bottom: 1px solid #f1f5f9; padding-bottom: 12px; margin-bottom: 20px;">
          <span style="font-size: 16px; font-weight: 700; color: #0f172a; display: flex; align-items: center; gap: 6px;">
            💼 库管操作与全生命周期证据链
          </span>
        </div>
        
        <div class="double-panel-layout" style="display: flex; gap: 24px; flex-wrap: wrap; width: 100%; box-sizing: border-box;">
          <!-- 左侧：批量处置操作面板 (占 42%) -->
          <div class="left-panel" style="flex: 42; min-width: 320px; display: flex; flex-direction: column; gap: 16px; border-right: 1px solid #e2e8f0; padding-right: 24px; box-sizing: border-box;">
            <h4 style="margin: 0; font-size: 14px; font-weight: 600; color: #475569; display: flex; align-items: center; gap: 6px;">
              <span>⚡ 批量入库确认</span>
            </h4>
            
            <div v-if="!selectedDeliveries.length" class="empty-action-tip" style="padding: 30px 20px; text-align: center; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 12px; display: flex; flex-direction: column; align-items: center; gap: 10px; box-sizing: border-box;">
              <span style="font-size: 28px;">💡</span>
              <span style="font-size: 13px; color: #64748b; line-height: 1.6;">提示：请勾选列表中状态为“已接收待库管”的发货记录以执行批量入库确认。</span>
            </div>
            
            <div v-else class="action-panel" style="display: flex; flex-direction: column; gap: 16px; width: 100%; box-sizing: border-box;">
              <div class="action-summary" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; width: 100%; box-sizing: border-box;">
                <div style="display: flex; flex-direction: column; padding: 10px 12px; border-radius: 8px; background: #f8fafc; border: 1px solid #e2e8f0; box-sizing: border-box;">
                  <span style="font-size: 12px; color: #64748b; margin-bottom: 4px;">已勾选记录</span>
                  <strong style="font-size: 16px; color: #1e293b;">{{ selectedDeliveryAggregate.totalRecords }} 条</strong>
                </div>
                <div style="display: flex; flex-direction: column; padding: 10px 12px; border-radius: 8px; background: #f8fafc; border: 1px solid #e2e8f0; box-sizing: border-box;">
                  <span style="font-size: 12px; color: #64748b; margin-bottom: 4px;">总发货长度</span>
                  <strong style="font-size: 16px; color: #1e293b;">{{ formatAmount(selectedDeliveryAggregate.totalShippedQty) }} 米</strong>
                </div>
                <div style="display: flex; flex-direction: column; padding: 10px 12px; border-radius: 8px; background: #f8fafc; border: 1px solid #e2e8f0; box-sizing: border-box;">
                  <span style="font-size: 12px; color: #64748b; margin-bottom: 4px;">总物理接收</span>
                  <strong style="font-size: 16px; color: #1e293b;">{{ formatAmount(selectedDeliveryAggregate.totalReceivedQty) }} 米</strong>
                </div>
                <div style="display: flex; flex-direction: column; padding: 10px 12px; border-radius: 8px; background: #f8fafc; border: 1px solid #e2e8f0; box-sizing: border-box;">
                  <span style="font-size: 12px; color: #64748b; margin-bottom: 4px;">在途平均用时</span>
                  <strong style="font-size: 14px; color: #1e293b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" :title="selectedDeliveryAggregate.averageElapsedLabel">{{ selectedDeliveryAggregate.averageElapsedLabel }}</strong>
                </div>
              </div>
              
              <div v-if="pendingWarehouseSelectedDeliveries.length" class="form-grid" style="display: flex; flex-direction: column; gap: 12px; margin-top: 8px; width: 100%; box-sizing: border-box;">
                <label class="field" style="display: flex; flex-direction: column; gap: 6px;">
                  <span style="font-size: 13px; font-weight: 600; color: #475569;">✍️ 批量库管入库备注 (选填)</span>
                  <textarea v-model="warehouseForm.remark" class="textarea" rows="3" placeholder="可在此处统一填写这批量入库单的凭证说明或手续情况..." style="font-size: 13px; line-height: 1.5;"></textarea>
                </label>
                <button class="btn primary" type="button" :disabled="actionLoading" @click="submitWarehouse" style="width: 100%; padding: 12px; background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%); color: #ffffff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2); display: inline-flex; align-items: center; justify-content: center; gap: 6px;">
                  <span>{{ actionLoading ? '⏳ 正在提交确认...' : `💾 确认完成库管入库 (${pendingWarehouseSelectedDeliveries.length}条)` }}</span>
                </button>
              </div>
              
              <div v-else class="page-state compact" style="background: #fff8f8; border: 1px solid #ffe4e6; color: #b91c1c; border-radius: 8px; padding: 12px; font-size: 13px; text-align: center; font-weight: 500;">
                ⚠️ 当前勾选的记录中没有“已接收待库管”状态数据，无法执行入库确认。
              </div>
            </div>
          </div>
          
          <!-- 右侧：全生命周期流转时光轴 (占 58%) -->
          <div class="right-panel" style="flex: 58; min-width: 380px; display: flex; flex-direction: column; gap: 16px; box-sizing: border-box;">
            <h4 style="margin: 0; font-size: 14px; font-weight: 600; color: #475569; display: flex; justify-content: space-between; align-items: center;">
              <span>⏳ 运输单全生命周期流转轨迹</span>
              <span v-if="selectedDelivery" style="font-size: 12px; background: #e2e8f0; color: #475569; padding: 2px 8px; border-radius: 99px; font-weight: 500; font-family: monospace;">
                ID: {{ selectedDelivery.order_no || selectedDelivery.delivery_code || selectedDelivery.id }}
              </span>
            </h4>
            
            <div v-if="!selectedDelivery" class="empty-timeline-tip" style="padding: 40px 20px; text-align: center; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 12px; display: flex; flex-direction: column; align-items: center; gap: 10px; justify-content: center; height: 100%; min-height: 220px; box-sizing: border-box;">
              <span style="font-size: 28px;">🔍</span>
              <span style="font-size: 13px; color: #64748b; line-height: 1.6;">提示：点击上方列表中的任意一行记录，即可在此处瞬时查看其全生命周期闭环证据链与流转状态。</span>
            </div>
            
            <div v-else class="timeline-container" style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; position: relative; box-sizing: border-box; width: 100%;">
              <!-- 顶部信息摘要 -->
              <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 20px; background: #f8fafc; padding: 12px; border-radius: 8px; border: 1px solid #f1f5f9; box-sizing: border-box;">
                <div>
                  <div style="font-size: 11px; color: #64748b; margin-bottom: 2px;">车牌号</div>
                  <div style="font-size: 13px; font-weight: 600; color: #1e293b; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ selectedDelivery.vehicle_plate_no || '—' }}</div>
                </div>
                <div>
                  <div style="font-size: 11px; color: #64748b; margin-bottom: 2px;">规格型号</div>
                  <div style="font-size: 13px; font-weight: 600; color: #1e293b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" :title="selectedDelivery.pipe_model_name">{{ selectedDelivery.pipe_model_name || '—' }}</div>
                </div>
                <div>
                  <div style="font-size: 11px; color: #64748b; margin-bottom: 2px;">当前状态</div>
                  <div style="white-space: nowrap; overflow: hidden;">
                    <span :class="['status-pill', statusClass(selectedDelivery.status)]" style="padding: 2px 6px; font-size: 11px;">
                      {{ deliveryStatusLabelMap[selectedDelivery.status] || selectedDelivery.status }}
                    </span>
                  </div>
                </div>
              </div>
              
              <!-- 运输单 Timeline 时光轴 -->
              <div class="vertical-timeline" style="position: relative; padding-left: 24px; display: flex; flex-direction: column; gap: 20px; box-sizing: border-box;">
                <!-- 垂直连接虚线 -->
                <div style="position: absolute; left: 7px; top: 8px; bottom: 8px; width: 2px; border-left: 2px dashed #cbd5e1; z-index: 1;"></div>
                
                <!-- 1. 发货阶段 -->
                <div style="position: relative; z-index: 2;">
                  <span style="position: absolute; left: -24px; top: 2px; width: 16px; height: 16px; border-radius: 99px; background: #4f46e5; border: 3px solid #ffffff; box-shadow: 0 0 0 2px #4f46e5; display: inline-block;"></span>
                  <div style="display: flex; flex-direction: column; gap: 4px; box-sizing: border-box;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
                      <span style="font-size: 13px; font-weight: 700; color: #1e293b;">📦 供给侧装车发货</span>
                      <span style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTime(selectedDelivery.shipped_at) }}</span>
                    </div>
                    <div style="font-size: 12px; color: #475569; display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; margin-top: 2px; background: #fafafa; padding: 8px; border-radius: 6px; box-sizing: border-box; width: 100%;">
                      <div>发货量：<strong style="color: #0f172a;">{{ formatAmount(selectedDelivery.shipped_qty) }} 米</strong></div>
                      <div>操作账号：<span>{{ selectedDelivery.created_by || '供给端系统' }}</span></div>
                      <div>经办人：<span>{{ selectedDelivery.ship_contact_name || '—' }}</span></div>
                      <div style="grid-column: span 2;">联系电话：<span>{{ selectedDelivery.ship_contact_phone || '—' }}</span></div>
                      <div style="grid-column: span 2;">供给主体：<span>{{ selectedDelivery.supply_entity_name || '—' }} ({{ selectedDelivery.supply_entity_id || '—' }})</span></div>
                      <div style="grid-column: span 2; word-break: break-all;" v-if="selectedDelivery.ship_remark || selectedDelivery.cancel_reason">发货备注：<span style="color: #64748b; font-style: italic;">“{{ selectedDelivery.ship_remark || selectedDelivery.cancel_reason }}”</span></div>
                    </div>
                  </div>
                </div>
                
                <!-- 2. 到货确认阶段 -->
                <div style="position: relative; z-index: 2;">
                  <span :style="{
                    position: 'absolute', left: '-24px', top: '2px', width: '16px', height: '16px', borderRadius: '99px',
                    background: selectedDelivery.arrived_confirm_at ? '#10b981' : '#cbd5e1',
                    border: '3px solid #ffffff',
                    boxShadow: '0 0 0 2px ' + (selectedDelivery.arrived_confirm_at ? '#10b981' : '#cbd5e1'),
                    display: 'inline-block'
                  }"></span>
                  <div style="display: flex; flex-direction: column; gap: 4px; box-sizing: border-box;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
                      <span :style="{ fontSize: '13px', fontWeight: '700', color: selectedDelivery.arrived_confirm_at ? '#1e293b' : '#94a3b8' }">🚚 物流卸车到货确认</span>
                      <span v-if="selectedDelivery.arrived_confirm_at" style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTime(selectedDelivery.arrived_confirm_at) }}</span>
                      <span v-else style="font-size: 11px; color: #94a3b8; font-style: italic;">等待节点确认...</span>
                    </div>
                    <div v-if="selectedDelivery.arrived_confirm_at" style="font-size: 12px; color: #475569; display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; margin-top: 2px; background: #fafafa; padding: 8px; border-radius: 6px; box-sizing: border-box; width: 100%;">
                      <div>到货量：<strong style="color: #0f172a;">{{ formatAmount(selectedDelivery.arrived_qty) }} 米</strong></div>
                      <div>操作账号：<span style="font-weight: 500; color: #0f766e;">{{ selectedDelivery.arrived_confirm_by || '—' }}</span></div>
                      <div>经办人：<span>{{ selectedDelivery.arrived_confirm_name || '—' }}</span></div>
                      <div style="grid-column: span 2;" v-if="selectedDelivery.arrived_confirm_phone">联系电话：<span>{{ selectedDelivery.arrived_confirm_phone }}</span></div>
                      <div style="grid-column: span 2;">需求主体：<span>{{ selectedDelivery.section_1_name || '—' }} ({{ selectedDelivery.section_1_id || '—' }})</span></div>
                      <div style="grid-column: span 2; word-break: break-all;" v-if="selectedDelivery.arrived_remark">到货备注：<span style="color: #64748b; font-style: italic;">“{{ selectedDelivery.arrived_remark }}”</span></div>
                    </div>
                  </div>
                </div>
                
                <!-- 3. 施工接收阶段 -->
                <div style="position: relative; z-index: 2;">
                  <span :style="{
                    position: 'absolute', left: '-24px', top: '2px', width: '16px', height: '16px', borderRadius: '99px',
                    background: selectedDelivery.received_confirm_at || selectedDelivery.status === 'pending_diff_approve' ? '#8b5cf6' : '#cbd5e1',
                    border: '3px solid #ffffff',
                    boxShadow: '0 0 0 2px ' + (selectedDelivery.received_confirm_at || selectedDelivery.status === 'pending_diff_approve' ? '#8b5cf6' : '#cbd5e1'),
                    display: 'inline-block'
                  }"></span>
                  <div style="display: flex; flex-direction: column; gap: 4px; box-sizing: border-box;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
                      <span :style="{ fontSize: '13px', fontWeight: '700', color: selectedDelivery.received_confirm_at || selectedDelivery.status === 'pending_diff_approve' ? '#1e293b' : '#94a3b8' }">📐 施工物理接收确认</span>
                      <span v-if="selectedDelivery.received_confirm_at" style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTime(selectedDelivery.received_confirm_at) }}</span>
                      <span v-else-if="selectedDelivery.status === 'pending_diff_approve'" style="font-size: 11px; color: #f97316; font-weight: bold; font-style: italic;">⌛ 施工已上报待审批</span>
                      <span v-else style="font-size: 11px; color: #94a3b8; font-style: italic;">等待节点确认...</span>
                    </div>
                    <div v-if="selectedDelivery.received_confirm_at || selectedDelivery.status === 'pending_diff_approve'" style="font-size: 12px; color: #475569; display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; margin-top: 2px; background: #fafafa; padding: 8px; border-radius: 6px; box-sizing: border-box; width: 100%;">
                      <div>接收量：<strong style="color: #0f172a;">{{ formatAmount(selectedDelivery.received_qty) }} 米</strong></div>
                      <div>操作账号：<span style="font-weight: 500; color: #6d28d9;">{{ selectedDelivery.received_confirm_by || '—' }}</span></div>
                      <div>经办人：<span>{{ selectedDelivery.received_confirm_name || '—' }}</span></div>
                      <div style="grid-column: span 2;" v-if="selectedDelivery.received_confirm_phone">联系电话：<span>{{ selectedDelivery.received_confirm_phone }}</span></div>
                      <div style="grid-column: span 2;">需求主体：<span>{{ selectedDelivery.section_1_name || '—' }} ({{ selectedDelivery.section_1_id || '—' }})</span></div>
                      <div style="grid-column: span 2; word-break: break-all;" v-if="selectedDelivery.received_remark">接收备注：<span style="color: #64748b; font-style: italic;">“{{ selectedDelivery.received_remark }}”</span></div>
                      <div style="grid-column: span 2; color: #f97316; font-weight: 500;" v-if="selectedDelivery.is_timeout_receive">
                        🕒 提示：该订单由系统触发 [12小时超时强制自动确认接收]。
                      </div>
                    </div>
                  </div>
                </div>
                
                <!-- 4. 差异审批阶段 -->
                <div v-if="selectedDelivery.diff_approve_by || selectedDelivery.status === 'pending_diff_approve'" style="position: relative; z-index: 2;">
                  <span :style="{
                    position: 'absolute', left: '-24px', top: '2px', width: '16px', height: '16px', borderRadius: '99px',
                    background: selectedDelivery.diff_approve_by ? '#f97316' : '#cbd5e1',
                    border: '3px solid #ffffff',
                    boxShadow: '0 0 0 2px ' + (selectedDelivery.diff_approve_by ? '#f97316' : '#cbd5e1'),
                    display: 'inline-block'
                  }"></span>
                  <div style="display: flex; flex-direction: column; gap: 4px; box-sizing: border-box;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
                      <span :style="{ fontSize: '13px', fontWeight: '700', color: selectedDelivery.diff_approve_by ? '#1e293b' : '#94a3b8' }">🛡️ 现场负责人差异审批</span>
                      <span v-if="selectedDelivery.diff_approve_at" style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTime(selectedDelivery.diff_approve_at) }}</span>
                      <span v-else style="font-size: 11px; color: #f97316; font-weight: bold; font-style: italic;">⚠️ 挂起待审批...</span>
                    </div>
                    <div v-if="selectedDelivery.diff_approve_by" style="font-size: 12px; color: #475569; display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; margin-top: 2px; background: #fafafa; padding: 8px; border-radius: 6px; box-sizing: border-box; width: 100%;">
                      <div>审批人：<strong style="color: #0f172a;">{{ selectedDelivery.diff_approve_by }}</strong></div>
                      <div>审批时间：<span>{{ formatDateTime(selectedDelivery.diff_approve_at) }}</span></div>
                      <div style="grid-column: span 2; word-break: break-all;" v-if="selectedDelivery.diff_approve_remark">审批意见：<span style="color: #ea580c; font-weight: 500;">{{ selectedDelivery.diff_approve_remark }}</span></div>
                    </div>
                  </div>
                </div>
                
                <!-- 5. 库管入库阶段 -->
                <div style="position: relative; z-index: 2;">
                  <span :style="{
                    position: 'absolute', left: '-24px', top: '2px', width: '16px', height: '16px', borderRadius: '99px',
                    background: selectedDelivery.warehouse_confirm_at ? '#0f766e' : '#cbd5e1',
                    border: '3px solid #ffffff',
                    boxShadow: '0 0 0 2px ' + (selectedDelivery.warehouse_confirm_at ? '#0f766e' : '#cbd5e1'),
                    display: 'inline-block'
                  }"></span>
                  <div style="display: flex; flex-direction: column; gap: 4px; box-sizing: border-box;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
                      <span :style="{ fontSize: '13px', fontWeight: '700', color: selectedDelivery.warehouse_confirm_at ? '#1e293b' : '#94a3b8' }">🏢 库管确认手续结清</span>
                      <span v-if="selectedDelivery.warehouse_confirm_at" style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTime(selectedDelivery.warehouse_confirm_at) }}</span>
                      <span v-else style="font-size: 11px; color: #94a3b8; font-style: italic;">等待节点确认...</span>
                    </div>
                    <div v-if="selectedDelivery.warehouse_confirm_at" style="font-size: 12px; color: #475569; display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; margin-top: 2px; background: #fafafa; padding: 8px; border-radius: 6px; box-sizing: border-box; width: 100%;">
                      <div>入库状态：<strong style="color: #0f766e;">✅ 入库手续已结清</strong></div>
                      <div>操作账号：<span style="font-weight: 500; color: #0f766e;">{{ selectedDelivery.warehouse_confirm_by || '—' }}</span></div>
                      <div>经办人：<span>{{ selectedDelivery.warehouse_confirm_name || '—' }}</span></div>
                      <div style="grid-column: span 2;" v-if="selectedDelivery.warehouse_confirm_phone">联系电话：<span>{{ selectedDelivery.warehouse_confirm_phone }}</span></div>
                      <div style="grid-column: span 2; word-break: break-all;" v-if="selectedDelivery.warehouse_remark">入库备注：<span style="color: #64748b; font-style: italic;">“{{ selectedDelivery.warehouse_remark }}”</span></div>
                    </div>
                  </div>
                </div>
                
                <!-- 6. 管理员编辑覆盖节点 -->
                <div v-if="selectedDelivery.ship_remark && (selectedDelivery.ship_remark.includes('[超级修正智能补齐]') || selectedDelivery.ship_remark.includes(' | 状态强改至'))" style="position: relative; z-index: 2; margin-top: 20px;">
                  <span style="position: absolute; left: -24px; top: 2px; width: 16px; height: 16px; border-radius: 99px; background: #64748b; border: 3px solid #ffffff; box-shadow: 0 0 0 2px #64748b; display: inline-block;"></span>
                  <div style="display: flex; flex-direction: column; gap: 4px; box-sizing: border-box;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
                      <span style="font-size: 13px; font-weight: 700; color: #1e293b;">🛠️ 超级管理员覆盖修正</span>
                      <span style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTime(selectedDelivery.updated_at || selectedDelivery.shipped_at) }}</span>
                    </div>
                    <div style="font-size: 12px; color: #475569; display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; margin-top: 2px; background: #fafafa; padding: 8px; border-radius: 6px; box-sizing: border-box; width: 100%;">
                      <div>修正人：<strong style="color: #0f172a;">{{ selectedDelivery.updated_by || '超级管理员' }}</strong></div>
                      <div>修改时间：<span>{{ formatDateTime(selectedDelivery.updated_at) }}</span></div>
                      <div style="grid-column: span 2; word-break: break-all;">修正轨迹及批注：
                        <span style="color: #475569; font-style: italic; font-weight: 500;">
                          {{ 
                            selectedDelivery.ship_remark.includes('[超级修正智能补齐]') 
                              ? selectedDelivery.ship_remark.substring(selectedDelivery.ship_remark.indexOf('[超级修正智能补齐]')).replace('[超级修正智能补齐] ', '') 
                              : selectedDelivery.ship_remark.substring(selectedDelivery.ship_remark.indexOf(' | 状态强改至') + 3) 
                          }}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
                
                <!-- 6. 撤销/异常废弃阶段 (仅在状态是撤销时展示) -->
                <div v-if="selectedDelivery.status === 'cancelled' || selectedDelivery.cancel_reason" style="position: relative; z-index: 2; margin-top: 4px;">
                  <span style="position: absolute; left: -24px; top: 2px; width: 16px; height: 16px; border-radius: 99px; background: #ef4444; border: 3px solid #ffffff; box-shadow: 0 0 0 2px #ef4444; display: inline-block;"></span>
                  <div style="display: flex; flex-direction: column; gap: 4px; box-sizing: border-box;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
                      <span style="font-size: 13px; font-weight: 700; color: #b91c1c;">🚫 供给侧撤销/强制退单</span>
                      <span style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTime(selectedDelivery.updated_at || selectedDelivery.shipped_at) }}</span>
                    </div>
                    <div style="font-size: 12px; color: #475569; background: #fef2f2; padding: 8px; border-radius: 6px; border: 1px solid #fecaca; margin-top: 2px; box-sizing: border-box; width: 100%; word-break: break-all;">
                      <div>撤销缘由：<strong style="color: #b91c1c;">{{ selectedDelivery.cancel_reason || '主动撤单或后台废弃' }}</strong></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>

      <!-- Tab 2: 管件发货记录 -->
      <div v-if="activeTab === 'fitting'">
        <section class="card elevated fitting-ledger-card">
          <div class="fitting-ledger-header">
            <div class="fitting-ledger-heading">
              <h2>🔧 管件发货记录台账</h2>
              <p>
                共 {{ groupedWarehouseFittingRows.length }} 个车次 · {{ fittingRows.length }} 项明细 ·
                {{ warehouseFittingTotalQty }} 个管件
              </p>
            </div>
            <div class="fitting-ledger-actions">
              <button
                type="button"
                class="btn ghost btn-sm"
                @click="toggleAllFittingGroups(true)"
              >
                📖 展开全车次
              </button>
              <button
                type="button"
                class="btn ghost btn-sm"
                @click="toggleAllFittingGroups(false)"
              >
                📕 折叠全车次
              </button>
              <button
                type="button"
                class="btn ghost"
                @click="loadWarehouseFittingDeliveries"
              >
                🔄 刷新台账
              </button>
              <button
                type="button"
                class="btn ghost"
                :disabled="fittingExportLoading || !fittingRows.length"
                @click="exportWarehouseFittingExcel"
              >
                📥 导出管件台账 (.xlsx)
              </button>
            </div>
          </div>

          <!-- 管件透视概览指标（四节点流转） -->
          <div class="fitting-summary-grid">
            <div class="fitting-summary-item is-arrival">
              <span>🚚 待现场到货</span>
              <strong>{{ fittingSummary.pendingArrival }} 项</strong>
            </div>
            <div class="fitting-summary-item is-construction">
              <span>🏗️ 待施工接收</span>
              <strong>{{ fittingSummary.pendingConstruction }} 项</strong>
            </div>
            <div class="fitting-summary-item is-warehouse">
              <span>🏢 待库管确认</span>
              <strong>{{ fittingSummary.pendingWarehouse }} 项</strong>
            </div>
            <div class="fitting-summary-item is-completed">
              <span>✅ 库管已入库完结</span>
              <strong>{{ fittingSummary.completed }} 项</strong>
            </div>
          </div>

          <!-- 折叠车次列表 (默认收起) -->
          <div class="fitting-ledger-body">
            <div v-if="fittingActionMsg" :class="['alert', fittingActionMsg.type === 'error' ? 'alert-danger' : 'alert-success']" style="margin-bottom: 12px;">
              {{ fittingActionMsg.text }}
            </div>
            <div v-if="fittingLoading" class="loading-text">正在加载管件发货记录...</div>
            <div v-else-if="!groupedWarehouseFittingRows.length" class="empty-box">当前筛选条件下暂无管件发货记录。</div>
            <div v-else class="fitting-group-list">
              <div 
                v-for="group in groupedWarehouseFittingRows" 
                :key="group.groupKey"
                class="fitting-shipment-card"
              >
                <!-- 车次汇总行：车次信息、供需流向、状态操作分区排布 -->
                <div class="fitting-shipment-header">
                  <button
                    type="button"
                    class="fitting-shipment-toggle"
                    :aria-expanded="isFittingGroupExpanded(group.groupKey)"
                    @click="toggleFittingGroup(group.groupKey)"
                  >
                    <span class="fitting-shipment-chevron" :class="{ 'is-expanded': isFittingGroupExpanded(group.groupKey) }" aria-hidden="true">
                      ▶
                    </span>
                    <span class="fitting-shipment-main">
                      <span class="fitting-shipment-main-row">
                        <span class="fitting-shipment-label">车次</span>
                        <strong>{{ group.shipmentNo }}</strong>
                        <span class="plate-badge">{{ group.vehiclePlateNo }}</span>
                      </span>
                      <span class="fitting-shipment-time">发货时间 {{ formatDateTime(group.shippedAt) }}</span>
                    </span>
                    <span class="fitting-route" aria-label="供需流向">
                      <span class="fitting-route-party">
                        <small>供给主体</small>
                        <strong>{{ group.supplyEntityName }}</strong>
                      </span>
                      <span class="fitting-route-arrow" aria-hidden="true">→</span>
                      <span class="fitting-route-party">
                        <small>需求主体</small>
                        <strong>{{ group.section1Name }}</strong>
                      </span>
                    </span>
                  </button>

                  <div class="fitting-shipment-side">
                    <div class="fitting-shipment-quantity">
                      <span>{{ group.items.length }} 种规格</span>
                      <strong>{{ group.totalQty }} 个</strong>
                    </div>
                    <!-- 状态 Badge -->
                    <span v-if="group.status === 'shipped' || !group.status" class="fitting-status-badge is-shipped">🚚 待到货确认</span>
                    <span v-else-if="group.status === 'arrived'" class="fitting-status-badge is-arrived">✅ 待施工接收</span>
                    <span v-else-if="group.status === 'construction_confirmed' || group.status === 'received'" class="fitting-status-badge is-pending-warehouse">👷 待库管归档</span>
                    <span v-else-if="group.status === 'warehouse_confirmed'" class="fitting-status-badge is-warehouse-confirmed">🏢 库管已归档</span>
                    <span v-else-if="group.status === 'cancelled'" class="fitting-status-badge" style="background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca;">❌ 已撤销</span>
                    <span v-if="group.hasCancelled && group.status !== 'cancelled'" class="fitting-status-badge" style="background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa;">⚠️ 含已撤销明细</span>

                    <!-- 包含待归档项时显示“整车一键归档”按钮 -->
                    <button 
                      v-if="group.status === 'construction_confirmed' || group.status === 'received' || group.items.some(i => i.status === 'construction_confirmed' || i.status === 'received')"
                      type="button" 
                      class="btn primary btn-sm fitting-archive-button"
                      :disabled="fittingActionLoading"
                      @click.stop="handleConfirmFittingWarehouse(group.items)"
                    >
                      🏢 整车批量归档
                    </button>

                    <button 
                      type="button" 
                      class="btn ghost btn-sm fitting-proof-button"
                      @click.stop="showDeliveryDetail(group)"
                    >
                      📜 流转凭证
                    </button>
                  </div>
                </div>

                <!-- 明细展开区 -->
                <div v-show="isFittingGroupExpanded(group.groupKey)" class="fitting-shipment-details">
                  <div v-if="group.shipRemark" class="fitting-shipment-remark">
                    <span>📝 整车发货备注</span>
                    <strong>{{ group.shipRemark }}</strong>
                  </div>

                  <div class="fitting-detail-table-wrap">
                    <table class="data-table fitting-detail-table">
                      <colgroup>
                        <col class="fitting-col-index">
                        <col class="fitting-col-type">
                        <col class="fitting-col-model">
                        <col class="fitting-col-qty">
                        <col class="fitting-col-qty">
                        <col class="fitting-col-status">
                        <col class="fitting-col-action">
                      </colgroup>
                      <thead>
                        <tr>
                          <th class="fitting-col-index">#</th>
                          <th class="fitting-col-type">管件类型</th>
                          <th class="fitting-col-model">型号 / 规格描述</th>
                          <th class="fitting-col-qty">发货件数</th>
                          <th class="fitting-col-qty">实到件数</th>
                          <th class="fitting-col-status">履约状态</th>
                          <th class="fitting-col-action">归档操作</th>
                        </tr>
                      </thead>
                      <tbody>
                      <tr v-for="(item, idx) in group.items" :key="item.id">
                        <td class="fitting-col-index">{{ idx + 1 }}</td>
                        <td>
                          <span v-if="isStandardFittingType(item.fitting_type)" class="tag-badge primary" style="font-size: 11.5px;">{{ item.fitting_type }}</span>
                          <span v-else class="tag-badge warning" style="background: #fff7ed; color: #c2410c; border: 1px solid #ffedd5; font-size: 11.5px;">⚠️ {{ item.fitting_type }}</span>
                        </td>
                        <td>
                          <strong style="color: #1e293b;">{{ item.model_spec }}</strong>
                          <div class="fitting-order-number">单号：{{ item.order_no }}</div>
                        </td>
                        <td class="fitting-qty-cell is-shipped">{{ item.shipped_qty }} {{ item.unit || '个' }}</td>
                        <td class="fitting-qty-cell">
                          <span v-if="item.status && item.status !== 'shipped'" style="color: #2563eb;">
                            {{ item.arrived_qty !== undefined && item.arrived_qty !== null ? item.arrived_qty : item.shipped_qty }} {{ item.unit || '个' }}
                          </span>
                          <span v-else style="color: #94a3b8; font-weight: normal; font-size: 11.5px;">—</span>
                        </td>

                        <!-- 履约状态列 -->
                        <td style="text-align: center;">
                          <span v-if="item.status === 'shipped' || !item.status" class="tag-badge primary" style="background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; font-size: 11px; padding: 1px 6px;">🚚 待到货确认</span>
                          <span v-else-if="item.status === 'arrived'" class="tag-badge success" style="background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; font-size: 11px; padding: 1px 6px;">✅ 待施工接收</span>
                          <span v-else-if="item.status === 'construction_confirmed' || item.status === 'received'" class="tag-badge warning" style="background: #f3e8ff; color: #6b21a8; border: 1px solid #d8b4fe; font-size: 11px; padding: 1px 6px;">👷 待库管归档</span>
                          <span v-else-if="item.status === 'warehouse_confirmed'" class="tag-badge success" style="background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; font-size: 11px; padding: 1px 6px;">🏢 库管已归档</span>
                          <span v-else-if="item.status === 'cancelled'" class="tag-badge" style="background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; font-size: 11px; padding: 1px 6px;">❌ 已撤销</span>
                        </td>

                        <!-- 库管单项归档操作列 -->
                        <td style="text-align: center;">
                          <div v-if="item.status === 'construction_confirmed' || item.status === 'received'" style="display: flex; justify-content: center; gap: 4px;">
                            <button
                              type="button"
                              class="btn primary btn-sm"
                              style="padding: 2px 8px; font-size: 11.5px; background: #059669; border-color: #059669; color: #fff; cursor: pointer;"
                              :disabled="item.submitting"
                              @click.stop="handleConfirmSingleFittingWarehouse(item)"
                            >
                              {{ item.submitting ? '提交中...' : '🏢 归档入库' }}
                            </button>
                          </div>
                          <span v-else-if="item.status === 'warehouse_confirmed'" style="font-size: 11px; color: #16a34a; font-weight: 600;">✓ 已完成归档</span>
                          <span v-else-if="item.status === 'cancelled'" style="font-size: 11px; color: #b91c1c; font-weight: 600;">已撤销</span>
                          <span v-else style="font-size: 11px; color: #94a3b8;">⏳ 待前置完成</span>
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

    </main>

    <!-- 订单流转备注及全生命周期详情弹窗 -->
    <Transition name="fade">
      <div v-if="deliveryDetailModalVisible && deliveryDetailModalData" class="block-modal-overlay" @click.self="deliveryDetailModalVisible = false">
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
            <div v-if="deliveryDetailModalData.shipRemark" class="metric-block-card" style="grid-column: span 3; background: #eff6ff; border: 1px solid #bfdbfe; text-align: left; padding: 8px 12px; border-radius: 6px;">
              <span class="lbl" style="color: #1d4ed8; font-weight: 600; font-size: 11px; display: flex; align-items: center; gap: 4px;">📝 供给侧发货备注</span>
              <span class="val" style="font-size: 12px; color: #1e3a8a; font-weight: 500; white-space: pre-wrap; word-break: break-all; margin-top: 2px;">{{ deliveryDetailModalData.shipRemark }}</span>
            </div>
          </div>

          <!-- 本车装载物品管件明细清单 -->
          <div v-if="deliveryDetailModalData.itemsList && deliveryDetailModalData.itemsList.length" style="padding: 12px 15px; background: #ffffff; border-bottom: 1px solid #e2e8f0; width: 100%; box-sizing: border-box; overflow-x: auto;">
            <div style="font-size: 12.5px; font-weight: bold; color: #1e293b; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
              <span>📦 本车次搭载管件清单及履约明细</span>
              <span style="font-size: 11px; color: #4f46e5; background: #eef2ff; padding: 2px 8px; border-radius: 99px; border: 1px solid #c7d2fe;">
                共 {{ deliveryDetailModalData.totalTypesCount }} 种规格 / 合计 {{ deliveryDetailModalData.shippedQty }} {{ deliveryDetailModalData.unit || '个' }}
              </span>
            </div>
            <table style="margin: 0; width: 100%; table-layout: fixed; border-collapse: collapse; border: 1px solid #edf2f7; border-radius: 6px; font-size: 11.5px; box-sizing: border-box;">
              <thead>
                <tr style="background: #f1f5f9; color: #475569;">
                  <th style="padding: 6px 4px; text-align: center; width: 28px;">#</th>
                  <th style="padding: 6px 6px; text-align: left; width: 100px;">管件类型</th>
                  <th style="padding: 6px 6px; text-align: left; width: 140px;">规格型号</th>
                  <th style="padding: 6px 6px; text-align: right; width: 65px;">发货数</th>
                  <th style="padding: 6px 6px; text-align: right; width: 65px;">实到数</th>
                  <th style="padding: 6px 6px; text-align: left;">备注</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(it, idx) in deliveryDetailModalData.itemsList" :key="it.id || idx" style="border-bottom: 1px solid #f1f5f9;">
                  <td style="padding: 6px 4px; text-align: center; color: #94a3b8;">{{ idx + 1 }}</td>
                  <td style="padding: 6px 6px; font-weight: 600; color: #0f172a; word-break: break-word;">{{ it.fitting_type || it.fittingType || '管件' }}</td>
                  <td style="padding: 6px 6px; color: #334155; font-family: monospace; word-break: break-word;">{{ it.model_spec || it.modelSpec || '—' }}</td>
                  <td style="padding: 6px 6px; text-align: right; font-weight: bold; color: #2563eb; white-space: nowrap;">{{ it.shipped_qty || it.shippedQty }} {{ it.unit || '个' }}</td>
                  <td style="padding: 6px 6px; text-align: right; font-weight: bold; white-space: nowrap;">
                    <span v-if="it.status && it.status !== 'shipped'" style="color: #059669;">
                      {{ it.arrived_qty !== undefined && it.arrived_qty !== null ? it.arrived_qty : (it.arrivedQty !== undefined ? it.arrivedQty : it.shipped_qty || it.shippedQty) }} {{ it.unit || '个' }}
                    </span>
                    <span v-else style="color: #94a3b8; font-weight: normal;">—</span>
                  </td>
                  <td style="padding: 6px 6px; color: #64748b; font-style: italic; word-break: break-word;">{{ it.ship_remark || it.shipRemark || it.arrival_remark || '—' }}</td>
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
                  <span style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTime(deliveryDetailModalData.shippedAt) }}</span>
                </div>
                <div style="font-size: 11px; color: #475569; background: #fafafa; padding: 6px 10px; border-radius: 6px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px;">
                  <div>发货总数：<strong>{{ deliveryDetailModalData.shippedQty }} {{ deliveryDetailModalData.unit || '个' }}</strong></div>
                  <div>调度经办：<span>{{ deliveryDetailModalData.shipContactName || deliveryDetailModalData.createdBy }}</span></div>
                  <div style="grid-column: span 2;" v-if="deliveryDetailModalData.shipContactPhone">联系电话：<span>{{ deliveryDetailModalData.shipContactPhone }}</span></div>
                </div>
              </div>
            </div>

            <!-- 2. 现场确认到货阶段 -->
            <div style="position: relative; margin-bottom: 20px;">
              <span
                style="position: absolute; left: -24px; top: 2px; width: 12px; height: 12px; border-radius: 99px; border: 2px solid #fff; display: inline-block;"
                :style="{ background: deliveryDetailModalData.arrivedAt ? '#059669' : '#cbd5e1', boxShadow: deliveryDetailModalData.arrivedAt ? '0 0 0 2px #059669' : '0 0 0 2px #cbd5e1' }"
              ></span>
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                  <span style="font-size: 13px; font-weight: bold;" :style="{ color: deliveryDetailModalData.arrivedAt ? '#059669' : '#94a3b8' }">🚚 2. 现场确认到货</span>
                  <span v-if="deliveryDetailModalData.arrivedAt" style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTime(deliveryDetailModalData.arrivedAt) }}</span>
                  <span v-else style="font-size: 11px; color: #94a3b8;">(待到货确认)</span>
                </div>
                <div v-if="deliveryDetailModalData.arrivedAt" style="font-size: 11px; color: #475569; background: #ecfdf5; padding: 6px 10px; border-radius: 6px; border: 1px solid #a7f3d0;">
                  <div>实际到货总数：<strong style="color: #047857;">{{ deliveryDetailModalData.arrivedQty }} {{ deliveryDetailModalData.unit || '个' }}</strong></div>
                  <div>现场确认人：<span>{{ deliveryDetailModalData.arrivedBy || '现场负责人' }}</span></div>
                  <div v-if="deliveryDetailModalData.arrivalRemark">到货备注：<span style="color: #047857;">“{{ deliveryDetailModalData.arrivalRemark }}”</span></div>
                </div>
              </div>
            </div>

            <!-- 3. 施工确认接收阶段 -->
            <div style="position: relative; margin-bottom: 20px;">
              <span
                style="position: absolute; left: -24px; top: 2px; width: 12px; height: 12px; border-radius: 99px; border: 2px solid #fff; display: inline-block;"
                :style="{ background: deliveryDetailModalData.constructionConfirmedAt ? '#2563eb' : '#cbd5e1', boxShadow: deliveryDetailModalData.constructionConfirmedAt ? '0 0 0 2px #2563eb' : '0 0 0 2px #cbd5e1' }"
              ></span>
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                  <span style="font-size: 13px; font-weight: bold;" :style="{ color: deliveryDetailModalData.constructionConfirmedAt ? '#2563eb' : '#94a3b8' }">👷 3. 施工单位领用接收</span>
                  <span v-if="deliveryDetailModalData.constructionConfirmedAt" style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTime(deliveryDetailModalData.constructionConfirmedAt) }}</span>
                  <span v-else style="font-size: 11px; color: #94a3b8;">(待施工接收)</span>
                </div>
                <div v-if="deliveryDetailModalData.constructionConfirmedAt" style="font-size: 11px; color: #475569; background: #eff6ff; padding: 6px 10px; border-radius: 6px; border: 1px solid #bfdbfe;">
                  <div>施工领用接收人：<span>{{ deliveryDetailModalData.constructionConfirmedBy || '施工人员' }}</span></div>
                  <div v-if="deliveryDetailModalData.constructionRemark">接收备注：<span>“{{ deliveryDetailModalData.constructionRemark }}”</span></div>
                </div>
              </div>
            </div>

            <!-- 4. 库管入库归档阶段 -->
            <div style="position: relative;">
              <span
                style="position: absolute; left: -24px; top: 2px; width: 12px; height: 12px; border-radius: 99px; border: 2px solid #fff; display: inline-block;"
                :style="{ background: deliveryDetailModalData.warehouseConfirmedAt ? '#16a34a' : '#cbd5e1', boxShadow: deliveryDetailModalData.warehouseConfirmedAt ? '0 0 0 2px #16a34a' : '0 0 0 2px #cbd5e1' }"
              ></span>
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                  <span style="font-size: 13px; font-weight: bold;" :style="{ color: deliveryDetailModalData.warehouseConfirmedAt ? '#16a34a' : '#94a3b8' }">🏢 4. 库管入库归档</span>
                  <span v-if="deliveryDetailModalData.warehouseConfirmedAt" style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTime(deliveryDetailModalData.warehouseConfirmedAt) }}</span>
                  <span v-else style="font-size: 11px; color: #94a3b8;">(待库管归档)</span>
                </div>
                <div v-if="deliveryDetailModalData.warehouseConfirmedAt" style="font-size: 11px; color: #475569; background: #f0fdf4; padding: 6px 10px; border-radius: 6px; border: 1px solid #bbf7d0;">
                  <div>库管归档经办人：<span>{{ deliveryDetailModalData.warehouseConfirmedBy || '库管员' }}</span></div>
                  <div v-if="deliveryDetailModalData.warehouseRemark">归档备注：<span>“{{ deliveryDetailModalData.warehouseRemark }}”</span></div>
                </div>
              </div>
            </div>
          </div>

          <button
            type="button"
            class="btn primary"
            style="width: 100%; margin-top: 15px; background: #4f46e5 !important; color: #fff !important; font-weight: 600;"
            @click="deliveryDetailModalVisible = false"
          >
            已阅并关闭流转凭证
          </button>
        </div>
      </div>
    </Transition>
    <!-- 导出配置与 XLSX 导出组件 -->
    <ExportSettingsModal
      :show="showExportModal"
      :columns="exportColumns"
      :data="exportAllWarehouseRows"
      :filtered-data="exportWarehouseRows"
      default-filename="保温管库管待入库明细台账"
      @close="showExportModal = false"
    />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import * as XLSX from 'xlsx'
import { useAuthStore } from '../../daily_report_25_26/store/auth'
import { AppHeader, Breadcrumbs, useTubePageShell, useTubeRealtimeRefresh, DELIVERY_STATUS_DICT, getDeliveryStatus } from './shared'
import ExportSettingsModal from './ExportSettingsModal.vue'
import {
  confirmTubeWarehouseDeliveryWarehouse,
  getTubeWarehouseManagementDeliveries,
  getTubeWarehouseManagementOptions,
  getFittingDeliveriesList,
  confirmFittingDeliveryWarehouse,
} from '../../daily_report_25_26/services/api'

const auth = useAuthStore()
const projectKey = 'insulation_pipe_supply_2026'
const { breadcrumbItems, goProjectPages, errorMessage: shellError, managementMode, modeLabels } = useTubePageShell('库管员管理入口')

const activeTab = ref('pipe')

// 管件发货台账状态
const fittingRows = ref([])
const fittingLoading = ref(false)
const fittingExportLoading = ref(false)
const expandedWarehouseFittingGroupKeys = ref(new Set())
const fittingSubTab = ref('all') // 'all' | 'pending_arrival' | 'pending_construction' | 'pending_warehouse' | 'completed'

// 管件勾选与流转处置
const fittingActionLoading = ref(false)
const fittingActionMsg = ref(null)

// 凭证 Modal 对话框
const deliveryDetailModalVisible = ref(false)
const deliveryDetailModalData = ref(null)

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
  const totalArrivedQty = itemsList.reduce((sum, it) => sum + (Number(it.arrived_qty !== undefined && it.arrived_qty !== null ? it.arrived_qty : (it.arrivedQty !== undefined ? it.arrivedQty : (it.shipped_qty || it.shippedQty))) || 0), 0)

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
    unit: mainRow.unit || '个',
    pipeModelName: itemsList.length === 1 ? `${mainRow.fitting_type || '管件'} (${mainRow.model_spec || '未填'})` : `多规格组合管件车次 (${itemsList.length} 种规模型号卡块)`,
    supplyEntityName,
    section1Name,
    shipContactName,
    shipContactPhone,
    createdBy,
    shipRemark,
    arrivedAt: arrivedConfirmAt,
    arrivedBy: arrivedConfirmBy,
    arrivalRemark: arrivedRemark,
    constructionConfirmedAt,
    constructionConfirmedBy,
    constructionRemark,
    warehouseConfirmedAt,
    warehouseConfirmedBy,
    warehouseRemark
  }
  deliveryDetailModalVisible.value = true
}

function openDeliveryDetailModal(row) {
  showDeliveryDetail(row)
}

const toggleFittingGroup = (groupKey) => {
  const next = new Set(expandedWarehouseFittingGroupKeys.value)
  if (next.has(groupKey)) {
    next.delete(groupKey)
  } else {
    next.add(groupKey)
  }
  expandedWarehouseFittingGroupKeys.value = next
}

const isFittingGroupExpanded = (groupKey) => {
  return expandedWarehouseFittingGroupKeys.value.has(groupKey)
}

const toggleAllFittingGroups = (expandAll = true) => {
  if (expandAll) {
    expandedWarehouseFittingGroupKeys.value = new Set(groupedWarehouseFittingRows.value.map(g => g.groupKey))
  } else {
    expandedWarehouseFittingGroupKeys.value = new Set()
  }
}

const groupedWarehouseFittingRows = computed(() => {
  const map = new Map()
  for (const item of fittingRows.value) {
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
        section1Name: item.section_1_name || item.section_1_id || '—',
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
    'arrived': 1,
    'construction_confirmed': 2,
    'received': 2,
    'warehouse_confirmed': 3
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

const STANDARD_FITTING_TYPES = ['弯头', '三通', '大小头', '封头', '直缝弯管', '补偿器', '固定节']
function isStandardFittingType(typeStr) {
  if (!typeStr) return true
  return STANDARD_FITTING_TYPES.includes(String(typeStr).trim())
}

const warehouseFittingTotalQty = computed(() => {
  return fittingRows.value.reduce((sum, r) => sum + (Number(r.shipped_qty) || 0), 0)
})

const warehouseFittingBatches = computed(() => {
  const set = new Set(fittingRows.value.map(r => r.shipment_no || r.id))
  return set.size
})

const warehouseFittingStandardQty = computed(() => {
  return fittingRows.value
    .filter(r => isStandardFittingType(r.fitting_type))
    .reduce((sum, r) => sum + (Number(r.shipped_qty) || 0), 0)
})

const warehouseFittingNonStandardQty = computed(() => {
  return Math.max(0, warehouseFittingTotalQty.value - warehouseFittingStandardQty.value)
})

const fittingSummary = computed(() => {
  const total = fittingRows.value.length
  let pendingArrival = 0
  let pendingConstruction = 0
  let pendingWarehouse = 0
  let completed = 0
  let cancelled = 0

  for (const r of fittingRows.value) {
    const st = r.status || 'shipped'
    if (st === 'shipped') pendingArrival++
    else if (st === 'arrived') pendingConstruction++
    else if (st === 'construction_confirmed') pendingWarehouse++
    else if (st === 'warehouse_confirmed') completed++
    else if (st === 'cancelled') cancelled++
  }

  return {
    total,
    pendingArrival,
    pendingConstruction,
    pendingWarehouse,
    completed,
    cancelled,
  }
})

const filteredFittingRows = computed(() => {
  if (fittingSubTab.value === 'pending_arrival') {
    return fittingRows.value.filter(r => (r.status || 'shipped') === 'shipped')
  }
  if (fittingSubTab.value === 'pending_construction') {
    return fittingRows.value.filter(r => r.status === 'arrived')
  }
  if (fittingSubTab.value === 'pending_warehouse') {
    return fittingRows.value.filter(r => r.status === 'construction_confirmed')
  }
  if (fittingSubTab.value === 'completed') {
    return fittingRows.value.filter(r => r.status === 'warehouse_confirmed')
  }
  return fittingRows.value
})

const loadWarehouseFittingDeliveries = async () => {
  expandedWarehouseFittingGroupKeys.value = new Set()
  fittingLoading.value = true
  try {
    const res = await getFittingDeliveriesList(projectKey, {
      section1Id: filters.section1Ids ? filters.section1Ids.join(',') : '',
      startDate: filters.startDate,
      endDate: filters.endDate,
      searchKeyword: filters.searchKeyword,
      limit: 300,
    })
    if (res && res.ok) {
      fittingRows.value = (res.items || []).map(it => ({
        ...it,
        tempArrivedQty: Number(it.arrived_qty !== undefined && it.arrived_qty !== null ? it.arrived_qty : it.shipped_qty || 0),
        submitting: false
      }))
    }
  } catch (err) {
    console.error('库管侧加载管件发货记录失败:', err)
  } finally {
    fittingLoading.value = false
  }
}

async function handleConfirmFittingWarehouse(items) {
  if (!items || !items.length) return
  fittingActionLoading.value = true
  fittingActionMsg.value = null
  try {
    const ids = items.map(it => it.id)
    const res = await confirmFittingDeliveryWarehouse(projectKey, {
      ids,
      remark: '库管批量核对明细入库归档',
    })
    if (res && res.ok) {
      fittingActionMsg.value = { type: 'success', text: `🎉 成功完成库管最终入库确认 ${res.updated_count} 项管件！` }
      loadWarehouseFittingDeliveries()
    }
  } catch (err) {
    fittingActionMsg.value = { type: 'error', text: `库管入库确认失败: ${err.message}` }
  } finally {
    fittingActionLoading.value = false
  }
}

async function handleConfirmSingleFittingWarehouse(item) {
  if (!item || !item.id) return
  item.submitting = true
  try {
    const res = await confirmFittingDeliveryWarehouse(projectKey, {
      ids: [item.id],
      remark: '库管核对明细入库归档'
    })
    if (res && res.ok) {
      alert(`✅ 单项管件【${item.fitting_type || '管件'} (${item.model_spec || ''})】库管归档成功！`)
      await loadWarehouseFittingDeliveries()
    }
  } catch (err) {
    console.error('单项库管归档失败:', err)
    alert(`归档失败: ${err.message || '系统开小差了'}`)
  } finally {
    item.submitting = false
  }
}

const handleSwitchToFittingTab = () => {
  activeTab.value = 'fitting'
  loadWarehouseFittingDeliveries()
}

function exportWarehouseFittingExcel() {
  if (!fittingRows.value.length) {
    alert('当前暂无管件发货记录可导出')
    return
  }
  fittingExportLoading.value = true
  try {
    const exportData = fittingRows.value.map(r => ({
      '发货时间': formatDateTime(r.shipped_at),
      '发货车次号': r.shipment_no || '—',
      '订单号': r.order_no || '—',
      '运输车牌号': r.vehicle_plate_no || '—',
      '供给主体': r.supply_entity_name || r.supply_entity_id || '—',
      '需求主体': r.section_1_name || r.section_1_id || '—',
      '管件类型': r.fitting_type || '—',
      '型号/规格': r.model_spec || '—',
      '发货数量': r.shipped_qty ?? '—',
      '单位': r.unit || '个',
      '整车备注': r.ship_remark || '—',
    }))

    const worksheet = XLSX.utils.json_to_sheet(exportData)
    const workbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(workbook, worksheet, '库管管件发货记录台账')

    const dateStr = new Date().toISOString().slice(0, 10)
    XLSX.writeFile(workbook, `库管管件发货记录台账_${dateStr}.xlsx`)
  } catch (error) {
    console.error('导出管件到货台账失败:', error)
    alert('导出管件到货台账失败')
  } finally {
    fittingExportLoading.value = false
  }
}

const loading = ref(false)
const actionLoading = ref(false)
const pageError = ref('')
const pageMessage = ref('')
const options = ref(null)
const deliveries = ref([])
const allDeliveries = ref([])
const showExportModal = ref(false)
const exportColumns = computed(() => [
  { key: 'order_no', label: '订单号' },
  { key: 'shipment_no', label: '运输车次号' },
  { key: 'vehicle_plate_no', label: '车牌号' },
  { key: 'supply_entity_name', label: '供给主体' },
  { key: 'section_1_name', label: '装车接收需求主体' },
  { key: 'pipe_model_name', label: '保温管规格型号' },
  { key: 'shipped_qty', label: '发货量（米）' },
  { key: 'arrived_qty', label: '到货量（米）' },
  { key: 'received_qty', label: '接收量（米）' },
  { key: 'shippedAtDisplay', label: '发货时间' },
  { key: 'statusLabel', label: '状态' },
  { key: 'ship_contact_name', label: '发货联系人' },
  { key: 'ship_contact_phone', label: '发货电话' },
  { key: 'ship_remark', label: '发货备注' },
  { key: 'arrived_confirm_by', label: '到货确认人' },
  { key: 'arrivedConfirmAtDisplay', label: '确认到货时间' },
  { key: 'arrived_remark', label: '到货备注' },
  { key: 'received_confirm_by', label: '施工接收人' },
  { key: 'receivedConfirmAtDisplay', label: '接收确认时间' },
  { key: 'received_remark', label: '接收备注' },
  { key: 'warehouse_confirm_by', label: '库管确认人' },
  { key: 'warehouseConfirmAtDisplay', label: '入库确认时间' },
  { key: 'warehouse_remark', label: '入库备注' }
])
const exportWarehouseRows = computed(() => {
  return deliveries.value.map(row => ({
    ...row,
    shippedAtDisplay: formatDateTime(row.shipped_at),
    arrivedConfirmAtDisplay: formatDateTime(row.arrived_confirm_at),
    receivedConfirmAtDisplay: formatDateTime(row.received_confirm_at),
    warehouseConfirmAtDisplay: formatDateTime(row.warehouse_confirm_at),
    statusLabel: deliveryStatusLabelMap[row.status] || row.status || '',
    ship_remark: row.ship_remark || row.cancel_reason || ''
  }))
})
const exportAllWarehouseRows = computed(() => {
  return allDeliveries.value.map(row => ({
    ...row,
    shippedAtDisplay: formatDateTime(row.shipped_at),
    arrivedConfirmAtDisplay: formatDateTime(row.arrived_confirm_at),
    receivedConfirmAtDisplay: formatDateTime(row.received_confirm_at),
    warehouseConfirmAtDisplay: formatDateTime(row.warehouse_confirm_at),
    statusLabel: deliveryStatusLabelMap[row.status] || row.status || '',
    ship_remark: row.ship_remark || row.cancel_reason || ''
  }))
})
const selectedDeliveryId = ref('')
const selectedDeliveryIds = ref([])

const filters = reactive({
  section1Ids: [],
  supplyEntityIds: [],
  pipeModelIds: [],
  statuses: [],
  shipmentNo: '',
  orderNo: '',
  vehiclePlateNo: '',
})

// 多选下拉组件状态与控制
const activeDropdown = ref('')
const section1DropdownRef = ref(null)
const supplyDropdownRef = ref(null)
const pipeDropdownRef = ref(null)
const statusDropdownRef = ref(null)

const toggleDropdown = (name) => {
  if (activeTab.value === 'fitting' && (name === 'pipeModel' || name === 'status')) {
    return
  }
  activeDropdown.value = activeDropdown.value === name ? '' : name
}

const handleGlobalClick = (e) => {
  if (activeDropdown.value === 'section1' && section1DropdownRef.value && !section1DropdownRef.value.contains(e.target)) {
    activeDropdown.value = ''
  }
  if (activeDropdown.value === 'supplier' && supplyDropdownRef.value && !supplyDropdownRef.value.contains(e.target)) {
    activeDropdown.value = ''
  }
  if (activeDropdown.value === 'pipeModel' && pipeDropdownRef.value && !pipeDropdownRef.value.contains(e.target)) {
    activeDropdown.value = ''
  }
  if (activeDropdown.value === 'status' && statusDropdownRef.value && !statusDropdownRef.value.contains(e.target)) {
    activeDropdown.value = ''
  }
}

// 选中值格式化回显
const displaySelectedSection1s = computed(() => {
  if (filters.section1Ids.length === 0) return '全部需求主体'
  if (filters.section1Ids.length === section1Options.value.length) return '全部需求主体（全选）'
  const names = section1Options.value
    .filter(o => filters.section1Ids.includes(o.section_1_id))
    .map(o => o.section_1_name)
  return names.length <= 2 ? names.join(', ') : `已选 ${names.length} 个需求主体`
})

const displaySelectedSupplyEntities = computed(() => {
  if (filters.supplyEntityIds.length === 0) return '全部供给主体'
  if (filters.supplyEntityIds.length === supplyEntityOptions.value.length) return '全部供给主体（全选）'
  const names = supplyEntityOptions.value
    .filter(o => filters.supplyEntityIds.includes(o.entity_id))
    .map(o => o.entity_name)
  return names.length <= 2 ? names.join(', ') : `已选 ${names.length} 个主体`
})

const displaySelectedPipeModels = computed(() => {
  if (activeTab.value === 'fitting') return '不可选'
  if (filters.pipeModelIds.length === 0) return '全部型号'
  if (filters.pipeModelIds.length === pipeModelOptions.value.length) return '全部型号（全选）'
  const names = pipeModelOptions.value
    .filter(o => filters.pipeModelIds.includes(o.pipe_model_id))
    .map(o => o.pipe_model_name)
  return names.length <= 1 ? names.join(', ') : `已选 ${names.length} 个型号`
})

const displaySelectedStatuses = computed(() => {
  if (activeTab.value === 'fitting') return '不可选'
  if (filters.statuses.length === 0) return '全部状态'
  if (filters.statuses.length === deliveryStatusOptions.value.length) return '全部状态（全选）'
  const labels = deliveryStatusOptions.value
    .filter(o => filters.statuses.includes(o.value))
    .map(o => o.label)
  return labels.length <= 2 ? labels.join(', ') : `已选 ${labels.length} 个状态`
})

// 复选操作函数
const toggleSection1 = (id) => {
  const idx = filters.section1Ids.indexOf(id)
  if (idx > -1) filters.section1Ids.splice(idx, 1)
  else filters.section1Ids.push(id)
}
const selectAllSection1s = () => {
  filters.section1Ids = section1Options.value.map(o => o.section_1_id)
}
const clearAllSection1s = () => {
  filters.section1Ids = []
}

const toggleSupplyEntity = (id) => {
  const idx = filters.supplyEntityIds.indexOf(id)
  if (idx > -1) filters.supplyEntityIds.splice(idx, 1)
  else filters.supplyEntityIds.push(id)
}
const selectAllSupplyEntities = () => {
  filters.supplyEntityIds = supplyEntityOptions.value.map(o => o.entity_id)
}
const clearAllSupplyEntities = () => {
  filters.supplyEntityIds = []
}

const togglePipeModel = (id) => {
  const idx = filters.pipeModelIds.indexOf(id)
  if (idx > -1) filters.pipeModelIds.splice(idx, 1)
  else filters.pipeModelIds.push(id)
}
const selectAllPipeModels = () => {
  filters.pipeModelIds = pipeModelOptions.value.map(o => o.pipe_model_id)
}
const clearAllPipeModels = () => {
  filters.pipeModelIds = []
}

const toggleStatus = (val) => {
  const idx = filters.statuses.indexOf(val)
  if (idx > -1) filters.statuses.splice(idx, 1)
  else filters.statuses.push(val)
}
const selectAllStatuses = () => {
  filters.statuses = deliveryStatusOptions.value.map(o => o.value)
}
const clearAllStatuses = () => {
  filters.statuses = []
}

const warehouseForm = reactive({
  remark: '',
})
const nowTick = ref(Date.now())
let nowTimer = null

const section1Options = computed(() => options.value?.section_1s || [])
const supplyEntityOptions = computed(() => options.value?.supply_entities || [])
const pipeModelOptions = computed(() => options.value?.pipe_models || [])
const groupedPipeModelOptions = computed(() => {
  const groups = []
  let currentGroup = null
  
  pipeModelOptions.value.forEach((item) => {
    const groupName = item.category_group || '保温管型选并集'
    if (!currentGroup || currentGroup.name !== groupName) {
      currentGroup = {
        name: groupName,
        items: [],
      }
      groups.push(currentGroup)
    }
    currentGroup.items.push(item)
  })
  
  return groups
})
const deliveryStatusOptions = computed(() => options.value?.delivery_status_options || [])
const deliveryStatusLabelMap = computed(() => {
  const result = {}
  // 优先使用共享配置中的状态文字，保障多页面 Emoji 与中文一致性
  for (const key of Object.keys(DELIVERY_STATUS_DICT)) {
    result[key] = DELIVERY_STATUS_DICT[key].label
  }
  for (const item of deliveryStatusOptions.value) {
    if (!result[item.value]) {
      result[item.value] = item.label
    }
  }
  return result
})

const selectedDelivery = computed(() => deliveries.value.find((row) => String(row.id) === selectedDeliveryId.value) || null)
const selectedDeliveries = computed(() => {
  const selectedIdSet = new Set(selectedDeliveryIds.value)
  return deliveries.value.filter((row) => selectedIdSet.has(String(row.id)))
})
const pendingWarehouseSelectedDeliveries = computed(() => selectedDeliveries.value.filter((row) => row.status === 'pending_warehouse'))
const pendingWarehouseDeliveryIds = computed(() => deliveries.value.filter((row) => row.status === 'pending_warehouse').map((row) => String(row.id)))
const allPendingWarehouseSelected = computed(() => {
  if (!pendingWarehouseDeliveryIds.value.length) return false
  const selectedIdSet = new Set(selectedDeliveryIds.value)
  return pendingWarehouseDeliveryIds.value.every((id) => selectedIdSet.has(id))
})
const hasPartialPendingWarehouseSelection = computed(() => {
  if (!pendingWarehouseDeliveryIds.value.length) return false
  const selectedIdSet = new Set(selectedDeliveryIds.value)
  const selectedCount = pendingWarehouseDeliveryIds.value.filter((id) => selectedIdSet.has(id)).length
  return selectedCount > 0 && selectedCount < pendingWarehouseDeliveryIds.value.length
})

const selectedDeliveryAggregate = computed(() => {
  const shipmentSet = new Set()
  const orderSet = new Set()
  const section1Set = new Set()
  const pipeModelSet = new Set()
  const vehiclePlateSet = new Set()
  const statusCountMap = new Map()
  let totalShippedQty = 0
  let totalArrivedQty = 0
  let totalReceivedQty = 0
  let elapsedCount = 0
  let elapsedTotalMs = 0
  let maxElapsedMs = 0

  for (const row of selectedDeliveries.value) {
    if (row.shipment_no) shipmentSet.add(row.shipment_no)
    if (row.order_no || row.delivery_code || row.id) orderSet.add(row.order_no || row.delivery_code || String(row.id))
    if (row.section_1_name || row.section_1_id) section1Set.add(row.section_1_name || row.section_1_id)
    if (row.pipe_model_name || row.pipe_model_id) pipeModelSet.add(row.pipe_model_name || row.pipe_model_id)
    if (row.vehicle_plate_no) vehiclePlateSet.add(row.vehicle_plate_no)
    const statusKey = row.status || 'unknown'
    statusCountMap.set(statusKey, Number(statusCountMap.get(statusKey) || 0) + 1)
    totalShippedQty += Number(row.shipped_qty || 0)
    totalArrivedQty += Number(row.arrived_qty || 0)
    totalReceivedQty += Number(row.received_qty || 0)
    const elapsedMs = getDeliveryElapsedMs(row)
    if (elapsedMs !== null) {
      elapsedCount += 1
      elapsedTotalMs += elapsedMs
      if (elapsedMs > maxElapsedMs) {
        maxElapsedMs = elapsedMs
      }
    }
  }

  const statusSummaryLabel =
    Array.from(statusCountMap.entries())
      .map(([status, count]) => `${deliveryStatusLabelMap.value[status] || status} ${count}条`)
      .join(' / ') || '—'

  return {
    totalRecords: selectedDeliveries.value.length,
    pendingWarehouseCount: pendingWarehouseSelectedDeliveries.value.length,
    shipmentCount: shipmentSet.size,
    orderCount: orderSet.size,
    section1Count: section1Set.size,
    pipeModelCount: pipeModelSet.size,
    totalShippedQty,
    totalArrivedQty,
    totalReceivedQty,
    averageElapsedLabel: elapsedCount ? formatDurationMs(elapsedTotalMs / elapsedCount) : '—',
    maxElapsedLabel: elapsedCount ? formatDurationMs(maxElapsedMs) : '—',
    statusSummaryLabel,
    pipeModelLabel: summarizeCollection(Array.from(pipeModelSet)),
    shipmentLabel: summarizeCollection(Array.from(shipmentSet)),
    vehiclePlateLabel: summarizeCollection(Array.from(vehiclePlateSet)),
  }
})

const deliverySummary = computed(() => {
  const summary = {
    total: deliveries.value.length,
    pendingArrival: 0,
    pendingReceive: 0,
    pendingWarehouse: 0,
    completed: 0,
    cancelled: 0,
  }
  for (const row of deliveries.value) {
    if (row.status === 'pending_arrival') summary.pendingArrival += 1
    else if (row.status === 'pending_receive') summary.pendingReceive += 1
    else if (row.status === 'pending_warehouse') summary.pendingWarehouse += 1
    else if (row.status === 'completed') summary.completed += 1
    else if (row.status === 'cancelled') summary.cancelled += 1
  }
  return summary
})

function formatAmount(value) {
  const num = Number(value)
  if (!Number.isFinite(num) || num === 0) return '0'
  return Number.isInteger(num) ? String(num) : num.toFixed(2).replace(/\.00$/, '')
}

function formatOptionalAmount(value) {
  const num = Number(value)
  if (!Number.isFinite(num) || num === 0) return '—'
  return Number.isInteger(num) ? String(num) : num.toFixed(2).replace(/\.00$/, '')
}

function formatDateTime(value) {
  if (!value) return '--'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return String(value).replace('T', ' ').slice(0, 19)
  }
  const pad = (part) => String(part).padStart(2, '0')
  return `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())} ${pad(parsed.getHours())}:${pad(parsed.getMinutes())}:${pad(parsed.getSeconds())}`
}

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

function formatDurationMs(durationMs) {
  const totalSeconds = Math.max(Math.floor(Number(durationMs || 0) / 1000), 0)
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  if (days > 0) return `${days}天${hours}小时${minutes}分`
  if (hours > 0) return `${hours}小时${minutes}分`
  if (minutes > 0) return `${minutes}分`
  return `${seconds}秒`
}

function getDeliveryElapsedMs(row) {
  if (!row || row.status === 'cancelled' || !row.shipped_at) return null
  const shippedAt = new Date(row.shipped_at)
  if (Number.isNaN(shippedAt.getTime())) return null
  const arrivedConfirmAtVal = row.arrivedConfirmAt ?? row.arrived_confirm_at
  const endValue = arrivedConfirmAtVal ? new Date(arrivedConfirmAtVal) : new Date(nowTick.value)
  if (Number.isNaN(endValue.getTime())) return null
  return Math.max(endValue.getTime() - shippedAt.getTime(), 0)
}

function summarizeCollection(values, visibleCount = 3) {
  const normalizedValues = (values || []).filter(Boolean)
  if (!normalizedValues.length) return '—'
  if (normalizedValues.length <= visibleCount) {
    return normalizedValues.join('、')
  }
  const visibleValues = normalizedValues.slice(0, visibleCount)
  return `${visibleValues.join('、')} 等${normalizedValues.length}项`
}

function formatDeliveryElapsedDisplay(row) {
  if (!row || row.status === 'cancelled') return '—'
  return row.delivery_elapsed_label || formatElapsedLabel(row.shipped_at) || '—'
}

function getAbnormalLabel(row) {
  if (!row?.abnormal_flag) return ''
  const shippedQty = Number(row.shipped_qty ?? 0)
  const arrivedQty = row.arrived_qty == null ? null : Number(row.arrived_qty)
  const receivedQty = row.received_qty == null ? null : Number(row.received_qty)
  if (receivedQty != null && arrivedQty != null && receivedQty < arrivedQty) return '少接收'
  if (arrivedQty != null && arrivedQty < shippedQty) return '少到货'
  return '异常'
}

function statusClass(status) {
  if (status === 'pending_arrival') return 'status-warn'
  if (status === 'pending_receive') return 'status-info'
  if (status === 'pending_warehouse') return 'status-secondary'
  if (status === 'completed') return 'status-success'
  if (status === 'cancelled') return 'status-danger'
  return 'status-neutral'
}

function syncActionForms(row) {
  if (!row) return
  warehouseForm.remark = row.warehouse_remark || ''
}

function isDeliverySelected(deliveryId) {
  return selectedDeliveryIds.value.includes(String(deliveryId))
}

function selectDelivery(row) {
  selectedDeliveryId.value = String(row.id)
  syncActionForms(row)
}

function toggleDeliverySelection(row) {
  const deliveryId = String(row.id)
  
  // 非“待库管”状态的行，点击行时仅作为“查看单条详情备注”，不参与多选勾选
  if (row.status !== 'pending_warehouse') {
    selectedDeliveryId.value = deliveryId
    syncActionForms(row)
    return
  }
  
  // 待库管状态的行进行多选切换
  if (isDeliverySelected(deliveryId)) {
    selectedDeliveryIds.value = selectedDeliveryIds.value.filter((id) => id !== deliveryId)
    if (selectedDeliveryId.value === deliveryId) {
      selectedDeliveryId.value = selectedDeliveryIds.value[0] || ''
      const nextSelected = deliveries.value.find((item) => String(item.id) === selectedDeliveryId.value)
      if (nextSelected) {
        syncActionForms(nextSelected)
      }
    }
    return
  }
  selectedDeliveryIds.value = [...selectedDeliveryIds.value, deliveryId]
  selectDelivery(row)
}

function toggleSelectAllPendingWarehouse(event) {
  const checked = Boolean(event?.target?.checked)
  if (checked) {
    const selectedIdSet = new Set(selectedDeliveryIds.value)
    for (const deliveryId of pendingWarehouseDeliveryIds.value) {
      selectedIdSet.add(deliveryId)
    }
    selectedDeliveryIds.value = Array.from(selectedIdSet)
    if (!selectedDeliveryId.value && pendingWarehouseSelectedDeliveries.value.length) {
      selectDelivery(pendingWarehouseSelectedDeliveries.value[0])
    }
    return
  }
  const pendingSet = new Set(pendingWarehouseDeliveryIds.value)
  selectedDeliveryIds.value = selectedDeliveryIds.value.filter((id) => !pendingSet.has(id))
  if (selectedDeliveryId.value && !selectedDeliveryIds.value.includes(selectedDeliveryId.value)) {
    selectedDeliveryId.value = selectedDeliveryIds.value[0] || ''
    const nextSelected = deliveries.value.find((item) => String(item.id) === selectedDeliveryId.value)
    if (nextSelected) {
      syncActionForms(nextSelected)
    }
  }
}

async function loadOptions() {
  const payload = await getTubeWarehouseManagementOptions(projectKey)
  options.value = payload
  const section1IdSet = new Set(section1Options.value.map((item) => String(item.section_1_id || '')))
  const supplyEntityIdSet = new Set(supplyEntityOptions.value.map((item) => String(item.entity_id || '')))
  const pipeModelIdSet = new Set(pipeModelOptions.value.map((item) => String(item.pipe_model_id || '')))
  const deliveryStatusValueSet = new Set(deliveryStatusOptions.value.map((item) => String(item.value || '')))
  
  filters.section1Ids = filters.section1Ids.filter(id => section1IdSet.has(id))
  filters.supplyEntityIds = filters.supplyEntityIds.filter(id => supplyEntityIdSet.has(id))
  filters.pipeModelIds = filters.pipeModelIds.filter(id => pipeModelIdSet.has(id))
  filters.statuses = filters.statuses.filter(val => deliveryStatusValueSet.has(val))

  if (filters.section1Ids.length === 0 && section1Options.value.length === 1) {
    filters.section1Ids = [section1Options.value[0].section_1_id]
  }
}

async function loadAllDeliveries() {
  try {
    const payload = await getTubeWarehouseManagementDeliveries(projectKey, {})
    allDeliveries.value = Array.isArray(payload?.rows) ? payload.rows : []
  } catch (error) {
    console.error('Failed to load all deliveries for export:', error)
  }
}

async function loadDeliveries() {
  loading.value = true
  pageError.value = ''
  try {
    if (activeTab.value === 'fitting') {
      await loadWarehouseFittingDeliveries()
    }
    const payload = await getTubeWarehouseManagementDeliveries(projectKey, {
      section1Id: filters.section1Ids.join(','),
      supplyEntityId: filters.supplyEntityIds.join(','),
      pipeModelId: filters.pipeModelIds.join(','),
      status: filters.statuses.join(','),
      shipmentNo: filters.shipmentNo,
      orderNo: filters.orderNo,
      vehiclePlateNo: filters.vehiclePlateNo,
    })
    deliveries.value = Array.isArray(payload?.rows) ? payload.rows : []
    
    const availableIdSet = new Set(deliveries.value.map((row) => String(row.id)))
    selectedDeliveryIds.value = selectedDeliveryIds.value.filter((id) => availableIdSet.has(id))
    const keepSelected = deliveries.value.find((row) => String(row.id) === selectedDeliveryId.value)
    if (keepSelected) {
      syncActionForms(keepSelected)
    } else if (selectedDeliveryIds.value.length > 0) {
      const firstSelected = deliveries.value.find((row) => String(row.id) === selectedDeliveryIds.value[0])
      if (firstSelected) {
        selectDelivery(firstSelected)
      }
    } else if (deliveries.value.length > 0) {
      selectedDeliveryId.value = ''
    } else {
      selectedDeliveryId.value = ''
    }
  } catch (error) {
    pageError.value = error?.message || '读取库管台账失败'
    deliveries.value = []
    selectedDeliveryId.value = ''
    selectedDeliveryIds.value = []
  } finally {
    loading.value = false
  }
}

async function reloadAll() {
  try {
    await loadOptions()
  } catch (error) {
    pageError.value = error?.message || '读取库管页面选项失败'
    return
  }
  await Promise.all([
    loadDeliveries(),
    loadAllDeliveries()
  ])
}

async function resetFilters() {
  filters.section1Ids = []
  filters.supplyEntityIds = []
  filters.pipeModelIds = []
  filters.statuses = []
  filters.shipmentNo = ''
  filters.orderNo = ''
  filters.vehiclePlateNo = ''
  await Promise.all([
    loadDeliveries(),
    loadAllDeliveries()
  ])
}

async function submitWarehouse() {
  if (!pendingWarehouseSelectedDeliveries.value.length) return
  actionLoading.value = true
  pageError.value = ''
  pageMessage.value = ''
  
  const targets = [...pendingWarehouseSelectedDeliveries.value]
  const promises = targets.map((row) =>
    confirmTubeWarehouseDeliveryWarehouse(projectKey, row.id, {
      remark: warehouseForm.remark || '',
    })
  )
  
  try {
    const results = await Promise.allSettled(promises)
    const fulfilled = results.filter((r) => r.status === 'fulfilled')
    const rejected = results.filter((r) => r.status === 'rejected')
    
    if (rejected.length === 0) {
      pageMessage.value = `批量库管确认处理成功！已完美处理 ${fulfilled.length} 条记录。`
      warehouseForm.remark = ''
      selectedDeliveryIds.value = [] // 批量处置成功后清空勾选
    } else {
      const errorMsg = rejected.map((r) => {
        return r.reason?.message || '网络连接或权限异常'
      }).join('; ')
      pageError.value = `部分处置成功！成功 ${fulfilled.length} 条，失败 ${rejected.length} 条。失败反馈: ${errorMsg}`
    }
    await Promise.all([
      loadDeliveries(),
      loadAllDeliveries()
    ])
  } catch (error) {
    pageError.value = error?.message || '库管确认批量接口执行异常'
  } finally {
    actionLoading.value = false
  }
}

watch(
  selectedDelivery,
  (row) => {
    if (row) syncActionForms(row)
  },
  { immediate: true },
)

onMounted(async () => {
  nowTimer = setInterval(() => {
    nowTick.value = Date.now()
  }, 60000)
  await reloadAll()
})

useTubeRealtimeRefresh(reloadAll)

onBeforeUnmount(() => {
  if (nowTimer) {
    clearInterval(nowTimer)
    nowTimer = null
  }
})
</script>

<style scoped>
/* 悬浮凭证 Modal 遮罩与居中浮层 */
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
  padding: 18px 24px !important;
  text-align: center !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  gap: 6px !important;
}

.block-warning-icon {
  font-size: 32px !important;
}

.block-warning-desc {
  margin: 0 !important;
  font-size: 12.5px !important;
}

.block-modal-metrics {
  display: grid !important;
}

.metric-block-card {
  background: #f8fafc !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 8px !important;
  padding: 8px 12px !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 4px !important;
}

.metric-block-card .lbl {
  font-size: 11px !important;
  color: #64748b !important;
}

.metric-block-card .val {
  font-size: 13px !important;
  font-weight: 600 !important;
  color: #0f172a !important;
}

.tube-page-root { min-height: 100vh; background: var(--bg); }
.tube-page-main { display: flex; flex-direction: column; gap: 16px; padding-top: 18px; padding-bottom: 24px; max-width: 1440px; margin: 0 auto; width: 100%; box-sizing: border-box; padding-left: 24px; padding-right: 24px; }
.topbar { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.topbar h2 { margin: 0 0 6px; font-size: 22px; }
.topbar .sub { margin: 0; color: var(--muted); line-height: 1.6; }
.topbar-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.page-error { margin: 0; color: var(--danger); }
.page-success { margin: 0; color: #0f766e; }
.page-state { padding: 28px 12px; text-align: center; color: var(--muted); }
.page-state.compact { padding: 14px 12px; text-align: left; }
.card-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; font-weight: 600; margin-bottom: 14px; }
.muted { color: var(--muted); font-weight: 400; }
.filter-grid, .form-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.field { display: flex; flex-direction: column; gap: 8px; }
.field span { font-size: 13px; color: var(--muted); }
.field-wide { grid-column: 1 / -1; }
.input, .textarea { width: 100%; box-sizing: border-box; border: 1px solid rgba(15, 23, 42, 0.16); border-radius: 10px; padding: 10px 12px; font: inherit; background: #fff; color: var(--text); }
.textarea { resize: vertical; }
.filter-actions, .form-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 14px; flex-wrap: wrap; }
.form-actions { grid-column: 1 / -1; align-items: center; }
.stats-card { margin-top: 0; }
.stats-grid { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; }
.stat-box {
  border: 1px solid rgba(15, 23, 42, 0.08) !important;
  background: rgba(255, 255, 255, 0.65) !important;
  backdrop-filter: blur(12px) !important;
  -webkit-backdrop-filter: blur(12px) !important;
  border-radius: 12px !important;
  padding: 16px 14px !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 8px !important;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -1px rgba(0, 0, 0, 0.02) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  position: relative !important;
  overflow: hidden !important;
  box-sizing: border-box;
}

.stat-box::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 4px;
  background: #3b82f6;
}

.stat-box:nth-child(1)::before { background: #3b82f6; }
.stat-box:nth-child(2)::before { background: #f59e0b; }
.stat-box:nth-child(3)::before { background: #ea580c; }
.stat-box:nth-child(4)::before { background: #8b5cf6; }
.stat-box:nth-child(5)::before { background: #10b981; }
.stat-box:nth-child(6)::before { background: #64748b; }

.stat-box:hover {
  transform: translateY(-4px) !important;
  background: rgba(255, 255, 255, 0.85) !important;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.06), 0 4px 6px -2px rgba(0, 0, 0, 0.03) !important;
}

.stat-box span {
  color: #64748b !important;
  font-size: 13px !important;
  font-weight: 500 !important;
}

.stat-box strong {
  font-size: 24px !important;
  color: #1e293b !important;
  font-weight: 700 !important;
  font-family: "Inter", "Outfit", sans-serif !important;
}
.table-wrap {
  overflow-x: auto;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02), 0 10px 15px -3px rgba(0, 0, 0, 0.04);
}
.table {
  width: 100%;
  border-collapse: collapse;
  min-width: 1400px;
  table-layout: fixed;
}
.table th, .table td {
  padding: 14px 12px !important;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  text-align: left;
  vertical-align: middle !important;
}

/* colgroup 列宽物理比例控制 */
.col-checkbox { width: 50px !important; }
.col-order { width: 130px !important; }
.col-shipment { width: 120px !important; }
.col-plate { width: 100px !important; }
.col-supply { width: 160px !important; }
.col-section1 { width: 160px !important; }
.col-model { width: 130px !important; }
.col-qty { width: 105px !important; }
.col-status { width: 150px !important; }
.col-time { width: 160px !important; }
.col-elapsed { width: 110px !important; }

/* 单元格精细对齐与样式 */
.cell-checkbox {
  text-align: center !important;
  justify-content: center !important;
  width: 50px !important;
  padding: 14px 6px !important;
}
.cell-checkbox input[type="checkbox"] {
  cursor: pointer;
  width: 16px;
  height: 16px;
  border-radius: 4px;
  accent-color: #3b82f6;
  vertical-align: middle;
}
.cell-code-wrapper {
  text-align: left !important;
  white-space: nowrap !important;
}
.cell-code {
  font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace !important;
  font-size: 12.5px !important;
  background: #f1f5f9;
  color: #475569;
  padding: 3px 8px !important;
  border-radius: 6px;
  border: 1px solid rgba(15, 23, 42, 0.05);
  font-weight: 500;
  display: inline-block;
}
.cell-plate {
  min-width: 90px !important;
  width: 100px !important;
  text-align: center !important;
  white-space: nowrap !important;
}
.cell-plate-header {
  text-align: center !important;
}
.plate-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #eff6ff;
  color: #1e40af;
  border: 1px solid #bfdbfe;
  font-family: "Inter", "Outfit", -apple-system, sans-serif;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
  letter-spacing: 0.5px;
}
.cell-supply, .cell-section1 {
  max-width: 160px !important;
  min-width: 120px !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  color: #334155 !important;
  font-size: 13px !important;
}
.cell-model {
  max-width: 130px !important;
  min-width: 100px !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  font-weight: 500;
  color: #0f172a;
}
.cell-number {
  text-align: right !important;
  font-variant-numeric: tabular-nums;
  font-family: "JetBrains Mono", "Fira Code", monospace;
  font-size: 13.5px !important;
  font-weight: 600 !important;
  color: #0f172a !important;
  white-space: nowrap !important;
}
th.cell-number {
  text-align: right !important;
  font-family: inherit !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  color: #1e293b !important;
}
.cell-status {
  min-width: 140px !important;
  width: 150px !important;
  white-space: nowrap !important;
}
.cell-datetime {
  font-family: "Inter", -apple-system, sans-serif !important;
  font-size: 13px !important;
  color: #475569 !important;
  white-space: nowrap !important;
}
.cell-elapsed {
  font-family: "Inter", -apple-system, sans-serif !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  color: #2563eb !important;
  white-space: nowrap !important;
}

.table thead th {
  background: #f8fafc !important;
  color: #1e293b !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  letter-spacing: 0.5px;
  border-bottom: 2px solid #e2e8f0 !important;
  white-space: nowrap !important;
}
.table tbody tr {
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.table tbody tr:hover {
  background: rgba(59, 130, 246, 0.02) !important;
}
.table tbody tr.checked {
  background: rgba(59, 130, 246, 0.04) !important;
}
.table tbody tr.active {
  background: rgba(59, 130, 246, 0.08) !important;
}
.table tbody tr.active td {
  border-bottom-color: rgba(59, 130, 246, 0.15);
}
.table tbody tr.active td:first-child {
  position: relative;
}
.table tbody tr.active td:first-child::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 4px;
  background: #2563eb;
}

.tiny { padding: 6px 10px; font-size: 12px; }
.status-pill { display: inline-flex; align-items: center; padding: 5px 10px; border-radius: 999px; font-size: 12px; line-height: 1; border: 1px solid transparent; font-weight: 500; }
.status-pill-group { display: inline-flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.status-warn { background: #fff7ed; color: #c2410c; border-color: #fed7aa; }
.status-info { background: #eff6ff; color: #1d4ed8; border-color: #bfdbfe; }
.status-secondary { background: #f5f3ff; color: #6d28d9; border-color: #ddd6fe; }
.status-success { background: #ecfdf5; color: #047857; border-color: #a7f3d0; }
.status-danger { background: #fef2f2; color: #b91c1c; border-color: #fecaca; }
.status-neutral { background: #f8fafc; color: #475569; border-color: #e2e8f0; }
.status-abnormal {
  background: #fff1f2 !important;
  color: #e11d48 !important;
  border-color: #ffe4e6 !important;
  font-weight: 600 !important;
  animation: abnormal-pulse 2s infinite ease-in-out;
}
@keyframes abnormal-pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.03); }
  100% { transform: scale(1); }
}
.action-panel { display: flex; flex-direction: column; gap: 16px; }
.action-summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.action-summary > div { display: flex; flex-direction: column; gap: 8px; padding: 12px 14px; border-radius: 12px; background: rgba(248, 250, 252, 0.85); border: 1px solid rgba(15, 23, 42, 0.08); }
.action-summary span { color: var(--muted); font-size: 13px; }
.action-summary strong { font-size: 15px; }

/* 管件发货台账：稳定分区，避免主体名称与操作按钮相互挤压。 */
.fitting-ledger-card {
  padding: 0 !important;
  overflow: hidden;
}

.fitting-ledger-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 20px;
  border-bottom: 1px solid #e2e8f0;
}

.fitting-ledger-heading {
  min-width: 0;
}

.fitting-ledger-heading h2 {
  margin: 0;
  color: #0f172a;
  font-size: 17px;
  line-height: 1.4;
}

.fitting-ledger-heading p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 12.5px;
}

.fitting-ledger-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.fitting-ledger-actions .btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  padding: 0 12px;
  border-color: #cbd5e1;
  background: #fff;
  font-size: 12px;
  white-space: nowrap;
  cursor: pointer;
}

.fitting-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  padding: 14px 20px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.fitting-summary-item {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
  padding: 11px 13px 11px 16px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  border-radius: 9px;
  background: #fff;
}

.fitting-summary-item::before {
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: currentColor;
  content: '';
}

.fitting-summary-item span {
  overflow: hidden;
  color: #64748b;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fitting-summary-item strong {
  flex: 0 0 auto;
  font-size: 17px;
}

.fitting-summary-item.is-arrival { color: #d97706; }
.fitting-summary-item.is-construction { color: #2563eb; }
.fitting-summary-item.is-warehouse { color: #7e22ce; }
.fitting-summary-item.is-completed { color: #16a34a; }

.fitting-ledger-body {
  position: relative;
  min-height: 160px;
  padding: 16px 20px 20px;
}

.fitting-group-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.fitting-shipment-card {
  overflow: hidden;
  border: 1px solid #dbe4ef;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}

.fitting-shipment-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: stretch;
  background: #f8fafc;
}

.fitting-shipment-toggle {
  display: grid;
  grid-template-columns: 18px minmax(210px, 0.8fr) minmax(320px, 1.3fr);
  align-items: center;
  gap: 12px;
  min-width: 0;
  padding: 12px 14px;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.fitting-shipment-toggle:hover,
.fitting-shipment-toggle:focus-visible {
  background: #f1f5f9;
  outline: none;
}

.fitting-shipment-toggle:focus-visible {
  box-shadow: inset 0 0 0 2px #93c5fd;
}

.fitting-shipment-chevron {
  color: #4f46e5;
  font-size: 13px;
  font-weight: 700;
  transition: transform 0.2s ease;
}

.fitting-shipment-chevron.is-expanded {
  transform: rotate(90deg);
}

.fitting-shipment-main,
.fitting-shipment-main-row {
  display: flex;
  align-items: center;
  min-width: 0;
}

.fitting-shipment-main {
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.fitting-shipment-main-row {
  gap: 8px;
}

.fitting-shipment-main-row strong {
  overflow: hidden;
  color: #4338ca;
  font-family: "Inter", "SFMono-Regular", Consolas, monospace;
  font-size: 13.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fitting-shipment-label,
.fitting-shipment-time {
  color: #64748b;
  font-size: 11px;
}

.fitting-shipment-time {
  font-family: "Inter", "SFMono-Regular", Consolas, monospace;
}

.fitting-route {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  min-width: 0;
  padding: 7px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
}

.fitting-route-party {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.fitting-route-party small {
  color: #94a3b8;
  font-size: 10.5px;
}

.fitting-route-party strong {
  overflow: hidden;
  color: #334155;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fitting-route-arrow {
  color: #3b82f6;
  font-size: 16px;
  font-weight: 700;
}

.fitting-shipment-side {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  padding: 10px 14px;
  border-left: 1px solid #e2e8f0;
}

.fitting-shipment-quantity {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  min-width: 64px;
}

.fitting-shipment-quantity span {
  color: #94a3b8;
  font-size: 10.5px;
}

.fitting-shipment-quantity strong {
  color: #2563eb;
  font-size: 14px;
  white-space: nowrap;
}

.fitting-status-badge {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 7px;
  border: 1px solid;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.fitting-status-badge.is-shipped { border-color: #bfdbfe; background: #eff6ff; color: #1d4ed8; }
.fitting-status-badge.is-arrived { border-color: #a7f3d0; background: #ecfdf5; color: #047857; }
.fitting-status-badge.is-pending-warehouse { border-color: #d8b4fe; background: #f3e8ff; color: #6b21a8; }
.fitting-status-badge.is-warehouse-confirmed { border-color: #bbf7d0; background: #f0fdf4; color: #15803d; }

.fitting-archive-button,
.fitting-proof-button {
  min-height: 28px;
  padding: 0 9px !important;
  font-size: 11.5px !important;
  white-space: nowrap;
  cursor: pointer;
}

.fitting-archive-button {
  border-color: #059669 !important;
  background: #059669 !important;
  color: #fff !important;
  font-weight: 700;
}

.fitting-proof-button {
  border-color: #c7d2fe !important;
  background: #eef2ff !important;
  color: #4f46e5 !important;
}

.fitting-shipment-details {
  padding: 12px 14px 14px;
  border-top: 1px solid #e2e8f0;
  background: #fff;
}

.fitting-shipment-remark {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: 10px;
  margin-bottom: 10px;
  padding: 8px 10px;
  border-radius: 7px;
  background: #f1f5f9;
  color: #475569;
  font-size: 12px;
}

.fitting-shipment-remark strong {
  color: #0f172a;
  font-weight: 500;
  overflow-wrap: anywhere;
}

/* 宽表只在明细区域滚动，不拉宽整页。 */
.fitting-detail-table-wrap {
  max-width: 100%;
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  overscroll-behavior-inline: contain;
  scrollbar-gutter: stable;
}

.fitting-detail-table {
  width: 100%;
  min-width: 940px;
  margin: 0 !important;
  border: 0 !important;
  border-collapse: collapse;
  table-layout: fixed !important;
  font-size: 12px !important;
}

.fitting-detail-table thead {
  background: #f8fafc;
}

.fitting-detail-table th,
.fitting-detail-table td {
  padding: 9px 10px !important;
  vertical-align: middle;
}

.fitting-detail-table th {
  color: #475569;
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
}

.fitting-detail-table tbody tr:hover {
  background: #f8fafc;
}

.fitting-col-index {
  width: 42px;
  color: #94a3b8;
  text-align: center !important;
}

.fitting-col-type { width: 172px; }
.fitting-col-model { width: auto; }
.fitting-col-qty { width: 96px; text-align: right !important; }
.fitting-col-status { width: 138px; text-align: center !important; }
.fitting-col-action { width: 124px; text-align: center !important; }

.fitting-detail-table td:nth-child(2) .tag-badge {
  max-width: 100%;
  box-sizing: border-box;
  line-height: 1.35;
  white-space: normal;
}

.fitting-order-number {
  margin-top: 2px;
  color: #94a3b8;
  font-family: "Inter", "SFMono-Regular", Consolas, monospace;
  font-size: 10.5px;
}

.fitting-qty-cell {
  text-align: right;
  font-weight: 700;
}

.fitting-qty-cell.is-shipped {
  color: #64748b;
}

@media (max-width: 1180px) {
  .filter-grid, .form-grid, .stats-grid, .action-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .fitting-ledger-header { align-items: flex-start; }
  .fitting-ledger-actions { max-width: 470px; }
  .fitting-shipment-header { grid-template-columns: 1fr; }
  .fitting-shipment-side {
    justify-content: flex-start;
    padding: 8px 14px 10px 44px;
    border-top: 1px solid #e2e8f0;
    border-left: 0;
  }
}

@media (max-width: 900px) {
  .fitting-detail-table-wrap {
    overflow-x: hidden;
  }

  .fitting-detail-table {
    min-width: 0;
    table-layout: auto !important;
  }

  .fitting-detail-table colgroup,
  .fitting-detail-table thead {
    display: none;
  }

  .fitting-detail-table tbody {
    display: flex;
    flex-direction: column;
  }

  .fitting-detail-table tbody tr {
    display: grid;
    grid-template-columns: 42px minmax(150px, 0.9fr) minmax(210px, 1.3fr);
    grid-template-areas:
      "index type model"
      "index shipped arrived"
      "index status action";
    align-items: stretch;
    border-bottom: 1px solid #e2e8f0;
  }

  .fitting-detail-table tbody tr:last-child {
    border-bottom: 0;
  }

  .fitting-detail-table tbody td {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    width: auto !important;
    min-width: 0;
    border-right: 1px solid #eef2f7;
    border-bottom: 1px solid #eef2f7;
    text-align: left !important;
  }

  .fitting-detail-table tbody td:nth-child(1) {
    grid-area: index;
    justify-content: center;
    border-bottom: 0;
    background: #f8fafc;
    font-weight: 700;
  }

  .fitting-detail-table tbody td:nth-child(2) { grid-area: type; }
  .fitting-detail-table tbody td:nth-child(3) { grid-area: model; }
  .fitting-detail-table tbody td:nth-child(4) { grid-area: shipped; }
  .fitting-detail-table tbody td:nth-child(5) { grid-area: arrived; }
  .fitting-detail-table tbody td:nth-child(6) { grid-area: status; }
  .fitting-detail-table tbody td:nth-child(7) { grid-area: action; }

  .fitting-detail-table tbody td:nth-child(4)::before,
  .fitting-detail-table tbody td:nth-child(5)::before,
  .fitting-detail-table tbody td:nth-child(6)::before,
  .fitting-detail-table tbody td:nth-child(7)::before {
    flex: 0 0 auto;
    color: #94a3b8;
    font-size: 10.5px;
    font-weight: 500;
  }

  .fitting-detail-table tbody td:nth-child(4)::before { content: '发货'; }
  .fitting-detail-table tbody td:nth-child(5)::before { content: '实到'; }
  .fitting-detail-table tbody td:nth-child(6)::before { content: '状态'; }
  .fitting-detail-table tbody td:nth-child(7)::before { content: '操作'; }
}

@media (max-width: 720px) {
  .filter-grid, .form-grid, .stats-grid, .action-summary { grid-template-columns: 1fr; }
  .topbar { flex-direction: column; }
  .topbar-actions, .filter-actions, .form-actions { width: 100%; justify-content: stretch; }
  .topbar-actions .btn, .filter-actions .btn, .form-actions .btn { width: 100%; }
  .fitting-ledger-header { flex-direction: column; padding: 16px; }
  .fitting-ledger-actions { width: 100%; max-width: none; justify-content: flex-start; }
  .fitting-ledger-actions .btn { flex: 1 1 calc(50% - 8px); }
  .fitting-summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); padding: 12px 16px; }
  .fitting-ledger-body { padding: 14px 16px 16px; }
  .fitting-shipment-toggle { grid-template-columns: 16px minmax(0, 1fr); gap: 10px; padding: 12px; }
  .fitting-route { grid-column: 2; width: 100%; box-sizing: border-box; }
  .fitting-shipment-side { padding: 9px 12px; }
  .fitting-shipment-quantity { align-items: flex-start; margin-right: auto; }
  .fitting-proof-button { margin-left: auto; }
  .fitting-shipment-remark { grid-template-columns: 1fr; gap: 4px; }
  .fitting-detail-table tbody tr {
    grid-template-columns: 36px minmax(0, 1fr);
    grid-template-areas:
      "index type"
      "index model"
      "index shipped"
      "index arrived"
      "index status"
      "index action";
  }
}

/* 自定义多选下拉组件样式 */
.custom-multi-select-container {
  position: relative;
}
.custom-multi-select {
  position: relative;
  width: 100%;
  height: 41px;
}
.custom-multi-select .select-trigger {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid rgba(15, 23, 42, 0.16);
  border-radius: 10px;
  padding: 10px 12px;
  background: #fff;
  color: var(--text);
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
  transition: all 0.2s ease-in-out;
  height: 41px;
}
.custom-multi-select .select-trigger:hover {
  border-color: rgba(15, 23, 42, 0.3);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}
.custom-multi-select .select-trigger.active {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}
.custom-multi-select .trigger-text {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding-right: 8px;
  max-width: 90%;
  text-align: left;
}
.custom-multi-select .trigger-text.placeholder {
  color: #94a3b8;
}
.custom-multi-select .trigger-arrow {
  font-size: 10px;
  color: #64748b;
  transition: transform 0.2s ease;
}
.custom-multi-select .select-trigger.active .trigger-arrow {
  transform: rotate(180deg);
}

.custom-multi-select .select-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  width: 100%;
  min-width: 240px;
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 12px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
  z-index: 50;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.custom-multi-select .dropdown-actions {
  display: flex;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
  background: #f8fafc;
}
.custom-multi-select .action-btn {
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 600;
  color: #475569;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.custom-multi-select .action-btn:hover {
  background: #f1f5f9;
  color: #0f172a;
  border-color: rgba(15, 23, 42, 0.2);
}

.custom-multi-select .dropdown-list {
  max-height: 240px;
  overflow-y: auto;
  padding: 6px 0;
}
.custom-multi-select .dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  font-size: 13px;
  color: #334155;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s ease;
}
.custom-multi-select .dropdown-item:hover {
  background: #f1f5f9;
  color: #0f172a;
}
.custom-multi-select .dropdown-item.selected {
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 500;
}
.custom-multi-select .dropdown-item input[type="checkbox"] {
  width: 14px;
  height: 14px;
  cursor: pointer;
  accent-color: #3b82f6;
  margin: 0;
}
.custom-multi-select .item-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  width: 100%;
  text-align: left;
}

/* 动效 */
.dropdown-fade-enter-active,
.dropdown-fade-leave-active {
  transition: all 0.2s ease;
}
.dropdown-fade-enter-from,
.dropdown-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* 按钮 Premium 居中与防折行加固 */
.btn, .primary-button, .button {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  text-align: center !important;
  white-space: nowrap !important;
  word-break: keep-all !important;
  box-sizing: border-box !important;
}
</style>
