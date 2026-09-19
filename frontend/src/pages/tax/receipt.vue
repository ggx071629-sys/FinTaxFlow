<script setup lang="ts">
import { ref, watch } from 'vue';
import { onLoad, onShow } from '@dcloudio/uni-app';
import { extension } from '../../api/extension';
import { useResource } from '../../composables/resource';
import { go, guard } from '../../utils/navigation';
import { dateTime } from '../../utils/format';
import { downloadFile } from '../../utils/files';
import { errorMessage, StaleResponse } from '../../http/request';
import { session } from '../../stores/session';
import AppShell from '../../components/AppShell.vue';
import CompanyBar from '../../components/CompanyBar.vue';
import StatePanel from '../../components/StatePanel.vue';
const id = ref(''),
  fileBusy = ref(false),
  fileError = ref('');
onLoad((q) => {
  id.value = q?.id || '';
});
const { data, busy, error, load } = useResource(() => extension.receipt(id.value));
watch(
  () => session.epoch,
  () => {
    fileError.value = '';
    fileBusy.value = false;
  }
);
onShow(() => {
  if (guard()) load();
});
async function open() {
  if (!data.value?.file?.ready || fileBusy.value) return;
  fileBusy.value = true;
  fileError.value = '';
  try {
    await downloadFile(data.value.file);
  } catch (e) {
    if (!(e instanceof StaleResponse)) fileError.value = errorMessage(e);
  } finally {
    fileBusy.value = false;
  }
}
</script>
<template>
  <AppShell title="申报回执" fallback="tasks">
    <view class="extension-page">
      <CompanyBar />
      <StatePanel :busy="busy" :error="error" @retry="load">
        <template v-if="data">
          <view class="card">
            <view class="receipt-title">
              <text class="demo-badge">演示文件 · 非真实申报凭证</text>
              <text class="list-title" style="font-size: 20px">模拟申报受理回执</text>
              <text class="caption">FinTaxFlow 本地模拟申报站点</text>
            </view>
            <view class="detail-row">
              <text>受理编号</text>
              <text>{{ data.acceptance_number }}</text>
            </view>
            <view class="detail-row">
              <text>纳税人名称</text>
              <text>{{ data.company_name }}</text>
            </view>
            <view class="detail-row">
              <text>纳税人识别号</text>
              <text>{{ data.tax_id }}</text>
            </view>
            <view class="detail-row">
              <text>申报税种</text>
              <text>增值税（演示样例）</text>
            </view>
            <view class="detail-row">
              <text>所属期间</text>
              <text>{{ data.period }}</text>
            </view>
            <view class="detail-row">
              <text>受理时间</text>
              <text>{{ dateTime(data.accepted_at) }}</text>
            </view>
            <view class="receipt-footer">
              本文件仅用于演示财税自动化流程
              <br />
              不具备真实申报、缴税或税务证明效力
            </view>
          </view>
          <view v-if="!data.file?.ready" class="state-panel" role="status">
            <text>回执文件尚未就绪</text>
            <text class="caption">申报已受理，任务正在准备文件。请稍后刷新。</text>
            <button class="ft-button secondary" @click="load">刷新回执</button>
          </view>
          <text v-if="fileError" class="notice error" role="alert">{{ fileError }}</text>
          <text class="notice">回执关联原申报任务，重新登录后仍可查询。</text>
          <view class="button-row extension-actions">
            <button class="ft-button secondary" @click="go('task', { id: data.task_id })">
              返回任务
            </button>
            <button
              class="ft-button primary"
              :disabled="!data.file?.ready || fileBusy"
              :loading="fileBusy"
              @click="open"
            >
              查看回执文件
            </button>
          </view>
        </template>
      </StatePanel>
    </view>
  </AppShell>
</template>
