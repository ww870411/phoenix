// 使用后端实际会话序列化和前端实际 Pinia store，核对单位表单范围；不登录、不写数据库。
const fs = require('node:fs')
const path = require('node:path')
const { createRequire } = require('node:module')
const { spawnSync } = require('node:child_process')
const assert = require('node:assert/strict')
const root = path.resolve(__dirname, '../..')
const req = createRequire(path.join(root, 'frontend/package.json'))
const script = `
import json
from backend.services.auth_manager import auth_manager
auth_manager._ensure_loaded()
rows = []
for record in auth_manager._users_by_name.values():
    if record.group not in {'Global_admin','Group_admin','ZhuChengQu_admin','Unit_admin','unit_filler','shoudian_filler'}:
        continue
    session = auth_manager._build_session(record=record, group_permissions=auth_manager._groups[record.group], token='scope-test-not-persisted', issued_at=auth_manager._now(), expires_at=None, persistent=False)
    rows.append({'username':record.username,'group':record.group,'unit':record.unit,'permissions':session.to_permissions_payload()})
print(json.dumps(rows))
`
const response = spawnSync('python', ['-c', script], { cwd: root, encoding: 'utf8' })
assert.equal(response.status, 0, response.stderr)
const accounts = JSON.parse(response.stdout)
const vue = req('vue'), pinia = req('pinia')
pinia.setActivePinia(pinia.createPinia())
const source = fs.readFileSync(path.join(root, 'frontend/src/projects/daily_report_25_26/store/auth.js'), 'utf8')
const code = req('esbuild').transformSync(source, { format: 'cjs', loader: 'js' }).code
const moduleBox = { exports: {} }
require('node:vm').runInNewContext(code, {
  module: moduleBox, exports: moduleBox.exports, console,
  require: name => name === 'vue' ? vue : name === 'pinia' ? pinia : { setAuthToken() {} },
})
const store = moduleBox.exports.useAuthStore()
const config = JSON.parse(fs.readFileSync(path.join(root, 'backend_data/projects/daily_report_25_26/config/数据结构_基本指标表.json'), 'utf8').replace(/^\uFEFF/, ''))
const sheets = Object.entries(config).filter(([key]) => key !== '__global_settings__').map(([key, value]) => ({ sheet_key: key, unit_name: value['单位中文名'] || value['单位名称'] || '' }))
for (const account of accounts) {
  store.user = { username: account.username, unit: account.unit }
  store.permissions = account.permissions
  const visible = store.filterSheetsByRule('daily_report_25_26', 'data_entry', sheets).map(item => item.sheet_key).sort()
  let expected
  if (['unit_filler', 'Unit_admin'].includes(account.group)) expected = sheets.filter(item => item.sheet_key.toLowerCase().startsWith(account.unit.toLowerCase())).map(item => item.sheet_key).sort()
  else if (account.group === 'shoudian_filler') expected = ['Coal_inventory_Sheet']
  else if (account.group === 'ZhuChengQu_admin') expected = sheets.filter(item => /^(BeiHai|XiangHai|GongRe)_/.test(item.sheet_key)).map(item => item.sheet_key).sort()
  else expected = sheets.map(item => item.sheet_key).sort()
  assert.deepEqual(visible, expected, account.username)
  assert.ok(store.canSubmitFor('daily_report_25_26'), account.username)
  // 主城区展示页原本显式授权汇总表，不属于此处的基本指标表清单。
  assert.equal(store.filterSheetsByRule('daily_report_25_26', 'data_show', sheets).length, account.group === 'ZhuChengQu_admin' ? 0 : sheets.length)
  console.log(`${account.username}: ${visible.join(', ')}`)
}
console.log(`通过：${accounts.length} 个账号的填报表单范围、提交开关及数据展示范围`)
