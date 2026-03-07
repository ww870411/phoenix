时间：2026-03-08
任务：完善 AI 自由对话气泡并修复缺陷
触发来源：用户反馈“完善并解决一些BUG”

改动文件：
1) frontend/src/projects/daily_report_25_26/components/AiChatWorkspace.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

变更摘要：
- 修复 AiChatWorkspace 未消费父层文案 props 的问题，新增并启用 freeDescription/queryDescription/freePlaceholder/queryPlaceholder。
- 修复 Enter/Shift+Enter 行为：Enter 发送，Shift+Enter 换行。
- 修复 query_context 模式下 buildQueryContext 抛错无提示问题，新增异常兜底提示“构建查询上下文失败：...”。
- 修复消息内容多行与长词显示，新增 white-space: pre-wrap 与 word-break: break-word。
- 同步更新进度与前后端 README 留痕。

验证证据：
- 关键检索命中：
  - 模板使用新 props（line 46, 78）
  - defineProps 已新增 4 个参数（line 106-109）
  - handleEnter 已改为 preventDefault + send（line 155-159）
  - 上下文异常提示已落位（line 173）
  - 消息内容样式规则已落位（line 268）

风险与回滚：
- 风险较低，仅前端组件行为与文案消费变更，不涉及接口契约。
- 回滚方式：仅回退 AiChatWorkspace.vue 本次变更即可恢复旧行为。