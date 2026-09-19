import { session } from '../stores/session';
export const routes = {
  login: '/pages/login/index',
  company: '/pages/company/select',
  home: '/pages/home/index',
  invoices: '/pages/invoice/index',
  invoice: '/pages/invoice/detail',
  tax: '/pages/tax/progress',
  billing: '/pages/billing/index',
  create: '/pages/billing/create',
  result: '/pages/billing/result',
  accounting: '/pages/accounting/index',
  mine: '/pages/mine/index',
  settings: '/pages/demo/settings',
  preview: '/pages/invoice/preview',
  about: '/pages/about/index',
  billingImport: '/pages/billing/import',
  batch: '/pages/billing/batch',
  reconcile: '/pages/reconciliation/create',
  reconciliation: '/pages/reconciliation/result',
  tasks: '/pages/tasks/index',
  task: '/pages/tasks/detail',
  receipt: '/pages/tax/receipt'
} as const;
export type RouteName = keyof typeof routes;
export function go(name: RouteName, params: Record<string, string> = {}) {
  const query = Object.entries(params)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join('&');
  const url = routes[name] + (query ? '?' + query : '');
  if (['home', 'invoices', 'mine'].includes(name)) uni.reLaunch({ url });
  else uni.navigateTo({ url });
}
export function back(fallback: RouteName = 'home') {
  if (getCurrentPages().length > 1) uni.navigateBack();
  else go(fallback);
}
export function guard(company = true) {
  if (!session.token) {
    uni.reLaunch({ url: routes.login });
    return false;
  }
  if (company && !session.company) {
    uni.reLaunch({ url: routes.company });
    return false;
  }
  return true;
}
export function toast(title: string) {
  uni.showToast({ title, icon: 'none', duration: 2500 });
}
