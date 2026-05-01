# monthly_data_show 4月5日本期值查询开关

时间：2026-05-01

## 背景
生产月报 4 月存在两类统计记录：`YYYY-04-05` 表示供暖期结束时 1-5 日数据，`YYYY-04-01` 表示月底 1-30 日全月数据。用户需要在查询 25-26 供暖期等窗口时，将 4 月本期实际值切换到 `YYYY-04-05`。

## 变更
- `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 在“业务月份止（非必选）”后新增“改用4月5日”复选项。
  - `filters` 新增 `useApril5ForCurrent`，默认 `false`，重置时恢复关闭。
  - `buildPayload()` 新增 `use_april_5_for_current` 字段。
- `backend/projects/monthly_data_show/api/workspace.py`
  - `QueryRequest` 新增 `use_april_5_for_current: bool = False`。
  - 新增 `_iter_current_value_dates()`、`_append_current_date_condition()` 等辅助函数。
  - 主查询 `_build_query_sql_parts()` 在开关开启且包含 `type=real` 时，用逐月目标日期集合过滤实际值：4 月为 `YYYY-04-05`，其他月为 `YYYY-MM-01`。
  - 同比环比实际值 `_fetch_compare_map()` 使用同一日期集合，并用该集合判断月度覆盖完整性。
  - 计划值 `_fetch_plan_value_map()` 与年度计划取数未接入开关，`type=plan` 保持原日期窗口。
- 文档同步：`configs/progress.md`、`frontend/README.md`、`backend/README.md`。

## 示例
选择 `2025-11` 至 `2026-04` 且勾选开关时，本期实际值目标日期为：`2025-11-01`、`2025-12-01`、`2026-01-01`、`2026-02-01`、`2026-03-01`、`2026-04-05`。

## 验证
- `python -m py_compile backend\projects\monthly_data_show\api\workspace.py` 通过。
- `frontend` 目录执行 `npm run build` 通过。

## 回滚
移除前端开关和 payload 字段，删除后端 `use_april_5_for_current` 字段及日期集合过滤辅助函数，恢复 `_build_query_sql_parts()` 与 `_fetch_compare_map()` 的默认日期范围过滤。