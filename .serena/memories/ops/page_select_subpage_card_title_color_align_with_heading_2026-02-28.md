时间：2026-02-28
需求：项目子页面卡片大标题颜色需与“请选择功能页面”标题颜色一致。
修改文件：
1) frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现：
- 将 `.page-card-title` 的颜色从固定变量改为 `color: inherit`，使其继承与页面标题一致的色系。
结果：
- 各项目子页面卡片大标题颜色统一，与页面主标题视觉一致。