import { API_BASE, request, ApiError, StaleResponse } from '../http/request';
import { snapshot, isCurrent, clearSession } from '../stores/session';
import type { ImportKind, ImportValidation, FileRef } from '../types/api';
export interface SelectedFile {
  name: string;
  path: string;
  size: number;
}
export function chooseCsv(): Promise<SelectedFile | null> {
  return new Promise((resolve, reject) => {
    const success = (res: { tempFiles: { name: string; path: string; size: number }[] }) => {
      const file = res.tempFiles[0];
      if (!file || !/\.csv$/i.test(file.name))
        return reject(new ApiError('FILE_TYPE', '请选择 UTF-8 CSV 文件，使用固定模板填写'));
      if (!file.size) return reject(new ApiError('EMPTY_FILE', '文件为空，请重新选择'));
      resolve(file);
    };
    const fail = (e: { errMsg: string }) =>
      /cancel/i.test(e.errMsg)
        ? resolve(null)
        : reject(new ApiError('FILE_READ', '文件无法读取，请重新选择 CSV 文件'));
    // #ifdef H5
    uni.chooseFile({
      count: 1,
      type: 'all',
      extension: ['.csv'],
      success: (res) => success(res as unknown as { tempFiles: SelectedFile[] }),
      fail
    });
    // #endif
    // #ifdef MP-WEIXIN
    uni.chooseMessageFile({ count: 1, type: 'file', extension: ['csv'], success, fail });
    // #endif
  });
}
export function uploadCsv(
  file: SelectedFile,
  kind: ImportKind,
  period: string | undefined,
  key: string
): Promise<ImportValidation> {
  const context = snapshot();
  if (!context.token || !context.companyId)
    return Promise.reject(new ApiError('NO_COMPANY', '请先选择企业'));
  return new Promise((resolve, reject) =>
    uni.uploadFile({
      url: API_BASE + '/imports',
      filePath: file.path,
      name: 'file',
      formData: { company_id: context.companyId!, kind, ...(period ? { period } : {}) },
      header: { Authorization: `Bearer ${context.token}`, 'Idempotency-Key': key },
      timeout: 30000,
      success(res) {
        if (!isCurrent(context)) return reject(new StaleResponse());
        if (res.statusCode === 401) {
          clearSession();
          uni.reLaunch({ url: '/pages/login/index' });
        }
        try {
          const body = JSON.parse(res.data);
          if (res.statusCode < 200 || res.statusCode >= 300)
            reject(
              new ApiError(
                body.code || 'UPLOAD_FAILED',
                body.message || '上传校验失败，请重试',
                body.field_errors,
                res.statusCode
              )
            );
          else resolve(body);
        } catch {
          reject(new ApiError('INVALID_RESPONSE', '校验响应无法读取，请重试'));
        }
      },
      fail: () =>
        reject(
          isCurrent(context)
            ? new ApiError('NETWORK', '上传校验失败，请检查网络后重试')
            : new StaleResponse()
        )
    })
  );
}
async function download(path: string, name: string, pdf = false) {
  // #ifdef H5
  const bytes = await request<ArrayBuffer>(path, { responseType: 'arraybuffer' });
  const url = URL.createObjectURL(
    new Blob([bytes], { type: pdf ? 'application/pdf' : 'text/csv;charset=utf-8' })
  );
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return;
  // #endif
  // #ifdef MP-WEIXIN
  const context = snapshot();
  await new Promise<void>((resolve, reject) =>
    uni.downloadFile({
      url: `${API_BASE}${path}?company_id=${encodeURIComponent(context.companyId || '')}`,
      header: { Authorization: `Bearer ${context.token}` },
      timeout: 30000,
      success(res) {
        if (!isCurrent(context)) return reject(new StaleResponse());
        if (res.statusCode === 401) {
          clearSession();
          uni.reLaunch({ url: '/pages/login/index' });
        }
        if (res.statusCode !== 200)
          return reject(new ApiError('FILE_UNAVAILABLE', '文件暂不可用，请稍后重试'));
        if (pdf)
          uni.openDocument({
            filePath: res.tempFilePath,
            fileType: 'pdf',
            showMenu: true,
            success: () => resolve(),
            fail: () => reject(new ApiError('FILE_OPEN', '文件无法打开，请重试'))
          });
        else
          uni.shareFileMessage({
            filePath: res.tempFilePath,
            fileName: name,
            success: () => resolve(),
            fail: (e) =>
              /cancel/i.test(e.errMsg)
                ? resolve()
                : /not support|不支持/i.test(e.errMsg)
                  ? copyDownloadedCsv(res.tempFilePath, context).then(resolve, reject)
                  : reject(new ApiError('FILE_SAVE', '文件无法导出，请重试'))
          });
      },
      fail: () =>
        reject(
          isCurrent(context) ? new ApiError('NETWORK', '文件下载失败，请重试') : new StaleResponse()
        )
    })
  );
  // #endif
}
// #ifdef MP-WEIXIN
async function copyDownloadedCsv(path: string, context: ReturnType<typeof snapshot>) {
  if (!isCurrent(context)) throw new StaleResponse();
  const content = await new Promise<string>((resolve, reject) =>
    uni.getFileSystemManager().readFile({
      filePath: path,
      encoding: 'utf8',
      success: (res) => resolve(String(res.data)),
      fail: () => reject(new ApiError('FILE_READ', '文件读取失败，请重新下载'))
    })
  );
  if (!isCurrent(context)) throw new StaleResponse();
  await new Promise<void>((resolve, reject) =>
    uni.showModal({
      title: 'CSV 文件已下载',
      content: '当前环境不支持转发文件。可复制完整内容，粘贴到文本文件并以 UTF-8 CSV 保存。',
      confirmText: '复制内容',
      cancelText: '取消',
      success: (answer) => {
        if (!isCurrent(context)) return reject(new StaleResponse());
        if (!answer.confirm) return resolve();
        uni.setClipboardData({
          data: content,
          success: () => resolve(),
          fail: () => reject(new ApiError('FILE_SAVE', '复制失败，请重新下载'))
        });
      },
      fail: () => reject(new ApiError('FILE_SAVE', '文件无法导出，请重试'))
    })
  );
}
// #endif
export const downloadTemplate = (kind: ImportKind) =>
  download(`/import-templates/${kind.toLowerCase()}`, `${kind.toLowerCase()}-template.csv`);
export function downloadFile(file: FileRef) {
  if (!file.ready)
    return Promise.reject(new ApiError('FILE_NOT_READY', '文件尚未就绪，请稍后刷新'));
  return download(
    `/files/${encodeURIComponent(file.id)}/content`,
    file.name,
    file.media_type === 'application/pdf'
  );
}
