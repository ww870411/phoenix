# monthly_data_show 查询页 report_month 过滤逻辑确认

时间：2026-05-01
任务：确认 `/projects/monthly_data_show/query-tool` 单月查询时对 `monthly_data_show.report_month` 的匹配逻辑。

结论：当前前端 `MonthlyDataShowQueryToolView.vue` 的 `buildPayload()` 将月份控件转换为 `date_from=YYYY-MM-01`、`date_to=YYYY-MM-月末`，但显式传 `report_month_from: null`、`report_month_to: null`。因此主查询接口 `/monthly-data-show/query` 当前不会按 `report_month` 过滤，而是按表字段 `date` 做完整日期范围过滤。

后端证据：`backend/projects/monthly_data_show/api/workspace.py` 中 `_build_query_sql_parts()` 只有当请求包含 `report_month_from` / `report_month_to` 时才追加 `report_month >= :report_month_from` / `report_month <= :report_month_to`。解析使用 `date.fromisoformat`，字段格式要求为 `YYYY-MM-DD`，不是只取月份位数。

影响：如果调用方未来传入 `report_month_from=2026-03-01` 且 `report_month_to=2026-03-31`，则 `report_month` 在 2026 年 3 月任意日期都会命中；但当前查询页单月选择不会触发该条件。若传入上下界同为 `2026-03-01`，则只匹配 `report_month=2026-03-01`。