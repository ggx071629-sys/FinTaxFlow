<script lang="ts">
export default {
  options: { virtualHost: true, styleIsolation: 'shared' }
};
</script>
<script setup lang="ts">
import { session } from '../stores/session';
import { go } from '../utils/navigation';
defineProps<{ hero?: boolean; period?: string }>();
</script>
<template>
  <view :class="['company-bar', { 'executive-card': hero }]">
    <view class="row between">
      <text class="eyebrow">
        {{ hero ? session.company?.service_status || '企业专属财税服务' : '当前企业' }}
      </text>
      <slot name="action">
        <button id="switch-company" class="ft-button text-button" @click="go('company')">
          切换企业 ›
        </button>
      </slot>
    </view>
    <text class="company-name">{{ session.company?.name || '请先选择企业' }}</text>
    <view class="row between wrap company-meta">
      <text class="caption">{{ session.company?.tax_id }}</text>
      <text class="caption company-period">{{ period || '演示环境' }}</text>
    </view>
  </view>
</template>
