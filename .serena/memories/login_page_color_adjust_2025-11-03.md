## 2025-11-03 登录页面蓝色调微调
- 时间：2025-11-03T00:00（本地时区假定）
- 文件：frontend/src/daily_report_25_26/pages/LoginView.vue；frontend/README.md；configs/progress.md
- 变更：调深登录页背景渐变（含移动端断点），使蓝色主色调更沉稳；同步更新文档说明。
- 回滚：将渐变颜色恢复至 `#3876da/#4b89df/#9ed6ff` 与 `#3c7ade/#7ab9ff` 即可；文档备注可同时还原。
- 验证：未运行自动化测试，建议浏览器刷新 `/login` 检查视觉效果。