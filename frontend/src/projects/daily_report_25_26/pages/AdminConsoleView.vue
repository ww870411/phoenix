<template>
  <div class="admin-console-view">
    <AppHeader />
    <main class="admin-console-main">
      <Breadcrumbs :items="breadcrumbItems" />

      <section class="card elevated top-shell">
        <header class="card-header top-header">
          <div>
            <h2>全局管理后台</h2>
            <p class="subtext">统一处理后台文件与项目设定</p>
          </div>
          <div class="tab-group">
            <button class="tab-btn" :class="{ active: activeTab === 'files' }" type="button" @click="activeTab = 'files'">后台文件编辑</button>
            <button class="tab-btn" :class="{ active: activeTab === 'database' }" type="button" @click="activeTab = 'database'">数据库表编辑</button>
            <button class="tab-btn" :class="{ active: activeTab === 'project' }" type="button" @click="activeTab = 'project'">项目后台设定</button>
            <button class="tab-btn" :class="{ active: activeTab === 'system' }" type="button" @click="activeTab = 'system'">服务器管理</button>
            <button class="tab-btn" :class="{ active: activeTab === 'audit' }" type="button" @click="activeTab = 'audit'">操作日志</button>
          </div>
        </header>

        <section v-if="activeTab === 'files'" class="content-block">
          <div class="toolbar">
            <label class="field grow">
              <span>搜索</span>
              <input v-model.trim="fileSearch" type="text" placeholder="输入目录名或文件名关键字（树中筛选）" />
            </label>
            <button class="btn ghost" type="button" @click="loadDirectories">刷新目录</button>
          </div>

          <div class="tree-wrap">
            <div class="tree-head">
              <h3>文件树</h3>
              <p class="subtext">树根为 backend_data，目录与文件统一显示；点击文件后将在弹出窗口中编辑</p>
            </div>
            <div v-if="fileListLoading" class="panel-state">文件加载中…</div>
            <div v-else-if="!visibleTreeRows.length" class="panel-state">无匹配文件</div>
            <div v-else class="tree-list">
              <button
                v-for="row in visibleTreeRows"
                :key="row.key"
                class="tree-row"
                :class="[
                  row.type === 'folder' ? 'tree-folder' : 'tree-file',
                  row.type === 'file' && row.path === selectedFilePath ? 'active' : '',
                ]"
                :style="{ paddingLeft: `${12 + row.depth * 18}px` }"
                type="button"
                @click="onTreeRowClick(row)"
              >
                <span v-if="row.type === 'folder'" class="tree-icon">{{ row.expanded ? '▾' : '▸' }}</span>
                <span v-else class="tree-icon">•</span>
                <span class="tree-label">{{ row.name }}</span>
              </button>
            </div>
            <p v-if="selectedFilePath" class="subtext">最近打开：{{ selectedFilePath }}</p>
            <p class="subtext">点击文件后将在新窗口中打开编辑器。</p>
            <p v-if="fileMessage" class="message">{{ fileMessage }}</p>
          </div>
        </section>

        <section v-else-if="activeTab === 'database'" class="content-block">
          <section class="inner-card db-editor-card">
            <header class="section-header">
              <h3>数据库表在线编辑</h3>
              <div class="system-actions">
                <button class="btn ghost" type="button" :disabled="dbLoading || dbSaving" @click="loadDbTables">刷新表清单</button>
                <button class="btn primary" type="button" :disabled="dbLoading || dbSaving || !dbSelectedTable" @click="loadDbRows">
                  {{ dbLoading ? '加载中…' : '查询数据' }}
                </button>
                <button class="btn primary" type="button" :disabled="dbSaving || dbDirtyStats.dirtyRows === 0" @click="saveDbRows">
                  {{ dbSaving ? '保存中…' : `保存修改（${dbDirtyStats.dirtyRows}行）` }}
                </button>
              </div>
            </header>
            <div class="toolbar db-toolbar">
              <label class="field">
                <span>数据表</span>
                <select v-model="dbSelectedTable">
                  <option v-for="name in dbTables" :key="name" :value="name">{{ name }}</option>
                </select>
              </label>
              <label class="field grow">
                <span>关键字检索</span>
                <input v-model.trim="dbSearchText" type="text" placeholder="在全字段文本中模糊匹配" />
              </label>
              <label class="field">
                <span>排序字段</span>
                <select v-model="dbOrderBy">
                  <option value="">主键默认</option>
                  <option v-for="col in dbColumns" :key="`sort-${col.name}`" :value="col.name">{{ col.name }}</option>
                </select>
              </label>
              <label class="field">
                <span>排序方向</span>
                <select v-model="dbOrderDir">
                  <option value="asc">升序</option>
                  <option value="desc">降序</option>
                </select>
              </label>
              <label class="field">
                <span>每页行数</span>
                <input v-model.number="dbLimit" type="number" min="1" max="1000" />
              </label>
              <label class="field">
                <span>偏移量</span>
                <input v-model.number="dbOffset" type="number" min="0" />
              </label>
            </div>
            <div class="db-filter-wrap">
              <div class="db-filter-head">
                <span>字段筛选（AND）</span>
                <div class="inline-actions">
                  <button class="btn ghost" type="button" @click="addDbFilterRow">新增条件</button>
                  <button class="btn ghost" type="button" @click="resetDbFilters">清空条件</button>
                </div>
              </div>
              <div class="db-filter-list">
                <div v-for="(flt, idx) in dbFilters" :key="`flt-${idx}`" class="db-filter-item">
                  <select v-model="flt.column">
                    <option value="">选择字段</option>
                    <option v-for="col in dbColumns" :key="`flt-col-${idx}-${col.name}`" :value="col.name">{{ col.name }}</option>
                  </select>
                  <select v-model="flt.op">
                    <option value="contains">包含</option>
                    <option value="eq">等于</option>
                    <option value="ne">不等于</option>
                    <option value="starts_with">前缀</option>
                    <option value="ends_with">后缀</option>
                    <option value="gt">大于</option>
                    <option value="gte">大于等于</option>
                    <option value="lt">小于</option>
                    <option value="lte">小于等于</option>
                    <option value="is_null">为空</option>
                    <option value="not_null">非空</option>
                  </select>
                  <input
                    v-model="flt.value"
                    :disabled="flt.op === 'is_null' || flt.op === 'not_null'"
                    type="text"
                    placeholder="筛选值"
                  />
                  <button class="btn danger" type="button" @click="removeDbFilterRow(idx)">删除</button>
                </div>
              </div>
            </div>
            <p class="subtext">支持全部数据表查询；保存修改仍要求目标表存在主键。主键字段只读。</p>
            <p v-if="dbMessage" class="message">{{ dbMessage }}</p>
            <div v-if="dbRowsDraft.length" class="db-table-wrap">
              <table class="audit-table db-edit-table">
                <thead>
                  <tr>
                    <th v-for="col in dbColumns" :key="`h-${col.name}`">
                      {{ col.name }}
                      <span v-if="isDbPkColumn(col.name)" class="db-pk-tag">PK</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, rowIndex) in dbRowsDraft" :key="buildDbRowKey(row, rowIndex)">
                    <td v-for="col in dbColumns" :key="`c-${rowIndex}-${col.name}`">
                      <input
                        v-model="row[col.name]"
                        :disabled="isDbPkColumn(col.name)"
                        type="text"
                        class="db-cell-input"
                      />
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="panel-state">暂无数据，请先设置条件后点击“查询数据”。</div>
          </section>
        </section>

        <section v-else-if="activeTab === 'project'" class="content-block">
          <div class="project-switch">
            <button
              v-for="item in projects"
              :key="item.project_key"
              class="list-btn"
              :class="{ active: item.project_key === selectedProjectKey }"
              type="button"
              @click="selectProject(item.project_key)"
            >
              {{ item.project_name }}（{{ item.project_key }}）
            </button>
          </div>

          <div v-if="selectedProjectKey !== TARGET_PROJECT_KEY" class="panel-state">
            当前项目的后台设定暂未接入。请选择 {{ TARGET_PROJECT_KEY }} 查看现有配置模块。
          </div>

          <template v-else>
            <section class="inner-card">
              <header class="section-header">
                <h3>设定概览</h3>
              </header>
              <div v-if="loading" class="panel-state">加载中…</div>
              <div v-else-if="errorMessage" class="panel-state error">{{ errorMessage }}</div>
              <div v-else class="overview-grid">
                <div class="overview-item">
                  <span class="label">校验开关管理</span>
                  <strong>{{ actionLabel(overview?.actions?.can_manage_validation) }}</strong>
                </div>
                <div class="overview-item">
                  <span class="label">AI 设置管理</span>
                  <strong>{{ actionLabel(overview?.actions?.can_manage_ai_settings) }}</strong>
                </div>
                <div class="overview-item">
                  <span class="label">缓存发布管理</span>
                  <strong>{{ actionLabel(overview?.actions?.can_publish_cache) }}</strong>
                </div>
              </div>
            </section>

            <section class="inner-card">
              <header class="section-header">
                <h3>数据校验总开关</h3>
                <button class="btn primary" type="button" :disabled="!canManageValidation || validationPending" @click="toggleValidationMaster">
                  {{ validationPending ? '保存中…' : '切换开关' }}
                </button>
              </header>
              <p class="subtext">当前状态：{{ validationMasterEnabled ? '已开启' : '已关闭' }}</p>
            </section>

            <section class="inner-card">
              <header class="section-header">
                <h3>AI 设置</h3>
                <button class="btn primary" type="button" :disabled="!canManageAiSettings" @click="openAiSettingsDialog">
                  智能体设定
                </button>
              </header>
              <p class="subtext">与日报查询页、月报查询页共用同一套智能体配置（shared/ai_settings.json）。</p>
            </section>

            <section class="inner-card">
              <header class="section-header">
                <h3>看板功能设置</h3>
              </header>
              <div class="cache-actions">
                <label>
                  <span>业务日期（自动读取）</span>
                  <input v-model="dashboardBizDate" :disabled="!canManageCache || cachePending || bizDateLoading" type="date" />
                </label>
                <button class="btn ghost" type="button" :disabled="!canManageCache || cachePending || bizDateLoading" @click="syncDashboardBizDate">
                  {{ bizDateLoading ? '读取中…' : '读取业务日期' }}
                </button>
                <label>
                  <span>发布天数</span>
                  <select v-model.number="publishDays" :disabled="!canManageCache || cachePending">
                    <option :value="1">1</option>
                    <option :value="3">3</option>
                    <option :value="7">7</option>
                    <option :value="14">14</option>
                    <option :value="30">30</option>
                  </select>
                </label>
                <label>
                  <span>刷新日期</span>
                  <input v-model="refreshDate" :disabled="!canManageCache || cachePending" type="date" />
                </label>
                <button class="btn primary" type="button" :disabled="!canManageCache || cachePending" @click="publishCache">发布缓存</button>
                <button class="btn ghost" type="button" :disabled="!canManageCache || cachePending" @click="refreshCache">刷新单日</button>
                <button class="btn ghost" type="button" :disabled="!canManageCache || cachePending" @click="cancelPublish">停止任务</button>
                <button class="btn danger" type="button" :disabled="!canManageCache || cachePending" @click="disableCache">禁用缓存</button>
                <button class="btn ghost" type="button" :disabled="!canManageCache || temperatureImportBusy || cachePending" @click="importTemperature">
                  {{ temperatureImportBusy ? '导入中…' : '导入气温（预览）' }}
                </button>
              </div>
              <p class="subtext">任务状态：{{ cacheJobStatus }}</p>
              <div v-if="cacheWorkerGroups.length" class="cache-worker-grid">
                <div
                  v-for="group in cacheWorkerGroups"
                  :key="group.key"
                  class="cache-worker-card"
                  :class="`is-${group.status}`"
                >
                  <div class="cache-worker-card__header">
                    <span class="cache-worker-card__title">{{ group.label }}</span>
                    <span class="cache-worker-card__badge">{{ formatCacheWorkerStatus(group.status) }}</span>
                  </div>
                  <div class="cache-worker-card__message">{{ group.message || '等待开始' }}</div>
                  <div class="cache-worker-card__meta">
                    <span>分块：{{ group.sectionsText }}</span>
                    <span v-if="group.updatedAt">{{ group.updatedAt }}</span>
                  </div>
                </div>
              </div>
              <div v-if="cacheJobLogs.length" class="panel-state cache-job-log-panel">
                <div class="cache-job-log-panel__title">最近日志</div>
                <div v-for="(log, index) in cacheJobLogs" :key="`${index}-${log.time || ''}`">{{ log.time }} {{ log.text }}</div>
              </div>
              <div v-if="temperatureImportMessage" class="panel-state">{{ temperatureImportMessage }}</div>
            </section>
          </template>
        </section>

        <div v-if="temperatureImportDialogVisible" class="temp-import-modal">
          <div class="temp-import-modal__mask" @click="closeTemperatureImportDialog"></div>
          <div class="temp-import-modal__card">
            <header class="temp-import-modal__header">
              <h3>气温导入确认</h3>
              <button class="temp-import-modal__close" type="button" :disabled="temperatureImportCommitBusy" @click="closeTemperatureImportDialog">×</button>
            </header>
            <section class="temp-import-modal__body">
              <p v-if="temperatureImportStatus.message">{{ temperatureImportStatus.message }}</p>
              <p v-if="temperatureImportStatus.fetchedAt">获取时间：{{ temperatureImportStatus.fetchedAt }}</p>
              <p v-if="temperatureImportStatus.dates.length">涉及日期：{{ temperatureImportStatus.dates.join('、') }}</p>
              <p v-if="temperatureImportStatus.overlapHours">重合区间：{{ temperatureImportStatus.overlapRange }}（{{ temperatureImportStatus.overlapHours }} 小时）</p>
              <p v-if="temperatureImportStatus.diffCount">差异小时：{{ temperatureImportStatus.diffCount }} 条</p>
              <div v-if="temperatureImportStatus.overlapRecords.length" class="temp-import-modal__diffs">
                <div class="temp-import-modal__diffs-title">逐小时一致性（红色为不一致，未命中数据库显示“—”）：</div>
                <ul>
                  <li
                    v-for="item in temperatureImportStatus.overlapRecords"
                    :key="item.time"
                    :class="['temp-import-modal__diff-item', { 'temp-import-modal__diff-item--different': item.different }]"
                  >
                    {{ item.time }}：接口 {{ item.apiValue }}℃ / 数据库 {{ item.inDb ? (item.dbValue ?? '—') : '—' }}℃（{{ item.different ? '不一致' : '一致' }}）
                  </li>
                </ul>
              </div>
              <p class="temp-import-modal__hint">点击“确认入库”将覆盖重合时间段历史气温数据；点击“取消”仅保留预览。</p>
              <p v-if="temperatureImportStatus.writeMessage" class="temp-import-modal__write">{{ temperatureImportStatus.writeMessage }}</p>
            </section>
            <footer class="temp-import-modal__footer">
              <button class="btn primary" type="button" :disabled="temperatureImportCommitBusy" @click="commitTemperature">
                {{ temperatureImportCommitBusy ? '写入中…' : '确认入库' }}
              </button>
              <button class="btn ghost" type="button" :disabled="temperatureImportCommitBusy" @click="closeTemperatureImportDialog">取消</button>
            </footer>
          </div>
        </div>

        <section v-else-if="activeTab === 'system'" class="content-block">
          <section class="inner-card">
            <header class="section-header">
              <h3>服务器性能概览</h3>
              <div class="system-actions">
                <label class="switch-row">
                  <input v-model="systemAutoRefresh" type="checkbox" />
                  <span>自动刷新（5秒）</span>
                </label>
                <button class="btn primary" type="button" :disabled="systemLoading" @click="loadSystemMetrics">
                  {{ systemLoading ? '刷新中…' : '立即刷新' }}
                </button>
              </div>
            </header>
            <p class="subtext">
              指标来源：{{ systemMetrics?.metrics_provider || 'unknown' }} ｜ 最近刷新：{{ formatEast8Time(systemMetrics?.timestamp) }}
            </p>
            <div v-if="systemError" class="panel-state error">{{ systemError }}</div>
            <div v-else-if="!systemMetrics" class="panel-state">暂无系统指标</div>
            <div v-else class="system-grid">
              <div class="overview-item">
                <span class="label">CPU 使用率</span>
                <strong>{{ formatPercent(systemMetrics.cpu?.percent) }}</strong>
                <div class="sparkline-box">
                  <svg class="sparkline-svg" viewBox="0 0 160 44" preserveAspectRatio="none">
                    <polyline :points="sparkPoints(metricHistory.cpu)" class="sparkline-line sparkline-cpu" />
                  </svg>
                </div>
              </div>
              <div class="overview-item">
                <span class="label">内存使用率</span>
                <strong>{{ formatPercent(systemMetrics.memory?.percent) }}</strong>
                <div class="sparkline-box">
                  <svg class="sparkline-svg" viewBox="0 0 160 44" preserveAspectRatio="none">
                    <polyline :points="sparkPoints(metricHistory.memory)" class="sparkline-line sparkline-memory" />
                  </svg>
                </div>
              </div>
              <div class="overview-item">
                <span class="label">磁盘使用率</span>
                <strong>{{ formatPercent(systemMetrics.disk?.percent) }}</strong>
                <div class="sparkline-box">
                  <svg class="sparkline-svg" viewBox="0 0 160 44" preserveAspectRatio="none">
                    <polyline :points="sparkPoints(metricHistory.disk)" class="sparkline-line sparkline-disk" />
                  </svg>
                </div>
              </div>
              <div class="overview-item">
                <span class="label">进程内存(RSS)</span>
                <strong>{{ formatBytes(systemMetrics.process?.memory_rss_bytes) }}</strong>
              </div>
              <div class="overview-item">
                <span class="label">进程 CPU</span>
                <strong>{{ formatPercent(systemMetrics.process?.cpu_percent) }}</strong>
                <div class="sparkline-box">
                  <svg class="sparkline-svg" viewBox="0 0 160 44" preserveAspectRatio="none">
                    <polyline :points="sparkPoints(metricHistory.processCpu)" class="sparkline-line sparkline-proc" />
                  </svg>
                </div>
              </div>
              <div class="overview-item">
                <span class="label">运行时长</span>
                <strong>{{ formatUptime(systemMetrics.uptime_seconds) }}</strong>
              </div>
              <div class="overview-item">
                <span class="label">平台</span>
                <strong>{{ systemMetrics.platform?.system || '—' }} {{ systemMetrics.platform?.release || '' }}</strong>
              </div>
              <div class="overview-item">
                <span class="label">Python</span>
                <strong>{{ systemMetrics.platform?.python || '—' }}</strong>
              </div>
            </div>
            <p class="subtext">趋势图展示最近 {{ METRIC_HISTORY_LIMIT }} 次采样。</p>
          </section>

          <section class="inner-card super-card">
            <header class="section-header">
              <h3>超级管理员控制台</h3>
            </header>

            <p class="subtext">本页不再提供服务器管理员账号登录，命令与文件操作直接使用当前后端服务进程所在机器的权限执行。</p>
            <p v-if="superMessage" class="message">{{ superMessage }}</p>

            <div class="super-split">
              <div class="super-pane">
                <h4>命令执行</h4>
                <div class="super-preset-row">
                  <label class="field grow">
                    <span>默认命令</span>
                    <select v-model="selectedCommandPreset" :disabled="terminalRunning">
                      <option value="">请选择预设命令</option>
                      <option v-for="item in SUPER_COMMAND_PRESETS" :key="item.label" :value="item.label">
                        {{ item.label }}
                      </option>
                    </select>
                  </label>
                  <button class="btn ghost" type="button" :disabled="!selectedCommandPreset || terminalRunning" @click="applySelectedCommandPreset">
                    填充
                  </button>
                </div>
                <label class="field grow">
                  <span>工作目录（可选）</span>
                  <input v-model.trim="terminalCwd" type="text" placeholder="例如 /app 或 C:\\Users\\ww" />
                </label>
                <label class="field grow">
                  <span>命令</span>
                  <textarea v-model="terminalCommand" rows="4" placeholder="输入要执行的命令..." @keydown.ctrl.l.prevent="clearTerminalOutput" />
                </label>
                <label class="field">
                  <span>超时(秒)</span>
                  <input v-model.number="terminalTimeout" type="number" min="1" max="180" />
                </label>
                <div class="super-terminal-actions">
                  <button class="btn primary" type="button" :disabled="terminalRunning" @click="runTerminalCommand">
                    {{ terminalRunning ? '执行中…' : '执行命令' }}
                  </button>
                  <button class="btn ghost" type="button" :disabled="!terminalResult" @click="clearTerminalOutput">清屏</button>
                  <span class="subtext">快捷键：Ctrl+L（命令输入框聚焦时）</span>
                </div>
                <pre ref="terminalOutputRef" class="terminal-output">{{ terminalResult || '暂无输出' }}</pre>
              </div>

              <div class="super-pane">
                <h4>服务器文件管理（任意路径）</h4>
                <div class="toolbar">
                  <label class="field grow">
                    <span>当前目录</span>
                    <input v-model.trim="fileManagerPath" type="text" placeholder="/" />
                  </label>
                  <button class="btn ghost" type="button" :disabled="fileManagerLoading" @click="loadSuperFiles">刷新目录</button>
                </div>

                <div class="toolbar">
                  <label class="field grow">
                    <span>创建目录</span>
                    <input v-model.trim="mkdirPath" type="text" placeholder="输入目录绝对路径" />
                  </label>
                  <button class="btn ghost" type="button" @click="createSuperDirectory">创建</button>
                </div>

                <div class="toolbar">
                  <label class="field grow">
                    <span>移动源路径</span>
                    <input v-model.trim="moveSourcePath" type="text" placeholder="源路径" />
                  </label>
                  <label class="field grow">
                    <span>目标路径</span>
                    <input v-model.trim="moveDestinationPath" type="text" placeholder="目标路径" />
                  </label>
                  <button class="btn ghost" type="button" @click="moveSuperItem">移动/重命名</button>
                </div>

                <div class="super-batch-toolbar">
                  <span class="subtext">已选 {{ selectedSuperCount }} 项</span>
                  <button
                    class="btn danger"
                    type="button"
                    :disabled="!selectedSuperCount || fileManagerLoading"
                    @click="batchDeleteSuperItems"
                  >
                    批量删除
                  </button>
                  <label class="field grow">
                    <span>批量移动目标目录</span>
                    <input v-model.trim="batchMoveDestination" type="text" placeholder="例如 /var/www" />
                  </label>
                  <button
                    class="btn ghost"
                    type="button"
                    :disabled="!selectedSuperCount || !batchMoveDestination || fileManagerLoading"
                    @click="batchMoveSuperItems"
                  >
                    批量移动
                  </button>
                </div>

                <div
                  class="super-upload-dropzone"
                  :class="{ dragging: uploadDragging }"
                  @dragover="onUploadDragOver"
                  @dragleave="onUploadDragLeave"
                  @drop="onUploadDrop"
                >
                  <div class="super-upload-title">拖拽文件到此处上传到当前目录</div>
                  <div class="super-upload-actions">
                    <button class="btn ghost" type="button" :disabled="fileManagerLoading" @click="triggerUploadPicker">
                      选择文件上传
                    </button>
                    <span class="subtext">目标目录：{{ fileManagerPath }}</span>
                  </div>
                  <input ref="uploadInputRef" class="super-upload-input" type="file" multiple @change="onUploadInputChange" />
                </div>

                <p v-if="fileManagerMessage" class="message">{{ fileManagerMessage }}</p>
                <div class="super-explorer">
                  <aside class="super-dir-tree">
                    <div class="super-dir-tree-head">目录树</div>
                    <button
                      v-for="row in superDirRows"
                      :key="row.node.key"
                      class="super-tree-row"
                      :class="{ active: selectedSuperDirPath === row.node.path }"
                      :style="{ paddingLeft: `${8 + row.depth * 12}px` }"
                      type="button"
                      @click="selectSuperDir(row.node)"
                      @contextmenu.prevent="openSuperContextMenu($event, 'tree', { path: row.node.path, name: row.node.name, is_dir: true })"
                    >
                      <span class="super-tree-toggle" @click.stop="toggleSuperDirNode(row.node)">
                        {{ row.node.loading ? '…' : (row.node.expanded ? '▾' : '▸') }}
                      </span>
                      <span class="super-tree-label">{{ row.node.name }}</span>
                    </button>
                  </aside>

                  <div class="super-files-wrap" @contextmenu.prevent="openSuperContextMenu($event, 'list', { path: fileManagerPath, name: getItemName(fileManagerPath), is_dir: true })">
                    <table class="audit-table super-files-table">
                      <thead>
                        <tr>
                          <th class="super-select-col">
                            <input
                              type="checkbox"
                              :checked="isAllCurrentSelected"
                              :disabled="!fileManagerItems.length"
                              @change="toggleSelectAllCurrentFiles($event.target.checked)"
                            />
                          </th>
                          <th>名称</th>
                          <th>类型</th>
                          <th>大小</th>
                          <th>操作</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr
                          v-for="item in fileManagerItems"
                          :key="item.path"
                          :class="{ 'super-row-selected': isSuperPathSelected(item.path) }"
                          @contextmenu.prevent="openSuperContextMenu($event, 'list', item)"
                        >
                          <td class="super-select-col">
                            <input
                              type="checkbox"
                              :checked="isSuperPathSelected(item.path)"
                              @click.stop
                              @change="toggleSuperPathSelection(item.path, $event.target.checked)"
                            />
                          </td>
                          <td class="super-path-cell">{{ item.name }}</td>
                          <td>{{ item.is_dir ? '目录' : '文件' }}</td>
                          <td>{{ item.is_dir ? '—' : formatBytes(item.size) }}</td>
                          <td class="super-file-actions">
                            <button class="btn ghost" type="button" @click="openSuperPath(item)">
                              {{ item.is_dir ? '进入' : '打开' }}
                            </button>
                            <button class="btn danger" type="button" @click="deleteSuperItem(item.path)">删除</button>
                          </td>
                        </tr>
                        <tr v-if="!fileManagerItems.length && !fileManagerLoading">
                          <td colspan="5" class="panel-state">目录为空</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                <div
                  v-if="superContextMenu.visible"
                  class="super-context-mask"
                  @click="closeSuperContextMenu"
                  @contextmenu.prevent="closeSuperContextMenu"
                >
                  <div
                    class="super-context-menu"
                    :style="{ left: `${superContextMenu.x}px`, top: `${superContextMenu.y}px` }"
                    @click.stop
                  >
                    <button
                      v-for="item in superContextMenuItems"
                      :key="item.key"
                      class="super-context-item"
                      type="button"
                      @click="performSuperContextAction(item.key)"
                    >
                      {{ item.label }}
                    </button>
                  </div>
                </div>

                <div class="super-editor-wrap">
                  <label class="field grow">
                    <span>当前文件</span>
                    <input v-model="openedSuperFilePath" type="text" placeholder="点击文件后显示路径" />
                  </label>
                  <textarea
                    v-model="openedSuperFileContent"
                    rows="10"
                    class="super-editor"
                    placeholder="文件内容"
                    @input="onSuperFileEditorInput"
                  />
                  <div class="super-editor-actions">
                    <button class="btn primary" type="button" :disabled="!openedSuperFilePath || fileEditorLoading" @click="saveOpenedSuperFile">
                      {{ fileEditorLoading ? '保存中…' : '保存文件' }}
                    </button>
                    <span class="subtext">{{ fileEditorDirty ? '有未保存修改' : '已保存' }}</span>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </section>

        <section v-else-if="activeTab === 'audit'" class="content-block">
          <section class="inner-card">
            <header class="section-header">
              <h3>操作日志与分类统计</h3>
              <button class="btn ghost" type="button" :disabled="auditLoading" @click="reloadAuditData">
                {{ auditLoading ? '加载中…' : '刷新日志' }}
              </button>
            </header>
            <div class="toolbar">
              <label class="field">
                <span>时间范围</span>
                <select v-model.number="auditFilters.days">
                  <option :value="1">最近 1 天</option>
                  <option :value="3">最近 3 天</option>
                  <option :value="7">最近 7 天</option>
                  <option :value="15">最近 15 天</option>
                  <option :value="30">最近 30 天</option>
                </select>
              </label>
              <label class="field">
                <span>用户</span>
                <input v-model.trim="auditFilters.username" type="text" placeholder="用户名" />
              </label>
              <label class="field">
                <span>分类</span>
                <input v-model.trim="auditFilters.category" type="text" placeholder="如 navigation / click" />
              </label>
              <label class="field">
                <span>动作</span>
                <input v-model.trim="auditFilters.action" type="text" placeholder="如 page_open / click" />
              </label>
              <label class="field grow">
                <span>关键字</span>
                <input v-model.trim="auditFilters.keyword" type="text" placeholder="搜索 page/target/detail 等字段" />
              </label>
            </div>
            <div v-if="auditError" class="panel-state error">{{ auditError }}</div>
            <div class="audit-grid">
              <div class="overview-item">
                <span class="label">日志总量</span>
                <strong>{{ auditStats.total }}</strong>
              </div>
              <div class="overview-item">
                <span class="label">分类 TOP</span>
                <ul class="audit-list">
                  <li v-for="item in topCategoryStats" :key="`category-${item.key}`">{{ item.key }}：{{ item.value }}</li>
                  <li v-if="!topCategoryStats.length">暂无数据</li>
                </ul>
              </div>
              <div class="overview-item">
                <span class="label">动作 TOP</span>
                <ul class="audit-list">
                  <li v-for="item in topActionStats" :key="`action-${item.key}`">{{ item.key }}：{{ item.value }}</li>
                  <li v-if="!topActionStats.length">暂无数据</li>
                </ul>
              </div>
              <div class="overview-item">
                <span class="label">用户 TOP</span>
                <ul class="audit-list">
                  <li v-for="item in topUserStats" :key="`user-${item.key}`">{{ item.key }}：{{ item.value }}</li>
                  <li v-if="!topUserStats.length">暂无数据</li>
                </ul>
              </div>
            </div>
            <div class="audit-table-wrap">
              <table class="audit-table">
                <thead>
                  <tr>
                    <th class="col-time">时间</th>
                    <th class="col-user">用户</th>
                    <th class="col-ip">IP</th>
                    <th class="col-category">分类</th>
                    <th class="col-action">动作</th>
                    <th class="col-page">页面</th>
                    <th class="col-target">目标</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, index) in auditEvents" :key="item.id || item.ts || index">
                    <td>{{ item.ts_east8 || formatEast8Time(item.ts) }}</td>
                    <td>{{ item.username || '-' }}</td>
                    <td>{{ item.client_ip || item.ip || '-' }}</td>
                    <td>{{ item.category || '-' }}</td>
                    <td>{{ item.action || '-' }}</td>
                    <td>{{ item.page || '-' }}</td>
                    <td>{{ item.target || (item.detail ? JSON.stringify(item.detail) : '-') }}</td>
                  </tr>
                  <tr v-if="!auditEvents.length && !auditLoading">
                    <td colspan="7" class="panel-state">暂无日志数据</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </section>
      </section>
    </main>
    <AiChatWorkspace
      v-if="showChatBubble"
      title="管理助手"
      :query-mode-enabled="false"
      :send-chat="sendAdminFreeChat"
    />
    <AiAgentSettingsDialog
      v-model="aiSettingsDialogVisible"
      :can-manage="canManageAiSettings"
      :load-settings="loadAiSettingsPayload"
      :save-settings="saveAiSettingsPayload"
      :test-settings="testAiSettingsPayload"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppHeader from '../components/AppHeader.vue'
import AiAgentSettingsDialog from '../components/AiAgentSettingsDialog.vue'
import AiChatWorkspace from '../components/AiChatWorkspace.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { useAuthStore } from '../store/auth'
import {
  batchUpdateAdminDbTable,
  cancelAdminCachePublishJob,
  deleteSuperPath,
  disableAdminCache,
  execSuperCommand,
  getProjectDashboardBizDate,
  getAdminAiSettings,
  testAdminAiSettings,
  getAdminAuditEvents,
  getAdminAuditStats,
  getAdminSystemMetrics,
  getAdminOverview,
  getAdminValidationMasterSwitch,
  listAdminDbTables,
  listAdminFileDirectories,
  listAdminFiles,
  listAdminProjects,
  listSuperFiles,
  makeSuperDirectory,
  moveSuperPath,
  queryAdminDbTable,
  readSuperFile,
  publishAdminDashboardCache,
  refreshAdminCache,
  importProjectTemperatureData,
  commitProjectTemperatureData,
  setAdminValidationMasterSwitch,
  updateAdminAiSettings,
  uploadSuperFiles,
  writeSuperFile,
  runDataAnalysisDialogChat,
} from '../services/api'

const TARGET_PROJECT_KEY = 'daily_report_25_26'
const METRIC_HISTORY_LIMIT = 60
const ROOT_SUPER_PATH = '/'
const SUPER_COMMAND_PRESETS = [
  { label: 'cd /home/ww870411/25-26', command: 'cd /home/ww870411/25-26', cwd: '' },
  { label: 'docker compose down', command: 'docker compose -f lo1_new_server.yml down', cwd: '/home/ww870411/25-26' },
  { label: 'docker compose pull', command: 'docker compose -f lo1_new_server.yml pull', cwd: '/home/ww870411/25-26' },
  { label: 'docker compose up -d', command: 'docker compose -f lo1_new_server.yml up -d', cwd: '/home/ww870411/25-26' },
]
const router = useRouter()
const auth = useAuthStore()
const activeTab = ref('files')

const chatBubbleOverride = ref(null)
const showChatBubble = computed(() => {
  if (typeof chatBubbleOverride.value === 'boolean') return chatBubbleOverride.value
  return false
})

const syncChatBubbleFromSettings = async () => {
  try {
    const payload = await getAdminAiSettings()
    if (payload && typeof payload.show_chat_bubble === 'boolean') {
      chatBubbleOverride.value = payload.show_chat_bubble
    }
  } catch (err) {
    console.error('Failed to sync AI bubble in admin console:', err)
  }
}

const sendAdminFreeChat = (payload) => {
  return runDataAnalysisDialogChat(TARGET_PROJECT_KEY, payload)
}

const loading = ref(false)
const errorMessage = ref('')
const overview = ref(null)
const validationMasterEnabled = ref(true)
const validationPending = ref(false)
const aiSettingsDialogVisible = ref(false)
const cachePending = ref(false)
const publishDays = ref(1)
const refreshDate = ref('')
const dashboardBizDate = ref('')
const bizDateLoading = ref(false)
const temperatureImportBusy = ref(false)
const temperatureImportDialogVisible = ref(false)
const temperatureImportCommitBusy = ref(false)
const temperatureImportPreview = ref(null)
const temperatureImportMessage = ref('')
const temperatureImportStatus = reactive({
  message: '',
  fetchedAt: '',
  dates: [],
  overlapRange: '',
  overlapHours: 0,
  diffCount: 0,
  overlapRecords: [],
  writeMessage: '',
})

const directories = ref([])
const files = ref([])
const selectedFilePath = ref('')
const fileSearch = ref('')
const fileListLoading = ref(false)
const fileMessage = ref('')
const expandedFolderKeys = ref(new Set())
const popupWindowRef = ref(null)
const dbTables = ref([])
const dbSelectedTable = ref('monthly_data_show')
const dbColumns = ref([])
const dbPkColumns = ref([])
const dbRowsOriginal = ref([])
const dbRowsDraft = ref([])
const dbLimit = ref(200)
const dbOffset = ref(0)
const dbTotal = ref(0)
const dbLoading = ref(false)
const dbSaving = ref(false)
const dbMessage = ref('')
const dbSearchText = ref('')
const dbOrderBy = ref('')
const dbOrderDir = ref('asc')
const dbFilters = ref([])
dbFilters.value = [{ column: '', op: 'contains', value: '' }]

const projects = ref([])
const selectedProjectKey = ref(TARGET_PROJECT_KEY)
const systemLoading = ref(false)
const systemError = ref('')
const systemMetrics = ref(null)
const systemAutoRefresh = ref(true)
const auditLoading = ref(false)
const auditError = ref('')
const auditEvents = ref([])
const auditStats = reactive({
  total: 0,
  by_category: {},
  by_action: {},
  by_user: {},
  by_page: {},
})
const auditFilters = reactive({
  days: 7,
  username: '',
  category: '',
  action: '',
  keyword: '',
  limit: 300,
})
const metricHistory = reactive({
  cpu: [],
  memory: [],
  disk: [],
  processCpu: [],
})
let systemTimer = null
const superMessage = ref('')
const terminalCommand = ref('')
const terminalCwd = ref('')
const terminalTimeout = ref(20)
const terminalResult = ref('')
const terminalRunning = ref(false)
const terminalOutputRef = ref(null)
const fileManagerPath = ref('/')
const fileManagerItems = ref([])
const fileManagerLoading = ref(false)
const fileManagerMessage = ref('')
const openedSuperFilePath = ref('')
const openedSuperFileContent = ref('')
const fileEditorDirty = ref(false)
const fileEditorLoading = ref(false)
const mkdirPath = ref('')
const moveSourcePath = ref('')
const moveDestinationPath = ref('')
const selectedCommandPreset = ref('')
const selectedSuperDirPath = ref(ROOT_SUPER_PATH)
const selectedSuperPaths = ref([])
const batchMoveDestination = ref('')
const uploadDragging = ref(false)
const uploadInputRef = ref(null)
const superContextMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  scope: '',
  item: null,
})
const superDirTreeRoots = ref([
  {
    key: ROOT_SUPER_PATH,
    path: ROOT_SUPER_PATH,
    name: ROOT_SUPER_PATH,
    expanded: false,
    loading: false,
    loaded: false,
    children: [],
  },
])
const superDirRows = computed(() => {
  const rows = []
  const visit = (nodes, depth) => {
    for (const node of nodes || []) {
      rows.push({ node, depth })
      if (node.expanded) {
        visit(node.children || [], depth + 1)
      }
    }
  }
  visit(superDirTreeRoots.value, 0)
  return rows
})
const superContextMenuItems = computed(() => {
  const item = superContextMenu.item
  if (!item) return []
  const isDir = Boolean(item?.is_dir)
  const rows = []
  rows.push({ key: 'open', label: isDir ? '进入目录' : '打开文件' })
  if (isDir) rows.push({ key: 'new_folder', label: '新建子目录' })
  rows.push({ key: 'rename', label: '重命名' })
  rows.push({ key: 'delete', label: '删除' })
  rows.push({ key: 'copy_path', label: '复制路径' })
  rows.push({ key: 'refresh', label: '刷新' })
  return rows
})
const selectedSuperPathSet = computed(() => new Set(selectedSuperPaths.value))
const selectedSuperCount = computed(() => selectedSuperPaths.value.length)
const isAllCurrentSelected = computed(() => {
  const items = fileManagerItems.value || []
  if (!items.length) return false
  return items.every((item) => selectedSuperPathSet.value.has(String(item?.path || '')))
})

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '管理后台', to: null },
])

const canManageValidation = computed(() => auth.canManageValidationFor(TARGET_PROJECT_KEY))
const canManageAiSettings = computed(() => auth.canManageAiSettingsFor(TARGET_PROJECT_KEY))
const canManageCache = computed(() => auth.canPublishFor(TARGET_PROJECT_KEY))
const loadAiSettingsPayload = () => getAdminAiSettings()
const saveAiSettingsPayload = async (payload) => {
  const saved = await updateAdminAiSettings(payload)
  if (saved && typeof saved.show_chat_bubble === 'boolean') {
    chatBubbleOverride.value = saved.show_chat_bubble
  }
  return saved
}
const testAiSettingsPayload = (payload) => testAdminAiSettings(payload)

const filteredFiles = computed(() => {
  const keyword = fileSearch.value.trim().toLowerCase()
  if (!keyword) return files.value
  return files.value.filter((item) => String(item?.path || '').toLowerCase().includes(keyword))
})

const fileTree = computed(() => {
  const roots = []
  const folderMap = new Map()

  const ensureFolder = (folderKey, folderName, parentChildren) => {
    const existing = folderMap.get(folderKey)
    if (existing) return existing
    const node = { type: 'folder', key: folderKey, name: folderName, children: [] }
    folderMap.set(folderKey, node)
    parentChildren.push(node)
    return node
  }

  for (const dir of directories.value) {
    const name = String(dir || '').trim()
    if (!name) continue
    ensureFolder(`folder:${name}`, name, roots)
  }

  for (const item of filteredFiles.value) {
    const fullPath = String(item?.path || '')
    if (!fullPath) continue
    const parts = fullPath.split('/').filter(Boolean)
    if (!parts.length) continue

    let parentChildren = roots
    let accum = ''
    for (let index = 0; index < parts.length; index += 1) {
      const part = parts[index]
      const isLast = index === parts.length - 1
      accum = accum ? `${accum}/${part}` : part
      if (isLast) {
        parentChildren.push({ type: 'file', key: `file:${fullPath}`, name: part, path: fullPath })
      } else {
        const folderNode = ensureFolder(`folder:${accum}`, part, parentChildren)
        parentChildren = folderNode.children
      }
    }
  }

  const sortNodes = (nodes) => {
    nodes.sort((a, b) => {
      if (a.type !== b.type) return a.type === 'folder' ? -1 : 1
      return a.name.localeCompare(b.name, 'zh-CN')
    })
    for (const node of nodes) {
      if (node.type === 'folder') sortNodes(node.children)
    }
  }
  sortNodes(roots)
  return roots
})

const visibleTreeRows = computed(() => {
  const rows = []
  const visit = (nodes, depth) => {
    for (const node of nodes) {
      if (node.type === 'folder') {
        const expanded = expandedFolderKeys.value.has(node.key)
        rows.push({ type: 'folder', key: node.key, name: node.name, depth, expanded })
        if (expanded) visit(node.children, depth + 1)
      } else {
        rows.push({ type: 'file', key: node.key, name: node.name, path: node.path, depth })
      }
    }
  }
  visit(fileTree.value, 0)
  return rows
})

const cacheJobStatus = computed(() => {
  const job = overview.value?.cache_publish_job || {}
  const status = job.status
  if (!status) return '暂无任务'
  const total = Number(job.total || 0)
  const processed = Number(job.processed || 0)
  const label = job.current_label ? `，${job.current_label}` : ''
  return `${status}（${processed}/${total}${label}）`
})
const cacheWorkerGroups = computed(() => {
  const groups = overview.value?.cache_publish_job?.worker_groups
  if (!Array.isArray(groups)) return []
  return groups.map((group) => ({
    key: group?.key || '',
    label: group?.label || '未命名分块',
    status: group?.status || 'pending',
    message: group?.message || '',
    updatedAt: group?.updated_at || '',
    sectionsText: Array.isArray(group?.sections) ? group.sections.join(' / ') : '',
  }))
})
const cacheJobLogs = computed(() => {
  const logs = overview.value?.cache_publish_job?.logs
  if (!Array.isArray(logs)) return []
  return logs.slice(-20)
})
const formatCacheWorkerStatus = (status) => {
  if (status === 'running') return '进行中'
  if (status === 'completed') return '已完成'
  if (status === 'failed') return '失败'
  if (status === 'aborted') return '已中止'
  return '待执行'
}
const dbPkSet = computed(() => new Set((dbPkColumns.value || []).map((x) => String(x || ''))))
const dbColumnTypeMap = computed(() => {
  const map = {}
  for (const col of dbColumns.value || []) {
    const name = String(col?.name || '')
    if (!name) continue
    map[name] = String(col?.data_type || '').toLowerCase()
  }
  return map
})
const dbDirtyStats = computed(() => {
  const updates = collectDbUpdates()
  return { dirtyRows: updates.length, updates }
})

function asTopList(record, limit = 5) {
  if (!record || typeof record !== 'object') return []
  return Object.entries(record)
    .map(([key, value]) => ({ key, value: Number(value) || 0 }))
    .sort((a, b) => b.value - a.value)
    .slice(0, limit)
}

const topCategoryStats = computed(() => asTopList(auditStats.by_category, 6))
const topActionStats = computed(() => asTopList(auditStats.by_action, 6))
const topUserStats = computed(() => asTopList(auditStats.by_user, 6))

function actionLabel(flag) {
  return flag ? '已授权' : '未授权'
}

function formatPercent(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return '—'
  return `${n.toFixed(2)}%`
}

function formatBytes(value) {
  const n = Number(value)
  if (!Number.isFinite(n) || n < 0) return '—'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = n
  let idx = 0
  while (size >= 1024 && idx < units.length - 1) {
    size /= 1024
    idx += 1
  }
  return `${size.toFixed(size >= 100 || idx === 0 ? 0 : 2)} ${units[idx]}`
}

function formatUptime(value) {
  const total = Number(value)
  if (!Number.isFinite(total) || total < 0) return '—'
  const day = Math.floor(total / 86400)
  const hour = Math.floor((total % 86400) / 3600)
  const minute = Math.floor((total % 3600) / 60)
  const second = Math.floor(total % 60)
  if (day > 0) return `${day}天 ${hour}时 ${minute}分`
  if (hour > 0) return `${hour}时 ${minute}分 ${second}秒`
  if (minute > 0) return `${minute}分 ${second}秒`
  return `${second}秒`
}

function formatEast8Time(value) {
  const raw = String(value || '').trim()
  if (!raw) return '—'
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return raw
  const parts = new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).formatToParts(date)
  const pick = (type) => parts.find((item) => item.type === type)?.value || ''
  return `${pick('year')}-${pick('month')}-${pick('day')} ${pick('hour')}:${pick('minute')}:${pick('second')}`
}

function pushHistory(arr, value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return
  arr.push(Math.max(0, Math.min(100, n)))
  if (arr.length > METRIC_HISTORY_LIMIT) {
    arr.splice(0, arr.length - METRIC_HISTORY_LIMIT)
  }
}

function updateMetricHistory(metrics) {
  if (!metrics || typeof metrics !== 'object') return
  pushHistory(metricHistory.cpu, metrics?.cpu?.percent)
  pushHistory(metricHistory.memory, metrics?.memory?.percent)
  pushHistory(metricHistory.disk, metrics?.disk?.percent)
  pushHistory(metricHistory.processCpu, metrics?.process?.cpu_percent)
}

function sparkPoints(series) {
  if (!Array.isArray(series) || series.length === 0) return ''
  const width = 160
  const height = 44
  const xStep = series.length <= 1 ? 0 : width / (series.length - 1)
  return series
    .map((value, index) => {
      const x = index * xStep
      const y = height - (Math.max(0, Math.min(100, Number(value))) / 100) * height
      return `${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(' ')
}

function toggleFolder(folderKey) {
  const next = new Set(expandedFolderKeys.value)
  if (next.has(folderKey)) next.delete(folderKey)
  else next.add(folderKey)
  expandedFolderKeys.value = next
}

function onTreeRowClick(row) {
  if (row.type === 'folder') {
    toggleFolder(row.key)
    return
  }
  openFileEditor(row.path)
}

async function loadProjectSettings() {
  if (selectedProjectKey.value !== TARGET_PROJECT_KEY) return
  loading.value = true
  errorMessage.value = ''
  try {
    const payload = await getAdminOverview(TARGET_PROJECT_KEY)
    overview.value = payload
    validationMasterEnabled.value = Boolean(payload?.validation?.master_enabled)
    await syncDashboardBizDate({ silent: true })
  } catch (err) {
    console.error(err)
    errorMessage.value = err instanceof Error ? err.message : '加载管理后台失败'
  } finally {
    loading.value = false
  }
}

async function syncDashboardBizDate(options = {}) {
  if (!canManageCache.value) return
  const silent = Boolean(options?.silent)
  bizDateLoading.value = true
  if (!silent) temperatureImportMessage.value = ''
  try {
    const payload = await getProjectDashboardBizDate(TARGET_PROJECT_KEY)
    const next = typeof payload?.set_biz_date === 'string' ? payload.set_biz_date.trim() : ''
    dashboardBizDate.value = next
    refreshDate.value = next
    if (!silent && next) temperatureImportMessage.value = `业务日期已同步：${next}`
  } catch (err) {
    console.error(err)
    if (!silent) temperatureImportMessage.value = err instanceof Error ? err.message : '读取业务日期失败'
  } finally {
    bizDateLoading.value = false
  }
}

async function selectProject(projectKey) {
  selectedProjectKey.value = String(projectKey || '')
  if (selectedProjectKey.value === TARGET_PROJECT_KEY) {
    await loadProjectSettings()
    if (canManageValidation.value) {
      const payload = await getAdminValidationMasterSwitch()
      validationMasterEnabled.value = Boolean(payload?.validation_enabled)
    }
  }
}

function openAiSettingsDialog() {
  if (!canManageAiSettings.value) return
  aiSettingsDialogVisible.value = true
}

async function loadProjects() {
  try {
    const payload = await listAdminProjects()
    projects.value = Array.isArray(payload?.projects) ? payload.projects : []
    const hasTarget = projects.value.some((item) => item.project_key === TARGET_PROJECT_KEY)
    if (!hasTarget) {
      projects.value.unshift({ project_key: TARGET_PROJECT_KEY, project_name: '2025-2026供暖期生产日报' })
    }
  } catch (err) {
    console.error(err)
    projects.value = [{ project_key: TARGET_PROJECT_KEY, project_name: '2025-2026供暖期生产日报' }]
  }
}

async function loadDirectories() {
  fileListLoading.value = true
  fileMessage.value = ''
  try {
    const payload = await listAdminFileDirectories()
    const allDirectories = Array.isArray(payload?.directories) ? payload.directories : []
    directories.value = allDirectories

    const merged = new Map()
    const failed = []
    const results = await Promise.allSettled(
      allDirectories.map(async (dir) => {
        const resp = await listAdminFiles(dir)
        const rows = Array.isArray(resp?.files) ? resp.files : []
        return { dir, rows }
      }),
    )
    for (const result of results) {
      if (result.status === 'fulfilled') {
        for (const row of result.value.rows) {
          const key = String(row?.path || '')
          if (!key) continue
          merged.set(key, row)
        }
      } else {
        failed.push(String(result.reason?.message || '未知错误'))
      }
    }
    files.value = Array.from(merged.values())
    expandedFolderKeys.value = new Set(
      allDirectories.map((dir) => `folder:${String(dir || '').trim()}`).filter(Boolean),
    )
    if (failed.length) {
      fileMessage.value = `部分目录读取失败：${failed[0]}`
    }
  } catch (err) {
    console.error(err)
    files.value = []
    fileMessage.value = err instanceof Error ? err.message : '目录读取失败'
  } finally {
    fileListLoading.value = false
  }
}

function isDbPkColumn(columnName) {
  return dbPkSet.value.has(String(columnName || ''))
}

function buildDbRowKey(row, fallbackIndex = 0) {
  const pkCols = dbPkColumns.value || []
  if (!pkCols.length) {
    return `row:${fallbackIndex}`
  }
  return pkCols.map((col) => `${col}=${JSON.stringify(row?.[col] ?? null)}`).join('|')
}

function normalizeDbDraftValue(rawValue, dataType) {
  const type = String(dataType || '').toLowerCase()
  if (rawValue === null || rawValue === undefined) return null
  if (typeof rawValue !== 'string') return rawValue
  const text = rawValue.trim()
  if (!text) {
    if (type.includes('char') || type.includes('text')) return ''
    return null
  }
  if (type.includes('int') || type.includes('numeric') || type.includes('double') || type.includes('real') || type.includes('decimal')) {
    const value = Number(text)
    return Number.isFinite(value) ? value : rawValue
  }
  if (type.includes('bool')) {
    const lowered = text.toLowerCase()
    if (['true', 't', '1', 'yes', 'y'].includes(lowered)) return true
    if (['false', 'f', '0', 'no', 'n'].includes(lowered)) return false
    return rawValue
  }
  if (type.includes('json')) {
    try {
      return JSON.parse(text)
    } catch (_error) {
      return rawValue
    }
  }
  return rawValue
}

function createDbFilterItem() {
  return { column: '', op: 'contains', value: '' }
}

function normalizeDbQueryFilters() {
  const normalized = []
  for (const raw of dbFilters.value || []) {
    const column = String(raw?.column || '').trim()
    const op = String(raw?.op || '').trim()
    const value = raw?.value ?? ''
    if (!column || !op) continue
    if (op !== 'is_null' && op !== 'not_null' && String(value).trim() === '') continue
    normalized.push({ column, op, value })
  }
  return normalized
}

function addDbFilterRow() {
  dbFilters.value = [...(dbFilters.value || []), createDbFilterItem()]
}

function removeDbFilterRow(index) {
  const rows = [...(dbFilters.value || [])]
  if (index < 0 || index >= rows.length) return
  rows.splice(index, 1)
  dbFilters.value = rows.length ? rows : [createDbFilterItem()]
}

function resetDbFilters() {
  dbFilters.value = [createDbFilterItem()]
}

function collectDbUpdates() {
  const originalRows = dbRowsOriginal.value || []
  const draftRows = dbRowsDraft.value || []
  const updates = []
  const maxLen = Math.min(originalRows.length, draftRows.length)
  for (let idx = 0; idx < maxLen; idx += 1) {
    const original = originalRows[idx] || {}
    const draft = draftRows[idx] || {}
    const key = {}
    let keyValid = true
    for (const pk of dbPkColumns.value || []) {
      if (!(pk in original)) {
        keyValid = false
        break
      }
      key[pk] = original[pk]
    }
    if (!keyValid) continue
    const changes = {}
    for (const col of dbColumns.value || []) {
      const colName = String(col?.name || '')
      if (!colName || isDbPkColumn(colName)) continue
      const oldValue = original[colName]
      const newValue = normalizeDbDraftValue(draft[colName], col?.data_type)
      if (JSON.stringify(oldValue) === JSON.stringify(newValue)) continue
      changes[colName] = newValue
    }
    if (Object.keys(changes).length > 0) {
      updates.push({ key, changes })
    }
  }
  return updates
}

async function loadDbTables() {
  dbMessage.value = ''
  try {
    const payload = await listAdminDbTables()
    const tables = Array.isArray(payload?.tables) ? payload.tables : []
    dbTables.value = tables
    if (tables.length === 0) {
      dbSelectedTable.value = ''
      return
    }
    if (!tables.includes(dbSelectedTable.value)) {
      dbSelectedTable.value = tables.includes('monthly_data_show') ? 'monthly_data_show' : tables[0]
    }
  } catch (err) {
    console.error(err)
    dbMessage.value = err instanceof Error ? err.message : '加载数据库表失败'
  }
}

async function loadDbRows() {
  if (!dbSelectedTable.value) {
    dbMessage.value = '请先选择数据表'
    return
  }
  dbLoading.value = true
  dbMessage.value = ''
  try {
    const payload = await queryAdminDbTable({
      table: dbSelectedTable.value,
      limit: dbLimit.value,
      offset: dbOffset.value,
      search: dbSearchText.value,
      filters: normalizeDbQueryFilters(),
      order_by: dbOrderBy.value,
      order_dir: dbOrderDir.value,
    })
    dbColumns.value = Array.isArray(payload?.columns) ? payload.columns : []
    dbPkColumns.value = Array.isArray(payload?.pk_columns) ? payload.pk_columns : []
    const validColumns = new Set(dbColumns.value.map((x) => String(x?.name || '')))
    if (dbOrderBy.value && !validColumns.has(dbOrderBy.value)) {
      dbOrderBy.value = ''
    }
    const rows = Array.isArray(payload?.rows) ? payload.rows : []
    dbRowsOriginal.value = rows
    dbRowsDraft.value = rows.map((row) => ({ ...row }))
    dbTotal.value = Number(payload?.total || 0)
    dbMessage.value = `已加载 ${rows.length} 行（总计 ${dbTotal.value}）`
  } catch (err) {
    console.error(err)
    dbRowsOriginal.value = []
    dbRowsDraft.value = []
    dbColumns.value = []
    dbPkColumns.value = []
    dbTotal.value = 0
    dbMessage.value = err instanceof Error ? err.message : '读取表数据失败'
  } finally {
    dbLoading.value = false
  }
}

async function saveDbRows() {
  if (!dbSelectedTable.value) return
  const updates = collectDbUpdates()
  if (!updates.length) {
    dbMessage.value = '没有可保存的修改'
    return
  }
  dbSaving.value = true
  try {
    const payload = await batchUpdateAdminDbTable({
      table: dbSelectedTable.value,
      updates,
    })
    const failedCount = Array.isArray(payload?.failed) ? payload.failed.length : 0
    dbMessage.value = `保存完成：更新 ${Number(payload?.updated || 0)} 行，命中 ${Number(payload?.matched || 0)} 条记录${failedCount ? `，失败 ${failedCount} 项` : ''}`
    await loadDbRows()
  } catch (err) {
    console.error(err)
    dbMessage.value = err instanceof Error ? err.message : '保存表数据失败'
  } finally {
    dbSaving.value = false
  }
}

async function loadSystemMetrics() {
  if (systemLoading.value) return
  systemLoading.value = true
  systemError.value = ''
  try {
    const payload = await getAdminSystemMetrics()
    systemMetrics.value = payload?.metrics || null
    updateMetricHistory(systemMetrics.value)
  } catch (err) {
    console.error(err)
    systemError.value = err instanceof Error ? err.message : '获取系统指标失败'
  } finally {
    systemLoading.value = false
  }
}

async function runTerminalCommand() {
  const cmd = String(terminalCommand.value || '').trim()
  if (!cmd) {
    superMessage.value = '请输入要执行的命令'
    return
  }
  terminalRunning.value = true
  try {
    const payload = await execSuperCommand({
      command: cmd,
      cwd: terminalCwd.value,
      timeout_seconds: terminalTimeout.value,
    })
    const output = [
      `$ ${cmd}`,
      `returncode: ${payload?.returncode ?? 'null'}${payload?.timeout ? ' (timeout)' : ''}`,
      '',
      payload?.stdout ? `STDOUT:\n${payload.stdout}` : 'STDOUT:\n<empty>',
      '',
      payload?.stderr ? `STDERR:\n${payload.stderr}` : 'STDERR:\n<empty>',
    ].join('\n')
    appendTerminalOutput(output)
  } catch (err) {
    console.error(err)
    appendTerminalOutput(err instanceof Error ? err.message : '命令执行失败')
  } finally {
    terminalRunning.value = false
  }
}

function appendTerminalOutput(block) {
  const text = String(block || '').trim()
  if (!text) return
  terminalResult.value = terminalResult.value ? `${terminalResult.value}\n\n${text}` : text
  nextTick(() => {
    const el = terminalOutputRef.value
    if (el && typeof el.scrollTop === 'number') {
      el.scrollTop = el.scrollHeight
    }
  })
}

function clearTerminalOutput() {
  terminalResult.value = ''
}

function applySelectedCommandPreset() {
  const label = String(selectedCommandPreset.value || '')
  const preset = SUPER_COMMAND_PRESETS.find((item) => item.label === label)
  if (!preset) return
  terminalCommand.value = preset.command
  if (preset.cwd) {
    terminalCwd.value = preset.cwd
  }
}

function buildTreeNode(path, name) {
  return {
    key: path,
    path,
    name,
    expanded: false,
    loading: false,
    loaded: false,
    children: [],
  }
}

async function loadNodeChildren(node) {
  if (!node || node.loading || node.loaded) return
  node.loading = true
  try {
    const payload = await listSuperFiles(node.path)
    const items = Array.isArray(payload?.items) ? payload.items : []
    node.children = items
      .filter((item) => Boolean(item?.is_dir))
      .map((item) => buildTreeNode(String(item.path || ''), String(item.name || '')))
    node.loaded = true
  } catch (err) {
    console.error(err)
    fileManagerMessage.value = err instanceof Error ? err.message : '目录树加载失败'
    node.children = []
    node.loaded = false
  } finally {
    node.loading = false
  }
}

async function toggleSuperDirNode(node) {
  if (!node) return
  node.expanded = !node.expanded
  if (node.expanded) {
    await loadNodeChildren(node)
  }
}

function splitPathSegments(path) {
  const normalized = String(path || '').replace(/\\/g, '/')
  if (!normalized) return []
  if (/^[a-zA-Z]:\//.test(normalized)) {
    const drive = normalized.slice(0, 2)
    const rest = normalized.slice(2).split('/').filter(Boolean)
    return [drive, ...rest]
  }
  return normalized.split('/').filter(Boolean)
}

function isWindowsDrivePath(path) {
  return /^[a-zA-Z]:\\?$/.test(String(path || ''))
}

function joinPath(base, segment) {
  const b = String(base || '')
  if (!segment) return b
  if (b === '/') return `/${segment}`
  if (isWindowsDrivePath(b)) return `${b}\\${segment}`
  return `${b.replace(/[\\/]+$/, '')}/${segment}`
}

function findTreeNodeByPath(path) {
  const target = String(path || '')
  const stack = [...superDirTreeRoots.value]
  while (stack.length) {
    const node = stack.pop()
    if (!node) continue
    if (String(node.path || '') === target) return node
    if (Array.isArray(node.children) && node.children.length) {
      stack.push(...node.children)
    }
  }
  return null
}

function resetTreeLoadedState(nodes) {
  for (const node of nodes || []) {
    node.loaded = false
    node.loading = false
    node.children = []
  }
}

async function ensureTreePath(path) {
  const roots = superDirTreeRoots.value
  if (!roots.length) return
  const root = roots[0]
  const targetPath = String(path || ROOT_SUPER_PATH)
  root.expanded = true
  await loadNodeChildren(root)
  if (targetPath === ROOT_SUPER_PATH) return

  const segments = splitPathSegments(targetPath)
  if (!segments.length) return

  let cursor = root
  let currentPath = ROOT_SUPER_PATH
  for (const segment of segments) {
    currentPath = joinPath(currentPath, segment)
    await loadNodeChildren(cursor)
    const child = (cursor.children || []).find((item) => String(item.path || '') === currentPath)
    if (!child) break
    child.expanded = true
    cursor = child
  }
}

async function refreshSuperTree(targetPath = '') {
  const path = String(targetPath || selectedSuperDirPath.value || ROOT_SUPER_PATH)
  resetTreeLoadedState(superDirTreeRoots.value)
  await ensureTreePath(path)
}

async function selectSuperDir(node) {
  if (!node) return
  selectedSuperDirPath.value = String(node.path || ROOT_SUPER_PATH)
  fileManagerPath.value = selectedSuperDirPath.value
  await loadSuperFiles()
}

async function loadSuperFiles() {
  fileManagerLoading.value = true
  fileManagerMessage.value = ''
  try {
    const payload = await listSuperFiles(fileManagerPath.value)
    fileManagerPath.value = String(payload?.path || fileManagerPath.value)
    selectedSuperDirPath.value = fileManagerPath.value
    fileManagerItems.value = Array.isArray(payload?.items) ? payload.items : []
    selectedSuperPaths.value = []
    await ensureTreePath(fileManagerPath.value)
  } catch (err) {
    console.error(err)
    fileManagerMessage.value = err instanceof Error ? err.message : '目录读取失败'
    fileManagerItems.value = []
  } finally {
    fileManagerLoading.value = false
  }
}

async function openSuperPath(item) {
  if (!item) return
  if (item.is_dir) {
    const fakeNode = buildTreeNode(String(item.path || ''), String(item.name || ''))
    await selectSuperDir(fakeNode)
    return
  }
  fileEditorLoading.value = true
  fileManagerMessage.value = ''
  try {
    const payload = await readSuperFile(item.path)
    openedSuperFilePath.value = String(payload?.path || item.path || '')
    openedSuperFileContent.value = String(payload?.content || '')
    fileEditorDirty.value = false
  } catch (err) {
    console.error(err)
    fileManagerMessage.value = err instanceof Error ? err.message : '读取文件失败'
  } finally {
    fileEditorLoading.value = false
  }
}

async function saveOpenedSuperFile() {
  if (!openedSuperFilePath.value) return
  fileEditorLoading.value = true
  try {
    await writeSuperFile(openedSuperFilePath.value, openedSuperFileContent.value)
    fileEditorDirty.value = false
    fileManagerMessage.value = `保存成功：${openedSuperFilePath.value}`
    await loadSuperFiles()
  } catch (err) {
    console.error(err)
    fileManagerMessage.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    fileEditorLoading.value = false
  }
}

async function createSuperDirectory() {
  const target = String(mkdirPath.value || '').trim()
  if (!target) return
  await createSuperDirectoryFromPath(target)
  mkdirPath.value = ''
}

async function moveSuperItem() {
  const source = String(moveSourcePath.value || '').trim()
  const destination = String(moveDestinationPath.value || '').trim()
  if (!source || !destination) return
  await moveSuperItemByPath(source, destination)
  moveSourcePath.value = ''
  moveDestinationPath.value = ''
}

async function deleteSuperItem(path) {
  const target = String(path || '').trim()
  if (!target) return
  try {
    await deleteSuperPath(target)
    fileManagerMessage.value = `已删除：${target}`
    if (openedSuperFilePath.value === target) {
      openedSuperFilePath.value = ''
      openedSuperFileContent.value = ''
      fileEditorDirty.value = false
    }
    await loadSuperFiles()
    await refreshSuperTree(fileManagerPath.value)
  } catch (err) {
    console.error(err)
    fileManagerMessage.value = err instanceof Error ? err.message : '删除失败'
  }
}

function onSuperFileEditorInput() {
  fileEditorDirty.value = true
}

function normalizePathForUi(path) {
  return String(path || '').replace(/\\/g, '/')
}

function getItemParentPath(path) {
  const normalized = normalizePathForUi(path).replace(/\/+$/, '')
  if (!normalized || normalized === '/') return ROOT_SUPER_PATH
  if (/^[a-zA-Z]:$/.test(normalized)) return normalized
  const index = normalized.lastIndexOf('/')
  if (index <= 0) {
    if (/^[a-zA-Z]:/.test(normalized)) return normalized.slice(0, 2)
    return ROOT_SUPER_PATH
  }
  return normalized.slice(0, index)
}

function getItemName(path) {
  const normalized = normalizePathForUi(path).replace(/\/+$/, '')
  if (!normalized || normalized === '/') return normalized || ROOT_SUPER_PATH
  const index = normalized.lastIndexOf('/')
  if (index < 0) return normalized
  return normalized.slice(index + 1)
}

function openSuperContextMenu(event, scope, item) {
  const payload = {
    path: String(item?.path || ''),
    name: String(item?.name || getItemName(item?.path)),
    is_dir: Boolean(item?.is_dir),
    scope: scope || '',
    raw: item || null,
  }
  if (!payload.path) return
  superContextMenu.visible = true
  superContextMenu.x = Number(event?.clientX || 0)
  superContextMenu.y = Number(event?.clientY || 0)
  superContextMenu.scope = scope || ''
  superContextMenu.item = payload
}

function closeSuperContextMenu() {
  superContextMenu.visible = false
  superContextMenu.x = 0
  superContextMenu.y = 0
  superContextMenu.scope = ''
  superContextMenu.item = null
}

function isSuperPathSelected(path) {
  return selectedSuperPathSet.value.has(String(path || ''))
}

function toggleSuperPathSelection(path, checked) {
  const target = String(path || '')
  if (!target) return
  const set = new Set(selectedSuperPaths.value)
  if (checked) set.add(target)
  else set.delete(target)
  selectedSuperPaths.value = Array.from(set)
}

function toggleSelectAllCurrentFiles(checked) {
  if (!checked) {
    selectedSuperPaths.value = []
    return
  }
  selectedSuperPaths.value = (fileManagerItems.value || [])
    .map((item) => String(item.path || ''))
    .filter(Boolean)
}

async function performSuperContextAction(actionKey) {
  const item = superContextMenu.item
  closeSuperContextMenu()
  if (!item || !actionKey) return
  const targetPath = String(item.path || '')
  if (!targetPath) return

  if (actionKey === 'open') {
    await openSuperPath({ path: targetPath, name: item.name, is_dir: item.is_dir })
    return
  }

  if (actionKey === 'refresh') {
    await refreshSuperTree(selectedSuperDirPath.value)
    await loadSuperFiles()
    return
  }

  if (actionKey === 'copy_path') {
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(targetPath)
        fileManagerMessage.value = `已复制路径：${targetPath}`
      }
    } catch (err) {
      console.warn('复制路径失败', err)
      fileManagerMessage.value = '复制路径失败'
    }
    return
  }

  if (actionKey === 'new_folder') {
    const folderName = String(window.prompt('请输入新目录名称', 'new_folder') || '').trim()
    if (!folderName) return
    const parent = item.is_dir ? targetPath : getItemParentPath(targetPath)
    await createSuperDirectoryFromPath(joinPath(parent, folderName))
    return
  }

  if (actionKey === 'rename') {
    const currentName = item.name || getItemName(targetPath)
    const nextName = String(window.prompt('请输入新名称', currentName) || '').trim()
    if (!nextName || nextName === currentName) return
    const destination = joinPath(getItemParentPath(targetPath), nextName)
    await moveSuperItemByPath(targetPath, destination)
    return
  }

  if (actionKey === 'delete') {
    const confirmed = window.confirm(`确认删除：${targetPath} ?`)
    if (!confirmed) return
    await deleteSuperItem(targetPath)
  }
}

async function createSuperDirectoryFromPath(target) {
  const path = String(target || '').trim()
  if (!path) return
  try {
    await makeSuperDirectory(path)
    fileManagerMessage.value = `目录已创建：${path}`
    await loadSuperFiles()
    await refreshSuperTree(fileManagerPath.value)
  } catch (err) {
    console.error(err)
    fileManagerMessage.value = err instanceof Error ? err.message : '创建目录失败'
  }
}

async function moveSuperItemByPath(source, destination) {
  const src = String(source || '').trim()
  const dst = String(destination || '').trim()
  if (!src || !dst) return
  try {
    await moveSuperPath(src, dst)
    fileManagerMessage.value = `移动成功：${src} -> ${dst}`
    if (openedSuperFilePath.value === src) {
      openedSuperFilePath.value = dst
    }
    await loadSuperFiles()
    await refreshSuperTree(fileManagerPath.value)
  } catch (err) {
    console.error(err)
    fileManagerMessage.value = err instanceof Error ? err.message : '移动失败'
  }
}

async function batchDeleteSuperItems() {
  const targets = Array.from(new Set(selectedSuperPaths.value)).filter(Boolean)
  if (!targets.length) {
    fileManagerMessage.value = '请先选择要删除的项'
    return
  }
  const confirmed = window.confirm(`确认批量删除 ${targets.length} 项吗？`)
  if (!confirmed) return
  const failed = []
  for (const target of targets) {
    try {
      // eslint-disable-next-line no-await-in-loop
      await deleteSuperPath(target)
      if (openedSuperFilePath.value === target) {
        openedSuperFilePath.value = ''
        openedSuperFileContent.value = ''
        fileEditorDirty.value = false
      }
    } catch (err) {
      console.error(err)
      failed.push(target)
    }
  }
  selectedSuperPaths.value = []
  if (failed.length) {
    fileManagerMessage.value = `批量删除完成，失败 ${failed.length} 项`
  } else {
    fileManagerMessage.value = `批量删除成功：${targets.length} 项`
  }
  await loadSuperFiles()
  await refreshSuperTree(fileManagerPath.value)
}

async function batchMoveSuperItems() {
  const targets = Array.from(new Set(selectedSuperPaths.value)).filter(Boolean)
  const destinationDir = String(batchMoveDestination.value || '').trim()
  if (!targets.length) {
    fileManagerMessage.value = '请先选择要移动的项'
    return
  }
  if (!destinationDir) {
    fileManagerMessage.value = '请先填写批量移动目标目录'
    return
  }
  const failed = []
  for (const source of targets) {
    const destination = joinPath(destinationDir, getItemName(source))
    try {
      // eslint-disable-next-line no-await-in-loop
      await moveSuperPath(source, destination)
      if (openedSuperFilePath.value === source) {
        openedSuperFilePath.value = destination
      }
    } catch (err) {
      console.error(err)
      failed.push(source)
    }
  }
  selectedSuperPaths.value = []
  if (failed.length) {
    fileManagerMessage.value = `批量移动完成，失败 ${failed.length} 项`
  } else {
    fileManagerMessage.value = `批量移动成功：${targets.length} 项`
  }
  await loadSuperFiles()
  await refreshSuperTree(fileManagerPath.value)
}

function triggerUploadPicker() {
  if (!uploadInputRef.value) return
  uploadInputRef.value.value = ''
  uploadInputRef.value.click()
}

async function uploadSuperFileList(fileList) {
  const files = Array.from(fileList || [])
  if (!files.length) return
  try {
    const payload = await uploadSuperFiles(fileManagerPath.value, files)
    fileManagerMessage.value = `上传完成：${Number(payload?.count || 0)} 个文件`
    await loadSuperFiles()
    await refreshSuperTree(fileManagerPath.value)
  } catch (err) {
    console.error(err)
    fileManagerMessage.value = err instanceof Error ? err.message : '上传失败'
  }
}

async function onUploadInputChange(event) {
  await uploadSuperFileList(event?.target?.files || [])
}

function onUploadDragOver(event) {
  event.preventDefault()
  uploadDragging.value = true
}

function onUploadDragLeave(event) {
  event.preventDefault()
  uploadDragging.value = false
}

async function onUploadDrop(event) {
  event.preventDefault()
  uploadDragging.value = false
  const fileList = event?.dataTransfer?.files || []
  await uploadSuperFileList(fileList)
}

async function loadAuditEvents() {
  const payload = await getAdminAuditEvents({
    days: auditFilters.days,
    username: auditFilters.username,
    category: auditFilters.category,
    action: auditFilters.action,
    keyword: auditFilters.keyword,
    limit: auditFilters.limit,
  })
  auditEvents.value = Array.isArray(payload?.events) ? payload.events : []
}

async function loadAuditStats() {
  const payload = await getAdminAuditStats({ days: auditFilters.days })
  const stats = payload?.stats || {}
  auditStats.total = Number(stats.total || 0)
  auditStats.by_category = stats.by_category && typeof stats.by_category === 'object' ? stats.by_category : {}
  auditStats.by_action = stats.by_action && typeof stats.by_action === 'object' ? stats.by_action : {}
  auditStats.by_user = stats.by_user && typeof stats.by_user === 'object' ? stats.by_user : {}
  auditStats.by_page = stats.by_page && typeof stats.by_page === 'object' ? stats.by_page : {}
}

async function reloadAuditData() {
  if (auditLoading.value) return
  auditLoading.value = true
  auditError.value = ''
  try {
    await Promise.all([loadAuditEvents(), loadAuditStats()])
  } catch (err) {
    console.error(err)
    auditError.value = err instanceof Error ? err.message : '加载日志失败'
  } finally {
    auditLoading.value = false
  }
}

function stopSystemTimer() {
  if (systemTimer) {
    clearInterval(systemTimer)
    systemTimer = null
  }
}

function ensureSystemTimer() {
  stopSystemTimer()
  if (!systemAutoRefresh.value || activeTab.value !== 'system') return
  systemTimer = setInterval(() => {
    loadSystemMetrics()
  }, 5000)
}

async function openFileEditor(path) {
  const filePath = String(path || '')
  if (!filePath) return
  selectedFilePath.value = filePath
  const popupUrl = `/admin-file-editor?path=${encodeURIComponent(filePath)}`
  const opened = window.open(
    popupUrl,
    'phoenix_admin_file_editor',
    'popup=yes,width=1200,height=820,resizable=yes,scrollbars=yes',
  )
  if (!opened) {
    fileMessage.value = '浏览器拦截了弹窗，请允许本网站弹窗后重试。'
    return
  }
  opened.focus()
  popupWindowRef.value = opened
  fileMessage.value = `已在新窗口打开：${filePath}`
}

async function toggleValidationMaster() {
  if (!canManageValidation.value) return
  validationPending.value = true
  try {
    const next = !validationMasterEnabled.value
    await setAdminValidationMasterSwitch(next)
    validationMasterEnabled.value = next
    await loadProjectSettings()
  } finally {
    validationPending.value = false
  }
}

async function publishCache() {
  if (!canManageCache.value) return
  cachePending.value = true
  try {
    await publishAdminDashboardCache({ days: publishDays.value })
    await loadProjectSettings()
  } finally {
    cachePending.value = false
  }
}

async function refreshCache() {
  if (!canManageCache.value) return
  cachePending.value = true
  try {
    await refreshAdminCache({ showDate: refreshDate.value })
    await loadProjectSettings()
  } finally {
    cachePending.value = false
  }
}

async function cancelPublish() {
  if (!canManageCache.value) return
  cachePending.value = true
  try {
    await cancelAdminCachePublishJob()
    await loadProjectSettings()
  } finally {
    cachePending.value = false
  }
}

async function disableCache() {
  if (!canManageCache.value) return
  cachePending.value = true
  try {
    await disableAdminCache()
    await loadProjectSettings()
  } finally {
    cachePending.value = false
  }
}

async function importTemperature() {
  if (!canManageCache.value) return
  temperatureImportBusy.value = true
  temperatureImportMessage.value = '正在导入气温预览...'
  temperatureImportStatus.writeMessage = ''
  temperatureImportStatus.overlapRecords = []
  try {
    const payload = await importProjectTemperatureData(TARGET_PROJECT_KEY)
    temperatureImportPreview.value = payload
    const totalHours = Number(payload?.summary?.total_hours ?? 0)
    const overlapHours = Number(payload?.overlap?.hours ?? 0)
    const diffCount = Array.isArray(payload?.differences) ? payload.differences.length : 0
    const dateSpan = Array.isArray(payload?.dates) && payload.dates.length
      ? `${payload.dates[0]} ~ ${payload.dates[payload.dates.length - 1]}`
      : ''
    temperatureImportStatus.message = `气温预览完成：总计 ${totalHours} 条`
    temperatureImportStatus.fetchedAt = String(payload?.fetched_at || '')
    temperatureImportStatus.dates = Array.isArray(payload?.dates) ? payload.dates : []
    temperatureImportStatus.overlapRange = String(payload?.overlap?.start && payload?.overlap?.end ? `${payload.overlap.start} ~ ${payload.overlap.end}` : '')
    temperatureImportStatus.overlapHours = overlapHours
    temperatureImportStatus.diffCount = diffCount
    temperatureImportStatus.overlapRecords = Array.isArray(payload?.overlap_records)
      ? payload.overlap_records.map((item) => ({
          time: item?.time || '',
          apiValue: typeof item?.api_value === 'number' ? item.api_value : item?.apiValue,
          dbValue: typeof item?.db_value === 'number' ? item.db_value : item?.dbValue,
          different: Boolean(item?.different),
          inDb: Boolean(item?.in_db),
        }))
      : []
    temperatureImportStatus.writeMessage = ''
    temperatureImportDialogVisible.value = true
    temperatureImportMessage.value = [
      `气温预览完成：总计 ${totalHours} 条`,
      dateSpan ? `覆盖日期 ${dateSpan}` : '',
      `重叠小时 ${overlapHours} 条`,
      `差异小时 ${diffCount} 条`,
    ].filter(Boolean).join('；')
  } catch (err) {
    console.error(err)
    temperatureImportMessage.value = err instanceof Error ? err.message : '导入气温失败'
  } finally {
    temperatureImportBusy.value = false
  }
}

async function commitTemperature() {
  if (!canManageCache.value) return
  temperatureImportCommitBusy.value = true
  temperatureImportMessage.value = '正在提交气温入库...'
  temperatureImportStatus.writeMessage = ''
  try {
    const payload = await commitProjectTemperatureData(TARGET_PROJECT_KEY)
    temperatureImportPreview.value = payload
    const inserted = Number(payload?.write_result?.inserted ?? 0)
    const replaced = Number(payload?.write_result?.replaced ?? 0)
    const totalHours = Number(payload?.summary?.total_hours ?? 0)
    temperatureImportMessage.value = `气温入库完成：写入 ${inserted} 条，覆盖旧数据 ${replaced} 条（抓取 ${totalHours} 小时）`
    temperatureImportStatus.writeMessage = temperatureImportMessage.value
    await loadProjectSettings()
    temperatureImportDialogVisible.value = false
  } catch (err) {
    console.error(err)
    temperatureImportMessage.value = err instanceof Error ? err.message : '提交气温入库失败'
    temperatureImportStatus.writeMessage = temperatureImportMessage.value
  } finally {
    temperatureImportCommitBusy.value = false
  }
}

function closeTemperatureImportDialog() {
  if (temperatureImportCommitBusy.value) return
  temperatureImportDialogVisible.value = false
}

function onMessage(event) {
  if (event.origin !== window.location.origin) return
  const payload = event.data || {}
  if (payload.type === 'admin-file-saved') {
    fileMessage.value = `保存成功：${payload.path || ''}`
    if (payload.path) {
      selectedFilePath.value = String(payload.path)
    }
  }
}

onMounted(async () => {
  if (!auth.canAccessAdminConsole) {
    router.replace('/projects')
    return
  }
  window.addEventListener('message', onMessage)
  // 同步 AI 气泡设置
  syncChatBubbleFromSettings()
  
  await refreshSuperTree(fileManagerPath.value)
  await loadSuperFiles()
  await loadProjects()
  await loadDirectories()
  await loadDbTables()
  await loadDbRows()
  await selectProject(TARGET_PROJECT_KEY)
})

watch(
  () => activeTab.value,
  async (tab) => {
    if (tab === 'files') {
      stopSystemTimer()
      return
    }
    if (tab === 'database') {
      stopSystemTimer()
      if (!dbTables.value.length) {
        await loadDbTables()
      }
      if (!dbRowsDraft.value.length && dbSelectedTable.value) {
        await loadDbRows()
      }
      return
    }
    if (tab === 'system') {
      await loadSystemMetrics()
      ensureSystemTimer()
      if (!fileManagerItems.value.length) {
        await refreshSuperTree(fileManagerPath.value)
        await loadSuperFiles()
      }
      return
    }
    if (tab === 'audit') {
      await reloadAuditData()
      stopSystemTimer()
      return
    }
    stopSystemTimer()
  },
)

watch(
  () => [auditFilters.days, auditFilters.username, auditFilters.category, auditFilters.action, auditFilters.keyword].join('|'),
  () => {
    if (activeTab.value === 'audit') {
      reloadAuditData().catch((err) => console.error(err))
    }
  },
)

watch(
  () => dbSelectedTable.value,
  () => {
    dbOffset.value = 0
    dbOrderBy.value = ''
    resetDbFilters()
  },
)

watch(
  () => systemAutoRefresh.value,
  () => {
    ensureSystemTimer()
  },
)

onBeforeUnmount(() => {
  window.removeEventListener('message', onMessage)
  stopSystemTimer()
  try {
    if (popupWindowRef.value && !popupWindowRef.value.closed) {
      popupWindowRef.value.close()
    }
  } catch (err) {
    console.warn('关闭文件编辑窗口失败', err)
  }
})
</script>

<style scoped>
.admin-console-main {
  padding: 24px;
  max-width: 1280px;
  margin: 0 auto;
  display: grid;
  gap: 16px;
}

.top-shell { padding-bottom: 8px; }

.top-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.tab-group {
  display: inline-flex;
  background: #f3f4f6;
  border-radius: 10px;
  padding: 4px;
  gap: 4px;
}

.tab-btn {
  border: none;
  background: transparent;
  color: #4b5563;
  padding: 8px 14px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
}

.tab-btn.active {
  background: #ffffff;
  color: #1d4ed8;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
}

.content-block { padding: 8px 0; }

.subtext {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--neutral-500);
}

.toolbar {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  margin-bottom: 12px;
}

.field {
  display: grid;
  gap: 6px;
  min-width: 180px;
}

.field.grow { flex: 1; }

.tree-wrap {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px;
}

.tree-head {
  margin-bottom: 8px;
}

.tree-list {
  max-height: 560px;
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 6px;
}

.tree-row {
  width: 100%;
  border: none;
  background: transparent;
  text-align: left;
  border-radius: 6px;
  padding: 8px 10px;
  cursor: pointer;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 6px;
  position: relative;
  border: 1px solid transparent;
}

.tree-row:hover {
  background: rgba(14, 116, 144, 0.08);
  border-color: rgba(14, 116, 144, 0.25);
}

.tree-row.active {
  background: rgba(37, 99, 235, 0.14);
  color: #1d4ed8;
  border-color: rgba(37, 99, 235, 0.35);
}

.tree-folder {
  font-weight: 600;
}

.tree-icon {
  width: 12px;
  text-align: center;
  opacity: 0.85;
}

.dirty-dot {
  color: #b45309;
  font-size: 12px;
  background: #fef3c7;
  border: 1px solid #fcd34d;
  border-radius: 999px;
  padding: 2px 8px;
}

.message {
  color: #047857;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 12px;
}

.tree-label {
  position: relative;
}

.tree-row::before {
  content: '';
  position: absolute;
  left: 4px;
  top: 50%;
  width: 8px;
  height: 1px;
  background: rgba(100, 116, 139, 0.45);
}

.project-switch {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.inner-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px;
  margin-top: 10px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.system-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.system-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.sparkline-box {
  margin-top: 8px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 4px 6px;
  background: #f8fafc;
}

.sparkline-svg {
  width: 100%;
  height: 44px;
  display: block;
}

.sparkline-line {
  fill: none;
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.sparkline-cpu {
  stroke: #ef4444;
}

.sparkline-memory {
  stroke: #3b82f6;
}

.sparkline-disk {
  stroke: #f59e0b;
}

.sparkline-proc {
  stroke: #10b981;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.overview-item {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px;
  display: grid;
  gap: 8px;
}

.overview-item .label {
  font-size: 12px;
  color: var(--neutral-500);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.form-grid label {
  display: grid;
  gap: 6px;
  font-size: 13px;
}

.span-2 { grid-column: span 2; }

.switch-row {
  display: flex !important;
  align-items: center;
  gap: 8px;
}

.cache-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 10px;
}

.temp-import-modal {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.temp-import-modal__mask {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
}

.temp-import-modal__card {
  position: relative;
  width: min(640px, calc(100vw - 32px));
  max-height: calc(100vh - 48px);
  overflow: auto;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #dbeafe;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.22);
  padding: 16px 18px;
}

.temp-import-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.temp-import-modal__header h3 {
  margin: 0;
  font-size: 16px;
}

.temp-import-modal__close {
  border: none;
  background: transparent;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  color: #64748b;
}

.temp-import-modal__body p {
  margin: 6px 0;
  color: #334155;
}

.temp-import-modal__diffs-title {
  margin-top: 8px;
  color: #0f172a;
  font-weight: 600;
}

.temp-import-modal__diffs ul {
  margin: 6px 0 0;
  padding-left: 16px;
}

.temp-import-modal__diff-item--different {
  color: #b91c1c;
  font-weight: 600;
}

.temp-import-modal__hint {
  margin-top: 8px;
  color: #888;
}

.temp-import-modal__write {
  margin-top: 10px;
  color: #1d4ed8;
  font-weight: 600;
}

.temp-import-modal__footer {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.cache-actions label {
  display: grid;
  gap: 6px;
  font-size: 13px;
}

.list-btn {
  border: 1px solid #d1d5db;
  background: #fff;
  color: #1f2937;
  border-radius: 8px;
  padding: 8px 10px;
  text-align: left;
  cursor: pointer;
}

.list-btn.active {
  border-color: var(--primary-400);
  background: rgba(59, 130, 246, 0.1);
}

.panel-state {
  padding: 16px 0;
  color: var(--neutral-600);
}

.panel-state.error {
  color: var(--danger);
}

.btn.ghost {
  border: 1px solid var(--primary-200);
  background: transparent;
  color: var(--primary-600);
}

.db-editor-card {
  margin-top: 12px;
}

.db-toolbar {
  flex-wrap: wrap;
}

.db-filter-wrap {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px;
  background: #f8fafc;
  margin-bottom: 10px;
}

.db-filter-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 600;
  color: #334155;
}

.db-filter-list {
  display: grid;
  gap: 8px;
}

.db-filter-item {
  display: grid;
  grid-template-columns: minmax(160px, 1fr) minmax(120px, 0.8fr) minmax(220px, 1.2fr) auto;
  gap: 8px;
  align-items: center;
}

.db-filter-item select,
.db-filter-item input {
  width: 100%;
}

.db-table-wrap {
  margin-top: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  max-height: 420px;
  overflow: auto;
}

.db-edit-table {
  min-width: 980px;
}

.db-pk-tag {
  display: inline-block;
  margin-left: 6px;
  font-size: 10px;
  line-height: 1;
  padding: 2px 4px;
  border-radius: 999px;
  background: #dbeafe;
  color: #1e40af;
  border: 1px solid #bfdbfe;
}

.db-cell-input {
  width: 100%;
  min-width: 120px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 4px 6px;
  font-size: 12px;
  line-height: 1.3;
  background: #ffffff;
}

.db-cell-input:disabled {
  background: #f3f4f6;
  color: #6b7280;
}

.super-card {
  margin-top: 12px;
  border-color: #fca5a5;
  background: linear-gradient(180deg, #fff7f7 0%, #ffffff 100%);
}

.super-split {
  margin-top: 12px;
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: 12px;
}

.super-pane {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px;
  display: grid;
  gap: 10px;
}

.super-pane h4 {
  margin: 0;
  font-size: 14px;
  color: #991b1b;
}

.super-preset-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}

.terminal-output {
  min-height: 200px;
  max-height: 360px;
  overflow: auto;
  background: #0f172a;
  color: #e2e8f0;
  border-radius: 8px;
  padding: 10px;
  font-size: 12px;
  line-height: 1.5;
}

.super-terminal-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.super-files-wrap {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: auto;
  max-height: 280px;
}

.super-batch-toolbar {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.super-upload-dropzone {
  border: 1px dashed #93c5fd;
  border-radius: 10px;
  padding: 10px;
  background: #f8fbff;
  display: grid;
  gap: 8px;
  transition: all 0.15s ease;
}

.super-upload-dropzone.dragging {
  border-color: #2563eb;
  background: #eff6ff;
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.25);
}

.super-upload-title {
  font-size: 13px;
  font-weight: 600;
  color: #1e3a8a;
}

.super-upload-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.super-upload-input {
  display: none;
}

.super-explorer {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 10px;
}

.super-dir-tree {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  max-height: 280px;
  overflow: auto;
  background: #f8fafc;
}

.super-dir-tree-head {
  position: sticky;
  top: 0;
  z-index: 1;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 600;
  color: #334155;
  background: #eef2ff;
  border-bottom: 1px solid #e5e7eb;
}

.super-tree-node {
  display: grid;
}

.super-tree-row {
  width: 100%;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  padding: 7px 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #1f2937;
}

.super-tree-row:hover {
  background: rgba(59, 130, 246, 0.08);
}

.super-tree-row.active {
  background: rgba(37, 99, 235, 0.16);
  color: #1d4ed8;
  font-weight: 600;
}

.super-tree-row.child {
  padding-left: 18px;
}

.super-tree-row.child.grand {
  padding-left: 28px;
}

.super-tree-toggle {
  width: 14px;
  text-align: center;
  color: #475569;
}

.super-tree-label {
  word-break: break-all;
}

.super-context-mask {
  position: fixed;
  inset: 0;
  z-index: 1000;
}

.super-context-menu {
  position: fixed;
  min-width: 170px;
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.18);
  padding: 6px;
  display: grid;
  gap: 4px;
}

.super-context-item {
  border: none;
  background: transparent;
  border-radius: 6px;
  text-align: left;
  padding: 8px 10px;
  cursor: pointer;
  font-size: 12px;
  color: #1f2937;
}

.super-context-item:hover {
  background: rgba(59, 130, 246, 0.12);
  color: #1d4ed8;
}

.super-files-table {
  table-layout: auto;
}

.super-files-table .super-select-col {
  width: 46px;
  text-align: center;
}

.super-files-table input[type='checkbox'] {
  width: 14px;
  height: 14px;
  cursor: pointer;
}

.super-row-selected td {
  background: rgba(37, 99, 235, 0.08);
}

.super-path-cell {
  max-width: 280px;
  word-break: break-all;
}

.super-file-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.super-editor-wrap {
  display: grid;
  gap: 8px;
}

.super-editor {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 10px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  line-height: 1.5;
  resize: vertical;
}

.super-editor-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.audit-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.audit-list {
  margin: 0;
  padding-left: 16px;
  font-size: 12px;
  color: #334155;
  display: grid;
  gap: 4px;
}

.audit-table-wrap {
  margin-top: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: auto;
}

.audit-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.audit-table th,
.audit-table td {
  border-bottom: 1px solid #e5e7eb;
  padding: 8px 10px;
  text-align: left;
  font-size: 12px;
  white-space: normal;
  word-break: break-word;
  overflow-wrap: anywhere;
  vertical-align: top;
}

.audit-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f8fafc;
  color: #334155;
}

.audit-table .col-time { width: 170px; }
.audit-table .col-user { width: 96px; }
.audit-table .col-ip { width: 130px; }
.audit-table .col-category { width: 88px; }
.audit-table .col-action { width: 90px; }
.audit-table .col-page { width: 30%; }
.audit-table .col-target { width: 24%; }

@media (max-width: 1200px) {
  .top-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .system-actions {
    width: 100%;
    justify-content: space-between;
    flex-wrap: wrap;
  }

  .editor-modal {
    width: 95vw;
  }

  .super-split {
    grid-template-columns: 1fr;
  }

  .super-preset-row {
    flex-direction: column;
    align-items: stretch;
  }

  .super-explorer {
    grid-template-columns: 1fr;
  }

  .db-filter-item {
    grid-template-columns: 1fr;
  }
}
.cache-worker-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  margin: 12px 0;
}
.cache-worker-card {
  border: 1px solid #d9e3f2;
  border-radius: 14px;
  background: #f8fbff;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cache-worker-card.is-running {
  border-color: #93c5fd;
  background: #eff6ff;
}
.cache-worker-card.is-completed {
  border-color: #86efac;
  background: #f0fdf4;
}
.cache-worker-card.is-failed {
  border-color: #fca5a5;
  background: #fef2f2;
}
.cache-worker-card.is-aborted {
  border-color: #fcd34d;
  background: #fffbeb;
}
.cache-worker-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.cache-worker-card__title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}
.cache-worker-card__badge {
  border-radius: 999px;
  padding: 2px 9px;
  font-size: 12px;
  font-weight: 700;
  color: #334155;
  background: #e2e8f0;
}
.cache-worker-card__message {
  font-size: 13px;
  line-height: 1.6;
  color: #334155;
}
.cache-worker-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  font-size: 12px;
  color: #64748b;
}
.cache-job-log-panel__title {
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #64748b;
  text-transform: uppercase;
}
</style>
