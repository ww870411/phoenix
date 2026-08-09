# 保温管全局管理“提交记录”排版整理

- 时间：2026-08-09
- 页面：`/projects/insulation_pipe_supply_2026/pages/global_management` 的“提交记录”标签页。
- 变更文件：
  - `frontend/src/projects/insulation_pipe_supply_2026/pages/GlobalManagementView.vue`
  - `configs/progress.md`
  - `frontend/README.md`
  - `backend/README.md`
- 变更摘要：提交概览改为主信息与统计指标分区；筛选区改为两行三列响应式网格；明细表增加固定列宽、粘性表头、斑马纹、悬停态及独立横向滚动；分页样式统一。
- 行为边界：未改提交记录接口、筛选参数、分页逻辑、后端代码、数据库或字段口径。
- 验证证据：`npm run build` 通过（Vite 7.1.10，149 modules，10.09s）；`git diff --check` 通过；浏览器 1692px 视口的 document client/scroll width 均为 1692px，筛选面板 client/scroll width 均为 861px，表格容器 client width 846px、scroll width 960px，仅表格独立横向滚动。
- 风险：构建仍有项目既有的大分包告警（TubeProjectPageRouterView 超过 500kB），与本轮排版无直接关系。
- 回滚：反向恢复上述四个文件的本轮差异即可，无后端或数据回滚步骤。
- 后续文案调整：按用户要求移除“提交记录”标题下方“核对需求主体（现场施工队/标段）与供给主体（供货厂家/运输队）的数据提交动态，核查开发与生产环境数据新旧及覆盖风险。”整段说明；功能与布局其余部分不变。重新执行 `npm run build` 与 `git diff --check` 均通过。
- 最后验证日期：2026-08-09