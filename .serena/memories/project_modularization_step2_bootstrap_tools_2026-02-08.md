时间戳：2026-02-08
任务：按用户要求继续推进计划顺序，实现可直接使用的目录迁移过渡工具。

改动文件：
1) backend/services/project_data_paths.py
2) backend/api/v1/daily_report_25_26.py
3) configs/progress.md
4) backend/README.md
5) frontend/README.md

实现内容：
- project_data_paths 新增迁移工具函数：
  - ensure_project_dirs
  - bootstrap_project_files
  - get_project_file_status
- 新增后端接口（系统管理员）：
  - GET /project/modularization/status
  - POST /project/modularization/bootstrap
- 接口内置首批配置与运行时文件清单，可一键创建目录并按“仅缺失时复制”迁移旧平铺文件。

结果：
- 从“只能兼容读取”提升为“可观测 + 可执行迁移”，用户不需要手工在 backend_data 中逐个建目录/复制文件。
- 仍保持低风险：不覆盖新目录已有文件。