时间：2026-03-01
主题：发电水耗率/供热水耗率公式修订

用户确认新公式：
1) 发电水耗率=(耗水量-供汽量-热网耗水量)*(1-热分摊比)/发电量
2) 供热水耗率=((耗水量-供汽量-热网耗水量)*热分摊比+供汽量+热网耗水量)/供热量

改动文件：
1) backend/projects/monthly_data_show/api/workspace.py
2) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
3) configs/progress.md
4) backend/README.md
5) frontend/README.md

实现摘要：
- 后端计算公式已替换为新口径；
- CALCULATED_DEPENDENCY_MAP 中两指标依赖新增 热网耗水量；
- 前端“查看公式”弹窗文案同步更新。

结果：
- 页面展示的公式说明与后端实时计算口径一致。