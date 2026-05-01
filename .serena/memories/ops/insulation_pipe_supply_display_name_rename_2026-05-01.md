# 2026-05-01 2026年保温管供需管理系统显示名调整

## 背景
用户要求将项目显示名称统一改为“2026年保温管供需管理系统”。

## 变更
- 保持项目键 `insulation_pipe_supply` 不变，避免影响路由、权限与目录结构。
- 将以下位置的显示名称统一改为“2026年保温管供需管理系统”：
  - `backend_data/shared/项目列表.json`
  - `frontend/src/projects/insulation_pipe_supply/pages/InsulationPipeSupplyEntryView.vue`
  - `backend_data/projects/insulation_pipe_supply/README.md`
  - `configs/progress.md`
  - `frontend/README.md`
  - `backend/README.md`

## 验证
- Serena 检查确认项目清单、前端入口页、项目目录 README 已显示新名称。

## 备注
- 仅修改用户可见名称，不修改目录名与项目键。