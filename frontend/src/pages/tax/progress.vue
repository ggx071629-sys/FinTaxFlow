<script setup lang="ts">
import { ref, watch } from 'vue';
import { onLoad, onShow } from '@dcloudio/uni-app';
import { api } from '../../api';
import { extension } from '../../api/extension';
import { useCommand } from '../../composables/command';
import ModalSheet from '../../components/ModalSheet.vue';
import type { TaxFiling } from '../../types/api';
import { session } from '../../stores/session';
import { useResource } from '../../composables/resource';
import { go, guard } from '../../utils/navigation';
import { dateTime } from '../../utils/format';
import AppShell from '../../components/AppShell.vue';
import CompanyBar from '../../components/CompanyBar.vue';
import StatePanel from '../../components/StatePanel.vue';
import StatusBadge from '../../components/StatusBadge.vue';
import MonthPicker from '../../components/MonthPicker.vue';
import Timeline from '../../components/Timeline.vue';
const selectedTax = ref<TaxFiling | null>(null);
const command = useCommand('declare');
async function declare() {
  if (!selectedTax.value) return;
  const input = {
    filing_id: selectedTax.value.id,
    period: selectedTax.value.period,
    tax_type: 'VAT' as const,
    confirmed: true as const
  };
  const result = await command.run(input, (key) => extension.declare(input, key));
  if (result) {
    selectedTax.value = null;
    go('task', { id: result.id });
  }
}
const period = ref(''),
  expanded = ref<string[]>([]);
onLoad((q) => {
  period.value = q?.period || '';
});
watch(
  () => session.epoch,
  () => {
    selectedTax.value = null;
    period.value = '';
    expanded.value = [];
  }
);
const { data, busy, error, load } = useResource(() => api.taxes(period.value || undefined));
onShow(() => {
  if (guard()) load();
});
function month(value: string) {
  period.value = value;
  expanded.value = [];
  load();
}
function toggle(id: string) {
  expanded.value = expanded.value.includes(id)
    ? expanded.value.filter((v) => v !== id)
    : [...expanded.value, id];
}
</script>
<template>
  <AppShell title="报税进度">
    <CompanyBar>
      <template #action>
        <button id="switch-company" class="ft-button text-button" @click="go('company')">
          切换企业 ›
        </button>
      </template>
    </CompanyBar>
    <MonthPicker
      :period="period || data?.period || ''"
      :periods="data?.periods || []"
      @change="month"
    />
    <text class="notice">仅支持增值税样例的模拟申报，税种与节点不代表实际申报或缴税义务。</text>
    <StatePanel :busy="busy" :error="error" @retry="load">
      <template v-if="data">
        <view class="executive-card">
          <text class="eyebrow">{{ data.period }} · 当期总体进度</text>
          <text class="company-name">{{ data.summary }}</text>
        </view>
        <StatePanel
          :empty="!data.items.length"
          empty-text="该月份暂无报税样例，可查询已有期间或在演示设置恢复样例"
        >
          <view v-for="tax in data.items" :key="tax.id" class="card">
            <view class="row between wrap">
              <text class="section-title">{{ tax.name }}</text>
              <StatusBadge :status="tax.status" />
            </view>
            <text class="caption">
              所属期 {{ tax.period }} · 更新 {{ dateTime(tax.updated_at) }}
            </text>
            <text v-if="tax.failure_reason" class="notice error" style="margin-top: 12px">
              模拟处理说明：{{ tax.failure_reason }}
            </text>
            <button
              class="ft-button text-button"
              :aria-expanded="expanded.includes(tax.id)"
              @click="toggle(tax.id)"
            >
              {{ expanded.includes(tax.id) ? '收起节点 ↑' : '展开节点 ↓' }}
            </button>
            <Timeline v-if="expanded.includes(tax.id)" :events="tax.nodes" />
            <button
              v-if="tax.receipt_id"
              class="ft-button secondary"
              @click="go('receipt', { id: tax.receipt_id })"
            >
              查看模拟回执
            </button>
            <button
              v-if="tax.declaration_task_id"
              class="ft-button text-button"
              @click="go('task', { id: tax.declaration_task_id })"
            >
              查看申报任务
            </button>
            <button
              v-else-if="tax.tax_type === 'VAT' && tax.can_declare"
              class="ft-button primary"
              @click="selectedTax = tax"
            >
              发起模拟申报
            </button>
          </view>
        </StatePanel>
      </template>
    </StatePanel>
    <button class="ft-button secondary" :disabled="busy" @click="load">刷新状态</button>
    <ModalSheet
      :open="!!selectedTax"
      title="确认发起模拟申报"
      :busy="command.busy.value"
      @close="selectedTax = null"
    >
      <text class="list-title">{{ session.company?.name }}</text>
      <view class="detail-row">
        <text>所属期间</text>
        <text>{{ selectedTax?.period }}</text>
      </view>
      <view class="detail-row">
        <text>申报税种</text>
        <text>增值税（演示样例）</text>
      </view>
      <text class="notice warning">
        仅操作本地模拟申报站点，不提交真实税务平台。请复核企业与期间。
      </text>
      <text v-if="command.error.value" class="notice error" role="alert">
        {{ command.error.value }}
      </text>
      <view class="button-row">
        <button
          class="ft-button secondary"
          :disabled="command.busy.value"
          @click="selectedTax = null"
        >
          取消
        </button>
        <button
          class="ft-button primary"
          :disabled="command.busy.value"
          :loading="command.busy.value"
          @click="declare"
        >
          确认发起申报
        </button>
      </view>
    </ModalSheet>
  </AppShell>
</template>
