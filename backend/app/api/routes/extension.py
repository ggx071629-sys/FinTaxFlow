from typing import Annotated, Literal
from fastapi import APIRouter, Depends, File, Form, Header, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import require_company
from app.core.errors import ApiError
from app.core.security import get_current_user
from app.db import get_db
from app.models import (AutomationTask, BillingBatch, Declaration, FileAsset, ImportRecord, ImportLine, Reconciliation, User)
from app.services import automation as a, batches, declarations, imports, reconciliation

from app.schemas.extension import BatchInput, RetryInput, ReconciliationInput, DeclarationInput, RecoveryInput

router=APIRouter(tags=['automation'])
DB=Annotated[Session,Depends(get_db)]
Actor=Annotated[User,Depends(get_current_user)]
Key=Annotated[str|None,Header(alias='Idempotency-Key')]


def company_for(db,user,cid):return require_company(db,user,cid)


def records(db,model,company):
    return db.scalars(select(model).where(model.company_id==company.id,model.generation==company.generation).order_by(model.id)).all()


def binary(file):
    if file.content is None:raise ApiError(425,'FILE_NOT_READY','文件尚未就绪')
    from urllib.parse import quote
    return Response(file.content,media_type=file.media_type,headers={'Content-Disposition':"attachment; filename*=UTF-8''"+quote(file.name),'Cache-Control':'no-store'})


@router.get('/import-templates/{kind}')
def download_template(kind:str,company_id:str,db:DB,user:Actor):
    company_for(db,user,company_id)
    content=imports.template(kind.upper())
    return Response(content,media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="{kind.lower()}.csv"'})


@router.post('/imports')
def upload(db:DB,user:Actor,company_id:Annotated[str,Form()],kind:Annotated[str,Form()],
                 file:Annotated[UploadFile,File()],period:Annotated[str|None,Form()]=None,idempotency_key:Key=None):
    company=company_for(db,user,company_id)
    content=file.file.read(5*1024*1024+1)
    if len(content)>5*1024*1024:raise ApiError(400,'INVALID_CSV','固定样例 CSV 请控制在 5 MB 内')
    return imports.create_import(db,user,company,kind,period,file.filename or 'import.csv',content,idempotency_key)


@router.get('/imports/{value}')
def import_detail(value:str,company_id:str,db:DB,user:Actor):
    return imports.import_out(db,a.owned(db,ImportRecord,company_for(db,user,company_id),value))


@router.get('/imports/{value}/rows')
def import_rows(value:str,company_id:str,db:DB,user:Actor,filter:Literal['ISSUES','VALID']='ISSUES',page:int=1,page_size:int=20):
    imp=a.owned(db,ImportRecord,company_for(db,user,company_id),value)
    rows=db.scalars(select(ImportLine).where(ImportLine.import_id==imp.id).order_by(ImportLine.row_number)).all()
    return a.page([imports.row_out(r) for r in rows if (r.status=='VALID')==(filter=='VALID')],page,page_size)


@router.post('/billing-batches')
def batch_create(body:BatchInput,db:DB,user:Actor,idempotency_key:Key=None):
    body=body.model_dump()
    return batches.create_batch(db,user,company_for(db,user,body.get('company_id')),body,idempotency_key)


@router.get('/billing-batches')
def batch_list(company_id:str,db:DB,user:Actor,page:int=1,page_size:int=20):
    rows=records(db,BillingBatch,company_for(db,user,company_id))
    return a.page(sorted([batches.batch_out(db,r) for r in rows],key=lambda x:x['created_at'],reverse=True),page,page_size)


@router.get('/billing-batches/{value}')
def batch_detail(value:str,company_id:str,db:DB,user:Actor):
    return batches.batch_out(db,a.owned(db,BillingBatch,company_for(db,user,company_id),value))


@router.get('/billing-batches/{value}/rows')
def batch_rows(value:str,company_id:str,db:DB,user:Actor,status:str='',page:int=1,page_size:int=20):
    batch=a.owned(db,BillingBatch,company_for(db,user,company_id),value)
    if status not in ['', 'ALL','PENDING','PROCESSING','SUCCESS','FAILED']:
        raise ApiError(400,'INVALID_INPUT','不支持此状态')
    rows=[batches.row_out(db,l) for l in batches.lines(db,batch)]
    return a.page([r for r in rows if status in ['', 'ALL'] or r['status']==status],page,page_size)


@router.post('/billing-batches/{value}/retry')
def batch_retry(value:str,body:RetryInput,db:DB,user:Actor,idempotency_key:Key=None):
    body=body.model_dump()
    return batches.retry(db,user,company_for(db,user,body.get('company_id')),value,body,idempotency_key)


@router.post('/reconciliations')
def reconcile(body:ReconciliationInput,db:DB,user:Actor,idempotency_key:Key=None):
    body=body.model_dump()
    return reconciliation.create_reconciliation(db,user,company_for(db,user,body.get('company_id')),body,idempotency_key)


@router.get('/reconciliations')
def reconciliation_list(company_id:str,db:DB,user:Actor,period:str|None=None,page:int=1,page_size:int=20):
    rows=[reconciliation.reconciliation_out(db,r) for r in records(db,Reconciliation,company_for(db,user,company_id))]
    return a.page(sorted([r for r in rows if not period or r['period']==period],key=lambda x:x['created_at'],reverse=True),page,page_size)


@router.get('/reconciliations/{value}')
def reconciliation_detail(value:str,company_id:str,db:DB,user:Actor):
    return reconciliation.reconciliation_out(db,a.owned(db,Reconciliation,company_for(db,user,company_id),value))


@router.get('/reconciliations/{value}/rows')
def reconciliation_rows(value:str,company_id:str,db:DB,user:Actor,differences_only:bool=False,page:int=1,page_size:int=20):
    rec=a.owned(db,Reconciliation,company_for(db,user,company_id),value)
    return a.page([r for r in rec.results if not differences_only or r['status']!='MATCHED'],page,page_size)


@router.get('/automation/tasks')
def task_list(company_id:str,db:DB,user:Actor,kind:str='',attention:bool=False,page:int=1,page_size:int=20):
    if kind not in ['', 'ALL', *a.TITLES]:raise ApiError(400,'INVALID_INPUT','不支持此任务类型')
    tasks=records(db,AutomationTask,company_for(db,user,company_id))
    rows=[a.task_out(db,t) for t in sorted(tasks,key=lambda t:t.created_at,reverse=True)
          if (kind in ['', 'ALL'] or t.kind==kind) and (not attention or t.status in a.ATTENTION)]
    return a.page(rows,page,page_size)


@router.get('/automation/tasks/{value}')
def task_detail(value:str,company_id:str,db:DB,user:Actor):
    return a.task_out(db,a.owned(db,AutomationTask,company_for(db,user,company_id),value))


@router.get('/automation/overview')
def overview(company_id:str,db:DB,user:Actor):
    tasks=records(db,AutomationTask,company_for(db,user,company_id));services=[]
    for kind,title in a.TITLES.items():
        selected=sorted([t for t in tasks if t.kind==kind],key=lambda t:t.created_at,reverse=True)
        service={'kind':kind,'title':title,'status':selected[0].status if selected else 'PENDING','summary':f'{len(selected)} 项任务' if selected else '暂无任务'}
        if selected:
            item=a.task_out(db,selected[0])
            service['object_id']=item.get('batch_id') or item.get('reconciliation_id') or item['id']
        services.append(service)
    return {'attention_count':sum(t.status in a.ATTENTION for t in tasks),'services':services}


@router.post('/declarations')
def declaration_create(body:DeclarationInput,db:DB,user:Actor,idempotency_key:Key=None):
    body=body.model_dump()
    return declarations.create(db,user,company_for(db,user,body.get('company_id')),body,idempotency_key)


@router.post('/declarations/{value}/recover')
def declaration_recover(value:str,body:RecoveryInput,db:DB,user:Actor,idempotency_key:Key=None):
    body=body.model_dump()
    return declarations.recover(db,user,company_for(db,user,body.get('company_id')),value,body,idempotency_key)


@router.get('/declaration-receipts/{value}')
def receipt(value:str,company_id:str,db:DB,user:Actor):
    company=company_for(db,user,company_id)
    return declarations.receipt_out(db,company,a.owned(db,Declaration,company,value))


@router.get('/files/{value}/content')
def file_content(value:str,company_id:str,db:DB,user:Actor):
    return binary(a.owned(db,FileAsset,company_for(db,user,company_id),value))
