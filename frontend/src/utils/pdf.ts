import { API_BASE, request, ApiError, StaleResponse } from '../http/request';
import { snapshot, isCurrent, clearSession } from '../stores/session';
// #ifdef H5
export async function browserInvoicePdf(id: string): Promise<string> {
  const bytes = await request<ArrayBuffer>(`/invoices/${encodeURIComponent(id)}/pdf`, {
    responseType: 'arraybuffer'
  });
  const header = new TextDecoder().decode(bytes.slice(0, 5));
  if (header !== '%PDF-') throw new ApiError('INVALID_PDF', '文件内容不是有效 PDF，请稍后重试');
  return URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }));
}
// #endif
// #ifdef MP-WEIXIN
export function nativeInvoicePdf(id: string): Promise<string> {
  const context = snapshot();
  if (!context.token || !context.companyId)
    return Promise.reject(new ApiError('UNAUTHENTICATED', '请先登录并选择企业'));
  return new Promise((resolve, reject) =>
    uni.downloadFile({
      url: `${API_BASE}/invoices/${encodeURIComponent(id)}/pdf?company_id=${encodeURIComponent(context.companyId || '')}`,
      header: { Authorization: `Bearer ${context.token}` },
      timeout: 30000,
      success(res) {
        if (!isCurrent(context)) {
          reject(new StaleResponse());
          return;
        }
        if (res.statusCode === 401) {
          clearSession();
          uni.reLaunch({ url: '/pages/login/index' });
          reject(new ApiError('EXPIRED', '登录已失效，请重新登录'));
          return;
        }
        if (res.statusCode !== 200) {
          reject(new ApiError('PDF_UNAVAILABLE', '文件获取失败，请稍后重试'));
          return;
        }
        uni.openDocument({
          filePath: res.tempFilePath,
          fileType: 'pdf',
          showMenu: false,
          success: () => (isCurrent(context) ? resolve('native') : reject(new StaleResponse())),
          fail: () => reject(new ApiError('PDF_OPEN_FAILED', '文件无法打开，请重新加载'))
        });
      },
      fail: () =>
        reject(
          isCurrent(context)
            ? new ApiError('NETWORK', '文件加载失败，请检查网络后重试')
            : new StaleResponse()
        )
    })
  );
}
// #endif
export async function openInvoicePdf(id: string): Promise<string> {
  // #ifdef H5
  return browserInvoicePdf(id);
  // #endif
  // #ifdef MP-WEIXIN
  return nativeInvoicePdf(id);
  // #endif
}
export function releasePdf(url: string) {
  // #ifdef H5
  if (url.startsWith('blob:')) URL.revokeObjectURL(url);
  // #endif
}
