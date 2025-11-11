2025-11-22：在 backend_data/数据结构_基本指标表.json 推广数据填报校验。
- 将除 BeiHai_co_generation_Sheet/BeiHai_gas_boiler_Sheet/Coal_inventory_Sheet 之外的模板校验开关默认置为 true，同时保持 __global_settings__.校验总开关=false 方便全局停用。
- 为 BeiHai_water/XiangHai/JinZhou/BeiFang/JinPu/ZhuangHe 补充“全厂热效率” expression_range 规则，范围 0.5~0.95 且本期相对同期波动 ≤10%。
- 为含有“耗水量”的模板（含 YanJiuYuan_Sheet）新增“耗水量>0 且本期位于同期 50%~115%”组合规则；供热公司仅生效耗水量，供热分中心/煤炭库存仍无规则。
- 更新 backend/README.md、frontend/README.md 以及 configs/progress.md 记录来源与回滚路径。