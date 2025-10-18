时间：2025-10-18
变更文件：
- frontend/src/daily_report_25_26/pages/DashboardView.vue
- frontend/README.md
- backend/README.md

问题与原因：
- /projects/:projectKey/sheets 看板页面表名点击无法进入填报页，疑因路由参数键不匹配（data-entry 路由定义为 projectKey/sheetKey，点击处理可能传入了 project_key/sheet_key）。
- 部分环境出现空白页，推测与首屏数据拉取失败或导航异常有关，先保证点击跳转路径正确，避免交互阻塞。

处理方案：
- 将 Dashboard 表名链接由 @click.prevent="openFill(s)" 改为命名路由 <router-link :to="{ name: 'data-entry', params: { projectKey, sheetKey: s.sheet_key } }">，直接依赖路由定义，避免参数键不一致导致的跳转失败。
- 文档补充：更新 frontend/README.md 路由结构；backend/README.md 提醒接口清单。

回滚思路：
- 如需回滚，恢复上述文件至变更前版本。

验证建议：
- 打开 /projects/daily_report_25_26/sheets 页面，点击任一表名，应跳转至 /projects/daily_report_25_26/sheets/<sheet_key> 页面。
- 若仍空白，请打开浏览器控制台检查网络/脚本错误；如为后端 404，建议在前端 services/api.js 的 listSheets() 增加兜底常量返回。