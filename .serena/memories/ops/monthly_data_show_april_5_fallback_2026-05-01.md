# monthly_data_show 4月5日优先与4月1日回退

时间：2026-05-01

## 背景
用户反馈开启“改用4月5日”后，如果某年 4 月没有 `YYYY-04-05` 数据但有 `YYYY-04-01` 数据，应回退查询 4 月 1 日。同比场景也需要同样回退，否则上一年度无 4 月 5 日数据时同期值为空。

## 变更
- `backend/projects/monthly_data_show/api/workspace.py`
  - `_iter_current_value_dates()` 在开关开启时为每个 4 月同时加入 `YYYY-04-05` 与 `YYYY-04-01` 候选日期。
  - `_append_current_date_condition()` 增加 SQL guard：同一 `company + item + period + type` 维度存在 `YYYY-04-05` 时排除 `YYYY-04-01`；不存在 `YYYY-04-05` 时保留 `YYYY-04-01`。
  - `_fetch_compare_map()` 的完整性判断改为按月初月份键覆盖，避免强制要求 `04-05` 才认为同比窗口完整。
- 文档同步：`configs/progress.md`、`frontend/README.md`、`backend/README.md`。

## 效果
开启“改用4月5日”后，4 月本期值、同比值、环比值均执行：优先 `YYYY-04-05`，缺失则回退 `YYYY-04-01`。计划值逻辑仍不受影响。

## 验证
- `python -m py_compile backend\projects\monthly_data_show\api\workspace.py` 通过。
- `frontend` 目录执行 `npm run build` 通过。