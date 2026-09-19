import { request } from '../http/request';
import type * as T from '../types/api';
const id = (value: string) => encodeURIComponent(value);
export const api = {
  login: (username: string, password: string) =>
    request<T.LoginResponse>('/auth/login', {
      method: 'POST',
      auth: false,
      scoped: false,
      data: { username, password }
    }),
  profile: () => request<T.User>('/auth/profile', { scoped: false }),
  companies: () => request<T.Company[]>('/companies', { scoped: false }),
  company: (value: string) => request<T.Company>(`/companies/${id(value)}`, { scoped: false }),
  dashboard: () => request<T.Dashboard>('/dashboard'),
  invoices: (query: T.InvoiceQuery) => request<T.InvoicePage>('/invoices', { data: { ...query } }),
  invoice: (value: string) => request<T.Invoice>(`/invoices/${id(value)}`),
  taxes: (period?: string) =>
    request<T.TaxResponse>('/tax-filings', { data: period ? { period } : {} }),
  billing: (status?: string, page = 1) =>
    request<T.PageResult<T.BillingTask>>('/billing', {
      data: { status: status || undefined, page, page_size: 20 }
    }),
  task: (value: string) => request<T.BillingTask>(`/billing/${id(value)}`),
  createBilling: (input: T.BillingInput, key: string) =>
    request<T.BillingTask>('/billing', {
      method: 'POST',
      data: { ...input },
      headers: { 'Idempotency-Key': key }
    }),
  accounting: (period?: string) =>
    request<T.Accounting>('/accounting/summary', { data: period ? { period } : {} }),
  settings: () => request<T.DemoSettings>('/demo/settings'),
  saveSettings: (next_result: T.DemoSettings['next_result']) =>
    request<T.DemoSettings>('/demo/settings', { method: 'PUT', data: { next_result } }),
  reset: (key: string) =>
    request<T.ResetRun>('/demo/reset', {
      method: 'POST',
      data: { confirmed: true },
      headers: { 'Idempotency-Key': key }
    }),
  resetRun: (value: string) => request<T.ResetRun>(`/demo/resets/${id(value)}`)
};
