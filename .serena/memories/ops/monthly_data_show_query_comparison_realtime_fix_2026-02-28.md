时间：2026-02-28
问题：同比值明明存在却显示 NULL；环比口径需按上一个等长时期。
处理：
1) 后端新增 /monthly-data-show/query-comparison，按 QueryRequest 实时补查当前/同比/环比三窗口数据。
2) 同比窗口=当前窗口平移一年；环比窗口=前一个等长窗口。
3) 对比维度严格对齐 company+item+period+type+unit，并支持 aggregate_companies。
4) 前端 MonthlyDataShowQueryToolView 改为并行调用 query + query-comparison，不再基于当前页 rows 本地推导同比。
5) 导出 XLSX 的“同比环比对比”sheet 改用后端实时结果。
涉及文件：
- backend/projects/monthly_data_show/api/workspace.py
- frontend/src/projects/daily_report_25_26/services/api.js
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- configs/progress.md
- backend/README.md
- frontend/README.md
验证：python -m py_compile backend/projects/monthly_data_show/api/workspace.py 通过。