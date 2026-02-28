时间：2026-02-28
需求：口径（可多选）内部内容更紧凑。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现：
- 口径列表容器加类名 company-list。
- 调整 company-list：列宽160、间距/内边距缩小、条目最小高度降低。
结果：
- 口径区更紧凑，指标区保持原样。