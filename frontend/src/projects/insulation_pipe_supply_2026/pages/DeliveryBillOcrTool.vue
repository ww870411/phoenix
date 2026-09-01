<template>
  <div class="ocr-tool-container">
    <!-- 工具顶栏与介绍说明 -->
    <div class="panel-title-row" style="flex-wrap: wrap; gap: 12px;">
      <div>
        <h2 style="display: flex; align-items: center; gap: 8px;">
          <span>📷 业务单据智能识别</span>
        </h2>
      </div>
      <div class="top-actions-bar">
        <button
          v-if="extractedResult"
          type="button"
          class="btn ghost compact-btn"
          @click="handleReset"
        >
          🔄 重新拍摄
        </button>
        <button
          v-if="extractedResult"
          type="button"
          class="btn ghost compact-btn"
          @click="copyJsonResult"
        >
          📋 复制 JSON
        </button>
        <button
          v-if="extractedResult"
          type="button"
          class="btn primary compact-btn"
          :disabled="isExporting"
          @click="exportExtractedExcel"
        >
          {{ isExporting ? '⏳ 正在导出…' : '📥 导出 Excel' }}
        </button>
      </div>
    </div>

    <!-- 导出成功轻提示 Toast -->
    <transition name="fade">
      <div v-if="exportSuccessToast" class="ocr-toast-notification">
        <span class="toast-icon">🎉</span>
        <span class="toast-msg">Excel 文件已生成并触发下载，请查看浏览器下载栏！</span>
      </div>
    </transition>

    <!-- 隐藏式文件与相机拍照输入控件 -->
    <input
      ref="fileInputRef"
      type="file"
      accept="image/jpeg,image/png,image/webp,image/bmp"
      style="display: none;"
      @change="handleFileSelected"
    />
    <input
      ref="cameraInputRef"
      type="file"
      accept="image/*"
      capture="environment"
      style="display: none;"
      @change="handleFileSelected"
    />

    <!-- 0. 功能维护中状态提示卡片 -->
    <div
      v-if="serviceChecked && !isServiceEnabled && !extractedResult"
      class="ocr-maintenance-card"
    >
      <div class="maintenance-icon">🛠️</div>
      <h3 class="maintenance-title">业务单据智能识别功能维护中</h3>
      <p class="maintenance-desc">
        当前单据智能识别服务正在进行系统维护与升级，暂不提供在线拍照与单据结构化解析服务。<br />
        如有紧急单据录入需求，请联系系统管理员或稍后再试。
      </p>
      <div class="maintenance-status-badge">
        <span>维护模式生效中 · 暂停拍照与图片识别</span>
      </div>
    </div>

    <!-- 1. 未识别状态：拍照/上传引导卡片 -->
    <div
      v-if="isServiceEnabled && !extractedResult && !loading"
      class="upload-dropzone-card"
      :class="{ 'is-dragging': isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleFileDrop"
      @paste="handlePaste"
    >
      <div class="dropzone-inner">
        <div class="drop-illustration">📄</div>
        <h3 class="drop-title">拍摄或上传业务单据照片</h3>
        <p class="drop-subtitle">
          支持移动端相机即拍即识，或从相册/电脑上传单据图片，支持直接截图 <code>Ctrl + V</code> 粘贴
        </p>

        <div class="action-buttons-group">
          <button type="button" class="btn primary btn-large" @click="triggerCamera">
            <span class="btn-icon">📷</span>
            <span>拍照快速识别</span>
          </button>
          <button type="button" class="btn secondary btn-large" @click="triggerUpload">
            <span class="btn-icon">📁</span>
            <span>选择本地照片</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 2. 识别加载中状态 (真实、克制的标准加载提示) -->
    <div v-if="loading" class="ocr-loading-card">
      <div class="loading-visual-area">
        <div class="loading-spinner-ring"></div>
      </div>
      
      <h3 class="loading-title">正在识别单据并提取明细台账...</h3>
      <p class="loading-sub-desc">已提交单据图像进行版面分析与表格结构提取，请稍候...</p>
    </div>

    <!-- 错误警告提示 -->
    <div v-if="errorMessage" class="error-banner">
      <span class="err-icon">⚠️</span>
      <div class="err-content">
        <strong>单据识别提示：</strong>
        <span>{{ errorMessage }}</span>
      </div>
      <button type="button" class="btn-retry" @click="retryLastRecognition">
        重试
      </button>
    </div>

    <!-- 3. 上下分段现代工作台（识别完成呈现） -->
    <div v-if="extractedResult && !loading" class="extracted-workspace-stack">
      <!-- 上半部分：单据原图核对区 -->
      <div class="doc-preview-panel">
        <div class="panel-section-header">
          <div class="header-left">
            <span class="sec-icon">🖼️</span>
            <strong>单据原件影像</strong>
            <span class="panel-tag-hint">（点击照片可开启全屏高清放大灯箱，支持滚轮自由缩放与按住平移）</span>
          </div>
          <div class="header-tools">
            <button
              type="button"
              class="btn-tool"
              title="点击全屏放大查看高清大图细节"
              @click="openLightbox"
            >
              🔍 放大查看
            </button>
            <button
              type="button"
              class="btn-tool"
              title="顺时针旋转90度"
              @click="rotateImage(90)"
            >
              🔄 旋转 90°
            </button>
            <button
              type="button"
              class="btn-tool"
              title="更换其他照片重新识别"
              @click="triggerUpload"
            >
              📁 更换照片
            </button>
          </div>
        </div>

        <div class="image-viewer-viewport" @click="openLightbox">
          <div class="image-overlay-hint">
            <span>🔍 点击开启全屏高清放大灯箱</span>
          </div>
          <img
            v-if="previewDataUrl"
            :src="previewDataUrl"
            alt="单据照片"
            class="doc-img"
            :style="{ transform: `rotate(${imageRotation}deg)` }"
          />
        </div>

        <div class="image-meta-info" v-if="compressedInfo">
          <span>📷 原始影像规格：{{ compressedInfo.width }} × {{ compressedInfo.height }} 像素</span>
          <span class="preview-mode-hint">💡 建议对比原图校对下方数据，支持直接修改条目与单元格</span>
        </div>
      </div>

      <!-- 下半部分：单据信息与 RevoGrid 电子表格明细 -->
      <div class="doc-table-panel">
        <!-- 顶部综合状态与单据名称栏 -->
        <div class="doc-header-banner">
          <div class="doc-header-left">
            <div class="doc-title-box">
              <span class="doc-title-icon">📄</span>
              <input
                v-model="extractedResult.document_title"
                class="doc-title-input"
                placeholder="单据名称"
                title="点击可直接修改单据名称"
              />
            </div>
            
            <div class="verification-badge-pill verified">
              <span class="badge-icon">✅</span>
              <span class="badge-text">解析完成</span>
            </div>
          </div>

          <div class="doc-header-right">
            <button
              type="button"
              class="btn-action-primary"
              :disabled="isExporting"
              @click="exportExtractedExcel"
            >
              {{ isExporting ? '⏳ 正在生成…' : '📥 导出 Excel' }}
            </button>
          </div>
        </div>

        <!-- 单据主头信息区 (原汁原味动态提取卡片网格) -->
        <div class="bill-master-summary-card">
          <div class="master-card-header">
            <div class="section-badge-title">
              <span>📌 单据抬头信息</span>
              <span class="section-count-tag">{{ extractedResult.metadata_fields?.length || 0 }} 项</span>
            </div>
          </div>

          <div class="master-badges-grid">
            <div
              v-for="(field, idx) in extractedResult.metadata_fields"
              :key="idx"
              class="master-chip"
            >
              <div class="chip-header">
                <input
                  v-model="field.label"
                  class="chip-label-input"
                  placeholder="项目名"
                />
                <button
                  type="button"
                  class="btn-delete-chip"
                  title="删除该项"
                  @click="removeMetadataField(idx)"
                >
                  ✖
                </button>
              </div>
              <input
                v-model="field.value"
                class="chip-value-input"
                :class="{ 'font-bold': field.label && (field.label.includes('车') || field.label.includes('号') || field.label.includes('单')) }"
                placeholder="—"
              />
            </div>
          </div>

          <div v-if="extractedResult.remarks !== undefined" class="master-remark-row">
            <span class="remark-tag">📝 附注 / 备注：</span>
            <input
              v-model="extractedResult.remarks"
              class="remark-input"
              placeholder="可在此输入单据总备注或说明..."
            />
          </div>
        </div>

        <!-- 电子表格明细主区域 -->
        <div class="grid-section-container">
          <div class="grid-toolbar">
            <div class="toolbar-left">
              <span class="grid-title">📊 单据明细台账</span>
              <span class="grid-badge-pill">共 <strong>{{ extractedResult?.table_rows?.length || 0 }}</strong> 行</span>
            </div>
            <div class="toolbar-right">
              <button type="button" class="btn-grid-action" @click="addGridRow">
                ➕ 增加明细行
              </button>
              <button
                type="button"
                class="btn-grid-action btn-danger-action"
                :disabled="!extractedResult?.table_rows?.length"
                @click="deleteLastGridRow"
              >
                🗑️ 删除末行
              </button>
              <button type="button" class="btn-grid-action" @click="copyJsonResult">
                📋 复制 JSON
              </button>
            </div>
          </div>

          <!-- RevoGrid 电子表格主区域 -->
          <div class="revogrid-container" style="min-height: 280px; border: 1px solid #cbd5e1; border-radius: 6px; overflow: hidden; background: #fff;">
            <RevoGrid
              ref="gridRef"
              :row-headers="true"
              :hide-attribution="true"
              :stretch="true"
              :row-size="32"
              :resize="true"
              :range="true"
              :can-focus="true"
              :apply-on-close="true"
              :columns="gridColumns"
              :source="gridSource"
              style="height: 380px; width: 100%;"
              @afteredit="handleAfterEdit"
              @afterEdit="handleAfterEdit"
            />
          </div>
        </div>

      </div>
    </div>

    <!-- 4. 单据原图全屏放大灯箱 / 缩放查看器 -->
    <div
      v-if="isLightboxOpen"
      class="image-lightbox-backdrop"
      tabindex="-1"
      @keydown.esc="closeLightbox"
      @click.self="closeLightbox"
    >
      <div class="lightbox-toolbar">
        <div class="lightbox-title-text">
          <span>🔍 {{ extractedResult?.document_title || '单据原图细节查看' }}</span>
          <span class="lightbox-scale-indicator">{{ Math.round(lightboxScale * 100) }}%</span>
        </div>
        <div class="lightbox-btn-group">
          <button type="button" class="btn-lightbox" title="放大 (+25%)" @click="zoomIn">
            ➕ 放大
          </button>
          <button type="button" class="btn-lightbox" title="缩小 (-25%)" @click="zoomOut">
            ➖ 缩小
          </button>
          <button type="button" class="btn-lightbox" title="重置 1:1" @click="resetZoom">
            📐 1:1
          </button>
          <button type="button" class="btn-lightbox" title="适应窗口" @click="fitZoom">
            🖼️ 适应
          </button>
          <button type="button" class="btn-lightbox" title="顺时针旋转 90°" @click="rotateImage(90)">
            🔄 旋转
          </button>
          <button type="button" class="btn-lightbox btn-close" title="关闭 (Esc)" @click="closeLightbox">
            ✖ 关闭
          </button>
        </div>
      </div>

      <div
        class="lightbox-canvas-viewport"
        :class="{ 'is-dragging': isDraggingImage }"
        @wheel.prevent="handleWheelZoom"
        @mousedown="startImageDrag"
        @mousemove="onImageDrag"
        @mouseup="stopImageDrag"
        @mouseleave="stopImageDrag"
      >
        <img
          :src="previewDataUrl"
          alt="单据高清大图"
          class="lightbox-doc-img"
          :style="{
            transform: `translate(${lightboxTranslate.x}px, ${lightboxTranslate.y}px) scale(${lightboxScale}) rotate(${lightboxRotate}deg)`
          }"
          draggable="false"
        />
      </div>
      <div class="lightbox-footer-tip">
        <span>💡 滚轮缩放 / 按住鼠标左键拖拽平移 / 点击遮罩或按 Esc 关闭</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, nextTick } from 'vue'
import RevoGrid from '@revolist/vue3-datagrid'
import * as XLSX from 'xlsx-js-style'
import {
  ocrDeliveryBill,
  getOcrToolConfig,
} from '../../daily_report_25_26/services/api'

const props = defineProps({
  projectKey: {
    type: String,
    default: 'insulation_pipe_supply_2026'
  },
  selectedSection1Id: {
    type: String,
    default: ''
  },
  section1Options: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['navigate-tab'])

const fileInputRef = ref(null)
const cameraInputRef = ref(null)

const isDragging = ref(false)
const loading = ref(false)
const loadingStatusText = ref('')
const errorMessage = ref('')

// 服务可用状态（正常服务 vs 功能维护中）
const isServiceEnabled = ref(true)
const serviceChecked = ref(false)

async function checkServiceStatus() {
  try {
    const cfg = await getOcrToolConfig(props.projectKey)
    isServiceEnabled.value = cfg.enabled !== false
  } catch (err) {
    console.warn('获取单据识别服务状态失败，默认允许使用:', err)
    isServiceEnabled.value = true
  } finally {
    serviceChecked.value = true
  }
}

onMounted(() => {
  checkServiceStatus()
})

const previewDataUrl = ref('')
const currentBase64 = ref('')
const imageRotation = ref(0)
const compressedInfo = ref(null)

const isExporting = ref(false)
const exportSuccessToast = ref(false)



// 提取结果与表格数据模型
const extractedResult = ref(null)
const gridRef = ref(null)
const gridColumns = ref([])
const gridSource = ref([])

// 灯箱放大图片状态
const isLightboxOpen = ref(false)
const lightboxScale = ref(1)
const lightboxRotate = ref(0)
const lightboxTranslate = ref({ x: 0, y: 0 })
const isDraggingImage = ref(false)
const dragStartPos = ref({ x: 0, y: 0 })

function syncToGrid(columns, rows) {
  let cols = Array.isArray(columns) && columns.length ? [...columns] : []
  const rawRows = Array.isArray(rows) ? rows : []
  
  if (!cols.length && rawRows.length) {
    cols = Object.keys(rawRows[0] || {})
  }
  if (!cols.length) {
    cols = ['序号', '物资名称/规格', '数量', '单位', '备注']
  }

  gridColumns.value = cols.map((colName, idx) => {
    const isSeq = colName === '序号' || (idx === 0 && colName.includes('序号'))
    let size = 140
    if (isSeq) size = 65
    else if (colName.includes('名称') || colName.includes('品名') || colName.includes('规格') || colName.includes('型号')) size = 190
    else if (colName.includes('单位')) size = 75
    else if (colName.includes('量') || colName.includes('数') || colName.includes('重') || colName.includes('额')) size = 110
    else if (colName.includes('备注')) size = 160
    
    return {
      prop: colName,
      name: colName,
      size,
      readonly: false,
      sortable: true,
      pin: isSeq ? 'colPinStart' : undefined
    }
  })

  gridSource.value = rawRows.map(r => ({ ...r }))
  nextTick(() => {
    if (gridRef.value && typeof gridRef.value.refresh === 'function') {
      gridRef.value.refresh()
    }
  })
}

// 自动计算所有数值型列的合计
const computeTotals = computed(() => {
  if (!extractedResult.value || !extractedResult.value.table_rows) return {}
  const cols = (Array.isArray(extractedResult.value.table_columns) && extractedResult.value.table_columns.length)
    ? extractedResult.value.table_columns
    : (gridColumns.value.map(c => c.prop) || [])
  const rows = extractedResult.value.table_rows || []
  const totals = {}

  cols.forEach(col => {
    if (col === '序号') return
    let isNumeric = true
    let sum = 0
    let count = 0

    for (const row of rows) {
      const val = row[col]
      if (val === undefined || val === null || String(val).trim() === '') continue
      const num = Number(val)
      if (isNaN(num)) {
        isNumeric = false
        break
      }
      sum += num
      count++
    }

    if (isNumeric && count > 0) {
      totals[col] = Number.isInteger(sum) ? sum : Number(sum.toFixed(3))
    }
  })

  return totals
})



function triggerUpload() {
  if (!isServiceEnabled.value) {
    errorMessage.value = '业务单据智能识别功能维护中，暂不可用。'
    return
  }
  errorMessage.value = ''
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
    fileInputRef.value.click()
  }
}

function triggerCamera() {
  if (!isServiceEnabled.value) {
    errorMessage.value = '业务单据智能识别功能维护中，暂不可用。'
    return
  }
  errorMessage.value = ''
  if (cameraInputRef.value) {
    cameraInputRef.value.value = ''
    cameraInputRef.value.click()
  }
}

function formatFileSize(bytes) {
  if (!bytes || bytes <= 0) return '0 KB'
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(0)} KB`
  }
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

// 客户端 Canvas 高清等比智能压缩与规格对齐算法
function compressImageFile(file, maxWidth = 1600, maxHeight = 1600, quality = 0.82) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const rawDataUrl = e.target.result
      const rawBase64 = rawDataUrl.includes('base64,') ? rawDataUrl.split('base64,')[1] : ''
      const img = new Image()
      img.onload = () => {
        let w = img.width
        let h = img.height
        const needsResize = w > maxWidth || h > maxHeight

        if (needsResize) {
          if (w / h > maxWidth / maxHeight) {
            h = Math.round((h * maxWidth) / w)
            w = maxWidth
          } else {
            w = Math.round((w * maxHeight) / h)
            h = maxHeight
          }
        }

        const canvas = document.createElement('canvas')
        canvas.width = w
        canvas.height = h
        const ctx = canvas.getContext('2d')
        ctx.fillStyle = '#FFFFFF'
        ctx.fillRect(0, 0, w, h)
        ctx.drawImage(img, 0, 0, w, h)

        const compressedDataUrl = canvas.toDataURL('image/jpeg', quality)
        const compressedBase64 = compressedDataUrl.split('base64,')[1]
        const compressedBytes = Math.round((compressedBase64.length * 3) / 4)

        // 若无需缩小宽高尺寸且原文件本就小于重编码后体积（例如本身为高压小图），直接采用原图，防止“越压越大”
        if (!needsResize && file.size > 0 && compressedBytes >= file.size) {
          resolve({
            dataUrl: rawDataUrl,
            base64: rawBase64,
            originalSize: file.size,
            compressedSize: file.size,
            width: img.width,
            height: img.height,
            mimeType: file.type || 'image/jpeg',
          })
          return
        }

        resolve({
          dataUrl: compressedDataUrl,
          base64: compressedBase64,
          originalSize: file.size,
          compressedSize: compressedBytes,
          width: w,
          height: h,
          mimeType: 'image/jpeg',
        })
      }
      img.onerror = () => reject(new Error('图片加载失败，请检查文件格式'))
      img.src = rawDataUrl
    }
    reader.onerror = () => reject(new Error('读取本地文件失败'))
    reader.readAsDataURL(file)
  })
}

async function processFile(file) {
  if (!file || !file.type.startsWith('image/')) {
    errorMessage.value = '请选择或拍摄有效的图片格式（JPG / PNG / WEBP）'
    return
  }

  loading.value = true
  errorMessage.value = ''
  loadingStatusText.value = '正在处理照片并解析单据条目与表格数据...'

  try {
    const comp = await compressImageFile(file)
    compressedInfo.value = comp
    previewDataUrl.value = comp.dataUrl
    currentBase64.value = comp.base64
    imageRotation.value = 0

    loadingStatusText.value = '正在解析单据内容并核对条目与表格数据...'
    await executeOcrRecognition(comp.mimeType)
  } catch (err) {
    console.error('单据识别处理异常:', err)
    errorMessage.value = err?.message || '解析单据照片失败'
    loading.value = false
  }
}

async function executeOcrRecognition(mimeType = 'image/jpeg') {
  try {
    const payload = {
      image_base64: currentBase64.value,
      mime_type: mimeType || 'image/jpeg',
      enable_double_check: false,
    }

    const res = await ocrDeliveryBill(props.projectKey, payload)
    const rawData = res.extracted_data || res || {}

    const tableCols = Array.isArray(rawData.table_columns) && rawData.table_columns.length
      ? rawData.table_columns
      : ['序号', '材料名称', '规格型号', '单位', '数量', '备注']
    const tableRows = Array.isArray(rawData.table_rows) ? rawData.table_rows : []

    extractedResult.value = {
      document_title: rawData.document_title || rawData.bill_type || '单据明细台账',
      metadata_fields: Array.isArray(rawData.metadata_fields) ? rawData.metadata_fields : [],
      table_columns: tableCols,
      table_rows: tableRows,
      remarks: rawData.remarks || '',
    }

    syncToGrid(tableCols, tableRows)
  } catch (err) {
    console.error('单据识别请求失败:', err)
    const detailMsg = err?.response?.data?.detail || err?.detail || err?.message || String(err)
    const formattedDetail = typeof detailMsg === 'object' ? JSON.stringify(detailMsg, null, 2) : String(detailMsg)
    
    let userMsg = formattedDetail
    if (userMsg.includes('维护中')) {
      isServiceEnabled.value = false
      userMsg = '业务单据智能识别功能维护中，暂不可用。请稍后再试或联系系统管理员开启服务。'
    } else if (
      userMsg.includes('503') ||
      userMsg.toLowerCase().includes('high demand') ||
      userMsg.toLowerCase().includes('overloaded') ||
      userMsg.toLowerCase().includes('temporarily unavailable') ||
      userMsg.includes('服务器繁忙')
    ) {
      userMsg = '服务器繁忙，请点击重试'
    }
    
    errorMessage.value = userMsg
  } finally {
    loading.value = false
  }
}

function handleAfterEdit(e) {
  if (!e?.detail) return
  const { model, prop, val } = e.detail
  if (model && prop) {
    model[prop] = val
    if (extractedResult.value) {
      extractedResult.value.table_rows = gridSource.value.map(r => ({ ...r }))
    }
  }
}

function addGridRow() {
  const cols = gridColumns.value.map(c => c.prop)
  if (!cols.length) {
    cols.push('序号', '物资名称', '规格型号', '单位', '数量', '备注')
  }
  const rows = [...gridSource.value]
  const lastRow = rows.length > 0 ? rows[rows.length - 1] : null
  const isLastRowTotal = lastRow && Object.values(lastRow).some(v => String(v).includes('合计') || String(v).includes('总计'))

  const regularRowsCount = isLastRowTotal ? rows.length - 1 : rows.length
  const nextSeq = regularRowsCount + 1
  const newRow = {}
  cols.forEach(col => {
    if (col === '序号') {
      newRow[col] = String(nextSeq)
    } else {
      newRow[col] = ''
    }
  })

  if (isLastRowTotal) {
    rows.splice(rows.length - 1, 0, newRow)
  } else {
    rows.push(newRow)
  }
  syncToGrid(cols, rows)
  if (extractedResult.value) {
    extractedResult.value.table_rows = rows.map(r => ({ ...r }))
  }
}

function deleteLastGridRow() {
  if (!gridSource.value.length) return
  const rows = [...gridSource.value]
  const lastRow = rows[rows.length - 1]
  const isLastRowTotal = lastRow && Object.values(lastRow).some(v => String(v).includes('合计') || String(v).includes('总计'))

  if (isLastRowTotal && rows.length > 1) {
    rows.splice(rows.length - 2, 1)
  } else {
    rows.pop()
  }
  const cols = gridColumns.value.map(c => c.prop)
  syncToGrid(cols, rows)
  if (extractedResult.value) {
    extractedResult.value.table_rows = rows.map(r => ({ ...r }))
  }
}

function removeMetadataField(index) {
  if (extractedResult.value?.metadata_fields) {
    extractedResult.value.metadata_fields.splice(index, 1)
  }
}

// 灯箱放大全屏操作
function openLightbox() {
  if (!previewDataUrl.value) return
  lightboxScale.value = 1
  lightboxRotate.value = imageRotation.value
  lightboxTranslate.value = { x: 0, y: 0 }
  isLightboxOpen.value = true
}

function closeLightbox() {
  isLightboxOpen.value = false
}

function zoomIn() {
  lightboxScale.value = Math.min(lightboxScale.value + 0.25, 4)
}

function zoomOut() {
  lightboxScale.value = Math.max(lightboxScale.value - 0.25, 0.5)
}

function resetZoom() {
  lightboxScale.value = 1
  lightboxTranslate.value = { x: 0, y: 0 }
}

function fitZoom() {
  lightboxScale.value = 1
  lightboxTranslate.value = { x: 0, y: 0 }
}

function rotateImage(deg = 90) {
  imageRotation.value = (imageRotation.value + deg) % 360
  lightboxRotate.value = imageRotation.value
}

function handleWheelZoom(e) {
  e.preventDefault()
  const delta = e.deltaY > 0 ? -0.15 : 0.15
  const newScale = Math.min(Math.max(lightboxScale.value + delta, 0.4), 4.5)
  lightboxScale.value = Number(newScale.toFixed(2))
}

function startImageDrag(e) {
  isDraggingImage.value = true
  dragStartPos.value = {
    x: e.clientX - lightboxTranslate.value.x,
    y: e.clientY - lightboxTranslate.value.y
  }
}

function onImageDrag(e) {
  if (!isDraggingImage.value) return
  lightboxTranslate.value = {
    x: e.clientX - dragStartPos.value.x,
    y: e.clientY - dragStartPos.value.y
  }
}

function stopImageDrag() {
  isDraggingImage.value = false
}

function handleKeydown(e) {
  if (e.key === 'Escape' && isLightboxOpen.value) {
    closeLightbox()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

function handleFileSelected(e) {
  const file = e?.target?.files?.[0]
  if (file) {
    processFile(file)
  }
}

function handleFileDrop(e) {
  isDragging.value = false
  const file = e?.dataTransfer?.files?.[0]
  if (file) {
    processFile(file)
  }
}

function handlePaste(e) {
  const items = e?.clipboardData?.items
  if (!items) return
  for (const item of items) {
    if (item.type && item.type.startsWith('image/')) {
      const file = item.getAsFile()
      if (file) {
        processFile(file)
        break
      }
    }
  }
}

function handleReset() {
  extractedResult.value = null
  previewDataUrl.value = ''
  currentBase64.value = ''
  compressedInfo.value = null
  errorMessage.value = ''
  imageRotation.value = 0
}

function retryLastRecognition() {
  if (currentBase64.value) {
    loading.value = true
    errorMessage.value = ''
    loadingStatusText.value = '正在重新解析单据条目与表格数据...'
    executeOcrRecognition()
  }
}

function copyJsonResult() {
  if (!extractedResult.value) return
  const exportPayload = {
    document_title: extractedResult.value.document_title,
    metadata_fields: extractedResult.value.metadata_fields,
    table_columns: extractedResult.value.table_columns,
    table_rows: extractedResult.value.table_rows,
    remarks: extractedResult.value.remarks,
  }
  const str = JSON.stringify(exportPayload, null, 2)
  navigator.clipboard.writeText(str).then(() => {
    alert('已成功复制单据 JSON 数据至剪贴板！')
  }).catch(() => {
    alert('复制失败，请手动选择复制')
  })
}

function exportExtractedExcel() {
  if (!extractedResult.value || isExporting.value) return

  isExporting.value = true

  // 使用 setTimeout(..., 20) 将耗时计算移入微任务队列，确保浏览器先完成按钮“正在导出”的点击动画与视觉反馈
  setTimeout(() => {
    try {
      const wb = XLSX.utils.book_new()
      const res = extractedResult.value || {}
      const title = res.document_title || '单据提取识别台账'
      const metaFields = res.metadata_fields || []
      const cols = res.table_columns || []
      const rows = res.table_rows || []

      // 1. 构造 Excel 主体数据 (干净纯粹，无虚假质检字段)
      const wsData = [
        [title],
        ['导出时间', new Date().toLocaleString()],
      ]

      // 添加 metadata_fields (按每行 2 组排版)
      for (let i = 0; i < metaFields.length; i += 2) {
        const f1 = metaFields[i]
        const f2 = metaFields[i + 1]
        const r = [f1.label || '', f1.value || '']
        if (f2) {
          r.push('', f2.label || '', f2.value || '')
        }
        wsData.push(r)
      }

      if (res.remarks) {
        wsData.push(['单据附注/备注', res.remarks])
      }

      wsData.push([]) // 空行隔开

      // 表格列头
      wsData.push(cols)

      // 表格行
      rows.forEach((row) => {
        const rData = cols.map(c => {
          const v = row[c]
          if (v == null) return ''
          // 若为纯数字且非序号，转为数字类型导出
          if (c !== '序号' && !isNaN(Number(v)) && String(v).trim() !== '') {
            return Number(v)
          }
          return v
        })
        wsData.push(rData)
      })

      // 合计行（若表格行中未包含合计行，则自动追加计算合计行）
      const hasTotalRowAlready = rows.some(r => Object.values(r).some(v => String(v).includes('合计') || String(v).includes('总计')))
      if (!hasTotalRowAlready) {
        const totals = computeTotals.value
        if (Object.keys(totals).length > 0) {
          const totalRow = cols.map((c, idx) => {
            if (idx === 0) return '合计'
            if (totals[c] !== undefined) return totals[c]
            return ''
          })
          wsData.push(totalRow)
        }
      }

      const ws = XLSX.utils.aoa_to_sheet(wsData)

      // 动态列宽
      ws['!cols'] = cols.map(c => {
        if (c === '序号') return { wch: 8 }
        if (c.includes('名称') || c.includes('品名') || c.includes('规格') || c.includes('型号')) return { wch: 24 }
        if (c.includes('单位')) return { wch: 10 }
        if (c.includes('量') || c.includes('数') || c.includes('重') || c.includes('额')) return { wch: 14 }
        return { wch: 18 }
      })

      const safeFileName = `${title.replace(/[\/\\?%*:|"<>]/g, '_')}_${new Date().toISOString().slice(0, 10)}.xlsx`
      XLSX.utils.book_append_sheet(wb, ws, '单据明细台账')
      XLSX.writeFile(wb, safeFileName)

      // 弹出轻量成功 Toast 提示
      exportSuccessToast.value = true
      setTimeout(() => {
        exportSuccessToast.value = false
      }, 3000)
    } catch (err) {
      console.error('导出 Excel 失败:', err)
      alert('导出 Excel 失败: ' + (err?.message || String(err)))
    } finally {
      isExporting.value = false
    }
  }, 20)
}
</script>

<style scoped>
.ocr-tool-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 520px;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

/* 0. 维护中状态提示卡片 */
.ocr-maintenance-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
  border: 2px dashed #fcd34d;
  border-radius: 16px;
  padding: 48px 24px;
  gap: 14px;
  box-shadow: 0 4px 12px rgba(217, 119, 6, 0.06);
  margin-top: 8px;
}

.ocr-maintenance-card .maintenance-icon {
  font-size: 48px;
  line-height: 1;
}

.ocr-maintenance-card .maintenance-title {
  font-size: 18px;
  font-weight: 800;
  color: #92400e;
  margin: 0;
}

.ocr-maintenance-card .maintenance-desc {
  font-size: 13.5px;
  color: #78350f;
  margin: 0;
  line-height: 1.6;
  max-width: 520px;
}

.ocr-maintenance-card .maintenance-status-badge {
  margin-top: 6px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #ffffff;
  border: 1px solid #fde68a;
  padding: 5px 16px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  color: #b45309;
  box-shadow: 0 2px 4px rgba(180, 83, 9, 0.08);
}

.panel-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}



.top-actions-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.compact-btn {
  padding: 6px 12px;
  font-size: 13px;
}

/* 上传卡片 */
.upload-dropzone-card {
  border: 2px dashed #cbd5e1;
  border-radius: 12px;
  padding: 48px 24px;
  text-align: center;
  background: #f8fafc;
  transition: all 0.2s ease;
  cursor: pointer;
}

.upload-dropzone-card:hover,
.upload-dropzone-card.is-dragging {
  border-color: #3b82f6;
  background: #eff6ff;
}

.dropzone-inner {
  max-width: 640px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.drop-illustration {
  font-size: 48px;
}

.drop-title {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}

.drop-subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
  line-height: 1.5;
}

.drop-subtitle code {
  background: #e2e8f0;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}

.action-buttons-group {
  display: flex;
  gap: 16px;
  margin: 12px 0 8px;
}

.btn-large {
  padding: 10px 24px;
  font-size: 15px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border-radius: 8px;
}

/* 加载卡片：动态识别流水线工作台 */
.ocr-loading-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  background: #ffffff;
  border: 1.5px solid #dbeafe;
  border-radius: 14px;
  box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.08);
  gap: 16px;
  text-align: center;
}

.loading-visual-area {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-spinner-ring {
  width: 48px;
  height: 48px;
  border: 4px solid #e2e8f0;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-title {
  font-size: 17px;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
  transition: all 0.2s ease;
}

/* 动态干活播报胶囊 */
.loading-sub-desc {
  font-size: 13px;
  color: #64748b;
  margin: 0;
  max-width: 480px;
}

.error-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fef2f2;
  border: 1px solid #fca5a5;
  color: #991b1b;
  border-radius: 8px;
  padding: 10px 16px;
  gap: 12px;
}

.err-icon {
  font-size: 18px;
}

.err-content {
  flex: 1;
  font-size: 13px;
}

.btn-retry {
  background: #dc2626;
  color: #ffffff;
  border: none;
  border-radius: 4px;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

/* 识别结果工作台：上下垂直堆叠 */
.extracted-workspace-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

/* 上半部分：单据原图卡片 */
.doc-preview-panel {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.panel-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #1e293b;
}

.panel-tag-hint {
  font-size: 12px;
  color: #64748b;
  font-weight: normal;
}

.header-tools {
  display: flex;
  gap: 8px;
}

.btn-tool {
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 4px 10px;
  font-size: 12px;
  color: #334155;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-tool:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.image-viewer-viewport {
  width: 100%;
  max-width: 100%;
  height: 320px;
  background: #0b1120;
  border-radius: 6px;
  overflow: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px;
  box-sizing: border-box;
  position: relative;
  cursor: zoom-in;
}

.image-overlay-hint {
  position: absolute;
  bottom: 12px;
  right: 12px;
  background: rgba(15, 23, 42, 0.75);
  color: #f8fafc;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  pointer-events: none;
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: opacity 0.2s ease;
}

.image-viewer-viewport:hover .image-overlay-hint {
  opacity: 0.95;
}

.doc-img {
  max-width: 100%;
  max-height: 290px;
  object-fit: contain;
  transition: transform 0.25s ease;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.5);
}

.image-meta-info {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #64748b;
  padding: 0 4px;
}

.preview-mode-hint {
  color: #2563eb;
  font-weight: 500;
}

/* 下半部分：单据表格卡片 */
.doc-table-panel {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.doc-header-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 14px;
  flex-wrap: wrap;
  gap: 12px;
}

.doc-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 320px;
  flex-wrap: wrap;
}

.doc-title-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 5px 12px;
  flex: 1;
  min-width: 280px;
  max-width: 100%;
  transition: all 0.2s ease;
}

.doc-title-box:focus-within {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.doc-title-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.doc-title-input {
  border: none;
  background: transparent;
  font-size: 15px;
  font-weight: 700;
  color: #1e3a8a;
  outline: none;
  width: 100%;
  min-width: 220px;
  flex: 1;
}

.doc-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.verification-badge-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  background: #f0fdf4;
  color: #15803d;
  border: 1px solid #bbf7d0;
}

.verification-badge-pill.corrected {
  background: #eff6ff;
  color: #1d4ed8;
  border-color: #bfdbfe;
}



.score-tag {
  font-weight: 600;
  opacity: 0.9;
}

.doc-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-action-primary {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: #ffffff;
  border: none;
  border-radius: 6px;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(37, 99, 235, 0.2);
  transition: all 0.15s ease;
}

.btn-action-primary:hover {
  background: linear-gradient(135deg, #1d4ed8, #1e40af);
}

.btn-action-secondary {
  background: #ffffff;
  color: #334155;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-action-secondary:hover:not(:disabled) {
  background: #f1f5f9;
  color: #0f172a;
}

.btn-action-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-action-ghost {
  background: transparent;
  color: #2563eb;
  border: 1px dashed #bfdbfe;
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-action-ghost:hover {
  background: #eff6ff;
  border-color: #3b82f6;
}

/* 展开的逐项质检纠偏抽屉 */
.verification-details-drawer {
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 6px;
  padding: 10px 14px;
  font-size: 12px;
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid #e2e8f0;
  flex-wrap: wrap;
  gap: 6px;
}

.drawer-title {
  font-weight: 700;
  color: #1e293b;
}

.drawer-summary {
  color: #64748b;
}

.drawer-list {
  margin: 0;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  line-height: 1.5;
}

.drawer-list li {
  color: #475569;
}

/* 单据主头信息卡片网格 */
.bill-master-summary-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.master-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 6px;
  border-bottom: 1px solid #e2e8f0;
}

.section-badge-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}

.section-count-tag {
  font-size: 11px;
  background: #e2e8f0;
  color: #475569;
  padding: 1px 6px;
  border-radius: 999px;
  font-weight: 600;
}

.btn-add-meta {
  font-size: 12px;
  padding: 3px 8px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  color: #334155;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-add-meta:hover {
  background: #f1f5f9;
}

.master-badges-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 8px;
  width: 100%;
  box-sizing: border-box;
}

.master-chip {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 6px 10px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  position: relative;
  transition: border-color 0.15s ease;
}

.master-chip:hover {
  border-color: #94a3b8;
}

.chip-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chip-label-input {
  font-size: 11px;
  color: #64748b;
  font-weight: 600;
  border: none;
  background: transparent;
  width: 80%;
  outline: none;
  padding: 0;
}

.btn-delete-chip {
  background: transparent;
  border: none;
  font-size: 11px;
  color: #94a3b8;
  cursor: pointer;
  padding: 0 2px;
  opacity: 0.6;
}

.btn-delete-chip:hover {
  color: #ef4444;
  opacity: 1;
}

.chip-value-input {
  border: none;
  background: transparent;
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  outline: none;
  width: 100%;
  padding: 0;
}

.chip-value-input.font-bold {
  color: #1d4ed8;
  font-weight: 700;
}

.btn-add-chip-inline {
  border: 1px dashed #cbd5e1;
  background: #ffffff;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-add-chip-inline:hover {
  border-color: #3b82f6;
  color: #2563eb;
  background: #eff6ff;
}

.master-remark-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding-top: 6px;
  border-top: 1px dashed #e2e8f0;
}

.remark-tag {
  color: #64748b;
  font-weight: 600;
  white-space: nowrap;
}

.remark-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 12px;
  color: #334155;
  outline: none;
}

/* RevoGrid 表格区 */
.grid-section-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.grid-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.grid-title {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
}

.grid-badge-pill {
  background: #eff6ff;
  color: #1e40af;
  border: 1px solid #dbeafe;
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
}



.toolbar-right {
  display: flex;
  gap: 6px;
}

.btn-grid-action {
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  color: #334155;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-grid-action:hover:not(:disabled) {
  background: #e2e8f0;
  color: #0f172a;
}

.btn-danger-action:hover:not(:disabled) {
  background: #fee2e2;
  color: #991b1b;
  border-color: #fca5a5;
}

.btn-grid-action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 原生可编辑数据表格样式 */
.native-grid-container {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  overflow-x: auto;
  overflow-y: auto;
  max-height: 420px;
  background: #ffffff;
  box-sizing: border-box;
}

.native-bill-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  text-align: left;
}

.native-bill-table thead {
  position: sticky;
  top: 0;
  z-index: 10;
  background: #f8fafc;
  border-bottom: 2px solid #cbd5e1;
}

.native-bill-table th {
  padding: 8px 10px;
  font-weight: 700;
  color: #1e293b;
  border-right: 1px solid #e2e8f0;
  background: #f1f5f9;
  white-space: nowrap;
}

.native-bill-table th:last-child {
  border-right: none;
}

.native-bill-table tbody tr {
  border-bottom: 1px solid #e2e8f0;
  transition: background-color 0.1s ease;
}

.native-bill-table tbody tr:hover {
  background-color: #f8fafc;
}

.native-bill-table tbody tr.row-total {
  background-color: #f0fdf4;
  font-weight: 700;
}

.native-bill-table td {
  padding: 4px 6px;
  border-right: 1px solid #e2e8f0;
}

.native-bill-table td:last-child {
  border-right: none;
}

.cell-editor-input {
  width: 100%;
  border: 1px solid transparent;
  border-radius: 4px;
  padding: 4px 6px;
  font-size: 13px;
  color: #1e293b;
  background: transparent;
  outline: none;
  box-sizing: border-box;
  transition: all 0.15s ease;
}

.cell-editor-input:hover {
  border-color: #cbd5e1;
  background: #ffffff;
}

.cell-editor-input:focus {
  border-color: #3b82f6;
  background: #ffffff;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

.cell-editor-input.font-semibold {
  font-weight: 600;
}

.cell-seq .cell-editor-input {
  text-align: center;
  color: #64748b;
  font-weight: 600;
}

.btn-row-del {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 12px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 4px;
  transition: all 0.15s ease;
}

.btn-row-del:hover {
  color: #ef4444;
  background: #fee2e2;
}

.table-empty-placeholder {
  padding: 32px 16px;
  text-align: center;
  color: #64748b;
  font-size: 13px;
  background: #f8fafc;
}

.result-action-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid #eef2f6;
  flex-wrap: wrap;
  gap: 12px;
}

.footer-left,
.footer-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-export-highlight {
  font-size: 13px;
  padding: 8px 18px;
  font-weight: 600;
  border-radius: 6px;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
}

/* 全屏灯箱查看器 */
.image-lightbox-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(8px);
  z-index: 9999;
  display: flex;
  flex-direction: column;
  outline: none;
}

.lightbox-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: rgba(30, 41, 59, 0.85);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.lightbox-title-text {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 15px;
  font-weight: 600;
}

.lightbox-scale-indicator {
  font-size: 12px;
  background: rgba(255, 255, 255, 0.15);
  padding: 2px 8px;
  border-radius: 4px;
  color: #93c5fd;
}

.lightbox-btn-group {
  display: flex;
  gap: 8px;
}

.btn-lightbox {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #f8fafc;
  padding: 6px 12px;
  font-size: 13px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-lightbox:hover {
  background: rgba(255, 255, 255, 0.25);
}

.btn-lightbox.btn-close {
  background: #dc2626;
  border-color: #ef4444;
}

.btn-lightbox.btn-close:hover {
  background: #b91c1c;
}

.lightbox-canvas-viewport {
  flex: 1;
  width: 100%;
  height: 100%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: grab;
  position: relative;
}

.lightbox-canvas-viewport.is-dragging {
  cursor: grabbing;
}

.lightbox-doc-img {
  max-width: 90vw;
  max-height: 85vh;
  object-fit: contain;
  user-select: none;
  transform-origin: center center;
  transition: transform 0.05s ease-out;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
}

.lightbox-footer-tip {
  text-align: center;
  padding: 8px 0;
  font-size: 12px;
  color: #94a3b8;
  background: rgba(15, 23, 42, 0.8);
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

/* 导出轻提示 Toast 悬浮胶囊 */
.ocr-toast-notification {
  position: fixed;
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  background: #0f172a;
  color: #f8fafc;
  padding: 12px 24px;
  border-radius: 999px;
  border: 1px solid #334155;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.2);
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 600;
  pointer-events: none;
  animation: toastSlideDown 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.toast-icon {
  font-size: 16px;
}

.toast-msg {
  color: #38bdf8;
  font-weight: 700;
}

@keyframes toastSlideDown {
  from {
    opacity: 0;
    transform: translate(-50%, -12px);
  }
  to {
    opacity: 1;
    transform: translate(-50%, 0);
  }
}
</style>
