时间：2026-04-09
任务：从 monthly_data_show/query-tool 页面“口径（可多选）”中移除“临海”。
来源定位：`临海` 并非前端写死，而是后端 `get_monthly_data_show_query_options()` 在数据库口径列表之外额外兜底追加。
实现文件：
- backend/projects/monthly_data_show/api/workspace.py
- configs/progress.md
- frontend/README.md
- backend/README.md
实现摘要：
- 删除 `get_monthly_data_show_query_options()` 中：
  - `if "临海" not in companies: companies.append("临海")`
- 现在查询页口径列表仅返回数据库中实际存在的口径。
验证：
- `py_compile` 编译 `backend/projects/monthly_data_show/api/workspace.py` 通过。
- `frontend` 目录执行 `npm run build` 通过。
降级说明：涉及 `.py` 之外还包含 `.md` 文件编辑，按 AGENTS 约定使用 `apply_patch` 修改并补写本记忆条目。