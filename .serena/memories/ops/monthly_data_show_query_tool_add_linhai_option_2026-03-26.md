时间：2026-03-26
任务：为 `http://localhost:5173/projects/monthly_data_show/query-tool` 页面“口径”栏目补充“临海”选项。
结论：查询页前端不维护本地口径枚举，`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue` 在 `loadOptions()` 中调用 `getMonthlyDataShowQueryOptions('monthly_data_show')`，直接使用接口返回的 `companies` 作为筛选项。
变更文件：
- `backend/projects/monthly_data_show/api/workspace.py`
- `configs/progress.md`
- `frontend/README.md`
- `backend/README.md`
变更摘要：
- 在 `get_monthly_data_show_query_options()` 中先构造 `companies` 列表，再在缺少时追加 `"临海"`。
- 同步文档说明：查询页“口径”来源于 `/monthly-data-show/query-options`，本次由后端接口兜底补齐。
证据：
- `get_monthly_data_show_query_options()` 原实现直接返回数据库 distinct company。
- 修改后代码包含：`if "临海" not in companies: companies.append("临海")`。
验证：
- 代码检索确认 `backend/projects/monthly_data_show/api/workspace.py` 第 2176-2178 行已存在兜底追加逻辑。
- 未运行自动化测试；本次为小范围接口返回值补充，前端会自动消费 `companies`。