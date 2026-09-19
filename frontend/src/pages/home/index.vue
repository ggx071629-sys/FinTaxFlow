<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app';
import { api } from '../../api';
import { extension } from '../../api/extension';
import StatusBadge from '../../components/StatusBadge.vue';
import type { AutomationOverview } from '../../types/api';
import { useResource } from '../../composables/resource';
import { go, guard, type RouteName } from '../../utils/navigation';
import { money, dateTime } from '../../utils/format';
import type { Activity } from '../../types/api';
import AppShell from '../../components/AppShell.vue';
import CompanyBar from '../../components/CompanyBar.vue';
import StatePanel from '../../components/StatePanel.vue';
import Icon from '../../components/Icon.vue';
const { data, busy, error, load } = useResource(api.dashboard);
const automation = useResource(extension.overview);
function openService(service: AutomationOverview['services'][number]) {
  if (service.object_id)
    go(
      service.kind === 'BILLING'
        ? 'batch'
        : service.kind === 'RECONCILIATION'
          ? 'reconciliation'
          : 'task',
      { id: service.object_id }
    );
  else
    go(
      service.kind === 'BILLING'
        ? 'billingImport'
        : service.kind === 'RECONCILIATION'
          ? 'reconcile'
          : 'tax'
    );
}
onShow(() => {
  if (guard()) {
    load();
    automation.load();
  }
});
const serviceRoutes: Record<string, RouteName> = {
  invoice: 'invoices',
  tax: 'tax',
  billing: 'billing'
};
const shortcuts: { name: string; icon: string; route: RouteName }[] = [
  { name: '票据管理', icon: 'invoices', route: 'invoices' },
  { name: '报税进度', icon: 'tax', route: 'tax' },
  { name: '一键开票', icon: 'billing', route: 'billing' },
  { name: '账务查询', icon: 'accounting', route: 'accounting' }
];
function openActivity(a: Activity) {
  if (a.object_type === 'invoice') go('invoice', { id: a.object_id });
  else if (a.object_type === 'billing') go('result', { id: a.object_id });
  else go('tax', a.period ? { period: a.period } : {});
}
</script>
<template>
  <AppShell title="财税服务工作台" tab="home">
    <CompanyBar hero :period="data?.period">
      <template #action>
        <button id="switch-company" class="ft-button text-button" @click="go('company')">
          切换企业 ›
        </button>
      </template>
    </CompanyBar>
    <view class="row between">
      <text class="caption">
        {{
          automation.data.value
            ? `${automation.data.value.attention_count} 项任务需要关注`
            : '自动化任务与记录'
        }}
      </text>
      <button class="ft-button text-button" @click="go('tasks')">查看任务</button>
    </view>
    <StatePanel
      :busy="automation.busy.value"
      :error="automation.error.value"
      @retry="automation.load"
    >
      <view v-if="automation.data.value?.services.length" class="card service-card">
        <button
          v-for="service in automation.data.value.services"
          :key="service.kind"
          class="ft-button service-row"
          @click="openService(service)"
        >
          <view class="service-icon">
            <Icon
              :name="
                service.kind === 'BILLING'
                  ? 'billing'
                  : service.kind === 'RECONCILIATION'
                    ? 'accounting'
                    : 'tax'
              "
            />
          </view>
          <view class="grow">
            <text class="title">{{ service.title }}</text>
            <text class="summary">{{ service.summary }}</text>
          </view>
          <StatusBadge :status="service.status" />
        </button>
      </view>
    </StatePanel>
    <text class="section-title">本月服务核心进展</text>
    <StatePanel :busy="busy && !data" :error="error" @retry="load">
      <template v-if="data">
        <StatePanel
          :error="data.services.error?.message"
          :empty="data.services.data?.length === 0"
          empty-text="本月暂无服务进度"
          @retry="load"
        >
          <view class="card service-card">
            <button
              v-for="service in data.services.data"
              :key="service.kind"
              class="ft-button service-row"
              @click="go(serviceRoutes[service.kind])"
            >
              <view class="service-icon" :class="service.kind">
                <Icon :name="service.kind === 'invoice' ? 'invoices' : service.kind" />
              </view>
              <view class="grow">
                <view class="title">
                  <text>{{ service.title }}</text>
                  <text class="service-count">{{ service.count }}</text>
                </view>
                <text class="summary">{{ service.summary }}</text>
                <view class="service-meta">
                  <text>{{ service.status }}</text>
                  <text>{{ dateTime(service.updated_at) }}</text>
                </view>
              </view>
              <text class="muted">›</text>
            </button>
          </view>
        </StatePanel>
      </template>
    </StatePanel>
    <text class="section-title">常用服务</text>
    <view class="quick-grid">
      <button class="ft-button" v-for="item in shortcuts" :key="item.route" @click="go(item.route)">
        <view class="shortcut-icon" :class="item.icon"><Icon :name="item.icon" /></view>
        <text>{{ item.name }}</text>
      </button>
    </view>
    <template v-if="data">
      <view class="row between">
        <text class="section-title">本月票据概览</text>
        <text class="caption">价税合计 · 元</text>
      </view>
      <StatePanel :error="data.statistics.error?.message" @retry="load">
        <view v-if="data.statistics.data" class="card overview-card">
          <view class="metric-grid">
            <view
              class="metric"
              :class="{ 'metric-wide': money(data.statistics.data.input_amount).length > 10 }"
            >
              <text class="caption">本月进项</text>
              <text class="number">{{ money(data.statistics.data.input_amount) }}</text>
            </view>
            <view
              class="metric"
              :class="{ 'metric-wide': money(data.statistics.data.output_amount).length > 10 }"
            >
              <text class="caption">本月销项</text>
              <text class="number" style="color: var(--teal-dark)">
                {{ money(data.statistics.data.output_amount) }}
              </text>
            </view>
          </view>
          <view class="detail-row">
            <text>本月待处理票据</text>
            <text>{{ data.statistics.data.pending_invoices }} 张</text>
          </view>
        </view>
      </StatePanel>
      <text class="section-title">近期服务动态</text>
      <StatePanel
        :error="data.activities.error?.message"
        :empty="data.activities.data?.length === 0"
        empty-text="暂无服务动态，新的处理进度将在这里显示"
        @retry="load"
      >
        <view class="card activity-card">
          <button
            v-for="activity in data.activities.data"
            :key="activity.id"
            class="ft-button menu-row"
            @click="openActivity(activity)"
          >
            <view class="activity-dot" />
            <view class="grow">
              <text style="display: block">{{ activity.title }}</text>
              <text class="caption">{{ dateTime(activity.time) }}</text>
            </view>
            <text>›</text>
          </button>
        </view>
      </StatePanel>
    </template>
    <view class="card service-card">
      <button class="ft-button menu-row" style="padding: 14px" @click="go('tasks')">
        全部自动化任务
        <text>›</text>
      </button>
      <button class="ft-button menu-row" style="padding: 14px" @click="go('settings')">
        演示设置
        <text>›</text>
      </button>
    </view>
    <text class="empty-foot">财税处理结果为模拟 · 进度以已保存记录为准</text>
  </AppShell>
</template>
