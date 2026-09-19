<script setup lang="ts">
import AppShell from '../../components/AppShell.vue';
</script>
<template>
  <AppShell title="关于系统" fallback="mine">
    <view class="login-brand">
      <image class="brand-logo" src="/static/fintax_logo.jpg" />
      <text class="brand-name">财税云</text>
      <text class="caption">FinTaxFlow · Demo v0.1.0</text>
    </view>
    <view class="card">
      <text class="section-title">让财税服务进度清晰可见</text>
      <text class="muted">
        面向企业老板的财税服务工作台，集中查看票据处理、报税进度、开票任务与独立账务摘要。
      </text>
    </view>
    <view class="card">
      <text class="section-title">演示能力边界</text>
      <view class="detail-row">
        <text>账号与记录</text>
        <text>通过服务端认证与保存</text>
      </view>
      <view class="detail-row">
        <text>财税处理</text>
        <text>开票、验真、报税结果均为模拟</text>
      </view>
      <view class="detail-row">
        <text>账务摘要</text>
        <text>独立预置，不自动记账</text>
      </view>
      <view class="detail-row">
        <text>邮件服务</text>
        <text>只保存邮箱，不发送邮件</text>
      </view>
    </view>
    <text class="notice warning">
      演示文件，非真实发票。这里的税种、税率、金额和处理节点不构成实际财税办理依据。
    </text>
  </AppShell>
</template>
