时间：2026-02-12
问题：daily_report_25_26 的“数据展示”页面导出 Excel 时卡住并报错，前端展示 Cloudflare 504 HTML。
定位结论：DisplayRuntimeView.vue 中 exportToExcel 对 runtime/spec/eval 发起 3 个并发请求，失败时直接透传 HTML 错误文本；api.js 的 evalSpec 不支持 AbortController，缺少超时控制。
改动文件：
1) frontend/src/projects/daily_report_25_26/services/api.js
   - evalSpec(projectKey, body, options={}) 增加 signal 透传。
2) frontend/src/projects/daily_report_25_26/pages/DisplayRuntimeView.vue
   - 新增 EXPORT_EVAL_TIMEOUT_MS=120000、EXPORT_RETRY_DELAY_MS=1200。
   - 新增 normalizeExportError：将 HTML/Cloudflare/504 归一为可读提示。
   - 新增 evalSpecForExport：超时中断 + 超时/504 一次重试。
   - exportToExcel 中 runtime/spec/eval 改为串行执行，降低并发压力。
3) configs/progress.md
4) frontend/README.md
5) backend/README.md
验证证据：frontend 执行 npm run build 通过。