# 单耗卡片标签分离（2025-11-11）
- 变更：`frontend/src/daily_report_25_26/pages/DashBoard.vue` 的 `useUnitConsumptionOption` 将“本期/同期”组合标签拆分为各自独立标签，并开启同期柱的数值显示，配合 12 栅格布局提升可读性。
- 降级说明：Serena 暂不支持 `.vue` 符号级写入，本次通过 `desktop-commander::read_file` + `apply_patch` 修改；回滚时恢复该文件即可。
- 验证：刷新仪表盘确认单耗卡片中每根柱体单独显示两位小数标签，且不会再出现组合标签。