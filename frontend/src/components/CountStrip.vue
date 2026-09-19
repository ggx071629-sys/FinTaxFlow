<script setup lang="ts">
defineProps<{ items: { label: string; value: number; tone?: string }[] }>();
</script>
<template>
  <view class="count-strip">
    <view v-for="item in items" :key="item.label">
      <text class="number" :class="item.tone">{{ item.value }}</text>
      <text class="caption">{{ item.label }}</text>
    </view>
  </view>
</template>
