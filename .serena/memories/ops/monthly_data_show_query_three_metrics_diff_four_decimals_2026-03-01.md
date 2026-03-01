时间：2026-03-01
需求：在月报查询中，三项指标（供暖热耗率/供暖水耗率/供暖电耗率）的同比/环比/计划差值也改为4位小数。
实现：
- 文件：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- 调整：formatSignedNumber(value, item) 按 valueDecimalDigitsByItem(item) 控制小数位；
- 调用点：简要分析段落中的 yoyDiff/momDiff/planDiff；导出对比明细中的三类差值。
结果：三项指标的差值展示与其值展示精度一致，均为4位小数；后端无改动。