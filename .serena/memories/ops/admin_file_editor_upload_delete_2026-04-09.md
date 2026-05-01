时间：2026-04-09
主题：管理后台“后台文件编辑”新增上传文件与删除文件能力

触发背景：用户要求在“管理后台”的“后台文件编辑”中增加上传文件和删除文件功能。

变更文件：
- backend/api/v1/admin_console.py
- frontend/src/projects/daily_report_25_26/services/api.js
- frontend/src/projects/daily_report_25_26/pages/AdminFileEditorWindow.vue
- frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

核心改动：
1. 后端新增 POST /api/v1/admin/files/upload
   - 查询参数 directory，multipart 参数 file
   - 仅后台管理员可用
   - 目录与目标文件路径必须位于 backend_data/ 下
   - 文件扩展名必须属于现有可编辑文本白名单
   - 文件大小沿用 2MB 上限
   - 内容必须可按 UTF-8 解码
   - 返回 ok/path/size/overwritten
2. 后端新增 DELETE /api/v1/admin/files
   - 查询参数 path
   - 仅后台管理员可用
   - 仅允许删除 backend_data/ 下文件
3. 前端 API 新增 uploadAdminFile()、deleteAdminFile()
4. 后台文件编辑弹窗新增：
   - “上传文件”按钮：上传到当前文件所在目录，成功后自动载入新文件，并向父窗口发送 admin-file-uploaded
   - “删除文件”按钮：删除当前文件，成功后发送 admin-file-deleted 并关闭窗口
   - 当前目录提示、上传/删除中的禁用态与确认提示
5. 管理后台主界面新增对 admin-file-uploaded / admin-file-deleted 的消息监听，收到后刷新目录树与文件列表，并更新最近打开状态。

验证结果：
- backend/api/v1/admin_console.py 已通过 py_compile
- frontend 已执行 npm run build，构建通过

补充说明：
- 本轮前端 .vue 与文档修改因 Serena 不适合结构化编辑，按仓库规范使用 apply_patch / desktop-commander 降级完成。