<script setup lang="ts">
import { inputValue } from '../../utils/forms';
import { ref, reactive, computed, watch } from 'vue';
import { onLoad, onShow } from '@dcloudio/uni-app';
import { api } from '../../api';
import { session, snapshot, isCurrent } from '../../stores/session';
import { errorMessage, ApiError, StaleResponse } from '../../http/request';
import { guard, go } from '../../utils/navigation';
import { validateBilling, splitAmount, rates, requestKey } from '../../utils/billing';
import { invoiceTypes } from '../../utils/format';
import type { BillingInput, BillingTask } from '../../types/api';
import AppShell from '../../components/AppShell.vue';
import StatePanel from '../../components/StatePanel.vue';
import ModalSheet from '../../components/ModalSheet.vue';
import AmountBreakdown from '../../components/AmountBreakdown.vue';
const form = reactive<BillingInput>({
  invoice_type: 'DIGITAL_NORMAL',
  buyer_name: '',
  buyer_tax_id: '',
  item_name: '',
  total_amount: '',
  tax_rate: '0.06',
  email: '',
  remark: ''
});
const savedForm = ref(JSON.stringify(form));
const unsavedChanges = computed(() => JSON.stringify(form) !== savedForm.value);
const fields = [
  { key: 'buyer_name', label: '购买方名称', placeholder: '请输入购买方完整名称', max: 120 },
  { key: 'buyer_tax_id', label: '购买方税号', placeholder: '18 位大写字母或数字', max: 18 },
  { key: 'item_name', label: '开票项目', placeholder: '例如：技术服务费', max: 120 },
  { key: 'total_amount', label: '开票金额（含税）', placeholder: '0.00', max: 13 },
  { key: 'email', label: '接收邮箱（选填）', placeholder: '选填，演示环境不发送邮件', max: 120 }
] as const;
const source = ref<BillingTask | null>(null),
  loading = ref(false),
  loadError = ref(''),
  errors = ref<Record<string, string>>({}),
  submitError = ref(''),
  review = ref(false),
  busy = ref(false),
  contextChanged = ref(false),
  uncertain = ref(false);
let context = snapshot(),
  idempotency = requestKey(),
  submittedBody: BillingInput | null = null;
const amounts = computed(() => splitAmount(form.total_amount, form.tax_rate));
onLoad(async (q) => {
  context = snapshot();
  if (q?.source_task_id) {
    form.source_task_id = q.source_task_id;
    savedForm.value = JSON.stringify(form);
    await loadSource();
  }
});
onShow(() => {
  guard();
  if (!isCurrent(context)) {
    contextChanged.value = true;
    review.value = false;
  }
});
watch(
  () => session.epoch,
  () => {
    contextChanged.value = true;
    review.value = false;
  }
);
async function loadSource() {
  if (!form.source_task_id) return;
  loading.value = true;
  loadError.value = '';
  try {
    const task = await api.task(form.source_task_id);
    if (task.status !== 'FAILED') throw new Error('仅失败申请可以修改后重新提交');
    source.value = task;
    Object.assign(form, task.input, { source_task_id: task.id });
    savedForm.value = JSON.stringify(form);
  } catch (e) {
    loadError.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}
function check() {
  errors.value = validateBilling(form);
  if (Object.keys(errors.value).length) {
    // #ifdef H5
    setTimeout(
      () => document.getElementById(Object.keys(errors.value)[0])?.querySelector('input')?.focus(),
      0
    );
    // #endif
    return;
  }
  review.value = true;
}
async function submit() {
  if (busy.value || contextChanged.value || !isCurrent(context)) {
    contextChanged.value = true;
    return;
  }
  if (Object.keys(validateBilling(form)).length && !uncertain.value) return;
  busy.value = true;
  submitError.value = '';
  if (!submittedBody) submittedBody = { ...form, total_amount: amounts.value.total_amount };
  try {
    const task = await api.createBilling(submittedBody, idempotency);
    savedForm.value = JSON.stringify(form);
    review.value = false;
    uni.redirectTo({ url: `/pages/billing/result?id=${encodeURIComponent(task.id)}` });
  } catch (e) {
    if (e instanceof StaleResponse) {
      contextChanged.value = true;
      review.value = false;
    } else {
      submitError.value = errorMessage(e);
      if (
        e instanceof ApiError &&
        (e.code === 'NETWORK' || (e.status ?? 0) >= 500 || e.status === 408)
      ) {
        uncertain.value = true;
      } else {
        uncertain.value = false;
        submittedBody = null;
        idempotency = requestKey();
        if (e instanceof ApiError) errors.value = e.fields;
        review.value = false;
      }
    }
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <AppShell
    :title="form.source_task_id ? '修改后重新申请' : '新建开票申请'"
    fallback="billing"
    :unsaved-changes="unsavedChanges"
    :navigation-busy="busy"
  >
    <view class="company-bar">
      <text class="eyebrow">销售方 · 只读</text>
      <text class="company-name">{{ session.company?.name }}</text>
      <text class="caption">{{ session.company?.tax_id }}</text>
    </view>
    <text class="notice warning">
      仅用于模拟开票。提交前请核对票种、购方与金额；演示环境不发送邮件。
    </text>
    <view v-if="contextChanged" class="notice error">
      <text>企业或登录状态已改变，请返回记录页，重新确认销售方后填写。</text>
      <button class="ft-button secondary" @click="go('billing')">返回开票记录</button>
    </view>
    <StatePanel :busy="loading" :error="loadError" @retry="loadSource">
      <view v-if="source" class="notice error">
        <text>原失败申请：{{ source.number }}</text>
        <text style="display: block">模拟失败原因：{{ source.failure_reason }}</text>
        <text style="display: block">本次创建关联的新申请，原记录保留。</text>
      </view>
      <view class="card">
        <text class="field-label">发票类型</text>
        <view class="segments">
          <button
            class="ft-button"
            v-for="type in ['DIGITAL_NORMAL', 'DIGITAL_SPECIAL'] as const"
            :key="type"
            :disabled="busy || uncertain || contextChanged"
            :class="{ selected: form.invoice_type === type }"
            @click="form.invoice_type = type"
          >
            {{ invoiceTypes[type] }}
          </button>
        </view>
        <view v-for="field in fields" :key="field.key" class="field">
          <label :for="field.key" class="field-label">{{ field.label }}</label>
          <input
            :id="field.key"
            v-model="form[field.key]"
            @blur="form[field.key] = inputValue($event)"
            :aria-label="field.label"
            :aria-invalid="!!errors[field.key]"
            :class="{ invalid: errors[field.key] }"
            :placeholder="field.placeholder"
            :maxlength="field.max"
            :type="field.key === 'total_amount' ? 'digit' : 'text'"
            :disabled="busy || uncertain || contextChanged"
            :cursor-spacing="120"
          />
          <text v-if="errors[field.key]" class="error-text">{{ errors[field.key] }}</text>
          <text v-if="field.key === 'email'" class="caption">只保存邮箱，不发送邮件</text>
        </view>
        <view class="field">
          <text class="field-label">演示税率</text>
          <view class="filter-chips">
            <button
              class="ft-button"
              v-for="rate in rates"
              :key="rate"
              :disabled="busy || uncertain || contextChanged"
              :class="['chip', { 'selected-card': form.tax_rate === rate }]"
              @click="form.tax_rate = rate"
            >
              {{ Number(rate) * 100 }}%
            </button>
          </view>
          <text class="caption">税率仅为演示配置，不是实际适用税率建议</text>
        </view>
        <view class="field">
          <label for="remark" class="field-label">备注（选填）</label>
          <textarea
            id="remark"
            v-model="form.remark"
            @blur="form.remark = inputValue($event)"
            aria-label="备注"
            :disabled="busy || uncertain || contextChanged"
            placeholder="填写补充说明"
            maxlength="500"
            :cursor-spacing="120"
          />
        </view>
        <AmountBreakdown v-bind="amounts" />
      </view>
      <text v-if="submitError && !review" class="notice error" role="alert">{{ submitError }}</text>
      <view class="sticky-actions">
        <button
          class="ft-button primary"
          :disabled="contextChanged || busy"
          :loading="busy"
          @click="uncertain ? (review = true) : check()"
        >
          {{ uncertain ? '查询本次提交结果' : form.source_task_id ? '提交新申请' : '提交开票申请' }}
        </button>
      </view>
    </StatePanel>
    <ModalSheet :open="review" title="请复核开票申请" :busy="busy" @close="review = false">
      <text class="notice">销售方：{{ session.company?.name }}</text>
      <view class="detail-row">
        <text>购买方</text>
        <text>{{ form.buyer_name }}</text>
      </view>
      <view class="detail-row">
        <text>税号</text>
        <text>{{ form.buyer_tax_id }}</text>
      </view>
      <view class="detail-row">
        <text>项目</text>
        <text>{{ form.item_name }}</text>
      </view>
      <view class="detail-row">
        <text>票种 / 税率</text>
        <text>{{ invoiceTypes[form.invoice_type] }} / {{ Number(form.tax_rate) * 100 }}%</text>
      </view>
      <AmountBreakdown v-bind="amounts" />
      <text v-if="submitError" class="notice error" role="alert">{{ submitError }}</text>
      <text v-if="uncertain" class="notice warning">
        提交结果尚未确认，输入暂时锁定。重试将查询同一次提交，避免重复申请，也可返回记录查看。
      </text>
      <view class="button-row">
        <button class="ft-button secondary" :disabled="busy || uncertain" @click="review = false">
          返回修改
        </button>
        <button
          class="ft-button primary"
          :disabled="busy || contextChanged"
          :loading="busy"
          @click="submit"
        >
          {{ busy ? '提交中…' : uncertain ? '重试本次提交' : '确认提交' }}
        </button>
      </view>
      <button v-if="uncertain" class="ft-button text-button" @click="go('billing')">
        返回开票记录
      </button>
    </ModalSheet>
  </AppShell>
</template>
