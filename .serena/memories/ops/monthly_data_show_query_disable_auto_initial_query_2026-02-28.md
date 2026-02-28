时间：2026-02-28
反馈：查询页进入后默认显示结果，不符合预期。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现：
- 页面 onMounted 仅加载筛选项，不再自动 runQuery。
- 新增 hasSearched 状态控制首屏显示。
- 未查询前显示提示文案“请先设置筛选条件并点击查询”。
- 重置筛选时清空结果，不自动查询。
结果：
- 页面初始状态不再自动返回任何查询结果。