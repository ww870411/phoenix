# 2026-05-24 tube配置读取根因修复

时间：2026-05-24

## 现象
用户直接修改 `backend_data/projects/insulation_pipe_supply_2026/tube_config.json` 后，前端页面即使刷新也仍显示旧数据；但如果在全局管理页保存一次相同字段，页面又会显示新值。

## 根因
不是前端单一刷新问题，而是 tube 子项目存在双数据源路径冲突：

1. Docker Compose 将运行数据目录挂载到容器 `/app/data`。
2. Phoenix 平台统一通过 `backend.config.DATA_DIRECTORY` / `backend.services.project_data_paths.get_project_root()` 解析项目数据目录。
3. 但 `backend/projects/insulation_pipe_supply_2026/services/config_service.py` 之前没有走平台统一机制，而是硬编码：
   - `Path(__file__).resolve().parents[4] / "backend_data" / "projects" / PROJECT_KEY`
4. 在容器环境下，这会指向镜像内 `/app/backend_data/projects/insulation_pipe_supply_2026/tube_config.json` 的历史副本，而不是宿主机挂载到 `/app/data/projects/insulation_pipe_supply_2026/tube_config.json` 的实时文件。
5. 于是形成两套配置：
   - 手工修改的是宿主挂载目录那份；
   - 后端接口读写的是镜像内旧副本；
   - 所以前端刷新仍拿到旧值。
   - 当在全局管理页保存时，后端把变更写回自己正在使用的旧副本，因此页面又“看起来恢复正常”。

## 修复
- 文件：`backend/projects/insulation_pipe_supply_2026/services/config_service.py`
- 改动：`PROJECT_DATA_DIR` 从硬编码仓库路径改为 `get_project_root(PROJECT_KEY)`。
- 结果：`CONFIG_PATH` 统一跟随平台标准数据目录 `DATA_DIRECTORY/projects/<project_key>/tube_config.json`，与容器挂载目录机制对齐。

## 验证
- 运行 `python -m py_compile backend/projects/insulation_pipe_supply_2026/services/config_service.py backend/projects/insulation_pipe_supply_2026/api/workspace.py`
- 结果：通过。

## 结论
此次问题确实存在“多重机制”叠加：
- 前端曾有本地状态不覆盖问题；
- 后端又存在更根本的配置路径分叉问题。
后者是导致“手改配置文件无效，但在页面保存一次就生效”的直接根因。