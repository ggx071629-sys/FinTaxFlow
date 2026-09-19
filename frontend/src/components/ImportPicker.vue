<script setup lang="ts">
import { ref, watch } from 'vue';
import { session, snapshot, isCurrent } from '../stores/session';
import { chooseCsv, uploadCsv, downloadTemplate, type SelectedFile } from '../utils/files';
import { errorMessage, StaleResponse } from '../http/request';
import { requestKey } from '../utils/billing';
import type { ImportKind, ImportValidation } from '../types/api';
const props = defineProps<{
  kind: ImportKind;
  title: string;
  period?: string;
  disabled?: boolean;
}>();
const emit = defineEmits<{
  validated: [value: ImportValidation | null];
  selectedChange: [value: boolean];
  busyChange: [value: boolean];
}>();
const file = ref<SelectedFile | null>(null),
  result = ref<ImportValidation | null>(null),
  busy = ref(false),
  error = ref('');
watch(file, (value) => emit('selectedChange', !!value));
// Validation can unmount this picker immediately; notify before the parent renders.
watch(busy, (value) => emit('busyChange', value), { flush: 'sync' });
let key = '',
  generation = 0;
watch(
  () => [session.epoch, props.period],
  () => {
    generation++;
    file.value = null;
    result.value = null;
    error.value = '';
    busy.value = false;
    key = '';
    emit('validated', null);
  }
);
async function choose() {
  const ctx = snapshot(),
    gen = generation;
  try {
    const selected = await chooseCsv();
    if (!isCurrent(ctx) || gen !== generation || !selected) return;
    file.value = selected;
    key = requestKey();
    result.value = null;
    error.value = '';
    emit('validated', null);
  } catch (e) {
    if (isCurrent(ctx) && gen === generation) error.value = errorMessage(e);
  }
}
async function validate() {
  if (!file.value || busy.value || props.disabled) return;
  const gen = generation;
  busy.value = true;
  error.value = '';
  try {
    const data = await uploadCsv(file.value, props.kind, props.period, key);
    if (gen === generation) {
      result.value = data;
      emit('validated', data);
    }
  } catch (e) {
    if (gen === generation && !(e instanceof StaleResponse)) error.value = errorMessage(e);
  } finally {
    if (gen === generation) busy.value = false;
  }
}
async function template() {
  try {
    await downloadTemplate(props.kind);
  } catch (e) {
    if (!(e instanceof StaleResponse)) error.value = errorMessage(e);
  }
}
</script>
<template>
  <view class="card">
    <view class="row between">
      <text class="section-title">{{ title }}</text>
      <button class="ft-button text-button" :disabled="busy || disabled" @click="template">
        下载模板
      </button>
    </view>
    <text class="caption">请使用 UTF-8 CSV 固定模板，一行对应一笔记录。</text>
    <view class="upload-zone">
      <text class="list-title">{{ file?.name || `选择${title}` }}</text>
      <text class="caption">
        {{
          file
            ? `${file.size} 字节 · ${result ? '已完成校验' : '待校验'}`
            : '支持 CSV · 使用模板可减少填写错误'
        }}
      </text>
      <button class="ft-button secondary" :disabled="busy || disabled" @click="choose">
        {{ file ? '重新选择文件' : '选择文件' }}
      </button>
    </view>
    <text v-if="error" class="notice error" role="alert">{{ error }}</text>
    <text v-if="result" class="notice" role="status">
      校验完成：{{ result.valid }} 行有效，{{ result.errors }} 行错误，{{ result.duplicates }}
      行重复。
    </text>
    <button
      v-if="!result"
      class="ft-button primary"
      :disabled="!file || busy || disabled"
      :loading="busy"
      @click="validate"
    >
      {{ busy ? '上传并校验中…' : '校验清单' }}
    </button>
  </view>
</template>
