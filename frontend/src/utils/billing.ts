import type { BillingInput } from '../types/api';
export const rates = ['0', '0.01', '0.03', '0.06', '0.09', '0.13'];
export function validateBilling(form: BillingInput) {
  const errors: Record<string, string> = {};
  if (!form.buyer_name.trim()) errors.buyer_name = '请输入购买方名称';
  if (!/^[A-Z0-9]{18}$/.test(form.buyer_tax_id))
    errors.buyer_tax_id = '请输入 18 位大写字母或数字的演示税号';
  if (!form.item_name.trim()) errors.item_name = '请输入开票项目';
  if (!/^\d{1,10}(\.\d{1,2})?$/.test(form.total_amount) || Number(form.total_amount) <= 0)
    errors.total_amount = '请输入大于 0 的金额，最多两位小数、十位整数';
  if (!rates.includes(form.tax_rate)) errors.tax_rate = '请选择演示税率';
  if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
    errors.email = '请输入有效邮箱，或留空';
  return errors;
}
export function splitAmount(amount: string, rate: string) {
  if (!/^\d{1,10}(\.\d{1,2})?$/.test(amount) || !rates.includes(rate))
    return { net_amount: '0.00', tax_amount: '0.00', total_amount: '0.00' };
  const [whole, dec = ''] = amount.split('.');
  const cents = BigInt(whole) * 100n + BigInt(dec.padEnd(2, '0'));
  const rateUnits = BigInt(Math.round(Number(rate) * 10000));
  const denominator = 10000n + rateUnits;
  const net = (cents * 10000n + denominator / 2n) / denominator;
  const decimal = (v: bigint) => `${v / 100n}.${(v % 100n).toString().padStart(2, '0')}`;
  return {
    net_amount: decimal(net),
    tax_amount: decimal(cents - net),
    total_amount: decimal(cents)
  };
}
export function requestKey() {
  return `ftf-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
}
