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
