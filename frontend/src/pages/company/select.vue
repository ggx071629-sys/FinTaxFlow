<script setup lang="ts">
import { ref } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import { api } from '../../api';
import { session, setCompany } from '../../stores/session';
import { useResource } from '../../composables/resource';
import { errorMessage } from '../../http/request';
import { go, guard } from '../../utils/navigation';
import AppShell from '../../components/AppShell.vue';
import StatePanel from '../../components/StatePanel.vue';
const { data, busy, error, load } = useResource(api.companies);
const selected = ref(''),
  switching = ref(false),
  switchError = ref('');
onShow(() => {
  if (guard(false)) {
    selected.value = session.company?.id || '';
    load();
  }
});
async function enter() {
  if (!selected.value || switching.value) return;
  switchError.value = '';
  switching.value = true;
  try {
    const company = await api.company(selected.value);
    setCompany(company);
    go('home');
  } catch (e) {
    switchError.value = errorMessage(e);
  } finally {
    switching.value = false;
  }
}
</script>
<template>
  <AppShell
    title="选择企业"
    :no-back="!session.company"
    :unsaved-changes="!!session.company && selected !== session.company.id"
    :navigation-busy="switching"
  >
    <text class="section-title">{{ session.user?.name }}，欢迎回来</text>
    <text class="muted">选择您要查看的企业工作台</text>
    <text class="notice" style="margin-top: 20px">
      企业记录独立管理。切换企业不会清除已有申请和票据。
    </text>
    <StatePanel
      :busy="busy"
      :error="error"
      :empty="data?.length === 0"
      empty-text="当前账号暂无可用企业，请联系项目管理员"
      @retry="load"
    >
      <button
        class="ft-button"
        v-for="company in data"
        :key="company.id"
        :disabled="switching"
        :class="['list-card', 'company-choice', { 'selected-card': selected === company.id }]"
        :aria-pressed="selected === company.id"
        @click="selected = company.id"
      >
        <view class="row between">
          <text class="caption">{{ company.service_status }}</text>
          <text class="company-selection-mark" :aria-hidden="selected !== company.id">
            ✓ 已选择
          </text>
        </view>
        <text class="company-name">{{ company.name }}</text>
        <text class="caption">演示信用代码 · {{ company.tax_id }}</text>
      </button>
    </StatePanel>
    <text v-if="switchError" class="notice error" role="alert">{{ switchError }}</text>
    <button
      class="ft-button primary"
      :disabled="!selected || busy || switching"
      :loading="switching"
      @click="enter"
    >
      {{ switching ? '正在切换企业…' : '进入工作台' }}
    </button>
  </AppShell>
</template>
