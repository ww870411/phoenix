时间：2026-03-01
目标：将 monthly_data_show 指标顺序与计算公式由硬编码改为配置驱动，保持页面逻辑与功能不变。

新增文件：
1) backend_data/projects/monthly_data_show/indicator_config.json
- 定义 basic_items（含 category 占位）
- 定义 calculated_items（含 unit/formula）
- 公式占位格式：{{指标名}}，并支持 {{天数}}

2) backend/projects/monthly_data_show/services/indicator_config.py
- 加载与归一化配置
- 计算依赖提取
- 指标顺序合并（配置优先）
- 安全表达式求值（除零/异常兜底为 0）
- 生成前端 indicator_config 载荷

后端改造：
- backend/projects/monthly_data_show/api/workspace.py
  - 引入配置服务与运行时刷新 _refresh_indicator_runtime
  - query-options 返回 indicator_config，并按配置顺序输出 items
  - 计算指标执行由硬编码分支改为按配置公式 evaluate_formula
  - 保留两轮计算逻辑，支持计算指标依赖计算指标
- backend/projects/monthly_data_show/services/extractor.py
  - 跳过计算指标集合改为读配置，不再硬编码

前端改造：
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
  - loadOptions 接收 indicator_config 并驱动两块指标区域
  - 公式弹窗改为配置下发
  - 基本指标展示分类标签（当前占位）
  - 指标排序改为配置优先，未配置项后置

验证：
- 执行 python -m py_compile：workspace.py/extractor.py/indicator_config.py 均通过。

留痕：
- configs/progress.md 已追加本次变更记录
- frontend/README.md、backend/README.md、backend_data/projects/monthly_data_show/README.md 已同步结构说明。