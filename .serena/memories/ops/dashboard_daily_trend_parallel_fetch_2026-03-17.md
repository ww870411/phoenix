时间：2026-03-17
背景：用户要求继续优化数据看板 10.每日对比趋势，同时明确要求保证数据正确性。
变更文件：
- backend/services/dashboard_expression.py
实现摘要：
1. 保留 groups 数据的原始口径，不改 _fetch_metrics_from_view 的查询逻辑。
2. 将趋势块使用的 _build_group_metric_cache 从按日期串行加载，改为：
   - 优先读取 shared_metrics_cache 中已存在的 groups:Group:YYYY-MM-DD 条目；
   - 对缺失日期使用 ThreadPoolExecutor 并发调用 _fetch_metrics_from_view；
   - 使用独立 SessionLocal 连接，避免共享 session；
   - 降低 tick_callback 频率，仅在趋势数据装载开始/完成时更新。
3. _fill_daily_trend_section 改为合并本期与同期所需日期后统一装载，再分别拆回 current_cache 与 peer_cache，避免本期/同期两轮独立装载。
4. evaluate_dashboard 调用趋势块时，将 metrics_cache 传入，用于复用已有日期缓存。
验证：
- python -m py_compile backend/services/dashboard_expression.py 通过
- 4 个代表日期（2026-03-15、2026-03-16、2025-03-15、2025-03-16）新旧结果逐项比较，mismatch_count = 0
- 4 天 groups 趋势数据装载耗时：串行约 86.79s，并发约 22.8s
- evaluate_dashboard(project_key='daily_report_25_26', show_date='2026-03-16', only_section_indexes=['10']) 新版耗时约 109.86s，已低于此前 120s 超时表现
备注：按用户要求，本轮未更新 configs/progress.md、frontend/README.md、backend/README.md。