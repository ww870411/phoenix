# monthly_data_show 简要分析4月口径标注

时间：2026-05-01

## 背景
用户反馈查询结果“简要分析”第一句仅显示原始本期窗口（如 `2026-04-01`），但开启“改用4月5日”后实际取数可能使用 `04-05`，同期也可能因无 `04-05` 回退 `04-01`，需要在分析文本中标注。

## 变更
- `backend/projects/monthly_data_show/api/workspace.py`
  - `QueryComparisonResponse` 新增 `current_value_date_note`、`yoy_value_date_note`、`mom_value_date_note`。
  - 新增 `_build_april_value_date_note()`，按当前/同期/环比窗口分别判断 4 月实际值口径。
  - 标注规则：全部命中 `04-05` -> “实际值使用04-05”；全部缺失 `04-05` 但命中 `04-01` -> “未命中04-05，回退使用04-01”；部分维度混用 -> “部分实际值使用04-05，缺失维度回退04-01”。
- `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - `comparisonMeta` 接收三段 note。
  - `analysisInsights` 第一句在“本期窗口为 ……”后追加括号说明。
- 文档同步：`configs/progress.md`、`frontend/README.md`、`backend/README.md`。

## 验证
- `python -m py_compile backend\projects\monthly_data_show\api\workspace.py` 通过。
- `frontend` 目录执行 `npm run build` 通过。