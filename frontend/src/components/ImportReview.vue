<script setup lang="ts">
import { ref, watch } from 'vue';
import { extension } from '../api/extension';
import { usePaged } from '../composables/paged';
import { downloadFile } from '../utils/files';
import { errorMessage } from '../http/request';
import { invoiceTypes } from '../utils/format';
import type { ImportValidation, ImportRow, PageResult } from '../types/api';
import CountStrip from './CountStrip.vue';
import StatePanel from './StatePanel.vue';
const props = defineProps<{ value: ImportValidation }>();
const fieldLabels: Record<string, string> = {
  business_number: '业务单号', buyer_name: '购买方名称', buyer_tax_id: '购买方税号',
  item_name: '项目', total_amount: '含税金额', tax_rate: '税率', invoice_type: '票种',
  email: '邮箱', remark: '备注', transaction_date: '交易日期', counterparty: '交易对方',
  direction: '收付方向', amount: '金额'
};
function fieldValue(key: string, value: string) {
  if (key === 'invoice_type') return invoiceTypes[value as keyof typeof invoiceTypes] || value;
  if (key === 'direction') return value === 'IN' ? '收入' : value === 'OUT' ? '支出' : value;
  if (key === 'tax_rate') return `${Number(value) * 100}%`;
  return value || '未填写';
}
const filter = ref('ISSUES'),
  fileError = ref('');
const { items, meta, busy, error, load } = usePaged<ImportRow, PageResult<ImportRow>>((page) =>
  extension.importRows(props.value.id, filter.value, page)
);
watch(
  () => props.value.id,
  () => {
    filter.value = props.value.errors + props.value.duplicates ? 'ISSUES' : 'VALID';
    load();
  },
  { immediate: true }
);
function select(value: string) {
  filter.value = value;
  load();
}
async function issues() {
  fileError.value = '';
  try {
    if (props.value.issue_file) await downloadFile(props.value.issue_file);
  } catch (e) {
    fileError.value = errorMessage(e);
  }
}
</script>
<template>
  <view class="card">
    <text class="section-title">清单校验完成</text>
    <CountStrip
      :items="[
        { label: '有效行', value: value.valid, tone: 'good' },
        { label: '错误行', value: value.errors, tone: 'bad' },
        { label: '重复行', value: value.duplicates, tone: 'warn' }
      ]"
    />
    <text class="caption">共 {{ value.total }} 行 · 计数不重叠</text>
  </view>
  <text v-if="!value.valid" class="notice warning" role="alert">
    没有可提交的数据。请修正问题后重新上传。
  </text>
  <view class="segments">
    <button class="ft-button" :class="{ selected: filter === 'ISSUES' }" @click="select('ISSUES')">
      需要修正
    </button>
    <button class="ft-button" :class="{ selected: filter === 'VALID' }" @click="select('VALID')">
      有效行复核
    </button>
  </view>
  <view class="card">
    <view class="row between">
      <text class="section-title">
        {{ filter === 'ISSUES' ? '需要修正的记录' : '本次有效数据' }}
      </text>
      <button
        v-if="value.issue_file"
        class="ft-button text-button"
        :disabled="!value.issue_file.ready"
        @click="issues"
      >
        下载问题清单
      </button>
    </view>
    <text v-if="fileError" class="notice error" role="alert">{{ fileError }}</text>
    <StatePanel
      :busy="busy && !items.length"
      :error="error"
      :empty="!busy && !items.length"
      :empty-text="filter === 'ISSUES' ? '没有错误或重复记录' : '没有有效数据'"
      @retry="load()"
    >
      <view
        v-for="row in items"
        :key="row.row_number"
        class="import-row"
        :class="{ issue: row.status !== 'VALID' }"
      >
        <text class="list-title">
          第 {{ row.row_number }} 行 · {{ row.business_number || '未填写业务单号' }}
        </text>
        <text v-for="issue in row.issues" :key="issue.field" class="error-text">
          {{ fieldLabels[issue.field] || issue.field }}：{{ issue.message }}
        </text>
        <view
          v-if="row.status === 'VALID'"
          v-for="(value, key) in row.fields"
          :key="key"
          class="detail-row"
        >
          <text>{{ fieldLabels[key] || key }}</text>
          <text>{{ fieldValue(key, value) }}</text>
        </view>
      </view>
    </StatePanel>
    <button
      v-if="meta && items.length < meta.total"
      class="ft-button secondary"
      :disabled="busy"
      @click="load(false)"
    >
      加载更多
    </button>
    <text v-if="meta" class="caption">已显示 {{ items.length }} / {{ meta.total }} 行</text>
  </view>
</template>
