// X01 presentation only. A server-created token binds company, period and business identity.
const $ = (id) => document.getElementById(id);
const token = new URLSearchParams(location.hash.slice(1)).get('token');
const base = '/api/simulation-portal';
let busy = false,
  context = null;
const error = (message) => {
  $('error').textContent = message;
  $('error').hidden = !message;
};
async function request(path, options = {}) {
  const response = await fetch(base + path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...options.headers
    }
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.message || '站点连接失败，请重试');
  }
  return response;
}
async function load() {
  error('');
  $('retry').hidden = true;
  if (!token) {
    $('loading').hidden = true;
    error('缺少申报访问凭证，请从已授权的申报任务进入。');
    return;
  }
  try {
    context = await (await request('/context')).json();
    $('company-name').textContent = context.company_name;
    $('tax-id').textContent = context.tax_id;
    $('period').textContent = context.period;
    $('business-number').textContent = context.business_number;
    $('sales').value = context.sample_sales;
    $('tax').value = context.sample_tax;
    const accepted = context.status === 'ACCEPTED';
    $('declaration-form').hidden = accepted;
    $('accepted').hidden = !accepted;
    $('acceptance-number').textContent = context.acceptance_number || '';
    $('receipt').disabled = !context.receipt_ready;
    $('receipt').textContent = context.receipt_ready ? '查看回执文件' : '回执尚未就绪';
  } catch (e) {
    error(e.message);
    $('retry').hidden = false;
  } finally {
    $('loading').hidden = true;
  }
}
$('declaration-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  if (busy || !context) return;
  let valid = true;
  for (const id of ['sales', 'tax']) {
    const ok = /^\d{1,10}(\.\d{1,2})?$/.test($(id).value.trim());
    $(id).setAttribute('aria-invalid', String(!ok));
    $(id + '-error').textContent = ok ? '' : '请输入不小于 0 的金额，最多两位小数';
    if (!ok) {
      if (valid) $(id).focus();
      valid = false;
    }
  }
  if (!valid) return;
  busy = true;
  $('submit').disabled = true;
  error('');
  const storage = `fintax.portal.${context.declaration_id}`;
  // Preserve input as an operation reference across ambiguous network failures.
  const pending = JSON.parse(sessionStorage.getItem(storage) || 'null') || {
    key: crypto.randomUUID(),
    sales_amount: $('sales').value.trim(),
    tax_amount: $('tax').value.trim()
  };
  if (
    pending.sales_amount !== $('sales').value.trim() ||
    pending.tax_amount !== $('tax').value.trim()
  ) {
    error('上次提交结果未确认，请保留原金额重试或刷新查询。');
    busy = false;
    $('submit').disabled = false;
    return;
  }
  sessionStorage.setItem(storage, JSON.stringify(pending));
  try {
    await request('/declarations', {
      method: 'POST',
      headers: { 'Idempotency-Key': pending.key },
      body: JSON.stringify({
        declaration_id: context.declaration_id,
        sales_amount: pending.sales_amount,
        tax_amount: pending.tax_amount
      })
    });
    sessionStorage.removeItem(storage);
    await load();
  } catch (e) {
    error(e.message + '。保留原输入重试或刷新查询已有受理记录。');
  } finally {
    busy = false;
    $('submit').disabled = false;
  }
});
$('receipt').addEventListener('click', async () => {
  if (!context?.receipt_ready) return;
  $('receipt').disabled = true;
  try {
    const response = await request(
      `/declarations/${encodeURIComponent(context.declaration_id)}/receipt`
    );
    const url = URL.createObjectURL(await response.blob());
    const a = document.createElement('a');
    a.href = url;
    a.download = '模拟申报回执.pdf';
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (e) {
    error(e.message);
  } finally {
    $('receipt').disabled = false;
  }
});
$('refresh').addEventListener('click', load);
$('retry').addEventListener('click', load);
load();
