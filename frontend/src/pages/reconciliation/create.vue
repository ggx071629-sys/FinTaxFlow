<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { onShow, onLoad } from '@dcloudio/uni-app';
import { api } from '../../api';
import { extension } from '../../api/extension';
import { useResource } from '../../composables/resource';
import { useCommand } from '../../composables/command';
import { session } from '../../stores/session';
import { go, guard } from '../../utils/navigation';
import type { ImportValidation } from '../../types/api';
import AppShell from '../../components/AppShell.vue';
import CompanyBar from '../../components/CompanyBar.vue';
import MonthPicker from '../../components/MonthPicker.vue';
import StatePanel from '../../components/StatePanel.vue';
import ImportPicker from '../../components/ImportPicker.vue';
import ImportReview from '../../components/ImportReview.vue';
const period = ref(''),
  bank = ref<ImportValidation | null>(null),
  ledger = ref<ImportValidation | null>(null);
const bankSelected = ref(false),
  ledgerSelected = ref(false),
  bankUploading = ref(false),
  ledgerUploading = ref(false),
  submitted = ref(false);
watch([bank, ledger, period], () => {
  submitted.value = false;
});
const unsavedChanges = computed(
  () =>
    !submitted.value &&
    (bankSelected.value || ledgerSelected.value || !!bank.value || !!ledger.value)
);
const { data, busy, error, load } = useResource(() => api.accounting(period.value || undefined));
const command = useCommand('reconcile');
onLoad((q) => {
  period.value = q?.period || '';
});
onShow(() => {
  if (guard()) load();
});
watch(
  () => session.epoch,
  () => {
    period.value = '';
    bank.value = null;
    ledger.value = null;
  }
);
watch(data, (value) => {
  if (value && !period.value) period.value = value.period;
});
function month(value: string) {
  period.value = value;
  bank.value = null;
  ledger.value = null;
}
const ready = computed(
  () =>
    !!period.value &&
    !!bank.value?.valid &&
    !!ledger.value?.valid &&
    !bank.value.errors &&
    !bank.value.duplicates &&
    !ledger.value.errors &&
    !ledger.value.duplicates
);
async function start() {
  if (!ready.value) return;
  const input = {
    bank_import_id: bank.value!.id,
    ledger_import_id: ledger.value!.id,
    period: period.value
  };
  const result = await command.run(input, (key) =>
    extension.reconcile(input.bank_import_id, input.ledger_import_id, input.period, key)
  );
  if (result) {
    submitted.value = true;
    go('reconciliation', { id: result.id });
  }
}
</script>
<template>
  <AppShell
    title="导入对账数据"
    fallback="accounting"
    :unsaved-changes="unsavedChanges"
    :navigation-busy="command.busy.value || bankUploading || ledgerUploading"
  >
    <view class="extension-page">
      <CompanyBar />
      <StatePanel :busy="busy" :error="error" @retry="load">
        <MonthPicker :period="period" :periods="data?.periods || []" @change="month" />
      </StatePanel>
      <text class="notice">
        上传同一企业、同一期间的两份数据，按业务单号、收付方向和金额一对一核对。
      </text>
      <ImportPicker
        kind="BANK"
        title="银行流水"
        @selected-change="
          bankSelected = $event;
          submitted = false;
        "
        @busy-change="bankUploading = $event"
        :period="period"
        :disabled="!period || command.busy.value"
        @validated="bank = $event"
      />
      <ImportReview v-if="bank" :value="bank" />
      <ImportPicker
        kind="LEDGER"
        title="收付款记录"
        @selected-change="
          ledgerSelected = $event;
          submitted = false;
        "
        @busy-change="ledgerUploading = $event"
        :period="period"
        :disabled="!period || command.busy.value"
        @validated="ledger = $event"
      />
      <ImportReview v-if="ledger" :value="ledger" />
      <text
        v-if="bank?.errors || bank?.duplicates || ledger?.errors || ledger?.duplicates"
        class="notice error"
        role="alert"
      >
        两份文件必须全部有效。请修正错误与重复业务单号后重新校验，不会自动选取其中一条。
      </text>
      <view class="card">
        <text class="section-title">核对规则</text>
        <view class="detail-row">
          <text>关联方式</text>
          <text>业务单号完全一致</text>
        </view>
        <view class="detail-row">
          <text>一致条件</text>
          <text>金额及收付方向均一致</text>
        </view>
        <view class="detail-row">
          <text>结果分类</text>
          <text>一致、差异、记录缺失</text>
        </view>
      </view>
      <text class="notice">对账不生成凭证，不会修改预置账务摘要。</text>
      <text v-if="command.error.value" class="notice error" role="alert">
        {{ command.error.value }}
      </text>
      <view class="extension-actions">
        <button
          class="ft-button primary"
          :disabled="!ready || command.busy.value"
          :loading="command.busy.value"
          @click="start"
        >
          开始对账
        </button>
      </view>
    </view>
  </AppShell>
</template>
