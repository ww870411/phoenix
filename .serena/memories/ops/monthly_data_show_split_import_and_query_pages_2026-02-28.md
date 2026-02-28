时间：2026-02-28
主题：monthly_data_show 拆分为导入/查询双子页面并按页授权

用户要求：
- 子页面1：月报导入工作台（Global_admin）
- 子页面2：月报数据查询工具（Global_admin + Group_admin）

实现：
1) 项目页面配置
- backend_data/shared/项目列表.json
  - monthly_data_show.pages 改为两个绝对路径键：
    - /projects/monthly_data_show/import-workspace
    - /projects/monthly_data_show/query-tool
2) 权限配置
- backend_data/shared/auth/permissions.json
  - Global_admin.monthly_data_show.page_access:
    - projects_monthly_data_show_import_workspace
    - projects_monthly_data_show_query_tool
  - Group_admin.monthly_data_show.page_access:
    - projects_monthly_data_show_query_tool
3) 前端路由
- frontend/src/router/index.js
  - 新增导入页路由 /projects/monthly_data_show/import-workspace
  - 新增查询页路由 /projects/monthly_data_show/query-tool
4) 页面与入口
- 导入页标题改为“月报导入工作台”
- 新增查询页组件 MonthlyDataShowQueryToolView.vue（查询工具占位）
- ProjectSelectView 移除 monthly_data_show 直达入口
- ProjectEntryView 移除 monthly_data_show 直达映射，统一走 /pages 子页面选择

留痕：
- configs/progress.md
- backend/README.md
- frontend/README.md