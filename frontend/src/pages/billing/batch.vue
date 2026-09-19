<script setup lang="ts">
import { ref, watch } from 'vue';
import { onLoad, onShow } from '@dcloudio/uni-app';
import { extension } from '../../api/extension';
import { useResource } from '../../composables/resource';
import { usePaged } from '../../composables/paged';
import { useCommand } from '../../composables/command';
import { go, guard } from '../../utils/navigation';
import { money, invoiceTypes } from '../../utils/format';
import { session } from '../../stores/session';
import type { BatchRow, PageResult } from '../../types/api';
import AppShell from '../../components/AppShell.vue';
import CompanyBar from '../../components/CompanyBar.vue';
import StatePanel from '../../components/StatePanel.vue';
import StatusBadge from '../../components/StatusBadge.vue';
import CountStrip from '../../components/CountStrip.vue';
import ModalSheet from '../../components/ModalSheet.vue';
const id = ref(''),
  status = ref(''),
  confirm = ref(false);
onLoad((q) => {
  id.value = q?.id || '';
});
const { data, busy, error, load } = useResource(() => extension.batch(id.value));
const rows = usePaged<BatchRow, PageResult<BatchRow>>((page) =>
  extension.batchRows(id.value, status.value, page)
);
const command = useCommand('retry-batch');
watch(
  () => session.epoch,
  () => {
    confirm.value = false;
    status.value = '';
  }
);
onShow(() => {
  if (guard()) refresh();
});
function refresh() {
  load();
  rows.load();
}
function filter(value: string) {
  status.value = value;
  rows.load();
}
async function retry() {
  if (!data.value?.failed) return;
  const result = await command.run({ id: id.value }, (key) => extension.retryBatch(id.value, key));
  if (result) {
    confirm.value = false;
    refresh();
  }
}
</script>
<template>
  <AppShell title="批次详情" fallback="billing">
    <view class="extension-page">
      <CompanyBar />
      <StatePanel :busy="busy" :error="error" @retry="refresh">
        <template v-if="data">
          <view class="executive-card">
            <view class="row between wrap">
              <text class="caption">{{ data.number }}</text>
              <StatusBadge :status="data.status" />
            </view>
            <text class="company-name">{{ data.name }}</text>
            <text class="number" style="font-size: 28px; font-weight: 700">
              ¥ {{ money(data.total_amount) }}
            </text>
            <text class="caption" style="display: block">{{ data.total }} 笔申请 · 价税合计</text>
            <view class="progress-track">
              <view
                :style="{
                  width: `${data.total ? ((data.success + data.failed) / data.total) * 100 : 0}%`
                }"
              />
            </view>
            <text class="caption">
              {{ data.success + data.failed }} / {{ data.total }} 笔已结束 · 可以离开，稍后查看结果
            </text>
          </view>
          <view class="card">
            <CountStrip
              :items="[
                { label: '成功', value: data.success, tone: 'good' },
                { label: '失败', value: data.failed, tone: 'bad' },
                { label: '处理中', value: data.processing }
              ]"
            />
          </view>
          <view class="segments">
            <button
              v-for="item in [
                { v: '', t: '全部' },
                { v: 'SUCCESS', t: '成功' },
                { v: 'FAILED', t: '失败' }
              ]"
              :key="item.v"
              class="ft-button"
              :class="{ selected: status === item.v }"
              @click="filter(item.v)"
            >
              {{ item.t }}
            </button>
          </view>
          <text v-if="data.failed" class="notice warning">
            仅重试失败的 {{ data.failed }} 笔，成功申请不会重复开票。原失败记录将保留。
          </text>
          <StatePanel
            :busy="rows.busy.value && !rows.items.value.length"
            :error="rows.error.value"
            :empty="!rows.busy.value && !rows.items.value.length"
            empty-text="没有符合筛选条件的申请"
            @retry="rows.load()"
          >
            <view v-for="row in rows.items.value" :key="row.id" class="card">
              <view class="row between wrap">
                <text class="caption">
                  源记录 {{ row.business_number }} · 第 {{ row.row_number }} 行
                </text>
                <StatusBadge :status="row.status" />
              </view>
              <text class="list-title">{{ row.buyer_name }}</text>
              <view class="row between wrap">
                <text class="caption">{{ invoiceTypes[row.invoice_type] }}</text>
                <text class="number">¥ {{ money(row.total_amount) }}</text>
              </view>
              <text v-if="row.failure_reason" class="error-text">{{ row.failure_reason }}</text>
              <button
                class="ft-button text-button"
                @click="go('result', { id: row.billing_task_id })"
              >
                查看开票申请
              </button>
              <button
                v-if="row.invoice_id"
                class="ft-button text-button"
                @click="go('invoice', { id: row.invoice_id })"
              >
                查看票据与 PDF
              </button>
              <view v-if="row.attempt_task_ids.length > 1">
                <text class="caption">关联重提 · 原尝试保留</text>
                <button
                  v-for="attempt in row.attempt_task_ids"
                  :key="attempt"
                  class="ft-button text-button"
                  @click="go('result', { id: attempt })"
                >
                  查看尝试 {{ attempt }}
                </button>
              </view>
            </view>
          </StatePanel>
          <button
            v-if="rows.meta.value && rows.items.value.length < rows.meta.value.total"
            class="ft-button secondary"
            :disabled="rows.busy.value"
            @click="rows.load(false)"
          >
            加载更多
          </button>
          <button class="ft-button text-button" @click="go('task', { id: data.task_id })">
            查看执行记录
          </button>
          <text v-if="command.error.value" class="notice error" role="alert">
            {{ command.error.value }}
          </text>
          <view class="extension-actions button-row">
            <button
              class="ft-button secondary"
              :disabled="busy || command.busy.value"
              @click="refresh"
            >
              刷新状态
            </button>
            <button
              v-if="data.failed"
              class="ft-button primary"
              :disabled="command.busy.value || data.processing > 0"
              @click="confirm = true"
            >
              仅重试 {{ data.failed }} 笔失败申请
            </button>
          </view>
        </template>
      </StatePanel>
      <ModalSheet
        :open="confirm"
        title="确认重试失败申请"
        :busy="command.busy.value"
        @close="confirm = false"
      >
        <text class="notice">仅重试当前批次失败行，沿用原业务单号与来源关联。成功行不会重开。</text>
        <text v-if="command.error.value" class="notice error">{{ command.error.value }}</text>
        <view class="button-row">
          <button
            class="ft-button secondary"
            :disabled="command.busy.value"
            @click="confirm = false"
          >
            取消
          </button>
          <button class="ft-button primary" :disabled="command.busy.value" @click="retry">
            确认重试
          </button>
        </view>
      </ModalSheet>
    </view>
  </AppShell>
</template>
