# 仪表盘 Trace 复选框移除（2025-11-09）
- 背景：数据看板页面顶部存在调试用 Trace 复选框，生产环境不需要且可能引起误操作。
- 操作：在 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 删除 Trace 复选框模板与关联的 `traceEnabled` 响应式变量，保留业务日期选择与自动刷新逻辑。
- 影响：前端不再向后端传递 trace 标记，界面更简洁；后端接口结构无变化。
- 回滚：恢复 `DashBoard.vue` 至本次修改前版本即可重新显示 Trace 开关。