from decimal import Decimal
from sqlalchemy import select
from app.core import clock
from app.core.errors import ApiError
from app.models import AutomationTask, BatchAttempt, BatchLine, BillingBatch, BillingTask, ImportLine, ImportRecord
from app.serialize import money
from app.services import automation as a
from app.services.billing import create_task


def attempts(db,line):
    return db.scalars(select(BillingTask).join(BatchAttempt,BatchAttempt.billing_task_id==BillingTask.id)
                      .where(BatchAttempt.line_id==line.id).order_by(BatchAttempt.position)).all()


def row_out(db,line):
    source=db.get(ImportLine,line.import_line_id)
    history=attempts(db,line);current=history[-1]
    out=dict(id=str(line.id),row_number=source.row_number,business_number=line.business_number,
             buyer_name=source.fields['buyer_name'],invoice_type=source.fields['invoice_type'],
             total_amount=source.fields['total_amount'],status=current.status,billing_task_id=str(current.id),
             attempt_task_ids=[str(t.id) for t in history])
    if current.invoice_id: out['invoice_id']=str(current.invoice_id)
    if current.failure_reason: out['failure_reason']=current.failure_reason
    return out


def lines(db,batch):
    return db.scalars(select(BatchLine).join(ImportLine,BatchLine.import_line_id==ImportLine.id)
                      .where(BatchLine.batch_id==batch.id).order_by(ImportLine.row_number)).all()


def batch_out(db,batch):
    task=db.get(AutomationTask,batch.task_id)
    rows=[row_out(db,line) for line in lines(db,batch)]
    return dict(id=str(batch.id),company_id=str(batch.company_id),number=task.number,name=batch.name,
                import_id=str(batch.import_id),task_id=str(task.id),status=task.status,total=len(rows),
                success=sum(r['status']=='SUCCESS' for r in rows),failed=sum(r['status']=='FAILED' for r in rows),
                processing=sum(r['status'] in ['PENDING','PROCESSING'] for r in rows),
                total_amount=money(sum((Decimal(r['total_amount']) for r in rows),Decimal(0))),created_at=clock.iso(task.created_at))


def create_batch(db,user,company,body,key):
    a.lock(db,company)
    old=a.previous(db,user,company,'batch_create',key,body,BillingBatch)
    if old: return batch_out(db,old)
    if body.get('confirmed') is not True:
        raise ApiError(400,'INVALID_INPUT','请确认有效行后提交')
    imp=a.owned(db,ImportRecord,company,body.get('import_id'))
    existing=db.scalar(select(BillingBatch).where(BillingBatch.import_id==imp.id))
    if existing:
        a.remember(db,user,company,'batch_create',key,body,existing)
        return batch_out(db,existing)
    valid=db.scalars(select(ImportLine).where(ImportLine.import_id==imp.id,ImportLine.status=='VALID').order_by(ImportLine.row_number)).all()
    if imp.kind!='BILLING' or not valid:
        raise ApiError(409,'IMPORT_NOT_SUBMITTABLE','没有可提交的开票有效行')
    business=[r.business_number for r in valid]
    if db.scalar(select(BatchLine.id).where(BatchLine.company_id==company.id,BatchLine.generation==company.generation,
                                          BatchLine.business_number.in_(business))):
        raise ApiError(409,'DUPLICATE_BUSINESS_NUMBER','存在已受理业务单号，请查询原批次或重新校验文件')
    task=a.new_task(db,company,'BILLING')
    batch=BillingBatch(company_id=company.id,generation=company.generation,import_id=imp.id,task_id=task.id,name=imp.file_name)
    db.add(batch);db.flush()
    for source in valid:
        line=BatchLine(company_id=company.id,generation=company.generation,batch_id=batch.id,
                       import_line_id=source.id,business_number=source.business_number)
        db.add(line);db.flush()
        result=create_task(db,user,company,source.fields,f'batch-{line.id}-1',allow_batch=True)
        from uuid import UUID
        db.add(BatchAttempt(line_id=line.id,billing_task_id=UUID(result['id']),position=1));db.flush()
    a.remember(db,user,company,'batch_create',key,body,batch)
    return batch_out(db,batch)


def retry(db,user,company,batch_id,body,key):
    a.lock(db,company)
    payload={**body,'batch_id':batch_id}
    old=a.previous(db,user,company,'batch_retry',key,payload,BillingBatch)
    if old:return batch_out(db,old)
    if body.get('failed_only') is not True:
        raise ApiError(400,'INVALID_INPUT','仅允许重试失败行')
    batch=a.owned(db,BillingBatch,company,batch_id)
    retried=0
    for line in lines(db,batch):
        history=attempts(db,line);current=history[-1]
        if current.status!='FAILED':continue
        result=create_task(db,user,company,{**current.input_snapshot,'source_task_id':str(current.id)},
                           f'batch-{line.id}-{len(history)+1}',allow_batch=True)
        from uuid import UUID
        db.add(BatchAttempt(line_id=line.id,billing_task_id=UUID(result['id']),position=len(history)+1));db.flush()
        retried+=1
    task=db.get(AutomationTask,batch.task_id)
    if retried:
        task.status='PROCESSING';a.event(task,'仅失败行已关联重提',note=f'{retried} 行；原失败尝试保留')
    a.remember(db,user,company,'batch_retry',key,payload,batch)
    return batch_out(db,batch)
