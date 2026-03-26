日期：2026-03-26
主题：daily_report_25_26 数据分析页累计模式 62 天区间上限排查

结论：
1. 用户反馈“只能查询最大 62 天区间的数据”属实。
2. 该现象不是前端日期控件限制，也不是数据库只能返回 62 天，而是后端接口显式拒绝超过 62 天的累计区间。
3. 当前页面前端不会预先拦截 62 天以上范围，只会把 `start_date/end_date` 原样提交给后端，并把后端报错展示给用户。

证据：
- `backend/services/data_analysis.py` 定义 `MAX_TIMELINE_DAYS = 62`。
- `backend/projects/daily_report_25_26/api/legacy_full.py` 在累计模式下执行 `range_days = (end_date - start_date).days + 1`，若 `range_days > MAX_TIMELINE_DAYS`，返回 400，提示“累计模式暂只支持 62 天内的区间，请缩小日期范围”。
- `backend/services/data_analysis.py` 的 `_query_analysis_timeline(...)` 按天循环：`while current <= end_date`，且每一天都 `with SessionLocal() as session` 并重新查询一次视图，说明区间放大时查询成本线性上升，这也是设置保护阈值的直接工程原因。
- `frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue` 中 `runAnalysis()` 构造 `requestBase` 时直接提交 `analysis_mode/start_date/end_date`；日期输入为普通 `<input type="date">`，未看到 62 天禁选逻辑。

影响范围：
- 页面：`/projects/daily_report_25_26/pages/data_analysis/data-analysis`
- 模式：累计模式（`analysis_mode = range`）
- 口径：包含首尾日期，允许最大 62 个自然日；第 63 天起后端拒绝。

文档同步：
- `configs/progress.md`
- `frontend/README.md`
- `backend/README.md`

补充：
- 本次未改业务代码，只做定位、确认与文档留痕。
- 若后续要放宽限制，不能只改常量，还需要先处理逐日 timeline 查询的线性放大问题，否则长区间性能风险很高。