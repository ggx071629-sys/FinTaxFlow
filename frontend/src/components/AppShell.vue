<script lang="ts">
export default {
  options: { virtualHost: true, styleIsolation: 'shared' }
};
</script>
<script setup lang="ts">
import { ref } from 'vue';
// #ifdef H5
import { onMounted } from 'vue';
import { prepareWelcomeTarget } from '../welcome/runtime';
// #endif
import { back, go, type RouteName } from '../utils/navigation';
import Icon from './Icon.vue';
import ModalSheet from './ModalSheet.vue';
// #ifdef H5
onMounted(prepareWelcomeTarget);
// #endif
const props = defineProps<{
  title: string;
  tab?: 'home' | 'invoices' | 'mine';
  fallback?: RouteName;
  noBack?: boolean;
  unsavedChanges?: boolean;
  navigationBusy?: boolean;
}>();
const confirmHome = ref(false);
function returnHome() {
  if (props.navigationBusy) return;
  if (props.unsavedChanges) confirmHome.value = true;
  else go('home');
}
function discardAndReturnHome() {
  if (props.navigationBusy) return;
  confirmHome.value = false;
  go('home');
}
</script>
<template>
  <view class="app-shell" :class="{ 'has-tabs': tab }">
    <view class="app-nav">
      <button
        v-if="!tab && !noBack"
        class="ft-button icon-button"
        aria-label="返回"
        @click="back(fallback)"
      >
        <Icon name="back" />
      </button>
      <image v-else class="nav-logo" src="/static/fintax_logo.jpg" mode="aspectFill" />
      <text class="nav-title">{{ title }}</text>
      <text class="demo-badge">虚构演示</text>
    </view>
    <view class="page-content">
      <view class="demo-disclosure">
        <text>虚构数据，仅供功能演示，与任何真实企业无关。</text>
        <text>编号为测试标识，开票与申报均为模拟。请勿输入真实财税资料。</text>
      </view>
      <view v-if="tab !== 'home' && !noBack" class="page-home-navigation">
        <button
          class="ft-button home-button"
          :disabled="navigationBusy"
          aria-label="返回首页"
          @click="returnHome"
        >
          <Icon name="home" tone="active" />
          <text>返回首页</text>
        </button>
      </view>
      <slot />
    </view>
    <ModalSheet
      :open="confirmHome"
      title="放弃修改并返回首页？"
      :busy="navigationBusy"
      @close="confirmHome = false"
    >
      <text class="notice">本页尚未提交的修改和文件选择不会保留。</text>
      <view class="button-row">
        <button class="ft-button secondary" :disabled="navigationBusy" @click="confirmHome = false">
          继续编辑
        </button>
        <button class="ft-button primary" :disabled="navigationBusy" @click="discardAndReturnHome">
          放弃并返回首页
        </button>
      </view>
    </ModalSheet>
    <view v-if="tab" class="tabbar">
      <button
        class="ft-button"
        v-for="item in ['home', 'invoices', 'mine'] as const"
        :key="item"
        :class="{ active: item === tab }"
        :aria-label="{ home: '首页', invoices: '票据', mine: '我的' }[item]"
        @click="go(item)"
      >
        <Icon :name="item" :tone="item === tab ? 'active' : 'muted'" />
        <text>{{ { home: '首页', invoices: '票据', mine: '我的' }[item] }}</text>
      </button>
    </view>
  </view>
</template>

<style scoped>
.demo-disclosure { display: flex; flex-direction: column; gap: 4px; margin-bottom: 16px; padding: 12px 14px; background: #edf5f4; color: #24544e; border: 1px solid #c4ded8; border-radius: 12px; font-size: 13px; line-height: 1.6; overflow-wrap: anywhere; }
</style>
