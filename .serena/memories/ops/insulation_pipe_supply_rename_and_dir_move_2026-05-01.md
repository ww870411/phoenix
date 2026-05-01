# 2026-05-01 2026年度保温管供需管理系统名称与目录改名

## 背景
用户要求将项目名称统一改为“2026年度保温管供需管理系统”，并同步修改对应的数据目录名。

## 变更
- 将项目显示名称统一改为“2026年度保温管供需管理系统”，覆盖以下位置：
  - `backend_data/shared/项目列表.json`
  - `frontend/src/projects/insulation_pipe_supply/pages/InsulationPipeSupplyEntryView.vue`
  - `backend_data/projects/insulation_pipe_supply_2026/README.md`
  - `configs/progress.md`
  - `frontend/README.md`
  - `backend/README.md`
- 将目录从 `backend_data/projects/insulation_pipe_supply/` 改名为 `backend_data/projects/insulation_pipe_supply_2026/`。
- 保持项目键、路由键、权限键为 `insulation_pipe_supply`，不做兼容面更大的结构性改动。

## 验证
- 前端 `npm run build` 通过。
- 目录校验通过：`backend_data/projects/insulation_pipe_supply_2026/` 存在，旧目录 `backend_data/projects/insulation_pipe_supply/` 不再存在。

## 备注
- 本次“目录名也改一下”解释为修改后端数据目录名；未同步修改前端项目目录名与项目键。