修复：审批模板选择主表=groups时无数据显示。
原因：backend/services/runtime_expression.py 固定从 sum_basic_data 取数，company=ZhuChengQu 在该视图中不存在，导致 metrics 缓存为空并返回空白。
改动：
- 新增 _fetch_metrics_from_view(session, table, company)，白名单支持 sum_basic_data|groups；根据模板 spec['查询数据源']['主表'] 切换视图。
- 替换原固定 _fetch_metrics_from_matview 调用。
注意：若数据库中 groups 视图未成功创建（10.29 提示词中出现 CTE 顺序错误），需先修复 SQL（create_view.sql）并执行，再验证该修复。
回滚：恢复为固定表名 sum_basic_data 查询即可。