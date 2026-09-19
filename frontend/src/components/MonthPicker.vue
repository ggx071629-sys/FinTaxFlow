<script setup lang="ts">
import { ref } from 'vue';
import ModalSheet from './ModalSheet.vue';
defineProps<{ period: string; periods: string[] }>();
defineEmits<{ change: [value: string] }>();
const open = ref(false);
</script>
<template>
  <button class="ft-button secondary row between" style="margin-bottom: 16px" @click="open = true">
    <text>查询月份</text>
    <text>{{ period || '选择月份' }} ▾</text>
  </button>
  <ModalSheet :open="open" title="选择查询月份" @close="open = false">
    <text class="caption">仅改变当前页面的查询月份</text>
    <button
      v-for="month in periods"
      :key="month"
      class="ft-button menu-row"
      @click="
        $emit('change', month);
        open = false;
      "
    >
      <text>{{ month }}</text>
      <text v-if="month === period">✓</text>
    </button>
    <text v-if="!periods.length" class="notice">暂无可选样例期间</text>
  </ModalSheet>
</template>
