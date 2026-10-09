<template>
  <div v-if="visible" class="review-modal-backdrop" @click.self="handleClose">
    <div class="review-modal-card">
      <!-- 弹窗顶栏 -->
      <div class="modal-header">
        <div class="modal-title-group">
          <div class="modal-icon-badge">⚖️</div>
          <div>
            <h3>提请多方联合会审</h3>
            <p class="modal-subtitle">发起订单协同校核 · 前序关键责任主体全票会签更正</p>
          </div>
        </div>
        <button type="button" class="btn-close" @click="handleClose" title="关闭">✕</button>
      </div>

      <div class="modal-body" v-if="order">
        <!-- 1. 一体化单据与会签概览卡片 (Dossier Brief) -->
        <div class="dossier-card">
          <div class="dossier-main-row">
            <div class="dossier-cell-order">
              <span class="dossier-lbl">{{ isPipe ? '业务单号' : '运输车次号' }}</span>
              <div class="dossier-val-wrap">
                <span class="dossier-val font-mono" :title="displayOrderCode">{{ displayOrderCode }}</span>
                <span class="lock-mini-tag">🔒</span>
              </div>
            </div>
            <div class="dossier-cell">
              <span class="dossier-lbl">物资品类</span>
              <span class="dossier-val">{{ isPipe ? '🔥 保温管' : '🔩 特种管件/阀门' }}</span>
            </div>
            <div class="dossier-cell" v-if="isPipe">
              <span class="dossier-lbl">规格型号</span>
              <span class="dossier-val font-semibold" :title="orderPipeModelName || '—'">{{ orderPipeModelName || '—' }}</span>
            </div>
            <div class="dossier-cell" v-else>
              <span class="dossier-lbl">车次包含明细</span>
              <span class="dossier-val font-semibold">{{ fittingItemsForm.length }} 笔订单</span>
            </div>
            <div class="dossier-cell">
              <span class="dossier-lbl">需求标段</span>
              <span class="dossier-val" :title="order.section_1_name || order.section_1_id">{{ order.section_1_name || order.section_1_id }}</span>
            </div>
            <div class="dossier-cell">
              <span class="dossier-lbl">供货厂家</span>
              <span class="dossier-val" :title="order.supply_entity_name || order.supply_entity_id">{{ order.supply_entity_name || order.supply_entity_id }}</span>
            </div>
          </div>
          <div class="dossier-signoff-bar">
            <div class="signoff-actors">
              <span class="signoff-prefix">会签主体：</span>
              <span class="signoff-actor-chip">{{ sceneActorsText }}</span>
            </div>
            <span class="signoff-rule-hint">💡 全票同意更正生效 · 一票异议公开挂起</span>
          </div>
        </div>

        <!-- 2. 拟修正字段表单区 (Patch Section) -->
        <!-- Case A: 直管模式 -->
        <div class="patch-section-card" v-if="isPipe">
          <div class="section-header-row">
            <span class="section-title">📝 拟更正内容 (直管订单)</span>
            <span class="section-hint">仅需修改发生差异的项目，其余项保持原样</span>
          </div>

          <div class="form-grid-compact">
            <!-- 1. 发货数量 (半宽) -->
            <div class="form-field-card" :class="{ 'is-modified': form.shipped_qty !== null && Number(form.shipped_qty) !== Number(order.shipped_qty) }">
              <div class="field-header">
                <label>发货数量 (米) *</label>
                <span class="orig-tag">原值: {{ order.shipped_qty }} 米</span>
              </div>
              <div class="input-with-unit">
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  v-model.number="form.shipped_qty"
                  placeholder="实到准确数量"
                  class="field-input"
                />
                <span class="unit-text">米</span>
              </div>
              <div class="diff-indicator" v-if="form.shipped_qty !== null && Number(form.shipped_qty) !== Number(order.shipped_qty)">
                <span class="diff-chip">更正: {{ order.shipped_qty }} ➔ {{ form.shipped_qty }} ({{ formatDiff(form.shipped_qty, order.shipped_qty) }} 米)</span>
              </div>
            </div>

            <!-- 2. 送货车牌 (半宽) -->
            <div class="form-field-card" :class="{ 'is-modified': form.vehicle_plate_no && form.vehicle_plate_no.trim() !== (order.vehicle_plate_no || order.plateNo || '') }">
              <div class="field-header">
                <label>送货车牌号</label>
                <span class="orig-tag">原值: {{ order.vehicle_plate_no || order.plateNo || '未录入' }}</span>
              </div>
              <input
                type="text"
                v-model="form.vehicle_plate_no"
                placeholder="更正送货车牌（如：冀B12345）"
                class="field-input"
              />
              <div class="diff-indicator" v-if="form.vehicle_plate_no && form.vehicle_plate_no.trim() !== (order.vehicle_plate_no || order.plateNo || '')">
                <span class="diff-chip">拟变更为: {{ form.vehicle_plate_no }}</span>
              </div>
            </div>

            <!-- 3. 保温管规格型号 (独占整行，全宽展示，确保原值 100% 完整显示无截断) -->
            <div class="form-field-card" style="grid-column: 1 / -1;" :class="{ 'is-modified': form.pipe_model_id && form.pipe_model_id.trim() !== (orderPipeModelName || '') }">
              <div class="field-header">
                <label>保温管规格型号</label>
                <span class="orig-tag orig-tag-long" :title="orderPipeModelName">
                  系统原登记型号: <strong class="orig-val-text font-mono">{{ orderPipeModelName || '—' }}</strong>
                </span>
              </div>
              <input
                type="text"
                v-model="form.pipe_model_id"
                placeholder="更正规格型号（若无差异保持原样即可）"
                class="field-input"
              />
              <div class="diff-indicator" v-if="form.pipe_model_id && form.pipe_model_id.trim() !== (orderPipeModelName || '')">
                <span class="diff-chip">拟变更为: {{ form.pipe_model_id }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Case B: 管件按车次模式 -->
        <div class="patch-section-card" v-else>
          <!-- 上方：整车公共信息修正 -->
          <div class="section-header-row">
            <span class="section-title">🚚 整车公共信息更正</span>
            <span class="section-hint">仅更正本标段、本厂家且处于同一待办节点的明细</span>
          </div>

          <div class="form-field-card" :class="{ 'is-modified': form.vehicle_plate_no && form.vehicle_plate_no.trim() !== (order.vehicle_plate_no || order.plateNo || '') }">
            <div class="field-header">
              <label>整车运输车牌号</label>
              <span class="orig-tag">原值: {{ order.vehicle_plate_no || order.plateNo || '未录入' }}</span>
            </div>
            <input
              type="text"
              v-model="form.vehicle_plate_no"
              placeholder="更正整车送货车牌（如：冀B12345）"
              class="field-input"
            />
            <div class="diff-indicator" v-if="form.vehicle_plate_no && form.vehicle_plate_no.trim() !== (order.vehicle_plate_no || order.plateNo || '')">
              <span class="diff-chip">拟变更为: {{ form.vehicle_plate_no }}</span>
            </div>
          </div>

          <!-- 下方：各具体订单明细信息修改 -->
          <div class="fitting-items-container">
            <div class="section-header-row" style="margin-top: 8px;">
              <span class="section-title">📦 车载各订单明细更正 (共 {{ fittingItemsForm.length }} 项)</span>
              <span class="section-hint">按单修正品类、规格与发货数量，未修改项保持原样</span>
            </div>

            <div class="fitting-items-list">
              <div
                v-for="(item, idx) in fittingItemsForm"
                :key="item.id || idx"
                class="fitting-item-row-card"
                :class="{ 'is-modified': isFittingItemModified(item) }"
              >
                <div class="fitting-item-card-header">
                  <div class="item-meta-group">
                    <span class="item-seq-badge">#{{ idx + 1 }}</span>
                    <span class="item-order-no font-mono" :title="'订单号: ' + item.order_no">{{ item.order_no }}</span>
                    <span v-if="isFittingItemModified(item)" class="modified-badge">✓ 已更正</span>
                  </div>
                  <div class="item-orig-text" :title="`原记录: ${item.orig_fitting_type || '—'} · ${item.orig_model_spec || '—'} · ${item.orig_shipped_qty} ${item.unit || '件'}`">
                    原: <span class="text-slate-700">{{ item.orig_fitting_type || '—' }}</span> · <span class="text-slate-700">{{ item.orig_model_spec || '—' }}</span> · <span class="text-slate-700 font-mono font-bold">{{ item.orig_shipped_qty }} {{ item.unit || '件' }}</span>
                  </div>
                </div>

                <fieldset class="fitting-item-card-inputs" :disabled="!isFittingItemEditable(item)" style="border: 0; padding: 0; margin: 0; min-width: 0;">
                  <div class="sub-input-col col-type">
                    <label class="sub-col-label">管件品类</label>
                    <input
                      type="text"
                      v-model.trim="item.fitting_type"
                      placeholder="如：弯头/三通"
                      class="field-input sub-input"
                      :class="{ 'input-changed': (item.fitting_type || '').trim() !== (item.orig_fitting_type || '').trim() }"
                    />
                  </div>

                  <div class="sub-input-col col-spec">
                    <label class="sub-col-label">规格型号描述</label>
                    <input
                      type="text"
                      v-model.trim="item.model_spec"
                      placeholder="如：DN200 90°"
                      class="field-input sub-input"
                      :class="{ 'input-changed': (item.model_spec || '').trim() !== (item.orig_model_spec || '').trim() }"
                    />
                  </div>

                  <div class="sub-input-col col-qty">
                    <label class="sub-col-label">发货数量 ({{ item.unit || '件' }}) *</label>
                    <input
                      type="number"
                      step="1"
                      min="1"
                      v-model.number="item.shipped_qty"
                      placeholder="数量"
                      class="field-input sub-input"
                      :class="{ 'input-changed': Number(item.shipped_qty) !== Number(item.orig_shipped_qty) }"
                    />
                  </div>
                </fieldset>
                <p v-if="!isFittingItemEditable(item)" class="section-hint">该明细处于其他节点，不参与本次会审。</p>

                <div class="diff-indicator" v-if="isFittingItemModified(item)" style="margin-top: 4px;">
                  <span class="diff-chip">
                    调整为: {{ item.fitting_type || '—' }} | {{ item.model_spec || '—' }} | {{ item.shipped_qty }} {{ item.unit || '件' }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="form-field-card">
          <div class="field-header"><label>发货备注更正</label><span class="orig-tag">会审决议会自动附在更正备注后</span></div>
          <textarea v-model="form.ship_remark" rows="2" class="field-input" placeholder="如需更正发货备注，请在此填写"></textarea>
        </div>

        <!-- 3. 事由说明与事实凭据区 (Reason & Attachment) -->
        <div class="reason-section-card">
          <div class="reason-header-row">
            <label class="reason-title">
              <span>提请会审事由说明 *</span>
              <span class="reason-char-count" :class="{ 'is-satisfied': (reviewReason || '').trim().length >= 4 }">
                {{ (reviewReason || '').trim().length >= 4 ? `✓ 已输入 ${(reviewReason || '').trim().length} 字` : `需输入不少于 4 字 (当前 ${(reviewReason || '').trim().length} 字)` }}
              </span>
            </label>
          </div>

          <!-- 快捷事由词条 Chips -->
          <div class="quick-reasons-bar">
            <span class="quick-prefix">快捷事由：</span>
            <button
              v-for="(qr, qIdx) in quickReasons"
              :key="qIdx"
              type="button"
              class="quick-reason-chip"
              @click="applyQuickReason(qr)"
              :title="'点击填入: ' + qr.text"
            >
              + {{ qr.label }}
            </button>
          </div>

          <textarea
            ref="reasonTextareaRef"
            v-model="reviewReason"
            rows="3"
            class="reason-textarea"
            placeholder="请详述现场核验实况与差异原因（如：随车磅单实际数量、规格核验差异、现场实际车牌等）..."
          ></textarea>

          <!-- 附件与照片凭证 -->
          <div class="attachment-bar-row">
            <input
              type="file"
              ref="fileInputRef"
              accept="image/*"
              style="display: none;"
              @change="handleFileUpload"
            />
            <button
              type="button"
              class="btn-upload-compact"
              @click="triggerFileInput"
              :disabled="attachments.length >= 3"
            >
              📷 上传现场凭据 ({{ attachments.length }}/3)
            </button>

            <div class="attachment-thumbs-list" v-if="attachments.length">
              <div v-for="(att, idx) in attachments" :key="idx" class="att-thumb-box">
                <img :src="att.url" :alt="att.name" class="att-img" />
                <button type="button" class="btn-remove-thumb" @click="removeAttachment(idx)" title="删除此照片">✕</button>
              </div>
            </div>
            <span class="att-hint-text" v-else>支持随车小票、磅单或现场管材照片</span>
          </div>
        </div>

        <!-- 错误提示 -->
        <div v-if="submitError" class="submit-error-banner">
          ⚠️ {{ submitError }}
        </div>
      </div>

      <!-- 弹窗底栏 (Sticky Footer) -->
      <div class="modal-footer">
        <div class="footer-status-guide">
          <span class="guide-dot" :class="{ 'is-ready': isReadyToSubmit, 'has-patch': changedFieldsCount > 0 }"></span>
          <span v-if="changedFieldsCount > 0 && reviewReason && reviewReason.trim().length >= 4" class="guide-text success">
            已就绪：拟更正 {{ changedFieldsCount }} 项数据，事由完备
          </span>
          <span v-else-if="changedFieldsCount > 0" class="guide-text">
            拟更正 {{ changedFieldsCount }} 项：请补充事由说明（不少于4字）
          </span>
          <span v-else-if="reviewReason && reviewReason.trim().length >= 4" class="guide-text success">
            现场异议协商模式：未修改数值，针对实况事由提请会签
          </span>
          <span v-else class="guide-text muted">
            请修改需要更正的字段，或填写事由说明（不少于4字）后发起
          </span>
        </div>

        <div class="footer-action-buttons">
          <button type="button" class="btn-cancel" @click="handleClose" :disabled="submitting">取消</button>
          <button type="button" class="btn-submit" @click="handleSubmit" :disabled="submitting">
            <span v-if="submitting">提请提交中...</span>
            <span v-else>确认发起联合会审 ➔</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { createJointReview } from '../services/jointReviewApi'

const props = defineProps({
  visible: { type: Boolean, default: false },
  order: { type: Object, default: () => null },
  orderData: { type: Object, default: () => null },
})

const emit = defineEmits(['close', 'success'])

const quickReasons = [
  { label: '实收短缺', text: '经现场实物吊装核验并清点，实到数量存在短缺，特提请供方核对随车出厂清单并协同更正。' },
  { label: '随车磅单差异', text: '经核对随车地磅单与出库单，换算米数/吨位存在出入，提请供方与现场负责人联合会审更正。' },
  { label: '规格型号更正', text: '到场实物管径/壁厚与系统登记规格不符，现提请各方会审更正为现场实际型号。' },
  { label: '送货车牌更正', text: '现场实际送货车辆与系统登记车牌不符，提请更正车牌以归档留存。' },
  { label: '外观异议协商', text: '物资送达现场，实物存在局部外观/防护层异议，提请各责任方开展现场会审协商处理。' },
]

function applyQuickReason(qr) {
  if (!reviewReason.value || reviewReason.value.trim().length === 0) {
    reviewReason.value = qr.text
  } else {
    reviewReason.value = `${reviewReason.value.trim()} ${qr.text}`
  }
}

function formatDiff(newVal, oldVal) {
  const n = Number(newVal)
  const o = Number(oldVal)
  if (isNaN(n) || isNaN(o)) return ''
  const diff = n - o
  return diff > 0 ? `+${diff}` : `${diff}`
}

// 统一解析订单对象，无论是父组件传 :order 还是 :order-data 均 100% 响应
const order = computed(() => props.order || props.orderData || null)

const isPipe = computed(() => {
  if (!order.value) return true
  return order.value.order_category === 'pipe' || order.value.category === 'pipe' || Boolean(order.value.pipe_model_id)
})

const orderPipeModelName = computed(() => {
  if (!order.value) return ''
  return order.value.pipe_model_name || order.value.pipeModelName || order.value.model_name || order.value.specification || order.value.pipe_model_id || ''
})

const displayOrderCode = computed(() => {
  if (!order.value) return '—'
  if (!isPipe.value && order.value.shipment_no) {
    return order.value.shipment_no
  }
  return order.value.order_no || order.value.delivery_code || order.value.shipment_no || '—'
})

const form = reactive({
  shipped_qty: null,
  pipe_model_id: '',
  vehicle_plate_no: '',
  ship_remark: '',
})

// 管件车次下的各订单明细表单
const fittingItemsForm = ref([])

const reviewReason = ref('')
const attachments = ref([])
const submitting = ref(false)
const submitError = ref('')
const fileInputRef = ref(null)
const reasonTextareaRef = ref(null)

function isFittingItemEditable(item) {
  return !item.status || !order.value?.status || item.status === order.value.status
}

function isFittingItemModified(item) {
  if (!item || !isFittingItemEditable(item)) return false
  const typeChanged = (item.fitting_type || '').trim() !== (item.orig_fitting_type || '').trim()
  const specChanged = (item.model_spec || '').trim() !== (item.orig_model_spec || '').trim()
  const qtyChanged = item.shipped_qty !== null && item.shipped_qty !== '' && Number(item.shipped_qty) !== Number(item.orig_shipped_qty)
  return typeChanged || specChanged || qtyChanged
}

watch(
  () => order.value,
  (newVal) => {
    if (!newVal) return
    form.shipped_qty = newVal.shipped_qty !== undefined && newVal.shipped_qty !== null ? newVal.shipped_qty : null
    form.pipe_model_id = orderPipeModelName.value || newVal.pipe_model_id || ''
    form.vehicle_plate_no = newVal.vehicle_plate_no || newVal.plateNo || newVal.vehiclePlateNo || ''
    form.ship_remark = newVal.ship_remark || ''
    reviewReason.value = ''
    attachments.value = []
    submitError.value = ''

    if (Array.isArray(newVal.items) && newVal.items.length > 0) {
      fittingItemsForm.value = newVal.items.map(it => ({
        id: it.id,
        order_no: it.order_no || '—',
        fitting_type: it.fitting_type || '',
        orig_fitting_type: it.fitting_type || '',
        model_spec: it.model_spec || it.specification || '',
        orig_model_spec: it.model_spec || it.specification || '',
        shipped_qty: it.shipped_qty !== undefined && it.shipped_qty !== null ? it.shipped_qty : null,
        orig_shipped_qty: it.shipped_qty !== undefined && it.shipped_qty !== null ? it.shipped_qty : null,
        unit: it.unit || '件',
        status: it.status,
      }))
    } else if (!isPipe.value) {
      fittingItemsForm.value = [{
        id: newVal.id || newVal.delivery_id || newVal.order_id,
        order_no: newVal.order_no || newVal.delivery_code || newVal.shipment_no || '—',
        fitting_type: newVal.fitting_type || '',
        orig_fitting_type: newVal.fitting_type || '',
        model_spec: newVal.model_spec || newVal.specification || '',
        orig_model_spec: newVal.model_spec || newVal.specification || '',
        shipped_qty: newVal.shipped_qty !== undefined && newVal.shipped_qty !== null ? newVal.shipped_qty : null,
        orig_shipped_qty: newVal.shipped_qty !== undefined && newVal.shipped_qty !== null ? newVal.shipped_qty : null,
        unit: newVal.unit || '件',
        status: newVal.status,
      }]
    } else {
      fittingItemsForm.value = []
    }
  },
  { immediate: true }
)

const sceneActorsText = computed(() => {
  if (!order.value) return '供货厂家 + 现场负责人'
  const st = order.value.status || ''
  if (st === 'pending_arrival') {
    return '供货厂家（1 方表决通过即生效）'
  }
  if (st === 'pending_receive' || st === 'pending_diff_approve') {
    return '供货厂家 + 现场负责人（2 方全票表决通过即生效）'
  }
  if (st === 'pending_warehouse') {
    return '供货厂家 + 现场负责人（精准排除施工方干扰，双签即可生效）'
  }
  return '供货厂家 + 现场负责人'
})

const diffList = computed(() => {
  if (!order.value) return []
  const o = order.value
  const list = []

  if (isPipe.value) {
    if (form.shipped_qty !== null && form.shipped_qty !== '' && Number(form.shipped_qty) !== Number(o.shipped_qty)) {
      list.push({
        key: 'shipped_qty',
        label: '直管发货数量',
        oldVal: `${o.shipped_qty} 米`,
        newVal: `${form.shipped_qty} 米`,
      })
    }
    const origModel = (orderPipeModelName.value || '').trim()
    if (form.pipe_model_id && form.pipe_model_id.trim() !== origModel) {
      list.push({
        key: 'pipe_model_id',
        label: '直管规格型号',
        oldVal: origModel || '空',
        newVal: form.pipe_model_id.trim(),
      })
    }
    const origPlate = (o.vehicle_plate_no || o.plateNo || o.vehiclePlateNo || '').trim()
    if (form.vehicle_plate_no && form.vehicle_plate_no.trim() !== origPlate) {
      list.push({
        key: 'vehicle_plate_no',
        label: '送货车牌',
        oldVal: origPlate || '空',
        newVal: form.vehicle_plate_no.trim(),
      })
    }
  } else {
    // fitting mode
    const origPlate = (o.vehicle_plate_no || o.plateNo || o.vehiclePlateNo || '').trim()
    if (form.vehicle_plate_no && form.vehicle_plate_no.trim() !== origPlate) {
      list.push({
        key: 'vehicle_plate_no',
        label: '整车送货车牌',
        oldVal: origPlate || '空',
        newVal: form.vehicle_plate_no.trim(),
      })
    }
    fittingItemsForm.value.forEach((it, idx) => {
      if (isFittingItemModified(it)) {
        const changes = []
        if ((it.fitting_type || '').trim() !== (it.orig_fitting_type || '').trim()) {
          changes.push(`品类: ${it.orig_fitting_type || '空'}➔${it.fitting_type || '空'}`)
        }
        if ((it.model_spec || '').trim() !== (it.orig_model_spec || '').trim()) {
          changes.push(`规格: ${it.orig_model_spec || '空'}➔${it.model_spec || '空'}`)
        }
        if (Number(it.shipped_qty) !== Number(it.orig_shipped_qty)) {
          changes.push(`数量: ${it.orig_shipped_qty}➔${it.shipped_qty} ${it.unit || '件'}`)
        }
        list.push({
          key: `item_${it.id || idx}`,
          label: `订单 ${it.order_no}`,
          oldVal: `${it.orig_fitting_type || ''} ${it.orig_model_spec || ''} (${it.orig_shipped_qty} ${it.unit || '件'})`,
          newVal: changes.join('; '),
        })
      }
    })
  }

  if ((form.ship_remark || '') !== (o.ship_remark || '')) {
    list.push({ key: 'ship_remark', label: '发货备注', oldVal: o.ship_remark || '空', newVal: form.ship_remark || '空' })
  }
  return list
})

const changedFieldsCount = computed(() => diffList.value.length)

const isReadyToSubmit = computed(() => {
  const reasonText = (reviewReason.value || '').trim()
  return (changedFieldsCount.value > 0 || reasonText.length >= 4) && reasonText.length >= 4
})

function focusReasonInput() {
  if (reasonTextareaRef.value) {
    reasonTextareaRef.value.focus()
  }
}

function triggerFileInput() {
  if (fileInputRef.value) fileInputRef.value.click()
}

function handleFileUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  if (attachments.value.length >= 3) {
    submitError.value = '最多支持添加 3 张现场照片凭证'
    return
  }
  const reader = new FileReader()
  reader.onload = (event) => {
    attachments.value.push({
      name: file.name,
      url: event.target.result,
    })
    if (fileInputRef.value) fileInputRef.value.value = ''
  }
  reader.readAsDataURL(file)
}

function removeAttachment(idx) {
  attachments.value.splice(idx, 1)
}

function handleClose() {
  emit('close')
}

async function handleSubmit() {
  submitError.value = ''
  const currentOrder = order.value
  if (!currentOrder) {
    submitError.value = '未检测到订单数据，请重新点击打开'
    return
  }

  const reasonText = (reviewReason.value || '').trim()
  const hasPatch = changedFieldsCount.value > 0

  if (!hasPatch && reasonText.length < 4) {
    submitError.value = '请在上方修改需要更正的项目（如发货数量、规格、车牌），或在事由框填写现场情况说明（至少4个字）'
    focusReasonInput()
    return
  }

  if (reasonText.length < 4) {
    submitError.value = '请在事由框中详细填写提请会审事由说明（不少于4个字符，以便各方核准）'
    focusReasonInput()
    return
  }

  const patch = {}
  if (isPipe.value) {
    if (form.shipped_qty !== null && form.shipped_qty !== '' && Number(form.shipped_qty) !== Number(currentOrder.shipped_qty)) {
      patch.shipped_qty = Number(form.shipped_qty)
    }
    const origModel = (orderPipeModelName.value || '').trim()
    if (form.pipe_model_id && form.pipe_model_id.trim() !== origModel) {
      patch.pipe_model_id = form.pipe_model_id.trim()
    }
    const origPlate = (currentOrder.vehicle_plate_no || currentOrder.plateNo || currentOrder.vehiclePlateNo || '').trim()
    if (form.vehicle_plate_no && form.vehicle_plate_no.trim() !== origPlate) {
      patch.vehicle_plate_no = form.vehicle_plate_no.trim()
    }
  } else {
    // fitting mode
    const origPlate = (currentOrder.vehicle_plate_no || currentOrder.plateNo || currentOrder.vehiclePlateNo || '').trim()
    if (form.vehicle_plate_no && form.vehicle_plate_no.trim() !== origPlate) {
      patch.vehicle_plate_no = form.vehicle_plate_no.trim()
    }
    const modifiedItems = fittingItemsForm.value.filter(it => isFittingItemModified(it))
    if (modifiedItems.length > 0) {
      patch.items = modifiedItems.map(it => ({
        id: it.id,
        order_no: it.order_no,
        fitting_type: it.fitting_type,
        model_spec: it.model_spec,
        shipped_qty: Number(it.shipped_qty),
        unit: it.unit || '件',
      }))
    }
  }

  if ((form.ship_remark || '') !== (currentOrder.ship_remark || '')) {
    patch.ship_remark = form.ship_remark || ''
  }
  const quantities = [patch.shipped_qty, ...(patch.items || []).map(item => item.shipped_qty)].filter(value => value !== undefined)
  if (quantities.some(value => !Number.isFinite(value) || value <= 0 || Math.abs(value * 100 - Math.round(value * 100)) > 0.000001)) {
    submitError.value = '发货数量必须为有限正数，最多2位小数'
    return
  }
  const deliveryId = currentOrder.id || currentOrder.delivery_id || currentOrder.order_id
  const orderCategory = currentOrder.order_category || currentOrder.category || (isPipe.value ? 'pipe' : 'fitting')

  submitting.value = true
  try {
    const res = await createJointReview({
      order_category: orderCategory,
      delivery_id: Number(deliveryId),
      proposed_patch: patch,
      review_reason: reasonText,
      attachments: attachments.value,
    })
    emit('success', res)
    emit('close')
  } catch (err) {
    submitError.value = err.message || '提请联合会审失败'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.review-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(5px);
  z-index: 1200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.review-modal-card {
  background: #ffffff;
  border-radius: 14px;
  width: 100%;
  max-width: 780px;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(0, 0, 0, 0.05);
  overflow: hidden;
  animation: modalScaleIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes modalScaleIn {
  from { opacity: 0; transform: scale(0.97); }
  to { opacity: 1; transform: scale(1); }
}

.modal-header {
  padding: 14px 20px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #ffffff;
}

.modal-title-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-icon-badge {
  font-size: 20px;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(249, 115, 22, 0.1);
}

.modal-title-group h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.modal-subtitle {
  margin: 2px 0 0;
  font-size: 12px;
  color: #64748b;
}

.btn-close {
  background: none;
  border: none;
  font-size: 18px;
  color: #94a3b8;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.btn-close:hover {
  color: #0f172a;
  background: #f1f5f9;
}

.modal-body {
  padding: 16px 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* 1. 一体化单据与会签概览卡片 */
.dossier-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dossier-main-row {
  display: grid;
  grid-template-columns: 1.2fr 0.9fr 1.8fr 1fr 1.1fr;
  gap: 10px;
}

.dossier-cell-order,
.dossier-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}

.dossier-lbl {
  font-size: 11px;
  color: #64748b;
  font-weight: 500;
}

.dossier-val-wrap {
  display: flex;
  align-items: center;
  gap: 4px;
  overflow: hidden;
}

.dossier-val {
  font-size: 12.5px;
  font-weight: 700;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.lock-mini-tag {
  font-size: 10px;
  color: #94a3b8;
}

.dossier-signoff-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 8px;
  border-top: 1px dashed #e2e8f0;
  font-size: 11.5px;
}

.signoff-actors {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #1e40af;
  font-weight: 600;
}

.signoff-actor-chip {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  padding: 1px 8px;
  border-radius: 4px;
  color: #1d4ed8;
}

.signoff-rule-hint {
  font-size: 11px;
  color: #64748b;
}

/* 2. 拟更正表单区 */
.patch-section-card {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px 14px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-title {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}

.section-hint {
  font-size: 11.5px;
  color: #94a3b8;
}

.form-grid-compact {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.form-field-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  transition: all 0.15s ease;
}

.form-field-card.is-modified {
  border-color: #3b82f6;
  background: #f0f7ff;
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.2);
}

.field-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11.5px;
}

.field-header label {
  font-weight: 600;
  color: #334155;
}

.orig-tag {
  color: #64748b;
  font-size: 11.5px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  padding: 1px 8px;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

.orig-tag .orig-val-text {
  color: #0f172a;
  font-weight: 700;
}

.orig-tag-long {
  max-width: none;
  white-space: normal;
  word-break: break-all;
}

.field-input {
  height: 32px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 8px;
  font-size: 12.5px;
  color: #0f172a;
  background: #ffffff;
  outline: none;
  transition: all 0.15s ease;
  width: 100%;
  box-sizing: border-box;
}

.field-input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
}

.input-with-unit {
  position: relative;
  display: flex;
  align-items: center;
}

.input-with-unit .field-input {
  padding-right: 28px;
  font-weight: 700;
  color: #1d4ed8;
}

.unit-text {
  position: absolute;
  right: 8px;
  font-size: 11.5px;
  color: #64748b;
  pointer-events: none;
}

.sub-input-row {
  display: flex;
  gap: 6px;
}

.flex-1 { flex: 1; }
.flex-2 { flex: 1.5; }

.diff-indicator {
  margin-top: 1px;
}

.diff-chip {
  display: inline-block;
  background: #ecfdf5;
  color: #059669;
  border: 1px solid #a7f3d0;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

/* 管件车载各订单明细列表样式 */
.fitting-items-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 4px;
}

.fitting-items-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 280px;
  overflow-y: auto;
  padding-right: 4px;
}

.fitting-item-row-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: all 0.15s ease;
}

.fitting-item-row-card.is-modified {
  border-color: #3b82f6;
  background: #f0f7ff;
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.2);
}

.fitting-item-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11.5px;
}

.item-meta-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.item-seq-badge {
  background: #e2e8f0;
  color: #475569;
  font-size: 10.5px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 4px;
}

.item-order-no {
  font-size: 12px;
  font-weight: 700;
  color: #1e293b;
}

.modified-badge {
  background: #ecfdf5;
  color: #059669;
  border: 1px solid #a7f3d0;
  font-size: 10.5px;
  padding: 0 5px;
  border-radius: 4px;
  font-weight: 600;
}

.item-orig-text {
  font-size: 11px;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 360px;
}

.fitting-item-card-inputs {
  display: grid;
  grid-template-columns: 1.2fr 2fr 1.1fr;
  gap: 8px;
}

.sub-input-col {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.sub-col-label {
  font-size: 11px;
  color: #475569;
  font-weight: 500;
}

.sub-input {
  height: 28px !important;
  padding: 0 6px !important;
  font-size: 12px !important;
}

.input-changed {
  border-color: #2563eb !important;
  background: #ffffff !important;
  font-weight: 600;
  color: #1d4ed8;
}

/* 3. 事由说明区 */
.reason-section-card {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px 14px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.reason-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.reason-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}

.reason-char-count {
  font-size: 11px;
  font-weight: normal;
  color: #f59e0b;
}

.reason-char-count.is-satisfied {
  color: #059669;
  font-weight: 600;
}

.quick-reasons-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.quick-prefix {
  font-size: 11px;
  color: #94a3b8;
}

.quick-reason-chip {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 2px 7px;
  font-size: 11px;
  color: #475569;
  cursor: pointer;
  transition: all 0.15s ease;
}

.quick-reason-chip:hover {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #1d4ed8;
  transform: translateY(-1px);
}

.reason-textarea {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 12.5px;
  color: #0f172a;
  outline: none;
  resize: vertical;
  line-height: 1.5;
  transition: all 0.15s ease;
  font-family: inherit;
  box-sizing: border-box;
  width: 100%;
}

.reason-textarea:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
}

/* 附件栏 */
.attachment-bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 4px;
}

.btn-upload-compact {
  height: 28px;
  padding: 0 10px;
  font-size: 11.5px;
  font-weight: 500;
  border: 1px dashed #cbd5e1;
  background: #f8fafc;
  color: #475569;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.btn-upload-compact:hover:not(:disabled) {
  border-color: #2563eb;
  color: #1d4ed8;
  background: #eff6ff;
}

.attachment-thumbs-list {
  display: flex;
  gap: 6px;
  align-items: center;
}

.att-thumb-box {
  position: relative;
  width: 36px;
  height: 36px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #cbd5e1;
}

.att-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.btn-remove-thumb {
  position: absolute;
  top: 1px;
  right: 1px;
  background: rgba(0, 0, 0, 0.65);
  color: #fff;
  border: none;
  font-size: 9px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.att-hint-text {
  font-size: 11px;
  color: #94a3b8;
}

.submit-error-banner {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #dc2626;
  font-size: 12px;
  padding: 8px 12px;
  border-radius: 6px;
}

/* 4. 底栏 (Sticky Footer) */
.modal-footer {
  padding: 12px 20px;
  border-top: 1px solid #e2e8f0;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.footer-status-guide {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  overflow: hidden;
}

.guide-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #cbd5e1;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.guide-dot.has-patch {
  background: #3b82f6;
}

.guide-dot.is-ready {
  background: #10b981;
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.4);
}

.guide-text {
  color: #475569;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.guide-text.success {
  color: #059669;
  font-weight: 600;
}

.guide-text.muted {
  color: #94a3b8;
}

.footer-action-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.btn-cancel {
  height: 32px;
  padding: 0 14px;
  font-size: 12.5px;
  font-weight: 500;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #475569;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-cancel:hover:not(:disabled) {
  background: #f1f5f9;
  color: #0f172a;
}

.btn-submit {
  height: 32px;
  padding: 0 16px;
  font-size: 12.5px;
  font-weight: 600;
  border: 1px solid #ea580c;
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
  color: #ffffff;
  border-radius: 6px;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(234, 88, 12, 0.2);
  transition: all 0.15s ease;
  white-space: nowrap;
}

.btn-submit:hover:not(:disabled) {
  background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgba(234, 88, 12, 0.25);
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}
</style>
