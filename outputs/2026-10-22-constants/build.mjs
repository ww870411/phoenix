import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const out = path.dirname(fileURLToPath(import.meta.url));
const deps = 'C:/Users/ww/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
try { await fs.symlink(deps, path.join(out,'node_modules'),'junction'); } catch(e) { if(e.code!=='EEXIST') throw e; }
const {Workbook, SpreadsheetFile}=await import('@oai/artifact-tool');
const root='D:/编程项目/phoenix';
const constants=JSON.parse(await fs.readFile(path.join(out,'source_constants.json'),'utf8'));
const config=JSON.parse(await fs.readFile(root+'/backend_data/projects/daily_report_25_26/config/数据结构_常量指标表.json','utf8'));
const daily=JSON.parse(await fs.readFile(root+'/backend_data/projects/daily_report_25_26/config/数据结构_基本指标表.json','utf8'));
const book=Workbook.create();
const main=book.worksheets.add('单位常量搜集');
const centers=book.worksheets.add('供热分中心搜集');
const notes=book.worksheets.add('填报口径说明');
const purpose={amount_whole_heating_area:'规模展示；不直接进入利润',amount_heating_fee_area:'煤、热、电、水单耗及万㎡投诉量的分母',eco_season_heating_income:'整季暖收入总额；按有效天数分摊',price_power_sales:'售电量×单价，计算售电收入',price_inner_heat_sales:'供热量×单价，计算内部售热收入',price_std_coal:'标煤耗量×单价，计算煤成本',price_std_coal_comparable:'计算可比煤价边际利润',price_purchased_power:'外购电量×单价，计算购电成本',price_purchased_water:'耗水量×单价，计算购水成本',price_natural_gas:'天然气耗量×单价，计算天然气成本',price_inner_purchased_heat:'管网接口热量×单价，计算内购热成本',price_outer_purchased_heat:'外购热量×单价，计算外购热成本',price_hot_water_sales:'高温水销量×单价，计算销售收入',price_steam_sales:'售汽量×单价，计算售汽收入',rate_sharing_ratio:'分中心成本分摊参数，按既有比例口径确认'};
const pair={price_power_sales:'amount_power_sales',price_inner_heat_sales:'amount_heat_supply',price_std_coal:'consumption_std_coal',price_std_coal_comparable:'consumption_std_coal',price_purchased_power:'consumption_purchased_power',price_purchased_water:'consumption_water',price_natural_gas:'consumption_natural_gas',price_inner_purchased_heat:'amount_network_interface_heat_supply',price_outer_purchased_heat:'consumption_outer_purchased_heat',price_hot_water_sales:'amount_hot_water_sales',price_steam_sales:'amount_steam_sales',price_acid:'consumption_acid',price_alkali:'consumption_alkali',price_oil:'consumption_oil',price_n_ammonia_water:'consumption_ammonia_water',price_limestone:'consumption_limestone',price_limestone_powder:'consumption_limestone_powder',price_magnesium_oxide:'consumption_magnesium_oxide',price_denitration_agent:'consumption_denitration_agent'};
const inverse=o=>Object.fromEntries(Object.entries(o||{}).map(([k,v])=>[v,k]));
const dailyKeys={};
for(const p of Object.values(daily)){
 if(!p||!p['单位标识'])continue;
 const inv=inverse(p['项目字典']);
 dailyKeys[p['单位标识']]??=new Set();
 for(const r of p['数据']||[])if(inv[r[0]])dailyKeys[p['单位标识']].add(inv[r[0]]);
}
function lookup(company,item,sheet,center){
 const list=constants.filter(r=>r.period==='25-26'&&r.item===item&&(center?(r.company===center||(r.company===company&&r.center===center)):r.company===company));
 const exact=list.filter(r=>r.sheet_name===sheet); const chosen=exact.length?exact:list;
 if(chosen.length>1)throw new Error('上期常量存在重复，需人工核对：'+company+item+center);
 return chosen[0];
}
const all=[];const branch=[];
for(const [sheet,p] of Object.entries(config)){
 if(!p||!Array.isArray(p['数据']))continue;
 const company=p['单位标识'],inv=inverse(p['项目字典']);
 const isCenter=!!p['中心字典'];const cinv=inverse(p['中心字典']);
 const list=[...p['数据']];
 // 补上每日表有耗量但常量表仅有字典、没有录入行的参数。
 if(!isCenter) for(const [item,label] of Object.entries(p['项目字典']||{})){
  if(!list.some(r=>r[0]===label)&&pair[item]&&dailyKeys[company]?.has(pair[item])&&!(company==='GongRe'&&['price_hot_water_sales','price_steam_sales'].includes(item))){
   list.push([label,item==='price_natural_gas'?'元/m³':item.includes('power')?'元/kWh':'元/GJ','','']);
  }
 }
 for(const row of list){
  const item=inv[row[0]];if(!item)throw new Error('指标字典缺少'+row[0]);
  const center=isCenter?cinv[row[1]]:null;
  const rawUnit=row[isCenter?2:1];const unit=item==='price_purchased_power'?'元/kWh':rawUnit;
  const src=lookup(company,item,sheet,center);
  const value=src?.value===null||!src?null:Number(src.value);
  let state=!src?'无记录':src.value===null?'原值为空':value===0?'已填0':'已填数值';
  let req=item.startsWith('price_')?'有业务时填写':'需要搜集';
  if(['price_purchased_power','price_purchased_water','price_inner_heat_sales','price_inner_purchased_heat'].includes(item))req='需要搜集';
  if(['price_std_coal','price_std_coal_comparable'].includes(item)&&['BeiHai','XiangHai','JinZhou','BeiFang','JinPu'].includes(company))req='需要搜集';
  const remarks=[];
  if(item==='price_purchased_power'&&rawUnit!=='元/kWh')remarks.push('原模板/历史单位误标元/吨，本表改为元/kWh，数值未改');
  if(item==='price_natural_gas')remarks.push('按元/m³搜集，录入前核对耗量单位与成本换算');
  if(item==='price_std_coal_comparable')remarks.push('本期、同期需使用一致基准才能实现同价比较');
  if(!isCenter&&pair[item]&&!dailyKeys[company]?.has(pair[item])){req='按实际业务确认';remarks.push('每日表未列对应耗量/销量，先确认本期是否启用');}
  if(company==='ZhuangHe'&&['price_std_coal','price_std_coal_comparable','price_acid','price_alkali','price_oil','price_n_ammonia_water','price_limestone','price_limestone_powder','price_magnesium_oxide','price_denitration_agent'].includes(item)){
   req='本期不适用';remarks.push('26–27全外购热运行；保留上期参考，不沿用旧燃煤参数');
  }
  if(company==='ZhuangHe'&&item==='price_outer_purchased_heat')req='需要搜集';
  if(item==='rate_sharing_ratio'){req='需确认口径';remarks.push('上期若空值则保持空白，不按0代填');}
  if(!isCenter&&!p['数据'].some(r=>r[0]===row[0]))remarks.push('参数已接入计算，但当前常量表缺少录入行');
  const use=purpose[item]||'辅材耗量×单价，计入可计量辅材成本';
  (isCenter?branch:all).push({company,center,item,value,unit,state,req,label:row[0],name:isCenter?row[1]:p['单位名'],use,remark:remarks.join('；'),sourceId:src?.id??null});
 }
}
// 校验上期所有常量都有对应搜集项，不因模板遗漏丢失历史数据。
const used=new Set([...all,...branch].map(r=>r.sourceId).filter(x=>x!==null));
const unmatched=constants.filter(r=>!used.has(r.id));
if(unmatched.length)throw new Error('历史常量未被覆盖：'+JSON.stringify(unmatched));
function setup(sheet,title,subtitle,rows,tableName){
 const n=rows.length+6;
 sheet.showGridLines=false;sheet.tabColor='#254B70';
 sheet.getRange(`A1:J${n}`).format.font={name:'Arial',size:11,color:'#24364B'};
 sheet.getRange(`A1:J${n}`).format.verticalAlignment='center';
 sheet.getRange('A2').values=[[title]];sheet.getRange('A2').format.font={name:'Arial',size:16,bold:true,color:'#173654'};
 sheet.getRange('A3').values=[[subtitle]];
 sheet.getRange('A4').values=[['黄色栏填写本期数值；灰色为上期参考。0与未填分别记录，变动额仅在两期均为数值时计算。']];
 sheet.getRange('A3:J4').format.font={name:'Arial',size:10,color:'#5C6674'};
 const headers=['单位/中心','常量指标','计量单位','25–26参考值','26–27填报值','较上期变动额','搜集要求','计算用途','上期数据状态','确认事项及备注'];
 sheet.getRange('A6:J6').values=[headers];
 sheet.getRange(`A7:J${n}`).values=rows.map(r=>[r.name,r.label,r.unit,r.value,null,null,r.req,r.use,r.state,r.remark]);
 sheet.getRange(`F7:F${n}`).formulas=rows.map((_,i)=>[`=IF(AND(ISNUMBER(E${i+7}),ISNUMBER(D${i+7})),E${i+7}-D${i+7},"")`]);
 sheet.getRange(`D7:F${n}`).setNumberFormat('#,##0.####;-#,##0.####;0');
 sheet.getRange(`D7:D${n}`).format.fill='#EDF1F5';
 sheet.getRange(`E7:E${n}`).format.fill='#FFF2CC';
 sheet.getRange(`E7:E${n}`).format.font={name:'Arial',size:11,color:'#1D4ED8'};
 sheet.getRange(`A7:J${n}`).format.rowHeight=36;
 sheet.getRange(`B7:C${n}`).format.wrapText=true;
 sheet.getRange(`G7:J${n}`).format.wrapText=true;
 sheet.getRange(`H7:J${n}`).format.font={name:'Arial',size:10,color:'#475569'};
 const widths=[18,23,13,19,19,19,22,46,18,75];
 widths.forEach((w,i)=>sheet.getRange(`${String.fromCharCode(65+i)}1:${String.fromCharCode(65+i)}${n}`).format.columnWidth=w);
 const table=sheet.tables.add(`A6:J${n}`,true,tableName);table.showBandedRows=false;
 sheet.getRange('A6:J6').format={fill:'#254B70',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:32,horizontalAlignment:'center',verticalAlignment:'center'};
 sheet.getRange('A6:J6').format.borders={insideVertical:{style:'thin',color:'#FFFFFF'}};
 sheet.freezePanes.freezeRows(6);sheet.freezePanes.freezeColumns(2);
 sheet.getRange(`G7:G${n}`).conditionalFormats.add('containsText',{text:'不适用',format:{fill:'#E5E7EB',font:{color:'#6B7280'}}});
 sheet.getRange(`I7:I${n}`).conditionalFormats.add('containsText',{text:'无记录',format:{fill:'#FFF0D8',font:{color:'#9A5700'}}});
 sheet.getRange(`I7:I${n}`).conditionalFormats.add('containsText',{text:'为空',format:{fill:'#FFF0D8',font:{color:'#9A5700'}}});
 for(let i=0;i<rows.length;i++)if(rows[i].item==='rate_sharing_ratio')sheet.getRange(`J${i+7}`).values=[['按百分数数值填写，如25表示25%；'+rows[i].remark]];
 return n;
}
const n=setup(main,'26–27供暖期常量指标搜集表','8个单位；25–26上期参考；本期填报栏留空',all,'UnitConstants');
const nc=setup(centers,'供热公司分中心常量搜集表','10个分中心；按中心逐项搜集，不与公司合计重复汇总',branch,'CenterConstants');
const guidance=[
 ['事项','填报与比较口径'],
 ['数据来源','上期参考读取本机生产日报数据库常量表25–26期；指标清单依据当前常量填报模板，并补充每日表已引用但缺少录入行的参数。'],
 ['提取日期','2026-10-22。上期为2025–2026供暖期，本期为2026–2027供暖期。'],
 ['范围',`8个单位${all.length}项，10个分中心${branch.length}项。主城区、集团由成员单位汇总，无需另搜集团或主城区单价。北海热电联产与水炉共用北海常量。`],
 ['填写方法','在黄色26–27填报值栏输入数值；确认事项及备注可记录不适用原因、价格来源、税价口径或联系人。未发生业务请明确填0或注明不适用，勿把未填当作确认的0。'],
 ['缺失值','25–26无记录或原值为空时，参考值保持空白；已填0保留数值0。系统计算可能默认按0，但本搜集表保留真实缺失状态。'],
 ['价格口径','先确认各单位价格是否含税、是否含运杂费及适用范围。数据库未提供这些业务定义，本表不推定为含税价或不含税价。'],
 ['电价单位','单位常量表和部分历史记录把外购电单价标为元/吨；按实际电价统一显示元/kWh，历史数值保持原值。现货电价不会自动替代该常量。'],
 ['天然气','按元/m³搜集购气单价；正式录入前核对每日耗量的单位以及成本换算。没有购气业务时确认不适用。'],
 ['可比煤价','需统一确认本期、同期可比标煤基准；代码分别读取各期参数，不会自动保证相等。'],
 ['暖收入','采暖期供暖收入填整季总额，单位万元；系统按各期统计起止日的总天数等额分摊，不填日收入。'],
 ['面积','挂网面积与供暖收费面积均以万㎡填报。收费面积用于单耗等分母，挂网面积主要用于规模展示。'],
 ['庄河26–27','已按全外购热运行标注煤价及燃煤辅材为本期不适用；重点搜集面积、暖收入、外购热单价、水价、电价。上期煤价和辅材保留作历史参考。'],
 ['供热公司收入','售高温水和售汽收入直接取每日填报金额，未将仅字典中存在的两种销售单价列为必填常量。'],
 ['分中心参数','分中心共7类参数。公司合计与中心明细独立确认，不直接相加；分摊比上期空白继续标为缺失，需明确百分数填报口径。'],
 ['业务变化','模板保留而每日表无对应耗量/销量的价格标为按实际业务确认；本期是否新增或停用业务由单位确认。'],
 ['数据库操作','本表仅供搜集及对比，不写回数据库，不自动继承上期值到本期。'],
];
notes.showGridLines=false;notes.tabColor='#8595A5';
notes.getRange('A2').values=[['常量搜集与参考口径']];notes.getRange('A2').format.font={name:'Arial',size:16,bold:true,color:'#173654'};
notes.getRange(`A5:B${guidance.length+4}`).values=guidance;
notes.getRange(`A5:B${guidance.length+4}`).format.font={name:'Arial',size:11,color:'#24364B'};
notes.getRange(`A5:B${guidance.length+4}`).format.verticalAlignment='center';
notes.getRange(`A5:B${guidance.length+4}`).format.rowHeight=55;
notes.getRange(`B5:B${guidance.length+4}`).format.wrapText=true;
notes.getRange('A1:A22').format.columnWidth=22;notes.getRange('B1:B22').format.columnWidth=112;
notes.getRange('A5:B5').format={fill:'#254B70',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:28};
book.recalculate();
// 验证可编辑栏不会把零值当作空白，并恢复所有测试输入。
const z=all.findIndex(r=>r.value===0)+7;
if(z<7)throw new Error('缺少零值测试样本');
main.getRange(`E${z}`).values=[[0]];book.recalculate();
console.log('zero-check',z,JSON.stringify(main.getRange(`D${z}:F${z}`).values));
if(main.getRange(`F${z}`).values[0][0]!==0)throw new Error('零值变动额错误');
main.getRange(`E${z}`).values=[[null]];book.recalculate();
console.log((await book.inspect({kind:'table',range:'单位常量搜集!A6:I11',include:'values,formulas',tableMaxRows:6,tableMaxCols:9,maxChars:1800})).ndjson);
console.log((await book.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:10},maxChars:1000})).ndjson);
for(const [sheet,range,name] of [[main,'A1:I15','units'],[centers,'A1:I14','centers'],[notes,'A1:B13','notes']]){
 const img=await book.render({sheetName:sheet.name,range,scale:1.5,format:'png'});
 await fs.writeFile(path.join(out,name+'.png'),new Uint8Array(await img.arrayBuffer()));
}
const target=path.join(out,'26-27供暖期常量指标搜集表（含25-26参考）.xlsx');
await (await SpreadsheetFile.exportXlsx(book)).save(target);
await fs.writeFile(path.join(out,'manifest.json'),JSON.stringify({rows:all.length,centers:branch.length,sourceRecords:constants.length,missing:[...all,...branch].filter(r=>r.value===null).length,sheets:[main.name,centers.name,notes.name],target},null,2));
console.log(JSON.stringify({target,unitRows:all.length,centerRows:branch.length,sourceRecords:constants.length}));
