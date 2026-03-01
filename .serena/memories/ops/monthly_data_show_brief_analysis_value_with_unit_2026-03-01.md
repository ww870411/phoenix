时间戳：2026-03-01
任务：简要分析中的本期/同期/计划值（并同步上期）显示计量单位。

变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- 新增 formatValueWithUnit(value, unit)。
- 简要分析描述行中的本期/同期/上期/计划值统一调用该函数。
- 对于 % 单位，沿用百分比样式，不重复追加单位文本。

结果：
- 分析正文中的数值均携带单位，语义更清晰。