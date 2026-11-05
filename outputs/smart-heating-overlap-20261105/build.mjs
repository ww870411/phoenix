import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

// 只读取当前代码配置，不请求上游接口，也不修改业务或实时数据。
const root = process.cwd();
const out = path.join(root, 'outputs/smart-heating-overlap-20261105');
const frontend = 'frontend/src/projects/daily_report_25_26/';
async function sourceModule(name) {
  const code = await fs.readFile(path.join(root, frontend, 'constants', name), 'utf8');
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const taxonomy = await sourceModule('smartHeatingTaxonomy.js');
const { OVERVIEW_GROUPS } = await sourceModule('smartHeatingOverview.js');
const { TAXONOMY_LIST, POINT_ALIAS_MAP, normalizePoint } = taxonomy;
const dcIds = { '北海电厂': 2, '香海电厂': 3 };
const szIds = { '北海#1首站': 2, '北海#2首站': 3, '北海水炉': 4, '香海首站': 5 };
const ywIds = { '华乐中心': 60, '北岗中心': 61, '双兴中心': 62, '香炉礁中心': 63, '兴工中心': 64, '春海中心': 65, '大纺中心': 66, '中山中心': 67, '东港中心': 68 };
function upstream(p) {
  if (p.level1 === '首站') return '/get_sz_data/' + szIds[p.level2];
  if (p.level1 === '电厂') return '/get_dc_data/' + dcIds[p.level2];
  return '/get_yw_data/' + ywIds[p.level2];
}
function dataArray(p) { return { '首站': 'sz_data', '电厂': 'dc_data', '一次网': 'yw_data' }[p.level1]; }
function fieldSummary(p) {
  if (p.level1 === '一次网') return 'f3供温℃；f5回温℃；f1供压MPa；f4回压MPa；f2流量m³/h；f222热流率GJ/h；温压差计算';
  return 'WENDU温度℃；YALI压力MPa；LIULIANG流量' + (p.level1 === '电厂' ? 't/h' : 'm³/h') + '；RELIANG热量GJ' + (p.level1 === '首站' ? '；FUHE负荷MW；PINLV频率Hz' : '');
}
const gkFields = 'WENDU温度℃；YALI压力MPa；LIULIANG流量t/h；RELIANG热量GJ';
const matches = OVERVIEW_GROUPS.flatMap((g, gi) => g.rows.map(p => ({
  ...p, group: g.title, rowId: `工况-${gi + 1}-${String(p.no).padStart(2, '0')}`,
  standard: normalizePoint(p.sourceName),
}))).map(p => ({ ...p, matched: p.standard.order <= 344 }));
const matched = matches.filter(p => p.matched);
if (matched.length !== 55 || new Set(matched.map(p => p.standard.order)).size !== 55) throw new Error('重合数量与前次核对不一致，需重新核实');
const matchByOrder = new Map(matched.map(p => [p.standard.order, p]));
const candidateId = order => '关联-' + String(order).padStart(3, '0');
function difference(p) {
  if (!p.matched) return '名称未匹配；不能据此认定为新增独立测点';
  if (p.standard.level1 === '首站') return '温压热字段同名；流量页面单位m³/h与t/h不同；热源另有负荷和频率';
  if (p.standard.level1 === '电厂') return '温压流热字段及页面单位同名同单位；同一物理测点与数值一致性仍待确认';
  return '字段结构不同；热源区分供回温压，工况仅单组温压；流量m³/h与t/h、热量GJ/h与GJ不同';
}
const mainHeaders = ['重合标记', '关联编号（非标准编码）', '标签页', '一级分类或展示分组', '二级分类', '标准序号或组内序号', '页面测点名称', '源名称或历史别名', '对应页测点名称', '上游采集接口（POST）', 'Phoenix数据路径', '指标字段与页面单位', '匹配依据或未匹配说明', '口径差异与待核实事项'];
const rows = [];
for (const p of TAXONOMY_LIST) {
  const m = matchByOrder.get(p.order);
  const aliases = Object.entries(POINT_ALIAS_MAP).filter(([, v]) => v === p.pointName).map(([k]) => k);
  rows.push([m ? '重合候选' : '未匹配工况页', m ? candidateId(p.order) : '', '热源信息', p.level1, p.level2, p.order, p.pointName, aliases.join('；'), m?.name || '', upstream(p), dataArray(p) + '[name→' + p.pointName + ']', fieldSummary(p), m ? (m.sourceName === p.pointName ? '源名称与标准名称完全一致' : '源名称经现有别名字典归一后匹配') : '工况82行中未匹配；不表示其他页面或上游无此点', m ? difference(m) : '本文件仅核对当前两页固定清单']);
}
for (const p of matches) rows.push([p.matched ? '重合候选' : '未匹配热源页', p.matched ? candidateId(p.standard.order) : '', '工况一览', p.group, '', p.no, p.name, p.sourceName, p.matched ? p.standard.pointName : '', '/gk_get_data/', 'gk_data.' + p.dictName + '[' + p.sourceName + ']', gkFields, p.matched ? (p.sourceName === p.standard.pointName ? '源名称与标准名称完全一致' : '源名称经现有别名字典归一后匹配') : '按源名称及现有别名字典未匹配344点标准清单', difference(p)]);

const pairHeaders = ['重合标记', '关联编号', '工况分组', '工况组内序号', '工况页面名称', '工况源名称', '热源标准序号', '热源一级分类', '热源二级分类', '热源标准名称', '热源上游接口（POST）', '工况上游接口（POST）', '工况字典', '匹配依据', '口径差异与待核实事项'];
const pairs = [...matches].sort((a,b) => Number(b.matched)-Number(a.matched)).map(p => [p.matched ? '重合候选' : '未匹配热源页', p.matched ? candidateId(p.standard.order) : '', p.group, p.no, p.name, p.sourceName, p.matched ? p.standard.order : null, p.matched ? p.standard.level1 : '', p.matched ? p.standard.level2 : '', p.matched ? p.standard.pointName : '', p.matched ? upstream(p.standard) : '', '/gk_get_data/', p.dictName, p.matched ? (p.sourceName === p.standard.pointName ? '名称完全一致' : '别名归一匹配') : '名称未匹配', difference(p)]);
const wb = Workbook.create();
function addTable(name, headers, data, widths) {
  const s = wb.worksheets.add(name);
  s.showGridLines = false;
  const range = s.getRangeByIndexes(0, 0, data.length + 1, headers.length);
  range.values = [headers, ...data];
  range.format.font = { name: 'Arial', size: 10, color: '#243247' };
  range.format.rowHeight = 58;
  range.format.verticalAlignment = 'center';
  range.format.wrapText = true;
  headers.forEach((_, i) => s.getRangeByIndexes(0, i, data.length + 1, 1).format.columnWidth = widths[i] || 25);
  const header = s.getRangeByIndexes(0, 0, 1, headers.length);
  header.format.fill = '#234566';
  header.format.font = { name: 'Arial', size: 10, bold: true, color: '#FFFFFF' };
  header.format.rowHeight = 42;
  header.format.horizontalAlignment = 'center';
  const table = s.tables.add(range, true, name === '测点清单' ? 'PointList' : 'OverlapPairs');
  table.showFilterButton = true;
  s.freezePanes.freezeRows(1);
  s.freezePanes.freezeColumns(3);
  s.getRangeByIndexes(1, 0, data.length, headers.length).conditionalFormats.addCustom('$A2="重合候选"', { fill: '#E5F2EC', font: { color: '#18513D' } });
  s.getRangeByIndexes(1, 0, data.length, 1).conditionalFormats.addCustom('$A2="未匹配热源页"', { fill: '#FFF0CF', font: { color: '#855400' } });
  return s;
}
const list = addTable('测点清单', mainHeaders, rows, [16, 19, 14, 24, 20, 14, 29, 30, 29, 25, 48, 60, 49, 62]);
list.tabColor = '#234566';
const pairSheet = addTable('重合对照', pairHeaders, pairs, [16, 17, 25, 14, 29, 31, 14, 15, 20, 31, 25, 24, 17, 23, 65]);
const audit = wb.worksheets.add('接口核查');
audit.showGridLines = false;
audit.getRange('A1:D24').format.font = { name: 'Arial', size: 10, color: '#243247' };
audit.getRange('A1:D24').format.verticalAlignment = 'center';
audit.getRange('A1:D24').format.wrapText = true;
audit.getRange('A1:D24').format.rowHeight = 48;
audit.getRange('A1:A24').format.columnWidth = 24;
audit.getRange('B1:B24').format.columnWidth = 61;
audit.getRange('C1:C24').format.columnWidth = 61;
audit.getRange('D1:D24').format.columnWidth = 63;
audit.getRange('A2').values = [['智慧供热测点重合与接口核查']];
audit.getRange('A2:D2').format.rowHeight = 28;
audit.getRange('A2').format.font = { name: 'Arial', size: 14, bold: true };
audit.getRange('A4:D4').values = [['核查项目', '热源信息', '工况一览', '结论或说明']];
audit.getRange('A4:D4').format.fill = '#234566';
audit.getRange('A4:D4').format.font = { name: 'Arial', size: 10, bold: true, color: '#FFFFFF' };
const endpoint = '/api/v1/projects/daily_report_25_26/smart-heating/';
const auditRows = [
 ['页面查询接口', 'GET ' + endpoint + 'latest', 'GET ' + endpoint + 'latest', '相同；fetchData统一查询，两个标签页读取同一响应的不同字段'],
 ['页面读取字段', 'sz_data[]；dc_data[]；yw_data[]', 'gk_data.<字典>.<源名称>', '结构不同；工况数据没有从热源数组现场重组'],
 ['上游采集接口', 'POST /get_sz_data/{id}；/get_dc_data/{id}；/get_yw_data/{id}', 'POST /gk_get_data/', '不同；当前配置默认内网基址为192.168.1.206:6688，实际地址由客户端配置决定'],
 ['采集请求参数', '首站sz_selected；一次网yw_selected；电厂无表单参数', '无表单参数', '均经fetch_intranet_post调用；各类ID见测点清单'],
 ['汇总推送接口', 'POST ' + endpoint + 'push', 'POST ' + endpoint + 'push', '相同；run_single_cycle各自采集后合并至同一推送载荷'],
 ['工况返回字典', '不适用：使用分类数组', 'dc_dict；sz_dict；yw_dict；yw2_dict；sh_dict', '保留源字典键；展示分组不等于源字典类别'],
 ['时效控制', '整体推流在线时效180秒', '整体在线且gk_collected_epoch独立有效180秒', '后端可在热源仍在线时隐藏过期gk_data，工况组件也校验独立时效'],
 ['名称处理', '采集端TYPO_CORRECTIONS及前端normalizePoint', '原始字典键保持不变；页面配置提供显示名', '本文件用工况sourceName经过现有POINT_ALIAS_MAP匹配热源标准名'],
 ['配置测点数', 344, 82, '426为两页展示清单行数；不能直接当成独立物理测点数'],
 ['名称匹配重合', 55, 55, '55对名称匹配；测点清单中对应110行标绿。关联编号只供本文件对照，非正式编码'],
 ['未匹配另一页', 289, 27, '名称未匹配不等于确定不重合；未使用模糊匹配推断物理身份'],
 ['数值及物理身份', '未逐点实测比对', '未逐点实测比对', '静态代码能确认接口关系；无法据此确认两个上游接口对应同一传感器、数据库记录或同期数值'],
 ['单位差异', '首站流量m³/h；电厂t/h；一次网m³/h，f222为GJ/h', '所有分组流量标t/h，RELIANG为GJ', '页面未做换算；尤其首站与一次网候选重合项需核实介质、单位和热量周期'],
 ['证据来源：页面', frontend + 'pages/SmartHeatingView.vue：fetchData、normalized*List', frontend + 'components/SmartHeatingOverview.vue：point、value、available', frontend + 'services/api.js：getSmartHeatingLatest'],
 ['证据来源：采集', 'backend/projects/daily_report_25_26/smart_heating_sync.py：run_single_cycle、DC_MAP/SZ_MAP/YW_MAP', 'backend_data/projects/daily_report_25_26/smart_heating_relay_win7.py：同样独立采集流程', 'backend/projects/daily_report_25_26/api/smart_heating.py：get_latest_smart_heating_data、_overview_is_online'],
 ['证据来源：测点', frontend + 'constants/smartHeatingTaxonomy.js', frontend + 'constants/smartHeatingOverview.js', '以当前工作区代码为准；未调用远端或上游接口，未导出实时值及认证信息'],
 ['核对日期与回滚', '2026-11-05', '本轮只新增本输出目录文件', '无业务代码修改，无迁移；回滚只需移除本轮新增输出文件'],
 ['标记说明', '绿色：名称匹配的重合候选；未匹配行保留原清单', '浅黄色：工况未匹配热源标准清单', '建议按关联编号筛选核对，再确认统一物理测点编码及指标口径'],
];
audit.getRangeByIndexes(4, 0, auditRows.length, 4).values = auditRows;
audit.getRange('A18:D21').format.rowHeight = 76;
wb.recalculate();
console.log((await wb.inspect({ kind: 'table', range: '重合对照!A1:J5', tableMaxRows: 5, tableMaxCols: 10, maxChars: 2200 })).ndjson);
const errors = await wb.inspect({ kind: 'match', searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!', options: { useRegex: true, maxResults: 10 }, maxChars: 600 });
console.log(errors.ndjson);
for (const [sheetName, range] of [['测点清单','A1:G7'], ['重合对照','A1:F7'], ['接口核查','A4:D10']]) {
  const blob = await wb.render({ sheetName, range, scale: 1.3, format: 'png' });
  await fs.writeFile(path.join(out, sheetName + '-preview.png'), new Uint8Array(await blob.arrayBuffer()));
}
const output = await SpreadsheetFile.exportXlsx(wb);
const target = path.join(out, '智慧供热测点清单_重合标注.xlsx');
await output.save(target);
console.log(JSON.stringify({ target, detailRows: rows.length, candidateRows: rows.filter(r=>r[0]==='重合候选').length, pairs: matched.length, unmatchedSource: 289, unmatchedOverview: 27 }));
