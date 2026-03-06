时间：2026-03-06
主题：前端移动端表格与录入页优化第二轮

前置说明：
- 延续第一轮的 apply_patch 降级编辑方式，原因仍为 Vue SFC 结构化编辑支持不足。
- 本轮仅修改前端展示层模板容器与样式断点，不改后端接口、数据库或协议。

改动摘要：
1. DataAnalysisView.vue
- 为同比、环比、计划比较三张结果表增加 result-table-wrapper 横向滚动容器。
- 为 result-table 增加 min-width，防止手机端强压缩。
- 将 timeline-grid-wrapper 改为横向滚动，并通过 :deep(revo-grid) 设置最小宽度。
- 新增 <=900px / <=640px 响应式断点，压缩字号、padding，并降低时间轴高度。

2. DashBoard.vue
- 为 summary-fold-table-wrapper 增加 -webkit-overflow-scrolling: touch。
- 在 <=1023px 与 <=640px 下收紧焦点指标折叠表的列宽、字号和 padding。
- 在 <=640px 下将 center-card 控制按钮改为纵向堆叠，降低拥挤度与误触。

构建验证：
- frontend 目录执行 npm run build，2026-03-06 再次通过。

浏览器实测（390x844，手机视口，前端 mock 登录/数据注入）：
- monthly_data_show/query-tool：table-wrap clientWidth=373, scrollWidth=1005, canScroll=true。
- daily_report_25_26/pages/demo/sheets/demo：table-wrap clientWidth=373, scrollWidth=1005, canScroll=true；mobile-grid-hint 可见。
- monthly_data_pull：table-wrap clientWidth=310, scrollWidth=440, canScroll=true。
- daily_report_25_26/pages/demo/data-analysis：result-table-wrapper clientWidth=329, scrollWidth=480, canScroll=true。
- daily_report_25_26/pages/demo/dashboard：summary-fold-table-wrapper clientWidth=337, scrollWidth=481, canScroll=true。

限制与剩余事项：
- 当前为浏览器模拟与前端 mock，不是真机触摸回归。
- DataAnalysisView 的完整环比/计划区与图表联动仍未做真实后端数据链路验证；当前重点验证的是窄屏容器与横滑能力。