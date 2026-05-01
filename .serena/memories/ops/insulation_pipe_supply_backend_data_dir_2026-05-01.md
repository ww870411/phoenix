# 2026-05-01 保温管供需管理系统后端数据目录

## 背景
用户要求在 `backend_data/projects` 下建立保温管供需管理系统的项目文件夹。

## 变更
- 新增 `backend_data/projects/insulation_pipe_supply/README.md`，由此创建项目目录 `backend_data/projects/insulation_pipe_supply/`。
- 目录键名使用 `insulation_pipe_supply`，与前端入口、共享项目清单、权限配置保持一致。
- 同步更新 `configs/progress.md`、`frontend/README.md`、`backend/README.md`。

## 验证
- Serena 检查确认 `backend_data/projects/insulation_pipe_supply/README.md` 已存在，包含项目说明与“项目目录已创建”标记。

## 回滚
- 删除 `backend_data/projects/insulation_pipe_supply/README.md`，并移除三份文档中的对应记录。