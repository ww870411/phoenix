时间：2026-03-17
主题：monthly_data_show 查询页 2023-11 平均气温未显示的程序逻辑排查（未改代码）

前置说明：
- 用户本轮明确要求先检查程序逻辑，不更新 configs/progress.md、frontend/README.md、backend/README.md。
- 已执行 serena__activate_project / serena__check_onboarding_performed。

检查范围：
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- backend/projects/monthly_data_show/api/workspace.py
- backend/projects/monthly_data_show/services/extractor.py
- backend/sql/calc_temp.sql

关键结论：
1. 前端查询页 buildPayload() 当前只传 date_from/date_to，不传 report_month_from/report_month_to；虽然注释写“同时约束 report_month”，但代码实际为 null。故 query-tool 当前并不会用 report_month 过滤 2023-11 查询。
2. 后端平均气温不读取 monthly_data_show 表，也不依赖导入时的 report_month；query_month_data_show() 在选中“平均气温”时，调用 _build_average_temperature_rows()，直接按 request.date_from/date_to 查询 calc_temperature_data 视图的 AVG(aver_temp)。
3. extractor.py 中上年同期数据的 date 会写成 report_year-1 的对应月份（如 2023-11-01），report_month 单独保存来源月份（如 2024-11-01）。因此即使 2023 数据来源于 2024 导入，也不会影响平均气温派生查询本身。
4. calc_temperature_data 视图定义为 temperature_data 的按日聚合视图（DATE_TRUNC day + AVG(value)）。
5. 本地直接验证数据库与后端函数：
   - calc_temperature_data 在 2023-11-01 至 2023-11-30 有 30 条日均记录。
   - temperature_data 在 2023-11 对应有 720 条小时记录。
   - 直接调用 query_month_data_show(QueryRequest(date_from=2023-11-01,date_to=2023-11-30, items=[平均气温], ...)) 返回 1 条记录：company=common,item=平均气温,value=6.14125,date=2023-11-01,report_month=2023-11-01。
   - 使用全部公司+全部指标查询时，平均气温仍位于第一页第 1 条，不存在被分页挤掉的问题。

推断：
- 按当前仓库代码逻辑，2023-11 的平均气温应当能显示；用户看到“不显示”更像是运行中的前端/后端实例与当前仓库代码不一致，或浏览器实际请求/页面状态与预期不一致，而不是 report_month 映射导致的后端查询缺失。
- 另一个轻微问题是前端注释与实际 payload 已不一致，容易误导后续排查。

后续建议：
- 下一步优先抓运行中页面的实际 query 请求体与响应体，确认 localhost 当前实例是否返回平均气温行。
- 若运行实例响应中无该行，再核对该实例是否仍为旧代码或调用了不同后端。