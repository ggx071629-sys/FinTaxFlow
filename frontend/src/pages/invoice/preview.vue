<script setup lang="ts">
import { ref, watch } from 'vue';
import { onLoad, onShow, onUnload } from '@dcloudio/uni-app';
import { api } from '../../api';
import { session, snapshot, isCurrent } from '../../stores/session';
import { go, guard } from '../../utils/navigation';
import { errorMessage, StaleResponse } from '../../http/request';
import { openInvoicePdf, releasePdf } from '../../utils/pdf';
import { money } from '../../utils/format';
import type { Invoice } from '../../types/api';
import AppShell from '../../components/AppShell.vue';
import CompanyBar from '../../components/CompanyBar.vue';
import StatePanel from '../../components/StatePanel.vue';
const id = ref(''),
  invoice = ref<Invoice | null>(null),
  busy = ref(false),
  error = ref(''),
  url = ref('');
let generation = 0;
onLoad((q) => (id.value = q?.id || ''));
onShow(() => {
  if (guard() && !url.value && !busy.value) load();
});
function clear() {
  generation++;
  releasePdf(url.value);
  url.value = '';
  invoice.value = null;
}
watch(() => session.epoch, clear);
onUnload(clear);
async function load() {
  if (busy.value) return;
  const current = ++generation,
    context = snapshot();
  releasePdf(url.value);
  url.value = '';
  busy.value = true;
  error.value = '';
  try {
    if (!id.value) throw new Error('缺少票据编号，请返回票据列表');
    const detail = await api.invoice(id.value);
    if (!detail.pdf_available) throw new Error('文件暂不可用，请稍后重新加载');
    invoice.value = detail;
    const result = await openInvoicePdf(id.value);
    if (current !== generation || !isCurrent(context)) {
      releasePdf(result);
      return;
    }
    url.value = result;
  } catch (e) {
    if (current === generation && !(e instanceof StaleResponse)) error.value = errorMessage(e);
  } finally {
    if (current === generation) busy.value = false;
  }
}
</script>
<template>
  <AppShell title="发票 PDF 预览" fallback="invoices">
    <CompanyBar>
      <template #action>
        <button id="switch-company" class="ft-button text-button" @click="go('company')">
          切换企业 ›
        </button>
      </template>
    </CompanyBar>
    <text class="notice warning">演示文件，非真实发票</text>
    <view v-if="invoice" class="card">
      <text class="list-title">发票 {{ invoice.number }}.pdf</text>
      <text class="caption">{{ invoice.seller.name }} → {{ invoice.buyer.name }}</text>
      <view class="detail-row">
        <text>{{ invoice.item_name }}</text>
        <text class="number">¥ {{ money(invoice.total_amount) }}</text>
      </view>
    </view>
    <StatePanel :busy="busy" :error="error" @retry="load">
      <template v-if="url">
        <!-- #ifdef H5 -->
        <view v-if="url !== 'native'" class="pdf-actions">
          <a class="ft-button secondary" :href="url" target="_blank" rel="noopener noreferrer">
            新窗口打开
          </a>
          <a
            class="ft-button secondary"
            :href="url"
            :download="`发票 ${invoice?.number || id}.pdf`"
          >
            下载 PDF
          </a>
        </view>
        <text class="notice">若预览为空白，可新窗口打开或下载查看。</text>
        <iframe
          v-if="url !== 'native'"
          :src="url"
          title="演示发票 PDF 文档，支持滚动和缩放"
          style="
            width: 100%;
            height: 65vh;
            border: 1px solid #d6dfe9;
            border-radius: 12px;
            background: white;
          "
        />
        <text class="caption" style="display: block; margin: 12px 0">
          使用文档查看器中的页码、滚动与缩放控件。
        </text>
        <!-- #endif -->
        <!-- #ifdef MP-WEIXIN -->
        <view class="card">
          <text class="section-title">文件已交给系统查看器</text>
          <text class="muted">可在查看器中滚动、缩放和查看页码。</text>
        </view>
        <!-- #endif -->
        <button class="ft-button secondary" @click="load">重新打开 PDF</button>
      </template>
    </StatePanel>
  </AppShell>
</template>
