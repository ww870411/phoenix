<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    :width="computedSize"
    :height="computedSize"
    viewBox="0 0 36 36"
    class="scale-balance-icon"
    role="img"
    aria-label="⚖️ 联合会审天平"
  >
    <defs>
      <!-- 金属主横梁与支柱金黄高光渐变 -->
      <linearGradient id="scale-gold-grad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#FCD34D" />
        <stop offset="40%" stop-color="#F59E0B" />
        <stop offset="100%" stop-color="#D97706" />
      </linearGradient>

      <!-- 底座沉稳渐变 -->
      <linearGradient id="scale-base-grad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#FBBF24" />
        <stop offset="60%" stop-color="#D97706" />
        <stop offset="100%" stop-color="#B45309" />
      </linearGradient>

      <!-- 托盘内部立体阴影渐变 -->
      <linearGradient id="scale-pan-grad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#FDE68A" />
        <stop offset="30%" stop-color="#F59E0B" />
        <stop offset="100%" stop-color="#B45309" />
      </linearGradient>

      <!-- 悬吊冷钢链渐变 -->
      <linearGradient id="scale-cable-grad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#94A3B8" />
        <stop offset="100%" stop-color="#64748B" />
      </linearGradient>
    </defs>

    <!-- 1. 左侧秤盘悬吊索 (2条) -->
    <path
      fill="url(#scale-cable-grad)"
      d="M3.923 22.923c-.212.511-.798.751-1.308.539-.51-.213-.751-.798-.539-1.308L6.693 9.616c.212-.51.798-.751 1.307-.539.51.213.751.798.539 1.308L3.923 22.923z"
    />
    <path
      fill="url(#scale-cable-grad)"
      d="M13.923 22.154c.212.51-.029 1.095-.539 1.308-.51.212-1.095-.028-1.308-.539L7.461 10.385c-.212-.51.029-1.095.539-1.308.51-.212 1.095.029 1.308.539l4.615 12.538z"
    />

    <!-- 2. 右侧秤盘悬吊索 (2条) -->
    <path
      fill="url(#scale-cable-grad)"
      d="M23.924 22.923c-.213.511-.799.751-1.309.539-.51-.213-.75-.798-.538-1.308l4.616-12.539c.212-.509.797-.75 1.307-.538.51.213.752.798.539 1.308l-4.615 12.538z"
    />
    <path
      fill="url(#scale-cable-grad)"
      d="M33.923 22.154c.212.51-.028 1.095-.538 1.308-.51.212-1.096-.028-1.309-.539l-4.615-12.538c-.213-.51.029-1.095.539-1.308.51-.212 1.095.029 1.307.539l4.616 12.538z"
    />

    <!-- 3. 左托盘与右托盘 (立体微弧厚度造型) -->
    <path
      fill="url(#scale-pan-grad)"
      d="M14.857 22H1.143C.512 22 0 22.511 0 23.143c0 2.524 3.582 4.571 8 4.571s8-2.047 8-4.571c0-.632-.512-1.143-1.143-1.143z"
    />
    <path
      fill="url(#scale-pan-grad)"
      d="M34.857 22H21.143c-.632 0-1.143.511-1.143 1.143 0 2.524 3.581 4.571 8 4.571s8-2.047 8-4.571c0-.632-.511-1.143-1.143-1.143z"
    />

    <!-- 4. 托盘边缘反光弧线 (精致高光) -->
    <path fill="#FEF3C7" opacity="0.55" d="M1.3 22.8C2.5 24.6 5 25.6 8 25.6s5.5-1 6.7-2.8H1.3z" />
    <path fill="#FEF3C7" opacity="0.55" d="M21.3 22.8c1.2 1.8 3.7 2.8 6.7 2.8s5.5-1 6.7-2.8H21.3z" />

    <!-- 5. 稳重阶梯台基底座 -->
    <path
      fill="url(#scale-base-grad)"
      d="M24 34H12c-.552 0-1-.447-1-1 0-2.209 3.134-4 7-4s7 1.791 7 4c0 .553-.447 1-1 1z"
    />
    <ellipse cx="18" cy="30" rx="3.5" ry="1.1" fill="#FDE68A" opacity="0.65" />

    <!-- 6. 中心垂直主立杆支柱 -->
    <path
      fill="url(#scale-gold-grad)"
      d="M19 3c0-.552-.447-1-1-1-.552 0-1 .448-1 1v27c0 .553.448 1 1 1 .553 0 1-.447 1-1V3z"
    />

    <!-- 7. 中轴顶部圆环与左右平衡支点 -->
    <circle fill="url(#scale-gold-grad)" cx="18" cy="4" r="2.2" />
    <circle fill="#FEF3C7" cx="17.4" cy="3.5" r="0.65" opacity="0.9" />
    <circle fill="url(#scale-gold-grad)" cx="8" cy="10" r="2" />
    <circle fill="url(#scale-gold-grad)" cx="28" cy="10" r="2" />

    <!-- 8. 主对称横梁 -->
    <path
      fill="url(#scale-gold-grad)"
      d="M28 10c0 1.104 0 0-10 0S8 11.104 8 10s3-4 10-4 10 2.896 10 4z"
    />
    <ellipse cx="18" cy="8.2" rx="2.4" ry="1.1" fill="#FEF3C7" opacity="0.75" />
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  size: {
    type: [Number, String],
    default: 20,
  },
})

const computedSize = computed(() => {
  if (typeof props.size === 'number') return `${props.size}px`
  return props.size || '20px'
})
</script>

<style scoped>
.scale-balance-icon {
  display: inline-block;
  vertical-align: -0.15em;
  flex-shrink: 0;
  line-height: 1;
}
</style>
