# daily_report_25_26 后端说明

## 最新结构与状态（2026-02-08）

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
