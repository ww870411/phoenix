# 标煤消耗卡片移除全幅标记（2025-11-09）
- 背景：“标煤消耗量对比”卡片仍携带 `dashboard-grid__item--table` 类，导致宽屏模式下即使设置 span 6 仍会占满整行。
- 操作：在 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 中移除该卡片 DOM 上的 `dashboard-grid__item--table` 类，同时保持栅格样式中 `dashboard-grid__item--coal` 的 span 6 设置。
- 影响：卡片在宽屏下可与“煤炭库存”并排显示，布局更紧凑；表格仍位于卡片内部，数据逻辑未变。
- 回滚：恢复卡片标签的类名至包含 `dashboard-grid__item--table` 即可撤销。