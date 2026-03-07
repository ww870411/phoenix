时间：2026-03-08
问题：用户反馈在智能体设定中关闭“显示 AI 聊天气泡”后，保存仍显示。

结论：
- 后端持久化链路正常（ai_settings.json 中 show_chat_bubble 可为 false）。
- 根因在前端页面状态未即时同步：保存后未将返回值回写到当前页用于 v-if 的状态对象。

改动文件：
1) frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue
2) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
3) configs/progress.md
4) frontend/README.md
5) backend/README.md

修复内容：
- 两个页面的 saveAiSettingsPayload 改为 async。
- 保存成功后读取接口返回 saved.show_chat_bubble，并分别回写：
  - 日报页：schema.ai_report_flags.show_chat_bubble
  - 月报页：options.aiChatFlags.show_chat_bubble

效果：
- 不刷新页面即可即时隐藏/显示 AI 聊天气泡。

风险与回滚：
- 仅前端状态同步逻辑修改，风险低。
- 回滚方式：回退两处 saveAiSettingsPayload 改动即可恢复旧行为。