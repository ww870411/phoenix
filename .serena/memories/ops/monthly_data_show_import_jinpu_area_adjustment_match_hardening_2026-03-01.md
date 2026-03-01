时间：2026-03-01
背景：用户反馈金普面积扣减规则已加但导出CSV仍为原值。
诊断：extract-csv链路确实调用extract_rows；问题更可能是规则命中条件过严（公司与指标名精确匹配）。
改动：
- 文件：backend/projects/monthly_data_show/services/extractor.py
- 函数：_apply_jinpu_heating_area_adjustment
  1) 公司匹配：company == 金普 -> "金普" in company
  2) 指标同义兼容：
     - 目标项：期末供暖收费面积/期末供热面积/期末供暖面积
     - 扣减项：高温水面积/高温水供暖面积/高温水供热面积
  3) 同窗口多目标行逐条扣减并统一单位为平方米。
- 同步留痕：configs/progress.md、backend/README.md、frontend/README.md。
结果：规则命中更稳健，提取导出CSV更可能体现扣减后结果。