# 后端说明（FastAPI）

## 新增能力（2025-10-23）

- 新增接口 `GET /api/v1/projects/{project_id}/pages`，用于按项目返回页面与所属模板文件映射。
- 所有 `/data_entry/sheets` 相关接口新增可选查询参数 `config`，允许前端显式指定模板 JSON 文件；默认仍回落至基础指标表。
- 模板枚举逻辑会自动读取 `backend_data/项目列表.json` 中声明的所有模板文件，无需手工维护候选列表。

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
          - standard：`{ template_type:'standard', cells:[...] }`
          - crosstab（煤炭库存）：`{ template_type:'crosstab', columns:[...], rows:[...] }`
          - constants：同 standard，cells 形式回填第一个数据列。
      - 项目级聚合查询：`POST /api/v1/projects/{project_key}/query`
        - 入参：`sheet_keys[]`、`scope`（data_entry/display/constants）、`biz_date|date_range`、`mode`（cells/records/matrix）。
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
    - SQL 包含 `gongre_branches_detail_data`，对应 ORM 类 `GongreBranchesDetailData`（见 `db/database_daily_report_25_26.py`）。

## 查询接口（镜像查询）
- 单表查询（已实现）：`POST /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/query`
  - standard（每日）：`{ template_type:'standard', biz_date, cells:[...] }`
  - constants（常量）：`{ template_type:'standard', period, cells:[...] }`
  - crosstab（煤炭库存）：`{ template_type:'crosstab', biz_date, columns:[...], rows:[...] }`
- 聚合查询（规划中）：`POST /api/v1/projects/{project_key}/query`
  - 入参：`sheet_keys[]`、`scope`（data_entry/display/constants）、`biz_date|date_range`、`mode`（cells/records/matrix）。
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
  - `GongRe_branches_detail_Sheet`：专用分支解析中心/指标，写入 `gongre_branches_detail_data`，调试记录输出至 `configs/111.md`。
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
## 镜像查询（/query）实现要点（2025-10-24）

### 变更记录（2025-10-25）
- 本次问题定位为前端渲染流程回退判定缺失，后端接口与返回结构保持不变（仍为 template/submit/query 三端点）。
- 对于 `Coal_inventory_Sheet`，若模板未包含 `template_type`，前端将回退推断为 `'crosstab'` 以匹配交叉表渲染与镜像回填。

本节说明“基本指标表/常量指标表”的镜像查询（将已入库长表数据逆映射回模板坐标）。

- 入口函数：`backend/api/v1/daily_report_25_26.py:1554` `query_sheet`
- 模板类型识别：
  - 常量表：`_is_constant_sheet(name)`（`*_constant_sheet` 后缀）→ constant 分支
  - 标准/每日表：默认 standard 分支
  - 煤炭库存：通过 `_locate_sheet_payload` + `_is_coal_inventory_sheet` 识别 → crosstab 分支（非本节重点）

### 基本指标表（standard/daily）
- 入参：`biz_date`（必填），可选 `company`
- 查询：`DailyBasicData.sheet_name == sheet_key AND date == biz_date`
- 回填：对每条行记录，生成一个 `cells` 单元：
  - `row_label = rec.item_cn or rec.item`
  - `unit = rec.unit`
  - `col_index = 2`（第一个数据列，对应“本期日”）
  - `value_type = 'num'|'text'`，`value_num`/`value_text`
- 备注列：若模板存在“备注/说明/解释说明”等列，则追加一条 `text` 类型的 `cells`，其 `col_index` 为模板中该列的实际索引。

### 常量指标表（constant）
- 入参：可选 `period`（如“2025年供热期”），可选 `company`
- 模板解析：
  - 通过 `_locate_sheet_payload` 读取模板；
  - 收集 `columns` 与 `dicts`（`_collect_all_dicts`），若模板含 `center_dict`，期别从第 4 列开始，否则从第 3 列开始；
  - 提取期别序列 `periods = columns[start_idx:]`。
- 查询：`ConstantData.sheet_name == sheet_key`（若给定 `period`/`company` 则加筛选）
- 回填：
  - 对每条记录，使用其 `period` 在 `periods` 中定位偏移 `p_offset`，计算 `col_index = start_idx + p_offset`；
  - 生成 `cells[{row_label, unit, col_index, value_num|value_text}]`。

说明：镜像查询与提交持久化为“互逆”设计，即：`submit` 平铺入库的键（`sheet_name/item/unit/(date|period)/(company)`）在 `/query` 中用于重建模板坐标（`row_label/unit/col_index`）。
