# daily_report_25_26 后端说明

## 平台名称展示微调说明（2026-03-10）
- 本轮继续调整前端展示文案：登录页副标题、浏览器页签标题，以及登录后顶部 banner 的平台简称均已按最新口径更新。
- 该调整仍仅影响前端显示层，不涉及后端接口、鉴权、路由或数据库结构变更。

## 登录页命名同步说明（2026-03-10）
- 本轮仅调整前端登录页与站点标题文案，不涉及后端接口、鉴权逻辑或配置结构变更。
- 平台对外名称已改为“大连洁净能源集团 生产经营数据智算平台”；登录页底部版权年份同步改为 `2025-2026`。
- 后端现阶段无需迁移或兼容处理，接口与数据结构保持不变。

## 月报导入工作台补充（2026-03-10）

- 本轮 `monthly_data_show/import-workspace` 新增的“步骤 3.2：标准表比对”未增加后端 API。
- 当前比对完全在前端基于步骤 3.1 导出的对照 CSV 本地执行，因此后端既有 `extract-csv`、`import-csv`、查询接口与数据库写入逻辑均保持不变。
- 既有步骤 3 导出仍继续输出 `item_transform_type`、`item_transform_note` 两列，供步骤 3.1 / 3.2 复用；步骤 4 入库仍忽略这两列。

## 事故记录补充（2026-03-09）

- 本轮按用户要求新增独立文档：`configs/3.9 docker故障记录.md`。
- 该文档集中整理了本次 Docker 网络异常、容器间访问异常、旧 network id 残留等证据链，后续可直接供运维专家接手。

## 登录 504 排障记录（2026-03-09）

- 登录接口入口：
  - `POST /api/v1/auth/login`
  - `GET /api/v1/auth/me`
  - `POST /api/v1/auth/logout`
- 登录核心逻辑位于 `backend/services/auth_manager.py`：
  - `login(...)` 负责读取账号配置、校验用户名密码、生成会话；
  - 当 `remember_me=true` 时，会调用 `_persist_session(...)` 将会话写入 PostgreSQL `auth_sessions` 表。
- 本地验证结果：
  - `phoenix_backend` 健康检查 `/healthz` 正常返回 `200`；
  - `/api/v1/auth/me` 无令牌时正常返回 `401`；
  - 本地后端日志中可见登录接口返回 `200 OK`。
- 因此 2026-03-09 线上 `504 Gateway time-out` 更接近部署层异常，而非此处认证接口代码直接报错。
- 服务器排查时需重点检查：
  - `web -> backend` 容器网络连通性；
  - `backend -> db` 连接是否阻塞；
  - `auth_sessions` 持久化表初始化/写入是否因数据库状态异常而卡住。
- 2026-03-09 服务器新增实测：
  - `phoenix-web` 日志报错为 `upstream timed out ... while connecting to upstream`；
  - upstream 目标是 `http://172.19.0.3:8000/api/v1/auth/login`；
  - `phoenix-backend` 日志为空。
- 这意味着：
  - Nginx 已拿到 `backend` 容器 IP，但 TCP 连接 `172.19.0.3:8000` 阶段就超时；
  - 请求尚未进入 FastAPI 路由层；
  - 当前优先怀疑 `phoenix-backend` 容器内部没有真正监听 8000，或 `uvicorn` 只保留父进程而子进程未成功启动。
- 第二轮实测修正（2026-03-09）：
  - `docker top phoenix-backend`、`docker logs phoenix-backend` 与容器内 Python 自检均确认：
    - Uvicorn 已成功启动；
    - `0.0.0.0:8000` 已建立监听；
    - `127.0.0.1:8000/healthz` 正常返回。
- 因而当前最终判断为：
  - 后端应用本身可用；
  - 故障位于 Docker 生产网络内 `phoenix-web -> phoenix-backend` 的容器间访问链路，而非认证接口代码本身。
- 第三轮服务器操作补充（2026-03-09）：
  - 停掉容器后 `25-26_phoenix_net` 已自动消失，`docker network rm` 报 `not found` 属于预期；
  - 后续应直接重建生产 compose 栈，而非继续手工删除同名网络。
- 第四轮服务器观察修正（2026-03-09）：
  - `docker ps` 为空而 `25-26_phoenix_net` 仍存在，并不矛盾；
  - 该网络属于 compose 创建的用户自定义 bridge，停止容器并不会自动删除，需要 `docker compose down` 或显式 `docker network rm`。
- 后续进展（2026-03-09）：
  - 经 `docker network inspect` 确认旧网络存在 IPAM 脏状态后，用户已成功删除 `25-26_phoenix_net`；
  - 当前应重新拉起 Phoenix 栈，验证新建网络下 `phoenix-web -> phoenix-backend` 是否恢复正常。

## 最新结构与状态（2026-02-28）

- 日报分析页智能报告触发逻辑改造联动（2026-03-08）：
  - 本轮无后端接口新增，仅前端调用时机调整。
  - 日报分析页现在在查询阶段固定传 `request_ai_report=false`，在用户点击“生成智能报告”时单独发起 `request_ai_report=true` 请求。
  - 后端仍复用既有接口：`POST /api/v1/projects/daily_report_25_26/data_analysis/query`。

- 月报查询页 query-options 500 修复（2026-03-08）：
  - 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - 接口：`GET /api/v1/projects/monthly_data_show/monthly-data-show/query-options`
  - 修复策略：
    - 指标配置刷新异常时降级，不中断请求；
    - 数据库读取异常时返回空筛选项；
    - 指标排序异常时回退原始 items；
    - AI 设置读取异常时回退 `show_chat_bubble=true`。
  - 目标：将接口行为从“异常即 500”调整为“异常可降级返回”，保证前端页面可进入。

- 月报查询页 CORS 问题前端侧规避联动（2026-03-08）：
  - 本轮无后端代码改动。
  - 前端已在本机开发环境下优先走同源 `/api/v1` 代理，避免浏览器直接跨域请求 `127.0.0.1:8001` 时触发 CORS 拦截。
  - 后端接口契约不变。

- AI 气泡开关刷新回弹兜底修复联动（2026-03-08）：
  - 本轮无后端代码改动。
  - 前端页面初始化已增加“主动读取 AI 设置并覆盖气泡开关”的兜底策略，确保刷新后显示状态以 `show_chat_bubble` 实时值为准。
  - 目的：规避 `schema/query-options` 标志链路与全局 AI 设置链路可能短时不一致造成的回弹。

- AI 气泡开关刷新后回弹修复联动（2026-03-08）：
  - 本轮仍无后端代码改动。
  - 前端已将配置读取接口调整为 `cache: 'no-store'`，避免刷新时读取到旧缓存导致 `show_chat_bubble` 视觉回弹。
  - 后端接口契约不变，继续返回实时设置值。

- AI 气泡显示开关即时生效修复联动（2026-03-08）：
  - 本轮无后端代码改动，接口行为保持不变。
  - 前端已在保存 AI 设置成功后，立即采用后端返回的 `show_chat_bubble` 回写当前页状态，因此无需刷新即可隐藏/显示聊天气泡。
  - 相关接口：
    - `POST /api/v1/projects/daily_report_25_26/data_analysis/ai_settings`
    - `POST /api/v1/admin/ai-settings`

- AI 自由对话气泡缺陷修复联动说明（2026-03-08）：
  - 本次仅前端组件修复，无后端接口与数据结构变更。
  - 现有对话接口保持不变，仍由前端传入 `mode/message/session_id/history/context`：
    - `POST /api/v1/projects/monthly_data_show/monthly-data-show/ai-chat/dialog`
    - `POST /api/v1/projects/daily_report_25_26/data_analysis/ai-chat/dialog`
  - 风险提示：前端在“数据分析模式”新增了上下文构建异常兜底提示；后端无需改造即可兼容。

- 构建慢过程分析同步（2026-03-06）：
  - 本轮为 `lo1_new_server.ps1` 镜像构建性能分析，后端代码未改动；
  - 已定位慢点集中在 `backend/Dockerfile.prod` 的依赖安装层（`pip install -r requirements.txt`）；
  - 根因与建议详见 `configs/progress.md` 对应条目。
- 构建慢过程二次观察同步（2026-03-06）：
  - 新日志显示慢点当前主要位于 `Installing collected packages` 阶段；
  - 结合 `platform: linux/arm64`，判断当前瓶颈以 ARM64 下依赖下载/安装耗时为主，版本回溯已非主导。

- monthly_data_show 对话能力当前为“后端保留、前端隐藏入口”（2026-03-05）：
  - 后端接口 `POST /api/v1/projects/monthly_data_show/monthly-data-show/ai-chat/query` 保留；
  - 本轮未改动后端逻辑，仅在前端 query-tool 页面暂时隐藏对话卡片；
  - 便于后续修复体验问题后直接恢复展示，无需重新接线后端。

- monthly_data_show 对话查询接口升级为“会话化 + 多工具增强”（2026-03-05）：
  - 文件：`backend/projects/monthly_data_show/api/workspace.py`；
  - 路径：`POST /api/v1/projects/monthly_data_show/monthly-data-show/ai-chat/query`；
  - 请求新增：`session_id`（可选）、`enable_web_search`（默认 true）；
  - 响应新增：`session_id`、`web_sources`、`tool_calls.details`；
  - 后端新增会话缓存（TTL 30 分钟），连续轮次会自动继承上下文；
  - 查询结果新增 `aggregate_rows` 聚合工具，输出分组摘要与 TopN 记录；
  - 支持 `search_web_public` 公开联网检索分支，供“最新/政策/搜索”等诉求使用。

- monthly_data_show 新增对话查询接口（2026-03-05）：
  - 文件：`backend/projects/monthly_data_show/api/workspace.py`；
  - 路径：`POST /api/v1/projects/monthly_data_show/monthly-data-show/ai-chat/query`；
  - 能力：接收自然语言问题，合并前端上下文后调度受控工具查询（普通查询/同比环比查询），再调用 AI 生成中文分析结论；
  - 返回字段：`answer`、`tool_calls`、`preview_rows`、`applied_query`，便于前端展示与审计。
- 对话工具调用边界（2026-03-05）：
  - 仅允许复用现有白名单查询函数：`query_month_data_show`、`query_month_data_show_comparison`；
  - 不开放任意 SQL 执行，避免越权查询与不可控输出；
  - 模型调用失败时返回保守兜底文案，保证接口稳定可用。
- AI 聊天上下文全量化与气泡开关（2026-03-07）：
  - `ai_chat_service.py` 的 `query_context` 摘要改为优先保留全量查询结果，再按字符预算裁剪，不再固定只取前若干行；
  - 聊天系统提示词改为固定业务文案，不再自动叠加 `instruction_monthly` / `instruction_daily`；
  - 全局 AI 设置新增 `show_chat_bubble` 字段；
  - 日报 `data_analysis/schema` 与月报 `query-options` 已分别暴露聊天气泡显示标志，供前端控制悬浮聊天入口。
  - 后续修复确认：气泡开关“无法保存”的直接原因是前端保存接口 body 漏传 `show_chat_bubble`，后端持久化逻辑本身可正常处理该字段。

- AI 聊天调试面板布局修复（2026-03-07）：
  - 本轮仅调整前端共享聊天组件的调试信息布局，后端接口无改动；
  - 目标是确保发送消息后仍能直接查看最近错误与最近返回结果。

- AI 聊天前端调试面板（2026-03-07）：
  - 前端共享聊天组件已内置调试信息展示；
  - 页面内可直接查看最近一次聊天请求 payload、响应结果与错误信息，便于和后端 debug 接口配合排查。

- AI 聊天调试接口（2026-03-07）：
  - 为便于分段排查聊天链路，新增 debug 回显接口：
    - `POST /api/v1/projects/daily_report_25_26/data_analysis/ai-chat/debug`
    - `POST /api/v1/projects/monthly_data_show/monthly-data-show/ai-chat/debug`
  - 返回内容包含：
    - 当前 `mode`
    - `provider`
    - `model`
    - `base_url`
    - `history_count`
    - `context_applied`
    - `context_summary`
  - 用于先确认“请求是否进入后端聊天模块”，再继续排查“后端是否能成功调用 new api / gemini”。

- AI 聊天器前端显示修复（2026-03-07）：
  - 本轮仅调整前端共享聊天组件样式，后端接口无改动；
  - 目的：避免超长消息内容撑破悬浮聊天框宽度。

- AI 聊天接口说明补充（2026-03-07）：
  - 新增聊天接口后，前端若出现 `Failed to fetch`，通常表示请求未成功命中新路由，而不是模型 Provider 连接失败；
  - 由于“智能体设定”中的连接测试复用旧接口，即使其测试正常，也不能说明新聊天接口已经被运行中的后端进程加载；
  - 前端开发环境现已优先通过 Vite `/api` 代理访问聊天接口，以便直接看到后端返回的真实错误；
  - 本轮建议：修改后需重启后端服务，以便加载：
    - `POST /api/v1/projects/monthly_data_show/monthly-data-show/ai-chat/dialog`
    - `POST /api/v1/projects/daily_report_25_26/data_analysis/ai-chat/dialog`

- 通用 AI 聊天服务（2026-03-07）：
  - 新增 `backend/services/ai_chat_service.py`，提供：
    - 通用聊天请求/响应模型；
    - 自由聊天 / 基于查询数据聊天 两种模式；
    - 会话存储、历史拼接、查询数据包摘要裁剪、统一 Prompt 组装；
  - 新增页面级聊天接口：
    - 月报查询页：`POST /api/v1/projects/monthly_data_show/monthly-data-show/ai-chat/dialog`
    - 日报分析页：`POST /api/v1/projects/daily_report_25_26/data_analysis/ai-chat/dialog`
  - 该聊天服务底层复用 `backend/services/ai_runtime.py` 的 `call_chat_model(...)`，支持多轮对话结构化消息（System/User/Assistant）。

- AI 架构抽离（2026-03-07）：
  - 原 `backend/services/data_analysis_ai_report.py` 不再承担“通用 AI 核心”定位；
  - 新增 `backend/services/ai_runtime.py`，承载 Provider 配置解析、路径自适应（Docker/本地）、运行时客户端缓存、结构化模型调用（call_chat_model）与连接测试；
  - 新增 `backend/services/ai_report_modes.py`，承载日报/月报模式常量与 Prompt 模板注册表；
  - `data_analysis_ai_report.py` 继续作为日报/月报 AI 报告生成服务存在，但已通过兼容别名层依赖新抽离模块；
  - `monthly_data_show` 的通用模型调用已改为直连 `ai_runtime.call_chat_model(...)`，聊天器已全面基于结构化消息构建。

- AI 设置 Provider 扩展（2026-03-07）：
  - `backend/projects/daily_report_25_26/api/legacy_full.py` 的 AI 设置读写链路新增 `backup_models` 持久化；
  - `AiSettingsPayload` / 全局后台 `admin_console.py` 同步支持 `newapi_backup_models`；
  - 返回给前端的 `providers` 结构现在包含每个 provider 的 `backup_models`，用于“智能体设定”中的备选模型切换。
  - 2026-03-07 后续前端交互补充了“测试当前 provider”和默认折叠卡片，后端接口无需变更，继续复用既有测试能力。
  - 2026-03-07 再次补充 provider 头部“当前生效 / 备用”标记与一键切换，仍为前端交互增强，无需额外接口。
  - 2026-03-07 移除底部全局“测试连接”按钮后，后端仍保留原测试接口，供卡片级测试与批量 New API 测试复用。

- AI 设置多 Provider 升级（2026-03-03）：
 - 模板设计器（新表）第一期骨架（2026-03-04）：
   - 新增后端模块 `projects/daily_report_25_26/api/template_designer.py`，提供模板列表、详情、创建、更新、发布接口；
   - 新增项目内模板存储文件 `backend_data/projects/daily_report_25_26/config/template_designer_templates.json`（不存在时自动初始化）；
   - 在 `projects/daily_report_25_26/api/router.py` 挂载模板设计器路由，路径前缀为 `/template_designer`；
   - 接口访问沿用项目权限体系，校验 `page_access.template_designer` 或动作权限 `can_manage_modularization`；
   - 该能力仅面向未来新增报表模板，不影响既有填报表与既有数据写入链路。
  - 配置结构新增 `providers[] + active_provider_id`，支持多通道并存与切换；
  - 运行时调用与连接测试均可按当前生效 provider 执行；
  - 同时保留 `provider/gemini_*/newapi_*` 旧字段兼容。
- AGENTS 协作规范升级联动（2026-03-04）：
  - 根目录 `AGENTS.md` 已更新为多项目现行规范，后端目录口径明确为 `backend/projects/*` 并行维护；
  - 协作要求继续保持：每轮改动同步 `configs/progress.md`、`frontend/README.md`、`backend/README.md`，并在交付中说明模块/函数/流程/结果。
- 数据看板 PDF 图标导出修复联动（2026-03-04）：
  - 本轮后端代码无新增改动；
  - 前端 `DashBoard.vue` 在导出链路中改为向克隆文档注入内联 SVG 图标，以规避 `html2canvas` 对 `mask-image` 兼容问题；
  - 前端随后补充颜色兼容：导出 SVG 采用计算色值填充，避免 `currentColor` 在截图链路中退化为黑色；
  - 前端进一步将导出图标填充色固定为白色，以彻底规避克隆态颜色漂移；
  - 前端进一步在导出克隆样式中关闭图标容器玻璃态效果（背景/阴影/滤镜/边框），移除 PDF 的方框伪影；
  - 后端接口协议与数据结构保持不变，无需迁移。
- New API 504 超时优化（2026-03-03）：
  - AI 调用层新增 5xx/超时自动退避重试（2 秒，最多一次）；
  - New API 场景下 Prompt 数据上限单独收紧（降低上游超时概率）。
- AI 设置新增连通性测试接口（2026-03-03）：
  - 项目级：`POST /api/v1/projects/{project_key}/data_analysis/ai_settings/test`；
  - 全局后台：`POST /api/v1/admin/ai-settings/test`；
  - 两接口均支持 `gemini/newapi` 按当前输入参数执行最小请求测试。
- New API 网关兼容优化（2026-03-03）：
  - `data_analysis_ai_report.py` 的 New API 请求已补充 `Accept` 与 `User-Agent`；
  - 对 `HTTP 403 + error code 1010` 增加专项报错提示，并输出请求 URL 便于诊断 base_url 配置与网关放行问题。
- AI 服务通道扩展（2026-03-03）：
  - AI 配置新增 `provider`（`gemini/newapi`）；
  - 新增 New API 配置项：`newapi_base_url`、`newapi_api_keys`、`newapi_model`；
  - `backend/services/data_analysis_ai_report.py` 已支持按 provider 分流调用（Gemini SDK / OpenAI-compatible Chat Completions）；
  - 项目级与管理后台 AI 设置接口均已支持读写上述字段并落盘 `backend_data/shared/ai_settings.json`。
- 月报查询排序修复（2026-03-02）：
  - `_merge_and_sort_rows` 已改为严格按 `order_fields` 生成排序键；
  - 自定义“口径/指标/时间”层次顺序会直接反映到查询结果显示顺序。
- 月报查询排序能力增强（2026-03-02）：
  - `monthly_data_show` 查询的 `order_fields` 新增 `time`；
  - 默认排序改为 `time -> company -> item`；
  - 当选择 `time` 时按 `report_month/date` 升序分组（先旧月后新月），满足跨月连续阅读。
- 已完成月报查询表名纠偏（2026-03-02）：
  - `monthly_data_show` 项目运行时 SQL 已从 `month_data_show` 统一切换到 `monthly_data_show`；
  - 导入、查询、对比与筛选项接口均使用新表名；
  - 建表脚本 `backend/sql/month_data_show.sql` 已同步更新为创建 `monthly_data_show`。
- 全局管理后台新增数据库表在线编辑接口（2026-03-01）：
  - `GET /api/v1/admin/db/tables`：读取可用表清单；
  - `POST /api/v1/admin/db/table/query`：分页读取表数据（字段/主键/总数）；
  - `POST /api/v1/admin/db/table/batch-update`：按主键批量保存修改。
  - 实现位置：`backend/api/v1/admin_console.py`（复用 `SessionLocal` 直连业务库）。
- 已修复 `monthly_data_show` 环比窗口错位（2026-03-01）：
  - 原逻辑按“天数平移”计算环比窗口，导致自然月查询（如 2 月）错位到 `1月4日~1月31日`；
  - 新增 `_resolve_mom_window` 后，若当前窗口为自然整月，则环比窗口固定为“上月整月”（如 `2026-01-01~2026-01-31`）；
  - 非整月窗口保持原“同天数平移”规则，兼容已有查询习惯。
- 结构同步说明：本轮仅调整 `monthly_data_pull` 前端页面头部样式（补回统一 banner），后端接口与模块无新增改动。
- 已修复登录跨域预检问题：`backend/main.py` 的 CORS 默认策略改为显式来源白名单（`localhost/127.0.0.1` 常见端口），避免 `allow_credentials=True` 与 `*` 组合导致浏览器拦截。
- 已追加 CORS 二次加固：增加 `allow_origin_regex=^https?://(localhost|127\\.0\\.0\\.1)(:\\d+)?$`，覆盖本机调试端口变化场景。
- 已定位并规避本地端口冲突：外部导表程序占用 `127.0.0.1:8000` 时，Phoenix 通过 `docker-compose.yml` 改为对外 `8001:8000`。
- 已完成外部导表程序接入评估：`外部待导入-导表程序` 为独立 FastAPI + `xlwings` 工具，核心处理链在 `app/core/engine.py`。
- 关键结论：当前后端容器基于 Linux `python:3.12-slim`，不具备 Windows Excel COM 环境，外部程序不可直接按原样上线。
- 可行接入方向（建议）：
  - 保留“映射解析 -> 源值提取 -> 目标写入 -> 差异报告”的业务流程；
  - 将执行内核从 `xlwings` 迁移为容器可运行的 `openpyxl`/纯 Python 链路；
  - 在 `backend/projects/daily_report_25_26/api/` 新增导表路由模块并接入现有项目路由与权限体系（不改现有 `/template` `/submit` `/query` 主链）。
- 现有主链确认：数据填报主逻辑仍在 `backend/projects/daily_report_25_26/api/legacy_full.py`，且 `Coal_inventory_Sheet` 继续走独立提交/查询分支。
- 月报导表新项目骨架已创建：`backend/projects/monthly_data_pull/`。
  - 路由入口：`backend/projects/monthly_data_pull/api/router.py`
  - 初始接口：`GET /api/v1/projects/monthly_data_pull/monthly-data-pull/ping`
  - 目录接口：`GET /api/v1/projects/monthly_data_pull/monthly-data-pull/workspace`
  - 文件工作台接口：
    - `GET /api/v1/projects/monthly_data_pull/monthly-data-pull/files?bucket=...`
    - `POST /api/v1/projects/monthly_data_pull/monthly-data-pull/files/upload?bucket=...`
  - 导表执行接口：
    - `POST /api/v1/projects/monthly_data_pull/monthly-data-pull/analyze-mapping`
    - `POST /api/v1/projects/monthly_data_pull/monthly-data-pull/get-sheets?bucket=...`
    - `POST /api/v1/projects/monthly_data_pull/monthly-data-pull/execute`
    - `GET /api/v1/projects/monthly_data_pull/monthly-data-pull/download/{filename}`
  - 执行引擎：`backend/projects/monthly_data_pull/services/engine.py`（openpyxl 版）
  - 默认目录：`backend_data/projects/monthly_data_pull/{mapping_rules,source_reports,target_templates,outputs}`

## 结构补充（2026-02-28，导表引擎调研）

- 已完成对 LibreOffice Headless 的可行性研判：在当前 Linux 容器体系下可作为 `xlwings` 替代方向。
- 后端接入建议（待实现）：
  - 采用“持久化 UNO 服务（建议 `unoserver`）+ 任务队列”模式进行公式重算与另存；
  - 保持现有数据填报主链不变，新增导表专用 API 模块承接月报导入流程。

## 最新结构与状态（2026-02-08）

- 项目列表来源：`backend_data/shared/项目列表.json`
  - `GET /api/v1/projects` 由 `backend/api/v1/routes.py` 中 `list_projects` 返回项目卡片数据；
  - 当前已增加第二个项目：`mini_project_demo`（迷你项目示例），并已精简为单页面最小配置（无审批、无常量指标配置清单）。
- 新增春节简化日报项目模块：`backend/projects/daily_report_spring_festval_2026/`
  - 路由入口：`api/router.py`；
  - 首个接口：`POST /api/v1/projects/daily_report_spring_festval_2026/spring-festival/extract-json`；
  - 功能：上传 xlsx 后提取 `byDate` JSON（按“本期/同期/差异”列组解析，含合并单元格补全逻辑）。
- 前端目录规范化协同状态：
  - 春节项目页面已迁移到独立目录 `frontend/src/projects/daily_report_spring_festval_2026/`；
  - `daily_report_25_26` 前端模块已迁移至 `frontend/src/projects/daily_report_25_26/`，与春节项目同层管理；
  - 后端接口路径与鉴权方式保持不变，无需调整调用协议。
- 发布缓存日期配置修复（2026-02-11）：
  - 修复 `dashboard_expression._resolve_date_config_path`，日期文件解析顺序改为：
    1) `projects/<project_key>/config/date.json`；2) `shared/date.json`（全局回退）；
  - 解决 `/dashboard/cache/publish` 在模块化目录下误报 `{\"detail\":\"日期配置文件不存在\"}` 的问题。
- 春节迷你看板联调说明（2026-02-11）：
  - 前端迷你看板页温度数据复用 `daily_report_25_26` 的 `/dashboard` 接口读取数据库气温；
  - 春节项目上传解析接口仍为 `/projects/daily_report_spring_festval_2026/spring-festival/extract-json`；
  - 解析接口会将最近一次结果写入 `runtime/spring_festival_latest_extract.json`，并可通过 `GET /spring-festival/latest-json` 回读；
  - 本轮后端接口无新增变更，继续保持与前端迷你看板的数据契约。
- 核心接口主文件：`backend/projects/daily_report_25_26/api/legacy_full.py`
  - 数据填报：`/data_entry/sheets/{sheet_key}/template`、`/submit`、`/query`
  - 数据分析：`/data_analysis/query`、`/data_analysis/ai_report`、`/data_analysis/ai_settings`
  - 仪表盘：`/dashboard`、缓存发布与取消接口
- 目录职责：
  - `backend/api/`：路由与请求编排
  - `backend/services/`：仪表盘表达式、分析服务、认证、缓存任务、天气导入等业务能力
  - `backend/db/`：ORM 模型与会话（`DailyBasicData`、`ConstantData`、`CoalInventoryData` 等）
  - `backend/sql/`：分析视图与数据结构 SQL
  - `backend/schemas/`：鉴权与接口数据模型
- 本次优化状态：
  - 已清理煤炭库存提交链路的重复函数定义，统一到单一生效实现。
  - 已给模板 JSON 读取增加基于文件变更指纹的内存缓存（`mtime_ns + size`），降低重复读取成本。
  - 已统一部分服务模块顶部注释中的数据路径口径：采用 `shared/project` 目录优先并保留旧路径回退说明。
  - 本轮后端无代码变更，仅同步前端 `jsconfig` 修复的联调说明与项目日志。
  - 已新增模块化结构总览文档：`configs/2.8项目模块化.md`（含旧/新结构与路径映射表）。

## 数据看板缓存发布优化（2026-02-08）

- 发布接口支持窗口参数：
  - `POST /dashboard/cache/publish?days=1..30`
  - 默认 `days=7`，可按运维场景缩短为 1 天快速发布。
- 发布任务执行优化：
  - `backend/services/dashboard_cache_job.py` 在单次发布任务内引入 `shared_metrics_cache`，跨日期复用查询结果，减少重复访问 `groups/sum_basic_data` 视图。
- 看板计算优化：
  - `backend/services/dashboard_expression.py` 移除进度回调中的固定 `sleep(0.1)`，降低人为等待。
  - “1.逐小时气温”改为回溯窗口模式：默认最近 7 天（可由配置 `回溯天数` 调整，范围 1~31）+ 预测天数，不再从历史起点全量扫描。

## 项目模块化第一步（2026-02-08）

- 新增路径兼容层：`backend/services/project_data_paths.py`
  - 规则：优先 `DATA_DIRECTORY/projects/<project_key>/{config|runtime}`，不存在则回退旧平铺目录。
- 已接入模块：
  - `backend/api/v1/daily_report_25_26.py`（模板/分析/审批/常量/API Key/调试文件路径）
  - `backend/services/dashboard_expression.py`（看板配置与 `date.json`）
  - `backend/services/dashboard_cache.py`（`dashboard_cache.json`）
  - `backend/services/data_analysis_ai_report.py`（`api_key.json`）
- 兼容策略：
  - 不要求立即迁移 `backend_data` 现有文件；
  - 若新项目目录文件存在则优先读取；否则保持旧路径行为不变。

## 项目模块化第一步增强（2026-02-08）

- shared 全局文件路径已纳入兼容层：
  - 项目列表：`shared/项目列表.json` → 回退 `项目列表.json`
  - 账户信息：`shared/auth/账户信息.json` → 回退 `账户信息.json`
  - 权限配置：`shared/auth/permissions.json` → 回退 `auth/permissions.json`
  - 全局日期：`shared/date.json` → 回退 `date.json`
- 已接入位置：
  - `backend/api/v1/routes.py`
  - `backend/services/auth_manager.py`
  - `backend/api/v1/daily_report_25_26.py`（项目列表扫描）

## 项目模块化过渡工具（2026-02-08）

- 新增迁移工具函数（`backend/services/project_data_paths.py`）：
  - `ensure_project_dirs(project_key)`：创建项目目录骨架；
  - `bootstrap_project_files(project_key, config_files, runtime_files)`：将旧平铺文件复制到新目录（仅复制缺失文件）；
  - `get_project_file_status(project_key, ...)`：返回新旧文件存在状态与路径。
- 新增项目管理接口（系统管理员可用）：
  - `GET /api/v1/projects/daily_report_25_26/project/modularization/status`
  - `POST /api/v1/projects/daily_report_25_26/project/modularization/bootstrap`
- 用途：
  - 先查询状态，再执行一键初始化；执行后可再次查询确认迁移结果。

## 仪表盘缓存控制（2025-12-01）

- 仪表盘缓存逻辑由 `dashboard_cache.py` 迁移至 `dashboard_cache_job.py`，改为后台任务模式以避免前端请求超时。
- 任务执行时通过 `cache_publish_job_manager` 跟踪进度，支持发布（publish）、取消（cancel）与状态查询（status）。
- 发布过程会遍历配置中的所有业务日期（`date.json` 指定的 `set_biz_date` 及前后若干天），逐一调用 `evaluate_dashboard` 并写入缓存。
- 缓存键格式为 `dashboard:daily_report_25_26:<date>`，内容为完整的 JSON 响应包。

## 数据分析页面接口（2025-11-27）

- `POST /data_analysis/query`：核心查询接口。
  - 接收 `unit_key`、`metrics`、`start_date`、`end_date`、`analysis_mode` 等参数。
  - 根据 `unit_key` 自动路由至 `sum_basic_data`（分公司）或 `groups`（集团/主城区）视图。
  - 支持 `daily`（逐日）与 `range`（累计）模式；累计模式下若勾选气温或常量指标，会自动补齐 `timeline` 逐日明细。
  - 返回结构包含 `rows`（汇总行）、`timeline`（明细行，仅累计模式）、`warnings`（缺失或异常提示）。
- `GET /data_analysis/ai_settings` 与 `POST /data_analysis/ai_settings`：
  - 读取/保存 `backend_data/projects/daily_report_25_26/config/api_key.json`（兼容旧平铺路径回退），管理 Gemini API Key、模型名称、Prompt 指令及开关。
  - 支持“验证开关（enable_validation）”与“非管理员权限（allow_non_admin_report）”。
- `POST /data_analysis/ai_report`（异步）：
  - 接收查询结果快照，将其转换为 HTML 表格与 Prompt，调用 Gemini 生成分析报告。
  - 任务 ID 写入响应，前端轮询 `GET /data_analysis/ai_report/{job_id}` 获取生成状态与最终 HTML。

## 仪表盘设备运行状态板块（2025-12-09）

- **功能新增**：在 `dashboard_expression.py` 中实现了 `_fill_device_status_section` 逻辑，用于填充仪表盘的“11.各单位运行设备数量明细表”。
- **逻辑说明**：
  - 读取配置中的单位列表（如“北海热电厂”）和指标列表（如“运行汽炉数”）。
  - 调用 `_fetch_metrics_from_view` 从 `sum_basic_data` 视图查询当日数值。
  - 将结果填充至 JSON 响应的 `section['本期']` 中，供前端渲染。
  - 该逻辑在 `evaluate_dashboard` 流程末尾自动执行，无需额外 API 调用。

## AI 报告修正（2025-12-30 ~ 2026-01-03）

- **计划比较恢复**：修复了遗留 API `_execute_data_analysis_query_legacy` 漏调计划对比逻辑的问题；Service 层增加单位映射（如 `BeiHai_co_generation_Sheet` -> `BeiHai`），确保计划值能正确匹配。
- **百分比展示**：引入 `PERCENTAGE_SCALE_METRICS`（如 `rate_overall_efficiency`），在生成 `plan_comparison` 与 `rows` 时自动乘以 100，修复了“80% 显示为 0.8%”的问题。
- **自动修订**：AI 报告流程新增“核查-修订”循环。若 Validation 阶段发现数值错误，会自动生成修订 Prompt 让模型重写报告，最大程度减少幻觉。
- **环比展示**：单日模式或 1 天跨度的累计模式下，强制计算上一日/上一周期的环比值，并输出至前端与 AI 报告。
- **配置加密**：恢复了对 `api_key.json` 的伪加密存储（`encrypt_api_key`），内存中透明解密，防止明文 Key 落地。
- **热加载**：修改 AI 配置后立即重置 Gemini Client，无需重启服务即可生效。

## 视图口径调整（2026-01-03）



- **净投诉量**：`analysis_company_sum` 与 `analysis_groups_sum` 视图中的“万平方米省市净投诉量”计算公式调整，改为取终止日的 `sum_season_total_net_complaints` 除以 `amount_heating_fee_area`，不再使用每日累加值，以符合最新的业务统计口径。



## 数据分析环比缩放修正（2026-01-10）



- **缩放对齐**：修正了 `_execute_data_analysis_query_legacy` 在构造 `ringCompare.prevTotals` 时漏调 `_scale_metric_value` 的 Bug。现在“全厂热效率”等百分比指标在环比比较中的“上期累计”值将正确显示为放大 100 倍后的数值（如 85.00% 而非 0.85%），确保了环比增长率计算的准确性。

## 项目模块化第三步（2026-02-08）

- 通用项目管理接口（系统管理员）已上线：
  - `GET /api/v1/projects/{project_id}/modularization/status`
  - `POST /api/v1/projects/{project_id}/modularization/bootstrap`
- 实现位置：
  - `backend/api/v1/routes.py`
  - 依赖 `backend/services/project_data_paths.py` 的目录创建、状态检查、缺失文件复制能力。
- 角色控制：
  - 仅 `系统管理员` 与 `Global_admin` 可执行。
- 兼容说明：
  - 仍保留 `daily_report_25_26` 下原有专用接口；
  - 通用接口可面向后续新项目复用，默认文件清单按当前日报项目模板执行。

## 项目模块化第四步（2026-02-08）

- `backend/api/v1/routes.py` 的迁移文件清单改为“配置驱动优先”：
  1. 优先读取项目配置中的目录化声明：
     - `modularization` / `目录化迁移` / `project_modularization`
     - 支持 `config_files`（或 `config/配置文件`）、`runtime_files`（或 `runtime/运行时文件`）
  2. 若未声明 `config_files`，自动从 `pages` 下各页面 `数据源/data_source` 推断 JSON 文件名；
  3. 若仍为空，再回退默认清单（兼容旧项目）。
- 这意味着新增项目可以仅通过 `项目列表.json` 配置迁移文件清单，无需改后端代码。

## 项目模块化第五步（2026-02-08）

- 新增 `backend/services/project_registry.py`，统一默认项目与内置迁移清单：
  - `get_default_project_key()`
  - `get_project_modularization_files(project_key)`
- 接入范围：
  - `backend/api/v1/routes.py`（通用模块化接口兜底清单来源）
  - `backend/api/v1/daily_report_25_26.py`（项目迁移清单来源）
  - `backend/services/dashboard_cache.py`
  - `backend/services/dashboard_expression.py`
  - `backend/services/data_analysis_ai_report.py`
- 结果：减少 `daily_report_25_26` 字符串与默认清单的散落硬编码，后续多项目扩展更可控。

## 项目模块化第六步（2026-02-08）

- 新增项目路由注册表：`backend/api/v1/project_router_registry.py`
  - 统一管理各项目 `router/public_router` 映射。
- `backend/api/v1/routes.py` 改造为循环挂载：
  - 按注册表自动挂载 `/api/v1/projects/<project_key>` 前缀。
- 效果：新增项目时路由接入改动点更集中，主路由文件稳定性更高。

## 项目模块化第七步（2026-02-08）

- 新增服务：`backend/services/project_modularization.py`
  - 统一封装项目目录化文件清单解析（配置声明 > pages 推断 > 注册表默认清单）。
  - 提供 `load_project_entries/load_project_entry` 供接口层复用。
- 接入调整：
  - `backend/api/v1/routes.py` 改为调用该服务，不再维护本地重复解析函数；
  - `backend/api/v1/daily_report_25_26.py` 的专用模块化接口也改为同一服务解析，确保口径一致。
- 效果：通用与专用接口共享同一解析链路，后续演进只需维护一处实现。

## 项目模块化第八步（2026-02-08）

- 新增项目目录路由入口：
  - `backend/projects/daily_report_25_26/api/router.py`
- 路由注册切换：
  - `backend/api/v1/project_router_registry.py` 改为从项目目录入口导入 `router/public_router`。
- 说明：
  - 当前为“入口迁移完成、实现复用旧模块”的过渡态；
  - 下一阶段将把 `backend/api/v1/daily_report_25_26.py` 的实现按功能继续拆分下沉到项目目录。

## 项目模块化第九步（2026-02-08）

- 新增项目目录实现文件：
  - `backend/projects/daily_report_25_26/api/modularization.py`
- 路由组装更新：
  - `backend/projects/daily_report_25_26/api/router.py` 现组合 `legacy_router + modularization_router`。
- 旧文件收缩：
  - `backend/api/v1/daily_report_25_26.py` 已移除 `/project/modularization/*` 接口实现，避免双维护。
- 结果：
  - 模块化管理接口已“实现归位到项目目录”，但对外 URL 与前端调用不变。

## 项目模块化第十步（2026-02-08）

- 新增项目目录实现文件：
  - `backend/projects/daily_report_25_26/api/dashboard.py`
- 路由组装更新：
  - `backend/projects/daily_report_25_26/api/router.py` 现组合 `legacy_router + modularization_router + dashboard_router`；
  - `public_router` 同时组合 legacy 与 dashboard 的公开接口。
- 旧文件收缩：
  - `backend/api/v1/daily_report_25_26.py` 已移除 `/dashboard*` 相关接口实现与冗余依赖导入。
- 结果：
  - 数据看板接口实现已按项目目录归位，且对外路径保持兼容。

## 项目模块化第十一步（2026-02-08）

- 文件归位：
  - 原 `backend/api/v1/daily_report_25_26.py` 已整体迁移到
    `backend/projects/daily_report_25_26/api/legacy_full.py`。
- 兼容策略：
  - `backend/api/v1/daily_report_25_26.py` 现为轻量兼容层，仅转发导入项目目录实现；
  - 旧导入路径继续可用，避免一次性改动冲击。
- 路由入口：
  - `backend/projects/daily_report_25_26/api/router.py` 已直接引用项目目录 `legacy_full.py`。

## 项目模块化第十二步（2026-02-08）

- `backend_data` 目录已完成数据层归位：
  - 全局文件：`backend_data/shared/`、`backend_data/shared/auth/`
  - 项目文件：`backend_data/projects/daily_report_25_26/config/`、`backend_data/projects/daily_report_25_26/runtime/`
- `shared/项目列表.json` 已更新：
  - 页面数据源路径切换为 `projects/daily_report_25_26/config/...`
  - 增加 `modularization.config_files/runtime_files` 清单
- 兼容性说明：
  - 路径解析已是“shared/project 优先 + 旧路径回退”，因此本次数据归位可平滑衔接。

## 项目模块化第十三步（2026-02-08）

- 全局状态文件归位：
  - `backend_data/shared/status.json`
  - `backend_data/shared/ai_usage_stats.json`
- 服务层路径修正：
  - `workflow_status.py` 使用 `resolve_workflow_status_path()`
  - `ai_usage_service.py` 使用 `resolve_ai_usage_stats_path()`
  - `project_data_paths.py` 新增上述解析函数（shared 优先，旧路径回退）
- 其他归位：
  - `api_key.json.backup` 迁移到 `projects/daily_report_25_26/config/`
  - `shared/项目列表.json` 的 `runtime_files` 清单移除 `ai_usage_stats.json`（改由 shared 统一维护）

## 结构同步（2026-02-08）

- 本轮后端代码无新增改动；主要变更发生在前端全局页面目录归属修复。

## 结构同步（2026-02-11 春节迷你项目提取链路）

- 春节迷你项目接口目录：`backend/projects/daily_report_spring_festval_2026/api/`
  - `xlsx_extract.py`：上传 xlsx、提取 `byDate`、落盘 latest-json、读取 latest-json。
- 本轮修复：
  - `xlsx_extract.py` 新增“Excel 公式转数值”能力（单元格引用与四则运算），用于将 `current/prior` 从公式文本转换为可视化所需数值。
- 结果：
  - mini 看板后续消费的提取 JSON 将优先包含可计算数值，减少“有数据但图表空白”问题。

## 结构同步（2026-02-12 春节迷你看板前端联调）

- 本轮后端接口与服务无新增改动。
- 前端已将 mini 看板气温解析逻辑对齐到主看板数据结构回退策略，以更稳定消费后端 `dashboard` 返回的气温 section（来源仍为 `calc_temperature_data` 视图链路）。

## 结构同步（2026-02-12 春节迷你看板日期窗口调整）

- 本轮后端接口与服务无新增改动。
- 前端已实现北京时间“昨日优先”默认日期与气温图 `±3` 天窗口展示，继续复用现有后端 `dashboard` 数据接口。

## 结构同步（2026-02-12 春节迷你看板气温图显示增强）

- 本轮后端接口与服务无新增改动。
- 前端新增气温图 tooltip 两位小数显示、业务日期竖线与业务日期本期/同期温度点位标注，数据来源仍沿用既有 `dashboard` 接口。

## 结构同步（2026-02-12 春节迷你看板气温标签策略调整）

- 本轮后端接口与服务无新增改动。
- 前端将气温图改为“全点位标签默认显示 + 业务日期竖线无文字标签”，继续复用既有 `dashboard` 接口数据。

## 结构同步（2026-02-12 春节迷你看板显示口径调整）

- 本轮后端接口与服务无新增改动。
- 前端新增气温标签防碰撞、浅色业务日期竖线，并将四卡差异展示口径调整为“绝对增减量”。

## 结构同步（2026-02-12 春节迷你看板煤耗口径图重构）

- 本轮后端接口与服务无新增改动。
- 前端将煤耗图重构为“业务日期当日各口径耗原煤量对比”，并完成四卡配色与主看板风格对齐。

## 结构同步（2026-02-12 春节迷你看板煤耗图同期补齐）

- 本轮后端接口与服务无新增改动。
- 前端煤耗图已从单柱扩展为“本期+同期”双柱对比，单位继续使用“吨”。

## 结构同步（2026-02-12 春节迷你看板精度与庄河同期规则）

- 本轮后端接口与服务无新增改动。
- 前端补充“庄河同期优先取剔除指标”规则，并按业务要求统一卡片/图表精度与煤耗图配色。

## 结构同步（2026-02-12 庄河同期来源修正）

- 本轮后端接口与服务无新增改动。
- 前端已将庄河口径同期来源从“剔除指标泛匹配”收敛为“其中：张屯原煤消耗量”优先匹配。

## 结构同步（2026-02-12 投诉量分项展示重构）

- 本轮后端接口与服务无新增改动。
- 前端将投诉量分项展示改为“双图（总/净）+一表”，并在两张图中叠加本期气温折线。

## 结构同步（2026-02-12 投诉分项布局与视觉优化）

- 本轮后端接口与服务无新增改动。
- 前端将投诉双图布局调整为半屏并排，并完成清新化样式与无横线图表设置。

## 结构同步（2026-02-12 投诉图气温线业务日期截断）

- 本轮后端接口与服务无新增改动。
- 前端在投诉双图中将“本期气温”折线限制到业务日期，业务日期后的预报点不再绘制。

## 结构同步（2026-02-12 投诉柱业务日期截断）

- 本轮后端接口与服务无新增改动。
- 前端已将投诉双图中的本期/同期柱同样限制到业务日期，业务日期后数据不绘制。

## 结构同步（2026-02-12 投诉区统一业务日期可见范围）

- 本轮后端接口与服务无新增改动。
- 前端将投诉双图与下方表统一限制到业务日期可见范围，并移除了气温线数值标签。

## 结构同步（2026-02-12 投诉图横轴与柱形观感优化）

- 本轮后端接口与服务无新增改动。
- 前端将投诉双图横轴改为 `MM-DD`，并通过固定窗口日期轴与柱宽间距优化改善早日期场景的图面比例。

## 结构同步（2026-02-12 投诉图全业务日期轴）

- 本轮后端接口与服务无新增改动。
- 前端将投诉双图横轴调整为完整业务日期范围，业务日期后以空数据保留右侧空间。

## 结构同步（2026-02-12 mini看板PDF导出入口）

- 本轮后端接口与服务无新增改动。
- 前端在 mini 看板顶部新增“下载PDF”按钮，复用浏览器打印导出能力。

## 结构同步（2026-02-12 mini看板PDF直出与差值+0修正）

- 本轮后端接口与服务无新增改动。
- 前端将 mini 看板 PDF 导出从浏览器打印流升级为 `html2canvas + jsPDF` 直出下载，并完善导出中按钮状态反馈。
- 前端同步修正顶部四卡差值显示规则：当差异为 0 时显示 `+0`（按字段既定精度）。

## 结构同步（2026-02-12 mini看板PDF链路改为主看板同款）

- 本轮后端接口与服务无新增改动。
- 前端将 mini 看板 PDF 导出实现切换为与主看板一致的全局脚本链路（`window.html2canvas` + `window.jspdf.jsPDF`），并移除本地模块依赖以消除 `jspdf` 模块错误风险。

## 结构同步（2026-02-12 mini看板PDF边距优化）

- 本轮后端接口与服务无新增改动。
- 前端将 mini 看板 PDF 导出内容增加统一页边距（6mm），修复左右贴边裁切观感。

## 结构同步（2026-02-12 mini看板新增原煤/设备明细表）

- 本轮后端接口与服务无新增改动。
- 前端在春节 mini 看板新增两块表格能力：  
  1) 原煤对比图下方新增“春节期间每日各口径本期/同期原煤消耗量”宽表（首列含气温，按业务日期截断）；  
  2) 页面底部新增“各单位运行设备数量明细表”（业务日期），口径覆盖北海（含北海水炉）、香海、金州、北方、金普、庄河。

## 结构同步（2026-02-12 mini看板设备表样式对齐）

- 本轮后端接口与服务无新增改动。
- 前端将 mini 看板设备明细表调整为与主看板参考一致的分组组合样式（炉机组态/调峰水炉/燃煤锅炉），并过滤本期/同期均为 0 的冗余设备项。

## 结构同步（2026-02-12 mini看板设备组合项换行显示）

- 本轮后端接口与服务无新增改动。
- 前端将 mini 看板设备表中的组合项改为纵向逐行展示，提升汽炉/汽轮机数值的左右对应可读性。

## 结构同步（2026-02-12 mini看板原煤明细列结构调整）

- 本轮后端接口与服务无新增改动。
- 前端将原煤明细表调整为“口径单列 + 单元格本期/同期”形式，不再拆分为本期列和同期列。

## 结构同步（2026-02-12 mini看板原煤明细分级表头）

- 本轮后端接口与服务无新增改动。
- 前端将原煤明细表改为分级表头：父级口径 + 子级本期/同期，匹配业务侧对“集团汇总下分本期/同期”的展示要求。

## 结构同步（2026-02-12 mini看板风格切换与春节主题）

- 本轮后端接口与服务无新增改动。
- 前端为春节 mini 看板新增主题切换能力（默认/春节氛围）及本地持久化，并增加春节风格背景与卡片/表格配色模板。

## 结构同步（2026-02-12 mini看板春节主题可读性修复）

- 本轮后端接口与服务无新增改动。
- 前端修复春节主题下顶部四卡可读性，并补充轻量节庆装饰元素（灯笼与主题徽标），在增强节日氛围的同时保持数据区清晰。

## 结构同步（2026-02-12 mini看板PDF清晰度提升）

- 本轮后端接口与服务无新增改动。
- 前端将 mini 看板 PDF 导出渲染倍率从 2 提升到 3，以约 1.5 倍像素密度提升导出清晰度。

## 结构同步（2026-02-12 mini看板标题文案调整）

- 本轮后端接口与服务无新增改动。
- 前端将 mini 看板主标题文案由“春节简化数据看板”调整为“春节数据看板”。

## 结构同步（2026-02-12 主看板气温读取切换至日聚合视图）

- 修改文件：`backend/services/dashboard_expression.py`
- 核心调整：
  - 将第1节气温填充由“查询 `temperature_data` 小时序列”切换为“查询 `calc_temperature_data` 日级统计”；
  - 新增 `_fetch_daily_temperature_stats_map` 读取 `max_temp/min_temp/aver_temp`；
  - `_fill_temperature_block` 改为按日期写入 `{max, min, avg}` 日级结构。
- 口径说明：
  - 某一时期平均气温仍按 `AVG(aver_temp)` 计算，即“每日平均气温的平均值”。
- 验证结果：
  - `python -m py_compile backend/services/dashboard_expression.py` 通过。

## 结构同步（2026-02-12 主看板第1节命名切换为日均气温）

- 修改文件：`backend/services/dashboard_expression.py`、`backend_data/projects/daily_report_25_26/config/数据结构_数据看板.json`、`backend_data/projects/daily_report_25_26/config/dashboard_frontend_config.json`
- 调整内容：
  - 第1节命名由“逐小时气温”改为“日均气温”；
  - 配置中的 `key/title/source_section` 与 `数据来源` 已同步切到 `1.日均气温` + `calc_temperature_data`；
  - 后端 section 解析保留旧键兼容（`1.逐小时气温`）以平滑过渡缓存。

## 结构同步（2026-02-12 下线项目模块化管理接口）

- 修改文件：`backend/projects/daily_report_25_26/api/router.py`
- 删除文件：`backend/projects/daily_report_25_26/api/modularization.py`
- 清理内容：
  - `daily_report_25_26` 项目路由不再挂载 `modularization_router`；
  - 项目专属 `/project/modularization/status` 与 `/project/modularization/bootstrap` 接口下线。
- 验证结果：
  - `python -m py_compile backend/projects/daily_report_25_26/api/router.py backend/api/v1/routes.py` 通过。

## 结构同步（2026-02-12 春节迷你看板“金镶玉”主题重构）

- 本轮后端接口与服务无新增改动。
- 前端对 `SpringFestivalDashboardView.vue` 的“春节氛围”模式进行了视觉重构，引入了深红暗纹背景、暖白卡片、金色边框及动态挂饰动画，提升了节日模式下的数据可读性与美观度。

## 结构同步（2026-02-12 数据展示页导出 Excel 504 超时修复）

- 本轮后端接口与服务无新增改动。
- 前端导出链路调整为串行 `runtime/spec/eval` + 超时中断 + 504 重试与可读报错，减少网关超时导致的导出失败。

## 结构同步（2026-02-12 修复 frontend/jsconfig 报错）

- 本轮后端接口与服务无新增改动。
- 前端 `frontend/jsconfig.json` 完成路径别名与 `include` 范围修正，用于提升工程索引与模块解析稳定性。

## 结构同步（2026-02-12 登录“账户信息文件缺失”部署兼容修复）

- 修改文件：`backend/services/project_data_paths.py`、`backend/services/auth_manager.py`
- 调整内容：
  - `resolve_accounts_path` 增加多路径候选（含 `accounts.json`）；
  - `resolve_permissions_path` 增加兼容候选路径；
  - 账户/权限文件缺失时报错中附带实际解析路径，提升线上排障效率。
- 验证结果：
  - `python -m py_compile backend/services/project_data_paths.py backend/services/auth_manager.py` 通过。

## 结构同步（2026-02-15 春节看板卡片文案修正）

- 本轮后端接口与服务无新增改动。
- 前端将春节看板顶部卡片文案从“当日集团标煤消耗（剔除庄河改造锅炉房）”调整为“当日集团原煤消耗（剔除庄河改造锅炉房）”，不涉及后端数据口径变更。

## 结构同步（2026-02-15 春节看板原煤图标题补充口径）

- 本轮后端接口与服务无新增改动。
- 前端将原煤对比图标题从“当日各口径耗原煤量对比”调整为“当日各口径耗原煤量对比（剔除庄河改造锅炉房）”，仅为展示文案更新。

## 结构同步（2026-02-15 春节看板两张表新增合计行）

- 本轮后端接口与服务无新增改动。
- 前端在春节看板页面为“当日各口径耗原煤量对比（剔除庄河改造锅炉房）”和“投诉量分项”两张表新增末尾“合计”行展示；其中“净投诉量（本期/同期）”合计单元格固定显示 `-`，不做汇总。

## 结构同步（2026-02-15 春节看板两张表去除非气温单位）

- 本轮后端接口与服务无新增改动。
- 前端将春节看板两张表中的原煤消耗量/投诉量列调整为纯数字展示（不带“吨/件”单位），气温列仍保留“℃”。

## 结构同步（2026-02-15 春节看板气温取数项目键修复）

- 本轮后端接口与服务无新增改动。
- 前端修复春节看板气温接口调用的项目键传参：不再固定请求 `daily_report_25_26`，改为按当前页面 `projectKey` 请求对应项目看板数据，减少无关数据包加载并修复跨项目取数偏差。

## 结构同步（2026-02-15 春节看板气温空白修复：新增轻量温度接口）

- 修改文件：`backend/projects/daily_report_25_26/api/dashboard.py`
- 新增接口：`GET /api/v1/projects/daily_report_25_26/dashboard/temperature/trend`
- 能力说明：
  - 按 `show_date/start_date/end_date` 查询 `calc_temperature_data`，返回本期 `main` 与同期 `peer` 的日均气温映射；
  - 用于春节看板气温曲线，避免前端再请求全量 `/dashboard` 数据包。
- 兼容说明：
  - 既有 `/dashboard`、`/dashboard/date` 等接口行为不变；新增接口为向后兼容扩展。

## 结构同步（2026-02-15 春节气温接口路由归位到 spring 项目）

- 新增文件：`backend/projects/daily_report_spring_festval_2026/api/temperature_trend.py`
- 修改文件：`backend/projects/daily_report_spring_festval_2026/api/router.py`
- 调整内容：
  - 在 spring 项目下新增公开接口：`GET /api/v1/projects/daily_report_spring_festval_2026/spring-dashboard/temperature/trend`；
  - spring 项目 `public_router` 已挂载该接口，前端可在项目内路径直接访问。
- 结果：
  - 春节看板温度接口职责与路由归属回归到 spring 模块边界，避免前端跨项目 API 路径耦合。

## 结构同步（2026-02-15 春节气温接口增加温度原表兜底）

- 修改文件：`backend/projects/daily_report_spring_festval_2026/api/temperature_trend.py`
- 调整内容：
  - `spring-dashboard/temperature/trend` 的日均温度查询增加兜底逻辑：  
    - 优先查 `calc_temperature_data`；  
    - 若为空，回退查 `temperature_data` 按天 `AVG(value)` 聚合。  
- 结果：
  - 避免因温度聚合视图未刷新导致接口返回空集，提升气温曲线可用性。

## 结构同步（2026-02-15 春节气温接口前端自动回退）

- 本轮后端接口与服务无新增改动。
- 前端为 spring 气温取数增加“主路径失败自动回退”机制：优先调用 spring 项目温度接口，异常时临时回退到 `daily_report_25_26` 轻量温度接口，降低发布切换窗口期空白风险。

## 结构同步（2026-02-15 春节气温链路增加老 dashboard 最终兜底）

- 本轮后端接口与服务无新增改动。
- 前端在现有回退机制上新增第3层兜底：当轻量温度接口不可用时，回退到历史 `daily_report_25_26` 的 `/dashboard` 接口，确保无需后端重启也能恢复气温曲线。

## 结构同步（2026-02-15 页面临时调试增强）

- 本轮后端接口与服务无新增改动。
- 前端新增温度链路调试可视化（默认开启），用于直接定位接口命中层级与数据映射状态，不影响后端协议。

## 结构同步（2026-02-15 温度图渲染强制可视化调试）

- 本轮后端接口与服务无新增改动。
- 前端温度图增加显式渲染参数与 ECharts 入参回显（`echartsPayload`），用于排查“数据存在但曲线不显示”的前端渲染异常。

## 结构同步（2026-02-15 EChart 组件渲染稳态修复）

- 本轮后端接口与服务无新增改动。
- 前端增强 EChart 组件初始化与尺寸监听（`nextTick` 应用 option + `ResizeObserver` + 强制 resize），用于提升温度图在布局切换场景下的可见性稳定性。

## 结构同步（2026-02-15 温度图样式回退）

- 本轮后端接口与服务无新增改动。
- 前端已将温度图视觉配置回退至既定展示样式，仅保留图表组件层稳定性修复。

## 结构同步（2026-02-16 春节看板合计行样式与气温合计修正）

- 本轮后端接口与服务无新增改动。
- 前端在 `spring-dashboard` 页面完成两项调整：
  - 两张明细表“合计”行加粗显示；
  - 气温合计改为算术平均值（不再求和）。

## 结构同步（2026-02-25 项目列表配置功能确认）

- 本轮后端代码与接口无改动。
- 已确认 `backend_data/shared/项目列表.json` 的当前职责：
  - 作为 `GET /api/v1/projects` 的项目清单来源；
  - 作为 `GET /api/v1/projects/{project_id}/pages` 的页面元数据来源；
  - 作为项目目录化迁移文件清单推断输入（`modularization/config_files/runtime_files`）；
  - 作为历史数据文件候选路径收集输入（根据 `pages[*].数据源` 推断）。

## 结构同步（2026-02-25 项目入口可见性/访问性核对）

- 本轮后端代码与接口无改动。
- 现状确认：
  - `list_projects` 当前不按用户权限过滤项目（仅按配置文件返回）；
  - 权限模型当前无项目级 `project_access` 字段，仅有 `page_access/sheet_rules/units_access/actions`；
  - 因此 `项目列表.json` 暂不具备“按用户组配置项目可见/可访问”的通用能力。

## 结构同步（2026-02-25 用户分组与权限系统核对）

- 本轮后端代码与接口无改动。
- 现状确认：
  - 账号文件：`backend_data/shared/auth/账户信息.json`（用户按组归类，含 `username/password/unit`）；
  - 权限文件：`backend_data/shared/auth/permissions.json`（组维度定义 `hierarchy/page_access/sheet_rules/units_access/actions`）；
  - 鉴权核心：`backend/services/auth_manager.py` 负责加载配置、签发与校验会话、解析可见单位与动作权限；
  - API 返回：`/api/v1/auth/login` 与 `/api/v1/auth/me` 返回 `permissions`，供前端展示过滤与操作按钮控制；
  - 强制校验仍以后端为准（如审批/撤销/发布接口中的 action 与单位范围检查）。

## 结构同步（2026-02-25 权限模型“项目>页面”改造方案确认）

- 本轮后端代码无改动，完成可行性与迁移路线评估。
- 计划中的后端改造点：
  - `permissions.json` 增加 `projects.{project_key}.page_access/sheet_rules/(可选 actions/units_access)`；
  - `auth_manager.py` 解析层兼容“旧平铺 + 新项目化”两种结构；
  - `routes.py::list_project_pages` 按 `project_id` 获取对应项目权限进行过滤；
  - 项目内关键接口逐步补齐项目维度动作权限读取，保留旧字段兜底。

## 结构同步（2026-02-25 权限文件模块化已落地）

- 本轮已完成后端代码改造：
  - `backend/services/auth_manager.py`
    - 新增 `ProjectPermissions`；
    - `GroupPermissions` 增加 `projects`；
    - `AuthSession` 增加项目维度权限解析与单位范围解析方法；
    - `_load_permissions` 支持 `groups.*.projects.*`，并兼容旧平铺字段回退。
  - `backend/schemas/auth.py`
    - `PermissionsModel` 新增 `projects`；
  - `backend/api/v1/routes.py`
    - `list_project_pages` 改为按 `project_id` 读取项目维度页面权限；
  - `backend/projects/daily_report_25_26/api/dashboard.py`
    - 缓存操作权限改为项目维度 `actions.can_publish`；
  - `backend/projects/daily_report_25_26/api/legacy_full.py`
    - 审批/撤销/发布与单位过滤统一切换为项目维度权限读取。
- 配置侧变更：
  - `backend_data/shared/auth/permissions.json` 已增加 `projects` 分层，完成“项目 > 页面”组织。

## 结构同步（2026-02-25 权限配置去重）

- 本轮后端代码无改动，仅更新配置文件：
  - `backend_data/shared/auth/permissions.json` 删除组级平铺字段：
    - `page_access`
    - `sheet_rules`
    - `units_access`
    - `actions`
  - 各组仅保留 `hierarchy` 与 `projects.*` 项目化权限定义。
- 结果：
  - 权限数据源保持“单一真相来源”（项目节点），减少重复配置与漂移风险。

## 结构同步（2026-02-25 unit_filler 煤炭库存表权限修复）

- 本轮后端代码无改动，配置调整如下：
  - `backend_data/shared/auth/账户信息.json`
    - `shoudian_filler` 账号从 `unit_filler` 拆分到独立组 `shoudian_filler`；
  - `backend_data/shared/auth/permissions.json`
    - `unit_filler` 组移除 `Coal_inventory_Sheet` 显式授权；
    - 新增 `shoudian_filler` 组并保留 `Coal_inventory_Sheet` 显式授权。
- 结果：
  - `Coal_inventory_Sheet` 的显式可见性从“所有填报员”收敛为“仅 shoudian_filler”。

## 结构同步（2026-02-25 硬编码权限分支核对）

- 本轮后端代码无改动。
- 核对结果：
  - 仍存在少量按角色名写死的操作权限分支（如系统管理员接口、春节提取接口、AI 使用量无限制组），后续可按需要统一收敛到权限配置。

## 结构同步（2026-02-25 硬编码权限已统一收敛到配置）

- 本轮后端改造：
  - `backend/services/auth_manager.py`
    - `ActionFlags` 增加项目动作位：
      - `can_manage_modularization`
      - `can_manage_validation`
      - `can_manage_ai_settings`
      - `can_manage_ai_sheet_switch`
      - `can_extract_xlsx`
      - `can_unlimited_ai_usage`
    - 会话权限序列化与解析已支持新动作位；
    - 新增 `has_project_access(project_key)` 供项目列表可见性控制。
  - `backend/schemas/auth.py`
    - `ActionFlagsModel` 同步新增上述动作位。
  - `backend/api/v1/routes.py`
    - `GET /projects` 增加鉴权依赖并按项目权限过滤返回；
    - 目录化接口权限改为 `can_manage_modularization`。
  - `backend/projects/daily_report_25_26/api/legacy_full.py`
    - 校验开关权限改为 `can_manage_validation`；
    - AI 设置权限改为 `can_manage_ai_settings`；
    - 表级 AI 开关权限改为 `can_manage_ai_sheet_switch`。
  - `backend/projects/daily_report_spring_festval_2026/api/xlsx_extract.py`
    - 提取接口权限改为 `can_extract_xlsx`。
  - `backend/services/ai_usage_service.py`
    - 不限次数逻辑改为 `can_unlimited_ai_usage`，移除组名白名单判断。
- 配置同步：
  - `backend_data/shared/auth/permissions.json` 已补齐对应动作位。

## 结构同步（2026-02-25 项目可见性串权限问题修复）

- 本轮后端代码无改动。
- 问题归因：前端项目列表缓存未按账号 token 隔离，导致切换账号后沿用旧缓存列表。
- 修复方式：在前端 API 层将项目列表缓存绑定当前 token，并在 token 变更时自动失效。

## 结构同步（2026-02-25 项目可用性最高优先级开关）

- 本轮后端改造：  
  - `backend/api/v1/routes.py`
    - 新增项目可用性解析函数 `_is_project_enabled_for_group(project_entry, group_name)`，支持：
      - `项目可用性: false` -> 全部拒绝；
      - `项目可用性: true` -> 继续走 `permissions.json`；
      - `项目可用性: [组列表]` -> 仅白名单组继续走 `permissions.json`；
    - 新增统一校验 `_ensure_project_visible_and_accessible(...)`；
    - `GET /api/v1/projects` 先按项目可用性过滤，再按会话项目权限过滤；
    - `GET /api/v1/projects/{project_id}/pages` 增加项目级总闸校验；
    - `modularization/status` 与 `modularization/bootstrap` 增加项目级总闸校验；
    - 项目路由注册时为 `router/public_router` 统一挂载项目访问依赖，避免绕过项目列表直连接口。
- 配置同步：  
  - `backend_data/shared/项目列表.json`
    - `daily_report_25_26`：`"项目可用性": true`；
    - `daily_report_spring_festval_2026`：`"项目可用性": ["Global_admin"]`。
- 结果：  
  - 项目访问链路统一为“项目可用性（最高优先级）→ permissions.json（项目/页面权限）”，实现不可见即不可访问。

## 结构同步（2026-02-25 可用性字段命名修正）

- 本轮后端改造：
  - `backend/api/v1/routes.py`
    - 项目可用性读取键优先级调整为：`availability` → `project_availability` → `项目可用性`；
    - 权限行为不变，仍为项目入口最高优先级总闸。
- 配置同步：
  - `backend_data/shared/项目列表.json`
    - 全部项目由 `项目可用性` 改为 `availability`；
    - 白名单用户组继续采用数组格式（即使单组也为列表）。

## 结构同步（2026-02-25 availability 兼容回退移除）

- 本轮后端改造：
  - `backend/api/v1/routes.py`
    - `_is_project_enabled_for_group()` 仅保留 `availability` 读取；
    - 移除 `project_availability` 与 `项目可用性` 的兼容回退逻辑。
- 结果：
  - 项目可用性配置入口单一化，避免多键并存带来的配置歧义。

## 结构同步（2026-02-25 切换账号项目残留显示问题）

- 本轮后端代码无改动。
- 问题定位：
  - 属于前端状态一致性问题（全局项目列表状态未在会话切换时清空），并非后端权限过滤异常。

## 结构同步（2026-02-25 数据分析页白屏排查联动）

- 本轮后端代码无改动。
- 联动结论：
  - 将前端“切号清空项目列表”从 `auth store` 耦合方式改为“项目选择页进入时重置并强制重拉”，后端接口契约不受影响。

## 结构同步（2026-02-25 数据分析页白屏修复联动）

- 本轮后端代码无改动。
- 联动结论：
  - 白屏根因是前端 `DataAnalysisView` 变量引用错误（`isGlobalAdmin` 未定义），与后端权限接口无关。

## 结构同步（2026-02-26 管理后台一期）

- 新增项目管理后台聚合接口模块：
  - `backend/projects/daily_report_25_26/api/admin_console.py`
  - `GET /api/v1/projects/daily_report_25_26/admin/overview`
- 接口职责：
  - 汇总当前会话在本项目的管理动作位（校验/AI/缓存）；
  - 返回校验总开关状态（复用现有校验配置读取链路）；
  - 返回 AI 配置摘要（仅掩码 key 与统计，不返回明文）；
  - 返回看板缓存状态与缓存发布任务快照。
- 路由挂载：
  - `backend/projects/daily_report_25_26/api/router.py` 已合并 `admin_console_router`。

## 结构同步（2026-02-26 管理后台全局化）

- 后端新增全局管理路由模块：
  - `backend/api/v1/admin_console.py`
  - 对外路径统一为 `/api/v1/admin/*`（不再属于项目路由）。
- 全局后台权限：
  - 新动作位：`can_access_admin_console`；
  - 仅当会话具备该动作位才允许访问全局后台接口。
- 路由组织调整：
  - `backend/api/v1/routes.py` 已挂载 `admin_console_router`；
  - `backend/projects/daily_report_25_26/api/router.py` 已移除后台路由挂载；
  - 删除项目内旧文件：`backend/projects/daily_report_25_26/api/admin_console.py`。

## 结构同步（2026-02-26 管理后台扩展：文件编辑与项目分流）

- 后端全局后台模块扩展（`backend/api/v1/admin_console.py`）：
  - 文件编辑接口：
    - `GET /api/v1/admin/files/directories`
    - `GET /api/v1/admin/files`
    - `GET /api/v1/admin/files/content`
    - `POST /api/v1/admin/files/content`
  - 项目设定列表接口：
    - `GET /api/v1/admin/projects`
  - 项目化概览：
    - `GET /api/v1/admin/overview?project_key=...`
    - 当前仅 `daily_report_25_26` 返回 `supported=true`，其他项目返回 `supported=false`。
- 安全约束：
  - 文件路径仅允许 `backend_data` 根目录下相对路径；
  - 拒绝越界访问与绝对路径；
  - 单文件在线编辑大小上限 2MB。

## 结构同步（2026-02-26 管理后台文件编辑可用性优化）

- 文件列表过滤策略已收敛（`backend/api/v1/admin_console.py`）：
  - 仅返回可编辑文本扩展名：`json/md/txt/yaml/yml/ini/toml/py/js/ts/vue/css/sql/csv`；
  - 自动跳过超过 2MB 的文件；
  - 目的：降低二进制/超大文件进入前端编辑器导致的性能与误操作风险。

## 结构同步（2026-02-26 树形文件浏览前端联动）

- 本轮后端接口无新增；继续复用：
  - `GET /api/v1/admin/files/directories`
  - `GET /api/v1/admin/files`
  - `GET /api/v1/admin/files/content`
  - `POST /api/v1/admin/files/content`
- 前端已将文件列表消费方式改为树形展示与弹窗编辑，接口契约保持兼容。

## 结构同步（2026-02-26 新窗口编辑器联动）

- 本轮后端接口无新增改动；
- 前端新增独立编辑窗口路由 `/admin-file-editor`，仍复用现有 `admin/files/content` 读写接口；
- 主窗口与编辑窗口通过浏览器 `postMessage` 做保存结果通知，后端无感知变更。

## 结构同步（2026-02-26 管理后台设定项来源盘点）

- 本轮后端代码无新增改动，完成“设定项来源梳理”：
  - 全局后台聚合接口：`backend/api/v1/admin_console.py`
  - 项目内能力来源：`backend/projects/daily_report_25_26/api/legacy_full.py`、`dashboard.py`
- 关键来源映射：
  - 校验总开关：`/admin/validation/master-switch` -> 项目 `data_entry/validation/master-switch` -> `数据结构_基本指标表.json` 全局配置；
  - AI 设置：`/admin/ai-settings` -> 项目 `data_analysis/ai_settings` -> `projects/daily_report_25_26/config/api_key.json`；
  - 缓存发布：`/admin/cache/*` -> 看板缓存服务 -> `projects/daily_report_25_26/runtime/dashboard_cache.json`；
  - 项目列表：`/admin/projects` -> `backend_data/shared/项目列表.json`；
- 全局后台访问动作位：`can_access_admin_console` -> `backend_data/shared/auth/permissions.json`。

## 结构同步（2026-02-26 项目列表与审批状态迁移到项目目录）

- 文件迁移：
  - `backend_data/shared/项目列表.json` -> `backend_data/projects/daily_report_25_26/config/项目列表.json`
  - `backend_data/shared/status.json` -> `backend_data/projects/daily_report_25_26/runtime/status.json`
- 路径解析更新：
  - `backend/services/project_data_paths.py`
    - `resolve_project_list_path()` 优先项目路径；
    - `resolve_workflow_status_path()` 优先项目路径；
    - 旧路径保留回退兼容（`shared` 与历史根目录路径）。
- 相关服务联动：
  - `routes.py`、`admin_console.py`、`project_modularization.py`、`legacy_full.py`、`workflow_status.py` 通过统一解析函数读取，无需单独改业务逻辑。

## 结构同步（2026-02-26 迁移更正：项目列表与 date 文件位置纠偏）

- 文件位置更正：
  - `项目列表.json` 回到 `backend_data/shared/项目列表.json`；
  - `date.json` 迁到 `backend_data/projects/daily_report_25_26/runtime/date.json`。
- 路径解析更正（`backend/services/project_data_paths.py`）：
  - `resolve_project_list_path()`：`shared` 路径为首选，项目内路径为兼容回退；
  - `resolve_global_date_path()`：项目内 runtime 路径为首选，`shared/date.json` 为回退。

## 结构同步（2026-02-26 后台文件树 UI 调整联动）

- 本轮后端接口无改动。
- 前端将后台文件编辑改为“目录+文件统一树”，继续复用既有接口：
  - `GET /api/v1/admin/files/directories`
  - `GET /api/v1/admin/files`
  - `GET /api/v1/admin/files/content`
  - `POST /api/v1/admin/files/content`

## 结构同步（2026-02-26 后台 JSON 编辑器联动）

- 本轮后端接口无改动。
- 前端在新窗口编辑器中新增 JSON 语法校验与格式化能力，仍复用既有读写接口：
  - `GET /api/v1/admin/files/content`
  - `POST /api/v1/admin/files/content`

## 结构同步（2026-02-26 JSON 错误定位增强联动）

- 本轮后端接口无改动。
- 前端 JSON 编辑器在报错时新增行列与错误行定位展示，仍复用既有 `admin/files/content` 读写接口。

## 结构同步（2026-02-26 JSON 光标定位联动）

- 本轮后端接口无改动。
- 前端在 JSON 错误场景新增“光标自动跳转到错误位置”能力，仍复用既有读写接口。

## 结构同步（2026-02-26 管理后台系统监控接口）

- 新增全局后台监控接口：
  - `GET /api/v1/admin/system/metrics`
  - 文件：`backend/api/v1/admin_console.py`
- 指标内容：
  - CPU、内存、磁盘、进程级指标（PID/CPU/RSS/线程/OpenFiles）、平台与 Python 版本、服务运行时长。
- 采集策略：
  - 优先使用 `psutil`；
  - 异常情况下返回基础占位字段（不抛出 500）。
- 依赖更新：
  - `backend/requirements.txt` 增加 `psutil>=5.9.8`。

## 结构同步（2026-02-26 系统监控图形化联动）

- 本轮后端接口无新增改动。
- 前端图形化基于既有 `/api/v1/admin/system/metrics` 轮询结果做可视化，不新增后端历史曲线接口。

## 结构同步（2026-02-26 系统监控时间显示联动）

- 本轮后端接口无改动。
- 前端将“最近刷新”时间按东八区格式化展示（去除 `+08:00` 后缀），不影响接口返回结构。


## 结构同步（2026-02-26 系统后台操作日志与分类统计）

- 新增审计日志服务：`backend/services/audit_log.py`
  - 日志落盘目录：`backend_data/shared/log`
  - 存储格式：按日 `audit-YYYY-MM-DD.ndjson`
  - 能力：事件写入、筛选查询、分类统计聚合。
- 扩展全局后台接口：`backend/api/v1/admin_console.py`
  - `POST /api/v1/audit/events`：接收前端事件上报（登录态用户）
  - `GET /api/v1/admin/audit/events`：日志列表查询
  - `GET /api/v1/admin/audit/stats`：分类统计（category/action/user/page）
- 权限口径：
  - 查询接口继续复用全局后台访问动作位 `can_access_admin_console`。


## 结构同步（2026-02-26 超级管理员控制台）

- 扩展全局后台接口：`backend/api/v1/admin_console.py`
  - 超级管理员登录：`POST /api/v1/admin/super/login`
  - 命令执行：`POST /api/v1/admin/super/terminal/exec`
  - 文件管理：
    - `GET /api/v1/admin/super/files/list`
    - `GET /api/v1/admin/super/files/read`
    - `POST /api/v1/admin/super/files/write`
    - `POST /api/v1/admin/super/files/mkdir`
    - `POST /api/v1/admin/super/files/move`
    - `DELETE /api/v1/admin/super/files`
- 二次鉴权：
  - 通过 `X-Super-Admin-Token` 进行超级管理员令牌校验。
- 超级管理员凭据来源：
  - 优先 `backend_data/shared/auth/super_admin.json`
  - 未配置时默认 `root / root123456`。


## 结构同步（2026-02-26 超级控制台前端交互增强联动）

- 本轮后端接口无新增改动。
- 前端已为超级管理员控制台补充：
  - 运维命令预设下拉（含 `cd /home/ww870411/25-26` 与 docker compose down/pull/up -d）；
  - 资源管理器式目录树（左树右列表）浏览交互。


## 结构同步（2026-02-26 超级控制台可靠性修复联动）

- 本轮后端接口无新增改动。
- 前端已修复超级控制台的目录树深层渲染、目录树刷新一致性与超级管理员令牌 401 失效处理。


## 结构同步（2026-02-26 超级文件管理器右键菜单联动）

- 本轮后端接口无新增改动。
- 前端在既有超级文件管理接口之上新增右键菜单交互（进入/新建/重命名/删除/复制路径/刷新）。


## 结构同步（2026-02-26 超级文件管理器批量与上传联动）

- 后端接口（`backend/api/v1/admin_console.py`）：
  - `POST /api/v1/admin/super/files/upload`
  - 说明：支持 multipart 多文件上传到 `target_dir`（超级管理员令牌鉴权）。
- 联动说明：
  - 前端已基于既有 `list/move/delete` 与新增 `upload` 接口实现多选批量删除、批量移动与拖拽上传；
  - 本轮后端无需新增其他文件管理接口。


## 结构同步（2026-02-26 超级管理员退出登录联动）

- 本轮后端接口无新增改动。
- 前端新增“退出管理员登录”按钮，仅执行前端超级管理员令牌与会话清理，不影响既有后端鉴权接口。


## 结构同步（2026-02-26 超级管理员登录区单行布局联动）

- 本轮后端接口无新增改动。
- 前端仅调整登录区展示布局（用户名/密码/登录/退出同一行），不影响后端鉴权逻辑与接口契约。


## 结构同步（2026-02-26 页签文案调整联动）

- 本轮后端接口无新增改动。
- 前端将后台页签文案“系统监控”调整为“服务器管理”，不影响接口和鉴权逻辑。


## 结构同步（2026-02-26 服务器管理认证切换为 SSH 账号）

- 文件：`backend/api/v1/admin_console.py`
- 认证语义调整：
  - `POST /api/v1/admin/super/login` 从“应用内固定凭据”切换为“SSH 服务器账号认证”；
  - 登录参数新增 `host/port`，使用 `username/password` 进行 SSH 登录验证。
- 执行路径调整：
  - `POST /api/v1/admin/super/terminal/exec` 改为 SSH 远程命令执行；
  - `GET/POST/DELETE /api/v1/admin/super/files*` 改为基于 SFTP 的远程文件管理。
- 新增依赖：
  - `backend/requirements.txt` 增加 `paramiko>=3.4.0`。
- 兼容说明：
  - 接口路径保持不变，前端仅需调整登录参数与文案即可完成切换。


## 结构同步（2026-02-26 服务器管理白屏修复联动）

- 本轮后端接口无新增改动。
- 前端修复 `api.js` 中 `loginSuperAdmin` 变量重名语法错误，后端无需调整。

## 结构同步（2026-02-27 部署问答留痕）

- 本轮后端代码与接口无改动。
- 部署链路结论确认：
  - `lo1_new_server.ps1` 仅负责镜像构建、打标签、推送；
  - 数据库 5432 对外暴露来自服务器运行编排 `lo1_new_server.yml` 的 `db.ports` 配置；
  - 构建编排与运行编排可以分离维护，运行编排以最小运行参数为主。

## 结构同步（2026-02-27 部署遗留文件核查）

- 本轮后端代码与接口无改动。
- 仅完成部署遗留文件有效性核查：
  - 当前主流程为 `lo1_new_server.ps1` + `lo1_new_server.yml`；
  - `docker-compose.server.yml` 等旧编排文件仍被历史脚本/文档引用，但不在当前主流程内。

## 结构同步（2026-02-28 服务器管理取消页面内登录）

- 文件：`backend/api/v1/admin_console.py`
- 管理后台“服务器管理”能力改为本地执行模式：
  - `POST /api/v1/admin/super/terminal/exec`：使用后端进程本地 `subprocess.run` 执行命令；
  - `GET/POST/DELETE /api/v1/admin/super/files*`：使用本地文件系统实现列目录、读写、移动、删除、上传。
- 登录接口兼容：
  - `POST /api/v1/admin/super/login` 保留为兼容占位接口，返回“无需页面内登录”的提示，不再发放 token。
- 鉴权口径：
  - 取消 `X-Super-Admin-Token` 二次鉴权；
  - 保留原有应用登录权限校验（`can_access_admin_console`），系统级权限由服务进程所在操作系统负责。

## 结构同步（2026-02-28 Phoenix 结构复盘：导表模块迁移评估）

- 本轮后端代码与接口无改动。
- 结构确认结论：
  - 后端主入口：`backend/main.py`，统一挂载 `/api/v1`；
  - 项目路由注册：`backend/api/v1/project_router_registry.py`；
  - 项目总路由装配：`backend/api/v1/routes.py`，统一前缀 `/api/v1/projects/{project_key}`；
  - 项目数据路径：`backend/services/project_data_paths.py`（`backend_data/projects/<project_key>/{config|runtime}` + 兼容回退）。
- 可复用接入模板：
  - 参考 `backend/projects/daily_report_spring_festval_2026/api/xlsx_extract.py` 的“上传 xlsx -> 提取 json -> runtime 落盘 -> latest 查询”模式，可用于导表模块一期接入。

## 结构同步（2026-02-28 monthly_data_pull 映射显示规则修正联动）

- 本轮后端接口与导表执行逻辑无改动。
- 联动说明：
  - 前端对映射键名仅做展示归一（去括号/去扩展名），不改变提交给后端的原始键值；
  - `monthly_data_pull` 的文件匹配与执行仍使用原始映射键，接口契约保持不变。

## 结构同步（2026-02-28 项目数据目录归位修正）

- 文件：`backend/projects/monthly_data_pull/api/workspace.py`
  - `monthly_data_pull` 工作目录根路径已从 `DATA_DIRECTORY / PROJECT_KEY` 改为 `get_project_root(PROJECT_KEY)`；
  - 导表模块统一落盘到 `backend_data/projects/monthly_data_pull/`。
- 数据目录迁移：
  - `backend_data/monthly_data_pull/` 已整体迁移至 `backend_data/projects/monthly_data_pull/`；
  - `workspace_settings.json` 中默认目录路径已同步更新为 `backend_data/projects/monthly_data_pull/...`。
- 同类目录治理：
  - `backend_data/spring_festival_latest_extract.json` 已迁移到
    `backend_data/projects/daily_report_spring_festval_2026/runtime/spring_festival_latest_extract.json`；
  - 迁移后 `backend_data` 根目录仅保留全局共享与数据库文件，不再平铺项目业务目录。

## 结构同步（2026-02-28 monthly_data_pull 清空目录与打包下载）

- 文件：`backend/projects/monthly_data_pull/api/workspace.py`
- 新增接口：
  - `POST /api/v1/projects/monthly_data_pull/monthly-data-pull/clear-workspace`
    - 清空 `mapping_rules/source_reports/target_templates/outputs` 四个目录内文件；
    - 保留 `.gitkeep`，避免目录骨架被删除。
  - `GET /api/v1/projects/monthly_data_pull/monthly-data-pull/download-outputs-zip`
    - 将 `outputs` 目录下文件打包为 zip 并下载返回；
    - 使用临时 zip 文件 + 响应后自动清理。
- 兼容说明：
  - 不改变既有导表执行接口与参数；
  - 仅新增目录运维与批量导出能力。

## 结构同步（2026-02-28 monthly_data_pull 批量上传智能归位联动）

- 本轮后端接口无新增改动。
- 联动说明：
  - 前端批量上传功能复用既有 `POST /monthly-data-pull/get-sheets` 上传解析接口逐个处理文件；
  - 文件名智能归位逻辑在前端执行，仅影响槽位预填充，不改变后端执行契约。

## 结构同步（2026-02-28 monthly_data_pull 批量识别预览联动）

- 本轮后端接口无新增改动。
- 联动说明：
  - 前端已将批量归位流程升级为“识别预览 -> 用户确认 -> 执行上传”；
  - 后端继续复用现有 `get-sheets` 接口处理确认后的文件上传与 sheet 读取。

## 结构同步（2026-02-28 monthly_data_pull 源文件 .xls 兼容修复）

- 文件：`backend/projects/monthly_data_pull/services/engine.py`
  - 新增 `.xls` 适配读取：
    - `get_sheet_names` 支持通过 `xlrd` 读取 `.xls` 的 sheet 列表；
    - 源工作簿加载改为按后缀分流：`.xls` 使用 `xlrd` 适配器，其他继续 `openpyxl`。
  - 保持目标工作簿写入链路不变（仍使用 `openpyxl` 输出目标副本）。
- 依赖更新：
  - `backend/requirements.txt` 新增 `xlrd>=2.0.1`。
- 修复效果：
  - 解决源文件为 `.xls` 时批量确认阶段失败的问题。

## 结构同步（2026-02-28 紧急修复：xlrd 缺失不再影响全局路由）

- 文件：`backend/projects/monthly_data_pull/services/engine.py`
  - `xlrd` 改为可选导入，避免依赖缺失时在模块导入阶段抛错；
  - 仅在读取 `.xls` 时检查依赖并返回明确错误提示。
- 修复目标：
  - 防止 `monthly_data_pull` 依赖问题影响 `api/v1` 全局路由挂载；
  - 确保 `POST /api/v1/auth/login` 等基础接口可正常访问。

## 结构同步（2026-02-28 口径收敛：monthly_data_pull 仅支持 xlsx）

- 文件：`backend/projects/monthly_data_pull/services/engine.py`
  - 已移除 `.xls/xlrd` 兼容分支，源文件与映射读取统一为 `openpyxl`；
  - 保持既有导表执行流程不变。
- 依赖：`backend/requirements.txt`
  - 已移除 `xlrd` 依赖。
- 最终口径：
  - `monthly_data_pull` 当前仅支持 `xlsx` 相关格式上传与处理。

## 结构同步（2026-02-28 monthly_data_pull 导表稳定性修复）

- 文件：`backend/projects/monthly_data_pull/services/engine.py`
  - 源工作簿读取切换为 `data_only=True`，避免公式文本跨表写入导致 `#REF!`；
  - 累计写入逻辑新增“公式保留”：目标累计单元格若已有公式则不覆盖；
  - 每次执行新增导表日志 `execution_log_<timestamp>.json`（记录行级状态与错误）。
- 文件：`backend/projects/monthly_data_pull/api/workspace.py`
  - 上传与解析接口统一校验扩展名，仅允许 `xlsx/xlsm/xltx/xltm`。
- 修复效果：
  - 导表异常可追踪；
  - 全年累计公式可保留；
  - 后端上传口径与“仅 xlsx”要求一致。

## 结构同步（2026-02-28 monthly_data_pull 累计值对照日志）

- 文件：`backend/projects/monthly_data_pull/services/engine.py`
  - 累计处理新增对照日志：
    - 行级字段：`acc_compare_status`、`acc_compare_diff`、`tgt_acc_before`；
    - 状态值：`ok` / `mismatch` / `skipped_target_formula` / `non_numeric`。
  - 执行日志新增汇总统计：`acc_compare_stats`。
- 说明：
  - 该能力用于“对照与追踪”，不阻断导表执行；
  - 目标累计单元格若为公式会按“保留公式”策略标记为 `skipped_target_formula`。

## 结构同步（2026-02-28 monthly_data_pull 异常清单联动）

- 本轮后端接口无新增改动。
- 联动说明：
  - 前端异常清单区域基于 `execution_log_*.json` 渲染；
  - 日志字段来源于导表引擎既有输出（`status`、`acc_compare_status`、`acc_compare_diff`、`acc_compare_stats`）。

## 结构同步（2026-02-28 累计表达式与空源单元格异常）

- 文件：`backend/projects/monthly_data_pull/services/engine.py`
  - 累计源 `src_acc` 新增表达式支持：非单坐标时按公式表达式求值（如 `H30+H62`）；
  - 新增源单元格为空检测并记录：
    - `empty_source_refs_month`
    - `empty_source_refs_acc`
    - 状态 `warn_source_empty`；
  - 无法计算的表达式记录：
    - `warn_month_expr_invalid`
    - `warn_acc_expr_invalid`。
- 结果：
  - 映射中的“合计算式”可直接执行；
  - 源单元格为空会进入执行日志并在前端异常清单可见。

## 结构同步（2026-02-28 执行日志增加指标名称）

- 文件：`backend/projects/monthly_data_pull/services/engine.py`
  - 执行日志行对象新增 `indicator_name`；
  - 来源列按优先顺序提取：`指标名称` -> `指标` -> `项目名称` -> `项目`。
- 联动说明：
  - 前端异常清单已新增“指标名称”列读取该字段。

## 结构同步（2026-02-28 指标名称字段来源修正）

- 文件：`backend/projects/monthly_data_pull/services/engine.py`
  - 指标名称提取改为固定读取映射列 `子公司月报表指标名称`；
  - 增加列名空格差异兜底匹配，避免因列名格式差异导致空值。
- 结果：
  - 执行日志中的 `indicator_name` 与映射规则字段来源一致。

## 结构同步（2026-02-28 异常行号对齐映射表）

- 文件：`backend/projects/monthly_data_pull/services/engine.py`
  - 执行日志 `row_index` 起始值由 `1` 调整为 `2`；
  - 行号口径改为映射文件可见行号（第1行为表头，数据行从第2行开始）。

## 结构同步（2026-02-28 累计一致性核对补强）

- 文件：`backend/projects/monthly_data_pull/services/engine.py`
  - 目标累计单元格为公式时，新增公式求值比对逻辑；
  - `acc_compare_status` 新增 `formula_not_verifiable`；
  - 可计算公式将输出 `ok/mismatch`，不再统一视为“跳过校验”。

## 结构同步（2026-02-28 跨子工作表公式核验支持）

- 文件：`backend/projects/monthly_data_pull/services/engine.py`
  - 表达式求值新增跨 sheet 引用解析：
    - `Sheet!Cell`
    - `'Sheet Name'!Cell`
  - 月值/累计表达式与空源单元格检测均支持上述跨 sheet 写法；
  - 目标累计公式核验可对跨 sheet 引用进行求值比对。

## 结构同步（2026-02-28 递归公式求值修复）

- 文件：`backend/projects/monthly_data_pull/services/engine.py`
  - 单元格数值提取新增递归公式求值（支持公式引用公式）；
  - 增加递归深度上限与循环引用保护；
  - 用于累计核验时避免将二级公式误判为 0。
- 修复效果：
  - 链式累计公式可被正确展开，累计不一致可稳定检出。

## 结构同步（2026-02-28 monthly_data_show 预研）

- 本轮后端代码无改动（仅调研与接入点梳理）。
- 已确认后续新增 `monthly_data_show` 时的主接入位：
  - 项目路由注册：`backend/api/v1/project_router_registry.py`
  - 项目模块目录：`backend/projects/monthly_data_show/`
  - 项目可见性与页面配置：`backend_data/shared/项目列表.json`
  - 角色权限：`backend_data/shared/auth/permissions.json`
- 需求来源：
  - `外部导入项目-月报表导入数据库/2.28 月报数据库化配置文件.txt`
  - `外部导入项目-月报表导入数据库/综合表26.1.xlsx`

## 结构同步（2026-02-28 monthly_data_pull 中文名调整）

- 文件：`backend_data/shared/项目列表.json`
  - `monthly_data_pull.project_name`：`月报导表工作台` -> `月报拉取工作台`
  - `monthly_data_pull.pages.workspace.页面名称`：`月报导表主页` -> `月报拉取主页`
- 说明：
  - 本次仅调整展示命名，不涉及后端接口、项目键名或权限结构变更。

## 结构同步（2026-02-28 monthly_data_show 第一阶段：CSV 提取工作台）

- 新增项目模块：`backend/projects/monthly_data_show/`
  - 路由入口：`backend/projects/monthly_data_show/api/router.py`
  - 工作台接口：`backend/projects/monthly_data_show/api/workspace.py`
  - 提取服务：`backend/projects/monthly_data_show/services/extractor.py`
- 路由注册：
  - 更新 `backend/api/v1/project_router_registry.py`，注册 `monthly_data_show`。
- 新增接口：
  - `POST /api/v1/projects/monthly_data_show/monthly-data-show/inspect`
  - `POST /api/v1/projects/monthly_data_show/monthly-data-show/extract-csv`
- 提取口径（首版）：
  - 输出字段：`company,item,unit,value,date,period,type`
  - 自动剔除口径：`恒流`、`天然气炉`、`中水`
  - 支持指标清洗/重命名、剔除指标过滤、计算指标过滤、单位清洗与 `千瓦时 -> 万千瓦时` 转换
  - 按文件名 `yy.m` 推导日期口径（如 `26.1 -> 2026-01`）

## 结构同步（2026-02-28 monthly_data_show 源字段复选提取）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - `inspect` 响应新增 `source_columns`、`default_selected_source_columns`
  - `extract-csv` 新增表单参数 `source_columns`
- 文件：`backend/projects/monthly_data_show/services/extractor.py`
  - `extract_rows` 新增 `selected_source_columns` 入参
  - 仅提取被勾选的源字段（`本年计划/本月计划/本月实际/上年同期`）

## 结构同步（2026-02-28 monthly_data_show 步骤2常驻展示联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端将步骤2调整为常驻显示，仅优化页面交互表现，不影响现有提取接口与参数。

## 结构同步（2026-02-28 monthly_data_show 常量注入配置）

- 文件：`backend/projects/monthly_data_show/services/extractor.py`
  - 新增默认常量规则（发电设备容量/锅炉设备容量）
  - 新增常量规则标准化函数
  - 提取主流程新增常量注入能力（可按键覆盖同口径同周期行）
  - 支持按 `source_column` 决定写入 period/type/date
- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - `inspect` 响应新增：
    - `constants_enabled_default`
    - `constant_rules`
  - `extract-csv` 入参新增：
    - `constants_enabled`
    - `constant_rules_json`

## 结构同步（2026-02-28 monthly_data_show 常量写入口径多选）

- 文件：`backend/projects/monthly_data_show/services/extractor.py`
  - 常量规则写入口径由 `source_column` 升级为 `source_columns`（列表）
  - 常量注入按多选口径逐一写入（每个口径生成对应周期行）
  - 兼容旧配置：单字段 `source_column` 会自动转换为列表

## 结构同步（2026-02-28 monthly_data_show 常量默认策略联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端已将常量注入默认开启，并将常量默认写入口径对齐为“源字段（计划/实际口径）”默认选中集合。

## 结构同步（2026-02-28 monthly_data_show 常量源字段选项一致性联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端已将常量注入区域的源字段可选项，改为实时跟随“源字段（计划/实际口径）”当前勾选集合。

## 结构同步（2026-02-28 monthly_data_show 常量源字段显示策略修正联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端改为“常量源字段选项固定全量显示，勾选状态与上方源字段联动同步（取消即全取消，重选即全重选）”。

## 结构同步（2026-02-28 monthly_data_show 名称与权限调整）

- 文件：`backend_data/shared/项目列表.json`
  - `monthly_data_show.project_name`：`月报入库工作台` -> `月报导入与查询`
  - `monthly_data_show.availability`：新增 `Group_admin`
  - `monthly_data_show.pages.workspace.页面名称`：`月报入库主页` -> `月报导入与查询主页`
- 文件：`backend_data/shared/auth/permissions.json`
  - `Group_admin.projects` 新增 `monthly_data_show`（`page_access: ["workspace"]`）

## 结构同步（2026-02-28 monthly_data_show 双子页面与页面级权限）

- 文件：`backend_data/shared/项目列表.json`
  - `monthly_data_show.pages` 拆分为：\n    - `/projects/monthly_data_show/import-workspace`（月报导入工作台）\n    - `/projects/monthly_data_show/query-tool`（月报数据查询工具）
- 文件：`backend_data/shared/auth/permissions.json`
  - `Global_admin.monthly_data_show.page_access`：\n    - `projects_monthly_data_show_import_workspace`\n    - `projects_monthly_data_show_query_tool`
  - `Group_admin.monthly_data_show.page_access`：\n    - `projects_monthly_data_show_query_tool`（仅查询页）

## 结构同步（2026-02-28 项目页审批进度模块移除联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端项目页面选择页已移除“审批进度”展示与操作区，不再调用对应审批进度交互链路。

## 结构同步（2026-02-28 页面卡片字体样式对齐联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端已修正项目子页面卡片的字体继承与按钮默认样式差异，统一视觉风格。

## 结构同步（2026-02-28 审批进度模块按项目定向显示联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端已将“审批进度”改为项目级条件显示：
    - `monthly_data_show` 项目页隐藏；
    - 其他项目继续保留审批进度展示与审批操作入口。

## 结构同步（2026-02-28 子页面卡片标题颜色统一联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端已将项目子页面卡片大标题颜色改为继承页面标题色系，实现与“请选择功能页面”一致的视觉效果。

## 结构同步（2026-02-28 子页面卡片标题蓝色一致性修正联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端已将子页面卡片大标题颜色明确设为 `var(--primary-700)`，确保与“请选择功能页面”标题蓝色一致。

## 结构同步（2026-02-28 monthly_data_show 新增 report_month 字段）

- 文件：`backend/projects/monthly_data_show/services/extractor.py`
  - `ALLOWED_FIELDS` 新增 `report_month`
  - 新增 `_build_report_month_text` 统一生成来源月份（`YYYY-MM-01`）
  - 普通提取与常量注入两条路径均写入 `report_month`
- 结果：
  - `monthly_data_show` 导出 CSV 支持来源月份字段，示例 `26.2 -> 2026-02-01`。

## 结构同步（2026-02-28 monthly_data_show 报告月份自动识别与手工覆盖）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - `inspect` 响应新增：
    - `inferred_report_year`
    - `inferred_report_month`
    - `inferred_report_month_date`
  - `extract-csv` 新增表单参数：
    - `report_year`
    - `report_month`
  - 新增输入校验：
    - `report_year` 范围 2000-2099
    - `report_month` 范围 1-12
- 文件：`backend/projects/monthly_data_show/services/extractor.py`
  - `extract_rows` 支持接收 `report_year/report_month` 覆盖值
  - 未提供覆盖值时，仍按文件名自动解析年月
  - 覆盖后的年月统一用于 `date`、`period/type` 映射及 `report_month` 字段写入

## 结构同步（2026-02-28 monthly_data_show 第4步 CSV 入库）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - 新增接口：`POST /monthly-data-show/import-csv`
  - 新增响应模型：`ImportCsvResponse`
  - 新增 CSV 解析与字段校验逻辑：
    - 必要字段：`company,item,unit,value,date,period,type,report_month`
    - 日期格式：`YYYY-MM-DD`
  - 入库策略：UPSERT 写入 `month_data_show`
    - 冲突键：`(company, item, date, period, type)`
    - 冲突更新：`unit,value,report_month,operation_time`

## 结构同步（2026-02-28 monthly_data_show CSV 空值入库兼容）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - `value` 字段支持空值标记自动转 `NULL`：
    - `none/null/nan/--/#DIV/0!/无/空/空字符串`
  - `import-csv` 响应新增 `null_value_rows`，返回本次按空值入库条数

## 结构同步（2026-02-28 monthly_data_show 查询接口）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - 新增 `GET /monthly-data-show/query-options`
    - 返回筛选维度：`companies/items/periods/types`
  - 新增 `POST /monthly-data-show/query`
    - 支持筛选：`report_month/date` 区间、`companies/items/periods/types`
    - 支持分页：`limit/offset`
    - 返回字段：`rows + total + summary`
    - `summary` 包含：`total_rows/value_non_null_rows/value_null_rows/value_sum`

## 结构同步（2026-02-28 monthly_data_show 查询排序层次与口径聚合）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - `QueryRequest` 新增：
    - `order_mode`（`company_first` / `item_first`）
    - `aggregate_companies`（是否聚合口径）
  - 查询行为扩展：
    - `order_mode` 控制结果层次顺序（先口径后指标或先指标后口径）
    - `aggregate_companies=true` 时按 `item,unit,date,period,type,report_month` 聚合，返回 `company='聚合口径'`
    - 聚合模式下 `total` 与 `summary` 按聚合结果计算

## 结构同步（2026-02-28 查询页勾选顺序数字标注联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端已在口径/指标勾选项上增加顺序数字标注（1,2,3...），用于表达选择先后顺序。

## 结构同步（2026-02-28 查询筛选项顺序整理）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - `query-options` 接口中 `items` 返回顺序调整为 `ORDER BY MIN(id)`（首次入库出现顺序）
  - 用于配合前端“指标有序勾选”展示，避免仅按字母序带来的阅读割裂

## 结构同步（2026-02-28 指标业务排序规则联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端已在查询页按业务规则重排指标：
    - 基础/半计算在前，19个计算指标在后；
    - 前半区按产量、销售量、消耗量（煤优先）、其他排序；
    - 相似指标中“总”优先。

## 结构同步（2026-02-28 指标三栏分段展示联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端已将指标选择区拆分为三段：
    - 当前指标
    - 常量指标
    - 计算指标
  - 解决“计算指标/常量指标不易识别”的展示问题。

## 结构同步（2026-02-28 查询页分栏样式展开联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端已将口径/指标筛选区域改为整行展开布局，并提升复选列宽与换行表现，修复“内容挤在一起”的问题。

## 结构同步（2026-02-28 查询页指标分组结构修正联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端已将指标分组调整为：
    - 当前指标（尾部含常量指标）
    - 计算指标（19项固定展示）
  - 取消“常量指标单独成栏”方案，避免与用户预期不一致。

## 结构同步（2026-02-28 查询页选择区滚动条修复联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端已修复口径/指标选择区滚动条与高度约束，确保长列表可完整浏览。

## 结构同步（2026-02-28 查询页按月筛选与顺序调整联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端筛选控件已改为按月选择，并按“业务月份优先、来源月份其次”的顺序展示；
  - 前端会将月份自动转换为月初/月末日期后调用现有查询接口。

## 结构同步（2026-02-28 查询层次顺序动态排序）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - `QueryRequest` 新增 `order_fields`（可选值：`company/item/period/type`）
  - 新增安全排序构造函数 `_build_order_sql`
    - 白名单校验
    - 去重与默认兜底
    - 聚合口径模式下自动忽略 `company`
  - 查询结果排序支持按前端“有序勾选层次”动态生效

## 结构同步（2026-02-28 查询页排版密度二次优化联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端已对查询页筛选与结果区做统一密度优化，缓解“部分过松、部分过紧”的排版问题。

## 结构同步（2026-02-28 查询页口径/指标整行占满联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端已将“口径（可多选）”与“指标（可多选）”区域调整为整行占满展示。

## 结构同步（2026-02-28 口径选择区紧凑化联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端已对“口径（可多选）”内部列表做独立紧凑化样式调整。

## 结构同步（2026-02-28 指标两栏显示不全修复联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端已提升指标分段容器可视高度，并为分段内容增加独立滚动，修复显示不全问题。

## 结构同步（2026-02-28 四筛选模块同一行布局联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端已将“期间/类型/层次顺序/是否聚合口径”四模块重排为同一行并列布局。

## 结构同步（2026-02-28 查询空选不提取保护）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - 查询入口新增保护：
    - 当 `periods` 为空或 `types` 为空时，直接返回空结果与空汇总
  - 避免“无期间/无类型”条件下误查全量数据

## 结构同步（2026-02-28 查询页初始不自动查询联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端查询页已改为仅加载筛选项，不在页面初始化阶段自动发起查询。

## 结构同步（2026-02-28 期间月份聚合开关）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - `QueryRequest` 新增 `aggregate_months`
  - 查询逻辑支持“月份区间聚合”：
    - `aggregate_months=false`：逐月列出
    - `aggregate_months=true`：按区间聚合（不按 date/report_month 分组）
  - 可与 `aggregate_companies` 叠加使用

## 结构同步（2026-02-28 聚合口径开关文案微调联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端将聚合口径关闭态文案更新为“不聚合口径（逐口径列出）”。

## 结构同步（2026-02-28 查询前置条件扩展）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - 查询空选保护从“期间/类型”扩展为“四项必选”：
    - `companies`
    - `items`
    - `periods`
    - `types`
  - 任一为空时返回空结果

## 结构同步（2026-02-28 汇总信息去除数值合计联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端查询页“汇总信息”已移除“数值合计”卡片。

## 结构同步（2026-02-28 类型顺序 real 优先联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端查询页“类型”筛选顺序已调整为 `real` 优先展示。

## 结构同步（2026-02-28 monthly_data_show 一键入库联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端已支持将第3步导出的 CSV 结果直接复用到第4步入库调用（免手动重新选文件）。

## 结构同步（2026-02-28 monthly_data_show 第3步提取与下载分离联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端将第3步拆分为“提取 CSV”和“下载 CSV”两个按钮；
  - 后端提取接口保持不变，继续返回 CSV 文件流供前端缓存与下载。

## 结构同步（2026-02-28 新增 month_data_show 建表脚本）

- 文件：`backend/sql/month_data_show.sql`
  - 新增表：`month_data_show`
  - 字段：
    - `company, item, unit, value, date, period, type, report_month`
    - `id, operation_time`
  - 索引：
    - 唯一索引：`(company, item, date, period, type)`
    - 查询索引：`(date, company)`、`(report_month)`

## 结构同步（2026-02-28 monthly_data_show 查询接入“平均气温”）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - 新增派生指标常量：
    - `AVERAGE_TEMPERATURE_ITEM = "平均气温"`
    - `AVERAGE_TEMPERATURE_UNIT = "℃"`
  - `GET /monthly-data-show/query-options`：
    - 对 `items` 列表追加兜底项“平均气温”（不存在时追加）
  - `POST /monthly-data-show/query`：
    - 新增温度派生行构建逻辑：`_build_average_temperature_rows(...)`
    - 数据源：`calc_temperature_data.aver_temp`
    - 规则：
      - 仅在已选择指标“平均气温”且 `period=month`、`type=real` 时参与结果
      - 非 `aggregate_months`：按月聚合当月每日温度算术平均
      - `aggregate_months=true`：对整段日期区间做算术平均
    - 主表查询结果与温度派生结果合并后，统一排序、分页与汇总返回

## 结构同步（2026-02-28 monthly_data_show 平均气温纠偏）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - 修正温度日期范围推断：
    - 当仅给出单个月份边界（如仅 `date_from`）时，自动扩展为该月完整日期区间
  - 查询主流程调整：
    - 将“平均气温”从主表 `month_data_show` 项中过滤，防止同名历史行干扰
    - 若仅选择“平均气温”，则跳过主表查询，只返回 `calc_temperature_data` 派生结果
  - 效果：平均气温按“月内每日 `aver_temp` 算术平均”稳定输出

## 结构同步（2026-02-28 查询页同比/分析/XLSX 导出联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端查询页新增“同比/环比对比”“专业分析要点”“XLSX 导出”能力；
  - 对比与分析基于查询接口返回结果在前端计算生成；
  - 导出文件包含查询结果、对比结果、分析结论三个工作表。

## 结构同步（2026-02-28 monthly_data_show 后端实时同比/环比接口）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - 新增接口：`POST /monthly-data-show/query-comparison`
  - 对比窗口规则：
    - 当前窗口：优先 `date_from/date_to`，回退 `report_month_from/report_month_to`
    - 同比窗口：当前窗口向前平移一年
    - 环比窗口：当前窗口前一个等长时间段
  - 维度对齐：
    - `company + item + period + type + unit`
    - 支持 `aggregate_companies`
  - 返回字段：
    - `current_value / yoy_value / yoy_rate / mom_value / mom_rate`
    - 同时返回三段窗口标签，供前端展示

## 结构同步（2026-02-28 可视化总览联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端新增“同比/环比热力图 + TopN 条形图”；
  - 图形数据全部复用后端 `query-comparison` 接口，保证口径与表格一致。

## 结构同步（2026-02-28 同比/环比配色语义联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端将同比/环比颜色语义统一调整为“正值红、负值绿”，仅表现层变更，不影响接口与计算逻辑。

## 结构同步（2026-02-28 热力图标题换行联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端热力图标题改为“纵轴=指标，横轴=口径”并设置不换行，属于展示文案修正，不影响后端接口与数据计算。

## 结构同步（2026-02-28 热力图网格错位联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端将热力图列布局由 `auto-fill` 改为按口径数固定列数，并在小屏采用横向滚动，属于展示层修复，不影响后端数据接口。

## 结构同步（2026-03-01 monthly_data_show 排查会话）

- 本轮后端代码无改动。
- 排查结论：
  - `backend/projects/monthly_data_show/api/workspace.py` 查询与对比接口定义完整，前端调用入口已对齐；
  - 待用户提供可复现 BUG 现象后执行针对性修复。

## 结构同步（2026-03-01 monthly_data_show 计算指标实时查询修复）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - 新增计算指标元数据：
    - `CALCULATED_ITEM_SET`（19 项）
    - `CALCULATED_ITEM_UNITS`（单位映射）
    - `CALCULATED_DEPENDENCY_MAP`（计算依赖关系）
  - 新增核心函数：
    - `_collect_required_base_items`：递归收集计算指标依赖的基础指标
    - `_compute_calculated_indicator`：按公式计算单个指标（缺失按 0、分母 0 按 0）
    - `_build_calculated_rows`：按查询维度分组生成计算指标结果行
  - 查询接口增强：
    - `POST /monthly-data-show/query` 支持“基础指标补查 + 实时计算 + 合并输出”
    - `POST /monthly-data-show/query-comparison` 所依赖的 `_fetch_compare_map` 同步支持计算指标窗口计算
- 效果：
  - 计算指标不依赖落库，可在查询与同比/环比中实时显示。

## 结构同步（2026-03-01 查询连通性排查）

- 本轮后端代码无新增改动。
- 运行排查结论：
  - 前端 `VITE_API_BASE` 与 `docker-compose` 端口映射一致（`127.0.0.1:8001`）；
  - `ERR_CONNECTION_REFUSED` 指向后端服务未监听（未启动或异常退出），非接口路径错误。

## 结构同步（2026-03-01 计算指标两轮计算）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - 新增 `_compute_calculated_two_pass(...)`，固定两轮计算计算指标。
  - `POST /monthly-data-show/query` 与 `query-comparison` 的 `_fetch_compare_map` 统一切换到两轮计算结果。
  - 依赖取值顺序优化：
    - 先取本轮缓存；
    - 再取上一轮已计算值；
    - 最后回退递归计算。
- 效果：
  - 计算指标依赖计算指标的场景展示更稳定，满足“两轮计算后显示”要求。

## 结构同步（2026-03-01 计算指标别名兜底）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - 新增 `METRIC_ALIAS_MAP`（同义指标映射），例如：
    - `耗标煤总量` ↔ `标煤耗量` / `煤折标煤量`
    - `供热耗标煤量` ↔ `供热标准煤耗量`
    - `发电耗标煤量` ↔ `发电标准煤耗量`
  - `_collect_required_base_items` 改为主指标+别名一并补查。
  - `_compute_calculated_indicator` 取值逻辑新增别名回退。
- 效果：
  - 在底层指标命名不一致时，计算链依赖仍可命中，提升 `发电水耗率/供热水耗率` 等指标准确性。

## 结构同步（2026-03-01 水耗率公式修订）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - 公式更新：
    - `发电水耗率 = (耗水量-供汽量-热网耗水量) * (1-热分摊比) / 发电量`
    - `供热水耗率 = ((耗水量-供汽量-热网耗水量) * 热分摊比 + 供汽量 + 热网耗水量) / 供热量`
  - 依赖更新：
    - 两指标依赖项均新增 `热网耗水量`。
- 效果：
  - 后端实时计算与最新业务口径一致。

## 结构同步（2026-03-01 查询排序按用户选择顺序）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - 新增 `_build_rank_map(...)` 构建用户选择顺序索引。
  - `_merge_and_sort_rows(...)` 新增 `rank_maps` 参数，排序时优先使用用户选择顺序。
  - `query` 结果排序改为：
    - 维度层级仍按 `order_fields`；
    - 同一层级内按用户勾选顺序（`companies/items/periods/types`）排序，文本顺序作为兜底。
- 效果：
  - 指标与口径展示顺序可与勾选次序对齐。

## 结构同步（2026-03-01 导出文件名与列同步联动）

- 本轮后端代码无改动。
- 联动说明：
  - 导出 XLSX 列与命名规则调整发生在前端页面层；
  - 后端接口返回结构保持不变。

## 结构同步（2026-03-01 query-comparison 新增计划比）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - `QueryComparisonRow` 新增字段：`plan_value`、`plan_rate`。
  - `QueryComparisonResponse` 新增字段：`plan_window_label`。
  - 新增 `_fetch_plan_value_map(...)`：
    - 在当前对比窗口内，以 `type='plan'` 查询计划值；
    - 同时支持基础指标与计算指标（复用计算引擎）。
  - `query-comparison` 组装结果时新增：
    - `plan_value`（计划值）
    - `plan_rate = (current - plan) / |plan|`
- 效果：
  - 对比接口支持同比/环比/计划比三种口径统一返回。

## 结构同步（2026-03-01 热力图与TopN统一口径切换开关联动）

- 本轮后端代码无改动。
- 联动说明：
  - 统一切换开关改动发生在前端查询页可视化层；
  - 后端 `query-comparison` 已提供 `yoy_rate/mom_rate/plan_rate` 三类速率字段，前端切换仅切换展示口径，不改变接口契约。

## 结构同步（2026-03-01 query-comparison 排序对齐筛选顺序）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - 新增 `_sort_comparison_rows(...)`，对 `QueryComparisonRow` 按 `order_fields` + 用户选择 rank 进行排序。
  - `query_month_data_show_comparison(...)` 增强：
    - 校验 `order_mode`；
    - 解析 `resolved_order_fields`；
    - 基于 `companies/items/periods/types` 构建 `rank_maps`；
    - 返回前调用 `_sort_comparison_rows(...)` 统一排序。
- 效果：
  - 同比/环比/计划比结果的口径与指标顺序与上方筛选选择顺序保持一致。

## 结构同步（2026-03-01 query-comparison 增加气温同比明细）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - `QueryComparisonResponse` 新增字段：`temperature_comparison`。
  - 新增模型：
    - `TemperatureDailyComparisonRow`
    - `TemperatureComparisonSummary`
    - `TemperatureComparisonPayload`
  - 新增 `_build_temperature_comparison_payload(...)`：
    - 从 `calc_temperature_data` 查询当前窗口与同比窗口逐日温度；
    - 输出逐日明细（本期日期/本期温度/同期日期/同期温度/同比差值/同比率）；
    - 计算并返回本期平均温度、同期平均温度及同比差值/差异率。
- 效果：
  - 当前端选择“平均气温”时，可直接获取该区间的逐日温度同比明细与均值对比数据。

## 结构同步（2026-03-01 XLSX导出样式优化与子表调整联动）

- 本轮后端代码无改动。
- 联动说明：
  - 导出样式优化与“移除热力图/TopN子表”均发生在前端导出层；
  - 后端接口返回结构未新增变化，保持与前端既有导出数据源兼容。

## 结构同步（2026-03-01 平均气温口径固定 common 并置顶）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
  - 新增常量：`AVERAGE_TEMPERATURE_COMPANY = "common"`。
  - 平均气温数据生成调整：
    - `_build_average_temperature_rows(...)` 不再按实际口径复制，统一输出 `company=common`。
    - `_fetch_compare_map(...)` 中平均气温对比键统一为 `common|平均气温|month|real|℃`。
  - 排序调整：
    - `_merge_and_sort_rows(...)` 与 `_sort_comparison_rows(...)` 增加“平均气温优先”排序键，使其在结果中前置显示。
- 效果：
  - “平均气温”指标从业务口径上与实际单位解耦，固定归入 `common`；
  - 查询结果与对比结果均可优先看到该指标。

## 结构同步（2026-03-01 差异率分母绝对值规则确认）

- 本轮后端代码无新增改动。
- 规则确认：
  - `query-comparison` 使用 `_calc_rate(current, base)` 统一计算同比/环比/计划比差异率；
  - 计算式为 `(current - base) / abs(base)`，分母固定取绝对值。

## 结构同步（2026-03-01 筛选项简化与简要分析文案改版联动）

- 本轮后端代码无改动。
- 联动说明：
  - “来源月份起止”筛选去除与“简要分析”报告化表达均在前端实现；
  - 后端接口契约保持兼容，允许 `report_month_from/report_month_to` 为空。

## 结构同步（2026-03-01 简要分析层次化逐项叙述联动）

- 本轮后端代码无改动。
- 联动说明：
  - 分层逐项报告由前端基于 `query-comparison` 返回数据和 `order_fields` 动态组织；
  - 后端继续提供同比/环比/计划比基础数据，无需新增接口字段。

## 结构同步（2026-03-01 隐藏期间/类型筛选联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端已将 `periods/types` 固定传为 `['month']/['real']`；
  - 后端接口继续按传入筛选处理，兼容固定值场景。

## 结构同步（2026-03-01 层次顺序与聚合开关布局优化联动）

- 本轮后端代码无改动。
- 联动说明：
  - “数据层次顺序 + 聚合开关”布局优化仅发生在前端页面样式与结构层；
  - 后端接口与数据契约保持不变。

## 结构同步（2026-03-01 层次顺序仅保留口径/指标联动）

- 本轮后端代码无改动。
- 联动说明：
  - 前端 `order_fields` 改为仅提交 `company/item`；
  - 后端排序解析仍兼容，未提交维度将按既有兜底逻辑处理。

## 结构同步（2026-03-01 层次顺序与聚合开关视觉对齐联动）

- 本轮后端代码无改动。
- 联动说明：
  - 本次为前端样式层微调，后端接口与排序逻辑不变。

## 结构同步（2026-03-01 业务月份筛选器体验优化联动）

- 本轮后端代码无改动。
- 联动说明：
  - 月份筛选体验优化发生在前端控件层；
  - 后端继续接收 `date_from/date_to` 范围参数，接口契约不变。

## 结构同步（2026-03-01 简要分析分层文本排版联动）

- 本轮后端代码无改动。
- 联动说明：
  - 分析区去圆点与层次排版属于前端呈现层改造；
  - 后端数据接口不受影响。

## 结构同步（2026-03-01 简要分析指标层文案精简联动）

- 本轮后端代码无改动。
- 联动说明：
  - “指标：”前缀去除为前端文案层调整，接口结构不变。

## 结构同步（2026-03-01 简要分析指标圆点与缩进联动）

- 本轮后端代码无改动。
- 联动说明：
  - 指标圆点与描述缩进属于前端排版层改造；
  - 后端接口不受影响。

## 结构同步（2026-03-01 简要分析数值单位展示联动）

- 本轮后端代码无改动。
- 联动说明：
  - 分析文本中“值+单位”展示为前端文案层改造；
  - 后端仍按原结构返回 `value` 与 `unit` 字段。

## 结构同步（2026-03-01 缺失上期值时省略环比段联动）

- 本轮后端代码无改动。
- 联动说明：
  - 环比段显示规则为前端文案拼接逻辑调整；
  - 后端继续返回 `mom_value/mom_rate`，由前端按可用性决定是否渲染。

## 结构同步（2026-03-01 对比列表隐藏期间/类型联动）

- 本轮后端代码无改动。
- 联动说明：
  - 对比表“期间/类型”隐藏为前端展示层调整；
  - 后端仍返回 `period/type` 字段，保持接口兼容性。

## 结构同步（2026-03-01 对比字段命名调整联动）

- 本轮后端代码无改动。
- 联动说明：
  - “本期值/同期值/上期值”命名调整为前端展示与导出表头改造；
  - 后端接口字段保持 `current_value/yoy_value/mom_value` 不变。

## 结构同步（2026-03-01 简要分析全零指标过滤联动）

- 本轮后端代码无改动。
- 联动说明：
  - 全零指标跳过规则为前端分析文案层逻辑；
  - 后端仍按原样返回对比数据。

## 结构同步（2026-03-01 简要分析口径标题高亮联动）

- 本轮后端代码无改动。
- 联动说明：
  - 口径标题加粗标色属于前端样式层增强；
  - 后端数据接口不受影响。

## 结构同步（2026-03-01 查询结果字段精简与月份控件优化联动）

- 本轮后端代码无改动。
- 联动说明：
  - 查询结果隐藏 `period/type` 与月份控件交互优化均为前端展示层调整；
  - 后端返回字段保持兼容。

## 结构同步（2026-03-01 日期快捷按钮右侧固定联动）

- 本轮后端代码无改动。
- 联动说明：
  - 日期按钮位置调整为前端样式层变更；
  - 后端接口不受影响。

## 结构同步（2026-03-01 按钮横排与标题强化联动）

- 本轮后端代码无改动。
- 联动说明：
  - 按钮横排修正、标题显眼度调整与“重置默认”移除均为前端展示层改造；
  - 后端接口契约保持不变。

## 结构同步（2026-03-01 按钮横排样式加固联动）

- 本轮后端代码无改动。
- 联动说明：
  - 日期快捷按钮“强制横排”与筛选标题再次增强为前端样式层优化；
  - 后端查询与对比接口保持不变。

## 结构同步（2026-03-01 月份行防重叠布局修复联动）

- 本轮后端代码无改动。
- 联动说明：
  - 月份行防重叠属于前端布局层调整；
  - 后端接口与查询逻辑不受影响。

## 结构同步（2026-03-01 移除月份行小按钮联动）

- 本轮后端代码无改动。
- 联动说明：
  - 移除月份行“本月/上月/同起始月”按钮为前端交互层调整；
  - 后端接口与默认月份逻辑保持不变。

## 结构同步（2026-03-01 移除快捷区间联动）

- 本轮后端代码无改动。
- 联动说明：
  - 去除“快捷区间”属于前端展示层精简；
  - 后端查询接口与默认值逻辑不受影响。

## 结构同步（2026-03-01 业务月份止默认上个月联动）

- 本轮后端代码无改动。
- 联动说明：
  - “业务月份止默认上个月”在前端默认值与重置逻辑中实现；
  - 后端接口契约不变。

## 结构同步（2026-03-01 业务月份止非必选联动）

- 本轮后端代码无改动。
- 联动说明：
  - “业务月份止（非必选）”文案与默认空值策略在前端实现；
  - 后端查询接口继续支持仅传起始月份。

## 结构同步（2026-03-01 monthly_data_show 指标配置驱动）

- 文件：
  - `backend/projects/monthly_data_show/services/indicator_config.py`（新增）
  - `backend/projects/monthly_data_show/api/workspace.py`
  - `backend/projects/monthly_data_show/services/extractor.py`
  - `backend_data/projects/monthly_data_show/indicator_config.json`（新增）
- 变更点：
  - 新增指标配置加载服务，统一提供：
    - 计算指标集合
    - 指标单位
    - 公式依赖
    - 公式执行（安全表达式求值）
    - 前端渲染配置载荷
  - `query-options` 新增返回 `indicator_config`，并按配置顺序输出指标。
  - 查询与同比环比计算改为“运行时刷新配置 + 按配置公式计算”。
  - 入库提取阶段“跳过计算指标”改为读取配置集合，不再硬编码。
- 联动说明：
  - 前端指标分区、顺序、公式弹窗已切换到配置下发；
  - 后续仅改 `indicator_config.json` 即可调整次序、公式和分类。

## 结构同步（2026-03-01 计算指标标题默认态兜底联动）

- 本轮后端代码无改动。
- 联动说明：
  - “计算指标（0项）”默认文案兜底为前端展示层调整；
  - 后端仍通过 `query-options.indicator_config` 提供正式指标配置。

## 结构同步（2026-03-01 指标配置增加基本分组结构）

- 文件：
  - `backend/projects/monthly_data_show/services/indicator_config.py`
  - `backend_data/projects/monthly_data_show/indicator_config.json`
- 变更点：
  - 配置新增 `basic_groups`（分组名 + 指标列表）；
  - 配置加载支持 `basic_groups` 优先解析，并向后兼容旧 `basic_items`；
  - `query-options.indicator_config` 同步下发 `basic_groups` 给前端。
- 联动说明：
  - 前端已改为按分组展示基本指标，后续分组调整仅需改 JSON 配置。

## 结构同步（2026-03-01 前端变量重名编译修复联动）

- 本轮后端代码无改动。
- 联动说明：
  - `Identifier 'current' has already been declared` 为前端脚本声明冲突；
  - 后端接口与配置结构保持不变。

## 结构同步（2026-03-01 其它指标分组补全）

- 文件：`backend_data/projects/monthly_data_show/indicator_config.json`
- 变更点：
  - 在 `basic_groups` 的 `【其他指标】` 下补充了配置缺失的基础指标条目。
- 联动说明：
  - 后端配置读取逻辑不变；
  - 前端按配置渲染后，未分组指标将进一步收敛。

## 结构同步（2026-03-01 指标配置路径修复）

- 文件：`backend/projects/monthly_data_show/services/indicator_config.py`
- 变更点：
  - 配置文件读取路径改为候选优先级：
    - `/app/data/projects/monthly_data_show/indicator_config.json`（容器挂载主路径）
    - `/app/backend_data/projects/monthly_data_show/indicator_config.json`（兼容回退）
- 效果：
  - 容器环境与本地开发环境均可读取到最新配置；
  - 分类名称、分组顺序与指标顺序可按用户配置即时生效。

## 结构同步（2026-03-01 基础指标单位配置化）

- 文件：
  - `backend/projects/monthly_data_show/services/indicator_config.py`
  - `backend_data/projects/monthly_data_show/indicator_config.json`
- 变更点：
  - 配置解析支持 `basic_groups.items[].unit`；
  - 当前基础指标分组项已补齐 `unit` 字段。
- 效果：
  - 基础指标单位可通过配置文件统一维护（与计算指标单位维护方式一致）。

## 结构同步（2026-03-01 指标选区隐藏单位（前端展示层））

- 本轮后端代码无改动。
- 联动说明：
  - 后端仍按配置文件下发指标单位字段（`indicator_config`）；
  - 前端仅调整为“不在指标选择区显示单位”，单位继续用于查询结果和分析文本展示。

## 结构同步（2026-03-01 导入指标映射新增“锅炉耗柴油量”）

- 文件：`backend/projects/monthly_data_show/services/extractor.py`
- 变更点：
  - `ITEM_RENAME_MAP` 新增映射：`"锅炉耗柴油量" -> "耗油量"`。
- 效果：
  - 月报导入工作台在提取阶段可将“锅炉耗柴油量”统一归一到“耗油量”，避免同义指标分裂。

## 结构同步（2026-03-01 金普期末供暖收费面积扣减规则）

- 文件：`backend/projects/monthly_data_show/services/extractor.py`
- 变更点：
  - 新增规则函数 `_apply_jinpu_heating_area_adjustment(rows)`；
  - 在 `extract_rows` 中接入：对 `company=金普` 的同窗口数据执行  
    `期末供暖收费面积 = 期末供暖收费面积 - 高温水面积`；
  - 结果单位统一为 `平方米`，并输出统计字段 `jinpu_heating_area_adjusted`。
- 效果：
  - 月报导入提取阶段可稳定执行该专属业务规则，后续入库与查询结果一致。

## 结构同步（2026-03-01 金普面积扣减规则命中增强）

- 文件：`backend/projects/monthly_data_show/services/extractor.py`
- 变更点：
  - 金普口径匹配由精确匹配升级为包含匹配（公司名含“金普”即命中）；
  - 规则指标名增加同义兼容：
    - 目标项：`期末供暖收费面积/期末供热面积/期末供暖面积`
    - 扣减项：`高温水面积/高温水供暖面积/高温水供热面积`
  - 同窗口多目标行逐条扣减。
- 效果：
  - 导入提取对不同月报文本写法更稳健，CSV 中金普面积值更符合业务规则。

## 结构同步（2026-03-01 查询页三项指标4位小数（前端展示层））

- 本轮后端代码无改动。
- 联动说明：
  - 前端查询页新增按指标控制小数位展示规则：`供暖热耗率/供暖水耗率/供暖电耗率` 默认 4 位小数；
  - 后端仍按原值下发，不改变存储与计算精度。

## 结构同步（2026-03-01 查询页三项指标差值4位小数（前端展示层））

- 本轮后端代码无改动。
- 联动说明：
  - 前端将三项指标的同比/环比/计划差值展示也统一为 4 位小数；
  - 后端数据接口与计算逻辑保持不变。

## 结构同步（2026-03-01 半计算补齐规则落地到提取链路）

- 文件：`backend/projects/monthly_data_show/services/extractor.py`
- 变更点：
  - 新增 `_apply_semicalculated_completion_rules(rows)`，按口径+同窗口（date/period/type/report_month）重写半计算指标；
  - 补齐“四、补充指标”中此前未落地项：`煤折标煤量`、`供热耗标煤量`、`耗电量`、`耗水量`、`热网耗水量`、`热网耗电量`、`供暖耗热量`；
  - 在 `extract_rows` 接入执行，新增统计字段 `semi_calculated_completed`；
  - 保留并继续执行规则5（金普期末供暖收费面积扣减）。
- 效果：
  - `extract-csv` 导出阶段直接生成补齐后的半计算指标，后续入库与查询链路使用同一结果基线。

## 结构同步（2026-03-01 extract-csv 规则命中统计下发）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
- 变更点：
  - `extract-csv` 接口读取 `extract_rows` 的统计并写入响应头：
    - `X-Monthly-Semi-Calculated-Completed`
    - `X-Monthly-Jinpu-Heating-Area-Adjusted`
    - `X-Monthly-Extracted-Total-Rows`
  - 增加 `Access-Control-Expose-Headers`，保证跨域场景前端可读取统计头。
- 效果：
  - 前端导入页可直接展示提取规则命中条数与总提取行数。

## 结构同步（2026-03-01 规则命中明细下发）

- 文件：
  - `backend/projects/monthly_data_show/services/extractor.py`
  - `backend/projects/monthly_data_show/api/workspace.py`
- 变更点：
  - 半计算补齐函数改为返回逐项命中明细字典；
  - `extract-csv` 在响应头新增 `X-Monthly-Rule-Details`（URL 编码 JSON）；
  - 暴露头部字段，确保前端可读取明细。
- 效果：
  - 前端可弹窗展示每条规则的命中明细，而不只是总计数字。

## 结构同步（2026-03-01 import-csv 返回新增/更新统计）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
- 变更点：
  - `import-csv` 的 UPSERT 增加 `RETURNING (xmax = 0) AS inserted`；
  - 统计并返回：
    - `inserted_rows`（新增）
    - `updated_rows`（更新）
  - `ImportCsvResponse` 模型同步新增字段。
- 效果：
  - 前端可区分“新增写入”与“同主键更新覆盖”，避免误判未入库。

## 结构同步（2026-03-01 import-csv 批量 RETURNING 兼容修复）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
- 变更点：
  - 修复 `executemany + RETURNING` 导致结果集关闭异常；
  - 改为逐行执行 UPSERT 并读取返回标志统计新增/更新。
- 效果：
  - 消除 `This result object does not return rows` 报错，入库流程恢复稳定。

## 结构同步（2026-03-01 金普面积扣减规则临时关闭）

- 文件：`backend/projects/monthly_data_show/services/extractor.py`
- 变更点：
  - 新增开关 `ENABLE_JINPU_HEATING_AREA_ADJUSTMENT = False`；
  - `extract_rows` 中仅开关开启时执行金普面积扣减规则。
- 效果：
  - 当前提取链路不再执行“金普期末供暖收费面积扣减”。

## 结构同步（2026-03-01 供暖耗热量规则调整：金普=供热量）

- 文件：`backend/projects/monthly_data_show/services/extractor.py`
- 变更点：
  - 半计算补齐规则中，“供暖耗热量”改为：
    - `金州/北方 = 供热量 - 高温水销售量`；
    - `金普/庄河/研究院/主城区电锅炉 = 供热量`。
- 效果：
  - 金普口径下“供暖耗热量”不再扣减高温水销售量，改为直接取供热量。

## 结构同步（2026-03-01 提取规则改为 monthly_data_pull 配置驱动）

- 文件：
  - `backend/projects/monthly_data_show/services/extractor.py`
  - `backend_data/projects/monthly_data_pull/mapping_rules/monthly_data_show_extraction_rules.json`
- 变更点：
  - 新增提取规则配置文件（剔除、重命名、默认源字段、常量、半计算规则、开关）；
  - 提取服务新增配置加载/刷新机制，接口执行时优先按配置运行，缺失时回退内置默认；
  - 半计算补齐改为通用规则引擎（`copy/sum/subtract`）按 `semi_calculated_rules` 执行。
- 效果：
  - 后续规则调整可直接改 JSON，无需改后端代码。

## 结构同步（2026-03-01 提取规则配置目录更正为 monthly_data_show）

- 文件：
  - `backend/projects/monthly_data_show/services/extractor.py`
  - `backend_data/projects/monthly_data_show/monthly_data_show_extraction_rules.json`
- 变更点：
  - 将提取规则配置文件从 `monthly_data_pull` 目录迁移到 `monthly_data_show` 目录；
  - 同步修正后端候选读取路径（容器与本地）到新位置。
- 效果：
  - 规则维护路径与项目归属一致，避免跨项目目录混淆。

## 结构同步（2026-03-01 提取规则可选执行）

- 文件：
  - `backend/projects/monthly_data_show/services/extractor.py`
  - `backend/projects/monthly_data_show/api/workspace.py`
- 变更点：
  - `inspect` 接口新增返回 `extraction_rules`（规则清单）；
  - `extract-csv` 新增入参 `extraction_rule_ids`，按所选规则执行提取；
  - 支持规则粒度：指标剔除、指标重命名、半计算规则子项、金普面积扣减；
  - 提取统计新增：`item_exclude_hits`、`item_rename_hits`、`selected_rule_ids`，并随详情头回传。
- 效果：
  - 后端可按前端勾选子集执行规则，且可追踪本次实际命中情况。

## 结构同步（2026-03-01 规则清单描述增强）

- 文件：`backend/projects/monthly_data_show/services/extractor.py`
- 变更点：
  - `get_extraction_rule_options()` 为规则下发补充可读描述；
  - 半计算规则描述可自动生成（口径、目标指标、计算表达式、单位）。
- 效果：
  - 前端规则选择弹窗可展示更完整的规则说明，便于人工核对。

## 结构同步（2026-03-01 已禁用规则不再下发到弹窗）

- 文件：`backend/projects/monthly_data_show/services/extractor.py`
- 变更点：
  - `get_extraction_rule_options()` 仅在 `ENABLE_JINPU_HEATING_AREA_ADJUSTMENT=True` 时下发“金普面积扣减”规则。
- 效果：
  - 已取消的金普面积扣减规则不会出现在前端规则弹窗中。

## 结构同步（2026-03-01 CSV 空值 token 增加“-”）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
- 变更点：
  - `NULL_VALUE_TOKENS` 增加单个 `-`。
- 效果：
  - 导入 CSV 时 `value='-'` 会按空值写入（NULL），并计入空值统计。

## 结构同步（2026-03-01 多月聚合状态值按最后一期）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
- 变更点：
  - 新增状态值集合 `LATEST_VALUE_ITEMS`（含 `期末供暖收费面积`、`发电设备容量`、`锅炉设备容量` 等）；  
  - 聚合 SQL 增加分支：状态值取最后一期，其他指标继续求和；  
  - 应用范围：查询页多月聚合、同比/环比窗口聚合、计划窗口聚合。
- 效果：
  - 状态值指标不会因跨月而被累计求和，结果符合“取最后一期”的业务口径。

## 结构同步（2026-03-01 环比窗口自然月对齐修复）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
- 变更点：
  - 新增 `_resolve_mom_window(current_start, current_end)`；
  - 当当前窗口是自然整月时，环比窗口改为上月整月（而非同天数滚动）；
  - 非整月窗口继续使用滚动窗口。
- 效果：
  - 月报按月首日记账场景下，26.2 查询可正确命中 26.1 环比数据。

## 结构同步（2026-03-02 查询结果中文列头与列序联动）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
- 变更点：
  - 本轮后端接口与排序逻辑无新增代码改动（延续上一轮“数据层次顺序真实生效”修复）。
- 联动说明：
  - 前端已基于 `order_fields` 动态重排查询结果列，并将 `date/report_month` 转为“YYYY年M月”显示；
  - 后端继续提供 `company/item/date/value/unit` 原始字段，供前端按层次顺序重组展示与导出。

## 结构同步（2026-03-02 环比窗口支持多月等长回溯）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
- 变更点：
  - 调整 `_resolve_mom_window(current_start, current_end)`：
    - 当当前窗口是“连续自然月区间”（月初到月末）时，环比窗口改为“向前紧邻、等月数”的自然月区间；
    - 例如：`2026-01-01~2026-02-28` 对应环比 `2025-11-01~2025-12-31`；
    - 非自然月区间继续使用滚动天数窗口逻辑。
- 效果：
  - 多月窗口查询时，环比值不再只取前一单月，改为与当前窗口长度一致的上期自然月区间。

## 结构同步（2026-03-02 导出文件名区间化联动）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
- 变更点：
  - 本轮后端无代码改动。
- 联动说明：
  - 导出文件名区间化由前端 `MonthlyDataShowQueryToolView.vue` 处理，不影响后端查询/对比接口协议。

## 结构同步（2026-03-02 管理后台数据表查询增强）

- 文件：`backend/api/v1/admin_console.py`
- 变更点：
  - `DbTableQueryPayload` 新增参数：`search`、`filters`、`order_by`、`order_dir`；
  - `POST /admin/db/table/query` 增强：
    - 支持全字段关键字模糊检索（`ILIKE`）；
    - 支持字段级筛选（`eq/ne/contains/starts_with/ends_with/gt/gte/lt/lte/is_null/not_null`）；
    - 支持指定字段升降序排序（非法字段回退主键/首列排序）；
    - 计数查询与分页查询共享同一筛选条件，返回 `total` 与当前页数据一致。
- 效果：
  - 数据库在线编辑页具备实际可用的查询筛选能力，不再仅限“无条件分页浏览”。

## 结构同步（2026-03-02 月报查询单月默认范围修正联动）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
- 变更点：
  - 本轮后端无代码改动。
- 联动说明：
  - 前端查询页已在“仅填写业务月份起”时自动补齐当月 `date_to`，后端按既有 `date_from/date_to` 规则执行单月查询。

## 结构同步（2026-03-02 月份框体样式修正联动）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
- 变更点：
  - 本轮后端无代码改动。
- 联动说明：
  - 月份选择框体包裹问题为前端样式修复，不影响后端接口与查询逻辑。

## 结构同步（2026-03-02 AI 报告模式化与用户附加提示词）

- 文件：
  - `backend/services/data_analysis_ai_report.py`
  - `backend/projects/daily_report_25_26/api/legacy_full.py`
  - `backend/services/data_analysis.py`
- 变更点：
  - AI 报告核心新增模式注册机制：`daily_analysis_v1`、`monthly_analysis_v1`；
  - 提示词构建支持 `ai_mode_id` 选择模板，并支持 `ai_user_prompt` 作为本次附加要求；
  - 日报分析查询入参新增 `ai_mode_id`、`ai_user_prompt`，并在触发任务时透传；
  - 任务快照增加 `ai_mode_id` 字段，便于排查与审计。
- 效果：
  - 现有日报智能报告默认模式保持兼容；
  - 月报可后续按 `monthly_analysis_v1` 无缝接入同一套 AI 引擎。

## 结构同步（2026-03-02 月报查询页 AI 报告接口接入）

- 文件：`backend/projects/monthly_data_show/api/workspace.py`
- 变更点：
  - 新增月报 AI 接口：
    - `POST /monthly-data-show/ai-report/start`
    - `GET /monthly-data-show/ai-report/{job_id}`
  - 新增月报数据 -> 通用 AI payload 适配函数：
    - 将 `comparison_rows` 映射为统一 `rows` 结构；
    - 注入环比 `ringCompare` 与计划比较 `plan_comparison` 数据；
    - 默认 `ai_mode_id=monthly_analysis_v1`，支持 `ai_user_prompt`。
- 效果：
  - 月报查询页面可复用通用 AI 引擎异步生成报告，无需复制日报专用逻辑。

## 结构同步（2026-03-02 AI 模式提示词拆分：日报/月报独立）

- 文件：`backend/services/data_analysis_ai_report.py`
- 变更点：
  - 保持 `daily_analysis_v1` 原有提示词模板不变；
  - 为 `monthly_analysis_v1` 新增独立的内容/核查/修订/极速模式提示词模板；
  - `AI_MODE_TEMPLATE_REGISTRY` 中月报模式不再复用日报模板。
- 效果：
  - 日报与月报报告生成语义彻底解耦，后续可独立迭代两套提示词策略。

## 结构同步（2026-03-02 AI 配置跨项目共享与月报提示词）

- 文件：
  - `backend/services/project_data_paths.py`
  - `backend/services/data_analysis_ai_report.py`
  - `backend/projects/daily_report_25_26/api/legacy_full.py`
  - `backend/api/v1/admin_console.py`
  - `backend_data/shared/ai_settings.json`
- 变更点：
  - 新增全局 AI 配置解析函数 `resolve_global_ai_settings_path()`，标准路径切换为 `backend_data/shared/ai_settings.json`；
  - AI 报告服务读取配置改为“shared 优先 + 日报旧配置回退”，避免一次迁移导致功能中断；
  - AI 设置新增 `instruction_monthly` 字段，支持月报专用预设提示词；
  - 管理后台 AI 设置读写链路已兼容新字段并写入全局配置。
- 效果：
  - AI 配置从“日报项目内”升级为“跨项目共享”；
  - 日报既有 instruction 保持兼容，月报可独立维护提示词。

## 结构同步（2026-03-02 月报默认提示词内容更新）

- 文件：`backend_data/shared/ai_settings.json`
- 变更点：
  - `instruction_monthly` 更新为新的月报分析系统提示词（含对比逻辑、归因逻辑、结构化呈现、五模块报告框架）。
- 效果：
  - 月报 AI 报告生成将默认使用新的管理会计导向提示词模板。

## 结构同步（2026-03-02 shared AI 配置合并日报参数）

- 文件：`backend_data/shared/ai_settings.json`
- 变更点：
  - 将日报项目配置 `backend_data/projects/daily_report_25_26/config/api_key.json` 的关键字段合并至 shared：
    - `gemini_model`
    - `gemini_api_keys`
    - `instruction`（日报）
    - `report_mode`
    - `enable_validation`
    - `allow_non_admin_report`
  - 保留 `instruction_monthly`（月报）不变，实现双提示词共存。
- 效果：
  - `shared/ai_settings.json` 成为统一主配置，满足跨项目读取需求。

## 结构同步（2026-03-02 AI 配置收口与字段标准化）

- 文件：
  - `backend/services/project_data_paths.py`
  - `backend/services/data_analysis_ai_report.py`
  - `backend/projects/daily_report_25_26/api/legacy_full.py`
  - `backend/api/v1/admin_console.py`
  - `backend_data/shared/ai_settings.json`
  - `backend_data/projects/daily_report_25_26/config/api_key.json`（已删除）
- 变更点：
  - 全局 AI 配置路径统一为 `backend_data/shared/ai_settings.json`，不再回退日报项目内 `api_key.json`；
  - 提示词字段标准化为：
    - `instruction_daily`
    - `instruction_monthly`
  - AI 设置接口读写同步为新字段，并保留旧 `instruction` 入参的兼容接收；
  - shared 配置中旧键 `instruction` 已改名为 `instruction_daily`。
- 效果：
  - 配置源唯一化，跨项目配置管理更稳定；
  - 日报/月报提示词边界清晰，便于独立维护。

## 结构同步（2026-03-02 旧 api_key 正式下线）

- 文件：
  - `backend_data/projects/daily_report_25_26/config/api_key.json`（已删除）
  - `backend_data/shared/ai_settings.json`
  - `backend/services/project_data_paths.py`
  - `backend/services/data_analysis_ai_report.py`
- 变更点：
  - 删除日报项目内旧 AI 配置文件；
  - 全局路径解析不再回退旧路径，统一指向 shared；
  - 日报提示词读取与存储键固定为 `instruction_daily`。
- 效果：
  - 彻底消除双配置源并发风险，配置行为可预期。

## 结构同步（2026-03-02 月报 AI 报告4段式独立结构）

- 文件：`backend/services/data_analysis_ai_report.py`
- 变更点：
  - 月报模板章节固定为4段（`overview` / `coal_completion` / `profit_cost_breakdown` / `efficiency_and_actions`）；
  - 新增 `_normalize_sections_for_mode()`，月报模式下强制章节顺序与标题骨架；
  - 报告 HTML 渲染按模式分流：
    - 日报保留同比/环比/计划/逐日明细等硬性块；
    - 月报改为“月度关键对比图表”+ 4段正文，不再复用日报硬性块。
- 效果：
  - 日报与月报分析结构解耦；
  - 月报更贴合经营简报写法，形成图文并茂的4段式报告输出。

## 结构同步（2026-03-02 月报页 AI 设置入口联动）

- 本轮后端代码无新增改动。
- 联动说明：
  - 月报页面新增“智能体设定”入口，继续调用既有全局 AI 设置接口：
    - `GET/POST /admin/ai-settings`
  - 权限仍由后端统一校验（需具备 AI 设置管理权限）。

## 结构同步（2026-03-02 前端 AI 设置弹窗通用化联动）

- 本轮后端代码无新增改动。
- 联动说明：
  - 日报与月报页面已统一复用同一 AI 设置组件；
  - 组件仍分别调用既有接口：
    - 日报：`GET/POST /projects/{project_key}/data_analysis/ai-settings`
    - 月报管理：`GET/POST /admin/ai-settings`
  - 后端鉴权与配置落盘路径（`backend_data/shared/ai_settings.json`）保持不变。

## 结构同步（2026-03-02 AI 设置输入框宽度前端优化联动）

- 本轮后端代码无新增改动。
- 联动说明：
  - 前端共享组件调整了 API Key 输入框布局与响应式宽度；
  - 后端接口与数据结构保持不变，无需迁移。

## 结构同步（2026-03-02 AI 报告限流重试与输入瘦身）

- 文件：`backend/services/data_analysis_ai_report.py`
- 变更点：
  - Gemini 调用链新增 429/Quota 自动重试：
    - 识别限流/配额错误；
    - 读取错误文本中的 `retry_delay` 或 `retry in` 秒数；
    - 采用“至少 20 秒”退避后重试（最多 3 次）。
  - Prompt 数据新增分级压缩：
    - 裁剪指标数量、timeline 长度与对比明细；
    - 必要时移除 `timeline_matrix`；
    - 控制传模 JSON 大小，降低输入 token 超限风险。
- 效果：
  - 无需 key 轮换即可缓解高并发/大窗口下的 429 中断；
  - 报告生成流程稳定性提升。  

## 结构同步（2026-03-02 月报报告版式独立渲染）

- 文件：`backend/services/data_analysis_ai_report.py`
- 变更点：
  - 新增 `_generate_monthly_report_html(...)` 月报专用 HTML 渲染；
  - `_generate_report_html(...)` 按 `ai_mode_id` 分流：月报模式直接使用独立版式；
  - 月报不再沿用日报的卡片+趋势图主模板，改为正式简报风格（章节正文 + 对比附表）。
- 效果：
  - 日报/月报报告样式与结构彻底分离；
  - 月报输出更贴近经营简报阅读习惯。  

## 结构同步（2026-03-03 月报简报式排版增强）

- 文件：`backend/services/data_analysis_ai_report.py`
- 变更点：
  - 重写月报渲染函数 `_generate_monthly_report_html(...)`，进一步收敛为公文简报式结构：
    - 标题 + 元信息；
    - 四段章节正文（按月报模式章节）；
    - 附关键指标同比表；
    - 智能核对结果简表。
  - 继续保持与日报渲染链路分离，不回退到日报看板风格。
- 效果：
  - 月报报告在行文观感与版式上更接近正式运行简报。  

## 结构同步（2026-03-03 月报报告双图补齐）

- 文件：`backend/services/data_analysis_ai_report.py`
- 变更点：
  - 在月报专用渲染函数中新增 ECharts 图表区；
  - 增加两张图：
    - 同比差异率 Top10（绝对值）；
    - 本期值 Top10（绝对值）。
- 效果：
  - 月报报告不再仅有文字和表格，满足“至少两张图”的展示要求。  

## 结构同步（2026-03-03 登录 404 修复）

- 文件：`backend/projects/daily_report_25_26/api/legacy_full.py`
- 变更点：
  - 修复 `AiSettingsPayload` 的 `Field(...)` 使用未导入问题；
  - `from pydantic import BaseModel, ValidationError` 调整为 `from pydantic import BaseModel, Field, ValidationError`。
- 影响链路：
  - 该异常会阻断 `backend/api/v1/routes.py` 导入，导致 `backend/main.py` 不挂载 `/api/v1` 路由；
  - 修复后 `POST /api/v1/auth/login` 恢复可访问（空体返回 422，非 404）。

## 结构同步（2026-03-03 智能体设定不保存退出前端联动）

- 本轮后端代码无新增改动。
- 联动说明：
  - 前端共享智能体设定组件新增“退出（不保存）”按钮；
  - 后端 AI 设置读写接口与数据结构保持不变，无需迁移。

## 结构同步（2026-03-03 AI 报告进度展示前端联动）

- 本轮后端代码无新增改动。
- 联动说明：
  - 前端在日报/月报页面新增 AI 报告进度可视化；
  - 继续复用后端任务状态字段 `status` 与 `stage`，无需新增接口。

## 结构同步（2026-03-03 月报导出数值格式前端联动）

- 本轮后端代码无新增改动。
- 联动说明：
  - 月报查询页导出 XLSX 已改为前端写入数值单元格与格式化规则；
  - 后端仍返回原始数值/单位字段，无需调整接口。
## 结构同步（2026-03-04 模板设计器第一期收尾）

- 已确认并保持以下链路一致：
  - 路由挂载：`projects/daily_report_25_26/api/router.py` 引入并 `include_router(template_designer_router)`
  - 接口实现：`projects/daily_report_25_26/api/template_designer.py`（列表/详情/创建/更新/发布）
  - 模板存储：`backend_data/projects/daily_report_25_26/config/template_designer_templates.json`
  - 权限入口：`backend_data/shared/auth/permissions.json` 中 `template_designer` 页面权限
## 结构同步（2026-03-04 模板设计器入口可见性修复）

- 文件：`api/v1/routes.py`
- 调整：在 `list_project_pages` 过滤页面列表前，增加模板设计器入口兜底逻辑。
- 规则：当账号在项目下 `actions.can_manage_modularization=true` 且项目配置存在 `template_designer` 页面时，即使 `page_access` 漏配，也保留该入口。
- 目的：避免“功能已上线但页面入口不可见”的权限配置错配问题。
## 结构同步（2026-03-04 模板设计器入口迁移联动）

- 本次需求为入口位置调整，主要发生在前端：
  - 管理后台新增“模板设计器（新表）”入口按钮；
  - 页面选择页隐藏 `template_designer` 卡片。
- 后端接口与模板存储链路保持不变，仍由 `template_designer` API 负责。
## 结构同步（2026-03-04 模板设计器拖拽版前端联动）

- 本轮拖拽设计能力仅涉及前端页面重构：
  - `TemplateDesignerView` 新增行列拖拽、预览网格与 JSON 兼容编辑。
- 后端保持不变：
  - 继续使用 `template_designer` 既有接口（列表/详情/创建/更新/发布）；
  - 不涉及数据库结构与后端路由变更。
## 结构同步（2026-03-04 模板设计器页面壳层统一前端联动）

- 本轮仅调整模板设计器前端页面壳层与导航组件接入：
  - 补齐 `AppHeader` 与 `Breadcrumbs`；
  - 对齐统一页面容器样式。
- 后端接口与权限逻辑不变。
## 结构同步（2026-03-04 模板设计器标签闭合修复前端联动）

- 本次为前端模板页面标签闭合修复，后端接口与逻辑无变更。
## 结构同步（2026-03-04 模板设计器动态导入 500 修复前端联动）

- 本次修复为前端模板页面标签闭合补齐，后端无改动。
## 结构同步（2026-03-04 模板设计器固定字段可选前端联动）

- 本次实现为前端模板设计器交互增强：
  - 固定字段可选与默认值配置写入模板 `meta`；
  - 后端接口协议不变，继续透传 `meta` 字段。
## 结构同步（2026-03-04 模板设计器类 Excel 画布增强前端联动）

- 本轮为前端模板设计器交互能力增强：
  - 行列拖拽、列宽与连接配置写入 `meta`。
- 后端接口保持不变：
  - 通过既有模板创建/更新/发布接口透传扩展后的 `meta` 结构。
## 结构同步（2026-03-04 模板设计器交互修复前端联动）

- 本次为前端拖拽交互修复（手柄化拖拽），后端接口无改动。

## 结构同步（2026-03-05 模板设计器入口并列标签化前端联动）

- 本次改动为管理后台入口形态调整（独立按钮 -> 并列标签），仅涉及前端页面结构。
- 后端模板设计器接口与权限逻辑无改动，继续沿用：
  - `projects/daily_report_25_26/api/template_designer.py`
  - `projects/daily_report_25_26/api/router.py` 中 `/template_designer` 路由挂载

## 结构同步（2026-03-05 长表设计器方案评审联动）

- 本轮后端代码无改动，完成“长表设计器成熟方案”评审与接口升级方向定义。
- 现状基线：
  - `daily_basic_data` 已为长表结构，并具唯一索引 `(company, sheet_name, item, date)`；
  - 当前 `template_designer.py` 的 `columns/rows/meta` 为通用壳，缺少强约束语义。
- 规划方向：
  - 在保持现有接口可用的前提下，逐步强化 `meta`：引入字段契约、计算图、校验图、发布契约；
  - 发布阶段增加模板静态检查与样例回放检查，避免把问题模板发布到生产填报链路。

## 结构同步（2026-03-05 下线模板设计器页面联动）

- 路由清理：
  - `backend/projects/daily_report_25_26/api/router.py` 已移除 `template_designer` 子路由挂载。
- 接口清理：
  - 删除 `backend/projects/daily_report_25_26/api/template_designer.py`。
- 页面可见性清理：
  - `backend/api/v1/routes.py` 已移除对 `template_designer` 的页面可见性兜底逻辑。
- 配置清理：
  - `backend_data/shared/项目列表.json` 删除 `template_designer` 页面定义；
  - `backend_data/shared/auth/permissions.json` 删除 `template_designer` 页面权限键。
- 现状：
  - 后端不再暴露模板设计器 API，项目页面列表与权限模型中也不再包含该页面。

## 结构同步（2026-03-05 管理后台“看板功能设置”前端联动）

- 本轮后端代码无改动，复用既有看板接口能力：
  - `/dashboard/date`（读取 `set_biz_date`）
  - `/dashboard/temperature/import`（气温导入预览）
  - `/dashboard/temperature/import/commit`（气温写库）
  - `/admin/cache/*`（缓存发布/刷新/停止/禁用）
- 前端管理后台已将上述能力聚合到同一设置区，便于集中操作。

## 结构同步（2026-03-05 管理后台气温按钮反馈增强前端联动）

- 本轮后端无改动，前端提示逻辑已对齐后端返回字段：
  - 预览接口：`summary.total_hours`、`overlap`、`differences`、`dates`
  - 入库接口：`write_result.inserted`、`write_result.replaced`

## 结构同步（2026-03-05 管理后台气温导入弹框确认前端联动）

- 本轮后端无改动，前端将气温导入改为“预览 -> 弹框确认 -> 入库”流程：
  - 预览接口：`/dashboard/temperature/import`
  - 入库接口：`/dashboard/temperature/import/commit`

## 结构同步（2026-03-05 管理后台气温弹框逐小时一致性前端联动）

- 本轮后端无改动，前端在弹框中消费预览接口返回 `overlap_records`，展示逐小时接口值/数据库值与一致性状态。

## 结构同步（2026-03-05 项目后台页面移除日志统计区块前端联动）

- 本轮为前端页面展示收敛，后端接口无改动。

## 结构同步（2026-03-05 月报查询页指标分组全选/取消前端联动）

- 本轮为前端筛选交互增强，后端接口无改动。

## 结构同步（2026-03-05 月报查询页全选改单按钮切换前端联动）

- 本轮为前端交互调整，后端接口无改动。

## 结构同步（2026-03-05 月报查询页子分类单按钮切换前端联动）

- 本轮为前端交互细化，后端接口无改动。

## 2026-03-06 本地开发环境排查补记
- 本次仅排查 VS Code 在打开 `.py` 文件后自动执行 `Activate.ps1` 的现象。
- 仓库内未发现后端目录相关的 VS Code 工作区配置；结合终端输出，判断为 Python 扩展在识别到 Python 文件后自动激活已选解释器环境。
- 激活目标为 `d:\编程项目\phoenix_project\.venv`，提示当前解释器选择可能落在相邻项目环境上，而不是本仓库专属环境。

## 2026-03-06 本地环境补记
- 进一步确认 `D:\编程项目\phoenix_project` 不属于当前后端仓库目录。
- 该目录现存内容以 `.venv` 与 `@google/gemini-cli` 依赖为主，未见当前后端业务源码；从当前仓库运行角度看不是必需目录。
- 但 VS Code 目前把 Python 解释器指向该目录 `.venv`，删除前应先改回正确解释器。

## 结构同步（2026-03-06 前端移动端表格与录入页优化第一轮）
- 本轮变更仅发生在前端展示层，后端接口、字段命名与数据返回结构未改。
- 受影响前端页面：
  - `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`
  - `frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue`
- 联动结论：
  - 手机端体验优化通过前端断点样式、横向滚动容器和局部列裁剪完成；
  - 后端无需新增接口，也无需为移动端单独返回另一套数据结构；
  - 现有查询、导入和录入链路保持兼容。

## 结构同步（2026-03-06 前端移动端表格与录入页优化第二轮）
- 第二轮继续扩展到：
  - `frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`
  - `frontend/src/projects/daily_report_25_26/pages/DashBoard.vue`
- 联动结论：
  - 新增能力仍全部位于前端响应式容器与样式断点层；
  - 后端查询、分析、看板接口无需改动；
  - 当前移动端适配策略继续保持“桌面端默认不变，窄屏下局部横滑与密度收敛”。

## 结构同步（2026-03-06 前端移动端优化第三轮：入口页与文案收敛）
- 第三轮继续覆盖：
  - `frontend/src/pages/LoginView.vue`
  - `frontend/src/pages/ProjectSelectView.vue`
  - `frontend/src/pages/ProjectEntryView.vue`
  - `frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue`
- 联动结论：
  - 本轮依旧没有新增后端接口需求；
  - 调整重点在前端入口观感与交互文案收敛，保持现有接口完全兼容。

## 结构同步（2026-03-06 数据填报页顶部开关紧凑化修正）
- 本次修正仅涉及 `frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue` 的移动端顶栏布局。
- 后端接口与权限开关语义未改，仅前端手机断点下的排列方式调整为更紧凑的块状布局。

## 结构同步（2026-03-06 月报查询页与拉取页顶部密度收敛）
- 本次继续涉及：
  - `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`
- 联动结论：
  - 调整仍全部位于前端响应式布局层；
  - 后端查询、导表、权限和数据结构均无变化。

## 结构同步（2026-03-06 Banner 与按钮文字换行规整修正）
- 本次继续涉及前端样式层：
  - `frontend/src/projects/daily_report_25_26/components/AppHeader.vue`
  - `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`
- 联动结论：
  - 仅调整文字换行与按钮排版规则；
  - 后端接口与数据结构无变化。

## 结构同步（2026-03-07 月报查询页“重置”按钮手机端溢出修正）
- 本次仅涉及 `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue` 的移动端按钮区布局。
- 联动结论：
  - 仅前端手机断点修正；
  - 后端接口与数据结构无变化。

## 结构同步（2026-03-07 全局 AppHeader 手机端重排）
- 本次仅涉及 `frontend/src/projects/daily_report_25_26/components/AppHeader.vue` 的前端头部布局。
- 联动结论：
  - 仅前端全局头部在手机端的分层重排；
  - 后端接口与数据结构无变化。

## 结构同步（2026-03-07 Phoenix 手机页面优化 Skill 草案）
- 本次新增项目内 skill 文档：
  - `configs/skills/phoenix-mobile-layout/SKILL.md`
- 联动结论：
  - 该 skill 为项目协作规范沉淀，不涉及后端接口与数据结构变更。

## 结构同步（2026-03-06 项目选择页桌面卡片高度回退）
- 本次仅涉及 `frontend/src/pages/ProjectSelectView.vue` 的桌面端卡片高度回退。
- 联动结论：
  - 仅前端展示密度修正；
  - 后端接口与数据结构无变化。

## 结构同步（2026-03-06 后端依赖版本锁定）
- `backend/requirements.txt` 中原先未锁定的直接依赖已改为固定版本。
- 为减少 `google-generativeai` 链路导致的回溯，还额外显式锁定：
  - `grpcio==1.76.0`
  - `grpcio-status==1.71.2`
- 验证：
  - 本机执行 `python -m pip install --dry-run -r backend/requirements.txt` 成功，未出现版本冲突。

## 结构同步（2026-03-06 后端 Docker pip 镜像源切换）
- `backend/Dockerfile.prod` 的 builder 阶段已新增：
  - `PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple`
  - `PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn`
- 联动结论：
  - 仅影响 Docker 构建时的 Python 依赖下载来源；
  - 不影响运行期接口、数据结构与业务逻辑。

## 2026-03-08 前端联动说明（DataAnalysis 按钮位置）
- 本轮无后端接口、服务、模型或 SQL 变更。
- 前端仅调整 `DataAnalysisView` 的智能报告相关按钮位置，后端调用链路保持不变。

## 2026-03-08 前端联动说明（DataAnalysis 二次微调）
- 本轮仍为前端展示层微调，无后端接口、服务或数据结构变更。
- 仅调整 `DataAnalysisView` 的按钮顺序与标题对齐样式。

## 2026-03-08 月报智能体设定权限前端对齐
- 本轮无后端代码变更。
- 月报前端已改为使用 `monthly_data_show` 项目动作权限 `can_manage_ai_settings`，与后端鉴权口径保持一致。

## 2026-03-08 前端联动说明（AI 气泡文案）
- 本轮无后端改动。
- 前端仅调整 AI 气泡入口文案为“智能助手”。

## 结构同步（2026-03-08 admin-console 操作日志页前端恢复）

- 本次为前端模板修复，后端审计接口未改动。
- 继续使用既有接口：
  - `GET /api/v1/admin/audit/events`
  - `GET /api/v1/admin/audit/stats`
  - `POST /api/v1/audit/events`
- 说明：前端恢复渲染后，现有审计查询链路可正常被使用。

## 结构同步（2026-03-08 审计日志真实客户端 IP）

- 文件：`backend/api/v1/admin_console.py`
- 接口：`POST /api/v1/audit/events`
- 调整：审计日志记录 IP 改为优先解析代理头（`X-Forwarded-For` 首个地址，其次 `X-Real-IP`），无法解析时回退 `request.client.host`。
- 说明：适配 Nginx/反向代理部署，避免日志仅记录容器宿主机或代理地址。
## 结构同步（2026-03-08 管理后台日志页签范围调整）

- 本次需求为前端行为收敛，后端接口与服务实现未改动。
- 受影响前端行为：
  - 审计事件上报不再由应用入口全局触发；
  - 改为仅在管理后台“操作日志”页签启用采集。
- 后端现状：
  - `/admin/audit/events` 与 `/admin/audit/stats` 接口保持不变；
  - `backend/services/audit_log.py` 无需调整。

## 结构同步（2026-03-08 更正：前端撤回采集范围收敛）

- 根据用户确认，前端撤回“仅在 audit 页签采集”的改动。
- 后端接口与服务仍无变更：
  - `/admin/audit/events`
  - `/admin/audit/stats`
  - `backend/services/audit_log.py`

## 结构同步（2026-03-08 仅展示修复）

- 本次仅修复前端页签条件渲染，后端无代码改动。
- 审计相关接口与服务保持不变：
  - `/admin/audit/events`
  - `/admin/audit/stats`
  - `backend/services/audit_log.py`

## 生产环境故障记录（2026-03-09）

- **故障现象**：Oracle 服务器重启后，登录接口 `/api/v1/auth/login` 返回 504。
- **排查结论**：
  - 后端应用正常（`127.0.0.1:8000/healthz` 响应 200）。
  - 故障源于 Docker 网络元数据损坏，`phoenix-web` 无法连接到 `phoenix-backend:8000`。
  - 删除网络后出现 `network not found` 残留引用错误。
- **运维建议**：
  - 需强制清理生产环境残留容器。
  - 使用 `docker network prune` 清理孤立端点。
  - 建议在 `lo1_new_server.yml` 中更换全新子网（`172.30.25.0/24`）以强制刷新 IPAM。
- **详见**：`configs/3.9 docker故障记录.md`。

## 外部接口分析记录（2026-03-09，辽宁省发改委现货电价）

- 本轮后端无代码改动。
- 已确认站外现货电价页面的实际数据接口为：
  - `POST https://fgw.ln.gov.cn/indexview/api/getListData`
  - `POST https://fgw.ln.gov.cn/indexview/api/getLine`
- 其中 `getListData` 的请求体仅需 `{"date":"YYYY-MM-DD"}`，适合作为后端定时采集入口。
- 单日返回口径：
  - `data` 固定 24 行；
  - 每行含 4 组 `name/beforeTime/realTime`；
  - 合并后对应 96 个 15 分钟时点。
- 已实测 `2026-01-01` 至 `2026-03-09` 共 68 天：
  - `2026-01-01` 至 `2026-03-08` 数据完整；
  - `2026-03-09` 结构存在，但价格字段全为空字符串，应按“未发布”处理。
- 若后续接入 Phoenix 后端，建议：
  - 采集时保留原始日期与原始字符串；
  - 增加“全空日”判定，避免误入库为 0；
  - 可用 `getLine` 返回的 `xData/before/realTime` 作为图表校验辅助数据。

## 外部接口抓取脚本（2026-03-09，辽宁省发改委现货电价）

- 新增脚本：
  - `backend/services/liaoning_spot_price_fetcher.py`
- 定位：
  - 独立 CLI，不依赖现有 FastAPI 路由；
  - 适合手工执行或后续接到定时任务。
- 默认行为：
  - 直接执行时默认抓取 `2026-01-01` 到 `2026-03-08`；
  - 默认过滤“全空占位日”；
  - 默认输出单个 JSON 到 `backend_data/liaoning_spot_price_2026-01-01_2026-03-08.json`；
  - 仍支持导出 JSON/CSV。
- JSON 结构：
  - 采用 `days[] -> points[]` 的按天分组格式；
  - `biz_date` 仅保留在每天节点，点位内不再重复；
  - `points[]` 已按 `time_label` 从 `00:15` 到 `24:00` 递增排序。
- 关键参数：
  - `--start-date YYYY-MM-DD`
  - `--end-date YYYY-MM-DD`
  - `--output-json <path>`
  - `--output-csv <path>`
  - `--include-empty-days`
- 已完成最小验证：
  - `python backend/services/liaoning_spot_price_fetcher.py --start-date 2026-03-08 --end-date 2026-03-09`
  - 实际输出为仅保留 `2026-03-08`，`2026-03-09` 因全空被默认过滤。
- 已完成默认行为验证：
  - `python backend/services/liaoning_spot_price_fetcher.py`
  - 已生成：
    - `D:\编程项目\phoenix\backend_data\liaoning_spot_price_2026-01-01_2026-03-08.json`
- 依赖说明：
  - 脚本已改为仅依赖 Python 标准库；
  - 不再要求安装 `httpx`。
# 后端结构说明

## 2026-03-10 结构同步

- `backend/projects/monthly_data_show/services/extractor.py`
  - 运行时已不再依赖旧 `item_rename_map`，当前仅使用 `item_rename_rules`。
  - 新增 `unit_normalize_rules`，单位字符串归一与数值换算由配置驱动。
  - 导出 CSV 时额外追加 `item_transform_type`、`item_transform_note` 两列：
    - `item_transform_type`：如 `指标更名`、`单位转换`、`常量注入`、`半计算`；
    - `item_transform_note`：如 `A→B`、`千瓦时→万千瓦时`、`源1 + 源2→目标指标`。
  - 这两列仅用于步骤 3/3.1 留痕，不参与步骤 4 入库。

- `monthly_data_show/import-workspace` 的“步骤 3.1：标准表对照”为纯前端分支：
  - 本轮未新增后端接口；
  - 对照表 CSV 基于步骤 3 已提取的标准化结果在前端本地生成，保留 `company,item,item_transform_note` 三列并按 `company+item` 去重聚合说明。

- `backend/projects/monthly_data_show/api/workspace.py`
  - 修复计算指标分组口径：默认按 `date`（业务月份）聚合，不再把 `report_month` 一并作为分组键。
  - 仅在显式使用 `report_month_*` 查询来源月份窗口时，才保留 `report_month` 分组。
  - 查询结果排序时间维度也改为优先使用 `date`，`report_month` 仅作回退。
  - `query-comparison` 新增同比/计划窗口完整性校验：
    - 同比值仅在同比窗口逐月齐备时返回；
    - 计划值仅在计划窗口逐月齐备时返回；
    - 若窗口内缺任一月份，则视为不可比，返回 `null`，避免局部月份数据冒充整段窗口结果。
- `backend/projects/monthly_data_show/services/extractor.py`
  - 抽取规则新增 `item_rename_rules`：
    - 每条规则独立声明 `source/target/companies`；
    - `companies=[\"all\"]`：对全部未被 `blocked_companies` 屏蔽的子工作表生效；
    - `companies=[\"北海\"]`：仅对指定子工作表生效。
  - 抽取时会按当前子工作表标题逐条匹配适用规则，再执行指标标准化。
  - 旧 `item_rename_map` 与旧 `scope/rename_map` 结构仍保留兼容兜底。
  - 导出 CSV 时额外追加 `item_transform_note` 字段，用于标记指标是否经更名规则转换（如 `A→B`）；该字段不参与步骤 4 入库。
