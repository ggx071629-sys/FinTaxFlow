<script setup lang="ts">
import { ref } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import { api } from '../../api';
import { session, clearSession } from '../../stores/session';
import { useResource } from '../../composables/resource';
import { go, guard } from '../../utils/navigation';
import AppShell from '../../components/AppShell.vue';
import CompanyBar from '../../components/CompanyBar.vue';
import StatePanel from '../../components/StatePanel.vue';
import ModalSheet from '../../components/ModalSheet.vue';
const { data, busy, error, load } = useResource(api.profile);
const confirm = ref(false);
onShow(() => {
  if (guard()) load();
});
function logout() {
  clearSession();
  uni.reLaunch({ url: '/pages/login/index' });
}
</script>
<template>
  <AppShell title="我的" tab="mine">
    <view class="card">
      <StatePanel :busy="busy" :error="error" @retry="load">
        <view class="row">
          <image
            class="nav-logo"
            style="width: 54px; height: 54px; border-radius: 16px"
            src="/static/fintax_logo.jpg"
          />
          <view>
            <text class="section-title" style="margin: 0">
              {{ data?.name || session.user?.name }}
            </text>
            <text class="caption">演示账号 · {{ data?.username || session.user?.username }}</text>
          </view>
        </view>
      </StatePanel>
    </view>
    <CompanyBar hero>
      <template #action>
        <button id="switch-company" class="ft-button text-button" @click="go('company')">
          切换企业 ›
        </button>
      </template>
    </CompanyBar>
    <view class="card">
      <button class="ft-button menu-row" @click="go('company')">
        <text>我的企业</text>
        <text>›</text>
      </button>
      <button class="ft-button menu-row" @click="go('settings')">
        <text>演示设置</text>
        <text>›</text>
      </button>
      <button class="ft-button menu-row" disabled>
        <text>通知设置</text>
        <text class="caption">暂未开放</text>
      </button>
      <button class="ft-button menu-row" disabled>
        <text>联系客服</text>
        <text class="caption">暂未开放</text>
      </button>
      <button class="ft-button menu-row" @click="go('about')">
        <text>关于系统</text>
        <text>›</text>
      </button>
    </view>
    <button class="ft-button secondary" @click="confirm = true">退出登录</button>
    <text class="empty-foot">FinTaxFlow · Demo v0.1.0</text>
    <ModalSheet :open="confirm" title="退出当前账号？" @close="confirm = false">
      <text class="notice">退出仅清除本机登录状态。已保存的企业申请与票据将在重新登录后保留。</text>
      <view class="button-row">
        <button class="ft-button secondary" @click="confirm = false">取消</button>
        <button class="ft-button primary" @click="logout">确认退出</button>
      </view>
    </ModalSheet>
  </AppShell>
</template>
