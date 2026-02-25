日期：2026-02-25
主题：确认 backend_data/shared/项目列表.json 当前功能

结论：
1) 该文件是全局项目注册表，`backend/api/v1/routes.py` 的 `list_projects` 通过 `_load_project_entries` 读取并返回 `/api/v1/projects`。
2) 该文件的 `pages` 字段驱动 `list_project_pages` 返回 `/api/v1/projects/{project_id}/pages`，包括页面名称、data_source、description 与 page_key（slug）。
3) 路径解析由 `backend/services/project_data_paths.py::resolve_project_list_path` 提供，优先 `backend_data/shared/项目列表.json`，兼容旧路径 `backend_data/项目列表.json`。
4) 该文件还被用于目录化迁移文件推断：`backend/services/project_modularization.py::resolve_project_modularization_files` 读取 `modularization.config_files/runtime_files`，缺省时从 `pages` 的 数据源 推断。
5) 在 `backend/projects/daily_report_25_26/api/legacy_full.py::_load_data_file_candidates` 中，会遍历该文件提取页面数据源 JSON 作为候选数据文件路径。

本次改动文件：
- configs/progress.md
- backend/README.md
- frontend/README.md

备注：本轮无业务代码变更，仅文档留痕与功能说明确认。