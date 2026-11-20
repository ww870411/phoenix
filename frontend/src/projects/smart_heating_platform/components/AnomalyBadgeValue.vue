<template>
  <span v-if="note" class="abv-wrap" :class="{ 'tip-bottom': placement === 'bottom' }" :title="`⚠️ ${note}`" tabindex="0">
    <span class="abv-text"><slot>{{ text }}</slot><sup class="abv-mark">*</sup></span>
    <span class="abv-tip" role="tooltip">
      <strong>⚠️ 数据异常已修正</strong>
      <span>{{ note }}</span>
    </span>
  </span>
  <span v-else><slot>{{ text }}</slot></span>
</template>

<script setup>
defineProps({
  text: { type: [String, Number], default: '' },
  note: { type: String, default: '' },
  placement: { type: String, default: 'top' },
})
</script>

<style scoped>
.abv-wrap {
  position: relative;
  display: inline-flex;
  align-items: baseline;
  cursor: help;
}
.abv-text {
  color: #dc2626 !important;
  font-weight: 700;
  text-decoration: underline dotted #f87171;
  text-underline-offset: 3px;
}
.abv-mark {
  color: #b91c1c;
  font-size: 10px;
  margin-left: 1px;
  font-weight: 800;
}
.abv-tip {
  display: none;
  position: absolute;
  left: 50%;
  bottom: calc(100% + 6px);
  transform: translateX(-50%);
  z-index: 80;
  min-width: 220px;
  max-width: 340px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #0f172a;
  color: #f8fafc;
  font-size: 12px;
  font-weight: 400;
  line-height: 1.45;
  white-space: normal;
  text-align: left;
  box-shadow: 0 10px 25px rgba(15, 23, 42, 0.3);
  border: 1px solid #ef4444;
  pointer-events: none;
}
.abv-wrap.tip-bottom .abv-tip {
  bottom: auto;
  top: calc(100% + 6px);
}
.abv-tip strong {
  color: #fca5a5;
  font-size: 11px;
}
.abv-wrap:hover .abv-tip,
.abv-wrap:focus-within .abv-tip {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
</style>
