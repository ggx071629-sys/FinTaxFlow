from decimal import Decimal
from sqlalchemy import select
from app.core import clock
from app.core.errors import ApiError
from app.models import AutomationTask, ImportRecord, ImportLine, Reconciliation
from app.serialize import money
from app.services import automation as a
from app.services.imports import valid_period


def reconciliation_out(db,rec):
    task=db.get(AutomationTask,rec.task_id)
    return dict(id=str(rec.id),company_id=str(rec.company_id),number=task.number,period=task.period,
                status=task.status,bank_import_id=str(rec.bank_import_id),ledger_import_id=str(rec.ledger_import_id),
                bank_count=sum(r['bank'] is not None for r in rec.results),ledger_count=sum(r['ledger'] is not None for r in rec.results),
                total=len(rec.results),matched=sum(r['status']=='MATCHED' for r in rec.results),
                different=sum(r['status']=='DIFFERENT' for r in rec.results),missing=sum(r['status']=='MISSING' for r in rec.results),
                task_id=str(task.id),created_at=clock.iso(task.created_at))


def create_reconciliation(db,user,company,body,key):
    a.lock(db,company)
    old=a.previous(db,user,company,'reconcile',key,body,Reconciliation)
    if old:return reconciliation_out(db,old)
    period=valid_period(body.get('period'));sources=[];maps=[]
    for kind,field in [('BANK','bank_import_id'),('LEDGER','ledger_import_id')]:
        imp=a.owned(db,ImportRecord,company,body.get(field))
        rows=db.scalars(select(ImportLine).where(ImportLine.import_id==imp.id)).all()
        if imp.kind!=kind or not rows or any(r.status!='VALID' for r in rows):
            raise ApiError(409,'IMPORT_NOT_SUBMITTABLE','两侧必须使用对应模板且所有行通过校验')
        if imp.period!=period:
            raise ApiError(409,'IMPORT_PERIOD_MISMATCH','两侧所属期间必须与所选期间一致')
        sources.append(imp)
        maps.append({r.business_number:{'import_id':str(imp.id),'file_name':imp.file_name,'row_number':r.row_number,
                      **{k:r.fields[k] for k in ['transaction_date','counterparty','direction','amount']}} for r in rows})
    existing=db.scalar(select(Reconciliation).where(Reconciliation.bank_import_id==sources[0].id,Reconciliation.ledger_import_id==sources[1].id))
    if existing:
        a.remember(db,user,company,'reconcile',key,body,existing)
        return reconciliation_out(db,existing)
    results=[]
    for bn in sorted(maps[0].keys()|maps[1].keys()):
        bank,ledger=maps[0].get(bn),maps[1].get(bn)
        status='MISSING';reason='银行流水缺失' if bank is None else '收付款记录缺失';difference=None
        if bank and ledger:
            difference=money(Decimal(bank['amount'])-Decimal(ledger['amount']))
            equal_amount=Decimal(bank['amount'])==Decimal(ledger['amount'])
            equal_direction=bank['direction']==ledger['direction']
            status='MATCHED' if equal_amount and equal_direction else 'DIFFERENT'
            reason='业务单号、金额与方向一致' if status=='MATCHED' else '、'.join(x for x,yes in [('金额不同',not equal_amount),('收付方向不同',not equal_direction)] if yes)
        results.append(dict(business_number=bn,status=status,reason=reason,bank=bank,ledger=ledger,difference=difference))
    task=a.new_task(db,company,'RECONCILIATION',period);task.status='SUCCESS'
    a.event(task,'一对一对账完成',note='结果仅用于核对，独立账务摘要未修改')
    rec=Reconciliation(company_id=company.id,generation=company.generation,task_id=task.id,
                       bank_import_id=sources[0].id,ledger_import_id=sources[1].id,results=results)
    db.add(rec);a.remember(db,user,company,'reconcile',key,body,rec)
    return reconciliation_out(db,rec)
