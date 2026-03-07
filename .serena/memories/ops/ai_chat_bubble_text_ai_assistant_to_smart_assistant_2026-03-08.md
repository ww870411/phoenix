时间戳：2026-03-08（Asia/Hong_Kong）
任务：将 AI 气泡组件显示文字“AI 助手”改为“智能助手”。
变更文件：frontend/src/projects/daily_report_25_26/components/AiChatWorkspace.vue。
改动摘要：替换 `.ai-chat-floating__launcher-text` 的静态文案，不涉及事件、权限、接口或状态逻辑。
验证证据：组件模板中已为“智能助手”。
文档留痕：已追加更新 configs/progress.md、frontend/README.md、backend/README.md。
降级说明：使用 apply_patch 对 .vue 模板做单行精确替换。
回滚方式：将该行文案恢复为“AI 助手”。