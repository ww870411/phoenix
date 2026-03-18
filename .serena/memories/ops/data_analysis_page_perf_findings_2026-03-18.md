日期：2026-03-18
主题：daily_report_25_26 数据分析页 perf 首轮结论

用户复测样本：
- analysis_mode=range
- timeline_days=59
- selected_metrics_count=6
- 单位：Group、ZhuChengQu、JinZhou

结果：
1. Group
- total_ms=22506.79
- main_analysis_query_ms=10531.76
- analysis_timeline_ms=2395.3
- previous_period_query_ms=9579.45
- analysis_view=analysis_groups_sum
- analysis_timeline_view=analysis_groups_daily

2. ZhuChengQu
- total_ms=22088.89
- main_analysis_query_ms=9866.78
- analysis_timeline_ms=2363.81
- previous_period_query_ms=9858.04
- analysis_view=analysis_groups_sum
- analysis_timeline_view=analysis_groups_daily

3. JinZhou
- total_ms=1806.52
- main_analysis_query_ms=69.92
- analysis_timeline_ms=1668.19
- previous_period_query_ms=68.08
- analysis_view=analysis_company_sum
- analysis_timeline_view=analysis_company_daily

结论：
- 集团/主城区口径的主瓶颈在 `analysis_groups_sum` 主查询及其上一周期同类查询，两段合计约 20 秒。
- `analysis_groups_daily` timeline 查询约 2.3 秒，不是第一优先级。
- 公司口径（如 JinZhou）主查询很轻，主要耗时在 timeline 查询。
- 数据分析页当前不是单一瓶颈；不同单位口径对应的慢点不同。
- 前端按单位串行请求，页面总耗时近似为各单位耗时累加。

建议优先级：
1. 先分析 `analysis_groups_sum` / `analysis_groups_daily` 视图定义和执行计划。
2. 其次评估前端多单位并发。
3. 再考虑重写 timeline 查询，避免按天循环。