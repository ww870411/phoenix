时间：2026-03-01
需求：业务月份止默认不选，并改文案为“业务月份止（非必选）”。
实现：
- 文件：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- 模板文案：业务月份止 -> 业务月份止（非必选）
- loadOptions()：dateMonthFrom 默认上个月，dateMonthTo 默认空字符串
- resetFilters()：dateMonthTo 重置为空字符串
结果：页面初始与重置后，月份止为空且语义明确为非必选。
留痕：已同步更新 configs/progress.md、frontend/README.md、backend/README.md。