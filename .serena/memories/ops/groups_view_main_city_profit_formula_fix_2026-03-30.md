时间：2026-03-30
主题：daily_report_25_26 展示页 groups 视图主城区利润口径修正
变更文件：backend/sql/groups.sql；configs/progress.md；frontend/README.md；backend/README.md。
背景：数据展示页 /pages/data_show/sheets 的全口径展示表对 Group/ZhuChengQu 走运行时路由到数据库视图 groups。原 groups 视图中，主城区 eco_marginal_profit / eco_comparable_marginal_profit 由 base_zc 直接透传，等于 BeiHai/XiangHai/GongRe 三个子单位利润结果求和；eco_direct_income 也按售电/暖/售高温水/售汽重算，遗漏内售热收入。
本次修正：
1. 主城区 passthrough 排除项新增 eco_marginal_profit、eco_comparable_marginal_profit。
2. 主城区 eco_direct_income 改为直接汇总子单位 eco_direct_income。
3. 主城区 eco_marginal_profit 改为按公式 直接收入 - 煤成本 - 外购电成本 - 购水成本 - 可计量辅材成本 重算。
4. 主城区 eco_comparable_marginal_profit 改为按公式 直接收入 - 可比煤成本 - 外购电成本 - 购水成本 - 可计量辅材成本 重算。
5. 可比煤成本使用主城区成员单位在 biz_period / peer_period 的 price_std_coal_comparable 常量求和，并与 consumption_std_coal 相乘后 /10000。
影响：展示页 groups 链路与数据分析页 analysis_groups_* 链路在主城区两个利润指标上的口径已对齐。
验证状态：已静态检查 SQL 片段插入位置与 UNION ALL 链完整；未执行数据库刷新或实库查询，需用户在数据库重建视图后验数。