## 2025-11-06 审批页业务日改造
- ApprovalView.vue 默认模式不再传递 'regular'，而是调用 getWorkflowStatus 获取 biz_date 并将其传给 /runtime/spec/eval。
- 目的是让审批页面只受业务日（current_biz_date）控制，展示页继续使用 set_biz_date。
- 文档 progress.md、backend/frontend README 均记录了该行为差异。