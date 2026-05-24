时间：2026-05-24
主题：在需求方管理页面新增站点提交按钮入口。

本次变更：
- 文件：`frontend/src/projects/insulation_pipe_supply_2026/pages/DemandManagementView.vue`
- 在页面顶部 `topbar-actions` 区域新增按钮：`提交本换热站填报状态`
- 位置选择：
  - 与“返回功能页”同层
  - 位于页面最上部
  - 不与“三日计划保存”“实际使用量保存”混淆

当前按钮行为：
- 仅作为提交入口占位
- 点击后通过 `actionMessage` 提示：后续将接入提交条件校验与提交记录写入
- 目前不写入 `station_submission_status.json`

同步文档：
- `configs/progress.md`
- `frontend/README.md`

验证：
- 前端 `npm run build` 通过。