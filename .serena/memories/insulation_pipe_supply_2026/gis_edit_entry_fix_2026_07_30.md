# GIS 点位编辑入口修复

时间：2026-07-30

## 变更
- `frontend/src/projects/insulation_pipe_supply_2026/pages/GisMapView.vue`
  - `startEditMarker(item)` 改为先设置 `editingId`、`formModel` 和 `activeSideTab = 'form'`，再清理遗留草稿点位。
  - `clearDraftMarker()` 改为先释放 `draftMarkerObject` 与 `hasDraftMarker` 状态，然后在 `try/catch` 中调用高德地图的 `mapInstance.remove`。覆盖物移除异常仅以 `console.warn` 记录，不再中断编辑、新增、取消或卸载流程。
- 已同步 `configs/progress.md`、`frontend/README.md`、`backend/README.md`；后端接口和数据库无改动。

## 原因与效果
此前编辑入口会在切换右侧表单之前清理草稿覆盖物。若高德地图覆盖物移除失败，异常会中止事件函数，用户无法进入编辑表单。修复后先完成表单切换，且地图清理异常已隔离。

## 验证
- 2026-07-30 执行 `frontend` 目录下 `npm run build` 成功，Vite 构建 139 个模块并退出码为 0。
- `git diff --check` 输出了工作区既有文件的尾随空格提示；未发现本次新增函数段的格式问题。