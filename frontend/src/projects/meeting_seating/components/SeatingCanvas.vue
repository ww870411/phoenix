<template>
  <div class="canvas-shell" :class="{ mono: layout.mono }">
    <svg
      ref="svgRef"
      class="seating-svg"
      :viewBox="`0 0 ${scene.width} ${scene.height}`"
      role="img"
      aria-label="交互式会议会场平面图"
      xmlns="http://www.w3.org/2000/svg"
      preserveAspectRatio="xMidYMid meet"
      @pointermove="onSvgPointerMove"
      @pointerup="onSvgPointerUp"
      @pointercancel="onSvgPointerCancel"
    >
      <!-- 房间外框与地板 -->
      <rect
        :x="scene.wallPad"
        :y="scene.wallTop"
        :width="innerRoomW"
        :height="innerRoomH"
        fill="#faf9f5"
        stroke="#b5a18a"
        stroke-width="3"
        rx="8"
      />

      <!-- 顶部木质墙体（为右上外开门留出开口） -->
      <template v-if="doorGeometry">
        <rect
          :x="mxRect(scene.wallPad + 4, doorGeometry.leftWallLen)"
          :y="scene.wallTop + 4"
          :width="Math.max(0, doorGeometry.leftWallLen)"
          height="13"
          fill="#94765c"
          class="wood"
        />
        <rect
          :x="mxRect(doorGeometry.rightWallStart, doorGeometry.rightWallLen)"
          :y="scene.wallTop + 4"
          :width="Math.max(0, doorGeometry.rightWallLen)"
          height="13"
          fill="#94765c"
          class="wood"
        />
      </template>
      <rect
        v-else
        :x="scene.wallPad + 4"
        :y="scene.wallTop + 4"
        :width="innerRoomW - 8"
        height="13"
        fill="#94765c"
        class="wood"
      />

      <!-- 左、右、下墙体 -->
      <rect
        :x="scene.wallPad + 4"
        :y="scene.wallTop + 17"
        width="12"
        :height="innerRoomH - 34"
        fill="#94765c"
        class="wood"
      />
      <rect
        :x="scene.wallPad + innerRoomW - 16"
        :y="scene.wallTop + 17"
        width="12"
        :height="innerRoomH - 34"
        fill="#94765c"
        class="wood"
      />
      <rect
        :x="scene.wallPad + 4"
        :y="scene.wallTop + innerRoomH - 17"
        :width="innerRoomW - 8"
        height="13"
        fill="#94765c"
        class="wood"
      />

      <!-- 右上位置：朝上方外开门 -->
      <g v-if="doorGeometry" class="door-group">
        <rect
          :x="mxRect(doorGeometry.doorX, doorGeometry.doorW)"
          :y="scene.wallTop + 2"
          :width="doorGeometry.doorW"
          height="15"
          fill="#f8f5ef"
          stroke="#b5a18a"
          stroke-width="1"
        />
        <path
          :d="doorGeometry.arcPath"
          fill="rgba(212, 232, 237, 0.22)"
          stroke="#7f6b55"
          stroke-width="1.3"
          stroke-dasharray="4 3"
        />
        <rect
          :x="doorGeometry.leafRectX"
          :y="scene.wallTop - doorGeometry.leafLen"
          width="5"
          :height="doorGeometry.leafLen"
          fill="#c49a6c"
          stroke="#6f5032"
          stroke-width="1.2"
          rx="1"
          class="wood"
        />
        <text
          :x="mxPoint(doorGeometry.doorX + doorGeometry.doorW / 2 - 4)"
          :y="scene.wallTop - doorGeometry.leafLen / 2 + 4"
          text-anchor="middle"
          font-size="11"
          font-weight="600"
          fill="#6e5a44"
        >
          {{ layout.room?.door?.label || '出入口（外开）' }}
        </text>
      </g>

      <!-- 左侧墙体窗户 -->
      <g v-for="(win, idx) in leftWindowPanes" :key="`lw-${idx}`">
        <rect
          :x="mxRect(scene.wallPad + 5, 11)"
          :y="win.y"
          width="11"
          :height="win.h"
          fill="#d4e8ed"
          stroke="#7fa3ae"
          stroke-width="1"
          rx="1"
          class="windowpane"
        />
        <line
          :x1="mxPoint(scene.wallPad + 5)"
          :y1="win.y + win.h / 2"
          :x2="mxPoint(scene.wallPad + 16)"
          :y2="win.y + win.h / 2"
          stroke="#7fa3ae"
          stroke-width="1"
        />
      </g>
      <text
        v-if="leftWindowPanes.length > 0"
        :x="mxPoint(scene.wallPad + 36)"
        :y="leftWindowTagY"
        text-anchor="middle"
        font-size="12"
        fill="#667f88"
      >
        窗侧
      </text>

      <!-- 左上角：设备室（贴合实景独立隔间、玻璃观察窗与控制机柜） -->
      <g v-if="equipmentRoomGeo" class="equipment-room-group">
        <!-- 设备室地板 -->
        <rect
          :x="mxRect(equipmentRoomGeo.x, equipmentRoomGeo.w)"
          :y="equipmentRoomGeo.y"
          :width="equipmentRoomGeo.w"
          :height="equipmentRoomGeo.h"
          fill="#ece8de"
          stroke="none"
          class="eq-floor"
        />
        <!-- 音控/网络机柜示意 -->
        <rect
          :x="mxRect(equipmentRoomGeo.x + 10, 32)"
          :y="equipmentRoomGeo.y + 10"
          width="32"
          height="20"
          rx="2"
          fill="#4a5b54"
          stroke="#2c3a34"
          stroke-width="1"
          class="eq-rack"
        />
        <line
          :x1="mxPoint(equipmentRoomGeo.x + 14)"
          :y1="equipmentRoomGeo.y + 17"
          :x2="mxPoint(equipmentRoomGeo.x + 38)"
          :y2="equipmentRoomGeo.y + 17"
          stroke="#9ab8ab"
          stroke-width="1"
        />
        <line
          :x1="mxPoint(equipmentRoomGeo.x + 14)"
          :y1="equipmentRoomGeo.y + 23"
          :x2="mxPoint(equipmentRoomGeo.x + 38)"
          :y2="equipmentRoomGeo.y + 23"
          stroke="#9ab8ab"
          stroke-width="1"
        />
        <!-- 设备室右侧木质隔墙（含设备室门洞） -->
        <rect
          :x="mxRect(equipmentRoomGeo.x + equipmentRoomGeo.w - 6, 6)"
          :y="equipmentRoomGeo.y"
          width="6"
          :height="equipmentRoomGeo.h - 38"
          fill="#94765c"
          class="wood"
        />
        <rect
          :x="mxRect(equipmentRoomGeo.x + equipmentRoomGeo.w - 6, 6)"
          :y="equipmentRoomGeo.y + equipmentRoomGeo.h - 10"
          width="6"
          height="10"
          fill="#94765c"
          class="wood"
        />
        <!-- 设备室小门开启弧线 -->
        <path
          :d="equipmentRoomGeo.doorArcPath"
          fill="rgba(212, 232, 237, 0.22)"
          stroke="#7f6b55"
          stroke-width="1.1"
          stroke-dasharray="3 2"
        />
        <line
          :x1="equipmentRoomGeo.doorLeafX1"
          :y1="equipmentRoomGeo.doorLeafY"
          :x2="equipmentRoomGeo.doorLeafX2"
          :y2="equipmentRoomGeo.doorLeafY"
          stroke="#6f5032"
          stroke-width="2.5"
        />
        <!-- 设备室下侧木质隔墙与玻璃观察窗 -->
        <rect
          :x="mxRect(equipmentRoomGeo.x, equipmentRoomGeo.w)"
          :y="equipmentRoomGeo.y + equipmentRoomGeo.h - 6"
          :width="equipmentRoomGeo.w"
          height="6"
          fill="#94765c"
          class="wood"
        />
        <rect
          :x="mxRect(equipmentRoomGeo.x + 16, equipmentRoomGeo.w - 34)"
          :y="equipmentRoomGeo.y + equipmentRoomGeo.h - 6"
          :width="Math.max(20, equipmentRoomGeo.w - 34)"
          height="6"
          fill="#d4e8ed"
          stroke="#7fa3ae"
          stroke-width="1"
          class="windowpane"
        />
        <text
          :x="mxPoint(equipmentRoomGeo.x + equipmentRoomGeo.w / 2 - 2)"
          :y="equipmentRoomGeo.y + equipmentRoomGeo.h / 2 + 10"
          text-anchor="middle"
          dominant-baseline="middle"
          font-size="12"
          font-weight="700"
          fill="#4b3b2c"
        >
          {{ layout.room?.equipmentRoom?.label || '设备室' }}
        </text>
      </g>

      <!-- 右侧墙体窗户（与最左侧墙体一样配备窗） -->
      <g v-for="(win, idx) in rightWindowPanes" :key="`rw-${idx}`">
        <rect
          :x="mxRect(scene.wallPad + innerRoomW - 16, 11)"
          :y="win.y"
          width="11"
          :height="win.h"
          fill="#d4e8ed"
          stroke="#7fa3ae"
          stroke-width="1"
          rx="1"
          class="windowpane"
        />
        <line
          :x1="mxPoint(scene.wallPad + innerRoomW - 16)"
          :y1="win.y + win.h / 2"
          :x2="mxPoint(scene.wallPad + innerRoomW - 5)"
          :y2="win.y + win.h / 2"
          stroke="#7fa3ae"
          stroke-width="1"
        />
      </g>
      <text
        v-if="rightWindowPanes.length > 0"
        :x="mxPoint(scene.wallPad + innerRoomW - 36)"
        :y="scene.wallTop + 42"
        text-anchor="middle"
        font-size="12"
        fill="#667f88"
      >
        窗侧
      </text>

      <!-- 顶部正前方显示屏 -->
      <g>
        <rect
          :x="mxRect(screenRect.x, screenRect.w)"
          :y="screenRect.y"
          :width="screenRect.w"
          :height="screenRect.h"
          fill="#263332"
          stroke="#9a7958"
          stroke-width="3.5"
          rx="3"
        />
        <text
          :x="mxPoint(screenRect.x + screenRect.w / 2)"
          :y="screenRect.y + screenRect.h / 2 + 1"
          text-anchor="middle"
          dominant-baseline="middle"
          font-size="14"
          font-weight="600"
          fill="#ffffff"
        >
          {{ layout.room?.screenLabel || '显示屏 / 会场正前方' }}
        </text>
      </g>

      <!-- 中央与外围拼接桌渲染（每边由 3 张桌子拼接，显示拼接缝线） -->
      <g class="tables-layer">
        <g
          v-for="tbl in scene.tables"
          :key="tbl.key"
          :class="['table-unit', { 'is-hidden-ghost': tbl.hidden }]"
        >
          <rect
            :x="mxRect(tbl.x + 0.8, tbl.w - 1.6)"
            :y="tbl.y + 0.8"
            :width="Math.max(8, tbl.w - 1.6)"
            :height="Math.max(8, tbl.h - 1.6)"
            rx="2"
            class="tableShape"
          />
          <rect
            :x="mxRect(tbl.x + 3.6, tbl.w - 7.2)"
            :y="tbl.y + 3.6"
            :width="Math.max(4, tbl.w - 7.2)"
            :height="Math.max(4, tbl.h - 7.2)"
            rx="1"
            class="tableEdge"
          />
          <line
            v-if="tbl.orientation === 'h'"
            :x1="mxPoint(tbl.x)"
            :y1="tbl.y + 2"
            :x2="mxPoint(tbl.x)"
            :y2="tbl.y + tbl.h - 2"
            class="tableSeam"
          />
          <line
            v-else
            :x1="mxPoint(tbl.x + 2)"
            :y1="tbl.y"
            :x2="mxPoint(tbl.x + tbl.w - 2)"
            :y2="tbl.y"
            class="tableSeam"
          />
          <title>{{ tbl.rowLabel }}（3 桌拼接）</title>
        </g>
      </g>

      <!-- 中央绿植花盆（可直接拖动调整位置） -->
      <g class="plants-layer">
        <g
          v-for="plant in renderedPlants"
          :key="plant.id"
          :class="['plant-unit', { 'is-hidden-ghost': plant.hidden }]"
          @pointerdown="onPlantPointerDown($event, plant)"
        >
          <circle
            :cx="mxPoint(plant.x)"
            :cy="plant.y"
            r="16"
            fill="#e6e6d9"
            stroke="#b8c2af"
            stroke-width="1.2"
          />
          <ellipse
            v-for="j in 8"
            :key="`leaf-${plant.id}-${j}`"
            :cx="mxPoint(plant.x)"
            :cy="plant.y - 9"
            rx="4"
            ry="11"
            fill="#557b4c"
            class="plant-leaf"
            :transform="`rotate(${(j - 1) * 45} ${mxPoint(plant.x)} ${plant.y})`"
          />
          <circle :cx="mxPoint(plant.x) - 4" :cy="plant.y - 5" r="3.8" fill="#aa4545" class="plant-flower" />
          <circle :cx="mxPoint(plant.x) + 5" :cy="plant.y + 3" r="3.8" fill="#aa4545" class="plant-flower" />
          <circle :cx="mxPoint(plant.x) + 1" :cy="plant.y + 9" r="3.8" fill="#aa4545" class="plant-flower" />
          <title>{{ plant.label }}（拖动可调整花盆位置）</title>
        </g>
      </g>

      <!-- 排名称与席位统计标签 -->
      <g class="tags-layer">
        <text
          v-for="tag in scene.tags"
          :key="tag.key"
          :x="mxPoint(tag.x)"
          :y="tag.y"
          text-anchor="middle"
          dominant-baseline="middle"
          :class="tag.onTable ? 'fronttag' : 'rowtag'"
        >
          {{ tag.text }}
        </text>
      </g>

      <!-- 座位渲染 -->
      <g class="seats-layer">
        <g
          v-for="seat in renderedSeats"
          :key="`${seat.rowId}-${seat.seatIdx}`"
          :data-row-id="seat.rowId"
          :data-seat-idx="seat.seatIdx"
          tabindex="0"
          role="button"
          :aria-label="`${seat.rowLabel} ${seat.code} ${seat.name || '空座'}`"
          :class="[
            'seat',
            {
              assigned: Boolean(seat.name.trim()) && !seat.effectiveHidden,
              duplicate: !seat.effectiveHidden && seat.isDuplicate,
              selected: isSeatSelected(seat),
              'drag-target': isDragTarget(seat),
              'is-hidden-ghost': seat.effectiveHidden,
            },
          ]"
          @pointerdown="onSeatPointerDown($event, seat)"
          @click.stop="onSeatClick(seat)"
          @keydown.enter.prevent="onSeatClick(seat)"
          @keydown.space.prevent="onSeatClick(seat)"
        >
          <rect
            :x="mxRect(seat.x, seat.w)"
            :y="seat.y"
            :width="seat.w"
            :height="seat.h"
            rx="5"
            class="seatbox"
          />
          <rect
            v-if="seat.backRect"
            :x="mxRect(seat.backRect.x, seat.backRect.w)"
            :y="seat.backRect.y"
            :width="seat.backRect.w"
            :height="seat.backRect.h"
            rx="2"
            class="back"
          />
          <text
            :x="mxPoint(seat.x + seat.w / 2)"
            :y="seat.y + (layout.numbers ? Math.round(seat.h * 0.4) : Math.round(seat.h * 0.52))"
            text-anchor="middle"
            dominant-baseline="middle"
            class="seatname"
            :font-size="seat.nameFontSize"
            :fill="seat.name.trim() ? '#182b23' : '#87978d'"
            :opacity="seat.name.trim() ? 1 : 0.7"
          >
            {{ seat.displayName }}
          </text>
          <text
            v-if="layout.numbers"
            :x="mxPoint(seat.x + seat.w / 2)"
            :y="seat.y + Math.round(seat.h * 0.77)"
            text-anchor="middle"
            dominant-baseline="middle"
            class="seatno"
          >
            {{ seat.effectiveHidden ? '隐藏' : seat.code }}
          </text>
          <title>{{ seat.rowLabel }} {{ seat.code }} {{ seat.name || '空座' }}</title>
        </g>
      </g>
    </svg>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { computeRoomScene } from '../utils/seatingLayout'

const props = defineProps({
  layout: { type: Object, required: true },
  selectedSeat: { type: Object, default: null }, // { rowId, seatIdx }
  isPrinting: { type: Boolean, default: false },
})

const emit = defineEmits([
  'select-seat',
  'swap-seats',
  'move-plant',
  'commit-plant-move',
])

const svgRef = ref(null)
const dragState = ref(null)
const dragHoverSeat = ref(null)

const showHidden = computed(() => Boolean(props.layout?.showHiddenPreview) && !props.isPrinting)
const mirror = computed(() => Boolean(props.layout?.flip))

const scene = computed(() => computeRoomScene(props.layout, showHidden.value))
const innerRoomW = computed(() => scene.value.width - scene.value.wallPad * 2)
const innerRoomH = computed(() => scene.value.height - scene.value.wallTop - 20)

function mxPoint(x) {
  return mirror.value ? scene.value.width - x : x
}

function mxRect(x, w) {
  return mirror.value ? scene.value.width - x - w : x
}

const screenRect = computed(() => {
  const w = Math.min(scene.value.ringW * 0.9, 440)
  const x = scene.value.tx + (scene.value.ringW - w) / 2
  return { x, y: scene.value.wallTop + 16, w, h: 25 }
})

const doorGeometry = computed(() => {
  if (!props.layout?.room?.door?.enabled) return null
  const doorW = 68
  const leafLen = 58
  const doorX = scene.value.wallPad + innerRoomW.value - 134
  const hingeXRaw = doorX + doorW
  const openStartXRaw = doorX + doorW - leafLen
  const hingeX = mxPoint(hingeXRaw)
  const openStartX = mxPoint(openStartXRaw)
  const wy = scene.value.wallTop + 4
  const sweepFlag = mirror.value ? 0 : 1
  const arcPath = `M ${openStartX} ${wy} A ${leafLen} ${leafLen} 0 0 ${sweepFlag} ${hingeX} ${wy - leafLen}`
  const leafRectX = mirror.value ? hingeX : hingeX - 5

  return {
    doorX,
    doorW,
    leafLen,
    leftWallLen: doorX - (scene.value.wallPad + 4),
    rightWallStart: doorX + doorW,
    rightWallLen: scene.value.wallPad + innerRoomW.value - 4 - (doorX + doorW),
    arcPath,
    leafRectX,
  }
})

const equipmentRoomGeo = computed(() => {
  if (props.layout?.room?.equipmentRoom?.enabled === false) return null
  const x = scene.value.wallPad + 16
  const y = scene.value.wallTop + 17
  const w = 104
  const h = 104
  const doorLen = 26
  const hingeY = y + h - 10
  const wallEdgeX = x + w - 3
  const hingeX = mxPoint(wallEdgeX)
  const openTipX = mxPoint(wallEdgeX + doorLen)
  const topPointY = hingeY - doorLen
  const sweepFlag = mirror.value ? 1 : 0
  const doorArcPath = `M ${hingeX} ${topPointY} A ${doorLen} ${doorLen} 0 0 ${sweepFlag} ${openTipX} ${hingeY}`
  return {
    x,
    y,
    w,
    h,
    doorArcPath,
    doorLeafX1: hingeX,
    doorLeafX2: openTipX,
    doorLeafY: hingeY,
  }
})

function buildWindowList(count, customTop = null) {
  const n = Math.max(0, Math.min(8, Number(count || 0)))
  if (!n) return []
  const top = customTop ?? scene.value.wallTop + 58
  const bottom = Math.min(
    scene.value.wallTop + innerRoomH.value - 80,
    scene.value.ty + scene.value.ringOuterH + 20,
  )
  const step = Math.max(40, (bottom - top) / n)
  const h = Math.max(28, step - 14)
  return Array.from({ length: n }, (_, idx) => ({
    y: top + idx * step,
    h,
  }))
}

const leftWindowTop = computed(() =>
  equipmentRoomGeo.value ? equipmentRoomGeo.value.y + equipmentRoomGeo.value.h + 18 : scene.value.wallTop + 58,
)
const leftWindowTagY = computed(() =>
  equipmentRoomGeo.value ? leftWindowTop.value - 5 : scene.value.wallTop + 42,
)
const leftWindowPanes = computed(() => buildWindowList(props.layout?.room?.leftWindows ?? 4, leftWindowTop.value))
const rightWindowPanes = computed(() => buildWindowList(props.layout?.room?.rightWindows ?? 4))

const renderedPlants = computed(() => {
  return (props.layout?.plants || []).filter((p) => !p.hidden || showHidden.value)
})

const renderedSeats = computed(() => {
  return scene.value.seats.map((s) => {
    const chars = Array.from(s.name)
    const maxChars = s.w < 46 ? 4 : s.w < 58 ? 6 : 8
    const displayName = chars.length > maxChars ? `${chars.slice(0, maxChars - 1).join('')}…` : s.name || '空位'
    let nameFontSize = 14
    if (!s.name.trim()) {
      nameFontSize = s.w < 46 ? 9 : 11
    } else if (s.w < 46) {
      nameFontSize = chars.length > 2 ? 9.5 : 11
    } else if (chars.length > 5) {
      nameFontSize = 10.5
    } else if (chars.length > 3) {
      nameFontSize = 12
    }

    const actualFace = mirror.value
      ? s.face === 'left'
        ? 'right'
        : s.face === 'right'
          ? 'left'
          : s.face
      : s.face

    let backRect = null
    if (actualFace === 'down') backRect = { x: s.x + 6, y: s.y + 1, w: Math.max(8, s.w - 12), h: 4 }
    else if (actualFace === 'up') backRect = { x: s.x + 6, y: s.y + s.h - 5, w: Math.max(8, s.w - 12), h: 4 }
    else if (actualFace === 'right') backRect = { x: s.x + 1, y: s.y + 6, w: 4, h: Math.max(8, s.h - 12) }
    else if (actualFace === 'left') backRect = { x: s.x + s.w - 5, y: s.y + 6, w: 4, h: Math.max(8, s.h - 12) }

    return {
      ...s,
      displayName,
      nameFontSize,
      backRect,
    }
  })
})

function isSeatSelected(seat) {
  return (
    props.selectedSeat &&
    props.selectedSeat.rowId === seat.rowId &&
    props.selectedSeat.seatIdx === seat.seatIdx
  )
}

function isDragTarget(seat) {
  return (
    dragHoverSeat.value &&
    dragHoverSeat.value.rowId === seat.rowId &&
    dragHoverSeat.value.seatIdx === seat.seatIdx
  )
}

function clientToSvgPoint(clientX, clientY) {
  const svg = svgRef.value
  if (!svg) return { x: 0, y: 0 }
  const ctm = svg.getScreenCTM()
  if (!ctm) return { x: 0, y: 0 }
  const pt = svg.createSVGPoint()
  pt.x = clientX
  pt.y = clientY
  const transformed = pt.matrixTransform(ctm.inverse())
  return {
    x: mirror.value ? scene.value.width - transformed.x : transformed.x,
    y: transformed.y,
  }
}

function onSeatPointerDown(e, seat) {
  if (e.button !== 0 || seat.effectiveHidden || e.pointerType === 'touch') return
  dragState.value = {
    kind: 'seat',
    rowId: seat.rowId,
    seatIdx: seat.seatIdx,
    startX: e.clientX,
    startY: e.clientY,
    moved: false,
  }
}

function onPlantPointerDown(e, plant) {
  if (e.button !== 0) return
  e.stopPropagation()
  const svgPt = clientToSvgPoint(e.clientX, e.clientY)
  dragState.value = {
    kind: 'plant',
    plantId: plant.id,
    startClientX: e.clientX,
    startClientY: e.clientY,
    startSvgX: svgPt.x,
    startSvgY: svgPt.y,
    originX: plant.x,
    originY: plant.y,
    moved: false,
  }
  try {
    svgRef.value?.setPointerCapture?.(e.pointerId)
  } catch {
    // ignore
  }
}

function onSvgPointerMove(e) {
  const ds = dragState.value
  if (!ds) return
  if (ds.kind === 'seat') {
    if (Math.hypot(e.clientX - ds.startX, e.clientY - ds.startY) > 8) {
      ds.moved = true
    }
    if (ds.moved) {
      const target = document.elementFromPoint(e.clientX, e.clientY)?.closest?.('.seat')
      if (target) {
        dragHoverSeat.value = {
          rowId: target.getAttribute('data-row-id'),
          seatIdx: Number(target.getAttribute('data-seat-idx')),
        }
      } else {
        dragHoverSeat.value = null
      }
    }
    return
  }

  if (Math.hypot(e.clientX - ds.startClientX, e.clientY - ds.startClientY) > 3) {
    ds.moved = true
  }
  if (!ds.moved) return
  const cur = clientToSvgPoint(e.clientX, e.clientY)
  const dx = cur.x - ds.startSvgX
  const dy = cur.y - ds.startSvgY
  const nextX = Math.max(40, Math.min(scene.value.width - 40, Math.round((ds.originX + dx) / 5) * 5))
  const nextY = Math.max(scene.value.wallTop + 30, Math.min(scene.value.height - 30, Math.round((ds.originY + dy) / 5) * 5))
  emit('move-plant', { id: ds.plantId, x: nextX, y: nextY })
}

function onSvgPointerUp(e) {
  const ds = dragState.value
  dragState.value = null
  dragHoverSeat.value = null
  if (!ds) return

  try {
    if (svgRef.value?.hasPointerCapture?.(e.pointerId)) {
      svgRef.value.releasePointerCapture(e.pointerId)
    }
  } catch {
    // ignore
  }

  if (ds.kind === 'seat' && ds.moved) {
    const target = document.elementFromPoint(e.clientX, e.clientY)?.closest?.('.seat')
    if (target) {
      const targetSeat = {
        rowId: target.getAttribute('data-row-id'),
        seatIdx: Number(target.getAttribute('data-seat-idx')),
      }
      if (targetSeat.rowId && Number.isFinite(targetSeat.seatIdx)) {
        emit('swap-seats', { rowId: ds.rowId, seatIdx: ds.seatIdx }, targetSeat)
      }
    }
  } else if (ds.kind === 'plant' && ds.moved) {
    emit('commit-plant-move')
  }
}

function onSvgPointerCancel() {
  dragState.value = null
  dragHoverSeat.value = null
}

function onSeatClick(seat) {
  if (dragState.value && dragState.value.moved) return
  emit('select-seat', { rowId: seat.rowId, seatIdx: seat.seatIdx })
}
</script>

<style scoped>
.canvas-shell {
  width: 100%;
}

.seating-svg {
  display: block;
  width: 100%;
  height: auto;
  overflow: visible;
  user-select: none;
}

.seating-svg text {
  font-family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
  user-select: none;
}

.tableShape {
  fill: #3d7660;
  stroke: #204b3a;
  stroke-width: 1.5;
}

.tableEdge {
  stroke: #79a492;
  stroke-width: 1;
  fill: none;
}

.tableSeam {
  stroke: #1b3f30;
  stroke-width: 1.4;
}

.plant-unit {
  cursor: move;
  touch-action: none;
}

.seat {
  cursor: pointer;
  outline: none;
}

.seat .seatbox {
  stroke: #8a9b91;
  stroke-width: 1.2;
  fill: #f5f8f5;
}

.seat.assigned .seatbox {
  fill: #e1eee5;
  stroke: #42765e;
}

.seat.duplicate .seatbox {
  stroke: #b65b35;
  stroke-width: 2;
}

.seat.selected .seatbox,
.seat:focus .seatbox {
  stroke: #ca8b23;
  stroke-width: 2.8;
}

.seat.drag-target .seatbox {
  stroke: #2563eb;
  stroke-width: 2.8;
  fill: #dbeafe;
}

.seat:hover .seatbox {
  stroke: #ca8b23;
  stroke-width: 2;
}

.seat .back {
  fill: #43574f;
}

.seat.assigned .back {
  fill: #22644f;
}

.seatname {
  font-weight: 700;
}

.seatno {
  fill: #62776c;
  font-size: 8.5px;
}

.fronttag {
  font-size: 11.5px;
  font-weight: 600;
  fill: #f5faf7;
  pointer-events: none;
}

.rowtag {
  fill: #53695e;
  font-size: 11.5px;
  font-weight: 600;
  pointer-events: none;
}

.is-hidden-ghost {
  opacity: 0.35;
}

.is-hidden-ghost .tableShape,
.is-hidden-ghost .seatbox {
  stroke-dasharray: 4 3;
}

.mono .fronttag {
  fill: #222;
}

.mono .tableShape {
  fill: #dedede;
  stroke: #555;
}

.mono .tableEdge {
  stroke: #aaa;
}

.mono .tableSeam {
  stroke: #444;
}

.mono .seat.assigned .seatbox {
  fill: #eee;
  stroke: #222;
}

.mono .seat .back {
  fill: #555;
}

.mono .seat.duplicate .seatbox {
  stroke: #555;
  stroke-dasharray: 3 2;
}

.mono .plant-leaf {
  fill: #aaa;
}

.mono .plant-flower {
  fill: #666;
}

.mono .windowpane {
  fill: #eee;
  stroke: #777;
}

.mono .wood {
  fill: #aaa;
}

.mono .eq-floor {
  fill: #f0f0f0;
}

.mono .eq-rack {
  fill: #777;
  stroke: #444;
}

@media print {
  .seat.selected .seatbox,
  .seat:focus .seatbox {
    stroke: #8a9b91;
    stroke-width: 1.2;
  }

  .seat.assigned.selected .seatbox {
    stroke: #42765e;
  }
}
</style>
