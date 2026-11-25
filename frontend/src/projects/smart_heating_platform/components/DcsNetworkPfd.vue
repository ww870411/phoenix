<template>
  <div class="pfd-shell">
    <div class="mobile-pan-hint">← 左右滑动查看完整全网工艺总貌图（点击节点可联动下钻） →</div>
    <div class="pfd-wrap">
    <svg
      class="pfd-svg"
      viewBox="0 0 1280 374"
      role="img"
      aria-label="主城区智慧供热分系统工艺组态图"
    >
      <defs>
        <marker id="arrow-pipe" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="#64748b" />
        </marker>
        <marker id="arrow-active" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="#1d4ed8" />
        </marker>
        <pattern id="dcs-grid-pat" width="20" height="20" patternUnits="userSpaceOnUse">
          <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#cfd7e2" stroke-width="0.6" />
        </pattern>
      </defs>

      <!-- 哑光仪表背景底纹 -->
      <rect x="0" y="0" width="1280" height="374" fill="#dce2ea" rx="2" />
      <rect x="0" y="0" width="1280" height="374" fill="url(#dcs-grid-pat)" opacity="0.6" />

      <!-- 北海 / 香海 两大独立热源体系分界区带 -->
      <rect x="10" y="28" width="998" height="146" rx="3" fill="#d3dce7" opacity="0.45" />
      <rect x="10" y="246" width="998" height="114" rx="3" fill="#d0dae6" opacity="0.45" />
      <line x1="12" y1="241" x2="1008" y2="241" stroke="#94a3b8" stroke-width="1" stroke-dasharray="6 4" />
      <text x="16" y="198" class="zone-divider-lbl">── 上区：北海热电体系（含中心区）</text>
      <text x="16" y="214" class="zone-divider-lbl">── 中区：独立热源 ── 下区：香海热电体系</text>

      <!-- 区域标题标尺 -->
      <text x="16" y="20" class="stage-hdr">STAGE 1 · 分厂热源</text>
      <text x="242" y="20" class="stage-hdr">STAGE 2 · 各自首站/枢纽</text>
      <text x="485" y="20" class="stage-hdr">STAGE 3 · 分系统主干管网（北海系 / 独立源 / 香海系）</text>
      <text x="1030" y="20" class="stage-hdr">STAGE 4 · 末端换热与保障</text>

      <!-- 工艺管道 1：北海电厂 -> 北海#2首站 / 北海#1首站（北海系内部，不连香海） -->
      <path d="M 192 74 L 222 74 L 222 68 L 245 68" class="pipe-supply" marker-end="url(#arrow-pipe)" />
      <path d="M 192 126 L 222 126 L 222 146 L 245 146" class="pipe-supply" marker-end="url(#arrow-pipe)" />

      <!-- 工艺管道 2：香海电厂 -> 香海首站/低真空/蒸汽网（香海系内部，不连北海电厂） -->
      <path d="M 192 296 L 245 296" class="pipe-supply" marker-end="url(#arrow-pipe)" />

      <!-- 各自独立的分区集分水母管（北海#2母管 / 中心区主网母管 / 香海供热母管） -->
      <!-- 1. 北海#2首站 -> 北海#2母管（只供北海北网/北海南网） -->
      <path d="M 420 68 L 448 68" class="pipe-supply" />
      <rect x="448" y="40" width="9" height="54" rx="2" fill="#5e7996" stroke="#334155" stroke-width="1" />
      <text x="452" y="35" text-anchor="middle" class="mini-lbl">北海#2母管</text>

      <!-- 2. 北海#1/水炉首站 -> 中心区主网母管（供东环/南环） -->
      <path d="M 420 138 L 448 138" class="pipe-supply" />
      <rect x="448" y="108" width="9" height="56" rx="2" fill="#5e7996" stroke="#334155" stroke-width="1" />
      <text x="443" y="103" text-anchor="end" class="mini-lbl">中心区母管</text>

      <!-- 3. 跨区联络虚线支路（仅示意香海首站对中心区东/南环混水界并网） -->
      <path d="M 420 266 L 432 266 L 432 156 L 448 156" class="pipe-tie" />
      <circle cx="432" cy="238" r="3.5" fill="#e2e8f0" stroke="#475569" stroke-width="1.2" />
      <text x="424" y="236" text-anchor="end" class="tie-lbl">香-北联络</text>

      <!-- 4. 香海首站/低真空 -> 香海独立母管（只供香海#1低真空 / #3低真空 / 香海蒸汽网） -->
      <path d="M 420 296 L 448 296" class="pipe-supply" />
      <rect x="448" y="254" width="9" height="88" rx="2" fill="#5e7996" stroke="#334155" stroke-width="1" />
      <text x="452" y="249" text-anchor="middle" class="mini-lbl">香海母管</text>

      <!-- 独立调峰小站标识徽章（老热泵 / 电锅炉不接两电厂母管） -->
      <g v-for="solo in soloNetBadges" :key="solo.key">
        <rect x="440" :y="solo.cy - 9" width="32" height="18" rx="2" fill="#e5eaf0" stroke="#7c8d9f" stroke-width="1" />
        <text x="456" :y="solo.cy + 3.5" text-anchor="middle" font-size="8.5" font-weight="700" fill="#475569">独立</text>
      </g>

      <!-- 右侧分组汇集入末端统计（不再用一整根铁棒将北海香海焊死） -->
      <rect x="990" y="40" width="9" height="124" rx="2" fill="#7c8d9f" stroke="#475569" stroke-width="1" />
      <path d="M 999 102 L 1018 102 L 1018 76 L 1028 76" class="pipe-supply" marker-end="url(#arrow-pipe)" />
      <rect x="990" y="254" width="9" height="88" rx="2" fill="#7c8d9f" stroke="#475569" stroke-width="1" />
      <path d="M 999 298 L 1018 298 L 1018 106 L 1028 106" class="pipe-supply" marker-end="url(#arrow-pipe)" />
      <path d="M 1018 190 L 1028 190" class="pipe-supply" marker-end="url(#arrow-pipe)" />
      <path d="M 1018 286 L 1028 286" class="pipe-supply" marker-end="url(#arrow-pipe)" />

      <!-- STAGE 1: 北海热电厂 & 香海热电厂 矢量设备组 -->
      <g
        v-for="(plant, idx) in plantPositions"
        :key="plant.key"
        class="svg-clickable"
        @click="$emit('select-plant', plant.data)"
      >
        <rect
          :x="16"
          :y="plant.y"
          width="176"
          height="112"
          rx="3"
          :class="['equip-box', `sev-box-${plant.data.severity}`]"
        />
        <!-- 锅炉 + 梯形汽轮机 + 发电机矢量图标 -->
        <rect :x="24" :y="plant.y + 14" width="16" height="26" fill="#c7d1dc" stroke="#475569" stroke-width="1.1" />
        <path :d="`M ${27} ${plant.y + 32} L ${32} ${plant.y + 22} L ${37} ${plant.y + 32}`" fill="none" stroke="#b45309" stroke-width="1.2" />
        <line :x1="40" :y1="plant.y + 22" x2="48" :y2="plant.y + 22" stroke="#475569" stroke-width="1.4" />
        <polygon
          :points="`${48},${plant.y + 16} ${68},${plant.y + 11} ${68},${plant.y + 35} ${48},${plant.y + 30}`"
          fill="#b8c4d1"
          stroke="#334155"
          stroke-width="1.2"
        />
        <line :x1="68" :y1="plant.y + 23" x2="73" :y2="plant.y + 23" stroke="#334155" stroke-width="1.4" />
        <line
          v-if="plant.data.running"
          x1="50"
          :y1="plant.y + 23"
          x2="67"
          :y2="plant.y + 23"
          stroke="#1d4ed8"
          stroke-width="2"
          stroke-dasharray="3 3"
          class="mini-rotor-anim"
        />
        <circle :cx="78" :cy="plant.y + 23" r="6" fill="#e2e8f0" stroke="#334155" stroke-width="1.1" />
        <circle
          v-if="plant.data.running"
          :cx="78"
          :cy="plant.y + 23"
          r="8.5"
          fill="none"
          stroke="#2563eb"
          stroke-width="1"
          stroke-dasharray="4 4"
          :style="{ transformOrigin: `78px ${plant.y + 23}px` }"
          class="mini-gen-spin"
        />
        <text :x="78" :y="plant.y + 26.5" text-anchor="middle" font-size="8" font-weight="700" fill="#1e3a5f">G</text>

        <text :x="90" :y="plant.y + 24" class="equip-title">{{ plant.data.title }}</text>
        <text :x="90" :y="plant.y + 39" class="equip-sub">{{ plant.data.count }} 监测点</text>

        <!-- 内嵌仪器铭牌 -->
        <rect :x="26" :y="plant.y + 52" width="74" height="48" rx="2" fill="#edf2f7" stroke="#94a3b8" />
        <text :x="32" :y="plant.y + 68" class="tag-lbl">积分热量</text>
        <text :x="32" :y="plant.y + 88" class="tag-val">{{ fmt(plant.data.hourHeat, ' GJ', 0) }}</text>

        <rect :x="106" :y="plant.y + 52" width="76" height="48" rx="2" fill="#edf2f7" stroke="#94a3b8" />
        <text :x="112" :y="plant.y + 68" class="tag-lbl">平均温度</text>
        <text :x="112" :y="plant.y + 88" class="tag-val">{{ fmt(plant.data.avgTemp, '℃', 1) }}</text>

        <!-- 状态指示灯 -->
        <circle :cx="178" :cy="plant.y + 14" r="5" :class="['led-dot', `led-${plant.data.severity}`]" />
      </g>

      <!-- STAGE 2: 首站板式换热机组矢量符号 -->
      <g
        v-for="hub in hubPositions"
        :key="hub.key"
        class="svg-clickable"
        @click="$emit('select-hub', hub.data)"
      >
        <rect
          :x="248"
          :y="hub.y"
          width="172"
          height="74"
          rx="3"
          :class="['equip-box', `sev-box-${hub.data.severity}`]"
        />
        <!-- 板式换热器波纹符号 -->
        <rect :x="258" :y="hub.y + 11" width="24" height="26" fill="#cbd5e1" stroke="#334155" stroke-width="1.2" />
        <path
          :d="`M ${262} ${hub.y + 15} L ${278} ${hub.y + 20} L ${262} ${hub.y + 26} L ${278} ${hub.y + 31} L ${262} ${hub.y + 34}`"
          fill="none"
          stroke="#1e3a5f"
          stroke-width="1.2"
        />
        <!-- 循环泵符号 -->
        <circle :cx="270" :cy="hub.y + 54" r="8" fill="#cbd5e1" stroke="#334155" stroke-width="1.2" />
        <polygon :points="`${266},${hub.y + 49} ${275},${hub.y + 54} ${266},${hub.y + 59}`" fill="#3b6b8f" />

        <text :x="290" :y="hub.y + 22" class="equip-title">{{ hub.data.title }}</text>
        <text :x="290" :y="hub.y + 37" class="equip-sub">{{ hub.data.count }} 点 · 最高 {{ fmt(hub.data.maxTemp, '℃', 1) }}</text>
        <text :x="290" :y="hub.y + 59" class="tag-val-sm">总流量 {{ fmt(hub.data.sumFlow, ' t/h', 0) }}</text>

        <circle :cx="408" :cy="hub.y + 13" r="4.5" :class="['led-dot', `led-${hub.data.severity}`]" />
      </g>

      <!-- STAGE 3: 9 大主干热网真实分流管道 + 调节阀 + 流量热计铭牌 -->
      <g
        v-for="(net, i) in rdfzRows"
        :key="net.group_key || i"
        class="svg-clickable"
        @click="$emit('toggle-rdfz', net.group_name)"
      >
        <!-- 供水管道（带流动动画当选中） -->
        <line
          :x1="net.solo ? 472 : 457"
          :y1="net.cy"
          :x2="net.solo ? 1018 : 990"
          :y2="net.cy"
          :class="['net-pipe', { active: selectedRdfz === net.group_name, dimmed: selectedRdfz && selectedRdfz !== net.group_name }]"
        />
        <line
          v-if="selectedRdfz === net.group_name"
          :x1="net.solo ? 472 : 457"
          :y1="net.cy"
          :x2="net.solo ? 1018 : 990"
          :y2="net.cy"
          class="net-pipe-flow"
        />

        <!-- 电动调节阀矢量符号（双三角蝴蝶阀） -->
        <polygon
          :points="`474,${net.cy - 6} 484,${net.cy} 474,${net.cy + 6}`"
          :fill="selectedRdfz === net.group_name ? '#2563eb' : '#64748b'"
        />
        <polygon
          :points="`494,${net.cy - 6} 484,${net.cy} 494,${net.cy + 6}`"
          :fill="selectedRdfz === net.group_name ? '#2563eb' : '#64748b'"
        />
        <line x1="484" :y1="net.cy" x2="484" :y2="net.cy - 9" stroke="#334155" stroke-width="1.2" />
        <rect x="479" y="0" :transform="`translate(0, ${net.cy - 13})`" width="10" height="5" fill="#94a3b8" stroke="#334155" stroke-width="0.8" />

        <!-- 管网参数 Tag 铭牌盒 -->
        <rect
          x="508"
          :y="net.cy - 14"
          width="462"
          height="28"
          rx="2"
          :class="[
            'pipe-tag-plate',
            `sev-box-${net.severity}`,
            { selected: selectedRdfz === net.group_name },
          ]"
        />
        <!-- 告警点 -->
        <circle :cx="520" :cy="net.cy" r="4" :class="['led-dot', `led-${net.severity}`]" />
        <!-- 管网名 -->
        <text x="530" :y="net.cy + 4" class="net-lbl">{{ net.group_name }}</text>
        <!-- 站数 -->
        <text x="626" :y="net.cy + 4" class="net-mono">{{ net.online_stations }}/{{ net.total_stations }}站</text>
        <!-- 小时供热量 -->
        <text x="692" :y="net.cy + 4" class="net-mono-bold">{{ fmt(net.hour_heat_gj, ' GJ', 1) }}</text>
        <!-- 供回温 -->
        <text x="774" :y="net.cy + 4" class="net-mono">{{ fmt(net.avg_sup_temp, '', 0) }}/{{ fmt(net.avg_ret_temp, '℃', 0) }}</text>

        <!-- 嵌入式热指标 Analog Bar -->
        <rect x="850" :y="net.cy - 5" width="70" height="10" fill="#cbd5e1" stroke="#94a3b8" stroke-width="0.8" />
        <rect x="863" :y="net.cy - 5" width="35" height="10" fill="#b0c2d4" />
        <rect
          x="850"
          :y="net.cy - 4"
          :width="barWidth(net.heat_index_wm2, 80, 70)"
          height="8"
          :fill="net.severity === 'critical' ? '#dc2626' : (net.severity === 'warning' ? '#d97706' : '#3b6b8f')"
        />
        <text x="926" :y="net.cy + 4" class="net-mono">{{ fmt(net.heat_index_wm2, ' W', 0) }}</text>
      </g>

      <!-- STAGE 4: 末端换热群 + 商业用户阀组 + 居民楼宇室温液柱 -->
      <!-- 1. 242 换热站群 -->
      <g>
        <rect x="1030" y="38" width="234" height="90" rx="3" class="equip-box" />
        <text x="1042" y="57" class="equip-title">242 座换热站总群</text>
        <text x="1042" y="73" class="equip-sub">在线 {{ kpis.online_stations ?? 0 }} 站 · 热指标 {{ fmt(kpis.heat_index_wm2, ' W/㎡', 1) }}</text>
        <text x="1042" y="95" class="tag-val-sm">总供热 {{ fmt(kpis.hour_heat_gj, ' GJ', 1) }}</text>
        <text x="1042" y="114" class="equip-sub">补水 {{ fmt(kpis.hour_water_t, ' t', 1) }} ｜ 电耗 {{ fmt(kpis.hour_elec_kwh, ' kWh', 0) }}</text>
      </g>

      <!-- 2. 464 商业用户 -->
      <g class="svg-clickable" @click="$emit('open-merchants')">
        <rect x="1030" y="140" width="234" height="84" rx="3" class="equip-box" />
        <text x="1042" y="159" class="equip-title">464 户商业用户直供网</text>
        <text x="1042" y="176" class="equip-sub">在线 {{ merchantSummary.online_merchants ?? 0 }} 户 · 用热 {{ merchantSummary.active_heat_merchants ?? 0 }} 户</text>
        <text x="1042" y="200" class="tag-val-sm">小时耗热 {{ fmt(merchantSummary.total_hour_heat_gj, ' GJ', 1) }}</text>
        <text x="1175" y="200" class="equip-sub">流量 {{ fmt(merchantSummary.total_hour_flow_t, ' t', 0) }}</text>
      </g>

      <!-- 3. 居民建筑楼宇 + 液柱温度计 -->
      <g>
        <rect x="1030" y="236" width="234" height="98" rx="3" class="equip-box" />
        <!-- 建筑矢量剪影 -->
        <rect x="1042" y="264" width="22" height="54" fill="#b6c2cf" stroke="#475569" />
        <rect x="1066" y="254" width="24" height="64" fill="#a8b6c6" stroke="#475569" />
        <rect x="1047" y="272" width="5" height="6" fill="#fef08a" />
        <rect x="1055" y="272" width="5" height="6" fill="#fef08a" />
        <rect x="1072" y="264" width="5" height="6" fill="#fef08a" />
        <rect x="1080" y="264" width="5" height="6" fill="#fef08a" />
        <rect x="1072" y="280" width="5" height="6" fill="#fef08a" />

        <text x="1100" y="255" class="equip-title">居民采暖末梢</text>
        <text x="1100" y="271" class="equip-sub">有效样本 {{ tempSummary.valid_devices ?? 0 }} 户</text>
        <text x="1100" y="294" class="tag-val">{{ fmt(kpis.avg_room_temp, '℃', 2) }}</text>
        <text x="1100" y="313" class="equip-sub">达标 {{ fmt(kpis.temp_pass_rate_pct, '%', 1) }} ｜ 室外 {{ fmt(kpis.outdoor_temp, '℃', 1) }}</text>

        <!-- 温度计液柱指示 -->
        <rect x="1238" y="250" width="12" height="68" rx="6" fill="#cbd5e1" stroke="#64748b" />
        <rect
          x="1240"
          :y="316 - tempHeight(kpis.avg_room_temp)"
          width="8"
          :height="tempHeight(kpis.avg_room_temp)"
          rx="4"
          :fill="(kpis.avg_room_temp ?? 20) < 18 ? '#dc2626' : '#3b6b8f'"
        />
        <!-- 18℃ 红线刻度 -->
        <line x1="1234" y1="292" x2="1254" y2="292" stroke="#dc2626" stroke-width="1.5" />
      </g>
    </svg>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  plantNodes: { type: Array, default: () => [] },
  hubNodes: { type: Array, default: () => [] },
  rdfzBlocks: { type: Array, default: () => [] },
  kpis: { type: Object, default: () => ({}) },
  merchantSummary: { type: Object, default: () => ({}) },
  tempSummary: { type: Object, default: () => ({}) },
  selectedRdfz: { type: String, default: '' },
})

defineEmits(['select-plant', 'select-hub', 'toggle-rdfz', 'open-merchants'])

function fmt(val, suffix = '', fixed = 2) {
  if (val === null || val === undefined || val === '') return '--'
  const num = Number(val)
  if (!Number.isFinite(num)) return '--'
  return `${num.toFixed(fixed).replace(/\.00$/, '')}${suffix}`
}

function barWidth(val, maxVal, widthPx) {
  const n = Number(val)
  if (!Number.isFinite(n) || n <= 0) return 0
  return Math.min(widthPx, Math.max(2, (n / maxVal) * widthPx))
}

function tempHeight(val) {
  const n = Number(val)
  if (!Number.isFinite(n)) return 0
  const pct = Math.max(0.08, Math.min(1, (n - 10) / 20))
  return Math.round(pct * 64)
}

const plantPositions = computed(() => {
  const yMap = { beihai: 44, xianghai: 244 }
  return props.plantNodes.slice(0, 2).map((p, i) => ({
    key: p.key,
    y: yMap[p.key] ?? (i === 0 ? 44 : 244),
    data: p,
  }))
})

const hubPositions = computed(() => {
  // 严格按物理位置自上而下排布：北海#2首站(上) -> 北海#1/水炉首站(中) -> 香海首站/网口(下)
  const orderKeys = ['b2', 'b1', 'xh']
  const yMap = { b2: 32, b1: 112, xh: 256 }
  const hMap = new Map(props.hubNodes.map((h) => [h.key, h]))
  return orderKeys
    .filter((k) => hMap.has(k))
    .map((k) => ({
      key: k,
      y: yMap[k],
      data: hMap.get(k),
    }))
})

const RDFZ_LAYOUT_ORDER = {
  北海北网: { order: 0, cy: 50, solo: false },
  北海南网: { order: 1, cy: 82, solo: false },
  东环: { order: 2, cy: 118, solo: false },
  南环: { order: 3, cy: 152, solo: false },
  老热泵: { order: 4, cy: 186, solo: true },
  电锅炉: { order: 5, cy: 218, solo: true },
  '香海#1低真空': { order: 6, cy: 262, solo: false },
  '香海#3低真空': { order: 7, cy: 296, solo: false },
  香海蒸汽网: { order: 8, cy: 330, solo: false },
}

const rdfzRows = computed(() => {
  const list = [...props.rdfzBlocks].slice(0, 9).sort((a, b) => {
    const oa = RDFZ_LAYOUT_ORDER[a.group_name]?.order ?? 99
    const ob = RDFZ_LAYOUT_ORDER[b.group_name]?.order ?? 99
    return oa - ob
  })
  return list.map((g, i) => ({
    ...g,
    cy: RDFZ_LAYOUT_ORDER[g.group_name]?.cy ?? (50 + i * 34),
    solo: Boolean(RDFZ_LAYOUT_ORDER[g.group_name]?.solo),
  }))
})

const soloNetBadges = computed(() =>
  rdfzRows.value
    .filter((r) => r.solo)
    .map((r) => ({ key: r.group_key || r.group_name, cy: r.cy }))
)
</script>

<style scoped>
.pfd-shell {
  width: 100%;
  min-width: 0;
}

.mobile-pan-hint {
  display: none;
  font-size: 11px;
  color: #475569;
  text-align: center;
  padding: 2px 0 5px;
}

.pfd-wrap {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  background: #dce2ea;
  border: 1px solid #9faab8;
  border-radius: 2px;
}

@media (max-width: 768px) {
  .mobile-pan-hint {
    display: block;
  }
}

.pfd-svg {
  display: block;
  width: 100%;
  min-width: 980px;
  height: auto;
  max-height: 365px;
}

.stage-hdr {
  font-size: 11px;
  font-weight: 700;
  fill: #475569;
  letter-spacing: 0.4px;
}

.mini-lbl {
  font-size: 9.5px;
  font-weight: 700;
  fill: #475569;
}

.pipe-supply {
  fill: none;
  stroke: #6e8094;
  stroke-width: 3;
  stroke-linejoin: round;
}

.pipe-tie {
  fill: none;
  stroke: #64748b;
  stroke-width: 2;
  stroke-dasharray: 5 4;
  stroke-linejoin: round;
}

.zone-divider-lbl {
  font-size: 9.5px;
  font-weight: 700;
  fill: #475569;
}

.tie-lbl {
  font-size: 8.5px;
  font-weight: 700;
  fill: #475569;
}

.net-pipe {
  stroke: #76879b;
  stroke-width: 3.5;
  transition: stroke 0.15s, opacity 0.15s;
}

.net-pipe.active {
  stroke: #2563eb;
  stroke-width: 4.5;
}

.net-pipe.dimmed {
  opacity: 0.35;
}

.net-pipe-flow {
  stroke: #93c5fd;
  stroke-width: 2;
  stroke-dasharray: 8 8;
  animation: dcs-flow 1.1s linear infinite;
}

@keyframes dcs-flow {
  from { stroke-dashoffset: 16; }
  to { stroke-dashoffset: 0; }
}

.svg-clickable {
  cursor: pointer;
}

.equip-box {
  fill: #eef2f6;
  stroke: #8f9ead;
  stroke-width: 1.4;
}

.svg-clickable:hover .equip-box {
  fill: #e2e8f0;
  stroke: #3b6b8f;
}

.sev-box-critical {
  fill: #fef2f2;
  stroke: #dc2626;
}

.sev-box-warning {
  fill: #fffbeb;
  stroke: #d97706;
}

.pipe-tag-plate {
  fill: #eef2f6;
  stroke: #8f9ead;
  stroke-width: 1.1;
}

.svg-clickable:hover .pipe-tag-plate {
  fill: #e2e8f0;
}

.pipe-tag-plate.selected {
  fill: #dbeafe;
  stroke: #1d4ed8;
  stroke-width: 1.8;
}

.pipe-tag-plate.sev-box-critical {
  fill: #fef2f2;
  stroke: #dc2626;
}

.pipe-tag-plate.sev-box-warning {
  fill: #fffbeb;
  stroke: #d97706;
}

.equip-title {
  font-size: 12px;
  font-weight: 700;
  fill: #0f172a;
}

.equip-sub {
  font-size: 10.5px;
  fill: #475569;
}

.tag-lbl {
  font-size: 9.5px;
  fill: #475569;
  font-weight: 600;
}

.tag-val {
  font-family: Consolas, monospace;
  font-size: 13px;
  font-weight: 700;
  fill: #0f172a;
}

.tag-val-sm {
  font-family: Consolas, monospace;
  font-size: 11.5px;
  font-weight: 700;
  fill: #1e3a5f;
}

.net-lbl {
  font-size: 11.5px;
  font-weight: 700;
  fill: #0f172a;
}

.net-mono {
  font-family: Consolas, monospace;
  font-size: 10.5px;
  fill: #334155;
}

.net-mono-bold {
  font-family: Consolas, monospace;
  font-size: 11px;
  font-weight: 700;
  fill: #0f172a;
}

.led-dot.led-normal { fill: #3b6b8f; }
.led-dot.led-warning { fill: #d97706; }
.led-dot.led-critical { fill: #dc2626; }

.mini-rotor-anim {
  animation: pfd-rotor-dash 0.7s linear infinite;
}

@keyframes pfd-rotor-dash {
  from { stroke-dashoffset: 6; }
  to { stroke-dashoffset: 0; }
}

.mini-gen-spin {
  animation: pfd-gen-spin 2.4s linear infinite;
}

@keyframes pfd-gen-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
