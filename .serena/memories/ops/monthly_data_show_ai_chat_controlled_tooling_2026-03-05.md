时间：2026-03-05
任务：为 monthly_data_show/query-tool 增加“可对话查询”能力，支持 AI 根据用户意图调用受控查询工具并返回结果解释。

实现摘要：
1) 后端新增对话接口
- 文件：backend/projects/monthly_data_show/api/workspace.py
- 新增路由：POST /api/v1/projects/monthly_data_show/monthly-data-show/ai-chat/query
- 新增模型：MonthlyAiChatRequest/MonthlyAiChatResponse/MonthlyAiChatToolCall
- 新增能力：
  - 自然语言中提取月份（YYYY-MM / YYYY年M月）
  - 从问题文本匹配口径/指标（基于 query-options 候选集）
  - 与前端 context（QueryRequest）合并形成最终查询参数
  - 工具路由：普通查询(query_month_data_show) 与对比查询(query_month_data_show_comparison)
  - 使用 data_analysis_ai_report._call_model 生成中文分析结论；失败时兜底文本
- 返回字段：answer/tool_calls/preview_rows/applied_query

2) 前端接入对话面板
- 文件：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- 新增“对话查询助手（BETA）”区块（消息流、输入框、发送按钮、错误提示、预览表格）
- 新增 sendChatMessage，调用新接口并携带当前筛选上下文（buildChatContextPayload）

3) 前端 API 封装
- 文件：frontend/src/projects/daily_report_25_26/services/api.js
- 新增 queryMonthlyDataShowAiChat(projectKey, payload)

验证：
- python -m py_compile backend/projects/monthly_data_show/api/workspace.py 通过
- frontend 执行 npm run build 通过

文档同步：
- configs/progress.md
- frontend/README.md
- backend/README.md

偏差/降级留痕：
- Serena 对 .vue 符号解析不可用（当前仅 Python），前端页面改动使用 apply_patch 降级执行。影响范围仅 monthly_data_show 查询页与共享 API，不影响既有日报主链。回滚可按文件级撤销本次新增区块。