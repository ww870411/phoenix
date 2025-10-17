// 前端项目内的最小 API 封装，仅依赖浏览器 fetch
// 与接口规范保持一致：/template, /submit, /query

const JSON_HEADERS = { 'Content-Type': 'application/json' };

export async function getTemplate(projectKey, sheetKey) {
  const url = `/api/v1/projects/${encodeURIComponent(projectKey)}/sheets/${encodeURIComponent(sheetKey)}/template`;
  const res = await fetch(url, { method: 'GET' });
  if (!res.ok) throw new Error(`获取模板失败: ${res.status}`);
  return res.json();
}

export async function submitData(payload) {
  const { project_key, sheet_key } = payload;
  const url = `/api/v1/projects/${encodeURIComponent(project_key)}/sheets/${encodeURIComponent(sheet_key)}/submit`;
  const res = await fetch(url, {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`提交失败: ${res.status}`);
  return res.json();
}

export async function queryData(payload) {
  const { project_key, sheet_key } = payload;
  const url = `/api/v1/projects/${encodeURIComponent(project_key)}/sheets/${encodeURIComponent(sheet_key)}/query`;
  const res = await fetch(url, {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`查询失败: ${res.status}`);
  return res.json();
}

