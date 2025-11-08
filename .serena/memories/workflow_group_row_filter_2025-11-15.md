## 2025-11-15 审批进度过滤集团行
- 修改 `frontend/src/daily_report_25_26/pages/PageSelectView.vue`，`workflowUnits` 计算属性新增黑名单集合 `{ '系统管理员', 'Group' }`，避免集团本身出现在审批列表。
- 背景：Group 行不需要审批，显示会误导操作；现在仅会显示实际单位，权限判断不受影响。
- 回滚方式：去除该黑名单即可恢复原列表。