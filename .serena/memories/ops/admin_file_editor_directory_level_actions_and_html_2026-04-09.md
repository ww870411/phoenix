时间：2026-04-09
主题：管理后台文件编辑改为主界面目录级上传/删除，并支持 HTML 文件

触发背景：用户反馈上传/删除不应依赖先打开文件，且后台目录中的 HTML 文件未显示。

变更文件：
- backend/api/v1/admin_console.py
- frontend/src/projects/daily_report_25_26/services/api.js
- frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue
- frontend/src/projects/daily_report_25_26/pages/AdminFileEditorWindow.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

核心改动：
1. 后端将 .html / .htm 加入后台可编辑文本白名单，因此文件树、读取、保存、上传都支持 HTML 文本文件。
2. 后端新增 DELETE /api/v1/admin/files/directories
   - 仅允许删除 backend_data/ 下空目录
   - 禁止删除 backend_data 根目录
3. 管理后台前端改为：
   - 文件树单击只选中目录/文件
   - 双击文件才打开编辑器
   - 顶部工具栏新增“上传到所选目录”“打开所选文件”“删除所选”
   - 选中目录时可上传；选中文件可打开；选中文件或空目录可删除
4. 后台文件编辑弹窗移除上传/删除按钮，回归纯编辑窗口。

验证结果：
- backend/api/v1/admin_console.py 已通过 py_compile
- frontend 已执行 npm run build，构建通过

补充说明：
- 本轮 .vue / .md 修改因 Serena 不适合结构化编辑，按仓库规范使用 apply_patch / desktop-commander 降级完成。