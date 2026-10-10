<script setup>
// 应用根组件：渲染当前路由页面与全局系统级联合会审通知弹窗
import DailyReviewNoticeModal from './projects/insulation_pipe_supply_2026/components/DailyReviewNoticeModal.vue'
</script>

<template>
  <router-view />
  <!-- 全局多方联合会审前序责任主体强提醒弹窗（全系统各页面常驻） -->
  <DailyReviewNoticeModal />
</template>

<style scoped>
/* 可按需添加全局布局样式 */
</style>

