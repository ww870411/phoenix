import test from 'node:test'
import assert from 'node:assert/strict'
import {
  buildDefaultLayout,
  buildSeatCatalog,
  computeRoomScene,
  normalizeOrMigrateLayout,
  resetRoomLayout,
  resetSeatingNames,
} from '../utils/seatingLayout.js'

test('默认按边设置座位数：每边3桌拼接且左右竖边略长于上下横边、双侧窗户、左上设备室与右上外开门', () => {
  const layout = buildDefaultLayout()
  assert.equal(layout.paper, 'portrait')
  assert.equal(layout.rows.length, 8)
  assert.ok(layout.rows.every((r) => r.tableCount === 3 && r.seats.length === 6))
  assert.equal(layout.room.door.enabled, true)
  assert.equal(layout.room.equipmentRoom.enabled, true)
  assert.equal(layout.room.equipmentRoom.label, '设备室')
  assert.equal(layout.room.leftWindows, 4)
  assert.equal(layout.room.rightWindows, 4)
  assert.equal(layout.plants.length, 4)

  const scene = computeRoomScene(layout)
  // 每条边由 3 张拼接桌构成，8 排共 24 个桌段
  assert.equal(scene.tables.length, 24)
  assert.equal(scene.seats.length, 48)
  // 中央方形左右竖边外沿 (520) 略长于上下横边 (444)
  assert.equal(scene.ringW, 444)
  assert.equal(scene.ringOuterH, 520)
  assert.ok(scene.ringOuterH > scene.ringW)

  // 校验所有横排（非桌面内嵌标签）不与任何桌体或座椅垂直重叠
  const nonTableTags = scene.tags.filter((t) => !t.onTable && t.key.startsWith('tag-'))
  nonTableTags.forEach((tag) => {
    const hitTable = scene.tables.some(
      (tbl) =>
        tag.x >= tbl.x &&
        tag.x <= tbl.x + tbl.w &&
        tag.y >= tbl.y - 6 &&
        tag.y <= tbl.y + tbl.h + 6,
    )
    const hitSeat = scene.seats.some(
      (s) =>
        tag.x >= s.x &&
        tag.x <= s.x + s.w &&
        tag.y >= s.y - 6 &&
        tag.y <= s.y + s.h + 6,
    )
    assert.equal(hitTable, false, `${tag.key} 不应与桌子重叠`)
    assert.equal(hitSeat, false, `${tag.key} 不应与座椅重叠`)
  })
})

test('支持隐藏整排或单座后重新顺编可见座位且座椅不重叠', () => {
  const layout = buildDefaultLayout()
  layout.rows[0].seats[0].hidden = true
  layout.rows[7].hidden = true

  const visible = buildSeatCatalog(layout.rows, false)
  const withHidden = buildSeatCatalog(layout.rows, true)
  assert.equal(visible.list.length, 48 - 1 - 6)
  assert.equal(withHidden.list.length, 48)
  assert.equal(visible.list[0].code, 'A-01')

  // 单边紧凑调整为 9 座时水平坐标单调递增不重叠
  for (let i = 0; i < 3; i += 1) {
    layout.rows[0].seats.push({ id: `A-extra-${i}`, name: '', hidden: false })
  }
  const scene = computeRoomScene(layout)
  const frontSeats = scene.seats.filter((s) => s.rowId === 'A')
  assert.equal(frontSeats.length, 8)
  for (let i = 0; i < frontSeats.length - 1; i += 1) {
    assert.ok(frontSeats[i].x + frontSeats[i].w < frontSeats[i + 1].x)
  }
})

test('支持初始化排座、初始化布局（保留/清空姓名）及旧版 JSON 迁移', () => {
  const layout = buildDefaultLayout()
  layout.meeting = '集团调度会'
  layout.rows[0].seats[0].name = '张主任'
  layout.rows[3].seats[1].name = '李部长'
  layout.rows[7].hidden = true
  layout.plants[0].x = 120

  // 1. 仅初始化排座：清空名字但保留排隐藏、座位数与花盆位置
  const cleared = resetSeatingNames(layout)
  assert.equal(cleared.rows[7].hidden, true)
  assert.equal(cleared.plants[0].x, 120)
  assert.equal(cleared.rows[0].seats[0].name, '')

  // 2. 初始化布局（保留姓名）
  const resetKeep = resetRoomLayout(layout, { preserveNames: true })
  assert.equal(resetKeep.meeting, '集团调度会')
  assert.equal(resetKeep.rows[7].hidden, false)
  assert.equal(resetKeep.plants[0].x, 294)
  assert.equal(resetKeep.plants[0].y, 392)
  assert.equal(resetKeep.rows[0].seats[0].name, '张主任')
  assert.equal(resetKeep.rows[3].seats[0].name, '李部长')

  // 3. 兼容迁移旧版 HTML rows 格式
  const migrated = normalizeOrMigrateLayout({
    meeting: '旧方案测试',
    rows: [
      { id: 'A', label: '前排', zone: 'front', names: ['甲', '乙', '丙', '丁'] },
      { id: 'B', label: '左排', zone: 'innerLeft', names: ['戊'] },
      { id: 'C', label: '右排', zone: 'innerRight', names: [] },
      { id: 'D', label: '后排', zone: 'innerRear', names: [] },
    ],
  })
  assert.equal(migrated.meeting, '旧方案测试')
  assert.equal(migrated.rows[0].seats.length, 4)
  assert.equal(migrated.rows[0].seats[0].name, '甲')
})
