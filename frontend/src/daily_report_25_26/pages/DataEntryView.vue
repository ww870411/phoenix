<template>
  <div class="page">
    <header class="topbar">
      <div>
        <h2>数据填报</h2>
        <div class="sub">项目：{{ projectKey }} ｜ 表：{{ sheetKey }}</div>
      </div>
      <div class="right">
        <label class="date">
          <span>业务日期</span>
          <input type="date" v-model="bizDate" @change="loadExisting" />
        </label>
        <button class="ghost" @click="reloadTemplate">重载模板</button>
        <button class="primary" @click="onSubmit">提交</button>
      </div>
    </header>

    <div class="table-wrap" v-if="columns.length">
      <table>
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
</template>

<script setup>
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
.page { padding: 20px; }
.topbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.sub { color: #666; font-size: 13px; margin-top: 6px; }
.date { display: inline-flex; align-items: center; gap: 8px; margin-right: 8px; }
.ghost { height: 32px; padding: 0 12px; border-radius: 8px; border: 1px solid #e5e7eb; background: #fff; cursor: pointer; margin-right: 8px; }
.primary { height: 32px; padding: 0 12px; border-radius: 8px; border: 1px solid #4f46e5; background: #4f46e5; color: #fff; cursor: pointer; }
.table-wrap { overflow-x: auto; background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; }
table { width: 100%; border-collapse: collapse; }
th, td { border-bottom: 1px solid #f1f5f9; padding: 8px 10px; text-align: left; }
thead th { background: #f8fafc; }
input[type="text"] { width: 120px; height: 28px; border: 1px solid #e5e7eb; border-radius: 6px; padding: 0 8px; }
.placeholder { padding: 40px; text-align: center; color: #777; }
</style>

