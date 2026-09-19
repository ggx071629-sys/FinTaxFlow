<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import { api } from '../../api';
import { extension } from '../../api/extension';
import { session, invalidateContext } from '../../stores/session';
import { useResource } from '../../composables/resource';
import { errorMessage, StaleResponse } from '../../http/request';
import { guard, go } from '../../utils/navigation';
import { requestKey } from '../../utils/billing';
import type { ResetRun } from '../../types/api';
import AppShell from '../../components/AppShell.vue';
import CompanyBar from '../../components/CompanyBar.vue';
import StatePanel from '../../components/StatePanel.vue';
import ModalSheet from '../../components/ModalSheet.vue';
const { data, busy, error, load } = useResource(api.settings);
const fault = ref<'NONE' | 'RECEIPT_DISCONNECT'>('NONE');
const selected = ref<'SUCCESS' | 'FAILED'>('SUCCESS'),
  saving = ref(false),
  saveError = ref(''),
  saved = ref(false),
  confirm = ref(false),
  resetBusy = ref(false),
  resetError = ref(''),
  run = ref<ResetRun | null>(null),
  pendingKey = ref('');
const savedSettings = ref('SUCCESS:NONE');
const unsavedChanges = computed(() => `${selected.value}:${fault.value}` !== savedSettings.value);
const storage = () => `fintax.reset.${session.user?.id}.${session.company?.id}`;
function remember() {
  uni.setStorageSync(storage(), { key: pendingKey.value, id: run.value?.id });
}
watch(data, (value) => {
  if (value) {
    selected.value = value.next_result;
    fault.value = value.declaration_fault || 'NONE';
    savedSettings.value = `${selected.value}:${fault.value}`;
  }
});
watch(
  () => session.epoch,
  () => {
    selected.value = 'SUCCESS';
    fault.value = 'NONE';
    savedSettings.value = 'SUCCESS:NONE';
    saveError.value = '';
    saved.value = false;
    run.value = null;
    pendingKey.value = '';
    confirm.value = false;
  }
);
onShow(async () => {
  if (!guard()) return;
  load();
  const existing = uni.getStorageSync(storage());
  if (existing?.key) {
    pendingKey.value = existing.key;
    if (existing.id) {
      try {
        await applyRun(await api.resetRun(existing.id));
      } catch (e) {
        resetError.value = errorMessage(e);
      }
    } else resetError.value = '上次恢复结果尚未确认，请查询恢复结果。';
  }
});
async function save() {
  if (saving.value) return;
  saving.value = true;
  saved.value = false;
  saveError.value = '';
  try {
    const result = await extension.settings(selected.value, fault.value);
    selected.value = result.next_result;
    fault.value = result.declaration_fault || 'NONE';
    savedSettings.value = `${selected.value}:${fault.value}`;
    saved.value = true;
  } catch (e) {
    if (!(e instanceof StaleResponse)) saveError.value = errorMessage(e);
  } finally {
    saving.value = false;
  }
}
async function applyRun(result: ResetRun) {
  run.value = result;
  remember();
  if (result.status === 'SUCCESS') {
    uni.removeStorageSync(storage());
    confirm.value = false;
    invalidateContext();
    uni.showToast({ title: '当前企业数据已恢复', icon: 'none' });
    go('home');
  } else if (result.status === 'FAILED')
    resetError.value = result.message || '恢复失败，请重试恢复或重新查询状态';
}
async function restore() {
  if (resetBusy.value) return;
  resetBusy.value = true;
  resetError.value = '';
  if (!pendingKey.value) pendingKey.value = requestKey();
  remember();
  try {
    await applyRun(await api.reset(pendingKey.value));
    confirm.value = false;
  } catch (e) {
    if (!(e instanceof StaleResponse)) resetError.value = errorMessage(e);
  } finally {
    resetBusy.value = false;
  }
}
async function refresh() {
  if (resetBusy.value) return;
  if (!run.value || run.value.status === 'PROCESSING') {
    // The server resumes committed cleanup with the same idempotency key.
    await restore();
    return;
  }
  resetBusy.value = true;
  resetError.value = '';
  try {
    await applyRun(await api.resetRun(run.value.id));
  } catch (e) {
    if (!(e instanceof StaleResponse)) resetError.value = errorMessage(e);
  } finally {
    resetBusy.value = false;
  }
}
</script>
<template>
  <AppShell
    title="演示设置"
    fallback="mine"
    :unsaved-changes="unsavedChanges"
    :navigation-busy="saving || resetBusy"
  >
    <CompanyBar>
      <template #action>
        <button id="switch-company" class="ft-button text-button" @click="go('company')">
          切换企业 ›
        </button>
      </template>
    </CompanyBar>
    <text class="caption" style="display: block; margin-bottom: 16px">
      当前账号：{{ session.user?.username }}
    </text>
    <StatePanel :busy="busy" :error="error" @retry="load">
      <view class="card">
        <text class="section-title">下一次开票结果</text>
        <text class="muted">为当前企业选择一次演示场景</text>
        <view class="stack" style="margin-top: 16px">
          <button
            class="ft-button"
            v-for="item in ['SUCCESS', 'FAILED'] as const"
            :key="item"
            :class="['secondary', { 'selected-card': selected === item }]"
            :disabled="saving || !!pendingKey"
            :aria-pressed="selected === item"
            @click="
              selected = item;
              saved = false;
            "
          >
            {{ selected === item ? '◉' : '○' }} {{ item === 'SUCCESS' ? '模拟成功' : '模拟失败' }}
          </button>
        </view>
        <text class="notice" style="margin-top: 16px">
          仅下一次成功创建的申请生效，使用后恢复默认成功。取消、校验失败不会消费场景；已创建的申请不受更改影响。
        </text>
        <text class="section-title">下一次模拟申报</text>
        <view class="stack">
          <button
            v-for="item in [
              { v: 'NONE', t: '正常获取回执' },
              { v: 'RECEIPT_DISCONNECT', t: '提交后回执连接中断' }
            ] as const"
            :key="item.v"
            class="ft-button secondary"
            :class="{ 'selected-card': fault === item.v }"
            :aria-pressed="fault === item.v"
            :disabled="saving || !!pendingKey"
            @click="
              fault = item.v;
              saved = false;
            "
          >
            {{ item.t }}
          </button>
        </view>
        <text class="notice" style="margin-top: 16px">
          仅下次成功创建的申报任务使用。故障发生在提交后，恢复先核对原申报，再补取回执，不重复提交。
        </text>
        <text v-if="saveError" class="notice error" role="alert">{{ saveError }}</text>
        <text v-if="saved" class="notice" role="status">下次演示场景已保存</text>
        <button
          class="ft-button primary"
          :disabled="saving || !!pendingKey"
          :loading="saving"
          @click="save"
        >
          {{ saving ? '保存中…' : '保存下次演示场景' }}
        </button>
      </view>
    </StatePanel>
    <view class="card" style="border-color: #f2c9cd">
      <text class="section-title" style="color: var(--danger)">恢复演示数据</text>
      <text class="muted">
        恢复当前企业的初始样例，清除该企业新增申请、票据、导入、批次、对账、申报、任务事件和关联文件，并阻止旧任务回写。另一企业和其他账号不受影响。
      </text>
      <text v-if="resetError" class="notice error" style="margin-top: 16px" role="alert">
        {{ resetError }}
      </text>
      <text v-if="run && run.status !== 'FAILED'" class="notice" style="margin-top: 16px">
        恢复{{
          run.status === 'PENDING' ? '等待处理' : '处理中'
        }}，以服务端完成结果为准。可刷新查看进度。
      </text>
      <button
        v-if="pendingKey"
        class="ft-button secondary"
        style="margin-top: 16px"
        :disabled="resetBusy"
        :loading="resetBusy"
        @click="refresh"
      >
        查询恢复结果
      </button>
      <button
        class="ft-button danger"
        style="margin-top: 16px"
        :disabled="resetBusy || (!!pendingKey && run?.status !== 'FAILED')"
        @click="confirm = true"
      >
        {{ run?.status === 'FAILED' ? '重试恢复' : '恢复当前企业演示数据' }}
      </button>
    </view>
    <ModalSheet
      :open="confirm"
      title="确认恢复当前企业？"
      :busy="resetBusy"
      @close="confirm = false"
    >
      <text class="list-title">{{ session.company?.name }}</text>
      <text class="notice warning">
        将清除该企业新增的开票申请、票据、导入、批次、对账、申报、任务事件及关联文件，阻止旧任务回写，并重新生成最近三个月样例。此操作不能撤销。
      </text>
      <text class="caption">仅影响当前账号下的这家企业，不影响另一企业和其他账号。</text>
      <text v-if="resetError" class="notice error" role="alert">{{ resetError }}</text>
      <view class="button-row">
        <button class="ft-button secondary" :disabled="resetBusy" @click="confirm = false">
          取消
        </button>
        <button
          class="ft-button danger"
          :disabled="resetBusy"
          :loading="resetBusy"
          @click="restore"
        >
          {{ resetBusy ? '恢复中…' : '确认恢复' }}
        </button>
      </view>
    </ModalSheet>
  </AppShell>
</template>
