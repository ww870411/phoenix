日期：2026-03-17
任务：按用户要求调整 monthly_data_show 抽取顺序，并移除金普面积特殊修正专用开关。

关键变更：
1. backend/projects/monthly_data_show/services/extractor.py
- extract_rows() 执行顺序调整为：
  - 原始抽取阶段：指标剔除 -> 指标重命名 -> 计量单位转换
  - 后处理阶段：常量注入 -> 半计算规则
- get_extraction_rule_options() 去掉“特殊修正”父项。
- _refresh_extraction_rules() 移除 enable_jinpu_heating_area_adjustment 相关读取。
- 删除 _apply_jinpu_heating_area_adjustment() 专用函数。
2. backend_data/projects/monthly_data_show/monthly_data_show_extraction_rules.json
- 删除顶层 enable_jinpu_heating_area_adjustment。
- 在 semi_calculated_rules 中新增普通规则：
  - 金普期末供暖收费面积扣减高温水面积
  - companies=[金普]
  - target_item=期末供暖收费面积
  - operation=subtract
  - sources=[期末供暖收费面积, 高温水面积]
3. 文档同步：
- configs/progress.md
- frontend/README.md
- backend/README.md

验证：
- JSON 解析通过
- python -m py_compile backend/projects/monthly_data_show/services/extractor.py backend/projects/monthly_data_show/api/workspace.py 通过
- frontend npm run build 通过

偏差与留痕：
- apply_patch 在当前环境再次失败，已按仓库允许的降级方案改用 Desktop Commander 结构化编辑。
- 降级范围仅限 extractor.py 与 monthly_data_show_extraction_rules.json 的必要改动。