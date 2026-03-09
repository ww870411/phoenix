时间：2026-03-08
用户要求：仅修复“日志展示范围”，不要改日志采集。

问题根因：
- frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue 中日志区块使用 v-else，且该节点处于与 files/database/project 不同的条件链。
- 在 temperatureImportDialogVisible=false 且 activeTab!=system 时，日志区块会被误渲染到其他页签。

修复：
- 将日志区块条件改为 v-else-if="activeTab === 'audit'"，实现仅“操作日志”页签显示。

变更文件：
1) frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

结果：
- 仅展示逻辑修复；日志采集逻辑保持不变。