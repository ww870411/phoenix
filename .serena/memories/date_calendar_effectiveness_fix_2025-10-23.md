时间：2025-10-23
主题：修复数据填报页日历修改未生效（标准表列头日期未随 biz_date 更新）
变更摘要：
- 根因：后端标准表 `_flatten_records` 以列头日期文本作为每列 `date`，而前端仅在模板初次加载时对 `(本期日)/(同期日)` 占位符做了一次替换，导致用户通过日历修改 `biz_date` 后，列头未重算，提交仍使用旧日期。
- 方案：在 `frontend/src/daily_report_25_26/pages/DataEntryView.vue` 新增 `baseColumns` 缓存未替换的原始列头；监听 `bizDate` 变更，使用 `replaceDatePlaceholdersInColumns` 重新计算列头并更新 `columns` 与 `gridColumns.name`，确保 UI 展示与提交 payload 一致。
- 影响范围：仅前端渲染与提交；后端接口与数据结构不变。煤炭库存表依旧使用顶层 `biz_date`。
证据：
- 后端取值逻辑：`backend/api/v1/daily_report_25_26.py` 中 `_flatten_records` 的 `date = columns[col_index]`；煤炭库存 `_parse_coal_inventory_records` / `_flatten_records_for_coal` 使用 `payload['biz_date']`。
- 前端修复涉及：`DataEntryView.vue` 新增 `baseColumns` 与 `watch(bizDate)`，初次加载缓存原始列头并基于该缓存重算。
文件清单：
- 修改：frontend/src/daily_report_25_26/pages/DataEntryView.vue
- 更新：configs/progress.md；frontend/README.md；backend/README.md
回滚：删除 `baseColumns` 与 `watch(bizDate)` 代码块，并恢复仅在加载时替换列头。