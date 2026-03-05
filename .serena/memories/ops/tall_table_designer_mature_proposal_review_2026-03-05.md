时间：2026-03-05
主题：长表设计器成熟方案评审（先方案，后实施）

用户诉求：
- 不接受最小化临时方案，要求完整成熟设计。
- 重点关注：单位填报范围、字段数据类型、前端自动计算关系、长表/交叉表复杂度差异。

现状核对证据：
1) backend_data/projects/daily_report_25_26/config 下存在多份“数据结构_*.json”，以单位维度和 regular/crosstab 类型组织。
2) backend/sql/create_tables.sql：
   - daily_basic_data 为长表结构（company/sheet_name/item/value/date 等）
   - 唯一索引：ux_daily_basic_unique(company, sheet_name, item, date)
3) backend/projects/daily_report_25_26/api/template_designer.py：
   - 当前模板模型核心为 template_key/template_name/table_type/columns/rows/meta
   - 尚无强语义的字段契约、计算图、校验图。

评审结论：
- 采用“存储统一长表，展示按需透视”的总原则。
- 设计器升级为三层：数据契约层 + 采集编排层 + 展示层。
- 优先落地长表设计器，不把交叉表结构直接绑定入库。

文档同步：
- configs/progress.md 新增“2026-03-05（长表设计器成熟方案评审稿）”
- frontend/README.md 新增“结构同步（2026-03-05 长表设计器方案评审）”
- backend/README.md 新增“结构同步（2026-03-05 长表设计器方案评审联动）”