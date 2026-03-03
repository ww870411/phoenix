时间：2026-03-03。
需求：智能体设定弹窗除了“保存并退出”，还需支持“不保存直接退出”。
实现：修改 frontend/src/projects/daily_report_25_26/components/AiAgentSettingsDialog.vue，在 footer 动作区新增“退出（不保存）”按钮，绑定 closeDialog，仅关闭弹窗，不触发保存接口。
影响范围：该组件被日报查询页、月报查询页、管理后台复用，因此三处同步生效。
文档同步：configs/progress.md、frontend/README.md、backend/README.md。