<template>
  <div v-if="show" class="modal-overlay">
    <div class="modal-card elevated" style="max-width: 580px; width: 90%; background: #ffffff; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.25);">
      <!-- 弹窗 Header -->
      <div class="modal-header" style="padding: 20px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
        <h3 style="margin: 0; font-size: 18px; font-weight: 700; color: #1e293b; display: flex; align-items: center; gap: 8px;">
          <span>📥 导出 Excel 设置</span>
        </h3>
        <button type="button" class="close-btn" @click="handleClose" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #64748b;">×</button>
      </div>

      <!-- 弹窗 Body -->
      <div class="modal-body" style="padding: 20px; max-height: 65vh; overflow-y: auto; display: flex; flex-direction: column; gap: 20px;">
        <!-- 1. 导出文件名设置 -->
        <div class="form-group" style="display: flex; flex-direction: column; gap: 6px;">
          <span style="font-size: 13px; font-weight: 600; color: #475569;">📂 自定义导出文件名 (可修改)</span>
          <div style="display: flex; align-items: center; gap: 4px; border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px 10px; background: #ffffff;">
            <input 
              v-model.trim="exportFilename" 
              type="text" 
              placeholder="请输入文件名" 
              style="flex: 1; border: none; outline: none; font-size: 14px; padding: 6px 0; color: #1e293b;" 
            />
            <span style="color: #64748b; font-size: 13px; font-weight: 600; background: #f1f5f9; padding: 4px 8px; border-radius: 4px;">.xlsx</span>
          </div>
        </div>

        <!-- 2. 导出数据范围选择 -->
        <div class="form-group" style="display: flex; flex-direction: column; gap: 8px;">
          <span style="font-size: 13px; font-weight: 600; color: #475569;">📊 选择导出数据范围</span>
          <div style="display: flex; gap: 24px; background: #f8fafc; padding: 12px 16px; border-radius: 8px; border: 1px solid #e2e8f0;">
            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 14px; color: #334155; font-weight: 500;">
              <input type="radio" value="filtered" v-model="exportRange" style="cursor: pointer; accent-color: #4f46e5;" />
              <span>仅导出当前筛选后的数据 ({{ filteredData.length }} 条)</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 14px; color: #334155; font-weight: 500;">
              <input type="radio" value="all" v-model="exportRange" style="cursor: pointer; accent-color: #4f46e5;" />
              <span>导出全部原始数据 ({{ data.length }} 条)</span>
            </label>
          </div>
        </div>

        <!-- 3. 自定义要导出的列字段 -->
        <div class="form-group" style="display: flex; flex-direction: column; gap: 10px;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 13px; font-weight: 600; color: #475569;">📋 自定义选择导出的列 (字段过滤)</span>
            <div style="display: flex; gap: 12px;">
              <button type="button" @click="selectAllCols(true)" style="background: none; border: none; font-size: 12px; color: #4f46e5; font-weight: 600; cursor: pointer; padding: 0;">一键全选</button>
              <span style="color: #cbd5e1; font-size: 12px;">|</span>
              <button type="button" @click="selectAllCols(false)" style="background: none; border: none; font-size: 12px; color: #64748b; font-weight: 600; cursor: pointer; padding: 0;">一键清除</button>
            </div>
          </div>
          
          <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 16px; max-height: 180px; overflow-y: auto;">
            <label 
              v-for="col in availableColumns" 
              :key="col.key" 
              style="display: flex; align-items: center; gap: 8px; font-size: 13.5px; color: #334155; cursor: pointer; padding: 4px 0; font-weight: 500;"
            >
              <input 
                type="checkbox" 
                :value="col.key" 
                v-model="selectedColumnKeys" 
                style="cursor: pointer; accent-color: #4f46e5; width: 15px; height: 15px;" 
              />
              <span>{{ col.label }}</span>
            </label>
          </div>
          <p style="margin: 0; font-size: 12px; color: #64748b;">
            💡 提示：您可以根据具体报表诉求自由勾选导出列，未被勾选的列将不会呈现在生成的 Excel 文件中。
          </p>
        </div>

        <!-- 4. 🔀 车次单元格合并选项 (仅在提供 mergeColumns 时呈现) -->
        <div v-if="mergeColumns && mergeColumns.length" class="form-group" style="display: flex; flex-direction: column; gap: 8px;">
          <span style="font-size: 13px; font-weight: 600; color: #475569;">🔀 聚合排版设置</span>
          <div style="background: #f8fafc; padding: 10px 14px; border-radius: 8px; border: 1px solid #e2e8f0; display: flex; align-items: center; justify-content: space-between; gap: 10px;">
            <div style="display: flex; flex-direction: column; gap: 2px;">
              <span style="font-size: 13.5px; font-weight: 600; color: #1e293b;">合并同车次前置公共列单元格</span>
              <span style="font-size: 12px; color: #64748b;">勾选后，同一车次内的车次号、车牌、供需主体等前置公共信息将在 Excel 中自动跨行合并居中展示</span>
            </div>
            <input type="checkbox" v-model="enableGroupMerge" style="width: 18px; height: 18px; cursor: pointer; accent-color: #4f46e5; flex-shrink: 0;" />
          </div>
        </div>
      </div>

      <!-- 弹窗 Footer -->
      <div class="modal-footer" style="padding: 16px 20px; border-top: 1px solid #e2e8f0; display: flex; justify-content: flex-end; gap: 12px; background: #f8fafc; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;">
        <button type="button" class="btn ghost" @click="handleClose" style="padding: 10px 20px; border: 1px solid #cbd5e1; background: #ffffff; color: #475569; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer;">取消</button>
        <button 
          type="button" 
          class="btn primary" 
          :disabled="isExporting || selectedColumnKeys.length === 0" 
          @click="executeExcelExport" 
          style="padding: 10px 20px; border: none; background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%); color: #ffffff; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2); display: flex; align-items: center; gap: 6px;"
        >
          <span>{{ isExporting ? '⏳ 正在生成报表...' : '💾 确认导出 Excel' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import * as XLSX from 'xlsx-js-style'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  columns: {
    type: Array,
    required: true
  },
  data: {
    type: Array,
    required: true
  },
  filteredData: {
    type: Array,
    required: true
  },
  defaultFilename: {
    type: String,
    default: '报表导出'
  },
  isGroupedExport: {
    type: Boolean,
    default: false
  },
  groupKeyField: {
    type: String,
    default: ''
  },
  mergeColumns: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['close'])

const exportFilename = ref('')
const exportRange = ref('filtered') // 'filtered' or 'all'
const availableColumns = ref([])
const selectedColumnKeys = ref([])
const isExporting = ref(false)
const enableGroupMerge = ref(false)

// 获取当前日期字符串 YYYYMMDD
function getTodayDateString() {
  const d = new Date()
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const date = String(d.getDate()).padStart(2, '0')
  return `${year}${month}${date}`
}

// 监听弹窗显示，初始化默认数据
watch(() => props.show, (newVal) => {
  if (newVal) {
    exportFilename.value = `${props.defaultFilename}_${getTodayDateString()}`
    exportRange.value = props.filteredData.length > 0 ? 'filtered' : 'all'
    enableGroupMerge.value = Boolean(props.isGroupedExport)
    
    // 过滤出有有效 label 的列定义
    availableColumns.value = props.columns.filter(col => col.key && col.label && col.label !== '操作' && col.label !== '序号' && col.label !== '')
    // 默认全选
    selectedColumnKeys.value = availableColumns.value.map(col => col.key)
  }
})

function handleClose() {
  emit('close')
}

function selectAllCols(selectAll) {
  if (selectAll) {
    selectedColumnKeys.value = availableColumns.value.map(col => col.key)
  } else {
    selectedColumnKeys.value = []
  }
}

// 执行高规格 XLSX 导出，支持单元格纵向合并、高级样式美化与自适应列宽
async function executeExcelExport() {
  if (selectedColumnKeys.value.length === 0) return
  isExporting.value = true
  
  try {
    // 1. 确定导出范围的数据源
    let rawRows = exportRange.value === 'filtered' ? [...props.filteredData] : [...props.data]
    if (rawRows.length === 0) {
      alert('当前选定的导出数据范围没有可导出的行数据！')
      isExporting.value = false
      return
    }

    // 2. 映射当前勾选的列和表头
    const activeCols = availableColumns.value.filter(col => selectedColumnKeys.value.includes(col.key))
    
    // 3. 若启用了按车次合并单元格，先对数据按照分组键进行稳定排序归集
    const groupKeyField = props.groupKeyField || 'shipment_no'
    if (enableGroupMerge.value && groupKeyField) {
      rawRows.sort((a, b) => {
        const keyA = String(a[groupKeyField] || a.shipment_no || a.order_no || a.id || '')
        const keyB = String(b[groupKeyField] || b.shipment_no || b.order_no || b.id || '')
        return keyA.localeCompare(keyB, 'zh-CN')
      })
    }

    // 4. 构建待导出的 JSON 记录（按中文表头 Key 进行重塑）
    const exportRows = rawRows.map(row => {
      const entry = {}
      activeCols.forEach(col => {
        let val = row[col.key]
        if (col.key === 'statusLabel' && row.statusLabel) {
          val = row.statusLabel
        } else if (col.key === 'shippedAtDisplay' && row.shippedAtDisplay) {
          val = row.shippedAtDisplay
        } else if (val === null || val === undefined) {
          val = ''
        }
        entry[col.label] = val
      })
      return entry
    })

    // 5. 调用 xlsx-js-style 库创建 Worksheet
    const ws = XLSX.utils.json_to_sheet(exportRows)

    // 🌟 6. 高级合并单元格计算 (Merge Cells) 🌟
    const merges = []
    const groups = []
    let currentGroup = null

    // 计算每个连续车次组的起止索引
    rawRows.forEach((row, idx) => {
      const gKey = String(row[groupKeyField] || row.shipment_no || row.order_no || row.id || `row_${idx}`)
      if (!currentGroup || currentGroup.key !== gKey) {
        currentGroup = { key: gKey, startIndex: idx, count: 1, groupIndex: groups.length }
        groups.push(currentGroup)
      } else {
        currentGroup.count += 1
      }
    })

    if (enableGroupMerge.value && props.mergeColumns && props.mergeColumns.length) {
      const mergeColSet = new Set(props.mergeColumns)
      for (const grp of groups) {
        if (grp.count > 1) {
          const rStart = 1 + grp.startIndex
          const rEnd = 1 + grp.startIndex + grp.count - 1

          activeCols.forEach((col, colIdx) => {
            if (mergeColSet.has(col.key)) {
              merges.push({
                s: { r: rStart, c: colIdx },
                e: { r: rEnd, c: colIdx }
              })
            }
          })
        }
      }

      if (merges.length > 0) {
        ws['!merges'] = merges
      }
    }

    // 🌟 7. 专业排版与单元格美化样式 (Cell Styling) 🌟
    const thinBorder = {
      top: { style: 'thin', color: { rgb: 'CBD5E1' } },
      bottom: { style: 'thin', color: { rgb: 'CBD5E1' } },
      left: { style: 'thin', color: { rgb: 'CBD5E1' } },
      right: { style: 'thin', color: { rgb: 'CBD5E1' } }
    }

    const headerStyle = {
      font: { name: 'Microsoft YaHei', sz: 10.5, bold: true, color: { rgb: 'FFFFFF' } },
      fill: { fgColor: { rgb: '334155' } }, // 商务深蓝灰色 #334155
      alignment: { horizontal: 'center', vertical: 'center', wrapText: true },
      border: {
        top: { style: 'thin', color: { rgb: '1E293B' } },
        bottom: { style: 'medium', color: { rgb: '0F172A' } },
        left: { style: 'thin', color: { rgb: '475569' } },
        right: { style: 'thin', color: { rgb: '475569' } }
      }
    }

    // 构建每行数据对应的车次组索引，以便渲染交替斑马底色
    const rowGroupIndexMap = new Map()
    groups.forEach(grp => {
      for (let i = 0; i < grp.count; i++) {
        rowGroupIndexMap.set(grp.startIndex + i, grp.groupIndex)
      }
    })

    const mergeColSet = new Set(props.mergeColumns || [])
    const totalDataRows = exportRows.length
    const totalCols = activeCols.length

    // 设置行高：表头 30pt，数据行 24pt
    const rowHeights = [{ hpt: 30 }]

    // 格式化所有单元格
    for (let r = 0; r <= totalDataRows; r++) {
      if (r > 0) {
        rowHeights.push({ hpt: 24 })
      }

      for (let c = 0; c < totalCols; c++) {
        const cellAddress = XLSX.utils.encode_cell({ r, c })
        if (!ws[cellAddress]) {
          ws[cellAddress] = { v: '', t: 's' }
        }

        if (r === 0) {
          // 表头样式
          ws[cellAddress].s = headerStyle
        } else {
          // 数据行
          const dataRowIndex = r - 1
          const colDef = activeCols[c]
          const isMergeCol = mergeColSet.has(colDef.key)
          const grpIdx = rowGroupIndexMap.get(dataRowIndex) || 0
          
          // 车次交替微底色：偶数组纯白，奇数组极淡蓝灰
          const isOddGroup = grpIdx % 2 === 1
          const bgRgb = isOddGroup ? 'F8FAFC' : 'FFFFFF'

          // 判断对齐方式
          let hAlign = 'left'
          let fontColor = '1E293B'
          let isBold = false

          if (isMergeCol) {
            hAlign = 'center'
            if (colDef.key === 'shipment_no') {
              fontColor = '3730A3' // 沉稳靛蓝
              isBold = true
            } else if (colDef.key === 'vehicle_plate_no') {
              fontColor = '0F766E' // 青翠深绿
              isBold = true
            }
          } else if (
            colDef.key.includes('qty') || 
            colDef.key.includes('amount') || 
            colDef.label.includes('量') || 
            colDef.label.includes('米') || 
            colDef.label.includes('件')
          ) {
            hAlign = 'right'
            isBold = true
            fontColor = '0F172A'
          } else if (
            colDef.key.includes('status') || 
            colDef.key.includes('code') || 
            colDef.key.includes('no') || 
            colDef.key.includes('time') || 
            colDef.key.includes('At') || 
            colDef.key.includes('elapsed')
          ) {
            hAlign = 'center'
          }

          ws[cellAddress].s = {
            font: { 
              name: 'Microsoft YaHei', 
              sz: 9.5, 
              color: { rgb: fontColor },
              bold: isBold
            },
            fill: { fgColor: { rgb: bgRgb } },
            alignment: { 
              horizontal: hAlign, 
              vertical: 'center', 
              wrapText: true 
            },
            border: thinBorder
          }
        }
      }
    }

    ws['!rows'] = rowHeights

    // 🌟 8. 高级自适应列宽计算，确保 Excel 表格极其整齐美观 🌟
    const colWidths = activeCols.map(col => {
      const headerLen = col.label ? col.label.replace(/[^\x00-\xff]/g, '00').length : 10
      const maxValLen = exportRows.reduce((max, row) => {
        const val = row[col.label] ?? ''
        const len = String(val).replace(/[^\x00-\xff]/g, '00').length
        return Math.max(max, len)
      }, 0)
      return { wch: Math.max(headerLen, maxValLen) + 4 }
    })
    ws['!cols'] = colWidths

    // 9. 生成 Workbook 并写入下载
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, '数据台账')
    
    const finalFilename = exportFilename.value.endsWith('.xlsx') 
      ? exportFilename.value 
      : `${exportFilename.value}.xlsx`
      
    XLSX.writeFile(wb, finalFilename)
    
    // 10. 成功后关闭弹窗
    handleClose()
  } catch (error) {
    console.error('Excel export error:', error)
    alert(`导出 Excel 失败: ${error?.message || '未知错误'}`)
  } finally {
    isExporting.value = false
  }
}
</script>

<style scoped>
/* 极致高鲁棒性且屏幕绝对水平垂直居中样式 */
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
