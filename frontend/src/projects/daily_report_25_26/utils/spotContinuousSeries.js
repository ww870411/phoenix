/**
 * 电力现货区间“连续显示”原始时序构造工具。
 *
 * 从区间内首个有效点位至最后一个有效点位按标准 15 分钟步长（每日 1..96 点）展开，
 * 不做聚合、平滑或降采样；若中间某天或某些时段存在数据缺失，则插入占位空点以便在图表中断开连线。
 */

const DAY_MS = 24 * 60 * 60 * 1000
const MAX_EXPANDED_POINTS = 180000

/**
 * 将 YYYY-MM-DD 日期字符串解析为 UTC 零点毫秒时间戳。
 * @param {string} dateStr
 * @returns {number|null}
 */
function parseUtcDateMs(dateStr) {
  if (typeof dateStr !== 'string') return null
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateStr.trim())
  if (!match) return null
  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  const ms = Date.UTC(year, month - 1, day)
  const check = new Date(ms)
  if (
    check.getUTCFullYear() !== year
    || check.getUTCMonth() !== month - 1
    || check.getUTCDate() !== day
  ) {
    return null
  }
  return ms
}

/**
 * 将 UTC 毫秒时间戳格式化为 YYYY-MM-DD。
 * @param {number} ms
 * @returns {string}
 */
function formatUtcDate(ms) {
  const d = new Date(ms)
  const y = d.getUTCFullYear()
  const m = String(d.getUTCMonth() + 1).padStart(2, '0')
  const day = String(d.getUTCDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/**
 * 根据 15 分钟时点序号（1..96）生成标准官方时刻与起止区间。
 * @param {number} pointIndex
 * @returns {{ time_label: string, period_start_time: string, period_end_time: string }}
 */
export function formatPointPeriod(pointIndex) {
  const endMinutes = pointIndex * 15
  const startMinutes = endMinutes - 15
  const formatHm = (mins) => {
    const h = String(Math.floor(mins / 60)).padStart(2, '0')
    const m = String(mins % 60).padStart(2, '0')
    return `${h}:${m}`
  }
  const timeLabel = formatHm(endMinutes)
  return {
    time_label: timeLabel,
    period_start_time: `${formatHm(startMinutes)}:00`,
    period_end_time: `${timeLabel}:00`,
  }
}

/**
 * 构造连续 15 分钟时序数组；中间缺数据时插入 `__missing: true` 空值点位。
 * @param {Array<Object>} points 已按 trade_date ASC, point_index ASC 排序的原始点位
 * @returns {Array<Object>}
 */
export function buildContinuousTimeline(points) {
  if (!Array.isArray(points) || points.length === 0) return []

  const first = points[0]
  const last = points[points.length - 1]
  const firstDayMs = parseUtcDateMs(first?.trade_date)
  const lastDayMs = parseUtcDateMs(last?.trade_date)
  const firstIdx = Number(first?.point_index)
  const lastIdx = Number(last?.point_index)

  if (
    firstDayMs === null
    || lastDayMs === null
    || !Number.isInteger(firstIdx)
    || !Number.isInteger(lastIdx)
    || firstIdx < 1
    || firstIdx > 96
    || lastIdx < 1
    || lastIdx > 96
  ) {
    return points.map(item => ({
      ...item,
      __missing: false,
      axisLabel: `${item.trade_date || ''} ${item.time_label || ''}`.trim(),
    }))
  }

  const totalDays = Math.round((lastDayMs - firstDayMs) / DAY_MS)
  const expectedTotal = totalDays * 96 + (lastIdx - firstIdx) + 1

  // 超大异常跨度防护：仅在相邻点不连续时插入单个断点标记，避免内存爆炸
  if (expectedTotal <= 0 || expectedTotal > MAX_EXPANDED_POINTS) {
    const fallback = []
    let prevSlot = null
    for (const item of points) {
      const dMs = parseUtcDateMs(item.trade_date)
      const pIdx = Number(item.point_index)
      const slot = dMs !== null && Number.isInteger(pIdx) ? Math.round(dMs / DAY_MS) * 96 + (pIdx - 1) : null
      if (prevSlot !== null && slot !== null && slot - prevSlot > 1) {
        const missingSlot = prevSlot + 1
        const mDate = formatUtcDate(Math.floor(missingSlot / 96) * DAY_MS)
        const mIdx = (missingSlot % 96) + 1
        const period = formatPointPeriod(mIdx)
        fallback.push({
          trade_date: mDate,
          point_index: mIdx,
          ...period,
          day_ahead_price: null,
          real_time_price: null,
          bill_real_time_price: null,
          price_spread: null,
          beihai_total_sales: null,
          xianghai_total_sales: null,
          __missing: true,
          axisLabel: `${mDate} ${period.time_label}`,
        })
      }
      fallback.push({
        ...item,
        __missing: false,
        axisLabel: `${item.trade_date} ${item.time_label}`,
      })
      prevSlot = slot
    }
    return fallback
  }

  const lookup = new Map()
  for (const item of points) {
    const key = `${item.trade_date}#${item.point_index}`
    lookup.set(key, item)
  }

  const timeline = new Array(expectedTotal)
  const firstSlot = Math.round(firstDayMs / DAY_MS) * 96 + (firstIdx - 1)

  for (let offset = 0; offset < expectedTotal; offset++) {
    const slot = firstSlot + offset
    const dayIndex = Math.floor(slot / 96)
    const pIdx = (slot % 96) + 1
    const dateStr = formatUtcDate(dayIndex * DAY_MS)
    const existing = lookup.get(`${dateStr}#${pIdx}`)
    if (existing) {
      timeline[offset] = {
        ...existing,
        __missing: false,
        axisLabel: `${existing.trade_date} ${existing.time_label}`,
      }
    } else {
      const period = formatPointPeriod(pIdx)
      timeline[offset] = {
        trade_date: dateStr,
        point_index: pIdx,
        ...period,
        day_ahead_price: null,
        real_time_price: null,
        bill_real_time_price: null,
        price_spread: null,
        beihai_total_sales: null,
        xianghai_total_sales: null,
        __missing: true,
        axisLabel: `${dateStr} ${period.time_label}`,
      }
    }
  }

  return timeline
}
