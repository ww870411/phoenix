// 前端目录运行：node --test src/projects/daily_report_25_26/tests/analysisExcelExport.test.mjs
import assert from 'node:assert/strict'
import test from 'node:test'
import XLSX from 'xlsx-js-style'
import {
  buildAnalysisExcelWorkbook,
  buildStyledUnitWorksheet,
  resolveSheetName,
  sanitizeSheetName,
} from '../utils/analysisExcelExport.js'

test('sanitizeSheetName 与 resolveSheetName 正确处理非法字符、截断与重名', () => {
  assert.equal(sanitizeSheetName('北海/热电*厂[1]'), '北海_热电_厂_1_')
  assert.equal(sanitizeSheetName('超长单位名称'.repeat(10)).length, 31)

  const used = new Set()
  assert.equal(resolveSheetName('北海热电厂', used), '北海热电厂')
  assert.equal(resolveSheetName('北海热电厂', used), '北海热电厂_2')
  assert.equal(resolveSheetName('北海热电厂', used), '北海热电厂_3')
})

test('buildStyledUnitWorksheet 为单日/累计数据生成完整合并标题、深色表头、千分位数值与语义色', () => {
  const result = {
    meta: {
      unit_label: '北海热电厂',
      analysis_mode: 'range',
      analysis_mode_label: '累计数据',
      start_date: '2026-11-01',
      end_date: '2026-11-02',
    },
    rows: [
      {
        key: 'amount_power_generation',
        label: '发电量',
        unit: '万kWh',
        decimals: 2,
        total_current: 1234.567,
        total_peer: 1000.0,
      },
      {
        key: 'rate_heat_per_10k_m2',
        label: '供暖热单耗',
        unit: 'GJ/万㎡',
        decimals: 4,
        total_current: 9.5,
        total_peer: 10.0,
      },
    ],
    ringCompare: {
      range: { start: '2026-10-30', end: '2026-10-31' },
      prevTotals: {
        amount_power_generation: 1100.0,
        rate_heat_per_10k_m2: 10.0,
      },
    },
    planComparison: { month_label: '2026年11月' },
    timeline: {
      columns: [
        { prop: 'date', name: '日期' },
        { prop: 'amount_power_generation__current', name: '发电量(本期)' },
        { prop: 'amount_power_generation__peer', name: '发电量(同期)' },
        { prop: 'amount_power_generation__delta', name: '发电量(同比%)' },
      ],
      rows: [
        {
          date: '2026-11-01',
          amount_power_generation__current: 600.12,
          amount_power_generation__peer: 500,
          amount_power_generation__delta: { text: '20.02%', delta: 20.02 },
        },
        {
          date: '总计',
          amount_power_generation__current: 1234.57,
          amount_power_generation__peer: 1000,
          amount_power_generation__delta: { text: '23.46%', delta: 23.46 },
        },
      ],
    },
  }

  const ws = buildStyledUnitWorksheet(result, {
    analysisMode: 'range',
    pageDisplayName: '数据查询与分析',
    generatedAt: '2026-11-23 18:15:00',
    resolveTotalCurrent: (r) => r.total_current,
    resolvePlanEntries: () => [
      { label: '发电量', actualValue: 1234.567, planValue: 1200, completionRate: 102.88, unit: '万kWh', decimals: 2 },
    ],
    formatPlanStatus: () => '超出计划',
  })

  // 1. 合并区域、列宽、行高必须齐全
  assert.ok(Array.isArray(ws['!merges']) && ws['!merges'].length >= 6)
  assert.ok(Array.isArray(ws['!cols']) && ws['!cols'].length >= 6)
  assert.ok(Array.isArray(ws['!rows']) && ws['!rows'][0].hpx === 34)

  // 2. 顶部大标题与摘要样式校验
  assert.equal(ws.A1.v, '北海热电厂 · 数据查询与分析报表')
  assert.equal(ws.A1.s.font.bold, true)
  assert.equal(ws.A1.s.fill.fgColor.rgb, 'EFF6FF')
  assert.equal(ws.A2.s.fill.fgColor.rgb, 'F8FAFC')

  // 3. 核心指标汇总表头与数据样式（第4行板块条，第5行深色表头，第6/7行数据）
  assert.equal(ws.A4.v, '📊 核心指标对比汇总')
  assert.equal(ws.A4.s.fill.fgColor.rgb, 'DBEAFE')
  assert.equal(ws.A5.v, '指标')
  assert.equal(ws.A5.s.fill.fgColor.rgb, '1E293B')
  assert.equal(ws.A5.s.font.color.rgb, 'FFFFFF')

  // 第6行：发电量，保留小数且设置千分位 numFmt，同比正值红色
  assert.equal(ws.B6.v, 1234.57)
  assert.equal(ws.B6.z, '#,##0.00')
  assert.equal(ws.B6.s.alignment.horizontal, 'right')
  assert.equal(ws.D6.s.font.color.rgb, 'DC2626')

  // 第7行：4位小数指标与负同比绿色
  assert.equal(ws.B7.v, 9.5)
  assert.equal(ws.B7.z, '#,##0.0000')
  assert.equal(ws.D7.s.font.color.rgb, '15803D')

  // 4. 校验写入为真实 xlsx 二进制缓冲后可无损重读
  const wb = buildAnalysisExcelWorkbook(['BeiHai'], { BeiHai: result }, {
    analysisMode: 'range',
    pageDisplayName: '数据查询与分析',
  })
  const buf = XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' })
  assert.ok(buf.byteLength > 2000)
  const parsed = XLSX.read(buf, { type: 'buffer' })
  assert.deepEqual(parsed.SheetNames, ['北海热电厂'])
})
