时间：2026-03-01
范围：monthly_data_show 查询页视觉微调
文件：
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

变更摘要：
1) 日期快捷按钮横排样式加固，避免被全局样式覆盖：
   - month-quick-actions .btn 增加 writing-mode: horizontal-tb !important
   - month-quick-actions .btn 增加 white-space: nowrap !important
   - 增加 text-orientation: mixed
   - 增加 inline-flex + 居中对齐
2) 筛选标题 panel-title 轻量强化：字号提升至 14px（保留加粗与高对比色）
3) 文案与结构确认：
   - “同起始月”文案已生效
   - “重置默认”按钮已移除
4) 联动留痕：同步更新 progress.md、frontend/README.md、backend/README.md。