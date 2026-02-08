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
