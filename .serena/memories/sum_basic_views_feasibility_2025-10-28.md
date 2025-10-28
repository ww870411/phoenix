日期：2025-10-28
主题：将一级物化视图改为普通视图的可行性评估
范围：backend/sql/create_view.sql、backend/sql/create_tables.sql
结论：可行。sum_basic_data 与 sum_gongre_branches_detail_data 不依赖物化视图能力，改为普通视图可行；实时性提升，省去刷新；性能需依赖底表索引。
关键证据：
- 物化视图定义仅包含 current_date-1 锚点与窗口聚合；文件：backend/sql/create_view.sql（行 14、76）。
- 运行时代码中未发现 REFRESH MATERIALIZED VIEW 调用；相关命令仅在运维文档（configs/logs.md）与进展记录（configs/progress.md）中出现。
影响与差异：
- 一致性：快照→实时；
- 性能：失去视图索引，需依赖底表索引；建议新增 (company,item,date) 与分中心明细部分索引（见 progress.md）。
迁移建议：
- 先建 draft 普通视图对比；低峰期替换同名视图并移除刷新任务；观察性能，必要时加索引；保留回滚脚本以恢复物化视图。