<script setup lang="ts">
import type { TimelineEvent } from '../types/api';
import { dateTime, statusLabels } from '../utils/format';
defineProps<{ events: TimelineEvent[] }>();
</script>
<template>
  <view class="timeline">
    <view v-for="(event, index) in events" :key="index" class="timeline-node">
      <text class="timeline-title">
        {{ event.label }} · {{ statusLabels[event.status] || event.status }}
      </text>
      <text class="caption">{{ dateTime(event.time) }}</text>
      <text v-if="event.note" class="caption">{{ event.note }}</text>
    </view>
    <text v-if="!events.length" class="caption">暂无处理节点</text>
  </view>
</template>
