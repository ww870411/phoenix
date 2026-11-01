<template>
  <button ref="opener" class="lifecycle-launch" type="button" aria-haspopup="dialog" @click="openDialog">
    <span><strong>主设备启停生命周期</strong><small>按阶段查看设备轨迹、运行时长，支持多主体对比与图表导出</small></span>
    <span class="launch-action">打开时间轴 ↗</span>
  </button>
  <dialog ref="dialogElement" class="lifecycle-dialog" aria-labelledby="dispatch-lifecycle-dialog-title" @close="onClosed" @click="onBackdropClick">
    <div class="dialog-shell">
      <header class="dialog-heading">
        <div><h2 id="dispatch-lifecycle-dialog-title">主设备生命周期分析</h2><p>主体多选 · 按日查看 · 运行时长 · 完整导出</p></div>
        <button type="button" class="dialog-close" aria-label="关闭生命周期弹窗" @click="closeDialog">关闭 ×</button>
      </header>
      <div class="dialog-body">
        <DispatchLifecycle v-if="isOpen" :project-key="projectKey" :latest-date="latestDate" :available-dates="availableDates" :refresh-key="refreshKey" />
      </div>
    </div>
  </dialog>
</template>

<script setup>
import { onBeforeUnmount, ref } from 'vue'
import DispatchLifecycle from './DispatchLifecycle.vue'

defineProps({ projectKey: { type: String, required: true }, latestDate: { type: String, default: '' }, availableDates: { type: Array, default: () => [] }, refreshKey: { type: Number, default: 0 } })
const dialogElement = ref(null), opener = ref(null), isOpen = ref(false)

function openDialog() {
  if (!dialogElement.value || dialogElement.value.open) return
  dialogElement.value.showModal()
  isOpen.value = true
}
function closeDialog() { dialogElement.value?.close() }
function onClosed() { isOpen.value = false; opener.value?.focus() }
function onBackdropClick(event) { if (event.target === dialogElement.value) closeDialog() }
onBeforeUnmount(() => { dialogElement.value?.close() })
</script>

<style scoped>
.lifecycle-launch { width: 100%; display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 18px 24px; border: 1px solid #dce7f1; border-radius: 12px; background: linear-gradient(110deg, #edf6ff, #fff); color: #234665; text-align: left; cursor: pointer; font: inherit; }
.lifecycle-launch:hover { border-color: #7eafd8; box-shadow: 0 3px 12px #215e9610; }
.lifecycle-launch strong { display: block; font-size: 16px; margin-bottom: 5px; }
.lifecycle-launch small { display: block; font-size: 12px; color: #718398; line-height: 1.6; }
.launch-action { flex-shrink: 0; padding: 9px 14px; border-radius: 7px; background: #215e96; color: #fff; font-size: 12px; }
.lifecycle-dialog { width: min(1580px, calc(100vw - 40px)); max-width: none; max-height: calc(100dvh - 40px); padding: 0; border: 0; border-radius: 16px; overflow: auto; box-shadow: 0 24px 80px #0f172a45; background: #f4f7fb; }
.lifecycle-dialog::backdrop { background: #0f172a85; backdrop-filter: blur(3px); }
.dialog-heading { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 16px 22px; background: #fff; border-bottom: 1px solid #e2e8f0; position: sticky; top: 0; z-index: 10; }
.dialog-heading h2 { font-size: 18px; color: #234665; margin: 0 0 4px; }
.dialog-heading p { font-size: 11px; color: #8293a6; margin: 0; }
.dialog-close { border: 1px solid #dce5ef; border-radius: 7px; color: #52677e; padding: 8px 13px; cursor: pointer; background: #fff; white-space: nowrap; }
.dialog-close:hover { background: #edf5fc; }
.dialog-body { padding: 16px; }
@media (max-width: 640px) { .lifecycle-launch { padding: 14px 16px; }.lifecycle-launch small { font-size: 11px; }.launch-action { padding: 8px; }.lifecycle-dialog { width: calc(100vw - 16px); max-height: calc(100dvh - 16px); }.dialog-heading { padding: 12px 14px; }.dialog-body { padding: 8px; } }
</style>
