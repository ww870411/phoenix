时间：2026-02-26
任务：纠正上一轮文件迁移口径。
用户最终口径：
1) 项目列表文件应在 shared：backend_data/shared/项目列表.json
2) date 文件应在项目目录：backend_data/projects/daily_report_25_26/runtime/date.json
执行：
- 文件移动：
  - projects/daily_report_25_26/config/项目列表.json -> shared/项目列表.json
  - shared/date.json -> projects/daily_report_25_26/runtime/date.json
- 代码修改：backend/services/project_data_paths.py
  - resolve_project_list_path()：shared 优先，项目内/根目录回退。
  - resolve_global_date_path()：项目内 runtime/date.json 优先，shared/根目录回退。
- 文档留痕：configs/progress.md、backend/README.md、frontend/README.md 已追加更正记录。
结果：路径已按最新口径落地，前端无需改动。