时间戳：2026-03-01
任务：隐藏“期间/类型”筛选器并固定查询为 month+real。

变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- UI：移除筛选区中的“期间（可多选）”“类型（可多选）”。
- 校验：查询按钮与空选择提示仅依赖“口径+指标”。
- 参数：buildPayload 固定传 periods=['month']、types=['real']。
- 状态：loadOptions/resetFilters 固定 filters.periods=['month']、filters.types=['real']。

结果：
- 页面筛选更简洁；
- 查询行为固定为月度实绩口径（month + real）。