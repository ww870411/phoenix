# 前端说明（Vue3 + Vite）

## 平台名称展示微调（2026-03-10）
- 登录页 `frontend/src/pages/LoginView.vue` 的副标题已进一步收敛为“生产经营数据智算平台”，不再重复集团全称。
- 浏览器页签标题 `frontend/index.html` 已改为“大连洁净能源集团生产经营数据智算平台”，与用户指定口径完全一致。
- 登录后顶部 banner `frontend/src/projects/daily_report_25_26/components/AppHeader.vue` 的副标识已由“数据填报平台”改为“数据智算平台”。

## 登录页与站点标题改名（2026-03-10）
- 登录页 `frontend/src/pages/LoginView.vue` 的主视觉副标题已由“生产数据在线填报平台”统一改为“大连洁净能源集团 生产经营数据智算平台”。
- 登录页底部版权文案已由 `© 2025 大连洁净能源集团有限公司 · 经济运行部` 改为 `© 2025-2026 大连洁净能源集团有限公司 · 经济运行部`。
- 站点页签标题 `frontend/index.html` 已同步更新为“大连洁净能源集团 生产经营数据智算平台”，保证浏览器标签与登录页文案一致。

## 月报导入工作台补充（2026-03-10）

- `src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue` 新增“步骤 3.2：标准表比对”。
- 该功能要求用户分别上传两份由步骤 3.1 导出的对照 CSV，字段口径至少包含 `company`、`item`，可选携带 `item_transform_type`、`item_transform_note`。
- 比对在浏览器本地完成，不新增后端接口，也不影响原步骤 3 的提取下载或步骤 4 的 CSV 入库。
- 比对主口径是 `company`：系统会先按口径分组，再在同一口径内部比较 `item`；不会再把同名指标拿到不同口径下做候选匹配。
- 比对输出会生成可下载诊断 CSV，核心列包括：
  - `result_type`
  - `reason_category`
  - `standard_company`
  - `standard_item`
  - `nonstandard_company`
  - `nonstandard_item`
  - `reason_detail`
- 诊断逻辑优先识别三类问题：
  - 口径缺失：标准口径或待比对口径在另一侧根本不存在
  - 标准表缺失于待比对：同口径下标准表有而待比对没有
  - 待比对表多出项：同口径下待比对有而标准表没有

## 事故记录补充（2026-03-09）

- 本轮按用户要求新增独立文档：`configs/3.9 docker故障记录.md`。
- 该文档用于汇总本次“服务器重启后 Docker 环境错乱，导致登录 504”的完整过程，便于交由外部 Docker/运维专家继续处理。

## 登录 504 排障记录（2026-03-09）

- 当前登录页 `src/pages/LoginView.vue` 只负责采集用户名、密码、记住状态，并调用 `useAuthStore().login(...)`。
- 实际登录请求由 `src/projects/daily_report_25_26/services/api.js` 中的 `login(credentials)` 发起，目标固定为 `${API_BASE}/auth/login`。
- 用户 2026-03-09 提供的控制台证据显示：
  - 浏览器已成功发出 `POST https://platform.smartview.top/api/v1/auth/login`
  - 返回为 Cloudflare `504 Gateway time-out` HTML 页面
- 这说明前端路由与请求构造已生效，故障点不在登录页组件本身，而在线上服务器对 `/api` 的回源链路。
- 联动判断：
  - 若首页可访问而登录接口 504，优先怀疑 `web` 容器到 `backend` 容器的反代异常，或后端处理登录时被数据库阻塞。
- 2026-03-09 服务器新增实测进一步确认：
  - `phoenix-web` 与 `phoenix-backend` 同属 `25-26_phoenix_net`；
  - `phoenix-web` 错误日志为 `while connecting to upstream`，目标 upstream 是 `http://172.19.0.3:8000/api/v1/auth/login`；
  - 因而前端与 Nginx 入口都正常，真正异常点已经收敛到“backend 容器内部 8000 端口未监听或未成功拉起服务”。
- 第二轮实测修正结论（2026-03-09）：
  - `phoenix-backend` 容器内 `127.0.0.1:8000/healthz` 已返回正常；
  - 因此前端登录 504 的直接根因不再是后端应用未启动，而是 `phoenix-web` 到 `phoenix-backend` 的容器间网络链路异常。
- 第三轮服务器操作补充（2026-03-09）：
  - 停掉 Phoenix 容器后，`25-26_phoenix_net` 已被 Docker 自动移除；
  - 因此前端侧后续无需围绕“手工删网络失败”继续排障，直接等待正确生产栈重新拉起即可。
- 第四轮服务器观察修正（2026-03-09）：
  - 即使 `docker ps` 为空，`25-26_phoenix_net` 仍可能保留；
  - 这是 Docker 自定义 bridge 网络的正常行为，不代表前端或 Nginx 配置再次异常。
- 后续进展（2026-03-09）：
  - Phoenix 旧网络 `25-26_phoenix_net` 已被成功删除；
  - 前端当前无需再围绕旧网络残留现象排障，下一步直接等待新网络随 compose 重建并验证 `web -> backend` 链路。

## 最新结构与状态（2026-02-28）

- 日报分析页智能报告触发逻辑改造（2026-03-08）：
  - `src/projects/daily_report_25_26/pages/DataAnalysisView.vue` 已从“查询阶段自动触发报告”改为“查询后手动触发报告”。
  - 交互调整：
    - 查询按钮仅生成分析结果；
    - 新增独立“生成智能报告”按钮；
    - “下载智能分析报告”按钮仅用于下载已生成内容。
  - 与月报查询页触发节奏对齐，支持先看结果再决定是否生成报告。

- 月报查询页 500 异常联动修复（2026-03-08）：
  - 针对 `GET /api/v1/projects/monthly_data_show/monthly-data-show/query-options` 初始化阶段 500，后端已增加异常降级返回策略。
  - 前端表现：即使后端底层配置/数据库存在异常，页面不再因 500 直接白屏，可先进入页面并继续排障。
  - 本轮前端源码无新增改动（仅联动记录）。

- 月报查询页 CORS 修复（2026-03-08）：
  - 调整 `src/projects/daily_report_25_26/services/api.js` 的 API 基址策略：
    - 本机开发（`localhost/127.0.0.1`）且后端基址同为本机时，强制回落为同源 `'/api/v1'`；
    - 通过前端同源代理转发，避免浏览器跨域拦截。
  - 新增函数：`shouldPreferSameOriginProxy(base)`。
  - 影响：`monthly_data_show/query-options` 等请求不再默认直连 `127.0.0.1:8001`，本机开发稳定性提升。

- AI 气泡开关刷新回弹兜底修复（2026-03-08）：
  - 日报分析页与月报查询页在页面初始化时，都会额外主动读取 AI 设置接口中的 `show_chat_bubble`，并覆盖本地显示开关。
  - 新增覆盖状态 `chatBubbleOverride`，优先级高于 `schema/query-options` 内的气泡标记。
  - 变更文件：
    - `src/projects/daily_report_25_26/pages/DataAnalysisView.vue`
    - `src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 效果：关闭并保存后，刷新页面仍保持隐藏（以 AI 设置实时值为准）。

- AI 气泡开关刷新后回弹修复（2026-03-08）：
  - 对配置类接口读取统一增加 `cache: 'no-store'`，避免浏览器/中间层返回旧值导致刷新后回弹。
  - 变更函数（`src/projects/daily_report_25_26/services/api.js`）：
    - `getDataAnalysisSchema`
    - `getMonthlyDataShowQueryOptions`
    - `getAiSettings`
    - `getAdminAiSettings`
  - 结果：关闭气泡并保存后，刷新页面仍保持隐藏状态。

- AI 气泡显示开关即时生效修复（2026-03-08）：
  - 关闭“显示 AI 聊天气泡”并保存后，日报分析页与月报查询页现在会立即同步隐藏气泡，无需手动刷新。
  - 修复点：
    - `src/projects/daily_report_25_26/pages/DataAnalysisView.vue`
    - `src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 技术实现：`saveAiSettingsPayload` 改为异步，并将保存接口返回的 `show_chat_bubble` 回写到页面本地状态（`schema.ai_report_flags` / `options.aiChatFlags`）。

- AI 自由对话气泡缺陷修复（2026-03-08）：
  - 组件 `src/projects/daily_report_25_26/components/AiChatWorkspace.vue` 已修复父层文案参数不生效问题，支持页面传入：
    - `free-description`
    - `query-description`
    - `free-placeholder`
    - `query-placeholder`
  - 输入框回车策略改为：`Enter` 发送、`Shift+Enter` 换行，避免此前手动追加换行导致的输入异常。
  - 数据分析模式下 `buildQueryContext` 抛错时，组件会展示“构建查询上下文失败”提示，不再静默中断。
  - 消息内容样式新增 `white-space: pre-wrap; word-break: break-word;`，多行/长文本显示更稳定。

- 构建慢过程分析同步（2026-03-06）：
  - 本轮为部署构建性能分析，不涉及前端代码改动；
  - 结论已记录至 `configs/progress.md`，用于指导后续镜像构建优化；
  - 前端模块、路由与页面行为保持不变。
- 构建慢过程二次观察同步（2026-03-06）：
  - 新日志已从“依赖回溯提示”转为“Installing collected packages”长耗时；
  - 该现象属于后端镜像构建阶段，前端构建链路无新增异常。

- 月报查询页临时隐藏“对话查询助手”入口（2026-03-05）：
  - 页面：`src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`；
  - 处理：通过样式规则隐藏包含 `.chat-panel` 的卡片区块；
  - 说明：仅隐藏 UI，未删除原有对话逻辑与接口调用代码，后续可快速恢复。

- 月报查询页对话助手升级为“连续会话 + 联网来源可视化”（2026-03-05）：
  - 页面：`src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`；
  - 新增：`chatSessionId`、`chatWebSources` 状态，发送消息自动携带 `session_id` 维持连续上下文；
  - 新增：“新会话”按钮，可一键清空当前会话上下文并重新开始；
  - 新增：联网检索来源列表展示（标题 + 链接），便于追溯外部信息来源；
  - 对后端响应的 `web_sources`、`session_id` 做兼容处理，不影响原有查询页主流程。

- 月报查询页新增“对话查询助手（BETA）”（2026-03-05）：
  - 页面：`src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`；
  - 能力：用户以自然语言提问后，前端调用新接口执行受控查询，并显示 AI 结论与数据预览；
  - 请求会携带当前筛选上下文（时间范围/口径/指标/排序层次/聚合开关），避免对话与页面筛选脱节；
  - 原有“查询按钮 + 智能报告生成”流程保持不变。
- 月报对话 API 封装新增（2026-03-05）：
  - 文件：`src/projects/daily_report_25_26/services/api.js`；
  - 新函数：`queryMonthlyDataShowAiChat(projectKey, payload)`；
  - 路径：`POST /projects/{projectKey}/monthly-data-show/ai-chat/query`。
- 模板设计器（新表）第一期骨架（2026-03-04）：
  - 新增页面：`src/projects/daily_report_25_26/pages/TemplateDesignerView.vue`。
  - 新增路由：`/projects/:projectKey/pages/:pageKey/template-designer`。
  - 页面入口联动：`PageSelectView.vue` 增加 `template_designer` 的描述与跳转分支。
  - 新增 API 封装：模板列表/详情/创建/更新/发布（`services/api.js`）。
  - 当前能力：管理员可在项目内创建与维护“新表模板”，并发布模板版本；既有日报页面不受影响。
- AGENTS 协作规范升级联动（2026-03-04）：
  - 仓库根 `AGENTS.md` 已更新为多项目现行规范，前端侧目录口径明确为 `src/projects/*`（不再沿用旧的单项目路径描述）。
  - 协作要求继续保持：每轮改动后同步 `configs/progress.md` 与前后端 README，并在交付中说明模块/函数/流程/结果。
- 数据看板 PDF 图标导出修复（2026-03-04）：
  - 文件：`src/projects/daily_report_25_26/pages/DashBoard.vue`。
  - 根因：顶部四个摘要卡片图标使用 `::before + mask-image(data:svg)`，`html2canvas` 导出截图时对该渲染方式兼容不稳定，导致 PDF 图标空白。
  - 实现：在 `downloadPDF` 的 `onclone` 阶段调用 `injectPdfSafeSummaryIcons`，向克隆文档注入内联 SVG 图标，并以导出专用样式禁用 `::before`，保证 `html2canvas` 可稳定捕获。
  - 二次修复：将导出内联 SVG 的 `path fill` 由 `currentColor` 调整为克隆 DOM 实际计算色值，修复 PDF 中图标发黑问题。
  - 三次修复：为彻底规避克隆态颜色计算漂移，导出图标填充色固定为 `#ffffff`，确保顶部四卡在 PDF 中视觉稳定。
  - 四次修复：在导出克隆样式中关闭 `.summary-card__icon` 的背景/阴影/滤镜/边框，去除 PDF 中图标周围“小方框”伪影。
  - 影响：仅作用于 PDF 导出克隆 DOM，页面实时样式与交互不变。
- AI 聊天上下文与气泡开关（2026-03-07）：
  - 数据分析页“基于查询数据”聊天上下文已改为优先使用当前单位完整查询结果，而不是仅使用预览行；
  - 月报页在聊天前会尽量补拉全量查询结果，避免只用默认 200 行分页数据；
  - 智能体设定新增“显示 AI 聊天气泡”开关，日报页与月报页都会消费该配置决定是否显示悬浮聊天入口；
  - 聊天 `query_context` 模式的系统提示词改为固定业务文案，不再额外叠加 `instruction_monthly` / `instruction_daily`。
  - `show_chat_bubble` 保存链路已修复：前端 `updateAiSettings/updateAdminAiSettings` 现在会把该字段一并提交给后端。

- AI 聊天调试面板布局修复（2026-03-07）：
  - 调试面板中的“最近错误 / 最近返回结果”已上移到顶部；
  - 调试区新增独立滚动，发送消息后不会再轻易被内容挤出可视区域。

- AI 聊天页面内调试面板（2026-03-07）：
  - `AiChatWorkspace.vue` 现已内置“调试信息”面板；
  - 可直接查看最近一次：
    - 发送 payload
    - 返回结果
    - 错误信息
    - 当前 mode / session_id
  - 用于继续分段排查聊天链路问题。

- AI 聊天链路排障（2026-03-07）：
  - 后端新增聊天 debug 回显接口，用于分段确认“前端请求是否进入后端聊天模块”；
  - 当前已确认日报聊天接口能够正确识别：
    - `provider = newapi`
    - `model = gpt-5.4`
    - `base_url = https://ai.xingyungept.cn/v1`

- AI 聊天器显示修复（2026-03-07）：
  - `AiChatWorkspace.vue` 已修复长文本撑破弹窗的问题；
  - 对超长连续字符串新增自动断行策略（`overflow-wrap: anywhere`），聊天消息会优先在弹窗内部换行。
  - 聊天输入框补充 `box-sizing:border-box` 与宽度约束，不再超出悬浮弹窗。

- AI 聊天器交互优化（2026-03-07）：
  - `AiChatWorkspace.vue` 改为右下角悬浮图标展开式交互；
  - 默认不显示欢迎语，第一轮对话由用户主动发起；
  - 若浏览器侧出现 `Failed to fetch`，前端会提示优先检查后端是否已重启并加载新聊天接口；
  - 开发环境已在 `frontend/vite.config.js` 中为 `/api` 配置代理到 `127.0.0.1:8001`；修改后需要重启 Vite 开发服务器生效；
  - 日报分析页已移除单独聊天卡片，仅保留悬浮聊天入口。

- AI 聊天器初版（2026-03-07）：
  - 新增共享组件 `frontend/src/projects/daily_report_25_26/components/AiChatWorkspace.vue`；
  - 在月报查询页与日报分析页接入两种聊天模式：
    - 自由聊天
    - 基于当前查询数据包聊天
  - 月报页上下文来自 `rows / comparisonRows / summary / temperatureSummary / buildPayload()`；
  - 日报分析页上下文来自 `previewRows / lastQueryMeta / timelineGrid / ringCompare / planComparison`；
  - 两个页面分别调用新的聊天接口，不再依赖旧报告服务私有函数。

- **Docker 代理路径修正（2026-03-07）**：
  - `vite.config.js` 的 `target` 修正为 `http://backend:8000`，解决了在容器环境下无法通过 `127.0.0.1:8001` 访问后端的问题。
- AI 模块专家级重构与排障（2026-03-07）：
  - **路径自适应**：后端已修复 `DATA_DIRECTORY` 硬编码问题，现在支持在本地开发环境下自动定位 `backend_data`，解决了配置文件加载失败导致的聊天中断。
  - **结构化对话**：后端 `ai_runtime.py` 与 `ai_chat_service.py` 已全面升级为 `messages` 数组模式（System/User/Assistant），不再使用简单的字符串拼接。
  - **回复质量提升**：通过 System Role 注入“凤凰计划助手”身份，AI 对话更专业、上下文连贯性更强。
  - **兼容性**：前端调用接口路径与数据格式保持不变，无感升级。

- 智能体设定增强（2026-03-07）：
  - `AiAgentSettingsDialog.vue` 修复 provider“标识 ID”输入失焦问题，列表稳定 key 改为内部 `uiKey`；
  - 新增“测试全部 New API”按钮，测试结果直接显示在各 provider 卡片内；
  - New API provider 新增“打开站点”按钮，会从 `base_url` 推导站点根链接并新窗口打开；
  - 每个 provider 新增“备选模型”编辑区，可一键把备选模型切换为当前主模型。
  - 每个 provider 卡片新增“测试当前”按钮，并改为默认折叠，仅在头部显示名称与模型名，点击后展开详情。
  - provider 卡片头部新增“当前生效 / 备用”标记，并支持一键“设为当前”切换生效 provider。
  - 底部全局“测试连接”按钮已移除，测试入口统一收敛为“测试当前”与“测试全部 New API”。

- 智能体设定 UI 升级（2026-03-03）：
  - 新增多 Provider 管理（每项独立 `base_url/api_keys/model`）；
  - 新增“当前生效 Provider”选择；
  - 页面改为折叠分组布局（基础设置/Provider 管理/提示词设置/运行策略）；
  - 主按钮改为“保存并退出”。
- New API 报告超时兼容优化（2026-03-03）：
  - 后端已增加 504/5xx 自动退避重试与 New API 提示词压缩，前端无需改操作即可受益。
- AI 设置弹窗新增“测试连接”（2026-03-03）：
  - 统一组件 `AiAgentSettingsDialog.vue` 新增测试按钮；
  - 日报分析页/月报查询页/管理后台均已接入；
  - 支持在保存前按当前 provider 参数执行连通性测试。
- New API 调用诊断增强（2026-03-03）：
  - 后端对 `403/1010` 返回更明确错误信息（含请求 URL），前端可直接据此检查 provider 的 base_url 与网关限制。
- AI 设置弹窗双通道扩展（2026-03-03）：
  - 统一组件 `AiAgentSettingsDialog.vue` 新增 `provider` 切换（Gemini / New API）；
  - 新增 New API 字段输入：`Base URL / API Keys / 模型`；
  - 日报页、月报页、全局管理后台继续共用同一弹窗与同一份后端配置；
  - 前端 API 封装 `updateAiSettings / updateAdminAiSettings` 已支持 provider/newapi 字段透传。
- 月报查询层次顺序生效修复（2026-03-02）：
  - 调整“数据层次顺序”（如“口径 -> 指标 -> 时间”）后，查询结果将按该顺序真实分层展示；
  - 不再固定按默认时间优先排序。
- 月报查询页层次排序增强（2026-03-02）：
  - “数据层次顺序”新增“时间”选项；
  - 默认顺序改为“时间 -> 口径 -> 指标”；
  - 跨月区间查询时，结果按月份先后展示（如 26.1 在前，26.2 在后）。
- 已联动完成月报表名纠偏（2026-03-02）：
  - 月报导入页与查询页文案中的数据库表名已改为 `monthly_data_show`；
  - 前端调用路径不变，后端运行时已切换到新表名，页面无需额外改参。
- 全局管理后台“后台文件编辑”页新增数据库表在线编辑能力（2026-03-01）：
  - 页面位置：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`；
  - 能力：选择数据表、分页加载、行内编辑、批量保存；
  - 默认可直接编辑 `monthly_data_show`，并支持切换其他表（后端返回清单）。
- 已联动修复 `monthly_data_show` 环比缺失问题（2026-03-01）：
  - 当查询窗口为自然整月（如 `2026-02-01 ~ 2026-02-28`）时，后端环比窗口改为“上月自然整月”（`2026-01-01 ~ 2026-01-31`）；
  - 前端无需改动请求参数，重新查询后可直接显示 26.2 对 26.1 的环比值。
- 已联调修复登录跨域阻断：后端 CORS 默认允许 `localhost/127.0.0.1` 的常见开发端口，前端登录页无需改动接口路径即可通过预检。
- 已联调追加 CORS 兼容加固：后端新增 `localhost/127.0.0.1` 任意端口正则匹配，降低本地端口切换导致的预检失败概率。
- 已规避本地端口冲突：开发环境 API 基础地址调整为 `http://127.0.0.1:8001`（对应 compose 后端映射 `8001:8000`），避免与外部导表程序默认 `8000` 冲突。
- 已完成“外部导表程序”在线化可行性调研，结论为：前端可承接该流程，但后端执行内核需先从 `xlwings` 解耦后再接入线上容器。
- 现有可复用前端能力：
  - 项目级路由与权限链路已稳定，可新增“月报导表”页面并复用登录态与项目访问控制；
  - 现有文件上传、任务状态反馈、结果下载等交互模式可直接复用到导表流程。
- 建议前端接入形态（待实现）：
  - 在 `frontend/src/projects/daily_report_25_26/pages/` 新增导表页面；
  - 页面流程建议固定为“上传映射表/源表/底表 -> 预检 -> 执行 -> 下载结果/差异报告”；
  - 与后端新导表 API 解耦对接，不改现有数据填报页 `DataEntryView.vue` 的在线填报主流程。
- 已新增导表项目入口骨架：
  - 入口分发页：`frontend/src/pages/ProjectEntryView.vue`
  - 新项目页面：`frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`
  - 项目选择页已将 `monthly_data_pull` 设为直达入口项目。
- `monthly_data_pull` 页面现已升级为三步导表流程：
  - 步骤1：上传映射并解析关系分组；
  - 步骤2：按分组完成“源文件 ↔ 目标底表”匹配与 sheet 选择；
  - 步骤3：执行导表并下载输出文件。
- `monthly_data_pull` 页面视觉已与主项目对齐：
  - 顶部统一使用 `AppHeader`；
  - 页面内补充 `Breadcrumbs` 导航（项目选择 -> 月报导表工作台）。

## 结构补充（2026-02-28，导表引擎调研）

- 导表在线化后端候选引擎已补充 LibreOffice Headless 路线评估。
- 前端侧结论：页面交互形态无需因引擎切换而重构，可继续沿用“上传 -> 执行 -> 下载”前后端分离模式。

## 最新结构与状态（2026-02-08）

- 项目目录已统一：`frontend/src/projects/`
  - `daily_report_25_26` 与 `daily_report_spring_festval_2026` 均已归位到该目录；
  - 全局壳层页保留在 `frontend/src/pages/`（登录、项目选择）。
- 项目入口页：`frontend/src/pages/ProjectSelectView.vue`
  - 页面展示数据来自 `useProjects -> services/api.js -> GET /api/v1/projects`；
  - 项目顺序与后端 `backend_data/shared/项目列表.json` 键顺序一致；
  - 当前第二位项目为 `mini_project_demo`（迷你项目示例），仅保留单页面线性流程入口。
- 新增春节项目直达页：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalEntryView.vue`
  - 路由：`/projects/daily_report_spring_festval_2026`（不经过 `/pages` 选择页）；
  - 功能：上传 xlsx、调用后端提取 JSON、页面预览，并通过“生成数据看板”跳转到迷你看板页；
  - API：`frontend/src/projects/daily_report_spring_festval_2026/services/api.js` 适配项目专属调用，底层复用共享请求函数。
- 新增春节迷你看板页：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
  - 路由：`/projects/daily_report_spring_festval_2026/spring-dashboard`；
  - 卡片：当日平均气温、当日集团标煤消耗、当日总投诉量、当日净投诉量；
  - 图表：气温变化（含同期）、标煤消耗量对比、投诉量分项（图+表）；
  - 数据来源：上传提取 JSON 负责煤耗/投诉；气温始终通过数据库接口（复用 `getDashboardData('daily_report_25_26')`）读取。
  - 稳健性：看板页读取提取结果采用“内存缓存 + sessionStorage + localStorage”三级回退，避免路由跳转后图表空白。
  - 进一步稳健化：提取接口会将结果同步保存到后端运行时文件，迷你看板支持从 `/spring-festival/latest-json` 回读，避免浏览器存储命中失败导致空白。
- 主要页面目录：`frontend/src/projects/daily_report_25_26/pages/`
  - `DataEntryView.vue`：模板拉取、在线填报、提交与回填
  - `DataAnalysisView.vue`：多单位分析、同比/环比、AI 报告交互
  - `DashBoard.vue`：数据看板、趋势图、缓存与导出
- 全局壳层页面目录：`frontend/src/pages/`
  - `ProjectSelectView.vue`：项目列表入口
  - `LoginView.vue`：全局登录页入口（已从项目目录迁出）
- 核心组件目录：`frontend/src/projects/daily_report_25_26/components/`
  - `UnitAnalysisLite.vue`：填报页内本单位轻量分析
  - 其他 RevoGrid/ECharts 相关展示组件
- 服务层：
  - `frontend/src/projects/daily_report_25_26/services/api.js` 对接后端 `/template`、`/submit`、`/query`、`/data_analysis/*`、`/dashboard` 等接口
- 当前联调说明：
  - 后端已完成煤炭库存提交链路去重与模板 JSON 缓存优化，前端接口契约未变，无需改动请求参数即可继续使用。
  - `frontend/jsconfig.json` 已补充 `compilerOptions.baseUrl = "."`，与 `vite.config.js` 中的 `@` 别名配置保持一致，避免编辑器路径映射报错。
  - 项目模块化结构对照文档已落地：`configs/2.8项目模块化.md`（可用于核对旧/新目录和迁移关系）。
  - 发布缓存链路已修复日期配置回退：`/dashboard/cache/publish` 在项目化目录场景会正确读取 `shared/date.json`，不再误报“日期配置文件不存在”。

## 数据看板运维流程优化（2026-02-08）

- `pages/DashBoard.vue` 的“发布缓存”区域新增“发布天数”选择（`1天 / 3天 / 7天`，默认 `1天`）。
- 发布动作会调用 `publishDashboardCache(projectKey, { days })`，对应后端接口：
  - `POST /dashboard/cache/publish?days=...`
- 建议日常流程：
  - 当日导入气温后，优先使用 `1天` 发布，完成后再下载 PDF；
  - 仅在需要补历史缓存时再切到 `3天/7天`。

## 项目模块化第一步协作说明（2026-02-08）

- 本轮仅后端实施“配置路径项目化兼容层”，前端页面与路由结构暂未改动。
- 现有前端仍按 `daily_report_25_26` 项目包运行；接口路径与参数保持兼容。
- 后续若进入第二步（前端项目壳路由与动态项目包），将基于本轮后端路径能力继续推进。

## 项目模块化第一步增强协作说明（2026-02-08）

- 本轮继续增强后端：将项目列表与鉴权相关全局配置路径纳入 `shared` 兼容层；前端代码与调用协议保持不变。
- 前端无新增改动点，仍可按现有流程访问项目列表、登录与页面路由。

## 项目模块化过渡工具协作说明（2026-02-08）

- 后端已新增“迁移状态查询/一键初始化”接口，面向系统管理员使用：
  - `GET /projects/daily_report_25_26/project/modularization/status`
  - `POST /projects/daily_report_25_26/project/modularization/bootstrap`
- 前端暂未接入专用管理页面；现阶段可通过 API 调试工具调用。

## 会话小结（2026-01-03 数据分析净投诉量新口径说明）

- 后端 `analysis_company_sum/analysis_groups_sum` 的 `amount_daily_net_complaints_per_10k_m2` 现以终止日 `sum_season_total_net_complaints` 除 `amount_heating_fee_area` 计算，取代旧的“区间内当日净投诉量求和”算法。前端可直接沿用现有接口展示，数值含义自动更新为“终止日累计投诉折算面积”，无需额外处理。
- 主城区与集团的“万㎡净投诉量”卡片、数据分析表格、仪表盘投诉区均会读取视图新结果即可，与 UI 层逻辑完全解耦；如需验证，可在浏览器网络面板检查 `/data_analysis/query` 的该指标值，相比旧版本会与终止日的累计投诉保持一致。
- 本次无前端源码改动，此处仅记录口径更新，方便排查数据差异；如需回滚旧口径，只需恢复后端 SQL，前端展示逻辑不必调整。

## 会话小结（2025-12-31 计划比较百分比展示修复）

- 数据分析页、填报页本单位分析以及 AI 报告下载的“计划比较”区块均直接使用 `/data_analysis/query` 的 `plan_comparison.entries`。后端现将 `rate_overall_efficiency` 这类百分比指标在返回前统一乘以 100，因此页面与导出文案会显示为 “80.00%” 而非 “0.80%”，无需前端额外处理。
- 若未来新增其它百分比指标，也会通过同一后端集合自动缩放；前端继续沿用现有格式（`formatPercent` 等）即可，无需判断 0-1 小数。

## 会话小结（2025-12-30 数据分析计划比较数据恢复）

- 后端 `_build_plan_comparison_payload` 改为按月份前缀匹配 `paln_and_real_month_data.period`，除 `period LIKE 'YYYY-MM%'` 外，还会通过 `regexp_replace(period, '[^0-9]', '', 'g') LIKE 'YYYYMM%'` 抓取“月底日期”“2025年11月”这类字符串，解决最近导入的计划值无法返回 `plan_comparison` 的问题。
- 前端数据分析页与本单位分析组件读取到新的 `plan_comparison_note` 字段，在无计划值或跨月区间时会显示原因提示；只要选择同一自然月且计划表有数据，原有“计划比较”表、摘要 `【计划】` 与导出内容都会恢复。
- 若需回滚旧逻辑，恢复后端对应函数即可；前端保持监听 `response.plan_comparison/plan_comparison_note` 的处理流程即可兼容后续扩展。
- AI 报告 HTML 现同步渲染“计划比较”表格与摘要说明，当接口返回 `plan_comparison` 时，下载的报告会列出本期/计划/完成率，与页面上的内容保持一致。

## 会话小结（2026-01-02 AI 配置伪加密兼容）

- 后端恢复了对 `backend_data/api_key.json` 的简易加密（第 5 位插入 `ww`），但 `GET/POST /data_analysis/ai_settings` 在读写时会自动解密/加密，因此数据分析页“智能体设定”弹窗仍然看到与提交明文一致的 Key，无需额外 UI 逻辑。
- 保存成功后可在浏览器网络面板确认，发送给 FastAPI 的 `api_key` 仍为用户输入的明文；后端落盘时才会插入 `ww`，因此前端无需感知或调整任何校验逻辑，且因为后端会即时重置 AI 客户端，用户保存后立刻再次触发智能报告就会使用新密钥。
- 同时，后端现在会在“单日模式”或“累计模式但起止相同”的情况下同样计算环比窗口，因此 `DataAnalysisView` 与 `UnitAnalysisLite` 无需改动即可在这类查询下展示“环比比较”表格。

## 会话小结（2026-01-02 填报页本单位分析接入智能报告）

- 数据填报页底部的 `UnitAnalysisLite` 组件现新增“智能报告”功能：Global_admin 可在组件内勾选“智能报告”复选框并在分析成功后点击“下载智能报告”按钮，同步触发后端 `request_ai_report`、轮询 `/data_analysis/ai_report/{job_id}` 并下载 HTML；其它角色看不到开关，也无法启动 AI 任务。
- 该实现仅包含启用开关与下载按钮，沿用了数据分析页面的阶段提示/轮询逻辑，但未提供“智能体设定”入口；如需调整 AI Key 仍须前往数据分析主页面。
- 控件位于“生成汇总对比”按钮右侧，状态提示会显示在表单下方；下载按钮在报告准备完毕前保持禁用，避免下载空文档。
- 若后续扩展需要显示密文或掩码，可复用现有 `aiSettingsForm`，当前版本仅记录后端行为变化便于排查。

## 会话小结（2025-12-27 数据分析智能体设定入口）

- 数据分析页“智能报告生成（BETA）”旁新增“智能体设定”按钮，仅 `Global_admin` 可见。点击后弹出模态窗，读取并展示 `backend_data/api_key.json` 里的 `api_key`、`model`，支持直接编辑并保存，保存成功后提示“智能体配置已保存”。
- 新增 `getAiSettings/updateAiSettings` API 封装，分别对应 FastAPI 的 `GET/POST /projects/{project_key}/data_analysis/ai_settings`。模态窗打开时会自动拉取配置，保存时禁用关闭按钮避免误操作。
- 普通用户看不到该按钮；如需联调请确保登录账户属于 Global_admin。若需回滚入口，恢复 `pages/DataAnalysisView.vue` 与 `services/api.js` 即可。
- 弹窗新增“智能体提示词（instruction）”多行输入区域。该字段会在 AI 报告四阶段 Prompt（洞察/结构/内容/检查）最前端以 “### AI 指令（最高优先级）” 注入，用于统一定义文风/重点；空值则保持原提示词不变。
- 新增“启用检查核实阶段”“允许非 Global_admin 启用智能报告”两个开关：保存后会写入 `enable_validation/allow_non_admin_report`，页面会根据 schema 中的 `ai_report_flags` 自动禁用非授权用户的勾选，并在 AI 流程末尾是否呈现“AI 自检结果”。

## 会话小结（2025-12-27 数据分析接口一次返回上期气温）

- 后端 `/data_analysis/query` 在累计模式下已默认计算上一窗口（上期）并在响应 `ringCompare` 中附带 `prevTotals`，其中含平均气温等温度指标的区间平均值；不再依赖“智能报告”开关才能拿到环比数据。
- 页面首次请求即可得到“本期/同期/上期平均气温”及环比百分比，现有的环比比较表、AI 报告和数据卡片都直接复用该载荷，不必等待第二次数据包。
- 若后续前端还需展示上期逐日折线，可在已有响应结构上拓展，而无需新增接口调用；如需回退旧逻辑，仅需恢复后端对应改动。

## 会话小结（2025-12-27 AI 报告新增同比＆区间明细）

- 后端 `data_analysis_ai_report.py` 针对智能报告输出新增“同比比较”“环比比较”“区间明细（逐日）”三块表格，与网页端 `DataAnalysisView` 的对比区一致；前端无需改动即可直接展示新版 HTML，平均气温与常量指标的累计值、环比差异在卡片与表格中都会同步出现。
- 逐日区间表采用与网页端相同的列设计（指标列拆分为本期/同期/同比三列）并附带总计行，delta 列根据正负着色；如需在前端内嵌展示，可继续沿用原有 iframe/下载逻辑，默认视图已经包含这些段落。
- 若未来需要在前端本地渲染同样结构，可参考该 HTML 中的 `<table class="timeline-table">` 与 CSS 命名，直接复用即可；本次无前端源码改动，回滚仅需恢复后端生成逻辑。

## 会话小结（2025-12-27 北海分表分析视图说明）

- 后端新增 `analysis_beihai_sub_daily/analysis_beihai_sub_sum` 视图并独立于 `analysis_company_*`，输出字段完全一致但以 `sheet_name` 粒度过滤（仅 `BeiHai_co_generation_Sheet`、`BeiHai_water_boiler_Sheet`）。本轮未改动前端代码，仅在此登记数据口径，后续若页面需要直接按模板查询，可在 API 层切换到新视图或新增 `/analysis_beihai_sub/*` 入口，前端无需额外适配即可消费。
- 视图只暴露 9 个经济指标（内售热收入/煤成本/外购电/外购水/可计量辅材/直接收入/边际利润/可比煤价边际利润/全厂热效率）和底表原始行，若要在 UI 中展示其它指标，应继续调用现有 `analysis_company_*`。
- 若未来需要根据 sheet_name 动态渲染 sub-view，可重用 data analysis 页现有的单位切换/指标映射逻辑，只需在接口中提供 `sheet_name` 列表或另建下拉选项即可；本次仅做文档说明，无构建或依赖更新。

## 会话小结（2025-12-27 数据分析 AI 报告阶段进度 UI）

- `pages/DataAnalysisView.vue` 在“智能报告生成中…”提示后附加 `阶段 x/4：…` 字串，阶段依次为洞察分析 → 结构规划 → 内容撰写 → 检查核实；任务刚入队会显示 `阶段 0/4`，完成时提示自动消失，失败仍显示后端返回的错误信息。
- 轮询 `/data_analysis/ai_report/{job_id}` 及“下载智能分析报告”前的即时查询都会读取 `payload.stage` 并刷新阶段提示；切换单位、重新发起查询或关闭智能报告时会同步清空阶段状态，避免沿用旧任务的进度。
- 本次仅改前端 UI，接口契约不变，仍依赖后端返回的 `stage` 字段；若要回滚，恢复 `DataAnalysisView.vue` 即可。

## 会话小结（2025-12-27 AI 报告 HTML 输出提醒）

- 后端调整 AI 报告 Prompt，模型必须输出纯 HTML（禁止 ```html/```css 代码块），页头需包含单位/模式/日期、正文含逐日明细表与可切换图表控件；每个指标的 `timeline_entries` 已在 payload 中提供，供渲染逐日表时使用。
- 前端无需改动即可消费新版 HTML，但在调试或内嵌展示时可假定输出总是 `<html>...</html>` 结构；若检测到 Markdown 包裹，可提示后端重新生成。

## 会话小结（2025-12-27 数据分析 AI 报告阶段化）

- 后端 AI 报告接口现采四阶段执行（洞察 → 结构 → 内容 → 检查），`/data_analysis/ai_report/{job_id}` 会在不同阶段返回 `stage`（pending/insight/layout/content/review/ready/failed）以及 `insight/layout/content/validation/started_at`，供前端展示生成进度或调试中间结果。
- `DataAnalysisView.vue` 现有的“智能报告生成（BETA）”轮询逻辑无需改动即可享受新状态：如果需要更细粒度的提示，可根据 `stage` 显示“分析中/排版中/内容撰写/检查核实”；当接口返回 `insight/layout/content/validation` 时，也可在 UI 中预览 JSON，便于定位模型输出问题。
- 若模型输出非法 JSON，后端会在 2 次重试后将 job 标记为 `status=failed` 并附 `error` 描述（如“洞察分析 阶段多次解析失败”），前端的已有错误提示机制可直接展示该消息。

## 会话小结（2025-12-27 AI 报告前端轮询修复）

- 修复了 `DataAnalysisView.vue` 中 AI 报告生成后未自动启动轮询的 Bug。
- 优化了生成过程中的状态提示文案，现在能更清晰地显示“洞察->结构->渲染”的进度。


## 会话小结（2025-12-26 本次仍无前端改动）

- 本轮仅在后端删除“供热输差/内部购热成本”指标，前端逻辑与结构保持不变；如需显示最新指标集，只需依赖后端刷新视图即可。

## 会话小结（2025-12-26 本次无前端改动）

- 本轮仅后端 `backend/sql/analysis.sql` 补齐“内售热收入”视图项，前端页面、配置与构建流程维持现状；记录于此以便与后端会话小结对齐，若需查看该指标请直接消费后端新视图。

## 会话小结（2025-12-25 数据填报页移动端适配）

- `pages/DataEntryView.vue` 顶部工具栏重构为 `topbar__title-group/topbar__actions`，状态/日期与操作按钮拆分为两行容器；在窄屏（<=768px）下自动纵向排列，业务日期、本单位分析开关、重载/提交按钮都会扩展至整行，方便触控点击。
- 新增响应式样式：提交时间、校验开关、折叠区开关与按钮在手机上按块展示；校验提醒列表在小屏改为上下排列文本；`.table-wrap` 支持横向滚动并在移动端收窄边距，避免 RevoGrid 被裁切。
- 桌面端布局保持不变，仅通过媒体查询覆盖小屏行为，验证可在浏览器 DevTools 切换为 iPhone/Android 视图，确认顶部区域与校验提示均能自然换行且表格可左右滚动。

## 会话小结（2025-12-25 数据分析页/本单位分析计划比较）

- `pages/DataAnalysisView.vue` 解析后端 `plan_comparison` 载荷：同月查询会在“同比/环比比较”之后渲染“计划比较”表（本期、月度计划、完成率），并在“数据简报”新增 `【计划】` 段落；多 Sheet Excel 导出同步包含该分块。
- `components/UnitAnalysisLite.vue` 同步接入计划比较：展开本单位分析后若处于同月区间，则显示计划表格，完成率列使用颜色+进度条区分“落后/达成/超出”，导出的单 Sheet Excel 亦追加“计划比较”板块。
- 两处组件均无需改动调用方式，只要后端返回 `plan_comparison` 即可；回滚分别恢复各自文件的新增段落即可。

## 会话小结（2025-12-24 月度计划/实绩数据准备）

- 后端新建 `paln_and_real_month_data` 表及独立 SQL（`backend/sql/paln_and_real_month_data.sql`），用于统一存储“计划值/实际值”类的月度颗粒数据，字段与 `daily_basic_data` 相同（company/item/unit/value 等），并额外标识 `period` 与 `type`（计划/实绩）。
- 前端暂未消费该表，但在数据填报、报表或仪表盘需要展示“月度计划 vs 实际”曲线时，可直接约定 API 从该表提供聚合后的 datasets（按 `period` 拆分月份、`type` 区分计划/实绩），无需额外结构调整。
- 后端 ORM (`backend/db/database_daily_report_25_26.py`) 已加入 `PlanAndRealMonthData` 模型，后续若提供 API，前端可直接请求对应接口获得计划/实绩曲线数据；本次前端代码仍未改动，仅记录数据面已准备就绪。
- 如需调试，可在本地执行 `psql -f backend/sql/paln_and_real_month_data.sql` 创建表，再通过后端 API 接口读取；待接口落地后在此 README 补充前端接入方式。

## 会话小结（2025-12-23 仪表盘导出自动展开折叠表）

- `pages/DashBoard.vue` 的 `downloadPDF` 升级为 `async` 流程：执行前若“供暖期焦点指标详表”处于收起状态，会先将 `cumulativeTableExpanded` 置为 `true`，并串行等待 `nextTick → requestAnimationFrame → 360ms` 过渡时间后再调用 `html2canvas/jsPDF`，保证折叠内容已经完全展开；导出完成后按初始状态恢复，避免破坏用户当前视图。
- `html2canvas` 的 `onclone` 现在使用克隆文档对象隐藏“下载PDF”按钮，保证截图中不再出现按钮本体，生成的 PDF 始终包含完整的折叠表内容。

## 会话小结（2025-12-23 标煤消耗量卡片多维切换）

- “标煤消耗量对比”卡片新增展示维度切换按钮（沿用供暖单耗的 pill 样式），支持“本期/同期”“本月累计/同期月累计”“供暖期累计/同供暖期累计”三种组合，点击后即重新构建表格列、柱状图数据与卡片副标题。
- `coalStdPhaseOptions/coalStdPhaseMode` 驱动 `coalStdSeries` 在 `/dashboard` 的 5 号 section 中读取对应的 `本期/本月累计/本供暖期累计` 等节点；即使部分阶段暂未提供数据，也会自动退回占位栈，确保 UI 不崩溃。
- 卡片 `extra` 文案同步更新为 “单位：吨标煤 · {当前维度}”，用户导出/截图时能明确当前展示口径。

## 会话小结（2025-12-23 供暖单耗卡片新增“本月累计”维度）

- “供暖热/电/水单耗对比”三张卡片的顶栏按钮新增“本月累计/同期月累计”，按钮顺序为“本期/同期 → 本月累计/同期月累计 → 供暖期累计/同供暖期累计”。`unitPhaseBuckets` 会根据当前模式切换到 `本月/同期月` 或 `本供暖期/同供暖期` 数据，图表与表格即时联动。
- `/dashboard` 的 4 号 section 现提供 `本月累计/同期月累计` 数据，按钮切换后即可直接渲染真实值，无需额外请求；若后端暂缺对应数据，则自动回退占位数组，不影响其他功能。
- “主城区供热服务中心单耗明细”卡片同样引入展示维度按钮，可在“本期 → 本月累计 → 供暖期累计”三档之间切换。前端读取 8 号 section 的新阶段数据并按所选维度重算柱状图、表格及副标题提示。

## 会话小结（2025-12-23 数据看板页面结构复盘）

- 阅读 `frontend/src/daily_report_25_26/pages/DashBoard.vue`：模板顶部由业务日期/PDF 下载/缓存发布/气温导入面板组成，中段摘要卡片读取 `summary` 系列 computed（行 1484-2050），折叠表使用 `summaryFoldTable`（行 1859 起）渲染“指标 × 本日/本月累计/供暖期累计”矩阵，主网格渲染气温、边际利润、收入、投诉、单耗、主城中心、煤耗、库存、趋势等卡片。
- 逻辑层围绕 `dashboardData.sections` 解析 `/dashboard` 响应：`loadDashboardData`（行 1187）支持缓存、本地 pending 计数与 AbortController；`metricAliasMap` 与 `resolveSection/resolveBucketByLabel`（行 1038-1475）统一处理“编号.标题”/别名等键，`temperatureSeries/summaryFoldTable/complaintTableData/...` 等 computed 将各段落转换为图表/Table 所需的结构；`useTempOption/useMarginOption/useIncomeCompareOption` 等函数（行 2818 起）统一生成 ECharts option。
- 页面还内置 `temperatureImportStatus` 模态（行 1023 起）和 `cacheJob` 轮询（行 2738 起），`downloadPDF`（行 3934 起）沿用 `html2canvas+jsPDF` 方案导出当前视图；样式区控制摘要/网格/弹窗布局，方便追踪 UI 变体。无代码改动，仅文档留痕，后续调试可直接定位至对应行。

## 会话小结（2025-12-23 供暖单耗供暖期累计切换）

- 供暖单耗板块新增“展示范围”标签（“本期 / 同期”“供暖期累计”），按钮位于三张卡片前，`unitPhaseMode` 控制当前模式，`unitSeries` 会在 `/dashboard` 响应中读取 `本期/同期` 或 `本供暖期累计/同供暖期累计` 数据，并把 legend 传给图表。
- `useUnitConsumptionOption` 根据 `seriesData.legend` 动态渲染 “（本供暖期累计）”“（同供暖期累计）” 等标签，tooltip 也改为按最后一个括号分割名称，三张单耗图与后续主城区排序表保持同步切换。

## 会话小结（2025-12-23 供暖单耗 UI 微调）

- “展示范围”按钮组改为独立网格项 `dashboard-grid__item--unit-toggle`，宽屏下占满 12 列，避免把“供暖水单耗”卡片挤到下一行，样式统一在 `.unit-phase-toggle*` 中维护。
- `unitSeries` 里新增过滤逻辑：对于“供暖电单耗”，自动将“研究院”数据置为 `null`，确保图表和表格不再显示该单位的电单耗；fallback 数据同样遵循这一规则。

## 会话小结（2025-12-23 投诉量分项文案精简）

- “投诉量分项”卡片去掉副标题“本期与同期对比”，仅保留标题与单位提示，让卡片头部更紧凑且避免与图表内容重复说明。

## 会话小结（2025-12-23 日趋势窗口可拉伸）

- “标煤耗量与平均气温趋势图” dataZoom 滑块解除固定 7 天窗口：新增 `dailyTrendWindowSize` 状态，`handleDailyTrendZoom` 根据拖动区间实时更新起止索引/跨度，`resetDailyTrendWindow` 与 `dailyTrendDataZoom` 一并适配，用户可通过拖拽/缩放自主选择展示区间长度。

## 会话小结（2025-12-22 数据看板单耗配置补充供暖期累计）

- 更新伪配置 `backend_data/数据结构_数据看板.json` 中“4.供暖单耗”节点，新增“本供暖期累计”“同期供暖期累计”占位，结构与本期/同期一致（集团/主城区/各厂，研究院电单耗仍排除标记），计量单位沿用热/电/水默认值。
- 当前前端页面未改动，后续接入供暖期累计切换时可直接读取新增键，缺数据仍可回退本期/同期。

## 会话小结（2025-12-16 填报页本单位分析组件完成）

- `components/UnitAnalysisLite.vue` 完成本单位分析折叠区：展开时读取 `getUnitAnalysisMetrics`、按 `set_biz_date` 回溯 7 天设置日期，强制当前单位 + `analysis_mode=range` 调用 `/data_analysis/query`，生成本期/同期/同比汇总、warning、逐日 RevoGrid 表、趋势图（温度优先右轴），并支持单单位 Excel 导出（汇总+逐日+查询信息）。
- 指标多选带序号展示，温度按权重默认勾选；指标/日期变更会清空旧结果，切换单位自动重新加载 schema。未改动其他页面。

## 会话小结（2025-12-16 数据填报页编译错误修复）

- 修复 `pages/DataEntryView.vue` 悬挂的 `router.replace` 代码块，恢复 `if (!projectKey || !pageKey || !sheetKey)` 路由校验，解决编译阶段 Unexpected token 报错。仅前端脚本调整，后端接口不变。

## 会话小结（2025-12-17 数据填报页分析开关位置调整）

- 将“本单位数据分析”启用开关移动到顶栏“业务日期”左侧，与校验开关分离；保持仅管理员可切换，功能逻辑不变。
- 移除页面中原有独立卡片式开关，避免重复入口。

## 会话小结（2025-12-17 数据填报页分析开关尺寸统一）

- 调整顶栏“本单位分析”开关的 checkbox 尺寸为 16x16，与表级校验开关保持一致，样式对齐更整洁，功能未变。

## 会话小结（2025-12-17 本单位分析指标面板滚动）

- 优化 `components/UnitAnalysisLite.vue` 指标选择区域：为分组网格与组内网格设置最大高度并启用纵向滚动，避免指标过多时撑高页面。

## 会话小结（2025-12-17 本单位分析未知单位容错）

- `UnitAnalysisLite` 计算 `analysisUnitKey` 时优先用 schema 下发的 `unit_key`，否则按 `unit_dict` 匹配当前单位（key/label 精确与模糊），最后再回退 props，避免出现 “未知单位” 报错。

## 会话小结（2025-12-17 本单位分析单位匹配再修正）

- 进一步优化 `analysisUnitKey` 选择：移除默认取 `unit_dict` 首项的行为，改为 schema `unit_key` → `unit_dict` 与 props（key/label）大小写/模糊匹配 → props 回退，防止误用其他单位导致 400。

## 会话小结（2025-12-17 本单位分析单位匹配再修正 v2）

- 添加 `_Sheet` 去除、大小写无关的精确匹配以及 label 模糊匹配，再回退 props 与 unit_dict 首项，进一步避免“未知单位”报错。

## 会话小结（2025-12-17 本单位分析 schema 等待与单位校验）

- `runUnitAnalysis` 先等待 `ensureAnalysisSchema` 完成，schema 未加载时提示错误；运行前校验 `analysisUnitKey` 非空，缺失则提示“缺少单位信息”，避免携带空 unit_key 导致 400。

## 会话小结（2025-12-17 本单位分析禁用填报 config 透传）

- `runDataAnalysis` 调用不再透传填报页的 config（如 `数据结构_基本指标表.json`），改用后端默认分析配置，避免因错误 config 触发“未知单位”。

## 会话小结（2025-12-17 本单位分析相关矩阵接入）

- `UnitAnalysisLite` 新增相关矩阵板块：基于已勾选且有逐日数据的指标计算相关系数，展示 r 值、强度条与缺失提示，不额外调用接口。

## 会话小结（2025-12-16 数据分析页现状复盘）

- 复核 `pages/DataAnalysisView.vue`：首屏加载 schema 解析单位/指标/分析模式/默认日期，温度指标按权重自动勾选；表单校验要求至少选择单位与指标，日期联动单日/区间模式。`runAnalysis` 按所选单位逐一调用 `/data_analysis/query`，缓存 `rows/warnings/timeline/meta`，结果区支持单位切换、warnings、摘要（整体/趋势/相关性/风险）、相关矩阵、RevoGrid 逐日表、ECharts 趋势图及多单位多 Sheet Excel 导出。
- 趋势图沿用温度优先右轴策略，芯片/单位切换与 dataZoom/tooltip 联动；摘要可复制，相关矩阵仅在已勾选且具逐日数据的指标间生成。未改动代码，本次仅文档登记，回滚删除本节即可。

## 会话小结（2025-12-14 数据分析页面结构梳理）

- 梳理 `pages/DataAnalysisView.vue` 的主要流程：首屏加载 schema（单位/指标/分析模式/默认日期），按温度权重自动勾选默认气温指标但不选单位；表单校验要求至少选择单位与指标后方可调用 `runDataAnalysis`，并按所选单位逐一请求 `/data_analysis/query` 缓存结果。
- 预览区按 active 单位展示汇总表、warning、数据简报（整体概览/趋势观测/相关矩阵/风险提示），支持相关矩阵与摘要复制；多单位可在单位切换区切换视图。
- 区间模式提供 RevoGrid 逐日明细与趋势图（温度强制右轴，带 dataZoom/tooltip），指标芯片与单位切换保持联动；Excel 导出按单位生成独立 Sheet，包含汇总/逐日/查询信息。
- 本次仅做结构梳理与文档登记，未修改代码或接口。

## 会话小结（2025-12-14 填报页本单位分析折叠区）

- `pages/DataEntryView.vue` 底部新增“本单位数据分析”折叠卡片（默认收起），展开后自动读取 data_analysis schema，强制使用当前表对应单位（模板下发的 `unit_id/unit_name`），仅支持区间模式。
- 提供时间范围选择、指标多选（全选/清空），调用 `/data_analysis/query` 以 `analysis_mode=range`、单一 `unit_key` 生成本期/同期/同比汇总与 warnings，不返回其他单位或逐日曲线，避免数据泄露。
- 支持导出单 Sheet Excel（汇总表 + 查询信息），无多单位/相关矩阵/趋势图，仅作为填报页的轻量汇总辅助。
- 若需回滚，恢复 `DataEntryView.vue` 即可，原有填报/校验/提交逻辑保持不变。

## 会话小结（2025-12-14 填报页指标自动聚合接口）

- 后端新增 `GET /projects/daily_report_25_26/data_entry/analysis/metrics`，按单位聚合审批/常量配置的项目字典并追加气温指标与小数位；前端 `DataEntryView` 调用该接口获取可选指标。
- 折叠区若未选择指标将自动全选接口返回集合，再以 `analysis_mode=range`、当前单位调用 `/data_analysis/query`，保证能生成本单位汇总且不会跨单位泄露。
- 导出仍为单单位单 Sheet；回滚恢复 `daily_report_25_26.py`、`DataEntryView.vue`、`services/api.js` 即可。

## 会话小结（2025-12-14 填报页指标分组栅格布局）

- 指标接口输出顺序与配置一致，并返回 `unit_dict` 供前端使用准确 `unit_key`，避免“未知单位”报错。
- 折叠区改为栅格卡片布局：每个分组独立卡片、内部等宽网格，便于阅读；未分组时同样使用网格排布。
- 回滚恢复 `daily_report_25_26.py` 与 `DataEntryView.vue` 即可。

## 会话小结（2025-12-14 填报页指标分组与单位修正）

- 指标面板按“审批/常量/气温”分组展示，组内按中文排序；空选时默认全选分组集合。接口附带 `unit_dict`，前端查询 `unit_key` 优先用接口值，避免“未知单位”报错。
- 回滚同上：恢复 `daily_report_25_26.py`、`DataEntryView.vue`、`services/api.js` 即可。

## 会话小结（2025-12-14 填报页逐日表与趋势图）

- “本单位数据分析”折叠区读取 `/data_analysis/query` 的 `timeline`，新增逐日 RevoGrid 表与 ECharts 趋势图，支持指标芯片切换、同比色彩提示。
- 仅前端变动，回滚恢复 `DataEntryView.vue` 即可。

## 会话小结（2025-12-14 填报页分析趋势图对齐）

- `DataEntryView.vue` 的趋势图配置与数据分析页面保持一致：图例移至顶部滚动、Tooltip 改为深色卡片并附单位与同比百分比，折线/渐变/虚线配色与正式分析页同步。
- 新增温度指标识别（依赖 `/data_entry/analysis/metrics` 返回的 `temperature` 组 + `value_type`），`assignTimelineAxisSlots` 保证“平均气温”等温度项始终绑定右轴，其它指标走左轴；无温度时退回“首个左轴、其余右轴”的旧策略。
- `analysisTimelineMetrics` 记录 `value_type`，趋势图缓存 `seriesMeta` 在 Tooltip 中显示单位与实时 delta，避免“本期/同期”错列；无后端改动，回滚恢复该 .vue 文件即可。

## 会话小结（2025-12-14 填报页分析默认日期/指标与导出增强）

- 折叠区默认日期改为读取 `/projects/{key}/dashboard/date` 返回的 `set_biz_date`，结束日期固定为该值，开始日期自动回溯 6 天，总是覆盖最近 7 天；切换业务日期时沿用同样窗口。
- 指标多选默认仅勾选“平均气温”类指标，并在每个选项旁展示勾选顺序编号，与 `DataAnalysisView` 一致；若未选择任何指标会提示“请至少选择一个指标”，不再自动全选。
- 逐日合计行遵循数据分析页的 `value_type` 规则：常量直接使用单日值，其它指标按区间累计，避免平均气温等被错误求和。
- 导出 Excel 结果现包含“区间明细”区块，直接写入逐日 RevoGrid 表格数据（含总计行），同时修复汇总区同比列缺少 “%” 的显示问题；生成的文件可完整反映本期每日数据。回滚恢复 `DataEntryView.vue` 即可。

## 会话小结（2025-12-12 dockerignore 添加）

- 仓库根目录新增 `.dockerignore`，将 `db_data` 数据目录排除出镜像构建上下文，前端代码与依赖未变更；若需临时保留该目录，可在 `.dockerignore` 中移除对应条目。

## 会话小结（2025-12-13 AI 测试脚本文本化）

- `configs/ai_test.py` 已调整为纯文本对话模式：移除了 HTML 报告生成/保存/浏览器唤起流程，仅保留多轮文本答复与 Google Search Grounding 工具；提示文案同步为“返回纯文本答案”。若需恢复 HTML 报告能力，请还原该脚本的旧版分支。

## 会话小结（2025-12-13 AI 测试脚本提示词变量）

- `configs/ai_test.py` 新增 `BASE_SYSTEM_PROMPT` 常量用于基础提示词，默认指示模型“用中文简洁回答，避免编造数据”，每次请求都会自动追加；需要关闭/替换时修改该常量即可。

## 会话小结（2025-12-13 采暖收入键名纠正）

- 后端分析视图中采暖收入键名调整为 `eco_heating_supply_income`（中文名“其中：暖收入”），直接收入汇总改用新键名。若前端有依赖分析视图 item 字段的展示或映射，请确保使用新键。

该目录使用 Vue3 + Vite 作为开发脚手架，业务模块 `daily_report_25_26` 与后端接口一一对应。

## 会话小结（2025-12-11 数据分析默认选项优化）

- `pages/DataAnalysisView.vue` 现将“单位选择（多选）”初始状态设为空，`selectedUnits/activeUnit` 不再自动带入 `Group` 等默认值，避免用户忽视单位维度；若未勾选单位直接运行，将通过现有表单校验提示“请选择至少一个单位”。
- 温度类指标引入权重排序：优先匹配 `平均气温/平均温度`，其次是包含“平均”+“气温/温度”关键字的指标，最后才退回其它温度选项。页面加载与“重置选择”都会根据该排序仅勾选一个温度指标，其余指标保持未选，确保趋势图与“数据简报”的相关性分析始终具备温度基准。
- 若 Schema 中未提供 temperature 组，也会遍历 `metric_options/metric_dict` 查找气温关键词，确保默认选中逻辑在不同配置下都能触发；无需追加后端字段。

## 会话小结（2025-12-?? 仪表盘气温导入对比）

- “导入气温”按钮保持仅 `can_publish` 账号可见，执行后除条数/日期外新增“重合区间 + 差异列表”展示：后端返回 `overlap/differences`，前端以弹窗呈现，并提供“确认入库/稍后处理”；点击确认会调用新接口写入 `temperature_data` 并返回写入/覆盖条数。
- `services/api.js` 添加 `commitTemperatureData()`，`DashBoard.vue` 的 `temperatureImportStatus` 增加 `overlapRange/overlapHours/differences` 与写入提示，便于人工对比后再写库。
- 修复：补充 `commitTemperatureData` 引入，避免前端控制台出现未定义错误。
- 更新：弹窗现在列出所有重合小时的接口/数据库值，差异项标红，便于人工审阅即使无差异也能看到完整对齐情况。
- 追加：数据库缺少的小时也会被列出（库值显示为 “—”），确保“每一时刻的气温对比”始终呈现。
- 提示：确认入库写成功后页面顶部会显示“气温数据写库成功”，失败时展示具体错误。
- 提醒：仪表盘“业务日期”默认值现优先使用后端 `set_biz_date`，仅在获取失败时回退到“昨日”，避免日期显示与数据来源不一致。
- 回滚方式：恢复 `DashBoard.vue` 与 `services/api.js` 本次改动即可，按钮行为会退回到仅显示条数/日期。

## 会话小结（2025-12-?? 仪表盘气温导入按钮）

- 仪表盘顶部缓存按钮组新增“导入气温”按钮，仅在具备 `can_publish` 权限的账号下可见。点击后调用 `POST /projects/daily_report_25_26/dashboard/temperature/import`，实时展示“获取中…”状态，并在完成后提示“成功获取 XX 条逐小时气温数据 / 涉及日期列表”。
- `services/api.js` 新增 `importTemperatureData()`，界面状态通过 `temperatureImportStatus` 在 `DashBoard.vue` 内部管理，确保导入提示与缓存操作互不干扰；当前阶段仅获取 Open-Meteo 数据，不写入数据库。

## 会话小结（2025-12-11 数据分析指标组自由组合）

- 数据分析页去掉了基于 `metric_group_views` 的视图约束逻辑，“当前视图不支持该组”提示被移除，任意单位/分析模式下所有指标组均可勾选。
- 若某些指标在当前组合中无返回数据，依旧通过 `warnings` 与“以下指标暂缺数据：xxx”提示反馈，保证“可选项不受限 + 结果忠实呈现”。

## 会话小结（2025-12-11 趋势图温度固定右轴）

- 趋势图引入 `assignAxisSlots`，无论“平均气温”在芯片中被勾选的顺序如何，只要与其它指标同时展示，就始终使用右侧纵轴，其余指标走左轴；若没有温度指标，则保持“首个左轴、其余右轴”的原策略。
- “左轴/右轴”提示与 ECharts 配置复用同一分配逻辑，避免提示与实际绘图不一致。

## 会话小结（2025-12-10 数据分析筛选布局优化）

- `pages/DataAnalysisView.vue` 将“单位选择（多选）”与“分析模式”并排在同一行（`form-grid--top` 最小列宽 320px），新增 `form-layout` 容器，将“指标选择（多选）”移动到下一行独占整行，保持指标面板的滚动与操作区域不受压缩。
- 样式新增 `.form-layout/.form-grid--top/.form-panel--metrics`，确保宽屏为“两列 + 一列”布局，窄屏自动折行；未改动接口调用或数据处理逻辑。

## 会话小结（2025-12-10 数据分析区间明细趋势图）

- “区间明细（逐日）”下方新增趋势图：基于逐日 timeline 同时绘制本期/同期双折线，支持 dataZoom（slider + inside）缩放；Tooltip 显示单位与同比百分比，右上角 Legend 可滚动。
- 新增指标切换器：按照当前查询结果中带有 timeline 的指标生成芯片，默认仅展示首个指标；当用户启用第二个指标后，趋势图自动切换为双纵轴（左右轴）模式，分别对应首、次指标，超过两项也沿用同一策略；芯片可全部取消以显示空态提示，切换单位或重新查询时自动保留可用指标。
- 图表组件 `TrendChart` 内置自适应 resize，配色含渐变填充（本期）+ 虚线（同期），依赖全局 `echarts` CDN；ECharts Legend 支持点选隐藏曲线，双轴模式下方会提示“左轴/右轴”对应指标，并提供趋势区域内的单位切换入口。
- 2025-12-10 更新：`TrendChart` 在刷新 option 时改为 `notMerge: true`，解决切换指标后旧曲线残留的问题，图例/芯片的显示与曲线完全同步；图表高度提升至 420px。
- 2025-12-10 更新：默认加载时自动勾选“气温/温度”类指标（如存在），其他指标默认不勾选，需用户选择；简报的相关性会覆盖所有勾选指标与气温的关系。

## 会话小结（2025-12-10 数据分析数据简报）

- “分析结果预览”卡片内新增“数据简报”子卡片，基于当前单位的 `previewRows`、`timeline` 与告警自动生成多段摘要（整体概览/趋势观测/相关性/风险提示），若存在“平均气温/温度”指标，会输出与其它已勾选指标的相关性（皮尔逊 r）。
- 附带“复制简报”按钮，可一键复制摘要文本（含单位/日期）；摘要随 active 单位与最新查询结果自动刷新。
- 2025-12-12 更新：相关性段落改为相关矩阵展示，所有已勾选且具备逐日数据的指标两两对照，正相关、负相关与缺失在单元格中使用不同色彩区分，摘要内同步提示“矩阵已生成/数据不足”等状态。
- 2025-12-12 更新：整体概览改为仅统计“有效指标数 + 同比上升/下降 + 缺失数量”，趋势观测则对所有已勾选且具备逐日数据的指标输出“区间均值 X 单位（较同期±Y%）”的描述（移除“约”字），聚焦本期平均水平与同期对比。
- 2025-12-12 更新：区间明细卡片新增单位切换标签，复用页面统一的 `handleSwitchUnit` 行为，确保表格、趋势图与摘要在切换单位时同步刷新；同时清理调试日志，控制台不再输出 `[data-analysis]` 调试信息。

## 会话小结（2025-12-10 数据分析页面开放 Group_admin）

- 登录态中 `Group_admin` 角色现在同样会在 `permissions.page_access` 中收到 `data_analysis`，`PageSelectView.vue` 因此会为集团管理员展示“数据分析页面”入口，导航逻辑沿用已有 `normalizedKey === 'data_analysis'` 分支。
- 其他角色（ZhuChengQu_admin/Unit_admin/unit_filler/Group_viewer）依旧无法看见该卡片；如需临时排查，可切换到 `Global_admin` 或 `Group_admin` 账号登录。

## 会话小结（2025-12-10 数据分析同比颜色纠正）

- `pages/DataAnalysisView.vue` 中“分析预览”表格的 `.delta-up/.delta-down` 色彩定义调整为“同比增加=红、同比下降=绿”，与逐日区间明细中 `timelineDeltaCellTemplate` 的 `getDeltaColor` 输出保持一致，避免颜色语义反转。
- 不涉及 API 调整；若后续新增其它同比展示模块，复用同一 CSS class 即可获得正确的颜色映射。

## 会话小结（2025-12-10 数据分析默认日期读取 set_biz_date）

- `DataAnalysisView.vue` 加载 schema 前会调用 `getDashboardBizDate()`（即 `GET /projects/daily_report_25_26/dashboard/date`），将 `start_date/end_date` 默认值优先设置为 `backend_data/date.json` 的 `set_biz_date`，未命中时再退回当日。这样在 D 端未切换日期时能与仪表盘保持同一业务日期。
- `resetSelections` 及日期默认逻辑也会复用这一配置，后续若需更改默认日期，只需更新 `date.json` 或相应接口。

## 会话小结（2025-12-10 数据分析支持多单位批量查询/导出）

- 单位选择改为多选芯片，点击“生成分析结果”会对所选单位逐一调用 `/data_analysis/query` 并缓存结果，在结果区域可通过“切换单位”标签切换查看，UI 中的指标/逐日明细始终只展示当前选中的单位；单位芯片左侧显示顺序编号，勾选顺序同时决定结果与导出 Sheet 的排列顺序。
- 指标芯片同样显示勾选顺序编号，便于按选定顺序检查/导出。
- 下载 Excel 时，每个单位都会生成独立 Sheet，内容包含“汇总”“区间明细”“查询信息”三部分（按顺序垂直排布），并自动去重 Sheet 名，满足“一个单位对应一个标签”的需求。
- 如果部分单位查询失败，错误提示会标注具体单位名称，其他单位的结果仍可正常查看/导出，后端接口无需改动。

## 会话小结（2025-12-10 数据分析常量/气温逐日显示）

- 常量与气温指标现在也会出现在“区间明细（逐日）”里：常量每天显示同值；气温每天从 `calc_temperature_data` 读取本期/同期值。区间合计（total）使用逐日数据的平均值，避免常量被按天数累加。

## 会话小结（2025-12-09 AI 多轮助手 + google-genai Grounding）

- `configs/ai_test.py` 现已改用 `google-genai` 客户端并启用 Google Search Grounding，可作为前端验证“带搜索引用的 AI 报告”交互的样例；若输入包含“html报告”，模型会输出完整 HTML 并尝试在浏览器打开，方便直接查看效果。
- 该脚本的会话状态通过 `_conversation`（`google.genai.types.Content`）维护，展示了如何在发送请求时将历史轮次与工具配置一同提交，后续 DashBoard/DailyReport 若需要上线 AI 报告，可参考这一写法将前端收集的上下文附带到后端服务；为了防止模型输出“请复制粘贴”之类的提示，HTML 报告指令已强化为“只输出包含 ECharts 图表的完整 HTML”。

## 会话小结（2025-12-09 NewAPI Gemini 兼容脚本）

- `configs/ai_test_newapi.py` 再次切换到 OpenAI Chat Completions 兼容模式：`POST https://api.voct.top/v1/chat/completions`、`model=grok-4-expert`，`messages` 列表维持 system/user/assistant 历史，依旧在检测到 “html报告” 时追加提示并生成 HTML/ECharts 报告。
- API Key 顺序未变（环境变量 → backend_data/newapi_api_key.json → 默认值），因此前端若要测试其他模型，可直接改 `MODEL_NAME` 并复用同样的 CLI 逻辑。

## 会话小结（2025-12-08 数据分析指标补齐）

- 今天后端 `analysis.sql` 已同步“供暖电单耗(-研究院)”指标的视图定义，`pages/DataAnalysisView.vue` 中当你选择“集团全口径 + 调整指标 > 供暖电单耗(-研究院)”时，将直接从 `/data_analysis/query` 得到完整数据（`missing=false`），不再弹出“缺失”告警。
- 该指标仍位于“调整指标”分组，key 为 `rate_power_per_10k_m2_YanJiuYuan`，单位 `kWh/万㎡`。前端渲染逻辑保持不变：选定指标 → 发送 `metrics` 数组 → 结果表格按 `previewRows` 显示当前值/同期值/同比，若有区间查询还可在“区间明细” RevoGrid 中看到逐日曲线。
- 若需要确认后端刷新成功，可在调试面板观察 `/data_analysis/query` 返回对象内的 `source_view`（应为 `analysis_groups_daily` 或 `analysis_groups_sum`）以及 `missing=false`，再对比旧数据验证扣除研究院后的差异。

## 会话小结（2025-12-04 analysis.sql 基础数据修复）

- 后端执行 `analysis.sql` 报错 `column "sum_7d_biz" does not exist`，已移除 `yjy_power` CTE 中多余的 `sum_7d_* / sum_month_* / sum_ytd_*` 列聚合，只保留 `value_biz_date/value_peer_date`，保证集团“供暖电单耗(-研究院)”的指标能够顺利刷新。
- 前端依赖的 `/data_analysis/query`、仪表盘展示表和后续 AI 报告在读取该指标时将继续得到稳定结果，无需额外代码调整；部署或本地调试时记得重新执行 `psql -f backend/sql/analysis.sql`。
- 同期修复“供热公司”在“供暖水单耗”上无值的问题：后端 `calc_rate_water_per_10k_m2` 现在汇总一次网补水、站补水与网用水三类指标，前端无需修改即可正常查询。

## 会话小结（2025-12-04 AI 报告预研）

- AI 报告功能计划接入 `DashBoard.vue`，前端只需等待后端提供统一的 `/api/v1/projects/daily_report_25_26/ai/report` 接口；本次会话新增的 `configs/ai_test.py`（基于官方 `google-generativeai` SDK，并从 `backend_data/api_key.json` 读取密钥与模型配置）可用于提前验证 API Key 与模型表现。
- 未来在 `pages/DashBoard.vue` 中将新增“生成 AI 报告”区域，捕获仪表盘现有数据包后请求后端 AI 接口，再将文本结果渲染为卡片或者弹窗；前端无需直接暴露 API Key。
- 若后续评估中决定暂缓该功能，只需保持现有 DashBoard 结构不变，并删除 `configs/ai_test.py` 与相关文档说明即可。

## 会话小结（2025-11-30 数据分析接口模块化）

- 后端已将 `/data_analysis/schema` 与 `/data_analysis/query` 的核心逻辑抽离到 `backend/services/data_analysis.py`，前端 `DataAnalysisView.vue` 继续沿用同一接口契约，不需要额外改动即可获得统一的 schema/查询结果。
- 服务层统一处理指标分组、常量/气温/逐日明细与 Excel 导出数据，因此前端在渲染 RevoGrid、同比列以及下载文件时的字段含义保持不变；如需调试历史实现，可与后端 `_execute_data_analysis_query_legacy` 对照。
- 若后续要在数据看板或其它页面复用同一查询结果，可直接请求 `/data_analysis/query`，现在的实现已经聚合在 service 层，便于多路调用共享逻辑。

## 会话小结（2025-11-30 数据看板每日对比趋势）

- `pages/DashBoard.vue` 新增 “每日对比趋势” 卡片（位于“煤炭库存”之后，栅格宽度 12），展示供暖期内标煤耗量（本期/同期）与平均气温同轴曲线，使用全新的 `useDailyTrendOption` 生成双纵轴折线图。
- 新增 `dailyTrendSection/dailyTrendSeries` 解析函数，将后端返回的 `labels + series` 结构解耦为左轴（吨）与右轴（℃），并通过 `getDisplayLabel`/别名系统同步展示图例名称。
- 样式层追加 `.dashboard-grid__item--trend` 以占满一行，`dailyTrendExtraLabel` 在卡片副标题中提示双轴单位；如需回滚，只需移除 10 号段配置与上述组件/样式即可。

## 会话小结（2025-11-28 全厂热效率分母引入油耗）

- 后端 `sum_basic_data`/`groups` 视图更新后，`rate_overall_efficiency` 与集团同名字段在所有窗口的分母将包含 `consumption_oil`（按 1.4571 系数折算为等效标煤）；前端直接读取相同字段即可得到新口径。
- UI 若展示热效率对比，请注意新旧数据存在轻微差异，尤其是富油耗单位，必要时可在说明文字中提示“含油耗折算热量”。
- 若需要回滚旧算法，仅需重新执行上一版本 SQL 并刷新接口，前端无需代码调整。
- 数据分析页面调用的 `analysis_*` 视图也同步调整，`/data_analysis/query`、自由构建等功能读取的 `rate_overall_efficiency` 会与 dashboard/展示表一致，无需额外前端兼容。

## 会话小结（2025-11-27 集团电单耗双口径）

- 后端 `groups` 视图新增 `rate_power_per_10k_m2_YanJiuYuan` 字段（中文名“供暖电单耗(-研究院)”），其值等于集团整体现有 `rate_power_per_10k_m2` 在分子、分母上扣除 `YanJiuYuan` 数据后的结果。
- UI 若需要展示两个口径，可沿用当前表格结构增加一列或在 tooltip 中切换；字段 key 与接口一致，单位仍为 `kWh/万㎡`。
- 旧字段 `rate_power_per_10k_m2` 继续返回包含研究院的全量数据，可用于对比分析。

## 会话小结（2025-11-27 数据看板/展示表同步）

- 数据看板 `backend_data/数据结构_数据看板.json` 的“4.供暖单耗-集团汇总”已将“供暖电单耗”映射到 `供暖电单耗(-研究院)`，仪表盘直接展示新口径。
- `backend_data/数据结构_全口径展示表.json` 的 `Group_analysis_brief_report_Sheet` 现通过 `value_biz_date(rate_power_per_10k_m2_YanJiuYuan)`/`value_peer_date(rate_power_per_10k_m2_YanJiuYuan)` 读取同一字段，避免出现 0 值。
- 前端无需额外改动即可在数据看板与分析简报中看到一致的“集团电单耗（-研究院）”数据，如需保留旧口径可继续使用 `rate_power_per_10k_m2` 字段。

## 会话小结（2025-11-27 数据分析页面仅限 Global_admin）

- 后端权限矩阵仅为 `Global_admin` 保留 `data_analysis` page_access，页面 `/projects/daily_report_25_26/pages/data_analysis/data-analysis` 只有全局管理员可见，其余角色在页面入口列表中不再显示该卡片。
- 如需调试，需使用 Global_admin 账号或临时调整 `permissions.json`；前端逻辑无需改动，入口是否可见完全由后端权限接口决定。

## 会话小结（2025-11-27 集团口径站购电回滚）

- 因口径需求调整，后端已恢复 `consumption_station_purchased_power` 在集团层级中包含 `YanJiuYuan`，前端读取 `groups` 视图时会重新看到包含研究院的数据。
- 这意味着“集团全口径” `rate_power_per_10k_m2` 与其它派生指标将再度与历史报表一致，如需与主城区对比请注意主城区仍只包含 `BeiHai/XiangHai/GongRe`。
- 若要确认效果，可在调试面板中比较 `/groups` 返回的 `Group` 行与各单位数值总和：集团列应等于全部八家单位之和。

## 会话小结（2025-11-26 数据分析页面入口补丁）

- `PageSelectView.vue` 已自带 `data_analysis` 卡片逻辑，但受权限矩阵控制；后台 `permissions.json` 现将该 page_key 加入所有角色 `page_access`，登录后刷新即可看到“数据分析页面”卡片。
- 新页面仍由 `DataAnalysisView.vue` 渲染，首屏依赖 `/data_analysis/schema` 接口拉取单位/指标/日期选项；后续若扩展真实查询 API，可在该页面中追加表单提交逻辑。
- 若 `数据结构_数据分析表.json` 中配置 `显示单位` 列表，`DataAnalysisView.vue` 仅展示这些单位的单选项（其余单位仍保留在 `unit_dict` 中供派生逻辑使用）。
- `指标选择` 支持“主要指标”与“常量指标”两组：常量组展示来自 `constant_data` 表的字段，并在 UI 中以独立卡片标示；多选集合依旧共享，方便后续统一提交。

## 会话小结（2025-11-25 日分析视图拆分）

- 后端新增 `backend/sql/daily_analysis.sql`，提供 `company_daily_analysis`（公司维度）与 `gourps_daily_analysis`（主城区/集团汇总）两张“本日/同期”专用视图；自由构建页面在展示任意日期或日期区间时，可循环设置 `SET phoenix.biz_date = :target_date` 并查询上述视图，而不再调用包含月度/YTD 聚合的旧视图，显著降低资源消耗。
- `company_daily_analysis` 输出与现有 `sum_basic_data` 相同的 item 语义（含热效率、边际利润、投诉率等），字段仅保留 `value_biz_date/value_peer_date`。前端只需将新接口结果映射到既有 `valueCurrent/valuePeer` 即可。
- `gourps_daily_analysis` 已将主城区与集团全口径的派生指标（投诉率、单耗、张屯口径煤耗、全厂热效率、直接收入等）重新按日值计算；当自由构建页面需要“主城区/集团”切换时，无需再重复在前端聚合。
- 后续若为自由构建页面新增 API，建议直接调用上述视图，将日期/区间作为参数（循环查询或在 SQL 中聚合），即可与现有固定视图共享同一计算链路。
- 若前端需要进行期间累计展示，可在调用前设置 `phoenix.sum_start_date`/`phoenix.sum_end_date`，复用后端新建的 `company_sum_analysis` 与 `groups_sum_analysis` 结果，直接获取区间累计值及主城区/集团派生指标，避免在浏览器端逐日累加。

## 会话小结（2025-11-24 数据模板行内格式统一）

- 后端 `backend_data/数据结构_基本指标表.json` 现将所有 `“数据”` 数组行合并为单行，RevoGrid 模板接口返回的数据结构不变。前端解析 `rows/cells` 时无需改动，只是未来 `git diff` 更易阅读。
- 若本地有依赖旧格式的脚本（例如基于换行数计算列宽），请改用 JSON 解析而非行文本判断，以免在模板再次格式化时受到影响。
- `Coal_inventory_Sheet` 与 `GongRe_branches_detail_Sheet` 的长列表也已行内化，前端在渲染这些大表格时可获得更清晰的 diff；如需确认模板是否更新，可比较 `sheet_key` 相应的 `rows` 列表应全部为单行字符串数组。

## 会话小结（2025-11-23 仪表盘图表监听优化）

- `pages/DashBoard.vue` 中的 `DashboardEChart` 组件新增 `shallowRef` 缓存，`chart.setOption` 改为 `notMerge: false, lazyUpdate: true` 的增量更新，并取消 `deep` 级 watcher，避免每次响应式细节变化都触发整棵 option 深度遍历与整图重绘。
- 由于 `props.option` 现在以浅引用追踪，任意图表数据更新只会触发一次重绘；图表在窗口 resize 或折叠面板切换时仍可通过已有的 `handleResize` 监听正常响应。
- 若需回滚到旧实现，只需恢复 `DashboardEChart` 组件中的 `chart.setOption(props.option, true)` 与 `watch(..., { deep: true })` 逻辑。

## 会话小结（2025-11-23 仪表盘日期请求防抖）

- `pages/DashBoard.vue` 为业务日期切换新增 450ms 防抖（`scheduleDashboardLoad`）、内存缓存以及 `AbortController`，`loadDashboardData` 会取消仍在进行的旧请求，仅保留用户最后一次选择；命中缓存时直接复用上次 payload，避免重复渲染。
- `services/api.js/getDashboardData` 允许传入 `signal`，供前端在切换日期时中止先前的 fetch；其他调用方可忽略此参数，行为保持不变。
- 卸载页面时会清理计时器并 abort 悬挂的请求，防止切换路由后依旧写入已销毁的组件。

## 会话小结（2025-11-22 校验提示细化）

- `pages/DataEntryView.vue` 在校验面板中追加“当前值/参照值/当前比例”等明细。`formatViolationDetail` 会根据 `evaluateRule` 返回的 `cellValue/referenceValue/expressionValue` 拼装文案，默认提示或自定义 `message` 都会附带这些括号说明。
- `number_range`/`less_equal_than`/`column_ratio`/`expression_range` 均会把实时数值写入违规记录，便于提示面板直接展示；无须修改模板配置即可获得更详尽的错误描述。
- 任何新增的规则只要沿用现有字段（如 `min/max/min_ratio/reference_row`），前端就能自动附带数值说明；若要关闭细节，可在模板级关闭校验或在 UI 端过滤。

## 会话小结（2025-11-22 全局校验开关）

- `pages/Sheets.vue` 在列表顶部新增“全局校验开关”复选框：所有用户都能看到当前状态；仅“系统管理员”可勾选，其他角色呈现禁用态并提示“仅系统管理员可修改”。
- UI 已微调：开关控件整体下移以与页面标题对齐，同时仅在切换失败或加载中提示信息，普通用户不再看到“仅系统管理员可修改”字样；具备“系统管理员”关键词的账号即可操作。
- `pages/DataEntryView.vue` 在“业务日期”输入框左侧新增无文字复选框（`Coal_inventory_Sheet` 除外），用于联动各模板的 `校验开关`：管理员勾选时调用 `/data_entry/sheets/{sheet_key}/validation-switch` 写入 JSON，并在成功后自动重载模板；普通用户只能查看当前状态。
- 若存在 error 级校验且对应行的“解释说明”列已填写内容，则视为“带解释放行”，提交按钮不会被锁定；未填写说明的错误仍会阻止提交。
- 各模板通过 `校验说明映射` 字段指定“错误行需要在哪个指标填写解释才能放行”，当前 `backend_data/数据结构_基本指标表.json` 为所有“全厂热效率”映射到“标煤耗量”。前端在模板响应的 `validation_explanation_map` 中读取该配置。
- 勾选状态与后端 `/data_entry/validation/master-switch` GET/POST 同步，切换时先更新 UI，再落盘；写入失败会回滚到上一次值并显示错误信息。
- `services/api.js` 暴露 `getValidationMasterSwitch/setValidationMasterSwitch`，供其他页面按需重用；如需自定义 UI，可复用这两个方法。

## 会话小结（2025-11-22 数据填报校验联动）

- `GET /api/v1/projects/daily_report_25_26/data_entry/sheets/{sheet_key}/template` 现会为除 `BeiHai_co_generation_Sheet`、`BeiHai_gas_boiler_Sheet`、`Coal_inventory_Sheet` 外的大部分模板返回 `validation_enabled: true`，且新增“全厂热效率”与“耗水量”规则；渲染 `DataEntryView` 时需尊重该开关，并在 `runFullValidation` 中读取新的 rule 集合。
- “全厂热效率”规则沿用 `(value('供热量') + value('售电量') * 36) / (29.308 * value('标煤耗量'))`，前端需要把 `depends_on` 对应的行数值写入 `virtualContext` 才能计算表达式；若 `validation_rules['全厂热效率'][*].virtual` 为 true，则不要尝试在 RevoGrid 中渲染该指标。
- “耗水量”规则由 `number_range`（本期/同期需 >0）与 `column_ratio`（本期需在同期 50%~115%）组成，UI 在展示错误摘要时应保留 message 原文，以指示用户是超出区间还是出现 0 值。
- 特殊情况：`GongRe_branches_detail_Sheet` 暂无耗水量行，因此仍不会收到相关规则；`YanJiuYuan_Sheet` 只包含耗水量校验而无热效率校验，前端需要支持部分规则缺失的场景。

## 会话小结（2025-11-21 仪表盘气温标签错位）

- `pages/DashBoard.vue` 的 `useTempOption` 现会计算 push_date 对应的本期/同期温度差，当差值 ≤1℃ 且双值有效时，自动把 markPoint 标签改为左右平移（左侧对齐蓝色“本期”，右侧对齐橙色“同期”），避免前后三日窗口内的标签上下堆叠；差值大于阈值时则维持原来的上下排布。
- 新增 `buildTempLabel` 助手统一 label 样式（600 粗体、半透明白色背景、12px 间距与 padding），无论温度为正为负都能保持可读，并确保 markLine、折线本身不挡住数值。
- 如需回退至旧行为，可删除 `buildTempLabel`、`highlightLabelOverlap` 相关逻辑并恢复 markPoint 标签的默认 `position: 'top'/'bottom'`。

## 会话小结（2025-11-19 仪表盘净投诉量累计数据）

- 后端 `/dashboard` 现以 `sum_season_total_net_complaints` 提供“集团汇总净投诉量”本期/同期值，并在 `0.5卡片详细信数据表（折叠）` 中分别填充“当日/本月累计/本供暖期累计”净投诉量（全部使用 `value_biz_date/value_peer_date` 状态值），前端 `summaryFoldTable` 等组件直接沿用现有解析逻辑即可。
- summary 区第 4/8 张卡片同步改为“投诉量 / 净投诉量”双值展示：当日卡读取“当日省市平台投诉量 / 当日净投诉量”，供暖期卡读取“集团汇总供暖期省市平台投诉量 / 集团汇总净投诉量”，括号差值均与同期值相比；同时通过 `summary-card__value--paired` 将整行字号减小 3px（24px→21px），突出其他卡片主值。
- “供暖期关键指标详表”中新增的“净投诉量（件）”已配置 0 位小数、禁止千分位，和表格内其它整数指标保持一致。
- 若需要在 UI 中展示新的累计卡片，可在 `DashBoard.vue` 的 `resolveSection('9.累计卡片')` 结果中追加渲染逻辑；若暂不使用，只需保持隐藏或过滤该字段即可。

## 会话小结（2025-11-18 仪表盘平均气温 trace 撤销）

- 由于浏览器 Console 输出过多，`DashBoard.vue` 中针对“平均气温”折叠表的 `[dashboard-trace] summary-fold …` 调试日志已移除；切换业务日期时将不再自动打印本期/同期的本日值。
- 若后续需要排查，可在本地备份中临时恢复该 `console.group/table` 代码或直接比对 UI 数值即可。

## 会话小结（2025-11-17 仪表盘折叠表格）

- `pages/DashBoard.vue` 在第八个 summary 卡片后追加“供暖期关键指标详表”折叠区，默认收起，展开后渲染 4×5 表格（指标/单位/本日/本月累计/供暖期累计），并通过 `summary-card--span-full` 让其在 12 栅格中独占一行。
- 新增 `summaryFoldTable`（原 `cumulativeHeadlineTable` 升级）、`toggleCumulativeTable` 及相关样式/动画（`fold` transition、`summary-card__toggle` 等），直接复用顶部 summary 卡片与 9 号累计卡片的数据，并可优先读取 `backend_data/数据结构_数据看板.json` 中的 `0.5卡片详细信数据表（折叠）` 配置来决定指标顺序与单位；其中“本月累计”列已预留，待后端提供数值后即可填充。
- 折叠表格改为“第一列纵向合并 + 第二列标示本期/同期”的定制 `<table>`，支持双行对照展示（本期/同期），替换掉通用 `Table` 组件。
- 当前版本已优先读取 `/dashboard` 响应中的 `0.5卡片详细信数据表（折叠）` 节点：只要后端填入 `本日/本月累计/本供暖期累计` 数值，前端即可直接渲染；若该节点缺失，则折叠表不展示数据（不再回退兜底）。
- 如需回滚，可删除新增 summary 块与相关 computed/样式，或恢复 `DashBoard.vue` 至变更前的版本。

## 会话小结（2025-11-17 仪表盘配置驱动蓝图）

- `backend_data/dashboard_frontend_config.json` 现已包含两类信息：一是前端渲染所需的布局/组件绑定；二是 `data_contracts` 与 `data_mapping`，明确每个图表/卡片对应的真实视图、item_key 与公司口径。前端改造时可先读取该 JSON，按 `contract_id` + selection 直接驱动数据请求与渲染。
- 目标：把 `DashBoard.vue` 里关于组织顺序、单位、指标来源的硬编码迁移到配置层，未来仅需解析该文件即可完成页面搭建；当前代码仍未接入，待实现时请在加载 `/dashboard` 数据前同步加载该配置。
- 如需回滚，删除上述 JSON 并沿用现有硬编码逻辑即可；本文件记录其存在，方便定位来源。

## 会话小结（2025-11-15 会话持久化说明）

- 本次改动仅涉及后端新增 `backend/sql/create_auth_sessions_table.sql`，准备将登录 token 持久化到 PostgreSQL，前端代码暂无变更。
- 现有 Pinia `auth` 仓库、路由守卫与页面结构保持不变；待后端切换到数据库会话后，前端可继续沿用当前 `Authorization` 头部与刷新逻辑，无需额外适配。
- 如需在前端提示用户“会话可跨重启保留”等信息，可在登录页或顶部 `AppHeader` 中追加文案；回滚时删除上述说明即可。

## 会话小结（2025-11-15 填报提示符号优化）

- `pages/DataEntryView.vue` 中填报成功提示由“提交成功，数据已入库。”更新为“提交成功，数据已入库！”，与产品文案保持一致；倒计时与刷新逻辑未改动。

## 会话小结（2025-11-15 审批列表隐藏集团行）

- `pages/PageSelectView.vue` 的审批进度表格新增 `Set(['系统管理员','Group'])` 黑名单，默认不再展示集团本身的审批行，避免无意义的按钮。

## 会话小结（2025-11-15 集团张屯煤耗汇总数据对齐）

- 后端 `groups` 视图为 `company = 'Group'` 新增 `sum_consumption_amount_raw_coal_zhangtun`、`sum_consumption_std_coal_zhangtun` 两条记录，均携带标准的 `value_biz_date / sum_ytd_biz` 等字段，可直接呈现为新的量化卡片或表格行。
- 如需在仪表盘或数据展示页引用，请通过 `item` 判断（`sum_consumption_amount_*_zhangtun`），`item_cn` 已内置“原煤耗量汇总(张屯)/标煤耗量汇总(张屯)”中文名；其取值系 `ZhuChengQu + JinZhou + BeiFang + JinPu` 的常规煤耗与 `ZhuangHe` 张屯口径的叠加。
- 当前前端代码未读取该条目，待设计稿确认后可在 `unitCards` 或 `unitSeries` 相关配置中追加映射。若需回滚，仅需忽略或过滤上述 `item` 即可。

## 会话小结（2025-11-16 张屯指标别名渲染）

- `DashBoard.vue` 读取配置新增的 `口径别名` 映射，统一构建 `metricAliasMap` 与 `buildLabelVariants`，在 `resolveSection`、`getCumulativeMetric`、`cumulativeUnits`、投诉图表/表格以及收入表格中始终以“标煤耗量/原煤耗量”等原口径文案展示，但数据来源仍是 `sum_consumption_amount_*_zhangtun`。
- 兼容性：当后台未来继续追加其他别名，只需在 `backend_data/数据结构_数据看板.json` 的 `口径别名` 中注册即可；若要回滚，删除该配置并还原 `DashBoard.vue` 中的 alias 逻辑即可恢复旧有直读模式。
- UI 不再出现“标煤耗量汇总(张屯)”等内部口径名称，且 `resolveSection` 现支持多别名参数，确保改名后仍可定位第 5 段落。
- 2025-11-16 晚间补丁：修复 `buildLabelVariants` 在做字符串级别替换时导致的无限扩展（例如“标煤耗量”→“标煤耗量汇总(张屯)”→“标煤耗量汇总(张屯)汇总(张屯)”……），该 bug 会让浏览器内存持续膨胀直至崩溃；现在 BFS 仅在“别名/规范名”之间跳转，不再做字符串替换。

# 前端说明（Vue3 + Vite）

该目录使用 Vue3 + Vite 作为开发脚手架，业务模块 `daily_report_25_26` 与后端接口一一对应。

## 会话小结（2025-11-12 数据展示页业务日自动刷新）

- 状态：数据展示子页面（`DisplayRuntimeView.vue`）现会在用户调整业务日期后自动拉取最新只读数据，结束依赖手动点击“刷新”按钮。
- 改动：新增 `pendingAutoRefresh`、`scheduleAutoRefresh` 与 `bizDateAutoRefreshTimer`，对 `<input type="date">` 的 `bizDate` 建立 400ms 去抖监听；当首次加载尚未完成或已有请求在途时，自动刷新请求会排队至当前任务结束，避免并发压垮 `/runtime/spec/eval`。
- 安全措施：为 `loadDefaultBizDate()` 增加 `suppressNextBizDateReaction` 标记，跳过初始化时写入 `bizDate` 触发的监听，确保首屏只执行一次 `runEval()`；组件卸载时统一清理定时器。
- 影响：`projects/.../pages/data_show/sheets` 的每个子页面在切换日历日期后会自动显示“数据载入中…”并刷新到对应日期；原“刷新”按钮仍可手动重试，逻辑保持不变。
- 下一步：可视需要在顶部添加“自动刷新进行中”提示或禁用刷新按钮，进一步降低用户对请求状态的疑惑。

## 会话小结（2025-11-11 填报提交倒计时刷新）

- `pages/DataEntryView.vue` 提交成功后新增 3 秒倒计时提示，实时展示剩余秒数，同时保持提示条常显。
- 倒计时结束时调用 `reloadTemplate()` 重新拉取当前业务日期的数据（不整页刷新），确保留在此前日历选择的表格并立即看到回填结果。
- 新增 `.submit-countdown` 样式与倒计时清理逻辑；若提交失败或页面卸载会立即终止倒计时，提示恢复原状。

## 会话小结（2025-11-11 供暖收费面积口径说明）

- 后端已在 `sum_basic_data` 与 `groups` 视图中将“万平方米净投诉量”分母调整为 `amount_heating_fee_area`，前端读取的字段、单位不变。
- 联调时建议在仪表盘投诉量卡片补充“按供暖收费面积计算”等提示语，确保业务侧理解口径变更；如需改动 UI，可在数据看板页面追加说明文案。

## 会话小结（2025-11-10 仪表盘修复与PDF下载）

- 状态：修复了仪表盘“投诉量”卡片的渲染崩溃问题，并为仪表盘页面增加了“下载为PDF”的功能。
- 改动：
  - `pages/DashBoard.vue`:
    - 在 `useComplaintsOption` 函数中定义了缺失的 `phaseGap` 和 `metricGap` 变量，解决了渲染错误。
    - 在页面头部新增了“下载PDF”按钮，并为其添加了样式。
    - 实现了 `downloadPDF` 函数，该函数使用 `html2canvas` 截取仪表盘页面，并使用 `jsPDF` 将其转换为 PDF 文件进行下载。
    - PDF 文件名会根据当前业务日期动态生成。
    - 在生成截图时，下载按钮会被自动隐藏。
    - **优化**: 将截图格式从无损的 PNG 切换为 80% 质量的 JPEG，并在 `jsPDF` 中启用 `MEDIUM` 压缩，以显著减小生成的 PDF 文件大小。
    - **二次优化**: 为解决JPEG压缩导致的清晰度下降问题，将截图格式恢复为 PNG，同时将 `html2canvas` 的渲染比例提升至 2 倍，并使用 `FAST` 压缩模式，以在保证清晰度的前提下，适度控制文件大小。
  - `index.html`:
    - 添加了 `html2canvas` 和 `jsPDF` 的 CDN 链接，以支持PDF下载功能。
- 影响：用户现在可以从仪表盘页面下载包含当前视图的PDF文件，并且文件大小得到了显著优化。

## 会话小结（2025-11-10 供暖单耗柱距优化）

- 状态：优化“供暖单耗”三张卡片的柱状图排布，提升本期/同期对比的可读性。
- 改动：
  - `pages/DashBoard.vue`：在 `useUnitConsumptionOption` 中将柱状图系列的 `barGap` 调整为 `0%`，令同一单位下本期与同期柱形紧贴；同时把 `barCategoryGap` 提升至 `65%`，扩大不同单位分组间距，避免视觉拥挤。
  - “供暖单耗”与“标煤消耗量对比”卡片移除同期柱体的独立数值标签，改由“本期”标签双行展示本期/同期；“煤炭库存”卡片移除合计虚线折线但保留顶部合计标签（以零半径散点实现），“边际利润简报”标签新增轻量白底，同时清理其它标签的白色背景。
  - “投诉量分项”卡片的柱状标签改为始终显示数值（即便为 0），避免零值被判定为“无标签”。
  - 新增“供热分中心单耗明细”卡片：支持在热/电/水单耗间切换排序，条形图按从低到高展示并标注平均线，右侧表格同步列出三项单耗（字号 8px），数值统一使用千位分隔符；在桌面端条形图与表格各占 6 列。
  - 平均气温摘要添加与同期差值展示（示例：12.34（+0.80）），便于对比趋势。
- 影响：相关卡片更易对比时间段，煤炭库存视觉更简洁，其余交互保持不变。

## 会话小结（2025-11-10 投诉卡片联调）

- 仪表盘 `pages/DashBoard.vue` 投诉卡片现直接消费 `/dashboard` 第六段数据：按配置解析“当日省市平台服务投诉量”“当日净投诉量”两个指标的本期/同期 company 值，缺失时退回 0。
- 图表渲染四条分组柱（两指标 × 本期/同期），启用 `labelLayout.moveOverlap='shiftY'` 与 `axisLabel.hideOverlap=true` 保持标签可读；表格列扩展为“本期/同期”“本期净/同期净”四列并随数据自动生成单位。
- 摘要数值默认读取“集团全口径”本期投诉量，若缺失则遍历当前公司列表回退第一个有效值。
- 2025-11-10 补充：新增统一的标签判定逻辑，投诉量、单耗、标煤、收入及边际利润等图表在数值为 0 时不再显示顶部标签，仅保留非零值标注。
- 2025-11-10 补充：煤炭库存卡片改为读取 `/dashboard` 第七段返回的“厂内/港口/在途”库存数据，按公司堆叠展示（颜色为蓝/橙/绿等高对比调色板，附带折线标注合计），空数据时回退至演示数据。
- 2025-11-10 补充：煤炭库存卡片新增底部表格，按“单位 × 存储方式 + 合计”列出吨数，与堆叠柱图数据同步。
- 2025-11-10 补充：投诉量柱图为“同期”系列开启斜线 `decal` 并调成蓝绿色，同时通过 `barGap`/`barCategoryGap` 将每个指标组（本期/同期）与下一个指标组拉开距离，提升可读性。
- 2025-11-10 补充：投诉量表格字体缩小为 11px，且所有柱状图的“同期”系列统一采用亮蓝斜纹填充，快速区分本期/同期。
- 2025-11-10 补充：投诉量卡片拆分为两张图（省市平台服务投诉量、净投诉量），分别对比本期/同期，且同期柱形统一改为橙色；卡片占 8 列并保留原表格，收入卡片缩为 4 列并新增表格展示本期/同期对比。

## 会话小结（2025-11-10 仪表盘加载提示 & 填报反馈）

- `pages/DashBoard.vue`：
  - 新增 `isLoading` 计数状态，加载 `/dashboard` 数据时在卡片区前显示“数据载入中，请稍候…”提示，全部请求完成后自动隐藏。
  - Loading 提示样式写入 `.dashboard-loading-hint`，确保首屏没有数据时也有明确反馈。
- `pages/DataEntryView.vue`：
  - 引入 `isSubmitting` 状态阻止重复提交，并在模板中禁用提交按钮。
  - 新增 `submitFeedback` 轻量提示条（绿色成功、红色失败），提交完成后立即显示，约 3.2 秒后自动淡出；组件销毁时清理定时器。
  - `onSubmit` 捕获异常写入日志并将错误文案透传到提示条，成功提交后刷新“最近提交”时间戳。
- 样式：补充 `.submit-feedback*` 相关类与过渡动画，提示醒目但不遮挡表格区域。

## 会话小结（2025-11-10 页面入口信息脱敏）

- 状态：项目页面选择视图的卡片副标题统一替换为业务描述，避免直接暴露模板/配置文件路径。
- 改动：`pages/PageSelectView.vue` 新增 `PAGE_DESCRIPTION_MAP` 与 `pageDescription` 辅助函数，依据 `page_key` 输出“数据看板”“数据填报”“数据审批”“数据展示”“常量指标”“运行时调试”等中文说明，并在模板中改用该函数。
- 影响：`/projects/:projectKey/pages` 页面卡片仅呈现友好文案，隐藏 `/app/data/*.json`、`configs/*.json` 等敏感路径，同时保留既有路由跳转与 query 传参；调试入口文案提醒为内部设施。
- 下一步：后续新增页面时，请同步在映射表补充描述；若配置文件未来提供正式描述字段，可改为直接透传后端内容。

## 会话小结（2025-11-10 项目列表补充页面描述）

- 状态：项目配置 `backend_data/项目列表.json` 现含 `页面描述` 字段，接口直接返回描述文案。
- 改动：`backend/api/v1/routes.py` 在 `_normalize_pages` 中透传描述为 `page_description/description`；`PageSelectView` 的 `pageDescription` 优先使用接口字段，映射表仅兜底旧项目。
- 影响：页面副标题与接口返回保持一致，后续如需调整文案可直接编辑配置文件；未配置描述的项目仍回退至固定映射。
- 下一步：新增页面时请在配置中填好 `页面描述`；若需多语言，可考虑在配置添加 `descriptions` 子字段并在前端按语言读取。

## 会话小结（2025-11-09 仪表盘移除 Trace 选项）

- 状态：数据看板页面顶部只保留业务日期输入；调试用 Trace 复选框已下线。
- 改动：`pages/DashBoard.vue` 删除 Trace 复选框模板与 `traceEnabled` 响应式变量，其余日期监听与数据加载逻辑保持不变。
- 影响：避免生产用户误触调试开关，页面交互更简洁；如需恢复，可回滚该文件。
- 下一步：如后续需要调试功能，可单独引入仅内部可见的调试入口或通过路由守卫限制访问。

## 会话小结（2025-11-09 气温/边际利润卡片面积调整）

- 状态：气温曲线与边际利润图表在宽屏模式下平均分配一行，图例下沉后不再遮挡坐标轴文字。
- 改动：`pages/DashBoard.vue` 将气温 ECharts 高度调为 240px，并为两张卡片补充 `min-height: 320px`、移除气温卡片的满宽修饰，同时统一各图表 `legend.bottom` 与 `grid.bottom` 设置，并为 `.dashboard-table` 增加 `box-sizing: border-box`；“投诉量”卡片在宽屏下改为 span 6、移除 `dashboard-grid__item--table` 标记，三个“供暖单耗”卡片统一为 span 4，“标煤消耗量对比”“煤炭库存”统一为 span 6 且移除全幅标记；栅格行间距减半（14px），并为柱状图启用 `labelLayout.moveOverlap='shiftY'`、统一 `distance`，并开启 `axisLabel.hideOverlap=true` 以配合智能避让保持标签清晰。
- 影响：上排两张卡片更紧凑整齐，所有图例脱离坐标轴刻度；若需恢复旧高度或位置，可回滚该文件。
- 下一步：如需继续压缩排版，可评估引入图例折叠或分页方式，避免 legend 占用过多纵向空间。

## 会话小结（2025-11-09 气温/边际利润卡片面积调整）

- 状态：气温变化与边际利润卡片在宽屏模式下各占半屏，并保持统一高度，气温图表高度收紧至 240px。
- 改动：`pages/DashBoard.vue` 将气温 ECharts 高度调低，同时为两张卡片补充 `min-height: 320px` 限制，并移除气温卡片的满宽修饰，使其在宽屏下与边际利润卡片同排对齐。
- 影响：上排卡片更加紧凑，仍可完整展示气温曲线与边际利润表格；若需恢复旧高度，可回滚该文件。
- 下一步：后续若再压缩页面空间，可评估为气温表格增加折叠或分页。

## 会话小结（2025-11-09 边际利润表格回归卡片）

- 状态：“边际利润简报”卡片重新包含明细表格，并与“气温变化情况”卡片在宽屏模式下并排显示。
- 改动：`pages/DashBoard.vue` 将表格回迁至卡片内部，新增 `dashboard-table-wrapper--compact` 以保持卡片高度；同时将“气温变化情况”列宽调整为 6，与“边际利润简报”相同，实现同排对齐。
- 影响：布局较拆分方案更紧凑，表格仍随业务日期刷新且支持滚动；若需恢复独立表格卡片，可回滚该文件。
- 下一步：视需要可进一步为表格添加分页或导出功能，保持视觉高度一致时注意滚动条样式。

## 会话小结（2025-11-09 边际利润板块布局分离）

- 状态：“边际利润简报”与“收入分类对比（集团）”卡片默认同排展示，原表格拆分为独立的“边际利润明细”卡片并置于两者下方。
- 改动：`pages/DashBoard.vue` 调整网格列宽（两卡片各占 6 列），移除“边际利润简报”卡片内部表格，新增独立网格项承载表格内容。
- 影响：页面层次更清晰，图表与表格分离后阅读体验提升；如需恢复旧结构，可回滚该文件。
- 下一步：可在明细卡片补充同比/环比信息或导出入口，进一步强化分析能力。

## 会话小结（2025-11-09 数据看板布局优化）

- 状态：仪表盘页面完成摘要卡片与主体网格的视觉调整，摘要区更为紧凑，主体各组件高度保持一致，避免纵向堆叠时的遮挡感。
- 改动：`pages/DashBoard.vue` 调整摘要卡片圆角、内边距与图标尺寸，降低投影强度；为主体 `.dashboard-grid` 增加 `grid-auto-rows` 与 flex 拉伸规则，使所有卡片在 12 列布局和窄屏单列下均能自动拉伸至统一高度；修正 `z-index` 设置，消除下方组件侵入上方内容的现象。
- 影响：页面布局更整洁，摘要与各图表区域在不同分辨率下对齐；如需恢复旧版视觉，可回滚该文件。
- 下一步：可在布局稳定基础上继续接入余下数据板块，并根据实际内容微调断点下的最小高度。

## 会话小结（2025-11-09 边际利润面板接入真实数据）

- 状态：`pages/DashBoard.vue` 中“边际利润简报”面板现直接读取 `/dashboard` 返回的“2.边际利润”数据，卡片、图表与表格随业务日期自动刷新。
- 改动：新增 `marginSection`/`marginSeries` 等计算属性，将接口数据转换为单位指标列表；`useMarginOption` 改为根据真实数值绘制“直接收入/煤成本/外购热成本/水电辅材成本”堆叠与“可比煤价边际利润”折线；摘要卡片标题更新为“集团全口径可比煤价边际利润”并输出两位小数；折线节点新增标签（现保留一位小数并配气泡背景），图表高度调至 300px，移除卡片副标题以保持视觉简洁；“收入分类对比（集团）”柱状图同步为本期、同期系列增加一位小数的顶部标签；“单耗”板块解析 `/dashboard` “4.供暖单耗” 节点后拆分为热/电/水三张图，每张图展示本期/同期两组柱并在卡片 `extra` 中标注计量单位，tooltip 带单位说明；“标煤消耗量对比”读取“5.标煤耗量”节点，图表/表格/摘要实时呈现本期与同期数据且统一保留一位小数，并清理页面内“本期 vs 同期”文案。
- 影响：仪表盘不再依赖演示常量，若接口缺失某指标则以 0/空值兜底；其他尚未接入的板块仍沿用演示数据。
- 下一步：可进一步引入同期曲线或同比条形图，并结合 `marginSeries` 中保留的同期数据，扩展对比展示或下载功能。

## 会话小结（2025-11-09 集团收入明细接入）

- 状态：仪表盘“集团全口径收入明细”柱状图现在使用 `/dashboard` 的真实数据展示当期/同期收入，并按模板定义科目顺序显示。
- 改动：`DashBoard.vue` 新增 `incomeSection`/`incomeSeries` 计算属性，统一将“3.集团全口径收入明细”节点解析为分类、本期、同期数组；`useIncomeCompareOption` 直接消费该计算结果输出常规柱状图，并移除早先的断轴尝试，保持与当前 ECharts 版本兼容。
- 影响：图表随业务日期变化自动刷新，若某收入科目缺值则以 0 兜底避免绘图错误；其他板块保持原状。
- 下一步：可考虑追加数值表格或同比/环比指标，或在图表下方展示总收入与增幅信息。

## 会话小结（2025-11-08 数据看板刷新按钮移除）

- 状态：仪表盘页面头部现仅保留 Trace 调试开关与业务日期选择器，临时“刷新”按钮已删除。
- 改动：`pages/DashBoard.vue` 清理按钮 DOM、顶部“今日/业务日期”静态提示、`refreshDashboard` 占位函数及相关样式，防止出现无效交互。
- 影响：用户依旧可以勾选 Trace 或调整业务日期，界面保持原有布局；如需恢复按钮，可回滚该文件。
- 下一步：待 `/dashboard` 接口完成后，可在日期变化时触发真实刷新逻辑，并补充 Trace/日期的引导文案。

## 会话小结（2025-11-08 数据看板统一数据容器）

- 状态：`DashBoard.vue` 已建立 `dashboardData` 响应式容器，集中存放 `/dashboard` 接口返回的 `meta` 与各个板块原始数据。
- 改动：`loadDashboardData` 成功后写入 `show_date/push_date/generated_at`，并将接口返回的 section 数据（去除 `push_date`、`展示日期`）同步到 `dashboardData.sections`，为后续逐块替换静态演示数据做准备。
- 影响：页面短期仍显示演示数据，但内部状态已统一，后续图表只需读取容器即可切换为真实数据；如需回滚，移除该容器与赋值逻辑即可。
- 下一步：逐步将温度、边际利润、单耗、库存等模块的图表/表格改为引用 `dashboardData.sections`，并补充加载/错误态处理。

## 会话小结（2025-11-08 仪表盘气温模块接入）

- 状态：气温折线图、表格及顶部“平均气温”卡片已改为读取 `/dashboard` 返回的“1.逐小时气温”数据。
- 改动：在 `DashBoard.vue` 增加 `temperatureSection/temperatureSeries` 计算属性，对后端数据进行日期排序与均值计算；`tempOpt`、`temperatureTableData`、`averageTemp` 绑定该计算结果，缺失值自动兜底。
- 卡片直接读取 `push_date` 当日的 24 小时列表求算术平均（两位小数），若该日期缺失则显示“—”。
- 表格与折线图统一使用两位小数的日均结果，保持与后端一致。
- 配合后端将缺失小时返回为 `null`，前端均值计算会自动忽略缺测数据，避免平均值偏低。
- 气温折线图新增 `markLine` 标记 `push_date` 对应的日期列，突出业务日。

## 会话小结（2025-11-08 数据看板 Revogrid 表格统一）

- 状态：仪表盘内所有表格（气温、边际利润、标煤耗量、投诉）已统一切换为 Revogrid。
- 改动：新增 `components/DashboardRevoGrid.vue` 封装 Revogrid 默认样式与只读配置；`DashBoard.vue` 删除自定义 Table 组件，列/行结构改为 `prop + 对象` 的形式，便于后续接入真实接口。
- 影响：表格外观、滚动体验、复制能力保持一致，后续需要排序、锁列等能力可直接在包装组件中扩展；其它页面未引入该组件。
- 下一步：待真实数据接入后，可依据同一包装组件快速渲染各模块指标，也可在此基础上扩展导出/过滤等功能。
- 影响：切换业务日期时气温模块实时更新，若后端无数据则显示 0 基线与“—”；其他模块仍保持演示数据。
- 下一步：继续为边际利润、单耗、库存等模块接入真实数据，完成仪表盘整体联调。

## 会话小结（2025-11-08 数据看板煤炭库存聚合修正）

- 状态：后端 `/dashboard` 接口的“7.煤炭库存明细”模块现返回按单位与仓储类型聚合后的库存值，前端无需额外改动即可展示真实数据。
- 影响：DashBoard 页面收到的数据结构保持不变，但各 storage_type 数值将不再出现 0 或缺失；如需调试，可在浏览器网络面板观察最新响应。
- 下一步：结合新数据，可在前端补充单位/仓储类型的可视化（如堆叠条形图），并按需展示集团合计或趋势信息。

## 会话小结（2025-11-08 数据看板 API 初版）

- 状态：后端已提供 `GET /api/v1/projects/daily_report_25_26/dashboard`，可按 `show_date` 查询参数获取数据看板 JSON。
- 改动：`services/api.js` 新增 `getDashboardData`，`pages/DashBoard.vue` 在挂载后请求该接口并根据返回的 `push_date` 更新日历默认值；未指定 `show_date` 时由 `backend_data/date.json` 的 `set_biz_date` 决定默认日期，选择新日期会再次触发请求。
- 影响：仪表盘打开后即可展示后端给定日期；后续需将接口返回的数据映射到图表与表格。
- 下一步：完善加载/错误提示，并将返回的数据填充至 ECharts 与表格；待后端接入数据库后同步更新数据映射逻辑。

## 会话小结（2025-11-07 数据填报指标联动）

- 状态：数据填报页面读取模板中的 `linkage_dict`/“指标联动”配置后，会在 RevoGrid 中保持主子指标的输入一致，用户编辑任一联动单元格，其余联动行会即时同步。
- 改动：`pages/DataEntryView.vue` 新增 `linkageMap`、`pickLinkageDict`、`rebuildLinkageMapFromPayload` 与 `ensureLinkedRowsAligned`，在模板加载与镜像查询后重建联动映射；`handleAfterEdit` 将最新值广播到映射内的所有行，并随提交 payload 回传 `linkage_dict`。
- 影响：声明 `"指标联动"` 的表格初始展示与后续提交会自动保持各联动项的列值一致，旧数据加载后也会被前端同步为主行取值；若需回滚，可移除上述辅助函数并恢复原有 `handleAfterEdit` 逻辑。
- 下一步：可在表格 UI 中增加联动提示（如行高亮、气泡说明）并关联后端差异告警，帮助填报人员理解同步规则。

## 会话小结（2025-11-20 数据填报行内校验）

- 状态：`DataEntryView.vue` 现会读取模板响应中的 `validation_rules`（后端兼容 `校验规则`/`数据校验`），在本地构建行列级校验映射并于编辑/提交前自动执行，校验结果通过“校验提醒”卡片集中提示。
- 改动：
  - 新增 `templateValidationRaw/validationRuleMap/validationDependents/cellValidationMap` 状态与 `rebuildValidationRulesFromRows`、`runFullValidation`、`validateRow` 等辅助方法，解析 `number_range` 与 `less_equal_than` 两类规则，支持列限定、参照行及 warning/error 级别；
  - `handleAfterEdit` 在同步联动行的同时触发行内与被依赖行的校验；`onSubmit` 会在发送请求前强制执行一次全量校验并在存在 error 时阻止提交；
  - 模板顶部新增“校验提醒”面板，按照严重级别与行列定位展示消息；若仍有 warning，提交按钮可用但会保留提醒；
  - 2025-11-20：新增 `column_ratio`（本期列与 `reference_column` 的比例需落在 `min_ratio/max_ratio`）与 `expression_range`（通过 `value('行名')` 求值、可声明 `reference_column` + `min_ratio/max_ratio`、`depends_on`）两种语法，并支持 `virtual: true` + `target_label` 声明“只校验、不展示”的衍生指标，示例见“发电量”80%-120%与“全厂热效率”表达式校验。
- 影响：示例模板 `BeiHai_co_generation_Sheet` 现对“发电量/供热量/耗水量/外购电量”执行非负校验，对“其中：电厂耗水量/外购电量”执行“不得大于主项”校验，并新增发电量本期/同期80%-120%区间与全厂热效率（虚拟指标）表达式校验。如需扩展其它表，只需在模板 JSON 中追加同名规则即可生效。无规则的模板体验保持不变。
- 校验总开关：模板若返回 `validation_enabled` / `enable_validation` / `校验开关 = false`，页面会完全跳过校验（不展示提醒、不阻塞提交）；恢复为 `true` 时重新解析规则并立即失效/生效。
- 回滚：若暂不需要校验，删除模板中的 `"校验规则"` 字段即可；前端检测到 `validation_rules` 为空后将自动移除提醒面板、恢复旧的提交行为。

## 会话小结（2025-11-07 审批取消批准按钮）

- 状态：项目页审批进度卡片依据新增 `can_revoke` 权限显示“取消批准”按钮，允许在前端撤回已完成审批的单位。
- 改动：扩展 Pinia `auth` 仓库（`store/auth.js`）与 API 客户端（`services/api.js`）以支持 `revokeWorkflow`、`canRevokeUnit`，并在 `PageSelectView.vue` 的审批列表中根据状态/权限切换“批准”与“取消批准”按钮。
- 影响：Global_admin / Group_admin / ZhuChengQu_admin 登录时，若单位处于 `approved` 状态且在可见范围内，可直接将其恢复为待审批；其它角色界面不受影响。
- 下一步：如需追踪撤销记录，可在 UI 中补充撤销人和时间字段，并与后端潜在审计字段对齐。

## 会话小结（2025-11-07 数据展示页加载提示）

- 状态：`DisplayRuntimeView.vue` 在等待数据库视图数据回填时，展示“数据载入中...”占位文案，加载完成但仍无列数据时继续提示“无展示数据”。
- 改动：占位块绑定现有 `loading` 状态，使用三元表达式区分加载阶段与真实空数据，避免首屏短暂闪现“无展示数据”导致误解。
- 影响：仅影响 `projects/daily_report_25_26/pages/data_show/sheets` 页面；其它页面抢占逻辑、接口与样式保持不变，如需回滚文案可恢复该 Vue 文件的旧版本。
- 下一步：可按需求评估骨架屏或进度条组件，进一步优化长耗时查询的用户体验。

## 会话小结（2025-11-03 仪表盘 DashBoard.vue 文件审查）

- 状态：本次操作为审查 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 文件内容，无代码改动。
- 说明：该文件是一个 Vue3 组件，用于展示仪表盘，包含本地 `Card`、`Table` 和 `EChart` 组件，以及模拟数据和样式。仪表盘展示了与“生产日报”相关的各项指标和图表。
- 影响：本次操作仅为文件审查，无任何代码改动，因此无影响范围。
- 下一步：根据项目计划，可以开始将仪表盘组件与后端 `dashboard/summary` 接口进行联调，替换模拟数据为真实数据。

## 会话小结（2025-11-06 项目页移除占位入口）

- 状态：项目页列表不再显示 `placeholder` 占位卡片，确保只展示可访问的实际页面或调试入口。
- 改动：后端调整 `backend_data/项目列表.json`，前端读取 `/projects/daily_report_25_26/pages` 时已不包含该节点，页面枚举逻辑无需修改。
- 影响：`/projects/daily_report_25_26/pages` 页面与卡片列表将消失“用于占位（稍后开始构建）”项；如需恢复，可让后端重新添加对应配置。
- 下一步：若需要支持跳转至非配置文件驱动的页面，可在页面清单中增加 `type`/`route` 等字段，与当前卡片渲染逻辑配合扩展。

## 会话小结（2025-11-06 审批页面默认业务日）

- 状态：审批页 `ApprovalView.vue` 中 `regular` 模式默认读取 workflow status 的 `biz_date`（昨天），不再随 `set_biz_date` 变化。
- 改动：组件在刷新前调用 `getWorkflowStatus`，将返回的 `biz_date` 作为请求体传递给 `/runtime/spec/eval`；“自定义”模式仍沿用既有输入框。
- 影响：审批页面只受业务日驱动，展示页仍使用 `set_biz_date` 控制；如需恢复旧逻辑，可回滚该组件改动。
- 下一步：可视需要在顶部提示“当前展示日期”并引用 workflow status 的 `display_date`，帮助审批员了解展示口径。

## 会话小结（2025-11-06 仪表盘 Vue 组件重构）

- 状态：依据 `configs/仪表盘参考.vue` 的设计稿，`pages/DashBoard.vue` 已改写为 Vue3 `<script setup>` 单文件组件，保留示例数据与栅格布局，直接在前端渲染 7 个仪表盘卡片与顶部指标摘要。
- 改动：
  - 重写 `pages/DashBoard.vue`，定义局部 `Card` / `Table` 组件并通过 `EChart` 渲染 ECharts 配置，复刻气温、收入分类、单耗、煤耗、投诉量、煤炭库存等模块。
  - 统一整理静态演示数据、表格列定义与关键指标展示值，后续可替换为后端 `dashboard/summary` 接口的真实返回；内联 CSS 重现原设计的配色、阴影与栅格布局，无需依赖 Tailwind。
  - `router/index.js` 与 `PageSelectView.vue` 新增 `dashboard` 路径处理，“数据看板”卡片现可直接跳转到新版仪表盘页面。
  - `index.html` 通过 CDN 注入 `echarts.min.js`，`DashBoard.vue` 内置 `EChart` 轻量包装组件管理实例，避免额外 npm 依赖；摘要卡片与表格样式升级为渐变配色与栅格阴影风格，并自动读取 ECharts 调色板为表格边框/悬停色提供渐变。
- 影响：仪表盘页面可在 Vue 环境完整呈现设计稿，后端接口联调时仅需替换数据载入逻辑；如需回滚，恢复旧版 `DashBoard.vue` 与路由改动即可退回 React 风格占位实现。

## 会话小结（2025-11-06 售电煤炭库存权限）

- 状态：为售电公司账号开放煤炭库存表访问权限，`filterSheetsByRule` 支持在 `by_unit` 模式下读取权限文件中的显式授权白名单。
- 改动：`src/daily_report_25_26/store/auth.js` 在 `by_unit` 分支新增 `extraSheets` 集合，允许 `permissions.json` 提供的 `sheets` 列表直接放行无单位前缀的表单，并保留原有单位名称匹配。
- 影响：账号 `shoudian_filler` 登录后可在数据填报页看到 `Coal_inventory_Sheet` 卡片；其他单位仍受单位名前缀限制。如需回滚，删除白名单逻辑即可恢复单纯的单位匹配。

## 会话小结（2025-11-06 HTTP-only 访问修复）

- 状态：为避免构建后的前端请求落入 `D://.../api`，补齐 `deploy/nginx.http-only.conf` 的 `/api/` 代理，在 `ww.bash` 中加入 `VITE_API_BASE` 二次校验、日志输出与 `latest` 标签同步，并新增 `ww-certbot.yml`（固定 `locookies123@gmail.com` 与 `platform.smartview.top` 的参数）供服务器按需单独拉起 HTTP-only + Certbot 组合；需要其它邮箱或域名时，直接修改该文件的 `certbot` 命令参数即可。
- 影响：HTTP-only 部署现在可以继续沿用 `/api/v1` 相对路径；如需自定义外部域名，可显式设置 `VITE_API_BASE`（脚本会打印最终值以便确认）。
- 回滚：还原 `deploy/nginx.http-only.conf` 与 `ww.bash` 到上一个版本即可恢复既有行为。

## 会话小结（2025-11-05 仪表盘页面）

- 状态：展示页 `DisplayView.vue` 从占位按钮升级为真实仪表盘，联动后端新接口展示 7 个板块。
- 改动：
  - `services/api.js` 新增 `getDashboardSummary`，统一调用 `GET /api/v1/projects/daily_report_25_26/dashboard/summary` 并支持 `biz_date` 参数。
  - `pages/DisplayView.vue` 集成交互：业务日选择、加载状态提示，以及气温折线、指标对比、煤库存堆积柱等卡片布局。
  - 新增 `components/dashboard/LineChart.vue`、`GroupedBarChart.vue`、`StackedBarChart.vue`、`TemperaturePanel.vue`、`MetricComparisonPanel.vue`、`CoalInventoryPanel.vue` 等基础组件，使用 SVG 手绘满足图形化展示要求。
  - 交互特点：可按业务日刷新、指标下拉切换（单耗/投诉等），表格同步展示本期/同期值、差值与差率，煤炭库存卡片以堆积柱并列三段。
- 回滚方式：删除新增组件并恢复 `DisplayView.vue` 至原占位版本即可回退到旧展示状态；同时移除 `api.js#getDashboardSummary`。

## 会话小结（2025-11-04）

- 状态：`ww.bash` / `ww.ps1` 新增前端镜像构建链路，同步生成 `phoenix-web`（HTTPS 版）与 `phoenix-web-http`（HTTP-only 版）镜像并推送到 Docker Hub，可配合 `ww.yml` 或 `ww-http-only.yml` 直接部署。
- 改动：脚本允许通过 `VITE_API_BASE` 环境变量覆写打包时的接口前缀，同时记录构建时间戳；新增校验自动过滤 `file://` / Windows 本地路径，避免前端构建后指向本地磁盘。PowerShell 版本便于在纯 Windows 环境执行。
- 部署：`ww.yml` 继续使用 `deploy/Dockerfile.web` 生成的静态资源镜像，运行时只需从远端仓库拉取镜像即可；`ww-http-only.yml` 仅暴露 `80:80`，适合纯 HTTP 或将 TLS 托管给 Cloudflare 的场景。
- 下一步：如需缩短镜像体积，可在后续迭代中将 `npm ci` 缓存目录挂载到宿主或改用多阶段缓存策略。
- 数据接口：后端新增 `calc_temperature_data` 视图（按 `temperature_data` 的日期聚合日最高/最低/平均温度），后续若开放 REST 接口，可在天气数据填报或展示页面接入该聚合结果。

## 会话小结（2025-11-03）

- 状态：登录页已按“雏鸟计划”参考风格重构，采用左右分栏视觉面板 + 表单布局，沿用现有 Pinia 登录流程。
- 影响：`daily_report_25_26/pages/LoginView.vue` 新增视觉装饰与响应式样式，其余页面结构未调整；今日补充标题与描述文字居中，并微调蓝色渐变令整体色调更深。
- 下一步：若需要验证码或更多公告信息，可在当前表单面板内扩展交互，不影响已有登录链路。

## 会话小结（2025-11-02）

- 状态：本次后端仅调整运行时表达式取值规则，前端代码与路由结构未发生变化。
- 影响：展示页/审批页已依赖的指标（如“省市平台净投诉量”行的 `(本期月)/(本供暖期)` 列）会自动受益于后端修复，无需额外前端补丁。
- 下一步：待后端提供更多不可加指标白名单时，若需要在前端显式提示“按日累计值已直接返回”，可在表格列标题处补充说明。

## 会话小结（2025-10-29）

- 状态：本次会话仅为初始化与规范确认，无前端代码改动与目录调整。
- 动作：完成 Serena 项目激活与入职检查；按 AGENTS 3.9 使用 `apply_patch` 对仓库文档进行留痕。
- 下一步：待后端最小闭环接口到位后，在 `daily_report_25_26/pages/DataEntryView.vue` 路径接入行数据渲染与提交链路联调。

### 增补（2025-10-29 夜）
- 常量页查询修复：`DataEntryView.vue` 在 `templateType==='constant'` 时增加一次 `/query` 调用（无需 `biz_date`），并使用通用回填函数 `applyStandardQueryResult` 将常量 period 列与行数据写入网格，解决“constant_data 有数据但前端不显示”的问题。

## 结构快照更新（2025-10-29）

- 本次仅对后端 SQL 视图进行了职责拆分与计算指标扩展：`sum_basic_data`（仅公司明细 + 计算指标）与视图 `groups`（主城区/集团再聚合，比例/单耗类按“组内分子/常量”重算）。前端接口与页面结构不变。
- 命名对齐说明（无前端改动）：后端已统一 `sheet_name` 尾缀为 `*_Sheet`，中心英文码为 `*_Center`。前端无需感知大小写修正，依旧消费 `template/sumbit/query` 返回的字段。

## 目录结构

```
frontend/
├─ .env.development         # 本地调试环境变量（API 基础路径等）
├─ Dockerfile               # 前端容器镜像定义
├─ nginx.conf               # Nginx 转发配置
├─ package.json
├─ vite.config.js
├─ src/
│  ├─ App.vue               # 根组件
│  ├─ main.js               # 应用入口
│  ├─ router/index.js       # 全局路由：/login、/projects、/projects/:projectKey/data_entry/sheets、/projects/:projectKey/data_entry/sheets/:sheetKey
│  ├─ stores/               # Pinia store（占位）
│  └─ daily_report_25_26/
│     ├─ components/        # AppHeader、Breadcrumbs、dashboard 下的可视化组件
│     ├─ constants/         # project_key、sheet 常量
│     ├─ pages/             # LoginView、ProjectSelectView、DisplayView（仪表盘）、Sheets、DataEntryView 等
│     ├─ services/          # API 封装（api.js）
│     ├─ store/             # 业务状态（预留）
│     └─ styles/theme.css   # 统一视觉风格
├─ public/
└─ README.md
```

## 结构快照更新（2025-10-28）

- 本次变更为后端 SQL 脚本中补充二级物化视图的“唯一索引（并发刷新支持）”，前端目录与页面结构不变、接口不变。
- 若后续展示页直接消费二级物化视图结果，将在 `daily_report_25_26/pages/` 下新增展示组件并同步更新本文结构说明。
 - 本轮后端新增“运行时表达式求值”模块（`backend/services/expression_eval.py`），作为后端内部计算能力，对前端结构与接口无影响。
 - 追加说明（2025-10-28）：评估将后端“一级物化视图”改为“普通视图”不影响前端接口与目录结构；前端依然调用 `/template`、`/submit`、`/query`，与视图物化与否无关。
 - 补充说明（2025-10-28）：示例数据生成脚本已更新至 `backend/scripts/generate_daily_basic_sample.py`，前端无改动；用于快速填充 2025-10-20～2025-10-27 的演示数据。

## 启动方式

开发模式：

```bash
cd frontend
npm install
npm run dev
```

容器模式：

```bash
docker compose up -d --build
```

默认访问地址：`http://localhost:5173/`

## 路由与页面

- `/login` → `LoginView.vue`
- `/projects` → `ProjectSelectView.vue`
  - 首次进入时请求 `GET /api/v1/projects`，显示项目中文名列表并根据所选项目跳转。
- `/projects/:projectKey/data_entry/sheets` → `Sheets.vue`
  - 展示模板清单；按单位分组并以卡片呈现；点击表名进入填报页面；
  - `listSheets` 响应新增 `unit_name/sheet_name` 字段，以适配英文/中文双写。 
- `/projects/:projectKey/data_entry/sheets/:sheetKey` → `DataEntryView.vue`
  - 使用 `@revolist/vue3-datagrid` 提供的 `RevoGrid` 组件渲染表格，自带自定义元素注册；
  - 通过 `@afteredit` 事件回调同步 `gridSource`，提交阶段直接基于 `gridSource` 生成提交数据（rows-only）；
  - 模板 `columns` 会扫描列头中首次出现“计量单位”的位置，将该列及之前列标记为只读，其余列渲染本期/同期/解释说明等可编辑数据。
  - 模板响应中的所有 `*_dict` 字段会缓存至 `templateDicts.entries`，提交时逐项带回，扩展字典（中心/状态等）无需额外适配。
  - 首列在模板与历史数据完成加载后触发 `autoSizeFirstColumn()`，基于整列文本宽度动态设定列宽并再次调用 RevoGrid 自适应，支持任意单元格内容完整显示。
  - 通过 `:apply-on-close="true"` 启用 RevoGrid 内建的失焦自动保存机制，配合 `@afteredit` 更新本地状态，确保未按 Enter 的输入也能保留。

## API 交互要点

所有请求以 `/api/v1` 为前缀，`project_key` 统一为 `daily_report_25_26`。

### 变更记录（2025-10-23）
- 修复数据填报页日历联动：标准表在后端以“列头日期文本”决定每列的 `date`，现于 `pages/DataEntryView.vue` 中缓存原始列头 `baseColumns` 并在 `bizDate` 变更时重算列头与 `gridColumns` 名称，确保提交与展示使用最新日期。
- 通用查询接口（设计中）：保持现有 `services/api.js::queryData(projectKey, sheetKey, payload)` 用于“单表查询”；后续将新增“项目级聚合查询”接口，前端可在数据展示/常量页选择批量请求以减少 HTTP 次数。

### 变更记录（2025-10-28）
- 修复标准表日历切换后数据未刷新的问题：在 `DataEntryView.vue` 中新增 `applyStandardQueryResult`，统一处理 `/query` 回包的列头与 `rows` 回填；`loadTemplate` 首发查询与 `watch(bizDate)` 共同调用该方法，确保切换日期后即时刷新并保持首列自适应宽度，同时避免回包中的列头覆盖前端按昨日/同期替换后的显示。

| 接口 | 说明 |
| --- | --- |
| `GET /api/v1/projects` | 返回项目列表（`project_id/project_name`），供前端展示中文名 |
| `GET /api/v1/projects/{project_key}/data_entry/sheets` | 返回数据填报模板清单；单个条目同时包含 `单位名/表名` 以及 `unit_name/sheet_name` |
| `GET /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/template` | 返回填报模板；`columns` 先保留模板配置中的全部列（含“解释说明”等自定义列），再自动追加当前日期与上一年度同日；`rows` 为二维数组；同时附带模板定义的字典字段（如“项目字典”“单位字典”），提交时需保持字段名与内容不变 |
| `POST /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/submit` | 占位（待实现） |
| `POST /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/query` | 占位（待实现） |

前端 `services/api.js` 会读取 `.env` 中的 `VITE_API_BASE`，默认 `http://127.0.0.1:8000`，可按部署场景调整。

## 与 @revolist/vue3-datagrid 的配合

- `DataEntryView.vue` 直接导入 `@revolist/vue3-datagrid` 默认导出的 `RevoGrid` 组件，无需手动调用 `defineCustomElements`；
  - 调试日志：已在 `DataEntryView.vue` 和 `services/api.js` 加入 rows-only 渲染链路的调试输出，包括：
    - `[data-entry/route-init]`、`[data-entry/reloadTemplate]`
    - `[revogrid/watch]`（columns/rows/gridColumns/gridSource 长度）
    - `[api/getTemplate]`、`[api/queryData/request]`、`[api/submitData/request]`
    - `[revogrid/afterEdit]`、`[data-entry/submit]`
  - 观察要点：当 `gridColumns.length > 0` 且 `gridSource.length > 0` 后，应能显示数据；若仍空白，检查模板容器的 `v-if="columns.length"` 是否及时更新。
- 模板首行使用后端返回的四列表头（项目、计量单位、今日日期、去年同日）； 
- 数据从第二行开始对应后端返回的 `rows`（二维数组），并根据列数动态渲染；
- 用户编辑后触发的 `afteredit/afterEdit` 事件统一由 `handleAfterEdit` 处理，同步更新 `gridSource` 与本地缓存，最终调用 `submitData` 接口提交。

## 接口演进记录（2025-10-19）

- 模板接口返回结构已定型：`sheet_key/sheet_name/unit_name/columns/rows`；`columns[2]`、`columns[3]` 自动写入日期，无需前端手动拼装。 
- 模板清单接口兼容中文/英文键名，便于组件直接显示。
- 若模板缺失列名或数据，后端会返回 422，前端需引导用户检查模板配置。

## 环境变量

- `VITE_API_BASE`：前端调用后端的基础地址，开发默认 `http://127.0.0.1:8000`；
- 其余变量按需扩展。

## 生产部署（Nginx + Certbot）

- 使用 `docker-compose.server.yml` 启动生产栈：包含 `web`（Nginx + 前端静态资源 + 反向代理）、`certbot`、`backend`、`db` 四个服务。
- `deploy/Dockerfile.web` 会构建 Vue 静态文件并复制到 Nginx（基础镜像 `nginx:1.27-alpine`），同时加载 `deploy/nginx.prod.conf`。
- 默认域名沿用旧项目 `platform.smartview.top`，`/api/` 反向代理到 `backend:8000`。若域名不同，请同步修改 `nginx.prod.conf` 与证书路径。
- HTTPS 证书存放于卷 `certbot_etc`、`certbot_www`；首次部署需在服务器上执行 `docker compose -f docker-compose.server.yml run --rm certbot certonly --webroot -w /var/www/certbot -d <你的域名>` 获取证书，之后常驻的 `certbot` 服务会每 12 小时自动尝试续期。
- 启动命令示例：`docker compose -f docker-compose.server.yml up -d --build`。
#
# 追加变更记录（2025-10-23）

- 修复交叉表（煤炭库存 Coal_inventory_Sheet）首屏空白：调整 `pages/DataEntryView.vue` 的 `loadTemplate()` 初始化顺序，先判定 `template_type==='crosstab'` 并调用 `setupCrosstabGrid` 初始化列与占位行，再执行镜像查询以回填 `columns/rows`，并避免后续渲染流程覆盖查询结果，确保打开页面即可显示默认日期数据。
# 追加说明：渲染流程（模板 + 镜像查询）

- 标准表（standard）
- 首屏：`getTemplate` → 占位符应用（含日期文字）→ `setupStandardGrid` 渲染 → 立刻调用 `queryData` 以 `rows` 回填网格；
- 首屏：`getTemplate` → 占位符应用（含日期文字）→ `setupStandardGrid` 渲染 → 立刻调用 `queryData` 以 `rows` 回填网格；
- 调试：在应用 query 数据时，会弹出提示框显示响应中的 `request_id`，便于你核对具体是哪一次响应被渲染（若弹窗不可用则降级为控制台 `[query/request_id]` 日志）。
 - 统一行为：standard 与 crosstab 均只在模板加载完成后触发一次首发查询；不再执行二次 `loadExisting()` 查询。
  - 日期切换：重算列头文字 → `queryData` 回填当前日期数据；
  - 关键代码：`pages/DataEntryView.vue:249`（`loadTemplate`）、`pages/DataEntryView.vue:541`（watch 处理）。

- 交叉表（crosstab，Coal_inventory_Sheet）
  - 首屏：`getTemplate` 后先确定 `template_type==='crosstab'`，调用 `setupCrosstabGrid` 初始化列与占位行 → 再 `queryData`，若返回 `columns` 则同步列头，并用 `rows` 重建 `gridSource`；
  - 日期切换：`queryData` 返回的 `columns/rows` 直接替换 `columns/gridSource`；
  - 行顺序：后端 `/query` 已按模板定义的 `(单位, 煤种)` 顺序回填，前端无需额外排序即可保持与配置文件一致。
  - 关键代码：`pages/DataEntryView.vue:249`（`loadTemplate`）、`pages/DataEntryView.vue:592`（watch 处理）。

- 接口：`services/api.js:85` `queryData(projectKey, sheetKey, payload, { config })`。
## 数据获取与回填（2025-10-25 更新）

- `/template`：提供模板元信息（`columns`、`rows`、`*_dict` 等）。
- `/query`：现已与模板结构对齐，直接返回 `columns` + `rows`，前端仅消费 `rows` 与 `columns`。
- 已移除 cells 路径：不再读取或合并 `cells`，避免覆盖 `rows`。

### 前端回填要点（2025-10-25）
- 回填顺序与要点：
  - 若存在 `q.columns`，重建/对齐 `gridColumns`（`prop: c${i}`）。
  - 将 `q.rows` 映射为 `gridSource`：`{ c0, c1, ... }`，单元格统一转字符串或空串。
  - 同步设置内部 `rows` 为 `q.rows`，保持显示与提交一致。
## 运维提示：Docker 启动失败（数据库 unhealthy）

- 现象：`phoenix_db` 在编排启动时变为 `unhealthy`，日志包含 `invalid magic number`/`could not locate a valid checkpoint record`。
- 原因：数据库挂载目录 `./db_data` 的 WAL/检查点损坏。
- 建议：先尝试 `pg_resetwal -f "$PGDATA"` 修复；若仍失败，备份并清空 `./db_data` 后重新初始化数据库，再启动前端服务。
## 调试输出策略（2025-10-25）

- 已移除所有前端调试输出：不再使用 `console.*` 与 `alert(...)`。
- 不影响功能：模板加载与 rows-only 渲染流程保持一致。
- 如需排障，建议临时在本地分支加入日志，避免进入主干。
### 2025-10-27 视图规划沟通（AI 辅助）
- 当前会话仅讨论 PostgreSQL 视图设计，前端无需改动；待后端提供视图接口后再补充数据展示方案。
### 2025-10-31 煤炭库存汇总视图对接提示
- 后端新增 `sum_coal_inventory_data`，已按最新日期产出公司与存储方式汇总行，附带 `storage_type='all_sites'`（全部地点）和 `company='sum_company'` 的合计。
- 前端若需展示煤炭库存总览，可直接请求该视图或等待 API 包装，注意根据 `storage_type_cn` 判断列分组并保持单位一致。
### 2025-10-27 审批表渲染对接（计划）
- 后端将提供“运行时表达式求值”服务，返回已替换表达式的 `columns + rows`（rows-only）结构。
- 前端保持 RevoGrid 渲染逻辑不变，仅消费后端返回的行数据；无需内置任何公式解析。
- 如需差异颜色/箭头等展示效果，可在拿到 `*_diff_rate()` 结果后按阈值做样式扩展（后续再议）。
### 2025-10-27 调试页新增（已实现）
- 新增页面：`/debug/runtime-eval` → `src/daily_report_25_26/pages/RuntimeEvalDebug.vue`
- 用途：调用后端 `POST /api/v1/projects/daily_report_25_26/runtime/spec/eval`，按模板运行时计算表达式并以表格展示结果。
- 使用：支持“零参数”请求，程序会从 `config` 指定的模板自动读取 `sheet_key` 与 `unit_id(company)`；也可手动输入覆盖。
  - 建议：`config` 使用 `configs/字典样例.json`（相对 `/app/data`）；`biz_date` 可选 `regular` 或指定日期。
 - 项目入口：已在 `backend_data/项目列表.json` 增加 `\"/debug/runtime-eval\"` 页面项，在“选择页面”界面点击“运行时表达式求值（调试）”卡片即可跳转。

### 2025-10-30 数据展示页后台修复提示
- 影响说明：后端运行时表达式 `_preprocess` 已修复嵌套 `I(...)` 参数解析，`value_*` 不再返回空值；数据展示页（含“省市平台净投诉量”）将直接收到数值，无需前端改动。
- 验证建议：若单元格仍为空，可在调试页开启 `trace=true`，核对 `safe_expr` 是否为 `value_*(\"指标\")`，并结合 `configs/10.30trace.md` 对比排查。

### 2025-10-30 展示表二（交叉表）支持
- 新增 `column_headers`/`column_groups` 元数据透传，RevoGrid 通过 `column-grouping` 渲染两行表头。
- 首两列继续显示“项目/计量单位”，其余列按“公司 × (本期日/同期日/日差异)” 分组，支持多公司比较。
- Trace 模式下可对比 `_trace` 中 `func_calls`、`used_consts`，快速定位某公司缺数据的原因。

## 会话小结（2025-11-06 HTTPS 切换）
- 变更：`ww-http-only.yml:1` 已升级为 HTTPS 部署方案，`web` 改用 `WEB_IMAGE` 并开放 `80/443`；证书卷与 `certbot` 容器保证续期。
- 影响：前端打包无需指定完整域名，默认 `/api/v1` 即可；Nginx 在容器内负责将 `/api/` 代理到 `backend:8000`。
- 构建：如需临时纯 HTTP-only，可设置环境变量 `BUILD_HTTP_ONLY=1` 并在 compose 中改回 `WEB_HTTP_IMAGE`。

### 域名/证书具体化（2025-11-06）
- 前端部署域名：platform.smartview.top；HTTPS 由 Nginx 终止，证书路径通过 compose 绑定到容器内 `/etc/letsencrypt`。
- 生产构建：维持 `VITE_API_BASE=/api/v1`（相对路径），由 Nginx `/api/` 反代后端，无需在前端写死域名。

### 会话小结（2025-11-06 ww.ps1 精简）
- 生产构建：脚本只产出 `phoenix-web:<ts>`，不再涉及 HTTP-only 或 latest。
- API 前缀：默认 `/api/v1`；如需更改，构建时设置 `VITE_API_BASE` 即可。

### 构建镜像源调整（2025-11-06）
- 前端构建所用基础镜像切换为 DaoCloud 镜像源：
  - Node: `docker.m.daocloud.io/library/node:20-alpine`
  - Nginx: `docker.m.daocloud.io/library/nginx:1.27-alpine`
- 仅影响拉取来源，前端功能与打包结果不变；需要回退时把 Dockerfile 恢复原 FROM 即可。
## 会话小结（2025-11-02 常量提交键位调整）

- 状态：后端常量写库不再使用 `center/center_cn`；幂等键改为 `(company, sheet_name, item, period)`。
- 前端影响：
  - 提交 `constant` 模板时，继续发送 `columns/rows` 与字典字段；无需包含中心字段；
  - 若模板包含“中心”列，其值仅用于后端解析 `company/company_cn`，前端无需特殊处理。

## 结构快照更新（2025-12-13 数据分析页梳理）

- 文件：`frontend/src/daily_report_25_26/pages/DataAnalysisView.vue`。主要包含单位多选、分析模式（单日/累计）、日期联动、指标分组多选、生成分析结果入口，以及摘要/相关矩阵/逐日 RevoGrid/趋势图（ECharts）与 Excel 导出；状态由 `selectedUnits`、`selectedMetrics`、`analysisMode`、`timelineGrid`、`activeTimelineMetricKeys` 等 ref 管理，计算属性生成 `correlationMatrixState`、`timelineChartOption` 等图表配置。
- 本次仅阅读结构，无代码改动；若后续调整交互/样式，请同步更新本说明与进度记录。

## 会话小结（2025-12-17 供暖水单耗口径提示）

- 后端 `analysis.sql` 调整“供暖水单耗”分子，不再乘以 10000，公式为耗水量总和 / 供暖收费面积（万㎡）；前端数据分析页、展示页无需改动，读取新视图值即可。
- 若发现数值骤降属预期口径收敛；如需回滚，后端恢复乘以 10000 的公式即可。

## 会话小结（2025-12-18 数据分析页环比比较）

- `pages/DataAnalysisView.vue` 新增“累计数据”模式下的环比比较：当选择的起止日期不同，自动取紧邻上一段（同长度；整月则取上月）累计值进行对比，最早不早于 2025-11-01。
- “数据简报”新增环比表格，复用同比表格样式，展示上期累计、本期累计与环比百分比；若上一周期早于最早日期或无数据，则提示环比未计算。

## 会话小结（2025-12-18 本单位分析环比）

- `components/UnitAnalysisLite.vue` 增加环比比较：累计模式起止不同才计算，整月取上月、否则同长度上一段，最早不早于 2025-11-01；无可用上一周期则提示。
- “同比比较/环比比较”表格居中显示，环比率带正负颜色；导出 Excel 时会包含环比比较分块或提示。

## 会话小结（2025-12-02 北海分表分析视图说明）
- 后端新增 `analysis_beihai_sub_daily` / `analysis_beihai_sub_sum` 视图，专供北海分表（热电/水锅炉）按 sheet_name 聚合的 9 个指标，口径与原公司级视图一致。
- 前端当前页面无需改动；若后续需要按 sheet_name 维度展示，可直接调用上述视图并沿用原指标字段（item/item_cn/unit/value_*）。

### 2025-12-02 本单位分析口径扩展（北海）
- `components/UnitAnalysisLite.vue`：当单位为 BeiHai 时，新增“分析口径”单选，默认公司级，另可选择 `BeiHai_co_generation_Sheet`、`BeiHai_water_boiler_Sheet` 分表口径；切换后重新加载指标与结果，导出内容随口径变化。
- 北海单位“分析口径”改为下拉框并默认公司口径，热电/水锅炉分表与公司并列可选，指标一致。- 北海默认口径文案更新为“北海汇总”。- 北海分表口径文案：热电分表“北海热电联产”，水锅炉分表“北海水炉”。- 北海分表口径指标统一用公司口径加载，确保指标一致，结果按所选分表查询。- 北海分表口径接口参数：unit_key 固定 BeiHai，scope_key 携带所选分表，防止未知单位错误；后端若需要区分分表可据 scope_key 处理。- 分表口径查询参数：unit_key=所选口径（含分表），schema_unit_key=BeiHai（加载指标），scope_key=所选分表，便于后端切换 `analysis_beihai_sub_*` 视图。- 分表分析请求：unit_key=BeiHai（公司口径），scope_key=分表，用于后端选择北海子视图；schema_unit_key 仍为 BeiHai 以加载指标。- 北海分表分析后端已支持 scope_key 分流到子视图（analysis_beihai_sub_daily/sum），前端无需额外修改。
# 会话小结（2025-12-02 数据分析接口 scope_key 修复）

- 后端修复：`backend/api/v1/daily_report_25_26.py` 中的 `DataAnalysisQueryPayload` 补充了 `scope_key` 和 `schema_unit_key` 字段。



## 会话小结（2025-12-02 本单位分析口径交互优化）

- `UnitAnalysisLite.vue` 中北海分表口径文案已更新为“子表：...”。
- 切换口径时现在会保留已选指标，不再自动清空，方便对比。

## 会话小结（2026-01-03 本地开发环境配置路径修复）

- 后端 `backend/config.py` 已修复本地开发环境下 `DATA_DIRECTORY` 的指向问题（自动探测 `backend_data`），解决了本地调试时“智能体设定”无法读取/保存配置文件的错误。
- 前端无需改动，但本地联调时不再依赖 Docker 环境的 `/app/data` 挂载。

## 会话小结（2026-01-03 智能体设定保存修复）

- 修复了 `services/api.js` 中 `updateAiSettings` 方法漏传 `allow_non_admin_report` 与 `enable_validation` 字段的问题，确保前端开关状态能正确写入后端配置。

## 会话小结（2026-01-10 数据分析环比缩放修正）

- 后端修正了 `/data_analysis/query` 响应中 `ringCompare.prevTotals` 的百分比缩放问题。前端 `DataAnalysisView` 在渲染环比表格时，不再会出现“本期 85% vs 上期 0.85%”的量级冲突，所有百分比指标的“上期累计”列均已对齐至 0-100 量级。

## 会话小结（2026-02-08 项目模块化管理页）

- 新增页面：`frontend/src/daily_report_25_26/pages/ProjectModularizationView.vue`
  - 功能：查看 `config/runtime` 文件迁移状态，执行“仅复制缺失文件”的初始化动作。
  - 权限：仅系统管理员（`系统管理员` / `Global_admin`）可操作。
- 路由新增：`/projects/:projectKey/modularization`（`src/router/index.js`）。
- 页面入口：`PageSelectView.vue` 新增“项目模块化管理”卡片，仅系统管理员可见。
- API 封装新增（`src/daily_report_25_26/services/api.js`）：
  - `getProjectModularizationStatus(projectKey)`
  - `bootstrapProjectModularization(projectKey)`
- 对应后端接口：
  - `GET /api/v1/projects/{project_id}/modularization/status`
  - `POST /api/v1/projects/{project_id}/modularization/bootstrap`

## 会话小结（2026-02-08 项目模块化配置驱动适配）

- 前端模块化管理页无需改动交互；后端已将迁移文件清单切换为“项目配置驱动优先”。
- 影响：同一页面可直接适配不同项目的迁移清单，不再要求后端为每个项目新增硬编码清单。
- 建议：新增项目时在 `项目列表.json` 配置 `modularization` 字段，可让管理页展示更准确的文件状态。

## 会话小结（2026-02-08 项目注册表统一默认值）

- 本轮前端页面与交互无新增改动。
- 后端已新增项目注册表并统一默认项目 key/迁移清单来源，前端模块化管理页继续复用现有接口即可正常工作。

## 会话小结（2026-02-08 项目路由注册表）

- 本轮前端代码无改动。
- 后端路由接入改为“项目路由注册表 + 循环挂载”后，前端已有访问路径不变，现有页面与 API 调用保持兼容。

## 会话小结（2026-02-08 模块化解析服务统一）

- 本轮前端代码无改动。
- 后端将模块化文件清单解析收敛为统一服务后，前端模块化管理页继续调用原有接口，无需调整。

## 会话小结（2026-02-08 项目目录入口落地）

- 本轮前端代码无改动。
- 后端已将项目路由来源切换到 `backend/projects/daily_report_25_26/api/router.py` 入口（过渡层），前端访问路径与行为保持不变。

## 会话小结（2026-02-08 模块化接口下沉到项目目录）

- 本轮前端代码无改动。
- 后端已将 `/project/modularization/*` 接口实现迁移到 `backend/projects/daily_report_25_26/api/modularization.py`，前端仍按原路径调用，无需调整。

## 会话小结（2026-02-08 数据看板接口下沉到项目目录）

- 本轮前端代码无改动。
- 后端已将 `/dashboard*` 相关接口实现迁移到 `backend/projects/daily_report_25_26/api/dashboard.py`，前端现有调用路径保持兼容。

## 会话小结（2026-02-08 日报核心实现文件归位）

- 本轮前端代码无改动。
- 后端已将 `daily_report_25_26` 核心实现文件整体迁入项目目录，旧路径仅保留兼容层；前端接口调用路径保持不变。

## 会话小结（2026-02-08 backend_data 项目化归位）

- 本轮前端代码无改动。
- 后端数据挂载目录已迁移为 `shared + projects/daily_report_25_26` 结构，前端 API 路径保持不变。

## 会话小结（2026-02-08 全局状态文件归位）

- 本轮前端代码无改动。
- 后端将审批状态与 AI 使用量统计统一归位到 `backend_data/shared/`，前端接口路径与交互不受影响。

## 会话小结（2026-02-08 全局项目选择页目录归位）

- `ProjectSelectView.vue` 已从项目目录迁移到全局目录：
  - `frontend/src/pages/ProjectSelectView.vue`
- 路由 `/projects` 已改为加载全局页面文件。
- 页面功能不变，仅修正“全局页不应放在项目目录”这一结构问题。

## 会话小结（2026-02-11 春节迷你看板空白定位与联调）

- 本轮前端页面结构无新增迁移，继续使用：
  - 入口页：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalEntryView.vue`
  - 看板页：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 联调结论：
  - 调试面板显示命中指标存在，但来自后端提取 JSON 的 `current/prior` 为公式字符串，导致图表无法按数值渲染。
  - 已由后端提取器修复公式转数值，前端继续复用现有渲染逻辑即可。

## 会话小结（2026-02-12 春节迷你看板气温链路与卡片样式）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 气温数据链路对齐：
  - mini 看板的气温解析改为与 `daily_report_25_26` 主看板一致的 section 解析逻辑；
  - 支持 `1/1.逐小时气温/逐小时气温/calc_temperature_data` 等键名回退，避免结构轻微变化导致空图。
- 卡片视觉对齐：
  - 前四张摘要卡片新增渐变背景类（蓝/橙/红），并同步白色文本与阴影样式，与主看板风格保持一致。
- 验证结果：
  - `npm run build` 已通过，`SpringFestivalDashboardView` 打包成功。

## 会话小结（2026-02-12 春节迷你看板日期策略）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 日期选择默认值：
  - 默认选中“北京时间当前日历日的前一日”；
  - 若该日期不在下拉选项中，自动选中最接近的可用日期。
- 气温图时间范围：
  - X 轴改为固定显示“选定日期前 3 日 + 当日 + 后 3 日”共 7 天；
  - 不足数据日期保留刻度并显示空值，便于按窗口观察。
- 调试增强：
  - 调试面板新增 `temperature.windowDates` 字段，直接展示当前图表窗口日期。

## 会话小结（2026-02-12 春节迷你看板气温图读数增强）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 交互与标注增强：
  - 气温曲线 tooltip 统一显示 2 位小数；
  - 图中新增业务日期竖线标识（`markLine`）；
  - 图中常驻显示业务日期的“本期/同期”点位温度值（`markPoint`，2 位小数）。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 春节迷你看板气温全标签显示）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 标注策略调整：
  - 保留业务日期竖线，但取消顶端“业务日期”文字；
  - 本期/同期曲线改为默认显示所有点位标签（2 位小数，单位 ℃）；
  - 去除业务日期单点 `markPoint`，避免与全量标签重叠。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 春节迷你看板标签防碰撞与卡片口径）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 图表优化：
  - 气温标签增加 `labelLayout` 防碰撞（隐藏重叠 + 纵向错位）；
  - 业务日期虚线改为更浅的半透明蓝色。
- 卡片口径优化：
  - 顶部四卡改为“本期值（增减量）”展示，不再显示差异率；
  - 增减量统一按绝对差计算（`current - prior` / `main - peer`）。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 春节迷你看板煤耗图与配色对齐）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 视觉与可读性：
  - 气温图增加横轴边距与底部留白，缓解点位标签与横坐标重叠；
  - 顶部四卡配色改为与主看板同样的蓝/绿/橙/红方案。
- 煤耗图逻辑重构：
  - 原“本期/同期按日期”对比改为“业务日期当日各口径耗原煤量”对比；
  - 口径固定为：集团汇总、主城区、金州、北方、金普、庄河；
  - 柱图默认显示数据标签（两位小数）。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 春节迷你看板煤耗图补齐同期）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 煤耗图更新：
  - “当日各口径耗原煤量对比”改为双柱：本期 + 同期；
  - tooltip 同步展示本期值与同期值；
  - 计量单位保持“吨”，未做单位切换。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 春节迷你看板精度与庄河同期口径）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 精度规则：
  - 顶部卡片：气温保留 1 位小数，其余卡片统一整数；
  - 气温曲线图：tooltip 与点位标签统一 1 位小数；
  - 原煤对比图：本期/同期 tooltip 与柱上标签统一整数。
- 口径与可视化：
  - 庄河口径的同期值优先取“剔除xxx”原煤指标；
  - 原煤图颜色调整为深蓝（本期）+橙色（同期），并保留标签防重叠策略。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 庄河同期指标修正）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 规则修正：
  - 庄河口径的同期值改为优先取“其中：张屯原煤消耗量”；
  - 保留回退关键词匹配，兼容文本中空格差异。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 投诉量分项双图重构）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 结构调整：
  - “投诉量分项（图与表）”改为两张图：
    - 本日总投诉量（本期/同期）+ 本期气温曲线；
    - 本日净投诉量（本期/同期）+ 本期气温曲线。
- 表格调整：
  - 新增最左侧“气温”字段；
  - “总投诉量（本期/同期）”与“净投诉量（本期/同期）”按相邻列呈现。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 投诉分项双图半屏清新风格）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 布局调整：
  - 投诉区域改为双图并排（各占半屏）+ 下方整表；
  - 移动端自动切换为单列。
- 风格调整：
  - 两图改为浅色面板样式；
  - 关闭 y 轴横向网格线；
  - 采用更清新的柱线配色（浅蓝/浅橙/绿色）。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 投诉图气温线截断到业务日期）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 逻辑调整：
  - 投诉双图中的“本期气温”曲线改为仅显示到业务日期；
  - 业务日期后的点位按 `null` 处理，不再绘制。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 投诉量柱同样截断到业务日期）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 逻辑调整：
  - 投诉双图中的总/净、本期/同期柱，统一按“业务日期后置空”处理；
  - 与本期气温线采用同一业务日期截断判断函数。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 投诉区图表与表统一业务日期截断）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 一致性调整：
  - 投诉双图与下方表格统一仅展示到业务日期；
  - 投诉双图改为以 `complaintVisibleRows` 驱动 x 轴与序列；
  - 本期气温线移除数值标签。
- 防重叠增强：
  - 图例启用滚动模式；
  - x 轴标签启用重叠隐藏。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 投诉图横轴标签与早日期观感优化）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 横轴格式：
  - 投诉双图横轴标签改为 `MM-DD`（去掉年份）。
- 观感优化：
  - 双图改为固定窗口日期轴并在业务日期后置空数据；
  - 调整柱宽与柱间距，缓解业务日期靠前时“柱形撑满整图”的视觉问题。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 投诉图完整业务日期轴修正）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 逻辑修正：
  - 投诉双图横轴改为完整业务日期范围（起始到最后业务日）；
  - 业务日期后继续置空数据，形成右侧留白，而非压缩图面。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 顶部PDF导出按钮）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 交互新增：
  - 工具栏新增“下载PDF”按钮；
  - 点击触发浏览器打印流程，可直接“另存为 PDF”。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 mini看板PDF直出与差值+0修正）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 导出能力升级：
  - 由浏览器打印流改为 `html2canvas + jsPDF` 直出下载；
  - 支持按 A4 自动分页保存，文件名包含业务日期；
  - 导出中按钮禁用并显示“正在生成PDF…”。
- 差值显示修正：
  - `formatIncrement` 对 `-0` 做归一化处理；
  - 差值 `0` 场景统一显示为带正号的 `+0`（按既定精度格式化）。
- 依赖更新：
  - 新增 `html2canvas`、`jspdf`（见 `frontend/package.json`）。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 mini看板PDF导出链路对齐主看板）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 导出链路修复：
  - mini 看板 PDF 导出由本地模块导入方式改为 `window.html2canvas + window.jspdf.jsPDF`；
  - 与 `daily_report_25_26` 的 `downloadPDF` 机制保持一致；
  - 导出格式改为 210mm 宽的长页等比导出，更贴近“所见即所得”。
- 依赖回滚：
  - 移除本轮新增的 `html2canvas`、`jspdf` 本地依赖，统一使用 `index.html` 中的 CDN 全局脚本。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 mini看板PDF边距留白优化）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 导出视觉优化：
  - `downloadDashboardPdf` 新增 `6mm` 页边距；
  - 导出内容按可用宽度等比缩放，页面高度同步补齐上下边距；
  - 图片在 PDF 中从 `(padding, padding)` 位置开始绘制，避免左右贴边裁切。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 mini看板原煤/设备明细表扩展）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 原煤明细扩展：
  - 在“当日各口径耗原煤量对比”图下新增每日明细表；
  - 列包含：日期、气温、集团汇总/主城区/金州/北方/金普/庄河 的本期与同期；
  - 数据源来自 `byDate`，并统一仅显示到业务日期。
- 设备明细扩展：
  - 页面底部新增“各单位运行设备数量明细表”（业务日期）；
  - 行口径：北海电厂（含北海水炉）、香海电厂、金州、北方、金普、庄河；
  - 指标列：运行汽炉数、运行汽轮机数、运行水炉数、运行锅炉房锅炉数（均含本期/同期）；
  - 北海口径按“北海热电联产 + 北海水炉”聚合。
- 样式补充：
  - 新增 `table-scroll` 容器以支持宽表横向滚动。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 mini看板设备明细表样式对齐参考表）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 结构修正：
  - 底部设备表由“多指标本期/同期平铺列”改为分组列：`炉机组态`、`调峰水炉`、`燃煤锅炉`；
  - 组内采用“标签 + 本期/同期”组合单元格展示（如 `炉 3/3`），对齐 `daily_report_25_26` 参考样式。
- 规则修正：
  - 设备项本期与同期均为 0 时自动隐藏；
  - 组内全部隐藏时显示 `—`，避免冗余字段堆叠。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 mini看板设备组合项换行）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 样式调整：
  - 设备组合单元格从横向换行改为纵向逐行展示；
  - `combo-item` 增加最小宽度和两端对齐，确保“炉/机”本期/同期在视觉上更容易左右对应。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 mini看板原煤明细表列结构调整）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 表结构调整：
  - 原煤明细表由“每口径拆分本期/同期两列”改为“每口径单列”；
  - 单元格统一展示为 `本期/同期` 格式，提升横向可读性。
- 实现补充：
  - 新增 `formatCurrentPrior` 格式化函数，处理空值与统一精度输出。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 mini看板原煤明细表分级表头）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 结构调整：
  - 原煤明细表改为两级表头；
  - 父级为各口径（集团汇总、主城区、金州、北方、金普、庄河），子级统一为“本期/同期”。
- 数据展示：
  - 行内按口径子列分别展示本期与同期值，不再采用单元格拼接字符串。
- 清理：
  - 删除不再使用的 `formatCurrentPrior` 函数。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 mini看板风格切换与春节主题）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 交互新增：
  - 工具栏增加“风格”开关（默认风格 / 春节氛围）；
  - 主题状态 `themeMode` 支持本地持久化（`localStorage`），刷新后保持上次选择。
- 视觉实现：
  - 新增春节主题背景层（暖色渐变、光斑、轻纹理）；
  - 卡片、按钮、下拉框、表头与表格切换至春节暖色系；
  - 默认主题保留原视觉，不影响现有布局与交互。

## 会话小结（2026-02-12 mini看板春节主题可读性优化）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 可读性修复：
  - 春节主题卡片皮肤改为仅作用于 `.card:not(.summary-card)`，避免覆盖顶部四卡；
  - 顶部四卡在春节主题下单独恢复渐变底色与高对比文字，解决“背景消失/文字不见”。
- 喜庆增强：
  - 新增轻量节庆装饰层（左右灯笼 + “福启新岁”徽标），并保持 `pointer-events: none`，不影响操作。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 mini看板PDF清晰度提升）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 导出质量调整：
  - 将 `downloadDashboardPdf` 中 `html2canvas` 的渲染倍率由 `2` 提升至 `3`；
  - 相比原配置导出像素密度提升约 `1.5x`，改善 PDF 细节与文字清晰度。
- 兼容性说明：
  - 现有边距和长页导出比例保持不变，仅提高渲染分辨率。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 mini看板标题文案调整）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 文案变更：
  - 页面主标题由“春节简化数据看板”调整为“春节数据看板”。

## 会话小结（2026-02-12 主看板气温来源改为日视图兼容）

- 修改页面：`frontend/src/projects/daily_report_25_26/pages/DashBoard.vue`
- 兼容处理：
  - `calcAverageFromList` 从“仅支持逐小时数组”扩展为支持日级对象（`avg/aver_temp/average/value`）与旧数组双格式；
  - `temperatureSeries`、`averageTemp` 继续复用原调用链，自动消费后端返回的日级气温结构。
- 口径结果：
  - 页面上的当日平均气温与气温趋势计算不再依赖小时数组拆解，改为优先使用日级平均值。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 主看板第1节命名改为日均气温）

- 修改页面：`frontend/src/projects/daily_report_25_26/pages/DashBoard.vue`
- 兼容改动：
  - 第1节 section 读取别名改为 `resolveSection('1', '1.日均气温', '1.逐小时气温')`；
  - 兼容旧缓存键与新配置键并行，避免发布切换期显示异常。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 下线项目模块化管理页面）

- 修改范围：`frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue`、`frontend/src/router/index.js`、`frontend/src/projects/daily_report_25_26/services/api.js`
- 清理内容：
  - 移除“项目模块化管理”卡片与页面跳转逻辑；
  - 移除 `/projects/:projectKey/modularization` 路由；
  - 删除前端模块化状态/初始化 API 调用封装。
- 删除文件：
  - `frontend/src/projects/daily_report_25_26/pages/ProjectModularizationView.vue`
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 春节迷你看板“金镶玉”主题重构）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 视觉重构：
  - “春节氛围”模式升级为“金镶玉”风格：深红质感背景 + 暖白宣纸底色卡片 + 2px 金色边框；
  - 细节优化：增加灯笼摇曳动画、朱砂红书法标题风格，并显著提升了图表在节日模式下的清晰度。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 数据展示页导出 Excel 504 超时修复）

- 修改页面：`frontend/src/projects/daily_report_25_26/pages/DisplayRuntimeView.vue`
- 修改服务：`frontend/src/projects/daily_report_25_26/services/api.js`
- 修复内容：
  - 将导出阶段 3 个 `runtime/spec/eval` 由并发改为串行，降低瞬时计算压力；
  - 增加 `AbortController` 超时控制（120 秒）与一次重试（仅超时/504）；
  - 对 Cloudflare 504 HTML 错误做归一化提示，避免页面展示整段 HTML。
- 验证结果：
  - `npm run build` 已通过。

## 会话小结（2026-02-12 修复 jsconfig 报错）

- 修改文件：`frontend/jsconfig.json`
- 调整内容：
  - 路径别名 `@/*` 从 `./src/*` 统一为 `src/*`；
  - 新增 `include`，显式覆盖 `src/**/*.js|jsx|vue|json` 及 `vite.config.*`。
- 结果：
  - 提升前端工程的路径解析稳定性，减少编辑器/语言服务误报。

## 会话小结（2026-02-12 登录“账户信息文件缺失”排障）

- 本轮前端代码无改动。
- 后端已增加账户/权限文件多路径兜底与缺失路径明细报错，用于修复服务器部署目录差异导致的登录失败。

## 会话小结（2026-02-15 春节看板卡片文案修正）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 调整内容：
  - 顶部摘要卡片文案由“当日集团标煤消耗（剔除庄河改造锅炉房）”改为“当日集团原煤消耗（剔除庄河改造锅炉房）”。
- 实现链路说明：
  - 文案位于模板区 `summary-grid` 的第二张卡片 `summary-card__label`；
  - 数值展示仍由同文件内 `coalCard` 计算属性与 `formatMetric/formatIncrement` 负责，业务计算逻辑未改动。

## 会话小结（2026-02-15 春节看板原煤图标题补充口径）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 调整内容：
  - 图表卡片标题由“当日各口径耗原煤量对比”改为“当日各口径耗原煤量对比（剔除庄河改造锅炉房）”。
- 实现链路说明：
  - 标题位于原煤对比图所在卡片的 `<header class="card-header">` 下 `h3` 节点；
  - 图表配置仍由 `coalTrendOption`、`coalScopeRows`、`coalVisibleRows` 驱动，本次未改数据处理逻辑。

## 会话小结（2026-02-15 春节看板两张表新增合计行）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 调整内容：
  - 新增 `sumRowsByField(rows, field)` 作为表格数值列汇总函数；
  - 新增 `coalRowsWithTotal`，在 `coalVisibleRows` 末尾追加“合计”行；
  - 新增 `complaintRowsWithTotal`，在 `complaintVisibleRows` 末尾追加“合计”行；
  - 表格循环分别改为 `v-for="row in coalRowsWithTotal"` 与 `v-for="row in complaintRowsWithTotal"`；
  - “投诉量分项”表格中“净投诉量（本期/同期）”在合计行固定显示 `-`（不参与求和）。
- 实现链路说明：
  - 原煤表仍由 `coalRows -> coalVisibleRows` 过滤业务日期后进入 `coalRowsWithTotal` 汇总输出；
  - 投诉表仍由 `complaintRows -> complaintVisibleRows` 过滤业务日期后进入 `complaintRowsWithTotal` 汇总输出；
  - `formatMetric` 继续负责普通行数值格式化，净投诉量合计例外由模板条件渲染为 `-`。

## 会话小结（2026-02-15 春节看板两张表去除非气温单位）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 调整内容：
  - 原煤表格中各口径本期/同期列由 `formatMetric(value, '吨', 0)` 改为 `formatMetric(value, '', 0)`；
  - 投诉表格中总投诉量与净投诉量列由 `formatMetric(value, '件', 0)` 改为 `formatMetric(value, '', 0)`；
  - 气温列仍保持 `formatMetric(value, '℃', 1)` 不变。
- 实现链路说明：
  - 仅修改模板展示层单位参数，不影响 `coalRowsWithTotal` 与 `complaintRowsWithTotal` 的计算结果与合计逻辑。

## 会话小结（2026-02-15 春节看板气温取数项目键修复）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 修改服务：`frontend/src/projects/daily_report_spring_festval_2026/services/api.js`
- 调整内容：
  - `getTemperatureTrendByDate` 从固定请求 `daily_report_25_26` 改为接收 `projectKey` 参数并按当前项目请求；
  - `loadTemperatureFromDatabase` 调用更新为 `getTemperatureTrendByDate(projectKey.value, selectedDate.value)`。
- 实现链路说明：
  - 页面监听 `selectedDate` 后触发 `loadTemperatureFromDatabase`；
  - 后者通过项目看板接口读取第1节气温数据，构造 `temperatureMainMap/temperaturePeerMap`；
  - 本次修复确保该链路使用当前 `spring` 项目，而非错误地拉取 `daily_report_25_26` 数据包。

## 会话小结（2026-02-15 春节看板气温空白修复：轻量接口）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 修改服务：
  - `frontend/src/projects/daily_report_spring_festval_2026/services/api.js`
  - `frontend/src/projects/daily_report_25_26/services/api.js`
- 调整内容：
  - 新增轻量调用 `getDashboardTemperatureTrend`，避免拉取全量 dashboard 包；
  - 春节项目 `getTemperatureTrendByDate` 改为调用 `daily_report_25_26` 的轻量温度接口；
  - `loadTemperatureFromDatabase` 按“可见日期范围 + 选中日±3天”请求温度，并保留旧 sections 解析回退。
- 实现链路说明：
  - `selectedDate` 变化 -> `loadTemperatureFromDatabase` -> 轻量温度接口 -> 生成 `temperatureMainMap/temperaturePeerMap` -> `temperatureTrendOption` 绘图；
  - 接口返回仅含温度映射，减少网络体积并修复空白问题。

## 会话小结（2026-02-15 春节气温接口路由归位到 spring 项目）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 修改服务：`frontend/src/projects/daily_report_spring_festval_2026/services/api.js`
- 调整内容：
  - `getTemperatureTrendByDate` 改为请求当前项目路径：`/api/v1/projects/{projectKey}/spring-dashboard/temperature/trend`；
  - 页面调用改为显式传入 `projectKey.value`，避免跨项目路径耦合。
- 实现链路说明：
  - 春节页面温度链路现在完全在 spring 项目 API 命名空间内闭环，符合项目模块化边界。

## 会话小结（2026-02-15 春节气温图空白兜底修复）

- 本轮前端页面与交互代码无新增变更。
- 后端 `spring-dashboard/temperature/trend` 已增加 `temperature_data` 聚合兜底，前端现有调用链可直接受益，避免视图空数据导致曲线空白。

## 会话小结（2026-02-15 春节气温接口前端自动回退）

- 修改服务：`frontend/src/projects/daily_report_spring_festval_2026/services/api.js`
- 调整内容：
  - `getTemperatureTrendByDate` 改为“主路径 + 回退路径”调用；
  - 先请求 spring 项目接口 `/spring-dashboard/temperature/trend`；
  - 若请求异常（如后端未热重载导致 404），自动回退到 `daily_report_25_26` 的轻量温度接口。
- 实现链路说明：
  - 在保证模块化主路径优先的前提下，增加运行时降级，避免接口切换窗口期出现温度图空白。

## 会话小结（2026-02-15 春节气温链路增加老接口最终兜底）

- 修改服务：`frontend/src/projects/daily_report_spring_festval_2026/services/api.js`
- 调整内容：
  - `getTemperatureTrendByDate` 增加第3层回退：当两个轻量接口均异常时，回退调用 `getDashboardData('daily_report_25_26')`；
  - 该回退复用历史稳定接口，兼容后端未重载新增路由的运行环境。
- 实现链路说明：
  - 取数优先级：`spring 轻量接口` -> `daily 轻量接口` -> `daily /dashboard 全量接口`；
  - 前端已有 `sections` 解析回退逻辑，因此可直接消费最终兜底返回结构恢复曲线。

## 会话小结（2026-02-15 页面临时调试增强：气温链路可视化）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 修改服务：`frontend/src/projects/daily_report_spring_festval_2026/services/api.js`
- 调整内容：
  - 调试开关默认开启（`debugVisible = true`）；
  - 气温图下新增临时调试面板，输出：
    - 请求参数（项目键、selectedDate、start/end、窗口日期）；
    - 接口命中来源（`spring_light / daily_light / daily_dashboard_full`）；
    - 每层尝试日志（成功/失败、URL、状态码、错误）；
    - 返回主键、`main/peer` 原始条数、映射后条数、样例点；
    - 图表7天窗口逐日 `main/peer` 值与可见点数量。
  - `getTemperatureTrendByDate` 返回 `_debug` 元信息，供页面调试面板直接展示。

## 会话小结（2026-02-15 温度图渲染强制可视化调试）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 调整内容：
  - 温度图 `temperatureTrendOption` 增加显式渲染参数：固定配色、线宽、符号点、`animation=false`、`connectNulls=false`；
  - 温度图 `yAxis` 增加动态 `min/max`，确保当前窗口数据始终落在坐标范围内；
  - 调试输出新增 `echartsPayload`，展示最终送入图表的 `xAxisData/mainSeries/peerSeries`。
- 目的：
  - 在“数据有值但图空白”场景下，区分是数据映射问题还是纯渲染问题。

## 会话小结（2026-02-15 EChart 组件渲染稳态修复）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 调整内容：
  - 内嵌 `EChart` 组件增强：`setOption` 后强制 `resize`、初始化改为 `nextTick` 应用、增加 `ResizeObserver` 监听容器尺寸；
  - 温度调试输出新增 `chartLibraryReady` 与 `hasWindowEcharts` 状态字段。
- 目标：
  - 解决“数据与 series 均正常但图表空白”的实例渲染时序问题。

## 会话小结（2026-02-15 温度图样式回退）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 调整内容：
  - 温度图 `temperatureTrendOption` 的视觉参数回退到既定样式（恢复平滑线与原标签格式）；  
  - 去除排障期间加入的强制渲染样式参数（固定颜色、symbol、动态坐标范围等）；  
  - 调试开关默认值恢复为关闭（`debugVisible=false`）。
- 保留项：
  - EChart 组件层的渲染稳态修复（`nextTick + resize + ResizeObserver`）继续保留。

## 会话小结（2026-02-16 春节看板合计行强调与气温合计算法修正）

- 修改页面：`frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue`
- 调整内容：
  - 为“原煤分项表”“投诉分项表”的合计行增加样式类 `mini-table-total-row`，并设置加粗展示；
  - 新增 `averageRowsByField(rows, field)`；
  - 两张表的 `temperature` 合计计算由 `sumRowsByField` 改为 `averageRowsByField`；
  - 其它指标列仍沿用 `sumRowsByField` 汇总，净投诉量合计保持 `-`。
- 实现链路说明：
  - 原煤表：`coalRows -> coalVisibleRows -> coalRowsWithTotal`，其中合计行 `temperature` 取算术平均；
  - 投诉表：`complaintRows -> complaintVisibleRows -> complaintRowsWithTotal`，其中合计行 `temperature` 取算术平均；
  - 模板层通过 `row.isTotal` 命中样式类，使“合计”行整行加粗。

## 会话小结（2026-02-25 项目列表配置功能确认）

- 本轮前端代码无改动。
- 已确认前端项目/页面选择链路依赖后端读取 `backend_data/shared/项目列表.json`：
  - `frontend/src/projects/daily_report_25_26/services/api.js` 的 `listProjects()` 调用 `GET /api/v1/projects`；
  - 项目页面入口通过 `GET /api/v1/projects/{project_id}/pages` 获取页面名、路由段与描述；
  - 页面显示顺序受 `项目列表.json` 顶层键顺序影响。

## 会话小结（2026-02-25 项目入口权限能力核对）

- 本轮前端核心逻辑无改动。
- 现状确认：
  - 项目卡片是否出现由后端 `GET /api/v1/projects` 返回结果决定；
  - 通用权限体系为页面级，不是项目级；
  - 存在单项目前端硬编码拦截示例：`ProjectSelectView.vue` 对 `daily_report_spring_festval_2026` 仅允许 `Global_admin` 点击进入。

## 会话小结（2026-02-25 用户分组与权限系统核对）

- 本轮前端业务逻辑无改动。
- 现状确认：
  - 前端登录态存储在 `store/auth.js`，持久化到 `localStorage/sessionStorage`；
  - 登录后保存后端返回的 `permissions`，并派生 `canSubmit/canApprove/canRevoke/canPublish`；
  - 页面列表通过 `filterPages` 基于 `page_access` 过滤；
  - 表格列表通过 `filterSheetsByRule` 按 `sheet_rules.mode`（`all/explicit/by_unit`）过滤；
  - 审批与发布按钮按动作权限与单位范围联动显示，并在调用前再做前端拦截。

## 会话小结（2026-02-25 权限模型“项目>页面”改造方案）

- 本轮前端代码无改动，完成适配点梳理。
- 计划中的前端改造点：
  - `store/auth.js` 的过滤函数改为携带 `projectKey`（如 `filterPages(projectKey, pages)`）；
  - 页面访问、表单过滤与动作按钮判断切换到项目维度读取；
  - 保留旧版平铺权限字段兜底，保证后端未切换时前端仍可运行。

## 会话小结（2026-02-25 权限文件模块化已落地）

- 本轮前端改造已完成：
  - `frontend/src/projects/daily_report_25_26/store/auth.js`
    - 新增项目权限解析 `resolveProjectPermission(projectKey)`；
    - `filterPages`、`filterSheetsByRule` 改为支持项目参数，兼容旧签名；
    - 新增 `canSubmitFor/canApproveFor/canRevokeFor/canPublishFor`；
    - `canApproveUnit/canRevokeUnit` 增加项目维度单位范围判断。
  - `frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue`
    - 页面卡片过滤、审批/撤销按钮列显示、发布按钮显示改为按当前 `projectKey` 判断。
  - `frontend/src/projects/daily_report_25_26/pages/Sheets.vue`
    - 表格可见性过滤改为 `auth.filterSheetsByRule(projectKey, pageKey, rawSheets)`。
- 结果：
  - 前端权限消费已可按“项目 > 页面”生效，同时仍兼容旧平铺权限结构。

## 会话小结（2026-02-25 权限配置去重）

- 本轮前端代码无改动。
- 配置侧调整：
  - 权限文件改为仅保留 `projects` 子树，移除组级重复平铺字段；
  - 前端继续通过项目维度权限读取逻辑生效（`resolveProjectPermission(projectKey)`）。

## 会话小结（2026-02-25 unit_filler 煤炭库存表权限修复）

- 本轮前端代码无改动。
- 配置侧修复：
  - 通过账号分组拆分，将 `shoudian_filler` 单独归组；
  - 仅该组保留 `Coal_inventory_Sheet` 显式授权；
  - `unit_filler` 组改为纯 `by_unit` 规则，不再包含该表显式授权。

## 会话小结（2026-02-25 硬编码权限分支核对）

- 本轮前端代码无改动。
- 核对结果：
  - 项目入口处仍有一处春节项目的前端硬编码角色拦截（`Global_admin`），其余页面权限主要已走配置化链路。

## 会话小结（2026-02-25 前端角色硬编码已改为动作位）

- 本轮前端改造：
  - `frontend/src/pages/ProjectSelectView.vue`
    - 删除春节项目入口 `Global_admin` 硬编码拦截，统一依赖后端项目可见性返回；
  - `frontend/src/projects/daily_report_25_26/store/auth.js`
    - 新增项目动作位读取函数：
      - `canManageValidationFor(projectKey)`
      - `canManageAiSettingsFor(projectKey)`
      - `canExtractXlsxFor(projectKey)`
  - `frontend/src/projects/daily_report_25_26/pages/Sheets.vue`
    - 校验总开关按钮权限改为 `canManageValidationFor(projectKey)`；
  - `frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue`
    - 表级校验开关权限改为 `canManageValidationFor(projectKey)`；
  - `frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`
    - AI 配置入口权限改为 `canManageAiSettingsFor(projectKey)`；
  - `frontend/src/projects/daily_report_25_26/components/UnitAnalysisLite.vue`
    - AI 功能管理员判断改为 `canManageAiSettingsFor(props.projectKey)`。
- 结果：
  - 前端角色名硬编码权限判断已统一迁移到 `permissions.json` 动作位。

## 会话小结（2026-02-25 项目列表缓存按账号隔离）

- 修改文件：`frontend/src/projects/daily_report_25_26/services/api.js`
- 调整内容：
  - 新增 `cachedProjectsToken`，将项目列表缓存与当前 `authToken` 绑定；
  - `listProjects()` 缓存命中条件改为“缓存存在且 token 一致”；
  - `setAuthToken()` 在 token 变化时自动清空项目缓存；
  - `resetProjectCache()` 同时清空 `cachedProjects` 与 `cachedProjectsToken`。
- 结果：
  - 切换账号后项目列表会重新请求后端，避免复用上个账号权限结果。

## 会话小结（2026-02-25 项目可用性最高优先级开关联动）

- 本轮前端代码无改动。
- 后端联动行为更新：
  - 项目卡片来源接口 `GET /api/v1/projects` 现已先经过项目可用性总闸；
  - 项目页面接口与项目下路由统一受项目可用性限制；
  - 当项目在 `项目列表.json` 中配置为 `false` 或当前用户组不在白名单时：
    - 前端不会拿到该项目卡片；
    - 即使直连项目接口也会收到 `403`。

## 会话小结（2026-02-25 availability 命名修正）

- 本轮前端代码无改动。
- 联动说明：
  - 项目列表配置键从“项目可用性”统一为 `availability`；
  - 前端交互行为不变，仍由后端 `GET /api/v1/projects` 与项目接口鉴权结果驱动；
  - 单一白名单组也继续使用数组格式（如 `["Global_admin"]`）。

## 会话小结（2026-02-25 availability 旧键兼容移除）

- 本轮前端代码无改动。
- 联动说明：
  - 后端已不再识别旧键 `project_availability`/`项目可用性`；
  - 前端行为保持不变，继续以后端返回的项目列表与接口鉴权结果为准。

## 会话小结（2026-02-25 切换账号项目列表残留修复）

- 修改文件：
  - `frontend/src/projects/daily_report_25_26/composables/useProjects.js`
  - `frontend/src/projects/daily_report_25_26/store/auth.js`
- 调整内容：
  - 在 `useProjects` 新增 `resetProjectsState()`，用于统一清空项目列表状态；
  - 在 `auth.clearSession()` 调用 `resetProjectsState()`，会话清理即清空项目卡片；
  - 在 `auth.login()` 成功后调用 `resetProjectsState()`，账号切换先清空旧列表再加载新列表。
- 结果：
  - 切换账号后不再显示上一个账号的项目卡片残留（无需手工刷新页面）。

## 会话小结（2026-02-25 切号修复方案调整，降低对白屏风险）

- 修改文件：
  - `frontend/src/projects/daily_report_25_26/store/auth.js`
  - `frontend/src/pages/ProjectSelectView.vue`
- 调整内容：
  - 移除 `auth.js` 对 `useProjects` 的直接依赖与状态重置调用；
  - 在 `ProjectSelectView` 进入时执行：
    - `resetProjectsState()` 清空旧项目状态；
    - `ensureProjectsLoaded(true)` 强制按当前会话重拉项目列表。
- 验证：
  - `npm run build` 通过。
- 结果：
  - 保留“切号即刷新项目列表”的效果，同时减少 `auth store` 级联依赖对其他页面（如 `DataAnalysisView`）的潜在干扰。

## 会话小结（2026-02-25 数据分析页白屏修复：isGlobalAdmin 未定义）

- 修改文件：
  - `frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`
- 问题原因：
  - `aiFeatureAccessible` 计算属性仍引用已移除变量 `isGlobalAdmin`，触发运行时 `ReferenceError`，导致页面白屏。
- 修复内容：
  - 将 `isGlobalAdmin.value` 替换为 `canConfigureAiSettings.value`，与当前权限动作位实现保持一致。
- 验证：
  - `npm run build` 通过。

## 会话小结（2026-02-26 管理后台一期）

- 新增页面：
  - `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
- 新增路由：
  - `/projects/:projectKey/pages/:pageKey/admin-console`
- 页面入口接入：
  - `PageSelectView.vue` 已支持 `admin_console` 页面描述与跳转。
- 管理后台能力：
  - 概览：读取 `getAdminOverview(projectKey)`；
  - 校验管理：切换 `data_entry/validation/master-switch`；
  - AI 管理：读取/保存 `data_analysis/ai_settings`；
  - 缓存管理：发布、刷新、停止任务、禁用缓存。
- API 封装新增：
  - `frontend/src/projects/daily_report_25_26/services/api.js` 增加 `getAdminOverview(projectKey)`。

## 会话小结（2026-02-26 管理后台入口与权限调整）

- 入口位置改造：
  - `frontend/src/projects/daily_report_25_26/components/AppHeader.vue`
  - 在用户信息左侧新增“进入后台”按钮，跳转 `/admin-console`。
- 全局路由化：
  - `frontend/src/router/index.js` 管理后台路由调整为 `/admin-console`（不再走项目页参数路由）。
- 页面调用改造：
  - `AdminConsoleView.vue` 改为调用全局 `/api/v1/admin/*` 接口，不再依赖 `projectKey`。
- 权限联动：
  - `store/auth.js` 增加 `canAccessAdminConsole`；
  - 按 `permissions.actions.can_access_admin_console` 控制按钮可见与页面准入；
  - 当前仅 `Global_admin` 在配置中开启该权限。

## 会话小结（2026-02-26 管理后台页面完善）

- 页面重构文件：
  - `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
- 新增板块：
  1. 后台文件编辑：
     - 左侧列出 `backend_data` 子目录；
     - 中间显示选中目录下文件；
     - 右侧在线编辑文件并提交保存。
  2. 项目后台设定：
     - 顶部显示项目切换按钮（项目中文名 + key）；
     - 仅在选中 `daily_report_25_26` 时显示当前“校验/AI/缓存”设定模块；
     - 其他项目显示“暂未接入”提示。
- API 扩展（`services/api.js`）：
  - `listAdminProjects`
  - `listAdminFileDirectories`
  - `listAdminFiles`
  - `readAdminFile`
  - `saveAdminFile`
  - `getAdminOverview(projectKey)`（新增项目参数）

## 会话小结（2026-02-26 管理后台体验重构）

- 页面文件：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
- 结构调整：
  - 改为双标签页：`后台文件编辑` / `项目后台设定`；
  - 文件编辑区重排为“目录选择 + 文件搜索 + 文件列表 + 编辑器”。
- 交互增强：
  - 未保存改动标记；
  - 切换文件前二次确认；
  - 支持 `Ctrl/Cmd + S` 快捷保存；
  - 展示字数与保存反馈。
- 入口样式：
  - `AppHeader.vue` 的“进入后台”按钮增加独立视觉样式，提升识别度。

## 会话小结（2026-02-26 树形文件浏览与弹窗编辑）

- 页面文件：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
- 文件编辑区升级：
  - 将文件列表改为树形结构（目录可展开/收起，文件可点击）；
  - 支持关键字过滤后按树形层级展示。
- 编辑流程升级：
  - 点击文件后在独立弹窗中编辑；
  - 弹窗支持“保存并关闭”“不保存关闭”；
  - 未保存改动关闭确认；
  - `Ctrl/Cmd + S` 快捷保存（弹窗打开时）。
- 交互反馈：
  - 显示当前文件路径、字数、未保存标记与保存结果提示。

## 会话小结（2026-02-26 新窗口编辑器与树形美化）

- 新增文件：
  - `frontend/src/projects/daily_report_25_26/pages/AdminFileEditorWindow.vue`
- 新增路由：
  - `/admin-file-editor`（通过 query 参数传递 `path`）
- 编辑流程调整：
  - 后台文件树点击文件后，不再在主页面弹层编辑；
  - 改为 `window.open` 打开独立新窗口编辑；
  - 支持“保存并关闭 / 不保存关闭”，并在未保存时确认；
  - 支持 `Ctrl/Cmd + S` 快捷保存。
- 主页面联动：
  - `AdminConsoleView.vue` 监听 `postMessage` 的 `admin-file-saved` 回执并提示保存成功。

## 会话小结（2026-02-26 管理后台设定项来源盘点）

- 本轮前端代码无功能改动，完成管理后台“当前内容来源”核对：
  - 页面：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
  - 接口封装：`frontend/src/projects/daily_report_25_26/services/api.js`
- 已确认当前“项目后台设定”模块来源：
  - 设定概览：`getAdminOverview(projectKey)`；
  - 校验总开关：`getAdminValidationMasterSwitch/setAdminValidationMasterSwitch`；
  - AI 设置：`getAdminAiSettings/updateAdminAiSettings`；
  - 缓存任务：`publishAdminDashboardCache/getAdminCachePublishStatus/cancelAdminCachePublishJob/disableAdminCache/refreshAdminCache`。
- 已补齐“分散设定项”前端触点清单（供后续统一并入后台）：
  - `DataEntryView.vue`：表级校验开关、表级 AI 开关、本单位分析开关；
  - `DataAnalysisView.vue`：AI 设置弹窗、分析 schema 驱动参数；
  - `DashBoard.vue`：缓存发布窗口天数、缓存任务状态、气温导入/写库；
  - `PageSelectView.vue`：审批/撤销/发布状态与业务日期展示。

## 会话小结（2026-02-26 项目列表与审批状态文件迁移联动）

- 本轮前端代码无改动。
- 后端数据文件位置变更：
  - 项目列表改为 `projects/daily_report_25_26/config/项目列表.json`
  - 审批状态改为 `projects/daily_report_25_26/runtime/status.json`
- 前端影响评估：
  - 前端仍通过既有 API 获取项目列表/审批状态，不直接读取上述 JSON 文件，接口契约保持不变。

## 会话小结（2026-02-26 迁移更正联动）

- 本轮前端代码无改动。
- 后端文件位置更正为：
  - 项目列表：`backend_data/shared/项目列表.json`
  - 业务日期：`backend_data/projects/daily_report_25_26/runtime/date.json`
- 前端影响评估：
  - 前端仍走 API，不直接依赖这两个 JSON 的物理路径，因此无需前端代码调整。

## 会话小结（2026-02-26 后台文件树去掉独立“目录”控件）

- 修改文件：
  - `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
- 调整内容：
  - 删除后台文件编辑区的“目录”下拉；
  - 树形结构升级为“目录 + 文件”统一节点，目录直接作为可展开节点显示；
  - `loadDirectories()` 调整为批量拉取所有目录文件并合并成单棵树；
  - 保留现有新窗口编辑器流程（点击文件后 `window.open`）。
- 用户可见结果：
  - 页面中不再出现与树重复的目录选择器；
  - 操作从“先选目录再选文件”变为“直接在树中导航并编辑”。

## 会话小结（2026-02-26 后台新窗口 JSON 专用编辑器）

- 修改文件：
  - `frontend/src/projects/daily_report_25_26/pages/AdminFileEditorWindow.vue`
- 新增能力（仅 `.json` 文件）：
  - 自动进入 JSON 专用模式并显示模式提示；
  - 实时语法校验，展示错误信息与行列位置（基于 `position` 计算）；
  - JSON 非法时禁用“保存并关闭”，避免错误写回；
  - 新增“一键格式化 JSON”按钮（2 空格缩进）。
- 非 JSON 文件行为：
  - 继续沿用原文本编辑模式，不受本次改动影响。

## 会话小结（2026-02-26 JSON 错误定位增强）

- 修改文件：
  - `frontend/src/projects/daily_report_25_26/pages/AdminFileEditorWindow.vue`
- 增强内容：
  - JSON 非法时新增错误面板；
  - 显示行列、错误信息、出错行文本与 `^` 指针定位；
  - 便于直接在窗口内修复格式问题，而不是仅看到通用报错。

## 会话小结（2026-02-26 JSON 光标定位）

- 修改文件：
  - `frontend/src/projects/daily_report_25_26/pages/AdminFileEditorWindow.vue`
- 新增能力：
  - 错误面板增加“定位到错误位置”按钮；
  - 通过 `line/column -> absolute index` 计算后，调用 `textarea.setSelectionRange` 自动将光标跳转到错误点；
  - 点击保存时若 JSON 非法，会自动执行一次定位并阻止保存。
- 实现方式：
  - 纯前端原生实现（Vue + textarea），未引入第三方 JSON 编辑器包。

## 会话小结（2026-02-26 管理后台新增系统监控页）

- 修改文件：
  - `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
  - `frontend/src/projects/daily_report_25_26/services/api.js`
- 新增内容：
  - 管理后台顶部新增 `系统监控` 标签页；
  - 接入 `getAdminSystemMetrics()` 调用 `/api/v1/admin/system/metrics`；
  - 展示 CPU/内存/磁盘/进程/运行时长/平台/Python 版本；
  - 支持“立即刷新”与“自动刷新（5秒）”轮询开关。

## 会话小结（2026-02-26 系统监控图形化）

- 修改文件：
  - `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
- 图形化内容：
  - 在系统监控页新增 4 条实时趋势折线（SVG sparkline）：
    - CPU 使用率
    - 内存使用率
    - 磁盘使用率
    - 进程 CPU
  - 前端维护最近 `60` 次轮询样本并绘图，无需新增后端历史接口。

## 会话小结（2026-02-26 系统监控时间显示调整）

- 修改文件：
  - `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
- 调整内容：
  - “最近刷新”时间改为固定按东八区（`Asia/Shanghai`）格式化；
  - 展示格式统一为 `YYYY-MM-DD HH:mm:ss`，不再显示 `+08:00` 后缀。


## 结构同步（2026-02-26 系统后台操作日志页与分类统计）

- 新增前端审计埋点模块：`frontend/src/projects/daily_report_25_26/services/audit.js`
  - 自动记录路由打开事件（`page_open`）
  - 自动记录可点击元素点击事件（`click`）
  - 采用批量缓冲 + 定时上报策略。
- 入口接入：`frontend/src/main.js`
  - 应用启动时初始化审计跟踪。
- 后台页面扩展：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
  - 新增“操作日志”页签（在系统后台内）
  - 支持按时间范围/用户/分类/动作/关键字筛选
  - 支持分类统计展示与日志明细表展示。
- API 扩展：`frontend/src/projects/daily_report_25_26/services/api.js`
  - `postAdminAuditEvents`
  - `getAdminAuditEvents`
  - `getAdminAuditStats`


## 结构同步（2026-02-26 系统监控页新增超级管理员控制台）

- 页面：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
  - 在“系统监控”下方新增“超级管理员控制台”板块；
  - 提供用户名/密码登录区，登录后可执行命令与进行任意路径文件管理。
- API：`frontend/src/projects/daily_report_25_26/services/api.js`
  - 新增超级管理员登录、命令执行、文件管理方法；
  - 新增 `setSuperAdminToken`，后续请求自动携带 `X-Super-Admin-Token`。
- 功能覆盖：
  - 终端命令：command/cwd/timeout + stdout/stderr 展示；
  - 文件管理：目录浏览、文本读取编辑保存、创建目录、移动重命名、删除。


## 结构同步（2026-02-26 超级控制台交互增强）

- 页面：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
  - 命令执行区新增默认命令预设（包含 `cd /home/ww870411/25-26` 与 docker compose down/pull/up -d）；
  - 文件管理区改为资源管理器式布局（左侧目录树 + 右侧目录项列表），支持点选目录后查看并操作文件。


## 结构同步（2026-02-26 超级控制台可靠性修复）

- `AdminConsoleView.vue` 已完成三项修复：
  1) 目录树支持无限层级渲染；
  2) 文件操作后自动刷新目录树并保持当前路径；
  3) 超级管理员令牌过期（401）时自动清理前端 token 并提示重新登录。


## 结构同步（2026-02-26 超级文件管理器右键菜单）

- `AdminConsoleView.vue` 的超级文件管理区新增右键菜单操作：
  - 进入/打开
  - 新建子目录
  - 重命名
  - 删除
  - 复制路径
  - 刷新
- 目录树与列表均支持右键触发，交互更接近资源管理器。


## 结构同步（2026-02-26 超级文件管理器批量与上传）

- 页面：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
  - 文件列表新增多选列与全选；
  - 新增批量操作区（批量删除、批量移动到目标目录）；
  - 新增拖拽上传区与“选择文件上传”入口；
  - 列表新增选中态高亮与上传拖拽高亮样式。
- API：`frontend/src/projects/daily_report_25_26/services/api.js`
  - 新增 `uploadSuperFiles(targetDir, files)` 封装；
  - 上传请求走 `multipart/form-data`，沿用超级管理员令牌鉴权。
- 行为优化：
  - 批量删除/批量移动改为批量执行后统一刷新，减少逐项刷新导致的性能与状态抖动。


## 结构同步（2026-02-26 超级管理员退出登录）

- 页面：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
  - 超级管理员登录区新增“退出管理员登录”按钮；
  - 新增 `handleSuperLogout()`，用于主动清理超级管理员令牌与本地会话缓存（`sessionStorage`）。
- 交互结果：
  - 退出后即失去超级管理员态，命令执行与服务器文件管理等高权限操作需重新登录。


## 结构同步（2026-02-26 超级管理员登录区单行布局）

- 页面：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
  - 超级管理员登录区改为单行布局：用户名、密码、登录、退出同一行展示；
  - 布局实现为 `flex + nowrap`，窄屏时可横向滚动，避免自动折行破坏结构。


## 结构同步（2026-02-26 页签文案：服务器管理）

- 页面：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
  - 顶部页签文案由“系统监控”调整为“服务器管理”；
  - 仅文案调整，`activeTab` 内部键值保持 `system`，不影响现有逻辑与路由。


## 结构同步（2026-02-26 服务器管理改为 SSH 账号登录）

- 页面：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
  - 登录区新增 `主机/端口` 输入；
  - 登录参数从“页面内超管凭据”调整为“SSH 服务器账号”（host/port/username/password）；
  - 文案统一为“服务器管理员登录/会话”，避免与应用内权限混淆。
- API：`frontend/src/projects/daily_report_25_26/services/api.js`
  - `loginSuperAdmin` 改为对象入参（`{ host, port, username, password }`）；
  - 401 失效提示改为“服务器管理员会话已失效”。
- 用户可见行为：
  - 只有 SSH 登录成功后，命令执行与服务器文件管理才可继续使用。


## 结构同步（2026-02-26 服务器管理白屏修复）

- 文件：`frontend/src/projects/daily_report_25_26/services/api.js`
- 修复内容：
  - `loginSuperAdmin` 中入参与响应变量重名导致的语法错误；
  - 入参变量改为 `loginPayload`，响应变量改为 `data`。
- 结果：
  - 修复 `Identifier 'payload' has already been declared`，页面不再白屏。

## 结构同步（2026-02-27 部署问答留痕）

- 本轮前端代码、路由与 API 封装无改动。
- 与部署相关的链路确认：
  - 数据库 5432 暴露由服务器运行编排控制（`lo1_new_server.yml`），非前端或构建脚本逻辑；
  - 构建编排与运行编排可分离，前端联调接口基址策略不受该分离方式影响。

## 结构同步（2026-02-27 部署遗留文件核查）

- 本轮前端代码、路由与 API 封装无改动。
- 仅完成部署遗留文件有效性核查：
  - 当前主流程为 `lo1_new_server.ps1` + `lo1_new_server.yml`；
  - `ww*` 与旧 compose/certbot 文件属于历史部署链路，是否删除取决于是否仍需旧证书与旧部署方案回滚。

## 结构同步（2026-02-28 服务器管理取消页面内登录）

- 页面：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
  - 删除服务器管理中的登录输入区（主机/端口/用户名/密码/登录/退出）；
  - 命令执行、目录刷新、文件读写、批量操作、上传等功能不再受 `superTokenReady` 门槛限制；
  - 页面加载后直接初始化目录树并读取文件列表。
- API：`frontend/src/projects/daily_report_25_26/services/api.js`
  - 移除 `X-Super-Admin-Token` 注入；
  - 删除 `setSuperAdminToken` 与 `loginSuperAdmin`；
  - `/admin/super/*` 接口保留原路径，错误提示改为通用后端消息透传。

## 结构同步（2026-02-28 Phoenix 结构复盘：导表模块迁移评估）

- 本轮前端代码、路由与 API 封装无改动。
- 结构确认结论：
  - 全局壳层路由：`frontend/src/router/index.js`；
  - 项目选择入口：`frontend/src/pages/ProjectSelectView.vue`，项目卡片来自 `GET /api/v1/projects`；
  - 项目页面目录：`frontend/src/projects/<project_key>/...`（当前已含 `daily_report_25_26` 与 `daily_report_spring_festval_2026`）。
- 可复用接入模板：
  - 参考春节项目入口页与 service（`frontend/src/projects/daily_report_spring_festval_2026/`）可快速接入导表模块页面与 API 调用，保持现有项目化路由风格一致。

## 结构同步（2026-02-28 monthly_data_pull 映射显示规则修正）

- 页面：`frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`
  - 新增 `normalizeReferenceName(name)`，用于映射键名展示归一：
    - 去文件扩展名；
    - 去中英文括号及括号内内容（`()`、`（）`、`[]`、`【】`）；
    - 去除多余空白。
  - 源文件/目标底表槽位标题由原始 `key` 改为归一化后的参考名展示。
  - 槽位下方文件名保持实际上传文件名显示（`fileState.*[key]?.name`）。
- 用户可见行为：
  - 映射规则里的“参考文件名”不再携带年月括号；
  - 上传实际文件后，显示的就是该实际文件名，不受映射示例名干扰。

## 结构同步（2026-02-28 项目数据目录归位修正联动）

- 本轮前端页面与 API 调用代码无改动。
- 联动说明：
  - 后端 `monthly_data_pull` 工作目录已统一迁移到 `backend_data/projects/monthly_data_pull/`；
  - 前端仍按既有接口读取后端返回的 `workspace.paths`，无需改动即可展示新目录路径。

## 结构同步（2026-02-28 monthly_data_pull 新增清空目录与打包下载按钮）

- 页面：`frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`
  - 顶部操作区新增两个按钮：
    - `清空目录`：调用后端清空 4 个工作目录文件（带二次确认）；
    - `打包下载`：调用后端打包 `outputs` 并触发浏览器保存 zip。
  - 新增状态：`clearing`、`downloading`，用于防重复点击与按钮文案状态反馈。
  - 清空成功后重置页面状态到步骤 1，避免界面残留旧文件关联。
- API：`frontend/src/projects/daily_report_25_26/services/api.js`
  - 新增 `clearMonthlyDataPullWorkspace(projectKey)`；
  - 新增 `downloadMonthlyDataPullOutputsZip(projectKey)`（返回 `blob + filename`）。

## 结构同步（2026-02-28 monthly_data_pull 批量上传与智能归位）

- 页面：`frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`
  - 步骤 2 新增两个批量按钮：
    - `批量上传源文件并识别`
    - `批量上传底表并识别`
  - 新增隐藏多选文件输入框（`multiple`），并在按钮点击时触发选择。
  - 新增匹配逻辑：
    - `normalizeMatchToken(name)`：文件名归一化（去扩展名、去括号内容、去符号）；
    - `findBestSlotKey(filename, keys)`：对槽位键进行打分匹配，避免并列冲突误匹配；
    - `applyUploadedFile(...)`：复用单文件上传后状态写入与 sheet 自动映射。
  - 批量处理后弹窗反馈：已匹配条目与未匹配文件列表。
- 交互行为：
  - 自动匹配只做预填充，不改变你后续手动调整能力；
  - 对无法确定归属的文件，不会强行自动归位。

## 结构同步（2026-02-28 monthly_data_pull 批量识别预览与确认）

- 页面：`frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`
  - 批量上传新增“识别预览表”，展示 `文件名 -> 识别槽位/未匹配`；
  - 新增预览操作按钮：
    - `确认应用`：确认后才执行逐文件上传并写入槽位；
    - `取消`：放弃本次批量识别结果。
  - 匹配策略升级为一对一占位分配，避免多个文件自动覆盖同一槽位。
- 在“重新解析映射”或“清空目录”后，自动清理旧预览状态，避免跨批次残留。

## 结构同步（2026-02-28 monthly_data_pull 批量确认错误可见性修复）

- 页面：`frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`
  - 在步骤2区域新增 `errorMessage` 展示，批量确认失败可直接看到错误；
  - `applyBatchPreview` 异常分支新增 `alert`，避免用户感知为“无响应”。
- 联动说明：
  - 配合后端 `.xls` 兼容修复，源文件批量确认链路可观测、可定位。

## 结构同步（2026-02-28 登录 404 后端导入链路修复联动）

- 本轮前端代码无改动。
- 联动说明：
  - 后端已将 `xlrd` 调整为可选导入，避免依赖缺失影响 `/api/v1/auth/login` 路由挂载；
  - 前端登录调用链路保持不变。

## 结构同步（2026-02-28 xlsx 口径收敛联动）

- 本轮前端代码无改动。
- 联动说明：
  - 后端已按需求收敛为仅支持 `xlsx`；
  - 前端现有上传 accept 与交互逻辑可继续使用（建议仅选择 xlsx 文件）。

## 结构同步（2026-02-28 monthly_data_pull 结果文件下载鉴权修复）

- API：`frontend/src/projects/daily_report_25_26/services/api.js`
  - 新增 `downloadMonthlyDataPullOutputFile(projectKey, filename)`，使用鉴权请求下载单文件 blob。
- 页面：`frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`
  - 步骤3结果列表由匿名超链接改为鉴权下载按钮；
  - 解决“点击结果文件提示缺少认证信息”问题；
  - 上传控件 `accept` 收敛为 `xlsx/xlsm/xltx/xltm`。

## 结构同步（2026-02-28 研究院源 sheet 自动匹配完善）

- 页面：`frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`
  - 新增 `pickBestSheetName(ruleSheet, actualSheets)`；
  - 源文件上传后，规则 sheet 到实际 sheet 的默认映射改为“按名称归一化智能匹配”，不再统一默认第一张；
  - 仍保留手动下拉改选能力。

## 结构同步（2026-02-28 monthly_data_pull 异常清单区域）

- 页面：`frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`
  - 步骤3新增“异常清单”区域，自动读取本次执行产生的 `execution_log_*.json`；
  - 展示累计对照汇总（总行数、累计一致、不一致、保留公式）；
  - 表格展示异常行（错误行、累计不一致、源公式文本告警）；
  - 在重新解析映射与清空目录时会自动重置异常面板。

## 结构同步（2026-02-28 异常清单展示细化）

- 页面：`frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`
  - 异常清单标题改为固定“异常清单”（不再显示日志文件名）；
  - 源键/目标键列改为去括号后的简化展示（如“金州”）；
  - 异常筛选新增：
    - `warn_source_empty`（源单元格为空）；
    - `warn_month_expr_invalid` / `warn_acc_expr_invalid`（表达式无效）。

## 结构同步（2026-02-28 异常清单新增指标名称列）

- 页面：`frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`
  - 异常清单表格新增“指标名称”列；
  - 展示字段来自执行日志 `indicator_name`。

## 结构同步（2026-02-28 指标名称来源修正联动）

- 本轮前端代码无改动。
- 联动说明：
  - 后端已将 `indicator_name` 字段来源锁定为映射列“子公司月报表指标名称”；
  - 前端异常清单继续直接展示该字段。

## 结构同步（2026-02-28 异常行号口径修正联动）

- 本轮前端代码无改动。
- 联动说明：
  - 后端执行日志 `row_index` 已按映射表可见行号输出（数据行起始为第2行）；
  - 前端异常清单按该行号直接展示。

## 结构同步（2026-02-28 累计一致性异常展示补强）

- 页面：`frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`
  - 异常清单汇总新增“公式未校验”计数；
  - 异常筛选新增 `acc_compare_status=formula_not_verifiable`；
  - 异常说明新增“累计公式无法校验”提示。

## 结构同步（2026-02-28 跨子工作表公式核验联动）

- 本轮前端代码无改动。
- 联动说明：
  - 后端累计公式核验已支持跨 sheet 引用（`Sheet!Cell` / `'Sheet Name'!Cell`）；
  - 前端异常清单继续按 `mismatch/formula_not_verifiable` 展示核验结果。

## 结构同步（2026-02-28 递归公式核验联动）

- 本轮前端代码无改动。
- 联动说明：
  - 后端累计核验已支持“公式引用公式”的递归求值；
  - 前端异常清单将直接体现新的 `mismatch` 检出结果。

## 结构同步（2026-02-28 monthly_data_show 预研）

- 本轮前端代码无改动（仅调研与接入点梳理）。
- 已确认后续新增 `monthly_data_show` 时的主接入位：
  - 项目入口分发：`frontend/src/pages/ProjectEntryView.vue`
  - 项目选择直达逻辑：`frontend/src/pages/ProjectSelectView.vue`
  - 新模块页面目录：`frontend/src/projects/monthly_data_show/pages/`
  - API 复用入口：`frontend/src/projects/daily_report_25_26/services/api.js`
- 需求来源：
  - `外部导入项目-月报表导入数据库/2.28 月报数据库化配置文件.txt`
  - `外部导入项目-月报表导入数据库/综合表26.1.xlsx`

## 结构同步（2026-02-28 monthly_data_pull 中文名调整）

- 页面：`frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`
  - 页面标题：`月报导表工作台` -> `月报拉取工作台`
  - 面包屑末级：`月报导表工作台` -> `月报拉取工作台`
- 联动说明：
  - 项目列表展示名由后端配置同步为“月报拉取工作台”（见 `backend_data/shared/项目列表.json`）。

## 结构同步（2026-02-28 monthly_data_show 第一阶段：CSV 提取页面）

- 新增页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 页面名称：月报入库工作台
  - 交互流程：上传文件 -> 读取可选口径/字段 -> 复选 -> 提取并下载 CSV
  - 提供口径与字段的全选/全不选操作
- 入口接线：
  - `frontend/src/pages/ProjectEntryView.vue`：新增 `monthly_data_show` 入口映射
  - `frontend/src/pages/ProjectSelectView.vue`：将 `monthly_data_show` 加入直达项目
- API 封装：
  - `frontend/src/projects/daily_report_25_26/services/api.js`
    - `inspectMonthlyDataShowFile(projectKey, file)`
    - `extractMonthlyDataShowCsv(projectKey, file, companies, fields)`

## 结构同步（2026-02-28 monthly_data_show 步骤2新增源字段复选）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 步骤2新增“源字段（计划/实际口径）”复选区
  - 支持源字段全选/全不选
  - 提取前新增校验：至少选择 1 个源字段
- API：`frontend/src/projects/daily_report_25_26/services/api.js`
  - `extractMonthlyDataShowCsv` 新增 `sourceColumns` 参数并传递 `source_columns` 表单字段

## 结构同步（2026-02-28 monthly_data_show 步骤2常驻展示）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 步骤2改为页面初始常驻显示（移除上传后才显示的条件）
  - 未读取文件时显示引导文案与空态提示（暂无可选源字段/口径/字段）
  - 各“全选/全不选”按钮在无可选项时自动禁用
- 结果：
  - 首页进入即显示完整 1-2-3 流程，视觉更连贯，交互预期更稳定。

## 结构同步（2026-02-28 monthly_data_show 常量注入设定栏）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 步骤2新增“常量注入设定”面板
  - 支持开关控制“是否启用常量注入”
  - 支持逐条编辑默认常量值
  - 支持逐条选择写入源字段（本年计划/本月计划/本月实际/上年同期）
- API：`frontend/src/projects/daily_report_25_26/services/api.js`
  - `extractMonthlyDataShowCsv` 新增：
    - `constantsEnabled`
    - `constantRules`

## 结构同步（2026-02-28 monthly_data_show 常量写入口径多选）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 常量表格中“写入源字段”由单选下拉改为多选复选组
  - 支持单条常量同时勾选多个源字段
- 交互效果：
  - 提取时将多选口径随 `constant_rules_json` 一并提交后端，生成对应多周期记录

## 结构同步（2026-02-28 monthly_data_show 常量默认与布局调整）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 常量注入面板位置下移至“源字段（计划/实际口径）”面板下方
  - 常量注入开关默认启用
  - 常量规则默认 `source_columns` 与“源字段”默认选中集合保持一致

## 结构同步（2026-02-28 monthly_data_show 常量源字段选项与源字段复选一致）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 常量注入表格中的源字段选项改为实时使用 `selectedSourceColumns`
  - 上方源字段取消勾选后，常量规则中的对应 `source_columns` 会自动移除
  - 当源字段为空时，常量表格显示“请先在上方源字段中选择可用项”提示

## 结构同步（2026-02-28 monthly_data_show 常量源字段显示策略修正）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 常量源字段选项恢复为全量显示（不因上方取消勾选而消失）
  - 上方“源字段”取消某项时，常量区所有规则同步取消该项
  - 上方“源字段”重新勾选某项时，常量区所有规则同步勾选该项

## 结构同步（2026-02-28 monthly_data_show 项目文案更新）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 页面主标题：`月报入库工作台` -> `月报导入与查询`
  - 面包屑末级：`月报入库工作台` -> `月报导入与查询`
- 联动说明：
  - 项目列表名称由后端配置同步为“月报导入与查询”。

## 结构同步（2026-02-28 monthly_data_show 双子页面路由拆分）

- 页面：
  - 导入页：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`\n    - 页面标题调整为“月报导入工作台”
  - 查询页：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`（新增）
- 路由：`frontend/src/router/index.js`
  - 新增：`/projects/monthly_data_show/import-workspace`
  - 新增：`/projects/monthly_data_show/query-tool`
- 入口：
  - `frontend/src/pages/ProjectSelectView.vue` 移除 `monthly_data_show` 直达入口（改为先进入页面选择）
  - `frontend/src/pages/ProjectEntryView.vue` 移除 `monthly_data_show` 直达组件映射

## 结构同步（2026-02-28 移除项目页审批进度模块）

- 页面：`frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue`
  - 删除“审批进度”卡片区域
  - 删除审批状态加载与审批/撤销/发布操作逻辑
  - 删除相关样式定义
- 结果：
  - 项目页仅保留功能页面卡片选择，界面更简洁。

## 结构同步（2026-02-28 项目子页面卡片字体样式对齐）

- 页面：`frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue`
  - `.page-card` 增加字体继承与 `appearance: none`
  - `.page-card-title` / `.page-card-desc` 字号与颜色对齐到项目卡片风格
- 结果：
  - `monthly_data_show/pages` 的子页面卡片字体观感与其他项目卡片一致。

## 结构同步（2026-02-28 审批进度模块按项目定向显示修正）

- 页面：`frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue`
  - 恢复审批进度模块 UI 与审批链路脚本（审批、取消批准、发布、状态读取）
  - 新增项目级判断：`projectKey === "monthly_data_show"` 时隐藏审批进度模块
  - 在 `monthly_data_show` 下不触发审批状态请求；其他项目保持原行为
- 结果：
  - 仅 `monthly_data_show` 页不显示审批进度，其他项目审批模块恢复可用。

## 结构同步（2026-02-28 项目子页面卡片标题颜色统一）

- 页面：`frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue`
  - `.page-card-title` 颜色改为 `color: inherit`
  - 统一跟随页面标题色系，避免卡片标题与“请选择功能页面”颜色不一致
- 结果：
  - 各项目子页面卡片大标题颜色一致，视觉规范统一。

## 结构同步（2026-02-28 项目子页面卡片标题蓝色一致性修正）

- 页面：`frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue`
  - `.page-card-title` 颜色由 `inherit` 调整为 `var(--primary-700)`
  - 直接对齐“请选择功能页面”使用的蓝色标题体系
- 结果：
  - “数据看板”“数据展示页面”等子页面卡片大标题为同样蓝色。

## 结构同步（2026-02-28 monthly_data_show 新增 report_month 字段联动）

- 本轮前端代码无改动。
- 联动说明：
  - 后端 `monthly_data_show` 已新增 `report_month` 导出字段；
  - 前端字段列表来自 `inspect` 动态返回，读取后可直接勾选并导出该字段。

## 结构同步（2026-02-28 monthly_data_show 报告月份设定栏）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 在“步骤 2：复选提取范围”顶部新增“报告月份设定（自动识别，可修改）”面板
  - 增加年份/月份输入控件与 `YYYY-MM-01` 预览
  - `inspect` 后自动填入后端识别出的年月
  - 提取前进行年月合法性校验并随接口提交
- API：`frontend/src/projects/daily_report_25_26/services/api.js`
  - `extractMonthlyDataShowCsv` 新增 `reportYear/reportMonth` 参数
  - 向后端 `extract-csv` 传递 `report_year/report_month` 表单字段

## 结构同步（2026-02-28 month_data_show 建表脚本联动）

- 本轮前端代码无改动。
- 联动说明：
  - 后端新增 `backend/sql/month_data_show.sql`，用于承接 `monthly_data_show` 导出数据后续入库。

## 结构同步（2026-02-28 month_data_show 唯一性口径确认联动）

- 本轮前端代码无改动。
- 联动说明：
  - 后端已确认 `month_data_show` 核心唯一性按 `date, period, type, company, item` 执行；
  - `report_month` 保留为参考字段并提供单列查询索引。

## 结构同步（2026-02-28 monthly_data_show 第4步 CSV 入库）

- API：`frontend/src/projects/daily_report_25_26/services/api.js`
  - 新增 `importMonthlyDataShowCsv(projectKey, file)`，调用后端 `/monthly-data-show/import-csv`
- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 新增“步骤 4：CSV 入库（写入 month_data_show）”
  - 支持 CSV 文件选择、上传入库触发与成功条数提示

## 结构同步（2026-02-28 monthly_data_show 第3步结果一键入库）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 第3步导出完成后，自动缓存导出的 CSV 到内存文件对象
  - 第4步新增按钮“使用第3步结果一键入库”
  - 保留“手动选择 CSV 再入库”作为并行入口
- 结果：
  - 导出后可直接点击一键入库，减少重复操作。

## 结构同步（2026-02-28 monthly_data_show 第3步按钮拆分）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 第3步由“提取并下载 CSV”拆分为两个按钮：
    - `提取 CSV`（仅提取并缓存）
    - `下载 CSV`（下载已缓存结果）
  - 新增提取完成提示文案，显示缓存文件名
  - 与第4步联动保持不变：提取后仍可直接一键入库

## 结构同步（2026-02-28 monthly_data_show 入库空值统计提示）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 第4步入库成功提示新增空值入库统计：
    - `入库成功：共处理 X 条记录（空值入库 Y 条）`

## 结构同步（2026-02-28 monthly_data_show #DIV/0! 空值入库联动）

- 本轮前端代码无改动。
- 联动说明：
  - 后端已将 `#DIV/0!` 纳入空值标记集合，入库时按 `NULL` 处理。

## 结构同步（2026-02-28 monthly_data_show 查询页面第一阶段）

- API：`frontend/src/projects/daily_report_25_26/services/api.js`
  - 新增 `getMonthlyDataShowQueryOptions(projectKey)`
  - 新增 `queryMonthlyDataShow(projectKey, payload)`
- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 由占位页升级为可用查询页
  - 新增筛选区：
    - 来源月份起止、业务日期起止
    - 公司/指标/期间/类型多选
  - 新增汇总卡片：
    - 总记录数、数值非空、数值空值、数值合计
  - 新增结果表与分页：
    - 字段展示：`company,item,unit,value,date,period,type,report_month,operation_time`
    - 上一页/下一页翻页

## 结构同步（2026-02-28 查询页筛选交互重构与开关联动）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - “公司（可多选）”改为“口径（可多选）”
  - 口径与指标改为有序复选列表（支持全选/全不选）
  - 新增开关：
    - `先口径后指标 / 先指标后口径`
    - `是否聚合口径`
  - 移动端下列表布局自适应
- API：`frontend/src/projects/daily_report_25_26/services/api.js`
  - 查询请求新增透传：
    - `order_mode`
    - `aggregate_companies`

## 结构同步（2026-02-28 查询页勾选顺序数字标注）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 在“口径（可多选）”和“指标（可多选）”勾选项旁增加顺序数字徽标
  - 编号按勾选先后显示为 `1,2,3...`，取消后自动重排

## 结构同步（2026-02-28 查询页口径固定顺序）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 口径列表改为固定顺序展示：\n    全口径、主城区、集团本部、股份本部、北海、北海水炉、香海、供热公司、金州、北方、金普、庄河、研究院、主城区电锅炉
  - 固定清单之外的口径自动追加到列表末尾
  - “口径全选”按固定顺序写入选择数组
- 联动：\n  - 指标列表使用后端 `query-options` 返回顺序（后端已调整为首次出现顺序）

## 结构同步（2026-02-28 查询页指标业务排序规则）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 新增 19 个计算指标集合，统一后置显示
  - 指标排序规则：
    - 基础/半计算指标在前
    - 计算指标在后
    - 前半区按：产量 -> 销售量 -> 消耗量（煤/油/水/电/气优先级）-> 其他
    - 相似指标中“总”优先
  - 结果：指标勾选列表更贴合业务阅读与分析路径

## 结构同步（2026-02-28 查询页指标三栏分段）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 指标选择区拆分为三段：
    - 当前指标
    - 常量指标
    - 计算指标
  - 常量指标固定优先顺序：
    - 发电设备容量
    - 锅炉设备容量
  - 计算指标使用固定顺序清单展示
  - 三段内均保留勾选顺序数字标注

## 结构同步（2026-02-28 查询页分栏样式展开修正）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 口径/指标/开关筛选区改为整行展开（`span-full`）
  - 复选网格列宽提升到 `minmax(220px, 1fr)`，并增大可视高度
  - 勾选项文本支持换行，移动端自动切换单列
- 结果：
  - 解决“分栏缩在一起”的视觉拥挤问题。

## 结构同步（2026-02-28 查询页紧凑化与指标分组修正）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 布局从“过度展开”回调为“紧凑有序”：
    - 关键筛选区改为 `span-2`
    - 复选网格列宽由 220 调整为 170
    - 减小分段间距与网格间距
  - 指标分组调整为两段：
    - 当前指标（尾部含常量指标）
    - 计算指标（19项固定展示）
  - 常量指标不再单独成栏，改为附着在当前指标末尾

## 结构同步（2026-02-28 查询页选择区滚动条修复）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 口径复选区 `check-list` 增加纵向滚动（`overflow-y: auto`）与高度约束
  - 指标分段区 `check-list.sections` 增加纵向滚动
  - 各分段内部 `section-items` 增加独立纵向滚动
- 结果：
  - 选项超出可视范围时可滚动查看，不再出现“显示不全且无滚动条”。

## 结构同步（2026-02-28 查询页按月筛选与布局适中化）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 时间筛选输入改为 `type=\"month\"`，并按顺序调整为：
    - 业务月份起/止
    - 来源月份起/止
  - 查询参数转换：
    - 月份起 -> 月初日期
    - 月份止 -> 月末日期
  - 布局密度优化：
    - 复选网格列宽 170 -> 190
    - 分段/列表高度与间距适度上调
- 结果：
  - 页面不再“过紧”，同时满足“先业务后来源”的按月筛选习惯。

## 结构同步（2026-02-28 查询页期间/类型勾选化与层次顺序勾选）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - “期间”“类型”由多选下拉改为复选列表（含全选/全不选）
  - 期间/类型选项支持顺序数字标注（1,2,3...）
  - 新增“数据层次顺序（有序勾选）”：
    - 口径、指标、期间、类型
    - 支持勾选顺序数字与“重置默认”
- API：`frontend/src/projects/daily_report_25_26/services/api.js`
  - 查询请求新增透传 `order_fields`

## 结构同步（2026-02-28 查询页排版密度二次优化）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 主内容区宽度与卡片内边距统一上调
  - 筛选网格列宽、列表高度、段落间距统一标尺
  - 指标分段取消段内二级滚动，改为外层统一滚动
  - 汇总卡、按钮、标题间距统一微调
- 结果：
  - 页面密度更均衡，避免“有的太空、有的太挤”。

## 结构同步（2026-02-28 查询页口径/指标整行占满）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - “口径（可多选）”区域改为 `span-full`，整行占满
  - “指标（可多选）”两栏分段区域改为 `span-full`，整行占满
  - 增加 `span-full` 样式与移动端适配规则

## 结构同步（2026-02-28 口径选择区内部紧凑化）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 口径列表增加 `company-list` 独立样式
  - 列宽、间距、内边距、条目行高下调，提升口径区信息密度
  - 指标区样式保持不变

## 结构同步（2026-02-28 指标两栏显示不全修复）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 指标分段容器高度上调（`check-list.sections.compact`）
  - 分段块增加 `flex: 0 0 auto`，避免被压缩
  - 分段内容区 `section-items` 增加独立纵向滚动
- 结果：
  - 两栏指标都可完整查看，不再截断。

## 结构同步（2026-02-28 四筛选模块同一行布局）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - “期间”“类型”“数据层次顺序”“是否聚合口径”重排为同一行四列（`inline-four`）
  - 每列采用统一小卡片样式
  - 响应式下自动切换两列/一列
- 结果：
  - 四个模块同域展示，交互链路更连贯。

## 结构同步（2026-02-28 期间/类型默认值与空选规则）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 期间默认值：`month`
  - 类型默认值：`real`
  - 重置筛选时同样回到 `month/real`
  - 当期间或类型为空时：
    - 查询按钮禁用
    - 展示“为空不提取”提示
    - 前端本地返回空结果

## 结构同步（2026-02-28 查询页取消默认自动查询）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 初始化仅加载筛选项，不自动执行查询
  - 新增 `hasSearched` 控制首屏文案：
    - 未查询前提示“请先设置筛选条件并点击查询”
    - 查询后再展示结果/空结果状态
  - 重置筛选改为清空结果，不自动触发查询

## 结构同步（2026-02-28 聚合开关栏新增“期间月份聚合”）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 在“聚合开关”栏新增 `aggregateMonths` 开关
  - 开启后表示区间聚合月份；关闭则逐月展示
  - 重置时恢复默认不聚合
- API：`frontend/src/projects/daily_report_25_26/services/api.js`
  - 查询请求新增透传 `aggregate_months`

## 结构同步（2026-02-28 聚合口径关闭态文案调整）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 聚合口径开关关闭态文案调整为：
    - `不聚合口径（逐口径列出）`

## 结构同步（2026-02-28 查询按钮四项必选约束）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 查询按钮禁用条件扩展为：
    - 口径/指标/期间/类型任一为空即禁用
  - 提示文案同步为“四项至少各选一项”

## 结构同步（2026-02-28 汇总信息移除数值合计）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 删除“数值合计”汇总卡片
  - 汇总区保留：总记录数、数值非空、数值空值

## 结构同步（2026-02-28 类型筛选顺序 real 优先）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 新增 `orderedTypes` 计算顺序
  - “类型”选项列表与全选逻辑改为 `real` 置顶

## 结构同步（2026-02-28 指标区更名与“平均气温”追加）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 指标分段标题由“当前指标（尾部含常量指标）”调整为“基本指标”
  - 新增 `AVERAGE_TEMPERATURE_ITEM = '平均气温'`
  - “基本指标”分段中：
    - 常规指标在前
    - 常量指标随后
    - “平均气温”固定在尾部
  - `loadOptions()` 增加兜底：若接口未返回“平均气温”，前端自动补入选项

## 结构同步（2026-02-28 查询结果隐藏 operation_time）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 查询结果表格移除 `operation_time` 列（表头与行数据同步删除）
  - 保留字段：`company/item/unit/value/date/period/type/report_month`

## 结构同步（2026-02-28 查询结果同比/环比分析 + XLSX 导出）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 查询结果头部新增 `导出 XLSX` 按钮
  - 新增“同比与环比（基于最新月份）”对比表
  - 新增“专业分析要点”列表（同比分布、波动最大项、温度相关性、空值提示）
  - 新增本地导出逻辑（`xlsx`）：
    - Sheet1 `查询结果`
    - Sheet2 `同比环比对比`
    - Sheet3 `专业分析`
  - 新增样式：
    - 分析模块卡片样式
    - 同比/环比涨跌颜色（绿/红）
    - 结果头部动作区布局

## 结构同步（2026-02-28 同比/环比改为后端实时补查）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 查询时并行调用主查询与对比查询接口
  - 对比表数据来源改为后端 `query-comparison` 返回
  - 同比/环比窗口标签由后端返回并展示
  - XLSX 导出中的“同比环比对比”sheet 同步采用后端实时数据
- API：`frontend/src/projects/daily_report_25_26/services/api.js`
  - 新增 `queryMonthlyDataShowComparison(projectKey, payload)` 封装

## 结构同步（2026-02-28 同比/环比可视化总览）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 新增可视化控制：
    - 视角切换：同比 / 环比
    - TopN 指标数量：10/15/20/30
  - 新增图形区：
    - 热力图（指标 × 口径）：按涨跌幅着色
    - 波动 TopN 条形图：按绝对涨跌幅排序
  - 保留并强化对比表与专业分析要点，数据统一来源于后端实时对比接口

## 结构同步（2026-02-28 同比/环比配色语义调整）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 同比/环比配色统一为：正值红色、负值绿色
  - 影响范围：
    - 对比表百分比列（`delta-up/delta-down`）
    - 热力图色阶
    - TopN 条形图填充色

## 结构同步（2026-02-28 热力图标题换行修正）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 热力图标题改为：`热力图（纵轴=指标，横轴=口径）`
  - 新增 `viz-title-nowrap`，防止标题换行导致轴向语义误读

## 结构同步（2026-02-28 热力图网格错位修复）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 热力图网格改为“固定列数=口径数量”（由 `heatmapGridStyle` 动态注入）
  - 移除 `auto-fill` 列策略，避免指标标签行错位
  - 小屏下改为最小宽度 + 横向滚动，保持矩阵结构稳定

## 结构同步（2026-03-01 monthly_data_show 排查会话）

- 本轮前端代码无改动。
- 排查范围：
  - `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - `frontend/src/router/index.js`
  - `frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue`
- 排查结论：
  - 路由与 API 调用链已打通；
  - 待用户提供具体 BUG 复现步骤后执行定向修复与功能完善。

## 结构同步（2026-03-01 monthly_data_show 计算指标公式弹窗）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 在“计算指标（19项）”标题右侧新增 `查看公式` 按钮
  - 新增 `calculatedFormulaRows`，维护 19 项计算指标的公式与单位
  - 新增公式弹窗（遮罩层 + 表格）：点击按钮展示，支持关闭
  - 新增样式：
    - `section-title-row`（标题行与按钮布局）
    - `formula-dialog-*`（弹窗布局与滚动）
    - `formula-table`（公式列可换行）
- 联动说明：
  - 计算指标数据由后端实时计算；前端弹窗用于展示计算口径与公式说明。

## 结构同步（2026-03-01 查询连通性排查）

- 本轮前端代码无新增改动。
- 排查结论：
  - 前端 API 地址配置为 `http://127.0.0.1:8001`，与容器映射一致；
  - 页面报错 `ERR_CONNECTION_REFUSED` 属于后端不可达，需先恢复后端服务。

## 结构同步（2026-03-01 查询页数值展示规则统一）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 新增 `formatValue(value, unit)`：
    - 当 `unit === '%'` 时按百分比展示（`value * 100` 后拼接 `%`）。
  - 调整 `formatNumber`：
    - 整数显示为整数；
    - 非整数统一保留 2 位小数。
  - 应用范围：
    - 主查询结果表 `value` 列；
    - 同比/环比对比表中的 `当前值/同比值/环比值`。
- 效果：
  - 百分比指标显示从比例值改为业务可读百分数（例如 `0.65 -> 65%`）；
  - 全表数值小数位规则统一。

## 结构同步（2026-03-01 北海水耗率问题联动）

- 本轮前端代码无改动。
- 联动说明：
  - 北海 `发电水耗率/供热水耗率` 偏差修复发生在后端计算依赖取值层（指标别名兜底），前端展示逻辑保持不变。

## 结构同步（2026-03-01 水耗率公式文案同步）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 公式弹窗中以下两项更新为最新口径：
    - `发电水耗率 = (耗水量-供汽量-热网耗水量) * (1-热分摊比) / 发电量`
    - `供热水耗率 = ((耗水量-供汽量-热网耗水量) * 热分摊比 + 供汽量 + 热网耗水量) / 供热量`
- 联动说明：
  - 页面公式说明已与后端实时计算逻辑保持一致。

## 结构同步（2026-03-01 查询结果隐藏 report_month）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 查询结果表格移除 `report_month` 列（表头与行数据同步删除）。
- 联动说明：
  - 后端仍保留该字段用于内部排序/计算，不再在查询结果表中展示。

## 结构同步（2026-03-01 XLSX 导出字段与命名简化）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 导出 sheet“查询结果”移除 `report_month` 列，保持与页面一致。
  - 导出文件名改为：`月报查询分析_YYYY-MM.xlsx`（优先从当前筛选月份推断）。
- 效果：
  - 页面展示与导出列完全一致；
  - 文件名更短，更便于归档与检索。

## 结构同步（2026-03-01 查询页新增计划比）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 对比口径下拉新增 `计划比` 选项。
  - 对比表新增列：
    - `计划值`
    - `计划比`
  - 窗口提示新增 `计划窗口` 标签。
  - 热力图与 TopN 复用逻辑扩展支持计划比视图。
  - 专业分析要点加入计划比统计与偏差最大项。
  - XLSX 导出的“同比环比对比”sheet 增加 `plan_value`、`plan_rate` 列。
- 效果：
  - 查询页形成同比/环比/计划比三口径统一查看与导出能力。

## 结构同步（2026-03-01 热力图与TopN统一口径切换开关）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 可视化工具栏新增统一切换按钮组：`同比 / 环比 / 计划比`。
  - 新增 `comparisonModeLabel` 计算属性，统一驱动热力图与 TopN 标题文案。
  - 热力图标题改为：`{{ comparisonModeLabel }}热力图（纵轴=指标，横轴=口径）`。
  - TopN 标题改为：`{{ comparisonModeLabel }}波动 TopN（绝对值）`。
  - 新增按钮组样式：`mode-switch-group`、`mode-switch-btn`、`active`。
- 效果：
  - 热力图与 TopN 切换口径统一，用户一次切换可同步观察两类图表。

## 结构同步（2026-03-01 对比结果排序与筛选顺序一致性修复）

- 本轮前端代码无新增改动。
- 联动说明：
  - 下方“同比/环比/计划比（实时窗口）”的排序一致性由后端 `query-comparison` 排序规则修复；
  - 前端继续按返回顺序渲染对比表、热力图与 TopN 列表。

## 结构同步（2026-03-01 专业分析增强与平均气温折叠区）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - “专业分析要点”增强：
    - 按“数据层次顺序（orderFields）”进行分组；
    - 输出分组级同比/环比/计划比差值与差异率；
    - 补充当前口径 Top 波动、异常阈值计数与空值风险提示。
  - 新增“平均气温区间分析（默认折叠）”模块（仅在勾选“平均气温”时展示）：
    - 本期与同期平均气温卡片（含同比差值、同比差异率）；
    - 本期/同期每日气温对照表；
    - 本期与同期曲线图（SVG 折线）。
  - XLSX 导出扩展为多子工作表：
    - `汇总信息`
    - `查询结果`
    - `对比明细`
    - `${当前口径}热力图`
    - `${当前口径}TopN`
    - `专业分析`
    - `气温日序同比`（有气温数据时）
    - `气温汇总`（有气温数据时）
- 效果：
  - 页面展示与导出均形成“查询结果 + 对比可视化 + 文字解读 + 气温专题”的一体化分析结构。

## 结构同步（2026-03-01 XLSX导出样式优化与子表收敛）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 导出新增 `finalizeSheet(...)`：
    - 统一设置列宽；
    - 统一设置表头自动筛选。
  - 导出表头改为中文业务列名，提升阅读体验。
  - 导出值统一按页面格式输出（百分比、差值符号、两位小数规则）。
  - 移除导出子表：
    - `${当前口径}热力图`
    - `${当前口径}TopN`
  - 保留并优化子表：
    - `汇总信息`
    - `查询结果`
    - `对比明细`
    - `专业分析`
    - `气温日序同比`（有气温数据时）
    - `气温汇总`（有气温数据时）
- 效果：
  - 导出内容更聚焦，表格版式更清晰，便于业务直接阅读和汇报使用。

## 结构同步（2026-03-01 平均气温口径改为common并前置显示）

- 本轮前端代码无新增改动。
- 联动说明：
  - “平均气温”口径归属与排序优先级由后端接口统一控制；
  - 前端查询结果/对比结果继续按接口返回顺序渲染，因此会直接显示为 `company=common` 且排在前部。

## 结构同步（2026-03-01 差异率分母绝对值规则确认）

- 本轮前端代码无新增改动。
- 规则确认：
  - 前端分组分析差异率使用 `calcRate(current, base)`；
  - 计算式为 `(current - base) / Math.abs(base)`，与后端口径一致。

## 结构同步（2026-03-01 筛选项简化与简要分析报告化）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 筛选区第一行移除：
    - `来源月份起`
    - `来源月份止`
  - 请求构造调整：
    - `report_month_from/report_month_to` 固定传 `null`。
  - 分析区改版：
    - 标题从“专业分析要点”调整为“简要分析”；
    - 分析内容改为报告体顺序行文（“一、二、三...”），不再输出“分组1（口径=...）”样式。
- 效果：
  - 筛选操作更聚焦；
  - 分析阅读更贴近正式报告表达。

## 结构同步（2026-03-01 简要分析层次化逐项叙述）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - `analysisInsights` 改为按 `orderFields` 动态分层输出（如口径 > 指标 > 期间 > 类型）。
  - 每个末级条目输出完整叙述：
    - 本期值；
    - 同期值、同比增加/减少、差值、差异率；
    - 上期值、环比增加/减少、差值、差异率；
    - 计划值、较计划增加/减少、差值、差异率。
  - 保留“风险提示”“数据完整性”作为报告结尾段。
- 效果：
  - 分析文本从“技术分组摘要”升级为“分层逐项报告体”。

## 结构同步（2026-03-01 隐藏期间/类型筛选并固定月度实绩）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 隐藏筛选项：
    - `期间（可多选）`
    - `类型（可多选）`
  - 查询校验调整为仅检查：
    - `口径` 至少选择 1 项
    - `指标` 至少选择 1 项
  - 查询参数固定：
    - `periods = ['month']`
    - `types = ['real']`
  - 初始化与重置时同步固定：
    - `filters.periods = ['month']`
    - `filters.types = ['real']`
- 效果：
  - 筛选区更简洁，查询口径固定为“month + real”。

## 结构同步（2026-03-01 层次顺序与聚合开关布局优化）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 布局容器由 `inline-four` 调整为 `inline-layout`（双栏）。
  - 左栏：`order-col`（数据层次顺序）；右栏：`aggregate-col`（聚合开关）。
  - 聚合开关卡片增加 `aggregate-switch`，统一行高与间距。
  - 响应式策略：
    - `<=900px`：双栏并排；
    - `<=640px`：单栏堆叠。
- 效果：
  - 该区域结构更紧凑，信息分区更明确。

## 结构同步（2026-03-01 层次顺序仅保留口径/指标并同排展示）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - `数据层次顺序` 仅保留：
    - `口径`
    - `指标`
  - 默认与重置值统一：
    - `filters.orderFields = ['company', 'item']`
  - 查询提交时 `order_fields` 仅提交 `company/item`。
  - 布局改造：
    - 层次顺序项使用 `order-inline` 同排显示；
    - 聚合开关项使用 `aggregate-inline` 同排显示两项。
- 效果：
  - 层次顺序选择更聚焦，聚合区表达更紧凑，整体阅读路径更清晰。

## 结构同步（2026-03-01 层次顺序与聚合开关视觉对齐）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 双栏容器 `inline-layout` 增加等高拉伸。
  - 两栏卡片统一最小高度与头部高度。
  - 内容容器：
    - `order-inline`
    - `aggregate-inline`
    统一最小高度、垂直居中与可拉伸特性。
  - 行内项统一行高，文字基线更一致。
- 效果：
  - “数据层次顺序”与“聚合开关”在视觉上更对齐，整体更美观。

## 结构同步（2026-03-01 业务月份筛选器体验优化）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - “业务月份起/止”输入区样式升级：
    - 卡片化背景
    - 聚焦态高亮
    - 控件尺寸统一
  - 快捷按钮：
    - 起月：`本月`、`上月`
    - 止月：`本月`、`同起月`
  - 快捷区间：
    - `近3个月`、`近6个月`、`近12个月`、`本年`
  - 新增月份范围顺序校正逻辑，避免起止颠倒。
- 效果：
  - 月份筛选更直观，常见区间设置更高效。

## 结构同步（2026-03-01 简要分析分层文本排版）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 分析渲染结构由 `ul/li` 改为段落流。
  - 新增 `analysisLineClass(...)` 按行文前缀识别层级并附加样式类。
  - 样式升级：
    - 移除圆点；
    - 一级标题加粗；
    - 二级/三级内容按层级缩进。
- 效果：
  - “简要分析”层次更清晰，阅读更接近报告正文。

## 结构同步（2026-03-01 简要分析指标层文案精简）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 分层分析输出中，`item` 层级不再显示“指标：”前缀。
  - 示例：
    - 由 `指标：耗标煤总量` 调整为 `耗标煤总量`。
- 效果：
  - 文案更简洁，减少重复标签干扰。

## 结构同步（2026-03-01 简要分析指标圆点与描述缩进）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 指标层标题从纯文本改为带圆点：`•指标名`。
  - 指标下比较描述行前增加两个空格缩进。
  - 样式支持：
    - `insight-line` 使用 `white-space: pre-wrap` 保留前导空格；
    - `item-title` 指标行加粗以增强层次。
- 效果：
  - 指标标题与描述层级更清晰，阅读分段更自然。

## 结构同步（2026-03-01 简要分析数值附加计量单位）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 新增 `formatValueWithUnit(value, unit)`。
  - 简要分析中本期/同期/上期/计划值统一使用“值+单位”表达。
  - `%` 指标保持百分比样式，不重复拼接单位。
- 效果：
  - 报告正文中的数值语义更完整，避免单位歧义。

## 结构同步（2026-03-01 缺失上期值时省略环比段）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 简要分析末级描述由固定模板改为“分段动态拼接”。
  - 当 `momValue` 缺失时，不输出“上期...环比...”段落。
  - 仍保留本期、同比、计划比段落。
- 效果：
  - 避免无效环比文案，分析内容更符合实际数据可比性。

## 结构同步（2026-03-01 对比列表隐藏期间/类型）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - “同比/环比/计划比（实时窗口）”对比表移除列：
    - `期间`
    - `类型`
  - 同步移除行渲染中的对应字段。
  - 表格最小宽度从 `1080px` 调整为 `860px`。
- 效果：
  - 对比表更紧凑，信息焦点集中在口径、指标与对比值。

## 结构同步（2026-03-01 对比字段命名调整）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 对比表字段重命名：
    - `当前值` → `本期值`
    - `同比值` → `同期值`
    - `环比值` → `上期值`
  - 导出“对比明细”工作表表头同步调整。
- 效果：
  - 页面与导出字段命名一致，表达更贴近业务语义。

## 结构同步（2026-03-01 简要分析全零指标过滤）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 简要分析新增全零过滤规则：
    - 当 `本期/同期/上期/计划值` 均为 `0` 时，跳过该指标分析行。
  - 分层输出同步过滤空分组，避免出现无正文的指标标题。
- 效果：
  - 分析文本更聚焦，减少无效冗余信息。

## 结构同步（2026-03-01 简要分析口径标题高亮）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 分析分层识别新增口径专属类：`company-title`。
  - 口径行样式强化：
    - 字号更大
    - 字重加粗
    - 左侧色条
    - 浅色背景高亮
    - 主色文字
- 效果：
  - 各口径在简要分析中更显眼，阅读层级更清晰。

## 结构同步（2026-03-01 查询结果字段与月份控件优化）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 查询结果表移除字段：
    - `period`
    - `type`
  - 导出“查询结果”工作表同步移除“期间/类型”列。
  - 月份控件交互：
    - 按钮区域保持左右排列（含窄屏）；
    - 起始月份默认设为上个月。
- 效果：
  - 查询表更简洁；月份筛选操作更顺手，默认值更符合业务习惯。

## 结构同步（2026-03-01 日期快捷按钮右侧固定）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - `month-input-wrap` 改为单行不换行。
  - `month-quick-actions` 改为单行不换行，并通过 `margin-left: auto` 固定到输入框右侧。
- 效果：
  - 日期输入框与快捷按钮左右对齐，不再上下错位。

## 结构同步（2026-03-01 按钮横排与标题视觉强化）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 日期快捷按钮文本强制横排：
    - `writing-mode: horizontal-tb`
    - `white-space: nowrap`
  - 按钮文案：
    - `同起月` → `同起始月`
  - 筛选标题增强（新增 `panel-title`）：
    - `口径（可多选）`
    - `指标（可多选）`
    - `数据层次顺序`
    - `聚合开关`
  - 移除“重置默认”按钮。
- 效果：
  - 日期按钮可读性恢复正常；筛选区标题更醒目且布局更简洁。

## 结构同步（2026-03-01 按钮横排样式加固）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 日期快捷按钮增加“强制横排”样式：
    - `writing-mode: horizontal-tb !important`
    - `white-space: nowrap !important`
    - `text-orientation: mixed`
    - `inline-flex` 居中对齐
  - 筛选标题 `panel-title` 字号提升至 `14px`，在原有加粗与高对比色基础上进一步增强可见性。
- 效果：
  - 按钮文本在全局样式影响下仍稳定横排；
  - 标题层级辨识度进一步提升。

## 结构同步（2026-03-01 月份行防重叠布局修复）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 月份输入区布局改为两列网格：
    - 左侧：月份输入框（自适应宽度）
    - 右侧：快捷按钮区（横排、右对齐）
  - 关键样式调整：
    - `month-input-wrap`：`grid-template-columns: minmax(0, 1fr) auto`
    - `month-input`：`width: 100%` + `min-width: 0`
    - `month-quick-actions`：`min-width: max-content` + `justify-content: flex-end`
    - 快捷按钮 `min-width` 下调到 `56px`
- 效果：
  - 月份行不再出现输入框与按钮叠压；
  - 按钮仍保持横排并固定在输入框右侧。

## 结构同步（2026-03-01 移除月份行小按钮）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 移除“业务月份起/业务月份止”中的快捷按钮：
    - `本月`
    - `上月`
    - `同起始月`
  - 删除对应方法与样式（`month-quick-actions`）。
  - 月份输入区域回归纯输入框布局，避免额外控件挤占空间。
- 效果：
  - 月份行更宽敞；
  - 不再出现按钮压住日期选框的问题。

## 结构同步（2026-03-01 移除快捷区间）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 删除月份区域“快捷区间”及其按钮：
    - `近3个月`
    - `近6个月`
    - `近12个月`
    - `本年`
  - 删除对应方法：
    - `setBusinessMonthRangeRecent`
    - `setBusinessMonthRangeCurrentYear`
  - 清理对应样式与响应式样式。
- 效果：
  - 月份筛选区域只保留起止月份输入框，空间更充足、交互更直接。

## 结构同步（2026-03-01 业务月份止默认上个月）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 默认月份策略更新：
    - `loadOptions()`：`dateMonthFrom/dateMonthTo` 均默认为上个月
    - `resetFilters()`：起止月份都重置为上个月
- 效果：
  - 页面初始化与重置后，月份起止默认一致，均为上个月。

## 结构同步（2026-03-01 业务月份止改为非必选）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 月份标题文案更新：
    - `业务月份止` → `业务月份止（非必选）`
  - 默认值策略调整：
    - `loadOptions()`：`dateMonthFrom` 默认为上个月，`dateMonthTo` 默认空
    - `resetFilters()`：同样仅重置 `dateMonthFrom` 为上个月，`dateMonthTo` 为空
- 效果：
  - 月份止字段语义更明确，且保持可选不填。

## 结构同步（2026-03-01 指标配置驱动化）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 指标两块区域改为读取后端 `query-options` 返回的 `indicator_config`：
    - `basic_section_title/basic_items`
    - `calculated_section_title/calculated_items`
  - 公式弹窗数据源改为配置下发（不再前端硬编码公式数组）。
  - 指标排序改为“配置顺序优先，未配置项后置”。
  - 基本指标区新增分类标签展示（来自 `basic_items[].category`，当前为占位值）。
- 效果：
  - 前端不再硬编码计算指标集合与公式；
  - 调整指标顺序与公式时，只需改后端配置文件即可生效。

## 结构同步（2026-03-01 计算指标标题默认态兜底）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 默认标题由 `计算指标（0项）` 调整为 `计算指标`。
  - 标题渲染增加兜底逻辑：若配置标题为空或为 `0项`，按当前列表动态生成为 `计算指标（N项）`。
- 效果：
  - 在配置未返回或旧接口场景下，不再出现误导性的“0项”显示。

## 结构同步（2026-03-01 基本指标分组展示）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 基本指标区域改为分组结构渲染：
    - 分组标题（如“主要指标”“消耗指标”）
    - 分组内指标复选项
  - 取消“每个指标后方分类标签”展示方式。
  - 支持后端下发 `indicator_config.basic_groups`，并在未分组项存在时自动归入“未分组”。
- 效果：
  - 基本指标结构更清晰，后续可通过配置直接调整分组与顺序。

## 结构同步（2026-03-01 itemSections 变量重名编译修复）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 修复 `itemSections` 计算属性中的重复变量声明：
    - 删除重复的 `const current = []`。
- 效果：
  - 消除 `Identifier 'current' has already been declared` 编译错误。

## 结构同步（2026-03-01 其它指标配置补全联动）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 无新增代码变更（继续按 `basic_groups` 渲染）。
- 联动说明：
  - 已在配置文件 `indicator_config.json` 的 `【其他指标】` 分组补入更多指标；
  - 前端读取同一配置后，未分组项会进一步减少。

## 结构同步（2026-03-01 指标配置路径修复联动）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 本轮前端代码无改动。
- 联动说明：
  - 后端改为优先读取容器挂载路径 `/app/data/...` 的配置文件；
  - 前端继续通过 `query-options.indicator_config` 渲染，分组名称与顺序将与最新配置一致。

## 结构同步（2026-03-01 指标选区隐藏计量单位）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 移除指标选择区域（基本指标分组/计算指标分组）中每项后的单位标签展示；
  - 清理选区专用单位映射计算与样式定义。
- 效果：
  - 选区更简洁，仅显示指标名称与选择顺序；
  - 计量单位继续用于查询结果表格与简要分析内容，不影响结果口径。

## 结构同步（2026-03-01 导入映射新增联动）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowImportWorkspace.vue`
  - 本轮前端代码无改动。
- 联动说明：
  - 后端导入规则新增 `锅炉耗柴油量 -> 耗油量` 后，前端上传同名指标时将自动按新规则归并处理。

## 结构同步（2026-03-01 金普面积扣减规则联动）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowImportWorkspace.vue`
  - 本轮前端代码无改动。
- 联动说明：
  - 后端导入提取新增金普口径面积扣减规则后，前端工作台预览/导入同一文件时将得到扣减后的“期末供暖收费面积”结果。

## 结构同步（2026-03-01 金普面积扣减规则命中增强联动）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowImportWorkspace.vue`
  - 本轮前端代码无改动。
- 联动说明：
  - 后端已增强金普口径与指标同义词匹配，前端导入工作台在提取/导出 CSV 时会直接体现增强后的扣减结果。

## 结构同步（2026-03-01 查询页三项指标4位小数）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 新增按指标定制小数位规则：
    - `供暖热耗率/供暖水耗率/供暖电耗率` 默认 4 位小数；
    - 其他指标保持 2 位小数。
  - `formatValue`、`formatValueWithUnit` 新增 `item` 参数；
  - 查询结果表、对比列表、简要分析与导出数据格式化调用统一传入 `item`。
- 效果：
  - 指定三项指标在查询页面显示更精细，且前后展示链路口径一致。

## 结构同步（2026-03-01 查询页三项指标差值4位小数）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - `formatSignedNumber` 增加按 `item` 控制小数位；
  - 简要分析与导出对比明细中的 `同比/环比/计划` 差值格式化统一传入指标名。
- 效果：
  - `供暖热耗率/供暖水耗率/供暖电耗率` 的三类差值也按 4 位小数展示。

## 结构同步（2026-03-01 半计算补齐规则联动）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 本轮前端代码无改动。
- 联动说明：
  - 后端 `extract-csv` 已补齐半计算指标规则，前端导入工作台在同样操作下会直接获取补齐后的 CSV 数据。

## 结构同步（2026-03-01 导入页显示提取命中统计）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 提取完成提示新增统计信息：
    - 半计算补齐命中条数
    - 金普面积扣减命中条数
    - 提取总行数
- API 封装：`frontend/src/projects/daily_report_25_26/services/api.js`
  - 从 `extract-csv` 响应头读取统计并返回 `stats`。
- 效果：
  - 导入页可直观看到规则是否实际生效与命中规模。

## 结构同步（2026-03-01 规则命中详情弹窗）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 新增“查看规则命中详情”按钮（提取成功后显示）；
  - 新增弹窗展示逐项统计明细（半计算子规则、金普面积扣减、常量注入、总行数）。
- API：`frontend/src/projects/daily_report_25_26/services/api.js`
  - 读取 `X-Monthly-Rule-Details` 并解析为 `stats.ruleDetails`。
- 效果：
  - 可直接核对“每一项处理”的命中情况细节，无需手工排查。

## 结构同步（2026-03-01 入库成功提示显示新增/更新）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 入库成功提示新增显示：总处理条数、新增条数、更新条数、空值入库条数。
- 联动说明：
  - 后端 `import-csv` 已返回 `inserted_rows/updated_rows`，用于判断本次是新增还是覆盖更新。

## 结构同步（2026-03-01 import-csv 结果集异常修复联动）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 本轮前端代码无改动。
- 联动说明：
  - 后端已修复批量 RETURNING 兼容问题，第四步入库报错已消除，前端可继续展示新增/更新统计。

## 结构同步（2026-03-01 金普面积扣减规则临时关闭联动）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 本轮前端代码无改动。
- 联动说明：
  - 后端已临时关闭“金普期末供暖收费面积扣减”规则，导入页规则统计中的该项将不再增长。

## 结构同步（2026-03-01 供暖耗热量规则调整联动）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 本轮前端代码无改动。
- 联动说明：
  - 后端已将金普口径“供暖耗热量”改为直接取“供热量”；导入工作台提取结果会直接体现该规则。

## 结构同步（2026-03-01 提取规则配置化联动）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 本轮前端代码无改动。
- 联动说明：
  - 后端提取规则已改为读取 `backend_data/projects/monthly_data_show/monthly_data_show_extraction_rules.json`；
  - 导入工作台提取/入库行为将随该配置文件调整而变化。

## 结构同步（2026-03-01 导入页规则勾选执行）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 新增“规则执行选择”面板，支持全选/全不选；
  - 默认勾选全部规则；
  - 提取时将勾选规则 ID 传给后端；
  - 详情弹窗新增“本次选中规则”及命中明细展示。
- API：`frontend/src/projects/daily_report_25_26/services/api.js`
  - `extractMonthlyDataShowCsv` 新增参数 `extractionRuleIds` 并上传 `extraction_rule_ids`。
- 效果：
  - 用户可手动控制本次提取执行哪些规则，并在结果中看到实际命中反馈。

## 结构同步（2026-03-01 规则选择改为弹窗）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - “规则执行选择”改为弹窗交互：
    - 主面板仅显示已选数量与摘要；
    - 点击“打开规则列表”进入弹窗勾选；
    - 弹窗中逐条显示规则名称与详细说明，并支持全选/全不选。
- 效果：
  - 规则信息可读性提升，避免主页面拥挤且便于核对后再执行。

## 结构同步（2026-03-01 已取消规则不在弹窗展示）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 本轮前端代码无改动。
- 联动说明：
  - 后端已调整规则清单下发逻辑，已禁用的“金普面积扣减”规则不会在弹窗中出现。

## 结构同步（2026-03-01 CSV 空值 token 增加“-”联动）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 本轮前端代码无改动。
- 联动说明：
  - 后端导入解析已将 `-` 识别为空值，前端入库结果中的空值条数会相应反映该处理。

## 结构同步（2026-03-01 多月聚合状态值按最后一期联动）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 本轮前端代码无改动。
- 联动说明：
  - 后端已修正多月聚合口径：状态值指标按最后一期取值，前端查询结果会直接体现该修正。

## 结构同步（2026-03-02 查询结果列头中文化与动态列序）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 查询结果表头改为中文字段：`口径/指标名/时间/值/计量单位`；
  - `时间` 列由原始日期改为 `YYYY年M月` 展示；
  - 新增 `resultColumns` 动态列配置，按“数据层次顺序”排列 `时间/口径/指标名`，后置 `值/计量单位`；
  - 表格行渲染改为按动态列取值，避免固定列顺序。
- 导出联动：
  - `downloadXlsx` 的“查询结果”子表改为复用同一列定义，导出列头、列顺序、时间格式与页面一致。

## 结构同步（2026-03-02 气温日序同比导出改为纯数值列）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 导出 XLSX 子表“气温日序同比”中：
    - `本期气温/同期气温` 单元格由带 `℃` 文本改为纯数值；
    - 列标题改为 `本期气温(℃)`、`同期气温(℃)`。
- 效果：
  - 导出后可直接按数值进行筛选、排序和公式计算，且单位在表头保留清晰标识。

## 结构同步（2026-03-02 导出文件名按查询月份区间命名）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - `resolveExportMonthTag()` 支持区间命名：
    - 多月查询：`YYYY-MM_~_YYYY-MM`
    - 单月查询：`YYYY-MM`
  - 最终导出文件名：`月报查询分析_${monthTag}.xlsx`。
- 效果：
  - 文件名与查询月份区间一致，便于归档与检索。

## 结构同步（2026-03-02 管理后台新增独立“数据库表编辑”页）

- 页面：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
  - 顶部标签新增“数据库表编辑”（位于“后台文件编辑”之后）；
  - 原文件编辑页内的数据库编辑模块已迁移至该独立标签页；
  - 数据库查询新增交互：
    - 关键字检索（全字段文本匹配）
    - 字段筛选条件（AND，可增删）
    - 排序字段与排序方向
    - 分页参数（limit/offset）
  - 保存修改逻辑保持不变：按主键字段锁定行，非主键字段可编辑并批量保存。
- API 联动：`frontend/src/projects/daily_report_25_26/services/api.js`
  - `queryAdminDbTable` 增加入参透传：`search/filters/order_by/order_dir`。

## 结构同步（2026-03-02 月报查询单月默认范围修正）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - `buildPayload()` 调整日期组装规则：
    - 当仅填写“业务月份起”且“业务月份止”为空时，`date_to` 自动取“业务月份起”的月末；
    - 从而形成“当月起-当月止”的单月查询窗口。
- 效果：
  - 单月查询无需再填写“业务月份止”，避免误查跨月数据。

## 结构同步（2026-03-02 月份筛选框体包裹样式修正）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 月份筛选相关样式增加 `box-sizing: border-box`：
    - `.field input/.field select`
    - `.month-field`
    - `.month-input`
- 效果：
  - “业务月份起/止”外层框体与日期输入框宽度对齐，右侧不再出现未包裹完整的视觉缺口。

## 结构同步（2026-03-02 日报分析页 AI 附加提示词输入）

- 页面：`frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`
  - 在“智能报告生成（BETA）”开启且有权限时，新增“本次分析要求（可选）”输入框；
  - `runAnalysis` 请求体新增：
    - `ai_mode_id`（当前默认 `daily_analysis_v1`）
    - `ai_user_prompt`（用户附加提示词）
  - 样式补充：`form-actions` 允许换行，新增 `ai-user-prompt-field` 组件样式。
- 联动：
  - 后端 AI 报告引擎已支持模式化与用户附加提示词透传。

## 结构同步（2026-03-02 月报查询页接入 AI 智能报告）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 新增 AI 工具栏：智能报告开关、生成按钮、下载按钮；
  - 新增“本次分析要求（可选）”输入框（最多 2000 字）；
  - 新增任务状态轮询与提示文案；
  - 查询结果刷新/筛选重置时自动清理旧任务状态，避免串任务。
- API：`frontend/src/projects/daily_report_25_26/services/api.js`
  - 新增：
    - `startMonthlyDataShowAiReport(projectKey, payload)`
    - `getMonthlyDataShowAiReport(projectKey, jobId)`
- 默认模式：
  - 月报查询页固定透传 `ai_mode_id=monthly_analysis_v1`，并支持 `ai_user_prompt`。

## 结构同步（2026-03-02 AI 提示词拆分联动）

- 页面：`frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`、`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 本轮前端代码无新增改动。
- 联动说明：
  - 后端已将 `daily_analysis_v1` 与 `monthly_analysis_v1` 的预设提示词彻底分离；
  - 前端继续按既有方式透传 `ai_mode_id`，即可命中对应项目模式提示词。

## 结构同步（2026-03-02 AI 配置共享路径文案同步）

- 页面：`frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`
- 变更点：
  - AI 设置弹窗中的提示文案由 `backend_data/api_key.json` 更新为 `backend_data/shared/ai_settings.json`。
- 效果：
  - 前端页面提示与后端实际配置落盘路径一致，减少运维误操作。

## 结构同步（2026-03-02 月报默认提示词更新联动）

- 本轮前端代码无功能改动。
- 联动说明：
  - 月报默认提示词已在后端共享配置 `backend_data/shared/ai_settings.json` 的 `instruction_monthly` 更新；
  - 前端继续透传 `ai_mode_id=monthly_analysis_v1` 时将命中新模板。

## 结构同步（2026-03-02 AI 共享配置合并联动）

- 本轮前端代码无功能改动。
- 联动说明：
  - 后端 `backend_data/shared/ai_settings.json` 已合并日报与月报提示词及 AI 运行参数；
  - 前端既有 AI 设置与报告调用链无需改动，读取结果将统一来自 shared 主配置。

## 结构同步（2026-03-02 AI 设置弹窗双提示词折叠编辑）

- 页面：`frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`
- API：`frontend/src/projects/daily_report_25_26/services/api.js`
- 变更点：
  - AI 设置弹窗提示词区域改为两段折叠编辑（默认收起）：
    - `instruction_daily`（日报）
    - `instruction_monthly`（月报）
  - 保存请求字段由旧 `instruction` 切换为 `instruction_daily`，并新增 `instruction_monthly` 透传；
  - 样式新增折叠块视觉样式，保持弹窗布局稳定。
- 效果：
  - 提示词编辑更清晰，默认界面更简洁；
  - 与后端字段标准化保持一致。

## 结构同步（2026-03-02 AI 设置字段改名与防误覆盖）

- 页面：`frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`
- API：`frontend/src/projects/daily_report_25_26/services/api.js`
- 变更点：
  - 保存参数从 `instruction` 切换为 `instruction_daily`；
  - 透传 `instruction_monthly`；
  - 当调用方未提供某提示词字段时，API 层不主动写空，避免覆盖既有配置。
- 效果：
  - 配置编辑行为更安全，减少误清空提示词风险。

## 结构同步（2026-03-02 月报4段式报告后端联动）

- 本轮前端代码无改动。
- 联动说明：
  - 月报 AI 报告已在后端切换为独立4段式结构渲染；
  - 前端无需调整调用参数，继续透传 `ai_mode_id=monthly_analysis_v1` 即可命中新逻辑。

## 结构同步（2026-03-02 月报查询页 AI 设置弹窗与宽度修复）

- 页面：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
- 变更点：
  - 在月报查询页 AI 工具栏新增“智能体设定”入口，仅 `global_admin` 可见；
  - 新增 AI 设置弹窗，支持全局配置读写（日报+月报共用）：
    - `instruction_daily`
    - `instruction_monthly`
    - `report_mode`
    - `enable_validation`
  - 折叠提示词编辑块样式修复：展开后改为全宽显示，不再出现“内容区过窄”。
- 效果：
  - 月报页可直接维护全局 AI 参数；
  - 提示词折叠编辑体验与日报页一致且布局正常。

## 结构同步（2026-03-02 日报/月报 AI 设置弹窗组件通用化）

- 新增组件：`frontend/src/projects/daily_report_25_26/components/AiAgentSettingsDialog.vue`
  - 统一承载 AI 设置弹窗 UI 与交互：
    - API Keys 列表管理；
    - 模型输入；
    - `instruction_daily` / `instruction_monthly` 折叠编辑；
    - `report_mode` / `enable_validation` / `allow_non_admin_report`。
- 页面接入：
  - `frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`
  - `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
- 重构结果：
  - 两个页面移除各自内联弹窗模板、重复状态与样式，改为统一组件；
  - 日报继续通过 `getAiSettings/updateAiSettings(projectKey, payload)` 读写；
  - 月报继续通过 `getAdminAiSettings/updateAdminAiSettings(payload)` 读写；
  - 样式与交互一致，后续维护只需修改一处组件。

## 结构同步（2026-03-02 AI 设置 API 输入框宽度优化）

- 文件：`frontend/src/projects/daily_report_25_26/components/AiAgentSettingsDialog.vue`
- 变更点：
  - 为 API Key 输入框增加弹性布局：`.api-key-item input { flex: 1 1 auto; min-width: 0; }`；
  - 新增移动端适配：小屏下 API 行可换行，输入框宽度强制 `100%`。
- 效果：
  - 智能体设定中 API 输入框不再被压缩过窄；
  - 日报与月报页面（共享组件）同步生效。

## 结构同步（2026-03-02 AI 报告限流优化后端联动）

- 本轮前端代码无改动。
- 联动说明：
  - 后端 AI 报告链路新增 429 自动退避重试与提示数据瘦身；
  - 前端无需改参数，原有“生成智能报告”流程即可受益。  

## 结构同步（2026-03-02 月报报告样式独立后端联动）

- 本轮前端代码无改动。
- 联动说明：
  - 后端已将月报 AI 报告改为独立版式渲染；
  - 前端仍透传 `ai_mode_id=monthly_analysis_v1`，无需额外参数即可得到新月报样式。  

## 结构同步（2026-03-03 管理后台 AI 设置入口统一）

- 页面：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
- 变更点：
  - 移除管理后台旧版内嵌 AI 表单；
  - 接入共享组件 `AiAgentSettingsDialog`；
  - 管理后台与日报查询页、月报查询页统一使用同一套“智能体设定”样式与交互。
- 联动接口：
  - 通过 `getAdminAiSettings/updateAdminAiSettings` 读写全局配置；
  - 配置源保持 `backend_data/shared/ai_settings.json`。

## 结构同步（2026-03-03 月报双图能力后端联动）

- 本轮前端代码无改动。
- 联动说明：
  - 月报 AI 报告由后端新增两张 ECharts 图（同比差异率 Top10、本期值 Top10）；
  - 前端维持原有报告获取流程，无需新增参数。  

## 结构同步（2026-03-03 登录 404 修复后端联动）

- 本轮前端代码无改动。
- 联动说明：
  - 登录失败根因在后端 `/api/v1` 路由未挂载（导入异常）；
  - 后端修复后，前端继续使用原有登录接口 `POST /api/v1/auth/login` 即可恢复登录流程。  

## 结构同步（2026-03-03 智能体设定新增不保存退出）

- 文件：`frontend/src/projects/daily_report_25_26/components/AiAgentSettingsDialog.vue`
- 变更点：
  - 在弹窗底部动作区新增按钮“退出（不保存）”；
  - 点击后仅关闭弹窗，不调用保存接口；
  - 现有“保存并退出”与“测试连接”逻辑不变。
- 影响范围：
  - 日报查询页、月报查询页、管理后台（均复用该组件）同步生效。

## 结构同步（2026-03-03 AI 报告进度可视化）

- 文件：
  - `frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`
  - `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
- 变更点：
  - 在 AI 报告状态文本下新增可视化进度区：进度条、百分比、阶段节点；
  - 阶段统一为：`洞察分析 → 结构规划 → 内容撰写 → 检查核实`；
  - 月报页面补充 `stage` 跟踪与别名阶段（`revision_pending`、`revision_content`）映射，进度显示更准确。
- 结果：
  - 用户可直观看到报告生成进展，不再仅依赖“生成中/完成/失败”文案。

## 结构同步（2026-03-03 月报导出 XLSX 数值格式修复）

- 文件：`frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
- 变更点：
  - 调整 `downloadXlsx` 导出逻辑，将关键数值列写为 Excel 数值单元格（不再写入格式化文本）；
  - 新增数值格式辅助函数：`isPercentUnit`、`buildDecimalFormat`、`buildExcelValueFormat`、`setSheetNumericCell`；
  - “查询结果”“对比明细”“气温日序同比”“气温汇总”四个子表的数值列统一设置 `numFmt`；
  - 百分比指标使用 `%` 格式，普通指标使用数值格式；小数位与页面规则保持一致。
- 结果：
  - 导出 XLSX 的数值列可直接进行排序、筛选、函数计算和图表绘制。
## 结构同步（2026-03-04 模板设计器第一期收尾）

- 已确认并保持以下链路一致：
  - 页面路由：`/projects/:projectKey/pages/:pageKey/template-designer`
  - 页面文件：`src/projects/daily_report_25_26/pages/TemplateDesignerView.vue`
  - 页面入口跳转：`src/projects/daily_report_25_26/pages/PageSelectView.vue` 中 `template_designer` 分支
  - API 封装：`src/projects/daily_report_25_26/services/api.js` 中模板列表/详情/创建/更新/发布函数
## 结构同步（2026-03-04 模板设计器入口可见性联动）

- 本次未改前端路由与页面代码；
- 入口不可见问题由后端 `list_project_pages` 过滤策略修复，前端继续复用既有 `PageSelectView` 渲染逻辑；
- 用户刷新页面后，具备模块化管理能力的账号应可看到“模板设计器（新表）”入口。
## 结构同步（2026-03-04 模板设计器入口迁移）

- 入口位置调整：
  - 从页面选择页迁移到管理后台 `AdminConsoleView` 顶部按钮；
  - 按钮点击后进入 `/projects/daily_report_25_26/pages/template_designer/template-designer`。
- 页面选择行为调整：
  - `PageSelectView` 中隐藏 `template_designer` 页面卡片；
  - 移除该页面在 `openPage` 中的专门跳转逻辑，避免入口重复。
## 结构同步（2026-03-04 模板设计器拖拽版）

- 文件：`src/projects/daily_report_25_26/pages/TemplateDesignerView.vue`
- 升级内容：
  - 列定义支持拖拽排序；
  - 行定义支持拖拽排序；
  - 新增可视化行编辑与预览网格（单元格初始值编辑）；
  - 保留 JSON 兼容编辑并支持“应用 JSON 到可视编辑”。
- 保存与发布：
  - 继续调用 `services/api.js` 中模板设计器既有接口，保持后端协议不变。
## 结构同步（2026-03-04 模板设计器页面壳层统一）

- 文件：`src/projects/daily_report_25_26/pages/TemplateDesignerView.vue`
- 同步内容：
  - 新增顶部 `AppHeader`；
  - 新增 `Breadcrumbs` 导航；
  - 主体改为统一的 `card elevated` 容器样式，与现有页面风格对齐。
## 结构同步（2026-03-04 模板设计器标签闭合修复）

- 文件：`src/projects/daily_report_25_26/pages/TemplateDesignerView.vue`
- 修复：
  - 将 `template-editor-panel` 的错误闭合标签 `</section>` 更正为 `</div>`；
  - 解决 Vite 编译报错 `Element is missing end tag`。
## 结构同步（2026-03-04 模板设计器动态导入 500 修复）

- 文件：`src/projects/daily_report_25_26/pages/TemplateDesignerView.vue`
- 修复：
  - 补齐外层 `section.card` 的闭合标签，解决动态导入返回 500 的编译失败问题。
- 验证：
  - `npm run build` 已通过。
## 结构同步（2026-03-04 模板设计器固定字段可选）

- 文件：`src/projects/daily_report_25_26/pages/TemplateDesignerView.vue`
- 新增能力：
  - 固定字段（`row_label`、`unit`）启用开关；
  - 固定字段默认值配置；
  - 行编辑表与预览网格按固定字段配置动态渲染；
  - 保存时将配置写入模板 `meta.fixed_fields/default_values`。
## 结构同步（2026-03-04 模板设计器类 Excel 画布增强）

- 文件：`src/projects/daily_report_25_26/pages/TemplateDesignerView.vue`
- 关键增强：
  - 画布网格支持直接拖拽行列；
  - 画布列头支持就地删除，工具条支持新增行/新增列；
  - 列定义新增列宽字段并在画布渲染；
  - 新增连接配置区并写入 `meta.binding`；
  - 新增布局预留 `meta.layout.frozen_columns`。
- 兼容性：
  - 继续兼容既有模板保存/发布接口与 rows JSON 结构。
## 结构同步（2026-03-04 模板设计器拖拽手柄化修复）

- 文件：`src/projects/daily_report_25_26/pages/TemplateDesignerView.vue`
- 修复点：
  - 将拖拽从整行/整列表头切换为“手柄触发拖拽”；
  - 解决输入框难以聚焦、删除按钮点击被拖拽干扰的问题。
- 验证：
  - `npm run build` 通过。

## 结构同步（2026-03-05 模板设计器入口并列标签化）

- 页面：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
- 调整：
  - 将“模板设计器（新表）”入口从顶部右侧独立按钮迁移到 `tab-group`；
  - 入口展示形式改为与其他后台子页面并列的标签按钮；
  - 保留原 `openTemplateDesigner` 跳转行为，避免影响既有模板设计器路由与页面实现。
- 清理：
  - 移除无引用样式 `.top-actions`。

## 结构同步（2026-03-05 长表设计器方案评审）

- 本轮无前端代码改动，仅完成长表设计器成熟方案评审与落地路径定义。
- 评审方向：
  - 设计器从单页“列/行 JSON 编辑”升级为向导式流程：
    - 业务范围（单位/日期粒度/口径）
    - 字段模型（维度/指标/固定字段）
    - 计算与校验（依赖图）
    - 入库映射（长表）
    - 预览回归与发布
  - 保持“存储长表、展示透视”原则，避免交叉表直接绑定入库。

## 结构同步（2026-03-05 下线模板设计器页面）

- 删除页面：`src/projects/daily_report_25_26/pages/TemplateDesignerView.vue`
- 删除路由：`/projects/:projectKey/pages/:pageKey/template-designer`（`src/router/index.js`）
- 删除入口：
  - `AdminConsoleView.vue` 顶部“模板设计器（新表）”标签；
  - 对应跳转函数 `openTemplateDesigner`。
- 接口清理：
  - `src/projects/daily_report_25_26/services/api.js` 中模板设计器相关函数已删除（列表/详情/创建/更新/发布）。
- 现状：
  - 前端已不再提供模板设计器入口与访问路径。

## 结构同步（2026-03-05 管理后台“看板功能设置”升级）

- 页面：`src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
- 调整：
  - “看板缓存任务”更名为“看板功能设置”；
  - 新增业务日期自动读取能力：通过看板日期接口读取 `set_biz_date`，并同步到“刷新日期”；
  - 新增气温相关操作按钮：`导入气温（预览）`、`提交气温入库`；
  - 保留并整合缓存操作按钮：`发布缓存`、`刷新单日`、`停止任务`、`禁用缓存`。
- API 封装新增：
  - `getProjectDashboardBizDate`
  - `importProjectTemperatureData`
  - `commitProjectTemperatureData`
  - 文件：`src/projects/daily_report_25_26/services/api.js`

## 结构同步（2026-03-05 管理后台气温按钮反馈增强）

- 页面：`src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
- 优化：
  - “导入气温（预览）/提交气温入库”点击后立即显示进行中提示；
  - 结果提示改为基于后端真实字段：
    - 预览：`summary.total_hours`、`overlap`、`differences.length`、`dates`；
    - 入库：`write_result.inserted`、`write_result.replaced`；
  - 提示区域由普通 `subtext` 改为 `panel-state`，提升可见性。

## 结构同步（2026-03-05 管理后台气温导入弹框确认）

- 页面：`src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
- 交互调整：
  - 点击“导入气温（预览）”后，先弹出“气温导入确认”弹框；
  - 弹框展示预览摘要（获取时间、涉及日期、重合区间、差异小时）；
  - 用户在弹框中点击“确认入库”后才执行写库；
  - 取消外层“提交气温入库”按钮，统一为弹框内确认流程。

## 结构同步（2026-03-05 管理后台气温弹框逐小时一致性）

- 页面：`src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
- 增强：
  - 弹框新增逐小时一致性列表（时间、接口值、数据库值、一致/不一致）；
  - 差异项红色高亮；
  - 数据映射接入 `overlap_records`，重合小时数读取 `overlap.hours`。

## 结构同步（2026-03-05 项目后台页面移除日志统计区块）

- 页面：`src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
- 调整：
  - 在“项目后台设定”视图中移除“操作日志与分类统计”整块内容；
  - 不影响同页面其他设定功能。

## 结构同步（2026-03-05 月报查询页指标分组全选/取消）

- 页面：`src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
- 调整：
  - 在“指标（可多选）”的每个基础指标分组标题右侧新增“全选/取消”按钮；
  - 新增 `toggleGroupItems(groupItems, checked)`，仅对当前分组内指标生效；
  - 保留原全局“全选/全不选”能力不变。

## 结构同步（2026-03-05 月报查询页全选改单按钮切换）

- 页面：`src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
- 调整：
  - 口径与指标顶部的“全选/全不选”改为单按钮“全选/取消”切换；
  - 指标各大类标题（含“计算指标”）新增单按钮“全选/取消”切换；
  - 基础指标分组级按钮继续保留。

## 结构同步（2026-03-05 月报查询页子分类单按钮切换）

- 页面：`src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
- 调整：
  - 基础指标子分类（如主要产销指标、主要消耗指标）按钮改为单按钮“全选/取消”切换。

## 2026-03-06 本地开发环境排查补记
- 本次仅排查 VS Code 在打开 `.py` 文件后自动重启集成终端并激活虚拟环境的现象。
- 结论为当前仓库前端目录内未发现触发该行为的工作区级 VS Code 配置，属于编辑器/Python 扩展本地环境行为，不涉及前端模块代码变更。

## 2026-03-06 本地环境补记
- 进一步确认 `D:\编程项目\phoenix_project` 为仓库外独立目录，当前前端模块不依赖该目录内容。
- 若清理该目录，需先在 VS Code 切走误绑定的 Python 解释器，避免打开 `.py` 文件时继续引用已删除环境。

## 结构同步（2026-03-06 前端移动端表格与录入页优化第一轮）
- `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：
  - 为聊天预览表和查询结果表补充统一的 `table-wrap` 横向滑动容器；
  - 在 `<=900px` 和 `<=640px` 断点下压缩表格字号与间距；
  - 对对比表在手机宽度隐藏部分“原始对比值”列，只保留关键比率与当前值，提升可读性。
- `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`：
  - 为批量识别预览表与异常表引入横向滚动容器；
  - 为异常说明列补充自动换行和最小宽度控制，避免窄屏撑破布局。
- `frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue`：
  - 保留桌面端 RevoGrid 默认展示；
  - 手机端新增横向滑动提示，并为表格容器和网格本体设置最小宽度与滚动能力。
- 本轮策略：
  - 桌面端视觉基线不改；
  - 仅在窄屏断点触发表格压缩、横滑和局部列隐藏；
  - 复杂录入表不强行压成单列，优先保证“能看清、能滑动、知道如何操作”。

## 结构同步（2026-03-06 前端移动端表格与录入页优化第二轮）
- `frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`：
  - 为同比、环比、计划比较三张结果表增加 `result-table-wrapper` 横向滚动容器；
  - 为时间轴 `RevoGrid` 容器改为横向滚动，并补充移动端最小宽度；
  - 在 `<=900px / <=640px` 断点下继续压缩表格字号、间距与时间轴高度。
- `frontend/src/projects/daily_report_25_26/pages/DashBoard.vue`：
  - 为焦点指标折叠表补充触摸滚动优化；
  - 在平板和手机宽度下收紧列宽、字号与单元格 padding；
  - 将中部卡片控制按钮在手机宽度改为纵向堆叠，降低按钮拥挤。
- 浏览器实测补充：
  - `DataAnalysisView` 结果表在 390px 宽度下已出现横滑容器；
  - `DashBoard` 焦点指标折叠表在 390px 宽度下可横向滑动，不再强挤。

## 结构同步（2026-03-06 前端移动端优化第三轮：入口页与文案收敛）
- `frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue`：
  - 删除显式的手机横滑提示文案，仅保留布局层面的滚动与最小宽度保护。
- `frontend/src/pages/LoginView.vue`：
  - 在手机宽度下收紧视觉区高度、标题字号、表单圆角与控件高度，使登录页更适合竖屏触控。
- `frontend/src/pages/ProjectSelectView.vue`：
  - 项目卡片在手机宽度下改为单列，整体更紧凑，减少留白和跳动感。
- `frontend/src/pages/ProjectEntryView.vue`：
  - 过渡加载态补充移动端的居中与行高优化。

## 结构同步（2026-03-06 数据填报页顶部开关紧凑化修正）
- `frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue`：
  - 在手机断点下将 `topbar__status-row` 从纵向拉伸改回横向换行；
  - 取消 `.unit-analysis-inline` 的整行宽度，恢复为内容自适应宽度；
  - 保留 `submit-time` 占整行，其余开关恢复紧凑块状排列。

## 结构同步（2026-03-06 月报查询页与拉取页顶部密度收敛）
- `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：
  - 手机断点下继续收紧主内容区、摘要卡片与查询按钮区；
  - 降低多选区默认高度，使筛选区不再过度吃屏。
- `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`：
  - 手机断点下收紧工作台主内容区与步骤卡片；
  - 顶部按钮、批量预览确认按钮在窄屏下改为更紧凑或整行排列。

## 结构同步（2026-03-06 Banner 与按钮文字换行规整修正）
- `frontend/src/projects/daily_report_25_26/components/AppHeader.vue`：
  - 头部品牌名、副标题、用户信息与导航按钮统一限制为单行，避免窄屏下随机断行。
- `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：
  - 查询页按钮与分组操作按钮统一限制为单行文本，减少汉字拆行。
- `frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue`：
  - 工作台按钮与结果下载链接统一限制为单行文本，避免出现不整齐的换行。

## 结构同步（2026-03-07 月报查询页“重置”按钮手机端溢出修正）
- `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`：
  - 在 `<=640px` 下将查询按钮区 `.actions` 改为纵向排列；
  - 解决“查询 / 重置”两个整行按钮同时存在时第二个按钮被挤出容器的问题。

## 结构同步（2026-03-07 全局 AppHeader 手机端重排）
- `frontend/src/projects/daily_report_25_26/components/AppHeader.vue`：
  - 将品牌区改为固定两层文案结构，不再让品牌名和平台名自由混排；
  - 在手机宽度下将头部改为纵向分层布局；
  - 保持按钮单字不拆，但允许按钮区整体换层，避免“全挤在一行”。

## 结构同步（2026-03-07 Phoenix 手机页面优化 Skill 草案）
- 新增项目内 skill 草案：
  - [configs/skills/phoenix-mobile-layout/SKILL.md](/D:/编程项目/phoenix/configs/skills/phoenix-mobile-layout/SKILL.md)
- 内容已沉淀：
  - 手机页面问题分类
  - 固定优化顺序
  - 表格 / 按钮 / Banner / 查询页 / 数据录入页的处理规则
  - 构建验证与浏览器视口复测清单

## 结构同步（2026-03-06 项目选择页桌面卡片高度回退）
- `frontend/src/pages/ProjectSelectView.vue`：
  - 删除桌面端 `.card` 的固定最小高度，恢复 PC 端卡片原本的紧凑高度；
  - 手机端单列卡片与紧凑样式保持不变。

## 结构同步（2026-03-06 后端依赖版本锁定）
- 本轮无前端代码逻辑改动。
- 后端 `backend/requirements.txt` 已将原先未锁定的直接依赖与关键传递依赖（`grpcio` / `grpcio-status`）改为固定版本，以减少 Docker 构建时 `pip` 解析回溯。

## 结构同步（2026-03-06 后端 Docker pip 镜像源切换）
- 本轮无前端代码逻辑改动。
- 后端 `backend/Dockerfile.prod` 已为 Docker 构建中的 `pip install` 配置清华 PyPI 镜像，用于改善镜像构建下载速度。

## 2026-03-08 DataAnalysis 页面按钮顺序调整
- 页面：`daily_report_25_26` -> `DataAnalysisView`。
- 调整内容：将“智能报告（BETA）”和“智能体设定”移动到结果区按钮组，并置于“生成智能报告”按钮之前。
- 关键结构：`result-header-actions` 负责结果区顶部操作按钮排列。
- 说明：查询区不再承载智能报告入口按钮，仅保留未开放账号提示。

## 2026-03-08 DataAnalysis 智能报告行二次调整
- 调整目标：优化“智能报告（BETA）”与按钮行垂直对齐，并将“智能体设定”置于该行末尾。
- 页面结构：`result-header-actions` 内按钮顺序更新为 `下载 Excel -> 智能报告（BETA） -> 生成智能报告 -> 下载智能分析报告 -> 智能体设定`。
- 样式实现：`.ai-report-title` 采用 `inline-flex` 垂直居中，避免与按钮基线错位。

## 2026-03-08 月报智能体设定权限口径统一
- 页面：`monthly_data_show` 查询页 `MonthlyDataShowQueryToolView`。
- 变更：智能体设定按钮与弹窗管理权限由 `isGlobalAdmin` 改为项目动作权限 `auth.canManageAiSettingsFor('monthly_data_show')`。
- 影响：权限口径与日报一致，统一按 `can_manage_ai_settings` 控制。

## 2026-03-08 AI 气泡入口文案更新
- 组件：`AiChatWorkspace`。
- 调整：浮动气泡入口文字由“AI 助手”改为“智能助手”。
- 影响：仅前端展示文案变化，无功能逻辑变更。

## 结构同步（2026-03-08 admin-console 操作日志页恢复）

- 修复页面：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
- 问题原因：`activeTab === 'audit'` 的模板分支被误清空，导致“操作日志”页签无内容。
- 修复内容：恢复日志页完整 UI（筛选、统计、日志表格），并绑定既有 `reloadAuditData` 数据流。
- 当前行为：
  - 点击“操作日志”页签后会触发日志加载；
  - 支持按时间范围、用户、分类、动作、关键字筛选；
  - 支持展示分类统计与日志明细。

## 结构同步（2026-03-08 审计日志 IP 展示兼容）

- 文件：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
- 调整：操作日志表格中的 IP 列改为优先显示 `client_ip`，并兼容历史字段 `ip`。
- 目的：适配后端真实客户端 IP 解析改动，同时不影响历史日志记录回看。
## 结构同步（2026-03-08 管理后台日志采集范围收敛）

- 变更目标：将后台审计日志采集从“全局页面”收敛为“仅管理后台的操作日志页签”。
- 代码调整：
  - `frontend/src/main.js`
    - 移除全局 `initAuditTracking` 初始化，避免应用级路由/点击统一写入审计日志。
  - `frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
    - 新增 `syncAuditTrackingByTab`：仅在 `activeTab === 'audit'` 时调用 `initAuditTracking(...)`。
    - 离开 `audit` 页签或组件卸载时调用 `stopAuditTracking()`。
- 结果：
  - “后台文件编辑 / 数据库表编辑 / 项目后台设定 / 服务器管理”页签不再产生审计记录。
  - “操作日志”页签保留审计采集与展示能力。

## 结构同步（2026-03-08 更正：撤回采集范围改动）

- 用户确认本次诉求不包含“采集范围调整”。
- 已回滚：
  - 恢复 `frontend/src/main.js` 全局审计初始化。
  - 移除 `AdminConsoleView.vue` 内按页签启停采集逻辑。
- 当前口径：采集行为恢复为原有机制；操作日志页仍用于日志查看与筛选展示。

## 结构同步（2026-03-08 仅展示修复：操作日志页签隔离）

- 文件：`frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue`
- 修复点：将日志区块条件从 `v-else` 改为 `v-else-if=\"activeTab === 'audit'\"`。
- 影响：日志展示区仅在“操作日志”页签渲染；其他后台子页签不再显示日志区块。
- 说明：本次未改日志采集逻辑。

## 生产环境故障记录（2026-03-09）

- **故障现象**：网站主页可正常打开，但点击登录 504。
- **排查结论**：
  - 前端代码（`LoginView.vue`）和 API 逻辑正常，请求已成功发出。
  - Cloudflare 返回 504 是由于 `phoenix-web` Nginx 反代无法连接后端容器。
  - 属于服务器运维级别的 Docker 网络元数据损坏问题，非前端业务 Bug。
- **运维建议**：
  - 需强制清理生产环境残留容器。
  - 使用 `docker network prune` 清理孤立端点。
- **详见**：`configs/3.9 docker故障记录.md`。

## 外部接口分析记录（2026-03-09，辽宁省发改委现货电价）

- 本轮前端无代码改动。
- 用户新增的需求是分析站外页面 `https://fgw.ln.gov.cn/fgw/xxgk/xhdj/index.shtml` 中的分时电价数据来源。
- 已确认该页面前端只是承载 `iframe`，真实数据页是 `https://fgw.ln.gov.cn/indexview`。
- 页面会向 `POST /indexview/api/getListData` 发送 `{"date":"YYYY-MM-DD"}`，并返回单日 24 行表格数据。
- 已实测 `2026-01-01` 到 `2026-03-09`：
  - `2026-01-01` 至 `2026-03-08` 返回有效价格数据；
  - `2026-03-09` 返回空字符串占位，属于“当天未填值”而不是接口失败。
- 若后续前端要接这个外部源，建议直接按日请求 `getListData`，并在展示层过滤“全空日”。

## 外部接口抓取脚本联动说明（2026-03-09）

- 本轮前端仍无代码改动。
- 后端已新增脚本：
  - `backend/services/liaoning_spot_price_fetcher.py`
- 该脚本用于离线批量抓取辽宁省发改委现货电价数据，默认过滤“全空占位日”。
- 因此前端若后续要接入这份结果文件，默认可直接消费“已发布有效日”，无需在展示层重复处理当天空壳记录。

## 外部接口抓取脚本默认产物说明（2026-03-09）

- 本轮前端无代码改动。
- 后端脚本默认执行口径已固定为：
  - 抓取 `2026-01-01` 至 `2026-03-08`
  - 输出单个 JSON 文件到 `backend_data`
- 默认产物路径：
  - `backend_data/liaoning_spot_price_2026-01-01_2026-03-08.json`
- 当前 JSON 已压缩为“按天分组”结构，避免点位内重复日期字段，且点位按时间递增排序。

## 外部接口抓取脚本依赖说明（2026-03-09）

- 本轮前端无代码改动。
- 后端抓取脚本已去除 `httpx` 依赖，改为 Python 标准库实现。
- 因此在未安装额外包的环境中，也可以直接运行该脚本。
# 前端结构说明

## 2026-03-10 结构同步

- `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 步骤 3 导出的标准化 CSV 末尾新增两列：
    - `item_transform_type`
    - `item_transform_note`
  - 步骤 3.1 标准表对照导出同步保留 `company,item,item_transform_type,item_transform_note`。
  - 指标更名、单位转换、常量注入、半计算都会在这两列留下处理痕迹；步骤 4 入库继续忽略它们。

- `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
  - 新增“步骤 3.1：标准表对照”。
  - 在步骤 3 提取完成后，可独立导出只含 `company,item,item_transform_note` 的去重 CSV，对照标准表项集合。
  - 该分支纯前端本地生成，不影响原下载 CSV 与步骤 4 入库。
  - 步骤 3 导出的标准化 CSV 末尾新增 `item_transform_note` 字段：若指标由更名规则转换得到，则记为 `A→B`，否则留空。

- `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue`
  - 修复月报查询页时间口径：查询窗口继续只按 `date`（业务月份）传递，不再错误绑定 `report_month`。
  - 结果表“时间”列改为优先显示 `date`，避免把来源月份当成业务月份展示。
  - 导出月份汇总也改为优先按 `date` 统计。
- 月报查询页的“同比/环比/计划比（实时窗口）”口径说明更新：
  - 同比与计划比现在要求对应窗口逐月完备才展示；
  - 如果窗口内任一月份缺同期值或计划值，则对应结果显示为空，不再用局部月份数据拼成整段窗口对比值。
- 月报抽取规则说明更新：
  - 后端现已支持按子工作表范围应用指标更名规则；
  - 更名规则现为“单条规则 + companies 列表”模式，后续可直接为某一条指标更名单独指定适用口径。
