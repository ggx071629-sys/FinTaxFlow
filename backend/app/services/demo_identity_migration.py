"""One-shot, idempotent synthetic identity update; never seed/reset existing data."""
from collections import Counter
from sqlalchemy import select
from app.models import Company, Invoice, BillingTask, Declaration, FileAsset, ImportLine
from app.services.demo_identity import IDENTITIES, replace_identity
from app.services.pdf import write_invoice_pdf, company_pdf_dir
from app.services.declarations import render_receipt_pdf


def migrate_demo_identities(db, *, write_files=False):
    counts = Counter()
    allowed = {(n,t) for old,oid,n,t in IDENTITIES} | {(old,oid) for old,oid,n,t in IDENTITIES}
    companies = [c for c in db.scalars(select(Company)) if (c.name,c.tax_id) in allowed]
    for company in companies:
        renamed = replace_identity(company.name, company.tax_id)
        if renamed != (company.name,company.tax_id):
            company.name,company.tax_id = renamed
            counts['companies'] += 1
        for model in (Invoice, BillingTask):
            for row in db.scalars(select(model).where(model.company_id == company.id)):
                for prefix in ('buyer', 'seller') if model is Invoice else ('seller',):
                    name_key, id_key = f'{prefix}_name', f'{prefix}_tax_id'
                    old = (getattr(row,name_key),getattr(row,id_key))
                    new = replace_identity(*old)
                    if old != new:
                        setattr(row,name_key,new[0]);setattr(row,id_key,new[1])
                        counts[f'{model.__tablename__}_parties'] += 1
                if model is BillingTask:
                    snapshot = dict(row.input_snapshot)
                    old = (snapshot.get('buyer_name'),snapshot.get('buyer_tax_id'))
                    new = replace_identity(*old)
                    if old != new:
                        snapshot.update(buyer_name=new[0],buyer_tax_id=new[1])
                        row.input_snapshot = snapshot
                        counts['billing_snapshots'] += 1
                elif row.pdf_available and row.pdf_path and write_files:
                    # Keep the stored location and ID; replace contents atomically.
                    path = company_pdf_dir(row.company_id) / f"{row.id}.pdf"
                    if str(path) != row.pdf_path:
                        raise RuntimeError('Unexpected PDF path; abort migration')
                    write_invoice_pdf(row)
                    counts['invoice_pdfs'] += 1
        for line in db.scalars(select(ImportLine).where(ImportLine.company_id == company.id)):
            fields = dict(line.fields)
            old = (fields.get('buyer_name'), fields.get('buyer_tax_id'))
            new = replace_identity(*old)
            if new != old:
                fields.update(buyer_name=new[0], buyer_tax_id=new[1])
                line.fields = fields
                counts['import_display_fields'] += 1
        for dec in db.scalars(select(Declaration).where(Declaration.company_id == company.id)):
            if dec.receipt_file_id:
                file = db.get(FileAsset,dec.receipt_file_id)
                data = render_receipt_pdf(company,dec)
                if file.content != data:
                    file.content = data
                    counts['receipt_pdfs'] += 1
    db.flush()
    return dict(counts)
