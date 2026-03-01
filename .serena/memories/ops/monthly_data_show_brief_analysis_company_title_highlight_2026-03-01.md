时间戳：2026-03-01
任务：简要分析中强化“口径”层级视觉（更大、更粗、标色）。

变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- analysisLineClass 增加口径专属类：level-2 company-title。
- 新增 company-title 样式：
  - 14px 字号
  - 700 字重
  - 左侧强调线
  - 浅蓝背景
  - 深蓝文字

结果：
- 各口径标题在简要分析中更醒目，层次辨识提升。