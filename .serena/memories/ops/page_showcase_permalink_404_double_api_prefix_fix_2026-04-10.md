时间：2026-04-10
问题：开发环境点击 page_showcase 详情页“生成永久链接”后，打开页面显示 {"detail":"Not Found"}。
根因：frontend/src/projects/daily_report_25_26/services/api.js 中 getPageShowcasePublicUrl(projectKey, fileName) 对 projectPath(projectKey) 的结果又套了一次 normalized(...)。由于 projectPath 已经包含 /api/v1 前缀，最终链接被错误拼成 /api/v1/api/v1/projects/page_showcase/page-showcase/public-html/{file_name}，因此返回 404。
修复：
- 文件：frontend/src/projects/daily_report_25_26/services/api.js
- 改动：getPageShowcasePublicUrl(...) 直接使用 `${projectPath(projectKey)}/page-showcase/public-html/${encodedFileName}`，不再重复调用 normalized(...)
结果：永久链接恢复为正确路径 /api/v1/projects/page_showcase/page-showcase/public-html/{file_name}。
验证：frontend npm run build 通过。
同步：configs/progress.md、frontend/README.md、backend/README.md 已更新。