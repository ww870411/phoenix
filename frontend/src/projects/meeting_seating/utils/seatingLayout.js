/**
 * 会议排座助手布局数据结构（按边/排管理座位数，支持 3 桌拼接显示、隐藏桌椅、花盆拖拽与初始化）
 */

export function cloneLayout(obj) {
  return JSON.parse(JSON.stringify(obj))
}

export function makeRow(id, label, zone, seatCount = 6) {
  const count = Math.max(0, Math.min(24, Math.floor(seatCount)))
  return {
    id,
    label,
    zone,
    tableCount: 3,
    hidden: false,
    seats: Array.from({ length: count }, (_, idx) => ({
      id: `${id}-${idx + 1}`,
      name: '',
      hidden: false,
    })),
  }
}

export function defaultPlants() {
  return [
    { id: 'P-1', x: 294, y: 392, label: '花盆 1', hidden: false },
    { id: 'P-2', x: 474, y: 392, label: '花盆 2', hidden: false },
    { id: 'P-3', x: 294, y: 584, label: '花盆 3', hidden: false },
    { id: 'P-4', x: 474, y: 584, label: '花盆 4', hidden: false },
  ]
}

/**
 * 构建贴合实景会议室的初始平面布局：
 * - 左上角为设备室，右上角为朝上方外开门
 * - 左、右两侧墙体均有窗
 * - 中央方形每边由 3 张桌子拼接而成，左右两竖边略长于上下两横边（桌角对齐）
 * - 每边默认 6 把椅子（3 桌 × 每桌 2 把紧凑布局），按边/排直接调节座位数
 * - 默认纸张为 A4 纵向（贴合会场平面长宽比）
 */
export function buildDefaultLayout() {
  return {
    version: 3,
    meeting: '会议座位安排图',
    subtitle: '',
    paper: 'portrait',
    mono: false,
    numbers: true,
    flip: false,
    showHiddenPreview: false,
    room: {
      door: { enabled: true, label: '出入口（外开）' },
      equipmentRoom: { enabled: true, label: '设备室' },
      leftWindows: 4,
      rightWindows: 4,
      screenLabel: '显示屏 / 会场正前方',
    },
    rows: [
      makeRow('A', '主席席', 'front', 6),
      makeRow('B', '窗侧内排', 'innerLeft', 6),
      makeRow('C', '右侧内排', 'innerRight', 6),
      makeRow('D', '回字桌后排', 'innerRear', 6),
      makeRow('E', '右侧外围排', 'right', 6),
      makeRow('F', '后方第1排', 'rear', 6),
      makeRow('G', '后方第2排', 'rear', 6),
      makeRow('H', '后方第3排', 'rear', 6),
    ],
    plants: defaultPlants(),
    seq: 10,
  }
}

/**
 * 兼容旧版 HTML rows 格式与 v2 tables 格式，统一规范为 v3 rows 格式
 */
export function normalizeOrMigrateLayout(raw) {
  if (!raw || typeof raw !== 'object') {
    throw new Error('配置文件格式错误')
  }
  const base = buildDefaultLayout()
  const validZones = new Set(['front', 'innerLeft', 'innerRight', 'innerRear', 'left', 'right', 'rear'])
  const fixedZones = ['front', 'innerLeft', 'innerRight', 'innerRear']

  let rowsIn = Array.isArray(raw.rows) ? raw.rows : null

  // 若导入的是 v2 tables 结构，按 groupId 聚合回 row
  if (!rowsIn && Array.isArray(raw.tables)) {
    const zoneById = new Map(base.rows.map((r) => [r.id, r.zone]))
    const grouped = new Map()
    raw.tables.forEach((t) => {
      const gid = String(t?.groupId || 'G').slice(0, 16)
      if (!grouped.has(gid)) {
        grouped.set(gid, {
          id: gid,
          label: String(t?.groupLabel || gid).slice(0, 32),
          zone: zoneById.get(gid) || 'rear',
          tableCount: 3,
          hidden: Boolean(t?.hidden),
          seats: [],
        })
      } else if (!t?.hidden) {
        grouped.get(gid).hidden = false
      }
      ;(t?.seats || []).forEach((s) => {
        grouped.get(gid).seats.push({
          id: String(s?.id || `${gid}-${grouped.get(gid).seats.length + 1}`),
          name: String(s?.name || '').slice(0, 40),
          hidden: Boolean(s?.hidden),
        })
      })
    })
    rowsIn = Array.from(grouped.values())
  }

  if (!Array.isArray(rowsIn)) {
    throw new Error('配置文件缺少有效座位排数据')
  }

  const seenIds = new Set()
  const cleanedRows = rowsIn.slice(0, 30).map((r, idx) => {
    let rid = String(r?.id || `R${idx + 1}`).slice(0, 16)
    if (seenIds.has(rid)) rid = `R${idx + 10}`
    seenIds.add(rid)
    const zone = validZones.has(r?.zone) ? r.zone : 'rear'
    const rawSeats = Array.isArray(r?.seats) ? r.seats : Array.isArray(r?.names) ? r.names : []
    const seats = rawSeats.slice(0, 24).map((s, sIdx) => {
      if (typeof s === 'string') {
        return { id: `${rid}-${sIdx + 1}`, name: s.slice(0, 40), hidden: false }
      }
      return {
        id: String(s?.id || `${rid}-${sIdx + 1}`).slice(0, 40),
        name: String(s?.name || '').slice(0, 40),
        hidden: Boolean(s?.hidden),
      }
    })
    return {
      id: rid,
      label: String(r?.label || rid).slice(0, 32),
      zone,
      tableCount: 3,
      hidden: Boolean(r?.hidden),
      seats,
    }
  })

  fixedZones.forEach((fz) => {
    if (!cleanedRows.some((r) => r.zone === fz)) {
      const def = base.rows.find((r) => r.zone === fz)
      if (def) cleanedRows.push(cloneLayout(def))
    }
  })

  return {
    version: 3,
    meeting: String(raw.meeting || base.meeting).slice(0, 100),
    subtitle: String(raw.subtitle || '').slice(0, 120),
    paper: raw.paper === 'portrait' ? 'portrait' : 'landscape',
    mono: Boolean(raw.mono),
    numbers: raw.numbers !== false,
    flip: Boolean(raw.flip),
    showHiddenPreview: Boolean(raw.showHiddenPreview),
    room: {
      ...base.room,
      ...(raw.room && typeof raw.room === 'object' ? raw.room : {}),
      door: {
        ...base.room.door,
        ...(raw.room?.door && typeof raw.room.door === 'object' ? raw.room.door : {}),
      },
      equipmentRoom: {
        ...base.room.equipmentRoom,
        ...(raw.room?.equipmentRoom && typeof raw.room.equipmentRoom === 'object'
          ? raw.room.equipmentRoom
          : {}),
      },
    },
    rows: cleanedRows,
    plants: Array.isArray(raw.plants)
      ? raw.plants.slice(0, 20).map((p, idx) => ({
          id: String(p?.id || `P-${idx + 1}`).slice(0, 32),
          x: Math.round(Number(p?.x || 0)),
          y: Math.round(Number(p?.y || 0)),
          label: String(p?.label || `花盆 ${idx + 1}`).slice(0, 24),
          hidden: Boolean(p?.hidden),
        }))
      : base.plants,
    seq: Number.isSafeInteger(raw.seq) && raw.seq >= 10 ? raw.seq : 10,
  }
}

/**
 * 统一计算当前所有座位索引、编号与重名统计
 */
export function buildSeatCatalog(rows, includeHidden = false) {
  const list = []
  const dupCounts = Object.create(null)

  ;(rows || []).forEach((row) => {
    const rowHidden = Boolean(row.hidden)
    let visibleNo = 0
    ;(row.seats || []).forEach((seat, seatIdx) => {
      const ownHidden = Boolean(seat.hidden)
      const effectiveHidden = rowHidden || ownHidden
      if (!effectiveHidden) visibleNo += 1
      if (!effectiveHidden || includeHidden) {
        const code = effectiveHidden
          ? `${row.id}-H${seatIdx + 1}`
          : `${row.id}-${String(visibleNo).padStart(2, '0')}`
        const trimmed = String(seat.name || '').trim()
        if (!effectiveHidden && trimmed) {
          dupCounts[trimmed] = (dupCounts[trimmed] || 0) + 1
        }
        list.push({
          rowId: row.id,
          seatIdx,
          seatId: seat.id,
          rowLabel: row.label,
          zone: row.zone,
          code,
          name: String(seat.name || ''),
          hidden: effectiveHidden,
          rowHidden,
          ownHidden,
        })
      }
    })
  })

  return { list, dupCounts }
}

/**
 * 计算按边/排布局的完整 SVG 几何结构：
 * - 中央方形每边由 3 张桌子拼接（tableSegments），左右竖边外沿略长于上下横边
 * - 每边座位数由该边 seats.length 直接决定，座椅自动等分紧凑排布
 */
export function computeRoomScene(layout, showHidden = false) {
  const rows = layout?.rows || []
  const byZone = (z) => rows.filter((r) => r.zone === z)
  const f = byZone('front')[0] || makeRow('A', '主席席', 'front', 6)
  const l = byZone('innerLeft')[0] || makeRow('B', '窗侧内排', 'innerLeft', 6)
  const r = byZone('innerRight')[0] || makeRow('C', '右侧内排', 'innerRight', 6)
  const b = byZone('innerRear')[0] || makeRow('D', '回字桌后排', 'innerRear', 6)
  const leftRows = byZone('left').filter((row) => !row.hidden || showHidden)
  const rightRows = byZone('right').filter((row) => !row.hidden || showHidden)
  const rearRows = byZone('rear').filter((row) => !row.hidden || showHidden)

  const tableDepth = 38
  const wallPad = 24
  const wallTop = 68

  const maxHorizSeats = Math.max(
    6,
    f.seats.length,
    b.seats.length,
    ...rearRows.map((row) => row.seats.length),
  )
  const maxVertSeats = Math.max(
    6,
    l.seats.length,
    r.seats.length,
    ...leftRows.concat(rightRows).map((row) => row.seats.length),
  )

  const ringW = maxHorizSeats <= 6 ? 444 : maxHorizSeats * 68 + 16
  // 保证左右竖边内跨度 >= 横边长度，使左右两竖边外沿（ringInnerH + 2*tableDepth）始终略长于上下横边
  const ringInnerH = Math.max(ringW, maxVertSeats <= 6 ? 444 : maxVertSeats * 58 + 16)
  const ringOuterH = ringInnerH + tableDepth * 2

  const sideBlockW = 122
  const rearStep = 114
  const rearStartOffset = 84
  const hasEqRoom = layout?.room?.equipmentRoom?.enabled !== false
  const leftMargin = hasEqRoom ? 142 : 114
  const tx = wallPad + leftMargin + leftRows.length * sideBlockW
  const ty = wallTop + 160
  const W = tx + ringW + 114 + rightRows.length * sideBlockW + wallPad
  const H = ty + ringOuterH + rearStartOffset + rearRows.length * rearStep + 44

  const tables = []
  const seats = []
  const tags = []
  const catalog = buildSeatCatalog(rows, showHidden)
  const codeMap = new Map()
  catalog.list.forEach((item) => {
    codeMap.set(`${item.rowId}::${item.seatIdx}`, item)
  })

  function pushSplicedTables(row, x, y, totalLen, orientation) {
    if (row.hidden && !showHidden) return
    const count = 3
    const segLen = totalLen / count
    for (let i = 0; i < count; i += 1) {
      tables.push({
        key: `${row.id}-t${i + 1}`,
        rowId: row.id,
        rowLabel: row.label,
        hidden: Boolean(row.hidden),
        orientation,
        x: orientation === 'h' ? x + i * segLen : x,
        y: orientation === 'v' ? y + i * segLen : y,
        w: orientation === 'h' ? segLen : tableDepth,
        h: orientation === 'v' ? segLen : tableDepth,
      })
    }
  }

  function pushHorizontalSeats(row, startX, spanW, seatY, face, tagY, tagOnTable = false) {
    const visiblePairs = []
    ;(row.seats || []).forEach((s, idx) => {
      const hidden = Boolean(row.hidden) || Boolean(s.hidden)
      if (!hidden || showHidden) visiblePairs.push({ seat: s, idx, hidden })
    })
    const n = visiblePairs.length
    if (n > 0) {
      const pitch = spanW / n
      const sw = Math.min(66, Math.max(30, Math.floor(pitch - 6)))
      const sh = 40
      visiblePairs.forEach((pair, pos) => {
        const meta = codeMap.get(`${row.id}::${pair.idx}`)
        seats.push({
          rowId: row.id,
          seatIdx: pair.idx,
          rowLabel: row.label,
          code: meta?.code || `${row.id}-${pair.idx + 1}`,
          name: String(pair.seat.name || ''),
          effectiveHidden: pair.hidden,
          isDuplicate: Boolean(
            !pair.hidden &&
              pair.seat.name.trim() &&
              catalog.dupCounts[pair.seat.name.trim()] > 1,
          ),
          x: startX + pos * pitch + (pitch - sw) / 2,
          y: seatY,
          w: sw,
          h: sh,
          face,
        })
      })
    }
    if (!row.hidden) {
      const activeCount = (row.seats || []).filter((s) => !s.hidden).length
      tags.push({
        key: `tag-${row.id}`,
        x: startX + spanW / 2,
        y: tagY,
        text: `${row.label} · ${activeCount}席`,
        onTable: tagOnTable,
      })
    }
  }

  function pushVerticalSeats(row, seatX, startY, spanH, face) {
    const visiblePairs = []
    ;(row.seats || []).forEach((s, idx) => {
      const hidden = Boolean(row.hidden) || Boolean(s.hidden)
      if (!hidden || showHidden) visiblePairs.push({ seat: s, idx, hidden })
    })
    const n = visiblePairs.length
    if (n > 0) {
      const pitch = spanH / n
      const sw = 66
      const sh = Math.min(44, Math.max(26, Math.floor(pitch - 5)))
      visiblePairs.forEach((pair, pos) => {
        const meta = codeMap.get(`${row.id}::${pair.idx}`)
        seats.push({
          rowId: row.id,
          seatIdx: pair.idx,
          rowLabel: row.label,
          code: meta?.code || `${row.id}-${pair.idx + 1}`,
          name: String(pair.seat.name || ''),
          effectiveHidden: pair.hidden,
          isDuplicate: Boolean(
            !pair.hidden &&
              pair.seat.name.trim() &&
              catalog.dupCounts[pair.seat.name.trim()] > 1,
          ),
          x: seatX,
          y: startY + pos * pitch + (pitch - sh) / 2,
          w: sw,
          h: sh,
          face,
        })
      })
    }
    if (!row.hidden) {
      const activeCount = (row.seats || []).filter((s) => !s.hidden).length
      tags.push({
        key: `tag-${row.id}`,
        x: seatX + 33,
        y: startY - 11,
        text: `${row.label} · ${activeCount}席`,
        onTable: false,
      })
    }
  }

  // 中央方形四边（每边 3 桌拼接；上下横边对齐外角，左右竖边夹于其间使外沿竖边更长）
  pushSplicedTables(f, tx, ty, ringW, 'h')
  pushHorizontalSeats(f, tx, ringW, ty - 45, 'down', ty + tableDepth / 2, true)

  pushSplicedTables(l, tx, ty + tableDepth, ringInnerH, 'v')
  pushVerticalSeats(l, tx - 71, ty + tableDepth, ringInnerH, 'right')

  pushSplicedTables(r, tx + ringW - tableDepth, ty + tableDepth, ringInnerH, 'v')
  pushVerticalSeats(r, tx + ringW + 5, ty + tableDepth, ringInnerH, 'left')

  pushSplicedTables(b, tx, ty + tableDepth + ringInnerH, ringW, 'h')
  pushHorizontalSeats(
    b,
    tx,
    ringW,
    ty + ringOuterH + 5,
    'up',
    ty + ringOuterH + 56,
    false,
  )

  // 左侧外围排
  leftRows.forEach((row, idx) => {
    const seatX = tx - 71 - (idx + 1) * sideBlockW
    const tblX = seatX + 71
    pushSplicedTables(row, tblX, ty + tableDepth, ringInnerH, 'v')
    pushVerticalSeats(row, seatX, ty + tableDepth, ringInnerH, 'right')
  })

  // 右侧外围排
  rightRows.forEach((row, idx) => {
    const tblX = tx + ringW + 76 + idx * sideBlockW
    const seatX = tblX + tableDepth + 5
    pushSplicedTables(row, tblX, ty + tableDepth, ringInnerH, 'v')
    pushVerticalSeats(row, seatX, ty + tableDepth, ringInnerH, 'left')
  })

  // 后方各排（预留充足行距，避免排名称标签与下一排桌子重合）
  rearRows.forEach((row, idx) => {
    const tblY = ty + ringOuterH + rearStartOffset + idx * rearStep
    pushSplicedTables(row, tx, tblY, ringW, 'h')
    pushHorizontalSeats(row, tx, ringW, tblY + tableDepth + 4, 'up', tblY + tableDepth + 55, false)
  })

  return {
    width: W,
    height: H,
    wallPad,
    wallTop,
    tx,
    ty,
    ringW,
    ringInnerH,
    ringOuterH,
    tableDepth,
    tables,
    seats,
    tags,
  }
}

/**
 * 仅初始化排座名单：清空全部座位姓名，保留当前各边/排座位数、花盆位置与隐藏状态
 */
export function resetSeatingNames(currentLayout) {
  const next = cloneLayout(currentLayout || buildDefaultLayout())
  ;(next.rows || []).forEach((row) => {
    ;(row.seats || []).forEach((seat) => {
      seat.name = ''
    })
  })
  return next
}

/**
 * 初始化会场布局为默认实景方案：
 * - preserveNames=true 时按排 ID 优先回填已录入姓名，其余姓名顺延补入空位
 * - preserveNames=false 时同时清空所有座位姓名
 */
export function resetRoomLayout(currentLayout, { preserveNames = true, clearMeta = false } = {}) {
  const fresh = buildDefaultLayout()
  if (currentLayout && !clearMeta) {
    fresh.meeting = currentLayout.meeting || fresh.meeting
    fresh.subtitle = currentLayout.subtitle || ''
    fresh.paper = currentLayout.paper === 'portrait' ? 'portrait' : 'landscape'
    fresh.mono = Boolean(currentLayout.mono)
    fresh.numbers = currentLayout.numbers !== false
  }

  if (!preserveNames || !currentLayout?.rows?.length) {
    return fresh
  }

  const namesByRowId = new Map()
  ;(currentLayout.rows || []).forEach((row) => {
    const queue = []
    ;(row.seats || []).forEach((seat) => {
      const name = String(seat?.name || '').trim()
      if (name) queue.push(name)
    })
    namesByRowId.set(row.id, queue)
  })

  const leftover = []
  fresh.rows.forEach((row) => {
    const queue = namesByRowId.get(row.id)
    if (!queue) return
    row.seats.forEach((seat) => {
      if (!seat.name && queue.length) {
        seat.name = queue.shift()
      }
    })
    while (queue.length) leftover.push(queue.shift())
    namesByRowId.delete(row.id)
  })

  namesByRowId.forEach((queue) => {
    while (queue.length) leftover.push(queue.shift())
  })

  if (leftover.length) {
    fresh.rows.forEach((row) => {
      row.seats.forEach((seat) => {
        if (!seat.name && leftover.length) {
          seat.name = leftover.shift()
        }
      })
    })
  }

  return fresh
}
