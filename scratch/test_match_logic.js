// 改进后的 matchSingleFittingItem
const FITTING_OD_TO_DN_MAP = {
  32: 25, 38: 32, 42: 32, 45: 40, 48: 40, 57: 50, 76: 65, 89: 80,
  108: 100, 114: 100, 133: 125, 140: 125, 159: 150, 168: 150,
  219: 200, 273: 250, 325: 300, 377: 350, 426: 400, 478: 450,
  529: 500, 630: 600, 720: 700, 820: 800, 920: 900, 1020: 1000
};

function cleanFittingSymbolString(str) {
  if (!str) return '';
  let s = String(str).trim();
  s = s.replace(/[\r\n\t]+/g, ' ');
  s = s.replace(/（/g, '(').replace(/）/g, ')').replace(/／/g, '/').replace(/、/g, '/').replace(/\\/g, '/').replace(/，/g, ',');
  s = s.replace(/[ΦφФф⌀]/g, 'DN');
  s = s.replace(/度|deg/gi, '°');
  s = s.replace(/[×xX\*]/g, '*');
  s = s.replace(/\s+/g, ' ');
  return s.trim();
}

function extractFittingDNA(fittingType, modelSpec) {
  const raw = `${fittingType || ''} ${modelSpec || ''}`;
  const s = cleanFittingSymbolString(raw);

  let family = null;
  if (/弯头|ELBOW/i.test(s)) family = '弯头';
  else if (/(?:排气|放气|疏水|放水|泄水)?(?:阀门|球阀|平衡阀|蝶阀|截止阀|阀)/i.test(s) && !/三通/i.test(s)) {
    if (/平衡阀/i.test(s)) family = '物联网平衡阀';
    else family = '球阀';
  }
  else if (/三通|跨越三通|直三通|分支|TEE|排气|放气|疏水|放水|泄水/i.test(s)) family = '三通';
  else if (/变径|异径|大小头|同心|偏心|REDUCER/i.test(s)) family = '变径管';
  else if (/封头|管帽|盲板|堵头|CAP/i.test(s)) family = '封头';
  else if (/弯管|BEND/i.test(s)) family = '弯管';
  else if (/补偿器|膨胀节|波纹/i.test(s)) family = '补偿器';
  else if (/固定节|固定支架|固定墩|ANCHOR/i.test(s)) family = '固定节';
  else if (/密封节/i.test(s)) family = '密封节';

  let angle = null;
  let sNoAngle = s;
  const mAngle = s.match(/(\d+(?:\.\d+)?)°/);
  if (mAngle) {
    angle = mAngle[1] + '°';
    sNoAngle = s.slice(0, mAngle.index) + ' ' + s.slice(mAngle.index + mAngle[0].length);
  }

  let radius = null;
  const mR = sNoAngle.match(/R\s*=\s*(\d+(?:\.\d+)?)\s*(?:DN|D)?/i);
  if (mR) {
    radius = `R=${mR[1]}DN`;
    sNoAngle = sNoAngle.slice(0, mR.index) + ' ' + sNoAngle.slice(mR.index + mR[0].length);
  }

  let dns = [];
  const pair = sNoAngle.match(/(?:DN)?\s*(\d+)\s*[\/\*\-]\s*(?:DN)?\s*(\d+)/i);
  if (pair) {
    const d1 = Number(pair[1]);
    const d2 = Number(pair[2]);
    const dn1 = FITTING_OD_TO_DN_MAP[d1] || d1;
    const dn2 = FITTING_OD_TO_DN_MAP[d2] || d2;
    dns = [String(dn1), String(dn2)];
  } else {
    const dnExplicit = Array.from(sNoAngle.matchAll(/DN\s*(\d+)/gi)).map(m => m[1]);
    if (dnExplicit.length) {
      dns = dnExplicit;
    } else {
      const nums = (sNoAngle.match(/\d+/g) || []).map(Number).filter(n => n >= 15);
      dns = nums.map(n => String(FITTING_OD_TO_DN_MAP[n] || n));
    }
  }

  return { family, angle, radius, dns };
}

function matchSingleFittingItem(rawFittingType, rawModelSpec, library) {
  const rawType = String(rawFittingType || '').trim();
  const rawSpec = String(rawModelSpec || '').trim();
  const cleanedRawSpec = cleanFittingSymbolString(rawSpec);
  const inputDNA = extractFittingDNA(rawType, rawSpec);

  // Pass 1: 品类族一致且规格型号完全吻合 (Strict Exact Match)
  const exactCandidates = [];
  for (const std of library) {
    const stdDNA = extractFittingDNA(`${std.category || ''} ${std.material_name || ''}`, std.model_spec);
    const stdSpecCleaned = cleanFittingSymbolString(std.model_spec);
    const specExact = (cleanedRawSpec.toLowerCase() === stdSpecCleaned.toLowerCase());
    const familyMatch = Boolean(
      (inputDNA.family && stdDNA.family && inputDNA.family === stdDNA.family) ||
      (!inputDNA.family && (std.category?.includes(rawType) || std.material_name?.includes(rawType)))
    );

    // 关键属性一致性检验：角度、弯曲半径、关键子品类
    const angleMatch = !inputDNA.angle || !stdDNA.angle || (inputDNA.angle === stdDNA.angle);
    const radiusMatch = !inputDNA.radius || !stdDNA.radius || (inputDNA.radius === stdDNA.radius);

    // 三通子品类校验：如“跨越三通” vs “直三通”
    let subtypeMatch = true;
    if (inputDNA.family === '三通') {
      const inputHasKuayue = /跨越/i.test(rawType);
      const stdHasKuayue = /跨越/i.test(`${std.category || ''} ${std.material_name || ''}`);
      if (inputHasKuayue !== stdHasKuayue) {
        subtypeMatch = false;
      }
    }

    if (specExact && familyMatch && angleMatch && radiusMatch && subtypeMatch) {
      exactCandidates.push(std);
    }
  }

  if (exactCandidates.length === 1) {
    return {
      match_type: 'exact',
      suggested_item: exactCandidates[0],
      candidates: exactCandidates,
      confidence: 1.0,
    };
  } else if (exactCandidates.length > 1) {
    return {
      match_type: 'candidates',
      suggested_item: exactCandidates[0],
      candidates: exactCandidates,
      confidence: 0.9,
    };
  }

  return { match_type: 'none', candidates: [] };
}

const mockLibrary = [
  { category: '弯头', material_name: '45°预制保温弯头', model_spec: 'DN50' },
  { category: '弯头', material_name: '90°预制保温弯头', model_spec: 'DN50' },
  { category: '三通', material_name: '预制保温直三通', model_spec: 'DN100/DN50' },
  { category: '三通', material_name: '预制保温跨越三通', model_spec: 'DN100/DN50' },
];

console.log("测试 1: 90°预制保温弯头 DN50 ->", matchSingleFittingItem("90°预制保温弯头", "DN50", mockLibrary));
console.log("测试 2: 预制保温弯头 DN50 (未指定角度) ->", matchSingleFittingItem("预制保温弯头", "DN50", mockLibrary));
console.log("测试 3: 45°预制保温弯头 DN50 ->", matchSingleFittingItem("45°预制保温弯头", "DN50", mockLibrary));
console.log("测试 4: 预制保温跨越三通 DN100/DN50 ->", matchSingleFittingItem("预制保温跨越三通", "DN100/DN50", mockLibrary));
console.log("测试 5: 预制保温直三通 DN100/DN50 ->", matchSingleFittingItem("预制保温直三通", "DN100/DN50", mockLibrary));
