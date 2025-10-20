我正在构建一个“在线数据填报平台”应用，以下内容我是的预想，实际操作中，请你辅助我完成开发工作，或许不会完全参照下面的流程/技术，但请你先了解情况。
整个程应用序在phoenix目录中,其中的backend目录为后端程序目录，frontend目录为前端程序目录，configs目录为一些基本的设定文件，还有一个待更新的logs.md日志文件。
你在读取和修改文件时，禁止使用cmd或者powershell/pwsh命令，必须使用apply_patch这类原生的工具进行读写。
每次对话后，都将对话内容及改动内容添加configs/progress.md中，并在backend与frontend各自目录下的README.md文件中更新程序的最新结构。
另外，很重要的一点是，因为我正在你的帮助下写代码，你要把你做的工作，以及某项功能在实现时，究竟是什么结构/模块/函数在起作用，它具体的实现流程是什么，产生了什么结果向我报告。

# 🦅 Phoenix Plan · 凤凰计划 概要说明书

---

## 一、项目概述

凤凰计划是供暖集团生产日报数字化工作的第二阶段工程，目标是构建一个统一的在线数据填报与展示平台，实现：

- 摆脱 Excel 表格互相引用、人工汇总的低效模式；
- 让各单位在线填报、自动校验、汇总入库；
- 自动生成多维度分析和趋势图，为决策提供科学依据。

该项目是早期“雏鸟计划（Nestling）”的升级版，核心理念：

> **“数据结构统一化、模板配置化、流程自动化。”**

---

## 二、整体结构与分层

```
phoenix/
├─ backend/      # FastAPI + SQLAlchemy
├─ frontend/     # Vue3 + RevoGrid
├─ configs/
│  └─ seeds/base_sheets.json   # 基础表模板（最小化 JSON）
├─ docs/
│  ├─ PHOENIX_OVERVIEW.md
│  ├─ API_SPEC.md
│  ├─ NAMING_GUIDE.md
│  └─ DATA_DICTIONARY.md
└─ docker-compose.yml
```

| 层级 | 技术栈 | 说明 |
|------|--------|------|
| **前端** | Vue3 + RevoGrid | 渲染表格模板、数据填报与提交 |
| **后端** | FastAPI + SQLAlchemy + PostgreSQL | 模板读取、数据接收、数据库写入与查询 |
| **数据库** | PostgreSQL | 统一存储所有表数据（Tall Table） |
| **容器化** | Docker + Compose | 启动 db / backend / frontend 三容器，数据库挂载持久化 |

---

## 三、核心设计原则

1. **后端单体、多项目共管**  
   - 仅一个后端服务；所有数据与接口均带 `project_key`。  
   - 当前项目代号：`daily_report_25_26`。

2. **表结构统一（Tall Table）**  
   - 所有日报行数据共用一张表 `entries`。  
   - 区分方式：`project_key`、`sheet_key`、`biz_date`。

3. **配置驱动（JSON 模板）**  
   - 表结构来自 `configs/seeds/base_sheets.json`。  
   - 前后端均依赖此文件，不得硬编码。

4. **接口最小化与标准化**  
   - 核心接口：`/template`、`/submit`、`/query`。  
   - 字段命名保持一致、接口稳定。

5. **人工可控、AI 辅助**  
   - 命名、接口、路径均手动管理。  
   - AI 工具仅实现逻辑，禁止更改规范部分。

---

## 四、核心数据结构

### 1️⃣ 模板文件：`base_sheets.json`

示例：
```json
{
  "BeiHai_co_generation_sheet": {
    "表名": "1.北海热电厂（热电联产）表",
    "列名": ["项目", "计量单位", "", ""],
    "数据": [
      ["发电量", "万kWh", "", ""],
      ["供热量", "GJ", "", ""],
      ["供汽量", "吨", "", ""]
    ]
  }
}
```

说明：
- `列名`：表头；
- `数据`：二维数组；
- 空单元格：预留填报位；
- 键名：表唯一标识（`sheet_key`）。

---

### 2️⃣ 数据库存储结构

**表名：** `entries`

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | SERIAL | 主键 |
| project_key | TEXT | 项目代号（如“daily_report_25_26”） |
| sheet_key | TEXT | 表键名（如“BeiHai_co_generation_sheet”） |
| sheet_name | TEXT | 表名（中文） |
| biz_date | DATE | 业务日期 |
| row_label | TEXT | 行项目（如“发电量”） |
| unit | TEXT | 计量单位 |
| col_index | INT | 列序号 |
| value_type | TEXT | `'num'` 或 `'text'` |
| value_num | FLOAT | 数值型数据 |
| value_text | TEXT | 文本型数据 |

**唯一约束：** `(project_key, sheet_key, biz_date, row_label, col_index)`  
**索引：** `(project_key, sheet_key, biz_date)`

---

## 五、接口规范

### 1️⃣ 获取模板
```
GET /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/template
```
**响应：**
```json
{
  "sheet_key": "BeiHai_co_generation_sheet",
  "sheet_name": "1.北海热电厂（热电联产）表",
  "columns": ["项目","计量单位","",""],
  "rows": [["发电量","万kWh","",""], ["供热量","GJ","",""]]
}
```

---

### 2️⃣ 提交数据
```
POST /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/submit
```
**请求体：**
```json
{
  "project_key": "daily_report_25_26",
  "sheet_key": "BeiHai_co_generation_sheet",
  "sheet_name": "1.北海热电厂（热电联产）表",
  "biz_date": "2025-11-15",
  "cells": [
    {"row_label": "发电量", "unit": "万kWh", "col_index": 2, "value_type": "num", "value_num": 123.4},
    {"row_label": "主设备启停情况", "col_index": 2, "value_type": "text", "value_text": "#3炉停"}
  ]
}
```
**响应：**
```json
{"ok": true}
```

---

### 3️⃣ 查询数据
```
POST /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/query
```
**请求体：**
```json
{"project_key":"daily_report_25_26","sheet_key":"BeiHai_co_generation_sheet","biz_date":"2025-11-15"}
```
**响应：**
```json
{
  "cells": [
    {"row_label":"发电量","unit":"万kWh","col_index":2,"value_type":"num","value_num":123.4}
  ]
}
```

---

## 六、前后端交互流程

1. 前端请求 `/template` → 渲染 RevoGrid 表格；  
2. 用户编辑单元格；  
3. 点击提交 → 前端构造 `cells[]` → 调用 `/submit`；  
4. 后端接收 JSON → 转 SQLAlchemy 对象 → 幂等写入数据库；  
5. 查询 `/query` → 返回已填数据 → 前端回填表格；  
6. 重复提交同单元格将覆盖旧值，不生成重复记录。

---

## 七、命名规范（统一跨端）

| 分类 | Python | TypeScript |
|------|---------|-------------|
| 普通变量 | `snake_case` | `camelCase` |
| 常量 | `UPPER_SNAKE` | 同上 |
| 类/类型名 | `PascalCase` | `PascalCase` |
| 接口字段 | 小写 + 下划线 | 保持一致 |
| 枚举值 | `'num'`, `'text'` | 同值一致 |

---

## 八、阶段路线图

| 阶段 | 内容 | 状态 |
|------|------|------|
| P1 | 目录与 Docker 环境 | ✅ 完成 |
| P2 | 数据库设计 | ✅ 完成 |
| P3 | FastAPI 后端骨架 | ⏳ 进行中 |
| P4 | 前端框架 + 登录页 | ⏳ 准备中 |
| P5 | 接入 RevoGrid 模板展示 | ⏳ 规划中 |
| P6 | 前后端联调（submit/query） | 🔜 目标阶段 |
| P7 | 仪表盘与分析扩展 | ⏳ 远期计划 |

---

## 九、AI 工具协作须知

1. **只实现逻辑，不改规范。**  
   - API、命名、字段、路径以本文件为准。

2. **允许修改的目录**
   ```
   backend/app/api/
   backend/app/models/
   backend/app/schemas/
   backend/app/services/
   frontend/src/daily_report_25_26/
   ```

3. **禁止修改的目录**
   ```
   configs/seeds/
   docs/
   docker-compose.yml
   frontend/src/api/
   ```

4. **命名必须一致。**  
   不得随意变更字段或路径，否则会导致前后端错位。

---

## 十、关键词速览

| 类别 | 内容 |
|------|------|
| 项目代号 | daily_report_25_26 |
| 后端框架 | FastAPI + SQLAlchemy |
| 前端框架 | Vue3 + RevoGrid |
| 数据库 | PostgreSQL |
| 表结构模式 | Tall Table (entries) |
| 唯一键 | project_key + sheet_key + biz_date + row_label + col_index |
| 主模板文件 | configs/seeds/base_sheets.json |
| 核心接口 | /template, /submit, /query |
| 管理方式 | 手动规范，AI 辅助开发 |

---

> 📌 **说明**  
> 本文件为凤凰计划统一开发说明书，所有 AI 工具和开发参与者必须遵守。  
> 改动接口、字段、命名规范前，需先更新本文件并经人工确认。

---
