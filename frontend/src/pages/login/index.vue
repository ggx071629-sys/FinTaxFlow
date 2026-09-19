<script setup lang="ts">
import { inputValue } from '../../utils/forms';
import { ref } from 'vue';
import { api } from '../../api';
import { setLogin } from '../../stores/session';
import { errorMessage } from '../../http/request';
import { go } from '../../utils/navigation';
import AppShell from '../../components/AppShell.vue';
import ModalSheet from '../../components/ModalSheet.vue';
const username = ref(''),
  password = ref(''),
  visible = ref(false),
  busy = ref(false),
  error = ref(''),
  accounts = ref(false);
const cloudDeployment = import.meta.env.VITE_CLOUD_DEPLOYMENT === 'true';
const demos = [
  { username: 'demo_boss01', password: cloudDeployment ? '' : '123456', name: '李总', companies: '虚构演示企业 A / B' },
  { username: 'demo_boss02', password: cloudDeployment ? '' : '123456', name: '王总', companies: '虚构演示企业 C / D' }
];
function fillDemo(account: (typeof demos)[number]) {
  username.value = account.username;
  password.value = account.password;
  error.value = '';
  accounts.value = false;
}
async function login() {
  if (busy.value) return;
  error.value = '';
  if (!username.value.trim() || !password.value) {
    error.value = '请填写账号和密码';
    return;
  }
  busy.value = true;
  try {
    setLogin(await api.login(username.value.trim(), password.value));
    go('company');
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <AppShell title="FinTaxFlow" no-back>
    <view class="login-page">
      <view class="login-brand">
        <image class="brand-logo" src="/static/fintax_logo.jpg" mode="aspectFill" />
        <text class="brand-name">财税云</text>
        <text class="muted">企业老板专属的财税服务工作台</text>
      </view>
      <view class="card">
        <view class="field">
          <label for="username" class="field-label">管理账号</label>
          <input
            id="username"
            v-model="username"
            @blur="username = inputValue($event)"
            aria-label="管理账号"
            placeholder="请输入演示账号"
            :disabled="busy"
            maxlength="80"
          />
        </view>
        <view class="field">
          <label for="password" class="field-label">登录密码</label>
          <view class="password-row">
            <input
              id="password"
              v-model="password"
              @blur="password = inputValue($event)"
              aria-label="登录密码"
              :password="!visible"
              placeholder="请输入密码"
              :disabled="busy"
              maxlength="128"
              confirm-type="done"
              @confirm="
                password = inputValue($event);
                login();
              "
            />
            <button
              class="ft-button"
              :aria-label="visible ? '隐藏密码' : '显示密码'"
              @click="visible = !visible"
            >
              {{ visible ? '隐藏' : '显示' }}
            </button>
          </view>
        </view>
        <text v-if="error" class="notice error" role="alert">{{ error }}</text>
        <button class="ft-button primary" :disabled="busy" :loading="busy" @click="login">
          {{ busy ? '正在登录…' : '登录' }}
        </button>
        <button
          class="ft-button text-button"
          style="width: 100%; margin-top: 10px"
          @click="accounts = true"
        >
          查看演示账号 ›
        </button>
      </view>
      <text class="notice">
        这是财税服务演示环境。财税处理结果为模拟数据，发票文件不具有真实票据效力。
      </text>
    </view>
    <ModalSheet :open="accounts" title="演示账号说明" @close="accounts = false">
      <text class="notice">
        {{ cloudDeployment ? '选择账号后，请输入管理员提供的演示密码。账号之间的企业数据相互隔离。' : '以下为后端种子账号。填入后仍须通过密码校验，不能跳过登录。每个账号拥有独立的两家企业。' }}
      </text>
      <button
        v-for="account in demos"
        :key="account.username"
        class="ft-button list-card"
        style="margin-top: 12px; text-align: left"
        @click="fillDemo(account)"
      >
        <text class="list-title">{{ account.name }} · {{ account.username }}</text>
        <text class="caption">{{ cloudDeployment ? '请使用分配的密码' : '密码 123456' }} · {{ account.companies }}</text>
        <text class="caption">{{ cloudDeployment ? '点击填入账号，再输入密码登录' : '点击填入，仍需点登录完成校验' }}</text>
      </button>
      <button class="ft-button primary" style="margin-top: 20px" @click="accounts = false">
        知道了
      </button>
    </ModalSheet>
  </AppShell>
</template>
