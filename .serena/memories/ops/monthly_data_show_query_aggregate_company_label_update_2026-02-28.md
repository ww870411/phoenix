时间：2026-02-28
需求：将聚合口径开关第一项文案改为“不聚合口径（逐口径列出）”。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现：
- 调整 aggregateCompanies=false 分支的显示文案。
结果：
- 页面文案与用户指定一致。