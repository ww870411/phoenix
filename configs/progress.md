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
