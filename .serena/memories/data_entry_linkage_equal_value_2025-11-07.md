# 数据填报指标联动 2025-11-07
- 原因：基础指标表新增 `"指标联动"` 配置，需要前后端同步主子指标数值以避免入库后数据不一致。
- 变更：后端 `backend/api/v1/daily_report_25_26.py` 引入 `LINKAGE_DICT_KEYS` 与 `_apply_linkage_constraints`，模板/查询响应透传 `linkage_dict` 并在标准报表提交前同步联动行值；前端 `frontend/src/daily_report_25_26/pages/DataEntryView.vue` 构建 `linkageMap`，在模板加载与镜像查询后重建映射，`handleAfterEdit` 将最新输入广播至所有关联行，并随提交 payload 回传 `linkage_dict`。
- 注意：联动检测通过“计量单位”列定位可编辑区域，常量/煤炭库存模板未启用该逻辑；回滚时移除新增常量与辅助函数，同时恢复前端事件处理即可。