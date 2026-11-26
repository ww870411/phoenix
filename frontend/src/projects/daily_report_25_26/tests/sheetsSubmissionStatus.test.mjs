// 前端目录运行：node src/projects/daily_report_25_26/tests/sheetsSubmissionStatus.test.mjs
// 验证表格列表页在数据填报页展示填报状态标签，在数据审批页与数据展示页隐藏填报状态标签且不请求状态接口。
import assert from 'node:assert/strict'
import vm from 'node:vm'
import { readFile } from 'node:fs/promises'
import { ref, reactive, computed, watch } from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = new URL('../pages/Sheets.vue', import.meta.url)
const source = await readFile(filename, 'utf8')
const { descriptor, errors } = parse(source)
assert.equal(errors.length, 0)

const script = compileScript(descriptor, { id: 'sheets-status-test' })
const template = compileTemplate({
  source: descriptor.template.content,
  filename: filename.pathname,
  id: 'sheets-status-test',
  compilerOptions: { bindingMetadata: script.bindings },
})
assert.deepEqual(template.errors, [])

// 校验模板中单位状态徽标与子表数量徽标均受 showSubmissionStatus 控制
assert.match(
  descriptor.template.content,
  /<div[^>]*v-if="showSubmissionStatus"[^>]*class="status-indicator"/,
  '单位卡片右上角状态标签应受 showSubmissionStatus 控制',
)
assert.match(
  descriptor.template.content,
  /<span[^>]*v-if="showSubmissionStatus && getSheetStatus\(sheet\.sheet_key\)"[^>]*class="pill-ratio"/,
  '子表胶囊内数量标签应受 showSubmissionStatus 控制',
)

// 提取 <script setup> 中去除 import 与 onMounted 之后的业务代码进行隔离验证
const rawScript = descriptor.scriptSetup.content
const bodyLines = rawScript
  .split(/\r?\n/)
  .filter((line) => !line.startsWith('import '))
  .join('\n')
  .replace(/onMounted\(\(\) => \{[\s\S]*?\}\)\r?\n?/, '')

function createHarness(initialRoute) {
  const route = reactive({
    params: { projectKey: 'daily_report_25_26', pageKey: initialRoute.pageKey },
    query: { config: initialRoute.config, pageName: initialRoute.pageName },
  })
  const statusRequests = []
  const listRequests = []
  const pushedRoutes = []

  const context = vm.createContext({
    ref,
    computed,
    watch,
    console: { error() {}, warn() {} },
    useRoute: () => route,
    useRouter: () => ({
      replace(target) {
        pushedRoutes.push({ type: 'replace', target })
      },
      push(target) {
        pushedRoutes.push({ type: 'push', target })
      },
    }),
    useAuthStore: () => ({
      permissions: {},
      canManageValidationFor: () => false,
      filterSheetsByRule: (_p, _page, list) => list,
    }),
    ensureProjectsLoaded: async () => {},
    getProjectNameById: () => '2026-2027供暖期生产日报',
    getValidationMasterSwitch: async () => ({ validation_enabled: true }),
    setValidationMasterSwitch: async (_p, next) => ({ validation_enabled: next }),
    listSheets: async (projectKey, configFile) => {
      listRequests.push({ projectKey, configFile })
      return {
        content: initialRoute.sheets,
      }
    },
    getSheetsSubmissionStatus: async (projectKey, configFile) => {
      statusRequests.push({ projectKey, configFile })
      return {
        ok: true,
        status: {
          BeiHai_co_generation_sheet: {
            count: 17,
            expected: 17,
            text: '17/17',
            is_complete: true,
          },
        },
      }
    },
  })

  vm.runInContext(
    `${bodyLines}
globalThis.exposed = {
  isApprovalPage,
  isDisplayPage,
  isConstantDataPage,
  showSubmissionStatus,
  submissionStatus,
  loadSheets,
  getSheetStatus,
  getSheetPillClass,
  getSheetPillTooltip,
  openSheet,
};`,
    context,
  )

  return {
    exposed: context.exposed,
    statusRequests,
    listRequests,
    pushedRoutes,
  }
}

// 1. 每日数据填报页面：保留填报状态标签与接口调用
const entryHarness = createHarness({
  pageKey: 'data_entry',
  config: 'projects/daily_report_25_26/config/数据结构_基本指标表.json',
  pageName: '每日数据填报页面',
  sheets: {
    BeiHai_co_generation_sheet: {
      sheet_name: '1.北海热电厂（热电联产）表',
      unit_name: '北海热电厂',
    },
  },
})
await entryHarness.exposed.loadSheets()
assert.equal(entryHarness.exposed.showSubmissionStatus.value, true)
assert.equal(entryHarness.statusRequests.length, 1)
assert.deepEqual(
  { ...entryHarness.exposed.getSheetPillClass('BeiHai_co_generation_sheet') },
  {
    'unit-sheet-pill--complete': true,
    'unit-sheet-pill--partial': false,
    'unit-sheet-pill--empty': false,
  },
)
assert.equal(
  entryHarness.exposed.getSheetPillTooltip({
    sheet_key: 'BeiHai_co_generation_sheet',
    sheet_name: '1.北海热电厂（热电联产）表',
  }),
  '1.北海热电厂（热电联产）表（填报进度: 17/17 项）',
)

// 2. 数据审批页面：隐藏填报状态标签且不请求状态接口
const approvalHarness = createHarness({
  pageKey: 'data_approval',
  config: 'projects/daily_report_25_26/config/数据结构_审批用表.json',
  pageName: '数据审批页面',
  sheets: {
    ZhuChengQu_approval_Sheet: {
      sheet_name: '1.主城区审批表',
      unit_name: '主城区',
    },
  },
})
await approvalHarness.exposed.loadSheets()
assert.equal(approvalHarness.exposed.isApprovalPage.value, true)
assert.equal(approvalHarness.exposed.showSubmissionStatus.value, false)
assert.equal(approvalHarness.statusRequests.length, 0)
assert.deepEqual({ ...approvalHarness.exposed.submissionStatus.value }, {})
assert.deepEqual({ ...approvalHarness.exposed.getSheetPillClass('ZhuChengQu_approval_Sheet') }, {})
assert.equal(
  approvalHarness.exposed.getSheetPillTooltip({
    sheet_key: 'ZhuChengQu_approval_Sheet',
    sheet_name: '1.主城区审批表',
  }),
  '1.主城区审批表',
)

// 3. 数据展示页面：隐藏填报状态标签且不请求状态接口
const displayHarness = createHarness({
  pageKey: 'data_show',
  config: 'projects/daily_report_25_26/config/数据结构_全口径展示表.json',
  pageName: '数据展示页面',
  sheets: {
    Group_sum_show_Sheet: {
      sheet_name: '1.集团全口径汇总表',
      unit_name: '经济运行部',
    },
  },
})
await displayHarness.exposed.loadSheets()
assert.equal(displayHarness.exposed.isDisplayPage.value, true)
assert.equal(displayHarness.exposed.showSubmissionStatus.value, false)
assert.equal(displayHarness.statusRequests.length, 0)
assert.deepEqual({ ...displayHarness.exposed.submissionStatus.value }, {})
assert.deepEqual({ ...displayHarness.exposed.getSheetPillClass('Group_sum_show_Sheet') }, {})
assert.equal(
  displayHarness.exposed.getSheetPillTooltip({
    sheet_key: 'Group_sum_show_Sheet',
    sheet_name: '1.集团全口径汇总表',
  }),
  '1.集团全口径汇总表',
)

// 4. 常量指标页面：隐藏填报状态标签且不请求状态接口
const constantHarness = createHarness({
  pageKey: 'constant_data',
  config: 'projects/daily_report_25_26/config/数据结构_常量指标表.json',
  pageName: '常量指标页面',
  sheets: {
    BeiHai_constant_Sheet: {
      sheet_name: '1.北海热电厂常量表',
      unit_name: '北海热电厂',
    },
  },
})
await constantHarness.exposed.loadSheets()
assert.equal(constantHarness.exposed.isConstantDataPage.value, true)
assert.equal(constantHarness.exposed.showSubmissionStatus.value, false)
assert.equal(constantHarness.statusRequests.length, 0)
assert.deepEqual({ ...constantHarness.exposed.submissionStatus.value }, {})
assert.deepEqual({ ...constantHarness.exposed.getSheetPillClass('BeiHai_constant_Sheet') }, {})
assert.equal(
  constantHarness.exposed.getSheetPillTooltip({
    sheet_key: 'BeiHai_constant_Sheet',
    sheet_name: '1.北海热电厂常量表',
  }),
  '1.北海热电厂常量表',
)

console.log('sheetsSubmissionStatus tests passed (4/4 scenarios)')
