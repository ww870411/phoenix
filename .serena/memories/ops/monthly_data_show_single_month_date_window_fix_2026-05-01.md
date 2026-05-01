# monthly_data_show 单月查询 date 窗口修正

时间：2026-05-01

## 背景
用户确认生产月报标准表 `monthly_data_show` 的月度合计数据记录在 `date=YYYY-MM-01`，原查询页单月选择会提交 `date_from=YYYY-MM-01`、`date_to=YYYY-MM-月末`，导致同月其他日期的零散数据也被纳入查询窗口。

## 变更
- `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - `buildPayload()` 在未选择“业务月份止”时，将 `normalizedDateTo` 从当月月末改为 `normalizedDateFrom`。
  - 单月查询现在提交 `date_from=date_to=YYYY-MM-01`。
  - 显式选择“业务月份止”时仍保留起始月 1 日至截止月月末的区间查询语义。
- `configs/progress.md`、`frontend/README.md`、`backend/README.md` 已同步记录口径变更。

## 验证
- Serena 检索确认 `runQuery()`、导出全量、AI 上下文、`queryMonthlyDataShowComparison()` 共用 `buildPayload()`。
- 在 `frontend` 目录执行 `npm run build` 通过，Vite 构建成功。

## 回滚
将 `buildPayload()` 中 `if (normalizedDateFrom) return normalizedDateFrom` 恢复为 `return toMonthEndDate(filters.dateMonthFrom)`，并删除对应文档条目。