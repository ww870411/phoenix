时间戳：2026-02-15
问题：spring 看板温度接口归位后，用户反馈气温曲线仍空白。

定位：
- spring 轻量接口仅查询 calc_temperature_data；当该视图为空/未刷新时返回空结果。

修复：
- 文件：backend/projects/daily_report_spring_festval_2026/api/temperature_trend.py
- 函数：_query_temperature_daily_avg_map
- 逻辑：先查 calc_temperature_data；若无行，则回退查 temperature_data（按 CAST(date_time AS DATE) 分组 AVG(value)）。

结果：
- 只要 temperature_data 存在原始温度数据，即可返回日均气温序列；避免因视图问题导致前端曲线空白。

同步记录：
- configs/progress.md
- backend/README.md
- frontend/README.md