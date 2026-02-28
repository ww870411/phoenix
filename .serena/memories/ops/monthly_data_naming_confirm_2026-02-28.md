时间：2026-02-28
主题：月报项目中文命名确认

用户确认：
1) monthly_data_pull 对应中文名：月报拉取工作台
2) 新项目 monthly_data_show 对应中文名：月报入库工作台

已落地改动：
- backend_data/shared/项目列表.json
  - monthly_data_pull.project_name: 月报导表工作台 -> 月报拉取工作台
  - monthly_data_pull.pages.workspace.页面名称: 月报导表主页 -> 月报拉取主页
- frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue
  - 页面标题和面包屑文案统一改为：月报拉取工作台
- 文档留痕：
  - configs/progress.md 新增“项目中文名确认”记录
  - backend/README.md、frontend/README.md 新增结构同步条目

约束：
- monthly_data_show 尚未创建，本轮仅确认名称并记录为后续创建时的固定命名。