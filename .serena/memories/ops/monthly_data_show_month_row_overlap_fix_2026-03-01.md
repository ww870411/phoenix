时间：2026-03-01
问题：月份筛选行输入区与快捷按钮发生叠压重叠。
处理：
- 文件：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- 将 month-input-wrap 从 flex 改为两列 grid（minmax(0,1fr)+auto）
- month-input 改为 width:100% + min-width:0
- month-quick-actions 改为右对齐并设置 min-width:max-content
- 按钮最小宽度从 62 调整为 56
结果：月份输入框与右侧按钮不再重叠，按钮继续横排显示。
留痕：已同步更新 configs/progress.md、frontend/README.md、backend/README.md。