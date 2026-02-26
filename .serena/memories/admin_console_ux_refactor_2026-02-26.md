日期：2026-02-26
主题：管理后台体验重构（视觉层次 + 操作便利性）

触发原因：用户反馈“页面不美观、操作便利性差”。

实施内容：
1) 前端页面重构（AdminConsoleView.vue）
- 顶部切换为双标签页：后台文件编辑 / 项目后台设定。
- 文件编辑区重排：目录下拉 + 文件搜索 + 文件列表 + 编辑器。
- 编辑交互增强：
  - 未保存状态标记；
  - 切换文件前确认；
  - Ctrl/Cmd + S 快捷保存；
  - 字数与保存结果提示。

2) 后端文件列表可用性优化（backend/api/v1/admin_console.py）
- 仅返回可编辑文本类型：json/md/txt/yaml/yml/ini/toml/py/js/ts/vue/css/sql/csv。
- 过滤 2MB 以上文件。
- 目的：减少噪音文件和二进制文件对前端体验影响。

3) 入口视觉优化
- AppHeader.vue 对“进入后台”按钮增加独立配色样式，提升可见性。

同步文档：
- configs/progress.md
- backend/README.md
- frontend/README.md