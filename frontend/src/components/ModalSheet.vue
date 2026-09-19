<script setup lang="ts">
import { ref, watch, nextTick, onUnmounted } from 'vue';
// #ifdef H5
import { trapModalFocus } from '../utils/modal-focus';
// #endif
const props = defineProps<{ open: boolean; title: string; busy?: boolean }>();
const emit = defineEmits<{ close: [] }>();
const sheet = ref<HTMLElement | { $el: HTMLElement } | null>(null);
// H5 traps keyboard focus. Mini-program uses native focus/accessibility primitives.
// #ifdef H5
let release: (() => void) | undefined;
let generation = 0;
watch(
  () => props.open,
  async (open) => {
    const current = ++generation;
    release?.();
    release = undefined;
    if (!open) return;
    await nextTick();
    if (current !== generation || !props.open) return;
    const element = sheet.value instanceof HTMLElement ? sheet.value : sheet.value?.$el;
    if (element) release = trapModalFocus(element, () => !props.busy, () => emit('close'));
  },
  { immediate: true }
);
onUnmounted(() => {
  generation++;
  release?.();
});
// #endif
</script>
<template>
  <view v-if="open" class="modal-overlay" @click.self="!busy && $emit('close')">
    <view ref="sheet" class="modal-sheet" role="dialog" aria-modal="true" :aria-label="title" @click.stop>
      <view class="row between">
        <text class="section-title">{{ title }}</text>
        <button
          class="ft-button icon-button"
          :disabled="busy"
          aria-label="关闭弹层"
          @click="$emit('close')"
        >
          ×
        </button>
      </view>
      <scroll-view scroll-y class="modal-scroll"><slot /></scroll-view>
    </view>
  </view>
</template>
