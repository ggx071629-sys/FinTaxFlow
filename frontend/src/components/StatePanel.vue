<script lang="ts">
export default {
  options: { virtualHost: true, styleIsolation: 'shared' }
};
</script>
<script setup lang="ts">
defineProps<{ busy?: boolean; error?: string; empty?: boolean; emptyText?: string }>();
defineEmits<{ retry: [] }>();
</script>
<template>
  <view v-if="busy" class="state-panel" role="status">
    <view class="skeleton" />
    <view class="skeleton short" />
    <text class="caption">正在加载…</text>
  </view>
  <view v-else-if="error" class="state-panel error-panel" role="alert">
    <text class="state-symbol">!</text>
    <text>{{ error }}</text>
    <button class="ft-button secondary" @click="$emit('retry')">重试</button>
  </view>
  <view v-else-if="empty" class="state-panel">
    <text class="state-symbol neutral">—</text>
    <text>{{ emptyText || '暂无记录' }}</text>
  </view>
  <slot v-else />
</template>
