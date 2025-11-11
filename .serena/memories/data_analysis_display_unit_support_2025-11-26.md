## 2025-11-26 数据分析页面“显示单位”支持
- `backend/api/v1/daily_report_25_26.py` 的 `/data_analysis/schema` 接口解析 `单位选择.显示单位` 列表，返回 `display_unit_keys` 与 `display_unit_options`，默认顺序与 JSON 中一致，若缺省则回退所有单位。
- `frontend/src/daily_report_25_26/pages/DataAnalysisView.vue` 新增 `resolveUnitOptions`，优先使用 `display_unit_options` 渲染单选芯片，其他单位仍留在 `unit_dict` 供视图映射与后续查询逻辑复用。