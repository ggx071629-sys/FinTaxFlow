<script setup lang="ts">
import { ref } from 'vue';
import { onLoad, onShow } from '@dcloudio/uni-app';
import { api } from '../../api';
import { useResource } from '../../composables/resource';
import { go, guard } from '../../utils/navigation';
import { invoiceTypes, dateTime } from '../../utils/format';
import AppShell from '../../components/AppShell.vue';
import CompanyBar from '../../components/CompanyBar.vue';
import StatePanel from '../../components/StatePanel.vue';
import AmountBreakdown from '../../components/AmountBreakdown.vue';
import Timeline from '../../components/Timeline.vue';
const id = ref('');
onLoad((q) => (id.value = q?.id || ''));
const { data, busy, error, load } = useResource(() => {
  if (!id.value) throw new Error('缺少申请编号，请从开票记录重新打开');
  return api.task(id.value);
});
onShow(() => {
  if (guard()) load();
});
const titles = {
  PENDING: '申请已受理',
  PROCESSING: '模拟开票处理中',
  SUCCESS: '模拟开票成功',
  FAILED: '模拟开票失败'
};
</script>
<template>
  <AppShell title="开票申请详情" fallback="billing">
    <CompanyBar>
      <template #action>
        <button id="switch-company" class="ft-button text-button" @click="go('company')">
          切换企业 ›
        </button>
      </template>
    </CompanyBar>
    <StatePanel :busy="busy" :error="error" @retry="load">
      <template v-if="data">
        <view :class="['card', 'result-banner', data.status.toLowerCase()]">
          <view class="result-icon">
            {{ data.status === 'SUCCESS' ? '✓' : data.status === 'FAILED' ? '!' : '◷' }}
          </view>
          <text class="result-title">{{ titles[data.status] }}</text>
          <text class="caption">{{ data.number }}</text>
          <text v-if="data.status === 'FAILED'" class="notice error" style="margin-top: 16px">
            演示场景：{{ data.failure_reason || '开票处理失败，请核对资料后重新提交' }}
          </text>
          <text
            v-if="['PENDING', 'PROCESSING'].includes(data.status)"
            class="notice"
            style="margin-top: 16px"
          >
            离开页面后仍可从开票记录查询。点击刷新获取最新状态。
          </text>
          <template v-if="data.status === 'SUCCESS'">
            <text class="list-title">票号 {{ data.invoice_number }}</text>
            <text class="caption">完成时间 {{ dateTime(data.completed_at) }}</text>
          </template>
        </view>
        <view class="stack" style="margin-bottom: 20px">
          <template v-if="data.status === 'SUCCESS' && data.invoice_id">
            <button class="ft-button primary" @click="go('preview', { id: data.invoice_id! })">
              查看发票 PDF
            </button>
            <button class="ft-button secondary" @click="go('invoice', { id: data.invoice_id! })">
              查看票据详情
            </button>
          </template>
          <button
            v-else-if="data.status === 'FAILED' && data.batch_id"
            class="ft-button primary"
            @click="go('batch', { id: data.batch_id })"
          >
            返回批次重试失败项
          </button>
          <button
            v-else-if="data.status === 'FAILED'"
            class="ft-button primary"
            @click="go('create', { source_task_id: data.id })"
          >
            修改后重新提交
          </button>
          <button v-else class="ft-button primary" :disabled="busy" @click="load">刷新状态</button>
          <button class="ft-button secondary" @click="go('billing')">返回开票记录</button>
        </view>
        <view class="card">
          <text class="section-title">申请资料</text>
          <view class="detail-row">
            <text>销售方</text>
            <text>{{ data.seller.name }}</text>
          </view>
          <view class="detail-row">
            <text>购买方</text>
            <text>{{ data.input.buyer_name }}</text>
          </view>
          <view class="detail-row">
            <text>购买方税号</text>
            <text>{{ data.input.buyer_tax_id }}</text>
          </view>
          <view class="detail-row">
            <text>票种</text>
            <text>{{ invoiceTypes[data.input.invoice_type] }}</text>
          </view>
          <view class="detail-row">
            <text>项目</text>
            <text>{{ data.input.item_name }}</text>
          </view>
          <view class="detail-row">
            <text>演示税率</text>
            <text>{{ Number(data.tax_rate) * 100 }}%</text>
          </view>
          <AmountBreakdown v-bind="data" />
          <view class="detail-row">
            <text>申请时间</text>
            <text>{{ dateTime(data.created_at) }}</text>
          </view>
          <view class="detail-row">
            <text>邮箱（不发送邮件）</text>
            <text>{{ data.input.email || '未填写' }}</text>
          </view>
          <view class="detail-row">
            <text>备注</text>
            <text>{{ data.input.remark || '未填写' }}</text>
          </view>
        </view>
        <view class="card">
          <text class="section-title">处理时间线</text>
          <Timeline :events="data.events" />
        </view>
        <view v-if="data.source_task_id || data.followup_task_ids.length" class="card">
          <text class="section-title">关联申请</text>
          <button
            v-if="data.source_task_id"
            class="ft-button menu-row"
            @click="go('result', { id: data.source_task_id! })"
          >
            <text>查看原申请</text>
            <text>›</text>
          </button>
          <button
            v-for="(related, index) in data.followup_task_ids"
            :key="related"
            class="ft-button menu-row"
            @click="go('result', { id: related })"
          >
            <text>查看后续申请 {{ index + 1 }}</text>
            <text>›</text>
          </button>
        </view>
      </template>
    </StatePanel>
  </AppShell>
</template>
