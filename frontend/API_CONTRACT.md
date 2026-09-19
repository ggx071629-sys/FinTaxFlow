# FinTaxFlow API 契约

类型定义入口为 [`src/types/api.ts`](src/types/api.ts)，请求为 [`src/api/index.ts`](src/api/index.ts)，通用错误为 [`src/http/request.ts`](src/http/request.ts)。此文补充 HTTP 和行为约定，不复制另一套字段定义。

## HTTP

- 开发 API 基址：`VITE_API_BASE_URL`，默认 `http://127.0.0.1:8000/api`。H5 后端需允许本地开发来源；小程序当前仅开发者工具本地调试。
- JSON API 直接返回类型中的对象/数组，不嵌套 `data` envelope；错误响应为 `{code,message,field_errors?}`，配合非 2xx 状态。
- 除登录外使用 `Authorization: Bearer <access_token>`；业务 GET 在 query、POST/PUT 在 JSON body 追加 `company_id`。后端仍必须授权校验，不信任客户端企业或对象 ID。
- 金额十进制字符串，最多两位小数；税率为 `"0.06"` 一类小数字符串；所有计算最终以后端十进制定点结果为准。
- 月份 `YYYY-MM`；日期筛选 `YYYY-MM-DD`。时间字段当前展示接口返回的本地时间部分；后端返回 Asia/Shanghai `+08:00` ISO 时间，避免 UTC 被误当本地。
- 页码从 1 起；分页对象 `{items,page,page_size,total}`。票据额外返回 `total_amount`，是**全部筛选结果**价税合计，不是当前页金额。
- 支持的枚举、字段和可选属性以 TypeScript 类型为准。列表详情均保留 `company_id`。

## 路由

| HTTP | 路径（均以 /api 为前缀） | 输入 / 输出类型 |
| --- | --- | --- |
| POST | /auth/login | username、password → LoginResponse |
| GET | /auth/profile | User |
| GET | /companies | Company[] |
| GET | /companies/{id} | Company；验证切换权限成功后前端才提交上下文 |
| GET | /dashboard | Dashboard；services/statistics/activities 分区可返回 error |
| GET | /invoices | InvoiceQuery + company_id → InvoicePage |
| GET | /invoices/{id} | company_id → Invoice |
| GET | /invoices/{id}/pdf | company_id + Bearer → application/pdf 二进制；未就绪/无权访问返回非 2xx |
| GET | /tax-filings | company_id、可选 period → TaxResponse |
| GET | /billing | company_id、status、page、page_size → PageResult<BillingTask> |
| POST | /billing | BillingInput + company_id + Idempotency-Key → BillingTask |
| GET | /billing/{id} | company_id → BillingTask |
| GET | /accounting/summary | company_id、可选 period → Accounting |
| GET | /demo/settings | company_id → DemoSettings |
| PUT | /demo/settings | company_id、next_result → DemoSettings |
| POST | /demo/reset | company_id、confirmed:true + Idempotency-Key → ResetRun |
| GET | /demo/resets/{id} | company_id → ResetRun |

## 具体行为

- `period` 缺省时由后端返回现有样例期间及当前选中期间；返回 `periods` 为企业现有三个月，不由前端生成或重置。报税和账务各自维护查询选择。
- `Dashboard` 不定义统一虚构完成百分比；三项服务返回真实聚合的 count/summary/status/updated_at。活动携带 `object_type` 与 `object_id`，税务活动可携带 period。
- 创建开票只接受数电普票/数电专票。税号采用 18 位大写字母或数字的演示格式；后端种子须一致。这不是实际资质核验。
- 购买方、项目、含税金额、税率、邮箱、备注来自表单；销售方由已授权企业确定。客户端复核用按分四舍五入；服务端返回最终分解。
- 同一表单不确定结果（网络/5xx）重试沿用同一个 Idempotency-Key 和输入快照，禁止自动生成第二笔。成功前端进入返回的任务 ID；状态不会由页面计时器推进。
- 原失败申请通过 `source_task_id` 创建新对象。返回来源及完整 `followup_task_ids`；原记录不覆盖。
- 成功任务返回 `invoice_id` / `invoice_number` / `completed_at`，对应票据的 PDF 必须已可读。普通票据通过 `pdf_available` 告知文件是否就绪。
- 演示设置仅由后端成功创建申请时原子消费；前端取消/校验不会发消费请求。
- 恢复以 ResetRun 状态为准，SUCCESS 才清客户端上下文并回首页；PENDING/PROCESSING 显示查询入口，FAILED 显示错误与重试。
- 恢复的 key / run ID 按账号+企业保存为本地操作引用，以便响应丢失或重开设置页后追查。相同 key 的 POST 应查询或安全续跑同一次恢复（含已失败操作），不可重复清除不同代次数据。
- 任一受认证请求的 401 清客户端身份；旧账号/企业请求的迟到 401 不影响新上下文。此客户端机制不代替服务器权限验证。

<a id="e1-contract"></a>
## 扩展接口契约

本节覆盖导入、批量开票、对账与模拟申报，TypeScript 字段见 `src/types/api.ts`，请求见 `src/api/extension.ts` / `src/utils/files.ts`。

| HTTP | 路径（/api） | 输入 → 输出 |
| --- | --- | --- |
| GET | /automation/overview | company_id → AutomationOverview，服务 object_id 对应批次/对账/申报任务 |
| GET | /import-templates/{billing\|bank\|ledger} | company_id → UTF-8 CSV 固定模板 |
| POST | /imports | multipart file、company_id、kind、可选 period + Idempotency-Key → ImportValidation |
| GET | /imports/{id} | company_id → ImportValidation |
| GET | /imports/{id}/rows | company_id、filter=ISSUES/VALID、page/page_size → PageResult<ImportRow> |
| GET / POST | /billing-batches | 分页查询 / import_id、confirmed:true、company_id + key → PageResult<Batch> / Batch |
| GET | /billing-batches/{id} | company_id → Batch |
| GET | /billing-batches/{id}/rows | status、page/page_size、company_id → PageResult<BatchRow> |
| POST | /billing-batches/{id}/retry | failed_only:true、company_id + key → 原 Batch（仅失败行创建关联新尝试） |
| GET / POST | /reconciliations | period 分页查询 / bank_import_id、ledger_import_id、period、company_id + key → PageResult<Reconciliation> / Reconciliation |
| GET | /reconciliations/{id} | company_id → Reconciliation |
| GET | /reconciliations/{id}/rows | differences_only、page/page_size、company_id → PageResult<ReconciliationRow> |
| GET | /automation/tasks | kind、attention、page/page_size、company_id → PageResult<AutomationTask> |
| GET | /automation/tasks/{id} | company_id → AutomationTask（3 种业务变体） |
| POST | /declarations | filing_id、period、tax_type=VAT、confirmed:true、company_id + key → AutomationTask |
| POST | /declarations/{id}/recover | confirmed:true、company_id + key → AutomationTask |
| GET | /declaration-receipts/{id} | company_id → DeclarationReceipt |
| GET | /files/{id}/content | company_id + Bearer → CSV/PDF 二进制 |
| PUT | /demo/settings | 原 next_result + declaration_fault=NONE/RECEIPT_DISCONNECT → DemoSettings |

- 上表所有 key 指 `Idempotency-Key`。同 key 同输入返回同对象；输入不一致返回 `IDEMPOTENCY_CONFLICT` (409)。未知网络结果/5xx 重试保留 key，不能通过换 key 绕过去重。客户端仅保存操作引用，服务器须实现幂等。
- 提交明确返回 409 `DUPLICATE_BUSINESS_NUMBER` / `IMPORT_NOT_SUBMITTABLE` / `IMPORT_PERIOD_MISMATCH` 时，本次创建已被拒绝，客户端清除该操作引用，允许修正输入后重新提交。`IDEMPOTENCY_CONFLICT`、`RESET_IN_PROGRESS`、未识别的 409 及 408/429 继续保留原 key；其中恢复检查早于幂等查询，不能据此推断原请求未受理。
- 批量开票 P15 在刷新或重新进入后，读取当前账号、当前企业的未确认操作引用并加载原 import_id。用户点击“查询或重试原提交”才沿用原输入和 key 重试；页面加载不自动提交。确认结果前禁止重新上传；原导入已清除等明确拒绝可解除等待状态。兼容已有 `{key,fingerprint}` 存储，不跨企业或账号恢复引用。
- 导入原始行号含表头偏移；计数 total=valid+errors+duplicates，三类互斥，valid_amount 仅含有效行。文件企业字段不得覆盖授权上下文。开票允许只提交有效行；对账每侧须全部有效且属于同企业、同期间、对应 kind。
- 批次计数是业务行数；attempt_task_ids 为原单笔 P09 开票申请 ID，重试不覆盖原失败尝试；成功行关联 invoice_id。批次任务 task_id 对应 P20。列表必须支持全部明细分页，不以设计稿代表行替代数据全集。
- 对账 missing 表示单侧 null，different 包括金额或方向差异；两侧保留 import_id/file_name/row_number/date/direction/amount，difference 可 null。差额不是税款或调整建议。
- TaxFiling 新增 tax_type/can_declare/declaration_task_id/receipt_id。只有 VAT 且服务端许可才显示发起按钮；已有任务直接进入查询。提交是否发生由 submitted/acceptance_number 表示，不能由 FAILED 推断尚未申报。
- WAITING_RECOVERY 唯一故障为表单提交后回执中断。恢复必须先核对企业、期间与业务标识，不二次提交，沿用原受理号、保留所有事件；恢复可返回 PROCESSING，前端只查询服务端状态。
- attention 包括 FAILED/PARTIAL_FAILED/WAITING_RECOVERY。任务/文件/来源 ID 均须后端授权。企业恢复继续用原 ResetRun，范围覆盖扩展对象并阻止旧 worker 回写。
- 文件 ready=false 显示未就绪且禁用；鉴权下载不在 URL 放登录 token。H5 下载文件，微信 CSV 导出/PDF 打开；开发者工具不支持CSV分享时，原生确认后复制实际下载文件内容。
- 错误沿用 `{code,message,field_errors?}`。约定 400 INVALID_TEMPLATE/INVALID_CSV/INVALID_INPUT、403 FORBIDDEN、404 NOT_FOUND、409 IDEMPOTENCY_CONFLICT/DUPLICATE_BUSINESS_NUMBER/IMPORT_NOT_SUBMITTABLE/IMPORT_PERIOD_MISMATCH/RESET_IN_PROGRESS、422 VALIDATION_FAILED、425 FILE_NOT_READY、503 SERVICE_UNAVAILABLE。可解析但存在问题行的 CSV 返回 200 校验结果；格式/读取失败返回非 2xx。前端显示服务端摘要与具体行问题，未知结果不宣称成功。

### X01 独立模拟站点

入口 `frontend/portal/index.html#token=<short-lived-run-token>`。token 为机器人后端签发的短期能力凭证，仅允许当前申报，服务端绑定身份/企业/期间/业务标识；不能用 URL company_id 切换企业。表单先 GET `/api/simulation-portal/context` → PortalContext；企业与期间只读。POST `/api/simulation-portal/declarations`，Bearer token、Idempotency-Key，JSON `{declaration_id,sales_amount,tax_amount}`，返回已受理记录；重复提交返回原受理结果。GET `/api/simulation-portal/declarations/{id}/receipt` 获取演示 PDF。同源挂载、无独立登录后台；表单以真实 HTTP 响应呈现受理号，不生成回执或执行 RPA。

### 业务行为补充

- X01 运行入口映射为 `/simulation-portal/index.html#token=<short-lived-run-token>`；挂载内容仍是 `frontend/portal/`。JWT 十分钟有效，专用 audience 绑定账号、企业、代次、期间、业务标识。普通登录 token 与站点 token 不能互换。
- 固定 CSV 使用规定的中文列名及列序，详见 `backend/samples/README.md`；支持 UTF-8/BOM，上传上限 5 MB，仅作本地小样例防护。错误字段名与 `ImportRow.fields` 使用类型契约中的英文键；保留原始字节、原字段、物理行号，问题 CSV 包含所有问题行。日期必须属于所选期间。
- 同 key 同输入可重取已有结果；同一导入以新 key 再建批次、同一对账输入组合、同企业代次/期间/VAT 再建申报均返回原业务对象。不同导入的已受理业务号返回 `DUPLICATE_BUSINESS_NUMBER`。查询不推动后台状态。
- 一次性 `next_result` 在批次中由首个实际创建的有效行消费，其余行正常创建；单笔既有规则保持。批次所属失败申请通过原批次重试，`POST /billing` 携带该申请 `source_task_id` 返回 `IMPORT_NOT_SUBMITTABLE`，避免独立重提绕过业务号唯一性。
- BillingTask可选`batch_id`由服务端真实批次尝试关系派生；P09批次失败显示“返回批次重试失败项”，普通单笔失败仍按原逻辑修改重提。仅重试失败行。
- `POST /declarations/{id}/recover`允许基础设施FAILED恢复，P20对带declaration_id的FAILED与WAITING_RECOVERY均提供恢复及确认。先查原受理，未受理才重新操作表单；恢复沿用原受理记录，避免重复提交。这是技术错误续跑，不增加第二种可选演示故障。
- 站点表单固定样例金额为销售额 `10000.00`、税额 `600.00`，服务端校验与该申报快照一致；这些值不是账务或真实税款计算。`submitted`、受理号和 `submission_count` 由数据库提供。
- 文件 `ready` 由数据库内容是否存在决定。扩展 CSV 和回执 PDF 经鉴权读取；机器人诊断截图不静态公开。恢复清除扩展数据与诊断文件，旧 token/旧任务不能写回。
