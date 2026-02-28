时间：2026-02-28
需求：查询页“公司/指标”改为有序勾选；新增层次顺序开关与口径聚合开关。
变更文件：
1) backend/projects/monthly_data_show/api/workspace.py
2) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
3) frontend/src/projects/daily_report_25_26/services/api.js
4) configs/progress.md
5) backend/README.md
6) frontend/README.md
实现摘要：
- 前端：
  - 文案“公司”改为“口径”。
  - 口径/指标改为有序复选列表，支持全选/全不选。
  - 新增开关：orderMode（company_first/item_first）与 aggregateCompanies。
- 后端：
  - QueryRequest 新增 order_mode 与 aggregate_companies。
  - order_mode 控制排序层次。
  - aggregate_companies=true 时按 item/unit/date/period/type/report_month 聚合，company 返回“聚合口径”。
  - 聚合模式下 total 和 summary 按聚合结果计算。
结果：
- 查询页筛选方式和结果层次/聚合行为均符合新需求，且为真实后端生效逻辑。