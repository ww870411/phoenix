# 2026-05-24 tube配置文件实时加载收口

时间：2026-05-24

## 背景
用户要求 `backend_data/projects/insulation_pipe_supply_2026/tube_config.json` 的所有配置项在前端页面中做到实时加载。问题表现为：直接手改 `biz_date` / `plan_start_date` 后，前端页面仍显示旧值，只有在全局管理页保存一次后，页面日期才会更新。

## 根因
- 后端 `load_tube_config()` 每次请求都会直接读取 `tube_config.json`，没有缓存。
- 前端各页面主要在 `onMounted` 时首次拉取配置或选项，并将日期/选项保存在本地状态中。
- `DemandManagementView.vue` 还存在 `if (!bizDate.value)` / `if (!anchorDate.value)` 这类只初始化一次的逻辑，导致后续重新拉接口时也不会覆盖旧日期。

## 变更文件
- `frontend/src/projects/insulation_pipe_supply_2026/pages/shared.js`
- `frontend/src/projects/insulation_pipe_supply_2026/pages/DemandManagementView.vue`
- `frontend/src/projects/insulation_pipe_supply_2026/pages/SupplyManagementView.vue`
- `frontend/src/projects/insulation_pipe_supply_2026/pages/WarehouseManagementView.vue`
- `frontend/src/projects/insulation_pipe_supply_2026/pages/GlobalManagementView.vue`
- `configs/progress.md`
- `frontend/README.md`
- `backend/README.md`

## 修复摘要
1. 在 `shared.js` 新增 `useTubeRealtimeRefresh`，统一处理页面激活、窗口回焦、标签页重新可见和 30 秒轮询时的配置自动重拉。
2. `useTubePageShell` 已接入该机制，`dashboard` 与公共配置摘要不再只停留在首次加载状态。
3. `DemandManagementView.vue` 每次加载都会覆盖 `bizDate` / `anchorDate` / `usageDate`，并在站点配置变化时修正当前选中站点；新增 `refreshRealtimeConfig()` 同步重拉选项与业务数据。
4. `SupplyManagementView.vue` 每次加载都会覆盖日期与主体/站点/型号配置状态，自动清理失效筛选与发货表单值；新增 `refreshRealtimeConfig()` 同步重拉选项、汇总与发货记录。
5. `WarehouseManagementView.vue` 每次加载都会重拉选项，并自动清理失效的站点、主体、型号和状态筛选。
6. `GlobalManagementView.vue` 已接入自动重载 `loadConfig()`，外部手改 `tube_config.json` 后可自动读到新配置。

## 验证
- 在 `frontend/` 目录运行 `npm run build`
- 结果：通过，Vite 构建成功。

## 结论
当前 tube 项目四个页面与公共摘要区已具备“配置文件变化后自动重新读取”的前端能力，不再必须依赖全局管理页的保存动作才能让页面日期或其他配置显示更新。