时间：2026-02-28
变更摘要：
1) monthly_data_show 查询页在“查询结果”中新增导出 XLSX 按钮。
2) 新增“同比与环比（基于最新月份）”对比表：按 company/item/period/type/unit 维度聚合，自动计算同比（月-12）和环比（月-1）。
3) 新增“专业分析要点”：输出同比分布、波动最大项、温度相关性（皮尔逊系数）与空值质量提示。
4) XLSX 导出包含三个工作表：查询结果、同比环比对比、专业分析。
涉及文件：
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md
说明：本轮后端接口未改，分析逻辑在前端基于查询结果计算。