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

      <section class="card elevated">
        <div class="card-header">
          <span>库管台账筛选</span>
          <span class="muted">展示日期：{{ options?.show_date || options?.biz_date || '--' }}</span>
        </div>
        <div class="filter-grid">
          <div class="field custom-multi-select-container" ref="stationDropdownRef">
            <span>换热站</span>
            <div class="custom-multi-select">
              <div class="select-trigger" @click="toggleDropdown('station')" :class="{ active: activeDropdown === 'station' }">
                <span class="trigger-text" :class="{ placeholder: filters.stationIds.length === 0 }">
                  {{ displaySelectedStations }}
                </span>
                <span class="trigger-arrow">▼</span>
              </div>
              <transition name="dropdown-fade">
                <div v-if="activeDropdown === 'station'" class="select-dropdown">
                  <div class="dropdown-actions">
                    <button type="button" class="action-btn" @click="selectAllStations">全选</button>
                    <button type="button" class="action-btn" @click="clearAllStations">清空</button>
                  </div>
                  <div class="dropdown-list">
                    <div 
                      v-for="item in stationOptions" 
                      :key="item.station_id" 
                      class="dropdown-item"
                      :class="{ selected: filters.stationIds.includes(item.station_id) }"
                      @click="toggleStation(item.station_id)"
                    >
                      <input type="checkbox" :checked="filters.stationIds.includes(item.station_id)" @click.stop="toggleStation(item.station_id)" />
                      <span class="item-label">{{ item.station_name }}（{{ item.station_id }}）</span>
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
              <div class="select-trigger" @click="toggleDropdown('pipeModel')" :class="{ active: activeDropdown === 'pipeModel' }">
                <span class="trigger-text" :class="{ placeholder: filters.pipeModelIds.length === 0 }">
                  {{ displaySelectedPipeModels }}
                </span>
                <span class="trigger-arrow">▼</span>
              </div>
              <transition name="dropdown-fade">
                <div v-if="activeDropdown === 'pipeModel'" class="select-dropdown">
                  <div class="dropdown-actions">
                    <button type="button" class="action-btn" @click="selectAllPipeModels">全选</button>
                    <button type="button" class="action-btn" @click="clearAllPipeModels">清空</button>
                  </div>
                  <div class="dropdown-list">
                    <div 
                      v-for="item in pipeModelOptions" 
                      :key="item.pipe_model_id" 
                      class="dropdown-item"
                      :class="{ selected: filters.pipeModelIds.includes(item.pipe_model_id) }"
                      @click="togglePipeModel(item.pipe_model_id)"
                    >
                      <input type="checkbox" :checked="filters.pipeModelIds.includes(item.pipe_model_id)" @click.stop="togglePipeModel(item.pipe_model_id)" />
                      <span class="item-label">{{ item.pipe_model_name }}</span>
                    </div>
                  </div>
                </div>
              </transition>
            </div>
          </div>

          <div class="field custom-multi-select-container" ref="statusDropdownRef">
            <span>状态</span>
            <div class="custom-multi-select">
              <div class="select-trigger" @click="toggleDropdown('status')" :class="{ active: activeDropdown === 'status' }">
                <span class="trigger-text" :class="{ placeholder: filters.statuses.length === 0 }">
                  {{ displaySelectedStatuses }}
                </span>
                <span class="trigger-arrow">▼</span>
              </div>
              <transition name="dropdown-fade">
                <div v-if="activeDropdown === 'status'" class="select-dropdown">
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
          <button v-if="deliveries.length > 0" class="btn primary" type="button" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important; color: #fff !important; border: none !important; font-weight: 600;" @click="showExportModal = true">📥 导出 Excel</button>
        </div>
      </section>

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
              <col class="col-station" />
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
                <th>换热站</th>
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
                <td class="cell-station" :title="row.station_name">{{ row.station_name }}</td>
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
                      <div>经办人：<span>{{ selectedDelivery.ship_contact_name || '供给端系统' }}</span></div>
                      <div style="grid-column: span 2;">联系电话：<span>{{ selectedDelivery.ship_contact_phone || '—' }}</span></div>
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
                      <div>确认人：<span style="font-weight: 500; color: #0f766e;">{{ selectedDelivery.arrived_confirm_by || '—' }}</span></div>
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
                      <div>经办人：<span style="font-weight: 500; color: #6d28d9;">{{ selectedDelivery.received_confirm_by || '施工填报人' }}</span></div>
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
                      <div>经办人：<span style="font-weight: 500; color: #0f766e;">{{ selectedDelivery.warehouse_confirm_by || '—' }}</span></div>
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
    </main>
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
import { AppHeader, Breadcrumbs, useTubePageShell, useTubeRealtimeRefresh, DELIVERY_STATUS_DICT, getDeliveryStatus } from './shared'
import ExportSettingsModal from './ExportSettingsModal.vue'
import {
  confirmTubeWarehouseDeliveryWarehouse,
  getTubeWarehouseManagementDeliveries,
  getTubeWarehouseManagementOptions,
} from '../../daily_report_25_26/services/api'

const projectKey = 'insulation_pipe_supply_2026'
const { breadcrumbItems, goProjectPages, errorMessage: shellError } = useTubePageShell('库管员管理入口')

const loading = ref(false)
const actionLoading = ref(false)
const pageError = ref('')
const pageMessage = ref('')
const options = ref(null)
const deliveries = ref([])
const allDeliveries = ref([])
const showExportModal = ref(false)
const exportColumns = [
  { key: 'order_no', label: '订单号' },
  { key: 'shipment_no', label: '运输车次号' },
  { key: 'vehicle_plate_no', label: '车牌号' },
  { key: 'supply_entity_name', label: '供给主体' },
  { key: 'station_name', label: '装车接收换热站' },
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
]
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
  stationIds: [],
  supplyEntityIds: [],
  pipeModelIds: [],
  statuses: [],
  shipmentNo: '',
  orderNo: '',
  vehiclePlateNo: '',
})

// 多选下拉组件状态与控制
const activeDropdown = ref('')
const stationDropdownRef = ref(null)
const supplyDropdownRef = ref(null)
const pipeDropdownRef = ref(null)
const statusDropdownRef = ref(null)

const toggleDropdown = (name) => {
  activeDropdown.value = activeDropdown.value === name ? '' : name
}

const handleGlobalClick = (e) => {
  if (activeDropdown.value === 'station' && stationDropdownRef.value && !stationDropdownRef.value.contains(e.target)) {
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
const displaySelectedStations = computed(() => {
  if (filters.stationIds.length === 0) return '全部换热站'
  if (filters.stationIds.length === stationOptions.value.length) return '全部换热站（全选）'
  const names = stationOptions.value
    .filter(o => filters.stationIds.includes(o.station_id))
    .map(o => o.station_name)
  return names.length <= 2 ? names.join(', ') : `已选 ${names.length} 个站`
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
  if (filters.pipeModelIds.length === 0) return '全部型号'
  if (filters.pipeModelIds.length === pipeModelOptions.value.length) return '全部型号（全选）'
  const names = pipeModelOptions.value
    .filter(o => filters.pipeModelIds.includes(o.pipe_model_id))
    .map(o => o.pipe_model_name)
  return names.length <= 1 ? names.join(', ') : `已选 ${names.length} 个型号`
})

const displaySelectedStatuses = computed(() => {
  if (filters.statuses.length === 0) return '全部状态'
  if (filters.statuses.length === deliveryStatusOptions.value.length) return '全部状态（全选）'
  const labels = deliveryStatusOptions.value
    .filter(o => filters.statuses.includes(o.value))
    .map(o => o.label)
  return labels.length <= 2 ? labels.join(', ') : `已选 ${labels.length} 个状态`
})

// 复选操作函数
const toggleStation = (id) => {
  const idx = filters.stationIds.indexOf(id)
  if (idx > -1) filters.stationIds.splice(idx, 1)
  else filters.stationIds.push(id)
}
const selectAllStations = () => {
  filters.stationIds = stationOptions.value.map(o => o.station_id)
}
const clearAllStations = () => {
  filters.stationIds = []
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

const stationOptions = computed(() => options.value?.stations || [])
const supplyEntityOptions = computed(() => options.value?.supply_entities || [])
const pipeModelOptions = computed(() => options.value?.pipe_models || [])
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
  const stationSet = new Set()
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
    if (row.station_name || row.station_id) stationSet.add(row.station_name || row.station_id)
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
    stationCount: stationSet.size,
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
  const stationIdSet = new Set(stationOptions.value.map((item) => String(item.station_id || '')))
  const supplyEntityIdSet = new Set(supplyEntityOptions.value.map((item) => String(item.entity_id || '')))
  const pipeModelIdSet = new Set(pipeModelOptions.value.map((item) => String(item.pipe_model_id || '')))
  const deliveryStatusValueSet = new Set(deliveryStatusOptions.value.map((item) => String(item.value || '')))
  
  filters.stationIds = filters.stationIds.filter(id => stationIdSet.has(id))
  filters.supplyEntityIds = filters.supplyEntityIds.filter(id => supplyEntityIdSet.has(id))
  filters.pipeModelIds = filters.pipeModelIds.filter(id => pipeModelIdSet.has(id))
  filters.statuses = filters.statuses.filter(val => deliveryStatusValueSet.has(val))

  if (filters.stationIds.length === 0 && stationOptions.value.length === 1) {
    filters.stationIds = [stationOptions.value[0].station_id]
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
    const payload = await getTubeWarehouseManagementDeliveries(projectKey, {
      stationId: filters.stationIds.join(','),
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
  filters.stationIds = []
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
.col-station { width: 160px !important; }
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
.cell-supply, .cell-station {
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

@media (max-width: 1180px) {
  .filter-grid, .form-grid, .stats-grid, .action-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 720px) {
  .filter-grid, .form-grid, .stats-grid, .action-summary { grid-template-columns: 1fr; }
  .topbar { flex-direction: column; }
  .topbar-actions, .filter-actions, .form-actions { width: 100%; justify-content: stretch; }
  .topbar-actions .btn, .filter-actions .btn, .form-actions .btn { width: 100%; }
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
