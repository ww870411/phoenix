# 数据看板单耗卡片栅格调整（2025-11-11）
- 需求：将仪表盘中“供暖热/电/水单耗对比”三张卡片在大屏上改为独占一行（12 栅格）。
- 实现：更新 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 样式，将 `.dashboard-grid__item--unit` 的 `grid-column` 从 `span 4` 调整为 `span 12`；后端 `/dashboard` 输出结构未改。
- 降级说明：Serena 暂不支持 `.vue` 样式块符号写入，本次通过 `desktop-commander::read_file` + `apply_patch` 完成修改，回滚仅需恢复该文件。
- 验证：刷新数据看板确认三张单耗对比卡片在 ≥1024px 视口各占一行，窄屏保持默认单列布局。