<script setup lang="ts">
import { money } from '../utils/format';
defineProps<{ net_amount: string; tax_amount: string; total_amount: string }>();
</script>
<template>
  <view class="amount-breakdown">
    <view class="detail-row">
      <text>不含税金额</text>
      <text class="number">¥ {{ money(net_amount) }}</text>
    </view>
    <view class="detail-row">
      <text>税额</text>
      <text class="number">¥ {{ money(tax_amount) }}</text>
    </view>
    <view class="detail-row total">
      <text>价税合计</text>
      <text class="number">¥ {{ money(total_amount) }}</text>
    </view>
  </view>
</template>
