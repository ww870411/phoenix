# 投诉量卡片栅格调整（2025-11-09）
- 背景：仪表盘上“当日省市平台服务投诉量”卡片需要在宽屏模式下与同排卡片保持一致的宽度和高度。
- 操作：在 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 中将投诉卡片在 1024px 以上断点下设置为 `grid-column: span 6`，补充 `min-height: 320px`，并移除 `dashboard-grid__item--table` 修饰，避免被全宽规则强制占满一行。
- 影响：投诉卡片与同排卡片宽度一致且底部对齐，表格仍保留在卡片内部；数据与接口逻辑不受影响。
- 回滚：恢复 `DashBoard.vue` 相关栅格样式及类名至本次修改前即可撤销。