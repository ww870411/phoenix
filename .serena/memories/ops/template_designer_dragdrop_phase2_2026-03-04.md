时间：2026-03-04
主题：模板设计器第二期（拖拽设计）

变更文件：
1) frontend/src/projects/daily_report_25_26/pages/TemplateDesignerView.vue
- 重构为可视化拖拽设计版本
- 列定义拖拽排序（onColumnDragStart/onColumnDrop）
- 行定义拖拽排序（onRowDragStart/onRowDrop）
- 新增行编辑表（row_key/row_label/unit）
- 新增预览网格，支持编辑 row.cells
- 保留 JSON 编辑并提供 applyRowsJson
- 保存/发布继续走既有 API

2) configs/progress.md
- 新增“模板设计器第二期：拖拽设计表格”记录

3) frontend/README.md
- 新增结构同步条目（拖拽版）

4) backend/README.md
- 新增联动说明（本轮无后端改动）

结果：
- 用户可在模板设计器中通过拖拽组织行列并可视化配置单元格初始值。
- 与既有模板创建/更新/发布流程兼容。