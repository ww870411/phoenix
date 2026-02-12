时间：2026-02-11
任务：在 /projects 页面新增迷你项目，并显示为第二位。

关键结论：
1) 前端项目列表链路：frontend/src/pages/ProjectSelectView.vue -> frontend/src/daily_report_25_26/composables/useProjects.js -> frontend/src/daily_report_25_26/services/api.js(listProjects) -> GET /api/v1/projects。
2) 后端项目列表来源：backend/api/v1/routes.py 的 list_projects，读取 backend_data/shared/项目列表.json（由 resolve_project_list_path 解析）。
3) 排序机制：/projects 返回顺序跟随 JSON 对象键顺序；Python3.7+ dict 保序，前端按返回数组直接渲染。

本次变更文件：
- backend_data/shared/项目列表.json（新增 mini_project_demo，放在第二位）
- backend/README.md（补充项目列表来源与迷你项目说明）
- frontend/README.md（补充 projects 页数据来源与排序说明）
- configs/progress.md（新增本次会话记录）

回滚方式：
- 删除 backend_data/shared/项目列表.json 中 mini_project_demo 条目；其余文档说明可按需回退。

补充说明：
- 若浏览器已缓存项目列表（前端内存缓存），需要刷新页面或重新登录后可看到新增项目。