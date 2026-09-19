import { reactive } from 'vue';
import type { Company, User, LoginResponse } from '../types/api';
const storageKey = 'fintax.session.v1';
export const session = reactive({
  token: '',
  user: null as User | null,
  company: null as Company | null,
  epoch: 0
});
export function restoreSession() {
  try {
    const saved = uni.getStorageSync(storageKey);
    if (saved?.token && saved?.user) {
      session.token = saved.token;
      session.user = saved.user;
      session.company = saved.company ?? null;
    }
  } catch {
    /* An unavailable storage leaves the user signed out. */
  }
}
function persist() {
  uni.setStorageSync(storageKey, {
    token: session.token,
    user: session.user,
    company: session.company
  });
}
export function setLogin(value: LoginResponse) {
  session.epoch++;
  session.token = value.access_token;
  session.user = value.user;
  session.company = null;
  persist();
}
export function setCompany(company: Company) {
  session.epoch++;
  session.company = company;
  persist();
}
export function invalidateContext() {
  session.epoch++;
}
export function clearSession() {
  session.epoch++;
  session.token = '';
  session.user = null;
  session.company = null;
  uni.removeStorageSync(storageKey);
}
export function snapshot() {
  return { epoch: session.epoch, token: session.token, companyId: session.company?.id };
}
export function isCurrent(context: ReturnType<typeof snapshot>) {
  return (
    context.epoch === session.epoch &&
    context.token === session.token &&
    context.companyId === session.company?.id
  );
}
