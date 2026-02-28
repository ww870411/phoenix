时间：2026-02-28
主题：异常清单新增“指标名称”列
需求：异常清单中显示源指标名称。

改动文件：
1) backend/projects/monthly_data_pull/services/engine.py
2) frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue
3) configs/progress.md
4) frontend/README.md
5) backend/README.md

实现摘要：
- 后端执行日志新增 indicator_name 字段；
- 从映射行按候选列提取：指标名称/指标/项目名称/项目；
- 前端异常清单新增“指标名称”列并显示该字段。

结果：
- 异常项可直接对应到具体指标，定位效率提升。