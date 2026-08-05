# 前端开发容器 xlsx-js-style 导入失败修复

- 时间：2026-08-05（Asia/Hong_Kong）
- 症状：Vite 在 `/app/src/projects/insulation_pipe_supply_2026/pages/SupplyManagementView.vue` 报 `Failed to resolve import "xlsx-js-style"`。

## 根因

`docker-compose.yml` 将宿主机 `./frontend` 绑定挂载到容器 `/app`，同时将命名卷 `phoenix_frontend_node_modules` 挂载到 `/app/node_modules`。宿主机已经安装并锁定 `xlsx-js-style@1.2.0`，但运行约 3 小时的前端容器命名卷尚未同步，因此源码可见、依赖不可见。

## 处理

- 执行 `docker exec phoenix_frontend npm install --no-audit --progress=false`，向命名卷补装依赖，成功新增 8 个包。
- 未修改 `docker-compose.yml`；前端服务启动命令已经是 `npm install && npm run dev -- --host 0.0.0.0 --port 5173`，后续重新创建容器时会自动同步锁文件。
- 本轮业务代码无新增修改；仅更新运行环境和三份强制文档：`configs/progress.md`、`frontend/README.md`、`backend/README.md`。

## 验证证据

- 直接请求 Vite 模块端点成功返回转换后的 `SupplyManagementView.vue`，其中导入已解析为 `/node_modules/.vite/deps/xlsx-js-style.js?v=8975f408`，无 import-analysis 错误。
- 容器内 `npm run build` 成功：Vite 7.1.10，149 modules transformed，15.50s；仅有既存 chunk >500kB 告警。
- 后端服务与数据库未变更。

## 工具与权限留痕

- 初次容器安装命令受 Windows Docker named pipe 沙箱权限拒绝；按规则申请提升权限后执行成功。
- 文档继续使用 Desktop Commander 精确块编辑，因为本会话 `apply_patch` 已连续两次触发 Windows sandbox `helper_unknown_error`，且 Markdown 不适合 Serena 符号编辑。

最后验证日期：2026-08-05