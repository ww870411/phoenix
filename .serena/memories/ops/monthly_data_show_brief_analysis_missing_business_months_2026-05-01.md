# monthly_data_show 简要分析业务数据缺失月份标注

时间：2026-05-01

## 背景
用户查询 `2026-03 ~ 2026-05` 时，4 月仅有平均气温、5 月没有数据，但简要分析仍显示整个窗口并给出 46 条对比序列。用户要求标注 4、5 月业务数据不存在，且仅有气温不能算业务数据存在。

## 变更
- `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 新增 `listSelectedMonthTags()`：从筛选起止月份生成应覆盖月份。
  - 新增 `resolveMissingBusinessMonthTags()`：从 `rows.value` 中提取非 `AVERAGE_TEMPERATURE_ITEM` 的业务数据月份，并与应覆盖月份做差集。
  - `analysisInsights` 第一句追加“业务数据缺失月份：YYYY-MM、YYYY-MM（平均气温不计入业务数据存在性）”。
  - 聚合期间月份模式下不做缺失月份判断，避免结果日期为空造成误报。
- 文档同步：`configs/progress.md`、`frontend/README.md`。

## 验证
- `frontend` 目录执行 `npm run build` 通过。