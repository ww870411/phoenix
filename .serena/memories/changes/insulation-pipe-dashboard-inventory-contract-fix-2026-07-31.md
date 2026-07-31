# 保温管全局看板库存字段契约与异常展示修复

日期：2026-07-31（Asia/Hong_Kong）。

## 根因
汇总 API rows 将库存输出为 `section_1_inventory_qty`，而 DashboardView 的 KPI、透视表、导出和图表读取 `station_inventory_qty`；前端 `undefined || 0` 将契约异常伪装为库存 0。

## 修改
- `backend/projects/insulation_pipe_supply_2026/api/workspace.py`：汇总 rows 对外统一返回 `station_inventory_qty`，`metrics.totalInv` 从同一字段聚合。
- `frontend/src/projects/insulation_pipe_supply_2026/pages/DashboardView.vue`：新增汇总数据状态和错误消息；缺失 rows 或库存字段时显示错误与“—”；有效的业务零值仍显示 0；发货流水加载失败不覆盖已成功加载的汇总 KPI。
- 已同步 `configs/progress.md`、`frontend/README.md`、`backend/README.md`。

## 验证
- 运行中后端函数实测返回 `station_inventory_qty=10.0`、`metrics.totalInv=10.0`。
- `frontend` 执行 `npm run build` 通过。
- Serena 的后端静态诊断仍报告项目既有的缺少环境依赖和历史类型问题；本次变更未引入构建错误。

## 降级留痕
Serena 无法对 `.vue` 文件提供符号能力；原生 `apply_patch` 因 Windows 沙箱初始化错误失败，随后按项目允许路径使用 Desktop Commander 对 Vue 及强制同步文档做精确文本编辑。后端 Python 字段契约通过 Serena replace_in_files 完成。