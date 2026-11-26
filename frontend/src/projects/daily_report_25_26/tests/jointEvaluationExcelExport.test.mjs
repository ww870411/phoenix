import assert from 'node:assert/strict'
import test from 'node:test'
import {
  buildJointEvaluationDetailSheet,
  buildJointEvaluationSummarySheet,
  buildJointEvaluationWorkbook,
} from '../utils/jointEvaluationExcelExport.js'

const samplePayload = {
  mode: 'single',
  default_biz_date: '2026-11-25',
  anchor_date: '2026-11-25',
  season_period: '26-27',
  valid_day_count: 2,
  excluded_count: 0,
  excluded_dates: [],
  area_source: { area_m2: 12000000, area_10k_m2: 1200 },
  summary: {
    label: '2026-11-25',
    valid_days: 1,
    avg_temp: 2.5,
    avg_hdd20_today: 17.5,
    avg_hdd20_prev3: 16.0,
    actual_unit_heat_avg: 18.2,
    ref_unit_heat_avg: 17.6,
    actual_heat_gj: 21840,
    ref_heat_gj: 21120,
    heat_delta_gj: 720,
    heat_deviation_pct: 3.41,
    actual_complaints: 45,
    ref_complaints: 50.0,
    complaint_delta: -5.0,
    complaint_index: 90.0,
    band_status: { status: 'within_band', label: '在 ±5% 经验带内' },
    quadrant: {
      code: 'IV',
      name: 'Ⅳ 高耗热·低投诉',
      diagnosis: '服务良好但偏粗放',
      action: '适度下调二网供温，挖掘节能空间。',
    },
  },
  trajectory_summary: {
    label: '轨迹区间合计',
    valid_days: 2,
    avg_temp: 3.0,
    avg_hdd20_today: 17.0,
    avg_hdd20_prev3: 15.8,
    actual_unit_heat_avg: 17.9,
    ref_unit_heat_avg: 17.4,
    actual_heat_gj: 42960,
    ref_heat_gj: 41760,
    heat_deviation_pct: 2.87,
    actual_complaints: 110,
    ref_complaints: 100.0,
    complaint_index: 110.0,
    quadrant: { code: 'I', name: 'Ⅰ 高耗热·高投诉' },
  },
  periods: [],
  daily_rows: [
    {
      date: '2026-11-24',
      avg_temp: 3.5,
      hdd20_today: 16.5,
      hdd20_prev3: 15.6,
      actual_unit_heat: 17.6,
      ref_unit_heat: 17.2,
      actual_heat_gj: 21120,
      ref_heat_gj: 20640,
      heat_deviation_pct: 2.33,
      actual_complaints: 65,
      ref_complaints: 50.0,
      complaint_index: 130.0,
      quadrant: { code: 'I', name: 'Ⅰ 高耗热·高投诉' },
      is_complete: true,
    },
    {
      date: '2026-11-25',
      avg_temp: 2.5,
      hdd20_today: 17.5,
      hdd20_prev3: 16.0,
      actual_unit_heat: 18.2,
      ref_unit_heat: 17.6,
      actual_heat_gj: 21840,
      ref_heat_gj: 21120,
      heat_deviation_pct: 3.41,
      actual_complaints: 45,
      ref_complaints: 50.0,
      complaint_index: 90.0,
      quadrant: { code: 'IV', name: 'Ⅳ 高耗热·低投诉' },
      is_complete: true,
    },
  ],
  model_spec: {
    equation: '参考日单耗 = 3.3730 + 0.5137 × 当日HDD20 + 0.3521 × 前3日平均HDD20 + 月份修正量',
    valid_window_rule: '每年 11月5日 — 次年3月31日',
    data_scope: { company_scope: 'ZhuChengQu' },
  },
}

test('buildJointEvaluationSummarySheet 生成商务样式汇总表及附带轨迹对照', () => {
  const ws = buildJointEvaluationSummarySheet(samplePayload, {
    mode: 'single',
    generatedAt: '2026-11-26 10:25:00',
  })

  assert.equal(ws.A1.v, '主城区供热联合评价模型（测试）诊断报表')
  assert.equal(ws.A1.s.fill.fgColor.rgb, 'EFF6FF')
  assert.equal(ws.A1.s.font.bold, true)
  assert.equal(ws.A4.v, '📊 核心诊断结论（单日：2026-11-25）')
  assert.equal(ws.A5.s.fill.fgColor.rgb, '1E293B')
  assert.equal(ws.A5.s.font.color.rgb, 'FFFFFF')
  // 轨迹累计对照板块存在
  assert.equal(ws.A12.v, '📈 附带轨迹累计对照（近 2 个有效日先累计后求比）')
  assert.ok(Array.isArray(ws['!merges']) && ws['!merges'].length >= 6)
})

test('buildJointEvaluationDetailSheet 与 Workbook 生成逐日明细、千分位数值、语义色与总计双底线', () => {
  const ws = buildJointEvaluationDetailSheet(samplePayload, {
    mode: 'single',
    generatedAt: '2026-11-26 10:25:00',
  })

  assert.equal(ws.A1.v, '主城区供热联合评价 · 逐日测算明细')
  assert.equal(ws.A4.v, '📅 逐日测算明细')
  assert.equal(ws.A5.s.fill.fgColor.rgb, '1E293B')
  // 第 6 行为 2026-11-24：正偏差红、投诉指数 130 红、Ⅰ象限红底
  assert.equal(ws.G6.v, 21120)
  assert.equal(ws.G6.z, '#,##0')
  assert.equal(ws.I6.s.font.color.rgb, 'DC2626')
  assert.equal(ws.L6.s.font.color.rgb, 'DC2626')
  assert.equal(ws.M6.s.fill.fgColor.rgb, 'FEE2E2')
  // 第 7 行为 2026-11-25：投诉指数 90 绿、Ⅳ象限蓝底
  assert.equal(ws.L7.s.font.color.rgb, '15803D')
  assert.equal(ws.M7.s.fill.fgColor.rgb, 'DBEAFE')
  // 第 8 行为区间合计总计行（双底线）
  assert.equal(ws.A8.v, '合计 / 区间(2天)')
  assert.equal(ws.A8.s.border.bottom.style, 'double')

  const wb = buildJointEvaluationWorkbook(samplePayload, { mode: 'single' })
  assert.deepEqual(wb.SheetNames, ['联合评价诊断汇总', '逐日联合评价明细'])
})
