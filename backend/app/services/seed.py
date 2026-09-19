from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.core.money import split_amount
from app.core.security import hash_password
from app.models import (
    AccountingSummary,
    Activity,
    BillingTask,
    Company,
    Invoice,
    TaxFiling,
    User,
    UserCompany,
)
from app.services.billing import add_event
from app.services.pdf import write_invoice_pdf

ACCOUNTS = [
    {
        "username": "demo_boss01",
        "password": "123456",
        "name": "李总",
        "companies": [
            {
                "seed_key": "xinghe",
                "name": "虚构演示企业 A",
                "tax_id": "DEMO00000000000001",
                "service_status": "代账专属服务进行中",
            },
            {
                "seed_key": "yuanhang",
                "name": "虚构演示企业 B",
                "tax_id": "DEMO00000000000002",
                "service_status": "服务进行中",
            },
        ],
    },
    {
        "username": "demo_boss02",
        "password": "123456",
        "name": "王总",
        "companies": [
            {
                "seed_key": "yuncheng",
                "name": "虚构演示企业 C",
                "tax_id": "DEMO00000000000003",
                "service_status": "代账专属服务进行中",
            },
            {
                "seed_key": "qingwu",
                "name": "虚构演示企业 D",
                "tax_id": "DEMO00000000000004",
                "service_status": "服务进行中",
            },
        ],
    },
]

COUNTERPARTIES = {
    "xinghe": [
        ("虚构演示企业 C", "DEMO00000000000003"),
        ("虚构演示交易方 01", "DEMO00000000000005"),
        ("虚构演示交易方 02", "DEMO00000000000006"),
    ],
    "yuanhang": [
        ("虚构演示交易方 03", "DEMO00000000000007"),
        ("虚构演示交易方 04", "DEMO00000000000008"),
        ("虚构演示交易方 05", "DEMO00000000000009"),
    ],
    "yuncheng": [
        ("虚构演示交易方 06", "DEMO00000000000010"),
        ("虚构演示交易方 07", "DEMO00000000000011"),
        ("虚构演示交易方 08", "DEMO00000000000012"),
    ],
    "qingwu": [
        ("虚构演示交易方 09", "DEMO00000000000013"),
        ("虚构演示交易方 10", "DEMO00000000000014"),
        ("虚构演示交易方 11", "DEMO00000000000015"),
    ],
}


ACCOUNTING = {
    "xinghe": [("380000.00", "218000.00", "56000.00", "23000.00"), ("325000.00", "210000.00", "48000.00", "21000.00"), ("290000.00", "180000.00", "41000.00", "19000.00")],
    "yuanhang": [("142000.00", "96000.00", "22000.00", "18000.00"), ("128000.00", "88000.00", "19000.00", "16000.00"), ("119000.00", "81000.00", "17000.00", "15000.00")],
    "yuncheng": [("210000.00", "132000.00", "35000.00", "14000.00"), ("198000.00", "121000.00", "31000.00", "12000.00"), ("176000.00", "110000.00", "28000.00", "11000.00")],
    "qingwu": [("86000.00", "54000.00", "12000.00", "9000.00"), ("79000.00", "51000.00", "11000.00", "8000.00"), ("72000.00", "47000.00", "10000.00", "7000.00")],
}


def _at(period: str, day: int, hour: int = 9, minute: int = 30) -> datetime:
    start = clock.period_start(period)
    return start.replace(day=min(day, 28), hour=hour, minute=minute, second=0, microsecond=0)


def _amounts(total: str, rate: str) -> dict[str, str]:
    return split_amount(total, rate)


def _tax_nodes(period: str, status: str, failed: bool = False) -> list[dict]:
    base = _at(period, 8, 10, 0)
    mid = _at(period, 15, 11, 0)
    end = _at(period, 18, 16, 30)
    if status == "COMPLETED":
        return [
            {"label": "资料归集", "status": "COMPLETED", "time": clock.iso(base)},
            {"label": "模拟申报", "status": "COMPLETED", "time": clock.iso(mid)},
            {"label": "结果确认", "status": "COMPLETED", "time": clock.iso(end)},
        ]
    if status == "FAILED":
        return [
            {"label": "资料归集", "status": "COMPLETED", "time": clock.iso(base)},
            {
                "label": "模拟申报",
                "status": "FAILED",
                "time": clock.iso(end),
                "note": "演示场景：资料核对未完成",
            },
        ]
    return [
        {"label": "资料归集", "status": "COMPLETED", "time": clock.iso(base)},
        {"label": "模拟申报", "status": "PROCESSING", "time": clock.iso(mid)},
    ]


def _invoice_specs(key: str, periods: list[str]) -> list[dict]:
    current, prev, older = periods
    buyers = COUNTERPARTIES[key]
    if key == "xinghe":
        return [
            {"period": current, "day": 18, "type": "DIGITAL_NORMAL", "dir": "OUTPUT", "total": "10000.00", "rate": "0.06", "item": "技术服务费", "verify": "VERIFIED", "party": buyers[0], "billing": True},
            {"period": current, "day": 16, "type": "DIGITAL_SPECIAL", "dir": "OUTPUT", "total": "28600.00", "rate": "0.06", "item": "软件实施服务", "verify": "VERIFIED", "party": buyers[1]},
            {"period": current, "day": 12, "type": "ELECTRONIC_NORMAL", "dir": "OUTPUT", "total": "8000.00", "rate": "0.06", "item": "运维服务费", "verify": "PENDING", "party": buyers[2]},
            {"period": current, "day": 10, "type": "DIGITAL_NORMAL", "dir": "INPUT", "total": "12500.00", "rate": "0.13", "item": "办公设备", "verify": "VERIFIED", "party": buyers[1]},
            {"period": current, "day": 9, "type": "ELECTRONIC_SPECIAL", "dir": "INPUT", "total": "3200.00", "rate": "0.13", "item": "耗材采购", "verify": "FAILED", "party": buyers[2]},
            {"period": current, "day": 6, "type": "DIGITAL_SPECIAL", "dir": "INPUT", "total": "5400.00", "rate": "0.06", "item": "云资源服务", "verify": "PENDING", "party": buyers[0]},
            {"period": prev, "day": 20, "type": "DIGITAL_NORMAL", "dir": "OUTPUT", "total": "15000.00", "rate": "0.06", "item": "咨询服务费", "verify": "VERIFIED", "party": buyers[0]},
            {"period": prev, "day": 11, "type": "ELECTRONIC_NORMAL", "dir": "INPUT", "total": "9000.00", "rate": "0.13", "item": "广告投放", "verify": "VERIFIED", "party": buyers[2]},
            {"period": older, "day": 22, "type": "ELECTRONIC_SPECIAL", "dir": "OUTPUT", "total": "12000.00", "rate": "0.06", "item": "项目验收款", "verify": "VERIFIED", "party": buyers[1]},
        ]
    if key == "yuanhang":
        return [
            {"period": current, "day": 17, "type": "DIGITAL_NORMAL", "dir": "OUTPUT", "total": "1800.00", "rate": "0.01", "item": "管理咨询", "verify": "VERIFIED", "party": buyers[0], "billing": True},
            {"period": current, "day": 14, "type": "DIGITAL_SPECIAL", "dir": "OUTPUT", "total": "2200.00", "rate": "0.06", "item": "培训服务", "verify": "VERIFIED", "party": buyers[1]},
            {"period": current, "day": 8, "type": "ELECTRONIC_NORMAL", "dir": "INPUT", "total": "88000.00", "rate": "0.13", "item": "仓储服务", "verify": "VERIFIED", "party": buyers[2]},
            {"period": current, "day": 5, "type": "ELECTRONIC_SPECIAL", "dir": "INPUT", "total": "15600.00", "rate": "0.09", "item": "物流费用", "verify": "VERIFIED", "party": buyers[0]},
            {"period": prev, "day": 19, "type": "DIGITAL_NORMAL", "dir": "INPUT", "total": "43000.00", "rate": "0.13", "item": "原材料", "verify": "PENDING", "party": buyers[1]},
            {"period": older, "day": 7, "type": "ELECTRONIC_NORMAL", "dir": "OUTPUT", "total": "3600.00", "rate": "0.03", "item": "信息服务", "verify": "VERIFIED", "party": buyers[2]},
        ]
    if key == "yuncheng":
        return [
            {"period": current, "day": 15, "type": "DIGITAL_SPECIAL", "dir": "OUTPUT", "total": "16800.00", "rate": "0.06", "item": "系统集成", "verify": "VERIFIED", "party": buyers[0], "billing": True},
            {"period": current, "day": 11, "type": "DIGITAL_NORMAL", "dir": "OUTPUT", "total": "4200.00", "rate": "0.06", "item": "驻场服务", "verify": "VERIFIED", "party": buyers[1]},
            {"period": current, "day": 4, "type": "ELECTRONIC_NORMAL", "dir": "INPUT", "total": "7600.00", "rate": "0.13", "item": "服务器租赁", "verify": "FAILED", "party": buyers[2]},
            {"period": prev, "day": 21, "type": "DIGITAL_NORMAL", "dir": "OUTPUT", "total": "9800.00", "rate": "0.06", "item": "接口开发", "verify": "VERIFIED", "party": buyers[0]},
            {"period": older, "day": 9, "type": "ELECTRONIC_SPECIAL", "dir": "INPUT", "total": "2100.00", "rate": "0.06", "item": "设计服务", "verify": "VERIFIED", "party": buyers[1]},
        ]
    return [
        {"period": current, "day": 13, "type": "DIGITAL_NORMAL", "dir": "OUTPUT", "total": "2600.00", "rate": "0.01", "item": "内容制作", "verify": "VERIFIED", "party": buyers[0], "billing": True},
        {"period": current, "day": 7, "type": "ELECTRONIC_NORMAL", "dir": "INPUT", "total": "11800.00", "rate": "0.13", "item": "场地租赁", "verify": "PENDING", "party": buyers[1]},
        {"period": prev, "day": 16, "type": "DIGITAL_SPECIAL", "dir": "OUTPUT", "total": "5100.00", "rate": "0.06", "item": "活动执行", "verify": "VERIFIED", "party": buyers[2]},
        {"period": older, "day": 3, "type": "ELECTRONIC_SPECIAL", "dir": "INPUT", "total": "1900.00", "rate": "0.06", "item": "印刷制作", "verify": "VERIFIED", "party": buyers[0]},
    ]


def _tax_status(key: str, index: int) -> str:
    layouts = {
        "xinghe": ["COMPLETED", "COMPLETED", "PROCESSING", "FAILED"],
        "yuanhang": ["PROCESSING", "COMPLETED", "FAILED", "COMPLETED"],
        "yuncheng": ["COMPLETED", "PROCESSING", "COMPLETED", "PROCESSING"],
        "qingwu": ["FAILED", "PROCESSING", "COMPLETED", "COMPLETED"],
    }
    return layouts[key][index]


def seed_company_data(db: Session, company: Company) -> None:
    periods = clock.last_three_periods()
    names = ["增值税", "企业所得税", "个人所得税", "印花税"]
    for period in periods:
        for index, name in enumerate(names):
            status = _tax_status(company.seed_key, index) if period == periods[0] else "COMPLETED"
            filing = TaxFiling(
                company_id=company.id,
                name=name,
                period=period,
                status=status,
                updated_at=_at(period, 18, 16, 30),
                failure_reason="资料核对未完成" if status == "FAILED" else None,
                nodes=_tax_nodes(period, status),
            )
            db.add(filing)
            if period == periods[0] and index == 0:
                db.add(
                    Activity(
                        company_id=company.id,
                        title=f"{name}进度更新",
                        time=filing.updated_at,
                        object_type="tax",
                        object_id="pending",
                        period=period,
                    )
                )
    db.flush()
    first_tax = db.scalar(
        select(TaxFiling).where(
            TaxFiling.company_id == company.id,
            TaxFiling.period == periods[0],
            TaxFiling.name == "增值税",
        )
    )
    if first_tax:
        activity = db.scalar(
            select(Activity).where(
                Activity.company_id == company.id,
                Activity.object_type == "tax",
                Activity.object_id == "pending",
            )
        )
        if activity:
            activity.object_id = str(first_tax.id)

    for offset, amounts in enumerate(ACCOUNTING[company.seed_key]):
        income, expense, receivable, payable = amounts
        db.add(
            AccountingSummary(
                company_id=company.id,
                period=periods[offset],
                income=Decimal(income),
                expense=Decimal(expense),
                profit=Decimal(income) - Decimal(expense),
                receivable=Decimal(receivable),
                payable=Decimal(payable),
            )
        )

    seq = 0
    for spec in _invoice_specs(company.seed_key, periods):
        seq += 1
        issued = _at(spec["period"], spec["day"], 9, 20 + seq)
        amounts = _amounts(spec["total"], spec["rate"])
        party_name, party_tax = spec["party"]
        output = spec["dir"] == "OUTPUT"
        buyer_name, buyer_tax = (party_name, party_tax) if output else (company.name, company.tax_id)
        seller_name, seller_tax = (company.name, company.tax_id) if output else (party_name, party_tax)
        task = None
        if spec.get("billing"):
            snapshot = {
                "invoice_type": spec["type"] if spec["type"] in ("DIGITAL_NORMAL", "DIGITAL_SPECIAL") else "DIGITAL_NORMAL",
                "buyer_name": buyer_name,
                "buyer_tax_id": buyer_tax,
                "item_name": spec["item"],
                "total_amount": amounts["total_amount"],
                "tax_rate": spec["rate"],
                "email": "finance@example.test",
                "remark": "种子样例申请",
            }
            created = issued.replace(minute=max(issued.minute - 8, 0))
            task = BillingTask(
                company_id=company.id,
                generation=company.generation,
                # Seed templates may be shared by multiple companies; identifiers are global.
                number=uuid4().hex,
                status="SUCCESS",
                input_snapshot=snapshot,
                net_amount=Decimal(amounts["net_amount"]),
                tax_amount=Decimal(amounts["tax_amount"]),
                total_amount=Decimal(amounts["total_amount"]),
                tax_rate=spec["rate"],
                seller_name=company.name,
                seller_tax_id=company.tax_id,
                created_at=created,
                completed_at=issued,
                bound_result="SUCCESS",
            )
            add_event(task, "申请已受理", "SUCCESS", created)
            add_event(task, "模拟处理完成", "SUCCESS", issued)
            db.add(task)
            db.flush()
        notes = {
            "VERIFIED": "演示数据：模拟验真通过，未连接外部税务平台",
            "PENDING": "演示数据：待模拟验真",
            "FAILED": "演示数据：模拟验真未通过，未连接外部税务平台",
        }
        invoice = Invoice(
            company_id=company.id,
            generation=company.generation,
            number=uuid4().hex,
            invoice_type=spec["type"],
            direction=spec["dir"],
            issued_at=issued,
            buyer_name=buyer_name,
            buyer_tax_id=buyer_tax,
            seller_name=seller_name,
            seller_tax_id=seller_tax,
            item_name=spec["item"],
            net_amount=Decimal(amounts["net_amount"]),
            tax_amount=Decimal(amounts["tax_amount"]),
            total_amount=Decimal(amounts["total_amount"]),
            tax_rate=spec["rate"],
            verification_status=spec["verify"],
            verification_note=notes[spec["verify"]],
            source_task_id=task.id if task else None,
            pdf_available=False,
        )
        db.add(invoice)
        db.flush()
        path = write_invoice_pdf(invoice)
        invoice.pdf_path = str(path)
        invoice.pdf_available = True
        if task:
            task.invoice_id = invoice.id
            task.invoice_number = invoice.number
            db.add(
                Activity(
                    company_id=company.id,
                    title=f"{invoice.item_name} · 模拟开票成功",
                    time=issued,
                    object_type="billing",
                    object_id=str(task.id),
                )
            )
            db.add(
                Activity(
                    company_id=company.id,
                    title="新增一张销项票据",
                    time=issued,
                    object_type="invoice",
                    object_id=str(invoice.id),
                )
            )

    failed_time = _at(periods[0], 14, 15, 10)
    failed_amount = _amounts("3200.00", "0.06")
    failed_party = COUNTERPARTIES[company.seed_key][0]
    failed = BillingTask(
        company_id=company.id,
        generation=company.generation,
        number=uuid4().hex,
        status="FAILED",
        input_snapshot={
            "invoice_type": "DIGITAL_NORMAL",
            "buyer_name": failed_party[0],
            "buyer_tax_id": failed_party[1],
            "item_name": "资料待核项目",
            "total_amount": failed_amount["total_amount"],
            "tax_rate": "0.06",
            "email": "",
            "remark": "种子失败样例",
        },
        net_amount=Decimal(failed_amount["net_amount"]),
        tax_amount=Decimal(failed_amount["tax_amount"]),
        total_amount=Decimal(failed_amount["total_amount"]),
        tax_rate="0.06",
        seller_name=company.name,
        seller_tax_id=company.tax_id,
        created_at=failed_time,
        completed_at=failed_time,
        failure_reason="开票处理失败，请核对资料后重新提交",
        bound_result="FAILED",
    )
    add_event(failed, "申请已受理", "SUCCESS", failed_time)
    add_event(failed, "模拟处理失败", "FAILED", failed_time, failed.failure_reason)
    db.add(failed)
    db.flush()


def ensure_accounts(db: Session) -> list[User]:
    users = []
    for account in ACCOUNTS:
        user = db.scalar(select(User).where(User.username == account["username"]))
        if user is None:
            user = User(
                username=account["username"],
                password_hash=hash_password(account["password"]),
                name=account["name"],
            )
            db.add(user)
            db.flush()
        users.append(user)
        for spec in account["companies"]:
            company = db.scalar(select(Company).where(Company.seed_key == spec["seed_key"]))
            if company is None:
                company = Company(
                    name=spec["name"],
                    tax_id=spec["tax_id"],
                    service_status=spec["service_status"],
                    seed_key=spec["seed_key"],
                    generation=1,
                )
                db.add(company)
                db.flush()
            link = db.scalar(
                select(UserCompany).where(
                    UserCompany.user_id == user.id, UserCompany.company_id == company.id
                )
            )
            if link is None:
                db.add(UserCompany(user_id=user.id, company_id=company.id))
            has_data = db.scalar(select(Invoice.id).where(Invoice.company_id == company.id).limit(1))
            if has_data is None:
                seed_company_data(db, company)
    return users


def seed_if_empty(db: Session) -> None:
    ensure_accounts(db)
