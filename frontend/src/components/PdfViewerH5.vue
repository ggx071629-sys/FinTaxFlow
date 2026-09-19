<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue';
import type { PDFDocumentLoadingTask, PDFDocumentProxy, RenderTask } from 'pdfjs-dist';
import { version } from 'pdfjs-dist/package.json';
const props = defineProps<{ src: string }>();
const host = ref<HTMLDivElement>();
const pageNumber = ref(1), pageCount = ref(0), zoom = ref(1), busy = ref(true), error = ref(''), pageText = ref('');
let loading: PDFDocumentLoadingTask | undefined;
let document: PDFDocumentProxy | undefined;
let rendering: RenderTask | undefined;
let run = 0, drawing = 0, disposed = false;
let observer: ResizeObserver | undefined;
let resizeTimer: ReturnType<typeof setTimeout> | undefined;
function reset() {
  ++run; ++drawing;
  rendering?.cancel(); rendering = undefined;
  void loading?.destroy().catch(() => {}); loading = undefined; document = undefined;
  host.value?.replaceChildren(); pageText.value = ''; pageCount.value = 0;
}
async function draw() {
  const pdf = document, target = host.value;
  if (!pdf || !target || disposed) return;
  const current = ++drawing;
  rendering?.cancel();
  busy.value = true; error.value = '';
  try {
    const page = await pdf.getPage(pageNumber.value);
    if (current !== drawing || disposed) return;
    const natural = page.getViewport({ scale: 1 });
    const scale = Math.max(1, target.clientWidth - 24) / natural.width * zoom.value;
    const viewport = page.getViewport({ scale });
    const density = Math.min(window.devicePixelRatio || 1, 2, Math.sqrt(8000000 / (viewport.width * viewport.height)));
    // Use a real DOM canvas; UniApp's canvas component is for native mini-program rendering.
    const canvas = window.document.createElement('canvas');
    canvas.width = Math.ceil(viewport.width * density); canvas.height = Math.ceil(viewport.height * density);
    canvas.style.width = `${viewport.width}px`; canvas.style.height = `${viewport.height}px`;
    canvas.style.display = 'block'; canvas.style.margin = '0 auto';
    canvas.setAttribute('role', 'img'); canvas.setAttribute('aria-label', `发票 PDF 第 ${pageNumber.value} 页`);
    rendering = page.render({ canvas, viewport, transform: [density, 0, 0, density, 0, 0] });
    await rendering.promise;
    const text = await page.getTextContent();
    if (current !== drawing || disposed) return;
    target.replaceChildren(canvas);
    pageText.value = text.items.map((item) => 'str' in item ? item.str : '').join(' ');
  } catch (e) {
    if (current === drawing && !disposed && (e as Error).name !== 'RenderingCancelledException') {
      error.value = 'PDF 预览加载失败，请重试或下载查看。';
    }
  } finally {
    if (current === drawing && !disposed) busy.value = false;
  }
}
async function load() {
  reset(); const current = run;
  busy.value = true; error.value = ''; pageNumber.value = 1; zoom.value = 1;
  try {
    const base = new URL(`/pdfjs/${version}/`, window.location.href).href;
    // Load the self-hosted legacy module directly: UniApp misnames vendor dynamic chunks.
    const pdfjs = await import(/* @vite-ignore */ base + 'pdf.js') as typeof import('pdfjs-dist');
    if (current !== run || disposed) return;
    pdfjs.GlobalWorkerOptions.workerSrc = base + 'pdf.worker.js';
    loading = pdfjs.getDocument({ url: props.src, cMapUrl: base + 'cmaps/', cMapPacked: true,
      standardFontDataUrl: base + 'standard_fonts/', wasmUrl: base + 'wasm/' });
    const pdf = await loading.promise;
    if (current !== run || disposed) return;
    document = pdf; pageCount.value = pdf.numPages;
    await draw();
  } catch {
    if (current === run && !disposed) { error.value = 'PDF 预览加载失败，请重试或下载查看。'; busy.value = false; }
  }
}
watch(() => props.src, load);
watch([pageNumber, zoom], draw);
onMounted(() => {
  void load();
  observer = new ResizeObserver(() => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => void draw(), 100); });
  if (host.value) observer.observe(host.value);
});
onBeforeUnmount(() => { disposed = true; reset(); observer?.disconnect(); clearTimeout(resizeTimer); });
</script>
<template>
  <view class="pdf-viewer">
    <view class="pdf-toolbar">
      <button class="ft-button secondary" aria-label="缩小 PDF" :disabled="busy || zoom <= 0.5" @click="zoom = Math.max(0.5, zoom - 0.25)">−</button>
      <text>{{ Math.round(zoom * 100) }}%</text>
      <button class="ft-button secondary" aria-label="放大 PDF" :disabled="busy || zoom >= 2" @click="zoom = Math.min(2, zoom + 0.25)">＋</button>
      <button class="ft-button text-button" :disabled="busy || zoom === 1" @click="zoom = 1">适合宽度</button>
    </view>
    <view v-if="pageCount > 1" class="pdf-toolbar">
      <button class="ft-button secondary" :disabled="busy || pageNumber <= 1" @click="pageNumber--">上一页</button>
      <text>第 {{ pageNumber }} / {{ pageCount }} 页</text>
      <button class="ft-button secondary" :disabled="busy || pageNumber >= pageCount" @click="pageNumber++">下一页</button>
    </view>
    <text v-if="busy" class="notice" role="status">正在绘制 PDF…</text>
    <view v-if="error" class="notice warning" role="alert">
      <text>{{ error }}</text>
      <button class="ft-button secondary" @click="load">重试预览</button>
    </view>
    <div ref="host" class="pdf-canvas-host" :aria-busy="busy" />
    <view class="pdf-readable-text">{{ pageText }}</view>
    <text v-if="pageCount === 1 && !busy && !error" class="caption">第 1 / 1 页 · 可放大后拖动查看</text>
  </view>
</template>
<style scoped>
.pdf-viewer { margin: 12px 0; min-width: 0; }
.pdf-toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 10px 0; }
.pdf-toolbar .ft-button { width: auto; min-width: 44px; min-height: 44px; margin: 0; padding: 8px 12px; }
.pdf-canvas-host { width: 100%; min-height: 220px; max-height: 70vh; overflow: auto; padding: 12px; box-sizing: border-box; border: 1px solid #d6dfe9; border-radius: 12px; background: #edf1f5; }
.pdf-readable-text { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
</style>
