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
        <button class="btn ghost" style="margin-left:auto;" @click="refreshAll">刷新状态</button>
      </div>
    </header>
    <Breadcrumbs />

    <div class="table-wrap card">
      <div v-if="loadError" class="placeholder">{{ loadError }}</div>
      <div v-else class="card-grid">
        <div class="card" v-for="g in grouped" :key="g.unit">
          <div class="card-header">{{ g.unit || '未分组' }}</div>
          <ul class="sheet-list">
            <li v-for="s in g.items" :key="s.sheet_key">
              <a href="#" @click.prevent="openFill(s)" class="sheet-link">{{ s.sheet_name }}</a>
              <span class="sub" style="margin-left:8px;">{{ s.sheet_key }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
  </div>
</template>

<script setup>
import '../styles/theme.css'
import AppHeader from '../components/AppHeader.vue'
import { onMounted, reactive, ref, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { listSheets, getTemplate, queryData } from '../services/api';

const route = useRoute();
const router = useRouter();
const projectKey = route.params.projectKey;
const sheets = ref([]);
const bizDate = ref(new Date().toISOString().slice(0, 10));

const statusMap = reactive({});
const loadError = ref('');

function openFill(s) {
  router.push(`/projects/${encodeURIComponent(projectKey)}/sheets/${encodeURIComponent(s.sheet_key)}`);
}

async function refreshStatus(s) {
  // 思路：
  // 1) 获取模板计算可填单元格数（从列索引>=2开始统计）
  // 2) 查询该日期已填单元格数量
  let tpl;
  try {
    tpl = await getTemplate(projectKey, s.sheet_key);
  } catch (err) {
    statusMap[s.sheet_key] = { filled: 0, total: 0 };
    return;
  }
  const columns = Array.isArray(tpl?.columns) ? tpl.columns : [];
  const rows = Array.isArray(tpl?.rows) ? tpl.rows : [];
  const fillableCols = columns.map((_, i) => i).filter(i => i >= 2);
  const total = rows.length * fillableCols.length;

  let q;
  try {
    q = await queryData({ project_key: projectKey, sheet_key: s.sheet_key, biz_date: bizDate.value });
  } catch (err) {
    q = {};
  }
  const cells = Array.isArray(q?.cells) ? q.cells : [];
  const filled = cells.length;
  statusMap[s.sheet_key] = { filled, total };
}

async function refreshAll() {
  for (const s of sheets.value) {
    await refreshStatus(s);
  }
}

onMounted(async () => {
  try {
    const data = await listSheets(projectKey);
    const arr = Object.entries(data).map(([k, v]) => ({
      sheet_key: k,
      sheet_name: v?.['表名'] || k,
      unit_name: v?.['单位名'] || '',
    }));
    sheets.value = arr;
    await refreshAll();
  } catch (e) {
    loadError.value = '无法获取表清单，请确认后端已提供 数据结构_基本指标表.json';
    console.error(e);
  }
});

const grouped = computed(() => {
  const map = new Map();
  for (const s of sheets.value) {
    const unit = s.unit_name || '';
    if (!map.has(unit)) map.set(unit, []);
    map.get(unit).push(s);
  }
  return Array.from(map.entries()).map(([unit, items]) => ({ unit, items }));
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
.sheet-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.sheet-link { color: var(--primary-700); text-decoration: none; }
.sheet-link:hover { text-decoration: underline; }
</style>
