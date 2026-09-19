import type { InvoiceType } from '../types/api';
export function money(value: string | undefined) {
  if (!value) return '0.00';
  const [whole, fraction = ''] = value.split('.');
  return whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',') + '.' + fraction.padEnd(2, '0').slice(0, 2);
}
export const invoiceTypes: Record<InvoiceType, string> = {
  DIGITAL_NORMAL: '数电普票',
  DIGITAL_SPECIAL: '数电专票',
  ELECTRONIC_NORMAL: '电子普票',
  ELECTRONIC_SPECIAL: '电子专票'
};
export const statusLabels: Record<string, string> = {
  PENDING: '待处理',
  PROCESSING: '处理中',
  SUCCESS: '模拟成功',
  FAILED: '模拟失败',
  VERIFIED: '模拟验真通过',
  COMPLETED: '模拟已完成',
  WAITING: '待处理',
  PARTIAL_FAILED: '部分失败',
  WAITING_RECOVERY: '等待恢复',
  MATCHED: '一致',
  DIFFERENT: '金额 / 方向差异',
  MISSING: '记录缺失'
};
export function dateTime(value?: string) {
  return value ? value.replace('T', ' ').replace(/(\.\d+)?(Z|[+-]\d{2}:\d{2})$/, '') : '—';
}
