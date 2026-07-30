# GIS 点位编辑入口诊断

时间：2026-07-30
范围：`frontend/src/projects/insulation_pipe_supply_2026/pages/GisMapView.vue` 与本地 Vite 服务。

## 结论与证据
- 路由 `gis_map` 在 `TubeProjectPageRouterView.vue` 中唯一映射到 `GisMapView.vue`。
- 点位列表的编辑按钮使用 `@click.stop="startEditMarker(item)"`；本地 Vite 已编译并下发同一事件处理器。
- `startEditMarker` 会先写入 `editingId` 与完整 `formModel`，然后将 `activeSideTab` 设为 `form`；表单使用 `v-if="activeSideTab === 'form'"` 渲染。文本检索未发现编辑后再自动将该状态写回 `list` 的逻辑。
- 本地 GIS 数据接口正常返回含 `id` 与完整点位字段的数据，故不存在点位标识缺失导致无法进入编辑模式的问题。
- 当前 Serena 仅启用 Python 语言服务，无法对 Vue 作符号级分析；已依 Serena 降级规则采用文本检索与本地 HTTP 只读验证。

## 风险点与建议
- `startEditMarker` 在切换 `activeSideTab` 前先调用 `clearDraftMarker()`。若已有草稿点且高德地图覆盖物移除抛出运行时异常，后续切换表单不会执行。建议修复时改为先切换表单与填充数据，再以受保护的清理逻辑处理草稿；同时给该入口增加最小回归测试或可观测错误提示。
- 当前诊断环境无可用的 in-app 本地浏览器执行通道，尚未完成真实 UI 点击复现；如用户界面仍复现，应优先采集浏览器控制台异常。