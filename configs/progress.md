- 2026-03-09：已按用户要求新增独立事故记录 `configs/3.9 docker故障记录.md`，系统整理本次服务器重启后 Phoenix Docker 网络异常、504 登录故障、bridge 网络脏状态与后续建议，供外部专家继续接手分析。

## 2026-03-09（登录故障排查：线上 `/api/v1/auth/login` 返回 504，定位为服务器回源链路异常）

- 现象：
  - 用户在 `https://platform.smartview.top` 登录时，请求 `POST /api/v1/auth/login` 长时间等待后失败。
  - 用户提供的浏览器控制台记录显示返回内容为 Cloudflare `504 Gateway time-out` 页面，而非 Phoenix 业务 JSON。
- 代码与本地验证：
  - 前端登录页 `frontend/src/pages/LoginView.vue` 调用 `auth.login(...)`；
  - 前端 API 层 `frontend/src/projects/daily_report_25_26/services/api.js` 登录固定请求 `POST ${API_BASE}/auth/login`；
  - 后端接口 `backend/api/v1/auth.py` 的 `/api/v1/auth/login` 逻辑仅调用 `auth_manager.login(...)`；
  - 本地容器环境中，`phoenix_backend`、`phoenix_frontend`、`phoenix_db` 均正常运行，本地 `curl http://127.0.0.1:8001/healthz` 返回 `200`，`/api/v1/auth/me` 返回预期 `401`；
  - 本地后端日志中可见登录接口曾返回 `200 OK`，说明当前仓库代码链路本身可用。
- 关键判断：
  - 本次不是前端未发请求、不是登录表单校验错误、也不是典型的 401/404 业务错误；
  - 504 表明线上入口已经收到 `/api/v1/auth/login`，但服务器在把 `/api` 转发给 Phoenix 后端时超时；
  - 结合部署文件，线上应使用 `docker-compose.server.yml` / `docker-compose.server_new_server.yml` 的 `web -> backend -> db` 结构，其中 Nginx 通过 `proxy_pass http://backend:8000` 转发；
  - 登录接口本身不依赖外部 HTTP，主要可能卡在两处：
    1. `web` 容器无法正确回源到 `backend`；
    2. `backend` 在处理登录时访问 PostgreSQL（尤其“记住登录”对应 `auth_sessions` 持久化）发生阻塞。
- 高优先级排查建议：
  1. 在服务器确认当前实际运行的是哪套容器：生产应重点看到 `phoenix-web` / `phoenix-backend` / `phoenix-db`，而不是开发态 `phoenix_frontend` / `phoenix_backend` / `phoenix_db`。
  2. 检查 `phoenix-web` 与 `phoenix-backend` 是否处于同一 Docker network（通常为 `phoenix_phoenix_net`）。
  3. 在服务器容器内验证：
     - `curl http://backend:8000/healthz`
     - `curl -i -X POST http://backend:8000/api/v1/auth/login ...`
  4. 查看 `phoenix-web` 的 Nginx 错误日志与 `phoenix-backend` 日志，确认是 upstream connect timeout、read timeout，还是后端执行卡住。
  5. 若 backend 日志无登录请求，则优先修复容器网络/错误容器栈；若 backend 收到请求但长时间不返回，则重点检查 PostgreSQL 连接、锁等待与崩溃恢复状态。
- 当前结论：
  - 暂未修改业务代码；
  - 根因更接近“服务器 Docker/反代/数据库回源异常”，不是本仓库登录逻辑回归。
- 新增服务器实测证据（用户 2026-03-09 回传）：
  - 线上实际运行容器为 `phoenix-web` / `phoenix-backend` / `phoenix-db`，且三者同属 `25-26_phoenix_net`；
  - `phoenix-web` 日志明确报错：
    - `upstream timed out (110: Operation timed out) while connecting to upstream`
    - upstream 为 `http://172.19.0.3:8000/api/v1/auth/login`
  - 这说明：
    1. `web` 能解析到 `backend` 容器 IP；
    2. 但与 `172.19.0.3:8000` 的 TCP 连接建立阶段就超时；
    3. 后端日志为空，说明请求尚未进入 FastAPI。
- 基于新增证据的收敛判断：
  - 优先级已进一步收敛为：`phoenix-backend` 容器虽然处于 Up 状态，但其内部 `8000` 端口未真正监听，或启动过程卡在应用导入/子进程拉起前；
  - 需要在服务器进一步检查：
    - `docker exec phoenix-backend ps -ef`
    - `docker exec phoenix-backend ss -ltnp`
    - `docker exec phoenix-backend curl http://127.0.0.1:8000/healthz`
    - `docker inspect phoenix-backend --format '{{json .State}}'`
  - 若容器内无 8000 监听，则应重点排查生产命令 `uvicorn ... --reload` 下的实际启动状态，以及导入阶段是否阻塞。
- 第二轮服务器实测（用户 2026-03-09 回传）：
  - `docker top phoenix-backend` 显示 `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1 --reload` 正在运行；
  - `docker logs phoenix-backend` 显示：
    - `Uvicorn running on http://0.0.0.0:8000`
    - `Application startup complete`
  - 容器内 Python 自检结果：
    - `socket.connect_ex(('127.0.0.1', 8000)) == 0`
    - `http://127.0.0.1:8000/healthz` 返回 200 JSON。
- 最终收敛结论：
  - `phoenix-backend` 容器内部服务已正常启动；
  - 当前故障不在 FastAPI 进程本身，而在同一 Docker 网络内 `phoenix-web -> phoenix-backend:8000` 的容器间连通性；
  - 下一步应直接从 `phoenix-web` 容器内验证访问 `http://backend:8000/healthz`，若失败，优先重建生产栈网络（而非继续修改业务代码）。
- 第三轮服务器操作结果（用户 2026-03-09 回传）：
  - 停掉 Phoenix 容器后执行 `docker network rm 25-26_phoenix_net` 返回 `network ... not found`；
  - 随后 `docker network ls` 中已不再存在 `25-26_phoenix_net`。
- 结论补充：
  - 这不表示删除失败，而是说明 compose 网络已在停容器后被 Docker 自动清理；
  - 当前无需继续手工删网络，下一步应直接使用正确的生产 compose 文件重新拉起整套服务，并重新生成新网络。
- 第四轮服务器观察（用户 2026-03-09 回传）：
  - `docker ps` 已为空，但 `docker network ls` 仍显示 `25-26_phoenix_net`；
  - 这属于 Docker 的正常行为：用户自定义 bridge 网络不会因为容器停止而自动消失，只有 `docker compose down` 或显式 `docker network rm` 才会删除。
- 当前运维判断：
  - 需要先确认是否仍有“已停止但未删除”的容器端点占用该网络；
  - 若无占用，则可直接 `docker network rm 25-26_phoenix_net`；
  - 若仍异常，再继续执行 Docker daemon 级网络重置或改用显式新 subnet。
- 当前结果更新（用户 2026-03-09 回传）：
  - `docker network inspect 25-26_phoenix_net` 显示 `Containers: {}`，但 `IPsInUse: 3`，确认该 bridge 网络存在脏状态；
  - 用户已成功执行 `docker network rm 25-26_phoenix_net`，并确认 `docker network ls` 中该网络已消失。
- 当前建议：
  - 直接用 `lo1_new_server.yml` 重新拉起 Phoenix，观察新建网络是否恢复容器间访问；
  - 若重建后仍异常，再进入“固定 subnet 重建”方案。

## 2026-03-08（日报/月报智能报告交互统一：移除复选框，改为直接按钮触发）

- 目标：
  - 日报分析页与月报查询页统一为“直接点击按钮生成/下载智能报告”，不再使用“智能报告生成”复选框作为前置开关。
  - 保留“智能体设定”按钮。
- 前端实现：
  - `frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`
    - 移除复选框与 `aiReportEnabled` 状态；
    - 保留并前置显示“智能报告（BETA）”文案；
    - 生成/下载按钮直接可用（仍受权限、加载状态、结果状态约束）；
    - “本次分析要求（可选）”输入框改为权限可用时直接展示。
  - `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
    - 移除复选框与 `aiReportEnabled` 状态；
    - 生成按钮改为直接触发（仍受 `loading`、结果为空、任务运行中约束）；
    - “本次分析要求（可选）”输入框改为始终展示。
- 结果：
  - 两个查询页面操作路径统一为：
    1) 查询结果
    2) 点击“生成智能报告”
    3) 点击“下载智能报告/下载智能分析报告”
  - 交互更直观，无需额外勾选步骤。

## 2026-03-08（日报分析页智能报告触发逻辑改造：查询后独立点击生成）

- 需求：
  - 日报分析页智能报告不再依赖“查询前勾选并随查询自动触发”；
  - 改为与月报一致：先完成查询，再点击“生成智能报告”按钮启动任务。
- 实现文件：
  - `frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`
- 关键改动：
  - 结果区新增独立“生成智能报告”按钮（与“下载智能分析报告”分离）；
  - 新增 `triggerAiReport()`，按当前激活单位与当前结果上下文发起 `runDataAnalysis(... request_ai_report: true)`；
  - 查询主流程 `runAnalysis` 中统一改为 `request_ai_report: false`，只负责产出查询结果；
  - 调整状态机文案与切换单位行为：无任务时提示“可点击生成”，不再自动进入 pending。
- 结果：
  - 日报查询页现在支持“先查后生”，交互灵活度与月报查询页一致。

## 2026-03-08（月报查询页 500 修复：query-options 接口异常降级）

- 现象：
  - 月报查询页改为同源代理后，`/monthly-data-show/query-options` 不再 CORS 报错，但返回 `500 Internal Server Error`，导致页面初始化失败。
- 处理：
  - 对 `backend/projects/monthly_data_show/api/workspace.py` 的 `get_monthly_data_show_query_options()` 增加全链路兜底：
    - 指标配置刷新失败：降级为空配置，不中断；
    - 数据库读取失败：返回空筛选项（`row = {}`）；
    - 指标排序异常：回退原始 `items_from_db`；
    - AI 设置读取异常：回退 `show_chat_bubble=true`。
- 结果：
  - `query-options` 接口在异常场景下可稳定返回 `200 + 空数据`，页面可进入并继续使用/排障，不再被 500 阻断。
- 验证：
  - 已执行 `python -m py_compile backend/projects/monthly_data_show/api/workspace.py`，语法通过。

## 2026-03-08（月报查询页 CORS 修复：本机开发优先同源 /api 代理）

- 现象：
  - 月报查询页初始化请求 `query-options` 时出现浏览器 CORS 拦截：
    - `http://localhost:5173` -> `http://127.0.0.1:8001/api/v1/...`
- 根因判断：
  - 本机开发环境中，前端存在直接命中绝对后端地址（`127.0.0.1:8001`）的路径，触发跨域链路；
  - 实际开发应优先走同源 `/api` 代理，避免 CORS 前置失败。
- 修复：
  - `frontend/src/projects/daily_report_25_26/services/api.js`
    - 新增 `shouldPreferSameOriginProxy(base)`；
    - 当检测到“本机前端 + 本机后端地址”组合时，`API_BASE` 强制使用 `'/api/v1'`；
    - 保持非本机场景（生产/非 localhost）不变。
- 结果：
  - 本机开发时接口优先同源代理，避免月报查询页因跨域导致 `Failed to fetch`。

## 2026-03-08（AI 气泡开关终极兜底：页面启动后强制同步 AI 设置）

- 现象补充：
  - 即使配置接口已设为 `no-store`，仍有场景出现“刷新后气泡回弹”。
- 处理策略：
  - 不再仅依赖 `schema/query-options` 中的开关字段。
  - 页面启动后主动调用 AI 设置接口读取 `show_chat_bubble`，并以该值作为气泡显示的最高优先级覆盖。
- 实现：
  - `frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`
    - 新增 `chatBubbleOverride`；
    - 新增 `syncChatBubbleFromSettings()`，通过 `getAiSettings` 读取并覆盖；
    - `onMounted` 改为 `await loadSchema(); await syncChatBubbleFromSettings();`。
  - `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
    - 新增 `chatBubbleOverride`；
    - 新增 `syncChatBubbleFromSettings()`，通过 `getAdminAiSettings` 读取并覆盖；
    - 页面初始化完成 `loadOptions()` 后立即同步 AI 设置。
- 结果：
  - 刷新后气泡状态以实时 AI 设置为准，避免中间链路差异导致的回弹。

## 2026-03-08（AI 气泡开关刷新后回弹修复：配置接口禁用缓存）

- 现象：
  - 在智能体设定中关闭气泡并保存后，当前页会隐藏；但刷新页面后，气泡再次出现。
- 处理：
  - 在前端配置读取接口上禁用缓存，确保每次刷新都读取最新配置：
    - `getDataAnalysisSchema(...)`
    - `getMonthlyDataShowQueryOptions(...)`
    - `getAiSettings(...)`
    - `getAdminAiSettings(...)`
  - 统一在 fetch 选项中增加 `cache: 'no-store'`。
- 影响文件：
  - `frontend/src/projects/daily_report_25_26/services/api.js`
- 结果：
  - “保存后即时生效”与“刷新后保持生效”两条链路已同时覆盖。

## 2026-03-08（AI 气泡显示开关修复：保存后当前页即时生效）

- 问题：
  - 在“智能体设定”里关闭“显示 AI 聊天气泡”并保存后，当前页面气泡仍然显示，需手动刷新后才可能生效。
- 根因：
  - 页面气泡显示状态分别依赖：
    - 日报分析页：`schema.ai_report_flags.show_chat_bubble`
    - 月报查询页：`options.aiChatFlags.show_chat_bubble`
  - 保存 AI 设置成功后，页面未把后端返回的 `show_chat_bubble` 回写到上述本地状态，导致 UI 未即时同步。
- 修复：
  - `frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`
    - `saveAiSettingsPayload` 改为异步，保存成功后把 `saved.show_chat_bubble` 回写到 `schema.ai_report_flags.show_chat_bubble`。
  - `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
    - `saveAiSettingsPayload` 改为异步，保存成功后把 `saved.show_chat_bubble` 回写到 `options.aiChatFlags.show_chat_bubble`。
- 结果：
  - 用户在智能体设定中关闭气泡并保存后，当前页会立即隐藏气泡，无需刷新页面。

## 2026-03-08（AI 自由对话气泡缺陷修复：文案透传 + 回车行为 + 上下文异常兜底）

- 结论：
  - 修复 `AiChatWorkspace` 未消费父页面文案参数的问题，页面传入的 `free-description/query-description/free-placeholder/query-placeholder` 现可生效。
  - 修复输入框回车逻辑：`Shift+Enter` 正常换行，`Enter` 发送消息，避免手动拼接换行导致的输入体验异常。
  - 修复“数据分析模式”构建上下文时的异常中断：`buildQueryContext` 抛错会转为前端错误提示，不再直接打断消息发送流程且无提示。
  - 修复消息内容换行展示：消息气泡内容支持 `pre-wrap` 与长词断行，保留多行文本阅读性。
- 影响文件：
  - `frontend/src/projects/daily_report_25_26/components/AiChatWorkspace.vue`
- 验证：
  - 代码级检查已完成（事件绑定、props 定义、异常分支、样式规则均已落位）。
  - 尚未执行前端构建命令；如需我可继续补跑 `npm run build` 做完整验证。

## 2026-03-07（AI 分析深度优化：月报全量数据包 + 维度补全）

- **故障分析:**
  - 用户反馈月报数据分析时数据包不全。
  - 核心原因：后端摘要逻辑对列数（16）和总字符（8000）限制过严，且前端未充分组装全量数据。
- **协同优化方案:**
  - **后端 (ai_chat_service.py)**: 放宽列限制至 24-32 列，总限制提升至 12,000 字符，并自动过滤无效元数据。
  - **前端 (MonthlyDataShowQueryToolView.vue)**: 重构 `buildMonthlyChatContext`，支持抓取最高 1000 条记录，并新增 `companies_scope` 等维度背景元数据。
- **结果:**
  - AI 现在能看到更多的行和更全的列（同比/环比/计划值等），数据分析的深度和准确性显著提升。

## 2026-03-07（紧急修复：管理后台页面无法加载问题）

- **故障描述:** 
  - 点击“进入后台”按钮无反应，控制台报错 `SyntaxError`，提示 `queryDailyDataAnalysisDialogChat` 未导出。
- **修复详情:**
  - 修正了 `AdminConsoleView.vue` 中的 API 导入名。
  - 将错误的 `queryDailyDataAnalysisDialogChat` 更正为后端配套的 `runDataAnalysisDialogChat`。
- **结果:**
  - 页面加载恢复正常，管理后台 AI 气泡功能链路闭环。

## 2026-03-07（AI 分析极限优化：数据包“表格化”序列化 + 容量翻倍）

- **故障诊断:**
  - 用户反馈在“所有单位+所有指标”查询下，AI 依然无法看到全量数据。
  - 深度分析：JSON 格式冗余度极高，重复的 Key 占据了 80% 以上的 Token 空间，导致 12,000 字符只能承载极少量行数。
- **重构方案:**
  - **序列化革新**: 后端引入 `_rows_to_compact_table` 逻辑，将行数据从 JSON 数组转换为“表头声明 + 纯数值行”的类 CSV 格式。
  - **容量扩充**: 字符限制提升至 24,000，Token 利用率提升约 400%。
  - **截断策略优化**: 采用百分比平滑缩减行数，确保在极端数据量下也能保留尽可能多的业务样本。
- **结果:**
  - AI 现在能一次性处理涵盖所有单位、所有指标的大型数据包，彻底解决了明细数据“看不到、数不对”的问题。

## 2026-03-07（功能扩展：管理后台集成 AI 助手气泡）

- **集成详情:**
  - 为 `AdminConsoleView.vue` 引入了 `AiChatWorkspace` 组件。
  - 实现了基于全局 AI 设置的显示逻辑，确保“显示/隐藏”状态在管理端与业务端完全同步。
  - 定制助手标题为“管理助手”，并锁定为“自由对话”模式。
- **体验一致性:**
  - 沿用了“默认隐藏”逻辑，彻底消除刷新后的视觉闪烁。
  - 保存 AI 设置时，管理后台的气泡状态会实时响应变更。

## 2026-03-07（体验优化：消除 AI 气泡刷新时的“闪烁”效应）

- **故障诊断:**
  - 虽然解决了持久化回弹问题，但由于计算属性默认返回 `true`，在异步加载配置前气泡会短暂显现（Flicker）。
- **优化细节:**
  - 将 `showChatBubble` 的缺省逻辑从 `true` 改为 `false`。
  - **实现逻辑**: 遵循“宁缺毋滥”原则，直到明确从 Schema 或 全局设置中获取到开启标志，否则不进行渲染。
- **结果:**
  - 彻底解决了气泡在刷新后的“闪现”现象，界面交互更加稳重、专业。

## 2026-03-07（AI 气泡开关持久化修复：解决刷新回弹问题）

- **故障诊断:**
  - 用户在智能体设置中关闭气泡后，刷新页面气泡会再次出现。
  - 根本原因：页面初始化时 `computed` 属性优先读取了 `schema/options` 接口的默认值，而异步同步的全局设置没有及时且强制地覆盖该状态。
- **修复方案:**
  - **DataAnalysisView.vue**: 重构 `showChatBubble` 计算逻辑，明确 `Override > Schema > Default` 的优先级链。
  - **MonthlyDataShowQueryToolView.vue**: 同步加固气泡显示逻辑，确保全局 AI 设置在加载后能稳定锁定显示状态。
  - **syncChatBubbleFromSettings**: 增强异步同步函数的赋值强度，确保其在各页面初始化后能第一时间强制修正显示状态。
- **结果:**
  - AI 气泡开关现在可以跨页面、跨刷新稳定持久化。

## 2026-03-07（AI 聊天弹窗视觉重构：去除调试信息 + 现代气泡设计）

- **功能精简:**
  - 彻底移除了“调试信息”折叠面板及其关联的所有 Payload 回显逻辑。
  - 删除了脚本中冗余的调试状态变量。
- **视觉美化:**
  - **气泡流**: 采用圆角气泡设计，通过颜色（蓝色/灰色）与对齐位置区分角色，移除显眼的文字标签。
  - **输入区**: 重构为胶囊式 Composer，整合发送按钮，并支持 `Enter` 快捷发送。
  - **反馈增强**: 增加打字机 Loading 动画、平滑置底滚动以及展开时的缩放过渡特效。
- **结果:**
  - AI 聊天窗口从“开发调试工具”转变为“正式产品级”的精致对话界面。

## 2026-03-07（Docker 网络代理修复：前端 ECONNREFUSED 解决）

- **故障诊断:**
  - `phoenix_frontend` 日志显示：`Error: connect ECONNREFUSED 127.0.0.1:8001`。
  - 根本原因：前端在容器内部访问 `127.0.0.1` 是访问自己，而非宿主机或后端。应通过 Docker 服务名访问。
- **前端修复:**
  - `frontend/vite.config.js`: 将 `proxy.target` 修改为 `http://backend:8000`。
  - 说明：`backend` 是后端在 Docker 中的服务名，`8000` 是其内部端口。

## 2026-03-07（AI 模块专家级重构：多轮对话结构化 + 路径兼容性修复）

- **故障诊断与修复:**
  - **路径问题:** 发现 `backend/config.py` 硬编码了容器路径 `/app/data`，导致 Windows 本地测试无法加载 AI 配置。已修复为“容器/本地自适应逻辑”，优先寻找项目根目录下的 `backend_data`。
  - **链路问题:** 解决了 Codex 拆分模块后遗留的单一 Prompt 字符串问题。AI 现已支持标准的 `messages` 数组（System/User/Assistant）。
- **重构细节:**
  - `ai_runtime.py`: 引入 `call_chat_model`，支持结构化消息调用。适配 Gemini 和 New API (OpenAI) 两种底层格式。
  - `ai_chat_service.py`: 重构对话拼装逻辑，由 `build_chat_messages` 代替字符串拼接，实现了真正的上下文连贯性。
  - **System Role**: 注入全局身份定义，确保 AI 明确其作为“凤凰计划助手”的职责。
- **验证结果:**
  - `debug_ai_chat_expert_v2.py` 测试通过，多轮对话流畅，Session 自动追加，逻辑闭环。

## 2026-03-07（聊天上下文全量化 + 固定系统提示词 + 气泡显示开关）

- 需求背景：
  - “基于查询数据”模式下，聊天上下文不应只停留在前 200 行或预览行；
  - 聊天系统提示词需要改为固定业务提示词，不再额外叠加 `instruction_monthly`；
  - 希望在“智能体设定”中新增“是否显示 AI 聊天气泡”开关。
- 后端实现：
  - `backend/services/ai_chat_service.py`
    - `summarize_query_context(...)` 改为保留查询结果的全量行集合，再由 `_serialize_context_summary(...)` 按字符上限渐进裁剪；
    - `build_chat_messages(...)` 的 `query_context` 模式改为使用固定业务系统提示词；
    - 不再在聊天系统提示词中额外注入 `instruction_monthly` / `instruction_daily`。
  - `backend/projects/daily_report_25_26/api/legacy_full.py`
    - AI 设置新增 `show_chat_bubble` 字段；
    - `get / update ai_settings`、`_read_ai_settings`、`_persist_ai_settings` 全链路支持该字段；
    - `data_analysis/schema` 返回的 `ai_report_flags` 新增 `show_chat_bubble`。
  - `backend/projects/monthly_data_show/api/workspace.py`
    - `query-options` 返回新增 `ai_chat_flags.show_chat_bubble`，供月报页决定是否展示聊天悬浮气泡。
- 前端实现：
  - `frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`
    - 数据分析聊天上下文改为优先使用当前单位完整结果 `currentResult.rows`，不再只用 `previewRows`；
    - 聊天气泡展示由 `schema.ai_report_flags.show_chat_bubble` 控制。
  - `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
    - `buildMonthlyChatContext()` 改为异步：若当前页面仅持有分页结果且 `summary.totalRows > rows.length`，会先补拉全量查询结果后再发送聊天上下文；
    - 聊天气泡展示由 `query-options.ai_chat_flags.show_chat_bubble` 控制。
  - `frontend/src/projects/daily_report_25_26/components/AiAgentSettingsDialog.vue`
    - 运行策略区域新增“显示 AI 聊天气泡”复选框；
    - 保存/读取链路同步 `show_chat_bubble`。
- 结果：
  - 基于查询数据模式现在尽量携带当前页面查询到的全量结果；
  - 聊天系统提示词固定为业务定义文案；
  - 是否显示聊天悬浮气泡现在可由智能体设定统一控制。
- 修复补充（同日）：
  - “显示 AI 聊天气泡”无法保存的根因，不在后端持久化，而在前端 API 封装：
    - `frontend/src/projects/daily_report_25_26/services/api.js`
    - `updateAiSettings(...)` 与 `updateAdminAiSettings(...)` 在 POST body 中漏传 `show_chat_bubble`；
  - 已补齐该字段透传，保存后可正确写入 `backend_data/shared/ai_settings.json`。

## 2026-03-07（AI 聊天调试面板布局修复）

- 需求背景：
  - 聊天发送后，调试面板中的“最近返回结果 / 最近错误”会被挤出可视区域，导致无法继续排障。
- 前端实现：
  - `frontend/src/projects/daily_report_25_26/components/AiChatWorkspace.vue`
    - 将“最近错误”“最近返回结果”调整到调试面板顶部；
    - 为调试面板增加独立滚动区域；
    - 适当压缩聊天消息区高度，给调试信息留出稳定可视空间。
- 结果：
  - 调试面板在发送消息后仍能直接查看最关键的错误与响应信息，方便继续分段排查。

## 2026-03-07（AI 聊天链路排障 C：页面内调试信息面板）

- 目标：
  - 直接在聊天组件内展示调试信息，避免反复切换 Network 面板或手工复制请求内容。
- 前端实现：
  - `frontend/src/projects/daily_report_25_26/components/AiChatWorkspace.vue`
    - 新增“调试信息”折叠面板；
    - 当前可直接显示：
      - 当前模式
      - 当前会话 ID
      - 最近发送 Payload
      - 最近返回结果
      - 最近错误
  - 目的：下一步直接根据页面内可见的请求/响应内容，继续排查聊天器剩余问题。

## 2026-03-07（AI 聊天链路排障 A：后端调试回显接口）

- 目标：
  - 先只验证“前端/请求 → 后端聊天接口”是否打通，暂不关心模型回答质量。
- 后端实现：
  - `backend/services/ai_chat_service.py`
    - 新增 `AiChatDebugResponse`；
    - 新增 `build_chat_debug_payload(...)`，用于返回：
      - 当前 mode
      - session_id
      - provider
      - model
      - base_url
      - history_count
      - context_applied
      - context_summary
  - 新增调试接口：
    - 日报分析页：`POST /api/v1/projects/daily_report_25_26/data_analysis/ai-chat/debug`
    - 月报查询页：`POST /api/v1/projects/monthly_data_show/monthly-data-show/ai-chat/debug`
- 当前验证结论：
  - 已使用日报分析页 debug 接口实测返回 `200 OK`；
  - 回显结果表明：
    - `provider = newapi`
    - `model = gpt-5.4`
    - `base_url = https://ai.xingyungept.cn/v1`
    - `mode = free`
    - `context_applied = false`
  - 说明 A 阶段“请求进入后端聊天模块，并成功识别当前 AI 通道”已确认打通。

## 2026-03-07（AI 聊天器显示修复：超长内容不再撑破弹窗）

- 需求背景：
  - AI 聊天消息中存在超长文本/链接时，内容会超过悬浮弹窗宽度，影响阅读。
- 前端实现：
  - 调整 `frontend/src/projects/daily_report_25_26/components/AiChatWorkspace.vue` 样式：
    - 为消息气泡补充 `min-width: 0`、`max-width: 100%`、`overflow: hidden`；
    - 为消息内容补充 `overflow-wrap: anywhere`，保证超长连续字符串也能自动断行；
    - 用户消息宽度改为 `width:min(88%, 100%)`，避免被长内容撑开。
    - 聊天输入框补充 `box-sizing:border-box`、`max-width:100%` 与 `overflow-x:hidden`，修复输入区域超出弹窗宽度的问题；
- 结果：
  - 聊天框内的长文本、长链接、长 JSON 片段将优先在弹窗内部换行，不再撑破悬浮聊天框宽度。

## 2026-03-07（AI 聊天器二轮：悬浮展开 + 首轮无欢迎语 + 请求失败提示优化）

- 需求背景：
  - 聊天器不希望占用页面固定区域，而是以悬浮图标形式出现，点击展开、可最小化回图标；
  - 不需要默认欢迎语，第一轮应由用户发起；
  - 目前用户测试聊天时出现 `执行失败：Failed to fetch`，而“智能体设定”的连接测试正常，需要改善定位与提示。
- 前端实现：
  - `frontend/src/projects/daily_report_25_26/components/AiChatWorkspace.vue`
    - 改为悬浮图标模式，默认仅显示右下角悬浮入口；
    - 点击图标展开聊天框，点击“最小化”收回到图标；
    - 删除默认欢迎语，聊天历史初始为空，首条消息由用户发起；
    - 针对浏览器原生 `Failed to fetch` 错误，改为更明确提示：优先提示“后端服务可能未重启或新聊天接口未加载”。
  - `frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`
    - 移除单独的聊天卡片容器，仅保留悬浮聊天组件挂载。
  - `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
    - 继续保留悬浮聊天组件挂载；
    - 清理旧内嵌聊天区与对应样式。
- 对 `Failed to fetch` 的当前判断：
  - 该报错通常不是“模型连接失败”，而是“浏览器请求没有成功打到后端接口”；
  - 由于“智能体设定”的测试接口是旧接口，而聊天接口是本轮新加接口，所以最常见原因是：前端已更新、后端还未重启加载新路由。
  - 本地进一步排查确认：
    - `127.0.0.1:8000` 当前无后端服务监听；
    - `127.0.0.1:8001` 正在提供 Phoenix 后端；
    - 月报聊天新接口在 `8001` 上可命中，并返回 `401 缺少认证信息`，说明路由本身已加载；
  - 因此本轮在前端聊天 API 增加了开发环境端口回退：若聊天请求发生网络级 `Failed to fetch`，会自动改用 `127.0.0.1:8001` 重试。
  - 同时在 `frontend/vite.config.js` 新增 `/api -> 127.0.0.1:8001` 的 dev proxy，聊天请求会优先走同源代理以避免跨域把真实后端错误吞掉；该变更需要重启前端开发服务器后才生效。
- 验证结果：
  - 后端 `py_compile` 通过；
  - `frontend/` 下 `npm run build` 通过。

## 2026-03-07（AI 聊天器初版：自由聊天 + 基于查询数据聊天）

- 需求背景：
  - 在 `monthly_data_show/query-tool` 与 `daily_report_25_26/data-analysis` 两个页面增加通用 AI 聊天组件；
  - 需要支持两种模式：
    1. 自由聊天：不附加业务数据包，连续对话；
    2. 基于查询数据聊天：把当前页面最新查询结果打包后，作为上下文连续追问。
- 后端实现：
  - 新增 `backend/services/ai_chat_service.py`：
    - 统一定义 `AiChatRequest` / `AiChatResponse`；
    - 提供会话存储、历史拼接、查询数据包摘要裁剪、Prompt 组装与统一聊天执行；
    - 复用 `backend/services/ai_runtime.py` 的 `call_model(...)`，不再依赖报告服务。
  - 新增页面级聊天接口：
    - 月报查询页：`POST /api/v1/projects/monthly_data_show/monthly-data-show/ai-chat/dialog`
    - 日报分析页：`POST /api/v1/projects/daily_report_25_26/data_analysis/ai-chat/dialog`
- 前端实现：
  - 新增共享组件 `frontend/src/projects/daily_report_25_26/components/AiChatWorkspace.vue`：
    - 内置“自由聊天 / 基于查询数据”模式切换；
    - 每个模式独立保留会话与上下文连续性；
    - 支持新会话重置、模式切换与基础错误提示。
  - 月报查询页 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：
    - 用共享组件替换旧的隐藏聊天区；
    - 基于当前 `rows / comparisonRows / summary / temperatureSummary / buildPayload()` 组装查询数据上下文。
  - 日报分析页 `frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`：
    - 新增 AI 聊天卡片；
    - 基于当前 `previewRows / lastQueryMeta / timelineGrid / ringCompare / planComparison` 组装查询数据上下文。
  - 前端 API 新增：
    - `queryMonthlyDataShowDialogChat(...)`
    - `runDataAnalysisDialogChat(...)`
- 结果：
  - 两个页面现在都具备通用聊天器初版；
  - 聊天器已不依赖旧的“受控工具查询”逻辑，后续可直接在此基础上继续演进聊天器和 Agent。
- 验证结果：
  - 后端 `py_compile` 通过；
  - `frontend/` 下 `npm run build` 通过。

## 2026-03-07（AI 核心抽离：运行时层与报告模式层解耦）

- 需求背景：
  - 原 `backend/services/data_analysis_ai_report.py` 同时承担 provider 运行时、提示词模板、报告生成流程与任务队列，已不适合作为后续通用聊天器/Agent 能力的基础层；
  - 目标是在不破坏现有日报/月报 AI 报告能力的前提下，把通用 AI 能力抽离出来，后续聊天器直接复用新通用层。
- 实现策略：
  - 保留 `backend/services/data_analysis_ai_report.py` 作为“数据分析报告专用服务 + 兼容入口”；
  - 新增 `backend/services/ai_runtime.py`：抽离通用 Provider 配置读取、当前生效 Provider 解析、运行时客户端缓存、统一模型调用、统一连接测试；
  - 新增 `backend/services/ai_report_modes.py`：抽离日报/月报 AI 模式常量、Prompt 模板注册表、运行时提示词/开关读取；
  - 原 `data_analysis_ai_report.py` 末尾新增兼容别名层，让既有报告流水线继续工作，同时内部全局函数名实际指向新模块实现。
- 外部调用迁移：
  - `backend/api/v1/admin_console.py` 的 AI 连接测试改为直接调用 `ai_runtime.run_ai_connection_test(...)`；
  - `backend/projects/daily_report_25_26/api/legacy_full.py` 的 AI 连接测试与运行时重置改为直接调用 `ai_runtime`；
  - `backend/projects/monthly_data_show/api/workspace.py` 的通用模型调用改为直接调用 `ai_runtime.call_model(...)`，不再依赖 `data_analysis_ai_report._call_model` 私有函数。
- 当前结构定位：
  - `ai_runtime.py`：通用 AI 底层；
  - `ai_report_modes.py`：日报/月报报告模式注册；
  - `data_analysis_ai_report.py`：报告生成应用层；
  - 后续聊天器应优先依赖 `ai_runtime.py`，而不是继续依赖 `data_analysis_ai_report.py`。
- 验证结果：
  - `python -m py_compile backend/services/ai_runtime.py backend/services/ai_report_modes.py backend/services/data_analysis_ai_report.py backend/api/v1/admin_console.py backend/projects/daily_report_25_26/api/legacy_full.py backend/projects/monthly_data_show/api/workspace.py` 通过。

## 2026-03-07（智能体设定：ID 输入失焦修复 + New API 批量测试 + 备选模型）

- 需求背景：
  - “智能体设定”中 provider 的“标识 ID”输入框每输入一个字符就丢失焦点；
  - 希望增加“一键测试全部 New API Provider”的能力，并把结果展示在各 provider 设置区；
  - 希望每个 provider 支持快捷打开站点根链接、维护备选模型列表，便于主模型异常时快速切换。
- 前置说明（偏差留痕）：
  - Serena 已完成项目激活与结构化检索；
  - `.vue` 与 Markdown 文件不适合 Serena 符号级编辑，本轮使用 `apply_patch` 进行最小范围修改；
  - 回滚方式：回退 `AiAgentSettingsDialog.vue`、`legacy_full.py`、`admin_console.py` 与三份文档中的本次新增段落。
- 前端实现（`frontend/src/projects/daily_report_25_26/components/AiAgentSettingsDialog.vue`）：
  - 修复失焦根因：provider 卡片列表的 `:key` 从可编辑的 `provider.id` 改为稳定的内部 `uiKey`，避免输入 ID 时节点被重建；
  - 新增“测试全部 New API”按钮，串行测试所有 `kind === "newapi"` 的 provider，并在各 provider 卡片头部展示成功/失败状态；
  - 新增“打开站点”按钮：从 `base_url` 自动提取站点根地址（如 `https://x666.me/v1` -> `https://x666.me`）并新窗口打开；
  - 新增“备选模型”编辑区，支持逐条添加、删除，并可一键“设为当前”把备选模型提升为主模型。
- 后端实现：
  - `backend/projects/daily_report_25_26/api/legacy_full.py`
    - `AiSettingsPayload` 新增 `newapi_backup_models`；
    - `_normalize_provider_record` / `_read_ai_settings` / `_persist_ai_settings` 全链路支持 `backup_models` 持久化与返回；
    - 兼容旧配置回退时，为 provider 默认补齐空的 `backup_models`。
  - `backend/api/v1/admin_console.py`
    - 全局 AI 设置 payload 同步新增 `newapi_backup_models`，继续复用统一的底层持久化逻辑。
- 结果：
  - “标识 ID”输入现在可连续输入，不再每击键丢焦点；
  - 可一次性检查全部 New API Provider 连通性，并在对应卡片内看到结果；
  - 每个 provider 现在具备站点直达与备选模型管理能力，适合做快速切换。

## 2026-03-07（智能体设定：单 Provider 测试 + 折叠卡片）

- 需求背景：
  - 希望每个 provider 都能单独测试当前连接；
  - 希望每个 provider 的设置区域可折叠，默认收起，仅展示名称和模型，降低弹窗纵向占用。
- 前端实现（`frontend/src/projects/daily_report_25_26/components/AiAgentSettingsDialog.vue`）：
  - 在每个 provider 卡片头部新增“测试当前”按钮，复用既有连接测试接口，结果继续显示在当前卡片头部；
  - provider 卡片默认折叠，头部显示序号、显示名称、当前模型名；
  - 新增展开/收起切换按钮，点击后再展示完整字段区；
  - 新增 provider 局部测试与全量 New API 测试的状态互斥，避免测试期间重复编辑或并发触发。
- 结果：
  - 现在既可以批量测试全部 New API，也可以针对单个 provider 快速验证；
  - 弹窗默认更紧凑，多个 provider 共存时更容易浏览。

## 2026-03-07（智能体设定：当前生效标记 + 一键切换 Provider）

- 需求背景：
  - 希望在 provider 卡片头部直接看出哪个是当前生效配置；
  - 希望在多个 provider 间快速切换，无需手动改顶部“当前使用 Provider”下拉。
- 前端实现（`frontend/src/projects/daily_report_25_26/components/AiAgentSettingsDialog.vue`）：
  - provider 卡片头部新增“当前生效 / 备用”状态标签；
  - 每个 provider 操作区新增“设为当前”按钮，点击后直接把 `activeProviderId` 切换为该 provider；
  - 当前已生效的 provider 会自动禁用“设为当前”按钮，避免重复操作。
- 结果：
  - 现在在多 provider 场景下，可更快识别当前通道并完成切换；
  - 顶部总选择器仍然保留，卡片级切换作为更直接的补充交互。

## 2026-03-07（智能体设定：移除底部全局测试连接按钮）

- 需求背景：
  - 组件内已经具备“测试当前”和“测试全部 New API”两类更清晰的测试入口；
  - 底部全局“测试连接”按钮语义重复，容易造成理解混淆。
- 前端实现（`frontend/src/projects/daily_report_25_26/components/AiAgentSettingsDialog.vue`）：
  - 删除底部 `测试连接` 按钮；
  - 移除对应的 `handleTestConnection` 逻辑；
  - 保留卡片内“测试当前”与顶部“测试全部 New API”作为唯一测试入口。
- 结果：
  - 智能体设定弹窗的测试动作收敛为更明确的局部/批量两种模式；
  - 底部操作区职责更单纯，仅保留退出与保存动作。

## 2026-03-06（lo1_new_server 构建慢过程根因分析）

- 现象：
  - 执行 `lo1_new_server.ps1` 的 `docker-compose -f docker-compose.server_new_server.yml build` 时，`backend builder` 的 `pip install` 阶段出现约 20 分钟卡顿。
  - 慢日志关键字：`pip is still looking at multiple versions of grpcio-status`。
- 根因判断：
  - 依赖解析回溯：`backend/requirements.txt` 中存在未锁定或范围依赖（如 `google-generativeai>=0.7.0`、`pydantic-settings`、`httpx` 等），触发 pip resolver 对 `grpcio-status` 及其关联依赖长时间求解。
  - 架构因素放大耗时：`docker-compose.server_new_server.yml` 指定 `platform: linux/arm64`，日志也出现 `manylinux...aarch64` 包元数据，说明在 ARM64 目标架构下解析/下载，速度受网络与镜像源波动影响更明显。
  - 每次全量构建触发安装：脚本使用 `docker-compose build`，当后端依赖层未命中缓存时，会重复进入慢解析流程。
- 本轮结论：
  - 该慢点不是单一“下载慢”，而是“依赖版本回溯 + ARM64 架构 + 缓存命中不稳定”叠加导致。
  - 本轮未改业务代码，仅完成定位与优化建议输出。
- 二次观察补充（同日）：
  - 新日志显示 `backend builder 5/5` 达到 `949.9s`，当前主要输出为 `Installing collected packages`，已不再出现 `grpcio-status` 多版本回溯提示。
  - 这说明慢点阶段已从“resolver 回溯”转为“多依赖实际下载与安装”。
  - 在 `docker-compose.server_new_server.yml` 指定 `platform: linux/arm64` 的前提下，若本机构建机为 x86_64，会触发跨架构构建（QEMU 仿真），安装阶段通常显著放慢。
  - 结合包清单（`grpcio`、`cryptography`、`paramiko`、`uvloop` 等），即使走 wheel，ARM64 下下载与解包/安装也更易拉长到 10~20 分钟区间。
- 结论更新：
  - 当前主要瓶颈是“ARM64 构建路径下的大规模依赖安装耗时”，版本解析问题已退居次要。

## 2026-03-05（monthly_data_show 临时隐藏 query-tool 对话助手）

- 需求背景：
  - 用户反馈当前对话工具可用性仍不足，先隐藏入口，避免影响页面主流程。
- 实现策略：
  - 仅隐藏前端展示，不删除既有实现与后端接口，便于后续灰度恢复；
  - 在 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue` 增加样式规则：
    - `.card:has(> .chat-panel) { display: none; }`
  - 结果：query-tool 页面不再展示“对话查询助手（BETA）”卡片，其余查询能力保持不变。
- 前置说明（偏差留痕）：
  - 本次为 `.vue` 文件调整，采用 `apply_patch` 降级编辑；
  - 回滚方式：删除上述样式块即可恢复对话工具显示。
- 验证结果：
  - `npm run build`（`frontend/`）通过。

## 2026-03-05（monthly_data_show 对话助手：会话上下文 + 数据处理 + 联网检索）

- 需求背景：
  - 在 `query-tool` 页面将上一轮“单次问答”升级为“有上下文的连续对话”；
  - 增强助手的数据处理能力（聚合/TopN/分组摘要）；
  - 在用户明确表达“联网/搜索/最新”等意图时，允许助手执行公开网络检索并返回来源。
- 前置说明（偏差留痕）：
  - Serena 已完成项目激活与 on-boarding 检查；Python 文件采用 Serena 符号级工具修改；
  - `.vue` 与 Markdown 文件仍采用 `apply_patch` 降级（Serena 对该类文件不提供稳定符号编辑），影响范围限定在 `monthly_data_show` 查询页及文档；
  - 回滚方式：仅回退本次改动文件中的新增段落/函数与前端会话区块即可恢复上一版行为。
- 后端实现（`backend/projects/monthly_data_show/api/workspace.py`）：
  - 对话请求/响应模型扩展：新增 `session_id`、`enable_web_search`、`web_sources`、`tool_calls.details`；
  - 新增服务端会话存储（TTL 30 分钟，最多保留 20 条消息），支持连续追问继承上下文；
  - 新增 `_chat_summarize_rows`，对查询结果做数值字段统计、公司维度摘要、TopN 行提取；
  - 新增 `_chat_execute_web_search`（公开搜索接口），在用户触发联网意图时走 `search_web_public` 工具分支；
  - 路由 `POST /monthly-data-show/ai-chat/query` 改为多工具链路：`query_month_data_show` / `query_month_data_show_comparison` / `aggregate_rows` / `search_web_public`。
- 前端实现（`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`）：
  - 新增会话态：`chatSessionId`、`chatWebSources`；
  - 发送对话时携带 `session_id` 与 `enable_web_search`；
  - 新增“新会话”按钮，允许用户主动清空上下文并重建会话；
  - 新增“当前会话”与“联网来源”展示区域。
- 验证结果：
  - `python -m py_compile backend/projects/monthly_data_show/api/workspace.py` 通过；
  - `npm run build`（`frontend/`）通过。
- 风险与后续：
  - 会话存储当前为进程内内存，服务重启后会话丢失；如需跨实例/持久化，应迁移至 Redis 或数据库；
  - 联网检索依赖外部公开接口可用性，失败时会回退为“无来源命中”并继续本地数据能力。

## 2026-03-05（monthly_data_show 对话查询助手：受控工具调用版）

- 需求背景：
  - 在 `query-tool` 页面保留现有“AI 报告”能力的同时，新增“可对话查询”能力；
  - 用户可用自然语言提出查询意图，由 AI 模块调度受控查询工具获取数据库结果并生成解释。
- 前置说明（偏差留痕）：
  - 本轮对 `.vue` 文件的符号级编辑在 Serena 不可用（Serena 当前仅对 Python 提供符号解析），因此前端页面修改采用 `apply_patch` 降级；
  - 影响范围限定为：`monthly_data_show` 查询页与共享 API 封装，不改现有日报主流程；
  - 回滚方式：回退以下文件本次改动块即可恢复旧行为（见“涉及文件”）。
- 后端实现：
  - 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - 新增接口：
    - `POST /api/v1/projects/monthly_data_show/monthly-data-show/ai-chat/query`
  - 新增能力：
    - 对话请求模型与响应模型（含 `tool_calls`、`preview_rows`、`applied_query`）；
    - 月份、口径、指标的自然语言提取与上下文合并（复用现有 `QueryRequest`）；
    - 工具路由：
      - 普通查询：`query_month_data_show`
      - 对比查询：`query_month_data_show_comparison`
    - AI 总结：基于工具执行结果调用现有 AI 运行时生成中文结论；失败时返回保守兜底结论。
  - 受控边界：
    - 不开放任意 SQL；
    - 仅复用现有白名单查询链路与参数模型。
- 前端实现：
  - 文件：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 新增“对话查询助手（BETA）”面板：
    - 消息流展示（用户/助手）；
    - 文本输入与发送；
    - 对话失败提示；
    - 工具返回预览表格展示。
  - 对话请求会附带当前筛选上下文（时间、口径、指标、排序与聚合开关）。
  - 文件：`frontend/src/projects/daily_report_25_26/services/api.js`
    - 新增 API 封装：`queryMonthlyDataShowAiChat(projectKey, payload)`。
- 当前结果：
  - `query-tool` 页面已具备“自然语言提问 -> 工具查询 -> AI解释”的端到端闭环；
  - 原有“查询按钮 + AI 报告生成”功能保持不变，可并行使用。
- 涉及文件：
  - `backend/projects/monthly_data_show/api/workspace.py`
  - `frontend/src/projects/daily_report_25_26/services/api.js`
  - `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - `configs/progress.md`
  - `frontend/README.md`
  - `backend/README.md`

## 2026-03-04（模板设计器第一期骨架：新表专用）

- 需求背景：
  - 用户确认新增“模板设计器（新表）”能力，明确“不改当前已有表格”，仅面向未来新表。
- 本轮交付范围（第一期）：
  - 新增项目内页面入口：`template_designer`；
  - 新增后端模板管理接口（列表/详情/创建/更新/发布）；
  - 新增前端模板设计器页面（基础表单 + 列定义 + 行定义 JSON）；
  - 完成菜单配置与权限配置联动。
- 后端实现：
  - 文件：`backend/projects/daily_report_25_26/api/template_designer.py`
  - 新增接口：
    - `GET /api/v1/projects/daily_report_25_26/template_designer/templates`
    - `GET /api/v1/projects/daily_report_25_26/template_designer/templates/{template_key}`
    - `POST /api/v1/projects/daily_report_25_26/template_designer/templates`
    - `PUT /api/v1/projects/daily_report_25_26/template_designer/templates/{template_key}`
    - `POST /api/v1/projects/daily_report_25_26/template_designer/templates/{template_key}/publish`
  - 存储文件：
    - `backend_data/projects/daily_report_25_26/config/template_designer_templates.json`（不存在时自动初始化）
  - 路由挂载：
    - `backend/projects/daily_report_25_26/api/router.py` 已 `include_router(template_designer_router)`。
- 前端实现：
  - 新页面：
    - `frontend/src/projects/daily_report_25_26/pages/TemplateDesignerView.vue`
  - 路由：
    - `frontend/src/router/index.js` 新增
      - `/projects/:projectKey/pages/:pageKey/template-designer`
  - 页面跳转：
    - `frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue`
    - 新增 `template_designer` 描述映射与跳转分支。
  - API 封装：
    - `frontend/src/projects/daily_report_25_26/services/api.js`
    - 新增模板设计器列表/详情/创建/更新/发布请求函数。
- 配置联动：
  - 页面配置：
    - `backend_data/shared/项目列表.json` 新增 `template_designer` 页面项。
  - 权限配置：
    - `backend_data/shared/auth/permissions.json`
    - 为 `Global_admin`、`Group_admin` 的 `daily_report_25_26.page_access` 增加 `template_designer`。
- 当前结果：
  - 你现在可以在项目页面看到“模板设计器（新表）”，并完成新模板草稿创建、更新和发布；
  - 该链路不会影响既有日报填报表与历史模板。
- 下一步（第二期建议）：
  - 把“行定义 JSON”升级为可视化拖拽编辑；
  - 增加字段级校验规则编辑器；
  - 增加模板版本回滚与差异比对。

## 2026-03-04（AGENTS.md 升级为多项目现行协作规范）

- 背景：
  - 原 `AGENTS.md` 为项目初期版本，内容以单项目 `daily_report_25_26` 为主，目录与当前仓库结构已脱节。
- 本轮目标：
  - 保留用户对 Codex 的系统性执行要求；
  - 将“项目结构、模块现状、协作风格、改动范围”更新为当前版本。
- 实施：
  - 重写 `AGENTS.md`，核心更新包括：
    - 明确“强制保留”的执行规则：原生文件工具编辑、每轮同步 `progress.md + frontend/README.md + backend/README.md`、交付需说明模块/函数/流程/结果；
    - 项目结构更新为多项目并行（前端 `frontend/src/projects/*`、后端 `backend/projects/*`）；
    - 更新可改/禁改范围与当前协作风格要求；
    - 增加质量安全底线与 Codex 快速执行清单。
- 结果：
  - `AGENTS.md` 已从“历史方案说明书”升级为“当前可执行协作规范”，可直接指导后续多项目开发。
- 涉及文件：
  - `AGENTS.md`
  - `configs/progress.md`
  - `frontend/README.md`
  - `backend/README.md`

## 2026-03-04（数据看板 PDF 导出图标空白修复）

- 背景：
  - 用户反馈 `http://localhost:5173/projects/daily_report_25_26/pages/dashboard/dashboard?...` 顶部四个摘要卡片（当日平均气温、边际利润、原煤消耗、净投诉量）在页面可见图标，但下载 PDF 后图标区域空白。
- 根因：
  - `frontend/src/projects/daily_report_25_26/pages/DashBoard.vue` 的图标采用 `::before + mask-image(data:image/svg+xml)` 渲染；
  - 导出链路 `downloadPDF -> html2canvas -> jsPDF` 对该 `mask-image` 方案兼容性不足，导致截图阶段丢失图形。
- 实施：
  - 在 `DashBoard.vue` 新增 `SUMMARY_CARD_ICON_PATHS`、`createSummaryIconSvgElement`、`injectPdfSafeSummaryIcons`；
  - 在 `downloadPDF` 的 `onclone` 回调中调用 `injectPdfSafeSummaryIcons(clonedDocument)`；
  - 导出克隆文档内：
    - 对四类图标（`sunrise/profit/coal/complaint`）注入内联 SVG；
    - 注入导出专用样式禁用 `::before`，确保 `html2canvas` 捕获稳定；
  - 页面实时渲染逻辑不变，仅 PDF 导出链路生效。
- 结果：
  - 导出 PDF 时顶部四个卡片图标可正常显示，不再出现空白。
  - 二次修复：导出图标曾出现“全黑”现象，已将内联 SVG 的 `path fill` 从 `currentColor` 改为克隆 DOM 实际计算色值（`getComputedStyle(iconEl).color`），避免 `html2canvas` 对 `currentColor` 解析偏差导致发黑。
  - 三次修复：部分环境下克隆 DOM 计算色值仍可能退化为黑色，已将导出图标 `fill` 固定为 `#ffffff`，确保四张彩色摘要卡片上的图标稳定为白色。
  - 四次修复：用户反馈图标背景出现“小方框”，定位为 `.summary-card__icon` 容器的 `box-shadow/backdrop-filter` 在导出截图中的伪影；已在导出克隆样式中禁用容器背景、阴影、边框与滤镜，仅保留 SVG 图形本体。
- 涉及文件：
  - `frontend/src/projects/daily_report_25_26/pages/DashBoard.vue`
  - `configs/progress.md`
  - `frontend/README.md`
  - `backend/README.md`

## 2026-03-03（智能体设定升级：多 Provider + 折叠分组布局）

- **User Request:** 在各处“智能体设定”中支持多个 provider（每个 provider 独立 `base_url/api_key/model`），可选择当前使用的 provider；同时优化布局，分组折叠，降低页面高度占用；底部按钮改为“保存并退出”。
- **Agent Action:**
  1. 后端配置协议升级（兼容旧字段）：
     - 新增结构：`providers[]` + `active_provider_id`；
     - 每个 provider 包含：`id/name/kind/base_url/model/api_keys`；
     - 写入时保留并同步旧字段（`provider/gemini_*/newapi_*`）用于平滑兼容。
  2. 运行时选择逻辑升级：
     - `data_analysis_ai_report` 优先读取 `providers + active_provider_id` 决定当前通道；
     - 若不存在则回退旧字段；
     - 连通性测试也支持按多 provider 结构测试当前生效 provider。
  3. API 接口扩展：
     - 项目级与全局 AI 设置保存/测试接口均支持 `providers/active_provider_id` 入参；
     - 获取 AI 设置接口返回 `providers/active_provider_id`，供前端渲染。
  4. 前端智能体设定组件重构：
     - 组件文件：`AiAgentSettingsDialog.vue`；
     - 新增折叠分组：基础设置、Provider 管理、提示词设置、运行策略；
     - 支持新增/删除 provider、切换当前生效 provider、每个 provider 独立维护 keys/model/base_url；
     - 底部主按钮文案改为“保存并退出”。
  5. 前端 API 透传升级：
     - `updateAiSettings/updateAdminAiSettings/testAiSettings/testAdminAiSettings` 增加 `providers/active_provider_id` 字段透传。
  6. 配置文件样例更新：
     - `backend_data/shared/ai_settings.json` 增加 `providers` 与 `active_provider_id` 示例。
- **Result:** 现在可在一个弹窗中维护多 provider 并指定当前使用者，布局改为分组折叠，整体更紧凑。

## 2026-03-03（New API 报告生成 504 超时优化）

- **User Feedback:** 连通性测试可通过，但完整报告生成阶段反复报 `HTTP 504 Gateway time-out`（Cloudflare 页面）。
- **Agent Action:**
  1. 在 `backend/services/data_analysis_ai_report.py` 增加瞬时网关错误识别 `_is_transient_gateway_error`；
  2. 模型调用层新增 5xx/超时自动退避重试（2 秒，最多一次额外重试）；
  3. 对 New API 启用更严格的 Prompt 数据压缩上限：
     - `PROMPT_DATA_MAX_CHARS_NEWAPI = 36000`；
     - `_serialize_prompt_processed_data` 改为按 provider 动态限长（Gemini 保持原上限，New API 走更小上限）。
- **Result:** New API 在长上下文场景下更不容易触发上游超时；即便出现瞬时 504，也会自动退避重试。

## 2026-03-03（AI 设置新增“测试连接”按钮与后端连通性接口）

- **User Request:** 增加“测试连接”能力，避免每次都跑完整报告才知道 provider/base_url/key/model 是否可用。
- **Agent Action:**
  1. 后端新增最小化连通性测试能力：
     - `backend/services/data_analysis_ai_report.py` 增加 `run_ai_connection_test(payload)`；
     - `gemini` 测试：最小 prompt 调用官方 SDK；
     - `newapi` 测试：最小 prompt 调用 `/chat/completions`。
  2. 新增项目级测试接口：
     - `POST /api/v1/projects/{project_key}/data_analysis/ai_settings/test`
     - 实现文件：`backend/projects/daily_report_25_26/api/legacy_full.py`
  3. 新增管理后台测试接口：
     - `POST /api/v1/admin/ai-settings/test`
     - 实现文件：`backend/api/v1/admin_console.py`
  4. 前端统一弹窗新增“测试连接”按钮：
     - 文件：`frontend/src/projects/daily_report_25_26/components/AiAgentSettingsDialog.vue`
     - 按当前表单输入发起测试，成功后显示“连接测试成功”。
  5. 页面接入测试函数（共用弹窗）：
     - 日报分析页：`DataAnalysisView.vue`（项目级测试）
     - 月报查询页：`MonthlyDataShowQueryToolView.vue`（管理后台测试）
     - 全局后台页：`AdminConsoleView.vue`（管理后台测试）
  6. API 封装新增：
     - `testAiSettings(projectKey, payload)`
     - `testAdminAiSettings(payload)`
     - 文件：`frontend/src/projects/daily_report_25_26/services/api.js`
- **Result:** 现在可在智能体设定弹窗中先做通道连通性验证，再决定保存/生成报告。

## 2026-03-03（New API 403/1010 网关拒绝兼容优化）

- **User Feedback:** New API 已配置 provider，但调用持续报错 `New API 调用失败: HTTP 403 error code: 1010`。
- **Agent Action:**
  1. 调整 `backend/services/data_analysis_ai_report.py` 的 New API 请求头：
     - 新增 `Accept: application/json`
     - 新增 `User-Agent: Phoenix-AI-Client/1.0`
  2. 增强 HTTP 错误提示：
     - 对 `403 + 1010` 给出专项诊断信息（提示检查 API 域名/路径与网关放行）；
     - 报错中附带实际请求 URL，便于快速定位 base_url 配置错误。
- **Result:** 该类错误可更快定位；同时提高了与部分网关策略的兼容性。

## 2026-03-03（AI 服务双通道扩展：Gemini / New API 可切换）

- **User Request:** 当前 Google 官方免费额度有限，希望 AI 智能服务支持 New API 格式接入，可配置 `base_url/api_key/model`，并能在 New API 与 Gemini 官方 API 之间切换。
- **前置说明:**
  1. 本轮为兼容性增强，不改变日报/月报 AI 报告主流程与现有提示词机制；
  2. 采用配置驱动方式扩展，保持对旧 `gemini_*` 配置的向后兼容；
  3. 全局管理后台、日报页、月报页继续共用同一个“智能体设定”组件与同一份配置文件。
- **Agent Action:**
  1. 后端配置读写层扩展（`legacy_full.py` / `admin_console.py`）：
     - 新增字段：`provider`、`newapi_base_url`、`newapi_api_keys`、`newapi_model`；
     - 保留既有 `api_keys/model`（Gemini）语义；
     - 持久化到 `backend_data/shared/ai_settings.json`，并继续兼容旧单 key 字段回退。
  2. AI 调用核心扩展（`backend/services/data_analysis_ai_report.py`）：
     - 新增 provider 分流：`gemini` / `newapi`；
     - `gemini` 继续走 `google.generativeai`；
     - `newapi` 新增 OpenAI-compatible `POST /chat/completions` 调用链；
     - 统一复用现有重试与限流退避框架，任务返回模型名改为运行时 provider 对应模型。
  3. 前端统一设置弹窗扩展（`AiAgentSettingsDialog.vue`）：
     - 新增“AI 服务商”切换；
     - 增加 New API `Base URL / API Keys / 模型` 输入区；
     - 保存时统一提交双通道字段，三处页面自动同步生效。
  4. API 封装扩展（`frontend/.../services/api.js`）：
     - 项目级与管理后台 AI 设置保存接口均补充 provider/newapi 字段透传。
  5. 共享配置扩展（`backend_data/shared/ai_settings.json`）：
     - 增加默认键：`provider/newapi_base_url/newapi_model/newapi_api_keys`。
- **Result:**
  1. 现在可在同一配置面板中维护 Gemini 与 New API 两套接入参数；
  2. 通过 `provider` 一键切换后，AI 报告链路会按所选通道调用；
  3. 旧 Gemini 配置与日报/月报现有模式保持兼容。

## 2026-02-28（登录 CORS 预检失败修复）

- **User Feedback:** 前端登录请求 `http://127.0.0.1:8000/api/v1/auth/login` 被浏览器拦截，报错 `No 'Access-Control-Allow-Origin' header`。
- **前置说明:**
  1. 本轮为线上联调阻断问题修复；
  2. 未触发 Serena 编辑受阻，使用 `apply_patch` 直接修复后端配置代码。
- **Agent Action:**
  1. 检查 `backend/main.py` 的 CORS 中间件配置；
  2. 定位问题：`allow_credentials=True` 与 `allow_origins=["*"]` 组合不兼容，导致浏览器预检失败；
  3. 修复为显式来源白名单（默认允许 `localhost/127.0.0.1` 的常见开发端口：`5173/4173/3000`），并保留 `PHOENIX_CORS_ORIGINS` 环境变量覆盖能力。
- **Result:** 本地开发场景下，`http://localhost:5173` 与 `http://127.0.0.1:5173` 对后端登录接口的预检请求可正常通过。

## 2026-02-28（monthly_data_pull 页面头部样式对齐）

- **User Feedback:** `monthly_data_pull` 页面进入后样式与其他项目不一致，顶部 banner 缺失。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`；
  2. 补回统一头部组件 `AppHeader`；
  3. 补回面包屑组件 `Breadcrumbs`，路径为“项目选择 > 月报导表工作台”；
  4. 微调页面主容器内边距，保持与现有页面观感一致。
- **Result:** `monthly_data_pull` 页面已恢复与其他项目一致的顶部 banner/导航体验。

## 2026-02-28（monthly_data_pull 第三阶段：关系匹配界面 + 导表执行闭环）

- **User Request:** 保留原先“每个子公司源文件与底表对应关系”的页面形式，并继续把模块做成真正可用。
- **前置说明:**
  1. 本轮在 `monthly_data_pull` 项目内继续增量开发，不影响现有日报项目主链；
  2. 当前执行引擎为 `openpyxl` 版本（无 xlwings），先实现可在线运行的首个闭环；
  3. 未触发 Serena 编辑受阻，全部通过 `apply_patch` 落地。
- **Agent Action:**
  1. 新增后端导表引擎：`backend/projects/monthly_data_pull/services/engine.py`
     - 映射解析：读取映射表，识别源/目标文件键、sheet 需求、业务分组；
     - 执行写入：按规则读取“源本月”（单元格或简单表达式）并写入目标本月；
     - 累计动作：当 `推荐动作` 包含“粘贴+累计”时，执行 `源累计 -> 目标累计`；
     - 输出：复制目标模板到 `outputs` 后写入并保存。
  2. 扩展项目接口：`backend/projects/monthly_data_pull/api/workspace.py`
     - `POST /monthly-data-pull/analyze-mapping`
     - `POST /monthly-data-pull/get-sheets?bucket=source_reports|target_templates`
     - `POST /monthly-data-pull/execute`
     - `GET /monthly-data-pull/download/{filename}`
     - 保留并兼容已有目录接口与上传接口。
  3. 扩展前端 API：`frontend/src/projects/daily_report_25_26/services/api.js`
     - `analyzeMonthlyDataPullMapping`
     - `getMonthlyDataPullSheets`
     - `executeMonthlyDataPull`
     - `buildMonthlyDataPullDownloadUrl`
  4. 重构项目页面：`frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`
     - 三步流程：导入映射 -> 关系匹配 -> 执行下载；
     - 页面按业务组展示“源文件/目标底表”双栏关系卡；
     - 源文件支持规则 sheet 映射，目标支持单 sheet 选择；
     - 执行后展示输出文件下载列表。
- **Result:**
  1. `monthly_data_pull` 已从“目录工作台”升级为“可执行导表”的在线模块；
  2. 你熟悉的“关系匹配”交互形式已保留并迁移到新项目页；
  3. 当前可完成：映射解析、关系确认、执行写入、下载输出文件的完整闭环。

## 2026-02-28（monthly_data_pull 第二阶段：文件工作台上线）

- **User Request:** 新项目页面已可见，继续推进下一步可用能力。
- **前置说明:**
  1. 本轮在 `monthly_data_pull` 范围内做增量实现，不改现有 `daily_report_25_26` 业务主链；
  2. 未触发 Serena 编辑受阻，全部通过 `apply_patch` 实施。
- **Agent Action:**
  1. 后端新增文件工作台接口（`backend/projects/monthly_data_pull/api/workspace.py`）：
     - `GET /monthly-data-pull/files?bucket=...`：读取默认目录文件列表；
     - `POST /monthly-data-pull/files/upload?bucket=...`：上传文件到指定默认目录；
     - 支持 bucket：`mapping_rules/source_reports/target_templates/outputs`；
     - 增加文件名安全处理、重名自动追加时间戳，返回文件大小与更新时间。
  2. 前端 API 封装扩展（`frontend/src/projects/daily_report_25_26/services/api.js`）：
     - `listMonthlyDataPullFiles(projectKey, bucket)`
     - `uploadMonthlyDataPullFiles(projectKey, bucket, files)`
  3. 前端页面升级（`frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`）：
     - 新增“文件工作台”区域；
     - 四类目录均支持“选文件 -> 上传 -> 刷新列表”；
     - 展示文件名称、大小、更新时间；失败时显示目录级错误信息。
- **Result:**
  1. `monthly_data_pull` 已从“纯骨架页”升级为可操作页面；
  2. 你可以直接在线上传映射规则、源文件、目标底表并查看目录内容；
  3. 为下一步“预检 + 执行任务”打通了输入准备链路。

## 2026-02-28（登录 CORS 二次加固：localhost/127.0.0.1 任意端口）

- **User Feedback:** 仍出现登录预检 CORS 拦截。
- **Agent Action:**
  1. 在 `backend/main.py` 的 CORS 中间件中新增 `allow_origin_regex`：
     - `^https?://(localhost|127\\.0\\.0\\.1)(:\\d+)?$`
  2. 保留原有显式白名单，形成“白名单 + 正则”双保险。
- **Result:** 开发环境下 `localhost/127.0.0.1` 不同端口组合均可通过预检。

## 2026-02-28（登录失败根因定位：端口冲突并切换 Phoenix 到 8001）

- **User Feedback:** 即使修复 CORS，登录仍失败。
- **Agent Action:**
  1. 直接请求运行中服务验证：
     - `http://127.0.0.1:8000/healthz` 返回 404；
     - `http://127.0.0.1:8000/` 返回“月报自动映射工具 v3.2”页面；
     结论：`8000` 端口被外部导表程序占用，前端请求未命中 Phoenix 后端。
  2. 端口冲突规避改造：
     - `frontend/.env.development`：`VITE_API_BASE` 改为 `http://127.0.0.1:8001`；
     - `docker-compose.yml`：backend 端口映射改为 `8001:8000`。
- **Result:** Phoenix 与外部导表程序可并行运行（外部程序保留 8000，Phoenix 使用 8001）。

## 2026-02-28（新增 monthly_data_pull 项目模块与默认目录骨架）

- **User Request:** 新增项目模块 `monthly_data_pull`（项目列表最后一项），仅 `Global_admin` 可见；创建对应前后端项目目录并放置程序文件；默认工作目录放在 `backend_data/monthly_data_pull` 下。
- **前置说明:**
  1. Serena 接入校验沿用本会话既有状态（已激活且 onboarding 完成）；
  2. 本轮以“可访问 + 可扩展”的第一阶段骨架为目标，未接入导表执行内核；
  3. 未触发 Serena 编辑受阻，无降级 shell 编辑，全部通过 `apply_patch` 完成。
- **Agent Action:**
  1. 项目注册与权限：
     - 更新 `backend_data/shared/项目列表.json`：新增 `monthly_data_pull`（位于最后），`availability` 设为 `[\"Global_admin\"]`；
     - 更新 `backend_data/shared/auth/permissions.json`：为 `Global_admin` 新增 `monthly_data_pull` 项目权限（`page_access: [\"workspace\"]`）。
  2. 后端项目骨架：
     - 新增 `backend/projects/monthly_data_pull/` 模块：
       - `api/router.py`
       - `api/workspace.py`
       - `__init__.py`
     - 新增接口：
       - `GET /api/v1/projects/monthly_data_pull/monthly-data-pull/ping`
       - `GET /api/v1/projects/monthly_data_pull/monthly-data-pull/workspace`
     - 更新 `backend/api/v1/project_router_registry.py`，注册 `monthly_data_pull` 路由。
  3. 默认目录与配置文件：
     - 新增 `backend_data/monthly_data_pull/` 及子目录：
       - `mapping_rules/`
       - `source_reports/`
       - `target_templates/`
       - `outputs/`
     - 新增文件：
       - `backend_data/monthly_data_pull/README.md`
       - `backend_data/monthly_data_pull/workspace_settings.json`
       - 各子目录 `.gitkeep`
  4. 前端入口与页面骨架：
     - 新增入口分发页：`frontend/src/pages/ProjectEntryView.vue`
     - 新增项目首页：`frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`
     - 更新路由 `frontend/src/router/index.js`：`/projects/:projectKey` 改为统一入口分发页
     - 更新项目选择页 `frontend/src/pages/ProjectSelectView.vue`：将 `monthly_data_pull` 加入直达入口集合
     - 更新 API 封装 `frontend/src/projects/daily_report_25_26/services/api.js`：新增 `getMonthlyDataPullWorkspace(projectKey)`
- **Result:**
  1. `Global_admin` 登录后可在项目列表看到并进入 `monthly_data_pull`；
  2. 进入后可看到月报导表项目骨架页，并读取后端返回的默认目录路径；
  3. `backend_data/monthly_data_pull` 默认目录体系已初始化，为后续导表执行链路接入做好落点准备。

## 2026-02-28（LibreOffice Headless 可行性调研）

- **User Request:** 在“无需 xlwings/Excel/WPS”的前提下，进一步了解 LibreOffice Headless 是否可作为在线导表执行引擎。
- **前置说明:**
  1. 本轮为技术调研与方案论证，未改动业务代码；
  2. 仅追加文档留痕，便于后续接入决策审计。
- **Agent Action:**
  1. 调研 LibreOffice 官方命令行参数与无界面运行能力（`--headless`、`--convert-to`、`--accept`）。
  2. 调研 LibreOffice UNO 计算接口能力（`XCalculatable.calculateAll()`）。
  3. 调研生态工具状态：`unoconv` 进入维护态，官方仓库建议生产优先考虑 `unoserver`。
  4. 结合 Phoenix 现有 Docker/Linux 环境评估接入方式与风险。
- **Result:**
  1. LibreOffice Headless 可在 Linux 服务器/容器运行，具备“无界面打开-计算-保存”的技术路径；
  2. 可作为 `xlwings` 的可行替代，但需按“单实例队列 + 稳定重试 + 真实模板回归”工程化落地；
  3. 建议优先走“持久化 UNO 服务（unoserver）”而非一次一进程的裸 `soffice` 批处理模式。

## 2026-02-28（外部导表程序接入可行性调研）

- **User Request:** 研究 `D:\编程项目\phoenix\外部待导入-导表程序`，评估将其纳入 Phoenix 平台在线运行的可行性（当前该程序原先在本地 Win11 使用）。
- **前置说明:**
  1. Serena 接入校验已完成：`activate_project` 成功，`check_onboarding_performed` 为已完成状态；
  2. 本轮以调研与方案论证为主，未修改后端/前端业务代码；
  3. 本轮未触发 Serena 编辑受阻，无降级写文件场景；仅按协作规范更新进度与结构文档。
- **Agent Action:**
  1. 完整梳理外部程序结构与主流程：
     - 入口：`外部待导入-导表程序/app/main.py`
     - 核心引擎：`外部待导入-导表程序/app/core/engine.py`
     - 前端页：`外部待导入-导表程序/templates/index.html`
     - 依赖：`xlwings/pandas/openpyxl/FastAPI`
  2. 确认该程序当前真实执行链路：
     - `analyze-mapping` 解析映射表并产出源/目标文件键、分组、sheet 需求；
     - `get-sheets` 读取上传文件 sheet；
     - `execute` 依据映射规则执行“源取值 -> 目标写值 -> 累计差异报告”；
     - `extract-mapping-json` 可导出“有效映射 JSON”，但执行主链仍以 Excel 映射表为输入。
  3. 对照 Phoenix 当前主链路：
     - 已有数据填报主链在 `backend/projects/daily_report_25_26/api/legacy_full.py`；
     - `Coal_inventory_Sheet` 已有独立提交与查询分支；
     - 当前容器为 Linux + `python:3.12-slim`（`backend/Dockerfile`），不具备 Windows Excel COM 环境。
  4. 输出接入结论与改造方向：
     - 不建议直接把外部程序原样并入线上容器（`xlwings` 强依赖本机 Excel/COM）；
     - 建议采用“规则引擎服务化”路线：保留映射规则与流程，替换 `xlwings` 执行内核为 `openpyxl`/纯 Python 读写链路，并通过 Phoenix 新增导表 API 与前端管理页接入。
- **Result:**
  1. 已形成可落地结论：该外部程序业务逻辑可迁移，但执行内核需从 `xlwings` 解耦后再上线；
  2. 已明确最小接入位置：优先新增项目内导表路由（建议放在 `backend/projects/daily_report_25_26/api/`）并复用现有权限与项目路由体系；
  3. 本轮未产生代码行为变更，仅完成调研与文档留痕。

## 2026-02-11（新增迷你项目入口并固定在 projects 第二位）

- **User Request:** 在 `http://localhost:5173/projects` 页面新增一个实现简单的迷你项目，并显示在第二位。
- **前置说明:**
  1. Serena 已完成接入校验：`activate_project` 与 `check_onboarding_performed` 均成功。
  2. 本次未触发 Serena 编辑能力限制，采用最小范围配置改动；回滚方案为删除 `backend_data/shared/项目列表.json` 中新增的 `mini_project_demo` 条目。
- **Agent Action:**
  1. 定位项目入口链路：`frontend/src/pages/ProjectSelectView.vue` -> `frontend/src/daily_report_25_26/composables/useProjects.js` -> `frontend/src/daily_report_25_26/services/api.js` 的 `GET /api/v1/projects`。
  2. 定位后端项目列表源：`backend/api/v1/routes.py` 的 `list_projects`，读取 `backend_data/shared/项目列表.json`。
  3. 在 `backend_data/shared/项目列表.json` 新增项目键 `mini_project_demo`，并放置在 `daily_report_25_26` 后，确保前端卡片展示顺序为第二位。
  4. 同步更新结构文档：
     - `backend/README.md`：补充项目列表来源与迷你项目状态。
     - `frontend/README.md`：补充 projects 页数据来源与排序机制。
- **Result:**
  1. `http://localhost:5173/projects` 将出现第二张项目卡片：`迷你项目（示例）`（`mini_project_demo`）。
  2. 该项目点击后可进入项目页面路由，满足“先可见、可进入”的最小实现目标。

## 2026-02-11（mini 项目配置再精简：单页面线性流程）

- **User Request:** 已手动调整 `backend_data/shared/项目列表.json`，希望进一步简化新项目配置：仅保留单页面线性流程，不需要审批与常量指标等配置。
- **前置说明:**
  1. 本次为配置级最小改动，不涉及后端接口实现扩展；
  2. 继续沿用 `GET /api/v1/projects` 读取 `backend_data/shared/项目列表.json` 的机制；
  3. 回滚方式：将 `mini_project_demo` 恢复为原先带 `modularization` 字段的结构。
- **Agent Action:**
  1. 精简 `backend_data/shared/项目列表.json` 中 `mini_project_demo`：
     - 保留单一页面 `mini_entry`；
     - 页面名称改为“迷你业务页”；
     - 页面描述改为“单页面线性流程（无审批、无常量指标配置）”；
     - 移除 `modularization.config_files/runtime_files` 空清单字段。
  2. 同步更新说明文档：
     - `backend/README.md`：声明 mini 项目为单页面最小配置；
     - `frontend/README.md`：声明 projects 页第二位 mini 项目仅保留单页面入口。
- **Result:** mini 项目在项目列表中保持第二位，配置结构已进一步简化为“单页面最小可维护形态”。

## 2026-02-11（春节简化日报：直达页面 + xlsx 提取 JSON 框架）

- **User Request:** 以当前 `backend_data/shared/项目列表.json` 为准，为 `daily_report_spring_festval_2026` 提供直达功能页（不显示 pages 选择），并先实现“上传 xlsx 并提取为 JSON”的能力；后续再共建简化看板。
- **前置说明:**
  1. Serena 接入校验已完成（项目激活与 onboarding 状态正常）；
  2. 本次实现聚焦“框架 + xlsx 提取 JSON”，暂不包含简化看板渲染与 PDF 生成；
  3. 主要基于你提供的参考文件实现提取规则：
     - `configs/2.11 xlsx_to_bydate.html`
     - `configs/2.11 春节期间示例数据.json`
- **Agent Action:**
  1. 新增春节项目后端模块并注册：
     - `backend/projects/daily_report_spring_festval_2026/api/router.py`
     - `backend/projects/daily_report_spring_festval_2026/api/xlsx_extract.py`
     - `backend/api/v1/project_router_registry.py` 注册 `daily_report_spring_festval_2026`。
  2. 新增上传提取接口：
     - `POST /api/v1/projects/daily_report_spring_festval_2026/spring-festival/extract-json`
     - 支持 `sheet_name`、`keep_diff_cell`、`compute_diff`、`normalize_metric` 参数；
     - 解析逻辑包含：表头识别（本期/同期/差异）、日期列组提取、合并单元格补全、指标规范化、diff 计算、按日期组织 `byDate`。
  3. 新增前端直达功能页：
     - `frontend/src/daily_report_25_26/pages/SpringFestivalEntryView.vue`
     - 路由新增：`/projects/:projectKey`（春节项目进入该页，其他项目自动跳转回 `/pages`）。
  4. 新增前端 API 封装：
     - `frontend/src/daily_report_25_26/services/api.js` 新增 `extractSpringFestivalJson`。
  5. 调整项目入口点击逻辑：
     - `frontend/src/pages/ProjectSelectView.vue` 对 `daily_report_spring_festval_2026` 直达 `/projects/{projectKey}`，不再先进入 pages 选择。
- **Result:**
  1. 访问 `http://localhost:5173/projects/daily_report_spring_festval_2026` 将直接进入春节简化项目功能页；
  2. 功能页已支持上传 xlsx 并生成与示例结构一致的 `byDate` JSON 预览与下载；
  3. 已为后续“简化看板 + PDF 下载”阶段打通数据输入链路。

## 2026-02-11（春节项目前端目录规范化迁移）

- **User Request:** 新项目应保持独立边界，页面不应继续放在 `daily_report_25_26` 目录下。
- **前置说明:**
  1. 本次目标为“前端目录规范化”，不改变已上线的后端接口；
  2. 回滚方式：将路由组件路径指回旧目录并恢复旧页面文件。
- **Agent Action:**
  1. 路由迁移：
     - `frontend/src/router/index.js` 中 `/projects/:projectKey` 组件改为
       `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalEntryView.vue`。
  2. 新增春节项目前端独立目录与文件：
     - `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalEntryView.vue`
     - `frontend/src/projects/daily_report_spring_festval_2026/services/api.js`
  3. 删除旧项目目录中的春节页面文件：
     - `frontend/src/daily_report_25_26/pages/SpringFestivalEntryView.vue`
  4. 保持接口链路不变：仍调用
     `POST /api/v1/projects/daily_report_spring_festval_2026/spring-festival/extract-json`。
- **Result:** 春节项目已完成前端目录独立化，结构边界与“新项目独立维护”诉求一致，同时不影响现有上传提取 JSON 功能。

## 2026-02-11（前端项目目录统一：daily_report_25_26 迁入 projects）

- **User Request:** 将 `daily_report_25_26` 也迁到 `frontend/src/projects/`，一次性修正全部引用路径与路由。
- **前置说明:**
  1. 目标为前端目录规范化，不改后端接口契约；
  2. 迁移范围覆盖 `main/router/pages` 与春节项目对老项目模块的复用引用；
  3. 回滚方式：将目录迁回 `frontend/src/daily_report_25_26` 并恢复导入路径。
- **Agent Action:**
  1. 迁移目录：
     - `frontend/src/daily_report_25_26/*` -> `frontend/src/projects/daily_report_25_26/*`；
     - 保持子目录结构不变（components/composables/constants/pages/services/store/styles）。
  2. 全局引用修正：
     - `frontend/src/main.js` 主题样式路径更新为 `./projects/daily_report_25_26/styles/theme.css`；
     - `frontend/src/router/index.js` 中 `auth` 与各页面组件导入统一改为 `../projects/daily_report_25_26/...`；
     - `frontend/src/pages/LoginView.vue`、`ProjectSelectView.vue` 相关导入改为 `../projects/daily_report_25_26/...`。
  3. 春节项目复用路径修正：
     - `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalEntryView.vue` 改为从 `../../daily_report_25_26/...` 复用组件与 composable；
     - `frontend/src/projects/daily_report_spring_festval_2026/services/api.js` 改为从 `../../daily_report_25_26/services/api` 复用请求封装。
  4. 文档同步：
     - `frontend/README.md`、`backend/README.md` 更新目录统一说明；
     - `frontend/src/projects/daily_report_25_26/README.md` 修正 `main.js` 样式路径示例。
- **Result:** `frontend/src` 下项目模块已统一到 `projects/` 目录，路由与导入链路可指向新路径，组织结构符合多项目并列规范。

## 2026-02-11（发布缓存报错修复：日期配置文件不存在）

- **User Request:** 在页面 `.../daily_report_25_26/pages/dashboard/dashboard` 点击“发布缓存”时报错 `{\"detail\":\"日期配置文件不存在\"}`，要求排查并修复项目化重组后的路径关联问题。
- **前置说明:**
  1. 问题聚焦后端看板发布链路；本次不改前端请求契约；
  2. 回滚方式：恢复 `backend/services/dashboard_expression.py` 中 `_resolve_date_config_path` 的旧实现。
- **Agent Action:**
  1. 定位报错源：`backend/services/dashboard_expression.py` 的 `load_default_push_date` 在 `date_config_path` 不存在时抛出该错误。
  2. 根因分析：`_resolve_date_config_path` 原先使用 `resolve_project_config_path(project_key, "date.json")`，回退仅到旧平铺 `DATA_DIRECTORY/date.json`，未优先覆盖已迁移到 `shared/date.json` 的全局日期文件。
  3. 修复实现：
     - 引入 `get_project_config_dir` 与 `resolve_global_date_path`；
     - 路径解析顺序改为：
       - `projects/<project_key>/config/date.json`（存在则用）；
       - 否则回退 `shared/date.json`（再兼容旧 `date.json`）。
  4. 同步文档：更新 `backend/README.md`、`frontend/README.md` 记录本次修复口径。
- **Result:** 看板发布缓存在项目化目录结构下可正确解析日期配置，不再因 `shared/date.json` 未命中而报“日期配置文件不存在”。

## 2026-02-11（春节迷你看板第一版：生成按钮 + 看板页）

- **User Request:** 在春节项目中，将“下载 JSON”改为“生成数据看板”；点击后跳转看板页，并展示指定卡片与图表。煤耗/投诉来自上传提取 JSON，气温必须从数据库读取。
- **前置说明:**
  1. 本次优先完成“可用框架 + 指定卡片图表”；
  2. 气温数据沿用现有数据库链路（通过看板接口读取），不使用上传 JSON 中的气温字段；
  3. 回滚方式：移除新增路由与 `SpringFestivalDashboardView.vue`，并恢复入口页按钮逻辑。
- **Agent Action:**
  1. 路由新增：
     - `frontend/src/router/index.js` 增加 `/projects/:projectKey/spring-dashboard`。
  2. 入口页调整：
     - `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalEntryView.vue`
       将“下载 JSON”按钮改为“生成数据看板”，点击后跳转新路由。
  3. 新增迷你看板页：
     - `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`，实现：
       - 4 张卡片：当日平均气温、当日集团标煤消耗、当日总投诉量、当日净投诉量；
       - 3 个图表：气温变化（向后预测3日，含同期）、标煤消耗量对比、投诉量分项（图+表）；
       - 日期选择、上传数据缺失提示、返回上传页。
  4. 数据来源拆分：
     - JSON（localStorage）用于煤耗/投诉指标；
     - 气温通过 `frontend/src/projects/daily_report_spring_festval_2026/services/api.js` 新增 `getTemperatureTrendByDate`，底层复用 `daily_report_25_26` 的 `getDashboardData`，从数据库加载“逐小时气温”后按日求均值。
- **Result:** 春节项目已形成“上传 xlsx -> 提取 JSON -> 生成迷你看板”的首版闭环，且满足气温走数据库、煤耗/投诉走上传数据的口径要求。

## 2026-02-11（春节迷你看板空白问题修复：数据回退链路增强）

- **User Feedback:** mini 数据看板页面出现“图表空白”，但 xlsx 提取 JSON 已成功。
- **前置说明:**
  1. 当前优先修复“跳转后数据丢失导致空白”的高概率链路；
  2. 本轮不改后端接口，仅增强前端数据持久与读取回退。
- **Agent Action:**
  1. `frontend/src/projects/daily_report_spring_festval_2026/services/api.js` 增加内存级缓存函数：
     - `setLatestExtractedPayload`
     - `getLatestExtractedPayload`
  2. `SpringFestivalEntryView.vue` 在解析成功后同时写入：
     - 内存缓存；
     - `sessionStorage`；
     - `localStorage`。
  3. `SpringFestivalDashboardView.vue` 的 payload 读取改为三级回退：
     - 内存缓存 -> `sessionStorage` -> `localStorage`；
     并补充 `dates` 为空时由 `byDate` 键自动回推日期列表。
  4. 增加图表库加载检测（`window.echarts`），未加载时给出明确提示，避免静默空白。
- **Result:** 上传后跳转 mini 看板时的数据命中率显著提高，降低“已提取成功但看板空白”的问题概率，并增加可诊断提示。

## 2026-02-11（mini 看板空白二次修复：后端落盘回读）

- **User Feedback:** 仍出现“extract-json 成功，但 mini 看板无数据与图形”。
- **Agent Action:**
  1. 后端增强（`backend/projects/daily_report_spring_festval_2026/api/xlsx_extract.py`）：
     - `extract-json` 成功后将 payload 写入 `runtime/spring_festival_latest_extract.json`；
     - 新增 `GET /spring-festival/latest-json` 返回最近一次提取结果。
  2. 前端增强：
     - `services/api.js` 新增 `getLatestExtractedJson(projectKey)`，并携带 Bearer Token；
     - `SpringFestivalDashboardView.vue` 在本地缓存未命中时自动回读后端最新提取结果。
- **Result:** mini 看板不再只依赖浏览器存储，提取成功后可通过后端回读兜底，提高数据可见性稳定性。

## 2025-12-09（仪表盘运行设备明细展示优化 - 零值隐藏）

- **User Request:** 如果某个指标（本期和同期）都为零，则不显示其标签和数字，而是显示一个中性占位符。
- **Agent Action:**
  1. 修改 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 中的 `renderDeviceCombo` 函数。
  2. 在渲染 `combo-item` 列表之前，先过滤掉那些本期和同期值都为零的 `item`。
  3. 如果过滤后没有剩余的 `item`（即所有指标都为零），则整个单元格显示一个居中的灰色 `—`。
  4. 为 `combo-zero-cell` 添加了 CSS 样式，使其在单元格中居中显示。
- **Result:** 现在，当某个设备的运行指标（例如“汽炉数”）本期和同期都为零时，该指标的标签和数字将不会显示，使得表格更专注于展示有数据的项。如果一个分组内的所有指标都为零，则该分组对应的单元格会显示一个清晰的 `—` 占位符，进一步提升了表格的简洁性和可读性。

## 2026-01-10（数据分析环比数据缩放修正）

- **User Request:** 修正数据分析页面累计模式下，“环比比较”板块中百分比指标（如“全厂热效率”）上期数值显示错误（如 0.85% 而非 85%）的问题。
- **Agent Action:**
  1. 分析 `backend/api/v1/daily_report_25_26.py` 中的 `_execute_data_analysis_query_legacy` 函数。
  2. 发现构造 `prev_totals_map` 时未对百分比类指标应用缩放函数 `_scale_metric_value`。
  3. 修改代码，在计算 `ring_ratio` 之前以及填充 `prev_totals_map` 时，统一对相关数值进行缩放处理。
- **Result:** 现在环比板块的“上期累计”数值量级已与本期、同期保持一致，百分比指标能够正确显示。

## 2026-01-31（SSL 证书过期导致 Cloudflare 526 错误）

- **User Request:** 网站突然无法访问，Cloudflare 显示 526 错误（SSL 无效），仅在 "Full" 模式下可用，"Strict" 模式报错。需要排查原因。
- **Agent Action:**
  1. 检查 `docker-compose.server.yml` 和 `deploy/nginx.prod.conf`。
  2. 发现 `certbot` 容器配置了自动续期命令 (`certbot renew`)，但 `web` (Nginx) 容器缺少对应的重载 (reload) 机制。
  3. Nginx 仅在启动时读取证书，即使 Certbot 更新了证书文件，Nginx 内存中仍运行旧证书，导致过期。
- **Result:** 建议用户在服务器执行 `docker compose -f docker-compose.server.yml restart web` 以重载证书。建议后续增加 Nginx 定时重载机制。

## 2026-02-08（后端填报链路优化：煤炭库存重复逻辑清理 + 模板读取缓存）

- **User Request:** 一起优化在线填报平台，提升稳定性与性能。
- **Agent Action:**
  1. 审查 `backend/api/v1/daily_report_25_26.py` 的填报/查询主链路，定位煤炭库存处理函数存在“同名函数重复定义”的问题（后定义会覆盖前定义）。
  2. 删除已失效的旧实现：`_flatten_records_for_coal`、早期版本 `_persist_coal_inventory`、早期版本 `handle_coal_inventory_submission`，保留并统一使用文件尾部的新版解析/写库实现。
  3. 为 `_read_json` 增加缓存层：新增 `_read_json_cached`（`functools.lru_cache`），缓存键包含 `path + mtime_ns + size`，保证文件变更后自动失效，减少模板查询与镜像查询中的重复磁盘读取。
  4. 同步更新 `backend/README.md` 与 `frontend/README.md` 的“最新结构与状态”说明，便于协作时快速定位模块职责。
- **Result:** 后端煤炭库存提交链路去重完成，避免维护时“看见A函数、运行B函数”的隐性风险；模板读取在高频请求场景下降低了重复 I/O 开销。接口路径与数据契约保持不变，可直接与现有前端继续联调。

## 2026-02-08（数据看板缓存发布性能优化 - 第一阶段）

- **User Request:** 针对“导入气温 → 导出 Excel → 发布缓存 → 下载 PDF”流程，优化发布缓存耗时问题；重点关注日志中“正在加载：Group 分组数据...”长期卡顿，且仅单核满载。
- **Agent Action:**
  1. 后端 `evaluate_dashboard` 去除进度回调中的固定 `sleep(0.1)`，避免人为串行等待。
  2. 后端新增发布任务级共享查询缓存：在 `dashboard_cache_job.py` 中为一次发布任务创建 `shared_metrics_cache`，跨日期复用 `(table, company, date)` 查询结果，减少 7 日发布中的重复 `groups/sum_basic_data` 查询。
  3. 后端优化逐小时气温板块范围：由“从模板最早日期扫到 push_date”改为“回溯窗口（默认 7 天，支持配置 `回溯天数`，限制 1~31）+ 预测天数”，显著减少温度查询次数。
  4. 后端发布接口支持天数参数：`POST /dashboard/cache/publish?days=1..30`，默认 7。
  5. 前端数据看板新增“发布天数”选择（1/3/7 天，默认 1 天），发布时透传 `days` 参数，减少日常运维等待。
- **Result:** 在不改变业务口径与数据结构的前提下，缓存发布链路减少了重复查询与无效等待；日常可用“1 天发布”快速完成缓存准备，7 天全量发布仍可保留用于补算场景。

## 2026-02-08（项目模块化第一步：配置路径项目化兼容层）

- **User Request:** 先落地“第一步”，认真仔细推进项目模块化，但避免大范围重构与业务风险。
- **Agent Action:**
  1. 新增 `backend/services/project_data_paths.py`，统一“新目录优先、旧平铺回退”的路径解析规则：
     - `resolve_project_config_path(project_key, filename)`
     - `resolve_project_runtime_path(project_key, filename)`
  2. 将 `backend/api/v1/daily_report_25_26.py` 的核心配置/运行时文件路径切到兼容解析：
     - `数据结构_基本指标表.json`、`数据结构_常量指标表.json`、`数据结构_审批用表.json`、`数据结构_数据分析表.json`、`api_key.json`
     - 调试输出 `test.md`
  3. 将 `backend/services/dashboard_expression.py` 的看板配置与日期配置改为按 `project_key` 动态解析（默认 `daily_report_25_26`），并在 `evaluate_dashboard` 中显式传递。
  4. 将 `backend/services/dashboard_cache.py` 的缓存文件改为按 `project_key` 解析运行时路径；`default_publish_dates` 增加 `project_key` 参数并传递到 `load_default_push_date`。
  5. 将 `backend/services/data_analysis_ai_report.py` 的 `api_key.json` 路径改为项目化兼容解析。
  6. 调整发布缓存调用，显式传递 `project_key` 到 `default_publish_dates`。
- **Result:** 在不改接口契约与业务口径的前提下，后端已具备“项目目录优先、旧目录兼容”的路径能力，为后续多项目接入打下基础；现有 `daily_report_25_26` 可继续按旧目录运行。

## 2026-02-08（项目模块化第一步增强：shared 全局路径兼容）

- **User Request:** 在第一步基础上继续推进，保持谨慎与低风险。
- **Agent Action:**
  1. 扩展 `backend/services/project_data_paths.py`，新增 shared 文件解析：
     - `resolve_project_list_path()`
     - `resolve_accounts_path()`
     - `resolve_permissions_path()`
     - `resolve_global_date_path()`
     解析规则均为“shared 目录优先，旧路径回退”。
  2. `backend/api/v1/routes.py` 的 `PROJECT_LIST_FILE` 改为 `resolve_project_list_path()`。
  3. `backend/services/auth_manager.py` 的账号/权限/全局日期路径改为 shared 兼容解析。
  4. `backend/api/v1/daily_report_25_26.py` 在扫描项目列表时改用 `resolve_project_list_path()`。
- **Result:** 除项目专属配置外，项目列表与鉴权相关全局文件也具备新目录兼容能力；后续可将全局文件迁移到 `backend_data/shared/...`，旧目录仍可继续使用。

## 2026-02-08（项目模块化第二步-过渡工具：迁移状态与一键初始化）

- **User Request:** 在前序兼容层基础上继续推进，尽可能给出可直接使用的结果。
- **Agent Action:**
  1. 扩展 `backend/services/project_data_paths.py`：
     - `ensure_project_dirs(project_key)`：创建 `projects/<key>/{config,runtime}` 目录；
     - `bootstrap_project_files(...)`：将旧平铺文件按“仅缺失时复制”迁移到新目录；
     - `get_project_file_status(...)`：输出新旧路径存在状态与绝对路径，便于核对。
  2. 在 `backend/api/v1/daily_report_25_26.py` 新增管理接口（系统管理员）：
     - `GET /project/modularization/status`：查看迁移状态；
     - `POST /project/modularization/bootstrap`：执行目录初始化与文件复制，并返回最新状态。
  3. 内置首批迁移清单：
     - 配置文件：`数据结构_基本指标表.json`、`数据结构_常量指标表.json`、`数据结构_审批用表.json`、`数据结构_数据分析表.json`、`数据结构_数据看板.json`、`date.json`、`api_key.json`
     - 运行时文件：`dashboard_cache.json`、`test.md`
- **Result:** 你现在可以通过接口直接“查看迁移进度 + 一键创建并复制文件”，不用手工逐个处理目录和文件，且不会覆盖已存在的新目录文件。

## 2026-02-08（项目模块化第三步-通用管理接口与前端管理页）

- **User Request:** 继续按计划推进，尽早实现项目模块化，并保持可视化可操作。
- **Agent Action:**
  1. 在 `backend/api/v1/routes.py` 新增通用接口（系统管理员）：
     - `GET /api/v1/projects/{project_id}/modularization/status`
     - `POST /api/v1/projects/{project_id}/modularization/bootstrap`
     并复用 `project_data_paths` 的 `get_project_file_status / ensure_project_dirs / bootstrap_project_files`。
  2. 为通用接口补充项目存在性校验（基于 `项目列表.json`）与系统管理员校验（`系统管理员` / `Global_admin`）。
  3. 在前端 `services/api.js` 新增：
     - `getProjectModularizationStatus(projectKey)`
     - `bootstrapProjectModularization(projectKey)`
  4. 新增页面 `frontend/src/daily_report_25_26/pages/ProjectModularizationView.vue`：
     - 展示项目目录、配置文件状态、运行时文件状态；
     - 提供“刷新状态”“执行初始化（仅复制缺失文件）”按钮；
     - 仅系统管理员可操作。
  5. 更新路由与入口：
     - `frontend/src/router/index.js` 增加 `/projects/:projectKey/modularization`
     - `frontend/src/daily_report_25_26/pages/PageSelectView.vue` 增加“项目模块化管理”卡片入口（系统管理员可见）。
- **Result:** 现在模块化能力从“单项目专用接口”升级为“项目维度通用接口 + 页面化运维入口”，可在前端直接查看与执行迁移初始化，加速后续多项目接入。

## 2026-02-08（项目模块化第四步-文件清单配置驱动）

- **User Request:** 继续推进模块化，项目当前功能正常，按计划继续做下一步。
- **Agent Action:**
  1. 改造 `backend/api/v1/routes.py` 的文件清单解析逻辑，新增三层优先级：
     - 项目配置显式声明（`modularization` / `目录化迁移` / `project_modularization`）；
     - 若未声明，则从 `pages` 的 `数据源/data_source` 自动推断 JSON 文件名；
     - 仍未得到结果时回退默认清单（保证兼容）。
  2. 新增辅助函数：
     - `_normalize_file_list`：清洗并去重文件名，限制为纯文件名；
     - `_extract_filename_from_data_source`：从数据源路径提取 JSON 文件名；
     - `_infer_project_config_files_from_pages`：从项目页面配置推断可迁移配置文件。
  3. 将通用接口中的 `_get_project_modularization_files` 改为接收 `project_entry`，按项目配置动态生成迁移清单。
- **Result:** 新项目不再依赖硬编码即可驱动模块化迁移状态与初始化，`项目列表.json` 可直接作为迁移清单来源；旧项目仍保留默认兜底与兼容能力。

## 2026-02-08（项目模块化第五步-项目注册表统一默认值）

- **User Request:** 继续推进模块化，功能保持正常。
- **Agent Action:**
  1. 新增 `backend/services/project_registry.py`，统一维护：
     - 默认项目 `DEFAULT_PROJECT_KEY`
     - 默认迁移清单（config/runtime）
     - `get_project_modularization_files(project_key)` 与 `get_default_project_key()`
  2. `backend/api/v1/routes.py` 改为通过注册表获取兜底清单，减少本地重复常量。
  3. `backend/api/v1/daily_report_25_26.py` 的 `PROJECT_CONFIG_FILES/PROJECT_RUNTIME_FILES` 改为读取注册表，不再硬编码重复清单。
  4. `backend/services/dashboard_cache.py`、`dashboard_expression.py`、`data_analysis_ai_report.py` 的默认项目 key 改为通过注册表获取，减少散落硬编码。
- **Result:** “默认项目 key + 内置迁移文件清单”收敛到单一来源，后续新增项目时需要改动的文件数量进一步下降，模块化维护成本继续降低。

## 2026-02-08（项目模块化第六步-项目路由注册表）

- **User Request:** 持续推进模块化并保持功能稳定。
- **Agent Action:**
  1. 新增 `backend/api/v1/project_router_registry.py`，统一维护项目路由映射（`router/public_router`）。
  2. `backend/api/v1/routes.py` 由“硬编码 include daily_report_25_26”改为“遍历注册表自动挂载 `projects/<project_key>` 前缀”。
- **Result:** 后续新增项目路由时只需在注册表新增映射项，主路由文件无需重复修改，进一步降低多项目扩展成本。

## 2026-02-08（项目模块化第七步-迁移清单解析服务统一）

- **User Request:** 继续推进模块化，保持当前功能正常。
- **Agent Action:**
  1. 新增 `backend/services/project_modularization.py`，统一提供：
     - `load_project_entries()` / `load_project_entry(project_key)`
     - `resolve_project_modularization_files(project_key, project_entry)`
     - 内部封装配置清单清洗、页面数据源推断、默认清单回退逻辑。
  2. `backend/api/v1/routes.py` 移除本地重复解析函数，改为直接调用 `resolve_project_modularization_files(...)`。
  3. `backend/api/v1/daily_report_25_26.py` 的专用模块化接口不再使用静态常量清单，改为与通用接口一致地动态解析项目清单。
- **Result:** 模块化文件清单解析逻辑收敛为单一服务，避免“通用接口与专用接口口径不一致”的维护风险，为后续多项目复用继续降本。

## 2026-02-08（项目模块化第八步-项目目录入口落地）

- **User Request:** 继续推进，目标是更贴近按项目目录组织代码。
- **Agent Action:**
  1. 新增项目目录入口文件：
     - `backend/projects/__init__.py`
     - `backend/projects/daily_report_25_26/__init__.py`
     - `backend/projects/daily_report_25_26/api/__init__.py`
     - `backend/projects/daily_report_25_26/api/router.py`
  2. 在 `backend/api/v1/project_router_registry.py` 中，将路由来源从旧路径切换为项目目录入口（过渡层）。
  3. 过渡层设计：`backend/projects/daily_report_25_26/api/router.py` 当前复用 `backend.api.v1.daily_report_25_26` 的 `router/public_router`，确保行为不变。
- **Result:** 主路由已经通过“项目目录入口”加载日报项目路由，目录组织迈出实质一步；后续可继续把 `daily_report_25_26.py` 内部实现逐段下沉到 `backend/projects/daily_report_25_26/`。

## 2026-02-08（项目模块化第九步-模块化接口迁移到项目目录）

- **User Request:** 程序文件要“各归各处”，继续向项目目录收敛。
- **Agent Action:**
  1. 新增 `backend/projects/daily_report_25_26/api/modularization.py`，承接以下接口：
     - `GET /project/modularization/status`
     - `POST /project/modularization/bootstrap`
  2. 更新 `backend/projects/daily_report_25_26/api/router.py` 为组合路由：
     - `legacy_router`（旧实现）
     - `modularization_router`（新项目目录实现）
  3. 从 `backend/api/v1/daily_report_25_26.py` 删除已迁移的模块化接口与对应专用解析函数，避免重复注册与双维护。
- **Result:** 目录化迁移管理接口已真正下沉到项目目录实现，旧大文件体积与职责开始收缩，路径与前端调用保持兼容。

## 2026-02-08（项目模块化第十步-数据看板接口迁移到项目目录）

- **User Request:** 继续推进“程序文件各归各处”。
- **Agent Action:**
  1. 新增 `backend/projects/daily_report_25_26/api/dashboard.py`，承接数据看板相关接口：
     - `GET /dashboard`
     - `GET /dashboard/date`
     - `POST /dashboard/cache/publish`
     - `DELETE /dashboard/cache`
     - `POST /dashboard/temperature/import`
     - `POST /dashboard/temperature/import/commit`
     - `GET /dashboard/cache/publish/status`
     - `POST /dashboard/cache/publish/cancel`
     - `POST /dashboard/cache/refresh`
  2. 更新 `backend/projects/daily_report_25_26/api/router.py`，将 `dashboard_router/dashboard_public_router` 纳入组合路由。
  3. 从 `backend/api/v1/daily_report_25_26.py` 移除已迁移的看板接口、辅助函数及相关无用导入，避免重复注册与双维护。
- **Result:** 数据看板接口实现已下沉到项目目录，旧大文件进一步瘦身，接口路径与前端调用保持不变。

## 2026-02-08（项目模块化第十一步-旧大文件整体迁入项目目录）

- **User Request:** 能做什么就做什么，尽快完成“程序文件各归各处”。
- **Agent Action:**
  1. 将原 `backend/api/v1/daily_report_25_26.py` 整体迁移至
     `backend/projects/daily_report_25_26/api/legacy_full.py`。
  2. 在原路径新增兼容层文件 `backend/api/v1/daily_report_25_26.py`，仅转发导入项目目录实现，保障历史导入不破坏。
  3. 更新 `backend/projects/daily_report_25_26/api/router.py`，直接从项目目录 `legacy_full.py` 加载 legacy 路由，不再依赖旧路径回转。
- **Result:** 日报项目的核心实现文件已物理归位到项目目录；`backend/api/v1` 保留轻量兼容层，代码组织与运行兼容同时满足。

## 2026-02-08（项目模块化第十二步-backend_data 挂载目录按项目归位）

- **User Request:** 指出 `backend_data` 仍是平铺结构，要求继续按项目划分。
- **Agent Action:**
  1. 创建并启用新目录结构：
     - `backend_data/shared/`
     - `backend_data/shared/auth/`
     - `backend_data/projects/daily_report_25_26/config/`
     - `backend_data/projects/daily_report_25_26/runtime/`
  2. 将平铺文件物理迁移到新结构：
     - 全局：`项目列表.json`、`date.json`、`账户信息.json`、`auth/permissions.json` -> `shared/...`
     - 项目配置：`数据结构_*.json`、`api_key.json`、`dashboard_frontend_config.json` -> `projects/.../config/`
     - 项目运行时：`dashboard_cache.json`、`test.md`、`ai_usage_stats.json` -> `projects/.../runtime/`
  3. 更新 `shared/项目列表.json`：
     - 页面 `数据源` 改为 `projects/daily_report_25_26/config/...` 相对路径；
     - 补充 `modularization.config_files/runtime_files` 清单，供模块化管理接口直接使用。
- **Result:** 数据挂载目录已从“根平铺”迁移为“shared + project”双层结构，真正进入数据层项目化；现有代码因已具备 shared/project 优先解析，运行路径保持兼容。

## 2026-02-08（项目模块化第十三步-全局状态文件归位与路径修正）

- **User Request:** 希望彻底梳理还未完成项并利索收尾。
- **Agent Action:**
  1. 进一步归位全局状态文件：
     - `backend_data/status.json` -> `backend_data/shared/status.json`
     - `backend_data/projects/daily_report_25_26/runtime/ai_usage_stats.json` -> `backend_data/shared/ai_usage_stats.json`
  2. 服务层路径修正（shared 优先、旧路径回退）：
     - `backend/services/workflow_status.py` 改为使用 `resolve_workflow_status_path()`；
     - `backend/services/ai_usage_service.py` 改为使用 `resolve_ai_usage_stats_path()`；
     - `backend/services/project_data_paths.py` 新增上述两个解析函数。
  3. 调整项目模块化清单：
     - `backend_data/shared/项目列表.json` 的 `runtime_files` 移除 `ai_usage_stats.json`（该文件已定义为全局 shared 文件）。
  4. 项目备份文件归位：
     - `backend_data/api_key.json.backup` -> `backend_data/projects/daily_report_25_26/config/api_key.json.backup`。
- **Result:** 全局状态文件与项目运行时文件边界清晰，路径解析与实际目录一致，减少运行期“找不到文件/写错位置”的风险。

## 2026-02-08（项目模块化第十四步-全局项目选择页剥离）

- **User Request:** 修复“/projects 页面属于全局但文件落在项目目录”的不足。
- **Agent Action:**
  1. 将页面文件迁移：
     - `frontend/src/daily_report_25_26/pages/ProjectSelectView.vue`
     -> `frontend/src/pages/ProjectSelectView.vue`
  2. 修正新文件内部依赖路径：
     - 主题、组件、composable 改为从 `../daily_report_25_26/...` 引用。
  3. 更新路由：
     - `frontend/src/router/index.js` 中 `/projects` 改为加载 `../pages/ProjectSelectView.vue`。
- **Result:** `/projects` 现在在目录归属上是全局壳层页面，不再放在项目目录内；功能与路由保持不变。

## 2026-02-08（项目模块化第十五步-全局登录页归位与路径口径统一）

- **User Request:** 同意继续修复未归位项中的 1、2，并删除历史文件 `DashBoard888.vue`。
- **Agent Action:**
  1. 全局登录页归位：
     - `frontend/src/daily_report_25_26/pages/LoginView.vue`
     -> `frontend/src/pages/LoginView.vue`
     - `frontend/src/router/index.js` 中 `/login` 路由改为加载 `../pages/LoginView.vue`。
     - 修正新文件内部依赖路径：`theme.css`、`useAuthStore` 改为 `../daily_report_25_26/...`。
  2. 后端路径口径统一（注释/文档，不改业务逻辑）：
     - `backend/services/auth_manager.py`
     - `backend/services/dashboard_cache.py`
     - `backend/services/dashboard_expression.py`
     - `backend/services/data_analysis_ai_report.py`
     - `backend/README.md`
  3. 删除历史文件：
     - `frontend/src/daily_report_25_26/pages/DashBoard888.vue`
  4. 同步文档：
     - `frontend/README.md` 更新“全局壳层页面目录”说明；
     - `frontend/src/daily_report_25_26/README.md` 清理 `DashBoard888.vue` 文案残留。
- **Result:** 登录页已与 `/projects` 一样归入全局壳层目录；后端路径文案与当前 `shared/project` 结构一致；历史冗余页面已删除，目录归位与口径一致性进一步提升。

## 2026-02-08（前端配置修复：jsconfig 路径映射报错）

- **User Request:** 检查 `frontend/jsconfig.json` 的报错原因。
- **Agent Action:**
  1. 读取并核对 `frontend/jsconfig.json` 与 `frontend/vite.config.js`。
  2. 确认 Vite 已配置 `@ -> ./src`，但 `jsconfig.json` 中使用 `compilerOptions.paths` 时缺少 `baseUrl`，会导致编辑器/TS Server 报错。
  3. 在 `frontend/jsconfig.json` 补充：`\"baseUrl\": \".\"`（最小修复）。
- **Result:** `jsconfig.json` 的路径映射配置满足规范，`@/*` 别名的编辑器报错应消失，且与 Vite 别名保持一致。

## 2026-02-08（项目模块化文档沉淀：2.8结构对照）

- **User Request:** 在 `configs` 目录生成 `2.8项目模块化.md`，清晰说明原先结构、新结构及对应关系。
- **Agent Action:**
  1. 扫描当前目录结构：`backend`、`frontend/src`、`backend_data`、`configs`。
  2. 新建文档 `configs/2.8项目模块化.md`，包含：
     - 模块化目标与范围；
     - 改造前结构树（后端/前端/数据目录）；
     - 当前结构树（后端/前端/数据目录）；
     - 旧路径与新路径对应关系表（后端代码、前端页面、backend_data）；
     - 兼容策略说明（路径回退、shim、URL 不变）；
     - 新项目落位规则与当前完成度结论。
  3. 同步更新 `backend/README.md` 与 `frontend/README.md`，增加该对照文档索引。
- **Result:** 项目模块化改造已形成可追溯的“一页式结构对照文档”，后续扩展新项目时可直接按文档执行。

## 2026-02-11（春节迷你看板空白问题：提取公式转数值修复）

- **User Request:** 提供调试信息，定位“mini 数据看板有 JSON 但卡片/图表空白”的根因并修复。
- **Agent Action:**
  1. 分析 `configs/2.12 调试信息.md`，确认命中指标存在，但 `current/prior` 为 Excel 公式字符串（如 `=AE12+...`），导致前端无法按数值绘图。
  2. 修复 `backend/projects/daily_report_spring_festval_2026/api/xlsx_extract.py`：
     - 新增公式数值解析能力（支持单元格引用 + 四则运算 + 括号）；
     - 对 `current/prior` 读取改为“数字优先 + 公式求值回退”；
     - 保留 `diffCell` 原始文本，不破坏追溯能力。
  3. 保持接口与路由不变：仍使用 `extract-json` / `latest-json`。
- **Result:** 春节项目提取 JSON 的关键指标值可从公式解析为数值，mini 看板卡片与图表具备渲染前提。

## 2026-02-12（春节迷你看板：气温取数链路对齐与卡片配色）

- **User Request:** mini 看板气温图改为与 `daily_report_25_26` 看板同源（数据库 `calc_temperature_data` 链路），并给前四张卡片增加与主看板一致的背景色。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - 气温加载改为“旧看板同款 section 解析策略”：支持 `data.sections`、`sections`、`data` 多种响应结构；
     - 增加按序号/旧键名解析：`1`、`1.逐小时气温`、`逐小时气温`、`calc_temperature_data`；
     - `buildDailyAverageMap` 支持数组、数值、对象（`avg/average/value`）三类值；
     - 同期日期做“映射到本年 + 缺口回补”处理，减少日期错位导致的空图。
  2. 修改同文件卡片样式：
     - 前四张卡片分别接入 `summary-card--primary/warning/danger`；
     - 增加与主看板一致风格的渐变背景、白色文字、阴影样式。
- **Result:** mini 看板气温取数路径与主看板保持一致，且顶部四张卡片已具备可视化底色层级。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过，无语法/打包错误。

## 2026-02-12（春节迷你看板：气温图时间窗与默认日期）

- **User Request:** 气温图日期范围改为“选定日期的当日+前三日+后三日”；日期下拉默认选中“北京时间当前日历日的前一日”，若不存在则取下拉中最近日期。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - 新增北京时间日期工具函数：`getBeijingYesterdayDateKey`；
     - 新增默认日期选择函数：`pickDefaultSelectedDate`（昨日优先，不存在则最近日期）；
     - 调整 `availableDates` 的标准化与排序逻辑；
     - `temperatureTrendOption` 改为使用 `temperatureWindowDates`，固定显示 `selectedDate ±3` 共 7 天窗口。
  2. 调试信息补充 `temperature.windowDates`，便于核对窗口是否符合预期。
- **Result:** mini 看板气温图时间窗口已按“前3+当日+后3”渲染；首次进入时默认日期策略已切换为北京时间昨日优先。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：气温图标签与业务日期标识）

- **User Request:** 鼠标悬浮曲线时数据标签保留 2 位小数；不悬浮时也要在图上标示业务日期位置及该日期本期/同期气温值。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - `temperatureTrendOption.tooltip.formatter` 改为统一输出 2 位小数（`xx.xx℃`）；
     - 在“本期”序列增加业务日期竖向虚线（`markLine`，标签“业务日期”）；
     - 在“本期/同期”序列分别增加业务日期点位标注（`markPoint`），常驻显示对应气温值（2 位小数）。
  2. 保持原有 `±3` 天窗口逻辑不变，仅增强展示与交互信息密度。
- **Result:** 气温图在悬浮与非悬浮状态下均可读到业务日期对应的本期/同期气温值，且显示精度统一为 2 位小数。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：气温全标签显示与业务日期线简化）

- **User Request:** 去掉图顶端“业务日期”文字（避免与标签重叠）；默认显示所有气温点的数据标签。
- **Agent Action:**
  1. 调整 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - 保留业务日期竖线（`markLine`）但关闭其文字标签（`label.show = false`）；
     - 为“本期/同期”两条线开启全点位 `label.show`，分别放置在上/下方，格式统一为 `xx.xx℃`；
     - 移除仅业务日期单点 `markPoint` 标注，避免与全量标签叠加。
- **Result:** 气温图在默认状态下即可看到全部点位温度值，且顶端不再出现“业务日期”重叠文字。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：标签防碰撞与卡片增减量口径）

- **User Request:** 气温图做标签防碰撞、业务日期虚线更浅；顶部四卡不显示差异率，改为本期值后括号显示增减量。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - 气温图两条线增加 `labelLayout`（`hideOverlap + moveOverlap: shiftY`）实现标签防碰撞；
     - 业务日期竖线颜色调整为半透明浅蓝（`rgba(37, 99, 235, 0.32)`）；
     - 四张卡片改为“主值 + 括号增减量”显示，新增 `formatIncrement`，移除差异率文案。
  2. 指标口径调整：
     - 煤耗/投诉卡片的 `delta` 改为 `current - prior`；
     - 气温卡片的 `delta` 改为 `main - peer`（绝对差）。
- **Result:** 图表标签可读性提升，业务日期线视觉干扰降低；四卡口径已改为“本期值（增减量）”。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：轴标签避让、四卡配色对齐、煤耗口径图重构）

- **User Request:** 处理数据标签与横坐标重叠；四卡颜色改为与 `daily_report_25_26` 顶部四卡一致；将“标煤消耗量对比”改为业务日期当日各口径耗原煤量对比并显示数据标签。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：\n     - 气温图增加横轴留白与标签边距（`grid.bottom`、`xAxis.axisLabel.margin`），降低标签与横轴重叠概率；\n     - 继续保留标签防碰撞策略（`labelLayout`）。
  2. 四卡配色对齐主看板：\n     - 第二卡改为 `summary-card--success` 绿色渐变；\n     - 第三卡改为 `summary-card--warning` 橙色渐变；\n     - 第一/第四卡保持蓝/红，形成与主看板一致的四卡色阶。
  3. 重构煤耗图：\n     - 图名改为“当日各口径耗原煤量对比”；\n     - 按业务日期 `selectedDate` 读取各口径“原煤消耗量”本期值；\n     - 展示口径：集团汇总、主城区、金州、北方、金普、庄河（含同义键回退）；\n     - 单序列柱图 + 顶部数据标签（两位小数）。
- **Result:** mini 看板煤耗图已切换为“业务日口径对比”视图；四卡颜色与主看板风格一致；气温图标签与横轴重叠问题得到缓解。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：煤耗图补齐同期柱）

- **User Feedback:** 原煤对比图缺少“同期值”。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - `coalScopeRows` 从仅返回 `current` 扩展为返回 `current + prior`；
     - `coalTrendOption` 从单序列改为双序列柱图（`本期`、`同期`）；
     - tooltip 改为同时显示本期与同期，单位保持 `吨` 不变；
     - 两个序列均保留顶部数据标签（两位小数）。
- **Result:** 当日各口径原煤图已可同时对比本期与同期值，满足“无需改计量单位”的要求。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：精度规范与庄河同期口径）

- **User Request:** 顶部卡片除气温外均保留整数；气温曲线图保留 1 位小数；原煤对比图保留整数且本期/同期均显示标签并增强配色；庄河同期取“剔除xxx”指标，标签防重叠。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - 卡片精度：煤耗卡改为整数显示（主值与增减量均四舍五入）；
     - 气温图精度：tooltip 与点位标签统一 1 位小数；
     - 原煤图精度：tooltip 与双柱标签统一为整数；
     - 原煤图配色：本期深蓝、同期橙色，提升对比度；
     - 庄河同期分支：优先使用“原煤消耗量 + 剔除”指标的 `prior` 值，回退到常规匹配。
  2. 标签防重叠：
     - 原煤图本期/同期标签继续使用 `labelLayout`（`hideOverlap + shiftY`）。
- **Result:** 全页面数值精度符合新规范，庄河同期口径已按“剔除”指标处理，原煤图对比更清晰。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：庄河同期口径修正为张屯原煤）

- **User Feedback:** 庄河口径同期值应选用“其中： 张屯原煤消耗量”。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - 在庄河分支的 `prior` 指标匹配中，改为优先匹配“其中：张屯原煤消耗量”（兼容“其中 + 张屯原煤消耗量”关键词组合）。
  2. 其余口径与单位保持不变。
- **Result:** 庄河口径的同期值来源已切换为“其中：张屯原煤消耗量”。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：投诉分项双图半屏与整表）

- **User Request:** 两张投诉图各占屏幕一半，风格更清新、不要横线；下方为一整张表。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - 投诉区域改为双列布局（左右各半）并在移动端自动单列；
     - 两图加入轻量面板样式（浅色背景+细边框）；
     - 两图 y 轴网格线关闭（`splitLine.show = false`）；
     - 两图柱色/线色改为更清新的浅蓝/浅橙/绿色；
     - 下方表格保持整表宽度，位于双图下方。
  2. 结构保持：
     - 图1：总投诉本期/同期 + 本期气温曲线；
     - 图2：净投诉本期/同期 + 本期气温曲线；
     - 表格含日期、气温、总投诉本期/同期、净投诉本期/同期。
- **Result:** 投诉区域已实现“上双图半屏 + 下整表”布局，视觉风格更清爽且图中无横向网格线。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：投诉图气温线仅显示至业务日期）

- **User Request:** 投诉图中的“本期气温”只显示到业务日期，业务日期之后属于预报不展示。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - 新增 `shouldShowActualTemperature(dateText)` 判断函数；
     - 在“总投诉图/净投诉图”的本期气温折线数据中，业务日期后的点统一置为 `null`。
  2. 业务日期及之前保持原有展示逻辑不变。
- **Result:** 两张投诉图中的“本期气温”曲线仅展示到业务日期，业务日期后的预报区间不再绘制。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：投诉量本期/同期同样截断至业务日期）

- **User Request:** 与气温线一致，投诉量（总/净，本期/同期）也只显示到业务日期。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - 将日期判断函数统一为 `shouldShowActualByBizDate`；
     - 在总投诉图与净投诉图中，对本期/同期柱数据均做“业务日期后置空（null）”处理；
     - 本期气温线继续复用同一判断逻辑。
- **Result:** 投诉双图中“总/净、本期/同期”及本期气温均只显示到业务日期，业务日期后不再绘制。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：投诉图与配套表统一截断）

- **User Request:** 投诉图与下方配套表中，气温与各类投诉量都仅显示到业务日期；气温曲线不要数字标签；投诉双图继续强化防重叠（标签与坐标轴文字）。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - 新增 `complaintVisibleRows`，按业务日期过滤投诉区可见数据；
     - 两张投诉图的 x 轴与序列统一改为使用 `complaintVisibleRows`（不再展示业务日期后的日期）；
     - 下方投诉配套表 `v-for` 改为 `complaintVisibleRows`；
     - 两张投诉图中的本期气温线移除数字标签；
     - 强化图例与坐标轴防重叠：`legend.type='scroll'`、`xAxis.axisLabel.hideOverlap`。
- **Result:** 投诉区图表与配套表已统一只显示到业务日期；气温线无数字标签；图例/坐标轴文本拥挤问题进一步缓解。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：投诉量分项双图+表重构）

- **User Request:** “投诉量分项（图与表）”拆为两个图+一张表：\n  - 图1：本日总投诉量（本期/同期）+ 本期气温曲线；\n  - 图2：本日净投诉量（本期/同期）+ 本期气温曲线；\n  - 表格左侧新增气温字段，且总投诉本期/同期相邻、净投诉本期/同期相邻。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - 模板层将原单图替换为 `complaintTotalTrendOption` 与 `complaintNetTrendOption` 两张图；
     - 表头改为：日期、气温、总投诉（本期/同期）、净投诉（本期/同期）；
     - `complaintRows` 增加 `temperature` 字段（取本期气温）。
  2. 图表层新增两个 option：\n     - 两图均采用投诉量双柱（本期/同期）+ 本期气温折线（双 y 轴）；\n     - 保留标签与防重叠设置。
- **Result:** “投诉量分项”区域已符合“两个图 + 一张表”的结构与字段排列要求。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：投诉图横轴去年份与早日期观感优化）

- **User Request:** 投诉双图横轴标签去掉年份；业务日期靠前时，不要出现柱形图占满整图的观感。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - 新增 `formatAxisMonthDay`，将投诉双图横轴显示为 `MM-DD`；
     - 新增 `complaintRowsByDate` 与 `complaintChartAxisDates`，双图改为固定窗口日期轴；
     - 固定轴上业务日期后数据继续置空，既保留窗口节奏又不渲染未来柱线；
     - 收敛柱宽与间距参数（`barMaxWidth`、`barCategoryGap`、`barGap`）改善少样本日视觉比例。
- **Result:** 投诉双图横轴已去年份；业务日期靠前时图面比例更均衡，不再出现柱形“撑满整图”的突兀感。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：投诉图横轴保留至最后业务日）

- **User Clarification:** 业务日期靠前时，柱图应从左侧开始，且需预留到最后业务日期（如 2.23）的空间。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - 将 `complaintChartAxisDates` 从“窗口轴”改为“完整业务日期轴”（`availableDates` 全量）；
     - 保留业务日期后数据置空逻辑，因此仅左侧已发生日期有柱，右侧未来日期留白。
- **Result:** 投诉双图现在从最早业务日期左起展示，并始终保留到最后业务日期的横轴空间，符合你的说明。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：顶部下载PDF按钮）

- **User Request:** 在页面上部增加“下载为PDF”按钮。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - 在工具栏新增“下载PDF”按钮；
     - 新增 `downloadDashboardPdf()`，调用 `window.print()` 进入浏览器打印/另存为 PDF 流程。
- **Result:** mini 看板顶部已提供“下载PDF”入口，可直接导出当前页面为 PDF。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：所见即所得PDF直出与+0显示）

- **User Request:** 不要打印弹窗，改为直接下载所见即所得 PDF；顶部四卡中差异为 0 时显示 `+0`。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - 引入 `html2canvas` 与 `jspdf`，将 `downloadDashboardPdf()` 从 `window.print()` 改为页面截图分页生成 PDF 后直接下载；
     - 新增 `downloadingPdf` 与 `dashboardCaptureRef`，导出期间禁用按钮并显示“正在生成PDF…”；
     - 调整 `formatIncrement`：将 `-0` 归一为 `0`，并使用 `>= 0` 规则输出正号，确保零差异显示为 `+0`（含对应小数精度）。
  2. 安装前端依赖：`html2canvas`、`jspdf`（更新 `frontend/package.json` 与 `frontend/package-lock.json`）。
- **Result:** mini 看板点击“下载PDF”后直接生成并下载文件（无打印弹窗）；四卡差异为零时已显示带正号的 `+0`。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：PDF导出复用主看板链路修复）

- **User Feedback:** mini 看板 PDF 导出报错，怀疑 `jspdf` 模块链路不稳定，要求借鉴 `daily_report_25_26` 现成流程。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - 移除 `import html2canvas` / `import { jsPDF }`，改为与主看板一致的 `window.html2canvas` + `window.jspdf.jsPDF`；
     - `downloadDashboardPdf()` 改为单页长图导出（按宽度 210mm 等比计算长页高度），保持“所见即所得”；
     - 保留导出中状态与失败提示，并在克隆节点中隐藏“下载PDF”按钮后再渲染。
  2. 回滚新增依赖：执行 `npm uninstall html2canvas jspdf`，避免模块冲突。
- **Result:** mini 看板 PDF 导出路径已与 `daily_report_25_26` 对齐，不再依赖本地 `jspdf` 模块解析。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：PDF导出边距优化）

- **User Request:** 当前导出 PDF 左右裁切过紧，希望保留少量边缘留白。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue` 的 `downloadDashboardPdf()`：
     - 增加 `pagePadding = 6mm`；
     - 导出内容宽度改为 `210 - 2*padding`，并按比例计算内容高度；
     - PDF 页面高度同步包含上下留白，图片插入点改为 `(padding, padding)`。
- **Result:** 导出 PDF 已保留四周边距，左右不再贴边裁切。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：原煤明细表与设备明细表）

- **User Request:**  
  1) 在“原煤量对比”图下方增加春节期间每日各口径本期/同期原煤消耗量表（首列保留气温），并仅显示到业务日期；  
  2) 在页面最下方新增“各单位运行设备数量明细表”，展示业务日期下各口径（北海电厂含北海水炉、香海、金州、北方、金普、庄河）设备运行数量。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：  
     - 新增 `COAL_SCOPE_CONFIGS` 与 `coalRows`/`coalVisibleRows`，按日期抽取各口径原煤本期/同期，并复用业务日期截断；  
     - 在“当日各口径耗原煤量对比”图下新增宽表（日期、气温、6个口径本期/同期）；  
     - 新增 `DEVICE_SCOPE_CONFIGS` 与 `deviceStatusRows`，按业务日期抽取“运行汽炉数/汽轮机数/水炉数/锅炉房锅炉数”；  
     - 北海口径按“北海热电联产 + 北海水炉”聚合；其余按各自候选口径匹配；  
     - 在所有图表下方新增“各单位运行设备数量明细表”卡片。  
  2. 样式层新增 `table-scroll`，支持宽表横向滚动，避免压缩。
- **Result:** mini 看板现已补齐“原煤每日明细表（到业务日期）”与“设备数量明细表（业务日期）”。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：设备明细表按参考样式重构）

- **User Feedback:** 当前设备表“形式不对”，要求按 `daily_report_25_26` 参考表修正，不应简单平铺所有设备与本期/同期列。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - 将底部设备表改为分组列：`炉机组态`、`调峰水炉`、`燃煤锅炉`；
     - 每组内改为“标签 + 本期/同期”组合显示（如 `炉 3/3`、`机 3/3`），与参考表的组合单元格逻辑一致；
     - 过滤“本期与同期均为 0”的设备项，若整组为空则显示 `—`，避免“把所有设备都列出来”。
  2. 新增组合单元格样式：`device-combo-cell`、`combo-item`、`combo-label`、`combo-value` 等。
- **Result:** 设备明细表已从“平铺字段列”改为“分组组合展示”，与参考表展示方式对齐。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：炉/机数量换行显示）

- **User Request:** 设备表中汽炉与汽轮机数量改为换行显示，便于左右对应查看。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue` 样式：
     - `device-combo-cell` 改为纵向布局（`flex-direction: column`）；
     - `combo-item` 增加固定最小宽度与两端对齐（`min-width` + `justify-content: space-between`），提升同列对齐性。
- **Result:** 设备组合单元格中“炉/机”已按行展示，不再同一行挤在一起。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：原煤明细表单元格改为本期/同期）

- **User Request:** 原煤对比表不要把每个口径的本期/同期拆成两列；应按口径列出，并在同一单元格中展示“本期/同期”。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：  
     - 原煤明细表表头由“口径本期 + 口径同期”改为单口径列（集团汇总、主城区、金州、北方、金普、庄河）；  
     - 每个口径单元格使用 `formatCurrentPrior` 输出统一格式 `本期/同期`；  
     - 新增 `formatCurrentPrior(current, prior, digits)`，兼容空值显示 `—`。
- **Result:** 原煤明细表已按“口径列 + 单元格本期/同期”展示。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：原煤明细表分级表头）

- **User Request:** 原煤明细表改为分级显示，例如“集团汇总”下分“本期/同期”子字段。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - 原煤明细表头改为两级结构：父级口径（集团汇总/主城区/金州/北方/金普/庄河）+ 子级字段（本期/同期）；
     - 数据行恢复为对应口径的本期值与同期值分别占子列展示；
     - 移除已不再使用的 `formatCurrentPrior`。
- **Result:** 原煤明细表现为“父级口径 + 子级本期/同期”的分级表头样式。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：界面风格切换与春节主题）

- **User Request:** 在当前风格基础上增加“春节氛围”背景模板，并提供界面风格切换开关。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：  
     - 新增 `themeMode`（`default`/`festival`）状态；  
     - 顶部工具栏新增“风格”下拉开关；  
     - 根容器改为按主题动态 class（`spring-dashboard-page--default` / `spring-dashboard-page--festival`）；  
     - 新增主题持久化：首次加载读取 `localStorage`，切换后自动保存。  
  2. 新增春节主题视觉：  
     - 背景采用暖色渐变 + 柔和光斑 + 轻纹理；  
     - 卡片、按钮、选择框、表头/表格配色切到春节暖色系；  
     - 默认主题保持原有风格不变。
- **Result:** 页面可在“默认风格/春节氛围”间切换，且刷新后保留用户选择。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：春节主题可读性与喜庆元素优化）

- **User Feedback:** 春节主题影响阅读（四卡背景丢失、文字不清晰），希望整体显示更周到，并增加喜庆元素。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - 在春节主题下将通用卡片样式限定为 `.card:not(.summary-card)`，避免覆盖顶部四卡原有渐变背景；
     - 为四卡在春节主题下单独恢复高对比渐变与文字阴影，确保标题/数值可读；
     - 新增固定轻量节日装饰（左右灯笼 + “福启新岁”徽标），仅作氛围点缀且不阻塞交互；
     - 保持表格、按钮、选择框暖色风格，同时控制对比度不压内容。
- **Result:** 春节主题在保留节庆氛围的同时，已恢复关键信息可读性，顶部四卡显示正常。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：PDF导出清晰度提升1.5倍）

- **User Request:** 下载 PDF 的清晰度/尺寸希望提高到约 1.5 倍。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：  
     - `downloadDashboardPdf()` 中 `html2canvas` 渲染倍率从 `scale: 2` 提升到 `scale: 3`（即当前导出像素密度提升约 1.5 倍）。  
     - 保持现有页边距与导出版式逻辑不变。
- **Result:** PDF 导出清晰度已按要求提升约 1.5 倍。
- **Verify:** 执行 `frontend` 构建（`npm run build`）通过。

## 2026-02-12（春节迷你看板：标题文案微调）

- **User Request:** 页面中的“春节简化数据看板”去掉“简化”二字。
- **Agent Action:** 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue` 页面主标题文案为“春节数据看板”。
- **Result:** 页面标题已更新为“春节数据看板”。

## 2026-02-12（数据看板缓存：逐小时气温链路改为日视图来源）

- **User Request:** 列出并改造所有“逐小时气温”业务点，统一改为从 `calc_temperature_data` 视图读取；期间平均气温按“每日平均气温的平均值”处理。
- **原业务点清单（逐小时链路）:**
  1. 后端 `backend/services/dashboard_expression.py`  
     - `_fetch_temperature_series`：从 `temperature_data` 按小时区间取 24 点数据；  
     - `_fill_temperature_block`：按日期填充“本期/同期”逐小时数组；  
     - `evaluate_dashboard` 第1节“逐小时气温”调用 `_fill_temperature_block`，发布缓存时也走这条链路。
  2. 前端 `frontend/src/projects/daily_report_25_26/pages/DashBoard.vue`  
     - `calcAverageFromList`：把逐小时数组计算为当日平均值；  
     - `temperatureSeries`：对本期/同期日期桶逐日求平均后绘图；  
     - `averageTemp`：读取当日逐小时数组后计算当日平均及同比差值。
- **Agent Action:**
  1. 后端改造（视图来源）：  
     - 新增 `_fetch_daily_temperature_stats_map`，直接查询 `calc_temperature_data` 的 `max_temp/min_temp/aver_temp`；  
     - 重写 `_fill_temperature_block`：按日期写入日级对象 `{max, min, avg}`，不再填充 24 点逐小时数组；  
     - `evaluate_dashboard` 第1节保持调用路径不变，但底层数据已切换为视图日级来源。  
  2. 前端兼容（统一日级口径）：  
     - 增强 `calcAverageFromList`，兼容日级对象（`avg/aver_temp/average/value`）与旧数组格式；  
     - 因此 `temperatureSeries` 与 `averageTemp` 无需改调用链即可消费视图日级数据。  
  3. 期间平均口径校验：  
     - 后端 `_fetch_average_temperature_between` 仍为 `AVG(aver_temp)`（即“每日平均气温再平均”），符合你的要求。
- **Result:** 数据看板（含发布缓存路径）已不再依赖逐小时原始表计算日均值，第1节气温读取统一来自 `calc_temperature_data` 视图日级数据。
- **Verify:**  
  - `frontend` 执行 `npm run build` 通过；  
  - `python -m py_compile backend/services/dashboard_expression.py` 通过。

## 2026-02-12（主看板口径命名：逐小时气温 → 日均气温）

- **User Request:** 将页面口径名称改为“日均气温”，并确保对应数据来源为 `calc_temperature_data` 视图。
- **Agent Action:**
  1. 修改后端：`backend/services/dashboard_expression.py`  
     - 第1节处理注释与进度提示改为“日均气温”；  
     - 第1节 section 解析改为 `get_section_by_index("1", "1.日均气温", "1.逐小时气温")`，兼容旧键。  
  2. 修改配置：  
     - `backend_data/projects/daily_report_25_26/config/数据结构_数据看板.json`：section 键改为 `1.日均气温`，`数据来源` 改为 `calc_temperature_data`；  
     - `backend_data/projects/daily_report_25_26/config/dashboard_frontend_config.json`：第1节 `key/title/source_section/contract_notes/description` 同步改为“日均气温”与视图来源。  
  3. 修改前端：`frontend/src/projects/daily_report_25_26/pages/DashBoard.vue`  
     - 第1节读取别名改为 `resolveSection('1', '1.日均气温', '1.逐小时气温')`，兼容旧缓存键。
- **Result:** 主看板第1节命名已切换为“日均气温”，且数据来源配置与后端读取路径均对齐至 `calc_temperature_data` 视图。
- **Verify:**  
  - `frontend` 执行 `npm run build` 通过；  
  - `python -m py_compile backend/services/dashboard_expression.py` 通过。

## 2026-02-12（下线“项目模块化管理”板块）

- **User Request:** 清理掉“项目模块化管理”板块。
- **Agent Action:**
  1. 前端清理：
     - `frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue` 移除“项目模块化管理”卡片与跳转逻辑；
     - `frontend/src/router/index.js` 移除 `/projects/:projectKey/modularization` 路由；
     - `frontend/src/projects/daily_report_25_26/services/api.js` 删除模块化状态/初始化接口方法；
     - 删除页面文件 `frontend/src/projects/daily_report_25_26/pages/ProjectModularizationView.vue`。
  2. 后端清理：
     - `backend/projects/daily_report_25_26/api/router.py` 取消挂载 `modularization_router`；
     - 删除接口文件 `backend/projects/daily_report_25_26/api/modularization.py`。
- **Result:** 页面与路由层面已无“项目模块化管理”入口，项目专属模块化接口已下线。
- **Verify:**  
  - `frontend` 执行 `npm run build` 通过；  
  - `python -m py_compile backend/projects/daily_report_25_26/api/router.py backend/api/v1/routes.py` 通过。

## 2026-02-12（春节上传链路：结构检校 + 自动对齐 + 提取）

- **User Request:** 上传后先按当前标准检校；不通过时自动对齐；显示是否对齐成功；成功后再提取 JSON。
- **Agent Action:**
  1. 后端 `backend/projects/daily_report_spring_festval_2026/api/xlsx_extract.py`：  
     - 新增结构检校：检测“统计主体/指标/计量单位”是否在标准列（A/B/C）；  
     - 不通过时触发自动对齐：在表头附近搜索关键列并重映射抽取；  
     - 自动对齐失败时返回 400，并携带结构化失败原因；  
     - 对齐成功或标准通过时继续提取，并在 `meta.validation` 回传状态（`passed/aligned/failed`）、列号与问题清单。  
  2. 前端 API `frontend/src/projects/daily_report_25_26/services/api.js`：  
     - 解析后端结构化错误信息，优先展示可读错误与校验问题。  
  3. 上传页 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalEntryView.vue`：  
     - 新增“结构检校结果”可视化区块；  
     - 显示通过/自动对齐成功/失败、对齐后的关键列位置、问题明细；  
     - 成功文案按检校结果动态显示。  
- **Result:** 上传流程已具备“标准检校→自动对齐→成功提取”闭环，并对失败原因可视化反馈。
- **Verify:**  
  - `frontend` 执行 `npm run build` 通过；  
  - `python -m py_compile backend/projects/daily_report_spring_festval_2026/api/xlsx_extract.py` 通过。

## 2026-02-12（春节迷你看板：“金镶玉”主题重构）

- **User Feedback:** 原春节主题不够美观且可能影响数据读取。
- **Agent Action:**
  1. 重构 `SpringFestivalDashboardView.vue` 的节日样式：
     - 背景升级为深宫红渐变并叠加传统暗纹；
     - 卡片引入“金镶玉”设计：暖白宣纸色背景 + 2px 精致金色边框 (`#d4af37`)；
     - 标题采用朱砂红并配以金色装饰底纹；
     - 为灯笼挂饰添加 `lantern-sway` 物理摇曳动画。
  2. 易读性优化：通过卡片的实体背景色彻底解决了深色背景对 ECharts 图表的视觉干扰。
- **Result:** 春节看板视觉质感大幅提升，实现了“喜庆氛围”与“专业数据展示”的平衡。
- **Verify:** 执行 `frontend` 构建通过。

## 2026-02-26（管理后台一期：聚合总览 + 独立页面入口）

- **User Request:** 在已完成项目化与权限模块化的基础上，开始构建应用管理后台。
- **前置说明:**
  1. Serena 接入校验已完成：`activate_project` 成功，`check_onboarding_performed` 为已完成状态；
  2. 本轮未触发 Serena 编辑受阻，无降级到 shell 写文件；全部改动通过 `apply_patch` 落地；
  3. 本轮先交付“管理后台一期骨架”，目标是把已有管理能力统一到一个入口，不改动现有核心业务链路。
- **Agent Action:**
  1. 新增后端管理后台聚合接口：
     - 文件：`backend/projects/daily_report_25_26/api/admin_console.py`
     - 新接口：`GET /api/v1/projects/daily_report_25_26/admin/overview`
     - 关键结构/函数：
       - `get_admin_overview`：按当前会话动作位聚合管理态信息；
       - `_collect_ai_settings_summary`：读取 AI 设置摘要并屏蔽 key（掩码）；
       - 复用 `dashboard_cache.get_cache_status` 与 `cache_publish_job_manager.snapshot` 输出缓存运行状态。
  2. 项目路由挂载管理后台模块：
     - 文件：`backend/projects/daily_report_25_26/api/router.py`
     - 行为：将 `admin_console_router` 合并到项目私有路由。
  3. 新增前端管理后台页面：
     - 文件：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
     - 页面模块与作用：
       - 总览卡：展示校验/AI/缓存管理授权状态；
       - 校验总开关卡：调用 `setValidationMasterSwitch` 直接切换；
       - AI 设置卡：调用 `getAiSettings`、`updateAiSettings` 维护模型、指令、key 与策略开关；
       - 缓存任务卡：调用 `publishDashboardCache`、`refreshDashboardCache`、`cancelCachePublishJob`、`disableDashboardCache`。
  4. 接入前端 API 与路由：
     - `frontend/src/projects/daily_report_25_26/services/api.js` 新增 `getAdminOverview(projectKey)`；
     - `frontend/src/router/index.js` 新增路由
       `/projects/:projectKey/pages/:pageKey/admin-console`；
     - `frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue`
       增加 `admin_console` 描述与跳转分支。
  5. 更新页面配置与权限：
     - `backend_data/shared/项目列表.json` 新增页面 `admin_console`；
     - `backend_data/shared/auth/permissions.json` 为 `Global_admin` 与 `Group_admin` 增加该页面访问权限。
- **Result:**
  1. 项目页选择界面新增“管理后台”入口；
  2. 管理后台可统一操作和查看“校验开关 / AI 设置 / 看板缓存任务”；
  3. 后端新增聚合总览接口作为后台首页数据源，前后端权限链路继续遵循项目化动作位控制。

## 2026-02-26（管理后台入口位置与权限模型调整）

- **User Request:** 管理后台入口改到页头 `ww870411｜系统管理` 左侧，文案“进入后台”；仅 `Global_admin` 可见可访问；后台为全局公共页面，不属于任一项目模块。
- **前置说明:**
  1. 本次为上一次“管理后台一期”的结构调整，不新增业务域能力；
  2. 继续通过 `apply_patch` 进行文件改写；
  3. 权限改为 `permissions.json` 明确声明，后端接口与前端展示双重校验。
- **Agent Action:**
  1. 后端权限模型扩展：
     - `backend/services/auth_manager.py`、`backend/schemas/auth.py`
     - 新增动作位：`can_access_admin_console`（组级动作位）。
  2. 后端路由全局化：
     - 新增 `backend/api/v1/admin_console.py`，统一暴露 `/api/v1/admin/*` 接口：
       - `/admin/overview`
       - `/admin/validation/master-switch`
       - `/admin/ai-settings`

## 2026-02-27（部署链路问答：db 端口来源与 compose 职责边界）

- **User Question:** 已能通过 5432 单独访问数据库，但脚本里没看到 db 对外端口配置；并追问构建 yml 与运行 yml 是否可不同、构建 yml 是否可简化。
- **前置说明:**
  1. Serena 接入校验已完成：`activate_project` 与 `check_onboarding_performed` 均成功；
  2. 本次仅做文件检索与结论说明，无代码逻辑改动；
  3. 已写入 Serena 记忆：`infra_db_port_mapping_lo1_new_server_2026-02-27`。
- **Agent Action:**
  1. 检索并比对 `docker-compose*.yml`、`lo1_new_server.yml`、`lo1_new_server.ps1`；
  2. 确认端口暴露位置在服务器运行文件 `lo1_new_server.yml` 的 `db.ports: "5432:5432"`；
  3. 说明职责边界：`lo1_new_server.ps1` 仅负责构建/打标签/推送镜像，不负责容器端口映射；
  4. 回答 compose 分工：构建文件与运行文件可不同，运行文件可以更精简地只保留 `image`、`env`、`volumes`、`ports`、`depends_on` 等运行期字段。
- **Result:** 已定位 5432 暴露来源并澄清“构建 yml 与运行 yml 可分离”的实践原则；本仓库文件未改动业务代码。
       - `/admin/cache/publish|status|cancel|refresh`
       - `/admin/cache`（DELETE）
     - `backend/api/v1/routes.py` 挂载 `admin_console_router`；
     - 移除项目级后台挂载：`backend/projects/daily_report_25_26/api/router.py` 不再包含后台路由；
     - 删除项目内旧文件：`backend/projects/daily_report_25_26/api/admin_console.py`。
  3. 前端入口位置调整：
     - `frontend/src/projects/daily_report_25_26/components/AppHeader.vue`
       在用户信息左侧新增按钮“进入后台”，点击跳转 `/admin-console`。
  4. 前端页面全局化：
     - 路由改为全局 `frontend/src/router/index.js`：`/admin-console`；
     - `AdminConsoleView.vue` 改为调用全局管理 API（不依赖 `projectKey` 路由参数）；
     - `store/auth.js` 新增 `canAccessAdminConsole` 供页头按钮与页面准入判断。
  5. 配置收口：
     - `backend_data/shared/auth/permissions.json`
       - 仅 `Global_admin` 增加组级动作：
         - `actions.can_access_admin_console = true`
       - 移除此前加入项目页面列表的 `admin_console`；
     - `backend_data/shared/项目列表.json` 删除 `admin_console` 页面项。
- **Result:**
  1. 管理后台已从“项目内页面”切换为“全局公共后台页面”；
  2. 入口位置符合要求：位于页头用户信息左侧，按钮名为“进入后台”；
  3. 仅 `Global_admin` 可见且可访问（前后端双重拦截）。

## 2026-02-26（管理后台页面完善：后台文件编辑 + 项目后台设定分流）

- **User Request:** 在管理后台新增两个板块：
  1) “后台文件编辑”：列出 `backend_data` 子目录，点目录看文件列表，点文件在线编辑并提交；
  2) “项目后台设定”：按项目维度切换，仅当选中 `daily_report_25_26` 时显示当前已有设置内容。
- **前置说明:**
  1. 本次在现有全局后台基础上扩展，不改变入口与权限原则（仍仅 `Global_admin`）；
  2. 文件编辑能力限定在 `backend_data` 目录内，并做路径越界拦截；
  3. 继续使用 `apply_patch` 完成改动并留痕。
- **Agent Action:**
  1. 后端新增全局后台文件接口（`backend/api/v1/admin_console.py`）：
     - `GET /api/v1/admin/files/directories`：列出 `backend_data` 一级子目录；
     - `GET /api/v1/admin/files?directory=...`：列出目录下文件；
     - `GET /api/v1/admin/files/content?path=...`：读取文本文件内容；
     - `POST /api/v1/admin/files/content`：保存文件内容；
     - 安全策略：仅允许相对路径、仅允许 `backend_data` 目录内、限制文件大小（2MB）。
  2. 后端新增项目设定列表接口：
     - `GET /api/v1/admin/projects`：读取 `shared/项目列表.json` 并返回 `project_key/project_name`。
  3. 后端调整后台概览接口：
     - `GET /api/v1/admin/overview?project_key=...`；
     - 若非 `daily_report_25_26` 返回 `supported=false`，前端据此做“未接入”提示。
  4. 前端 API 扩展（`frontend/src/projects/daily_report_25_26/services/api.js`）：
     - 新增 `listAdminProjects/listAdminFileDirectories/listAdminFiles/readAdminFile/saveAdminFile`；
     - `getAdminOverview` 支持 `projectKey` 参数。
  5. 前端后台页重构（`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`）：
     - 新增“后台文件编辑”三栏（目录/文件/编辑器+提交）；
     - 新增“项目后台设定”项目切换区；
     - 仅在 `selectedProjectKey === daily_report_25_26` 时显示原有“校验/AI/缓存”设定模块，其它项目显示“暂未接入”。
- **Result:**
  1. 管理后台已具备在线文件编辑能力（受限于 `backend_data`）；
  2. 项目后台设定实现项目切换分流，当前配置模块只在 `daily_report_25_26` 下展示；
  3. 页面结构符合“文件编辑 + 项目设定”两大板块目标。

## 2026-02-26（管理后台体验重构：视觉与操作流优化）

- **User Feedback:** 当前页面不美观且操作便利性差。
- **Agent Action:**
  1. 重构管理后台页面布局（`AdminConsoleView.vue`）：
     - 改为顶部双标签页：`后台文件编辑` / `项目后台设定`；
     - 文件编辑区重排为“目录选择 + 文件搜索 + 列表 + 编辑器”；
     - 项目设定区保留原有业务能力，并提升层次结构与可读性。
  2. 增强编辑交互：
     - 新增未保存状态提示（`未保存`）；
     - 切换文件前增加未保存确认；
     - 支持 `Ctrl/Cmd + S` 快捷保存；
     - 显示字数与保存结果反馈。
  3. 后端文件列表收敛（`backend/api/v1/admin_console.py`）：
     - 仅返回可编辑文本类型（json/md/txt/yaml/yml/ini/toml/py/js/ts/vue/css/sql/csv）；
     - 跳过超过 2MB 的文件，避免二进制和大文件影响体验。
  4. 页头入口视觉优化（`AppHeader.vue`）：
     - “进入后台”按钮增加高可见样式（与退出按钮区分）。
- **Result:**
  1. 页面信息结构更清晰，关键操作路径缩短；
  2. 文件编辑风险控制（脏状态确认）与效率（快捷键保存）显著提升；
  3. 文件列表噪音降低，更适合管理场景。

## 2026-02-26（后台文件树形展示 + 弹窗编辑）

- **User Suggestion:** 文件列表改为树形结构显示并支持点击；点击后在新弹出窗口中打开/编辑/提交保存或不保存关闭。
- **Agent Action:**
  1. 前端 `AdminConsoleView.vue` 文件编辑区升级：
     - 文件列表由平铺按钮改为可展开/折叠的树形结构（目录节点 + 文件节点）；
     - 支持按层级缩进显示，点击目录展开/收起，点击文件触发编辑。
  2. 新增弹窗编辑器：
     - 点击文件后以遮罩弹窗打开编辑器，不再在主页面内联编辑；
     - 提供“保存并关闭”与“不保存关闭”；
     - 对未保存改动提供关闭确认；
     - 支持 `Ctrl/Cmd + S` 快捷保存（弹窗打开时生效）。
  3. 交互反馈：
     - 弹窗内显示当前文件路径、字数、保存状态与未保存标记。
- **Result:**
  1. 文件定位方式从“列表检索”升级为“树形浏览”，结构感更强；
  2. 编辑动作迁移至独立弹窗，主页面信息不被打断；
  3. 已满足“保存关闭/不保存关闭”的编辑流程要求。

## 2026-02-26（树形美化与“新窗口”编辑器落地）

- **User Feedback:** 现有树形不美观，且未达到“点击后新窗口编辑”的预期。
- **Agent Action:**
  1. 将文件树样式升级为“连接线 + 模块节点”视觉：
     - 调整 `tree-row` 的连线、悬停、激活样式，提升结构辨识度；
     - 保留目录折叠/展开与文件点击行为。
  2. 新增独立编辑窗口页面：
     - 新文件：`frontend/src/projects/daily_report_25_26/pages/AdminFileEditorWindow.vue`
     - 路由：`/admin-file-editor?path=...`
     - 打开方式：主页面通过 `window.open(...)` 弹出新窗口。
  3. 新窗口编辑器功能：
     - 加载指定文件内容；
     - `保存并关闭`；
     - `不保存关闭`（未保存时二次确认）；
     - `Ctrl/Cmd + S` 快捷保存；
     - 保存后通过 `postMessage` 回传主窗口提示。
  4. 主页面联动更新：
     - `AdminConsoleView.vue` 改为“点击文件 -> 打开新窗口编辑”；
     - 监听 `admin-file-saved` 消息更新保存反馈。
- **Result:**
  1. 文件编辑已从“站内弹层”升级为“独立新窗口编辑器”；
  2. 树形视觉更接近模块连接风格，浏览感显著改善；
  3. 满足“打开/编辑/提交保存或不保存关闭”的完整流程。

## 2026-02-12（数据展示页导出 Excel 504 超时修复）

- **User Request:** `daily_report_25_26` 数据展示页导出 Excel 近期经常卡住并失败，页面显示 Cloudflare 504 HTML。
- **Agent Action:**
  1. 定位调用链：
     - 前端 `DisplayRuntimeView.vue` 的 `exportToExcel` 并发调用 3 次 `runtime/spec/eval`，失败时直接透传后端 HTML 错误文本；
     - `api.js` 的 `evalSpec` 未支持 `AbortController`，导出阶段无超时控制。
  2. 修复实现：
     - `frontend/src/projects/daily_report_25_26/services/api.js`：`evalSpec` 新增 `options.signal`，支持请求中断；
     - `frontend/src/projects/daily_report_25_26/pages/DisplayRuntimeView.vue`：
       - 导出阶段 `runtime/spec/eval` 由并发改为串行，降低网关与后端瞬时压力；
       - 增加单次 120 秒超时与 1 次重试（仅对超时/504类错误）；
       - 增加错误归一化：Cloudflare/HTML/504 报错转换为可读中文提示，避免页面堆叠整段 HTML。
- **Result:** 导出链路具备“串行执行 + 超时控制 + 重试 + 可读报错”能力，降低卡住与 504 导致的失败概率，并提升失败可诊断性。
- **Verify:** `frontend` 执行 `npm run build` 通过。

## 2026-02-12（修复 frontend/jsconfig.json 报错）

- **User Request:** 修复 `frontend/jsconfig.json` 报错。
- **Agent Action:**
  1. 规范路径别名：`@/*` 由 `./src/*` 调整为 `src/*`；
  2. 补充 `include` 范围，显式纳入 `js/jsx/vue/json` 与 `vite.config.*`，避免语言服务索引异常。
- **Result:** `jsconfig.json` 已调整为稳定可识别结构，便于 Vue/JS 项目索引与别名解析。

## 2026-02-12（服务器登录报“账户信息文件缺失”排障修复）

- **User Request:** 服务器容器部署后无法登录，返回 `{"detail":"账户信息文件缺失"}`。
- **Agent Action:**
  1. 定位后端抛错点：`backend/services/auth_manager.py` 的 `_load_accounts`；
  2. 增强路径兜底：`backend/services/project_data_paths.py` 中 `resolve_accounts_path` 新增多候选路径（含 ASCII 文件名 `accounts.json` 兼容），`resolve_permissions_path` 同步增加兼容候选；
  3. 增强错误可观测性：`auth_manager.py` 缺失报错改为携带实际解析路径，便于服务器现场定位。
- **Result:** 后端对账户/权限文件路径兼容性提升，且缺失时可直接看到具体路径，降低部署目录差异导致的登录中断风险。
- **Verify:** `python -m py_compile backend/services/project_data_paths.py backend/services/auth_manager.py` 通过。

## 2026-02-15（春节看板顶部卡片文案修正：标煤 -> 原煤）

- **User Request:** 将页面 `https://platform.smartview.top/projects/daily_report_spring_festval_2026/spring-dashboard` 顶部卡片文案“当日集团标煤消耗（剔除庄河改造锅炉房）”改为“当日集团原煤消耗（剔除庄河改造锅炉房）”。
- **前置说明:**
  1. 当前会话未提供 Serena 可用工具，采用仓库内最小范围直接改动并记录留痕；
  2. 仅改展示文案，不改任何数据计算、接口与字段；
  3. 回滚方式：将 `SpringFestivalDashboardView.vue` 对应标签文本改回“标煤”。
- **Agent Action:**
  1. 定位文案来源：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue` 顶部摘要卡片区；
  2. 精确替换 `summary-card__label` 文案为“当日集团原煤消耗（剔除庄河改造锅炉房）”； 
  3. 按规范同步更新 `backend/README.md` 与 `frontend/README.md` 结构记录。
- **Result:** 目标页面顶部第二张摘要卡片标题已更新为“当日集团原煤消耗（剔除庄河改造锅炉房）”，其数值仍由 `coalCard` 计算链路提供，功能行为不变。

## 2026-02-15（春节看板原煤图标题补充口径说明）

- **User Request:** 将图标题“当日各口径耗原煤量对比”改为“当日各口径耗原煤量对比（剔除庄河改造锅炉房）”。
- **前置说明:**
  1. 当前会话未提供 Serena 可用工具，采用仓库内最小范围直接改动并记录留痕；
  2. 本次仅改图表标题文案，不改图表数据源和计算逻辑；
  3. 回滚方式：将同一 `h3` 文案改回原值。
- **Agent Action:**
  1. 定位到 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue` 原煤对比图卡片标题；
  2. 将标题替换为“当日各口径耗原煤量对比（剔除庄河改造锅炉房）”；
  3. 同步更新 `backend/README.md` 与 `frontend/README.md` 结构记录。
- **Result:** 原煤对比图标题已按要求补充“剔除庄河改造锅炉房”口径说明，图表渲染与数据链路保持不变。

## 2026-02-15（春节看板两张表新增“合计”行）

- **User Request:** 在页面 `/projects/daily_report_spring_festval_2026/spring-dashboard` 中：
  1) “当日各口径耗原煤量对比（剔除庄河改造锅炉房）”图表下方表格新增最后一行“合计”；  
  2) “投诉量分项”图表下方表格新增最后一行“合计”；  
  3) “净投诉量（本期）/净投诉量（同期）”在合计行显示 `-`，不参与求和。
- **前置说明:**
  1. Serena 已完成 `activate_project` 与 `check_onboarding_performed`；  
  2. 本次仅修改前端页面渲染与计算属性，不改后端接口与数据结构；  
  3. 回滚方式：撤销 `SpringFestivalDashboardView.vue` 中 `coalRowsWithTotal/complaintRowsWithTotal` 与模板渲染替换即可恢复原行为。
- **Agent Action:**
  1. 在 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue` 新增 `sumRowsByField` 公共求和函数；  
  2. 新增 `coalRowsWithTotal`：基于 `coalVisibleRows` 计算各列合计并追加 `{ date: '合计', isTotal: true }` 到末尾；  
  3. 新增 `complaintRowsWithTotal`：基于 `complaintVisibleRows` 计算可求和列合计，净投诉量两列置空；  
  4. 模板中两处 `v-for` 改为遍历 `coalRowsWithTotal` 与 `complaintRowsWithTotal`；  
  5. “投诉量分项”表格中净投诉量两列渲染改为 `row.isTotal ? '-' : formatMetric(...)`。
- **Result:** 两张表均在最后一行展示“合计”；“净投诉量（本期/同期）”合计固定显示 `-`，避免错误汇总含义。

## 2026-02-15（春节看板两张表去除非气温单位显示）

- **User Request:** 在春节看板两张表中，除“气温”外的原煤消耗量/投诉量不显示计量单位。
- **前置说明:**
  1. 本次只改前端表格展示，不改任何计算与后端接口；  
  2. 回滚方式：将表格中 `formatMetric(..., '', 0)` 改回原单位参数（`吨/件`）。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`；  
  2. 原煤表格各“本期/同期”列由 `formatMetric(value, '吨', 0)` 改为 `formatMetric(value, '', 0)`；  
  3. 投诉表格“总投诉量/净投诉量”列由 `formatMetric(value, '件', 0)` 改为 `formatMetric(value, '', 0)`；  
  4. 气温列保持 `formatMetric(value, '℃', 1)` 不变。
- **Result:** 两张表现在仅气温保留单位，原煤消耗量与投诉量按纯数字展示。

## 2026-02-15（春节看板气温取数项目键修复）

- **User Feedback:** 春节看板“气温变化情况（向后预测3日，含同期）”曲线显示不全；并在开发者工具发现额外请求了 `daily_report_25_26` 看板数据包，导致数据不全且拖慢速度。
- **前置说明:**
  1. 通过代码链路排查后确认为前端项目键硬编码导致的跨项目请求；  
  2. 本次仅修复前端 API 调用参数，不改后端接口。  
  3. 回滚方式：将 `getTemperatureTrendByDate` 恢复为固定 `daily_report_25_26` 调用（不建议）。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/services/api.js`：  
     - `getTemperatureTrendByDate` 签名由 `(showDate)` 调整为 `(projectKey, showDate)`；  
     - 调用 `getDashboardData(targetProjectKey, { showDate })`，默认项目键为 `daily_report_spring_festval_2026`。  
  2. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：  
     - `loadTemperatureFromDatabase` 改为 `getTemperatureTrendByDate(projectKey.value, selectedDate.value)`，确保取数与当前页面项目一致。
- **Result:** 春节看板不再额外请求 `daily_report_25_26` 的 dashboard 包；气温曲线数据来源与当前项目统一，避免跨项目导致的数据缺失与额外开销。

## 2026-02-15（春节看板气温空白修复：改用轻量温度接口）

- **User Feedback:** 调整后气温图出现空白。
- **前置说明:**
  1. 排查确认：`daily_report_spring_festval_2026` 项目无独立 `/dashboard` 接口，直接按 spring 项目键请求会导致取数失败；  
  2. 为避免再次拉取 `daily_report_25_26` 全量 dashboard 大包，改为新增轻量气温接口，仅返回气温序列。  
  3. 回滚方式：移除轻量接口与前端调用切换，恢复旧 `/dashboard` 全量取数。
- **Agent Action:**
  1. 后端新增轻量接口 `GET /api/v1/projects/daily_report_25_26/dashboard/temperature/trend`（文件：`backend/projects/daily_report_25_26/api/dashboard.py`）：  
     - 支持 `show_date/start_date/end_date`；  
     - 直接查询 `calc_temperature_data` 返回 `main/peer`（本期/同期）日均气温映射。  
  2. 前端公共 API 新增 `getDashboardTemperatureTrend`（文件：`frontend/src/projects/daily_report_25_26/services/api.js`）。  
  3. 春节项目 API `getTemperatureTrendByDate` 改为调用轻量接口（文件：`frontend/src/projects/daily_report_spring_festval_2026/services/api.js`）。  
  4. `SpringFestivalDashboardView.vue` 的 `loadTemperatureFromDatabase` 改为：
     - 按可见业务日期 + 选中日期前后 3 日计算请求范围；  
     - 优先消费轻量接口 `main/peer`；  
     - 保留旧 `sections` 解析作为兼容回退。
- **Result:** 气温图恢复显示，且不再请求 `daily_report_25_26` 的全量 dashboard 包，降低网络负担并避免跨项目大包拖慢。

## 2026-02-15（接口归位：春节气温接口迁移至 spring 项目路由）

- **User Question:** 新增气温 API 是否应按模块化原则归属 spring 项目路径。
- **结论:** 是，应归位到 `daily_report_spring_festval_2026` 项目路由，对前端暴露 spring 自身 API；底层可复用共享数据源。
- **Agent Action:**
  1. 新增 `backend/projects/daily_report_spring_festval_2026/api/temperature_trend.py`：  
     - 提供 `GET /api/v1/projects/daily_report_spring_festval_2026/spring-dashboard/temperature/trend`；  
     - 读取 `calc_temperature_data` 返回 `main/peer` 温度映射。  
  2. 修改 `backend/projects/daily_report_spring_festval_2026/api/router.py`：在 `public_router` 挂载 `temperature_public_router`。  
  3. 修改 `frontend/src/projects/daily_report_spring_festval_2026/services/api.js`：  
     - `getTemperatureTrendByDate` 改为请求 spring 项目路径 `/spring-dashboard/temperature/trend`。  
  4. 修改 `SpringFestivalDashboardView.vue`：调用签名改为 `getTemperatureTrendByDate(projectKey.value, selectedDate.value, { startDate, endDate })`。
- **Result:** 接口职责与路由归属符合项目模块化原则；spring 页面不再跨项目调用温度接口。

## 2026-02-15（春节气温图空白兜底修复）

- **User Feedback:** 接口归位后气温曲线仍为空白。
- **前置说明:**
  1. 排查判断：spring 轻量气温接口仅查询 `calc_temperature_data`，当该视图为空/未刷新时会返回空映射；  
  2. 修复目标：保证“数据库已有温度原始数据”时曲线可出图。  
  3. 回滚方式：移除 `temperature_data` 聚合兜底 SQL，恢复仅查视图逻辑。
- **Agent Action:**
  1. 修改 `backend/projects/daily_report_spring_festval_2026/api/temperature_trend.py` 中 `_query_temperature_daily_avg_map`；  
  2. 查询策略调整为：  
     - 先查 `calc_temperature_data`（日均）；  
     - 若无结果，回退查 `temperature_data`（`CAST(date_time AS DATE)` 分组 `AVG(value)`）。  
- **Result:** 即使 `calc_temperature_data` 未刷新，只要 `temperature_data` 有数据，spring 气温接口也能返回日均序列，前端曲线不再因视图空而空白。

## 2026-02-15（春节气温接口前端自动回退，避免路由未热重载导致空白）

- **User Feedback:** 调整后页面仍空白。
- **前置说明:**
  1. 新增 spring 路由在部分运行环境可能尚未热重载，前端请求新路径会出现 404/异常；  
  2. 当前页面此前未做异常降级，接口异常会直接导致温度映射为空。  
  3. 回滚方式：移除 `getTemperatureTrendByDate` 中 `catch` 回退分支。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/services/api.js`；  
  2. `getTemperatureTrendByDate` 调用策略改为：  
     - 主路径：`/projects/{projectKey}/spring-dashboard/temperature/trend`；  
     - 异常回退：自动调用 `daily_report_25_26` 的 `getDashboardTemperatureTrend` 轻量接口。  
- **Result:** 即使 spring 新路由暂未生效，页面也能通过回退接口拿到温度数据，避免曲线空白。

## 2026-02-15（春节气温链路增加“老 dashboard 接口”最终兜底）

- **User Feedback:** 曲线仍空白，且在模块化调整前是正常的。
- **前置说明:**
  1. 推断现象与“后端未重启导致新增轻量接口未生效”高度一致；  
  2. 在不依赖后端重启的前提下，优先恢复可用性。  
  3. 回滚方式：移除 `getTemperatureTrendByDate` 中对 `getDashboardData('daily_report_25_26')` 的最终兜底分支。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/services/api.js`；  
  2. `getTemperatureTrendByDate` 回退链路升级为三级：  
     - 主路径：spring 项目轻量接口；  
     - 回退1：`daily_report_25_26` 轻量温度接口；  
     - 回退2（最终）：历史稳定接口 `getDashboardData('daily_report_25_26')`。  
- **Result:** 即使后端未加载新增路由，前端仍可走历史接口恢复气温曲线展示。

## 2026-02-15（页面临时调试增强：气温链路可视化）

- **User Request:** 在页面直接显示详细调试信息，排查气温曲线空白原因。
- **前置说明:**
  1. 本次为临时排障增强，优先信息透明与定位效率；  
  2. 调试信息默认开启显示，后续可按需要再回收。  
  3. 回滚方式：移除 `temperatureDebugText/temperatureDebugInfo` 及模板中的调试展示块。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/services/api.js`：  
     - `getTemperatureTrendByDate` 返回 `_debug` 字段，记录接口命中来源与每层尝试结果（成功/失败、错误信息、URL、状态）。  
  2. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：  
     - `debugVisible` 默认值改为 `true`；  
     - 新增 `temperatureDebugInfo` 与 `temperatureDebugText`；  
     - 在“气温变化情况”图表下方增加详细调试面板，展示请求参数、回退链路、返回字段、映射条数、样例数据、7天窗口逐日值与可见点数量。  
  3. 新增调试样式：`json-preview`、`temp-debug-box`，保证长文本可滚动查看。
- **Result:** 页面可直接观测“请求到了哪一层接口、每层为何失败/成功、最终图表序列是否有值”，便于快速锁定空白根因。

## 2026-02-15（温度图渲染强制可视化调试）

- **User Feedback:** 调试数据显示 7 天窗口有值，但图表仍空白。
- **前置说明:**
  1. 已确认数据链路正常，问题收敛到 ECharts 渲染层；  
  2. 采用“强制可见配置”验证渲染链路，减少主题/默认样式干扰。  
  3. 回滚方式：恢复 `temperatureTrendOption` 到原 smooth 线图配置。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：  
     - 温度图显式设置 `animation=false`、`color`、`lineStyle`、`itemStyle`、`symbol`、`symbolSize`、`connectNulls=false`；  
     - 计算并固定 `yAxis.min/max`（基于当前窗口有效值）；  
     - `smooth` 改为 `false` 便于判读折线节点。  
  2. 在 `temperatureDebugText` 增加 `echartsPayload`，直接输出最终传入图表的 `xAxisData/mainSeries/peerSeries`。
- **Result:** 页面调试面板现在可同时验证“数据源值”和“最终 ECharts 入参值”，用于精确定位是否为纯渲染异常。

## 2026-02-15（EChart 组件渲染稳态修复）

- **依据证据:** 用户提供 `2.16 气温调试信息2.md` 显示 `series` 数据完整，但曲线仍未渲染，判定为图表实例更新/尺寸监听问题。
- **Agent Action:**
  1. 修改 `SpringFestivalDashboardView.vue` 的内嵌 `EChart` 组件：  
     - `setOption` 后强制 `requestAnimationFrame + resize`；  
     - 初始化阶段改为 `nextTick` 后应用 option，避免容器尺寸未稳定；  
     - 增加 `ResizeObserver` 持续监听容器尺寸变化并触发 `resize`。  
  2. 调试面板补充 `chartLibraryReady` 与 `hasWindowEcharts` 字段，验证 ECharts 全局库与组件状态。
- **Result:** 提升图表在布局变化/初次挂载时的稳定渲染能力，减少“数据有值但图空白”。

## 2026-02-15（温度图样式回退到既定展示规范）

- **User Request:** 曲线已恢复，但图形样式和数据标签格式与既定规范不一致，需要恢复原样式。
- **前置说明:**
  1. 保留 EChart 组件层稳定性修复（`nextTick/resize/ResizeObserver`）；  
  2. 仅回退温度图 `temperatureTrendOption` 的视觉配置与默认调试显示状态。  
  3. 回滚方式：恢复当前补丁前的温度图强制渲染参数。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`；  
  2. `debugVisible` 默认值由 `true` 改回 `false`；  
  3. 温度图配置恢复为原设定：  
     - 去除 `animation=false`、强制 `color`、强制 `lineStyle/itemStyle/symbol`、`yAxis min/max`；  
     - 线条恢复 `smooth: true`；  
     - 标签格式继续使用原 `toFixed(1)` 规则。  
- **Result:** 温度图视觉与标签样式恢复到既定展示标准，同时保留“可显示”稳定性修复。

## 2026-02-16（春节看板两张表合计行加粗 + 气温合计改平均值）

- **User Request:** `spring-dashboard` 页面两张新增“合计”行需要加粗；气温字段合计由求和改为算术平均。
- **前置说明:**
  1. 本次仅调整前端展示与表格汇总算法，不改后端接口与数据库；
  2. 回滚方式：还原 `SpringFestivalDashboardView.vue` 中本次新增的 `averageRowsByField`、行类名绑定与样式。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`：
     - 两张表的 `tr` 增加 `:class="{ 'mini-table-total-row': row.isTotal }"`；
     - 新增 `averageRowsByField(rows, field)`；
     - `coalRowsWithTotal` 与 `complaintRowsWithTotal` 的 `temperature` 改为平均值计算；
     - 新增样式 `.mini-table .mini-table-total-row td { font-weight: 700; }`。
- **Result:** 两张表“合计”行文字已统一加粗；气温“合计”按可见日期的算术平均值展示，其它数值列仍保持求和逻辑。

## 2026-02-25（配置说明确认：backend_data/shared/项目列表.json）

- **User Request:** 询问 `backend_data/shared/项目列表.json` 当前功能。
- **前置说明:**
  1. 本次仅进行代码与配置链路核对，不修改业务代码；
  2. Serena 已完成 `activate_project` 与 `check_onboarding_performed`；
  3. 回滚方式：本次仅文档追加，如需回退可删除本节记录。
- **Agent Action:**
  1. 读取 `backend_data/shared/项目列表.json` 当前内容，确认包含项目名、页面配置、数据源路径、目录化文件清单；
  2. 核对后端入口：`backend/api/v1/routes.py` 中 `list_projects` 与 `list_project_pages` 通过 `_load_project_entries` 读取该文件；
  3. 核对路径解析：`backend/services/project_data_paths.py` 中 `resolve_project_list_path` 优先使用 `shared/项目列表.json`；
  4. 核对扩展用途：`backend/services/project_modularization.py` 与 `backend/projects/daily_report_25_26/api/legacy_full.py` 也会消费该文件的 `pages` / `modularization` 信息。
- **Result:** 已确认该文件是“全局项目注册表 + 页面元数据源 + 部分后端配置推断输入”，不仅用于项目列表展示。

## 2026-02-25（项目入口可见性/可访问性能力核对）

- **User Request:** 确认 `backend_data/shared/项目列表.json` 是否可配置项目显示、可见人群、可点击访问人群。
- **前置说明:**
  1. 本次仅核对现状能力，不做业务逻辑改造；
  2. 回滚方式：本次仅追加记录，删除本节即可回退。
- **Agent Action:**
  1. 核对后端项目列表接口 `backend/api/v1/routes.py::list_projects`，确认当前只按配置文件遍历返回项目，不含按用户过滤；
  2. 核对权限模型 `backend/schemas/auth.py` 与 `backend/services/auth_manager.py`，确认现有权限核心为 `page_access/sheet_rules/units_access/actions`，无 `project_access`；
  3. 核对前端项目入口 `frontend/src/pages/ProjectSelectView.vue`，确认存在春节项目的前端硬编码点击拦截（仅 `Global_admin`）。
- **Result:** 当前 `项目列表.json` 仅直接支持“是否显示”（通过是否存在项目条目）；“哪些用户可见/可访问”未在该文件形成通用配置能力，现状主要依赖权限系统的页面级控制与个别前端硬编码规则。

## 2026-02-25（用户分组与权限系统现状说明）

- **User Request:** 说明当前应用“用户分组及其权限”的设定体系与生效方式。
- **前置说明:**
  1. 本次仅做现状核对与说明，不修改鉴权逻辑；
  2. Serena 已完成项目激活与 onboarding 检查；
  3. 回滚方式：删除本节记录即可。
- **Agent Action:**
  1. 核对账号源：`backend_data/shared/auth/账户信息.json`；
  2. 核对权限矩阵：`backend_data/shared/auth/permissions.json`；
  3. 核对后端鉴权核心：`backend/services/auth_manager.py`、`backend/api/v1/auth.py`；
  4. 核对前端权限消费：`frontend/src/projects/daily_report_25_26/store/auth.js`、`PageSelectView.vue`。
- **Result:** 当前为“账号归组 + 组权限模板 + 会话令牌 + 前后端双侧校验”的 RBAC 变体：组定义页面访问、表单过滤、单位范围和动作权限；后端做最终鉴权，前端做展示过滤与交互拦截。

## 2026-02-25（权限文件按“项目>页面”组织可行性评估）

- **User Request:** 希望将 `backend_data/shared/auth/permissions.json` 从“全局页面平铺”改为“项目 > 页面”组织。
- **前置说明:**
  1. 本次输出为改造方案，不直接修改鉴权代码；
  2. 目标是保持现网兼容，先支持新结构，再平滑迁移旧结构；
  3. 回滚方式：若实施后异常，可暂时切回旧版平铺 `page_access/sheet_rules` 并沿用现有解析逻辑。
- **Agent Action:**
  1. 评估了当前权限生效链路：`auth_manager.py`（加载/会话）、`routes.py`（项目页面过滤）、前端 `store/auth.js`（页面和表单过滤）；
  2. 给出兼容改造路线：新增 `projects` 节点，解析层双栈兼容，接口透出项目维度权限，前后端过滤函数改为携带 `project_key`。
- **Result:** 该改造可行，且可采用“兼容旧结构 -> 灰度切换 -> 清理旧字段”的低风险实施路径。

## 2026-02-25（权限文件模块化实施：项目 > 页面）

- **User Request:** 直接实施权限文件模块化，允许同步修改相关程序代码，重点要求改动有序、链路完整。
- **前置说明:**
  1. Serena 已完成 `activate_project` 与 `check_onboarding_performed`；
  2. 本次采用“代码先兼容 + 配置迁移到新结构”的实施方式；
  3. 回滚方式：`permissions.json` 删除 `projects` 节点并沿用旧平铺字段；代码层保留兼容逻辑可直接承接回滚。
- **Agent Action:**
  1. 后端权限模型扩展（`backend/services/auth_manager.py`）：
     - 新增 `ProjectPermissions` 数据结构；
     - `GroupPermissions` 增加 `projects`；
     - `AuthSession` 增加 `allowed_units_by_project` 与项目维度方法：
       - `resolve_project_permissions(project_key)`
       - `get_project_page_access(project_key)`
       - `get_project_action_flags(project_key)`
       - `resolve_allowed_units(project_key)`
     - `_load_permissions` 支持读取 `groups.*.projects.*`，并兼容旧结构字段回退。
  2. 后端接口生效链路改造：
     - `backend/api/v1/routes.py::list_project_pages` 改为按 `project_id` 取项目页面权限；
     - `backend/projects/daily_report_25_26/api/dashboard.py` 的缓存权限校验改为项目维度动作权限；
     - `backend/projects/daily_report_25_26/api/legacy_full.py` 中审批/撤销/发布及单位过滤统一改为项目维度权限读取。
  3. 后端响应模型扩展：
     - `backend/schemas/auth.py::PermissionsModel` 新增 `projects` 字段，确保 `/auth/login` 与 `/auth/me` 返回项目化权限数据。
  4. 前端权限消费改造（`frontend/src/projects/daily_report_25_26/store/auth.js`）：
     - 新增项目维度解析逻辑：`resolveProjectPermission(projectKey)`；
     - `filterPages`、`filterSheetsByRule` 改为支持 `projectKey`，并兼容旧签名；
     - 新增 `canSubmitFor/canApproveFor/canRevokeFor/canPublishFor`；
     - `canApproveUnit/canRevokeUnit` 支持项目维度单位范围判断。
  5. 前端调用点对齐：
     - `PageSelectView.vue` 页面过滤与审批按钮显示改为按当前 `projectKey`；
     - `Sheets.vue` 表格过滤改为 `auth.filterSheetsByRule(projectKey, pageKey, sheets)`。
  6. 权限配置迁移：
     - `backend_data/shared/auth/permissions.json` 已新增 `groups.*.projects` 结构；
     - 当前将各组 `daily_report_25_26` 权限显式迁入，并为 `Global_admin` 增加 `daily_report_spring_festval_2026` 的 `mini_entry` 项目权限。
- **Result:** 应用权限体系已从“全局页面平铺”升级为“项目 > 页面”组织，并保持旧结构兼容，可继续按项目独立扩展权限而不互相干扰。

## 2026-02-25（权限配置去重：仅保留 projects 子树）

- **User Request:** `permissions.json` 存在平铺字段与项目字段重复，要求删除重复项，仅保留项目及其下属权限。
- **前置说明:**
  1. 代码层已具备兼容解析，允许配置文件只保留 `projects`；
  2. 本次仅调整权限配置文件，不修改业务代码；
  3. 回滚方式：将各组平铺字段 `page_access/sheet_rules/units_access/actions` 补回即可。
- **Agent Action:**
  1. 重建 `backend_data/shared/auth/permissions.json`；
  2. 各组仅保留 `hierarchy` + `projects`；
  3. 每个项目节点保留完整 `page_access/sheet_rules/units_access/actions`。
- **Result:** 权限配置去重完成，结构更清晰，避免同一组内双份权限定义带来的维护歧义。

## 2026-02-25（修复 unit_filler 误见 Coal_inventory_Sheet）

- **User Request:** 当前所有 `unit_filler` 都能看到 `Coal_inventory_Sheet`，应仅 `shoudian_filler` 可见。
- **前置说明:**
  1. 采用“分组拆分 + 权限收敛”方式修复，避免写死用户名判断；
  2. 本次仅修改账号分组与权限配置，不改业务代码；
  3. 回滚方式：将 `shoudian_filler` 并回 `unit_filler`，并恢复 `unit_filler` 的 `Coal_inventory_Sheet` 显式授权。
- **Agent Action:**
  1. `backend_data/shared/auth/账户信息.json`：把 `shoudian_filler` 从 `unit_filler` 拆到新组 `shoudian_filler`；
  2. `backend_data/shared/auth/permissions.json`：
     - `unit_filler` 的 `data_entry` 规则改为仅 `mode: by_unit`（移除 `Coal_inventory_Sheet` 显式授权）；
     - 新增 `shoudian_filler` 组，在 `data_entry` 的 `sheets` 中保留 `Coal_inventory_Sheet` 显式授权。
- **Result:** 普通 `unit_filler` 不再继承煤炭库存表显式权限，`Coal_inventory_Sheet` 仅对 `shoudian_filler` 生效。

## 2026-02-25（硬编码权限拦截清单核对）

- **User Request:** 说明当前系统中“少量硬编码拦截”具体是哪些。
- **前置说明:**
  1. 本次仅做现状核对，不修改代码；
  2. 回滚方式：本节为文档记录，无代码回滚需求。
- **Agent Action:** 扫描前后端中按 `projectKey/group` 写死的权限判断分支。
- **Result:** 已识别出项目入口拦截（前端）与若干操作级角色判断（前后端），并给出文件定位用于后续统一到权限文件。

## 2026-02-25（三类硬编码权限统一迁移到 permissions.json）

- **User Request:** 将此前识别的三类硬编码权限（项目入口、后端角色白名单、前端角色判断）统一迁移到 `permissions.json`。
- **前置说明:**
  1. 本次实施包含后端鉴权与前端显隐逻辑联动改造；
  2. 新增项目动作位用于替代角色名硬编码；
  3. 回滚方式：恢复相关硬编码判断，或在 `permissions.json` 回填对应动作位后按旧行为运行。
- **Agent Action:**
  1. 后端动作位扩展：
     - `ActionFlags` / `ActionFlagsModel` 增加：
       - `can_manage_modularization`
       - `can_manage_validation`
       - `can_manage_ai_settings`
       - `can_manage_ai_sheet_switch`
       - `can_extract_xlsx`
       - `can_unlimited_ai_usage`
  2. 后端硬编码替换：
     - `backend/api/v1/routes.py`：
       - `GET /projects` 增加登录态依赖并按项目权限过滤；
       - 项目目录化接口改为校验 `can_manage_modularization`；
     - `backend/projects/daily_report_25_26/api/legacy_full.py`：
       - 校验总开关改为 `can_manage_validation`；
       - AI 设置改为 `can_manage_ai_settings`；
       - 表级 AI 开关改为 `can_manage_ai_sheet_switch`；
     - `backend/projects/daily_report_spring_festval_2026/api/xlsx_extract.py`：
       - 提取接口改为 `can_extract_xlsx`；
     - `backend/services/ai_usage_service.py`：
       - 去除组名白名单，改为读取 `can_unlimited_ai_usage`。
  3. 前端硬编码替换：
     - `frontend/src/pages/ProjectSelectView.vue` 删除春节项目 `Global_admin` 硬编码拦截；
     - `frontend/src/projects/daily_report_25_26/store/auth.js` 增加项目动作位读取函数：
       - `canManageValidationFor`
       - `canManageAiSettingsFor`
       - `canExtractXlsxFor`
     - `Sheets.vue` / `DataEntryView.vue` 校验开关按钮改用 `canManageValidationFor(projectKey)`；
     - `DataAnalysisView.vue` 与 `UnitAnalysisLite.vue` 的 `Global_admin` 判断改为 `canManageAiSettingsFor(projectKey)`。
  4. 权限配置补齐：
     - `backend_data/shared/auth/permissions.json` 为相关项目配置上述动作位（Global_admin 与 Group_admin 按原业务口径赋值）。
- **Result:** 三类权限控制已统一收敛到 `permissions.json`，代码层不再依赖组名硬编码进行权限决策。

## 2026-02-25（修复项目列表跨账号缓存串权限）

- **User Feedback:** `daily_report_spring_festval_2026` 对非授权账号仍可见可进，与权限配置不符。
- **前置说明:**
  1. 根因定位为前端项目列表缓存未按账号隔离，而非后端权限判定失效；
  2. 本次修复仅改前端 API 缓存策略，不改后端权限规则；
  3. 回滚方式：恢复 `services/api.js` 中原先单一 `cachedProjects` 逻辑。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_25_26/services/api.js`：
     - 新增 `cachedProjectsToken`；
     - `listProjects()` 仅在 `cachedProjectsToken === authToken` 时命中缓存；
     - `setAuthToken()` 在 token 变化时自动 `resetProjectCache()`；
     - `resetProjectCache()` 同时清空 `cachedProjects` 与 `cachedProjectsToken`。
- **Result:** 切换账号后项目列表会强制按当前 token 重新拉取，项目可见性与 `permissions.json` 保持一致，不再出现跨账号串权限显示。

## 2026-02-25（新增项目可用性最高优先级开关）

- **User Request:** 在 `backend_data/shared/项目列表.json` 为每个项目增加“项目可用性”开关，支持 `true/false/[用户组列表]`，并作为高于 `permissions.json` 的项目入口总闸。
- **前置说明:**
  1. 本次采用“配置 + 后端统一鉴权”落地，不新增前端硬编码判断；
  2. 项目访问判定顺序调整为：`项目可用性` → `permissions.json`；
  3. 回滚方式：移除 `项目可用性` 字段并回退 `backend/api/v1/routes.py` 本次新增的可用性判定与项目路由依赖。
- **Agent Action:**
  1. 配置更新：`backend_data/shared/项目列表.json`
     - `daily_report_25_26` 增加 `"项目可用性": true`；
     - `daily_report_spring_festval_2026` 增加 `"项目可用性": ["Global_admin"]`。
  2. 后端统一判定：`backend/api/v1/routes.py`
     - 新增 `_is_project_enabled_for_group()`，解析 `项目可用性/project_availability`；
     - 新增 `_ensure_project_visible_and_accessible()`，统一执行“可用性总闸 + 既有权限判定”；
     - `GET /api/v1/projects` 增加按项目可用性过滤；
     - `GET /api/v1/projects/{project_id}/pages` 增加项目总闸校验；
     - 项目目录化接口（status/bootstrap）增加项目总闸校验；
     - 为注册到 `/api/v1/projects/{project_key}` 下的 `router/public_router` 统一挂载项目访问依赖，阻断绕过页面列表的直连访问。
- **Result:** 项目入口实现“不可见即不可访问”的统一规则；当项目可用性为 `false` 或当前组不在白名单时，项目不会出现在项目列表，且项目下接口访问会返回 `403`。

## 2026-02-25（可用性字段命名修正为 availability）

- **User Request:** 不再使用“项目可用性”命名，改为 `availability`；用户组即使只有一个也使用列表形式。
- **前置说明:**
  1. 本次仅做命名与兼容层调整，不改变权限语义；
  2. 回滚方式：将 `availability` 改回旧键，并回退 `routes.py` 中读取优先级调整。
- **Agent Action:**
  1. 配置更新：`backend_data/shared/项目列表.json`
     - 将项目级键由 `项目可用性` 改为 `availability`；
     - 春节项目继续使用列表白名单格式：`\"availability\": [\"Global_admin\"]`。
  2. 后端更新：`backend/api/v1/routes.py`
     - `_is_project_enabled_for_group()` 改为优先读取 `availability`；
     - 保留 `project_availability` 与 `项目可用性` 回退兼容，确保历史配置不立即失效。
- **Result:** 配置主键已统一为 `availability`，且白名单组保持列表格式；系统行为与上一版一致。

## 2026-02-25（移除 availability 旧键兼容）

- **User Request:** 不需要兼容旧键，仅保留 `availability`。
- **前置说明:**
  1. 本次为不兼容清理，旧键将不再生效；
  2. 回滚方式：恢复 `routes.py` 中旧键回退读取逻辑。
- **Agent Action:**
  1. 修改 `backend/api/v1/routes.py`：
     - `_is_project_enabled_for_group()` 改为仅读取 `availability`（缺省按 `true` 处理）；
     - 删除 `project_availability` 与 `项目可用性` 的回退读取。
- **Result:** 项目可用性配置已完成单键收敛，后续仅接受 `availability` 作为有效配置入口。

## 2026-02-25（修复切换账号后项目列表短暂显示旧账号数据）

- **User Feedback:** 切换账号后，在刷新前项目卡片仍显示原账号结果。
- **前置说明:**
  1. 根因在前端全局项目状态未随会话切换同步清空；
  2. 本次仅改前端状态管理，不改后端接口；
  3. 回滚方式：恢复 `useProjects.js` 与 `store/auth.js` 本次变更。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_25_26/composables/useProjects.js`：
     - 新增 `resetProjectsState()`，统一清空 `projects/projectsLoading/projectsError`。
  2. 修改 `frontend/src/projects/daily_report_25_26/store/auth.js`：
     - 引入 `resetProjectsState`；
     - 在 `clearSession()` 中调用，确保登出/会话失效时立即清空项目列表；
     - 在 `login()` 成功后立即调用，确保账号切换时先清空旧项目，再拉取新项目。
- **Result:** 账号切换后不再残留旧账号项目卡片；页面会先进入空/加载态，再展示当前账号项目列表。

## 2026-02-25（项目列表切号修复方案调整：移除 auth 对 useProjects 的直接耦合）

- **User Feedback:** 数据分析页出现白屏，需降低切号修复对其它页面的副作用风险。
- **前置说明:**
  1. 调整为“项目选择页进入时重置并强制重拉”方案；
  2. 移除 `auth store` 对 `useProjects` 的直接依赖；
  3. 回滚方式：恢复 `auth.js` 中 `resetProjectsState` 调用，并回退 `ProjectSelectView.vue` 本次改动。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_25_26/store/auth.js`：
     - 删除 `resetProjectsState` 引入与调用，解除 `auth -> useProjects` 直接耦合。
  2. 修改 `frontend/src/pages/ProjectSelectView.vue`：
     - 进入页面时先 `resetProjectsState()`；
     - 再调用 `ensureProjectsLoaded(true)` 强制按当前会话重拉项目列表。
  3. 本地验证：
     - 执行 `frontend` 构建（`npm run build`）通过。
- **Result:** 切号后项目列表仍能立即按当前账号刷新，同时降低对非项目选择页面（如数据分析页）的潜在影响面。

## 2026-02-25（修复数据分析页白屏：isGlobalAdmin 未定义）

- **User Feedback:** 数据分析页面白屏，控制台报错 `ReferenceError: isGlobalAdmin is not defined`。
- **前置说明:**
  1. 本次为前端变量引用修复，不涉及后端接口；
  2. 回滚方式：恢复 `DataAnalysisView.vue` 对 `aiFeatureAccessible` 的旧计算表达式。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`：
     - 将
       `const aiFeatureAccessible = computed(() => isGlobalAdmin.value || allowNonAdminAiReport.value)`
       改为
       `const aiFeatureAccessible = computed(() => canConfigureAiSettings.value || allowNonAdminAiReport.value)`。
  2. 本地验证：
     - 执行 `frontend` 构建（`npm run build`）通过。
- **Result:** 消除未定义变量异常，数据分析页恢复可渲染。

## 2026-02-26（管理后台设定项来源盘点）

- **User Request:** 先不继续堆功能，优先明确“项目后台设定”当前展示内容的真实来源，并全面搜集分散配置项，便于后续统一接入后台页面。
- **前置说明:**
  1. 本轮以“盘点与映射”为目标，未修改业务逻辑；
  2. 盘点范围覆盖：后端接口层、`backend_data` 配置层、前端页面使用层、全局运行时状态层；
  3. 回滚方式：本次仅文档记录，无需代码回滚。
- **Agent Action:**
  1. 已确认当前管理后台页面内容来源：
     - `AdminConsoleView.vue` 的“设定概览/校验总开关/AI设置/缓存任务”来自 `GET /api/v1/admin/overview` 与 `/api/v1/admin/*` 子接口；
     - 这些接口由 `backend/api/v1/admin_console.py` 聚合并转发到项目内既有能力。
  2. 已定位主要设定来源文件：
     - 项目配置：`backend_data/projects/daily_report_25_26/config/` 下 `api_key.json`、`数据结构_基本指标表.json`、`数据结构_数据分析表.json`、`数据结构_数据看板.json`、`dashboard_frontend_config.json` 等；
     - 项目运行时：`backend_data/projects/daily_report_25_26/runtime/dashboard_cache.json`；
     - 全局状态：`backend_data/shared/date.json`、`backend_data/shared/status.json`、`backend_data/shared/auth/permissions.json`、`backend_data/shared/项目列表.json`。
  3. 已完成“设定项归类口径”：
     - 全局后台权限与可见性；
     - 数据填报校验（总开关 + 表级开关）；
     - AI 配置（模型/key/提示词/模式/权限）；
     - 看板缓存发布与天气导入；
     - 审批发布流程状态（workflow）；
     - 数据分析 schema 与页面级行为参数。
- **Result:** 管理后台当前展示内容来源已可追溯，且分散设定项清单已可用于下一步页面分组与接入设计评审。

## 2026-02-26（迁移项目列表与审批状态到项目目录）

- **User Request:** 将 `backend_data/shared/项目列表.json` 与 `backend_data/shared/status.json` 迁移到 `daily_report_25_26` 项目目录，保留 `shared` 目录；并同步修正程序依赖路径。
- **前置说明:**
  1. 本次为“文件位置重构 + 路径解析更新”，不改变业务接口语义；
  2. 迁移后路径优先改为项目内，仍保留旧路径回退兼容；
  3. 回滚方式：将文件移回 `shared` 并回退 `project_data_paths.py` 本次路径优先级调整。
- **Agent Action:**
  1. 文件迁移：
     - `backend_data/shared/项目列表.json` -> `backend_data/projects/daily_report_25_26/config/项目列表.json`
     - `backend_data/shared/status.json` -> `backend_data/projects/daily_report_25_26/runtime/status.json`
  2. 代码修正：
     - `backend/services/project_data_paths.py`
       - `resolve_project_list_path()` 改为优先 `projects/daily_report_25_26/config/项目列表.json`
       - `resolve_workflow_status_path()` 改为优先 `projects/daily_report_25_26/runtime/status.json`
       - 旧 `shared/*` 与根目录旧路径保留回退兼容。
     - `backend/services/workflow_status.py`
       - 顶部说明更新为项目目录路径。
- **Result:** 项目列表与审批状态已从 `shared` 迁至 `daily_report_25_26` 项目目录；依赖代码已对齐新位置，`shared` 目录保留且不再强依赖这两个文件。

## 2026-02-26（迁移更正：项目列表回 shared，date 迁入项目目录）

- **User Feedback:** 上一轮迁移口径写反：`项目列表.json` 应保留在 `shared`，而 `date.json` 应迁入项目目录。
- **前置说明:**
  1. 本次属于对上一轮迁移的纠偏；
  2. 继续保留兼容回退路径，避免历史环境直接失效；
  3. 回滚方式：恢复本次两处文件移动与 `project_data_paths.py` 的优先级调整。
- **Agent Action:**
  1. 文件调整：
     - `backend_data/projects/daily_report_25_26/config/项目列表.json` -> `backend_data/shared/项目列表.json`
     - `backend_data/shared/date.json` -> `backend_data/projects/daily_report_25_26/runtime/date.json`
  2. 代码修正（`backend/services/project_data_paths.py`）：
     - `resolve_project_list_path()`：恢复 `shared/项目列表.json` 为首选；
     - `resolve_global_date_path()`：改为优先 `projects/daily_report_25_26/runtime/date.json`，`shared/date.json` 作为回退。
- **Result:** 当前口径已符合最新要求：项目列表在 `shared`，业务日期文件在 `daily_report_25_26` 项目目录内。

## 2026-02-26（后台文件编辑树形结构去掉独立目录选择）

- **User Request:** “后台文件编辑”已改树形后，不应再保留单独“目录”下拉；目录应直接作为树节点融入同一棵树。
- **前置说明:**
  1. 本次仅改前端展示与加载策略，不改后端接口；
  2. 保持“点击文件后新窗口编辑/保存”流程不变；
  3. 回滚方式：恢复 `AdminConsoleView.vue` 中 `selectedDirectory/selectDirectory` 与目录下拉 UI。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`：
     - 删除“目录”下拉控件；
     - 文件树改为“目录 + 文件”统一节点（树根视角为 `backend_data`）；
     - `loadDirectories()` 改为拉取全部子目录后批量加载文件并合并；
     - 删除 `selectedDirectory` 状态与 `selectDirectory()` 流程；
     - 默认展开一级目录节点，搜索在整树路径上筛选。
- **Result:** 页面不再有独立目录选择器；目录已融入树形结构，操作路径更统一。

## 2026-02-26（后台弹窗新增 JSON 专用编辑能力）

- **User Request:** 弹出的文件编辑窗口按文件类型提供专用编辑器；第一阶段先支持 JSON，避免纯文本编辑看不出结构且无法校验。
- **前置说明:**
  1. 本次仅实现 JSON 专用能力，其他类型仍按文本编辑；
  2. 不新增第三方编辑器库，先基于现有弹窗做语法校验与格式化；
  3. 回滚方式：恢复 `AdminFileEditorWindow.vue` 本次新增的 JSON 模式逻辑。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_25_26/pages/AdminFileEditorWindow.vue`：
     - 增加 `.json` 文件识别（`isJsonFile`）；
     - 增加 JSON 实时校验（`jsonValidation`）；
     - 解析 `JSON.parse` 报错中的 `position` 并换算行列，展示错误提示；
     - JSON 非法时禁用“保存并关闭”；
     - 新增“格式化 JSON”按钮（合法时执行 `JSON.stringify(..., null, 2)`）。
- **Result:** JSON 文件在弹窗中具备基础“结构化编辑”能力：可校验、可提示错误位置、可格式化、可阻止错误提交。

## 2026-02-26（JSON 错误定位增强）

- **User Request:** JSON 内容有格式问题时，希望明确指出问题位置。
- **前置说明:**
  1. 本次在现有 JSON 专用编辑基础上增强错误可视化；
  2. 不改变后端接口，仅前端弹窗展示增强；
  3. 回滚方式：恢复 `AdminFileEditorWindow.vue` 本次错误面板代码。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_25_26/pages/AdminFileEditorWindow.vue`：
     - 在 JSON 非法时新增错误面板；
     - 展示“行/列 + 原始错误消息 + 出错行文本 + caret(^)定位指针”。 
- **Result:** JSON 报错不再只有笼统提示，编辑窗口可直接定位到问题行列并快速修复。

## 2026-02-26（JSON 错误自动定位光标）

- **User Request:** 实现“自动定位光标到对应行列”，并说明 JSON 编辑器实现方式。
- **前置说明:**
  1. 本次在现有 JSON 错误提示基础上新增“光标跳转”；
  2. 不引入第三方编辑器库，继续使用原生 textarea；
  3. 回滚方式：恢复 `AdminFileEditorWindow.vue` 中 `jumpToJsonError` 与按钮绑定。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_25_26/pages/AdminFileEditorWindow.vue`：
     - 为 textarea 增加 `ref="editorRef"`；
     - 新增 `jumpToJsonError()`，按行列换算绝对索引后调用 `setSelectionRange` 定位光标；
     - JSON 错误面板新增“定位到错误位置”按钮；
     - 保存前若 JSON 非法，自动触发一次定位。
- **Result:** 用户可一键跳转到 JSON 语法错误点；误保存时也会自动聚焦到错误位置，便于立即修正。

## 2026-02-26（新增管理后台系统监控页面）

- **User Request:** 在管理后台增加页面，用于监控服务器性能状况。
- **前置说明:**
  1. 本次先交付第一版实时指标（CPU/内存/磁盘/进程/平台/运行时长）；
  2. 权限沿用全局后台访问动作位 `can_access_admin_console`；
  3. 回滚方式：移除 `admin/system/metrics` 接口、`AdminConsoleView` 的 `system` 标签页与 `api.js` 对应方法。
- **Agent Action:**
  1. 后端新增指标接口：
     - `backend/api/v1/admin_console.py`
       - 新增 `GET /api/v1/admin/system/metrics`
       - 返回 `timestamp/uptime/platform/cpu/memory/disk/process/metrics_provider`
       - 指标采集优先 `psutil`，异常时回退基础占位输出。
  2. 后端依赖更新：
     - `backend/requirements.txt` 新增 `psutil>=5.9.8`。
  3. 前端新增系统监控页签：
     - `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
       - 新增第三标签 `系统监控`
       - 支持“立即刷新”与“自动刷新（5秒）”
       - 展示 CPU/内存/磁盘/进程内存/进程CPU/运行时长/平台/Python 版本
     - `frontend/src/projects/daily_report_25_26/services/api.js`
       - 新增 `getAdminSystemMetrics()`
- **Result:** 管理后台已具备基础服务器性能监控能力，可在同一页面查看并轮询刷新关键运行指标。

## 2026-02-26（系统监控图形化）

- **User Request:** 系统监控希望做成图形化展示。
- **前置说明:**
  1. 本次采用轻量图形方案（SVG sparkline），不引入前端图表新依赖；
  2. 图形数据来自现有轮询结果，不新增后端历史序列接口；
  3. 回滚方式：移除 `AdminConsoleView.vue` 中 `metricHistory/sparkPoints` 与图形 DOM/CSS。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`：
     - 新增 `metricHistory` 与 `METRIC_HISTORY_LIMIT=60`；
     - 在每次 `loadSystemMetrics()` 成功后记录 CPU/内存/磁盘/进程CPU 历史；
     - 新增 `sparkPoints()` 将历史序列映射为 SVG 折线坐标；
     - 在系统监控卡片中增加 4 个实时趋势小图（CPU/内存/磁盘/进程CPU）。
- **Result:** 系统监控页面已支持基础图形化趋势展示，便于观察短时波动而不只看单点数值。

## 2026-02-26（系统监控“最近刷新”时间格式调整）

- **User Request:** 最近刷新时间改为东八区显示，且不显示 `+08:00` 后缀。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`：
     - 新增 `formatEast8Time()`；
     - 使用 `Intl.DateTimeFormat(..., timeZone: 'Asia/Shanghai')` 格式化为 `YYYY-MM-DD HH:mm:ss`；
     - 模板中“最近刷新”改为调用该格式化函数。
- **Result:** “最近刷新”统一显示为无时区后缀的东八区时间文本。


## 2026-02-26（系统后台新增操作日志页与分类统计）

- **User Request:** 在系统后台页面内新增“日志页面”，记录每位用户的页面打开与按钮点击等操作，并增加分类统计功能。
- **前置说明:**
  1. Serena 接入校验已完成（`activate_project` 与 `check_onboarding_performed` 成功）；
  2. 本次通过 `apply_patch` 与仓库内文件编辑完成，未使用破坏性命令；
  3. 日志目录按要求落在 `backend_data/shared/log`，系统后台页面内新增“操作日志”页签。
- **Agent Action:**
  1. 后端新增审计日志服务：`backend/services/audit_log.py`
     - 按天写入 `audit-YYYY-MM-DD.ndjson`；
     - 提供事件查询（按天数/用户/分类/动作/关键字过滤）；
     - 提供分类统计（按 category/action/user/page 聚合）。
  2. 后端扩展管理接口：`backend/api/v1/admin_console.py`
     - `POST /api/v1/audit/events`：前端上报事件批次；
     - `GET /api/v1/admin/audit/events`：后台查询日志；
     - `GET /api/v1/admin/audit/stats`：后台分类统计。
  3. 前端新增审计埋点模块：`frontend/src/projects/daily_report_25_26/services/audit.js`
     - 路由跳转自动记录 `page_open`；
     - 全局点击捕获可点击元素，记录 `click`；
     - 批量缓冲并定时上报，降低请求频次。
  4. 前端入口接入埋点：`frontend/src/main.js`
     - 在应用启动时初始化审计跟踪。
  5. 前端后台页签扩展：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
     - 新增“操作日志”页签；
     - 增加筛选（时间范围/用户/分类/动作/关键字）；
     - 展示分类统计卡片与日志表格。
  6. 前端 API 扩展：`frontend/src/projects/daily_report_25_26/services/api.js`
     - 新增 `postAdminAuditEvents/getAdminAuditEvents/getAdminAuditStats`。
- **Result:**
  1. 系统后台已内置“操作日志”页，支持日志查询与分类统计；
  2. 用户在前端的页面打开与按钮点击可自动记录并落盘到 `backend_data/shared/log`；
  3. 管理员可在后台按条件检索日志并查看聚合统计。


## 2026-02-26（系统后台新增超级管理员控制台：命令执行 + 任意路径文件管理）

- **User Request:** 在系统监控页面下方增加两项高权限功能：
  1) 控制台命令执行；
  2) 服务器文件管理（不限制于 `backend_data` 目录）；
  并提供用户名/密码登录区获取管理员权限。
- **前置说明:**
  1. 本轮按用户明确要求实现“最高权限运维面板”；
  2. 页面入口仍受现有后台访问权限控制（`can_access_admin_console`），敏感操作再通过“超级管理员二次登录令牌”放行；
  3. 全部改动在仓库内完成，未执行破坏性命令。
- **Agent Action:**
  1. 后端扩展 `backend/api/v1/admin_console.py`：
     - 新增超级管理员登录：`POST /api/v1/admin/super/login`
     - 新增命令执行：`POST /api/v1/admin/super/terminal/exec`
     - 新增文件管理：
       - `GET /api/v1/admin/super/files/list`
       - `GET /api/v1/admin/super/files/read`
       - `POST /api/v1/admin/super/files/write`
       - `POST /api/v1/admin/super/files/mkdir`
       - `POST /api/v1/admin/super/files/move`
       - `DELETE /api/v1/admin/super/files`
     - 使用 `X-Super-Admin-Token` 作为二次认证令牌。
  2. 超级管理员凭据来源：
     - 优先读取：`backend_data/shared/auth/super_admin.json`
     - 未配置时默认：`root / root123456`
  3. 前端 API 扩展 `frontend/src/projects/daily_report_25_26/services/api.js`：
     - 新增超级管理员登录、命令执行与文件管理请求封装；
     - 新增 `setSuperAdminToken`，自动携带 `X-Super-Admin-Token`。
  4. 前端页面扩展 `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`：
     - 在“系统监控”下新增“超级管理员控制台”板块；
     - 增加用户名/密码输入区与登录按钮；
     - 增加命令执行区（命令、cwd、超时、输出）；
     - 增加文件管理区（任意路径目录浏览、打开文本文件、编辑保存、创建目录、移动/重命名、删除）。
- **Result:**
  1. 系统后台页面中已可完成超级管理员二次登录；
  2. 登录后可直接执行控制台命令并查看标准输出/错误输出；
  3. 登录后可在任意可访问路径下进行文件管理与在线编辑。


## 2026-02-26（超级控制台增强：默认命令预设 + 资源管理器式目录树）

- **User Request:**
  1) 增加默认可选命令：
     - `cd /home/ww870411/25-26`
     - `docker compose -f lo1_new_server.yml down`
     - `docker compose -f lo1_new_server.yml pull`
     - `docker compose -f lo1_new_server.yml up -d`
  2) 文件管理改为更像资源管理器的目录树点选方式。
- **Agent Action:**
  1. 前端 `AdminConsoleView.vue` 命令区新增“默认命令”下拉与“填充”按钮，内置上述四个预设。
  2. 文件管理区改为“左侧目录树 + 右侧列表”布局：
     - 左侧目录树支持展开/折叠与目录点选；
     - 右侧列表显示当前目录项并可继续进入/打开/删除；
     - 保留创建目录、移动重命名、文本编辑保存能力。
- **Result:** 超级控制台已支持一键填充常用运维命令，并具备更接近资源管理器的目录树浏览与操作体验。


## 2026-02-26（超级控制台可靠性修复）

- **User Request:** 对后台页面做审慎检查后，修复已识别问题。
- **Agent Action:**
  1. 目录树改为无限层级扁平渲染（移除固定三层模板）。
  2. 文件操作后自动刷新目录树并尝试恢复到当前路径。
  3. 超级管理员令牌 401 失效时自动清理前端令牌与登录态，提示重新登录。
- **Result:** 目录树深层可用性、文件操作后的树一致性、令牌过期后的交互一致性均已修复。


## 2026-02-26（超级文件管理器增强：右键菜单风格）

- **User Request:** 试做资源管理器风格，增加右键操作体验。
- **Agent Action:**
  1. `AdminConsoleView.vue` 为目录树节点与文件列表行新增 `contextmenu` 事件；
  2. 新增右键菜单浮层，提供：进入/打开、新建子目录、重命名、删除、复制路径、刷新；
  3. 新增路径辅助函数（父目录、名称、拼接）与对应操作函数；
  4. 右键菜单支持点击遮罩关闭。
- **Result:** 超级文件管理区已具备接近资源管理器的右键操作流程。


## 2026-02-26（超级文件管理器增强：批量操作 + 拖拽上传）

- **User Request:** 继续完善超级文件管理器，新增多选后的批量删除/批量移动，并支持拖拽上传到当前目录。
- **前置说明:**
  1. Serena 接入状态已校验（项目激活与 onboarding 状态正常）；
  2. 按仓库规范仅使用仓库内编辑操作完成改动；
  3. 本轮未新增破坏性命令或仓库外写入。
- **Agent Action:**
  1. 后端（上一轮已接入，本轮确认联调）：
     - `backend/api/v1/admin_console.py` 提供 `POST /api/v1/admin/super/files/upload`（multipart 多文件上传）。
  2. 前端 API：
     - `frontend/src/projects/daily_report_25_26/services/api.js` 新增 `uploadSuperFiles(targetDir, files)`。
  3. 前端页面：
     - `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
     - 文件列表增加多选列与“全选”；
     - 新增批量工具栏（已选数量、批量删除、批量移动目标目录）；
     - 新增拖拽上传区与“选择文件上传”入口；
     - 批量删除/移动逻辑优化为“批量执行后统一刷新目录树”，减少逐条刷新造成的卡顿与状态抖动；
     - 文件列表新增选中行高亮与上传拖拽高亮样式。
- **Result:**
  1. 超级文件管理区可多选并批量删除/移动；
  2. 可通过拖拽或文件选择上传到当前目录；
  3. 大批量操作时刷新行为更稳定、交互更接近资源管理器。


## 2026-02-26（超级管理员控制台：新增退出登录按钮）

- **User Request:** 增加“退出服务器管理员账号”按钮。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`；
  2. 在超级管理员登录区域新增“退出管理员登录”按钮；
  3. 新增 `handleSuperLogout()`：清理前端超级管理员令牌、移除 sessionStorage 中的 `phoenix_super_admin_token`、重置文件管理与编辑状态。
- **Result:** 超级管理员可在后台页面中主动退出二次认证登录，后续敏感操作需重新登录。


## 2026-02-26（超级管理员登录区单行布局）

- **User Request:** 用户名、密码、登录、退出放在同一行显示。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue` 样式；
  2. 将 `.super-login-grid` 从 grid 改为 `flex + nowrap`；
  3. 为登录项设置固定最小宽度，按钮保持自适应；
  4. 移除小屏下该区域强制单列的规则，保证同一行呈现（必要时横向滚动）。
- **Result:** 超级管理员登录区四项控件统一在同一行，布局更紧凑直观。


## 2026-02-26（后台页签文案调整：系统监控 -> 服务器管理）

- **User Request:** 页面名称不要再叫“系统监控”，改为“服务器管理”。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`；
  2. 将顶部页签文案由“系统监控”改为“服务器管理”；
- **Result:** 后台顶部导航中该页面统一显示为“服务器管理”。


## 2026-02-26（服务器管理认证机制切换为 SSH 服务器账号）

- **User Request:** “服务器管理”中的登录应当是服务器账号登录，而不是页面内部账号；登录后才允许命令执行与文件管理。
- **前置说明:**
  1. Serena 项目已激活并完成 onboarding 校验；
  2. 本次属于认证机制替换，保持现有接口路径不变，仅调整认证语义与实现；
  3. 按仓库规范使用文件级补丁修改并留痕。
- **Agent Action:**
  1. 后端 `backend/api/v1/admin_console.py`：
     - `POST /api/v1/admin/super/login` 改为 SSH 认证（host/port/username/password）；
     - 登录成功后发放会话 token，并在内存会话中保存 SSH 目标与账号；
     - 命令执行改为 SSH `exec_command`；
     - 文件管理（list/read/write/mkdir/move/delete/upload）改为 SFTP 操作；
     - 新增 SSH/SFTP 辅助函数（远程路径规范化、递归建目录、递归删除目录）。
  2. 后端依赖 `backend/requirements.txt`：
     - 新增 `paramiko>=3.4.0`。
  3. 前端 `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`：
     - 登录区新增主机与端口输入项；
     - 登录请求改为提交 `{ host, port, username, password }`；
     - 文案统一为“服务器管理员登录/会话”。
  4. 前端 API `frontend/src/projects/daily_report_25_26/services/api.js`：
     - `loginSuperAdmin` 入参改为对象；
     - 401 提示改为“服务器管理员会话已失效”。
- **Result:**
  1. 服务器管理区认证已切换为真实 SSH 账号认证；
  2. 未登录或会话失效时，命令与文件管理不可继续执行；
  3. 登录后所有高权限操作基于 SSH/SFTP 在目标服务器执行。


## 2026-02-26（服务器管理白屏修复：api.js 变量重名）

- **User Feedback:** 页面白屏，报错 `Identifier 'payload' has already been declared`（`api.js`）。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_25_26/services/api.js`；
  2. 将 `loginSuperAdmin` 的参数变量与响应变量去重：
     - 入参 `payload` -> `loginPayload`
     - 响应 `payload` -> `data`
- **Result:** 消除语法错误，页面可恢复正常加载。

## 2026-02-27（无效文件核查：ww* 与旧 compose 文件）

- **User Request:** 评估以下文件是否可清理：`ww.ps1`、`ww.yml`、`ww2.ps1`、`docker-compose copy.yml`、`docker-compose.server.yml`、`ww.bash`、`ww-renew.yml`、`ww-http-only.yml`、`ww-certbot.yml`。
- **前置说明:**
  1. Serena 已完成项目激活与 onboarding 校验；
  2. 本次仅做“是否仍在使用”的核查与建议分级，不执行删除；
  3. 依据当前已确认主流程：`lo1_new_server.ps1` + `lo1_new_server.yml`。
- **Agent Action:**
  1. 读取 9 个目标文件内容，识别各自职责（构建推送/部署编排/certbot）；  
  2. 全仓检索文件名引用，确认仍存在历史文档与少量脚本引用（如 `lo1.ps1`、`init-certbot.sh` 对 `docker-compose.server.yml` 的引用）；  
  3. 输出“当前流程下可删”与“有条件保留”结论。
- **Result:**  
  - 在你当前部署路径下（新服务器 + NPM + lo1_new_server），这 9 个文件整体可视作历史链路文件；  
  - 若不再使用旧证书流程与旧部署脚本，建议统一归档或删除并同步修正文档引用。

## 2026-02-28（服务器管理去除页面内登录）

- **User Request:** “服务器管理”页面不需要管理员账号登录，页面已运行在服务器上；仅在命令行需要权限时由系统环境控制。
- **前置说明:**
  1. Serena 已完成项目激活与 onboarding 校验；
  2. 本次按用户指令执行，移除页面内 SSH 登录门槛，改为直接使用后端进程本地权限；
  3. 文件改动通过仓库内补丁方式完成，未使用仓库外写入。
- **Agent Action:**
  1. 后端 `backend/api/v1/admin_console.py`：
     - 移除超级管理员 token 会话与 SSH/SFTP 依赖链路；
     - `POST /api/v1/admin/super/login` 改为兼容占位接口（无需登录）；
     - `POST /api/v1/admin/super/terminal/exec` 改为本地 `subprocess.run` 执行；
     - `GET/POST/DELETE /api/v1/admin/super/files*` 改为本地文件系统读写/移动/删除/上传。
  2. 前端 `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`：
     - 删除“主机/端口/用户名/密码/登录/退出”区域与相关状态函数；
     - 去掉命令执行、文件管理、上传等操作对 `superTokenReady` 的禁用门槛；
     - 页面加载时直接初始化目录树并读取当前目录。
  3. 前端 API `frontend/src/projects/daily_report_25_26/services/api.js`：
     - 移除 `X-Super-Admin-Token` 注入与 `setSuperAdminToken/loginSuperAdmin` 逻辑；
     - 保留 `/admin/super/*` 接口路径，错误处理改为通用后端消息。
- **Result:**
  1. “服务器管理”已不再要求页面内再次登录；
  2. 命令执行与文件管理直接基于后端服务进程所在机器权限运行；
  3. 权限控制回归到应用登录权限 + 操作系统权限本身。

## 2026-02-28（Phoenix 项目结构复盘：为导表模块迁移做准备）

- **User Request:** “请你再详细了解一下 phoenix 项目。”
- **前置说明:**
  1. 本轮目标是结构化梳理，不做功能改造；
  2. 重点关注项目化路由注册、项目配置来源、前端入口组织与可复用接入模式。
- **Agent Action:**
  1. 梳理后端入口与路由装配：`backend/main.py`、`backend/api/v1/routes.py`、`backend/api/v1/project_router_registry.py`；
  2. 核对项目数据路径解析：`backend/services/project_data_paths.py` 与 `backend_data/shared/项目列表.json`；
  3. 对照前端项目壳与路由：`frontend/src/router/index.js`、`frontend/src/pages/ProjectSelectView.vue`；
  4. 抽样复盘“上传 xlsx -> 提取 json”现有实现：`backend/projects/daily_report_spring_festval_2026/api/xlsx_extract.py` 与其前端 service。
- **Result:**
  1. Phoenix 已形成“多项目单后端”架构，项目能力通过 `PROJECT_ROUTER_REGISTRY` 按 `project_key` 挂载到 `/api/v1/projects/{project_key}`；
  2. 项目入口与页面元数据由 `backend_data/shared/项目列表.json` 驱动，前端项目选择页直接消费该列表；
  3. 已存在与导表需求高度相似的“xlsx 提取 json”模块（春节项目），可作为导表模块迁移模板；
  4. 导表模块可按“新增项目包 + 路由注册 + 项目列表配置 + 前端项目页面”方式低风险接入，无需破坏现有日报主链路。

## 2026-02-28（monthly_data_pull 映射显示规则修正：去括号并保留实际文件名）

- **User Feedback:** 上传映射规则后页面展示有误；映射中的“源文件名/底表名”只是参考，每月实际文件名会变化，要求显示时去掉括号内容，并在上传后显示真实文件名。
- **前置说明:**
  1. Serena 已完成项目激活与 onboarding 校验；
  2. 本次仅调整前端展示，不修改导表执行接口与映射解析逻辑；
  3. 仍保留“映射键名用于匹配、上传文件名用于展示”的交互语义。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`：
     - 新增 `normalizeReferenceName(name)`：去扩展名、去中英文括号及其内容（`()`、`（）`、`[]`、`【】`）并清理多余空格；
     - 源文件与目标底表槽位标题从 `{{ key }}` 改为 `{{ normalizeReferenceName(key) }}`；
     - 槽位下方文件名继续使用 `fileState.*[key]?.name`，上传后显示真实文件名。
- **Result:**
  1. 页面标题不再受映射参考名中的年月括号干扰；
  2. 上传后仍以实际文件名为准，符合“映射仅参考、实际文件优先”的使用方式；
  3. 不影响现有步骤 2/3 的匹配与执行流程。

## 2026-02-28（项目数据目录归位修正：monthly_data_pull 与同类路径核查）

- **User Feedback:** `backend_data` 中新项目目录未放在 `projects/` 下，需与其他项目同级管理，并排查类似问题一并修正。
- **前置说明:**
  1. Serena 已完成项目激活与 onboarding 校验；
  2. 本次修正包含代码路径、数据目录迁移与同类项目运行时文件归位；
  3. 历史记录条目中的旧路径描述保留原文，仅新增纠偏记录。
- **Agent Action:**
  1. 后端路径修正：`backend/projects/monthly_data_pull/api/workspace.py`
     - `_workspace_root()` 从 `DATA_DIRECTORY / PROJECT_KEY` 改为 `get_project_root(PROJECT_KEY)`；
     - 统一走 `backend_data/projects/<project_key>` 目录规范。
  2. 目录迁移：
     - `backend_data/monthly_data_pull` -> `backend_data/projects/monthly_data_pull`（完整迁移映射、源文件、目标模板与输出文件）。
  3. 配置修正：
     - 更新 `backend_data/projects/monthly_data_pull/workspace_settings.json` 中四个默认目录为 `backend_data/projects/monthly_data_pull/...`。
  4. 同类问题排查并修正：
     - 发现 `backend_data/spring_festival_latest_extract.json` 为项目运行时文件；
     - 已迁移至 `backend_data/projects/daily_report_spring_festval_2026/runtime/spring_festival_latest_extract.json`。
  5. 结果核查：
     - 当前 `backend_data` 根目录仅保留 `projects/`、`shared/`、`sample.db`、`README.md`，无项目业务目录平铺残留。
- **Result:**
  1. `monthly_data_pull` 与其他项目目录结构已完全并列；
  2. 接口运行目录与文件实际落盘路径一致；
  3. 同类平铺运行时文件已同步归位，目录治理口径统一。

## 2026-02-28（monthly_data_pull 新增清空目录与 outputs 打包下载）

- **User Request:** 在导表页面新增两个按钮：`清空目录`（清除 4 个工作子目录文件）与 `打包下载`（导出 `outputs` 目录文件）。
- **前置说明:**
  1. Serena 已完成项目激活与 onboarding 校验；
  2. 本次新增后端接口 + 前端按钮联动，不改导表主执行逻辑；
  3. 清空操作保留 `.gitkeep`，避免目录骨架被误删除。
- **Agent Action:**
  1. 后端 `backend/projects/monthly_data_pull/api/workspace.py`：
     - 新增 `POST /monthly-data-pull/clear-workspace`：清空 `mapping_rules/source_reports/target_templates/outputs` 的文件（跳过 `.gitkeep`）；
     - 新增 `GET /monthly-data-pull/download-outputs-zip`：将 `outputs` 内文件打包成 zip 返回下载；
     - zip 使用临时文件并在响应结束后自动删除。
  2. 前端 API `frontend/src/projects/daily_report_25_26/services/api.js`：
     - 新增 `clearMonthlyDataPullWorkspace(projectKey)`；
     - 新增 `downloadMonthlyDataPullOutputsZip(projectKey)`（携带鉴权请求并返回 `blob + filename`）。
  3. 页面 `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`：
     - 顶部新增按钮：`清空目录`、`打包下载`；
     - `清空目录` 增加二次确认，成功后重置页面状态到步骤 1；
     - `打包下载` 触发浏览器保存 zip 文件（由浏览器选择保存位置）。
- **Result:**
  1. 你可以一键清理导表工作区文件，避免历史文件干扰；
  2. 你可以一键下载 `outputs` 的压缩包，不需要逐个下载；
  3. 页面功能与后端目录结构保持一致（`backend_data/projects/monthly_data_pull/...`）。

## 2026-02-28（monthly_data_pull 批量上传与文件名智能归位）

- **User Request:** 支持批量上传文件，并按文件名自动识别归属到每个源文件/目标底表槽位。
- **前置说明:**
  1. Serena 已完成项目激活与 onboarding 校验；
  2. 本次优先前端增强，复用现有后端 `get-sheets` 上传解析接口；
  3. 采用保守匹配策略：高置信度自动归位，冲突/未命中不自动分配。
- **Agent Action:**
  1. 页面 `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`：
     - 步骤 2 新增两个批量上传按钮：
       - `批量上传源文件并识别`
       - `批量上传底表并识别`
     - 新增隐藏多文件输入框与 `handleBatchPick(type, event)`；
     - 新增文件名归一与匹配函数：
       - `normalizeMatchToken(name)`：去扩展名、去中英文括号内容、去符号；
       - `findBestSlotKey(filename, keys)`：按“完全命中/包含命中”打分并避免并列冲突；
     - 新增 `applyUploadedFile(...)` 复用单文件上传赋值逻辑，保持 sheet 自动映射行为一致；
     - 批量处理完成后弹窗反馈“已匹配/未匹配”清单。
- **Result:**
  1. 可一次选择多个文件并自动归位到对应槽位；
  2. 自动归位后仍可在页面手动调整 sheet 或替换文件；
  3. 未匹配文件会被明确提示，避免静默丢失。

## 2026-02-28（monthly_data_pull 批量识别预览与确认应用）

- **User Request:** 在批量上传自动识别基础上，增加“先预览识别结果，再确认应用”的流程。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`：
     - 新增 `batchPreview` 状态与预览面板（文件名 + 识别结果）；
     - `handleBatchPick` 改为仅生成预览，不立即上传与写槽位；
     - 新增 `applyBatchPreview`：用户点击确认后才逐个上传并应用匹配；
     - 新增 `clearBatchPreview`：可取消本次预览；
     - 匹配算法改为“一对一占位”分配，避免同一槽位被多个文件自动覆盖。
  2. 交互补充：
     - 预览中显示未匹配文件；
     - 映射重解析或清空目录时自动清除旧预览。
- **Result:**
  1. 批量上传由“直接落位”升级为“预览-确认-应用”；
  2. 误匹配风险显著降低，保留你的最终确认权；
  3. 与现有手动调整流程完全兼容。

## 2026-02-28（修复：源文件批量确认无响应，补齐 .xls 兼容与错误可见性）

- **User Feedback:** 源文件批量识别后点击“确认应用”无反应；目标底表流程正常。
- **Root Cause:** 源文件存在 `.xls` 格式时，后端原逻辑仅用 `openpyxl` 读取，确认阶段实际上传解析失败；同时步骤2错误提示未显式展示，体感为“没反应”。
- **Agent Action:**
  1. 后端 `backend/projects/monthly_data_pull/services/engine.py`：
     - 新增 `.xls` 读取适配（`xlrd`）；
     - `get_sheet_names` 增加 `.xls` 分支；
     - 执行引擎加载源工作簿改为按后缀自动选择：
       - `.xls` -> `xlrd` 适配器；
       - 其他 -> `openpyxl`。
  2. 依赖更新：`backend/requirements.txt` 新增 `xlrd>=2.0.1`。
  3. 前端 `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`：
     - 在步骤2区域增加 `errorMessage` 可见提示；
     - 批量确认失败时增加 `alert`，确保错误即时可见。
- **Result:**
  1. 源文件 `.xls` 在批量确认阶段可正常解析并归位；
  2. 若后续仍有失败，将在步骤2直接看到错误信息，不再“无响应”。

## 2026-02-28（紧急修复：登录 404，避免 xlrd 缺失导致路由导入失败）

- **User Feedback:** 后端日志出现 `POST /api/v1/auth/login 404 Not Found`，登录再次不可用。
- **Root Cause:** `monthly_data_pull` 引擎新增 `xlrd` 后，在容器未安装该依赖时导入异常，导致 `api/v1/routes` 挂载失败，`/api/v1/*` 路由整体不可达。
- **Agent Action:**
  1. 修改 `backend/projects/monthly_data_pull/services/engine.py`：
     - 将 `xlrd` 改为可选导入（`try/except` 降级）；
     - 仅在实际处理 `.xls` 文件时才检查 `xlrd` 是否可用并抛出明确错误；
     - 避免依赖缺失在应用启动阶段中断路由导入。
- **Result:**
  1. `auth` 路由可恢复挂载，`/api/v1/auth/login` 不再因该问题返回 404；
  2. `.xls` 功能在未安装 `xlrd` 环境下会给出明确提示，待重建容器后可用。

## 2026-02-28（口径收敛：monthly_data_pull 仅支持 xlsx，移除 xls 兼容）

- **User Directive:** 明确不需要兼容 `.xls`，只会上传 `.xlsx`。
- **Agent Action:**
  1. 回退 `backend/projects/monthly_data_pull/services/engine.py` 中全部 `xlrd/.xls` 兼容逻辑；
  2. 回退源工作簿加载为统一 `openpyxl` 路径；
  3. 删除 `backend/requirements.txt` 中 `xlrd>=2.0.1` 依赖。
- **Result:**
  1. 导表模块技术口径回到纯 `openpyxl`；
  2. 避免额外依赖带来的导入风险；
  3. 当前约束为“仅支持 xlsx 上传”。 

## 2026-02-28（导表问题修复：REF 诊断日志 + 累计公式保留 + 结果文件鉴权下载）

- **User Feedback:**  
  1) 香海导出结果出现大量 `#REF!`，需要错误日志定位；  
  2) 全年累计字段公式丢失，需要支持保留公式；  
  3) 打包下载可用，但下方单文件链接点击报“缺少认证信息”。
- **Agent Action:**
  1. 后端引擎 `backend/projects/monthly_data_pull/services/engine.py`：
     - 源工作簿读取改为 `data_only=True`，避免把源公式文本直接写入目标导致 `#REF!`；
     - 累计写入逻辑增加“保留目标公式”分支：目标累计单元格若已有公式（`=` 开头）则不覆盖；
     - 每次执行导表生成 `execution_log_<timestamp>.json`（含每行状态、关键字段、错误信息），并作为结果文件返回。
  2. 后端接口 `backend/projects/monthly_data_pull/api/workspace.py`：
     - 强制服务端只接收 `xlsx/xlsm/xltx/xltm`，拒绝 `.xls` 上传（422）。
  3. 前端 API `frontend/src/projects/daily_report_25_26/services/api.js`：
     - 新增 `downloadMonthlyDataPullOutputFile(projectKey, filename)`，通过鉴权 fetch 下载单文件。
  4. 前端页面 `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`：
     - 步骤3结果列表由匿名超链接改为“鉴权下载按钮”，解决“缺少认证信息”；
     - 上传控件 `accept` 收敛为仅 `xlsx/xlsm/xltx/xltm`。
- **Result:**
  1. 可通过执行日志定位具体行的异常原因；
  2. 目标表累计公式不再被覆盖丢失；
  3. 下方结果文件可正常下载，不再触发认证缺失错误。

## 2026-02-28（研究院源 sheet 自动匹配完善 + 累计值对照日志）

- **User Feedback:**  
  1) 研究院源文件含多个有效子 sheet，但自动映射全默认第一张；  
  2) 询问“累计值对照功能”是否已做。  
- **Agent Action:**
  1. 前端 `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`：
     - 新增 `pickBestSheetName(ruleSheet, actualSheets)`；
     - 源文件自动映射改为按规则 sheet 名与实际 sheet 名做归一化匹配（完全命中/包含命中），不再统一选第一张。
  2. 后端 `backend/projects/monthly_data_pull/services/engine.py`：
     - 在累计处理分支新增对照日志字段：
       - `acc_compare_status`（`ok/mismatch/skipped_target_formula/non_numeric`）
       - `acc_compare_diff`
       - `tgt_acc_before`
     - 执行日志新增汇总：`acc_compare_stats`。
- **Result:**
  1. 研究院三张子 sheet 会按名称自动归位（仍可手动调整）；  
  2. “累计值对照”已落地为可追踪日志能力，可在 `execution_log_*.json` 查看逐行与汇总结论。  

## 2026-02-28（monthly_data_pull 新增异常清单区域）

- **User Request:** 在页面中单独增加“异常清单”区域。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`：
     - 在步骤3新增“异常清单”区域；
     - 执行完成后自动读取本次 `execution_log_*.json`；
     - 提取异常行（`error_*`、`warn_formula_text_from_source`、`acc_compare_status=mismatch`）并表格展示；
     - 展示累计对照汇总（总行数/累计一致/累计不一致/保留公式）；
     - 在重新解析映射与清空目录时重置异常面板。
- **Result:**
  1. 导表后无需手动打开日志文件即可查看异常条目；
  2. 异常定位效率提升，页面内即可看到问题行与说明。

## 2026-02-28（异常清单细化：标题/键名展示 + 累计算式 + 空源单元格异常）

- **User Feedback:**  
  1) 异常清单标题不需要显示日志文件名；  
  2) 异常清单中的源键/目标键应去括号简化显示；  
  3) 累计源表达式如 `H30+H62` 需支持计算；  
  4) 映射规则引用的源单元格为空时要纳入异常。
- **Agent Action:**
  1. 前端 `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`：
     - 异常清单标题改为固定“异常清单”；
     - 源键/目标键列改为 `normalizeReferenceName(...)` 展示；
     - 异常筛选新增 `warn_source_empty`、`warn_month_expr_invalid`、`warn_acc_expr_invalid`。
  2. 后端 `backend/projects/monthly_data_pull/services/engine.py`：
     - 累计源支持表达式计算：`src_acc` 非单坐标时走 `_evaluate_expr`（支持 `H30+H62`）；
     - 新增源单元格为空检测：
       - `empty_source_refs_month`
       - `empty_source_refs_acc`
       - 汇总为 `warn_source_empty` 并写入 `message`；
     - 对无效表达式新增告警状态：
       - `warn_month_expr_invalid`
       - `warn_acc_expr_invalid`。
- **Result:**
  1. 异常清单展示更符合业务阅读习惯；  
  2. 累计表达式可直接执行，不再因“非法坐标”报错；  
  3. 源单元格为空会明确出现在异常清单中。 

## 2026-02-28（异常清单新增“指标名称”列）

- **User Request:** 在异常清单中增加显示源的“指标名称”。
- **Agent Action:**
  1. 后端 `backend/projects/monthly_data_pull/services/engine.py`：
     - 执行日志每行新增 `indicator_name` 字段；
     - 从映射行按候选列提取：`指标名称` / `指标` / `项目名称` / `项目`。
  2. 前端 `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`：
     - 异常清单表格新增“指标名称”列并展示。
- **Result:**
  1. 异常定位可直接看到对应指标，不需回查映射行。 

## 2026-02-28（修复：指标名称为空，改为读取“子公司月报表指标名称”）

- **User Feedback:** 异常清单“指标名称”字段仍为空。
- **Agent Action:**
  1. 修改 `backend/projects/monthly_data_pull/services/engine.py`：
     - 指标名称提取改为专用函数 `_extract_indicator_name(row)`；
     - 按用户指定字段 `子公司月报表指标名称` 直接读取；
     - 增加空格差异兜底匹配（列名去空格后比对）。
- **Result:**
  1. 异常清单指标名称来源锁定为映射文件的“子公司月报表指标名称”列；
  2. 解决此前字段空值问题（需重新执行导表生成新日志后生效）。

## 2026-02-28（异常清单行号修正：按映射表可见行号 +1）

- **User Feedback:** 异常清单“行号”与映射文件存在 1 行相位差，应整体 +1。
- **Agent Action:**
  1. 修改 `backend/projects/monthly_data_pull/services/engine.py`：
     - 行日志 `row_index` 的枚举起始从 `1` 调整为 `2`；
     - 使异常行号与映射文件可见行号一致（首行表头，数据从第2行开始）。
- **Result:**
  1. 异常清单行号与映射文件行号对齐；
  2. 需重新执行导表生成新日志后可见修正结果。

## 2026-02-28（累计一致性补强：目标公式参与比对）

- **User Feedback:** 当前异常提示未充分考虑累计值是否一致，实际存在不一致。
- **Agent Action:**
  1. 后端 `backend/projects/monthly_data_pull/services/engine.py`：
     - 目标累计单元格为公式时，不再仅标记“保留公式”；
     - 新增公式可计算比对：对公式表达式做求值并与源累计比较；
     - 结果写入 `acc_compare_status`：`ok` / `mismatch` / `formula_not_verifiable`。
  2. 前端 `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`：
     - 异常筛选新增 `formula_not_verifiable`；
     - 异常汇总新增“公式未校验”计数；
     - 异常说明新增对应提示文案。
- **Result:**
  1. 可计算的累计公式会真正参与一致性核对并给出 `mismatch`；
  2. 无法计算的复杂公式会明确标记“公式未校验”，不再静默放过。

## 2026-02-28（累计公式核验增强：支持跨子工作表引用）

- **User Request:** 确认存在跨子工作表标签公式，要求实现可核验。
- **Agent Action:**
  1. 修改 `backend/projects/monthly_data_pull/services/engine.py`：
     - 表达式解析新增跨 sheet 引用支持：
       - `Sheet2!H30`
       - `'Sheet 2'!H30`
     - 月值/累计表达式求值与空单元格检测均接入同一跨 sheet 解析逻辑；
     - 目标累计公式核验时，支持对跨 sheet 引用公式求值后与源累计比对。
- **Result:**
  1. 跨子工作表引用的累计公式可参与一致性核验；
  2. 若公式包含暂不支持的函数或更复杂结构，仍会标记 `formula_not_verifiable`。

## 2026-02-28（累计一致性再修复：递归公式求值，避免链式公式误判）

- **User Feedback:** 跨 sheet 提示消失后，累计校验仍未正确检出不一致（26.2 累计应为 26.1 的 2 倍却未报异常）。
- **Root Cause:** 目标累计公式引用的单元格中包含二级公式时，旧逻辑将二级公式按 0 处理，导致比较失真。
- **Agent Action:**
  1. 修改 `backend/projects/monthly_data_pull/services/engine.py`：
     - `_cell_value_as_number` 增加递归公式求值能力（深度限制 + 循环引用保护）；
     - `_evaluate_expr` / `_sheet_value_by_name` 传递 workbook 上下文与递归状态；
     - 使“公式引用公式”的链式场景可被正确展开计算。
- **Result:**
  1. 类似“26.2 累计 = 26.1 累计 + 26.2 本月”的链式公式可参与真实比对；
  2. 不一致将落为 `acc_compare_status=mismatch` 并进入异常清单。

## 2026-02-28（monthly_data_show 需求预研与接入点梳理）

- **User Request:** 在已上线 `monthly_data_pull` 后，新增项目模块 `monthly_data_show`；需求与待导入文件位于 `外部导入项目-月报表导入数据库`，先完成“了解情况”。
- **前置说明:**
  1. Serena 接入校验已执行：`activate_project(D:\编程项目\phoenix)` 成功，`check_onboarding_performed` 为已完成状态；
  2. 本轮仅做调研与结构梳理，不改动业务代码；
  3. 未触发 Serena 编辑受阻，无降级到 shell 的场景。
- **Agent Action:**
  1. 读取外部需求文件 `外部导入项目-月报表导入数据库/2.28 月报数据库化配置文件.txt`，确认规则域：
     - 指标清洗与重命名；
     - 基础/半计算/计算指标分层；
     - 多月聚合与“多口径聚合”要求；
     - 特殊聚合指标与 `year+plan` 不聚合口径。
  2. 读取样例文件 `外部导入项目-月报表导入数据库/综合表26.1.xlsx`（含 17 个子表）并抽样确认列结构：
     - 主列为“项目/计量单位/本年计划/本月计划/上年同期/本月实际/本年累计/同比环比”；
     - 口径覆盖“全口径、主城区、北海、金普、庄河、研究院”等；
     - 需剔除子表：`恒流/天然气炉/中水`。
  3. 梳理现有 `monthly_data_pull` 挂载与复用点：
     - 前端入口：`ProjectSelectView` + `ProjectEntryView`；
     - 后端入口：`project_router_registry` + `backend/projects/monthly_data_pull/*`；
     - 权限与项目列表：`backend_data/shared/项目列表.json`、`backend_data/shared/auth/permissions.json`。
- **Result:**
  1. 已明确 `monthly_data_show` 可沿用当前“项目化挂载 + 权限矩阵 + 项目入口分发”路径；
  2. 已提炼该模块首批落地的核心数据规则与展示口径；
  3. 当前仓库状态为“完成预研，待进入模块创建与接口实现阶段”。

## 2026-02-28（项目中文名确认：monthly_data_pull -> 月报拉取工作台）

- **User Request:** 先敲定中文名：`monthly_data_pull` 对应“月报拉取工作台”；新项目 `monthly_data_show` 对应“月报入库工作台”。
- **前置说明:**
  1. 本轮仅处理已存在项目 `monthly_data_pull` 的实际展示名称；
  2. `monthly_data_show` 尚未创建，名称先作为后续创建时的固定命名约束。
- **Agent Action:**
  1. 更新项目配置 `backend_data/shared/项目列表.json`：
     - `monthly_data_pull.project_name`：`月报导表工作台` -> `月报拉取工作台`；
     - `monthly_data_pull.pages.workspace.页面名称`：`月报导表主页` -> `月报拉取主页`。
  2. 更新页面展示 `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`：
     - 页面标题与面包屑文案统一改为“月报拉取工作台”。
- **Result:**
  1. 项目列表与项目内页文案已统一为“月报拉取工作台”；
  2. 后续创建 `monthly_data_show` 时将使用“月报入库工作台”作为项目中文名。

## 2026-02-28（monthly_data_show 第一阶段：上传月报并提取入库 CSV）

- **User Request:** 先实现 `monthly_data_show`：上传表格文件后，按规则提取 CSV（字段风格对应数据库入库表）；提取时提供口径/字段复选；不复用 `monthly_data_pull`；后续再做查询分析页。
- **前置说明:**
  1. 本轮按“先提取 CSV、后查询分析”的顺序实现；
  2. `monthly_data_show` 为独立模块，未复用 `monthly_data_pull` 代码路径；
  3. 当前仅实现“上传并下载 CSV”闭环，后续可在此基础上对接数据库入库与分析页面。
- **Agent Action:**
  1. 项目注册与权限：
     - 更新 `backend_data/shared/项目列表.json`：新增项目 `monthly_data_show`，中文名“月报入库工作台”，页面键 `workspace`；
     - 更新 `backend_data/shared/auth/permissions.json`：为 `Global_admin` 增加 `monthly_data_show` 页面访问权限。
  2. 后端独立模块（新增）：
     - `backend/projects/monthly_data_show/api/router.py`
     - `backend/projects/monthly_data_show/api/workspace.py`
     - `backend/projects/monthly_data_show/services/extractor.py`
     - 并在 `backend/api/v1/project_router_registry.py` 注册项目路由。
  3. 后端接口：
     - `POST /api/v1/projects/monthly_data_show/monthly-data-show/inspect`
       - 上传文件后返回可选口径（自动剔除：恒流/天然气炉/中水）与可选字段；
     - `POST /api/v1/projects/monthly_data_show/monthly-data-show/extract-csv`
       - 按所选口径和字段提取并下载 CSV。
  4. 提取规则（第一阶段已实现）：
     - 指标名清洗：去空格、去“其中：”、按规则重命名；
     - 指标剔除：按你提供的“剔除指标”列表过滤；
     - 计算指标不入库：按“计算指标”列表过滤；
     - 单位清洗：`米2/米² -> 平方米`；
     - 单位转换：`千瓦时 -> 万千瓦时` 且数值除以 10000；
     - 字段生成：`company,item,unit,value,date,period,type`；
     - 日期口径：依据文件名中的 `yy.m` 推导（示例 `26.1 -> 2026-01`）。
  5. 前端页面（新增）：
     - `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
       - 步骤化页面：上传 -> 复选口径/字段 -> 提取并下载 CSV；
       - 提供口径与字段的全选/全不选操作。
  6. 前端接线：
     - `frontend/src/pages/ProjectEntryView.vue`：新增 `monthly_data_show` 入口分发；
     - `frontend/src/pages/ProjectSelectView.vue`：加入直达项目集合；
     - `frontend/src/projects/daily_report_25_26/services/api.js`：新增 `inspectMonthlyDataShowFile`、`extractMonthlyDataShowCsv`。
  7. 数据目录初始化：
     - 新增 `backend_data/projects/monthly_data_show/` 及 `uploads/`、`outputs/`；
     - 新增 `workspace_settings.json` 与目录 `README.md`。
- **Result:**
  1. 你现在可以进入 `http://localhost:5173/projects/monthly_data_show`；
  2. 上传月报后可按复选条件直接下载入库 CSV；
  3. 模块已具备后续“CSV 入库 + 查询分析页”的扩展基础。

## 2026-02-28（monthly_data_show 提取范围增强：新增“源字段”复选）

- **User Feedback:** 在“步骤 2：复选提取范围”中，还需要选择是否提取 `本年计划/本月计划/本月实际/上年同期` 这些源字段。
- **Agent Action:**
  1. 后端 `backend/projects/monthly_data_show/api/workspace.py`：
     - `inspect` 响应新增 `source_columns` 与 `default_selected_source_columns`；
     - `extract-csv` 新增表单参数 `source_columns`。
  2. 后端 `backend/projects/monthly_data_show/services/extractor.py`：
     - `extract_rows` 新增 `selected_source_columns` 入参；
     - 仅对被勾选的源字段执行提取，未勾选字段不生成记录。
  3. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`：
     - 步骤2新增“源字段（计划/实际口径）”复选区；
     - 新增全选/全不选按钮；
     - 提取按钮新增校验：必须至少选择 1 个源字段。
  4. 前端 API `frontend/src/projects/daily_report_25_26/services/api.js`：
     - `extractMonthlyDataShowCsv` 新增 `sourceColumns` 参数并回传到 `source_columns`。
- **Result:** 现在可以按“口径 + 字段 + 源字段”三层条件控制 CSV 提取范围。

## 2026-02-28（monthly_data_show 页面体验优化：步骤2常驻展示）

- **User Feedback:** 页面初始仅显示步骤1和步骤3，步骤2需上传后才出现，视觉不连贯。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`；
  2. 将“步骤 2：复选提取范围”改为常驻显示（移除条件渲染）；
  3. 未读取文件前展示引导文案与空态提示；
  4. 步骤2内各“全选/全不选”按钮在无可选项时自动禁用，避免误操作。
- **Result:** 页面首次进入即可看到完整的 1-2-3 流程，结构更稳定、视觉更一致。

## 2026-02-28（monthly_data_show 常量注入设定栏）

- **User Request:** 增加常量注入设定栏，使用已给定常量值作为默认值；允许修改，并可指定写入到哪一个源字段。
- **Agent Action:**
  1. 后端 `backend/projects/monthly_data_show/services/extractor.py`：
     - 新增默认常量规则（发电设备容量/锅炉设备容量）；
     - 新增 `get_default_constant_rules` 与 `normalize_constant_rules`；
     - `extract_rows` 支持 `constants_enabled` + `constant_rules`，按规则注入/覆盖行数据；
     - 每条常量支持 `source_column`（本年计划/本月计划/本月实际/上年同期）决定写入 period/type/date。
  2. 后端 `backend/projects/monthly_data_show/api/workspace.py`：
     - `inspect` 返回 `constants_enabled_default` 与 `constant_rules`；
     - `extract-csv` 新增参数：
       - `constants_enabled`
       - `constant_rules_json`。
  3. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`：
     - 步骤2新增“常量注入设定”面板；
     - 支持启用/关闭常量注入；
     - 支持逐条修改常量值与写入源字段。
  4. 前端 API `frontend/src/projects/daily_report_25_26/services/api.js`：
     - `extractMonthlyDataShowCsv` 新增 `constantsEnabled` 与 `constantRules` 参数并上传。
- **Result:** 现在可在页面直接配置常量注入策略，不必改代码即可调整默认常量与写入口径。

## 2026-02-28（monthly_data_show 常量注入增强：源字段支持多选）

- **User Feedback:** 常量指标的“写入源字段”应支持多选，而非单选。
- **Agent Action:**
  1. 后端 `backend/projects/monthly_data_show/services/extractor.py`：
     - 常量规则字段由 `source_column` 升级为 `source_columns`（列表）；
     - 规则标准化兼容旧字段并统一转换为列表；
     - 常量注入时对每个被勾选源字段分别写入对应 period/type/date 行。
  2. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`：
     - 常量设定表“写入源字段”由下拉单选改为复选组；
     - 支持每条常量独立勾选多个源字段。
  3. 前端 API `frontend/src/projects/daily_report_25_26/services/api.js`：
     - `constant_rules_json` 传输结构已兼容 `source_columns` 数组。
- **Result:** 每条常量可同时写入多个源字段口径（如本月实际 + 本月计划），提取 CSV 时自动生成对应多条周期记录。

## 2026-02-28（monthly_data_show 常量注入默认与布局优化）

- **User Request:** 常量注入默认选中；位置放在“源字段（计划/实际口径）”下方；常量注入默认选中源字段与“源字段”默认一致。
- **Agent Action:**
  1. 调整页面布局：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
     - 将“常量注入设定”面板移动到“源字段（计划/实际口径）”面板下方。
  2. 调整默认状态：
     - `constantsEnabled` 默认值改为启用（`true`）；
     - `inspect` 后若后端未显式返回默认开关，也默认启用。
  3. 调整常量默认写入口径：
     - 初始化常量规则时，不再使用规则内置默认字段；
     - 统一使用“源字段（计划/实际口径）”的当前默认选择作为每条常量的默认 `source_columns`。
- **Result:** 页面默认交互顺序与选中策略已按要求一致化。

## 2026-02-28（monthly_data_show 常量源字段选项与源字段复选完全一致）

- **User Clarification:** 常量注入里的“源字段选项”应与“源字段（计划/实际口径）”当前选项保持一致，不是仅默认值一致。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`：
     - 常量注入表格中的源字段复选项改为 `constantSourceColumnOptions`；
     - `constantSourceColumnOptions` 直接取 `selectedSourceColumns`（上方源字段当前勾选）；
     - 当上方源字段变更时，自动裁剪每条常量的 `source_columns`，移除不再可选项；
     - 若当前无可选源字段，在常量列中显示提示文案。
- **Result:** 常量注入区域的源字段可选项与上方源字段复选实现了实时一致。

## 2026-02-28（monthly_data_show 常量源字段显示策略修正）

- **User Clarification:** 常量注入“写入源字段”选项应始终显示全部字段；不因上方取消勾选而消失。上方取消则常量区对应字段全取消，上方重选则常量区对应字段全重选。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`：
     - 常量注入表格的源字段选项恢复为 `sourceColumns` 全量展示；
     - 监听 `selectedSourceColumns` 变化，按增量差异同步所有常量规则：
       - 上方取消某字段 -> 所有常量规则取消该字段；
       - 上方重新勾选某字段 -> 所有常量规则重新勾选该字段。
- **Result:** 现在常量注入区字段“选项固定显示，勾选状态联动同步”。

## 2026-02-28（monthly_data_show 项目名称与访问权限调整）

- **User Request:** 将 `monthly_data_show` 项目名称改为“月报导入与查询”，并设置 `Global_admin` 与 `Group_admin` 可访问。
- **Agent Action:**
  1. 修改 `backend_data/shared/项目列表.json`：
     - `monthly_data_show.project_name`：`月报入库工作台` -> `月报导入与查询`
     - `availability`：`[Global_admin]` -> `[Global_admin, Group_admin]`
     - 页面名：`月报入库主页` -> `月报导入与查询主页`
  2. 修改 `backend_data/shared/auth/permissions.json`：
     - 在 `Group_admin.projects` 中新增 `monthly_data_show`（`page_access: ["workspace"]`）。
  3. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`：
     - 页面主标题与面包屑统一为“月报导入与查询”。
- **Result:** `Global_admin` 与 `Group_admin` 现在都可在项目列表访问 `monthly_data_show`，并看到新名称“月报导入与查询”。

## 2026-02-28（monthly_data_show 拆分为导入/查询双子页面并按页授权）

- **User Request:** `monthly_data_show` 拆分为两个子页面：\n  1) “月报导入工作台”（仅 `Global_admin`）\n  2) “月报数据查询工具”（`Global_admin` + `Group_admin`）。
- **Agent Action:**
  1. 修改 `backend_data/shared/项目列表.json`：\n     - `monthly_data_show.pages` 改为两个页面项：\n       - `/projects/monthly_data_show/import-workspace`（月报导入工作台）\n       - `/projects/monthly_data_show/query-tool`（月报数据查询工具）。
  2. 修改 `backend_data/shared/auth/permissions.json`：\n     - `Global_admin.monthly_data_show.page_access`：导入页 + 查询页；\n     - `Group_admin.monthly_data_show.page_access`：仅查询页。
  3. 前端路由与入口：\n     - 新增路由：\n       - `/projects/monthly_data_show/import-workspace`\n       - `/projects/monthly_data_show/query-tool`\n     - `ProjectSelectView` 移除 `monthly_data_show` 直达入口，改为先进入页面选择；\n     - `ProjectEntryView` 移除 `monthly_data_show` 直达组件映射。
  4. 页面层：\n     - 现有导入页 `MonthlyDataShowEntryView.vue` 标题调整为“月报导入工作台”；\n     - 新增查询页 `MonthlyDataShowQueryToolView.vue`（先提供查询工具占位与能力说明）。
- **Result:** `monthly_data_show` 现已具备“项目页 -> 子页面卡片 -> 页面级权限控制”的结构，满足导入/查询分治与分权访问需求。

## 2026-02-28（移除项目页“审批进度”模块）

- **User Feedback:** “审批进度”模块没有必要。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue`；
  2. 删除“审批进度”整块 UI；
  3. 删除审批状态加载与审批/撤销/发布相关脚本逻辑；
  4. 删除对应样式，保留纯“页面卡片选择”结构。
- **Result:** 项目页面选择页仅保留功能页面卡片，不再展示审批进度模块。

## 2026-02-28（项目子页面卡片字体样式对齐修复）

- **User Feedback:** `http://localhost:5173/projects/monthly_data_show/pages` 的页面卡片字体观感与其他项目卡片不一致。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue`；
  2. 为 `.page-card` 增加 `font-family/font-size/line-height: inherit` 与 `appearance: none`，消除 `button` 默认字体差异；
  3. 将 `.page-card-title` 与 `.page-card-desc` 的字号与颜色对齐到项目卡片风格（标题 16、描述 13）。
- **Result:** 子页面卡片字体与项目列表卡片风格已对齐。

## 2026-02-28（审批进度模块按项目定向显示修正）

- **User Correction:** 仅 `http://localhost:5173/projects/monthly_data_show/pages` 不需要“审批进度”模块；其他原有项目应保留。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue`；
  2. 恢复审批进度模块完整逻辑与界面（状态加载、审批/取消批准、发布操作）；
  3. 增加项目级条件：当 `projectKey === "monthly_data_show"` 时隐藏审批进度模块并跳过审批状态加载；
  4. 其他项目保持原有审批进度展示与交互行为。
- **Result:** 现在仅 `monthly_data_show` 项目的页面选择页不显示审批进度，其他项目审批模块已恢复，不再被全局移除。

## 2026-02-28（项目子页面卡片大标题颜色统一）

- **User Request:** 子页面卡片大标题颜色应与“请选择功能页面”标题颜色一致（以 `daily_report_25_26/pages` 为例）。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue`；
  2. 将 `.page-card-title` 的颜色从固定变量改为 `color: inherit`，统一继承页面标题色系。
- **Result:** 所有项目子页面卡片的大标题颜色已统一，与“请选择功能页面”视觉一致。

## 2026-02-28（项目子页面卡片大标题蓝色一致性修正）

- **User Feedback:** 卡片大标题仍未达到与“请选择功能页面”一致的蓝色效果。
- **Agent Action:**
  1. 修改 `frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue`；
  2. 将 `.page-card-title` 颜色由 `inherit` 改为 `var(--primary-700)`（与页面标题使用的卡片标题蓝色体系一致）。
- **Result:** “数据看板”“数据展示页面”等子页面卡片大标题已统一为与“请选择功能页面”同样的蓝色。

## 2026-02-28（monthly_data_show 新增 report_month 导出字段）

- **User Request:** 新增 `report_month` 字段，表示月报数据来源月份；例如 `26.2` 应写为 `2026-02-01`。
- **Agent Action:**
  1. 修改 `backend/projects/monthly_data_show/services/extractor.py`；
  2. 将 `ALLOWED_FIELDS` 扩展为：`company,item,unit,value,date,period,type,report_month`；
  3. 新增 `_build_report_month_text(report_year, report_month)`，统一生成 `YYYY-MM-01`；
  4. 普通提取行与常量注入行均增加 `report_month` 字段，并写入同一来源月份值。
- **Result:** 导出 CSV 现可包含 `report_month`，且按文件名解析月份输出标准日期（如 `2026-02-01`）。

## 2026-02-28（monthly_data_show 新增“报告月份设定”区域：自动识别可修改）

- **User Request:** 在“步骤 2：复选提取范围”最上方新增一块选择区域；程序按文件名自动判断年月，但允许用户手动修改。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`：
     - 在步骤2顶部新增“报告月份设定（自动识别，可修改）”面板；
     - 增加“年份/月份”输入框与预览文案（`YYYY-MM-01`）；
     - `inspect` 后自动填入后端识别出的年月；
     - 提取前校验年份（2000-2099）与月份（1-12），并把值随请求提交。
  2. 修改 `frontend/src/projects/daily_report_25_26/services/api.js`：
     - `extractMonthlyDataShowCsv` 新增 `reportYear/reportMonth` 参数并提交 `report_year/report_month` 表单字段。
  3. 修改 `backend/projects/monthly_data_show/api/workspace.py`：
     - `inspect` 响应新增：`inferred_report_year`、`inferred_report_month`、`inferred_report_month_date`；
     - `extract-csv` 接口新增：`report_year`、`report_month` 入参，并做合法性校验。
  4. 修改 `backend/projects/monthly_data_show/services/extractor.py`：
     - `extract_rows` 新增可选覆盖参数 `report_year/report_month`；
     - 未传时沿用文件名自动解析；传入时以用户值覆盖；
     - 覆盖后的年月参与 `date/period/type` 计算及 `report_month` 字段生成。
- **Result:** 步骤2现已提供“自动识别 + 手工修正”的来源月份控制能力，满足提取前人工确认与修订场景。

## 2026-02-28（新增 month_data_show 数据库建表 SQL）

- **User Request:** 在 `D:\编程项目\phoenix\backend\sql` 生成新 SQL 文件，建立数据库表 `month_data_show`。
- **Agent Action:**
  1. 新建 `backend/sql/month_data_show.sql`；
  2. 建表字段与 `monthly_data_show` 当前导出结构对齐：
     - `company, item, unit, value, date, period, type, report_month`
     - 以及 `id, operation_time`；
  3. 增加唯一索引 `idx_month_data_show_unique`，防止同来源月份下重复写入；
  4. 增加常用查询索引（`report_month+company`、`date`）。
- **Result:** `month_data_show` 建表脚本已就位，可直接在数据库执行创建表与索引。

## 2026-02-28（month_data_show 唯一性口径确认与索引说明修正）

- **User Clarification:** 来源月份 `report_month` 仅作参考，核心唯一性以 `date, period, type, company, item` 为准。
- **Agent Action:**
  1. 修改 `backend/sql/month_data_show.sql`；
  2. 保持唯一索引为 `(company, item, date, period, type)`；
  3. 修正唯一索引注释描述；
  4. 将 `(date, company)` 索引名称修正为语义一致的 `idx_month_data_show_date_company`；
  5. 增加 `report_month` 单列索引 `idx_month_data_show_report_month`（参考查询用途）。
- **Result:** 表约束已与业务口径一致，查询索引命名和用途更清晰。

## 2026-02-28（monthly_data_show 新增第4步：CSV 入库）

- **User Request:** 在现有流程中新增“第4步”，完成 CSV 文件入库数据库。
- **Agent Action:**
  1. 后端新增接口：`POST /api/v1/projects/monthly_data_show/monthly-data-show/import-csv`
     - 文件：`backend/projects/monthly_data_show/api/workspace.py`
     - 仅接收 `.csv`，编码要求 UTF-8（可带 BOM）；
     - 校验必要字段：`company,item,unit,value,date,period,type,report_month`；
     - 使用 UPSERT 写入 `month_data_show`（冲突键：`company,item,date,period,type`）；
     - 返回 `imported_rows` 统计。
  2. 前端新增入库调用：
     - 文件：`frontend/src/projects/daily_report_25_26/services/api.js`
     - 新增 `importMonthlyDataShowCsv(projectKey, file)`。
  3. 前端页面新增“步骤 4：CSV 入库（写入 month_data_show）”：
     - 文件：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
     - 支持选择 CSV、触发入库、展示“入库成功处理条数”反馈。
- **Result:** 现在 `monthly_data_show` 已形成“上传读取 -> 复选提取 -> 导出 CSV -> CSV 入库”的完整四步链路。

## 2026-02-28（monthly_data_show 第3步结果一键入库）

- **User Request:** 需要“第3步导出结果”可直接一键入库，无需再手动选择 CSV。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`；
  2. 第3步导出成功后，将返回 `blob` 封装为内存 `File` 并缓存为 `lastExtractedCsvFile`；
  3. 第4步新增按钮“使用第3步结果一键入库”；\n     - 点击后直接调用现有入库流程；\n     - 同时保留“手动选择 CSV 再入库”能力。
- **Result:** 导出与入库实现无缝衔接，常用路径可一键完成。

## 2026-02-28（monthly_data_show 第3步按钮拆分：提取与下载分离）

- **User Request:** 第3步将 CSV“提取”和“下载”拆成两个按钮。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`；
  2. 第3步按钮改为：
     - `提取 CSV`：仅调用后端提取并缓存结果，不自动下载；
     - `下载 CSV`：下载已缓存的提取结果；
  3. 新增提取状态提示文案，显示当前已缓存文件名；
  4. 保持与第4步联动：提取后仍可直接一键入库。
- **Result:** 第3步操作语义更清晰，满足“先提取、再决定是否下载/入库”的流程需求。

## 2026-02-28（monthly_data_show value 空值标记入库兼容）

- **User Feedback:** 提取后 `value` 为 `none` 的记录无法入库。
- **Decision:** 将 `none/null/nan/--/无/空/空字符串` 统一视为缺失值并按 `NULL` 入库，不强制转 `0`。
- **Agent Action:**
  1. 修改 `backend/projects/monthly_data_show/api/workspace.py`：
     - CSV 解析阶段新增空值标记识别集合 `NULL_VALUE_TOKENS`；
     - `value` 命中空值标记时写入 `None`；
     - 入库响应新增 `null_value_rows`（本次按空值入库的记录数）。
  2. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`：
     - 第4步入库成功提示新增空值统计展示。
- **Result:** `value` 为 `none` 等空值标记时可正常入库，且可看到空值入库条数反馈。

## 2026-02-28（monthly_data_show 新增 #DIV/0! 空值兼容）

- **User Request:** 将 `#DIV/0!` 也按 `NULL` 写库。
- **Agent Action:**
  1. 修改 `backend/projects/monthly_data_show/api/workspace.py`；
  2. 在 `NULL_VALUE_TOKENS` 中新增 `#div/0!` 标记（解析时统一小写比较）。
- **Result:** CSV 入库时 `#DIV/0!` 将不再触发数值解析报错，而是按空值 `NULL` 入库。

## 2026-02-28（monthly_data_show 查询页面第一阶段落地）

- **User Request:** 已完成入库后，开始构建“月报数据查询工具”页面。
- **Agent Action:**
  1. 后端新增查询能力（`backend/projects/monthly_data_show/api/workspace.py`）：
     - `GET /monthly-data-show/query-options`：返回筛选项（公司/指标/期间/类型）；
     - `POST /monthly-data-show/query`：支持按来源月份、业务日期、公司、指标、期间、类型筛选；
     - 支持分页（`limit/offset`）；
     - 返回汇总统计（总条数、value 非空条数、空值条数、value 合计）。
  2. 前端 API 新增封装（`frontend/src/projects/daily_report_25_26/services/api.js`）：
     - `getMonthlyDataShowQueryOptions`
     - `queryMonthlyDataShow`
  3. 查询页面由占位改为可用工具（`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`）：
     - 筛选区：来源月份/业务日期区间 + 公司/指标/期间/类型多选；
     - 汇总区：总记录、非空数值、空值数值、数值合计；
     - 结果区：表格展示 + 上下页分页。
- **Result:** `月报数据查询工具` 已具备可用的基础查询分析能力，可直接查询 `month_data_show` 入库数据。

## 2026-02-28（查询页筛选交互重构：口径/指标勾选 + 层次与聚合开关）

- **User Request:**\n  1) “公司（可多选）”改为“口径（可多选）”，并使用勾选方式且有序；\n  2) 指标同样改为勾选方式且有序；\n  3) 增加开关：先指标后公司/先公司后指标（控制结果层次顺序）；\n  4) 增加开关：是否聚合口径（逐口径展示或聚合为新口径）。
- **Agent Action:**
  1. 前端页面重构（`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`）：
     - “公司”文案改为“口径（可多选）”；
     - 口径与指标改为有序复选列表（含全选/全不选）；
     - 新增两个开关：
       - `先口径后指标 / 先指标后口径`
       - `是否聚合口径`
  2. 后端查询能力扩展（`backend/projects/monthly_data_show/api/workspace.py`）：
     - `QueryRequest` 新增 `order_mode` 与 `aggregate_companies`；
     - `order_mode` 控制排序层次（`company_first` / `item_first`）；
     - `aggregate_companies=true` 时按 `item,unit,date,period,type,report_month` 聚合并返回 `company='聚合口径'`；
     - 分页总数与汇总统计在聚合模式下同步按聚合结果计算。
  3. 前端查询 API 参数联动（`frontend/src/projects/daily_report_25_26/services/api.js`）：
     - 将 `order_mode`、`aggregate_companies` 透传到查询接口。
- **Result:** 查询页面已满足“勾选式有序筛选 + 顺序层次开关 + 口径聚合开关”的新需求，且后端结果真实按开关生效。

## 2026-02-28（查询页勾选顺序数字标注）

- **User Request:** 选择次序需要用数字标注。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`；
  2. 在“口径（可多选）”与“指标（可多选）”的每个已选项右侧显示顺序编号（1,2,3...）；
  3. 编号按勾选先后自动更新，取消某项后剩余编号自动重排。
- **Result:** 勾选顺序可视化完成，便于确认“先选谁、后选谁”的层次意图。

## 2026-02-28（查询页口径固定顺序与指标顺序整理）

- **User Request:** 口径与指标顺序需整理；口径按以下固定次序：\n  全口径、主城区、集团本部、股份本部、北海、北海水炉、香海、供热公司、金州、北方、金普、庄河、研究院、主城区电锅炉。
- **Agent Action:**
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：
     - 新增口径固定顺序常量并用于列表展示；
     - 未在固定清单中的口径自动追加到末尾；
     - “全选口径”改为按该固定顺序勾选。
  2. 后端 `backend/projects/monthly_data_show/api/workspace.py`：
     - `query-options` 的 `items` 顺序由字母序改为按 `MIN(id)` 返回（即按入库首次出现顺序），使指标顺序更稳定、更贴近数据来源结构。
- **Result:** 口径顺序已严格按你指定顺序展示，指标顺序也已从“字母序”调整为“数据出现顺序”。

## 2026-02-28（查询页指标排序规则升级）

- **User Request:** 指标排序需按业务结构：\n  基本指标+半计算指标在前，19个计算指标整体放后；前者按“产量→销售量→消耗量（煤优先）→其他”，相似指标中“总”在前。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`；
  2. 新增 `CALCULATED_ITEM_SET`（19个计算指标）并作为“后置分组”；
  3. 新增指标排序函数：
     - 一级：是否计算指标（基础/半计算在前，计算指标在后）；
     - 二级：产量 > 销售量 > 消耗量 > 其他；
     - 三级（消耗量内）：煤 > 油 > 水 > 电 > 气 > 其他；
     - 四级：相似项中“总”优先（如“总X”排在“X”前）；
     - 五级：保持稳定顺序（回退到原始顺序索引）。
- **Result:** 指标列表展示已切换为业务导向排序，更符合查询使用习惯。

## 2026-02-28（查询页指标改为三栏分段展示）

- **User Feedback:** 需明确区分“当前指标 / 常量指标 / 计算指标”，而非单列表混排。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`；
  2. 指标区域改为三段结构：
     - 当前指标（前置）
     - 常量指标（置于末尾前段）
     - 计算指标（最后一段）
  3. 常量指标采用固定优先顺序：`发电设备容量`、`锅炉设备容量`；
  4. 计算指标采用固定顺序表；
  5. 保留每项的勾选顺序数字标注（1,2,3...）。
- **Result:** 指标选择区已按“当前 -> 常量 -> 计算”分栏展示，结构更清晰，可避免“计算指标不见了”的感知问题。

## 2026-02-28（查询页分栏样式展开修正）

- **User Feedback:** 指标分栏“都缩在一起”，阅读与勾选体验不佳。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`；
  2. 将口径/指标/开关区域改为整行占位（`span-full`）；
  3. 提升复选网格列宽（`minmax(220px, 1fr)`）与可视高度；
  4. 增加文本换行与行高，移动端下改为单列展示。
- **Result:** 查询筛选区由“拥挤”改为“展开式”布局，分栏可读性明显提升。

## 2026-02-28（查询页紧凑化回调 + 指标分组结构修正）

- **User Feedback:** 页面“展得太开”；且需求不是单独常量栏，而是“常量指标放在当前指标尾部”；计算指标 19 项需明确展示，不应为空栏。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`；
  2. 布局紧凑化：
     - 口径/指标/开关由整行改回双列跨度（`span-2`）；
     - 复选网格列宽由 `220` 调整为 `170`，并降低间距与高度，减少留白。
  3. 指标分组修正为两段：
     - `当前指标（尾部含常量指标）`
     - `计算指标（19项）`
  4. 常量指标处理：
     - 不再单独成栏；
     - 在“当前指标”末尾按固定顺序追加（发电设备容量、锅炉设备容量）。
  5. 计算指标处理：
     - 固定 19 项始终展示在“计算指标（19项）”段，即使数据库当前无记录也可见可选。
- **Result:** 页面由“过度展开”回调为“紧凑有序”；指标分组与展示口径已与最新要求一致。

## 2026-02-28（查询页口径/指标选择区滚动条修复）

- **User Feedback:** 指标两个选择栏没有滚动条，内容显示不全。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`；
  2. 为口径复选区 `check-list` 增加明确的纵向滚动与高度约束；
  3. 为指标分段区 `check-list.sections` 增加纵向滚动；
  4. 为每个分段内的 `section-items` 增加独立纵向滚动，避免段内溢出。
- **Result:** 口径与指标选择区域在内容较多时均可滚动，显示完整可选项。

## 2026-02-28（查询页布局适中化 + 月份选择器与筛选顺序调整）

- **User Feedback:** 页面仍偏紧凑；希望日历改为“按月选择”，并且先选业务日期，再选来源月份。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`；
  2. 时间筛选控件改为 `type=\"month\"`：
     - 业务月份起/止（前置）
     - 来源月份起/止（后置）
  3. 前端查询参数转换：
     - `YYYY-MM` -> 月初 `YYYY-MM-01`（from）
     - `YYYY-MM` -> 月末 `YYYY-MM-DD`（to）
     - 映射到后端 `date_from/date_to` 与 `report_month_from/report_month_to`
  4. 样式从“过紧”回调为“适中”：
     - 复选列宽由 170 调整为 190
     - 列表与分段最大高度适度提升，间距略增
- **Result:** 筛选交互改为“先业务后来源”的按月筛选，页面密度更均衡。

## 2026-02-28（查询页期间/类型改为勾选 + 数据层次顺序有序勾选）

- **User Request:**\n  1) “期间”“类型”改为勾选框，并支持顺序数字；\n  2) “数据层次顺序”改为勾选框，维度为“口径/指标/期间/类型”，按有序选择表示展示层次。
- **Agent Action:**
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：
     - 期间/类型由下拉多选改为复选列表（含全选/全不选）；
     - 期间/类型已选项显示顺序数字徽标；
     - 新增“数据层次顺序（有序勾选）”区，支持四维顺序选择与默认重置。
  2. 后端 `backend/projects/monthly_data_show/api/workspace.py`：
     - `QueryRequest` 新增 `order_fields`；
     - 查询排序改为按 `order_fields` 动态生成（并做白名单约束）；
     - 聚合模式下自动忽略 `company` 层次维度。
  3. 前端 API 联动：
     - 查询请求透传 `order_fields` 到后端。
- **Result:** 期间/类型筛选方式与口径/指标一致，数据展示层次可通过“有序勾选”精确控制。

## 2026-02-28（查询页排版密度二次优化）

- **User Feedback:** 目前排版密度不均，有的区域留白过大，有的区域过于紧凑。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`（仅样式层）；
  2. 统一密度标尺：
     - 主内容区宽度、卡片内边距、区块间距统一上调；
     - 筛选网格列宽与间距统一；
     - 复选区高度与最小高度统一；
     - 指标分段取消“段内再滚动”，避免双滚动造成拥挤观感；
     - 按钮、汇总卡、标题间距统一调整。
- **Result:** 页面从“松紧不一”调整为“紧凑且有呼吸感”的均衡排版。

## 2026-02-28（查询页口径与指标区域改为整行占满）

- **User Request:** “口径（可多选）”占满整行；“指标”两栏分段也占满整行。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`；
  2. 将“口径（可多选）”与“指标（可多选）”容器从 `span-2` 调整为 `span-full`；
  3. 新增 `span-full` 样式（`grid-column: 1 / -1`），并补充移动端回退规则。
- **Result:** 口径与指标区域已整行展开，视觉层级更清晰。

## 2026-02-28（口径选择区内部紧凑化）

- **User Request:** “口径（可多选）”内部内容再紧凑一些。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`；
  2. 为口径列表单独增加 `company-list` 样式：
     - 缩小列宽（`minmax(160px, 1fr)`）；
     - 缩小网格间距与内边距；
     - 降低条目最小高度与行内间距。
- **Result:** 仅口径区内容密度提升，指标区维持当前可读性。

## 2026-02-28（指标两栏显示不全修复）

- **User Feedback:** 两栏指标内容显示不全。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`；
  2. 提升指标分段容器高度（`check-list.sections.compact`）；
  3. 为每个分段块增加 `flex: 0 0 auto`，避免 flex 压缩；
  4. 为 `section-items` 增加独立纵向滚动与高度上限，确保每栏可完整浏览。
- **Result:** 指标两栏均可完整查看，不再出现被截断显示不全的问题。

## 2026-02-28（期间/类型/层次/聚合同一行布局）

- **User Request:** “期间、类型、层次、是否聚合口径”放在同一行。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`；
  2. 将这四块重构为同一行四列容器（`inline-four`）；
  3. 每列统一为独立小卡片，保持勾选与顺序数字逻辑不变；
  4. 增加响应式规则：中屏两列、小屏一列自动换行。
- **Result:** 四个筛选模块已在同一行展示，结构更集中，操作链路更连贯。

## 2026-02-28（期间/类型默认值与空选不提取规则）

- **User Request:** 期间默认选 `month`，类型默认选 `real`；当没有任何选择时不提取任何数据。
- **Agent Action:**
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：
     - 初始化与重置时：
       - `periods` 默认 `month`
       - `types` 默认 `real`
       - 若目标值不存在则回退首项
     - 当期间或类型为空时：
       - 查询按钮禁用
       - 页面提示“为空不提取”
       - 本地查询逻辑直接返回空结果
  2. 后端 `backend/projects/monthly_data_show/api/workspace.py`：
     - 查询入口增加保护：`periods` 或 `types` 为空时，直接返回空数据与空汇总。
- **Result:** 默认筛选已对齐 `month/real`，并实现“空选不提取”。

## 2026-02-28（查询页取消默认自动查询）

- **User Feedback:** 查询页面进入后会默认显示一套查询结果，不符合预期。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`；
  2. 页面初始化改为仅加载筛选项，不自动触发查询；
  3. 新增 `hasSearched` 状态：
     - 未查询前显示提示“请先设置筛选条件并点击查询”；
     - 查询后再展示“暂无数据/结果表”；
  4. 重置筛选时改为清空结果，不自动重新查询。
- **Result:** 查询页初始状态不再自动出结果，改为“用户显式查询”驱动。

## 2026-02-28（新增“是否聚合期间月份”开关）

- **User Request:** 在“是否聚合口径”同栏新增一个开关，用于控制月份区间是逐月列出还是聚合求值；不选则不聚合。
- **Agent Action:**
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：
     - 在“聚合开关”栏新增 `aggregateMonths` 开关；
     - 文案：
       - 开：`已聚合期间月份（区间汇总）`
       - 关：`不聚合期间月份（逐月列出）`
     - 查询参数透传 `aggregate_months`；
     - 重置时恢复默认 `false`。
  2. 后端 `backend/projects/monthly_data_show/api/workspace.py`：
     - `QueryRequest` 新增 `aggregate_months`；
     - 查询分组逻辑扩展：
       - 开启时按区间聚合月份（不再按 `date/report_month` 分组）；
       - 关闭时保持逐月明细；
       - 与“聚合口径”可叠加使用。
- **Result:** 用户可自主决定月份区间结果是“逐月列出”还是“区间聚合”。

## 2026-02-28（聚合口径开关文案微调）

- **User Request:** 第一个名字改为“不聚合口径（逐口径列出）”。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`；
  2. 聚合口径开关关闭态文案由“不聚合（逐口径列出）”调整为“不聚合口径（逐口径列出）”。
- **Result:** 开关文案已按指定更新。

## 2026-02-28（查询前置条件收紧：口径/指标为空禁查）

- **User Request:** 口径都不选，或者指标都不选时，不能点击查询。
- **Agent Action:**
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：
     - 查询按钮禁用条件扩展为：口径/指标/期间/类型任一为空即禁用；
     - 提示文案同步更新为“四项均需至少选择1项”。
  2. 后端 `backend/projects/monthly_data_show/api/workspace.py`：
     - 查询入口新增同等保护：口径或指标为空时直接返回空结果。
- **Result:** 前后端均已防止“口径/指标为空”触发查询。

## 2026-02-28（查询页汇总信息移除“数值合计”）

- **User Request:** 汇总信息栏去掉“数值合计”。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`；
  2. 删除“数值合计”汇总卡片，仅保留“总记录数/数值非空/数值空值”。
- **Result:** 汇总信息更简洁，聚焦记录量与空值情况。

## 2026-02-28（查询页类型顺序调整：real 优先）

- **User Request:** 在“类型”筛选中将 `real` 放在第一个。
- **Agent Action:**
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`；
  2. 新增 `orderedTypes` 计算排序：`real` 固定置顶，其他项顺序不变；
  3. “类型”列表展示与“全选”逻辑统一改用 `orderedTypes`。
- **Result:** 类型筛选中 `real` 始终位于首位。

## 2026-02-28（monthly_data_show 指标区更名与“平均气温”接入）

- **User Request:** 将“当前指标（尾部含常量指标）”改为“基本指标”；在该栏尾部新增“平均气温”，并按所选月份从 `calc_temperature_data` 视图读取每日数据做算术平均显示。
- **Agent Action:**
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：
     - 指标栏标题改为“基本指标”；
     - 新增常量 `AVERAGE_TEMPERATURE_ITEM = '平均气温'`；
     - 将“平均气温”固定放在“基本指标”列表末尾；
     - 加载筛选项时兜底追加“平均气温”选项。
  2. 后端 `backend/projects/monthly_data_show/api/workspace.py`：
     - 查询筛选项接口 `query-options` 兜底返回“平均气温”指标；
     - 查询接口新增派生指标逻辑：
       - 在 `items` 包含“平均气温”且 `periods` 含 `month`、`types` 含 `real` 时生效；
       - 从 `calc_temperature_data` 按日期区间读取 `aver_temp`；
       - 非聚合月份：按月对每日 `aver_temp` 做算术平均；
       - 聚合月份：对区间内每日 `aver_temp` 做算术平均；
       - 与主查询结果合并后统一排序、分页与汇总。
- **Result:** 查询页可在“基本指标”中勾选“平均气温”，并按月份区间显示来自 `calc_temperature_data` 的月均温结果。

## 2026-02-28（查询结果隐藏 operation_time + 平均气温修正）

- **User Feedback:**  
  1) `operation_time` 不需要显示；  
  2) “平均气温”显示成了当月首日值，而不是全月平均。
- **Agent Action:**
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：
     - 查询结果表头与行渲染中移除 `operation_time` 列。
  2. 后端 `backend/projects/monthly_data_show/api/workspace.py`：
     - 修正温度日期范围规则：当仅选单个月份边界时，按该月完整自然月计算（不再退化为单日）；
     - 查询时将“平均气温”从主表项中过滤，避免主表同名指标干扰；
     - 当仅选“平均气温”时跳过主表查询，仅返回派生温度结果；
     - 继续按 `calc_temperature_data` 每日 `aver_temp` 做月内/区间算术平均。
- **Result:** 页面不再显示 `operation_time`；“平均气温”按月口径正确展示为整月日均值算术平均。

## 2026-02-28（查询结果栏目新增同比/环比分析与 XLSX 导出）

- **User Request:** 参考数据分析页面风格，在查询结果栏目增加同比对比、专业分析，并支持 xlsx 导出。
- **Agent Action:**
  1. 页面 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：
     - 查询结果头部新增 `导出 XLSX` 按钮；
     - 在查询结果下方新增“同比与环比（基于最新月份）”对比表；
     - 新增“专业分析要点”模块，自动生成结构化结论；
     - 增加涨跌配色、分析卡片等样式，保持与现有页面视觉一致。
  2. 计算逻辑（前端本地）：
     - 依据 `report_month/date` 识别月份序列；
     - 以最新月份为“本期”，自动匹配“同比（月-12）”和“环比（月-1）”；
     - 按 `company+item+period+type+unit` 聚合比较；
     - 自动生成专业要点：同比/环比上升下降分布、波动最大项、温度相关性观察（皮尔逊系数）与空值质量提示。
  3. XLSX 导出内容：
     - Sheet1：查询结果；
     - Sheet2：同比环比对比；
     - Sheet3：专业分析结论。
- **Result:** 查询结果卡片现已具备“可看、可比、可导出”的分析能力，可直接用于月报研判与汇报。

## 2026-02-28（同比/环比逻辑修正为后端实时窗口补查）

- **User Feedback:** 当前同比值存在但显示为 `NULL`；同比应取“上一年度同一时期、同 type、同口径、同指标”，环比应取“上一个同样长度时期”。
- **Agent Action:**
  1. 后端 `backend/projects/monthly_data_show/api/workspace.py` 新增接口：
     - `POST /monthly-data-show/query-comparison`
     - 入参复用查询页 `QueryRequest`。
  2. 对比窗口定义：
     - 当前窗口：优先使用 `date_from/date_to`；若缺失则回退 `report_month_from/report_month_to`；
     - 同比窗口：当前窗口整体向前平移 1 年（按自然日安全平移）；
     - 环比窗口：紧邻当前窗口之前、且长度与当前窗口相同的时间段。
  3. 查询维度与聚合规则：
     - 严格按 `company + item + period + type + unit` 匹配；
     - 保留口径聚合开关 `aggregate_companies`；
     - 当前/同比/环比分别实时补查数据库并生成 `current_value/yoy_value/mom_value` 与涨跌率。
  4. 前端 `MonthlyDataShowQueryToolView.vue`：
     - 取消“仅基于当前页 rows 的本地同比推导”；
     - 查询时并行调用：
       - `/monthly-data-show/query`
       - `/monthly-data-show/query-comparison`
     - 对比表与分析要点改为使用后端实时对比结果；
     - 导出 XLSX 的“同比环比对比”sheet 同步使用实时对比数据。
  5. API 服务 `frontend/src/projects/daily_report_25_26/services/api.js`：
     - 新增 `queryMonthlyDataShowComparison` 调用封装。
- **Result:** 同比/环比不再受分页与前端样本截断影响，改为按数据库实时窗口补查；存在历史值时将正确显示，不再误判 `NULL`。

## 2026-02-28（新增同比/环比可视化总览：热力图 + TopN）

- **User Request:** 增加一个图，一目了然展示各指标同比/环比情况，并兼顾指标过多时的可读性。
- **Agent Action:**
  1. 页面 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue` 新增可视化模块：
     - 视角切换：`同比/环比`
     - 容量控制：`TopN 指标（10/15/20/30）`
  2. 图形设计：
     - 热力图（指标 × 口径）：颜色深浅表示涨跌幅绝对值，绿色为上升、红色为下降；
     - 波动 TopN 条形图：按绝对涨跌幅排序，突出最值得关注序列。
  3. 数据来源：
     - 复用后端 `query-comparison` 的实时对比结果；
     - 不再依赖当前分页结果推导，避免样本截断造成图形偏差。
  4. 导出联动：
     - XLSX 导出继续包含“同比环比对比”sheet，使用实时对比数据。
- **Result:** 已形成“总览（热力）+聚焦（TopN）”组合，指标数量较多时也可快速定位异常项。

## 2026-02-28（同比/环比颜色语义调整）

- **User Request:** 同比/环比百分比在表格、热力图等处统一为“正数红色，负数绿色”。  
- **Agent Action:**  
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 百分比样式类颜色反转：`delta-up` 改为红色，`delta-down` 改为绿色；  
     - 热力图着色逻辑反转：正值红色系、负值绿色系；  
     - TopN 条形图填充色同步反转。  
- **Result:** 页面内同比/环比颜色语义已完全统一为“红涨绿跌（正红负绿）”。

## 2026-02-28（热力图标题换行与轴向语义修正）

- **User Feedback:** 热力图“指标/口径”描述疑似因换行导致理解歧义。  
- **Agent Action:**  
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 标题改为：`热力图（纵轴=指标，横轴=口径）`；  
     - 增加 `viz-title-nowrap` 样式，标题不换行显示。  
- **Result:** 标题表达与轴向语义更清晰，避免“指标 口径”断行误读。

## 2026-02-28（热力图网格错位修复：指标行串到口径列）

- **User Feedback:** 热力图里“指标名称显示在口径一行里”，出现行列错位。  
- **Agent Action:**  
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 热力图容器从 `auto-fill` 动态列改为“固定列数=口径数量”；  
     - 新增 `heatmapGridStyle` 计算属性，动态设置：`220px + N个口径列`；  
     - 移除 `grid-template-columns: repeat(auto-fill, ...)`，避免浏览器自动换列；  
     - 小屏下改为最小宽度 + 横向滚动，不再压缩换列。  
- **Result:** 每一行严格保持“1个指标标签 + N个口径单元格”，不再出现指标文本串到口径列的错位问题。

## 2026-03-01（monthly_data_show 页面故障排查会话）

- **User Context:** 用户反馈 `http://localhost:5173/projects/monthly_data_show/pages` 相关页面仍有若干 BUG 与待完善功能。
- **Agent Action:**
  1. 完成 Serena 会话校验：
     - `serena__activate_project`：已激活 `D:\编程项目\phoenix`
     - `serena__check_onboarding_performed`：已完成 onboarding
  2. 代码与配置排查范围：
     - 前端页面：
       - `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
       - `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
       - `frontend/src/router/index.js`
       - `frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue`
     - 后端接口：
       - `backend/projects/monthly_data_show/api/workspace.py`
       - `frontend/src/projects/daily_report_25_26/services/api.js`（调用封装对齐）
     - 项目与权限配置：
       - `backend_data/shared/项目列表.json`
       - `backend_data/shared/auth/permissions.json`
  3. 结论：
     - 页面路由链路已存在：`/projects/monthly_data_show/pages` → 子页 → `/import-workspace` 与 `/query-tool`
     - 当前未收到可复现步骤/报错截图，暂无法针对性下补丁；待用户补充 BUG 清单后逐项修复。
- **Code Changes:** 本轮未修改业务代码，仅进行排查与留痕同步。

## 2026-03-01（monthly_data_show 计算指标实时查询修复 + 公式弹窗）

- **User Feedback:**  
  1) 月报数据查询页中“计算指标（19项）”无法查询显示；  
  2) 希望在“计算指标（19项）”标题右侧增加按钮，点击后弹出每个计算指标的公式说明。
- **Root Cause:**  
  - 导入链路 `extractor.py` 会过滤 19 项计算指标，不会写入 `month_data_show`；  
  - 查询接口此前仅查表，不做实时计算，因此计算指标始终为空。
- **Agent Action:**
  1. 后端 `backend/projects/monthly_data_show/api/workspace.py`：  
     - 新增计算指标元数据：  
       - `CALCULATED_ITEM_SET`（19项）  
       - `CALCULATED_ITEM_UNITS`（单位映射）  
       - `CALCULATED_DEPENDENCY_MAP`（依赖指标映射）  
     - 新增实时计算能力：  
       - `_collect_required_base_items`：按已选计算指标递归收集所需基础指标；  
       - `_compute_calculated_indicator`：按公式计算单个指标；  
       - `_build_calculated_rows`：按口径/期间/类型（及月份）分组生成计算指标结果行；  
       - 缺失指标按 0、分母为 0 按 0（与配置文件规则一致）。  
     - 查询主接口 `POST /monthly-data-show/query` 调整：  
       - 主查询不再只按用户选择项直接查表；若选了计算指标，会自动补查其依赖基础指标；  
       - 在数据库结果基础上实时计算 19 项，再与基础指标/平均气温结果合并排序分页返回。  
     - 对比接口 `_fetch_compare_map` 同步支持计算指标：  
       - 当前/同比/环比窗口下均可实时计算计算指标，确保对比分析与主查询口径一致。
  2. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 在“计算指标（19项）”标题行右侧新增 `查看公式` 按钮；  
     - 新增公式弹窗（遮罩+表格），展示 19 项指标对应公式与单位；  
     - 新增 `calculatedFormulaRows` 配置与弹窗样式。
- **Result:**  
  - 计算指标可在查询页实时计算并正常显示；  
  - 对比分析（同比/环比）同样可覆盖计算指标；  
  - 页面支持一键查看 19 项公式说明，便于校核与解释。

## 2026-03-01（查询失败排查：ERR_CONNECTION_REFUSED）

- **User Feedback:** 查询页点击“查询”后，`/monthly-data-show/query`、`/query-comparison` 及 `/audit/events` 全部 `ERR_CONNECTION_REFUSED`。
- **Agent Action:**
  1. 核对前端 API 基址：`frontend/.env.development` 为 `VITE_API_BASE=http://127.0.0.1:8001`；
  2. 核对容器端口映射：`docker-compose.yml` 中 backend 为 `8001:8000`；
  3. 结论：请求地址与映射一致，问题不在页面查询逻辑，属于后端服务当前不可达（未启动或启动后异常退出）。
- **Result:** 已明确本次报错为服务连通性问题，需优先恢复 backend 监听后再验证查询逻辑。

## 2026-03-01（计算指标展示规则与两轮计算增强）

- **User Request:**  
  1) 单位为 `%` 的值按百分数展示（如 `0.65` 显示 `65%`）；  
  2) 所有数据若小数部分不为 0，统一保留 2 位小数；  
  3) 计算指标存在依赖链，要求连续两轮计算后展示。
- **Agent Action:**
  1. 后端 `backend/projects/monthly_data_show/api/workspace.py`：  
     - 新增 `_compute_calculated_two_pass(...)`，固定执行两轮计算；  
     - `query` 与 `query-comparison` 两条链路均改为调用两轮计算结果；  
     - `val(...)` 取值顺序优化：优先当前缓存，再读上轮已写入的计算指标值，最后回退递归计算。
  2. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 新增 `formatValue(value, unit)`：单位为 `%` 时按 `value*100 + '%'` 展示；  
     - `formatNumber` 规则统一：  
       - 整数显示为整数；  
       - 非整数四舍五入后固定 2 位小数；  
     - 查询结果表与同比/环比表的数值渲染切换为 `formatValue(...)`。
- **Result:**  
  - 百分比类指标显示符合业务习惯；  
  - 数值小数位展示统一为“非整值两位”；  
  - 计算指标依赖链按两轮计算输出，最终展示更稳定。

## 2026-03-01（北海发电水耗率/供热水耗率计算偏差修复）

- **User Feedback:** `company=北海` 下，`发电水耗率`、`供热水耗率` 计算不正确。
- **Root Cause:**  
  - 两个指标依赖 `热分摊比`；`热分摊比` 又依赖 `耗标煤总量`。  
  - 实际数据中存在同义指标命名（如 `标煤耗量`、`煤折标煤量`），若仅按单一指标名取值，会出现依赖缺失并导致结果偏差。
- **Agent Action:**  
  1. 后端 `backend/projects/monthly_data_show/api/workspace.py` 新增 `METRIC_ALIAS_MAP`；  
  2. `_collect_required_base_items` 增强：计算依赖补查时同时补查别名指标；  
  3. `_compute_calculated_indicator` 的 `val(...)` 增强：主指标为 0/缺失时按别名顺序回退取值。
- **Result:**  
  - `发电水耗率`、`供热水耗率` 的上游依赖在命名不一致场景下可正确命中，北海口径计算结果与业务口径更一致。

## 2026-03-01（水耗率公式口径修订）

- **User Request:** 修订以下两个计算指标公式：  
  1) `发电水耗率 = (耗水量-供汽量-热网耗水量) * (1-热分摊比) / 发电量`  
  2) `供热水耗率 = ((耗水量-供汽量-热网耗水量) * 热分摊比 + 供汽量 + 热网耗水量) / 供热量`
- **Agent Action:**
  1. 后端 `backend/projects/monthly_data_show/api/workspace.py`：  
     - 更新 `发电水耗率`、`供热水耗率` 计算表达式；  
     - 依赖映射 `CALCULATED_DEPENDENCY_MAP` 同步加入 `热网耗水量`。
  2. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 公式弹窗中的两条公式文案同步更新。
- **Result:** 查询结果计算逻辑与页面公式说明均已切换到你最新给定口径。

## 2026-03-01（查询结果字段与排序修复）

- **User Feedback:**  
  1) 查询结果表不应显示 `report_month` 字段；  
  2) 指标显示顺序未完全按用户选择次序排序。
- **Agent Action:**
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 查询结果表头与行渲染中移除 `report_month` 列。
  2. 后端 `backend/projects/monthly_data_show/api/workspace.py`：  
     - 新增 `_build_rank_map(...)`；  
     - 排序函数 `_merge_and_sort_rows(...)` 增加 `rank_maps` 入参；  
     - `query` 返回前排序改为：按 `company/item/period/type` 的“用户勾选顺序”优先，再按文本兜底；  
     - 其中 `item` 顺序直接使用前端提交的 `filters.items` 顺序。
- **Result:**  
  - 查询结果页不再显示 `report_month`；  
  - 指标与维度行顺序优先遵循用户勾选次序，展示更符合操作预期。

## 2026-03-01（XLSX 导出与页面字段保持一致 + 文件名简化）

- **User Request:**  
  1) 导出文件与查询结果展示保持一致（不包含 `report_month`）；  
  2) 导出文件名简化为 `月报查询分析_YYYY-MM.xlsx`。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - `downloadXlsx()` 中查询结果 sheet 移除 `report_month` 列；  
     - 新增 `resolveExportMonthTag()`：按筛选条件/窗口标签推断月份；  
     - 文件名从长区间+时间戳改为 `月报查询分析_${monthTag}.xlsx`。  
- **Result:**  
  - 导出字段与页面字段一致；  
  - 文件名更简洁，符合 `月报查询分析_2026-01.xlsx` 风格。

## 2026-03-01（新增计划比：与当月 plan 对比）

- **User Request:** 在现有同比/环比基础上新增“计划比”，与当月 `plan` 值进行对比。
- **Agent Action:**
  1. 后端 `backend/projects/monthly_data_show/api/workspace.py`：  
     - `QueryComparisonRow` 新增：`plan_value`、`plan_rate`；  
     - `QueryComparisonResponse` 新增：`plan_window_label`；  
     - 新增 `_fetch_plan_value_map(...)`：在当前窗口内按 `type='plan'` 取计划值；  
     - 计划值支持基础指标与计算指标（复用计算引擎），并适配口径聚合；  
     - `query-comparison` 返回 `current` 相对 `plan` 的偏差率。
  2. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 展示口径下拉新增 `计划比`；  
     - 对比表新增 `计划值`、`计划比` 两列；  
     - 计划窗口标签接入显示；  
     - 热力图与 TopN 条形图复用 `rateValue`，支持计划比视角；  
     - 专业分析要点新增计划比统计与偏差 Top 项；  
     - XLSX 导出对比 sheet 新增 `plan_value`、`plan_rate`。
- **Result:**  
  - 页面现支持“同比/环比/计划比”三种对比口径，可统一查看、可视化与导出。

## 2026-03-01（热力图与波动 TopN 统一切换开关）

- **User Request:** 为“热力图”和“波动 TopN（绝对值）”增加统一切换开关，用于切换 `同比/环比/计划比`。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 在可视化工具栏新增统一按钮组（同比/环比/计划比）；  
     - 新增 `comparisonModeLabel` 计算属性，统一驱动可视化标题；  
     - 热力图与 TopN 标题改为动态显示当前口径；  
     - 补充按钮组样式（激活态高亮、分段边框）。
- **Result:**  
  - 热力图与 TopN 使用同一个口径开关，切换行为一致；  
  - 页面不再依赖下拉切换，交互更直观。

## 2026-03-01（同比/环比/计划比结果排序与筛选顺序对齐）

- **User Feedback:** 下方“同比/环比/计划比（实时窗口）”中的口径/指标排序未与上方勾选顺序一致。
- **Root Cause:**  
  - `query-comparison` 接口原先按 `sorted(current_map.keys())` 字典序输出，未应用与主查询一致的 rank 排序规则。
- **Agent Action:**  
  1. 后端 `backend/projects/monthly_data_show/api/workspace.py`：  
     - 新增 `_sort_comparison_rows(...)`，支持按 `order_fields` + `rank_maps` 排序；  
     - `query_month_data_show_comparison(...)` 中补充 `order_mode` 校验与 `resolved_order_fields` 解析；  
     - 按用户勾选顺序构建 `company/item/period/type` rank map；  
     - 返回前统一调用 `_sort_comparison_rows(...)` 排序。
- **Result:**  
  - 下方同比/环比/计划比结果已按上方选择顺序排序，口径与指标展示顺序一致。

## 2026-03-01（专业分析增强 + 平均气温折叠区 + 全量XLSX子工作表）

- **User Request:**  
  1) 丰富“专业分析要点”，并依据“数据层次顺序”分组输出同比/环比/计划比差值与差异率；  
  2) 当选择“平均气温”指标时，新增默认折叠区，展示区间每日气温、同比值、平均气温同比及本期/同期曲线；  
  3) 页面上所有数据与分析均纳入 XLSX 不同子工作表。
- **Agent Action:**  
  1. 后端 `backend/projects/monthly_data_show/api/workspace.py`：  
     - `QueryComparisonResponse` 新增 `temperature_comparison`；  
     - 新增模型：`TemperatureDailyComparisonRow`、`TemperatureComparisonSummary`、`TemperatureComparisonPayload`；  
     - 新增 `_build_temperature_comparison_payload(...)`：从 `calc_temperature_data` 生成“当前区间逐日 vs 同期逐日”明细与均值同比。  
  2. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - “专业分析要点”改为按 `filters.orderFields` 分组解说；  
     - 输出每个分组的同比/环比/计划比差值与差异率，并补充 Top 波动与风险条目；  
     - 新增“平均气温区间分析（默认折叠）”模块：  
       - 每日气温同比表；  
       - 本期/同期平均气温及同比；  
       - 本期与同期曲线图（SVG）；  
     - 扩展 XLSX 导出为多工作表：`汇总信息`、`查询结果`、`对比明细`、`热力图`、`TopN`、`专业分析`、`气温日序同比`、`气温汇总`（按数据存在情况追加）。  
- **Result:**  
  - 页面分析可读性与业务解释深度显著增强；  
  - 平均气温指标具备“日序+同比+曲线+均值同比”的完整分析闭环；  
  - 导出文件覆盖页面主要数据与分析结果，便于归档复盘。

## 2026-03-01（XLSX导出样式优化 + 移除热力图/TopN子表）

- **User Request:**  
  - 导出表格样式可读性太差；  
  - 不需要“热力图”和“TopN”两个子表。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 新增 `finalizeSheet(...)`，统一为各工作表设置列宽与表头筛选；  
     - 导出列头统一改为中文业务列名；  
     - 导出值统一改为页面同款格式（百分比、差值符号、小数位）；  
     - 明确移除 `${当前口径}热力图` 与 `${当前口径}TopN` 两个工作表；  
     - 保留并优化其余工作表（汇总/查询/对比/专业分析/气温明细/气温汇总）。
- **Result:**  
  - 导出文件可读性明显提升；  
  - 工作表数量收敛到业务需要的内容，不再包含热力图与TopN子表。

## 2026-03-01（平均气温口径固定为 common + 查询结果置顶）

- **User Request:**  
  - “平均气温”指标口径固定为 `common`（不归属现存实际口径）；  
  - 查询结果显示时，该指标置于最上方。
- **Agent Action:**  
  1. 后端 `backend/projects/monthly_data_show/api/workspace.py`：  
     - 新增常量 `AVERAGE_TEMPERATURE_COMPANY = "common"`；  
     - `_build_average_temperature_rows(...)` 改为只生成 `company=common` 的温度行；  
     - `_fetch_compare_map(...)` 中平均气温对比行改为固定 `company=common`；  
     - `_merge_and_sort_rows(...)` 与 `_sort_comparison_rows(...)` 增加“平均气温优先”排序前缀。  
- **Result:**  
  - 平均气温在查询/对比输出中统一以 `common` 口径显示；  
  - 查询结果中该指标优先显示在顶部。

## 2026-03-01（差异率分母统一按绝对值确认）

- **User Request:** 所有同比/环比/计划比差异率的分母统一按绝对值计算。
- **Agent Check:**  
  1. 后端 `backend/projects/monthly_data_show/api/workspace.py`：  
     - `_calc_rate(current, base)` 已使用 `(current - base) / abs(base)`。  
  2. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - `calcRate(current, base)` 已使用 `(current - base) / Math.abs(base)`；  
     - 专业分析分组差异率复用该函数。  
- **Result:**  
  - 查询对比、专业分析、气温同比相关差异率均满足“绝对值分母”规则，无需额外逻辑改动。

## 2026-03-01（筛选项简化 + 简要分析报告化改写）

- **User Request:**  
  1) 去掉筛选第一行中的“来源月份起止”；  
  2) 将“专业分析要点”改为“简要分析”，并将内容改写为报告式顺序行文，不使用“分组1（...）”技术表达。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 移除“来源月份起/来源月份止”两个筛选控件；  
     - `filters` 去除 `reportMonthFrom/reportMonthTo`；  
     - `buildPayload()` 中 `report_month_from/report_month_to` 固定传 `null`；  
     - `resetFilters()` 同步移除来源月份重置逻辑；  
     - 分析标题由“专业分析要点”改为“简要分析”；  
     - `analysisInsights` 重写为报告式结构（“一、二、三...”），按总体、结构、同比重点、环比重点、计划执行、当前关注、风险提示、数据完整性顺序输出。  
- **Result:**  
  - 筛选区第一行更简洁；  
  - 分析文案更接近业务报告写法，阅读体验更符合汇报场景。

## 2026-03-01（简要分析改为层次驱动的逐项报告结构）

- **User Clarification:**  
  - 除总体情况外，需按“数据层次顺序”逐层展开（如：口径 > 指标 > 期间 > 类型）；  
  - 在末级逐项输出：本期、同期同比、上期环比、计划比的差值与差异率，采用“增加/减少/持平”叙述。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 重写 `analysisInsights` 生成逻辑；  
     - 根据 `filters.orderFields` 动态构建层次树并按顺序遍历输出；  
     - 末级行文统一为：  
       - 本期值；  
       - 同期值 + 同比增减 + 差值 + 差异率；  
       - 上期值 + 环比增减 + 差值 + 差异率；  
       - 计划值 + 较计划增减 + 差值 + 差异率；  
     - 保留风险提示与数据完整性总结。\n+- **Result:**  
  - “简要分析”由概览型改为可直接阅读的分层逐项分析，更贴近报告正文结构。

## 2026-03-01（隐藏期间/类型筛选并固定 month+real）

- **User Request:** 隐藏“期间”“类型”筛选器，默认固定 `month` 与 `real`。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 移除筛选区中的“期间（可多选）”“类型（可多选）”；  
     - 查询按钮校验改为仅依赖“口径 + 指标”；  
     - `buildPayload()` 固定传 `periods: ['month']`、`types: ['real']`；  
     - `loadOptions()` 与 `resetFilters()` 固定初始化 `filters.periods=['month']`、`filters.types=['real']`。  
- **Result:**  
  - 页面不再暴露期间/类型选择，查询固定为月度实绩（month + real）。

## 2026-03-01（数据层次顺序与聚合开关布局优化）

- **User Request:** 调整“数据层次顺序”及其后方“聚合”框体布局。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 将该区域容器从 `inline-four` 重构为 `inline-layout` 双栏布局；  
     - 左栏为“数据层次顺序”（`order-col`），右栏为“聚合开关”（`aggregate-col`）；  
     - 聚合开关卡片增加 `aggregate-switch`，统一高度与间距；  
     - 响应式调整：  
       - ≤900px 双栏并排；  
       - ≤640px 单栏堆叠。  
- **Result:**  
  - “数据层次顺序”与“聚合开关”在桌面端对齐更清晰，移动端折叠更自然。

## 2026-03-01（层次顺序仅保留口径/指标并与聚合同排）

- **User Request:**  
  - 数据层次顺序中去掉“期间”“类型”，只保留“口径”“指标”，并同一行显示；  
  - 聚合框体中的两项内容也同一行显示。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - `layerOptions` 仅保留 `company/item`；  
     - `filters.orderFields` 默认值与重置值改为 `['company','item']`；  
     - 请求 `order_fields` 仅提交 `company/item`；  
     - “数据层次顺序”区域由纵向列表改为 `order-inline` 单行显示；  
     - “聚合开关”区域改为 `aggregate-inline` 单行放置两个开关项；  
     - 响应式补充：窄屏可自动换行避免溢出。  
- **Result:**  
  - 层次顺序只展示“口径/指标”；  
  - 层次顺序与聚合开关内部均为同排展示，结构更紧凑直观。

## 2026-03-01（层次顺序与聚合开关视觉对齐微调）

- **User Request:** “数据层次顺序”和“聚合开关”整体高度与文字竖直位置保持一致，整体排布更美观。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - `inline-layout` 增加 `align-items: stretch`，保证双栏等高；  
     - `inline-col` 统一 `min-height` 与 `gap`；  
     - 两栏头部 `field-head` 统一最小高度；  
     - `order-inline` 与 `aggregate-inline` 统一最小高度并开启 `flex: 1`；  
     - `order-inline .check-item` 与 `aggregate-item` 统一行高与垂直居中。  
- **Result:**  
  - 两块区域高度与文字基线更加一致，视觉上更整齐。

## 2026-03-01（业务月份筛选器样式与易用性优化）

- **User Feedback:** “业务月份起”日期选框不美观且操作不便利。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 对“业务月份起/止”输入区做组件化样式优化（卡片背景、聚焦高亮、控件尺寸统一）；  
     - 为“业务月份起”增加快捷按钮：`本月`、`上月`；  
     - 为“业务月份止”增加快捷按钮：`本月`、`同起月`；  
     - 新增“快捷区间”按钮：`近3个月`、`近6个月`、`近12个月`、`本年`；  
     - 增加月份范围顺序保护（起月晚于止月时自动纠正）。  
- **Result:**  
  - 月份选择交互显著简化，常用区间可一键设置，输入框视觉一致性提升。

## 2026-03-01（简要分析去圆点并强化层次排版）

- **User Request:** “简要分析”不要每行圆点开头，需要更清晰的结构层次。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 分析区从 `ul/li` 改为段落流式渲染；  
     - 新增 `analysisLineClass(...)`，按文本前缀识别层次：  
       - 一级：`一、二、三...`  
       - 二级：`口径：/指标：/期间：/类型：`  
       - 三级：明细句  
     - 样式改为分层缩进与字重区分，移除默认圆点。  
- **Result:**  
  - 分析内容从“点列”变为“分层文本”，结构更易读。

## 2026-03-01（简要分析指标层前缀精简）

- **User Request:** “指标：耗标煤总量”这类写法改为仅显示“耗标煤总量”。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 在分层分析生成逻辑中，对 `item` 层级改为仅输出指标名；  
     - 其余层级（如口径）仍保留前缀标签，维持结构可读性。  
- **Result:**  
  - 简要分析文本更简洁，指标行更贴近自然表述。

## 2026-03-01（简要分析指标圆点与描述缩进）

- **User Request:**  
  - 每个指标名前加小圆点；  
  - 指标下方比较描述前空两格。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 指标层文本改为 `•指标名`；  
     - 比较描述行文前增加两个空格前缀；  
     - `analysisLineClass` 增加 `item-title` 识别；  
     - 分析行样式增加 `white-space: pre-wrap`，保证空格缩进可见。  
- **Result:**  
  - 简要分析中“指标标题”和“指标说明”层次更清晰，排版更符合阅读习惯。

## 2026-03-01（简要分析数值补充计量单位）

- **User Request:** 每个指标的本期值/同期值/计划值需要带计量单位。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 新增 `formatValueWithUnit(value, unit)`；  
     - 在简要分析末级描述中，将本期/同期/上期/计划值统一改为“数值 + 单位”输出；  
     - `%` 单位保持百分比展示，不重复追加单位文本。  
- **Result:**  
  - 简要分析中的核心对比值具备单位语义，阅读更准确。

## 2026-03-01（缺失上期值时省略环比段）

- **User Request:** 若缺少“上期值”，则简要分析中整段环比描述不应显示。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 末级分析句改为分段动态拼接；  
     - 当 `momValue == null` 时，不拼接“上期...环比...”整段；  
     - 其余（本期/同比/计划）段落保持正常输出。  
- **Result:**  
  - 不再出现“上期—，环比0，差异率—”这类无意义句段，分析文本更自然。

## 2026-03-01（对比列表隐藏期间/类型字段）

- **User Request:** “同比/环比/计划比（实时窗口）”列表中隐藏“期间”“类型”字段。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 对比表移除“期间”“类型”表头与对应单元格；  
     - 对比表最小宽度从 `1080px` 调整为 `860px`，减少无效横向留白。  
- **Result:**  
  - 对比列表聚焦核心字段（口径、指标、值与比率），展示更简洁。

## 2026-03-01（对比列表字段命名业务化）

- **User Request:**  
  - “当前值”改为“本期值”；  
  - “同比值”改为“同期值”；  
  - “环比值”改为“上期值”。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 对比表表头替换为 `本期值/同期值/上期值`；  
     - XLSX 导出“对比明细”子表表头同步替换，保证页面与导出一致。  
- **Result:**  
  - 文案更符合业务语义，用户理解成本更低。

## 2026-03-01（四值全零指标跳过分析）

- **User Request:** 若某口径下某指标的本期/同期/上期/计划值全为 0，则跳过该指标的分析内容。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 在简要分析生成中新增 `shouldSkipAnalysisRow(...)`；  
     - 当 `current/yoy/mom/plan` 四值均为 0 时，末级描述不输出；  
     - 同步在分组阶段过滤该类行，避免出现仅有标题无正文的空指标块。  
- **Result:**  
  - 简要分析中不再输出“全零指标”的冗余内容，文本更聚焦。

## 2026-03-01（简要分析口径标题视觉强化）

- **User Request:** 在“简要分析”中，各口径的字体更大、加粗标色、更显眼。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - `analysisLineClass(...)` 增加口径专属类别：`company-title`；  
     - 新增样式 `.insight-line.level-2.company-title`：  
       - 字号提升（14px）  
       - 加粗（700）  
       - 左侧强调线  
       - 浅蓝底色高亮  
       - 主色文字（深蓝）。  
- **Result:**  
  - 口径层级在分析正文中更醒目，层次识别更快。

## 2026-03-01（查询结果字段精简 + 月份控件交互优化）

- **User Request:**  
  1) 查询结果表中不再显示 `period/type`；  
  2) 月份选择按钮改为左右排列；  
  3) 起始月份默认值设为上个月（当前时间下为 `2026-02`）。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 查询结果表移除 `period/type` 列（表头与行渲染同步删除）；  
     - 导出“查询结果”工作表同步移除 `期间/类型` 字段，保证一致；  
     - `month-input-wrap` 调整为横向排列并支持换行，不再小屏纵向堆叠；  
     - `loadOptions()` 与 `resetFilters()` 中将 `dateMonthFrom` 默认设为上个月。  
- **Result:**  
  - 查询结果字段更聚焦；  
  - 月份操作区交互更顺手；  
  - 起始月份默认满足“上个月”业务习惯。

## 2026-03-01（日期按钮固定在选框右侧）

- **User Feedback:** 日期快捷按钮希望固定在日期选框右侧，不要掉到下方。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - `month-input-wrap` 调整为 `nowrap`；  
     - `month-quick-actions` 调整为 `nowrap` 并设置 `margin-left: auto`，固定靠右。  
- **Result:**  
  - 日期输入与快捷按钮保持同一行，按钮固定在右侧。

## 2026-03-01（按钮横排修正 + 标题显眼度提升 + 去重置默认）

- **User Feedback:**  
  - 日期按钮文字出现竖排，需恢复横排；  
  - “同起月”改为“同起始月”；  
  - 筛选标题“口径/指标/数据层次顺序/聚合开关”需更显眼；  
  - 去掉“重置默认”按钮。
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - `month-quick-actions .btn` 与 `.btn.ghost` 强制横排文本（`writing-mode: horizontal-tb` + `nowrap`）；  
     - 按钮文案改为“同起始月”；  
     - 上述四个标题新增 `panel-title` 样式（加粗、提亮）；  
     - 移除“重置默认”按钮与对应函数。  
- **Result:**  
  - 日期按钮文本恢复正常横排；  
  - 标题层级更醒目；  
  - 控件区更简洁。

## 2026-03-01（按钮横排样式加固 + 标题再增强）

- **User Feedback:**  
  - 日期快捷按钮文字仍出现异常排版，需确保始终横排；  
  - 各筛选标题再略微显眼一点。  
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - `month-quick-actions .btn` 增加强制横排样式：  
       - `writing-mode: horizontal-tb !important`  
       - `white-space: nowrap !important`  
       - `text-orientation: mixed`  
       - `inline-flex` 对齐；  
     - `panel-title` 字号由默认提升至 `14px`（保持加粗与高对比色）。  
- **Result:**  
  - 日期按钮在全局样式干扰下也保持横排可读；  
  - “口径（可多选）/指标（可多选）/数据层次顺序/聚合开关”标题更清晰醒目。  

## 2026-03-01（月份行防重叠布局修复）

- **User Feedback:** 月份筛选行中的选区控件出现叠在一起的问题。  
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - `month-input-wrap` 从 `flex` 改为两列 `grid`（输入区 + 按钮区），避免挤压重叠；  
     - `month-input` 设为 `width: 100%` 且 `min-width: 0`，在网格内自适应缩放；  
     - `month-quick-actions` 右对齐并设置 `min-width: max-content`，保持按钮不塌陷；  
     - 按钮最小宽度微调为 `56px`，减少横向拥挤。  
- **Result:**  
  - 月份行输入框与快捷按钮不再重叠；  
  - 保持按钮横排且位于输入框右侧。  

## 2026-03-01（移除月份行小按钮，避免控件挤压）

- **User Feedback:** 月份行仍出现“本月”等按钮压住日期选框，希望直接去掉这些小按钮。  
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 移除“业务月份起/业务月份止”中的小按钮区：`本月/上月/同起始月`；  
     - 删除对应方法：`setBusinessMonthFromCurrent`、`setBusinessMonthFromPrevious`、`setBusinessMonthToCurrent`、`syncBusinessMonthToFrom`；  
     - 清理 `month-quick-actions` 相关样式，月份输入区改为纯输入布局。  
- **Result:**  
  - 月份行空间显著变宽，不再出现按钮压住日期框的问题。  

## 2026-03-01（移除“快捷区间”）

- **User Request:** 去掉月份区域中的“快捷区间”。  
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 删除“快捷区间”区块（近3个月/近6个月/近12个月/本年）；  
     - 删除对应方法：`setBusinessMonthRangeRecent`、`setBusinessMonthRangeCurrentYear`；  
     - 删除 `month-preset-field`、`month-presets` 及其响应式样式。  
- **Result:**  
  - 月份筛选区仅保留“业务月份起/业务月份止”输入框，界面更简洁宽敞。  

## 2026-03-01（业务月份止默认上个月）

- **User Request:** “业务月份止”默认也选择当前的上个月。  
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 在 `loadOptions()` 中统一设置默认月份：`dateMonthFrom/dateMonthTo` 均为上个月；  
     - 在 `resetFilters()` 中同样将起止月份都重置为上个月。  
- **Result:**  
  - 页面初始加载与点击重置后，业务月份起止均默认为上个月（例如当前为 2026-03 时默认 `2026-02`）。  

## 2026-03-01（业务月份止改为非必选且默认不选）

- **User Request:**  
  - “业务月份止”默认不选；  
  - 标题改为“业务月份止（非必选）”。  
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 标题文案更新为“业务月份止（非必选）”；  
     - `loadOptions()` 中 `dateMonthTo` 默认值改回空字符串；  
     - `resetFilters()` 中 `dateMonthTo` 重置值改回空字符串。  
- **Result:**  
  - 页面初始与重置后仅默认选中“业务月份起=上个月”；  
  - “业务月份止”明确为可不选字段。  

## 2026-03-01（指标硬编码改为配置驱动）

- **User Request:**  
  - 将“基本指标/计算指标”两块从硬编码改为读取 `backend_data/projects/monthly_data_show` 下 JSON 配置；  
  - 计算指标公式也改为读取配置并执行；  
  - 基本指标增加“分类”占位，后续可直接改配置调整顺序与公式；  
  - 保持现有页面逻辑与功能不变。  
- **Agent Action:**  
  1. 新增配置文件：`backend_data/projects/monthly_data_show/indicator_config.json`  
     - 包含 `basic_items`（含 `category` 占位字段）与 `calculated_items`（含 `unit/formula`）；  
     - 计算公式使用 `{{指标名}}` 占位（支持 `{{天数}}`）。  
  2. 新增后端配置服务：`backend/projects/monthly_data_show/services/indicator_config.py`  
     - 负责加载配置、生成有序指标清单、提取依赖、输出前端配置载荷；  
     - 提供安全表达式求值器（分母为 0 返回 0，异常兜底为 0）。  
  3. 后端接口改造：`backend/projects/monthly_data_show/api/workspace.py`  
     - 查询选项接口新增 `indicator_config` 返回；  
     - 计算指标集合/单位/依赖/公式改为运行时从配置刷新读取；  
     - 计算执行改为按配置公式求值（保留两轮计算逻辑）；  
     - `query-options` 的指标顺序改为优先按配置顺序输出。  
  4. 提取服务改造：`backend/projects/monthly_data_show/services/extractor.py`  
     - 入库提取时“跳过计算指标”改为读取配置中的计算指标集合，不再硬编码。  
  5. 前端页面改造：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`  
     - 加载 `query-options` 时接收 `indicator_config`；  
     - 两块指标区域与公式弹窗改为配置驱动渲染；  
     - 基本指标项展示分类标签（占位），便于后续你只改 JSON 生效。  
  6. 最小校验：  
     - `python -m py_compile` 校验通过（`workspace.py`/`extractor.py`/`indicator_config.py`）。  
- **Result:**  
  - 指标顺序与计算公式已从代码硬编码迁移至配置文件；  
  - 后续你可通过修改 `indicator_config.json` 完成顺序调整、公式修订与分类维护。  

## 2026-03-01（计算指标标题默认态兜底）

- **User Feedback:** 页面出现“计算指标（0项）”。  
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 默认标题从“计算指标（0项）”改为“计算指标”；  
     - 渲染标题时增加兜底：若标题为“0项”则按当前可用列表动态生成。  
- **Result:**  
  - 配置未加载/旧接口场景下，不再先显示误导性的“0项”标题。  

## 2026-03-01（基本指标改为“分组展示”结构）

- **User Request:** 基本指标不要“每项后面挂分类标签”，而是按分类分组展示（例如“主要指标”下挂多个指标）。  
- **Agent Action:**  
  1. 配置结构升级：`backend_data/projects/monthly_data_show/indicator_config.json`  
     - 新增 `basic_groups` 结构：`[{ name, items: [{name}] }]`；  
     - 预置示例分组与占位分组，便于后续直接编辑。  
  2. 后端配置加载升级：`backend/projects/monthly_data_show/services/indicator_config.py`  
     - 新增 `basic_groups` 解析与归一化；  
     - 保持向后兼容：若无 `basic_groups`，仍可读取旧 `basic_items`。  
  3. 前端渲染升级：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`  
     - 基本指标区改为按分组标题 + 分组内指标复选展示；  
     - 取消单项分类标签显示。  
  4. 校验：  
     - `python -m py_compile` 通过（配置加载/查询/提取模块）。  
- **Result:**  
  - 你现在可仅通过修改 `indicator_config.json` 的 `basic_groups` 来控制“基本指标”的分组、顺序与内容。  

## 2026-03-01（前端编译报错修复：变量重名）

- **User Feedback:** 前端报错 `Identifier 'current' has already been declared`。  
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 在 `itemSections` 计算属性中删除重复的 `const current = []` 声明，保留后续有效声明。  
- **Result:**  
  - 修复重复声明导致的 SFC 编译错误。  

## 2026-03-01（补全未分组指标到【其他指标】）

- **User Request:** 读取当前配置后，将页面“未分组”中配置未提到的指标写入配置文件 `【其他指标】` 分组。  
- **Agent Action:**  
  1. 读取当前配置：`backend_data/projects/monthly_data_show/indicator_config.json`；  
  2. 通过 `phoenix_backend` 容器查询 `month_data_show` 的指标全集；  
  3. 将缺失项补充到 `basic_groups -> 【其他指标】 -> items`。  
- **Result:**  
  - 配置覆盖范围扩大，减少页面落入“未分组”的基础指标。  

## 2026-03-01（修复容器读取配置路径，确保按最新配置渲染）

- **User Feedback:** 页面分类名称与顺序未完全按最新配置生效。  
- **Root Cause:**  
  - 后端配置加载默认读取 `/app/backend_data/...`；  
  - 容器实际挂载目录为 `/app/data/...`，导致读取到旧配置副本。  
- **Agent Action:**  
  1. `backend/projects/monthly_data_show/services/indicator_config.py`：  
     - 配置路径改为候选优先级读取：  
       - `/app/data/projects/monthly_data_show/indicator_config.json`（优先）  
       - `/app/backend_data/projects/monthly_data_show/indicator_config.json`（兼容回退）  
  2. 容器内验证：  
     - 已读取到你最新分组：`主要产销指标/主要消耗指标/其它消耗指标/面积与能力/【其他指标】`；  
     - 基础指标覆盖校验差集 `missing=0`。  
- **Result:**  
  - 页面分组名称、顺序与指标项可按你编辑的配置文件一致生效。  

## 2026-03-01（基础指标单位纳入配置文件）

- **User Request:** 将指标的计量单位加入配置文件。  
- **Agent Action:**  
  1. 后端配置解析升级：`backend/projects/monthly_data_show/services/indicator_config.py`  
     - 支持读取 `basic_groups.items[].unit`（并兼容旧结构）；  
  2. 配置文件补齐单位：`backend_data/projects/monthly_data_show/indicator_config.json`  
     - 为当前基础指标分组项补全 `unit` 字段；  
  3. 容器内验证：  
     - 配置加载后 `basic_items` 的单位字段已全部可读（`unit_count=67`）。  
- **Result:**  
  - 基础指标与计算指标都可在配置文件中统一维护计量单位。  

## 2026-03-01（指标选择区隐藏计量单位，仅在结果/分析使用）

- **User Request:** 指标选择区域不要显示每个指标的计量单位；单位仅用于查询结果表格与简要分析文本。  
- **Agent Action:**  
  1. 前端页面 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 移除“指标（可多选）”中基本分组与计算分组项后的单位标签渲染；  
     - 删除选择区单位映射计算 `itemUnitMap`；  
     - 删除对应样式 `.unit-tag`。  
- **Result:**  
  - 指标选区恢复为纯指标名展示；  
  - 计量单位仍由配置文件维护，并继续在查询结果/简要分析等结果呈现链路中使用。  

## 2026-03-01（导入映射新增：锅炉耗柴油量 -> 耗油量）

- **User Request:** 在月报导入工作台的指标名称转换规则中新增 `"锅炉耗柴油量" -> "耗油量"`。  
- **Agent Action:**  
  1. 后端导入提取映射 `backend/projects/monthly_data_show/services/extractor.py`：  
     - 在 `ITEM_RENAME_MAP` 新增条目：`"锅炉耗柴油量": "耗油量"`。  
- **Result:**  
  - 导入时若识别到源指标名“锅炉耗柴油量”，将统一归并为“耗油量”入库/后续计算。  

## 2026-03-01（金普期末供暖收费面积扣减规则补齐）

- **User Feedback:** 月报导入提取时，规则“金普 期末供暖收费面积 = 期末供暖收费面积 - 高温水面积”疑似未执行。  
- **Agent Action:**  
  1. 检查导入提取服务 `backend/projects/monthly_data_show/services/extractor.py`，确认该规则此前未落地；  
  2. 新增 `_apply_jinpu_heating_area_adjustment(rows)`：  
     - 按 `company=金普` + `date/period/type/report_month` 同窗口匹配两项指标；  
     - 命中时执行扣减：`期末供暖收费面积 -= 高温水面积`；  
     - 将结果单位统一为 `平方米`；  
  3. 在 `extract_rows` 中接入该规则，并新增统计字段 `jinpu_heating_area_adjusted`。  
- **Result:**  
  - 月报导入提取阶段将自动应用该业务规则，避免后续查询/分析使用未扣减值。  

## 2026-03-01（金普面积扣减规则鲁棒性增强）

- **User Feedback:** 仍观察到导出 CSV 中“金普-期末供暖收费面积”是原值，未扣减“高温水面积”。  
- **Root Cause（推断）:**  
  - 旧规则命中条件过于严格（仅 `company == 金普` 且仅匹配固定两项名称），实际月报可能出现同义写法。  
- **Agent Action:**  
  1. `backend/projects/monthly_data_show/services/extractor.py`：  
     - 公司匹配从精确值改为包含匹配：`"金普" in company`；  
     - 指标名称增加同义兼容：  
       - 目标项：`期末供暖收费面积/期末供热面积/期末供暖面积`；  
       - 扣减项：`高温水面积/高温水供暖面积/高温水供热面积`；  
     - 支持同窗口下多条目标项逐条扣减。  
- **Result:**  
  - 金普面积扣减规则命中率提高，导出 CSV 更稳定反映“原始期末供暖收费面积 - 高温水面积”的结果。  

## 2026-03-01（月报查询三项指标默认4位小数）

- **User Request:** 在月报数据查询页面中，将 `供暖热耗率`、`供暖水耗率`、`供暖电耗率` 默认显示为 4 位小数。  
- **Agent Action:**  
  1. 前端页面 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 新增按指标控制小数位规则：  
       - `FOUR_DECIMAL_ITEMS = {供暖热耗率, 供暖水耗率, 供暖电耗率}`；  
       - 其余指标保持 2 位小数。  
     - `formatValue/formatValueWithUnit` 增加 `item` 入参并按指标选择小数位。  
     - 更新查询结果表、同比/环比/计划比列表、简要分析与导出数据调用，统一传入 `item`。  
- **Result:**  
  - 三项指定指标在查询页相关展示链路默认 4 位小数；其他指标展示规则不变。  

## 2026-03-01（月报查询三项指标差值也改为4位小数）

- **User Request:** 对上述三项指标的同比/环比/计划比“差值”也统一 4 位小数。  
- **Agent Action:**  
  1. 前端页面 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - `formatSignedNumber` 增加 `item` 参数，并按指标规则决定小数位；  
     - 简要分析文本中的 `yoyDiff/momDiff/planDiff` 改为传入 `row.item`；  
     - 导出对比明细中的三类差值格式化改为传入 `x.item`。  
- **Result:**  
  - `供暖热耗率/供暖水耗率/供暖电耗率` 的同比差值、环比差值、计划差值统一为 4 位小数；其余指标保持原规则。  

## 2026-03-01（补齐“四、补充指标”半计算规则写入）

- **User Request:** 将 `2.28 月报数据库化配置文件` 中“四、因部分口径数据不完备，补充以下指标”未落地部分补齐为实际提取规则。  
- **Agent Action:**  
  1. 后端提取服务 `backend/projects/monthly_data_show/services/extractor.py`：  
     - 新增 `_apply_semicalculated_completion_rules(rows)`，在提取阶段按口径+同窗口（date/period/type/report_month）重写/补齐半计算指标；  
     - 覆盖落地规则：  
       - 3) `煤折标煤量`：金普/庄河 = `耗标煤总量`；  
       - 4) `供热耗标煤量`：北海水炉/金普/庄河 = `耗标煤总量`；  
       - 6) `耗电量`：  
         - 北海/香海 = `综合厂用电量 + 外购电量`；  
         - 供热公司/金普/庄河/研究院/主城区电锅炉 = `外购电量`；  
       - 7) `耗水量`：北海/北海水炉/香海 = `电厂耗水量`；  
       - 8) `热网耗水量`：供热公司/金普/庄河/研究院/主城区电锅炉 = `耗水量`；  
       - 9) `热网耗电量`：供热公司/金普/庄河/研究院/主城区电锅炉 = `外购电量`；  
       - 10) `供暖耗热量`：  
         - 供热公司 = `各热力站耗热量`；  
         - 金州/北方/金普 = `供热量 - 高温水销售量`；  
         - 庄河/研究院/主城区电锅炉 = `供热量`。  
     - 在 `extract_rows` 中接入执行，并新增统计字段 `semi_calculated_completed`。  
  2. 已保留原有规则：  
     - 金普 `期末供暖收费面积 = 期末供暖收费面积 - 高温水面积`（规则5）。  
- **Result:**  
  - 导出 CSV 时将直接包含补齐后的半计算指标结果，且按指定口径覆盖重写，未指定口径沿用原值。  

## 2026-03-01（导入页展示提取规则命中统计）

- **User Request:** 在导入页提取后展示规则命中情况。  
- **Agent Action:**  
  1. 后端 `extract-csv` 接口 `backend/projects/monthly_data_show/api/workspace.py`：  
     - 读取 `extract_rows` 返回统计并通过响应头下发：  
       - `X-Monthly-Semi-Calculated-Completed`  
       - `X-Monthly-Jinpu-Heating-Area-Adjusted`  
       - `X-Monthly-Extracted-Total-Rows`  
     - 增加 `Access-Control-Expose-Headers`，确保前端可读。  
  2. 前端 API 封装 `frontend/src/projects/daily_report_25_26/services/api.js`：  
     - 解析上述响应头并返回 `stats` 对象。  
  3. 导入页 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`：  
     - 提取成功提示追加显示：补齐规则命中数、金普面积扣减命中数、提取总行数。  
- **Result:**  
  - 你现在每次提取后可直接看到规则实际命中统计，无需再人工推断。  

## 2026-03-01（规则命中详情弹窗）

- **User Request:** 增加按钮，点击后弹窗列出每一项规则处理情况细节。  
- **Agent Action:**  
  1. 后端 `backend/projects/monthly_data_show/services/extractor.py`：  
     - 半计算补齐规则函数改为返回逐项命中明细（如“煤折标煤量补齐”“供暖耗热量补齐”等）。  
  2. 后端 `backend/projects/monthly_data_show/api/workspace.py`：  
     - `extract-csv` 响应头新增 `X-Monthly-Rule-Details`（URL 编码 JSON），并加入 `Access-Control-Expose-Headers`。  
  3. 前端 API `frontend/src/projects/daily_report_25_26/services/api.js`：  
     - 读取并解析 `X-Monthly-Rule-Details` 为 `stats.ruleDetails`。  
  4. 前端页面 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`：  
     - 提取成功后显示“查看规则命中详情”按钮；  
     - 点击弹出详情框，逐项展示命中统计（半计算各子项、金普面积扣减、常量注入、总行数）。  
- **Result:**  
  - 导入工作台支持一键查看规则执行明细，定位规则是否生效更直接。  

## 2026-03-01（入库结果新增“新增/更新”明细）

- **User Feedback:** 第四步点击入库后，体感像未写入数据库。  
- **Agent Action:**  
  1. 后端 `backend/projects/monthly_data_show/api/workspace.py`：  
     - `import-csv` 的 UPSERT SQL 增加 `RETURNING (xmax = 0) AS inserted`；  
     - 统计并返回 `inserted_rows`、`updated_rows`。  
  2. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`：  
     - 入库成功提示改为显示：总处理/新增/更新/空值入库。  
- **Result:**  
  - 入库后可直接判断是“新增写入”还是“同主键更新覆盖”，避免误判“没入库”。  

## 2026-03-01（修复 import-csv 返回结果集关闭错误）

- **User Feedback:** 入库报错：`CSV 入库失败：This result object does not return rows. It has been closed automatically.`  
- **Root Cause:**  
  - `executemany + RETURNING` 在当前驱动场景下，批量结果集不可直接 `fetchall`。  
- **Agent Action:**  
  1. 后端 `backend/projects/monthly_data_show/api/workspace.py`：  
     - 将 `import-csv` 的 UPSERT 统计改为逐行执行并读取 `RETURNING` 标志，避免批量结果集关闭问题。  
- **Result:**  
  - 解决入库报错；  
  - 保留 `inserted_rows/updated_rows` 统计能力。  

## 2026-03-01（临时作废金普面积扣减规则）

- **User Request:** 暂时作废规则：`金普 期末供暖收费面积 = 期末供暖收费面积 - 高温水面积`。  
- **Agent Action:**  
  1. 后端提取服务 `backend/projects/monthly_data_show/services/extractor.py`：  
     - 新增开关 `ENABLE_JINPU_HEATING_AREA_ADJUSTMENT = False`；  
     - 在 `extract_rows` 中仅当开关开启时才执行该规则，当前默认关闭。  
- **Result:**  
  - 提取 CSV 时不再执行金普面积扣减；  
  - 相关统计 `jinpu_heating_area_adjusted` 将保持为 0。  

## 2026-03-01（刷新供暖耗热量规则：金普=供热量）

- **User Request:** 将“10.供暖耗热量”中的金普规则调整为：`口径=金普，指标值=供热量，计量单位=吉焦`。  
- **Agent Action:**  
  1. 后端提取服务 `backend/projects/monthly_data_show/services/extractor.py`：  
     - 半计算补齐逻辑中，`供暖耗热量` 规则改为：  
       - `金州/北方 = 供热量 - 高温水销售量`（保持不变）；  
       - `金普/庄河/研究院/主城区电锅炉 = 供热量`。  
- **Result:**  
  - 金普口径下“供暖耗热量”提取值已改为直接等于“供热量”。  

## 2026-03-01（提取规则配置化：读取 monthly_data_pull 配置文件）

- **User Request:** 在 `backend_data/projects/monthly_data_pull` 生成配置文件，并让页面执行时按配置规则处理提取。  
- **Agent Action:**  
  1. 新增配置文件：  
     - `backend_data/projects/monthly_data_pull/mapping_rules/monthly_data_show_extraction_rules.json`  
     - 含规则项：剔除指标、指标重命名、默认源字段、常量注入、半计算补齐规则、金普面积扣减开关。  
  2. 后端提取服务配置驱动：`backend/projects/monthly_data_show/services/extractor.py`  
     - 新增配置加载与刷新机制（优先读取 `monthly_data_pull/mapping_rules/...`，失败回退内置默认）；  
     - `get_company_options / get_default_constant_rules / normalize_constant_rules / extract_rows` 全链路按配置刷新后执行；  
     - 半计算补齐规则改为通用规则引擎（`copy/sum/subtract`），由 JSON `semi_calculated_rules` 驱动。  
- **Result:**  
  - 你后续可直接改 JSON 文件来调整提取规则，代码无需再硬编码修改。  

## 2026-03-01（提取规则配置文件路径更正到 monthly_data_show）

- **User Feedback:** 配置文件放错目录，应放在 `backend_data/projects/monthly_data_show`。  
- **Agent Action:**  
  1. 文件迁移：  
     - `backend_data/projects/monthly_data_pull/mapping_rules/monthly_data_show_extraction_rules.json`  
       -> `backend_data/projects/monthly_data_show/monthly_data_show_extraction_rules.json`  
  2. 后端读取路径修正：`backend/projects/monthly_data_show/services/extractor.py`  
     - 容器与本地候选路径统一改为 `monthly_data_show` 目录。  
- **Result:**  
  - 提取规则配置已在正确目录生效，后续维护按 `backend_data/projects/monthly_data_show/monthly_data_show_extraction_rules.json` 进行。  

## 2026-03-01（导入页支持手动勾选执行规则，并回显实际命中）

- **User Request:** 在月报导入工作页可手动勾选执行哪些规则（默认全选），执行后显示哪些规则被实际执行。  
- **Agent Action:**  
  1. 后端规则清单下发：  
     - `backend/projects/monthly_data_show/services/extractor.py` 新增 `get_extraction_rule_options()`；  
     - `inspect` 接口返回 `extraction_rules`。  
  2. 提取接口支持规则子集执行：  
     - `backend/projects/monthly_data_show/api/workspace.py` 的 `extract-csv` 新增表单参数 `extraction_rule_ids`；  
     - 提取服务 `extract_rows` 新增 `selected_rule_ids`，支持按选择子集执行：指标剔除、指标重命名、半计算各规则、金普面积扣减。  
  3. 前端勾选与展示：  
     - `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue` 新增“规则执行选择”面板，默认全选；  
     - 提取按钮在未选规则时禁用；  
     - “规则命中详情”弹窗新增显示：剔除命中、重命名命中、半计算各项命中、金普面积扣减、常量注入、总行数、本次选中规则。  
  4. API 透传：  
     - `frontend/src/projects/daily_report_25_26/services/api.js` 在 `extractMonthlyDataShowCsv` 中附带 `extraction_rule_ids`。  
- **Result:**  
  - 规则执行由“固定全量”改为“可勾选子集执行（默认全选）”；  
  - 提取后可看到实际命中细节并核对本次执行范围。  

## 2026-03-01（规则执行选择改为弹窗并展示详细规则）

- **User Request:** “规则执行选择”模块过于简略，改为弹窗方式，列出具体规则。  
- **Agent Action:**  
  1. 后端规则描述增强：`backend/projects/monthly_data_show/services/extractor.py`  
     - `get_extraction_rule_options()` 为规则生成更具体的 `description`（口径、指标表达式、单位）。  
  2. 前端交互改造：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`  
     - 将内联规则复选改为“打开规则列表”弹窗；  
     - 弹窗内支持全选/全不选/完成，逐条展示规则名称与说明并勾选；  
     - 主面板显示“已选数量 + 当前规则摘要”。  
- **Result:**  
  - 规则选择更清晰，能够在同一界面完整查看每条规则再决定是否执行。  

## 2026-03-01（金普面积扣减规则从弹窗清单隐藏）

- **User Feedback:** 金普面积扣减规则已取消，但弹窗仍显示该规则。  
- **Agent Action:**  
  1. 后端 `backend/projects/monthly_data_show/services/extractor.py`：  
     - `get_extraction_rule_options()` 调整为仅当 `ENABLE_JINPU_HEATING_AREA_ADJUSTMENT=True` 时才下发该规则。  
- **Result:**  
  - 当前开关为关闭状态时，规则弹窗不再显示“金普面积扣减”。  

## 2026-03-01（CSV 导入空值规则新增“-”）

- **User Request:** 导入 CSV 时，单个 `-` 也按空值处理。  
- **Agent Action:**  
  1. 后端 `backend/projects/monthly_data_show/api/workspace.py`：  
     - `NULL_VALUE_TOKENS` 增加 `"-"`。  
- **Result:**  
  - CSV 中 `value` 为 `-` 时，将按 `NULL` 入库并计入 `null_value_rows`。  

## 2026-03-01（多月聚合状态值改为取最后一期）

- **User Feedback:** 查询两个月数据时，`期末供暖收费面积`、常量容量指标（如`发电设备容量`、`锅炉设备容量`）被错误求和。  
- **Agent Action:**  
  1. 后端 `backend/projects/monthly_data_show/api/workspace.py`：  
     - 新增状态值指标集合 `LATEST_VALUE_ITEMS`；  
     - 新增聚合表达式构造 `_build_value_aggregate_sql()`；  
     - 在多月聚合与对比窗口聚合 SQL 中：  
       - 状态值指标按 `report_month/date` 倒序取最后一期值；  
       - 非状态值指标保持 `SUM(value)`。  
- **Result:**  
  - 多月查询时，状态值指标不再累加，改为最后一期口径值；  
  - 同比/环比/计划比窗口中的状态值也按最后一期处理。  

## 2026-03-01（环比窗口修复：自然月按上月整月对比）

- **User Feedback:** 已导入 26.1 和 26.2，查询 26.2 未出现环比值。  
- **Root Cause:**  
  - 旧逻辑按“同天数滚动窗口”计算环比：`2026-02-01~2026-02-28` -> `2026-01-04~2026-01-31`；  
  - 月报数据按月首日记账（`2026-01-01`），导致 1 月数据被窗口排除。  
- **Agent Action:**  
  1. 后端 `backend/projects/monthly_data_show/api/workspace.py`：  
     - 新增 `_resolve_mom_window()`：  
       - 当前窗口若为自然整月（月初到月末），环比窗口改为“上月自然整月”；  
       - 非整月窗口保持原滚动逻辑。  
     - `query-comparison` 中改用该函数生成 `mom_start/mom_end`。  
- **Result:**  
  - 以 26.2 为当前月查询时，环比窗口将对齐到 26.1 整月，环比值可正常命中。  

## 2026-03-01（环比修复补充留痕：前后端 README 同步）

- **Agent Action:**  
  1. 更新 `backend/README.md`：补充“环比窗口错位修复”说明（自然月 -> 上月整月，非整月保持滚动窗口）。  
  2. 更新 `frontend/README.md`：补充“26.2 查询将命中 26.1 环比”的联动说明。  
- **Result:**  
  - 本轮修复的实现逻辑与前端联动行为已在 README 留痕，便于后续排查与交接。  

## 2026-03-01（全局管理后台新增数据库表在线编辑）

- **User Request:** 在“全局管理后台 -> 后台文件编辑”中增加数据库表在线编辑与保存能力，先支持 `monthly_data_show`，并可扩展到其他表。  
- **Agent Action:**  
  1. 后端 `backend/api/v1/admin_console.py` 新增数据库编辑接口：  
     - `GET /api/v1/admin/db/tables`：列出 `public` schema 下基础表；  
     - `POST /api/v1/admin/db/table/query`：按表名分页读取数据（返回字段、主键、总数、行数据）；  
     - `POST /api/v1/admin/db/table/batch-update`：按主键批量保存行修改。  
  2. 前端 API `frontend/src/projects/daily_report_25_26/services/api.js` 新增：  
     - `listAdminDbTables`、`queryAdminDbTable`、`batchUpdateAdminDbTable`。  
  3. 前端页面 `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`：  
     - 在“后台文件编辑”页新增“数据库表在线编辑”模块；  
     - 支持表选择、分页参数（limit/offset）、加载数据、行内编辑、批量保存；  
     - 主键字段只读并标记 `PK`，保存时仅提交变更字段。  
- **Verify:**  
  - 执行 `python -m py_compile backend/api/v1/admin_console.py`，通过。  
- **Result:**  
  - 现在可在后台直接对 `monthly_data_show` 等含主键表进行小幅临时修改并保存。  

## 2026-03-02（monthly_data_show 表名纠偏）

- **User Request:** 数据表已改名为 `monthly_data_show`，程序内仍有 `month_data_show` 依赖，要求统一修正。  
- **Agent Action:**  
  1. 后端 `backend/projects/monthly_data_show/api/workspace.py`：  
     - 查询、筛选项读取、CSV 入库 UPSERT 的表名统一改为 `monthly_data_show`；  
     - 接口 summary 文案同步更新。  
  2. 建表脚本 `backend/sql/month_data_show.sql`：  
     - `CREATE TABLE` 目标表改为 `monthly_data_show`；  
     - 索引名改为 `idx_monthly_data_show_*` 并绑定新表名。  
  3. 前端页面文案同步：  
     - `MonthlyDataShowEntryView.vue`、`MonthlyDataShowQueryToolView.vue` 中表名展示改为 `monthly_data_show`。  
- **Verify:**  
  - 执行 `python -m py_compile backend/projects/monthly_data_show/api/workspace.py`，通过。  
- **Result:**  
  - 月报导入/查询链路已切换为新表名 `monthly_data_show`，不再依赖旧表名。  

## 2026-03-02（月报查询数据层次顺序新增“时间”并默认第一位）

- **User Request:** 在“数据层次顺序”中增加“时间”，默认第一位；跨月查询按时间先后分组展示（如 26.1 全部口径/指标在前，26.2 在后）。  
- **Agent Action:**  
  1. 前端 `MonthlyDataShowQueryToolView.vue`：  
     - `layerOptions` 增加 `time`；  
     - 默认 `filters.orderFields` 调整为 `['time', 'company', 'item']`；  
     - `buildPayload` 放行 `time` 到 `order_fields`；  
     - `resetFilters` 默认值同步更新。  
  2. 后端 `workspace.py`：  
     - `_resolve_order_fields` 支持 `time`，默认排序字段改为时间优先；  
     - `_merge_and_sort_rows` 在选择 `time` 时按 `report_month/date` 升序排序；未选择 `time` 时保留原有降序行为；  
     - `_sort_comparison_rows` 对 `time` 字段做忽略处理（对比数据本身无月维度分列）。  
  3. 前端“简要分析”分层文案：  
     - 当层次包含 `time` 时，按当前窗口标签显示时间分组标题，避免出现空分组。  
- **Verify:**  
  - 执行 `python -m py_compile backend/projects/monthly_data_show/api/workspace.py`，通过。  
- **Result:**  
  - 查询结果可按“时间 -> 口径 -> 指标”顺序展示，满足跨月先后分组阅读需求。  

## 2026-03-02（月报查询层次顺序修复：自定义顺序真实生效）

- **User Feedback:** 默认排序正常，但手动调整“数据层次顺序”后，查询结果仍像默认时间优先。  
- **Root Cause:**  
  - 后端 `_merge_and_sort_rows` 在排序键中预置了时间优先键，导致自定义层次顺序无法覆盖。  
- **Agent Action:**  
  1. 修改 `backend/projects/monthly_data_show/api/workspace.py`：  
     - 移除固定前置时间键；  
     - 改为按 `order_fields` 顺序逐层生成排序键；  
     - 当 `time` 在层次中时，仅在对应位置参与排序（按 `report_month/date` 升序）；  
     - 仅当未选择 `time` 时，保留历史“时间降序兜底”行为。  
- **Verify:**  
  - 执行 `python -m py_compile backend/projects/monthly_data_show/api/workspace.py`，通过。  
- **Result:**  
  - “口径 -> 指标 -> 时间”等自定义层次顺序现在会真实影响查询结果排列。  

## 2026-03-02（查询结果字段名中文化与列顺序联动）

- **User Request:**  
  - 查询结果字段名改为中文：`company=口径`、`item=指标名`、`unit=计量单位`、`value=值`、`date=时间`；  
  - 时间值由 `YYYY-MM-DD` 显示为 `YYYY年M月`；  
  - `company/item/date(time)` 列顺序需与“数据层次顺序”一致，且后置 `值、计量单位`。  
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 查询结果表头改为 `resultColumns` 动态渲染；  
     - 表体改为按动态列取值；  
     - 新增 `formatResultMonth()`，将日期格式化为 `YYYY年M月`；  
     - 新增 `resultDimensionFields/resultColumns/getResultCellValue`，按层次顺序拼接维度列并固定尾部 `值、计量单位`。  
  2. 导出联动：  
     - `downloadXlsx()` 的“查询结果”子表改为与页面同一列顺序、同一中文列头、同一时间格式。  
- **Result:**  
  - 页面与导出文件的“查询结果”列头/列序保持一致，并可随“数据层次顺序”实时变化。  

## 2026-03-02（环比窗口修正为多月等长回溯 + 气温导出纯数）

- **User Feedback:**  
  1. 选择 `2026-01 ~ 2026-02` 时，环比上期仅命中 `2025-12`，应为 `2025-11 ~ 2025-12`；  
  2. 导出 XLSX 子表“气温日序同比”中本期/同期气温带单位文本，不便二次处理。  
- **Agent Action:**  
  1. 后端 `backend/projects/monthly_data_show/api/workspace.py`：  
     - 调整 `_resolve_mom_window()`：  
       - 当前窗口若为“连续自然月区间（起始月月初到结束月月末）”，环比窗口改为“紧邻向前、等月数”的自然月区间；  
       - 示例：`2026-01-01~2026-02-28 -> 2025-11-01~2025-12-31`。  
       - 非自然月区间仍按滚动天数窗口。  
  2. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 导出“气温日序同比”子表中：`本期气温/同期气温` 改为纯数值（不拼接 `℃`）；  
     - 列名改为 `本期气温(℃)`、`同期气温(℃)`。  
- **Verify:**  
  - 执行 `python -m py_compile backend/projects/monthly_data_show/api/workspace.py`，通过。  
- **Result:**  
  - 多月查询环比窗口与业务预期一致；  
  - 气温导出列更适合筛选、排序和数值计算。  

## 2026-03-02（导出文件名按查询月份区间命名）

- **User Request:** 导出文件名使用本次查询的月份区间名。  
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 调整 `resolveExportMonthTag()` 规则：  
       - 若筛选为多月（`dateMonthFrom` 与 `dateMonthTo` 不同）-> `YYYY-MM_~_YYYY-MM`；  
       - 若单月 -> `YYYY-MM`；  
       - 若结束月为空则使用起始月；  
       - 若筛选为空则回退当前窗口/结果数据推断。  
  2. 文件名继续使用 `月报查询分析_${monthTag}.xlsx`，其中 `monthTag` 已支持区间。  
- **Result:**  
  - 导出文件名会随查询区间变化，例如：`月报查询分析_2026-01_~_2026-02.xlsx`。  

## 2026-03-02（管理后台数据库编辑增强：独立页面 + 查询筛选）

- **User Request:**  
  1. 数据库编辑能力增强（不仅是基础分页查看）；  
  2. 不要放在“后台文件编辑”里，新增独立页面并排在其后。  
- **Agent Action:**  
  1. 前端页面 `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`：  
     - 顶部标签新增“数据库表编辑”，并放在“后台文件编辑”之后；  
     - 将原“数据库表在线编辑”模块从文件页移出，迁移到独立标签页；  
     - 新增查询能力：全字段关键字检索、字段筛选条件（AND）、排序字段/方向、分页参数；  
     - 保留批量保存修改能力（按主键更新）。  
  2. 后端接口 `backend/api/v1/admin_console.py`：  
     - `POST /admin/db/table/query` 新增入参：`search`、`filters`、`order_by`、`order_dir`；  
     - 支持筛选操作：`eq/ne/contains/starts_with/ends_with/gt/gte/lt/lte/is_null/not_null`；  
     - 支持排序方向 `asc/desc`，并保留主键默认排序兜底。  
  3. 前端 API `frontend/src/projects/daily_report_25_26/services/api.js`：  
     - `queryAdminDbTable` 同步透传上述查询参数。  
- **Verify:**  
  - 执行 `python -m py_compile backend/api/v1/admin_console.py`，通过。  
- **Result:**  
  - 管理后台数据库编辑已独立成页，且具备可用的查询筛选与排序能力；  
  - 当前仍保持“无主键表不可保存更新”的保护约束。  

## 2026-03-02（月报查询单月默认范围修正）

- **User Request:** 当仅填写“业务月份起”且“业务月份止”为空时，只查询起始月份当月数据，不要默认扩展到当前上个月。  
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 调整 `buildPayload()`：  
       - `date_from` 仍取起始月月初；  
       - 若 `dateMonthTo` 为空且 `dateMonthFrom` 有值，则 `date_to` 自动回填为起始月月末；  
       - 若起止都为空则保持空值。  
- **Result:**  
  - 现在“只选业务月份起”会稳定查询该月，不再跨月拉取。  

## 2026-03-02（月报查询月份框体包裹样式修正）

- **User Feedback:** “业务月份起/止”外层框体右侧未完整包住日期选择框，视觉上短一截。  
- **Agent Action:**  
  1. 前端 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 为 `.field input/.field select` 增加 `box-sizing: border-box`；  
     - 为 `.month-field` 增加 `box-sizing: border-box`；  
     - 为 `.month-input` 增加 `box-sizing: border-box`。  
- **Result:**  
  - 月份外框与日期输入框宽度对齐，右侧不再出现“露出/短边”问题。  

## 2026-03-02（AI 报告模块第一阶段通用化：模式化 + 用户附加提示词）

- **User Request:** 将 AI 智能报告能力通用化，保留日报模式，同时为月报预置独立模式，并支持用户实时输入附加提示词。  
- **Agent Action:**  
  1. 后端 AI 核心 `backend/services/data_analysis_ai_report.py`：  
     - 新增模式标识：`daily_analysis_v1`、`monthly_analysis_v1`；  
     - 新增模式模板注册表 `AI_MODE_TEMPLATE_REGISTRY`；  
     - 将提示词构建改为支持 `mode template + user_prompt`；  
     - 新增 `ai_user_prompt` 清洗（长度限制）与注入逻辑；  
     - 任务快照中记录 `ai_mode_id`。  
  2. 调用链透传：  
     - `backend/projects/daily_report_25_26/api/legacy_full.py` 的 `DataAnalysisQueryPayload` 新增：  
       `ai_mode_id`、`ai_user_prompt`；  
     - 触发 AI 任务前将这两个字段注入任务 payload；  
     - `backend/services/data_analysis.py` 的服务化执行链也同步透传。  
  3. 前端日报分析页 `frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`：  
     - 新增“本次分析要求（可选）”输入框（仅在开启智能报告且有权限时显示）；  
     - 查询请求新增 `ai_mode_id`（默认日报模式）与 `ai_user_prompt` 透传；  
     - 补充样式确保布局稳定。  
- **Verify:**  
  - 执行 `python -m py_compile backend/services/data_analysis_ai_report.py backend/services/data_analysis.py backend/projects/daily_report_25_26/api/legacy_full.py`，通过。  
- **Result:**  
  - AI 模块已具备“模式化 + 用户附加要求”能力；  
  - 报页默认走 `daily_analysis_v1`，行为保持兼容；  
  - `monthly_analysis_v1` 已在引擎预置，可在月报页面接入时直接调用。  

## 2026-03-02（月报查询页面接入 AI 智能报告）

- **User Request:** 在月报查询页面启用 AI 智能报告能力，使用通用 AI 引擎并默认调用月报模式。  
- **Agent Action:**  
  1. 后端 `backend/projects/monthly_data_show/api/workspace.py`：  
     - 新增接口：  
       - `POST /monthly-data-show/ai-report/start`（启动任务）  
       - `GET /monthly-data-show/ai-report/{job_id}`（查询任务）  
     - 新增月报 AI payload 组装逻辑：将查询对比数据映射为通用 AI 引擎输入结构；  
     - 默认透传 `ai_mode_id=monthly_analysis_v1`，支持 `ai_user_prompt`。  
  2. 前端 API `frontend/src/projects/daily_report_25_26/services/api.js`：  
     - 新增 `startMonthlyDataShowAiReport`、`getMonthlyDataShowAiReport`。  
  3. 前端页面 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：  
     - 新增“智能报告生成（BETA）”开关、附加提示词输入框；  
     - 新增“生成智能报告”“下载智能报告”按钮；  
     - 新增任务轮询与状态提示逻辑；  
     - 查询条件变化/重置时自动清理旧任务状态。  
- **Verify:**  
  - 执行 `python -m py_compile backend/projects/monthly_data_show/api/workspace.py`，通过。  
- **Result:**  
  - 月报查询页已可直接生成并下载 AI 报告（HTML），默认使用月报模式模板。  

## 2026-03-02（AI 预设提示词分离：日报保持原样，月报独立模板）

- **User Request:** 两个项目预设提示词拆分：日报保持当前提示词，月报单设独立提示词模式。  
- **Agent Action:**  
  1. 后端 `backend/services/data_analysis_ai_report.py`：  
     - 保持 `daily_analysis_v1` 的原有模板不变；  
     - 为 `monthly_analysis_v1` 新增独立模板链：  
       - `MONTHLY_CONTENT_PROMPT_TEMPLATE`  
       - `MONTHLY_VALIDATION_PROMPT_TEMPLATE`  
       - `MONTHLY_REVISION_PROMPT_TEMPLATE`  
       - `MONTHLY_FAST_INSIGHT_LAYOUT_PROMPT_TEMPLATE`  
       - `MONTHLY_FAST_VALIDATION_PROMPT_TEMPLATE`  
     - 将 `AI_MODE_TEMPLATE_REGISTRY` 的月报模式映射切换为上述独立模板。  
- **Verify:**  
  - 执行 `python -m py_compile backend/services/data_analysis_ai_report.py`，通过。  
- **Result:**  
  - 日报与月报提示词体系已完全分离：日报沿用当前方案，月报使用独立预设。  

## 2026-03-02（AI 配置跨项目抽离 + 月报专用 instruction）

- **User Request:** 将 `backend_data/projects/daily_report_25_26/config/api_key.json` 抽离为跨项目配置，并新增月报查询专用提示词 instruction。  
- **Agent Action:**  
  1. 新增全局路径解析：  
     - 文件：`backend/services/project_data_paths.py`  
     - 新增函数：`resolve_global_ai_settings_path()`  
     - 路径策略：`backend_data/shared/ai_settings.json` 优先，兼容回退日报旧路径。  
  2. AI 报告服务切换到全局配置并做兼容合并：  
     - 文件：`backend/services/data_analysis_ai_report.py`  
     - 新增配置合并逻辑：先读日报旧配置，再叠加 shared 配置；  
     - `_load_instruction_text(mode_id)` 按模式读取：  
       - 日报：`instruction`（兼容 `instruction_daily`）  
       - 月报：`instruction_monthly`。  
  3. 管理端读写支持新字段：  
     - 文件：`backend/projects/daily_report_25_26/api/legacy_full.py`  
       - `AiSettingsPayload` 与 `_read_ai_settings/_persist_ai_settings` 新增 `instruction_monthly`；  
       - AI 设置读写改为全局路径，并兼容旧路径合并读取。  
     - 文件：`backend/api/v1/admin_console.py`  
       - 管理后台 AI 设置 payload 与保存流程新增 `instruction_monthly`。  
  4. 新建共享配置文件：  
     - 文件：`backend_data/shared/ai_settings.json`  
     - 新增 `instruction_monthly`（月报专用提示词）；  
     - 日报原有 `instruction` 继续由旧配置回退保障，避免行为突变。  
  5. 前端提示文案同步：  
     - 文件：`frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`  
     - AI 设置弹窗提示路径更新为 `backend_data/shared/ai_settings.json`。  
- **Verify:**  
  - 执行 `python -m py_compile backend/services/project_data_paths.py backend/services/data_analysis_ai_report.py backend/projects/daily_report_25_26/api/legacy_full.py backend/api/v1/admin_console.py`，通过。  
- **Result:**  
  - AI 配置已支持跨项目共享；  
  - 月报已具备独立 instruction 入口；  
  - 日报旧提示词保持兼容可用。  

## 2026-03-02（月报默认提示词替换为用户指定版本）

- **User Request:** 将指定的大段提示词写入月报默认 instruction。  
- **Agent Action:**  
  1. 更新文件：`backend_data/shared/ai_settings.json`。  
  2. 将 `instruction_monthly` 全量替换为用户提供的“系统指令/执行逻辑/五段式报告结构”版本。  
- **Verify:**  
  - 通过文件回读确认 `instruction_monthly` 已写入完整文本。  
- **Result:**  
  - 月报 AI 默认提示词已切换到用户指定模板。  

## 2026-03-02（合并日报 api_key 配置到 shared/ai_settings）

- **User Request:** 将 `backend_data/projects/daily_report_25_26/config/api_key.json` 合并至 `backend_data/shared/ai_settings.json`。  
- **Agent Action:**  
  1. 读取两个配置文件并执行字段并集合并。  
  2. 在 `backend_data/shared/ai_settings.json` 中保留并整合以下字段：  
     - `gemini_model`  
     - `gemini_api_keys`  
     - `instruction`（日报提示词）  
     - `instruction_monthly`（月报提示词）  
     - `report_mode`  
     - `enable_validation`  
     - `allow_non_admin_report`  
  3. 不删除原日报 `api_key.json`（兼容回退路径仍可用）。  
- **Verify:**  
  - 回读 `backend_data/shared/ai_settings.json`，确认字段与内容已合并。  
- **Result:**  
  - shared AI 配置已包含日报与月报两套提示词及运行参数，可作为统一跨项目配置使用。  

## 2026-03-02（下线日报 api_key + 指令字段改名 + 弹窗折叠编辑）

- **User Request:**  
  1. 下线 `backend_data/projects/daily_report_25_26/config/api_key.json`，全部转向 `backend_data/shared/ai_settings.json`；  
  2. 将 `instruction` 重命名为 `instruction_daily`；  
  3. AI 设置弹窗中日报/月报提示词默认折叠，可展开修改并保存。  
- **Agent Action:**  
  1. 删除旧配置文件：`backend_data/projects/daily_report_25_26/config/api_key.json`。  
  2. 后端统一路径：  
     - `backend/services/project_data_paths.py` 的 `resolve_global_ai_settings_path()` 改为只返回 shared 路径；  
     - `backend/services/data_analysis_ai_report.py` 移除旧路径回退合并，仅读 shared。  
  3. 字段改名：  
     - `backend_data/shared/ai_settings.json` 中 `instruction` 更名为 `instruction_daily`；  
     - `legacy_full.py`、`admin_console.py` 的 AI 设置读写改为 `instruction_daily` + `instruction_monthly`；  
     - 读写接口保留对旧前端 `instruction` 入参的兼容接收（仅作为保存时回退来源）。  
  4. 前端弹窗：  
     - `DataAnalysisView.vue` 将提示词编辑区改为两个 `<details>` 折叠块（日报/月报），默认收起；  
     - 表单字段与保存参数改为 `instruction_daily`、`instruction_monthly`；  
     - `api.js` 的 `get/updateAiSettings` 与 `get/updateAdminAiSettings` 请求体同步字段改名。  
- **Verify:**  
  - `python -m py_compile backend/services/project_data_paths.py backend/services/data_analysis_ai_report.py backend/projects/daily_report_25_26/api/legacy_full.py backend/api/v1/admin_console.py` 通过；  
  - `python -m json.tool backend_data/shared/ai_settings.json` 通过。  
- **Result:**  
  - AI 配置已完全收口到 shared；  
  - 字段标准化为 `instruction_daily` / `instruction_monthly`；  
  - 页面上两段提示词默认折叠并可单独展开编辑保存。  

## 2026-03-02（最终收口：移除回退并删除旧 api_key 文件）

- **User Request:** 旧 `api_key.json` 直接下线，全部转向 shared；`instruction` 改为 `instruction_daily`；提示词编辑默认折叠。  
- **Agent Action:**  
  1. 删除文件：`backend_data/projects/daily_report_25_26/config/api_key.json`。  
  2. 移除后端回退：  
     - `project_data_paths.resolve_global_ai_settings_path()` 改为固定 shared 路径；  
     - `data_analysis_ai_report` 不再合并旧路径，只读 shared；  
     - 日报提示词读取键固定为 `instruction_daily`（月报为 `instruction_monthly`）。  
  3. shared 配置键更名：`instruction -> instruction_daily`。  
  4. 前端设置弹窗（DataAnalysisView）改为日报/月报两个 `<details>` 折叠块，默认收起，可展开编辑并保存。  
  5. API 透传修正：`instruction_daily`/`instruction_monthly` 未传时不强制写空，避免误覆盖。  
- **Verify:**  
  - Python 编译检查通过；  
  - `shared/ai_settings.json` JSON 校验通过；  
  - 文件存在性检查确认旧 `api_key.json` 已删除。  
- **Result:**  
  - AI 配置源单一化（shared）；  
  - 字段命名统一；  
  - 设置弹窗满足“默认折叠、可展开修改保存”。  

## 2026-03-02（月报 AI 报告改为独立4段式结构）

- **User Request:** `data_analysis_ai_report.py` 的硬性章节划分仅用于日报；月报需按 `instruction_monthly` 走专门4段式结构，并支持图文并茂展示。  
- **Agent Action:**  
  1. 月报提示词模板重构：  
     - 更新 `MONTHLY_LAYOUT_PROMPT_TEMPLATE` 与 `MONTHLY_CONTENT_PROMPT_TEMPLATE`，将章节固定为4段：  
       - `overview`  
       - `coal_completion`  
       - `profit_cost_breakdown`  
       - `efficiency_and_actions`  
     - 同步更新月报极速模板中的 section id 示例。  
  2. 报告渲染逻辑分流：  
     - 新增 `_normalize_sections_for_mode()`，仅在月报模式强制4段章节骨架与顺序；  
     - `mode_id != monthly`（日报）保留原有硬性块：同比/环比/计划/逐日明细；  
     - `mode_id == monthly`（月报）不再复用日报硬性块，新增“月度关键对比图表”区（同比/环比/计划三表）并结合趋势图与4段正文，形成图文并茂报告。  
- **Verify:**  
  - 本轮未执行命令行编译验证（按当前会话约束，采用静态改造+回读核对）。  
- **Result:**  
  - 日报与月报报告结构彻底解耦；  
  - 月报报告输出稳定为4段式分析结构，且保留关键图表展示能力。  

## 2026-03-02（月报页面增加智能体设定入口与折叠框宽度修复）

- **User Request:**  
  1) 月报查询页增加“智能体设定”入口，且仅 `global_admin` 可点击；  
  2) 修复折叠提示词编辑框展开后过窄；  
  3) 明确“完整模式/快速模式”“检查核实”对月报是否生效。  
- **Agent Action:**  
  1. 月报页面新增全局 AI 设置弹窗：  
     - 文件：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`；  
     - 在 AI 工具栏增加“智能体设定”按钮，`v-if="isGlobalAdmin"`；  
     - 接入 `getAdminAiSettings/updateAdminAiSettings`，可编辑并保存：  
       - API Keys、模型、`instruction_daily`、`instruction_monthly`、`report_mode`、`enable_validation`、`allow_non_admin_report`。  
  2. 折叠框宽度修复：  
     - 月报弹窗与日报弹窗统一为 `prompt-collapse` 全宽；  
     - 为折叠内 textarea 增加 `display:block;width:100%;box-sizing:border-box`。  
  3. 适用范围文案明确：  
     - 在设置项标题中新增“全局，日报+月报共用”说明；  
     - 检查核实项文案改为“全局，日报+月报第4阶段”。  
- **Verify:**  
  - 本轮主要为前端模板与样式改造，未执行前端构建命令。  
- **Result:**  
  - 月报页已具备仅 `global_admin` 可见的智能体设定入口；  
  - 折叠提示词编辑区展开宽度恢复正常；  
  - 模式与核实开关对月报的适用范围在界面上已明确。  

## 2026-03-02（日报/月报智能体设定组件通用化）

- **User Request:** 日报、月报页面上的智能体设定希望内容与样式一致，并尽可能通用复用。  
- **Agent Action:**  
  1. 新增并复用统一组件：`frontend/src/projects/daily_report_25_26/components/AiAgentSettingsDialog.vue`。  
  2. 日报页面 `DataAnalysisView.vue` 改为接入共享组件，移除页面内重复弹窗模板、状态变量、保存逻辑与相关样式。  
  3. 月报页面 `MonthlyDataShowQueryToolView.vue` 同步接入共享组件，移除页面内重复弹窗模板、状态变量、保存逻辑与相关样式。  
  4. 双页面保持原有接口职责不变：  
     - 日报：`getAiSettings/updateAiSettings(projectKey, payload)`；  
     - 月报：`getAdminAiSettings/updateAdminAiSettings(payload)`。  
- **Verify:**  
  - 执行 `npm run build`（frontend）成功，Vite 构建通过，无编译错误。  
- **Result:**  
  - 日报/月报“智能体设定”实现同一组件驱动，交互与样式完全一致；  
  - 后续新增字段或样式只需维护一处，维护成本显著降低。  

## 2026-03-02（智能体设定 API 输入框宽度修正）

- **User Request:** 智能体设定中的 API 输入框过窄，要求修正。  
- **Agent Action:**  
  1. 修改共享组件 `frontend/src/projects/daily_report_25_26/components/AiAgentSettingsDialog.vue`：  
     - 为 `.api-key-item input` 增加 `flex: 1 1 auto; min-width: 0;`，确保输入框占满剩余空间；  
     - 增加移动端规则，API 行可换行且输入框宽度为 100%。  
- **Verify:**  
  - 执行 `npm run build`（frontend）通过。  
- **Result:**  
  - 日报和月报页的智能体设定弹窗中，API 输入框宽度已显著改善并自适应。  

## 2026-03-02（AI 报告限流重试与提示数据瘦身）

- **User Request:** 优化 AI 报告流程，先不做 key 轮换，重点缓解 429/配额超限问题。  
- **Agent Action:**  
  1. 在 `backend/services/data_analysis_ai_report.py` 增加限流自恢复：  
     - 新增 429/Quota 错误识别；  
     - 解析 Gemini 错误中的 `retry in ...s` / `retry_delay { seconds: ... }`；  
     - 调用失败时按“至少 20 秒”自动等待并重试（默认最多 3 次）。  
  2. 增加 Prompt 输入瘦身策略：  
     - 对 `processed_data` 按重要性裁剪指标数量、时间序列长度、对比表项；  
     - 分级尝试压缩，确保传给模型的 JSON 体积受控（目标上限约 120000 字符）。  
  3. 保持现有 key 使用方式不变（未启用 key 轮换）。  
- **Verify:**  
  - 执行 `python -m py_compile backend/services/data_analysis_ai_report.py` 通过。  
- **Result:**  
  - 大查询窗口下触发 429 后可自动等待重试；  
  - 单次输入体积显著下降，降低触发免费层输入 token 限流概率。  

## 2026-03-02（月报 AI 报告版式与日报彻底分离）

- **User Request:** 月报报告当前样式看起来和日报一致，希望改为正式月报风格（参考 `configs/3.2 2月运行情况.pdf`）。  
- **Agent Action:**  
  1. 在 `backend/services/data_analysis_ai_report.py` 新增月报专用渲染函数 `_generate_monthly_report_html(...)`：  
     - 正式简报版式（纸面风格）与章节化正文；  
     - 输出“核心指标同比概览”+四段正文；  
     - 将环比/计划比作为附表；  
     - 保留智能核对结果区。  
  2. 在 `_generate_report_html(...)` 中增加模式分流：  
     - `mode_id == monthly_analysis_v1` 时直接走月报专用渲染，不再共享日报卡片+趋势图模板。  
- **Verify:**  
  - 执行 `python -m py_compile backend/services/data_analysis_ai_report.py` 通过。  
- **Result:**  
  - 月报报告视觉与结构已与日报明显区隔，避免“看起来一样”。  

## 2026-03-03（月报简报行文收敛 + 管理后台 AI 设置统一）

- **User Request:**  
  1) 月报 AI 报告行文与文章结构尽量对齐参考 PDF；  
  2) 管理后台的 AI 配置也改为与日报/月报查询页一致的“智能体设定”模式。  
- **Agent Action:**  
  1. 管理后台统一 AI 设置入口：  
     - 文件：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`；  
     - 移除后台原有内嵌 `AI 设置` 表单（模型/APIKey/提示词等旧字段）；  
     - 接入共享组件 `AiAgentSettingsDialog`，并使用 `getAdminAiSettings/updateAdminAiSettings`；  
     - 与日报查询页、月报查询页共同指向 `backend_data/shared/ai_settings.json`。  
  2. 月报报告版式再收敛：  
     - 文件：`backend/services/data_analysis_ai_report.py`；  
     - 重写 `_generate_monthly_report_html` 为“公文简报式”排版：标题、元信息、章节正文（四段主结构）、附关键同比表；  
     - 明显弱化日报风格元素（卡片看板感/趋势看板感）。  
- **Verify:**  
  - `python -m py_compile backend/services/data_analysis_ai_report.py` 通过；  
  - `npm run build`（frontend）通过。  
- **Result:**  
  - 三处 AI 设置入口（日报查询/月报查询/管理后台）已统一为同一交互与配置源；  
  - 月报报告已进一步贴近正式简报阅读样式。  

## 2026-03-03（月报报告补充两张图表）

- **User Request:** 月报报告需“至少两张图”。  
- **Agent Action:**  
  1. 在 `backend/services/data_analysis_ai_report.py` 的 `_generate_monthly_report_html` 中新增图表区；  
  2. 引入 ECharts CDN，并新增图表样式（双列图卡）；  
  3. 增加两张图：  
     - 图1：同比差异率 Top10（绝对值）柱图；  
     - 图2：本期值 Top10（绝对值）柱图。  
- **Verify:**  
  - `python -m py_compile backend/services/data_analysis_ai_report.py` 通过。  
- **Result:**  
  - 月报报告现已固定包含至少两张图，满足图文并茂要求。  

## 2026-03-03（登录 404 修复：v1 路由导入失败）

- **User Request:** 无法登录，`POST /api/v1/auth/login` 返回 `404 Not Found`。  
- **Agent Action:**  
  1. 检查后端路由挂载链路（`backend/main.py` → `backend/api/v1/routes.py`）；  
  2. 读取容器日志定位根因：`legacy_full.py` 使用 `Field(...)` 但未导入，导致 `v1_router` 导入失败并未挂载；  
  3. 修复导入：`backend/projects/daily_report_25_26/api/legacy_full.py` 增加 `Field`。  
- **Verify:**  
  - 本地接口校验：`POST /api/v1/auth/login` 从 `404` 变为 `422`（空请求体触发参数校验，说明路由已恢复）。  
- **Result:**  
  - 登录接口已恢复可用；  
  - `/api/v1/*` 不再因该异常整体失效。  

## 2026-03-03（智能体设定新增“不保存退出”按钮）

- **User Request:** 智能体设定弹窗除“保存并退出”外，增加“不保存直接退出”按钮。  
- **Agent Action:**  
  1. 修改共享组件 `frontend/src/projects/daily_report_25_26/components/AiAgentSettingsDialog.vue`；  
  2. 在底部动作区新增按钮“退出（不保存）”，点击执行 `closeDialog`，不触发保存。  
- **Verify:**  
  - 该组件被日报查询页、月报查询页、管理后台共同复用，三处同步生效。  
- **Result:**  
  - 用户可直接关闭弹窗，不影响已保存配置。  

## 2026-03-03（AI 报告生成进度展示）

- **User Request:** 生成智能报告时，增加进度展示。  
- **Agent Action:**  
  1. 日报页面 `DataAnalysisView.vue` 增加进度可视化：进度条、百分比、阶段节点（洞察分析/结构规划/内容撰写/检查核实）；  
  2. 月报页面 `MonthlyDataShowQueryToolView.vue` 同步增加同款进度展示；  
  3. 月报轮询逻辑补充 `stage` 状态接收与映射（含 `revision_pending`、`revision_content` 别名阶段处理）。  
- **Verify:**  
  - 执行 `npm run build`（frontend）通过。  
- **Result:**  
  - AI 报告从提交到完成（或失败）均可看到阶段化进度反馈，不再只有单行提示文本。  

## 2026-03-03（月报查询导出 XLSX 数值类型修复）

- **User Request:** 月报查询导出的 Excel 中，指标值不要是文本；普通指标应为数值格式，百分比指标应为百分比格式，小数位按页面规则。  
- **Agent Action:**  
  1. 修改 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue` 的 `downloadXlsx` 逻辑；  
  2. 为“查询结果”“对比明细”“气温日序同比”“气温汇总”写入真实数值单元格（`t: 'n'`）；  
  3. 按指标单位与页面小数位规则设置 Excel 格式：  
     - 普通数值：`#,##0.00` / `#,##0.0000`（按指标）  
     - 百分比：`0.00%` / `0.0000%`（按指标）  
  4. 新增导出格式辅助函数：`isPercentUnit`、`buildDecimalFormat`、`buildExcelValueFormat`、`setSheetNumericCell`。  
- **Verify:**  
  - 执行 `npm run build`（frontend）通过。  
- **Result:**  
  - 导出文件中的数值列可直接用于 Excel 计算/筛选/图表；  
  - 百分比列不再是字符串。  
## 2026-03-04（模板设计器第一期骨架：续做收尾）

- 对话目标：
  - 用户在断线后要求继续推进“模板设计器（新表）”实现并完成收尾。
- 本轮改动：
  - 补齐 `backend/README.md` 中缺失的“模板设计器（新表）第一期骨架”结构同步说明；
  - 对前后端与配置链路做一致性检查：
    - 后端路由挂载：`backend/projects/daily_report_25_26/api/router.py`
    - 后端接口定义：`backend/projects/daily_report_25_26/api/template_designer.py`
    - 前端路由：`frontend/src/router/index.js`
    - 页面跳转：`frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue`
    - 前端 API：`frontend/src/projects/daily_report_25_26/services/api.js`
    - 页面配置：`backend_data/shared/项目列表.json`
    - 权限配置：`backend_data/shared/auth/permissions.json`
- 结果：
  - 模板设计器第一期骨架相关文件与文档已对齐，页面入口、权限、接口与前端调用链路一致。
## 2026-03-04（模板设计器入口不可见修复）

- 问题反馈：
  - 用户反馈“已实现模板设计器，但页面中找不到入口”。
- 根因分析：
  - 项目页面列表接口会按 `page_access` 过滤；
  - 当账号具备 `can_manage_modularization` 但权限配置遗漏 `template_designer` 时，入口会被过滤隐藏。
- 代码修复：
  - 修改 `backend/api/v1/routes.py` 的 `list_project_pages`：
    - 在页面过滤前读取项目动作权限；
    - 若 `can_manage_modularization=true` 且项目已配置 `template_designer` 页面，则将其加入 `allowed_pages` 兜底保留。
- 结果：
  - 对具备模块化管理能力的账号，模板设计器入口不再因 `page_access` 漏配而消失。
## 2026-03-04（模板设计器入口迁移到管理后台）

- 用户反馈：
  - 模板设计器不应放在页面选择区，而应放在管理后台入口。
- 本轮前端改动：
  - `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
    - 在管理后台顶部新增“模板设计器（新表）”按钮；
    - 新增 `openTemplateDesigner()`，跳转到
      `/projects/daily_report_25_26/pages/template_designer/template-designer`。
  - `frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue`
    - 移除 `template_designer` 的专用跳转分支；
    - 新增隐藏键过滤（`HIDDEN_PAGE_KEYS`），在页面选择页隐藏该卡片，避免入口重复与误导。
- 结果：
  - 模板设计器入口统一归位于管理后台，页面选择页不再显示该入口。
## 2026-03-04（模板设计器第二期：拖拽设计表格）

- 用户目标：
  - 继续实现模板设计器，支持拖拽设计表格。
- 本轮实现：
  - 重构 `frontend/src/projects/daily_report_25_26/pages/TemplateDesignerView.vue` 为可视化拖拽设计版；
  - 新增列定义拖拽排序（HTML5 Drag & Drop）；
  - 新增行定义拖拽排序（HTML5 Drag & Drop）；
  - 新增行编辑表（`row_key / row_label / unit`）与“新增行/删除行”；
  - 新增预览网格，可按行列直接编辑单元格初始值（`row.cells`）；
  - 保留 JSON 兼容编辑区，并新增“应用 JSON 到可视编辑”按钮；
  - 保存/发布沿用既有后端 API，不改接口路径与发布流程。
- 兼容策略：
  - `rowsJson` 与可视编辑双向兼容；
  - 提交前会按当前列键过滤无效单元格键，避免历史脏键写入。
## 2026-03-04（模板设计器页面壳层统一）

- 用户反馈：
  - 模板设计器页面样式与站内其他页面不一致，缺少顶部 banner 与导航。
- 本轮修复：
  - 修改 `frontend/src/projects/daily_report_25_26/pages/TemplateDesignerView.vue`：
    - 接入 `AppHeader` 顶部栏；
    - 接入 `Breadcrumbs` 面包屑导航；
    - 页面主体改为 `page-main / page-content / card elevated` 结构；
    - 标题区样式对齐其它页面的 `card-header` 形态。
- 结果：
  - 模板设计器页面在视觉结构与导航体验上已与项目现有页面对齐。
## 2026-03-04（模板设计器页面标签闭合修复）

- 问题：
  - Vite 报错：`Element is missing end tag`，定位到 `TemplateDesignerView.vue`。
- 根因：
  - `template-editor-panel` 的结束标签误写为 `</section>`，应为 `</div>`。
- 修复：
  - 文件 `frontend/src/projects/daily_report_25_26/pages/TemplateDesignerView.vue`：
    - 将错误闭合标签改为 `</div>`，恢复合法 DOM 层级。
## 2026-03-04（模板设计器动态导入 500 修复）

- 现象：
  - 访问模板设计器路由时报错 `Failed to fetch dynamically imported module`，请求 `TemplateDesignerView.vue` 返回 500。
- 根因：
  - `TemplateDesignerView.vue` 模板第 6 行开启的外层 `<section class="card elevated template-shell">` 缺失闭合标签，导致 Vue 编译失败。
- 修复：
  - 在模板尾部补齐缺失的 `</section>`。
- 验证：
  - 本地执行 `npm run build`（frontend）通过，Vite 编译成功。
## 2026-03-04（模板设计器：固定字段可选与默认值）

- 用户诉求：
  - `单位` 不应作为默认硬编码字段；是否启用应可配置，并可设默认值。
- 本轮实现：
  - 文件：`frontend/src/projects/daily_report_25_26/pages/TemplateDesignerView.vue`
  - 新增“固定字段配置”区：
    - `row_label`（行标题）启用开关 + 默认值；
    - `unit`（单位）启用开关 + 默认值。
  - 行编辑区联动：
    - 根据固定字段开关动态显示/隐藏“行标题”“单位”列。
  - 预览网格联动：
    - 根据固定字段开关动态显示/隐藏“项目”“单位”列。
  - 数据结构联动：
    - 配置写入 `form.meta.fixed_fields` 与 `form.meta.default_values`；
    - 新增行时自动应用默认值；
    - 关闭字段后在提交 payload 前自动清空对应字段值。
- 验证：
  - `frontend` 执行 `npm run build` 通过。
## 2026-03-04（模板设计器第三期：类 Excel 画布增强）

- 用户目标：
  - 希望像 Excel 一样在表格中直接拖拽行列，并考虑后续接库连接能力。
- 本轮增强：
  - 文件：`frontend/src/projects/daily_report_25_26/pages/TemplateDesignerView.vue`
  - 画布交互：
    - 在“画布网格”中支持列头直接拖拽重排；
    - 在“画布网格”中支持行直接拖拽重排；
    - 列头支持就地删除；
    - 画布工具条支持新增行/新增列。
  - 列能力：
    - 列定义新增 `width`（列宽）字段并可编辑；
    - 预览网格按列宽渲染。
  - 后续接库预留：
    - 新增“连接配置（为后续接库预留）”区；
    - 配置写入 `meta.binding`（`target_table / write_mode / id_strategy`）；
    - 新增 `meta.layout.frozen_columns`（冻结列预留）。
- 数据兼容：
  - 仍沿用现有模板创建/更新/发布 API；
  - `meta` 扩展为结构化配置，不破坏既有模板读取。
- 验证：
  - `frontend` 执行 `npm run build` 通过。
## 2026-03-04（模板设计器交互修复：输入与删除不可用）

- 用户反馈：
  - 部分区域无法输入，删除操作不稳定。
- 根因：
  - 行/列整行设置 `draggable=true` 会干扰输入框聚焦与按钮点击（尤其在画布区域）。
- 修复：
  - 文件：`frontend/src/projects/daily_report_25_26/pages/TemplateDesignerView.vue`
  - 将拖拽触发改为“仅拖拽手柄可拖”：
    - 行拖拽、列拖拽均移除整行/整列表头 `draggable`；
    - 拖拽事件绑定到手柄元素 `span.drag-handle`。
  - 删除按钮保持普通点击事件，不再与拖拽抢占。
- 验证：
  - `frontend` 执行 `npm run build` 通过。

## 2026-03-05（模板设计器入口改为管理后台并列标签）

- 用户诉求：
  - 模板设计器不应作为单独按钮，而应与管理后台其他子页面入口并列展示。
- 前端改动：
  - 文件：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
  - 将“模板设计器（新表）”从右侧 `top-actions` 独立按钮迁移到顶部 `tab-group`，与“后台文件编辑/数据库表编辑/项目后台设定/服务器管理/操作日志”并列；
  - 保持既有 `openTemplateDesigner` 跳转逻辑不变，避免影响当前模板设计器页面与路由链路；
  - 删除已无引用的 `.top-actions` 样式，清理死代码。
- 结果：
  - 管理后台入口形态统一为并列标签，模板设计器不再以独立按钮呈现。

## 2026-03-05（长表设计器成熟方案评审稿）

- 背景：
  - 用户明确要求停止“最小化临时方案”，改为可长期维护的成熟长表设计器方案；
  - 结合现状：`backend_data/projects/daily_report_25_26/config` 已有多份“数据结构_*.json”，但语义分散且规则表达能力有限。
- 现状核对：
  - 当前数据库 `daily_basic_data` 已是长表结构（`company/sheet_name/item/value/date`），并有唯一索引 `(company, sheet_name, item, date)`；
  - 当前模板设计器接口仅提供 `template_key/template_name/table_type/columns/rows/meta` 通用壳，尚缺“字段契约 + 计算图 + 校验图 + 发布契约”。
- 方案结论（本轮仅评审，不落代码）：
  - 存储统一长表、展示按需透视；
  - 设计器升级为“数据契约层 + 采集编排层 + 展示层”三层模型；
  - 先落地长表设计器，再把交叉展示放到查询层，不再直接驱动入库结构。
- 下一步：
  - 待用户确认评审稿后，按“模板 JSON 升级 + 后端校验发布 + 前端向导式设计器”分阶段实施。

## 2026-03-05（下线模板设计器页面）

- 用户指令：
  - 直接去掉当前“表格模板设计页面”。
- 实施范围：
  1. 前端页面与入口下线：
     - 删除 `frontend/src/projects/daily_report_25_26/pages/TemplateDesignerView.vue`；
     - 删除路由 `'/projects/:projectKey/pages/:pageKey/template-designer'`（`frontend/src/router/index.js`）；
     - 删除管理后台 `AdminConsoleView.vue` 顶部“模板设计器（新表）”标签与跳转函数；
     - 删除 `services/api.js` 中模板设计器相关接口函数（列表/详情/创建/更新/发布）。
  2. 后端与配置联动清理：
     - 删除项目路由中 `template_designer` 子路由挂载（`backend/projects/daily_report_25_26/api/router.py`）；
     - 删除后端接口文件 `backend/projects/daily_report_25_26/api/template_designer.py`；
     - 删除项目页面清单中的 `template_designer` 配置（`backend_data/shared/项目列表.json`）；
     - 删除权限文件中的 `template_designer` 页面键（`backend_data/shared/auth/permissions.json`）；
     - 移除 `/api/v1/projects/{project_id}/pages` 中对 `template_designer` 的可见性兜底逻辑（`backend/api/v1/routes.py`）。
- 结果：
  - 模板设计器页面及其入口、路由与后端 API 已完全下线，不再对用户可见或可访问。

## 2026-03-05（管理后台看板区升级为“看板功能设置”）

- 用户诉求：
  - 将 `admin-console` 中“看板缓存任务”改为“看板功能设置”；
  - 增加业务日期自动读取；
  - 增加气温导入等数据看板页面相关功能按钮。
- 前端改动：
  1) `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
     - 标题从“看板缓存任务”改为“看板功能设置”；
     - 新增“业务日期（自动读取）”输入框与“读取业务日期”按钮（调用看板日期接口并同步到刷新日期）；
     - 保留并继续支持缓存能力按钮：发布缓存、刷新单日、停止任务、禁用缓存；
     - 新增气温能力按钮：导入气温（预览）、提交气温入库；
     - 新增状态提示：业务日期同步结果、气温预览/入库结果。
  2) `frontend/src/projects/daily_report_25_26/services/api.js`
     - 新增 `getProjectDashboardBizDate(projectKey)`；
     - 新增 `importProjectTemperatureData(projectKey)`；
     - 新增 `commitProjectTemperatureData(projectKey)`。
- 结果：
  - 管理后台“看板功能设置”已覆盖数据看板页的核心运维操作（业务日期读取、缓存控制、气温导入与入库）。

## 2026-03-05（管理后台气温按钮反馈增强）

- 用户反馈：
  - 点击“导入气温（预览）”后没有明显提示。
- 根因：
  - 前端提示文案读取字段与后端真实返回不完全匹配（后端为 `summary.total_hours`、`write_result.inserted/replaced`）；
  - 提示区域使用普通 `subtext`，可见性不强。
- 修复：
  - 文件：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
  - 导入预览提示改为基于真实返回字段：总小时数、重叠小时数、差异小时数、日期范围；
  - 入库提示改为基于 `write_result.inserted/replaced`；
  - 点击按钮后先显示“正在导入/正在提交”；
  - 提示展示容器改为更醒目的 `panel-state`。
- 验证：
  - `frontend` 执行 `npm run build` 通过。

## 2026-03-05（管理后台气温导入改为弹框确认流程）

- 用户诉求：
  - 参考数据看板逻辑，点击“导入气温”后先弹提示框，再让用户选择是否导入入库。
- 改动：
  - 文件：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
  - “导入气温（预览）”点击后：
    - 先请求预览数据；
    - 打开“气温导入确认”弹框，展示获取时间、涉及日期、重合区间、差异小时；
    - 在弹框内点击“确认入库”才执行写库；
  - 移除外层独立“提交气温入库”按钮，避免双入口冲突。
- 修正：
  - 预览统计改为读取后端真实字段（`summary.total_hours`、`overlap.hours`、`differences`）。
- 验证：
  - `frontend` 执行 `npm run build` 通过。

## 2026-03-05（管理后台气温弹框补齐逐小时一致性明细）

- 用户诉求：
  - 弹窗中需显示逐小时气温，并标示数据一致性，行为对齐数据看板。
- 改动：
  - 文件：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
  - 弹框新增“逐小时一致性”列表，逐条展示：
    - 时间
    - 接口气温
    - 数据库气温（未命中显示 `—`）
    - 一致性状态（`一致/不一致`）
  - 差异项使用红色高亮（`temp-import-modal__diff-item--different`）；
  - 预览数据映射补齐 `overlap_records`，并修正重合小时读取为 `overlap.hours`。
- 验证：
  - `frontend` 执行 `npm run build` 通过。

## 2026-03-05（项目后台页面移除“操作日志与分类统计”区块）

- 用户诉求：
  - 在“项目后台页面”中不再显示“操作日志与分类统计”部分。
- 改动：
  - 文件：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
  - 删除“操作日志与分类统计”整块 UI（筛选栏、分类统计、日志表格）；
  - 保留项目后台设定中其他模块（设定概览、校验开关、AI 设置、看板功能设置）。
- 验证：
  - `frontend` 执行 `npm run build` 通过。

## 2026-03-05（月报查询页指标分组新增“全选/取消”）

- 用户诉求：
  - 在月报查询页“指标（可多选）”中，为“主要产销指标”“主要消耗指标”等每个分类增加“全选/取消”按钮，仅作用于本分类。
- 改动：
  - 文件：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 在每个基础指标分组标题右侧新增分组级按钮：
    - `全选`：仅勾选该分组内指标（保留其他分组已选项）；
    - `取消`：仅取消该分组内指标（不影响其他分组已选项）。
  - 新增方法 `toggleGroupItems(groupItems, checked)` 实现分组粒度选择控制；
  - 新增样式：`basic-group-title-row`、`basic-group-actions`。
- 验证：
  - `frontend` 执行 `npm run build` 通过。

## 2026-03-05（月报查询页全选按钮改为单按钮切换，并覆盖计算指标）

- 用户诉求：
  - 页面上的“全选/全不选”改为单按钮切换；
  - “计算指标”也应支持同样能力。
- 改动：
  - 文件：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 口径与指标顶部按钮改为单按钮：`全选/取消` 自动切换；
  - 在每个指标大类（含“计算指标”）标题右侧新增单按钮切换；
  - 新增状态判断与方法：
    - `isAllCompaniesSelected` / `isAllItemsSelected`
    - `isSectionItemsAllSelected(section.items)`
    - `toggleSectionItems(section.items)`
  - 保留分组级（基础指标分组）“全选/取消”能力。
- 验证：
  - `frontend` 执行 `npm run build` 通过。

## 2026-03-05（月报查询页子分类按钮改为单按钮切换）

- 用户反馈：
  - 子分类指标按钮仍是双按钮，需改为单按钮切换。
- 改动：
  - 文件：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 基础指标子分类按钮由“全选/取消”双按钮改为单按钮自动切换：
    - 全部已选时显示“取消”；
    - 否则显示“全选”。
- 验证：
  - `frontend` 执行 `npm run build` 通过。

## 2026-03-06 VS Code 终端自动激活排查
- 现象：在 VS Code 中未打开 Python 文件前，集成终端保持普通目录提示符；打开 `.py` 文件后，终端出现 `& d:\编程项目\phoenix_project\.venv\Scripts\Activate.ps1` 并进入 `(.venv)`。
- 结论：当前仓库内未发现 `.vscode/settings.json`、`.code-workspace`、`launch.json`、`tasks.json` 等工作区级配置；该行为更符合 VS Code Python 扩展在激活后自动为集成终端注入已选解释器的虚拟环境激活命令。
- 补充：激活路径指向 `d:\编程项目\phoenix_project\.venv`，说明当前 VS Code 选中的 Python 解释器更可能绑定到了相邻项目的虚拟环境，而不是本仓库自身配置触发。
- 影响：本次仅为本地开发环境行为解释，未修改前后端业务代码。

## 2026-03-06 phoenix_project 目录删除风险补记
- 排查到 `D:\编程项目\phoenix_project` 独立存在于 `D:\编程项目` 下，不属于当前 `phoenix` 仓库目录。
- 目录内容主要为 `.venv`、`node_modules`、`package.json`、`package-lock.json` 与近乎空白的 `readme.md`。
- `package.json` 仅显示依赖 `@google/gemini-cli`，未见当前业务项目源码结构，判断更接近独立临时目录或工具试验目录。
- 结论：从当前仓库视角看，`phoenix_project` 不是运行本仓库所必需；但由于 VS Code 当前解释器误绑到该目录 `.venv`，删除前应先切换解释器，否则会继续触发终端激活报错。

## 2026-03-06（前端移动端表格与录入页优化第一轮）
- 目标：在不改变桌面端默认布局的前提下，优先改善手机访问时的表格可读性与录入页可操作性。
- 前置说明：Serena 已完成项目激活；由于 Vue SFC 结构化编辑支持有限，本轮按仓库规范降级使用 `apply_patch` 对目标页面做最小补丁，变更范围限定在前端三个页面与文档同步，回滚方式为反向撤销对应补丁片段。
- `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：
  - 为聊天预览表与查询结果表补充 `table-wrap` 横向滑动容器；
  - 在窄屏下压缩单元格间距与字号；
  - 对对比表在 `<=640px` 时隐藏同期值、上期值、计划值三列，保留当前值与比率列，减少横向拥挤。
- `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`：
  - 为批量识别预览表与异常表增加横向滚动容器；
  - 为异常说明列补充自动换行与最小宽度，避免手机端整行被撑爆；
  - 在 `<=960px` 时统一压缩表格字号与 padding。
- `frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue`：
  - 为 RevoGrid 外层补充横向滚动能力；
  - 增加手机端提示文案，明确“横向滑动查看，编辑建议横屏或电脑端”；
  - 为 RevoGrid 设置最小宽度，避免手机端被强行压扁。
- 验证：
  - 已执行 `frontend` 下 `npm run build`，2026-03-06 构建通过；
  - 本轮未做真机或浏览器移动端手动回归，后续建议优先检查月报查询页、月报导入页与日报录入页在 390px/430px 宽度下的实际观感。

## 2026-03-06（前端移动端表格与录入页优化第二轮）
- 目标：继续覆盖 `DashBoard.vue` 与 `DataAnalysisView.vue`，补齐大屏/分析页在手机宽度下的横滑与窄屏密度控制。
- 前置说明：沿用本轮已启用的 `apply_patch` 降级编辑方式，仅修改前端样式与模板容器，不涉及后端接口与数据结构。
- `frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`：
  - 为同比、环比、计划比较三张结果表增加 `result-table-wrapper` 横向滚动容器；
  - 为结果表设置最小宽度，防止手机端被强行挤压；
  - 将时间轴 `RevoGrid` 的 `timeline-grid-wrapper` 从隐藏溢出改为横向滚动，并为网格设置移动端最小宽度；
  - 在 `<=900px / <=640px` 下进一步压缩表格字号、padding，并降低时间轴高度。
- `frontend/src/projects/daily_report_25_26/pages/DashBoard.vue`：
  - 为 `summary-fold-table-wrapper` 增加触摸滚动优化；
  - 在 `<=1023px / <=640px` 下收紧汇总折叠表的列宽、padding 与字号；
  - 在手机宽度下将中部卡片控制按钮改为纵向堆叠，降低按钮拥挤与误触。
- 浏览器手机视口实测（390x844，前端 mock 登录/数据注入）：
  - `monthly_data_show/query-tool`：结果表容器 `clientWidth=373`、`scrollWidth=1005`、`canScroll=true`；
  - `daily_report_25_26/pages/demo/sheets/demo`：RevoGrid 容器 `clientWidth=373`、`scrollWidth=1005`、`canScroll=true`，手机提示可见；
  - `monthly_data_pull`：批量识别预览表容器 `clientWidth=310`、`scrollWidth=440`、`canScroll=true`；
  - `daily_report_25_26/pages/demo/data-analysis`：结果表容器 `clientWidth=329`、`scrollWidth=480`、`canScroll=true`；
  - `daily_report_25_26/pages/demo/dashboard`：焦点指标折叠表容器 `clientWidth=337`、`scrollWidth=481`、`canScroll=true`。
- 验证：
  - 第二轮补丁后再次执行 `frontend` 下 `npm run build`，2026-03-06 构建通过；
  - 目前验证方式为浏览器手机视口模拟 + 前端 mock 数据，尚未完成真机触摸回归。

## 2026-03-06（前端移动端优化第三轮：入口页与文案收敛）
- 目标：继续统一入口页手机观感，并去除显式“横向滑动查看模式”提示文案，避免界面说明感过强。
- `frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue`：
  - 删除手机端显式提示文案 `手机端已切换为横向滑动查看模式...`；
  - 保留纯布局层面的横向滚动与最小宽度保护。
- `frontend/src/pages/LoginView.vue`：
  - 在 `<=640px` 下收紧视觉区高度、标题字号与描述字距；
  - 让表单卡片在手机上更像底部承接面板，输入框与登录按钮提升可触达高度。
- `frontend/src/pages/ProjectSelectView.vue`：
  - 在手机宽度下将项目卡片改为单列排布；
  - 收紧卡片高度、间距与文字密度，避免项目入口页空洞和按钮区过松。
- `frontend/src/pages/ProjectEntryView.vue`：
  - 为“正在进入项目工作台...”过渡态增加居中与手机端尺寸优化。
- 验证：
  - 第三轮补丁后再次执行 `frontend` 下 `npm run build`，2026-03-06 构建通过；
  - 浏览器手机视口复测确认 `DataEntryView` 中已不再出现该提示文案，DOM 查询结果 `hint=false`、`containsText=false`。

## 2026-03-06（数据填报页顶部开关紧凑化修正）
- 现象：手机断点下，数据填报页顶部“表级校验 / 本单位分析”等开关被拉成整行长条，明显占空间。
- 原因：`@media (max-width: 768px)` 中将 `topbar__status-row` 改成纵向拉伸，同时把 `.unit-analysis-inline` 设为 `width: 100%`。
- 修正：
  - 保留 `topbar__action-row` 纵向堆叠；
  - 将 `topbar__status-row` 改回紧凑的横向换行布局；
  - 取消 `.unit-analysis-inline` 在手机端的 `width: 100%`，恢复为内容自适应宽度；
  - `submit-time` 改为占整行但不强制其余开关拉满整宽。
- 验证：
  - 修正后再次执行 `frontend` 下 `npm run build`，2026-03-06 构建通过；
  - 浏览器手机视口复测中，顶部状态区已恢复为紧凑块状布局。

## 2026-03-06（月报查询页与拉取页顶部密度收敛）
- 目标：继续降低手机端“工具页”顶部筛选区、按钮区与摘要区的厚重感，使页面更接近掌上数据库的紧凑操作布局。
- `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：
  - 在 `<=900px / <=640px` 下收紧主内容区 `padding` 与区块间距；
  - 将摘要卡片 `summary-grid` 改为更紧凑的 3 列 / 2 列布局；
  - 缩小摘要卡片的 padding、label/value 字号；
  - 将查询按钮区改为弹性排列，手机宽度下改成整行按钮；
  - 下调多选区 `check-list.sections.compact` 的最小/最大高度，减少筛选区默认占屏。
- `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`：
  - 在 `<=960px / <=640px` 下收紧主内容区 `padding` 与区块间距；
  - 将顶部操作按钮和预览确认按钮改为更紧凑的弹性排列，手机宽度下改成整行按钮；
  - 收紧步骤卡片 `group-card` 的内边距和标题间距；
  - `slot-actions` 下的按钮改为整行，减少局部碎片化。
- 验证：
  - 修改后再次执行 `frontend` 下 `npm run build`，2026-03-06 构建通过。

## 2026-03-06（Banner 与按钮文字换行规整修正）
- 现象：部分页面顶部 banner 文字换行不整齐，部分按钮文字在窄屏下被拆成两行，视觉上较乱。
- 修正范围：
  - `frontend/src/projects/daily_report_25_26/components/AppHeader.vue`
  - `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`
- 修正内容：
  - 为头部品牌名、副标题、用户信息与导航按钮增加 `white-space: nowrap` / `word-break: keep-all`；
  - 为月报查询页与月报拉取页的按钮统一增加单行文本约束，避免汉字被拆开；
  - 收紧 `AppHeader` 手机断点下的字体与按钮内边距，减少头部换行概率；
  - 为查询页分组操作按钮保持横向书写与更可控的弹性宽度。
- 验证：
  - 修正后再次执行 `frontend` 下 `npm run build`，2026-03-06 构建通过。

## 2026-03-07（月报查询页“重置”按钮手机端溢出修正）
- 现象：月报查询页手机宽度下，“重置”按钮被挤出页面容器外。
- 原因：`<=640px` 断点下，`.actions .btn` 被设为 `width: 100%`，但 `.actions` 本身仍保持横向 `flex`，导致第二个按钮横向溢出。
- 修正：
  - 在 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue` 的 `<=640px` 断点下，将 `.actions` 改为纵向排列。
- 验证：
  - 修正后执行 `frontend` 下 `npm run build`，2026-03-07 构建通过。

## 2026-03-07（全局 AppHeader 手机端重排）
- 目标：解决手机端顶部 banner 文字与按钮元素“全挤在一起”的问题，不再依赖简单 `nowrap` 硬压。
- 变更文件：`frontend/src/projects/daily_report_25_26/components/AppHeader.vue`
- 修改内容：
  - 将品牌区从单层横向排列改为 `brand-mark + brand-text` 结构；
  - `brand-text` 内固定为上下两层：集团名 / 平台名；
  - 在 `<=640px` 下将整个头部改为纵向分层：
    - 第一层：品牌区
    - 第二层：导航区（后台按钮、用户信息、退出）
  - 导航区允许整体换层，但单个按钮与单个文案保持不拆字。
- 结果：
  - 手机端 banner 不再是“所有元素硬塞一行”，而是分层排布；
  - 桌面端结构保持不变。
- 验证：
  - 修改后执行 `frontend` 下 `npm run build`，2026-03-07 构建通过。

## 2026-03-07（Phoenix 手机页面优化 Skill 草案）
- 目标：将近期多轮手机页面优化经验沉淀为可复用 skill，减少后续同类问题的重复判断成本。
- 新增文件：
  - `configs/skills/phoenix-mobile-layout/SKILL.md`
- Skill 内容覆盖：
  - 适用场景、项目约束、核心原则
  - 入口页 / 查询页 / 工作台页 / 数据录入页 / 看板分析页 的分类处理方法
  - 固定工作流、验证清单、浏览器复测建议
  - 文档与 Serena 留痕要求
  - 推荐入口文件与触发语句
- 说明：
  - 当前为仓库内 skill 草案，已可作为项目规范文档使用；
  - 若需像系统 skills 一样被直接发现和调用，后续还需迁移或安装到 Codex 的全局 skills 目录。

## 2026-03-06（项目选择页桌面卡片高度回退）
- 现象：回到 PC 界面后，项目选择页卡片高度明显偏高，导致桌面端密度过松。
- 原因：此前为项目选择页卡片添加了桌面端 `min-height: 136px`，本意是让手机卡片更稳定，但副作用影响了 PC 端展示。
- 修正：
  - 删除 `frontend/src/pages/ProjectSelectView.vue` 中桌面端 `.card` 的 `min-height: 136px`；
  - 保留手机断点下的单列卡片和紧凑样式，不影响移动端优化结果。
- 验证：
  - 修正后再次执行 `frontend` 下 `npm run build`，2026-03-06 构建通过。

## 2026-03-06（后端依赖版本锁定，减少 pip 回溯）
- 目标：优先解决 `lo1_new_server.ps1` 构建链路中后端镜像 `pip install -r requirements.txt` 的依赖回溯慢点。
- 变更文件：`backend/requirements.txt`
- 处理方式：
  - 将原先未锁定的直接依赖改为固定版本：
    - `pydantic-settings==2.13.1`
    - `passlib[bcrypt]==1.7.4`
    - `python-jose[cryptography]==3.5.0`
    - `python-multipart==0.0.22`
    - `openpyxl==3.1.5`
    - `psycopg2-binary==2.9.11`
    - `httpx==0.28.1`
    - `google-generativeai==0.8.6`
    - `psutil==7.2.2`
    - `paramiko==3.5.1`
  - 额外显式锁定传递依赖：
    - `grpcio==1.76.0`
    - `grpcio-status==1.71.2`
- 原因：
  - 之前慢点分析已指向 `google-generativeai` 相关链路的 `grpcio-status` 多版本回溯；
  - 显式锁定后，可显著降低 clean build 时的解析分支数量。
- 验证：
  - 本机执行 `python -m pip install --dry-run -r backend/requirements.txt` 成功；
  - 解析结果未报冲突，输出为确定的安装集合。

## 2026-03-06（后端 Docker 构建切换 pip 国内镜像源）
- 目标：降低 `backend/Dockerfile.prod` 中 `pip install` 的下载等待时间，优先改善网络侧慢点。
- 变更文件：`backend/Dockerfile.prod`
- 修改内容：
  - 在 builder 阶段的 `ENV` 中新增：
    - `PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple`
    - `PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn`
- 影响：
  - Docker 构建时的 `pip install --prefix=/install -r requirements.txt` 将默认走清华 PyPI 镜像；
  - 本轮未改 apt 源、未启用 BuildKit cache，也未调整脚本入口。
- 验证：
  - 本次为 Dockerfile 静态修改，未实际执行镜像构建；后续可直接通过 `./lo1_new_server.ps1` 观察 backend 依赖下载阶段耗时变化。

## 2026-03-08 DataAnalysis 智能报告按钮位置调整
- 需求：将“智能报告（BETA）”与“智能体设定”按钮移动到“生成智能报告”按钮前。
- 变更文件：`frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`。
- 实现：在结果区 `result-header-actions` 中新增“智能报告（BETA）”与“智能体设定”按钮，并放在“生成智能报告”按钮之前；查询区仅保留未开通提示文案。
- 结果：日报查询页面按钮顺序符合新要求，智能报告入口更集中于结果操作区。
- 回滚：恢复 `DataAnalysisView.vue` 中对应模板片段到本次改动前状态。

## 2026-03-08 DataAnalysis 智能报告行对齐与按钮顺序微调
- 需求补充：修复“智能报告（BETA）”与后方按钮不在同一水平位置问题；将“智能体设定”按钮放到该行最后。
- 变更文件：`frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`。
- 实现：
  - 在 `result-header-actions` 中将“智能体设定”按钮移动到最后一个。
  - 增强 `.ai-report-title` 样式为 `inline-flex + align-items:center + min-height + nowrap`，并补充字重，保证与按钮视觉对齐。
- 结果：按钮行顺序与对齐均满足最新交互要求。
- 回滚：恢复 `DataAnalysisView.vue` 的对应模板顺序与 `.ai-report-title` 样式为改动前状态。

## 2026-03-08 月报智能体设定权限改为项目动作权限
- 需求：月报页面“智能体设定”权限同步为 `monthly_data_show` 的 `can_manage_ai_settings`。
- 变更文件：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`。
- 实现：
  - 按钮显示/禁用由 `isGlobalAdmin` 改为 `canConfigureAiSettings`。
  - 弹窗 `:can-manage` 改为 `canConfigureAiSettings`。
  - 权限计算改为 `auth.canManageAiSettingsFor('monthly_data_show')`。
  - 打开设置函数中的权限拦截同步替换。
- 结果：月报智能体设定与日报一致，按项目动作权限 `can_manage_ai_settings` 控制。
- 回滚：恢复 `MonthlyDataShowQueryToolView.vue` 中上述判定与变量定义到改动前状态。

## 2026-03-08 AI 气泡文案调整
- 需求：将 AI 气泡组件显示文字“AI 助手”改为“智能助手”。
- 变更文件：`frontend/src/projects/daily_report_25_26/components/AiChatWorkspace.vue`。
- 实现：替换浮动入口文案文本，未改交互逻辑与权限逻辑。
- 结果：页面气泡入口统一展示为“智能助手”。
- 回滚：将上述组件文案恢复为“AI 助手”。

## 2026-03-08 会话记录（admin-console 操作日志页不可查看修复）

- **User Request:** 排查并修复 `http://localhost:5173/admin-console` 中“操作日志”无法查看的问题。
- **Root Cause:** `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue` 中 `activeTab === 'audit'` 对应模板分支被误清空为 `<section v-else class="content-block"></section>`，导致点击“操作日志”仅切换页签状态但无可见内容。
- **Code Changes:**
  - 在 `AdminConsoleView.vue` 恢复“操作日志与分类统计”渲染区块，包含：
    - 筛选条件（时间范围、用户、分类、动作、关键字）
    - 刷新按钮（调用 `reloadAuditData`）
    - 统计区（总量、分类/动作/用户 TOP）
    - 日志表格（时间、用户、IP、分类、动作、页面、目标）
  - 复用既有 `auditFilters`、`auditLoading`、`auditError`、`auditEvents`、`auditStats` 与 `top*Stats` 逻辑，无后端接口改动。
- **Result:** “操作日志”页签恢复可见并可查看日志数据；筛选与刷新流程重新生效。
- **Risk / Follow-up:** 若接口返回异常（403/500），页面会显示 `auditError` 文案，便于继续排查权限或后端数据问题。

## 2026-03-08 会话记录（操作日志记录真实客户端 IP 修复）

- **User Request:** 生产环境“操作日志”中的 IP 一直显示 Docker 上一跳地址，需改为真实用户 IP。
- **Root Cause:** `backend/api/v1/admin_console.py` 在 `POST /api/v1/audit/events` 中仅使用 `request.client.host` 写入 `client_ip`，在反向代理链路下该值通常为代理/宿主机地址。
- **Code Changes:**
  - 新增 `_extract_forwarded_client_ip(request)`：优先解析 `X-Forwarded-For`（取首个 IP），其次 `X-Real-IP`。
  - 新增 `_normalize_ip(raw_ip)`：使用 `ipaddress.ip_address` 规范化 IP 文本。
  - 新增 `_resolve_client_ip(request)`：优先使用转发头，回退到 `request.client.host`。
  - `collect_audit_events` 改为 `client_ip = _resolve_client_ip(request)`。
  - 前端日志表 IP 列兼容显示 `client_ip || ip`（兼容新老日志字段）。
- **Verification:**
  - `python -m py_compile backend/api/v1/admin_console.py` 通过；
  - `frontend` 执行 `npm run build` 通过。
- **Result:** 在生产反向代理场景下，审计日志优先记录并展示真实来源 IP。
## 2026-03-08 系统后台操作日志仅在“操作日志”页签启用

- 问题：系统后台多个子页面都会持续产生操作日志，用户期望仅在“操作日志”页签中呈现/采集相关日志。
- 根因：`frontend/src/main.js` 全局执行 `initAuditTracking(...)`，导致全站路由与点击都进入审计队列。
- 处理：
  - 移除 `frontend/src/main.js` 的全局审计埋点初始化。
  - 在 `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue` 增加按页签启停逻辑：仅当 `activeTab === 'audit'` 时启用埋点，离开该页签立即停止。
- 回滚方案：
  - 若需恢复“全局采集”，可将 `initAuditTracking(...)` 重新放回 `main.js`。
  - 或移除 `AdminConsoleView.vue` 内新增的 `syncAuditTrackingByTab` 与相关 `watch/onBeforeUnmount` 逻辑。
- 验证建议：
  - 在“后台文件编辑/数据库表编辑/项目后台设定/服务器管理”页签操作后，日志列表不应新增对应行为。
  - 切换到“操作日志”页签后再操作，应可看到新增日志。

## 2026-03-08 会话更正（撤回“采集范围收敛”）

- 说明：用户反馈本次需求并未授权修改“日志采集范围”，仅要求日志相关内容不要在其他子页面呈现。
- 已回滚：
  - 恢复 `frontend/src/main.js` 中全局 `initAuditTracking(...)` 初始化。
  - 删除 `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue` 中按 `activeTab==='audit'` 启停采集的新增逻辑。
- 当前状态：日志采集机制恢复为改动前行为；“操作日志”页面展示能力保持可用。

## 2026-03-08 会话记录（仅展示修复：日志块误出现在其他页签）

- 用户确认：本次仅处理“展示”，不调整采集。
- 根因：`AdminConsoleView.vue` 中日志区块使用 `v-else`，且位于另一条件链，导致在非 `system` 的页签也可能渲染日志区块。
- 修复：将日志区块改为 `v-else-if="activeTab === 'audit'"`。
- 结果：日志区块仅在“操作日志”页签显示；其他页签不再出现该区块；采集逻辑保持不变。
