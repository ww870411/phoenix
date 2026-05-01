时间：2026-04-10
需求：
1. page_showcase 首页卡片信息过多，去掉与标题重复的内容。
2. page_showcase 详情页增加“生成永久链接”按钮，任何人使用该链接都无需权限即可访问静态页面。
3. 排查 admin-console“后台文件编辑”在生产环境看不到部分 backend_data 目录的问题。

结论：
- page_showcase 卡片中 page_name 与 file_name 当前完全相同，重复展示造成冗余。
- 原 page_showcase viewer 只能在平台内通过鉴权接口拉取 HTML，再用 iframe/srcdoc 预览，无法形成真正的公开链接。
- admin-console 目录缺失的根因是：
  1) 后端 /admin/files/directories 只返回 backend_data 第一层目录；
  2) 前端目录树又主要靠“顶层目录 + 可编辑文件路径”拼树；
  3) 因此嵌套目录、空目录、或目录下没有可编辑文本文件的目录都会消失。

本轮改动：
1. frontend/src/projects/page_showcase/pages/PageShowcaseEntryView.vue
- 移除卡片里重复的 file_name 显示，仅保留大小和更新时间。

2. frontend/src/projects/page_showcase/pages/PageShowcaseViewerView.vue
- 新增“生成永久链接”按钮。
- 点击后调用公开链接生成函数，尝试复制到剪贴板，并直接在新窗口打开。
- 页面上新增永久链接提示文本。

3. frontend/src/projects/daily_report_25_26/services/api.js
- 新增 getPageShowcasePublicUrl(projectKey, fileName)，统一生成公开访问 URL。

4. backend/projects/page_showcase/api/workspace.py
- 新增 public_router 接口：GET /api/v1/projects/page_showcase/page-showcase/public-html/{file_name}
- 返回 HTMLResponse，供任何持链接者直接访问。

5. backend/api/v1/routes.py
- 对 project_key == page_showcase 的 public_router 取消项目访问依赖；其余项目保持原鉴权逻辑不变。

6. backend/api/v1/admin_console.py
- /admin/files/directories 改为递归遍历 backend_data 下所有子目录，并返回相对路径。

7. frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue
- 文件树构建逻辑增加 ensureFolderPath，支持把递归目录路径按层级展开；
- 因此后端返回的嵌套目录、空目录现在也能在树中显示。

验证：
- python -m py_compile backend/projects/page_showcase/api/workspace.py backend/api/v1/routes.py backend/api/v1/admin_console.py 通过。
- frontend 执行 npm run build 通过。

文档同步：
- configs/progress.md
- frontend/README.md
- backend/README.md