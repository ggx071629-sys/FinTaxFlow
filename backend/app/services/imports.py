"""Fixed UTF-8 CSV only; original bytes and fields remain traceable."""
import csv
import hashlib
import io
import re
from datetime import date
from decimal import Decimal
from pathlib import PurePath
from sqlalchemy import select
from app.core import clock
from app.core.errors import ApiError
from app.core.money import AMOUNT_RE
from app.models import BatchLine, FileAsset, ImportLine, ImportRecord
from app.serialize import money
from app.services import automation as a
from app.services.billing import validate_input

BILLING = {'业务单号':'business_number','购买方名称':'buyer_name','购买方税号':'buyer_tax_id',
           '项目':'item_name','含税金额':'total_amount','税率':'tax_rate','票种':'invoice_type'}
BANK = {'业务单号':'business_number','交易日期':'transaction_date','交易对方':'counterparty',
        '收付方向':'direction','金额':'amount'}
TEMPLATES = {'BILLING':BILLING, 'BANK':BANK, 'LEDGER':BANK}
TYPES = {'数电普票':'DIGITAL_NORMAL','数电专票':'DIGITAL_SPECIAL'}
DIRECTIONS = {'收':'IN','付':'OUT','收入':'IN','支出':'OUT'}


def csv_bytes(rows):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    # Prevent spreadsheet formula execution in exported diagnostics.
    for row in rows:
        writer.writerow(["'" + str(v) if str(v).startswith(('=','+','-','@','\t','\r')) else v for v in row])
    return stream.getvalue().encode('utf-8-sig')


def template(kind):
    if kind not in TEMPLATES:
        raise ApiError(400, 'INVALID_TEMPLATE', '不支持此模板')
    return csv_bytes([list(TEMPLATES[kind])])


def valid_period(period):
    if not isinstance(period, str) or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', period):
        raise ApiError(400, 'INVALID_INPUT', '期间格式须为 YYYY-MM')
    return period


def import_out(db, imp):
    rows = db.scalars(select(ImportLine).where(ImportLine.import_id == imp.id)).all()
    valid = [r for r in rows if r.status == 'VALID']
    out = dict(id=str(imp.id),company_id=str(imp.company_id),kind=imp.kind,file_name=imp.file_name,
               status='VALIDATED',total=len(rows),valid=len(valid),errors=sum(r.status=='ERROR' for r in rows),
               duplicates=sum(r.status=='DUPLICATE' for r in rows),
               valid_amount=money(sum((Decimal(r.fields.get('total_amount',r.fields.get('amount','0'))) for r in valid),Decimal(0))),
               created_at=clock.iso(imp.created_at))
    if imp.period:
        out['period'] = imp.period
    if imp.issue_file_id:
        out['issue_file'] = a.file_ref(db.get(FileAsset,imp.issue_file_id))
    return out


def row_out(row):
    return {k:getattr(row,k) for k in ['row_number','business_number','status','fields','issues']}


def create_import(db,user,company,kind,period,name,content,key):
    a.lock(db,company)
    if kind not in TEMPLATES:
        raise ApiError(400,'INVALID_TEMPLATE','不支持此模板')
    if kind != 'BILLING' or period is not None:
        valid_period(period)
    payload = {'kind':kind,'period':period,'file_name':name,'sha256':hashlib.sha256(content).hexdigest()}
    existing = a.previous(db,user,company,'import',key,payload,ImportRecord)
    if existing:
        return import_out(db,existing)
    try:
        decoded = content.decode('utf-8-sig')
        if '\x00' in decoded:
            raise ValueError('NUL')
        reader = csv.reader(io.StringIO(decoded,newline=''), strict=True)
        header = next(reader)
        mapping = TEMPLATES[kind]
        if [v.strip() for v in header] != list(mapping):
            raise ApiError(400,'INVALID_TEMPLATE','列名或顺序与固定模板不符，请下载模板')
        parsed=[]
        while True:
            # Physical original line number, including header/multiline fields.
            number=reader.line_num+1
            try:
                values=next(reader)
            except StopIteration:
                break
            if not values or all(not v.strip() for v in values):
                continue
            if len(values)!=len(mapping):
                raise ApiError(400,'INVALID_CSV',f'第 {number} 行列数不正确')
            parsed.append((number,dict(zip(mapping.values(),values))))
    except (UnicodeError,csv.Error,ValueError,StopIteration):
        raise ApiError(400,'INVALID_CSV','文件须为可读取的 UTF-8 CSV，且包含固定表头') from None
    if not parsed:
        raise ApiError(400,'INVALID_CSV','文件没有数据行')
    source=a.add_file(db,company,PurePath(name).name[:255] or 'import.csv','text/csv',content)
    imp=ImportRecord(company_id=company.id,generation=company.generation,kind=kind,period=period,
                     file_name=source.name,source_file_id=source.id,created_at=clock.now())
    db.add(imp);db.flush()
    accepted=set(db.scalars(select(BatchLine.business_number).where(BatchLine.company_id==company.id,
                   BatchLine.generation==company.generation)).all()) if kind=='BILLING' else set()
    seen=set();issues_export=[['原始行号','业务单号','字段','原因']]
    for number,raw in parsed:
        fields={k:v.strip() for k,v in raw.items()};issues={}
        bn=fields['business_number']
        if not bn or len(bn)>200:
            issues['business_number']='业务单号不能为空且不超过 200 字'
        if kind=='BILLING':
            fields['invoice_type']=TYPES.get(fields['invoice_type'],fields['invoice_type'])
            fields.update(email='',remark='')
            issues.update(validate_input(fields))
            amount_key='total_amount'
        else:
            amount_key='amount'
            fields['direction']=DIRECTIONS.get(fields['direction'],fields['direction'])
            if fields['direction'] not in ['IN','OUT']:
                issues['direction']='收付方向须为 IN/OUT 或 收/付'
            if not fields['counterparty']:
                issues['counterparty']='交易对方不能为空'
            try:
                value=fields['transaction_date'].replace('/','-')
                year,month,day=map(int,value.split('-'))
                fields['transaction_date']=date(year,month,day).isoformat()
                if fields['transaction_date'][:7]!=period:
                    issues['transaction_date']='交易日期不属于所选期间'
            except (ValueError,TypeError):
                issues['transaction_date']='交易日期无效'
            if not AMOUNT_RE.fullmatch(fields['amount']) or Decimal(fields['amount'])<=0:
                issues['amount']='金额须大于 0，最多两位小数、十位整数'
        for field,value in fields.items():
            if field not in ['business_number'] and len(value)>200:
                issues[field]='字段不能超过 200 字'
        if amount_key not in issues:
            fields[amount_key]=money(fields[amount_key])
        duplicate=bool(bn and (bn in seen or bn in accepted))
        if duplicate:
            issues['business_number']='同文件重复或该企业已受理此业务单号'
        status='DUPLICATE' if duplicate else ('ERROR' if issues else 'VALID')
        seen.add(bn)
        details=[{'field':field,'message':message} for field,message in issues.items()]
        db.add(ImportLine(company_id=company.id,generation=company.generation,import_id=imp.id,
                         row_number=number,business_number=bn[:200],status=status,raw_fields=raw,fields=fields,issues=details))
        issues_export.extend([number,bn,field,message] for field,message in issues.items())
    if len(issues_export)>1:
        imp.issue_file_id=a.add_file(db,company,'导入问题清单.csv','text/csv',csv_bytes(issues_export)).id
    a.remember(db,user,company,'import',key,payload,imp)
    return import_out(db,imp)
