const rawBase = typeof import.meta !== 'undefined' && import.meta.env
  ? import.meta.env.VITE_API_BASE ?? ''
  : '';
const API_BASE = rawBase ? rawBase.replace(/\/$/, '') : '';

export function resolveApiPath(path) {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return API_BASE ? `${API_BASE}${normalized}` : normalized;
}

const JSON_HEADERS = { 'Content-Type': 'application/json' };

function projectPath(projectKey) {
  return `/api/v1/projects/${encodeURIComponent(projectKey)}`;
}

let cachedProjects = null;

export async function listProjects(force = false) {
  if (!force && Array.isArray(cachedProjects)) {
    return cachedProjects;
  }
  const url = resolveApiPath('/api/v1/projects');
  const res = await fetch(url, { method: 'GET' });
  if (!res.ok) throw new Error(`获取项目列表失败: ${res.status}`);
  const data = await res.json();
  const list = Array.isArray(data?.projects) ? data.projects : Array.isArray(data) ? data : [];
  cachedProjects = list;
  return list;
}

export function clearProjectsCache() {
  cachedProjects = null;
}

export async function getTemplate(projectKey, sheetKey) {
  const url = resolveApiPath(
    `${projectPath(projectKey)}/sheets/${encodeURIComponent(sheetKey)}/template`,
  );
  const res = await fetch(url, { method: 'GET' });
  if (!res.ok) throw new Error(`获取模板失败: ${res.status}`);
  return res.json();
}

export async function listSheets(projectKey) {
  const url = resolveApiPath(`${projectPath(projectKey)}/sheets`);
  const res = await fetch(url, { method: 'GET' });
  if (!res.ok) throw new Error(`获取表清单失败: ${res.status}`);
  return res.json();
}

export async function submitData(payload) {
  const { project_key, sheet_key } = payload;
  const url = resolveApiPath(
    `${projectPath(project_key)}/sheets/${encodeURIComponent(sheet_key)}/submit`,
  );
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
  const url = resolveApiPath(
    `${projectPath(project_key)}/sheets/${encodeURIComponent(sheet_key)}/query`,
  );
  const res = await fetch(url, {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`查询失败: ${res.status}`);
  return res.json();
}
