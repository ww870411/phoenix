# 2026-05-01 保温管供需管理系统项目入口

## 背景
用户要求在 `/projects` 尾部新增项目“保温管供需管理系统”，权限仅限 `global_admin`，点击进入后显示“数据看板”“原材料管理”“生产与分配管理”“需求管理”四个页面卡片。

## 变更文件
- `backend_data/shared/项目列表.json`：尾部新增 `insulation_pipe_supply`，`availability` 仅包含 `Global_admin`，声明四个页面键：`dashboard`、`raw_materials`、`production_allocation`、`demand`。
- `backend_data/shared/auth/permissions.json`：仅在 `groups.Global_admin.projects` 下增加 `insulation_pipe_supply` 页面权限，其他组未配置该项目。
- `frontend/src/pages/ProjectSelectView.vue`：将 `insulation_pipe_supply` 加入直达项目集合，点击项目卡片进入 `/projects/insulation_pipe_supply`。
- `frontend/src/pages/ProjectEntryView.vue`：导入并映射 `InsulationPipeSupplyEntryView`。
- `frontend/src/projects/insulation_pipe_supply/pages/InsulationPipeSupplyEntryView.vue`：新增入口页，展示四个功能卡片；直接检查 `permissions.projects.insulation_pipe_supply.page_access`，未授权账号显示无权访问提示，避免旧版全局页面权限回退误放行。
- `configs/progress.md`、`frontend/README.md`、`backend/README.md`：同步记录本轮变更。

## 验证
- `npm run build` 通过。
- Python JSON 解析检查通过：`backend_data/shared/项目列表.json` 与 `backend_data/shared/auth/permissions.json` 均可解析。

## 回滚
移除上述新增项目配置、权限配置、前端直达映射和入口组件即可回退。