时间：2025-10-23
主题：修复 Coal_inventory_Sheet 首屏默认日期不显示（镜像查询回填被覆盖）
范围：frontend/src/daily_report_25_26/pages/DataEntryView.vue
现象：首次进入页面，已对默认日期执行 query 且返回正确，但网格不显示；切换日期后才显示。
根因：loadTemplate() 中初始化顺序问题。crosstab 在执行镜像查询后又被后续的模板初始化（setupCrosstabGrid 或等价流程）重置 gridSource，导致首屏回填被清空。watch(bizDate) 二次查询时才显示。
改动：
- 提前判定 template_type，若为 crosstab，先调用 setupCrosstabGrid(tpl) 初始化列与占位行，再执行镜像查询回填 columns/rows；
- 尾部渲染策略调整：crosstab 不再在末尾重复初始化，避免覆盖查询结果；standard 保持原流程。
影响：仅前端页面渲染逻辑，无后端接口与数据结构变更。
文件清单：
- frontend/src/daily_report_25_26/pages/DataEntryView.vue
- frontend/README.md（追加变更说明）
- backend/README.md（记录无后端改动）
验证建议：
- 打开“每日数据填报页面”> 煤炭库存表，保持默认日期，应直接显示数据；
- 切换其他日期再切回默认日期，显示应保持一致。
回滚：移除“提前初始化 crosstab 再查询”的逻辑，并恢复末尾 setupCrosstabGrid 调用（将重新出现首屏空白问题）。