from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorBody(BaseModel):
    code: str
    message: str
    field_errors: dict[str, str] | None = None


class UserOut(BaseModel):
    id: str
    username: str
    name: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    user: UserOut


class CompanyOut(BaseModel):
    id: str
    name: str
    tax_id: str
    service_status: str


class Party(BaseModel):
    name: str
    tax_id: str


class InvoiceOut(BaseModel):
    id: str
    company_id: str
    number: str
    invoice_type: str
    direction: str
    issued_at: str
    buyer: Party
    seller: Party
    item_name: str
    net_amount: str
    tax_amount: str
    total_amount: str
    tax_rate: str
    verification_status: str
    verification_note: str
    pdf_available: bool
    source_task_id: str | None = None


class PageResult(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int


class InvoicePage(PageResult[InvoiceOut]):
    total_amount: str


class BillingInput(BaseModel):
    invoice_type: Literal["DIGITAL_NORMAL", "DIGITAL_SPECIAL"]
    buyer_name: str
    buyer_tax_id: str
    item_name: str
    total_amount: str
    tax_rate: str
    email: str = ""
    remark: str = ""
    source_task_id: str | None = None
    company_id: str | None = None


class TimelineEvent(BaseModel):
    label: str
    status: str
    time: str | None = None
    note: str | None = None


class BillingTaskOut(BaseModel):
    id: str
    company_id: str
    number: str
    status: str
    input: dict
    seller: Party
    net_amount: str
    tax_amount: str
    total_amount: str
    tax_rate: str
    created_at: str
    completed_at: str | None = None
    failure_reason: str | None = None
    invoice_id: str | None = None
    invoice_number: str | None = None
    source_task_id: str | None = None
    followup_task_ids: list[str]
    events: list[TimelineEvent]


class ErrorInfo(BaseModel):
    code: str
    message: str


class Section(BaseModel, Generic[T]):
    data: T | None = None
    error: ErrorInfo | None = None


class Service(BaseModel):
    kind: Literal["invoice", "tax", "billing"]
    title: str
    status: str
    summary: str
    count: int
    updated_at: str


class ActivityOut(BaseModel):
    id: str
    title: str
    time: str
    object_type: Literal["invoice", "tax", "billing"]
    object_id: str
    period: str | None = None


class Statistics(BaseModel):
    input_amount: str
    output_amount: str
    pending_invoices: int


class DashboardOut(BaseModel):
    period: str
    services: Section[list[Service]]
    statistics: Section[Statistics]
    activities: Section[list[ActivityOut]]


class TaxFilingOut(BaseModel):
    id: str
    name: str
    period: str
    status: str
    updated_at: str
    failure_reason: str | None = None
    nodes: list[TimelineEvent]


class TaxResponse(BaseModel):
    period: str
    periods: list[str]
    summary: str
    items: list[TaxFilingOut]


class Trend(BaseModel):
    period: str
    income: str
    expense: str


class AccountingSummaryOut(BaseModel):
    income: str
    expense: str
    profit: str
    receivable: str
    payable: str


class AccountingOut(BaseModel):
    period: str
    periods: list[str]
    summary: AccountingSummaryOut | None
    trend: list[Trend]


class DemoSettingsOut(BaseModel):
    next_result: Literal["SUCCESS", "FAILED"]


class DemoSettingsIn(BaseModel):
    company_id: str
    next_result: Literal["SUCCESS", "FAILED"]
    declaration_fault: Literal["NONE", "RECEIPT_DISCONNECT"] | None = None


class ResetRequest(BaseModel):
    company_id: str
    confirmed: bool = False


class ResetRunOut(BaseModel):
    id: str
    status: Literal["PENDING", "PROCESSING", "SUCCESS", "FAILED"]
    message: str | None = None
