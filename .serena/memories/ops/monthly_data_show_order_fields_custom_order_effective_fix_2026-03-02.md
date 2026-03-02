时间：2026-03-02
主题：monthly_data_show 查询层次顺序不生效修复

现象：用户将层次顺序改为“口径->指标->时间”后，结果仍表现为默认时间优先。

根因：
- backend/projects/monthly_data_show/api/workspace.py 的 _merge_and_sort_rows 预置了固定前置时间键，覆盖了 order_fields 的真实优先级。

修复：
1) _merge_and_sort_rows
- 改为按 order_fields 顺序逐层构建排序键
- field == time 时仅在该层位置使用 report_month/date 升序键
- 若未选择 time，保留历史时间降序兜底行为（兼容旧习惯）

验证：
- python -m py_compile backend/projects/monthly_data_show/api/workspace.py 通过

结果：
- 自定义层次顺序（如 company,item,time）会真实影响查询结果展示层次。