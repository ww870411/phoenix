时间：2025-10-25
事项：按用户要求移除前端所有调试输出（console 与 alert），不改变功能。
文件清单：
- frontend/src/daily_report_25_26/pages/DataEntryView.vue
- frontend/src/daily_report_25_26/pages/PageSelectView.vue
- frontend/src/daily_report_25_26/pages/Sheets.vue
- frontend/src/daily_report_25_26/services/api.js
操作摘要：
- 删除 console.log/info/debug/warn/error/group 等全部调试输出。
- 删除所有 alert/window.alert 调试弹窗（含 request_id/attatch_time 提示）。
- 保留核心业务逻辑与渲染流程（rows-only）。
验证：
- Serena 全局检索 `console.|alert(`（frontend 范围）返回空结果。
偏差/降级：
- 无需降级；使用 Serena 搜索定位，apply_patch 精准编辑。
回滚策略：
- 若需排障，可在本地分支恢复必要 console.error，但不合入主干。