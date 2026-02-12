时间：2026-02-12
用户诉求：
1) mini看板气温图不要用xlsx中的气温，改为与daily_report_25_26同路径（数据库calc_temperature_data链路）；
2) 前四张卡片补齐主看板同风格底色。

变更文件：
- frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

关键实现：
- mini看板气温解析增强：
  - 新增 resolveDashboardSections/resolveTemperatureSection/buildSectionIndexMap；
  - 支持 data.sections、sections、data 三种返回结构；
  - 支持 '1'、'1.逐小时气温'、'逐小时气温'、'calc_temperature_data' 多键名回退；
  - buildDailyAverageMap 支持数组/数值/对象(avg|average|value)值形态；
  - 同期日期映射到本年并做缺口回补。
- mini摘要卡片样式：
  - 前四卡片应用 summary-card--primary/warning/danger；
  - 添加渐变背景、白色文字与阴影。

结果：
- mini看板气温数据来源逻辑对齐主看板，减少因返回结构差异导致的空图。
- 顶部摘要卡片视觉层级与主看板风格一致。