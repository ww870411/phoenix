时间：2026-02-26
任务：后台文件编辑页面去掉独立“目录”控件，将目录融入树形结构。
变更：
- 文件：frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue
- 删除：目录下拉（selectedDirectory/selectDirectory 相关状态与流程）
- 新策略：loadDirectories() 获取目录列表后批量调用 listAdminFiles(dir) 合并文件，生成“目录+文件”统一树
- 交互：目录作为树节点展开/收起；点击文件仍在新窗口编辑
结果：UI 不再有重复的目录入口，树形导航一致化。