# 后端说明（FastAPI）

## 新增能力（2025-10-23）

- 新增接口 `GET /api/v1/projects/{project_id}/pages`，用于按项目返回页面与所属模板文件映射。
- 所有 `/data_entry/sheets` 相关接口新增可选查询参数 `config`，允许前端显式指定模板 JSON 文件；默认仍回落至基础指标表。
- 模板枚举逻辑会自动读取 `backend_data/项目列表.json` 中声明的所有模板文件，无需手工维护候选列表。

## 结构快照更新（2025-10-28）

- 已在 `backend/sql/create_view.sql` 中完善二级物化视图并发刷新支持：
  - `calc_sum_basic_data` 增加唯一索引 `(company, item, scope)` → 允许 `REFRESH MATERIALIZED VIEW CONCURRENTLY`。
  - `calc_sum_gongre_branches_detail_data` 增加唯一索引 `(center, item, scope)` → 允许 `REFRESH MATERIALIZED VIEW CONCURRENTLY`。
  - 两处均以中文注释标明用途与行粒度假设，避免误删。
  - 新增调试视图 `calc_sum_basic_trace`，用于排查二级视图计算过程（显示数量、单价、乘积与缺失标记）。

## 运行时计算（替代二级物化视图，可选）

- 新增服务模块：`backend/services/calc_fill.py`
  - 函数：`fill_company_calc(payload: Dict[str, Any], db: Optional[Session]=None) -> Dict[str, Any]`
  - 入参：`{ company | company_cn, scope, period? }`，`scope` 支持 `value_biz_date/value_peer_date/sum_7d_*/sum_month_*/sum_ytd_*`。
  - 行为：直接聚合 `sum_basic_data` 指定口径列 + 读取 `constant_data`（带键名/期别规范化），在内存计算并返回一个“填满的对象”，字段与原二级物化视图一致。
  - 单位换算与公式同 `calc_sum_basic_data`：售电收入为万元（万kWh×元/kWh），售热收入除以 10000。
  - 适用场景：放弃/停用二级物化视图时，后端可用该函数按需计算，避免迁移成本。

- 新增表达式求值模块：`backend/services/expression_eval.py`（本次新增）
  - 函数：`fill_sheet_from_dict(sheet_obj: Dict[str, Any], db=None, trace: bool=False) -> Dict[str, Any]`
  - 输入：与 `configs/字典样例.json` 单表对象相同结构（含“单位标识/单位名/列名/数据/项目字典”）；
  - 行为：
    - 解析并执行单元格表达式与函数：`value_biz_date()/value_peer_date()/sum_month_*/sum_ytd_*`、`date|month|ytd_diff_rate()`；
    - 支持 `c.售电单价/售热单价/...` 的常量引用（来源 `constant_data`，自动 period 规范化）；
    - 支持同列行间引用（如“直接收入-煤成本-...”优先使用同列已算值）；
    - 单位换算与 `calc_fill.py` 保持一致：除 `售电单价` 外，数量×单价默认 `/10000` → 万元；
  - 输出：返回“数据已填满”的同结构对象；`trace=True` 时附带 `_trace.cells[]` 展示每个单元格的求值明细（便于排障）。

该目录存放 Phoenix 项目的后端代码，采用「FastAPI + 版本化路由」的结构：

- `main.py`：FastAPI 应用入口，挂载 `/api/v1` 前缀并提供 `/healthz`。 
- `api/v1/routes.py`：顶层路由调度，将不同项目的路由注册到 `/api/v1/projects/*`。 
- `api/v1/daily_report_25_26.py`：`daily_report_25_26` 项目的业务路由，实现 `ping`、`sheets`、`template/submit/query` 等接口。 
- `models/`、`schemas/`、`services/`：预留 ORM、Pydantic、领域服务层。 

## 运行方式

Docker 开发环境：

```bash
docker compose up -d --build
```

本地直接运行：

```bash
python -m pip install fastapi "uvicorn[standard]"
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

常用访问：

- 健康检查：`http://127.0.0.1:8000/healthz`
- 系统心跳：`http://127.0.0.1:8000/api/v1/ping`
- 项目心跳：`http://127.0.0.1:8000/api/v1/daily_report_25_26/ping`

## 目录快照（自动维护）

更新时间：2025-10-22

- 目录
  - `Dockerfile`
  - `README.md`
  - `__init__.py`
  - `config.py`
  - `main.py`
  - `api/`
    - `__init__.py`
    - `v1/`
      - `__init__.py`
      - `routes.py`（统一前缀 `/api/v1`）
  - `daily_report_25_26.py`（项目路由与模板/填报/查询逻辑）
    - 标准表提交流程：`_flatten_records` 从“列头日期文本”提取每列 `date`；前端应确保列头根据所选 `biz_date` 动态替换。
    - 煤炭库存表（`Coal_inventory_Sheet`）特殊处理：解析顶层 `biz_date` 并持久化到 `coal_inventory_data`。
    - 查询接口设计（提案，待实现）：
      - 单表查询：`POST /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/query`
        - 内部按模板类型自适应返回：
          - standard：`{ template_type:'standard', columns:[...], rows:[...] }`
          - crosstab（煤炭库存）：`{ template_type:'crosstab', columns:[...], rows:[...] }`
          - constants：同 standard，按 columns+rows 回填对应期别列。
      - 项目级聚合查询：`POST /api/v1/projects/{project_key}/query`
        - 入参：`sheet_keys[]`、`scope`（data_entry/display/constants）、`biz_date|date_range`、`mode`（records/matrix）。
        - 出参：`{ results: { [sheet_key]: ... }, meta: {...} }`，适用于数据展示/仪表盘批量读取。
  - `db/`
    - `__init__.py`
    - `database_daily_report_25_26.py`
- `models/`
    - `__init__.py`
- `schemas/`
    - `__init__.py`
- `services/`
    - `__init__.py`
- `sql/`
    - `create_tables.sql`
    - SQL 不再包含 `gongre_branches_detail_data`；分中心数据已统一落库 `daily_basic_data`（以 sheet_name='GongRe_branches_detail_Sheet' 区分）。
    - `create_view.sql`（集中维护物化视图/分析视图定义；包含：
      - 一级视图：`sum_basic_data`、`sum_gongre_branches_detail_data`（来源基于 `daily_basic_data` 并按 `sheet_name='GongRe_branches_detail_Sheet'` 过滤，视图对外仍以 `center/center_cn` 别名输出）。
      - 二级视图：`calc_sum_basic_data`、`calc_sum_gongre_branches_detail_data`；已添加唯一索引以支持并发刷新）。
      - 排障视图：`calc_sum_basic_trace`（仅用于查看中间输入与乘积，非物化）。

## 查询接口（镜像查询）
- 单表查询（已实现）：`POST /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/query`
  - standard（每日）：`{ template_type:'standard', biz_date, columns:[...], rows:[...], attatch_time, request_id, source }`
  - constants（常量）：`{ template_type:'constant', period, columns:[...], rows:[...], attatch_time, request_id, source }`（返回列头已替换为供暖期编码，如 `25-26`、`24-25`，便于前端直接展示与回填）
  - crosstab（煤炭库存）：`{ template_type:'crosstab', biz_date, columns:[...], rows:[...] }`
- 聚合查询（规划中）：`POST /api/v1/projects/{project_key}/query`
  - 入参：`sheet_keys[]`、`scope`（data_entry/display/constants）、`biz_date|date_range`、`mode`（records/matrix）。
  - 附加：`attatch_time` 为东八区时间戳（毫秒），便于前端对照调试；`request_id` 回显前端请求ID，便于去重与仅消费最新响应。
  - 附加：`source` 为调试信息，包含：
    - `handler`：处理本次查询的函数名（如 `query_sheet`）
    - `template_type`：`standard`/`constant`/`crosstab`
    - `received`：请求来源摘要 `{ path, query, payload:{ biz_date, period, company } }`
  - 出参：`{ results: { [sheet_key]: ... }, meta: {...} }`。

## 接口路线图（2025-10-19）

- `GET /api/v1/ping`：系统级心跳。
- `GET /api/v1/projects`：读取 数据目录（默认 `/app/data`）下的 `项目列表.json` 并返回项目（`project_id/project_name`）。
- `GET /api/v1/projects/{project_key}/data_entry/sheets`：读取 数据目录中的数据填报模板清单。返回字段包含：
  - `单位名`、`表名`：兼容旧有前端；
  - `unit_name`、`sheet_name`：便于英文字段访问。
- `GET /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/template`：
  - 从数据目录中的 `数据结构_基本指标表.json` 读取指定模板；
  - 支持 `sheet_key` 大小写归一化匹配，若该文件提供 “单位标识” 字段将优先返回该版本；
  - 自动追加两列日期，返回结构为 `sheet_key/sheet_name/unit_name/columns/rows`；
  - 附带模板内定义的字典字段（如“项目字典”“单位字典”等）；前端需保持字段名称与内容一致并在提交时原样回传；
  - `columns` 形如 `[项目, 计量单位, <今日（东八区）>, <去年同日>]`。
- `POST /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/submit`：当前为调试出口，会打印原始 payload、拆解结果与扁平化列表，后续可平滑接入数据库写入；自 2025-10-22 起，空值单元格在后端统一落库为 `NULL` 以区分未填与真实零值。
  - `GongRe_branches_detail_Sheet`：专用分支解析中心/指标，现已统一写入 `daily_basic_data`（company=中心英文名，company_cn=中心中文名，sheet_name='GongRe_branches_detail_Sheet'），调试记录输出至 `configs/111.md`。
  - `Coal_inventory_Sheet`：使用 `_parse_coal_inventory_records` 写入 `coal_inventory_data`，调试记录追加在 `backend_data/test.md`。
- `POST /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/query`：占位。

## 模板处理规则

1. 读取 数据目录中的 `数据结构_基本指标表.json`。
2. 查找到的模板字段会进行以下标准化：
   - 提取单位名、表名（支持多种键名）；
   - `columns` 保持模板内的占位符（如“(本期日)”“(同期日)”“(本期月)”），具体日期由前端渲染阶段替换；
   - `rows` 兼容任意长度的数组，逐行按列表返回。
   - 模板中出现的 `*_dict` 字段（如项目/单位/中心/状态字典）会在接口中全部透传给前端，便于提交时带回。
   - 前端渲染会按照列头中首次出现“计量单位”的位置，将此前列自动标记为只读，后端无需额外维护该规则。
3. 当模板缺少 `列名` 或 `数据` 字段时，接口返回 422 以提示数据管理员处理。

## CORS 设置

- 默认允许 `http://localhost:5173`、`http://127.0.0.1:5173`。
- 通过环境变量 `PHOENIX_CORS_ORIGINS`（逗号分隔）扩展来源，例如：

```bash
PHOENIX_CORS_ORIGINS=http://localhost:5173,http://my-host
```

- Docker Compose 场景下，`backend` 服务会自动挂载 `./backend_data` 至容器 `/app/data`，保持模板与日志可追溯；程序内部统一通过 `DATA_DIRECTORY`（默认 `/app/data`）访问。

## 数据库初始化脚本

- 新增 `backend/sql/create_tables.sql`，包含 `Daily_basic_data`、`Constant_data`、`Temperature_data`、`Coal_inventory_data` 四张业务表的建表语句，可重复执行（使用 `CREATE TABLE IF NOT EXISTS` / 索引自动去重）。
- docker-compose 已将宿主机 `backend/sql` 目录挂载至数据库容器 `/app/sql`，可通过以下命令在 `phoenix` 数据库中执行脚本（数据库容器需处于运行状态）：

```bash
docker compose exec db psql -U postgres -d phoenix -f /app/sql/create_tables.sql
```

- PostgreSQL 数据卷已绑定宿主机目录 `D:/编程项目/phoenix/db_data`，请确保目录存在并拥有写权限后再启动容器。
#
# 变更记录（2025-10-23）

- 前端修复：交叉表（`Coal_inventory_Sheet`）默认日期首次进入页面不显示数据的问题，属前端初始化顺序导致的镜像查询结果被覆盖；本次无后端接口与数据结构改动。
## 变更：镜像查询返回模板结构（2025-10-25）

- 动机：`cells` 形式在标准/常量表上增加了前后端复杂度；现已改为完全复用模板渲染路径（rows-only），降低分支逻辑与心智负担。
- 新行为：
  - `/api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/query` 现返回与 `/template` 一致的结构：`columns` + `rows`（另附 `sheet_name`、`unit_id`、`unit_name` 及各类 `*_dict`）。
  - 已移除 `cells` 字段，响应统一为 `columns` + `rows` 结构。
- 分表说明：
  - standard/每日类：默认将数值回填到第一个数据列（索引 2）；若模板存在备注列则同步回填文本。
  - constant/常量类：按模板期别列定位列索引并回填。
  - coal_inventory/煤炭库存：保持宽表 `columns`+`rows` 行为，无需调整。
- 迁移指引：前端已改为消费 `columns`+`rows`；后端已移除 `cells`。

## 变更记录（2025-10-25）

- 本轮仅在前端添加全链路调试日志，后端接口与数据模型无改动。
- 排查目标：确认前端在 rows-only 模式下收到正确的 `/template` 与 `/query` 数据并正确渲染。

### 运维提示：Docker 启动失败（数据库 unhealthy）

- 现象：`phoenix_db` 报 `invalid magic number ...`、`could not locate a valid checkpoint record`，健康检查失败。
- 原因：数据库数据目录（绑定 `./db_data`）WAL/检查点损坏。
- 处理优先级：先尝试 `pg_resetwal -f "$PGDATA"` 修复 WAL；不行再备份并清空 `./db_data` 重新初始化。
## 前端调试输出合规说明（2025-10-25）

- 前端已清理所有调试输出（`console.*` 与 `alert(...)`）。
- 后端接口契约不变：`/template`、`/submit`、`/query` 返回 rows-only；附带 `request_id`、`attatch_time`（东八区毫秒）、`source` 元信息。
### 2025-10-27 PostgreSQL 视图规划说明（AI 辅助）
- 现有核心业务表：`daily_basic_data`、`constant_data`、`temperature_data`、`coal_inventory_data`。
- 建议在 `backend/sql/create_views.sql` 中集中维护视图定义，覆盖日常汇总、常量维度对照以及煤炭库存的分支口径。
- 后续生成视图后，可通过 Alembic/初始化脚本执行 `CREATE OR REPLACE VIEW`，供查询接口直接消费。
### 2025-10-27 运行时表达式求值服务（计划）
- 目标：以 `sum_basic_data` / `sum_gongre_branches_detail_data` 与现有基础表为数据源，按“字典样例.json”的表达式规则运行时计算审批表/展示表单元格，避免扩张二级视图。
- 建议位置：`backend/app/services/runtime_expression.py`
- 拟定函数（待确认）：
  - `render_spec(spec: dict, project_key: str, primary_key: dict, *, trace: bool=False) -> dict`
  - 功能：预取主表与常量表，构建指标缓存与常量缓存；按列口径（本期日/同期日/月/供暖期）求值，支持 `value_*()`、`sum_*()`、`*_diff_rate()` 以及项目名与 `c.<常量>` 引用。
- 安全与一致性：
  - 表达式使用受限求值器（白名单运算与函数），禁止任意 Python 代码执行；
  - 差异率定义为 `(biz-peer)/NULLIF(abs(peer),0)`，除零返回 `None`。
- 后续：待产品确认常量口径与差异口径后实现，并补充单元测试与 `_trace` 调试输出。
### 2025-10-27 运行时表达式求值服务（首版已实现）
- 位置：`backend/services/runtime_expression.py`
- 核心能力：
  - 列名→帧映射（本期日/同期日/本期月/同期月/本供暖期/同供暖期）
  - 物化视图/动态日期两条路径：
    - `context.biz_date == "regular"`（默认）：从 `sum_basic_data` 读取缓存值；
    - 指定日期（如 `"2025-10-27"`）：在 `daily_basic_data` 上参数化聚合，口径与视图一致；
  - 常量 period 映射：`25-26`（biz系）/`24-25`（peer系），来自常量表 `period`
  - 多常量别名预留：表达式 `a.常量名` → `CA("a","常量名")`，别名到表名在 `spec['查询数据源']['缩写']` 中声明；保留 `C("常量名")` 等价于 `CA("c", ...)`
  - 受限表达式求值：仅允许 `+ - * / ()` 和 `I("项目名")/C("常量名")/CA("别名","常量名")/value_*()/sum_*()`；不执行任意代码
  - 差异列与“全厂热效率”按百分比字符串返回，保留两位小数；除零显示 `"-"`
- 调试路由：
  - `POST /api/v1/projects/daily_report_25_26/runtime/spec/eval`
  - 请求体：
    ```json
    {
      "sheet_key": "BeiHai_co_generation_approval_Sheet",
      "project_key": "daily_report_25_26",
      "primary_key": {"company":"BeiHai"},
      "config": "configs/字典样例.json",
      "biz_date": "regular",
      "trace": false
    }
    ```
  - 返回 rows-only：`columns` + `rows`，`trace=true` 时附带 `debug._trace`
- 使用示例：
```python
from backend.services.runtime_expression import render_spec
import json

spec = json.load(open('configs/字典样例.json','r',encoding='utf-8'))['BeiHai_co_generation_approval_Sheet']
out = render_spec(
    spec=spec,
    project_key='daily_report_25_26',
    primary_key={'company':'BeiHai'},
    trace=True,
    context={'biz_date':'regular'}  # 或 {'biz_date':'2025-10-27'}
)
# out['数据'] 可直接用于 rows-only 渲染；out['_trace'] 可用于抽查验证
```
