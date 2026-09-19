"""Local simulation portal: bound capability, durable acceptance, one submission."""
import io
import uuid
from datetime import datetime, timedelta, timezone
import jwt
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from sqlalchemy import select
from app.api.deps import require_company
from app.core import clock
from app.core.config import get_settings
from app.core.errors import ApiError
from app.models import AutomationTask, Company, Declaration, DemoSetting, FileAsset, TaxFiling, User
from app.services import automation as a


def declaration_for_filing(db,filing):
    dec=db.scalar(select(Declaration).where(Declaration.filing_id==filing.id))
    return {'tax_type':'VAT' if filing.name=='增值税' else 'OTHER',
            'can_declare':filing.name=='增值税' and filing.status!='COMPLETED' and dec is None,
            **({'declaration_task_id':str(dec.task_id)} if dec else {}),
            **({'receipt_id':str(dec.id)} if dec and dec.receipt_file_id else {})}


def create(db,user,company,body,key):
    a.lock(db,company)
    old=a.previous(db,user,company,'declaration_create',key,body,Declaration)
    if old:return a.task_out(db,db.get(AutomationTask,old.task_id))
    filing_id=body.get('filing_id')
    from app.api.deps import parse_uuid
    filing=db.get(TaxFiling,parse_uuid(filing_id))
    if filing is None or filing.company_id!=company.id:
        raise ApiError(404,'NOT_FOUND','税务记录不存在')
    if body.get('confirmed') is not True or body.get('tax_type')!='VAT' or filing.name!='增值税':
        raise ApiError(400,'INVALID_INPUT','仅支持已确认的增值税模拟申报')
    if body.get('period')!=filing.period:
        raise ApiError(409,'IMPORT_PERIOD_MISMATCH','所属期不一致')
    existing=db.scalar(select(Declaration).where(Declaration.company_id==company.id,
               Declaration.generation==company.generation,Declaration.period==filing.period,Declaration.tax_type=='VAT'))
    if existing:
        a.remember(db,user,company,'declaration_create',key,body,existing)
        return a.task_out(db,db.get(AutomationTask,existing.task_id))
    if filing.status=='COMPLETED':
        raise ApiError(409,'IMPORT_NOT_SUBMITTABLE','该记录已完成，不能重复申报')
    setting=db.get(DemoSetting,(user.id,company.id));fault=setting.declaration_fault if setting else 'NONE'
    if setting:setting.declaration_fault='NONE'
    task=a.new_task(db,company,'DECLARATION',filing.period)
    dec=Declaration(company_id=company.id,generation=company.generation,task_id=task.id,user_id=user.id,
                    filing_id=filing.id,period=filing.period,tax_type='VAT',business_number='SB'+uuid.uuid4().hex[:24].upper(),
                    sales_amount='10000.00',tax_amount='600.00',fault=fault,submission_count=0)
    db.add(dec);a.remember(db,user,company,'declaration_create',key,body,dec)
    return a.task_out(db,task)


def recover(db,user,company,value,body,key):
    a.lock(db,company)
    payload={**body,'declaration_id':value}
    old=a.previous(db,user,company,'declaration_recover',key,payload,Declaration)
    if old:return a.task_out(db,db.get(AutomationTask,old.task_id))
    dec=a.owned(db,Declaration,company,value);task=db.get(AutomationTask,dec.task_id)
    if body.get('confirmed') is not True:
        raise ApiError(400,'INVALID_INPUT','请确认恢复')
    if task.status not in ['WAITING_RECOVERY','FAILED','PROCESSING','PENDING','SUCCESS']:
        raise ApiError(409,'IMPORT_NOT_SUBMITTABLE','当前状态不可恢复')
    if task.status in ['WAITING_RECOVERY','FAILED']:
        # Keep the original failed event; browser will inspect ACCEPTED before doing anything.
        task.status='PENDING';task.failure_reason=None
        a.event(task,'恢复已请求',note='先核对原申报及受理记录，已受理时不再提交')
    a.remember(db,user,company,'declaration_recover',key,payload,dec)
    return a.task_out(db,task)


def token_for(dec):
    now=datetime.now(timezone.utc)
    return jwt.encode({'sub':str(dec.user_id),'aud':'fintax-simulation','declaration_id':str(dec.id),
                       'company_id':str(dec.company_id),'generation':dec.generation,'period':dec.period,
                       'business_number':dec.business_number,'iat':now,'exp':now+timedelta(minutes=10)},
                      get_settings().jwt_secret,algorithm='HS256')


def resolve_token(db,token,write=False):
    try:
        claims=jwt.decode(token,get_settings().jwt_secret,algorithms=['HS256'],audience='fintax-simulation')
        user=db.get(User,uuid.UUID(claims['sub']))
        if not user:raise ValueError()
        company=require_company(db,user,claims['company_id'])
        if write:a.lock(db,company)
        dec=a.owned(db,Declaration,company,claims['declaration_id'])
        if (claims['generation']!=company.generation or claims['period']!=dec.period or
            claims['business_number']!=dec.business_number or user.id!=dec.user_id):raise ValueError()
        return user,company,dec
    except (jwt.PyJWTError,ValueError,KeyError,ApiError):
        raise ApiError(401,'UNAUTHENTICATED','申报访问凭证已失效') from None


def context(db,company,dec):
    file=db.get(FileAsset,dec.receipt_file_id) if dec.receipt_file_id else None
    return dict(company_name=company.name,tax_id=company.tax_id,period=dec.period,declaration_id=str(dec.id),
                business_number=dec.business_number,sample_sales=dec.sales_amount,sample_tax=dec.tax_amount,
                status='ACCEPTED' if dec.acceptance_number else 'READY',
                receipt_ready=bool(file and file.content is not None),
                **({'acceptance_number':dec.acceptance_number} if dec.acceptance_number else {}))


def prepare_receipt(db,company,dec):
    if dec.receipt_file_id:return
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    output=io.BytesIO();pdf=canvas.Canvas(output);pdf.setFont('STSong-Light',16)
    for n,line in enumerate(['FinTaxFlow 模拟申报回执','演示文件，非真实税务申报凭证',company.name,
                             '纳税人识别号：'+company.tax_id,'所属期：'+dec.period,'税种：增值税',
                             '受理编号：'+dec.acceptance_number,'业务标识：'+dec.business_number,
                             '样例销售额：'+dec.sales_amount,'样例税额：'+dec.tax_amount,
                             '受理时间：'+clock.iso(dec.accepted_at)]):
        pdf.drawString(40,800-n*32,line)
    pdf.save()
    dec.receipt_file_id=a.add_file(db,company,'模拟申报回执.pdf','application/pdf',output.getvalue()).id


def accept(db,user,company,dec,body,key):
    if body.get('declaration_id')!=str(dec.id):
        raise ApiError(403,'FORBIDDEN','凭证不允许访问此申报')
    old=a.previous(db,user,company,'portal_submit',key,body,Declaration)
    if old:return context(db,company,old)
    if body.get('sales_amount')!=dec.sales_amount or body.get('tax_amount')!=dec.tax_amount:
        raise ApiError(400,'INVALID_INPUT','金额须与本次服务端固定样例一致')
    if not dec.acceptance_number:
        task=db.get(AutomationTask,dec.task_id)
        dec.acceptance_number='SL'+uuid.uuid4().hex[:24].upper()
        dec.accepted_at=clock.now();dec.submission_count=1
        a.event(task,'X01 表单已受理',note=dec.acceptance_number)
        if dec.fault=='RECEIPT_DISCONNECT':
            dec.fault='NONE';task.status='WAITING_RECOVERY'
            task.failure_reason='演示故障：提交已受理，获取回执时连接中断'
            a.event(task,'提交后回执中断','FAILED',task.failure_reason)
        else:
            prepare_receipt(db,company,dec)
    a.remember(db,user,company,'portal_submit',key,body,dec)
    return context(db,company,dec)


def receipt_out(db,company,dec):
    if not dec.acceptance_number:
        raise ApiError(425,'FILE_NOT_READY','申报尚未受理')
    out=dict(id=str(dec.id),company_id=str(company.id),task_id=str(dec.task_id),company_name=company.name,
             tax_id=company.tax_id,period=dec.period,tax_type='VAT',acceptance_number=dec.acceptance_number,
             accepted_at=clock.iso(dec.accepted_at))
    if dec.receipt_file_id:out['file']=a.file_ref(db.get(FileAsset,dec.receipt_file_id))
    return out
