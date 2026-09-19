<script setup lang="ts">
import { ref } from 'vue';
import { onLoad, onShow } from '@dcloudio/uni-app';
import { extension } from '../../api/extension';
import { useResource } from '../../composables/resource';
import { usePaged } from '../../composables/paged';
import { go, guard } from '../../utils/navigation';
import { money } from '../../utils/format';
import type { ReconciliationRow, PageResult } from '../../types/api';
import AppShell from '../../components/AppShell.vue';
import CompanyBar from '../../components/CompanyBar.vue';
import StatePanel from '../../components/StatePanel.vue';
import StatusBadge from '../../components/StatusBadge.vue';
import CountStrip from '../../components/CountStrip.vue';
const id = ref(''),
  only = ref(false);
onLoad((q) => {
  id.value = q?.id || '';
});
const { data, busy, error, load } = useResource(() => extension.reconciliation(id.value));
const rows = usePaged<ReconciliationRow, PageResult<ReconciliationRow>>((page) =>
  extension.reconciliationRows(id.value, only.value, page)
);
onShow(() => {
  if (guard()) {
    load();
    rows.load();
  }
});
function filter(value: boolean) {
  only.value = value;
  rows.load();
}
</script>
<template>
  <AppShell title="对账结果" fallback="accounting">
    <view class="extension-page">
      <CompanyBar />
      <StatePanel :busy="busy" :error="error" @retry="load">
        <template v-if="data">
          <view class="executive-card">
            <view class="row between wrap">
              <text class="caption">{{ data.number }}</text>
              <StatusBadge :status="data.status" />
            </view>
            <text class="company-name">
              {{
                data.status !== 'SUCCESS'
                  ? '对账处理中'
                  : data.different + data.missing
                    ? `发现 ${data.different + data.missing} 组记录差异`
                    : '本次记录全部一致'
              }}
            </text>
            <text class="caption">
              {{ data.period }} · {{ data.bank_count }} 条银行流水 /
              {{ data.ledger_count }} 条收付款记录
            </text>
            <text class="caption" style="display: block; margin-top: 16px">
              仅核对记录，不影响账务摘要
            </text>
          </view>
          <view class="card">
            <CountStrip
              :items="[
                { label: '一致', value: data.matched, tone: 'good' },
                { label: '金额 / 方向差异', value: data.different, tone: 'bad' },
                { label: '记录缺失', value: data.missing, tone: 'warn' }
              ]"
            />
            <text class="caption">共 {{ data.total }} 组结果 · 每组对应一笔业务单号</text>
          </view>
          <view class="segments">
            <button class="ft-button" :class="{ selected: !only }" @click="filter(false)">
              全部
            </button>
            <button class="ft-button" :class="{ selected: only }" @click="filter(true)">
              仅差异
            </button>
          </view>
          <StatePanel
            :busy="rows.busy.value && !rows.items.value.length"
            :error="rows.error.value"
            :empty="!rows.busy.value && !rows.items.value.length"
            :empty-text="only ? '没有差异记录' : '结果尚未就绪，请刷新任务'"
            @retry="rows.load()"
          >
            <view v-for="row in rows.items.value" :key="row.business_number" class="card">
              <view class="row between wrap">
                <text class="caption">{{ row.business_number }}</text>
                <StatusBadge :status="row.status" />
              </view>
              <text class="list-title">
                {{ row.bank?.counterparty || row.ledger?.counterparty }}
              </text>
              <view class="diff-pair">
                <view
                  v-for="side in [
                    { label: '银行流水', source: row.bank },
                    { label: '收付款记录', source: row.ledger }
                  ]"
                  :key="side.label"
                  class="diff-side"
                >
                  <text class="caption">
                    {{ side.label }} ·
                    {{ side.source ? `第 ${side.source.row_number} 行` : '缺失' }}
                  </text>
                  <template v-if="side.source">
                    <text class="number">¥ {{ money(side.source.amount) }}</text>
                    <text class="caption">
                      {{ side.source.direction === 'IN' ? '收入' : '支出' }} ·
                      {{ side.source.transaction_date }}
                    </text>
                    <text class="caption">{{ side.source.file_name }}</text>
                    <text class="caption">来源 {{ side.source.import_id }}</text>
                  </template>
                  <text v-else class="caption">未找到相同业务单号</text>
                </view>
              </view>
              <text :class="row.status === 'MATCHED' ? 'caption' : 'error-text'">
                {{ row.reason }}
              </text>
              <text v-if="row.difference !== null" class="caption">
                差额 ¥ {{ money(row.difference) }}
              </text>
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
          <view class="button-row extension-actions">
            <button class="ft-button secondary" @click="go('task', { id: data.task_id })">
              查看任务记录
            </button>
            <button class="ft-button primary" @click="go('reconcile', { period: data.period })">
              新建对账
            </button>
          </view>
        </template>
      </StatePanel>
    </view>
  </AppShell>
</template>
