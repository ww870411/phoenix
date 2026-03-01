时间：2026-03-01
需求：月报数据查询页面将“供暖热耗率/供暖水耗率/供暖电耗率”默认显示为4位小数。
实现：
- 文件：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- 新增：FOUR_DECIMAL_ITEMS 与 valueDecimalDigitsByItem(item)
- 调整：formatNumber 支持可配置小数位；formatValue/formatValueWithUnit 新增 item 参数并按指标选取小数位
- 调用点：查询结果表、同比/环比/计划比列表、简要分析文本、导出表格格式化均传入 item。
结果：三项指定指标默认4位小数，其余指标保持2位。后端无改动。