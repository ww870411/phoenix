## 2025-11-08 数据看板 Revogrid 表格统一
- 背景：仪表盘仍使用自定义 HTML 表格，样式难调、功能有限。
- 变更：新增 `frontend/src/daily_report_25_26/components/DashboardRevoGrid.vue` 封装 Revogrid，只读模式下统一加载 `@revolist/vue3-datagrid` 样式；`DashBoard.vue` 中的气温、边际利润、标煤耗量、投诉等表格全部改用该组件，数据结构统一为列定义 + 对象行。
- 效果：表格外观一致，可复制滚动，后续需要排序/锁列等能力可在包装组件中扩展；其它页面未受影响。