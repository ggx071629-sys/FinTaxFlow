import { ref, shallowRef, watch, onUnmounted } from 'vue';
import { session } from '../stores/session';
import { errorMessage, StaleResponse } from '../http/request';
import type { PageResult } from '../types/api';
export function usePaged<T, R extends PageResult<T>>(fetchPage: (page: number) => Promise<R>) {
  const items = shallowRef<T[]>([]),
    meta = shallowRef<R | null>(null),
    busy = ref(false),
    error = ref(''),
    page = ref(0);
  let generation = 0;
  function clear() {
    generation++;
    items.value = [];
    meta.value = null;
    page.value = 0;
    busy.value = false;
    error.value = '';
  }
  watch(() => session.epoch, clear);
  async function load(reset = true) {
    if (!reset && (busy.value || items.value.length >= (meta.value?.total ?? 0))) return;
    const gen = ++generation;
    const next = reset ? 1 : page.value + 1;
    busy.value = true;
    error.value = '';
    if (reset) {
      items.value = [];
      meta.value = null;
      page.value = 0;
    }
    try {
      const response = await fetchPage(next);
      if (gen !== generation) return;
      meta.value = response;
      items.value = reset ? response.items : [...items.value, ...response.items];
      page.value = response.page;
    } catch (e) {
      if (gen === generation && !(e instanceof StaleResponse)) error.value = errorMessage(e);
    } finally {
      if (gen === generation) busy.value = false;
      uni.stopPullDownRefresh();
    }
  }
  onUnmounted(() => generation++);
  return { items, meta, busy, error, load };
}
