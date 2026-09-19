import { session, snapshot, isCurrent, clearSession } from '../stores/session';
import type { ApiErrorBody } from '../types/api';
export const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api').replace(
  /\/$/,
  ''
);
export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public fields: Record<string, string> = {},
    public status?: number
  ) {
    super(message);
  }
}
export class StaleResponse extends ApiError {
  constructor() {
    super('STALE_RESPONSE', '企业或登录状态已改变，请重新加载');
  }
}
export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT';
  data?: Record<string, unknown>;
  auth?: boolean;
  scoped?: boolean;
  headers?: Record<string, string>;
  responseType?: 'text' | 'arraybuffer';
}
export function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const context = snapshot();
  const auth = options.auth !== false;
  if (auth && !session.token) return Promise.reject(new ApiError('UNAUTHENTICATED', '请先登录'));
  if (options.scoped !== false && auth && !session.company)
    return Promise.reject(new ApiError('NO_COMPANY', '请先选择企业'));
  const data: Record<string, unknown> = {};
  const raw = {
    ...options.data,
    ...(auth && options.scoped !== false ? { company_id: context.companyId } : {})
  };
  for (const [key, value] of Object.entries(raw)) {
    if (value !== undefined && value !== null) data[key] = value;
  }
  return new Promise((resolve, reject) => {
    uni.request({
      url: API_BASE + path,
      method: options.method || 'GET',
      data,
      timeout: 15000,
      responseType: options.responseType || 'text',
      header: {
        'Content-Type': 'application/json',
        ...(auth ? { Authorization: `Bearer ${context.token}` } : {}),
        ...options.headers
      },
      success(res) {
        // Never let an old request expire a newer account or replace a newer company.
        if (!isCurrent(context)) {
          reject(new StaleResponse());
          return;
        }
        if (res.statusCode === 401 && auth) {
          clearSession();
          uni.reLaunch({ url: '/pages/login/index' });
        }
        if (res.statusCode < 200 || res.statusCode >= 300) {
          let error = res.data as ApiErrorBody;
          // Binary endpoints still return the standard JSON error body on non-2xx.
          // #ifdef H5
          if (options.responseType === 'arraybuffer' && res.data instanceof ArrayBuffer) {
            try {
              error = JSON.parse(new TextDecoder().decode(res.data));
            } catch {
              /* Fall back to HTTP status. */
            }
          }
          // #endif
          reject(
            new ApiError(
              error?.code || `HTTP_${res.statusCode}`,
              error?.message ||
                (res.statusCode === 401 ? '登录已失效，请重新登录' : '请求失败，请稍后重试'),
              error?.field_errors,
              res.statusCode
            )
          );
          return;
        }
        resolve(res.data as T);
      },
      fail() {
        reject(
          isCurrent(context)
            ? new ApiError('NETWORK', '连接失败，请检查网络后重试')
            : new StaleResponse()
        );
      }
    });
  });
}
export function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : '操作失败，请重试';
}
