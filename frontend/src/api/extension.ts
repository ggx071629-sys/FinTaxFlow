import { request } from '../http/request';
import type * as T from '../types/api';
const id = encodeURIComponent;
const post = <R>(path: string, data: Record<string, unknown>, key: string) =>
  request<R>(path, { method: 'POST', data, headers: { 'Idempotency-Key': key } });
export const extension = {
  overview: () => request<T.AutomationOverview>('/automation/overview'),
  import: (value: string) => request<T.ImportValidation>(`/imports/${id(value)}`),
  importRows: (value: string, filter: string, page = 1) =>
    request<T.PageResult<T.ImportRow>>(`/imports/${id(value)}/rows`, {
      data: { filter, page, page_size: 20 }
    }),
  batches: (page = 1) =>
    request<T.PageResult<T.Batch>>('/billing-batches', { data: { page, page_size: 20 } }),
  batch: (value: string) => request<T.Batch>(`/billing-batches/${id(value)}`),
  batchRows: (value: string, status: string, page = 1) =>
    request<T.PageResult<T.BatchRow>>(`/billing-batches/${id(value)}/rows`, {
      data: { status, page, page_size: 20 }
    }),
  createBatch: (import_id: string, key: string) =>
    post<T.Batch>('/billing-batches', { import_id, confirmed: true }, key),
  retryBatch: (value: string, key: string) =>
    post<T.Batch>(`/billing-batches/${id(value)}/retry`, { failed_only: true }, key),
  reconciliations: (period?: string) =>
    request<T.PageResult<T.Reconciliation>>('/reconciliations', {
      data: { period, page: 1, page_size: 1 }
    }),
  reconcile: (bank_import_id: string, ledger_import_id: string, period: string, key: string) =>
    post<T.Reconciliation>('/reconciliations', { bank_import_id, ledger_import_id, period }, key),
  reconciliation: (value: string) => request<T.Reconciliation>(`/reconciliations/${id(value)}`),
  reconciliationRows: (value: string, differences_only: boolean, page = 1) =>
    request<T.PageResult<T.ReconciliationRow>>(`/reconciliations/${id(value)}/rows`, {
      data: { differences_only, page, page_size: 20 }
    }),
  tasks: (kind: string, attention: boolean, page = 1) =>
    request<T.PageResult<T.AutomationTask>>('/automation/tasks', {
      data: { kind, attention, page, page_size: 20 }
    }),
  task: (value: string) => request<T.AutomationTask>(`/automation/tasks/${id(value)}`),
  declare: (input: T.DeclarationInput, key: string) =>
    post<T.AutomationTask>('/declarations', { ...input }, key),
  recover: (value: string, key: string) =>
    post<T.AutomationTask>(`/declarations/${id(value)}/recover`, { confirmed: true }, key),
  receipt: (value: string) => request<T.DeclarationReceipt>(`/declaration-receipts/${id(value)}`),
  settings: (
    next_result: T.DemoSettings['next_result'],
    declaration_fault: T.DemoSettings['declaration_fault']
  ) =>
    request<T.DemoSettings>('/demo/settings', {
      method: 'PUT',
      data: { next_result, declaration_fault }
    })
};
