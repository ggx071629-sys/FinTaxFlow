<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import { api } from '../../api';
import { extension } from '../../api/extension';
import { session } from '../../stores/session';
import { useResource } from '../../composables/resource';
import { go, guard } from '../../utils/navigation';
import { money } from '../../utils/format';
import AppShell from '../../components/AppShell.vue';
import CompanyBar from '../../components/CompanyBar.vue';
import StatePanel from '../../components/StatePanel.vue';
import MonthPicker from '../../components/MonthPicker.vue';
const period = ref(''),
  selected = ref(0);
watch(
  () => session.epoch,
  () => {
    period.value = '';
    selected.value = 0;
  }
);
const { data, busy, error, load } = useResource(() => api.accounting(period.value || undefined));
const recent = useResource(() => extension.reconciliations(period.value || undefined));
onShow(() => {
  if (guard()) {
    load();
    recent.load();
  }
});
const metrics = [
  { key: 'income', label: '收入' },
  { key: 'expense', label: '支出' },
  { key: 'profit', label: '利润' },
  { key: 'receivable', label: '应收' },
  { key: 'payable', label: '应付' }
] as const;
const max = computed(() =>
  Math.max(1, ...(data.value?.trend || []).flatMap((t) => [Number(t.income), Number(t.expense)]))
);
function height(v: string) {
  return `${(Math.max(0, Number(v)) / max.value) * 90}%`;
}
function month(value: string) {
  period.value = value;
  load();
  recent.load();
}
</script>
<template>
  <AppShell title="账务查询">
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
    <text class="section-title">财务对账</text>
    <view class="card">
      <text class="list-title">银行流水与收付款记录</text>
      <text class="caption">核对业务单号、收付方向与金额，不修改账务摘要。</text>
      <button
        class="ft-button primary"
        style="margin-top: 12px"
        @click="go('reconcile', { period: period || data?.period || '' })"
      >
        新建对账
      </button>
      <StatePanel :busy="recent.busy.value" :error="recent.error.value" @retry="recent.load">
        <button
          v-if="recent.data.value?.items[0]"
          class="ft-button text-button"
          @click="go('reconciliation', { id: recent.data.value.items[0].id })"
        >
          最近对账 ·
          {{ recent.data.value.items[0].different + recent.data.value.items[0].missing }} 组差异
        </button>
        <text v-else class="caption">本期暂无对账记录</text>
      </StatePanel>
    </view>
    <text class="notice">
      独立预置的演示账务摘要，不随开票变化；利润按收入减支出的演示口径展示。
    </text>
    <StatePanel :busy="busy" :error="error" @retry="load">
      <template v-if="data">
        <StatePanel :empty="!data.summary" empty-text="该月份暂无账务摘要，请选择已有样例月份">
          <view v-if="data.summary" class="card">
            <view class="row between">
              <text class="section-title">{{ data.period }} 账务摘要</text>
              <text class="caption">单位：元</text>
            </view>
            <view class="metric-grid">
              <view
                v-for="metric in metrics"
                :key="metric.key"
                class="metric"
                :class="{ 'metric-wide': money(data.summary[metric.key]).length > 10 }"
              >
                <text class="caption">{{ metric.label }}</text>
                <text class="number">{{ money(data.summary[metric.key]) }}</text>
              </view>
            </view>
          </view>
        </StatePanel>
        <view class="card">
          <text class="section-title">三个月收支趋势</text>
          <view class="row between caption">
            <text>
              <text class="legend-dot" />
              收入
              <text class="legend-dot expense" />
              支出
            </text>
            <text>单位：元</text>
          </view>
          <template v-if="data.trend.length">
            <view class="chart-bars">
              <button
                v-for="(item, index) in data.trend"
                :key="item.period"
                class="ft-button chart-column"
                :aria-label="`${item.period} 收入 ${item.income} 元，支出 ${item.expense} 元`"
                :aria-pressed="selected === index"
                @click="selected = index"
              >
                <view class="bar" :style="{ height: height(item.income) }" />
                <view class="bar expense" :style="{ height: height(item.expense) }" />
              </button>
            </view>
            <view class="chart-labels">
              <text v-for="item in data.trend" :key="item.period">{{ item.period }}</text>
            </view>
            <view v-if="data.trend[selected]" class="notice" style="margin: 16px 0 0" role="status">
              <text>
                {{ data.trend[selected].period }} · 收入 {{ money(data.trend[selected].income) }} /
                支出 {{ money(data.trend[selected].expense) }} 元
              </text>
            </view>
          </template>
          <text v-else class="caption">暂无趋势数据</text>
        </view>
      </template>
    </StatePanel>
  </AppShell>
</template>
