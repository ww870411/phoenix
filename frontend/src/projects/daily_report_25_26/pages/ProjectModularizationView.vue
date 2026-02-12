<template>
  <div>
    <AppHeader />
    <main class="container modularization-view">
      <Breadcrumbs :items="breadcrumbItems" />
      <section class="card elevated">
        <header class="card-header">
          <h2>项目模块化管理</h2>
          <p class="sub">项目：{{ projectName }}</p>
        </header>
        <div v-if="!isSystemAdmin" class="placeholder error">
          当前账号不是系统管理员，无法访问该页面。
        </div>
        <template v-else>
          <div class="actions">
            <button class="btn" type="button" :disabled="loading" @click="loadStatus">
              {{ loading ? '刷新中…' : '刷新状态' }}
            </button>
            <button class="btn primary" type="button" :disabled="working" @click="runBootstrap">
              {{ working ? '初始化中…' : '执行初始化（仅复制缺失文件）' }}
            </button>
          </div>
          <div v-if="message" class="tips">{{ message }}</div>
          <div v-if="error" class="placeholder error">{{ error }}</div>
          <div v-else-if="loading && !status" class="placeholder">加载中…</div>
          <template v-else-if="status">
            <section class="block">
              <h3>目录信息</h3>
              <ul class="path-list">
                <li><strong>project_root：</strong>{{ status.dirs?.project_root || '—' }}</li>
                <li><strong>config_dir：</strong>{{ status.dirs?.config_dir || '—' }}</li>
                <li><strong>runtime_dir：</strong>{{ status.dirs?.runtime_dir || '—' }}</li>
              </ul>
            </section>
            <section class="block">
              <h3>配置文件状态</h3>
              <table class="status-table">
                <thead>
                  <tr>
                    <th>文件</th>
                    <th>项目目录</th>
                    <th>旧路径</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in configRows" :key="`config-${row.name}`">
                    <td>{{ row.name }}</td>
                    <td>{{ row.projectExists ? '已存在' : '缺失' }}</td>
                    <td>{{ row.legacyExists ? '存在' : '缺失' }}</td>
                  </tr>
                </tbody>
              </table>
            </section>
            <section class="block">
              <h3>运行时文件状态</h3>
              <table class="status-table">
                <thead>
                  <tr>
                    <th>文件</th>
                    <th>项目目录</th>
                    <th>旧路径</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in runtimeRows" :key="`runtime-${row.name}`">
                    <td>{{ row.name }}</td>
                    <td>{{ row.projectExists ? '已存在' : '缺失' }}</td>
                    <td>{{ row.legacyExists ? '存在' : '缺失' }}</td>
                  </tr>
                </tbody>
              </table>
            </section>
          </template>
        </template>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import {
  bootstrapProjectModularization,
  getProjectModularizationStatus,
} from '../services/api'
import { ensureProjectsLoaded, getProjectNameById } from '../composables/useProjects'
import { useAuthStore } from '../store/auth'

const route = useRoute()
const auth = useAuthStore()
const projectKey = String(route.params.projectKey ?? '')

const loading = ref(false)
const working = ref(false)
const error = ref('')
const message = ref('')
const status = ref(null)

const isSystemAdmin = computed(() => {
  const group = String(auth.user?.group || '').trim()
  return group === '系统管理员' || group === 'Global_admin'
})

const projectName = computed(() => getProjectNameById(projectKey) ?? projectKey)

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: projectName.value, to: `/projects/${encodeURIComponent(projectKey)}/pages` },
  { label: '项目模块化管理', to: null },
])

const configRows = computed(() => mapStatusRows(status.value?.config_files))
const runtimeRows = computed(() => mapStatusRows(status.value?.runtime_files))

function mapStatusRows(source) {
  if (!source || typeof source !== 'object') return []
  return Object.entries(source).map(([name, detail]) => ({
    name,
    projectExists: Boolean(detail?.project_exists),
    legacyExists: Boolean(detail?.legacy_exists),
  }))
}

async function loadStatus() {
  if (!isSystemAdmin.value) return
  loading.value = true
  error.value = ''
  try {
    const payload = await getProjectModularizationStatus(projectKey)
    status.value = payload?.status || null
    message.value = ''
  } catch (err) {
    status.value = null
    error.value = err instanceof Error ? err.message : '加载状态失败'
  } finally {
    loading.value = false
  }
}

async function runBootstrap() {
  if (!isSystemAdmin.value || working.value) return
  working.value = true
  error.value = ''
  try {
    const payload = await bootstrapProjectModularization(projectKey)
    status.value = payload?.status || status.value
    const copiedConfig = payload?.bootstrap?.copied_config?.length || 0
    const copiedRuntime = payload?.bootstrap?.copied_runtime?.length || 0
    message.value = `初始化完成：复制配置 ${copiedConfig} 个，运行时文件 ${copiedRuntime} 个。`
  } catch (err) {
    error.value = err instanceof Error ? err.message : '执行初始化失败'
  } finally {
    working.value = false
  }
}

onMounted(async () => {
  await ensureProjectsLoaded()
  await loadStatus()
})
</script>

<style scoped>
.modularization-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sub {
  margin-top: 6px;
  color: var(--neutral-500);
}

.actions {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.tips {
  margin-bottom: 12px;
  font-size: 13px;
  color: #065f46;
  background: #d1fae5;
  border: 1px solid #a7f3d0;
  border-radius: 8px;
  padding: 8px 10px;
}

.block {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.path-list {
  margin: 0;
  padding-left: 16px;
  color: var(--neutral-600);
}

.status-table {
  width: 100%;
  border-collapse: collapse;
}

.status-table th,
.status-table td {
  border-bottom: 1px solid #e5e7eb;
  padding: 8px 10px;
  text-align: left;
  font-size: 13px;
}

.status-table th {
  background: #f8fafc;
  color: var(--neutral-500);
  font-weight: 600;
}

.placeholder {
  padding: 28px;
  text-align: center;
  border: 1px dashed #e2e8f0;
  border-radius: 10px;
  color: var(--neutral-500);
}

.placeholder.error {
  color: var(--danger-600);
  border-color: var(--danger-200);
}
</style>
