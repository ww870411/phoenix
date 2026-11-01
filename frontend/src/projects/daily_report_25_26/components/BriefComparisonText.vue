<template>
  <span v-if="delta !== undefined" :class="briefDeltaClass(delta, digits)">{{ text }}</span>
  <span v-else><span v-for="(part, index) in parts" :key="index" :class="part.className">{{ part.text }}</span></span>
</template>

<script setup>
import { computed } from 'vue'
import { briefComparisonParts, briefDeltaClass } from '../composables/dailyBriefPresentation'
const props = defineProps({
  text: { type: String, default: '' },
  delta: { type: Number, default: undefined },
  digits: { type: Number, default: 2 },
})
const parts = computed(() => briefComparisonParts(props.text))
</script>

<style scoped>
.change-up { color: #c62828; }
.change-down { color: #16803c; }
.change-flat { color: #000; }
</style>
