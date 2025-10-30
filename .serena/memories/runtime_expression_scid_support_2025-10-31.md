## 2025-10-31 运行时表达式支持 scid.*
- 背景：数据展示页（Group_analysis_brief_report_Sheet）在“库存煤量（含港口、在途）”行使用 `scid.Group_sum` 等语法读取新建视图 `sum_coal_inventory_data` 的结果，原逻辑按常量表结构加载别名，导致该别名返回空集。
- 处理：
  1. `backend/sql/create_view.sql` 保留最新日期聚合，同时输出 `company='ZhuChengQu_sum'`、`company='Group_sum'` 等键，与模板中的 `scid.*` 对齐。
  2. `backend/services/runtime_expression.py` 在别名加载阶段识别 `table_name == "sum_coal_inventory_data"`，使用 `_fetch_sum_coal_inventory_constants` 读取 `*_sum` 聚合值，并为 biz/peer 口径返回相同数值。
- 结果：`render_spec(..., trace=True)` 的 `_trace.used_consts` 可看到 `scid.Group_sum`/`scid.JinZhou_sum` 等命中记录，展示页列首已正确显示最新库存数据。