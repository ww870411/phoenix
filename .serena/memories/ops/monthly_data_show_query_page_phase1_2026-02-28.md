时间：2026-02-28
目标：构建“月报数据查询工具”可用版本。
变更文件：
1) backend/projects/monthly_data_show/api/workspace.py
2) frontend/src/projects/daily_report_25_26/services/api.js
3) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
4) configs/progress.md
5) backend/README.md
6) frontend/README.md
实现摘要：
- 后端新增查询接口：
  - GET /monthly-data-show/query-options（返回 companies/items/periods/types）
  - POST /monthly-data-show/query（支持 report_month/date 区间 + 维度筛选 + limit/offset）
  - 返回 rows/total/summary，summary 含 total_rows/value_non_null_rows/value_null_rows/value_sum。
- 前端 API 新增 query-options/query 调用。
- 查询页从占位升级为可用：
  - 筛选区（时间区间 + 多选维度）
  - 汇总卡片
  - 结果表格 + 分页。
结果：
- 月报入库后可在查询页直接筛选与查看基础统计，形成“导入-入库-查询”闭环。