## 2025-11-07 审批撤销功能上线
- 操作时间：2025-11-07
- 变更文件：backend/api/v1/daily_report_25_26.py、backend/schemas/auth.py、backend/services/auth_manager.py、backend/services/workflow_status.py、backend_data/auth/permissions.json、frontend/src/daily_report_25_26/services/api.js、frontend/src/daily_report_25_26/store/auth.js、frontend/src/daily_report_25_26/pages/PageSelectView.vue、configs/progress.md、backend/README.md、frontend/README.md
- 变更摘要：新增 `can_revoke` 权限与 `/workflow/revoke` 接口，WorkflowStatusManager 增加 `mark_pending` 重置逻辑；权限矩阵为 Global_admin、Group_admin、ZhuChengQu_admin 启用撤销权限。前端同步新增 `revokeWorkflow`、`canRevokeUnit`，审批卡片支持“取消批准”按钮并实时刷新状态。文档与进度记录同步更新。
- 回滚方式：恢复上述文件至改动前版本并移除权限矩阵中的 `can_revoke` 字段即可撤销该功能。