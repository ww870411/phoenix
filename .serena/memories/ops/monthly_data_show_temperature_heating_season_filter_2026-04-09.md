时间：2026-04-09
主题：monthly_data_show 查询页气温指标仅在供暖期内返回

前置说明：
- Serena 项目激活与 onboarding 校验已完成。
- 本轮涉及 Python 源码与 Markdown 文本编辑；Python 逻辑定位使用 Serena，文件改动与文档同步按仓库规范降级使用 apply_patch。
- 降级范围：
  - backend/projects/monthly_data_show/api/workspace.py
  - configs/progress.md
  - frontend/README.md
  - backend/README.md
- 回滚思路：回退上述四个文件到本次修改前版本即可恢复旧气温查询行为。

需求：
- 气温数据只在每年 11 月 1 日至次年 4 月 5 日有效。
- 当用户在 monthly_data_show query-tool 中勾选气温类指标时，不应列出供暖期外的气温数据。

排查结论：
- 后端 workspace.py 中存在两类气温数据来源：
  1) 特殊生成项“平均气温”，直接从 calc_temperature_data 派生；
  2) monthly_data_show 表中的月报气温类指标（如“本月平均气温”“本月内最高气温”“本月内最低气温”）。
- 原逻辑未做供暖期过滤，因此夏季窗口下仍可能返回气温项，且“平均气温”会直接用窗口内全部日期参与平均。

处理：
- 新增常量与辅助函数：
  - _is_temperature_item_name
  - _is_heating_season_date
  - _iter_heating_season_segments
  - _extract_row_reference_date
  - _filter_temperature_rows_by_heating_season
  - _compute_average_temperature_value
- 主查询 query_month_data_show：
  - monthly_data_show 基础结果转成 base_rows_all 后，对所有气温类指标统一按供暖期过滤。
- 平均气温派生：
  - _build_average_temperature_rows 只对供暖期内有效日期求平均；若查询窗口与任何供暖期都不重叠，直接返回空。
- 对比逻辑：
  - _fetch_compare_map 中“平均气温”对比值改为仅按供暖期内日期计算。
  - _build_temperature_comparison_payload 的日序同比仅输出供暖期内日期，并据此计算平均值。
- 说明：本轮没有修改前端筛选项，也没有改接口协议，前端自然复用后端新规则。

验证：
- py_compile 编译 backend/projects/monthly_data_show/api/workspace.py 通过。
- frontend 目录执行 npm run build 通过。
- 直接调用 query_month_data_show(QueryRequest(date_from='2024-07-01', date_to='2024-07-31', items=['平均气温'], ...)) 返回 {'total': 0, 'rows': []}。

结果：
- 供暖期外的气温指标不会再出现在月报查询结果中。
- 夏季窗口下“平均气温”与气温同比明细均不再返回无效数据。