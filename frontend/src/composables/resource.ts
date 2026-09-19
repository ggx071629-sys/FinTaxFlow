import { ref, shallowRef, onUnmounted, watch } from 'vue';
import { session } from '../stores/session';
import { errorMessage, StaleResponse } from '../http/request';
export function useResource<T>(loader: () => Promise<T>) {
  const data = shallowRef<T | null>(null),
    busy = ref(false),
    error = ref('');
  let generation = 0;
  const stop = watch(
    () => session.epoch,
    () => {
      generation++;
      data.value = null;
      error.value = '';
      busy.value = false;
    }
  );
  async function load() {
    const current = ++generation;
    busy.value = true;
    error.value = '';
    try {
      const result = await loader();
      if (current === generation) data.value = result;
    } catch (e) {
      if (current === generation && !(e instanceof StaleResponse)) error.value = errorMessage(e);
    } finally {
      if (current === generation) busy.value = false;
    }
  }
  onUnmounted(() => {
    generation++;
    stop();
  });
  return { data, busy, error, load };
}
