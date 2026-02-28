时间：2026-02-28
主题：monthly_data_pull 项目数据目录归位到 backend_data/projects 下，并排查同类平铺路径
触发：用户指出 backend_data 中 monthly_data_pull 未位于 projects 子目录，要求与其他项目并列并修正类似问题。
变更文件：
1) backend/projects/monthly_data_pull/api/workspace.py
2) backend_data/projects/monthly_data_pull/workspace_settings.json
3) backend/README.md
4) frontend/README.md
5) configs/progress.md
目录迁移：
- backend_data/monthly_data_pull -> backend_data/projects/monthly_data_pull（整目录迁移）
- backend_data/spring_festival_latest_extract.json -> backend_data/projects/daily_report_spring_festval_2026/runtime/spring_festival_latest_extract.json
实现摘要：
- workspace.py 中 _workspace_root() 改为 get_project_root(PROJECT_KEY)，统一项目数据根到 backend_data/projects/<project_key>。
- workspace_settings.json 四个目录字段改为 backend_data/projects/monthly_data_pull/...。
- 复查 backend_data 根目录后仅保留 projects/shared/sample.db/README.md，无项目业务目录平铺残留。
验证证据：
- backend_data 目录清单显示存在 projects/monthly_data_pull，且根目录无 monthly_data_pull。
- monthly_data_pull/api/workspace.py 不再引用 DATA_DIRECTORY，已使用 get_project_root。
回滚方式：
- 将 workspace.py 的 _workspace_root 恢复为 DATA_DIRECTORY / PROJECT_KEY；
- 将目录移回 backend_data/monthly_data_pull 并恢复 workspace_settings.json 路径字段。