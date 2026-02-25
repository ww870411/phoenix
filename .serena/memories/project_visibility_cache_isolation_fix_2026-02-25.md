日期：2026-02-25
主题：项目可见性异常（非授权用户可见 spring 项目）修复

现象：
- 用户反馈非授权账号也可见/可进入 daily_report_spring_festval_2026。

根因：
- 前端 services/api.js 的项目列表缓存为全局单例 cachedProjects，未按 auth token 隔离。
- 切换账号后仍命中上一账号缓存，表现为串权限显示。

修复：
- 文件：frontend/src/projects/daily_report_25_26/services/api.js
- 新增 cachedProjectsToken；
- listProjects() 仅在 cachedProjectsToken === authToken 时命中缓存；
- setAuthToken() token 变化时自动 resetProjectCache();
- resetProjectCache() 同时清空 cachedProjects 与 cachedProjectsToken。

结果：
- 账号切换后项目列表强制重新请求，项目可见性与后端 permissions 过滤一致。