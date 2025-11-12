# 数据分析页面：气温指标与常量分组优化（2025-11-27）

## 关键改动
- `backend/api/v1/daily_report_25_26.py`
  - Schema 支持“气温指标字典”，`metric_group_views['temperature']` 映射到 `calc_temperature_data`；新增 `_query_temperature_rows`，单日模式读取指定日期，累计模式对区间做 `AVG()`，统一返回 `℃`。
  - 常量分组不再写入 `metric_group_views`，避免前端与单位视图绑定；返回体新增 `temperature_metric_dict/options`。
  - 查询流程新增 `temperature_metric_keys`，结果集将 `value_type='temperature'` 的行标记来源视图，缺失值会写入 warnings。
- `DataAnalysisView.vue`
  - 计算 `unitViewNames`，仅当分组视图出现在单位视图集合中才会根据 `activeView` 禁用；常量/气温分组始终可选。
  - 结果表新增“气温”标签，指标面板新增 `group-badge--temp`。
- 文档与进度记录：backend/frontend README、configs/progress.md 均添加本次兼容说明。

## 验证/注意
- 需确保数据库已执行 `backend/sql/calc_temp.sql`（或包含 `calc_temperature_data` 的脚本）。
- `python -m py_compile backend/api/v1/daily_report_25_26.py` 已验证语法；前端仍需 `npm run build` 才能产生产物。
- 如果配置中新增的 `气温指标` key 未能映射到 `max_temp/min_temp/aver_temp`，后端会返回 400 提示，方便排查。