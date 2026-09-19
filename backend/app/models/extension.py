"""E2 durable sources, business identities, attempts and automation records."""
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base


class Owned:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('companies.id'), index=True)
    generation: Mapped[int] = mapped_column(Integer)


class FileAsset(Owned, Base):
    __tablename__ = 'extension_files'
    name: Mapped[str] = mapped_column(String(255))
    media_type: Mapped[str] = mapped_column(String(80))
    content: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)


class ImportRecord(Owned, Base):
    __tablename__ = 'imports'
    kind: Mapped[str] = mapped_column(String(16))
    period: Mapped[str | None] = mapped_column(String(7))
    file_name: Mapped[str] = mapped_column(String(255))
    source_file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('extension_files.id'))
    issue_file_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('extension_files.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ImportLine(Owned, Base):
    __tablename__ = 'import_lines'
    __table_args__ = (UniqueConstraint('import_id', 'row_number'),)
    import_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('imports.id'), index=True)
    row_number: Mapped[int] = mapped_column(Integer)
    business_number: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16))
    raw_fields: Mapped[dict] = mapped_column(JSONB)
    fields: Mapped[dict] = mapped_column(JSONB)
    issues: Mapped[list] = mapped_column(JSONB)


class AutomationTask(Owned, Base):
    __tablename__ = 'automation_tasks'
    number: Mapped[str] = mapped_column(String(40), unique=True)
    kind: Mapped[str] = mapped_column(String(24), index=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    period: Mapped[str | None] = mapped_column(String(7))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    events: Mapped[list] = mapped_column(JSONB, default=list)
    failure_reason: Mapped[str | None] = mapped_column(String(500))


class BillingBatch(Owned, Base):
    __tablename__ = 'billing_batches'
    import_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('imports.id'), unique=True)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('automation_tasks.id'), unique=True)
    name: Mapped[str] = mapped_column(String(255))


class BatchLine(Owned, Base):
    __tablename__ = 'batch_lines'
    __table_args__ = (UniqueConstraint('company_id', 'generation', 'business_number'),)
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('billing_batches.id'), index=True)
    import_line_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('import_lines.id'), unique=True)
    business_number: Mapped[str] = mapped_column(String(200))


class BatchAttempt(Base):
    __tablename__ = 'batch_attempts'
    __table_args__ = (UniqueConstraint('line_id', 'position'),)
    billing_task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('billing_tasks.id'), primary_key=True)
    line_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('batch_lines.id'), index=True)
    position: Mapped[int] = mapped_column(Integer)


class Reconciliation(Owned, Base):
    __tablename__ = 'reconciliations'
    __table_args__ = (UniqueConstraint('bank_import_id', 'ledger_import_id'),)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('automation_tasks.id'), unique=True)
    bank_import_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('imports.id'))
    ledger_import_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('imports.id'))
    results: Mapped[list] = mapped_column(JSONB)


class Declaration(Owned, Base):
    __tablename__ = 'declarations'
    __table_args__ = (UniqueConstraint('company_id', 'generation', 'period', 'tax_type'),)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('automation_tasks.id'), unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    filing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tax_filings.id'), unique=True)
    period: Mapped[str] = mapped_column(String(7))
    tax_type: Mapped[str] = mapped_column(String(16), default='VAT')
    business_number: Mapped[str] = mapped_column(String(40), unique=True)
    sales_amount: Mapped[str] = mapped_column(String(32))
    tax_amount: Mapped[str] = mapped_column(String(32))
    fault: Mapped[str] = mapped_column(String(32), default='NONE')
    acceptance_number: Mapped[str | None] = mapped_column(String(40), unique=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submission_count: Mapped[int] = mapped_column(Integer, default=0)
    receipt_file_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('extension_files.id'))
