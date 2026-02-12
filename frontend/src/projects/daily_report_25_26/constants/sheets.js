// 临时常量：待后端提供模板枚举接口后替换为动态获取
// 偏差说明：为满足仪表盘状态汇总需求，当前以常量维护可用表清单；
// 后续与后端联动后改为从后端获取（如 /api/v1/projects/{project_key}/data_entry/sheets 列表）。

export const SHEETS = [
  {
    sheet_key: 'BeiHai_co_generation_sheet',
    sheet_name: '1.北海热电厂（热电联产）表',
  },
  // 可在此扩展更多表配置
];
