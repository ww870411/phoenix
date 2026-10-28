// 在仓库内留存审查结果；业务接口仅 GET，数据库查询在只读事务中执行。
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'

const outputDir = path.dirname(fileURLToPath(import.meta.url))
const pythonSource = await fs.readFile(path.join(outputDir, 'reproduce.py'), 'utf8')
const backend = spawnSync('docker', ['exec', '-i', 'phoenix_backend', 'python', '-B', '-'], {
  input: pythonSource, encoding: 'utf8', timeout: 60000,
})
if (backend.status !== 0) throw new Error(backend.stderr || `后端审查退出码 ${backend.status}`)
await fs.writeFile(path.join(outputDir, 'results.jsonl'), backend.stdout, 'utf8')
const frontend = spawnSync('node', [path.join(outputDir, 'frontend_checks.mjs')], {
  encoding: 'utf8', timeout: 10000,
})
if (frontend.status !== 0) throw new Error(frontend.stderr || `前端审查退出码 ${frontend.status}`)
console.log('已更新 results.jsonl 与 frontend_results.json。审查输出记录缺陷，不代表全部通过。')
