时间：2026-03-05
任务：将 monthly_data_show/query-tool 对话助手升级为连续会话 + 数据处理 + 联网检索。

前置说明：
- 已执行 serena__activate_project 与 serena__check_onboarding_performed；
- Python 主逻辑优先使用 Serena 符号编辑；
- .vue 与 markdown 文档采用 apply_patch 降级（Serena 对该类文件无稳定符号编辑）。

变更文件：
1) backend/projects/monthly_data_show/api/workspace.py
- 扩展 MonthlyAiChatRequest/Response/ToolCall 模型：session_id、enable_web_search、web_sources、tool_calls.details；
- 新增会话管理函数（TTL=30min，max turns=20）：_chat_get_or_create_session/_chat_get_session_history/_chat_append_session_history 等；
- 新增数据处理函数：_chat_summarize_rows（数值字段统计、公司摘要、TopN）；
- 新增联网检索函数：_chat_execute_web_search（公开接口检索并去重）；
- 重写 chat_monthly_data_show_query：根据意图分流 query/comparison/web-search，并回写会话上下文。

2) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- 新增 chatSessionId/chatWebSources；
- 发送时携带 session_id 与 enable_web_search；
- 新增 resetChatConversation（新会话按钮）；
- 新增当前会话ID与联网来源列表展示。

3) configs/progress.md
4) frontend/README.md
5) backend/README.md
- 同步记录本轮实现、降级原因、验证结果与风险。

验证证据：
- python -m py_compile backend/projects/monthly_data_show/api/workspace.py => 通过；
- npm run build (frontend) => 通过。