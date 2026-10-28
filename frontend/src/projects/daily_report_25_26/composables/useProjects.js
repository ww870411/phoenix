import { ref } from 'vue';
import { listProjects as fetchProjects } from '../services/api';

const PROJECTS_STORAGE_KEY = 'phoenix_projects_cache';

function readInitialProjects() {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(PROJECTS_STORAGE_KEY) || sessionStorage.getItem(PROJECTS_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length) return parsed;
    }
  } catch (_) {}
  return [];
}

function writeCachedProjects(list) {
  if (typeof window === 'undefined') return;
  try {
    if (Array.isArray(list) && list.length) {
      localStorage.setItem(PROJECTS_STORAGE_KEY, JSON.stringify(list));
    }
  } catch (_) {}
}

export const projects = ref(readInitialProjects());
export const projectsLoading = ref(false);
export const projectsError = ref(null);

export function resetProjectsState() {
  projects.value = [];
  projectsLoading.value = false;
  projectsError.value = null;
  try {
    if (typeof window !== 'undefined') {
      localStorage.removeItem(PROJECTS_STORAGE_KEY);
    }
  } catch (_) {}
}

export async function ensureProjectsLoaded(force = false) {
  if (projectsLoading.value) return;
  if (!force && projects.value.length) return;
  projectsLoading.value = true;
  projectsError.value = null;
  try {
    const list = await fetchProjects(force);
    projects.value = Array.isArray(list) ? list : [];
    writeCachedProjects(projects.value);
  } catch (err) {
    projectsError.value = err;
    if (!projects.value.length) {
      projects.value = [];
    }
    throw err;
  } finally {
    projectsLoading.value = false;
  }
}

const KNOWN_PROJECT_NAMES = {
  daily_report_25_26: '2026-2027供暖期生产日报',
  daily_report_spring_festval_2026: '（春节期间）生产日报',
  monthly_data_pull: '月报拉取工作台',
  monthly_data_show: '月报导入与查询',
  insulation_pipe_supply_2026: '2026年度保温管、管件物流链管理系统',
  page_showcase: '页面展示',
};

export function getProjectNameById(projectId) {
  const match = projects.value.find(item => item?.project_id === projectId);
  return match?.project_name || KNOWN_PROJECT_NAMES[projectId] || projectId || '';
}
