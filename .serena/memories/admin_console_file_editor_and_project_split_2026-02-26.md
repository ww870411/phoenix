日期：2026-02-26
主题：管理后台页面完善（后台文件编辑 + 项目后台设定分流）

需求实现：
1) 后台文件编辑
- 后端新增全局接口（backend/api/v1/admin_console.py）：
  - GET /api/v1/admin/files/directories
  - GET /api/v1/admin/files?directory=...
  - GET /api/v1/admin/files/content?path=...
  - POST /api/v1/admin/files/content
- 安全限制：
  - 仅允许 backend_data 根目录内相对路径；
  - 禁止越界与绝对路径；
  - 单文件编辑上限 2MB；
  - 仅按 UTF-8 文本读写。

2) 项目后台设定分流
- 后端新增项目列表接口：GET /api/v1/admin/projects
- 后端概览接口支持项目参数：GET /api/v1/admin/overview?project_key=...
  - 仅 daily_report_25_26 返回 supported=true；
  - 其它项目返回 supported=false + 提示。
- 前端管理页重构（AdminConsoleView.vue）：
  - 新增“后台文件编辑”三栏布局（目录/文件/编辑器）；
  - 新增“项目后台设定”项目切换；
  - 仅在选中 daily_report_25_26 时显示原有校验/AI/缓存设定模块。

3) 前端 API 扩展（services/api.js）
- listAdminProjects
- listAdminFileDirectories
- listAdminFiles
- readAdminFile
- saveAdminFile
- getAdminOverview(projectKey)

留痕文件：
- configs/progress.md
- backend/README.md
- frontend/README.md