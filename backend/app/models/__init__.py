from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(80))
    companies: Mapped[list[Company]] = relationship(
        secondary="user_companies", back_populates="users"
    )


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    tax_id: Mapped[str] = mapped_column(String(18))
    service_status: Mapped[str] = mapped_column(String(80))
    generation: Mapped[int] = mapped_column(Integer, default=1)
    seed_key: Mapped[str] = mapped_column(String(40))
    users: Mapped[list[User]] = relationship(
        secondary="user_companies", back_populates="companies"
    )


class UserCompany(Base):
    __tablename__ = "user_companies"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), primary_key=True)


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("number"), UniqueConstraint("source_task_id"))

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    generation: Mapped[int] = mapped_column(Integer, default=1)
    number: Mapped[str] = mapped_column(String(32))
    invoice_type: Mapped[str] = mapped_column(String(32))
    direction: Mapped[str] = mapped_column(String(16), index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    buyer_name: Mapped[str] = mapped_column(String(200))
    buyer_tax_id: Mapped[str] = mapped_column(String(18))
    seller_name: Mapped[str] = mapped_column(String(200))
    seller_tax_id: Mapped[str] = mapped_column(String(18))
    item_name: Mapped[str] = mapped_column(String(200))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    tax_rate: Mapped[str] = mapped_column(String(8))
    verification_status: Mapped[str] = mapped_column(String(16), index=True)
    verification_note: Mapped[str] = mapped_column(Text, default="")
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pdf_available: Mapped[bool] = mapped_column(Boolean, default=False)
    source_task_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("billing_tasks.id"), nullable=True
    )


class TaxFiling(Base):
    __tablename__ = "tax_filings"
    __table_args__ = (UniqueConstraint("company_id", "period", "name"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    period: Mapped[str] = mapped_column(String(7), index=True)
    status: Mapped[str] = mapped_column(String(16))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    nodes: Mapped[list] = mapped_column(JSONB, default=list)


class BillingTask(Base):
    __tablename__ = "billing_tasks"
    __table_args__ = (UniqueConstraint("number"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    generation: Mapped[int] = mapped_column(Integer, default=1)
    number: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), index=True)
    input_snapshot: Mapped[dict] = mapped_column(JSONB)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    tax_rate: Mapped[str] = mapped_column(String(8))
    seller_name: Mapped[str] = mapped_column(String(200))
    seller_tax_id: Mapped[str] = mapped_column(String(18))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_task_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("billing_tasks.id"), nullable=True
    )
    bound_result: Mapped[str] = mapped_column(String(16), default="SUCCESS")
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    events: Mapped[list[BillingEvent]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="BillingEvent.sort",
    )


class BillingEvent(Base):
    __tablename__ = "billing_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("billing_tasks.id"), index=True)
    label: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(16))
    time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    task: Mapped[BillingTask] = relationship(back_populates="events")


class AccountingSummary(Base):
    __tablename__ = "accounting_summaries"
    __table_args__ = (UniqueConstraint("company_id", "period"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    income: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    expense: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    profit: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    receivable: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    payable: Mapped[Decimal] = mapped_column(Numeric(14, 2))


class DemoSetting(Base):
    __tablename__ = "demo_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), primary_key=True)
    next_result: Mapped[str] = mapped_column(String(16), default="SUCCESS")
    declaration_fault: Mapped[str] = mapped_column(String(32), default="NONE", server_default="NONE")


class ResetRun(Base):
    __tablename__ = "reset_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("user_id", "company_id", "operation", "key"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"))
    operation: Mapped[str] = mapped_column(String(40))
    key: Mapped[str] = mapped_column(String(120))
    request_hash: Mapped[str] = mapped_column(String(64))
    object_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    object_type: Mapped[str] = mapped_column(String(16))
    object_id: Mapped[str] = mapped_column(String(64))
    period: Mapped[str | None] = mapped_column(String(7), nullable=True)

# Register extension metadata for migrations and isolated tests.
from app.models.extension import (FileAsset, ImportRecord, ImportLine, AutomationTask,
    BillingBatch, BatchLine, BatchAttempt, Reconciliation, Declaration)  # noqa: E402,F401
