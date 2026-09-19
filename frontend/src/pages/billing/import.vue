<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { onLoad, onShow } from '@dcloudio/uni-app';
import { extension } from '../../api/extension';
import { useCommand } from '../../composables/command';
import { session, snapshot, isCurrent } from '../../stores/session';
import { go, guard } from '../../utils/navigation';
import { money } from '../../utils/format';
import { errorMessage, StaleResponse } from '../../http/request';
import type { ImportValidation } from '../../types/api';
import StatePanel from '../../components/StatePanel.vue';
import AppShell from '../../components/AppShell.vue';
import CompanyBar from '../../components/CompanyBar.vue';
import ImportPicker from '../../components/ImportPicker.vue';
import ImportReview from '../../components/ImportReview.vue';
import ModalSheet from '../../components/ModalSheet.vue';
const validation = ref<ImportValidation | null>(null),
  confirm = ref(false),
  loadError = ref(''),
  importBusy = ref(false),
  importId = ref('');
const fileSelected = ref(false),
  uploadBusy = ref(false),
  submitted = ref(false);
watch(validation, () => {
  submitted.value = false;
});
const unsavedChanges = computed(
  () => !submitted.value && (fileSelected.value || !!validation.value)
);
const { busy, error, pending, refreshPending, run } = useCommand<{ import_id: string }>(
  'create-batch'
);
const pendingImport = computed(() =>
  typeof pending.value?.import_id === 'string' ? pending.value.import_id : ''
);
watch(
  () => session.epoch,
  () => {
    validation.value = null;
    confirm.value = false;
    importId.value = '';
    loadError.value = '';
    importBusy.value = false;
    fileSelected.value = false;
    submitted.value = false;
  }
);
onLoad((q) => {
  importId.value = q?.id || '';
});
onShow(() => {
  if (!guard()) return;
  refreshPending();
  if (pendingImport.value) importId.value = pendingImport.value;
  if (importId.value) loadImport();
});
async function loadImport() {
  if (importBusy.value) return;
  const context = snapshot();
  importBusy.value = true;
  loadError.value = '';
  try {
    const value = await extension.import(importId.value);
    if (isCurrent(context)) validation.value = value;
  } catch (e) {
    if (isCurrent(context) && !(e instanceof StaleResponse)) loadError.value = errorMessage(e);
  } finally {
    if (isCurrent(context)) importBusy.value = false;
  }
}
async function submit() {
  const id = pendingImport.value || (validation.value?.valid ? validation.value.id : '');
  if (!id) return;
  const batch = await run({ import_id: id }, (key) => extension.createBatch(id, key));
  if (batch) {
    submitted.value = true;
    confirm.value = false;
    go('batch', { id: batch.id });
  } else if (!pendingImport.value && !validation.value) {
    // A definitive rejection (e.g. the original import was reset) permits a new upload.
    importId.value = '';
    loadError.value = '';
  }
}
</script>
<template>
  <AppShell
    title="导入开票清单"
    fallback="billing"
    :unsaved-changes="unsavedChanges"
    :navigation-busy="busy || uploadBusy"
  >
    <view class="extension-page">
      <CompanyBar />
      <view class="stepper">
        <text :class="{ active: !validation }">1 选择文件</text>
        <text :class="{ active: !!validation }">2 校验清单</text>
        <text>3 提交开票</text>
      </view>
      <view v-if="pendingImport" class="card" role="status">
        <text class="section-title">上次提交结果待确认</text>
        <text class="notice">
          已保留原开票清单。请先查询或重试原提交：已受理时返回原批次，未受理时继续提交同一份清单，避免重复开票。
        </text>
        <button class="ft-button primary" :disabled="busy" :loading="busy" @click="submit">
          查询或重试原提交
        </button>
      </view>
      <text v-if="error" class="notice error" role="alert">{{ error }}</text>
      <StatePanel
        v-if="importId && !validation"
        :busy="importBusy"
        :error="loadError"
        @retry="loadImport"
      />
      <ImportPicker
        v-if="!validation && !importId"
        kind="BILLING"
        title="开票清单"
        @selected-change="
          fileSelected = $event;
          submitted = false;
        "
        @busy-change="uploadBusy = $event"
        @validated="validation = $event"
      />
      <template v-if="validation">
        <ImportReview :value="validation" />
        <text v-if="validation.errors + validation.duplicates" class="notice warning">
          错误行和重复行不会提交，请修正后另行导入。
        </text>
        <view class="card">
          <text class="section-title">本次提交预览</text>
          <view class="detail-row">
            <text>有效申请</text>
            <text>{{ validation.valid }} 笔</text>
          </view>
          <view class="detail-row">
            <text>价税合计</text>
            <text class="number">¥ {{ money(validation.valid_amount) }}</text>
          </view>
        </view>
        <view class="button-row extension-actions">
          <button
            class="ft-button secondary"
            :disabled="busy || !!pendingImport"
            @click="
              validation = null;
              importId = '';
              fileSelected = false;
              submitted = false;
            "
          >
            重新上传
          </button>
          <button
            class="ft-button primary"
            :disabled="busy || !!pendingImport || !validation.valid"
            @click="confirm = true"
          >
            提交 {{ validation.valid }} 笔申请
          </button>
        </view>
      </template>
      <text class="notice">当前仅模拟开票，不向真实税务平台提交。</text>
      <ModalSheet :open="confirm" title="确认批量开票" :busy="busy" @close="confirm = false">
        <text class="list-title">{{ session.company?.name }}</text>
        <text class="notice">
          本次仅提交 {{ validation?.valid }} 行有效数据，价税合计 ¥
          {{ money(validation?.valid_amount) }}。错误与重复行已排除。
        </text>
        <text v-if="error" class="notice error" role="alert">{{ error }}</text>
        <view class="button-row">
          <button class="ft-button secondary" :disabled="busy" @click="confirm = false">
            取消
          </button>
          <button class="ft-button primary" :disabled="busy" :loading="busy" @click="submit">
            确认提交
          </button>
        </view>
      </ModalSheet>
    </view>
  </AppShell>
</template>
