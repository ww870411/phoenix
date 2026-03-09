时间：2026-03-08
任务：将系统后台操作日志采集/呈现范围收敛到“操作日志”页签，移除其他子页面的日志记录。

前置说明（偏差/降级）：
- 已执行 Serena 项目激活与 onboarding 检查。
- Serena 当前仅支持 Python 语义符号能力，无法对 Vue 文件执行符号级编辑（报错：Cannot extract symbols from .vue）。
- 根据仓库 AGENTS 3.9 降级矩阵，降级使用 apply_patch 对目标文件进行最小修改。

变更文件清单：
1) frontend/src/main.js
2) frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue
3) configs/progress.md
4) frontend/README.md
5) backend/README.md

变更摘要：
- main.js：移除全局 initAuditTracking 初始化，避免应用级全局采集。
- AdminConsoleView.vue：新增按页签启停逻辑 syncAuditTrackingByTab，仅 activeTab==='audit' 时 initAuditTracking；离开页签或组件卸载时 stopAuditTracking。
- 文档同步：按规范更新 progress 与前后端 README，记录原因、影响、回滚与验证建议。

影响范围：
- 前端管理后台日志采集范围从“全局页面”变为“仅操作日志页签”。
- 后端接口与服务无改动。

回滚思路：
- 方案A：恢复 main.js 中全局 initAuditTracking 调用。
- 方案B：移除 AdminConsoleView.vue 新增的按页签启停逻辑。

验证建议：
- 在非 audit 页签操作时，日志列表不新增对应行为；
- 切换到 audit 页签后操作，可见新增日志。