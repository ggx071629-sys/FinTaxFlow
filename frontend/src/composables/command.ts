import { ref, shallowRef, watch } from 'vue';
import { session, snapshot, isCurrent } from '../stores/session';
import { ApiError, errorMessage, StaleResponse } from '../http/request';
import { requestKey } from '../utils/billing';
// These conflicts reject creation after checking the original idempotency key.
// Other conflicts (including reset-in-progress) do not establish its outcome.
const rejectedConflicts = new Set([
  'DUPLICATE_BUSINESS_NUMBER',
  'IMPORT_NOT_SUBMITTABLE',
  'IMPORT_PERIOD_MISMATCH'
]);
// Only an idempotency reference is persisted, never a fake business result.
export function useCommand<Input = unknown>(scope: string) {
  const busy = ref(false),
    error = ref('');
  const pending = shallowRef<Input | null>(null);
  const storageKey = () =>
    `fintax.operation.${session.user?.id}.${session.company?.id}.${scope}`;
  function refreshPending() {
    pending.value = null;
    if (!session.user || !session.company) return;
    const saved = uni.getStorageSync(storageKey());
    if (typeof saved?.key !== 'string' || !saved.key || typeof saved.fingerprint !== 'string')
      return;
    try {
      pending.value = JSON.parse(saved.fingerprint) as Input;
    } catch {
      // An unreadable reference must not silently authorize a new operation.
    }
  }
  refreshPending();
  watch(
    () => session.epoch,
    () => {
      error.value = '';
      busy.value = false;
      refreshPending();
    }
  );
  async function run<T>(
    identity: Input,
    action: (key: string) => Promise<T>
  ): Promise<T | undefined> {
    if (busy.value) return;
    const context = snapshot();
    const storage = `fintax.operation.${session.user?.id}.${context.companyId}.${scope}`;
    const fingerprint = JSON.stringify(identity);
    const previous = uni.getStorageSync(storage);
    if (previous?.fingerprint && previous.fingerprint !== fingerprint) {
      error.value = '上次操作结果尚未确认，请返回原输入重试，确认结果后再发起新操作。';
      return;
    }
    const key = previous?.key || requestKey();
    uni.setStorageSync(storage, { key, fingerprint });
    busy.value = true;
    error.value = '';
    try {
      const result = await action(key);
      if (!isCurrent(context)) return;
      uni.removeStorageSync(storage);
      return result;
    } catch (e) {
      if (isCurrent(context) && !(e instanceof StaleResponse)) {
        error.value = errorMessage(e);
        // Only a definitive rejection allows changing the input. Unknown outcomes retain the key.
        if (
          e instanceof ApiError &&
          e.status &&
          e.status >= 400 &&
          e.status < 500 &&
          (![408, 409, 429].includes(e.status) ||
            (e.status === 409 && rejectedConflicts.has(e.code)))
        )
          uni.removeStorageSync(storage);
      }
    } finally {
      if (isCurrent(context)) {
        busy.value = false;
        refreshPending();
      }
    }
  }
  return { busy, error, pending, refreshPending, run };
}
