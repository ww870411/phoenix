2025-10-29 示例数据与命名修正（记录）
- 背景：用户要求 daily_basic_data 本期较同期 +25%；constant_data 本期较同期 -20%；同时修复中心英文码 *_Center 与 sheet_name *_Sheet。 
- 变更：
  1) backend/scripts/generate_daily_basic_sample.py：
     - 新增 _normalize_sheet_name；修复 _normalize_center_code 为 *_Center；
     - build_records 改为以同期为基准，biz=peer*1.25；
     - 输出 sheet_name 使用 *_Sheet；SQL 头注释更新。
  2) backend/scripts/generate_constant_sample.py（新增）：
     - 从 backend_data/数据结构_常量指标表.json 读取（含“中心字典/项目字典”）；
     - 迭代标准表与分中心常量表；period 输出 '24-25' 与 '25-26'；biz=peer*0.8；
     - 统一 *_Center 与 *_Sheet；输出 CSV/SQL 到 backend/sql/。
- 影响：示例数据文件路径：sample_daily_basic_data.(csv|sql)、sample_constant_data.(csv|sql)；需要用户确认是否落盘生成大型 CSV/SQL。
- 回滚：恢复两脚本至变更前版本即可。