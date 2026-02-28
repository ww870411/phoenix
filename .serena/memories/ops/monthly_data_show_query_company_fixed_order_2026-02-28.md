时间：2026-02-28
需求：整理口径与指标顺序；口径按固定次序展示。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) backend/projects/monthly_data_show/api/workspace.py
3) configs/progress.md
4) backend/README.md
5) frontend/README.md
实现：
- 前端新增 COMPANY_ORDER 固定顺序：全口径、主城区、集团本部、股份本部、北海、北海水炉、香海、供热公司、金州、北方、金普、庄河、研究院、主城区电锅炉。
- 口径列表按固定顺序展示，未覆盖项自动放末尾。
- 口径“全选”按固定顺序写入。
- 后端 query-options 将 items 顺序从字母序调整为 ORDER BY MIN(id)（首次出现顺序）。
结果：
- 查询页口径顺序符合用户指定；指标顺序更贴近入库数据结构。