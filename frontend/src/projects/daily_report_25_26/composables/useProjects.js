import { ref } from 'vue';
import { listProjects as fetchProjects } from '../services/api';

export const projects = ref([]);
export const projectsLoading = ref(false);
export const projectsError = ref(null);

export async function ensureProjectsLoaded(force = false) {
  if (projectsLoading.value) return;
  if (!force && projects.value.length) return;
  projectsLoading.value = true;
  projectsError.value = null;
  try {
    const list = await fetchProjects(force);
    projects.value = Array.isArray(list) ? list : [];
  } catch (err) {
    projectsError.value = err;
    projects.value = [];
    throw err;
  } finally {
    projectsLoading.value = false;
  }
}

export function getProjectNameById(projectId) {
  const match = projects.value.find(item => item?.project_id === projectId);
  return match?.project_name || projectId || '';
}
