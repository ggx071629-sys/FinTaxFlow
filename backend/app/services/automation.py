"""Shared E2 ownership, transaction serialization and persistent projections."""
import uuid
from sqlalchemy import select, text
from app.api.deps import parse_uuid
from app.core import clock
from app.core.config import get_settings
from app.core.errors import ApiError
from app.models import (AutomationTask, BatchAttempt, BatchLine, BillingBatch, BillingTask,
                        Company, Declaration, FileAsset, ImportRecord, Reconciliation, ResetRun)
from app.services import idempotency

TITLES = {'BILLING': '批量模拟开票', 'RECONCILIATION': '一对一对账', 'DECLARATION': '增值税模拟申报'}
ATTENTION = ('FAILED', 'PARTIAL_FAILED', 'WAITING_RECOVERY')


def lock(db, company):
    # Same lock as the original local processor/reset; short database transactions only.
    db.execute(text('SELECT pg_advisory_xact_lock(:k)'), {'k': get_settings().processor_lock_key})
    db.refresh(company)
    if db.scalar(select(ResetRun.id).where(ResetRun.company_id == company.id,
                                         ResetRun.status.in_(['PENDING', 'PROCESSING', 'FAILED']))):
        raise ApiError(409, 'RESET_IN_PROGRESS', '当前企业恢复尚未完成，请先继续恢复')


def owned(db, model, company, value):
    item = db.get(model, value if isinstance(value, uuid.UUID) else parse_uuid(value))
    if item is None or item.company_id != company.id or item.generation != company.generation:
        raise ApiError(404, 'NOT_FOUND', '对象不存在')
    return item


def previous(db, user, company, operation, key, payload, model):
    record = idempotency.lookup(db, user, company.id, operation, key, payload)
    return owned(db, model, company, record.object_id) if record else None


def remember(db, user, company, operation, key, payload, item):
    db.flush()
    idempotency.store(db, user, company.id, operation, key, payload, item.id)
    return item


def event(task, label, status='SUCCESS', note=None):
    at = clock.now()
    task.updated_at = at
    task.events = [*(task.events or []), {'label': label, 'status': status, 'time': clock.iso(at), **({'note': note} if note else {})}]


def new_task(db, company, kind, period=None):
    tid = uuid.uuid4()
    task = AutomationTask(id=tid, company_id=company.id, generation=company.generation,
                          number='AT' + tid.hex[:24].upper(), kind=kind, period=period,
                          status='PENDING', created_at=clock.now(), updated_at=clock.now(), events=[])
    db.add(task)
    event(task, '任务已创建')
    db.flush()
    return task


def file_ref(file):
    return {'id': str(file.id), 'name': file.name, 'media_type': file.media_type, 'ready': file.content is not None}


def add_file(db, company, name, media_type, content):
    file = FileAsset(company_id=company.id, generation=company.generation, name=name,
                     media_type=media_type, content=content)
    db.add(file)
    db.flush()
    return file


def page(items, number, size):
    if number < 1 or size < 1 or size > 100:
        raise ApiError(400, 'INVALID_INPUT', '页码须大于 0，单页数量须在 1–100 之间')
    return {'items': items[(number-1)*size:number*size], 'page': number, 'page_size': size, 'total': len(items)}


def task_out(db, task):
    from app.services.batches import batch_out
    from app.services.reconciliation import reconciliation_out
    out = {k: getattr(task, k) for k in ['number','kind','status','events']}
    out.update(id=str(task.id), company_id=str(task.company_id), title=TITLES[task.kind],
               created_at=clock.iso(task.created_at), updated_at=clock.iso(task.updated_at), sources=[])
    if task.period:
        out['period'] = task.period
    if task.failure_reason:
        out['failure_reason'] = task.failure_reason
    if task.kind == 'BILLING':
        batch = db.scalar(select(BillingBatch).where(BillingBatch.task_id == task.id))
        info = batch_out(db, batch)
        imp = db.get(ImportRecord, batch.import_id)
        out.update(batch_id=str(batch.id), counts={k: info[k] for k in ['total','success','failed','processing']},
                   sources=[{'label':'开票清单','import_id':str(imp.id),'file_name':imp.file_name}])
    elif task.kind == 'RECONCILIATION':
        rec = db.scalar(select(Reconciliation).where(Reconciliation.task_id == task.id))
        info = reconciliation_out(db, rec)
        out.update(reconciliation_id=str(rec.id), counts={'total':info['total'],'success':info['total'],'failed':0,'processing':0})
        for label, iid in [('银行流水',rec.bank_import_id),('收付款记录',rec.ledger_import_id)]:
            imp = db.get(ImportRecord, iid)
            out['sources'].append({'label':label, 'import_id':str(iid), 'file_name':imp.file_name})
    else:
        dec = db.scalar(select(Declaration).where(Declaration.task_id == task.id))
        done = task.status == 'SUCCESS'
        out.update(declaration_id=str(dec.id), submitted=bool(dec.acceptance_number),
                   submission_count=dec.submission_count, total_steps=4,
                   completed_steps=4 if done else (3 if dec.acceptance_number else (1 if task.status != 'PENDING' else 0)),
                   counts={'total':1,'success':int(done),'failed':int(task.status in ATTENTION),'processing':int(task.status in ['PENDING','PROCESSING'])})
        if dec.acceptance_number:
            out['acceptance_number'] = dec.acceptance_number
        if dec.receipt_file_id:
            out['receipt_id'] = str(dec.id)
    return out


def sync_batches(db):
    from app.services.batches import batch_out
    for batch in db.scalars(select(BillingBatch)).all():
        task = db.get(AutomationTask, batch.task_id)
        company = db.get(Company, batch.company_id)
        if company.generation != batch.generation:
            continue
        info = batch_out(db, batch)
        if info['processing']:
            status = 'PROCESSING'
        elif info['failed']:
            status = 'PARTIAL_FAILED' if info['success'] else 'FAILED'
        else:
            status = 'SUCCESS'
        if status != task.status:
            task.status = status
            event(task, '批次结果更新', status, f"成功 {info['success']}，失败 {info['failed']}，处理中 {info['processing']}")
    db.flush()
