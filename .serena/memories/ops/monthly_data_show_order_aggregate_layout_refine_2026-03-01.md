时间戳：2026-03-01
任务：优化“数据层次顺序”与“聚合开关”框体布局。

变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- 模板结构：
  - 容器从 inline-four 改为 inline-layout。
  - 左栏 order-col（数据层次顺序），右栏 aggregate-col（聚合开关）。
  - 聚合开关项增加 aggregate-switch 样式类。
- 样式策略：
  - 桌面端双栏：左宽右窄（minmax 配置）。
  - <=900px 保持双栏并排。
  - <=640px 单栏堆叠。

结果：
- 层次顺序与聚合区域对齐更清晰，布局更稳定。