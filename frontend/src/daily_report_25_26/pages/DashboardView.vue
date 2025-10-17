<template>
  <div class="page">
    <header class="topbar">
      <div class="left">
        <h2>仪表盘（表格选择与状态）</h2>
        <div class="sub">项目：{{ projectKey }}</div>
      </div>
      <div class="right">
        <label class="date">
          <span>业务日期</span>
          <input type="date" v-model="bizDate" />
        </label>
      </div>
    </header>

    <div class="list">
      <div class="row head">
        <div class="col name">表名</div>
        <div class="col key">sheet_key</div>
        <div class="col status">状态（已填/总数）</div>
        <div class="col actions">操作</div>
      </div>
      <div class="row" v-for="(s, idx) in sheets" :key="s.sheet_key">
        <div class="col name">{{ s.sheet_name }}</div>
        <div class="col key">{{ s.sheet_key }}</div>
        <div class="col status">
          <span v-if="statusMap[s.sheet_key]">
            {{ statusMap[s.sheet_key].filled }} / {{ statusMap[s.sheet_key].total }}
          </span>
          <span v-else>-</span>
        </div>
        <div class="col actions">
          <button @click="refreshStatus(s)" class="ghost">刷新状态</button>
          <button @click="openFill(s)" class="primary">去填报</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
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
</script>

<style scoped>
.page { padding: 20px; }
.topbar { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 16px; }
.topbar .left h2 { margin: 0; }
.sub { color: #666; font-size: 13px; margin-top: 6px; }
.date { display: flex; align-items: center; gap: 8px; }
.list { border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden; background: #fff; }
.row { display: grid; grid-template-columns: 2fr 2fr 1fr 1fr; border-top: 1px solid #f1f5f9; }
.row:first-child { border-top: 0; }
.row.head { background: #f8fafc; font-weight: 600; }
.col { padding: 12px; display: flex; align-items: center; }
.actions { gap: 8px; }
button { height: 30px; padding: 0 12px; border-radius: 8px; border: 1px solid #e5e7eb; background: #fff; cursor: pointer; }
button.ghost:hover { background: #f8fafc; }
button.primary { border-color: #4f46e5; background: #4f46e5; color: #fff; }
button.primary:hover { filter: brightness(1.05); }
</style>

