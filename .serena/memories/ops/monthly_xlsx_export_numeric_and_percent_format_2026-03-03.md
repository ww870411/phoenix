时间：2026-03-03。
需求：月报查询导出的 XLSX 中，指标值需要是数值格式；百分比指标需要是百分比格式；小数位按页面规则。
实现：
- 文件：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- 在 downloadXlsx 中将查询结果、对比明细、气温日序同比、气温汇总改为写入数值单元格（t:'n'），避免写入带单位的字符串。
- 新增导出格式辅助函数：isPercentUnit、buildDecimalFormat、buildExcelValueFormat、setSheetNumericCell。
- 数值格式策略：普通值按 valueDecimalDigitsByItem 对应位数生成 #,##0.xx；百分比按 0.xx%（Excel 百分比格式）。
验证：npm run build（frontend）通过。
说明：用户更新的 backend_data/projects/monthly_data_show/indicator_config.json 与 monthly_data_show_extraction_rules.json 仍按既有配置加载链路生效，无需额外代码改动。