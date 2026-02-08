日期：2026-02-08
主题：项目模块化第四步（迁移文件清单改为配置驱动）

代码变更：
- 文件：backend/api/v1/routes.py
- 主要改动：
  1) `_get_project_modularization_files` 改为接收 `project_entry` 并按优先级解析：
     - 显式配置（modularization/目录化迁移/project_modularization）
     - pages 的 数据源/data_source 自动推断 JSON 文件
     - 默认清单兜底
  2) 新增辅助函数：
     - `_normalize_file_list`
     - `_extract_filename_from_data_source`
     - `_infer_project_config_files_from_pages`
  3) 通用接口 `status/bootstrap` 改为传入项目条目参与动态解析。

文档留痕：
- configs/progress.md 增加“第四步-文件清单配置驱动”记录
- backend/README.md 增加“项目模块化第四步”说明
- frontend/README.md 增加对应会话小结

效果：
- 新项目可通过项目列表配置驱动迁移清单，不再强依赖后端硬编码。
- 旧项目仍保持默认兜底与兼容行为。