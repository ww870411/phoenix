时间：2026-02-11
任务：按用户要求进一步简化 mini_project_demo 配置。

变更摘要：
1) 文件 backend_data/shared/项目列表.json
   - mini_project_demo 保留单一页面 mini_entry；
   - 页面名称改为“迷你业务页”；
   - 页面描述改为“单页面线性流程（无审批、无常量指标配置）”；
   - 删除 modularization 空清单字段（config_files/runtime_files）。
2) 文档同步：
   - backend/README.md：补充 mini 项目为单页面最小配置；
   - frontend/README.md：补充 projects 页第二位 mini 项目仅保留单页面入口；
   - configs/progress.md：新增本次会话记录。

实现链路说明：
- /projects 页面数据仍通过 frontend/src/pages/ProjectSelectView.vue -> useProjects.ensureProjectsLoaded -> services/api.listProjects -> GET /api/v1/projects -> backend/api/v1/routes.py:list_projects -> backend_data/shared/项目列表.json。
- 项目排序保持 JSON 键顺序，mini_project_demo 仍在第二位。