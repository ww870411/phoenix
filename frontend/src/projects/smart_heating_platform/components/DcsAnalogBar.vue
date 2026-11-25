<template>
  <div :class="['dcs-bar-wrap', { compact }]">
    <div v-if="label" class="dcs-bar-head">
      <span class="dcs-bar-label">{{ label }}</span>
      <span :class="['dcs-bar-val', `lvl-${resolvedLevel}`]">
        {{ formattedValue }}<span v-if="unit && value !== null && value !== undefined" class="dcs-bar-unit">{{ unit }}</span>
      </span>
    </div>
    <div class="dcs-track" :title="titleText">
      <div
        v-if="safeBandStyle"
        class="dcs-safe-band"
        :style="safeBandStyle"
      ></div>
      <div
        v-if="warnHighPct !== null"
        class="dcs-tick warn-tick"
        :style="{ left: `${warnHighPct}%` }"
      ></div>
      <div
        v-if="alarmLowPct !== null"
        class="dcs-tick alarm-tick"
        :style="{ left: `${alarmLowPct}%` }"
      ></div>
      <div
        v-if="fillPct !== null"
        :class="['dcs-fill', `lvl-${resolvedLevel}`]"
        :style="{ width: `${fillPct}%` }"
      ></div>
      <div
        v-if="fillPct !== null"
        :class="['dcs-pointer', `lvl-${resolvedLevel}`]"
        :style="{ left: `calc(${fillPct}% - 2px)` }"
      ></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: [Number, String], default: null },
  min: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  safeMin: { type: Number, default: null },
  safeMax: { type: Number, default: null },
  warnHigh: { type: Number, default: null },
  alarmLow: { type: Number, default: null },
  alarmLevel: { type: String, default: 'auto' }, // auto | normal | warn | critical | offline
  label: { type: String, default: '' },
  unit: { type: String, default: '' },
  decimals: { type: Number, default: 1 },
  compact: { type: Boolean, default: false },
})

const numVal = computed(() => {
  if (props.value === null || props.value === undefined || props.value === '') return null
  const n = Number(props.value)
  return Number.isFinite(n) ? n : null
})

function clampPct(v) {
  const span = props.max - props.min
  if (span <= 0) return 0
  return Math.max(0, Math.min(100, ((v - props.min) / span) * 100))
}

const fillPct = computed(() => (numVal.value === null ? null : clampPct(numVal.value)))

const safeBandStyle = computed(() => {
  if (props.safeMin === null || props.safeMax === null) return null
  const left = clampPct(props.safeMin)
  const right = clampPct(props.safeMax)
  if (right <= left) return null
  return { left: `${left}%`, width: `${right - left}%` }
})

const warnHighPct = computed(() => (props.warnHigh === null ? null : clampPct(props.warnHigh)))
const alarmLowPct = computed(() => (props.alarmLow === null ? null : clampPct(props.alarmLow)))

const resolvedLevel = computed(() => {
  if (props.alarmLevel && props.alarmLevel !== 'auto') return props.alarmLevel
  if (numVal.value === null) return 'offline'
  if (props.alarmLow !== null && numVal.value < props.alarmLow) return 'critical'
  if (props.warnHigh !== null && numVal.value > props.warnHigh) return 'warn'
  if (props.safeMax !== null && numVal.value > props.safeMax) return 'warn'
  if (props.safeMin !== null && numVal.value < props.safeMin) return 'warn'
  return 'normal'
})

const formattedValue = computed(() => {
  if (numVal.value === null) return '--'
  return numVal.value.toFixed(props.decimals).replace(/\.0+$/, '')
})

const titleText = computed(() => {
  const parts = [`当前: ${formattedValue.value}${props.unit || ''}`, `量程: ${props.min}~${props.max}${props.unit || ''}`]
  if (props.safeMin !== null && props.safeMax !== null) {
    parts.push(`正常带: ${props.safeMin}~${props.safeMax}${props.unit || ''}`)
  }
  return parts.join(' | ')
})
</script>

<style scoped>
.dcs-bar-wrap {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.dcs-bar-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 6px;
  font-size: 11px;
}

.dcs-bar-label {
  color: #475569;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dcs-bar-val {
  font-family: Consolas, "Courier New", monospace;
  font-variant-numeric: tabular-nums;
  font-weight: 700;
  font-size: 12px;
  color: #16202e;
}

.dcs-bar-val.lvl-critical { color: #b91c1c; }
.dcs-bar-val.lvl-warn { color: #b45309; }
.dcs-bar-val.lvl-offline { color: #64748b; }

.dcs-bar-unit {
  font-size: 10px;
  font-weight: 500;
  color: #526071;
  margin-left: 2px;
}

.dcs-track {
  position: relative;
  height: 8px;
  background: #c6cfd9;
  border: 1px solid #9aa7b7;
  border-radius: 1px;
  overflow: hidden;
}

.dcs-bar-wrap.compact .dcs-track {
  height: 6px;
}

.dcs-safe-band {
  position: absolute;
  top: 0;
  bottom: 0;
  background: #b0c2d4;
  border-left: 1px solid #8ea2b8;
  border-right: 1px solid #8ea2b8;
}

.dcs-fill {
  position: absolute;
  top: 1px;
  bottom: 1px;
  left: 0;
  background: #3b6b8f;
  transition: width 0.2s ease;
}

.dcs-fill.lvl-warn { background: #d97706; }
.dcs-fill.lvl-critical { background: #dc2626; }
.dcs-fill.lvl-offline { background: #94a3b8; }

.dcs-pointer {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 3px;
  background: #0f172a;
}

.dcs-pointer.lvl-critical { background: #7f1d1d; }
.dcs-pointer.lvl-warn { background: #78350f; }

.dcs-tick {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1.5px;
  z-index: 2;
}

.warn-tick { background: #b45309; }
.alarm-tick { background: #dc2626; }
</style>
