<script setup lang="ts">
import { inputValue } from '../../utils/forms';
import { ref, reactive, computed } from 'vue';
import { onShow, onPullDownRefresh, onReachBottom } from '@dcloudio/uni-app';
import { api } from '../../api';
import { usePaged } from '../../composables/paged';
import { go, guard } from '../../utils/navigation';
import { money, invoiceTypes } from '../../utils/format';
import type { Invoice, InvoicePage, InvoiceQuery } from '../../types/api';
import AppShell from '../../components/AppShell.vue';
import CompanyBar from '../../components/CompanyBar.vue';
import StatePanel from '../../components/StatePanel.vue';
import StatusBadge from '../../components/StatusBadge.vue';
import ModalSheet from '../../components/ModalSheet.vue';
const keyword = ref(''),
  query = reactive<InvoiceQuery>({}),
  filterOpen = ref(false),
  draft = reactive({ date_from: '', date_to: '', invoice_type: '', verification_status: '' }),
  filterError = ref('');
const { items, meta, busy, error, load } = usePaged<Invoice, InvoicePage>((page) =>
  api.invoices({ ...query, page, page_size: 20 })
);
onShow(() => {
  if (guard()) load();
});
onPullDownRefresh(() => load());
onReachBottom(() => load(false));
const filters = computed(() =>
  [
    query.date_from && `起 ${query.date_from}`,
    query.date_to && `止 ${query.date_to}`,
    query.invoice_type && invoiceTypes[query.invoice_type as keyof typeof invoiceTypes],
    query.verification_status &&
      { PENDING: '待模拟验真', VERIFIED: '模拟验真通过', FAILED: '模拟验真失败' }[
        query.verification_status
      ]
  ].filter(Boolean)
);
function search() {
  query.keyword = keyword.value.trim();
  load();
}
function openFilter() {
  Object.assign(draft, {
    date_from: query.date_from || '',
    date_to: query.date_to || '',
    invoice_type: query.invoice_type || '',
    verification_status: query.verification_status || ''
  });
  filterError.value = '';
  filterOpen.value = true;
}
function apply() {
  if (draft.date_from && draft.date_to && draft.date_from > draft.date_to) {
    filterError.value = '开始日期不能晚于结束日期';
    return;
  }
  Object.assign(query, draft);
  filterOpen.value = false;
  load();
}
function direction(value: string) {
  query.direction = value;
  load();
}
function resetDraft() {
  Object.assign(draft, { date_from: '', date_to: '', invoice_type: '', verification_status: '' });
  filterError.value = '';
}
</script>
<template>
  <AppShell title="票据管理" tab="invoices">
    <CompanyBar>
      <template #action>
        <button id="switch-company" class="ft-button text-button" @click="go('company')">
          切换企业 ›
        </button>
      </template>
    </CompanyBar>
    <view class="row" style="margin-bottom: 12px">
      <input
        v-model="keyword"
        @blur="keyword = inputValue($event)"
        class="grow"
        aria-label="搜索购销方名称或发票号码"
        placeholder="购销方名称或发票号码"
        confirm-type="search"
        @confirm="
          keyword = inputValue($event);
          search();
        "
      />
      <button class="ft-button text-button" @click="search">搜索</button>
      <button
        v-if="keyword"
        class="ft-button icon-button"
        aria-label="清除搜索"
        @click="
          keyword = '';
          search();
        "
      >
        ×
      </button>
    </view>
    <view class="row between">
      <view class="segments grow">
        <button
          class="ft-button"
          v-for="item in [
            { v: '', t: '全部' },
            { v: 'INPUT', t: '进项' },
            { v: 'OUTPUT', t: '销项' }
          ]"
          :key="item.v"
          :class="{ selected: (query.direction || '') === item.v }"
          @click="direction(item.v)"
        >
          {{ item.t }}
        </button>
      </view>
      <button class="ft-button text-button" style="margin-bottom: 16px" @click="openFilter">
        筛选 {{ filters.length || '' }}
      </button>
    </view>
    <view v-if="filters.length" class="filter-chips">
      <text v-for="f in filters" :key="String(f)" class="chip">{{ f }}</text>
    </view>
    <view v-if="meta" class="notice row between wrap">
      <text>全部筛选结果 {{ meta.total }} 张</text>
      <text class="number">价税合计 ¥ {{ money(meta.total_amount) }}</text>
    </view>
    <StatePanel
      :busy="busy && !items.length"
      :error="!items.length ? error : ''"
      :empty="!busy && !error && !items.length"
      :empty-text="
        query.keyword || filters.length
          ? '没有符合条件的票据，请调整搜索或筛选'
          : '当前企业暂无票据'
      "
      @retry="load()"
    >
      <button
        v-for="invoice in items"
        :key="invoice.id"
        class="ft-button list-card"
        @click="go('invoice', { id: invoice.id })"
      >
        <view class="row between wrap">
          <text class="chip">
            {{ invoice.direction === 'INPUT' ? '进项' : '销项' }} ·
            {{ invoiceTypes[invoice.invoice_type] }}
          </text>
          <StatusBadge
            :status="invoice.verification_status"
            :text="invoice.verification_status === 'PENDING' ? '待模拟验真' : undefined"
          />
        </view>
        <text class="list-title">
          {{ invoice.direction === 'INPUT' ? invoice.seller.name : invoice.buyer.name }}
        </text>
        <view class="row between wrap">
          <text class="caption">{{ invoice.issued_at.slice(0, 10) }}</text>
          <text class="number amount">¥ {{ money(invoice.total_amount) }}</text>
        </view>
        <text class="caption">票号 {{ invoice.number }}</text>
      </button>
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
    <text v-else-if="items.length" class="empty-foot">已加载全部 {{ meta?.total }} 张票据</text>
  </AppShell>
  <ModalSheet :open="filterOpen" title="筛选票据" @close="filterOpen = false">
    <view class="field">
      <text class="field-label">开始日期</text>
      <picker mode="date" :value="draft.date_from" @change="draft.date_from = inputValue($event)">
        <button class="ft-button secondary">
          {{ draft.date_from || '选择开始日期' }}
        </button>
      </picker>
    </view>
    <view class="field">
      <text class="field-label">结束日期</text>
      <picker mode="date" :value="draft.date_to" @change="draft.date_to = inputValue($event)">
        <button class="ft-button secondary">{{ draft.date_to || '选择结束日期' }}</button>
      </picker>
    </view>
    <text class="field-label">发票类型</text>
    <view class="filter-chips">
      <button
        class="ft-button"
        :class="['chip', { 'selected-card': !draft.invoice_type }]"
        @click="draft.invoice_type = ''"
      >
        全部
      </button>
      <button
        class="ft-button"
        v-for="(label, value) in invoiceTypes"
        :key="value"
        :class="['chip', { 'selected-card': draft.invoice_type === value }]"
        @click="draft.invoice_type = value"
      >
        {{ label }}
      </button>
    </view>
    <text class="field-label">模拟验真状态</text>
    <view class="filter-chips">
      <button
        class="ft-button"
        v-for="s in [
          { v: '', t: '全部' },
          { v: 'PENDING', t: '待验真' },
          { v: 'VERIFIED', t: '通过' },
          { v: 'FAILED', t: '失败' }
        ]"
        :key="s.v"
        :class="['chip', { 'selected-card': draft.verification_status === s.v }]"
        @click="draft.verification_status = s.v"
      >
        {{ s.t }}
      </button>
    </view>
    <text v-if="filterError" class="error-text">{{ filterError }}</text>
    <view class="button-row">
      <button class="ft-button secondary" @click="resetDraft">重置筛选</button>
      <button class="ft-button primary" @click="apply">确定</button>
    </view>
  </ModalSheet>
</template>
