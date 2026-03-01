时间：2026-03-01
需求：基本指标不再逐项挂分类标签，改为“分组标题 -> 指标列表”展示。

实现：
1) 配置文件升级
- 文件：backend_data/projects/monthly_data_show/indicator_config.json
- 新增 basic_groups 结构：
  [{ name: 分组名, items: [{name: 指标名}, ...] }, ...]
- 提供示例分组与占位分组，便于用户后续直接改配置。

2) 后端配置服务兼容升级
- 文件：backend/projects/monthly_data_show/services/indicator_config.py
- 新增 basic_groups 解析函数
- 解析顺序：basic_groups 优先；若缺失则回退 basic_items（向后兼容）
- query-options 下发 indicator_config 时包含 basic_groups

3) 前端渲染改造
- 文件：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- 基本指标区改为按分组渲染（组标题+组内复选指标）
- 去除每项 category 标签展示
- 若存在未被分组覆盖的项，自动放入“未分组”

验证：
- python -m py_compile 已通过（indicator_config/workspace/extractor）。

留痕：
- configs/progress.md、frontend/README.md、backend/README.md、backend_data/.../README.md 已更新。