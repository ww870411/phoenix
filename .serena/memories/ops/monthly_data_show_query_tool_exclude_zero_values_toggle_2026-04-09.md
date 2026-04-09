时间：2026-04-09
任务：为 monthly_data_show/query-tool 新增“去除0值”开关，并让列表、分页、导出、同比环比统一按零值过滤规则生效。
触发背景：用户要求在“数据层次顺序”“聚合开关”右侧新增小板块，控制是否剔除值等于 0 的指标，包括 0、0.0、0% 等零值形式。
关键变更：
1. 前端文件 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
   - 在 `.inline-layout` 中新增“0值过滤”板块。
   - `filters` 新增 `excludeZeroValues`。
   - `buildPayload()` 新增 `exclude_zero_values` 请求字段。
   - `resetFilters()` 新增该字段重置。
   - `.inline-layout` 从双列扩展为三列，并让新面板参与同排布局。
2. 后端文件 `backend/projects/monthly_data_show/api/workspace.py`
   - `QueryRequest` 新增 `exclude_zero_values: bool = False`。
   - 新增 `_is_effective_zero_value()`，基于 `_to_optional_float()` 统一识别零值。
   - `query_month_data_show()` 在排序/分页前过滤 `value == 0` 的结果行。
   - `query_month_data_show_comparison()` 在比较行生成后过滤 `current_value == 0` 的指标行。
3. 文档同步：
   - `configs/progress.md`
   - `frontend/README.md`
   - `backend/README.md`
降级说明：本轮涉及 `.vue` 与 `.md` 文件编辑，Serena 对这类文件的结构化编辑支持不足，因此按仓库 AGENTS 约定降级使用 `apply_patch` 修改文件，并补写本记忆条目留痕。
验证结果：
- `python -c "import py_compile; py_compile.compile(r'D:\编程项目\phoenix\backend\projects\monthly_data_show\api\workspace.py', doraise=True)"` 通过。
- `frontend` 目录执行 `npm run build` 通过。
影响说明：当用户勾选“已剔除 0 值”后，月报查询页主列表和同比环比对比结果都会统一隐藏当前值为 0 的指标；前端导出继续复用同一查询 payload，因此导出结果也会同步过滤。