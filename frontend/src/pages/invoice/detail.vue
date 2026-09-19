<script setup lang="ts">
import { ref } from 'vue';
import { onLoad, onShow } from '@dcloudio/uni-app';
import { api } from '../../api';
import { useResource } from '../../composables/resource';
import { go, guard, toast } from '../../utils/navigation';
import { invoiceTypes } from '../../utils/format';
import AppShell from '../../components/AppShell.vue';
import CompanyBar from '../../components/CompanyBar.vue';
import StatePanel from '../../components/StatePanel.vue';
import StatusBadge from '../../components/StatusBadge.vue';
import AmountBreakdown from '../../components/AmountBreakdown.vue';
const id = ref('');
onLoad((q) => {
  id.value = q?.id || '';
});
const { data, busy, error, load } = useResource(() => {
  if (!id.value) throw new Error('缺少票据编号，请从票据列表重新打开');
  return api.invoice(id.value);
});
onShow(() => {
  if (guard()) load();
});
function copy() {
  if (data.value)
    uni.setClipboardData({
      data: data.value.number,
      success: () => toast('票号已复制'),
      fail: () => toast('复制失败，请长按票号复制')
    });
}
</script>
<template>
  <AppShell title="票据详情" fallback="invoices">
    <CompanyBar>
      <template #action>
        <button id="switch-company" class="ft-button text-button" @click="go('company')">
          切换企业 ›
        </button>
      </template>
    </CompanyBar>
    <text class="notice warning">演示票据 · 验真结果为模拟</text>
    <StatePanel :busy="busy" :error="error" @retry="load">
      <template v-if="data">
        <view class="card">
          <view class="row between wrap">
            <text class="section-title">{{ invoiceTypes[data.invoice_type] }}</text>
            <text class="chip">{{ data.direction === 'INPUT' ? '进项' : '销项' }}</text>
          </view>
          <view class="detail-row">
            <text>发票号码</text>
            <text selectable class="number">{{ data.number }}</text>
          </view>
          <button class="ft-button text-button" style="margin-left: auto" @click="copy">
            复制票号
          </button>
          <view class="detail-row">
            <text>开票日期</text>
            <text>{{ data.issued_at.slice(0, 10) }}</text>
          </view>
          <StatusBadge :status="data.verification_status" />
          <text class="caption" style="display: block; margin-top: 8px">
            {{ data.verification_note }}
          </text>
        </view>
        <view class="card">
          <text class="section-title">购销双方</text>
          <view
            v-for="p in [
              { label: '购买方', value: data.buyer },
              { label: '销售方', value: data.seller }
            ]"
            :key="p.label"
            style="margin-bottom: 16px"
          >
            <text class="caption">{{ p.label }}</text>
            <text class="list-title">{{ p.value.name }}</text>
            <text class="caption" selectable>税号 {{ p.value.tax_id }}</text>
          </view>
        </view>
        <view class="card">
          <text class="section-title">开票内容</text>
          <view class="detail-row">
            <text>项目</text>
            <text>{{ data.item_name }}</text>
          </view>
          <view class="detail-row">
            <text>演示税率</text>
            <text>{{ Number(data.tax_rate) * 100 }}%</text>
          </view>
          <AmountBreakdown v-bind="data" />
        </view>
        <button
          v-if="data.pdf_available"
          class="ft-button primary"
          @click="go('preview', { id: data.id })"
        >
          查看发票 PDF
        </button>
        <text v-else class="notice">文件暂不可用，请稍后刷新票据详情。</text>
        <button
          v-if="data.source_task_id"
          class="ft-button secondary"
          style="margin-top: 12px"
          @click="go('result', { id: data.source_task_id! })"
        >
          查看开票申请
        </button>
      </template>
    </StatePanel>
  </AppShell>
</template>
