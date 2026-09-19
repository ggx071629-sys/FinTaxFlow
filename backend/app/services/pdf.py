from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

from app.core.config import get_settings
from app.models import Invoice
from app.serialize import money

FONT = "STSong-Light"
pdfmetrics.registerFont(UnicodeCIDFont(FONT))


def render_invoice_pdf(invoice: Invoice) -> bytes:
    buffer = BytesIO()
    page = canvas.Canvas(buffer, pagesize=A4, invariant=1)
    width, height = A4
    page.setTitle(f"演示发票 {invoice.number}")
    page.setFillGray(0.80)
    page.saveState()
    page.translate(width / 2, height / 2)
    page.rotate(32)
    page.setFont(FONT, 28)
    page.drawCentredString(0, 0, "虚构演示 · 非真实发票")
    page.restoreState()
    page.setFillGray(0)
    page.setFont(FONT, 18)
    page.drawCentredString(width / 2, height - 28 * mm, "电子发票（演示）")
    page.setFont(FONT, 11)
    page.drawCentredString(width / 2, height - 36 * mm, "演示文件，非真实发票 · 不具有票据效力")
    page.setFont(FONT, 10)
    page.drawCentredString(width / 2, height - 43 * mm, "虚构数据，仅供功能演示，与任何真实企业无关")
    y = height - 56 * mm
    lines = [
        f"发票号码：{invoice.number}",
        f"开票日期：{invoice.issued_at.strftime('%Y-%m-%d')}",
        f"发票类型：{invoice.invoice_type}　方向：{invoice.direction}",
        f"购买方：{invoice.buyer_name}",
        f"购买方测试编号：{invoice.buyer_tax_id}",
        f"销售方：{invoice.seller_name}",
        f"销售方测试编号：{invoice.seller_tax_id}",
        f"项目名称：{invoice.item_name}",
        f"税率：{invoice.tax_rate}",
        f"不含税金额：{money(invoice.net_amount)} 元",
        f"税额：{money(invoice.tax_amount)} 元",
        f"价税合计：{money(invoice.total_amount)} 元",
        f"模拟验真：{invoice.verification_status}",
        invoice.verification_note,
        "本文件由 FinTaxFlow 演示环境生成，未进行电子签名、防伪认证或真实开票。",
        "邮箱仅保存、不发送。品牌图形不代表真实印章。",
    ]
    for line in lines:
        page.drawString(22 * mm, y, line)
        y -= 9 * mm
    page.showPage()
    page.save()
    return buffer.getvalue()


def write_invoice_pdf(invoice: Invoice) -> Path:
    settings = get_settings()
    folder = settings.pdf_dir / str(invoice.company_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{invoice.id}.pdf"
    data = render_invoice_pdf(invoice)
    if not data.startswith(b"%PDF-"):
        raise RuntimeError("generated file is not a PDF")
    with NamedTemporaryFile(dir=folder, prefix=f".{invoice.id}-", suffix=".tmp", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(data)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def company_pdf_dir(company_id) -> Path:
    return get_settings().pdf_dir / str(company_id)
