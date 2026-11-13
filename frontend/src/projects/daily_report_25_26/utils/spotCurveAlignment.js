// 两厂上网电量曲线与日前/实时电价曲线的波形相关性评价算法

function toFiniteNumber(raw) {
  if (raw === null || raw === undefined || raw === '') return null
  const num = Number(raw)
  return Number.isFinite(num) ? num : null
}

export function computePearsonCorrelation(xs, ys) {
  const n = xs.length
  if (n < 3 || ys.length !== n) return null
  let sumX = 0
  let sumY = 0
  for (let i = 0; i < n; i++) {
    sumX += xs[i]
    sumY += ys[i]
  }
  const meanX = sumX / n
  const meanY = sumY / n
  let sumXY = 0
  let sumX2 = 0
  let sumY2 = 0
  for (let i = 0; i < n; i++) {
    const dx = xs[i] - meanX
    const dy = ys[i] - meanY
    sumXY += dx * dy
    sumX2 += dx * dx
    sumY2 += dy * dy
  }
  if (sumX2 <= 1e-12 || sumY2 <= 1e-12) return null
  const r = sumXY / Math.sqrt(sumX2 * sumY2)
  return Math.max(-1, Math.min(1, r))
}

/**
 * 针对单个“电厂电量字段 × 电价字段”组合计算全局与多日日内去均值波形相关系数。
 */
export function evaluateCurveAlignment(rows, salesField, priceField) {
  const qs = []
  const ps = []
  const dayMap = new Map()

  for (const row of rows || []) {
    const q = toFiniteNumber(row?.[salesField])
    const p = toFiniteNumber(row?.[priceField])
    if (q === null || p === null) continue
    const dayKey = typeof row?.trade_date === 'string' && row.trade_date ? row.trade_date : '__single__'
    qs.push(q)
    ps.push(p)
    if (!dayMap.has(dayKey)) dayMap.set(dayKey, [])
    dayMap.get(dayKey).push({ q, p })
  }

  const validPoints = qs.length
  const dayCount = dayMap.size
  if (validPoints === 0) {
    return {
      validPoints: 0,
      dayCount: 0,
      correlation: null,
      intradayCorrelation: null,
    }
  }

  const correlation = computePearsonCorrelation(qs, ps)

  let intradayCorrelation = null
  if (dayCount > 1) {
    const qDev = []
    const pDev = []
    for (const dayItems of dayMap.values()) {
      if (dayItems.length < 2) continue
      let dSumQ = 0
      let dSumP = 0
      for (const item of dayItems) {
        dSumQ += item.q
        dSumP += item.p
      }
      const dMeanQ = dSumQ / dayItems.length
      const dMeanP = dSumP / dayItems.length
      for (const item of dayItems) {
        qDev.push(item.q - dMeanQ)
        pDev.push(item.p - dMeanP)
      }
    }
    intradayCorrelation = computePearsonCorrelation(qDev, pDev)
  }

  return {
    validPoints,
    dayCount,
    correlation,
    intradayCorrelation,
  }
}

/**
 * 汇总北海、香海两厂分别对“日前电价”与“实时电价”的波形相关系数。
 */
export function buildPlantAlignmentReport(rows) {
  const plants = [
    { key: 'beihai', name: '北海热电厂', field: 'beihai_total_sales' },
    { key: 'xianghai', name: '香海热电厂', field: 'xianghai_total_sales' },
  ]
  const byKey = {}
  let hasAnyMetrics = false

  for (const plant of plants) {
    const dayAhead = evaluateCurveAlignment(rows, plant.field, 'day_ahead_price')
    const realTime = evaluateCurveAlignment(rows, plant.field, 'real_time_price')
    if (dayAhead.validPoints > 0 || realTime.validPoints > 0) {
      hasAnyMetrics = true
    }
    byKey[plant.key] = { dayAhead, realTime }
  }

  return {
    hasAnyMetrics,
    byKey,
  }
}
