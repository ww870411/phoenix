# AGENTS.md（Phoenix 当前协作规范）

最后更新：2026-03-04  
适用范围：本仓库根目录及全部子目录（如子目录存在更近的 AGENTS.md，则以子目录为准）

---

## 1. 文档目的

本文件用于约束 Codex/AI 协作行为，确保：

- 指令执行方式一致；
- 代码与文档留痕完整；
- 多项目并行开发时不混淆目录与接口口径；
- 输出内容可追踪、可复盘。

---

## 2. 必须保留的系统性要求（强制）

### 2.1 文件读写与改动方式

- 读取和修改文件时，不使用 `cmd` 或 `powershell/pwsh` 命令直接读写文件内容。
- 优先使用原生文件工具（如 `apply_patch`、MCP工具、结构化读写工具）完成编辑。
- 不使用临时 Python 脚本批量改写文件（除非明确授权且有必要）。

### 2.2 每轮对话后的文档同步（强制）

每次发生有效讨论或代码改动后，必须同步更新：

1. `configs/progress.md`（记录本轮结论与改动）  
2. `frontend/README.md`（同步前端结构/行为变化）  
3. `backend/README.md`（同步后端结构/行为变化）

### 2.3 结果说明方式（强制）

每次交付都要明确说明：

- 做了什么（具体文件与改动点）
- 是哪个结构/模块/函数在起作用
- 实现流程如何运行
- 产生了什么结果
- 若有风险或未完成项，必须显式标注

---

## 3. 当前项目现状（2026-03 版本）

本仓库已从“单项目日报”演进为“多项目模块并行”。

### 3.1 前端真实结构（核心）

- 根入口：`frontend/src/main.js`
- 全局页面：`frontend/src/pages/`
- 项目模块目录：`frontend/src/projects/`
  - `daily_report_25_26`
  - `daily_report_spring_festval_2026`
  - `monthly_data_pull`
  - `monthly_data_show`

### 3.2 后端真实结构（核心）

- 主入口：`backend/main.py`
- 全局 API：`backend/api/v1/`
- 项目模块目录：`backend/projects/`
  - `daily_report_25_26`
  - `daily_report_spring_festval_2026`
  - `monthly_data_pull`
  - `monthly_data_show`
- 核心服务：`backend/services/`
- 数据模型与数据库：`backend/db/`、`backend/sql/`

### 3.3 配置与运行数据

- 文档与过程记录：`configs/`
- 业务数据目录：`backend_data/`（按 shared/projects 组织）

---

## 4. 开发与改动范围规则

### 4.1 推荐可修改范围

- 后端：
  - `backend/api/`
  - `backend/projects/`
  - `backend/services/`
  - `backend/db/`
  - `backend/schemas/`
  - `backend/sql/`（仅在明确数据库变更时）
- 前端：
  - `frontend/src/projects/`
  - `frontend/src/pages/`（仅全局页面需求）
  - `frontend/src/router/`
- 文档：
  - `configs/progress.md`
  - `frontend/README.md`
  - `backend/README.md`
  - 本文件 `AGENTS.md`

### 4.2 禁止直接改动（除非用户明确要求）

- `configs/seeds/`（基础种子配置）
- `docs/`（历史文档归档区）
- `docker-compose.yml`（基础编排）
- 与当前任务无关的大范围重命名/重构

---

## 5. 接口与命名约束（持续有效）

- 接口字段命名保持跨端一致，不做随意改名。
- Python 使用 `snake_case`；TypeScript/JS 使用 `camelCase`；类型名 `PascalCase`。
- 涉及既有业务接口（如日报填报链路）时，优先兼容历史协议，再做增量演进。
- 任何破坏性接口变更，必须先在文档中写清迁移说明。

---

## 6. 当前协作风格要求（你的偏好）

- 沟通语言：中文。
- 风格：直接、清晰、务实，不写空话。
- 输出顺序：先结论，再证据/实现细节。
- 对排障类问题，明确区分：
  - 真错误（影响功能）
  - 可忽略告警（不影响主流程）
- 对不确定结论，必须标注不确定性来源与下一步验证动作。

---

## 7. 质量与安全底线

- 不执行破坏性命令（如 `rm -rf`、无确认的大规模删除/回滚）。
- 不泄露密钥、令牌、数据库密码等敏感信息。
- 变更应可回滚，必要时提供回滚点说明。
- 对数据库/恢复类操作，优先给“可验证”结论（例如：对象是否创建、关键表是否可查询）。

---

## 8. 快速执行清单（给 Codex）

每次任务默认按下列顺序执行：

1. 读取需求与相关文件  
2. 确认影响范围与真实目录  
3. 实施最小必要改动  
4. 给出“模块/函数/流程/结果”说明  
5. 同步更新 `progress.md` + 前后端 README  
6. 如有关键结论，写入知识留痕

---

## 9. 备注

- 本文件是“当前有效版本”，用于替换项目初期的单项目描述。
- 若未来新增项目模块，请优先更新本文件中的“3. 当前项目现状”与“4. 开发与改动范围规则”。

更新日期：2026年3月4日
