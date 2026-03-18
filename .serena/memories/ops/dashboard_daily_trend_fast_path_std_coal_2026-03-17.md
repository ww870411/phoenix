时间：2026-03-17
背景：用户反馈 10 号趋势块仍慢，需要继续优化，同时保持数据正确。
变更文件：
- backend/services/dashboard_expression.py
实现摘要：
1. 识别到当前看板配置中的 10 号趋势块实际仅包含一个重型 groups 指标：sum_consumption_std_coal_zhangtun（中文名：标煤耗量汇总(张屯)），另一个是平均气温。
2. 新增 FAST_GROUP_DAILY_METRIC_RULES 与 _fetch_fast_group_daily_metric_map：
   - 对 sum_consumption_std_coal_zhangtun 不再经 groups 视图全量计算；
   - 直接按 groups.sql 中 group_sum_std_zhangtun 的口径，从 daily_basic_data 聚合：
     * BeiHai/XiangHai/GongRe/JinZhou/BeiFang/JinPu 的 consumption_std_coal
     * 加上 ZhuangHe 的 consumption_std_coal_zhangtun
   - 仅取按日 value_biz_date 所需结果，适配趋势场景。
3. _fill_daily_trend_section 改为：
   - 优先尝试对趋势指标走 fast path；
   - 仅当某指标无 fast path 时才回退到 groups 视图缓存装载。
4. 保留原 groups 视图作为回退路径，不影响其他趋势指标的口径。
验证：
- python -m py_compile backend/services/dashboard_expression.py 通过
- 对 4 个代表日期（2026-03-15、2026-03-16、2025-03-15、2025-03-16）比较 fast path 与 groups 视图中的 sum_consumption_std_coal_zhangtun.value_biz_date，结果完全一致
- evaluate_dashboard('daily_report_25_26', show_date='2026-03-16', only_section_indexes=['10']) 耗时约 0.12s，较此前约 109.86s 显著下降
备注：按用户要求，本轮未更新 configs/progress.md、frontend/README.md、backend/README.md。