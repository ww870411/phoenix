<template>
  <div>
    <AppHeader />
    <div class="container">
    <header class="topbar">
      <div>
        <h2>仪表盘（表格选择与状态）</h2>
        <div class="sub">项目：{{ projectKey }}</div>
      </div>
      <div class="right" style="display:flex;align-items:center;gap:8px;">
        <label class="date">
          <span>业务日期</span>
          <input type="date" v-model="bizDate" />
        </label>
      </div>
    </header>

    <div class="table-wrap card">
      <table class="table">
        <thead>
          <tr>
            <th style="width:40%">表名</th>
            <th style="width:30%">sheet_key</th>
            <th style="width:15%">状态</th>
            <th style="width:15%">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in sheets" :key="s.sheet_key">
            <td>{{ s.sheet_name }}</td>
            <td>{{ s.sheet_key }}</td>
            <td>
              <span v-if="statusMap[s.sheet_key]" :class="['badge', badgeClass(s)]">
                {{ statusMap[s.sheet_key].filled }} / {{ statusMap[s.sheet_key].total }}
              </span>
              <span v-else class="badge neutral">-</span>
              <div v-if="statusMap[s.sheet_key]" class="progress" style="margin-top:6px;">
                <div class="progress-bar" :style="{ width: progressPct(s) }"></div>
              </div>
            </td>
            <td>
              <button @click="refreshStatus(s)" class="btn ghost">刷新状态</button>
              <button @click="openFill(s)" class="btn primary">去填报</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
  </div>
</template>

<script setup>
import '../styles/theme.css'
import AppHeader from '../components/AppHeader.vue'
import { onMounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { SHEETS } from '../constants/sheets';
import { getTemplate, queryData } from '../services/api';

const route = useRoute();
const router = useRouter();
const projectKey = route.params.projectKey;
const sheets = SHEETS;
const bizDate = ref(new Date().toISOString().slice(0, 10));

const statusMap = reactive({});

function openFill(s) {
  router.push(`/projects/${encodeURIComponent(projectKey)}/sheets/${encodeURIComponent(s.sheet_key)}/fill?biz_date=${bizDate.value}`);
}

async function refreshStatus(s) {
  // 思路：
  // 1) 获取模板计算可填单元格数（从列索引>=2开始统计）
  // 2) 查询该日期已填单元格数量
  const tpl = await getTemplate(projectKey, s.sheet_key);
  const fillableCols = tpl.columns.map((_, i) => i).filter(i => i >= 2);
  const total = (tpl.rows?.length || 0) * fillableCols.length;

  const q = await queryData({ project_key: projectKey, sheet_key: s.sheet_key, biz_date: bizDate.value });
  const filled = Array.isArray(q.cells) ? q.cells.length : 0;
  statusMap[s.sheet_key] = { filled, total };
}

onMounted(async () => {
  // 可选：首屏尝试拉一次状态（避免并发压力，按需刷新）
});

function badgeClass(s) {
  const st = statusMap[s.sheet_key];
  if (!st) return 'neutral';
  if (st.total > 0 && st.filled >= st.total) return 'success';
  if (st.total > 0 && st.filled > 0) return 'warning';
  return 'neutral';
}

function progressPct(s) {
  const st = statusMap[s.sheet_key];
  if (!st || !st.total) return '0%';
  const pct = Math.min(100, Math.round((st.filled / st.total) * 100));
  return pct + '%';
}
</script>

<style scoped>
.topbar { margin-bottom: 16px; }
.date { display: inline-flex; align-items: center; gap: 8px; }
</style>
