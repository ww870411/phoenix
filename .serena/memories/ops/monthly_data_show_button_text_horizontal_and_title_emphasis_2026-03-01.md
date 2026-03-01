时间戳：2026-03-01
任务：修复日期按钮竖排问题、更新同起始月文案、增强筛选标题显眼度并移除重置默认按钮。

变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- 日期快捷按钮：
  - month-quick-actions .btn + .btn.ghost 增加 writing-mode: horizontal-tb 与 nowrap。
- 文案调整：
  - “同起月”改为“同起始月”。
- 标题强化：
  - 新增 panel-title 样式并应用到口径/指标/数据层次顺序/聚合开关。
- 交互简化：
  - 移除“重置默认”按钮及对应函数。

结果：
- 按钮文本恢复横排且可读；标题更醒目；控件区更简洁。