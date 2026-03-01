时间戳：2026-03-01
任务：简要分析中每个指标名前加小圆点，比较描述前空两格。

变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- 指标层输出改为 `•指标名`。
- 比较描述行增加两个前导空格。
- 新增样式支持：
  - analysisLineClass 增加 item-title 分层识别。
  - insight-line 使用 white-space: pre-wrap，保留缩进空格。
  - item-title 加粗显示。

结果：
- 指标标题与描述结构更明显，阅读层次更清晰。