from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_invoice, normalize_page, normalize_page_size, require_company
from app.core.errors import ApiError
from app.core.security import get_current_user
from app.db import get_db
from app.models import User
from app.serialize import invoice_out
from app.services import queries
from app.services.pdf import company_pdf_dir, write_invoice_pdf

router = APIRouter(tags=["invoices"])


@router.get("/invoices")
def list_invoices(
    company_id: str,
    keyword: str | None = None,
    direction: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    invoice_type: str | None = None,
    verification_status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return queries.list_invoices(
        db,
        require_company(db, user, company_id),
        keyword=keyword,
        direction=direction,
        date_from=date_from,
        date_to=date_to,
        invoice_type=invoice_type,
        verification_status=verification_status,
        page=normalize_page(page),
        page_size=normalize_page_size(page_size),
    )


@router.get("/invoices/{invoice_id}")
def invoice_detail(
    invoice_id: str,
    company_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = require_company(db, user, company_id)
    return invoice_out(get_invoice(db, company, invoice_id))


@router.get("/invoices/{invoice_id}/pdf")
def invoice_pdf(
    invoice_id: str,
    company_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = require_company(db, user, company_id)
    invoice = get_invoice(db, company, invoice_id)
    if not invoice.pdf_available or not invoice.pdf_path:
        raise ApiError(404, "PDF_UNAVAILABLE", "文件暂不可用，请稍后重试")
    path = Path(invoice.pdf_path)
    if not path.is_file():
        # Generated simulation artifacts can be recovered from the owned invoice snapshot.
        # Never regenerate an arbitrary path or mutate the invoice/business identity.
        if path != company_pdf_dir(invoice.company_id) / f"{invoice.id}.pdf":
            raise ApiError(404, "PDF_UNAVAILABLE", "文件暂不可用，请稍后重试")
        try:
            write_invoice_pdf(invoice)
        except OSError:
            raise ApiError(503, "PDF_UNAVAILABLE", "文件恢复暂未完成，请稍后重试") from None
    return FileResponse(path, media_type="application/pdf", filename=f"{invoice.number}.pdf")
