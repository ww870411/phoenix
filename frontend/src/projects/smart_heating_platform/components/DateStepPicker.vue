<template>
  <div class="date-picker-group" role="group" :aria-label="ariaLabel">
    <button
      class="date-step-btn"
      type="button"
      title="前一天"
      :disabled="disabled || !canStepPrev"
      @click="stepDay(-1)"
    >
      ◀
    </button>
    <input
      :value="modelValue"
      type="date"
      :min="min || undefined"
      :max="effectiveMax || undefined"
      :disabled="disabled"
      class="date-step-input"
      :aria-label="ariaLabel"
      @change="onInputChange"
    />
    <button
      class="date-step-btn"
      type="button"
      title="后一天"
      :disabled="disabled || !canStepNext"
      @click="stepDay(1)"
    >
      ▶
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { MIN_PLATFORM_DATE, shiftIsoDate, todayLocalIso } from '../utils/dateUtils'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  min: {
    type: String,
    default: MIN_PLATFORM_DATE,
  },
  max: {
    type: String,
    default: '',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  ariaLabel: {
    type: String,
    default: '选择日期',
  },
})

const emit = defineEmits(['update:modelValue', 'change'])

const effectiveMax = computed(() => props.max || todayLocalIso())

const canStepPrev = computed(() => {
  const prev = shiftIsoDate(props.modelValue || effectiveMax.value, -1)
  return !props.min || prev >= props.min
})

const canStepNext = computed(() => {
  if (!props.modelValue) return false
  const next = shiftIsoDate(props.modelValue, 1)
  return !effectiveMax.value || next <= effectiveMax.value
})

function stepDay(delta) {
  const next = shiftIsoDate(props.modelValue || effectiveMax.value, delta)
  if (props.min && next < props.min) return
  if (effectiveMax.value && next > effectiveMax.value) return
  if (next !== props.modelValue) {
    emit('update:modelValue', next)
    emit('change', next)
  }
}

function onInputChange(event) {
  const val = String(event?.target?.value || '')
  emit('update:modelValue', val)
  emit('change', val)
}
</script>

<style scoped>
.date-picker-group {
  display: inline-flex;
  align-items: center;
  height: 34px;
  box-sizing: border-box;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  overflow: hidden;
  background: #ffffff;
}

.date-step-btn {
  border: none;
  background: #f8fafc;
  color: #334155;
  height: 100%;
  padding: 0 10px;
  font-size: 13px;
  font-weight: 600;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}

.date-step-btn:first-child {
  border-right: 1px solid #e2e8f0;
}

.date-step-btn:last-child {
  border-left: 1px solid #e2e8f0;
}

.date-step-btn:hover:not(:disabled) {
  background: #eff6ff;
  color: #1d4ed8;
}

.date-step-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.date-step-input {
  border: none;
  height: 100%;
  padding: 0 8px;
  font-size: 13px;
  font-weight: 600;
  line-height: 32px;
  color: #0f172a;
  background: #ffffff;
  min-width: 0;
  box-sizing: border-box;
  outline: none;
}

@media (max-width: 768px) {
  .date-picker-group {
    flex: 1;
    min-width: 0;
  }
  .date-step-input {
    flex: 1;
    width: 100%;
  }
}
</style>
