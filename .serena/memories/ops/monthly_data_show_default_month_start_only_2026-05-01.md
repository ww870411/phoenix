# monthly_data_show 默认多月实际值只取月初

时间：2026-05-01

## 背景
用户查询 `2026-03 ~ 2026-04` 且未勾选“改用4月5日”时，仍查出了 `2026-04-05` 数据。根因是前端多月区间会提交 `date_from=2026-03-01`、`date_to=2026-04-30`，后端未勾选时仍使用范围条件，导致 4 月 5 日落入查询范围。

## 变更
- `backend/projects/monthly_data_show/api/workspace.py`
  - `_append_current_date_condition()` 对包含 `type=real` 的查询统一使用逐月目标日期集合。
  - 未勾选 `use_april_5_for_current` 时，目标日期仅为各月 `YYYY-MM-01`。
  - 勾选时才启用 4 月 `04-05` 优先、缺失回退 `04-01`。
  - 若请求混合非 `real` 类型，非实际值分支仍使用原日期范围；当前查询页固定 `types=['real']`。
- 文档同步：`configs/progress.md`、`backend/README.md`。

## 效果
未勾选时，`2026-03 ~ 2026-04` 只查 `2026-03-01` 和 `2026-04-01`；若 `2026-04-01` 不存在，不会自动查 `2026-04-05`。

## 验证
- `python -m py_compile backend\projects\monthly_data_show\api\workspace.py` 通过。
- `frontend` 目录执行 `npm run build` 通过。