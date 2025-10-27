实施摘要（完成）
- 时间：2025-10-27
- 目标：将 “6.供热公司分中心明细表” 统一读写 daily_basic_data；删除专用 ORM；视图改为基于 daily_basic_data。
- 代码变更：
  1) backend/api/v1/daily_report_25_26.py
     - 移除 GongreBranchesDetailData 引用
     - handle_gongre_branches_detail_submission：解析后将 center→company，调用 _persist_daily_basic 落库
     - query_sheet(gongre 分支)：改为查询 DailyBasicData（sheet_name=GongRe_branches_detail_Sheet），以 (item[_cn], company[_cn]) 匹配行
  2) backend/db/database_daily_report_25_26.py
     - 删除 ORM 类 GongreBranchesDetailData
  3) backend/sql/create_tables.sql
     - 删除 gongre_branches_detail_data 建表与索引
  4) backend/sql/create_view.sql & create_view copy.sql
     - sum_gongre_branches_detail_data 视图：改为 FROM daily_basic_data + sheet_name 过滤；输出列以别名 center/center_cn 保持兼容
  5) backend/README.md
     - 更新提交流程与 SQL 说明；删除专表提法
- 验证建议：
  - 前端不变。以页面提交一次供热分中心数据；再用相同 biz_date 执行查询，确认 rows 回填正确；
  - 数据库校验：daily_basic_data 中 company=中心英文名、sheet_name='GongRe_branches_detail_Sheet' 是否写入；
  - 视图校验：刷新/重建物化视图后（如有），检查 sum_gongre_branches_detail_data 是否按 center 汇总。