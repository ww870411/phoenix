// 原生弹窗行为与组件挂载时机：无需浏览器或数据库。
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { ref } from 'vue'

test('点击入口才挂载生命周期，重复打开、遮罩关闭及焦点恢复正常', () => {
  const source = readFileSync(new URL('../src/projects/daily_report_25_26/components/DispatchLifecycleDialog.vue', import.meta.url), 'utf8')
  const script = source.match(/<script setup>([\s\S]*?)<\/script>/)[1].replace(/import[^\n]+\n/g, '')
  const callbacks = []
  const factory = new Function('ref', 'defineProps', 'onBeforeUnmount', `${script};return {dialogElement,opener,isOpen,openDialog,closeDialog,onClosed,onBackdropClick};`)
  const view = factory(ref, () => ({}), fn => callbacks.push(fn))
  let opened = 0, closed = 0, focused = 0
  view.dialogElement.value = { open: false, showModal() { this.open = true; opened++ }, close() { this.open = false; closed++ } }
  view.opener.value = { focus() { focused++ } }
  assert.equal(view.isOpen.value, false)
  view.openDialog(); view.openDialog()
  assert.equal(opened, 1)
  assert.equal(view.isOpen.value, true)
  view.onBackdropClick({ target: {} })
  assert.equal(closed, 0)
  view.onBackdropClick({ target: view.dialogElement.value })
  assert.equal(closed, 1)
  view.onClosed()
  assert.equal(view.isOpen.value, false)
  assert.equal(focused, 1)
  view.openDialog()
  callbacks[0]()
  assert.equal(closed, 2)
})
