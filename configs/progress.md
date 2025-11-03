# 进度记录

## 2025-11-06（售电煤炭库存填报权限）

前置说明（降级留痕）：
- Serena 暂不支持对 JSON / JS 非符号文件执行插入更新，依据 3.9 矩阵降级使用 `apply_patch` 修改 `backend_data/auth/permissions.json` 与 `frontend/src/daily_report_25_26/store/auth.js`。
- 回滚思路：恢复上述两个文件的旧版本即可撤销额外授权及前端筛选逻辑。

本次动作：
- `backend_data/auth/permissions.json` 在 `unit_filler` 组的 `data_entry` 规则下追加 `Coal_inventory_Sheet` 显式授权，并更新 `updated_at` 标记此次权限变更。
- `frontend/src/daily_report_25_26/store/auth.js` 在 `by_unit` 模式下引入 `extraSheets` 白名单，允许通过权限文件显式授权的表单绕过单位前缀匹配，从而展示售电公司煤炭库存表。
- 文档同步：本记录、`backend/README.md`、`frontend/README.md` 补充售电煤炭库存权限开通说明。

影响范围与回滚：
- 新账号 `shoudian_filler` 登录后可在数据填报页面访问 `Coal_inventory_Sheet`；回滚时删除授权或恢复文件快照即可恢复旧行为。
- 其他单位仍沿用原 `by_unit` 筛选逻辑，未列入授权清单的表单行为不受影响。

下一步建议：
1. 如售电公司后续新增独立表单，可继续在权限文件 `sheets` 中登记并复用本次逻辑。
2. 后端可考虑在模板元数据中补充 `unit_code` 字段，减少前端依赖命名约定进行匹配。

## 2025-11-06（HTTP-only API 路由修复）

前置说明（降级留痕）：
- Serena 对 Bash 与 Nginx 配置文件暂不提供符号级编辑，依据 3.9 矩阵降级使用 `apply_patch` 更新 `ww.bash` 与 `deploy/nginx.http-only.conf`。
- Serena 暂不支持在仓库根目录新增 Compose 文件，因此使用 `apply_patch` 创建 `ww-certbot.yml`。
- 回滚思路：恢复上述两个文件的旧版本即可撤销本次调整。

本次动作：
- `deploy/nginx.http-only.conf` 新增 `/api/` 反向代理，HTTP-only 镜像在同域下即可透传请求到 `backend:8000`，无需依赖构建期写入完整域名。
- `ww.bash` 补充 `VITE_API_BASE` 二次校验，仅允许 `http(s)://` 或 `/` 开头的值，在构建日志中输出最终取值，并在推送后自动同步 `latest` 标签，防止继续生成指向本地磁盘的前端静态资源且确保服务器默认拉取即可获得最新镜像。
- 新增 `ww-certbot.yml`，包含 HTTP-only 前端和 Certbot 组合，通过 `/bin/sh -c` 执行申请脚本；目前命令内固定邮箱 `locookies123@gmail.com` 与域名 `platform.smartview.top`，如需使用其它参数可直接编辑该命令。

影响范围与回滚：
- 重新构建前端镜像后，默认执行 `./ww.bash` 即可生成指向 `/api/v1` 的资产；如需跨域 API，可显式设置合法 URL 并从日志确认。
- 回滚时恢复两个文件即可返回旧行为，但需注意旧版 HTTP-only 配置访问 `/api` 会返回前端资源。

下一步建议：
1. 将脚本打印的 `VITE_API_BASE` 同步写入构建产物的元数据或 Markdown 记录，方便部署后回溯。
2. 评估在 `ww.bash` 内加入最小 smoke test（如 `curl` `/api/health`），确保镜像在推送前即可发现 API 代理异常。

## 2025-11-05（仪表盘聚合与前端联动）

前置说明（降级留痕）：
- Serena 目前无法对全新 schema/service 文件及 `.vue` 组件执行符号级编辑，依据 3.9 矩阵降级使用 `apply_patch` 创建 `backend/schemas/dashboard.py`、`backend/services/dashboard.py` 与 `components/dashboard/*` 等文件。
- 回滚思路：删除新增后端模块并还原 `backend/api/v1/daily_report_25_26.py`、`frontend/src/daily_report_25_26/pages/DisplayView.vue`、`services/api.js` 及文档改动，即可恢复到原有占位仪表盘状态。

本次动作：
- 后端：实现 `GET /api/v1/projects/daily_report_25_26/dashboard/summary`，按业务日聚合气温、边际利润、收入分类、单耗、煤耗、投诉量与煤炭库存数据，新增 `dashboard` schema/service 并在路由层返回结构化 JSON。
- 前端：重写 `DisplayView.vue`，引入业务日筛选、加载提示及 7 个仪表盘卡片；新增基于 SVG 的折线图、分组柱状图、堆积柱状图组件，并在各卡片中配套表格展示本期/同期差异。
- 文档：更新 `backend/README.md`、`frontend/README.md` 描述仪表盘接口与页面结构；在本文件登记改动与降级原因。

影响范围与回滚：
- 新增接口默认受登录权限控制，并按 `allowed_units` 过滤可见单位；若需回滚，可移除 dashboard 相关模块与路由注册，前端恢复旧版展示页即可。
- 前端 SVG 图表未引入第三方依赖，渲染失败时仍可通过返回的表格信息查看关键指标；如需临时停用，可在页面中隐藏对应卡片。

下一步建议：
1. 视图聚合会触发多次查询，可评估 Postgres 物化视图/缓存策略或在服务层增加简单缓存。
2. 根据业务反馈补充更多异常提示（如缺报单位/指标高亮）及导出能力，完善仪表盘配套交互。

## 2025-11-04（镜像构建与部署拆分）

前置说明（降级留痕）：
- Serena 当前不支持在仓库根目录新建脚本/Compose 文件，依据 3.9 矩阵降级使用 `apply_patch` 创建 `ww.bash`、`ww.ps1` 与 `ww.yml`。
- 回滚思路：删除新增脚本/配置或恢复 `docker-compose.server.yml` 的本地构建流程即可撤销本次调整。

本次动作：
- 新增 `ww.bash` / `ww.ps1`，分别面向 Bash 与 PowerShell 环境封装后端、前端 HTTPS 与 HTTP-only 三个镜像的构建与推送步骤，统一写入时间戳标签并在完成后提示镜像名称，便于服务器部署引用；脚本增加 `VITE_API_BASE` 校验，自动过滤 `file://` 或 Windows 本地路径，避免构建产物引用本地磁盘。
- 新增 `ww.yml`，以预构建镜像替换原 build 阶段，保留 PostgreSQL、Certbot 服务与后端数据目录挂载，方便服务器直接拉取镜像运行。
- 新增 `ww-http-only.yml`，在无需证书的场景仅启动 HTTP 版前端、后端与数据库，去除 Certbot 与证书卷，适用于暂不启用 HTTPS 或交给 Cloudflare 托管的部署。
- 文档同步：更新 `backend/README.md`、`frontend/README.md` 与 `configs/progress.md`，补充镜像分发链路与部署指引。

影响范围与回滚：
- 如需恢复服务器本地构建，可继续使用 `docker-compose.server.yml` 或删除 `ww.bash`、`ww.ps1`、`ww.yml`、`ww-http-only.yml` 并回退本次文档变更。
- `ww.yml` 依赖 Docker Hub 镜像与证书卷，部署前需确认 `.env` 内的 `BACKEND_IMAGE`、`WEB_IMAGE`、`WEB_HTTP_IMAGE` 与实际推送版本一致；`ww-http-only.yml` 默认暴露 `80:80`，需确认云端/防火墙已放行 HTTP 访问。

下一步建议：
1. 将 `ww.bash`/`ww.ps1` 输出的镜像标签自动写入共享 `.env` 或脚本内更新 `ww.yml`，减少人为同步成本。
2. 为构建脚本增加基础 smoke test，如通过 `docker run --rm` 检查健康端口，再执行推送，降低线上运行风险。

## 2025-11-03（登录页面视觉同步）

前置说明（降级留痕）：
- Serena 暂不支持对 `.vue` 单文件组件进行符号级编辑，依据 3.9 矩阵在本次会话中降级使用 `apply_patch` 完成模板与样式重构，并保留原文件备份以备回滚。
- 回滚思路：将 `frontend/src/daily_report_25_26/pages/LoginView.vue` 恢复至 11-02 版本即可撤销本次视觉调整；文档条目可按需删除。

本次动作：
- 前端：重构 `LoginView.vue`，引入视觉面板与装饰图形，保持登录逻辑不变并增加响应式样式；追加视觉面板文本居中并下调蓝色渐变亮度以贴合参考页面效果。
- 后端：调整 `backend/sql/create_view.sql` 中 `calc_coal_cost`，使“煤成本”按“标煤耗量 × 标煤单价 / 10000”计算，替换原煤耗量逻辑。
- 文档：更新 `frontend/README.md`、`backend/README.md` 与 `configs/progress.md` 记录登录页与煤成本公式的同步情况。

影响范围与回滚：
- 前端：影响范围仅限登录页面的外观展示；若需回滚，覆盖旧版组件即可恢复原样式。
- 后端：如需回退，可将 `calc_coal_cost` 中的字段与常量键恢复为 `consumption_amount_raw_coal` / `price_raw_coal`。

下一步建议：
1. 如需对接验证码或企业公告，可在当前表单面板内扩展，不会破坏已实现的左右分栏布局。
2. 若仍需保留“原煤成本”口径，可新增独立 item 避免覆盖现有指标。

## 2025-11-02（登录与审批进度打通）

前置说明（降级留痕）：
- Serena 对 `backend_data/账户信息.json` 返回空结果，改用 `read_file` 获取原始配置；后续所有代码编辑均使用 `apply_patch` 小步提交。
- 新增权限矩阵、后端模块与前端状态管理涉及多个新文件，均按 3.9 矩阵要求记录，并可通过删除新增文件与恢复引用完成回滚。

本次动作：
- 配置：新增 `backend_data/auth/permissions.json`，整理用户组→页面/操作/单位映射及审批 Biz 日偏移（默认东八区“昨日”）。
- 后端：新增 `backend/services/auth_manager.py`、`backend/services/workflow_status.py` 与 `backend/api/v1/auth.py`、`backend/schemas/auth.py`；`routes.py`、`daily_report_25_26.py` 接入登录校验、审批/发布接口；所有项目路由默认要求 Bearer Token。
- 前端：新增 Pinia `auth` store、统一请求头注入与 `/auth/*` 调用；登录页改为真实认证流程；路由守卫自动判定跳转；页面选择页增加审批进度卡片（含批准/发布操作与权限过滤）；模板/表格列表按用户权限过滤。
- 日期管理：创建 `backend_data/date.json`，`auth_manager` 统一计算实际业务日（东八区昨日）并维护“数据展示日期”；发布动作会将展示日期同步至当前业务日，未发布时保持上一批数据，前端在审批卡片中提示“当前业务日期 | 当前数据展示日期”。
- 部署：新增 `backend/requirements.txt`、`backend/Dockerfile.prod`、`frontend/Dockerfile.prod`、`deploy/nginx.conf`、`docker-compose.prod.yml` 与 `deploy/server_setup.bat`，形成可直接在服务器构建的生产版容器栈；批处理脚本负责创建数据目录、载入 `.env.prod` 并执行 `docker compose build/up`。
- UI：`DataEntryView` 为 `Unit_admin` / `unit_filler` 引入历史日期只读模式（非当期业务日仅可查看、不能编辑提交），并在 `main.js` 全局引入主题样式修复子路由刷新样式丢失问题。
- 编排：`docker-compose.prod.yml` 中数据库使用命名卷 `db_data`，后端数据仍通过宿主挂载 `./backend_data:/app/data` 保持可读写配置。
- 新增 `docker-compose.server.yml` / `deploy/Dockerfile.web` / `deploy/nginx.prod.conf`，复刻旧项目的 Nginx+Certbot 方案（80/443 暴露、域名 `platform.smartview.top`），方便在 VPS 上直接替换运行。
- 新增 `init-certbot.sh`：一键执行“停 web → 构建/启动临时 HTTP-only → certbot 签发 → 恢复 web”流程，便于首次申请或更新 HTTPS 证书。
- 单镜像支持：新增 `Dockerfile.full`、`deploy/nginx.full.conf`、`deploy/supervisord.conf` 与 `build-single-image.sh`，可一次构建前后端合并镜像（`phoenix-all`），用于资源受限或“单容器”部署场景。

- 影响范围与回滚：
  - 认证与权限逻辑集中在 `backend/services/auth_manager.py` 与 `frontend/src/daily_report_25_26/store/auth.js`；删除新文件并还原调用点即可回滚至旧版“摆设登录”。
  - 审批/发布状态现持久化于 `backend_data/status.json`，如需回滚，可移除文件并将 `workflow_status.py` 恢复至内存版本，同时删除前端审批卡片即可恢复旧界面。

下一步建议：
1. 后端提交/审批接口接入细粒度权限校验（当前仅验证登录态）。
2. 账户明文密码与配置热加载策略需在上线前引入哈希与缓存失效通知。
3. 审批/发布状态落地数据库或 Redis，补充多节点场景下的一致性策略。

## 2025-10-29（会话开始：问候/初始化）

前置说明（降级留痕）：
- 已按 AGENTS 规范先调用 Serena 完成“项目激活 + 入职检查”。
- 本次仅为问候与初始化，无代码变更；需要将对话与动作留痕至仓库文档。
- 由于涉及 Markdown 文档编辑（非符号文件），依据 3.9 矩阵安全降级使用 `apply_patch` 进行写入，并将在 Serena 记忆中补录时间戳、文件清单与变更摘要。

本次动作：
- Serena：`activate_project(D:\编程项目\phoenix)` 与 `check_onboarding_performed()` 成功。
- 目录扫描：完成项目根目录 2 层结构快照（用于本地理解，不落盘）。
- 文档维护：在 `backend/README.md` 与 `frontend/README.md` 追加“会话小结（无代码改动）”。

影响范围与回滚：
- 仅文档新增小节；如需回滚，可删除本条与两个 README 中对应小节，不影响任何代码与接口。

下一步建议：
- 请告知本轮具体开发目标（接口/脚本/页面），我将据此更新计划并实施变更；如无特别指令，将优先补齐 `/template`、`/submit`、`/query` 的最小闭环联调样例。

## 2025-10-29（审批页面空白修复：runtime 适配 groups 视图）

前置说明（降级留痕）：
- 根据 10.29提示词.md [16:55] 的问题，`ZhuChengQu_approval_Sheet` 在模板中设置 `查询数据源.主表=groups`，但后端 `runtime_expression.py` 固定从 `sum_basic_data` 取数，导致 company=`ZhuChengQu` 无匹配记录而整表空白。
- 本次为 Python 源码修复，直接使用 `apply_patch` 小步修改，并在此留痕；后续将把验证结果补录至 Serena 记忆。

变更内容：
- 新增函数 `_fetch_metrics_from_view(session, table, company)`，白名单允许 `sum_basic_data|groups`；当模板指定 `主表=groups` 时，改为读取 `groups` 视图。
- 原 `_fetch_metrics_from_matview` 被替换为更通用的 `_fetch_metrics_from_view` 调用；动态日期路径仍保持直接聚合底表的实现不变。

影响范围与回滚：
- 仅影响 runtime 模式下的求值来源切换；如需回滚，改回固定表名 `sum_basic_data` 即可。

后续建议：
- 请确认数据库中 `create_view.sql` 已成功创建 `sum_basic_data` 与 `groups`；若 `groups` 未成功创建（10.29日志中出现 CTE 顺序错误提示），请先修正 SQL 后再验证本修复效果。

## 2025-10-29（SQL 校验：主城区直接收入等式）

结论：成立。
- `sum_basic_data` 中 `calc_direct_income` 明确定义为五项之和：
  - 售电收入（`calc_power`）+ 内售热收入（`calc_inner_heat`）+ 暖收入（`calc_heating_income`）+ 售高温水收入（`calc_hot_water`）+ 售汽收入（`calc_steam`）。
  - 证据：backend/sql/create_view.sql:706、713、720-727；组件 CTE 见：344（售电）、360（内售热）、392（暖收入）、414（售高温水）、437（售汽）。
- `groups` 视图以 `s AS (SELECT * FROM sum_basic_data)` 为来源并按公司集合聚合；`base_zc/base_grp` 会把上述“直接收入”以及“五项分项收入”分别求和汇总到主城区（ZhuChengQu）与集团（Group）。因此在分组层面同样满足：
  `ZhuChengQu.直接收入 = ZhuChengQu.(售电+内售热+暖+售高温水+售汽)`。
  - 证据：backend/sql/create_view.sql:960 起（groups 定义），`base_zc` 聚合来源于 `sum_basic_data` 的 item 全量（仅对比率等特殊项另行重算）。

备注：若实际对比发现不相等，优先检查 `sum_basic_data` 是否已成功创建且包含上述六个 item；其次检查分组视图是否过滤了这些 item（当前版本未过滤）。

## 2025-10-29（指标修正：groups 主城区直接收入口径）

前置说明：
- 根据 `configs/10.29计算指标修正.md`：groups 视图中 company=ZhuChengQu 的“直接收入”应等于“其中：售电收入 + 其中：暖收入 + 其中：售高温水收入 + 其中：售汽收入”（不含“内售热收入”）。

改动内容：
- 修改 `backend/sql/create_view.sql` 的 `groups` 定义：
  - 在“主城区：量/金额类直接汇总”分支中，将 `eco_direct_income` 从直汇名单中排除；
  - 新增一段 `UNION ALL` 重算主城区 `eco_direct_income` 为上述四项之和，分别对应 value_biz_date/value_peer_date/sum_7d_*/sum_month_*/sum_ytd_*。

影响范围与回滚：
- 仅影响 `groups` 视图中 `company='ZhuChengQu'` 的 `eco_direct_income` 行；其它公司与其它指标不受影响。
- 回滚方式：恢复直汇（将 `eco_direct_income` 从排除列表移除，并删除重算片段）。

sum_basic_data 相关：
- 文档同时要求将“边际利润/可比煤价边际利润”引入外购热成本与内购热成本；现有 `create_view.sql` 已包含这两项，无需改动。

## 2025-10-29（审批占位符透传修复）

问题：
- `backend_data/数据结构_审批用表.json` 中 `GongRe_approval_Sheet` 的“突发情况说明”行，在非数值列使用了占位符（如“——”），但渲染为空。

原因：
- `backend/services/runtime_expression.py` 在渲染阶段对非只读列一律尝试按表达式求值；求值失败或空值返回 `None`，最终显示逻辑将 `None` 映射为空串，导致占位符被吞掉。

修复：
- 统一占位符为单字符 `-`：当单元格求值结果为 `None` 且原始文本为 `-` 时，显示 `-`；其它文本不再作为占位符处理。
- 代码位置：`backend/services/runtime_expression.py`（新增 `_is_placeholder()` 并在显示阶段仅对 `-` 占位）。

影响与回滚：
- 仅影响非表达式文本在审批/展示模板中的显示；不改变数字/比率/表达式的求值逻辑。
- 回滚：移除新增的占位符透传分支即可恢复原行为。

## 2025-10-29（常量页无数据：前端未触发常量查询）

问题：
- 表 `constant_data` 已有数据，但“常量指标页面”不显示。原因是前端 `DataEntryView.vue` 仅在模板类型为 `standard` 或 `crosstab` 时调用 `/query`，`constant` 类型未触发查询。

改动：
- 前端 `frontend/src/daily_report_25_26/pages/DataEntryView.vue`：在 `loadTemplate()` 中为 `templateType==='constant'` 增加一次 `queryData` 调用，并使用 `applyStandardQueryResult(q)` 回填 `columns+rows`。
- 不需要 `biz_date`，period 标签由后端按列头“(本供暖期)/(同供暖期)”映射为 `25-26/24-25`。

- 后端 `backend/api/v1/daily_report_25_26.py::get_sheet_template`：补齐常量模板类型识别，`_is_constant_sheet(sheet_key)` 时返回 `template_type='constant'`，避免前端误判为 `standard`。

影响与回滚：
- 仅影响常量页首屏加载的回填显示；其他模板不受影响。回滚删除该分支即可。

## 2025-10-29（示例数据与命名修正）

前置说明：
- 按 AGENTS 全局指南，已使用 Serena 激活项目并完成上手检查；后续文件读写均通过 `apply_patch` 执行（不使用 cmd/pwsh）。本次修正覆盖“示例数据生成逻辑 + 命名规范统一”，并在此留痕，稍后会将摘要补录至 Serena 记忆。

本次改动：
- 修复命名：中心英文码统一为 `*_Center`；`sheet_name` 统一为 `*_Sheet`（S 大写）。
- 更新 `backend/scripts/generate_daily_basic_sample.py`：
  - 由“仅本期”改为“本期+同期”，且满足关系“本期=同期×1.25（提高25%）”；
  - 生成时同步应用 `*_Center` 与 `*_Sheet` 规范。
  - 修复 item 键来源：严格按 backend_data/数据结构_基本指标表.json 的“项目字典”（权威）生成 item 与 item_cn；若字典缺失即抛错（不做任何猜测与回退）。
- 新增 `backend/scripts/generate_constant_sample.py`：
  - 读取 `backend_data/数据结构_常量指标表.json`；
  - 生成 period=`24-25`（同期）与 `25-26`（本期）两期数据，满足“本期=同期×0.8（下降20%）”；
  - 统一 `*_Center` 与 `*_Sheet` 命名；输出到 `backend/sql/sample_constant_data.(csv|sql)`。
  - 修正分中心常量表“公司/中心”字段语义：将中心作为 `company/company_cn` 输出，`center/center_cn` 置空（与 daily_basic_data 对齐）。
  - 同步修复 item 键来源：严格按常量模板“项目字典”生成键名，若缺失则抛错（不猜测）。

涉及文件：
- 更新：`backend/scripts/generate_daily_basic_sample.py`
- 新增：`backend/scripts/generate_constant_sample.py`
- 文档：`backend/README.md`、`frontend/README.md`

影响范围与回滚：
- 若需要恢复旧命名（`*_center`/`*_sheet`）或旧同比关系，可回退对应脚本至本条之前的版本；已在 README 标注输出文件路径，便于对比与替换。

下一步建议：
- 如需我直接把 CSV/SQL 成品也落盘（体量较大），请确认后我将以 `apply_patch` 方式一次性写入 `backend/sql/` 目录，便于直接导入数据库。

补充（2025-10-29 晚）：
- daily 示例脚本：模板来源固定为 `backend_data/数据结构_基本指标表.json`；跳过 `Coal_inventory_Sheet`（交叉表归属 `coal_inventory_data`）；严格用同表“项目字典”反查 item，不命中直接报错，并在报错中列出前 30 个可用中文项。
- constant 示例脚本：模板来源固定为 `backend_data/数据结构_常量指标表.json`；分中心常量表将“中心”作为 `company/company_cn`；严格用“项目字典”反查 item，不命中直接报错，并在报错中列出前 30 个可用中文项。

## 2025-10-29

前置说明：
- 本次根据 `configs/10.29提示词.md` 的要求，优先使用 Desktop Commander 工具进行文件读取与编辑。会话开始时为遵循仓库 AGENTS 规范先行调用了 Serena 进行项目激活与上手检查；随后已切换为 Desktop Commander 优先。该偏差已在此处留痕并将在 Serena 记忆中补录。

本次改动：
- 拆分视图职责：将 `sum_basic_data` 还原为“公司明细粒度（无分组）”，新建独立分组视图 `groups` 复用 `sum_basic_data` 进行再聚合。
- 未引入“计算指标”逻辑，等待业务公式与常量 period 口径确认后再补充。

涉及文件：
- 更新：`backend/sql/create_view.sql`

影响范围与回滚：
- 查询分组口径的下游改为读取 `groups` 视图；如需回滚，可将 `groups` 中两段 `SELECT ... GROUP BY` 合并回 `sum_basic_data`（参照 git 历史或本次提交前版本）。

下一步计划：
- 确认收入/成本/利润/单耗/效率等“计算指标”所依赖的底表 item/constant 名称与单位，以及 `constant_data.period` 的取值规范；据此在 `sum_basic_data` 中追加“计算指标”行或列（建议追加为行，item=计算项）。

## 2025-10-29 公式解析与待确认
- 已阅读：`configs/10.29建视图公式.md`，整理了“直接收入/成本/利润/单耗/效率/投诉量/网损热量”等公式与中英文 item 映射，以及 `c.xxx` 常量清单。
- 存疑点（待你确认）：
  1) `内售热收入` 使用的单价是否等同于常量表的“售热单价”（`price_heat_sales`）？文档中未出现“内售热单价”常量条目。\\n  2) `days_to_biz()` 是否对每个时间口径分别取“从该口径起点到口径末日的天数”（如：7日口径=7，本月口径=当月日序，本供暖期口径=自10-01起的天数；同理用于同期口径）？\\n  3) `全厂热效率` 返回单位为`%`，是否需要四舍五入到小数点后两位？\\n  4) 字典中存在 `eco_inner_purchased_heat_cost`（内购热成本）、`eco_heat_lose`（网损成本）等，但公式未定义，是否需要补充？\\n  5) 常量 period 取值：是否统一按供暖期编码映射（biz=当年“YY-YY+1”，peer=上一年“YY-1-YY”）？\\n  6) 对于公司 {JinZhou, BeiFang, JinPu, ZhuangHe, YanJiuYuan} 的“站内耗热量”优先使用推导式（供热量-高温水销售量），如底表已填同名指标是否仍以推导覆盖？\\n- SQL 设计建议：在 `sum_basic_data` 基础 CTE 上“按公司聚合+按 item 条件汇总出 8 口径值”，再 `UNION ALL` 生成计算指标行为新 item（如 `eco_direct_income`），常量按 period（二套：biz/peer）左连接；`groups` 视图自然对新计算项做再聚合。\\n- 等待你的确认后，将一次性补齐完整 SQL（含口径天数与异常口径保护 `NULLIF(...,0)` + `COALESCE(...,0)`）。

## 2025-10-30

前置说明：
- 延续仓库规范，已通过 Serena 执行项目激活与上手检查；运行时代码通过 `serena__replace_symbol_body` 修改。
- Markdown 文档（progress / README）因 Serena 暂不支持直接写入，按 3.9 降级矩阵使用 `apply_patch`，本条记录作为留痕。
- 排障依据：`configs/10.30trace.md` 中 `safe_expr` 报错（`unmatched ')'`）与数据展示页“省市平台净投诉量”空值。

本次改动：
- 修复 `runtime_expression.Evaluator._preprocess` 对帧函数参数的解析，支持 `I(...)` 含括号一次捕获，避免生成 `value_biz_date("I("...` 导致语法错误。
- 对多指标累加的 `value_*` 调用在二次遍历阶段拆分为多个 `value_*("名称")` 相加，确保“不可加指标”仅返回单值。
- 新增 `c.<公司>.<常量>` 跨单位常量读取：解析表达式中的公司码并预取对应常量，解决“万平方米省市净投诉量”分母为 0 的问题。
- README 补充运行时表达式调试提示，提醒通过 `_trace` 检查帧函数入参展开情况。
- 新增展示表二（`Group_analysis_brief_report_Sheet`）跨列交叉表支持：
  - 解析 `列名1/列名2` 多级表头并生成 `column_headers`+`column_groups` 元数据；
  - 列级 company 映射 + 多 company evaluator 缓存，按日口径求值 `value_biz_date()/value_peer_date()`；
  - `date_diff_rate()` 按列组（公司维度）计算，支撑复数差异列；
  - 前端 `RevoGrid` 启用列分组与多行表头排版，保留追踪信息。

验证：
- 运行临时脚本直接调用 `_preprocess`，确认 `value_biz_date(当日撤件后净投诉量)` 输出 `value_biz_date("当日撤件后净投诉量")`，`value_biz_date(当日撤件后净投诉量+本月累计净投诉量)` 拆分为两个 `value_biz_date("…")` 相加。
- 执行 `render_spec(..., trace=True)` 重产 `configs/10.30trace.md`，确认 `used_consts` 中 `c.GongRe.挂网面积` 等返回实际数值，分母不再为 0；新表 `Group_analysis_brief_report_Sheet` 返回 `column_headers`+`column_groups`，并针对每家公司输出日口径差异。

涉及文件：
- 更新：`backend/services/runtime_expression.py`、`backend/api/v1/daily_report_25_26.py`、`frontend/src/daily_report_25_26/pages/DisplayRuntimeView.vue`、`backend_data/数据结构_全口径展示表.json`、`configs/10.30trace.md`、`configs/progress.md`、`backend/README.md`、`frontend/README.md`

影响范围与回滚：
- 如需回滚，可恢复 `_preprocess` 至 2025-10-27 版本并撤销本条文档说明；届时“省市平台净投诉量”会再次返回空值并在 `10.30trace.md` 重现 `unmatched ')'` 错误。若仅需撤销交叉表渲染，可恢复本条涉及的 `runtime_expression.py`/`DisplayRuntimeView.vue`/`api` 改动并还原配置文件。

## 2025-10-31

前置说明：
- 依照 AGENTS 规范，仍先通过 Serena 激活项目与检查上手；由于 Serena 在 `create_view.sql` 等纯文本 SQL 上仅能返回定位信息，无法直接读取上下文，本次根据 3.9 降级矩阵改用 Desktop Commander 的 `read_file`/`apply_patch` 操作；此处留痕，稍后会在 Serena 记忆补录。

本次改动：
- 新增视图 `sum_coal_inventory_data`：聚焦 `coal_inventory_data` 最新日期数据，按 `company + storage_type` 汇总 `value` 并保留 `unit`。
- 追加公司级与集团级汇总行：为各公司生成 `storage_type='all_sites'`（中文名“全部地点”）的合计行，同时输出 `company='ZhuChengQu_sum'`、`company='Group_sum'` 等聚合键以匹配模板中的 `scid.*` 写法。
- 运行时表达式支持 `scid.*`：`render_spec` 在加载常量别名时识别 `sum_coal_inventory_data`，按公司提取 `*_sum` 聚合值并在所有时间帧返回相同结果，解决“库存煤量（含港口、在途）”空白问题。

涉及文件：
- 更新：`backend/sql/create_view.sql`、`backend/services/runtime_expression.py`

验证：
- 通过 CTE 锁定最大日期后再做分组，确保空表不会产出虚假汇总；`MAX()` 保留单位/中文名，避免混合口径带来 NULL。
- 运行 `render_spec` 针对 `Group_analysis_brief_report_Sheet` 启用 `trace=True`，可在 `_trace.used_consts` 中看到 `scid.Group_sum`、`scid.JinZhou_sum` 等命中最新库存值。

影响范围与回滚：
- 若需恢复旧行为，可删除新增的 `sum_coal_inventory_data` SQL 段并重新执行脚本；恢复后最新库存的公司级/集团级汇总行将不再提供。若仅需移除 `scid` 支持，可恢复 `runtime_expression.py` 中别名加载逻辑至本条前版本。

下一步建议：
- 如需将该视图用于运行时表达式或展示页，可在后端补充查询接口，并确认 `company_cn` 与 `storage_type_cn` 的展示文案是否需要进一步本地化。

## 2025-11-01

前置说明：
- 继续按 AGENTS 流程激活 Serena 项目并检索上下文；对 Vue 文件与 JSON 模板因 Serena 暂不支持完整渲染，依 3.9 降级矩阵使用 Desktop Commander `read_file`/`apply_patch`，本条作为留痕。

本次改动：
- `backend/services/runtime_expression.py`：解析模板 `accuracy` 字典时生成 `accuracy_map`，按行（项目中文名）计算精度覆盖并在回填阶段应用不同小数位；新增 `accuracy_map` 字段输出。
- `backend/api/v1/daily_report_25_26.py`：透传 `accuracy_map` 为响应字段 `accuracy_overrides`，默认值沿用 `accuracy`。
- `frontend/src/daily_report_25_26/pages/ApprovalView.vue`：新增模板精度加载逻辑，通过 `getTemplate` 读取 `accuracy` 配置并解析 `default+分项`，按“项目”列定位行标签，将 RevoGrid 每行数值格式化与 `Intl.NumberFormat` 缓存绑定，实现审批页分项小数位控制。
- `frontend/src/daily_report_25_26/pages/DisplayRuntimeView.vue`：同步引入分项精度解析与格式化，支持展示页在同一表中按“项目”配置不同小数位；优先使用后端返回的 `accuracy_overrides`，模板请求作为兜底，保留差异列百分比格式及列分组渲染。
- `backend/services/runtime_expression.py`：扩展 `value_*` 系列函数参数解析，优先将括号内内容视作公司编码（支持中文/英文与 `A+B` 组合），并在预取阶段按需加载多 company 指标；运行时根据参数动态切换公司或降级为项目/常量读取。
- `backend/services/runtime_expression.py`：`date/sum_month/sum_ytd_diff_rate` 仅在单元格显式填写时才计算；空表达式的“日/月/供暖期差异”列保持空白，避免模板中用于分隔的行被强制填入 `-`。
- `backend/services/runtime_expression.py`：新增 `company.item` 解析（如 `value_biz_date(GongRe.本月累计净投诉量)`），优先按英文 item 反查中文名称再取值，默认表仍遵循模板 `default` 路由逻辑。
- `backend/services/runtime_expression.py`：锚点日期改用 Asia/Shanghai 时区的当日日期（`_project_today()`），默认仍回退“今日-1”，避免部署在 UTC 环境下导致 (本期日) 滞后两天。
- `backend/services/runtime_expression.py`：当 `item_en` 以 `sum_month_`/`sum_season_` 等前缀开头时，`value_*` 自动映射到 `sum_month_*` / `sum_ytd_*` 字段，保障累计类指标在日列/比率列中返回非零值。

验证：
- 通过手动审查 `render_spec` 行级量化与前端 `buildSource` 输出逻辑，确认含 `%` 的差异列仍返回字符，不受小数位影响；建议在前端运行环境下分别加载 `Group_sum_show_Sheet` 与 `Group_analysis_brief_report_Sheet`，观察“万平方米省市净投诉量”等配置项是否以 2 位小数展示，其余保持模板默认精度。
- 针对新模板 `ZhuChengQu_sum_show_Sheet` 逐项检查 `value_biz_date(ZhuChengQu)`、`value_biz_date(BeiHai+XiangHai)` 等写法能正确取到目标公司指标，组合求和等价于逐项累加。
- 多段标题（如“二、热源厂”）所在行的差异列未填写 `date_diff_rate()` 时，应在审批/展示页保持为空。

影响范围与回滚：
- 变更主要影响审批页(`ApprovalView`)、展示页(`DisplayRuntimeView`)的渲染逻辑以及运行时表达式的行级精度；若需回滚，可还原上述文件至本次改动前版本，或删除后端 `accuracy_map` 相关逻辑并恢复统一小数位行为。
- 若需恢复旧的单 company 求值，可还原 `runtime_expression.py` 中 `_resolve_company_item/_value_of_item` 调整，并将 `companies_needed` 解析段落改回仅按行默认 company 读取。

## 2025-11-02

前置说明：
- 运行时表达式模块需补充白名单逻辑，Serena 无法在模块顶部对常量行做精确删除，按 3.9 降级矩阵使用 `apply_patch` 调整字面文本，已在本条记录留痕；其余修改通过 Serena 完成。

本次改动：
- `backend/services/runtime_expression.py`：新增 `_PREAGG_VALUE_ITEMS` 集合，并在 `_value_of_item` 中针对 `sum_month_total_net_complaints`、`sum_season_total_net_complaints` 等预聚合投诉指标直接返回 `value_biz_date/value_peer_date` 字段，避免被累计窗口逻辑强制改写为 `sum_month_*`/`sum_ytd_*`。
- `backend/api/v1/daily_report_25_26.py`：`/runtime/spec/eval` 默认读取 `auth_manager.current_display_date()`（映射 `DATA_DIRECTORY/date.json` 的 `set_biz_date`），在未显式指定或传入 `regular` 时以该日期调用 `render_spec`，并在响应中附带 `biz_date`/`biz_date_mode`/`requested_biz_date` 便于前端追踪。

验证：
- 暂未执行自动化用例；建议在 `ZhuChengQu_sum_show_Sheet` 页面检查“省市平台净投诉量”行 `(本期月)/(本供暖期)` 列是否与视图 `sum_basic_data` 的 `value_biz_date` 保持一致（与前一版本对比应无再次累加现象），并通过展示页 Trace 响应确认 `biz_date` 已回显 `date.json` 中的 `set_biz_date`。

影响范围与回滚：
- 影响展示页及审批页涉及“本月累计净投诉量”“本供暖期累计净投诉量”的表达式求值；若需回退，可移除 `_PREAGG_VALUE_ITEMS` 并恢复 `_value_of_item` 中的累计字段映射逻辑，或整文件回滚至本次提交前版本；如需恢复旧的 `biz_date` 透传逻辑，可撤销 `/runtime/spec/eval` 中关于 `set_biz_date` 的默认处理。

### 补充记录（2025-11-02 晚）

- `create_view.sql` 中的 `sum_basic_data`、`groups` 视图改为读取数据库会话级参数 `phoenix.biz_date`（缺省回落至 `current_date-1`）。运行时通过 `SET LOCAL phoenix.biz_date = :biz_date` 在查询阶段切换业务日期，沿用原 SQL 中的全部派生计算逻辑。
- `runtime_expression.py` 删除手写聚合逻辑，统一走视图查询：当 `context.biz_date` 提供具体日期时设置 GUC，未指定则重置为 `DEFAULT`，保证回退到旧口径。
- `frontend/src/daily_report_25_26/pages/DisplayRuntimeView.vue`：展示页的日期选择器默认读取 `date.json`（display_date），用户修改后直接把选定日期作为 `biz_date` 发送给 `/runtime/spec/eval`，日历旁显示当前生效口径。
- 建议在 `Group_sum_show_Sheet`、`ZhuChengQu_sum_show_Sheet` 开启 Trace 验证 `biz_date` 是否与 `date.json` 一致，并核对直接收入、供暖单耗、投诉 per 万㎡ 等关键指标已恢复正确值。

## 2025-11-04

前置说明：
- Serena 无法直接在 SQL 文件末尾追加内容，依据 3.9 降级矩阵使用 `apply_patch` 编辑 `backend/sql/create_view.sql`；回滚时删除新增视图定义并重新执行脚本。

本次改动：
- `backend/sql/create_view.sql`：新增普通视图 `calc_temperature_data`，按 `temperature_data` 的业务日期（24 小时）分组计算日最高/最低/平均温度，为后续天气数据统计提供聚合入口。

验证：
- 暂未执行数据库验证；建议在数据库运行 `SELECT * FROM calc_temperature_data LIMIT 5;`，确认视图创建成功并返回按日聚合的期望结构。

影响范围与回滚：
- 仅新增视图，不影响现有 `sum_basic_data` 等视图逻辑；如需回滚，删除该视图定义并重新加载脚本即可。

## 2025-11-06（HTTPS 切换与部署文件调整）

前置说明（留痕与合规）：
- 环境为沙箱只读，已按“3.9 编辑与文件操作降级矩阵”使用 Desktop Commander 工具进行小步安全修改；不涉及破坏性命令。
- 本次仅变更仓库内脚本/编排文件，不触及受限目录或远端 CI/CD。

本次动作：
- 更新 `ww.ps1:1`：新增 `BUILD_HTTP_ONLY` 开关（默认关闭），将 HTTP-only 前端镜像的构建与推送改为“可选”；启用 HTTPS 时默认跳过，避免不必要的镜像产出。
- 更新 `ww-http-only.yml:1`：升级为支持 HTTPS 的部署（开放 `80/443`，挂载 `certbot_etc` 与 `certbot_www` 卷，并内置 `certbot` 更新服务），`web` 服务改用 `WEB_IMAGE`（HTTPS 版）。

实现要点与流程：
- PowerShell 脚本：`Divider` 与 `Tag-And-PushLatest` 两个函数保持不变；通过新增布尔变量 `$BuildHttpOnly`（读取 `BUILD_HTTP_ONLY`）在构建阶段做分支，默认只构建/推送 HTTPS 版 `WEB_IMAGE`。
- Compose 部署：沿用 `deploy/nginx.prod.conf` 的证书路径与重定向策略，`web` 容器暴露 `80/443`（80 做 301 跳转，443 提供 TLS 服务）；`certbot` 容器以 `renew` 循环任务维持证书更新。

影响范围与回滚：
- 现有服务器可直接切换到本次调整后的 `ww-http-only.yml` 运行 HTTPS（需已有证书卷或先按 `ww.yml`/`ww-certbot.yml` 完成一次申请）。
- 若需回退到纯 HTTP-only，设置 `BUILD_HTTP_ONLY=1` 并改回 `WEB_HTTP_IMAGE` 的 compose 文件即可。

证据与文件清单：
- 修改：`ww.ps1:1`, `ww-http-only.yml:1`
- 参考：`deploy/nginx.prod.conf:1`, `ww.yml:1`

### 2025-11-06（域名与证书路径具体化）
- 域名：`platform.smartview.top`
- 邮箱：`locookies12@gmail.com`
- 证书（宿主机）：`/home/ww870411/25-26/certbot/letsencrypt/live/platform.smartview.top/`
- 变更：
  - `ww.yml:1` 与 `ww-http-only.yml:1` 的 `web`/`certbot` 服务将证书与 ACME webroot 改为宿主机绑定挂载：
    - `/home/ww870411/25-26/certbot/letsencrypt:/etc/letsencrypt`
    - `/home/ww870411/25-26/certbot/www:/var/www/certbot`
  - 移除两份 compose 中不再使用的命名卷 `certbot_etc`/`certbot_www`。
  - `ww-certbot.yml:1` 更新邮箱为 `locookies12@gmail.com`，并同步改为宿主机路径绑定挂载，便于一次性签发或重签直接落盘到上述目录。
- Nginx 配置确认：`deploy/nginx.prod.conf:1` 中 `server_name` 已是 `platform.smartview.top`；证书路径继续使用容器内 `/etc/letsencrypt/live/platform.smartview.top/`，与 compose 的宿主机路径绑定保持一致。
- 上线前自检：DNS 指向、80/443 放行、宿主目录存在并具备读写、已有证书文件可被 web 容器读取。

### 2025-11-06（禁用 latest 推送）
- 依据用户要求“绝对禁止 latest”，已移除 `ww.ps1` 中所有 `latest` 标记与推送逻辑：删除 `Tag-And-PushLatest` 函数，并去除后端/前端/HTTP-only 的调用。
- 影响：后续仅按时间戳 tag 推送，不再产生 `:latest`。
- 备注：本次构建失败的前端镜像为拉取 `nginx:1.27-alpine` 时网络 EOF；建议重试或预先 `docker pull nginx:1.27-alpine node:20-alpine` 后再运行脚本。

### 2025-11-06（ww.ps1 精简为“必要最小”）
- 目标：仅保留必要步骤，避免“为考虑而加”的非必要逻辑。
- 变更：
  - 移除 HTTP-only 分支与相关变量；脚本只构建/推送后端与 HTTPS 前端两张镜像。
  - 移除复杂的 `VITE_API_BASE` 过滤逻辑；仅当设置该环境变量时才作为 build-arg 传入，否则使用前端源码默认值。
  - 保留 `NO_CACHE` 支持与 `BUILD_TIMESTAMP`；日志仅输出关键信息。
- 影响：脚本总行数由 ~115 行降至 ~66 行，更易读、易控。

### 2025-11-06（构建稳定性增强：重试与预拉）
- ww.ps1 增强：
  - 新增 `Invoke-Retry`（最多 3 次，间隔 6 秒），用于 docker pull/build/push 的瞬时失败自动重试。
  - 在构建前预拉基础镜像：`python:3.12-slim`、`node:20-alpine`、`nginx:1.27-alpine`。
  - 对后端/前端 build/push 全部包裹重试，降低 EOF 失败概率。
- 说明：不改变输出镜像或版本，仅增强稳定性；无 latest 相关操作。

### 2025-11-06（构建加速镜像源——避免 auth.docker.io EOF）
- 现象：`failed to fetch oauth token: https://auth.docker.io/token EOF`，公共 Hub 取元数据不稳定。
- 变更：将基础镜像切换为 DaoCloud Hub 镜像源（可在国内稳定访问）：
  - backend/Dockerfile.prod:1 `FROM docker.m.daocloud.io/library/python:3.12-slim`（builder 与 runtime 两处）
  - deploy/Dockerfile.web:1 `FROM docker.m.daocloud.io/library/node:20-alpine`
  - deploy/Dockerfile.web:20 `FROM docker.m.daocloud.io/library/nginx:1.27-alpine`
- 影响：不改变业务产物，只更换镜像拉取来源；如需回退，改回 `python:3.12-slim` / `node:20-alpine` / `nginx:1.27-alpine` 即可。
### 2025-11-02（常量提交 500：移除 center/center_cn 依赖）
- 现象：在 `ZhuangHe_constant_Sheet` 提交数据时，前端 500；控制台报错 `{"ok":false,"message":"处理常量表数据时发生错误","error":"center_cn"}`（见 `configs/11.2常量提交错误.md:1,18`）。
- 根因：后端常量写库函数在构造 upsert 时引用了 `center/center_cn` 字段与唯一键 `(company, center, sheet_name, item, period)`；但数据库表与 ORM 模型均不再使用/不存在 `center/center_cn`，导致引用 `stmt.excluded.center_cn` 抛错。
- 变更：
  - `backend/api/v1/daily_report_25_26.py`
    - `_parse_constant_records`：取消向记录附加 `center_cn`；仅将中心中文名用于解析 `company/company_cn`，不再持久化中心字段。
    - `_persist_constant_data(records)`：
      - 写入前清理 `center/center_cn` 残留键；
      - `ON CONFLICT` 唯一键改为 `(company, item, period)`；
      - 更新字段集合移除 `center_cn`。
    - `_parse_decimal_value`：支持自动剔除字符串中的 `,`/`，`/空格，并过滤 `--`、`N/A` 等占位符，避免“采暖期供暖收入”等金额类单元格因存在千位分隔符而被解析为 `NULL`。
- 影响：
  - 常量数据幂等粒度以 `(company, item, period)` 为准；
  - 前端常量表 payload 无需也不应包含 `center/center_cn`；含中心维结构的表也仅用于解析 company/company_cn，不再单独存储 center 维度。
- 需要的数据库侧配合：为 `constant_data` 创建唯一约束/索引 `(company, item, period)`，并确保不存在 `center/center_cn` 列；否则 `ON CONFLICT` 将无法命中唯一键。
- 回滚思路：若需恢复 center 维度，需同步恢复表列 `center/center_cn`、唯一键 `(company, center, sheet_name, item, period)`，并回退服务端 upsert 的 `index_elements` 与 `set_`。
- 证据：
  - 服务端引用位置：`backend/api/v1/daily_report_25_26.py:1346`（变更后）
  - 模型定义：`backend/db/database_daily_report_25_26.py:40`（ConstantData 无 center/center_cn）
  - 示例 SQL（历史意图，仅供参考）：`backend/sql/sample_constant_data.sql:820` 起含 center/center_cn 列

### 2025-11-02（运行时温度极值接入 Group 分析简报）
- 场景：`Group_analysis_brief_report_Sheet` 中“日最高气温/日最低气温”需要取 `temperature_data` 当日极值，默认 `value_biz_date()` 仍接 sum_basic_data 导致返回 0。
- 变更：
  - `backend/sql/create_view.sql`、`backend/sql/create_temperature_view.sql`：视图更名为 `calc_temperature_data`，按日输出 `max_temp`/`min_temp`/`aver_temp`。
  - `backend/services/runtime_expression.py`
    - `_fetch_temperature_extremes`：新增从 `calc_temperature_data` 读取当日与同期日温度极值，统一映射到 `amount_temp_highest`、`amount_temp_lowest` 六个帧字段。
    - `render_spec` 在预取指标阶段将上述极值合并到 `metrics_by_company['Group']`，保持其它单位不受影响。
- 效果：模板仍使用 `value_biz_date()`/`value_peer_date()`，集团列可直接显示真实温度极值；差异列 `date_diff_rate()` 自动生效。
- 验证建议：
  1) 调用 `/runtime/spec/eval` 加 `trace=true`，确认 `_trace.used_items` 出现 `amount_temp_highest`/`amount_temp_lowest` 并返回新值；
  2) SQL：`SELECT * FROM calc_temperature_data WHERE date='2025-11-02';`；如需同期日，检查同一天减一年数据。
- 回滚思路：
  - 视图恢复为原 `average_temperature_data`；
  - 删除 `_fetch_temperature_extremes` 调用，并在 `Group_analysis_brief_report_Sheet` 中改回常量或默认值。

### 2025-11-06（供热分中心提交：center/center_cn 映射修复）
- 现象：在 `GongRe_branches_detail_Sheet` 提交数据时，`daily_basic_data` 中 `company`、`company_cn` 均写成“XX中心”（中文），未使用模板里的英文代号。
- 原因：`_parse_gongre_branches_detail_records` 仅从 payload 的 `center_dict` 键读取字典，但模板和前端传值使用的是“单位字典”，导致反向映射缺失。
- 变更：`backend/api/v1/daily_report_25_26.py`
  - `_parse_gongre_branches_detail_records` 使用 `_extract_mapping`，先查 `CENTER_DICT_KEYS`，若不存在再回落到 `COMPANY_DICT_KEYS`，并统一对项目字典走同样的转换，保证 `center_lookup` 能找到英文代号。
- 效果：分中心提交会将 `company` 写入 `HuaLe_Center` 等英文编码，`company_cn` 写入中文名称，满足数据库 Tall Table 设计。
- 验证建议：
  1) 在页面填写分中心数据并提交；
  2) 查询 `SELECT DISTINCT company, company_cn FROM daily_basic_data WHERE sheet_name='GongRe_branches_detail_Sheet' ORDER BY company;` 应显示英文编码 + 中文名称配对。
- 回滚：如需恢复旧行为，仅需将 `_extract_mapping` 调用还原为直接 `payload.get("center_dict")`。

### 2025-11-06（集团直接收入去除内售热）
- 现象：`groups` 视图中 `company='Group'`、`item_cn='直接收入'` 的重算块会把 `eco_direct_income` 连同 sum_basic_data 中的“内售热收入”一起求和。
- 变更：`backend/sql/groups.sql`
  - 在集团汇总基表 `base_grp` 中排除 `eco_direct_income` 基础行，避免重复；
  - 新增集团口径的自定义重算块，仅汇总 `售电/暖/售高温水/售汽` 四项收入。
- 效果：集团“直接收入”不再包含“内售热收入”，与主城区计算口径一致。
- 验证：执行 `SELECT item, value_biz_date FROM groups WHERE company='Group' AND item='eco_direct_income' LIMIT 1;` 并确认数值与四项收入之和一致。
- 回滚：删除新增 UNION 块，并将 `eco_direct_income` 从 `WHERE item NOT IN (...)` 的排除列表中移除即可。

### 2025-11-06（scid.* 省级汇总常量兼容）
- 现象：`ZhuChengQu_sum_show_Sheet` 行内使用 `scid.ZhuChengQu_sum` 时返回 0，原因是 `_value_of_const` 仅在当前 company 的常量缓存中查找，未回退到全局常量集合。
- 变更：`backend/services/runtime_expression.py`
  - `_value_of_const` 在本地别名查找不到时，会在 `self.consts_all` 中循环各公司别名，优先命中同名键，再进入 period 取值，兼容 `scid.Group_sum`、`scid.ZhuChengQu_sum` 等写法。
- 效果：`scid.*` 无需指定 `公司.常量` 形式即可返回合计库存值，历史模板写法保持有效。
- 验证：运行 `/runtime/spec/eval` 并检查 `_trace.used_consts` 是否出现 `scid.ZhuChengQu_sum` 等记录；或直接在前端页面观察库存列是否正常展示。
- 回滚：若要恢复旧行为，只需移除新增循环，让 `_value_of_const` 只在当前 company 常量缓存中查找即可。
