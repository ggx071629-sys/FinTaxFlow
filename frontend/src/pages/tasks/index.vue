<script setup lang="ts">
import { ref } from 'vue';
import { onShow, onReachBottom } from '@dcloudio/uni-app';
import { extension } from '../../api/extension';
import { usePaged } from '../../composables/paged';
import { go, guard } from '../../utils/navigation';
import { dateTime } from '../../utils/format';
import type { AutomationTask, PageResult } from '../../types/api';
import AppShell from '../../components/AppShell.vue';
import CompanyBar from '../../components/CompanyBar.vue';
import StatePanel from '../../components/StatePanel.vue';
import StatusBadge from '../../components/StatusBadge.vue';
const kind = ref(''),
  attention = ref(false);
const { items, meta, busy, error, load } = usePaged<AutomationTask, PageResult<AutomationTask>>(
  (page) => extension.tasks(kind.value, attention.value, page)
);
onShow(() => {
  if (guard()) load();
});
onReachBottom(() => load(false));
function filter(value: string) {
  kind.value = value;
  load();
}
function toggle() {
  attention.value = !attention.value;
  load();
}
</script>
<template>
  <AppShell title="自动化任务">
    <CompanyBar />
    <view class="segments">
      <button
        v-for="item in [
          { v: '', t: '全部' },
          { v: 'BILLING', t: '开票' },
          { v: 'RECONCILIATION', t: '对账' },
          { v: 'DECLARATION', t: '申报' }
        ]"
        :key="item.v"
        class="ft-button"
        :class="{ selected: kind === item.v }"
        @click="filter(item.v)"
      >
        {{ item.t }}
      </button>
    </view>
    <view class="row between">
      <text class="section-title">任务记录</text>
      <button class="ft-button text-button" :aria-pressed="attention" @click="toggle">
        {{ attention ? '显示全部状态' : '仅看需处理' }}
      </button>
    </view>
    <StatePanel
      :busy="busy && !items.length"
      :error="error"
      :empty="!busy && !items.length"
      :empty-text="
        attention ? '没有需要处理的任务' : '暂无自动化任务，导入清单或发起模拟申报后可在这里查看'
      "
      @retry="load()"
    >
      <button
        v-for="task in items"
        :key="task.id"
        class="ft-button list-card"
        @click="go('task', { id: task.id })"
      >
        <view class="row between wrap">
          <text class="caption">{{ task.number }}</text>
          <StatusBadge :status="task.status" />
        </view>
        <text class="list-title">{{ task.title }}</text>
        <text class="caption">
          共 {{ task.counts.total }} 项 · {{ task.counts.success }} 成功 ·
          {{ task.counts.failed }} 失败 · {{ task.counts.processing }} 处理中
        </text>
        <text v-if="task.failure_reason" class="error-text">{{ task.failure_reason }}</text>
        <text class="caption" style="display: block; margin-top: 8px">
          {{ dateTime(task.updated_at) }} · 查看任务与业务结果
        </text>
      </button>
    </StatePanel>
    <button
      v-if="meta && items.length < meta.total"
      class="ft-button secondary"
      :disabled="busy"
      @click="load(false)"
    >
      加载更多
    </button>
    <text v-if="meta" class="empty-foot">已显示 {{ items.length }} / {{ meta.total }} 条任务</text>
    <button class="ft-button secondary" @click="go('home')">返回工作台</button>
  </AppShell>
</template>
