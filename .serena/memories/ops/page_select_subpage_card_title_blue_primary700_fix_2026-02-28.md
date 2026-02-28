时间：2026-02-28
背景：用户反馈此前将子页面卡片标题色设为 inherit 后，未达到与“请选择功能页面”同蓝色效果。
修改文件：
1) frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现：
- 将 `.page-card-title` 颜色从 `inherit` 改为 `var(--primary-700)`。
结果：
- daily_report_25_26/pages 下“数据看板”“数据展示页面”等卡片大标题与“请选择功能页面”标题蓝色一致。