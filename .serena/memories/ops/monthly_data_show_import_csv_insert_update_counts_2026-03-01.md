时间：2026-03-01
问题：用户反馈第四步入库似乎未写库。
诊断：import-csv 为 UPSERT（同主键覆盖更新），容易被误判为“没入库”。
改动：
1) backend/projects/monthly_data_show/api/workspace.py
- ImportCsvResponse 增加 inserted_rows、updated_rows
- UPSERT SQL 增加 RETURNING (xmax = 0) AS inserted
- 统计新增/更新条数并返回
2) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
- 入库成功文案增加“新增/更新”统计
留痕：configs/progress.md、backend/README.md、frontend/README.md 已更新。
验证：python -m py_compile backend/projects/monthly_data_show/api/workspace.py 通过。