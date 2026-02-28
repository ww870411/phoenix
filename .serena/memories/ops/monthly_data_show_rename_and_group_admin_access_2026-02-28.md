时间：2026-02-28
主题：monthly_data_show 项目名称调整与 Group_admin 授权

用户需求：
- 项目名称改为“月报导入与查询”
- 访问权限调整为 Global_admin 和 Group_admin 可访问

已修改：
1) backend_data/shared/项目列表.json
- monthly_data_show.project_name: 月报入库工作台 -> 月报导入与查询
- monthly_data_show.availability: [Global_admin] -> [Global_admin, Group_admin]
- workspace 页面名称: 月报入库主页 -> 月报导入与查询主页

2) backend_data/shared/auth/permissions.json
- Group_admin.projects 新增 monthly_data_show
- page_access: ["workspace"]，actions 与现有非审批类项目一致

3) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
- 页面标题与面包屑文案同步为“月报导入与查询”

留痕文件：
- configs/progress.md
- backend/README.md
- frontend/README.md