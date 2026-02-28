时间：2026-02-28
主题：monthly_data_show 新增“源字段”复选提取

用户反馈：步骤2除口径和字段外，还需控制是否提取“本年计划/本月计划/本月实际/上年同期”。

实现内容：
1) 后端接口
- backend/projects/monthly_data_show/api/workspace.py
  - inspect 返回 source_columns + default_selected_source_columns
  - extract-csv 支持 source_columns 表单参数
2) 后端提取逻辑
- backend/projects/monthly_data_show/services/extractor.py
  - extract_rows 增加 selected_source_columns 参数
  - 仅提取已勾选源字段
3) 前端页面
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
  - 步骤2新增源字段复选区与全选/全不选
  - 提取按钮增加“必须选择至少1个源字段”限制
4) 前端 API
- frontend/src/projects/daily_report_25_26/services/api.js
  - extractMonthlyDataShowCsv 新增 sourceColumns 参数

留痕：
- configs/progress.md
- backend/README.md
- frontend/README.md