时间：2026-03-08
问题：月报查询页在 CORS 修复后，query-options 接口返回 500，页面初始化失败。

处理：
- 文件：backend/projects/monthly_data_show/api/workspace.py
- 函数：get_monthly_data_show_query_options
- 增加兜底降级逻辑：
  1) _refresh_indicator_runtime 异常不抛出
  2) 数据库查询异常时 row={} 返回空筛选项
  3) order_items_by_config 异常时回退 items_from_db
  4) _safe_read_ai_settings 异常时回退 {show_chat_bubble: true}

结果：
- 接口在异常场景下返回 200 + 空数据，不再 500 阻断前端页面。

验证：
- python -m py_compile backend/projects/monthly_data_show/api/workspace.py 通过。

文档同步：
- configs/progress.md
- frontend/README.md
- backend/README.md