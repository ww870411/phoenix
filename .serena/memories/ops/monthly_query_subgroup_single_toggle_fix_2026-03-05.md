时间：2026-03-05
反馈：子分类指标按钮仍为双按钮。

修复：
- 文件：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- 基础指标子分类按钮改为单按钮“全选/取消”切换：
  - 使用 isSectionItemsAllSelected(group.items) 判断文案
  - 点击调用 toggleSectionItems(group.items)

验证：
- frontend 执行 npm run build 通过

文档同步：
- configs/progress.md
- frontend/README.md
- backend/README.md