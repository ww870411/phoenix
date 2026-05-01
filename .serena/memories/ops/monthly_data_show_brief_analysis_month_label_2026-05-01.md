# monthly_data_show 简要分析窗口月份化

时间：2026-05-01

## 背景
用户反馈简要分析第一句显示 `2026-01-01 ~ 2026-04-30` 过于具体，月报分析场景应展示月份，如 `2026-01 ~ 2026-04`；单月也应展示 `YYYY-MM`，4 月实际值口径说明仍保留。

## 变更
- `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 新增 `formatAnalysisWindowMonthLabel()`。
  - `analysisInsights` 第一句从直接使用 `comparisonMeta.currentWindowLabel` 改为使用月份化标签。
  - 示例：`2026-01-01 ~ 2026-04-30` -> `2026-01 ~ 2026-04`；`2026-04-01` -> `2026-04`。
- 文档同步：`configs/progress.md`、`frontend/README.md`。

## 影响
仅影响“简要分析”文案；后端窗口字段、导出汇总和表格标签保持原有日期窗口。

## 验证
- `frontend` 目录执行 `npm run build` 通过。