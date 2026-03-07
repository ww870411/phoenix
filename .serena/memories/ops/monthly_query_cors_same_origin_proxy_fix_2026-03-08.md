时间：2026-03-08
问题：月报查询页打开时报 CORS（localhost:5173 请求 127.0.0.1:8001 的 query-options 被拦截）。

处理思路：
- 在本机开发环境优先走同源 /api 代理，绕开跨域链路。

代码变更：
- 文件：frontend/src/projects/daily_report_25_26/services/api.js
- 新增 shouldPreferSameOriginProxy(base)
- API_BASE 计算中新增分支：当“前端 origin 为 localhost/127.0.0.1 + base 也是本机地址”时，强制返回 '/api/v1'。

效果：
- monthly_data_show/query-options 等接口在本机开发走同源代理，避免 CORS preflight/header 问题。

文档同步：
- configs/progress.md
- frontend/README.md
- backend/README.md