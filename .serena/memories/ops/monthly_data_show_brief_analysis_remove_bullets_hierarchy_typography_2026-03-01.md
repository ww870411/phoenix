时间戳：2026-03-01
任务：简要分析去掉每行圆点，改为更清晰的层次化排版。

变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- 模板：分析区从 ul/li 改为段落容器 + p 行渲染。
- 脚本：新增 analysisLineClass(line)
  - 一级：一、二、三...
  - 二级：口径：/指标：/期间：/类型：
  - 三级：明细正文
- 样式：移除圆点，增加层级缩进与字重区分。

结果：
- 简要分析层级结构更明显，阅读路径更清晰。