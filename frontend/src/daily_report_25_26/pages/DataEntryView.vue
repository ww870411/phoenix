<template>
  <div>
    <AppHeader />
    <div class="container">
    <header class="topbar">
      <div>
        <h2>数据填报</h2>
        <div class="sub">项目：{{ projectKey }} ｜ 表：{{ sheetKey }}</div>
      </div>
      <div class="right" style="display:flex;align-items:center;gap:8px;">
        <label class="date">
          <span>业务日期</span>
          <input type="date" v-model="bizDate" @change="loadExisting" />
        </label>
        <button class="btn ghost" @click="reloadTemplate">重载模板</button>
        <button class="btn primary" @click="onSubmit">提交</button>
      </div>
    </header>

    <div class="table-wrap card" v-if="columns.length">
      <table class="table">
        <thead>
          <tr>
            <th v-for="(c,i) in columns" :key="i">{{ c }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(r, ri) in rows" :key="ri">
            <td v-for="(c, ci) in r" :key="ci">
              <template v-if="ci < 2">{{ c }}</template>
              <template v-else>
                <input
                  type="text"
                  :placeholder="'填报'"
                  v-model="values[`${ri}-${ci}`]"
                />
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="placeholder">无模板数据</div>
  </div>
  </div>
</template>

<script setup>
import '../styles/theme.css'
import AppHeader from '../components/AppHeader.vue'
import { onMounted, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';
import { getTemplate, queryData, submitData } from '../services/api';

const route = useRoute();
const projectKey = route.params.projectKey;
const sheetKey = route.params.sheetKey;
const initialDate = route.query.biz_date || new Date().toISOString().slice(0,10);

const sheetName = ref('');
const columns = ref([]);
const rows = ref([]);
const bizDate = ref(String(initialDate));
const values = reactive({});

function toKey(ri, ci) { return `${ri}-${ci}`; }

async function loadTemplate() {
  const tpl = await getTemplate(projectKey, sheetKey);
  sheetName.value = tpl.sheet_name || '';
  columns.value = tpl.columns || [];
  rows.value = tpl.rows || [];
  // 清空当前值
  Object.keys(values).forEach(k => delete values[k]);
}

async function loadExisting() {
  const q = await queryData({ project_key: projectKey, sheet_key: sheetKey, biz_date: bizDate.value });
  // 将已填报的值映射到 values
  if (Array.isArray(q.cells)) {
    for (const cell of q.cells) {
      const { row_label, col_index, value_type, value_num, value_text } = cell;
      const ri = rows.value.findIndex(r => r[0] === row_label);
      if (ri >= 0 && col_index >= 0) {
        values[toKey(ri, col_index)] = value_type === 'num' ? String(value_num ?? '') : String(value_text ?? '');
      }
    }
  }
}

async function reloadTemplate() {
  await loadTemplate();
  await loadExisting();
}

async function onSubmit() {
  const cols = columns.value;
  const fillableCols = cols.map((_, i) => i).filter(i => i >= 2);
  const cells = [];
  for (let ri = 0; ri < rows.value.length; ri++) {
    const row = rows.value[ri];
    for (const ci of fillableCols) {
      const key = toKey(ri, ci);
      const raw = values[key];
      if (raw === undefined || raw === '') continue;
      const asNum = Number(raw);
      const isNum = !Number.isNaN(asNum) && raw !== '' && /^-?\d+(\.\d+)?$/.test(String(raw));
      cells.push({
        row_label: row[0],
        unit: row[1] ?? '',
        col_index: ci,
        value_type: isNum ? 'num' : 'text',
        value_num: isNum ? asNum : undefined,
        value_text: isNum ? undefined : String(raw),
      });
    }
  }
  const payload = {
    project_key: projectKey,
    sheet_key: sheetKey,
    sheet_name: sheetName.value || '',
    biz_date: bizDate.value,
    cells,
  };
  await submitData(payload);
  // 简单提示
  alert('提交成功');
}

onMounted(async () => {
  await loadTemplate();
  await loadExisting();
});
</script>

<style scoped>
.topbar { gap: 12px; margin-bottom: 16px; }
.date { display: inline-flex; align-items: center; gap: 8px; margin-right: 8px; }
</style>
