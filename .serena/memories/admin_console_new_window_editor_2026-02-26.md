日期：2026-02-26
主题：管理后台文件编辑改为“新窗口编辑器”并美化树形结构

用户诉求：
- 树形结构更美观（模块连接感）；
- 点击文件后不是页内弹层，而是新窗口编辑。

实施：
1) 前端主页面（AdminConsoleView.vue）
- 文件树样式升级：连接线 + 模块节点的视觉。
- 文件点击行为：改为 window.open('/admin-file-editor?path=...')。
- 监听 postMessage('admin-file-saved')，显示“保存成功”回执。

2) 新增独立编辑页（AdminFileEditorWindow.vue）
- 路由：/admin-file-editor
- 能力：
  - 读取指定 path 文件；
  - 保存并关闭；
  - 不保存关闭（含未保存确认）；
  - Ctrl/Cmd + S 快捷保存；
  - 保存后向 opener 发回保存消息。

3) 后端
- 无新增接口，继续复用 /api/v1/admin/files/content 读写接口。

文档留痕：
- configs/progress.md
- frontend/README.md
- backend/README.md