"""Restore missing simulated invoice files from stored snapshots; never change DB rows."""
import argparse
import json
from pathlib import Path
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Invoice
from app.services.pdf import company_pdf_dir, write_invoice_pdf

parser = argparse.ArgumentParser()
parser.add_argument('--apply', action='store_true')
args = parser.parse_args()
missing = []
with SessionLocal() as db:
    invoices = db.scalars(select(Invoice).where(Invoice.pdf_available.is_(True))).all()
    for invoice in invoices:
        expected = company_pdf_dir(invoice.company_id) / f'{invoice.id}.pdf'
        if not invoice.pdf_path or Path(invoice.pdf_path) != expected:
            raise RuntimeError(f'Unexpected PDF path for invoice {invoice.id}')
        if not expected.is_file():
            missing.append(str(invoice.id))
            if args.apply:
                write_invoice_pdf(invoice)
    # Deliberately no commit: this command only reads existing business snapshots.
print(json.dumps({'apply': args.apply, 'available_rows': len(invoices), 'missing': missing,
                  'restored': len(missing) if args.apply else 0}, indent=2))
