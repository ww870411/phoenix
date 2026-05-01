# monthly_data_show 简要分析总体情况顺序调整

时间：2026-05-01

## 背景
用户要求将“业务数据缺失月份”从总体情况句尾移动到“本期窗口”后的括号内，并置于 4 月实际值口径说明之前，同时移除“平均气温不计入业务数据存在性”的显式尾注。

## 变更
- `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - `analysisInsights` 中新增 `windowNotes/windowNoteText` 拼接：先放业务数据缺失月份，再追加 current/yoy/mom 的 4 月取数说明。
  - 总体情况句格式变为：`本期窗口为 YYYY-MM ~ YYYY-MM（业务数据缺失月份：...；本期...；同期...），共纳入 ...。`
- 文档同步：`configs/progress.md`、`frontend/README.md`。

## 验证
- `frontend` 目录执行 `npm run build` 通过。