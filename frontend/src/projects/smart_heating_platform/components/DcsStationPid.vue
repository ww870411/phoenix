<template>
  <div class="pid-stage">
    <!-- 顶部对象工况铭牌 -->
    <div class="pid-stage-head">
      <div class="pid-title-left">
        <span class="pid-tag-code">{{ target?.tagId || 'DCS-MIMIC' }}</span>
        <h3>{{ target?.title || '请选择左侧站点或热源节点' }}</h3>
        <span class="pid-sub">{{ target?.subtitle || '' }}</span>
      </div>
      <div v-if="target" class="pid-status-right">
        <span :class="['pid-mode-badge', `sev-${target.severity}`]">
          只读状态 · {{ target.modeLabel }}
        </span>
      </div>
    </div>

    <!-- 单座换热站：全矢量 P&ID 工艺组态图 -->
    <div v-if="target?.kind === 'station'" class="pid-canvas-wrap">
      <svg class="pid-svg" viewBox="0 0 840 370" role="img" :aria-label="`${target.title} 工艺组态图`">
        <defs>
          <pattern id="pid-grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#cdd6e2" stroke-width="0.6" />
          </pattern>
          <marker id="pid-arr" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#3b6b8f" />
          </marker>
          <marker id="pid-arr-ret" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#64748b" />
          </marker>
        </defs>

        <!-- 背景底纹 -->
        <rect x="0" y="0" width="840" height="370" fill="#dae1e9" rx="2" />
        <rect x="0" y="0" width="840" height="370" fill="url(#pid-grid)" opacity="0.65" />

        <!-- 一次网供水管（左 -> 板换） -->
        <line x1="20" y1="86" x2="352" y2="86" :class="['p-pipe', st.online ? 'p-supply' : 'p-oos']" marker-end="url(#pid-arr)" />
        <line v-if="st.online" x1="20" y1="86" x2="352" y2="86" class="p-flow-anim" />
        <text x="26" y="74" class="pipe-name">一次网供水进站管</text>

        <!-- 一次网电动调节阀（位于供水管上） -->
        <g transform="translate(152, 86)">
          <polygon points="-14,-10 0,0 -14,10" fill="#64748b" stroke="#334155" stroke-width="1" />
          <polygon points="14,-10 0,0 14,10" fill="#64748b" stroke="#334155" stroke-width="1" />
          <line x1="0" y1="0" x2="0" y2="-18" stroke="#334155" stroke-width="1.5" />
          <rect x="-10" y="-28" width="20" height="10" rx="1" fill="#cbd5e1" stroke="#334155" stroke-width="1" />
          <text x="0" y="23" text-anchor="middle" class="mini-lbl">一次调节阀</text>
        </g>

        <!-- 一次网供水仪表铭牌 -->
        <g transform="translate(26, 102)">
          <rect x="0" y="0" width="110" height="60" rx="2" :class="['inst-box', tempAlarmClass]" />
          <text x="7" y="15" class="inst-lbl">一次供水温度 e3</text>
          <text x="7" y="34" :class="['inst-val', tempAlarmClass]">{{ fmt(st.e3, ' ℃', 1) }}</text>
          <text x="7" y="51" class="inst-sub">供压 {{ fmt(st.e7, ' MPa', 3) }}</text>
        </g>

        <!-- 一次网回水管（板换 -> 左出） -->
        <line x1="352" y1="210" x2="24" y2="210" class="p-pipe p-return" marker-end="url(#pid-arr-ret)" />
        <text x="26" y="232" class="pipe-name">一次网回水出站管</text>

        <!-- 一次网回水仪表铭牌 -->
        <g transform="translate(26, 244)">
          <rect x="0" y="0" width="110" height="60" rx="2" :class="['inst-box', tempAlarmClass]" />
          <text x="7" y="15" class="inst-lbl">一次回水温度 e4</text>
          <text x="7" y="34" :class="['inst-val', tempAlarmClass]">{{ fmt(st.e4, ' ℃', 1) }}</text>
          <text x="7" y="51" class="inst-sub">回压 {{ fmt(st.e8, ' MPa', 3) }}</text>
        </g>

        <!-- 流量 & 温差汇总牌 -->
        <g transform="translate(154, 134)">
          <rect x="0" y="0" width="150" height="58" rx="2" class="inst-box" />
          <text x="8" y="15" class="inst-lbl">一次网瞬时流量 / 温差</text>
          <text x="8" y="34" class="inst-val">{{ fmt(st.e1, ' t/h', 1) }}</text>
          <text x="8" y="50" class="inst-sub">ΔT = {{ fmt(deltaT, ' ℃', 1) }} ｜ 瞬热 {{ fmt(st.e11, ' GJ/h', 1) }}</text>
        </g>

        <!-- 核心设备：板式换热器 (PHE) -->
        <g transform="translate(358, 62)">
          <rect x="0" y="0" width="136" height="170" rx="3" :class="['equip-body', heatEquipClass]" />
          <!-- 板片波纹符号 -->
          <rect x="16" y="24" width="104" height="72" fill="#cfd8e3" stroke="#475569" stroke-width="1.3" />
          <line x1="34" y1="24" x2="34" y2="96" stroke="#64748b" stroke-width="1" />
          <line x1="52" y1="24" x2="52" y2="96" stroke="#64748b" stroke-width="1" />
          <line x1="70" y1="24" x2="70" y2="96" stroke="#64748b" stroke-width="1" />
          <line x1="88" y1="24" x2="88" y2="96" stroke="#64748b" stroke-width="1" />
          <line x1="106" y1="24" x2="106" y2="96" stroke="#64748b" stroke-width="1" />
          <path d="M 22 36 L 112 84 M 22 84 L 112 36" stroke="#3b6b8f" stroke-width="1.4" opacity="0.7" />
          <text x="68" y="17" text-anchor="middle" class="equip-hdr">板式换热机组</text>

          <!-- 小时精算读数 -->
          <text x="68" y="116" text-anchor="middle" class="inst-lbl">
            小时供热 ({{ st.hour_heat_source === 'METER_DIFF' ? '表底差' : '积分' }})
          </text>
          <text x="68" y="136" text-anchor="middle" class="inst-val-lg">{{ fmt(st.hour_heat_gj, ' GJ', 2) }}</text>
          <text x="68" y="154" text-anchor="middle" class="inst-sub">
            热指标 {{ fmt(st.heat_index_wm2, ' W/㎡', 1) }}
          </text>
        </g>

        <!-- 二次网侧向居民楼（换热器 -> 建筑末端） -->
        <line x1="494" y1="96" x2="646" y2="96" :class="['p-pipe', st.online ? 'p-supply' : 'p-oos']" marker-end="url(#pid-arr)" />
        <line x1="646" y1="196" x2="494" y2="196" class="p-pipe p-return" marker-end="url(#pid-arr-ret)" />
        <text x="570" y="84" text-anchor="middle" class="pipe-name">用户供热输出（二网分区停采）</text>

        <!-- 补水系统（左下角：软化水箱动态液位 + 补水泵 -> 二次回水母管） -->
        <g transform="translate(226, 250)">
          <!-- 补水箱容器 -->
          <rect x="0" y="0" width="94" height="94" rx="2" fill="#e5eaf0" stroke="#475569" stroke-width="1.4" />
          <text x="47" y="14" text-anchor="middle" class="inst-lbl">补水箱 (e16)</text>
          <!-- 液位槽 -->
          <rect x="10" y="22" width="74" height="48" fill="#cbd5e1" stroke="#94a3b8" />
          <rect
            x="11"
            :y="69 - tankFillPx"
            width="72"
            :height="tankFillPx"
            fill="#5b8db8"
            opacity="0.85"
          />
          <text x="47" y="85" text-anchor="middle" class="inst-sub">{{ fmt(st.e16, ' mm', 0) }}</text>

          <!-- 补水管道与泵 -->
          <line x1="94" y1="54" x2="184" y2="54" class="p-pipe p-water" />
          <line x1="184" y1="54" x2="184" y2="-54" class="p-pipe p-water" />
          <circle cx="138" cy="54" r="14" fill="#eef2f6" stroke="#334155" stroke-width="1.4" />
          <polygon points="133,47 146,54 133,61" :fill="waterAlarm ? '#d97706' : '#3b6b8f'" />
          <text x="138" y="82" text-anchor="middle" class="mini-lbl">补水泵</text>
        </g>

        <!-- 补水 & 电耗计量仪表盒 -->
        <g transform="translate(432, 250)">
          <rect x="0" y="0" width="184" height="94" rx="2" :class="['inst-box', waterAlarm || elecAlarm ? 'inst-warn' : '']" />
          <text x="10" y="18" class="inst-lbl">水电动力计量终端</text>
          <text x="10" y="42" class="inst-sub">小时补水：</text>
          <text x="78" y="42" class="inst-val-sm">{{ fmt(st.hour_water_t ?? st.e14, ' t', 2) }}</text>
          <text x="10" y="64" class="inst-sub">小时电耗：</text>
          <text x="78" y="64" class="inst-val-sm">{{ fmt(st.hour_elec_kwh, ' kWh', 1) }}</text>
          <text x="10" y="84" class="inst-sub">累计热量表底 totJ: {{ fmt(st.tot_j, ' GJ', 1) }}</text>
        </g>

        <!-- 右侧：供暖小区楼宇 + 居民室温实况 -->
        <g transform="translate(650, 52)">
          <rect x="0" y="0" width="168" height="292" rx="3" :class="['equip-body', roomAlarm ? 'sev-box-critical' : '']" />
          <text x="84" y="20" text-anchor="middle" class="equip-hdr">居民用热末端</text>

          <!-- 住宅楼矢量图 -->
          <g transform="translate(22, 34)">
            <rect x="0" y="18" width="44" height="90" fill="#b7c3d0" stroke="#475569" stroke-width="1.2" />
            <rect x="52" y="6" width="46" height="102" fill="#a8b6c6" stroke="#475569" stroke-width="1.2" />
            <rect x="8" y="28" width="10" height="10" fill="#fef08a" stroke="#64748b" stroke-width="0.6" />
            <rect x="26" y="28" width="10" height="10" fill="#fef08a" stroke="#64748b" stroke-width="0.6" />
            <rect x="8" y="48" width="10" height="10" fill="#fef08a" stroke="#64748b" stroke-width="0.6" />
            <rect x="26" y="48" width="10" height="10" fill="#fef08a" stroke="#64748b" stroke-width="0.6" />
            <rect x="60" y="18" width="11" height="11" fill="#fef08a" stroke="#64748b" stroke-width="0.6" />
            <rect x="79" y="18" width="11" height="11" fill="#fef08a" stroke="#64748b" stroke-width="0.6" />
            <rect x="60" y="38" width="11" height="11" fill="#fef08a" stroke="#64748b" stroke-width="0.6" />
            <rect x="79" y="38" width="11" height="11" fill="#fef08a" stroke="#64748b" stroke-width="0.6" />
            <rect x="60" y="58" width="11" height="11" fill="#fef08a" stroke="#64748b" stroke-width="0.6" />
            <rect x="79" y="58" width="11" height="11" fill="#fef08a" stroke="#64748b" stroke-width="0.6" />
          </g>

          <!-- 室温温度计柱 -->
          <rect x="134" y="42" width="14" height="98" rx="7" fill="#cbd5e1" stroke="#64748b" />
          <rect
            x="136"
            :y="138 - roomFillPx"
            width="10"
            :height="roomFillPx"
            rx="5"
            :fill="roomAlarm ? '#dc2626' : '#3b6b8f'"
          />
          <line x1="129" y1="100" x2="152" y2="100" stroke="#dc2626" stroke-width="1.5" />
          <text x="141" y="152" text-anchor="middle" class="mini-lbl">18℃</text>

          <!-- 室温读数卡片 -->
          <rect x="12" y="166" width="144" height="112" rx="2" fill="#f1f5f9" stroke="#94a3b8" />
          <text x="20" y="184" class="inst-lbl">站区有效平均室温</text>
          <text x="20" y="208" :class="['inst-val-lg', roomAlarm ? 'txt-crit' : '']">{{ fmt(st.avg_room_temp, ' ℃', 2) }}</text>
          <text x="20" y="230" class="inst-sub">达标率：{{ fmt(st.temp_pass_rate_pct, ' %', 1) }}</text>
          <text x="20" y="248" class="inst-sub">有效终端：{{ st.temp_valid_count ?? 0 }} 户</text>
          <text x="20" y="266" class="inst-sub">面积：{{ st.covered_area ? `${(st.covered_area / 10000).toFixed(2)} 万㎡` : '待补录' }}</text>
        </g>

        <!-- 异常状态现场挂牌 (Alarm Tag Overlay) -->
        <g v-if="target.severity === 'critical' || target.severity === 'warning'" transform="translate(324, 16)">
          <rect
            x="0"
            y="0"
            width="206"
            height="28"
            rx="2"
            :fill="target.severity === 'critical' ? '#fee2e2' : '#fef3c7'"
            :stroke="target.severity === 'critical' ? '#dc2626' : '#d97706'"
            stroke-width="1.5"
          />
          <text
            x="103"
            y="18"
            text-anchor="middle"
            :fill="target.severity === 'critical' ? '#991b1b' : '#92400e'"
            font-size="11.5"
            font-weight="700"
          >
            {{ target.severity === 'critical' ? '◆ 现场异常挂牌：' : '▲ 质量降级提示：' }}{{ target.modeLabel }}
          </text>
        </g>
      </svg>
    </div>

    <!-- 上游电厂（母管制）：汽轮机本体蒸汽组态（机侧不显示锅炉主汽参数） -->
    <div v-else-if="target?.kind === 'upstream' && isTurbineView" class="pid-canvas-wrap">
      <svg class="pid-svg" viewBox="0 0 840 370" role="img" :aria-label="`${target.title} 汽轮机热电联产工艺组态图`">
        <defs>
          <pattern id="pid-grid-tb" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#cdd6e2" stroke-width="0.6" />
          </pattern>
          <marker id="tb-arr" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#3b6b8f" />
          </marker>
          <marker id="tb-arr-act" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#1d4ed8" />
          </marker>
        </defs>

        <rect x="0" y="0" width="840" height="370" fill="#dae1e9" rx="2" />
        <rect x="0" y="0" width="840" height="370" fill="url(#pid-grid-tb)" opacity="0.65" />

        <!-- 标题标注 -->
        <text x="20" y="22" class="pipe-name">
          {{ turbineContextTitle }} · 母管制汽轮机蒸汽流程组态（来汽取自全厂主蒸汽母管 · 点击机侧蒸汽口切换测点）
        </text>

        <!-- 左侧：全厂公用高压主蒸汽母管（母管制来汽节点，机侧不混显锅炉主汽数值） -->
        <g
          transform="translate(18, 72)"
          :class="{ 'svg-clickable': Boolean(plantBoilerShortcut) }"
          @click="selectTurbinePort(plantBoilerShortcut)"
        >
          <rect x="0" y="0" width="88" height="140" rx="3" fill="#e5ebf2" stroke="#64748b" stroke-width="1.4" />
          <rect x="34" y="14" width="20" height="84" rx="4" fill="#4f6f91" stroke="#334155" stroke-width="1.2" />
          <line x1="44" y1="20" x2="44" y2="92" stroke="#cbd5e1" stroke-width="2" stroke-dasharray="6 6" />
          <text x="44" y="112" text-anchor="middle" class="equip-hdr">主蒸汽母管</text>
          <text x="44" y="128" text-anchor="middle" font-size="9.5" :fill="plantBoilerShortcut ? '#1d4ed8' : '#475569'" font-weight="600">
            {{ plantBoilerShortcut ? '查看炉侧母管 →' : '母管制来汽' }}
          </text>
        </g>

        <!-- 主汽管道（主蒸汽母管 -> 调门） -->
        <path
          d="M 106 114 L 246 114"
          :class="['p-pipe', !isTurbineRunning ? 'p-oos' : (activePortKey === 'main' ? 'p-active-line' : 'p-supply')]"
          :marker-end="activePortKey === 'main' ? 'url(#tb-arr-act)' : 'url(#tb-arr)'"
        />
        <line
          v-if="isTurbineRunning && (activePortKey === 'main' || (Number(turbinePorts.main?.flow) || 0) > 2)"
          x1="106"
          y1="114"
          x2="246"
          y2="114"
          :class="activePortKey === 'main' ? 'p-flow-anim-act' : 'p-flow-anim'"
        />

        <!-- 主汽调节阀 -->
        <g transform="translate(260, 114)">
          <polygon points="-13,-10 0,0 -13,10" :fill="isTurbineRunning ? '#475569' : '#94a3b8'" stroke="#1e293b" stroke-width="1" />
          <polygon points="13,-10 0,0 13,10" :fill="isTurbineRunning ? '#475569' : '#94a3b8'" stroke="#1e293b" stroke-width="1" />
          <line x1="0" y1="0" x2="0" y2="-18" stroke="#1e293b" stroke-width="1.5" />
          <rect x="-10" y="-28" width="20" height="10" rx="1" fill="#cbd5e1" stroke="#334155" />
          <text x="0" y="22" text-anchor="middle" class="mini-lbl">主汽调门</text>
        </g>

        <!-- 进汽管道（调门 -> 汽轮机高压缸前端） -->
        <path
          d="M 274 114 L 336 114 L 336 132"
          :class="['p-pipe', !isTurbineRunning ? 'p-oos' : (activePortKey === 'inlet' ? 'p-active-line' : 'p-supply')]"
          :marker-end="activePortKey === 'inlet' ? 'url(#tb-arr-act)' : 'url(#tb-arr)'"
        />
        <line
          v-if="isTurbineRunning && (activePortKey === 'inlet' || (Number(turbinePorts.inlet?.flow) || 0) > 2)"
          x1="274"
          y1="114"
          x2="336"
          y2="114"
          :class="activePortKey === 'inlet' ? 'p-flow-anim-act' : 'p-flow-anim'"
        />

        <!-- 核心：经典梯形扩压汽轮机本体（高压缸 -> 中低压缸） + 转子轴 + 发电机 G -->
        <g transform="translate(314, 96)">
          <!-- 高压缸（左梯形） -->
          <polygon points="8,36 106,20 106,96 8,80" :class="['equip-body', isTurbineRunning ? 'tb-running-body' : 'tb-stopped-body']" />
          <!-- 低压缸（右扩压大梯形） -->
          <polygon points="116,16 254,0 254,116 116,100" :class="['equip-body', isTurbineRunning ? 'tb-running-body' : 'tb-stopped-body']" />

          <!-- 汽轮机级间动叶片（运转时上下垂直滚动脉冲模拟转子高速旋转） -->
          <g :class="isTurbineRunning ? 'tb-blades-spin' : ''">
            <line x1="28" y1="35" x2="28" y2="81" stroke="#5b728a" stroke-width="2" stroke-dasharray="5 5" />
            <line x1="50" y1="31" x2="50" y2="85" stroke="#5b728a" stroke-width="2" stroke-dasharray="5 5" />
            <line x1="72" y1="27" x2="72" y2="89" stroke="#5b728a" stroke-width="2" stroke-dasharray="5 5" />
            <line x1="94" y1="24" x2="94" y2="92" stroke="#5b728a" stroke-width="2" stroke-dasharray="5 5" />
            <line x1="138" y1="16" x2="138" y2="100" stroke="#5b728a" stroke-width="2.2" stroke-dasharray="6 5" />
            <line x1="166" y1="13" x2="166" y2="103" stroke="#5b728a" stroke-width="2.2" stroke-dasharray="6 5" />
            <line x1="196" y1="9" x2="196" y2="107" stroke="#5b728a" stroke-width="2.2" stroke-dasharray="6 5" />
            <line x1="226" y1="5" x2="226" y2="111" stroke="#5b728a" stroke-width="2.2" stroke-dasharray="6 5" />
          </g>

          <!-- 贯通转子中心主轴（含旋转螺旋纹动画） -->
          <rect x="0" y="54" width="302" height="8" fill="#64748b" stroke="#334155" stroke-width="1" />
          <line
            v-if="isTurbineRunning"
            x1="4"
            y1="58"
            x2="296"
            y2="58"
            stroke="#e2e8f0"
            stroke-width="2.6"
            stroke-dasharray="7 9"
            class="tb-shaft-spin"
          />

          <!-- 高低压缸联通管 -->
          <path d="M 106 32 L 116 32" stroke="#475569" stroke-width="5" />
          <!-- 联轴器（运转时同步脉冲） -->
          <rect x="274" y="50" width="8" height="16" fill="#475569" />
          <line
            v-if="isTurbineRunning"
            x1="278"
            y1="50"
            x2="278"
            y2="66"
            stroke="#38bdf8"
            stroke-width="2"
            stroke-dasharray="3 3"
            class="tb-coupling-spin"
          />

          <!-- 发电机 G + 旋转转子十字磁极环 -->
          <circle cx="322" cy="58" r="24" fill="#eef2f6" stroke="#334155" stroke-width="1.8" />
          <g v-if="isTurbineRunning" class="tb-gen-rotor" style="transform-origin: 322px 58px;">
            <circle cx="322" cy="58" r="19" fill="none" stroke="#3b82f6" stroke-width="2" stroke-dasharray="8 7" />
            <line x1="306" y1="58" x2="338" y2="58" stroke="#93c5fd" stroke-width="1.4" />
            <line x1="322" y1="42" x2="322" y2="74" stroke="#93c5fd" stroke-width="1.4" />
          </g>
          <circle cx="322" cy="58" r="13" fill="#eef2f6" />
          <text x="322" y="64" text-anchor="middle" font-size="18" font-weight="700" fill="#1e3a5f">G</text>

          <!-- 运转状态自动判定铭牌 -->
          <rect
            x="284"
            y="88"
            width="76"
            height="18"
            rx="2"
            :fill="isTurbineRunning ? '#dcfce7' : '#e2e8f0'"
            :stroke="isTurbineRunning ? '#0f766e' : '#64748b'"
          />
          <text
            x="322"
            y="100.5"
            text-anchor="middle"
            font-size="9.5"
            font-weight="700"
            :fill="isTurbineRunning ? '#0f766e' : '#475569'"
          >
            {{ isTurbineRunning ? '● 运转中' : '○ 停机/冷备' }}
          </text>

          <text x="58" y="13" text-anchor="middle" class="mini-lbl">高压缸</text>
          <text x="186" y="-6" text-anchor="middle" class="mini-lbl">中低压缸</text>
        </g>

        <!-- 抽汽管路（中段抽出 -> 向下接供热首站/尖峰热网） -->
        <path
          d="M 425 194 L 425 256 L 372 256"
          :class="['p-pipe', !isTurbineRunning ? 'p-oos' : (activePortKey === 'extract' ? 'p-active-line' : 'p-supply')]"
          :marker-end="activePortKey === 'extract' ? 'url(#tb-arr-act)' : 'url(#tb-arr)'"
        />
        <line
          v-if="isTurbineRunning && (activePortKey === 'extract' || (Number(turbinePorts.extract?.flow) || 0) > 2)"
          x1="425"
          y1="194"
          x2="425"
          y2="256"
          :class="activePortKey === 'extract' ? 'p-flow-anim-act' : 'p-flow-anim'"
        />

        <!-- 排汽管路（低压缸末端向下 -> 凝汽器/低真空供热） -->
        <path
          d="M 538 206 L 538 244"
          :class="['p-pipe', !isTurbineRunning ? 'p-oos' : (activePortKey === 'exhaust' ? 'p-active-line' : 'p-return')]"
          :marker-end="activePortKey === 'exhaust' ? 'url(#tb-arr-act)' : 'url(#tb-arr)'"
        />
        <line
          v-if="isTurbineRunning && (activePortKey === 'exhaust' || (Number(turbinePorts.exhaust?.flow) || 0) > 2)"
          x1="538"
          y1="206"
          x2="538"
          y2="244"
          :class="activePortKey === 'exhaust' ? 'p-flow-anim-act' : 'p-flow-anim'"
        />
        <!-- 凝汽器 / 低真空热网图标 -->
        <g transform="translate(492, 248)">
          <rect x="0" y="0" width="92" height="36" rx="2" fill="#cfd8e3" stroke="#475569" stroke-width="1.2" />
          <path d="M 10 18 Q 25 10 40 18 T 70 18 L 82 18" fill="none" stroke="#3b6b8f" stroke-width="1.4" />
          <text x="46" y="30" text-anchor="middle" class="mini-lbl">凝汽/低真空</text>
        </g>

        <!-- 四大蒸汽口可点击仪表铭牌：1. 仅机主汽（母管制下不显示锅炉主汽） -->
        <g
          transform="translate(112, 38)"
          :class="{ 'svg-clickable': Boolean(turbinePorts.main) }"
          @click="selectTurbinePort(turbinePorts.main)"
        >
          <rect x="0" y="0" width="144" height="58" rx="2" :class="['inst-box', activePortKey === 'main' ? 'inst-focus' : '']" />
          <text x="8" y="15" class="inst-lbl">① 机主汽 {{ turbinePorts.main ? '' : '(无测点)' }}</text>
          <text x="8" y="34" class="inst-val-sm">{{ turbinePorts.main ? `${fmt(turbinePorts.main.temp, '℃', 1)} · ${fmt(turbinePorts.main.flow, 't/h', 1)}` : '--' }}</text>
          <text x="8" y="50" class="inst-sub">{{ turbinePorts.main ? turbinePorts.main.display_name : '本机未设机主汽表计' }}</text>
        </g>

        <!-- 2. 机进汽 -->
        <g
          transform="translate(268, 38)"
          :class="{ 'svg-clickable': Boolean(turbinePorts.inlet) }"
          @click="selectTurbinePort(turbinePorts.inlet)"
        >
          <rect x="0" y="0" width="144" height="58" rx="2" :class="['inst-box', activePortKey === 'inlet' ? 'inst-focus' : '']" />
          <text x="8" y="15" class="inst-lbl">② 机进汽 {{ turbinePorts.inlet ? '' : '(无测点)' }}</text>
          <text x="8" y="34" class="inst-val-sm">{{ turbinePorts.inlet ? `${fmt(turbinePorts.inlet.temp, '℃', 1)} · ${fmt(turbinePorts.inlet.flow, 't/h', 1)}` : '--' }}</text>
          <text x="8" y="50" class="inst-sub">{{ turbinePorts.inlet ? turbinePorts.inlet.display_name : '本机组未设进汽点' }}</text>
        </g>

        <!-- 3. 机抽汽 -->
        <g
          transform="translate(222, 228)"
          :class="{ 'svg-clickable': Boolean(turbinePorts.extract) }"
          @click="selectTurbinePort(turbinePorts.extract)"
        >
          <rect x="0" y="0" width="148" height="58" rx="2" :class="['inst-box', activePortKey === 'extract' ? 'inst-focus' : '']" />
          <text x="8" y="15" class="inst-lbl">③ 抽汽 {{ turbinePorts.extract ? '' : '(无测点)' }}</text>
          <text x="8" y="34" class="inst-val-sm">{{ turbinePorts.extract ? `${fmt(turbinePorts.extract.temp, '℃', 1)} · ${fmt(turbinePorts.extract.flow, 't/h', 1)}` : '--' }}</text>
          <text x="8" y="50" class="inst-sub">{{ turbinePorts.extract ? turbinePorts.extract.display_name : '本机组未设抽汽点' }}</text>
        </g>

        <!-- 4. 排汽 / 低真空 -->
        <g
          transform="translate(464, 294)"
          :class="{ 'svg-clickable': Boolean(turbinePorts.exhaust) }"
          @click="selectTurbinePort(turbinePorts.exhaust)"
        >
          <rect x="0" y="0" width="154" height="58" rx="2" :class="['inst-box', activePortKey === 'exhaust' ? 'inst-focus' : '']" />
          <text x="8" y="15" class="inst-lbl">④ 排汽/低真空 {{ turbinePorts.exhaust ? '' : '(无)' }}</text>
          <text x="8" y="34" class="inst-val-sm">{{ turbinePorts.exhaust ? `${fmt(turbinePorts.exhaust.pressure, 'MPa', 2)} · ${fmt(turbinePorts.exhaust.flow, 't/h', 1)}` : '--' }}</text>
          <text x="8" y="50" class="inst-sub">{{ turbinePorts.exhaust ? turbinePorts.exhaust.display_name : '本机组未设排汽点' }}</text>
        </g>

        <!-- 右侧/底部：当前焦点测点高精度读数面板 -->
        <g transform="translate(636, 200)">
          <rect x="0" y="0" width="186" height="152" rx="2" class="inst-box inst-focus" />
          <text x="10" y="18" class="inst-lbl">当前聚焦测点实时工况</text>
          <text x="10" y="36" class="equip-hdr">{{ target.title }}</text>
          <text x="10" y="60" class="inst-val">{{ fmt(target.raw.temp, ' ℃', 1) }} ｜ {{ fmt(target.raw.pressure, ' MPa', 3) }}</text>
          <text x="10" y="84" class="inst-sub">瞬时流量：{{ fmt(target.raw.flow, ' t/h', 1) }}</text>
          <text x="10" y="103" class="inst-sub">瞬时热量：{{ fmt(target.raw.heat, ' GJ/h', 2) }}</text>
          <text x="10" y="122" class="inst-sub">小时积分：{{ fmt(target.raw.hour_heat_gj, ' GJ', 2) }}</text>
          <text x="10" y="141" class="inst-sub">采集时间：{{ (target.raw.source_time || '-').slice(5, 16) }}</text>
        </g>
      </svg>
    </div>

    <!-- 上游电厂（母管制）：全厂锅炉群与高压主蒸汽母管工艺组态图 -->
    <div v-else-if="target?.kind === 'upstream' && isBoilerHeaderView" class="pid-canvas-wrap">
      <svg class="pid-svg" viewBox="0 0 840 390" role="img" :aria-label="`${boilerHeaderData.plantName} 锅炉母管制工艺组态图`">
        <defs>
          <pattern id="pid-grid-bl" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#cdd6e2" stroke-width="0.6" />
          </pattern>
          <marker id="bl-arr" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#3b6b8f" />
          </marker>
          <marker id="bl-arr-act" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#1d4ed8" />
          </marker>
        </defs>

        <rect x="0" y="0" width="840" height="390" fill="#dae1e9" rx="2" />
        <rect x="0" y="0" width="840" height="390" fill="url(#pid-grid-bl)" opacity="0.65" />

        <!-- 标题栏 -->
        <text x="18" y="22" class="pipe-name">
          {{ boilerHeaderData.plantName }} · 母管制锅炉群与主蒸汽母管组态（共 {{ boilerHeaderData.totalCount }} 台锅炉 · {{ boilerHeaderData.runningCount }} 台并汽运行 · 点击任意锅炉切换聚焦）
        </text>

        <!-- 高压主蒸汽母管（全厂横向汇流总母管） -->
        <rect
          :x="boilerHeaderData.headerStartX - 18"
          y="50"
          :width="Math.max(60, boilerHeaderData.headerEndX - (boilerHeaderData.headerStartX - 18))"
          height="14"
          rx="3"
          :fill="boilerHeaderData.headerActive ? '#3b6b8f' : '#94a3b8'"
          stroke="#1e293b"
          stroke-width="1.3"
        />
        <line
          v-if="boilerHeaderData.headerActive"
          :x1="boilerHeaderData.headerStartX - 10"
          y1="57"
          :x2="boilerHeaderData.headerEndX - 8"
          y2="57"
          stroke="#dbeafe"
          stroke-width="2.4"
          stroke-dasharray="9 9"
          class="bl-header-flow"
        />
        <text :x="boilerHeaderData.headerStartX - 14" y="42" class="mini-lbl">
          高压主蒸汽母管 (MAIN STEAM HEADER) · 并列汇流出口 →
        </text>

        <!-- 遍历展示该电厂全部锅炉单元及主汽汇入支管 -->
        <g v-for="b in boilerHeaderData.boilers" :key="b.id">
          <!-- 主汽上行支管（锅炉出口 -> 主蒸汽母管三通） -->
          <line
            :x1="b.cx"
            y1="154"
            :x2="b.cx"
            y2="64"
            :class="['p-pipe', !b.running ? 'p-oos' : (b.isCurrent ? 'p-active-line' : 'p-supply')]"
            :marker-end="b.isCurrent ? 'url(#bl-arr-act)' : 'url(#bl-arr)'"
          />
          <line
            v-if="b.running"
            :x1="b.cx"
            y1="152"
            :x2="b.cx"
            y2="68"
            :class="b.isCurrent ? 'p-flow-anim-act' : 'p-flow-anim'"
          />
          <!-- 汇入母管三通法兰节点 -->
          <circle
            :cx="b.cx"
            cy="57"
            r="4.5"
            :fill="b.running ? (b.isCurrent ? '#1d4ed8' : '#38bdf8') : '#cbd5e1'"
            stroke="#1e293b"
            stroke-width="1.2"
          />

          <!-- 支路主汽电动隔离阀 / 逆止阀 -->
          <g :transform="`translate(${b.cx}, 106)`">
            <polygon points="-9,-9 0,0 9,-9" :fill="b.running ? '#475569' : '#94a3b8'" stroke="#1e293b" stroke-width="0.9" />
            <polygon points="-9,9 0,0 9,9" :fill="b.running ? '#475569' : '#94a3b8'" stroke="#1e293b" stroke-width="0.9" />
            <line x1="0" y1="0" x2="15" y2="0" stroke="#1e293b" stroke-width="1.3" />
            <rect x="13" y="-6" width="8" height="12" rx="1" fill="#cbd5e1" stroke="#334155" stroke-width="0.9" />
            <text x="26" y="4" class="mini-lbl">{{ b.running ? '并汽' : '隔绝' }}</text>
          </g>

          <!-- 锅炉本体矢量图形（可点击切换） -->
          <g :transform="`translate(${b.x}, 154)`" class="svg-clickable" @click="selectTurbinePort(b.raw)">
            <rect
              x="0"
              y="0"
              :width="b.w"
              height="104"
              rx="3"
              :class="[
                'equip-body',
                b.isCurrent ? 'inst-focus' : '',
                b.running ? 'tb-running-body' : 'tb-stopped-body',
                b.severity === 'critical' ? 'sev-box-critical' : (b.severity === 'warning' ? 'sev-box-warning' : ''),
              ]"
            />
            <!-- 上汽包 -->
            <rect :x="Math.round((b.w - 64) / 2)" y="10" width="64" height="15" rx="7" fill="#cbd5e1" stroke="#475569" stroke-width="1.2" />
            <text :x="Math.round(b.w / 2)" y="20.5" text-anchor="middle" font-size="8.5" font-weight="700" fill="#1e293b">
              #{{ b.unitNum }} 汽包
            </text>

            <!-- 炉膛与过热器受热面 -->
            <rect :x="Math.round((b.w - 72) / 2)" y="30" width="72" height="50" rx="2" fill="#d5dee8" stroke="#475569" stroke-width="1.1" />
            <!-- 水冷壁/过热器蛇形管 -->
            <polyline
              :points="`${Math.round(b.w / 2 - 26)},38 ${Math.round(b.w / 2 - 14)},46 ${Math.round(b.w / 2 - 26)},54 ${Math.round(b.w / 2 + 26)},54`"
              fill="none"
              :stroke="b.running ? '#b45309' : '#64748b'"
              stroke-width="1.5"
            />
            <!-- 运行时燃烧火焰动画 -->
            <g v-if="b.running" :transform="`translate(${Math.round(b.w / 2)}, 75)`" class="bl-flame-pulse">
              <path d="M -14 0 Q -8 -16 0 -20 Q 8 -16 14 0 Z" fill="#f59e0b" opacity="0.85" />
              <path d="M -7 0 Q 0 -13 7 0 Z" fill="#ea580c" />
            </g>
            <text v-else :x="Math.round(b.w / 2)" y="72" text-anchor="middle" font-size="9" fill="#64748b">炉膛冷态</text>

            <!-- 锅炉状态底部标签 -->
            <rect
              x="12"
              y="84"
              :width="b.w - 24"
              height="15"
              rx="2"
              :fill="b.running ? '#dcfce7' : '#e2e8f0'"
              :stroke="b.running ? '#0f766e' : '#64748b'"
              stroke-width="0.9"
            />
            <text
              :x="Math.round(b.w / 2)"
              y="94.5"
              text-anchor="middle"
              font-size="9"
              font-weight="700"
              :fill="b.running ? '#0f766e' : '#475569'"
            >
              #{{ b.unitNum }}炉 · {{ b.running ? '● 产汽运转' : '○ 停炉/热备' }}
            </text>
          </g>

          <!-- 锅炉主汽实时参数卡片（可点击聚焦） -->
          <g :transform="`translate(${b.x}, 268)`" class="svg-clickable" @click="selectTurbinePort(b.raw)">
            <rect x="0" y="0" :width="b.w" height="106" rx="2" :class="['inst-box', b.isCurrent ? 'inst-focus' : '']" />
            <text x="8" y="16" class="inst-lbl">
              {{ b.shortLabel }} {{ b.isCurrent ? '◆ 当前聚焦' : '' }}
            </text>
            <text x="8" y="38" class="inst-val-sm">汽温：{{ fmt(b.temp, ' ℃', 1) }}</text>
            <text x="8" y="57" class="inst-val-sm">汽压：{{ fmt(b.pressure, ' MPa', 3) }}</text>
            <text x="8" y="76" class="inst-val-sm">流量：{{ fmt(b.flow, ' t/h', 1) }}</text>
            <text x="8" y="95" class="inst-sub">{{ b.running ? '已并入高压母管' : '隔离/未并汽' }}</text>
          </g>
        </g>

        <!-- 右侧上部：主蒸汽母管汇流总况（带跳转回机侧快捷入口） -->
        <g transform="translate(668, 38)">
          <rect x="0" y="0" width="156" height="148" rx="2" class="inst-box" />
          <text x="10" y="18" class="inst-lbl">主蒸汽母管合流总况</text>
          <text x="10" y="42" class="inst-val">{{ fmt(boilerHeaderData.totalFlow, ' t/h', 1) }}</text>
          <text x="10" y="60" class="inst-sub">并汽锅炉：{{ boilerHeaderData.runningCount }} / {{ boilerHeaderData.totalCount }} 台</text>
          <text x="10" y="78" class="inst-sub">母管均温：{{ fmt(boilerHeaderData.avgTemp, ' ℃', 1) }}</text>
          <text x="10" y="96" class="inst-sub">母管均压：{{ fmt(boilerHeaderData.avgPressure, ' MPa', 3) }}</text>
          <text x="10" y="114" class="inst-sub">输出：至汽轮机/首站母管</text>
          <g v-if="plantTurbineShortcut" class="svg-clickable" @click="selectTurbinePort(plantTurbineShortcut)">
            <rect x="10" y="122" width="136" height="18" rx="2" fill="#dce8f5" stroke="#3b6b8f" stroke-width="1" />
            <text x="78" y="134.5" text-anchor="middle" font-size="9.5" font-weight="700" fill="#1e3a5f">→ 切至本厂汽轮机侧</text>
          </g>
        </g>

        <!-- 右侧下部：当前聚焦锅炉明细 -->
        <g transform="translate(668, 198)">
          <rect x="0" y="0" width="156" height="176" rx="2" class="inst-box inst-focus" />
          <text x="10" y="18" class="inst-lbl">当前聚焦锅炉实测</text>
          <text x="10" y="38" class="equip-hdr">{{ target.title }}</text>
          <text x="10" y="62" class="inst-val-sm">主汽温度：{{ fmt(target.raw.temp, ' ℃', 1) }}</text>
          <text x="10" y="82" class="inst-val-sm">主汽压力：{{ fmt(target.raw.pressure, ' MPa', 3) }}</text>
          <text x="10" y="102" class="inst-val-sm">瞬时流量：{{ fmt(target.raw.flow, ' t/h', 1) }}</text>
          <text x="10" y="122" class="inst-sub">瞬时热量：{{ fmt(target.raw.heat, ' GJ/h', 2) }}</text>
          <text x="10" y="140" class="inst-sub">小时积分：{{ fmt(target.raw.hour_heat_gj, ' GJ', 2) }}</text>
          <text x="10" y="158" class="inst-sub">采数：{{ (target.raw.source_time || '-').slice(5, 16) }}</text>
        </g>
      </svg>
    </div>

    <!-- 上游首站/网口水系统：管网与循环泵断面组态图 -->
    <div v-else-if="target?.kind === 'upstream'" class="pid-canvas-wrap">
      <svg class="pid-svg" viewBox="0 0 840 310" role="img" :aria-label="`${target.title} 上游工艺断面`">
        <rect x="0" y="0" width="840" height="310" fill="#dae1e9" rx="2" />
        <rect x="0" y="0" width="840" height="310" fill="url(#pid-grid)" opacity="0.65" />
        <line x1="30" y1="138" x2="810" y2="138" class="p-pipe p-supply" />
        <line x1="30" y1="138" x2="810" y2="138" class="p-flow-anim" />
        <rect x="96" y="88" width="160" height="100" rx="3" class="equip-body" />
        <circle cx="176" cy="124" r="14" fill="#eef2f6" stroke="#334155" stroke-width="1.3" />
        <polygon points="171,117 184,124 171,131" fill="#3b6b8f" />
        <text x="176" y="156" text-anchor="middle" class="equip-hdr">{{ target.raw.category }}</text>
        <text x="176" y="174" text-anchor="middle" class="inst-sub">{{ target.raw.sub_category || '-' }}</text>

        <g transform="translate(290, 62)">
          <rect x="0" y="0" width="150" height="66" rx="2" class="inst-box" />
          <text x="10" y="18" class="inst-lbl">瞬时温度 (WENDU)</text>
          <text x="10" y="45" class="inst-val-lg">{{ fmt(target.raw.temp, ' ℃', 1) }}</text>
        </g>
        <g transform="translate(460, 62)">
          <rect x="0" y="0" width="150" height="66" rx="2" class="inst-box" />
          <text x="10" y="18" class="inst-lbl">瞬时压力 (YALI)</text>
          <text x="10" y="45" class="inst-val-lg">{{ fmt(target.raw.pressure, ' MPa', 3) }}</text>
        </g>
        <g transform="translate(630, 62)">
          <rect x="0" y="0" width="160" height="66" rx="2" class="inst-box" />
          <text x="10" y="18" class="inst-lbl">瞬时流量</text>
          <text x="10" y="45" class="inst-val-lg">{{ fmt(target.raw.flow, ' t/h', 1) }}</text>
        </g>
        <g transform="translate(290, 158)">
          <rect x="0" y="0" width="236" height="66" rx="2" class="inst-box" />
          <text x="10" y="18" class="inst-lbl">瞬时热量 / 小时积分热量</text>
          <text x="10" y="46" class="inst-val-lg">{{ fmt(target.raw.heat, ' GJ/h', 1) }} ｜ {{ fmt(target.raw.hour_heat_gj, ' GJ', 1) }}</text>
        </g>
        <g transform="translate(546, 158)">
          <rect x="0" y="0" width="244" height="66" rx="2" class="inst-box" />
          <text x="10" y="18" class="inst-lbl">采集时间戳</text>
          <text x="10" y="46" class="inst-val-sm">{{ target.raw.source_time || '-' }}</text>
        </g>
      </svg>
    </div>

    <!-- 商业用户：用热支路阀门与换热表计组态图 -->
    <div v-else-if="target?.kind === 'merchant'" class="pid-canvas-wrap">
      <svg class="pid-svg" viewBox="0 0 840 340" role="img" :aria-label="`${target.title} 商业用热工艺组态图`">
        <defs>
          <marker id="mc-arr" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#3b6b8f" />
          </marker>
          <marker id="mc-arr-ret" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#64748b" />
          </marker>
        </defs>
        <rect x="0" y="0" width="840" height="340" fill="#dae1e9" rx="2" />
        <rect x="0" y="0" width="840" height="340" fill="url(#pid-grid)" opacity="0.65" />

        <!-- 供水主管 -> 电动调节阀 -> 商业换热机组 -->
        <line x1="24" y1="96" x2="544" y2="96" :class="['p-pipe', target.raw.online ? 'p-supply' : 'p-oos']" marker-end="url(#mc-arr)" />
        <line v-if="target.raw.online" x1="24" y1="96" x2="544" y2="96" class="p-flow-anim" />
        <text x="28" y="82" class="pipe-name">商业户进水/供汽管（{{ target.raw.rdry || '高温水' }}）</text>

        <!-- 回水出户管 -->
        <line x1="544" y1="220" x2="28" y2="220" class="p-pipe p-return" marker-end="url(#mc-arr-ret)" />
        <text x="28" y="242" class="pipe-name">商业户回水管</text>

        <!-- 电动调节阀与实时开度指示柱 -->
        <g transform="translate(260, 96)">
          <polygon points="-15,-11 0,0 -15,11" fill="#475569" stroke="#1e293b" stroke-width="1" />
          <polygon points="15,-11 0,0 15,11" fill="#475569" stroke="#1e293b" stroke-width="1" />
          <line x1="0" y1="0" x2="0" y2="-22" stroke="#1e293b" stroke-width="1.6" />
          <rect x="-12" y="-34" width="24" height="12" rx="1" fill="#cbd5e1" stroke="#334155" />
          <text x="0" y="25" text-anchor="middle" class="mini-lbl">调节阀</text>
        </g>

        <!-- 阀门开度条牌 -->
        <g transform="translate(206, 134)">
          <rect x="0" y="0" width="136" height="64" rx="2" class="inst-box" />
          <text x="8" y="16" class="inst-lbl">实测阀位 / 设定开度</text>
          <text x="8" y="36" class="inst-val-sm">{{ fmt(target.raw.valve_open, '%', 0) }} / {{ fmt(target.raw.valve_set, '%', 0) }}</text>
          <rect x="8" y="46" width="120" height="8" fill="#cbd5e1" stroke="#94a3b8" />
          <rect x="8" y="47" :width="valveFillPx" height="6" fill="#3b6b8f" />
        </g>

        <!-- 供水铭牌 -->
        <g transform="translate(28, 112)">
          <rect x="0" y="0" width="142" height="64" rx="2" class="inst-box" />
          <text x="8" y="16" class="inst-lbl">供温 / 供压</text>
          <text x="8" y="37" class="inst-val">{{ fmt(target.raw.temp_sup, ' ℃', 1) }}</text>
          <text x="8" y="55" class="inst-sub">供压 {{ fmt(target.raw.pres_sup, ' MPa', 3) }}</text>
        </g>

        <!-- 回水铭牌 -->
        <g transform="translate(28, 252)">
          <rect x="0" y="0" width="142" height="64" rx="2" class="inst-box" />
          <text x="8" y="16" class="inst-lbl">回温 / 回压</text>
          <text x="8" y="37" class="inst-val">{{ fmt(target.raw.temp_ret, ' ℃', 1) }}</text>
          <text x="8" y="55" class="inst-sub">回压 {{ fmt(target.raw.pres_ret, ' MPa', 3) }}</text>
        </g>

        <!-- 流量/热量积分表计盒 -->
        <g transform="translate(366, 134)">
          <rect x="0" y="0" width="160" height="64" rx="2" class="inst-box" />
          <text x="8" y="16" class="inst-lbl">瞬时流量 / 热量</text>
          <text x="8" y="36" class="inst-val-sm">{{ fmt(target.raw.flow, ' t/h', 2) }} ｜ {{ fmt(target.raw.heat, ' GJ/h', 2) }}</text>
          <text x="8" y="54" class="inst-sub">ΔT = {{ fmt(mcDeltaT, ' ℃', 1) }}</text>
        </g>

        <!-- 商业楼宇末端用热体 -->
        <g transform="translate(550, 62)">
          <rect x="0" y="0" width="260" height="248" rx="3" :class="['equip-body', target.severity === 'critical' ? 'sev-box-critical' : (target.severity === 'warning' ? 'sev-box-warning' : '')]" />
          <text x="130" y="22" text-anchor="middle" class="equip-hdr">商业用户换热终端</text>
          <!-- 商业大厦矢量轮廓 -->
          <rect x="86" y="36" width="88" height="84" fill="#b7c3d0" stroke="#475569" stroke-width="1.2" />
          <rect x="98" y="48" width="16" height="12" fill="#e0f2fe" stroke="#64748b" stroke-width="0.6" />
          <rect x="122" y="48" width="16" height="12" fill="#e0f2fe" stroke="#64748b" stroke-width="0.6" />
          <rect x="146" y="48" width="16" height="12" fill="#e0f2fe" stroke="#64748b" stroke-width="0.6" />
          <rect x="98" y="68" width="16" height="12" fill="#fef08a" stroke="#64748b" stroke-width="0.6" />
          <rect x="122" y="68" width="16" height="12" fill="#fef08a" stroke="#64748b" stroke-width="0.6" />
          <rect x="146" y="68" width="16" height="12" fill="#fef08a" stroke="#64748b" stroke-width="0.6" />
          <rect x="116" y="96" width="28" height="24" fill="#64748b" />

          <rect x="18" y="132" width="224" height="98" rx="2" fill="#f1f5f9" stroke="#94a3b8" />
          <text x="28" y="152" class="inst-lbl">小时积分耗热量（5分钟积分）</text>
          <text x="28" y="177" class="inst-val-lg">{{ fmt(target.raw.hour_heat_gj, ' GJ', 3) }}</text>
          <text x="28" y="198" class="inst-sub">小时流量：{{ fmt(target.raw.hour_flow_t, ' t', 2) }}</text>
          <text x="28" y="216" class="inst-sub">归属：{{ target.raw.rdfz || '-' }} / {{ target.raw.branch_name || '-' }}</text>
        </g>
      </svg>
    </div>

    <!-- 嵌入式 24h 运行过程记录仪（Recorder Strip） -->
    <div v-if="target" class="pid-recorder-box">
      <div class="recorder-head">
        <span>📈 工艺趋势记录仪（{{ target.title }} · 24 小时历史曲线）</span>
        <span v-if="trendLoading" class="muted-mini">读取历史序列…</span>
      </div>
      <div ref="recorderChartEl" class="recorder-chart"></div>
    </div>
  </div>
</template>

<script setup>
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  target: { type: Object, default: null },
  upstreamPoints: { type: Array, default: () => [] },
  trendRows: { type: Array, default: () => [] },
  trendLoading: { type: Boolean, default: false },
})

const emit = defineEmits(['select-upstream'])

const recorderChartEl = ref(null)
let recorderChart = null

const st = computed(() => props.target?.raw || {})

const isBoilerHeaderView = computed(() => {
  if (props.target?.kind !== 'upstream') return false
  return /炉.*主汽/.test(props.target.title || '')
})

const isTurbineView = computed(() => {
  if (props.target?.kind !== 'upstream' || isBoilerHeaderView.value) return false
  const txt = `${props.target.title || ''} ${st.value.sub_category || ''}`
  return /机.*(主汽|进汽|进气|抽汽|抽气|排汽|排气|低真空|尖峰)|汽机|号机/.test(txt)
})

const turbinePlantTag = computed(() => {
  const txt = `${props.target?.title || ''} ${st.value.sub_category || ''}`
  if (txt.includes('北海')) return '北海'
  if (txt.includes('香海')) return '香海'
  return ''
})

const turbineUnitNum = computed(() => {
  const txt = `${props.target?.title || ''}`
  const m = txt.match(/[#]?([1-8])[#号]?(机|炉)/)
  return m ? m[1] : ''
})

const turbineContextTitle = computed(() => {
  const p = turbinePlantTag.value ? `${turbinePlantTag.value}电厂` : '热源电厂'
  const u = turbineUnitNum.value ? ` #${turbineUnitNum.value} 机组` : ''
  return `${p}${u}`
})

const activePortKey = computed(() => {
  const txt = String(props.target?.title || '')
  if (/排汽|排气|低真空|尖峰/.test(txt)) return 'exhaust'
  if (/抽汽|抽气/.test(txt)) return 'extract'
  if (/进汽|进气|调门/.test(txt)) return 'inlet'
  if (/主汽/.test(txt)) return 'main'
  return 'main'
})

const plantUpstreamPool = computed(() => {
  const plant = turbinePlantTag.value
  return (props.upstreamPoints || []).filter((u) => {
    if (!plant) return u.category === '电厂'
    return `${u.display_name || ''} ${u.sub_category || ''}`.includes(plant)
  })
})

const plantBoilerShortcut = computed(() => {
  const boilers = plantUpstreamPool.value.filter((u) => /炉.*主汽/.test(u.display_name || ''))
  return boilers.find((b) => (Number(b.flow) || 0) > 2.0) || boilers[0] || null
})

const plantTurbineShortcut = computed(() => {
  const turbines = plantUpstreamPool.value.filter((u) => /机.*(主汽|进汽|进气|抽汽|抽气)/.test(u.display_name || ''))
  return turbines.find((t) => (Number(t.flow) || 0) > 2.0) || turbines[0] || null
})

const turbinePorts = computed(() => {
  if (!isTurbineView.value) {
    return { main: null, inlet: null, extract: null, exhaust: null, unitTurbineList: [] }
  }
  const unit = turbineUnitNum.value
  // 母管制电厂：机侧仅严格取本机组汽轮机本体测点，绝不混显或回退锅炉主汽参数
  const unitPool = unit
    ? plantUpstreamPool.value.filter((u) => {
        const nm = `${u.display_name || ''}`
        return (nm.includes(`#${unit}`) || nm.includes(`${unit}号`)) && /机|低真空|尖峰/.test(nm)
      })
    : []

  const pickInUnit = (regex) => unitPool.find((u) => regex.test(u.display_name || '')) || null
  const curId = props.target?.id
  const curRaw = props.target?.raw

  const turbineMain = pickInUnit(/机.*主汽/)
  const inlet = pickInUnit(/机.*(进汽|进气)/)
  const extract = pickInUnit(/机.*(抽汽|抽气)/)
  const exhaust = pickInUnit(/机.*(排汽|排气)/) || pickInUnit(/低真空供水|尖峰加热器/)

  const ports = {
    main: turbineMain || (activePortKey.value === 'main' ? curRaw : null),
    inlet: inlet || (activePortKey.value === 'inlet' ? curRaw : null),
    extract: extract || (activePortKey.value === 'extract' ? curRaw : null),
    exhaust: exhaust || (activePortKey.value === 'exhaust' ? curRaw : null),
    unitTurbineList: unitPool,
  }
  if (curRaw && `${curRaw.data_zone}:${curRaw.source_name}` === curId) {
    if (activePortKey.value === 'main') ports.main = curRaw
    else if (activePortKey.value === 'inlet') ports.inlet = curRaw
    else if (activePortKey.value === 'extract') ports.extract = curRaw
    else if (activePortKey.value === 'exhaust') ports.exhaust = curRaw
  }
  return ports
})

function selectTurbinePort(pt) {
  if (pt) emit('select-upstream', pt)
}

const isTurbineRunning = computed(() => {
  if (!isTurbineView.value) return false
  const ports = turbinePorts.value
  // 汇集本台汽轮机全部机侧测点（如 #3机含左进汽/右进汽/抽汽等），仅凭汽轮机本体真实流量或热量判别运转
  const seen = new Set()
  const candidates = []
  for (const pt of [...(ports.unitTurbineList || []), ports.main, ports.inlet, ports.extract, ports.exhaust, st.value]) {
    if (!pt) continue
    const k = `${pt.data_zone || ''}:${pt.source_name || pt.display_name || ''}`
    if (seen.has(k)) continue
    seen.add(k)
    candidates.push(pt)
  }
  return candidates.some((pt) => {
    const flow = Number(pt.flow)
    const heat = Number(pt.heat)
    const hrHeat = Number(pt.hour_heat_gj)
    return (Number.isFinite(flow) && flow > 2.0)
      || (Number.isFinite(heat) && heat > 1.0)
      || (Number.isFinite(hrHeat) && hrHeat > 1.0)
  })
})

const boilerHeaderData = computed(() => {
  const plantName = turbinePlantTag.value ? `${turbinePlantTag.value}热电厂` : '热电厂'
  if (!isBoilerHeaderView.value) {
    return { plantName, boilers: [], totalCount: 0, runningCount: 0, totalFlow: null, avgTemp: null, avgPressure: null, headerActive: false, headerStartX: 80, headerEndX: 668 }
  }
  const curId = props.target?.id
  const rawList = plantUpstreamPool.value.filter((u) => /炉.*主汽/.test(u.display_name || ''))
  const list = rawList.length ? rawList : (props.target?.raw ? [props.target.raw] : [])
  const parsed = list.map((u, idx) => {
    const nm = `${u.display_name || ''}`
    const m = nm.match(/[#]?([1-8])[#号]?炉/)
    const unitNum = m ? m[1] : String(idx + 1)
    const flow = u.flow != null ? Number(u.flow) : null
    const temp = u.temp != null ? Number(u.temp) : null
    const pressure = u.pressure != null ? Number(u.pressure) : null
    const heat = u.heat != null ? Number(u.heat) : null
    const running = (Number.isFinite(flow) && flow > 2.0) || (Number.isFinite(heat) && heat > 1.0)
    const id = `${u.data_zone}:${u.source_name}`
    return {
      id,
      unitOrder: Number(unitNum) || idx + 1,
      unitNum,
      shortLabel: `#${unitNum}炉主汽`,
      displayName: nm,
      isCurrent: id === curId,
      flow,
      temp,
      pressure,
      heat,
      running,
      severity: u._severity || 'normal',
      raw: u,
    }
  }).sort((a, b) => a.unitOrder - b.unitOrder)

  const count = Math.max(1, parsed.length)
  const areaLeft = 18
  const areaWidth = 636
  const gap = parsed.length > 4 ? 8 : 12
  const slotW = Math.min(150, Math.floor((areaWidth - gap * (count - 1)) / count))
  const totalW = count * slotW + (count - 1) * gap
  const startX = areaLeft + Math.floor((areaWidth - totalW) / 2)

  const boilers = parsed.map((b, i) => {
    const x = startX + i * (slotW + gap)
    return { ...b, x, w: slotW, cx: x + Math.round(slotW / 2) }
  })

  const activeBoilers = boilers.filter((b) => b.running)
  const flowList = activeBoilers.map((b) => b.flow).filter((n) => Number.isFinite(n) && n > 0)
  const totalFlow = flowList.length ? flowList.reduce((acc, n) => acc + n, 0) : 0
  const tempPool = (activeBoilers.length ? activeBoilers : boilers).map((b) => b.temp).filter((n) => Number.isFinite(n) && n > 40)
  const presPool = (activeBoilers.length ? activeBoilers : boilers).map((b) => b.pressure).filter((n) => Number.isFinite(n) && n > 0.1)

  return {
    plantName,
    boilers,
    totalCount: boilers.length,
    runningCount: activeBoilers.length,
    totalFlow: boilers.length ? totalFlow : null,
    avgTemp: tempPool.length ? tempPool.reduce((a, b) => a + b, 0) / tempPool.length : null,
    avgPressure: presPool.length ? presPool.reduce((a, b) => a + b, 0) / presPool.length : null,
    headerActive: activeBoilers.length > 0,
    headerStartX: boilers[0]?.cx ?? 80,
    headerEndX: 668,
  }
})

function fmt(val, suffix = '', fixed = 2) {
  if (val === null || val === undefined || val === '') return '--'
  const num = Number(val)
  if (!Number.isFinite(num)) return '--'
  return `${num.toFixed(fixed).replace(/\.00$/, '')}${suffix}`
}

const deltaT = computed(() => {
  if (st.value.e3 == null || st.value.e4 == null) return null
  return Number(st.value.e3) - Number(st.value.e4)
})

const mcDeltaT = computed(() => {
  if (st.value.temp_sup == null || st.value.temp_ret == null) return null
  return Number(st.value.temp_sup) - Number(st.value.temp_ret)
})

const valveFillPx = computed(() => {
  const n = Number(st.value.valve_open)
  if (!Number.isFinite(n) || n <= 0) return 0
  return Math.max(2, Math.min(120, Math.round((n / 100) * 120)))
})

const tankFillPx = computed(() => {
  const n = Number(st.value.e16)
  if (!Number.isFinite(n) || n <= 0) return 6
  return Math.max(4, Math.min(46, Math.round((n / 2500) * 46)))
})

const roomFillPx = computed(() => {
  const n = Number(st.value.avg_room_temp)
  if (!Number.isFinite(n)) return 0
  const pct = Math.max(0.08, Math.min(1, (n - 10) / 20))
  return Math.round(pct * 94)
})

const tempAlarmClass = computed(() => {
  const f = String(st.value.fault_tag || '')
  if (f.includes('TEMP_INVERSION') || f.includes('SENSOR_OUT_OF_RANGE')) return 'inst-crit'
  return ''
})

const waterAlarm = computed(() => Boolean(st.value.field_notes?.e14))
const elecAlarm = computed(() => Boolean(st.value.field_notes?.hour_elec_kwh))
const roomAlarm = computed(() => st.value.avg_room_temp != null && Number(st.value.avg_room_temp) < 18)

const heatEquipClass = computed(() => {
  if (!st.value.online && st.value.has_record) return 'sev-box-critical'
  if (props.target?.severity === 'warning') return 'sev-box-warning'
  return ''
})

function renderRecorder() {
  if (!recorderChartEl.value) return
  if (!recorderChart) recorderChart = echarts.init(recorderChartEl.value)
  const rows = props.trendRows || []
  const labels = rows.map((r) => r.label || `${String(r.hour).padStart(2, '0')}:00`)
  const isSt = props.target?.kind === 'station'
  const isMc = props.target?.kind === 'merchant'

  recorderChart.setOption({
    backgroundColor: '#e5ebf2',
    grid: { left: 42, right: 42, top: 28, bottom: 22 },
    tooltip: { trigger: 'axis', confine: true },
    legend: {
      top: 2,
      textStyle: { fontSize: 11, color: '#334155' },
      itemWidth: 12,
      itemHeight: 8,
    },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: { fontSize: 10, color: '#475569' },
      axisLine: { lineStyle: { color: '#94a3b8' } },
    },
    yAxis: [
      {
        type: 'value',
        name: '热量 (GJ)',
        nameTextStyle: { fontSize: 10, color: '#475569' },
        axisLabel: { fontSize: 10, color: '#475569' },
        splitLine: { lineStyle: { color: '#cfd8e3' } },
      },
      {
        type: 'value',
        name: '温度 (℃)',
        nameTextStyle: { fontSize: 10, color: '#475569' },
        axisLabel: { fontSize: 10, color: '#475569' },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '小时热量(GJ)',
        type: 'bar',
        data: rows.map((r) => r.hour_heat_gj ?? null),
        itemStyle: { color: '#5c84a6' },
        barMaxWidth: 14,
      },
      {
        name: isSt ? '一网供温' : (isMc ? '商业供温' : '测点温度'),
        type: 'line',
        yAxisIndex: 1,
        data: rows.map((r) => (isSt ? r.avg_sup_temp : (isMc ? r.temp_sup : r.temp)) ?? null),
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 2, color: '#1e3a5f' },
      },
      ...(isSt || isMc
        ? [{
            name: isMc ? '商业回温' : '一网回温',
            type: 'line',
            yAxisIndex: 1,
            data: rows.map((r) => (isMc ? r.temp_ret : r.avg_ret_temp) ?? null),
            smooth: false,
            symbol: 'none',
            lineStyle: { width: 1.6, type: 'dashed', color: '#475569' },
          }]
        : []),
    ],
  }, true)
}

watch(
  () => [props.target?.id, props.trendRows],
  async () => {
    await nextTick()
    renderRecorder()
  },
  { deep: false }
)

function onResize() {
  recorderChart?.resize()
}

onMounted(() => {
  window.addEventListener('resize', onResize)
  nextTick(renderRecorder)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  recorderChart?.dispose()
})
</script>

<style scoped>
.pid-stage {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pid-stage-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.pid-title-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.pid-tag-code {
  font-family: Consolas, monospace;
  font-size: 11px;
  font-weight: 700;
  background: #233042;
  color: #e2e8f0;
  padding: 2px 7px;
  border-radius: 2px;
}

.pid-title-left h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.pid-sub {
  font-size: 12px;
  color: #475569;
}

.pid-mode-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 2px;
}

.pid-mode-badge.sev-normal { background: #dce6ef; color: #1e3a5f; border: 1px solid #96a4b5; }
.pid-mode-badge.sev-warning { background: #fef3c7; color: #92400e; border: 1px solid #f59e0b; }
.pid-mode-badge.sev-critical { background: #fee2e2; color: #991b1b; border: 1px solid #ef4444; }
.pid-mode-badge.sev-offline { background: #cbd5e1; color: #334155; }

.pid-canvas-wrap {
  width: 100%;
  overflow-x: auto;
  border: 1px solid #9aa7b7;
  border-radius: 2px;
  background: #dae1e9;
}

.pid-svg {
  display: block;
  width: 100%;
  min-width: 720px;
  height: auto;
}

.p-pipe {
  stroke-width: 4;
  fill: none;
}
.p-supply { stroke: #3b6b8f; }
.p-active-line { stroke: #1d4ed8; stroke-width: 5; }
.p-return { stroke: #6e8094; }
.p-water { stroke: #4b83a6; stroke-width: 3; }
.p-oos { stroke: #94a3b8; stroke-dasharray: 6 4; }

.p-flow-anim {
  stroke: #93c5fd;
  stroke-width: 2;
  stroke-dasharray: 8 10;
  animation: pid-flow 1s linear infinite;
}

.p-flow-anim-act {
  stroke: #dbeafe;
  stroke-width: 2.4;
  stroke-dasharray: 8 8;
  animation: pid-flow 0.75s linear infinite;
}

.svg-clickable { cursor: pointer; }
.inst-box.inst-focus {
  fill: #e0ecfb;
  stroke: #1d4ed8;
  stroke-width: 1.8;
}

.tb-running-body {
  fill: #eaf0f6;
  stroke: #2c4a6b;
}
.tb-stopped-body {
  fill: #d8dfe7;
  stroke: #7c8b9e;
}

.tb-blades-spin line {
  animation: tb-blades-move 0.55s linear infinite;
}

@keyframes tb-blades-move {
  from { stroke-dashoffset: 10; }
  to { stroke-dashoffset: 0; }
}

.tb-shaft-spin {
  animation: tb-shaft-move 0.45s linear infinite;
}

@keyframes tb-shaft-move {
  from { stroke-dashoffset: 16; }
  to { stroke-dashoffset: 0; }
}

.tb-coupling-spin {
  animation: tb-coupling-move 0.45s linear infinite;
}

@keyframes tb-coupling-move {
  from { stroke-dashoffset: 6; }
  to { stroke-dashoffset: 0; }
}

.tb-gen-rotor {
  animation: tb-gen-rotate 1.8s linear infinite;
}

@keyframes tb-gen-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.bl-header-flow {
  animation: bl-header-move 0.9s linear infinite;
}

@keyframes bl-header-move {
  from { stroke-dashoffset: 18; }
  to { stroke-dashoffset: 0; }
}

.bl-flame-pulse {
  animation: bl-flame-flicker 1.1s ease-in-out infinite alternate;
}

@keyframes bl-flame-flicker {
  from { opacity: 0.78; }
  to { opacity: 1; }
}

@keyframes pid-flow {
  from { stroke-dashoffset: 18; }
  to { stroke-dashoffset: 0; }
}

.pipe-name {
  font-size: 10.5px;
  font-weight: 700;
  fill: #334155;
}

.mini-lbl {
  font-size: 10px;
  font-weight: 600;
  fill: #475569;
}

.inst-box {
  fill: #eef2f6;
  stroke: #8f9ead;
  stroke-width: 1.2;
}
.inst-box.inst-crit { fill: #fef2f2; stroke: #dc2626; stroke-width: 1.6; }
.inst-box.inst-warn { fill: #fffbeb; stroke: #d97706; stroke-width: 1.5; }

.inst-lbl { font-size: 10px; font-weight: 600; fill: #475569; }
.inst-val { font-family: Consolas, monospace; font-size: 14px; font-weight: 700; fill: #0f172a; }
.inst-val.inst-crit, .txt-crit { fill: #b91c1c !important; }
.inst-val-lg { font-family: Consolas, monospace; font-size: 15px; font-weight: 700; fill: #0f172a; }
.inst-val-sm { font-family: Consolas, monospace; font-size: 12px; font-weight: 700; fill: #0f172a; }
.inst-sub { font-size: 10.5px; fill: #475569; }

.equip-body {
  fill: #eef2f6;
  stroke: #7c8d9f;
  stroke-width: 1.5;
}
.equip-body.sev-box-critical { fill: #fef2f2; stroke: #dc2626; }
.equip-body.sev-box-warning { fill: #fffbeb; stroke: #d97706; }

.equip-hdr {
  font-size: 12px;
  font-weight: 700;
  fill: #0f172a;
}

.pid-recorder-box {
  background: #e5ebf2;
  border: 1px solid #a8b4c2;
  border-radius: 2px;
  padding: 6px 10px;
}

.recorder-head {
  display: flex;
  justify-content: space-between;
  font-size: 11.5px;
  font-weight: 700;
  color: #334155;
  margin-bottom: 4px;
}

.recorder-chart {
  width: 100%;
  height: 158px;
}

.muted-mini { font-size: 11px; color: #64748b; font-weight: 500; }
</style>
