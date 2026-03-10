日期：2026-03-10
主题：登录页与站点标题改名
变更摘要：按用户要求，将登录页与站点标题中旧平台名称替换为“大连洁净能源集团 生产经营数据智算平台”，并将登录页底部版权年份由“2025”改为“2025-2026”。
涉及文件：
- frontend/src/pages/LoginView.vue
- frontend/index.html
- configs/progress.md
- frontend/README.md
- backend/README.md
验证结果：已检索前端目录，运行界面的旧文案“生产数据在线填报平台”不再存在；新文案与新年份已在 LoginView.vue 与 index.html 命中。README 中保留旧文案仅用于变更记录说明，属预期留痕。
备注：本轮未改动后端接口、数据库或配置结构。