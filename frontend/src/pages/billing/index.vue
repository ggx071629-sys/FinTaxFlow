<script setup lang="ts">
import { ref } from 'vue';
import { onShow, onPullDownRefresh, onReachBottom } from '@dcloudio/uni-app';
import { api } from '../../api';
import { extension } from '../../api/extension';
import CountStrip from '../../components/CountStrip.vue';
import { usePaged } from '../../composables/paged';
import { go, guard } from '../../utils/navigation';
import { money, invoiceTypes, dateTime } from '../../utils/format';
import type { BillingTask, Batch, PageResult } from '../../types/api';
import AppShell from '../../components/AppShell.vue';
import CompanyBar from '../../components/CompanyBar.vue';
import StatePanel from '../../components/StatePanel.vue';
import StatusBadge from '../../components/StatusBadge.vue';
const status = ref('');
const mode = ref('single');
const batches = usePaged<Batch, PageResult<Batch>>((page) => extension.batches(page));
function refresh() {
  if (mode.value === 'single') load();
  else batches.load();
}
function switchMode(value: string) {
  mode.value = value;
  refresh();
}
const { items, meta, busy, error, load } = usePaged<BillingTask, PageResult<BillingTask>>((page) =>
  api.billing(status.value, page)
);
onShow(() => {
  if (guard()) refresh();
});
onPullDownRefresh(() => refresh());
onReachBottom(() => (mode.value === 'single' ? load(false) : batches.load(false)));
function filter(value: string) {
  status.value = value;
  load();
}
</script>
<template>
  <AppShell title="开票记录">
    <CompanyBar>
      <template #action>
        <button id="switch-company" class="ft-button text-button" @click="go('company')">
          切换企业 ›
        </button>
      </template>
    </CompanyBar>
    <text class="notice">申请记录持续保存，离开页面后可在这里继续查看处理结果。</text>
    <view class="segments">
      <button
        class="ft-button"
        :class="{ selected: mode === 'single' }"
        @click="switchMode('single')"
      >
        单笔
      </button>
      <button
        class="ft-button"
        :class="{ selected: mode === 'batch' }"
        @click="switchMode('batch')"
      >
        批量
      </button>
    </view>
    <template v-if="mode === 'single'">
      <view class="segments">
        <button
          class="ft-button"
          v-for="item in [
            { v: '', t: '全部' },
            { v: 'PENDING', t: '待处理' },
            { v: 'PROCESSING', t: '处理中' },
            { v: 'SUCCESS', t: '成功' },
            { v: 'FAILED', t: '失败' }
          ]"
          :key="item.v"
          :class="{ selected: status === item.v }"
          @click="filter(item.v)"
        >
          {{ item.t }}
        </button>
      </view>
      <StatePanel
        :busy="busy && !items.length"
        :error="!items.length ? error : ''"
        :empty="!busy && !error && !items.length"
        :empty-text="status ? '没有该状态的申请' : '暂无开票申请，点击下方按钮新建'"
        @retry="load()"
      >
        <view v-for="task in items" :key="task.id" class="card">
          <button
            class="ft-button"
            style="width: 100%; text-align: left; padding: 0"
            @click="go('result', { id: task.id })"
          >
            <view class="row between wrap">
              <text class="caption">{{ task.number }}</text>
              <StatusBadge :status="task.status" />
            </view>
            <text class="list-title">{{ task.input.buyer_name }}</text>
            <view class="row between wrap">
              <text class="caption">{{ invoiceTypes[task.input.invoice_type] }}</text>
              <text class="number" style="font-size: 22px; font-weight: 700">
                ¥ {{ money(task.total_amount) }}
              </text>
            </view>
            <text class="caption">{{ dateTime(task.created_at) }}</text>
            <text v-if="task.source_task_id" class="chip" style="margin-left: 8px">关联重提</text>
            <text v-if="task.status === 'FAILED'" class="error-text">
              模拟失败：{{ task.failure_reason }}
            </text>
          </button>
          <button
            v-if="task.status === 'FAILED'"
            class="ft-button text-button"
            @click="go('create', { source_task_id: task.id })"
          >
            修改后重新提交 ›
          </button>
        </view>
      </StatePanel>
      <StatePanel v-if="error && items.length" :error="error" @retry="load(false)" />
      <button
        v-if="meta && items.length < meta.total"
        class="ft-button secondary"
        :disabled="busy"
        @click="load(false)"
      >
        {{ busy ? '加载中…' : '加载更多' }}
      </button>
      <text v-else-if="items.length" class="empty-foot">已加载全部 {{ meta?.total }} 条申请</text>
    </template>
    <template v-else>
      <StatePanel
        :busy="batches.busy.value && !batches.items.value.length"
        :error="batches.error.value"
        :empty="!batches.busy.value && !batches.items.value.length"
        empty-text="暂无批量开票记录，导入固定格式的清单开始第一批开票"
        @retry="batches.load()"
      >
        <button
          v-for="batch in batches.items.value"
          :key="batch.id"
          class="ft-button list-card"
          @click="go('batch', { id: batch.id })"
        >
          <view class="row between wrap">
            <text class="caption">{{ batch.number }}</text>
            <StatusBadge :status="batch.status" />
          </view>
          <text class="list-title">{{ batch.name }}</text>
          <view class="row between wrap">
            <text class="caption">{{ batch.total }} 笔开票申请</text>
            <text class="number">¥ {{ money(batch.total_amount) }}</text>
          </view>
          <CountStrip
            :items="[
              { label: '成功', value: batch.success, tone: 'good' },
              { label: '失败', value: batch.failed, tone: 'bad' },
              { label: '处理中', value: batch.processing }
            ]"
          />
          <text class="caption">{{ dateTime(batch.created_at) }} · 查看批次明细</text>
        </button>
      </StatePanel>
      <button
        v-if="batches.meta.value && batches.items.value.length < batches.meta.value.total"
        class="ft-button secondary"
        :disabled="batches.busy.value"
        @click="batches.load(false)"
      >
        加载更多
      </button>
    </template>
    <view class="sticky-actions">
      <button v-if="mode === 'single'" class="ft-button primary" @click="go('create')">
        ＋ 新建开票申请
      </button>
      <button v-else class="ft-button primary" @click="go('billingImport')">导入开票清单</button>
    </view>
  </AppShell>
</template>
