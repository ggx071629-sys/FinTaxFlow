export type Money = string;
export type BillingStatus = 'PENDING' | 'PROCESSING' | 'SUCCESS' | 'FAILED';
export type InvoiceType =
  | 'DIGITAL_NORMAL'
  | 'DIGITAL_SPECIAL'
  | 'ELECTRONIC_NORMAL'
  | 'ELECTRONIC_SPECIAL';
export type VerifyStatus = 'PENDING' | 'VERIFIED' | 'FAILED';
export interface User {
  id: string;
  username: string;
  name: string;
}
export interface Company {
  id: string;
  name: string;
  tax_id: string;
  service_status: string;
}
export interface LoginResponse {
  access_token: string;
  user: User;
}
export interface PageResult<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}
export interface Amounts {
  net_amount: Money;
  tax_amount: Money;
  total_amount: Money;
  tax_rate: string;
}
export interface Party {
  name: string;
  tax_id: string;
}
export interface Invoice extends Amounts {
  id: string;
  company_id: string;
  number: string;
  invoice_type: InvoiceType;
  direction: 'INPUT' | 'OUTPUT';
  issued_at: string;
  buyer: Party;
  seller: Party;
  item_name: string;
  verification_status: VerifyStatus;
  verification_note: string;
  pdf_available: boolean;
  source_task_id?: string;
}
export interface InvoiceQuery {
  keyword?: string;
  direction?: string;
  date_from?: string;
  date_to?: string;
  invoice_type?: string;
  verification_status?: string;
  page?: number;
  page_size?: number;
}
export interface InvoicePage extends PageResult<Invoice> {
  total_amount: Money;
}
export interface BillingInput {
  invoice_type: 'DIGITAL_NORMAL' | 'DIGITAL_SPECIAL';
  buyer_name: string;
  buyer_tax_id: string;
  item_name: string;
  total_amount: Money;
  tax_rate: string;
  email: string;
  remark: string;
  source_task_id?: string;
}
export interface TimelineEvent {
  label: string;
  status: string;
  time?: string;
  note?: string;
}
export interface BillingTask extends Amounts {
  id: string;
  company_id: string;
  number: string;
  status: BillingStatus;
  input: BillingInput;
  seller: Party;
  created_at: string;
  completed_at?: string;
  failure_reason?: string;
  invoice_id?: string;
  invoice_number?: string;
  source_task_id?: string;
  followup_task_ids: string[];
  batch_id?: string;
  events: TimelineEvent[];
}
export interface Section<T> {
  data: T | null;
  error?: { code: string; message: string };
}
export interface Service {
  kind: 'invoice' | 'tax' | 'billing';
  title: string;
  status: string;
  summary: string;
  count: number;
  updated_at: string;
}
export interface Activity {
  id: string;
  title: string;
  time: string;
  object_type: 'invoice' | 'tax' | 'billing';
  object_id: string;
  period?: string;
}
export interface Dashboard {
  period: string;
  services: Section<Service[]>;
  statistics: Section<{ input_amount: Money; output_amount: Money; pending_invoices: number }>;
  activities: Section<Activity[]>;
}
export interface TaxFiling {
  id: string;
  name: string;
  period: string;
  status: string;
  updated_at: string;
  failure_reason?: string;
  nodes: TimelineEvent[];
  tax_type?: 'VAT' | 'OTHER';
  can_declare?: boolean;
  declaration_task_id?: string;
  receipt_id?: string;
}
export interface TaxResponse {
  period: string;
  periods: string[];
  summary: string;
  items: TaxFiling[];
}
export interface Trend {
  period: string;
  income: Money;
  expense: Money;
}
export interface Accounting {
  period: string;
  periods: string[];
  summary: null | {
    income: Money;
    expense: Money;
    profit: Money;
    receivable: Money;
    payable: Money;
  };
  trend: Trend[];
}
export interface DemoSettings {
  next_result: 'SUCCESS' | 'FAILED';
  declaration_fault?: 'NONE' | 'RECEIPT_DISCONNECT';
}
export interface ResetRun {
  id: string;
  status: 'PENDING' | 'PROCESSING' | 'SUCCESS' | 'FAILED';
  message?: string;
}
export interface ApiErrorBody {
  code: string;
  message: string;
  field_errors?: Record<string, string>;
}

// E1 extension contract. These are server results, never client-computed business records.
export type ImportKind = 'BILLING' | 'BANK' | 'LEDGER';
export interface FileRef {
  id: string;
  name: string;
  media_type: string;
  ready: boolean;
}
export interface ImportRow {
  row_number: number;
  business_number: string;
  status: 'VALID' | 'ERROR' | 'DUPLICATE';
  fields: Record<string, string>;
  issues: { field: string; message: string }[];
}
export interface ImportValidation {
  id: string;
  company_id: string;
  kind: ImportKind;
  period?: string;
  file_name: string;
  total: number;
  valid: number;
  errors: number;
  duplicates: number;
  valid_amount: Money;
  status: 'VALIDATED';
  issue_file?: FileRef;
  created_at: string;
}
export type AutomationStatus = BillingStatus | 'PARTIAL_FAILED' | 'WAITING_RECOVERY';
export interface Batch {
  id: string;
  company_id: string;
  number: string;
  name: string;
  import_id: string;
  task_id: string;
  status: AutomationStatus;
  total: number;
  success: number;
  failed: number;
  processing: number;
  total_amount: Money;
  created_at: string;
}
export interface BatchRow {
  id: string;
  row_number: number;
  business_number: string;
  buyer_name: string;
  invoice_type: BillingInput['invoice_type'];
  total_amount: Money;
  status: BillingStatus;
  billing_task_id: string;
  attempt_task_ids: string[];
  invoice_id?: string;
  failure_reason?: string;
}
export interface Reconciliation {
  id: string;
  company_id: string;
  number: string;
  period: string;
  status: BillingStatus;
  bank_import_id: string;
  ledger_import_id: string;
  bank_count: number;
  ledger_count: number;
  total: number;
  matched: number;
  different: number;
  missing: number;
  task_id: string;
  created_at: string;
}
export interface ReconciliationSource {
  import_id: string;
  file_name: string;
  row_number: number;
  transaction_date: string;
  counterparty: string;
  direction: 'IN' | 'OUT';
  amount: Money;
}
export interface ReconciliationRow {
  business_number: string;
  status: 'MATCHED' | 'DIFFERENT' | 'MISSING';
  reason: string;
  bank: ReconciliationSource | null;
  ledger: ReconciliationSource | null;
  difference: Money | null;
}
export type AutomationKind = 'BILLING' | 'RECONCILIATION' | 'DECLARATION';
export interface AutomationTask {
  id: string;
  company_id: string;
  number: string;
  title: string;
  kind: AutomationKind;
  status: AutomationStatus;
  period?: string;
  created_at: string;
  updated_at: string;
  counts: { total: number; success: number; failed: number; processing: number };
  sources: { label: string; import_id?: string; file_name?: string; row_number?: number }[];
  events: TimelineEvent[];
  batch_id?: string;
  reconciliation_id?: string;
  declaration_id?: string;
  receipt_id?: string;
  failure_reason?: string;
  submitted?: boolean;
  acceptance_number?: string;
  submission_count?: number;
  completed_steps?: number;
  total_steps?: number;
}
export interface DeclarationInput {
  filing_id: string;
  period: string;
  tax_type: 'VAT';
  confirmed: true;
}
export interface DeclarationReceipt {
  id: string;
  company_id: string;
  task_id: string;
  company_name: string;
  tax_id: string;
  period: string;
  tax_type: 'VAT';
  acceptance_number: string;
  accepted_at: string;
  file?: FileRef;
}
export interface AutomationOverview {
  attention_count: number;
  services: {
    kind: AutomationKind;
    title: string;
    summary: string;
    status: AutomationStatus;
    object_id?: string;
  }[];
}
// X01 is a separate browser form; its short-lived token is bound to a server-created run.
export interface PortalContext {
  company_name: string;
  tax_id: string;
  period: string;
  declaration_id: string;
  business_number: string;
  sample_sales: Money;
  sample_tax: Money;
  status: 'READY' | 'ACCEPTED';
  acceptance_number?: string;
  receipt_ready: boolean;
}
