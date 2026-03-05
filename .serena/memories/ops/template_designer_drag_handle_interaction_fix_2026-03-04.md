时间：2026-03-04
问题：模板设计器中部分输入无法编辑、删除按钮点击不稳定。

根因：
- 整行/整列表头 draggable=true 导致拖拽与输入/点击交互冲突。

修复：
- 文件 frontend/src/projects/daily_report_25_26/pages/TemplateDesignerView.vue
- 拖拽改为仅手柄触发：
  - 行与列移除整块 draggable
  - dragstart/dragend 绑定到 span.drag-handle
- 删除按钮保持 click 语义，避免被拖拽抢占。

验证：
- npm run build（frontend）通过。

留痕：
- configs/progress.md
- frontend/README.md
- backend/README.md