"""Python Playwright operates X01; never substitutes a direct submit API call."""
import json
from pathlib import Path
from sqlalchemy import select, text
from playwright.sync_api import sync_playwright
from app.core import clock
from app.core.config import get_settings
from app.db import SessionLocal, engine
from app.models import AutomationTask, Company, Declaration, FileAsset, TaxFiling
from app.services import automation as a, declarations


def run_one():
    settings=get_settings()
    # Session-level lock survives the short transactions, but does not block portal/reset transactions.
    with engine.connect() as lease:
        acquired=lease.execute(text('SELECT pg_try_advisory_lock(:k)'),{'k':settings.processor_lock_key+1}).scalar()
        lease.commit()
        if not acquired:return
        try:
            _run_claimed(settings)
        finally:
            lease.execute(text('SELECT pg_advisory_unlock(:k)'),{'k':settings.processor_lock_key+1})
            lease.commit()


def _run_claimed(settings):
    with SessionLocal() as db:
        dec=db.scalar(select(Declaration).join(AutomationTask,Declaration.task_id==AutomationTask.id)
                      .where(AutomationTask.status.in_(['PENDING','PROCESSING']))
                      .order_by(AutomationTask.created_at).limit(1))
        if dec is None:return
        company=db.get(Company,dec.company_id);a.lock(db,company)
        if dec.generation!=company.generation:return
        task=db.get(AutomationTask,dec.task_id)
        recovering=bool(dec.acceptance_number)
        if recovering:
            a.event(task,'核对原申报',note=f'{company.tax_id} / {dec.period} / {dec.business_number} / {dec.acceptance_number}')
            declarations.prepare_receipt(db,company,dec)
        task.status='PROCESSING';task.failure_reason=None
        a.event(task,'浏览器已领取任务','PROCESSING', '恢复已有受理，不再次提交' if recovering else '实际操作 X01 表单')
        snapshot={k:getattr(dec,k) for k in ['id','company_id','generation','task_id','period','business_number','sales_amount','tax_amount','acceptance_number']}
        snapshot.update(company_name=company.name,tax_id=company.tax_id)
        token=declarations.token_for(dec)
        db.commit()
    folder=settings.rpa_evidence_dir/str(snapshot['company_id'])/str(snapshot['generation'])/str(snapshot['id'])/clock.now().strftime('%Y%m%dT%H%M%S%f')
    folder.mkdir(parents=True,exist_ok=True)
    steps=[];downloaded=None;error=None
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(channel=settings.rpa_browser_channel,headless=True)
            try:
                context=browser.new_context(accept_downloads=True,viewport={'width':1000,'height':850})
                page=context.new_page();page.set_default_timeout(15000)
                # Token stays in URL fragment and is never written to evidence/logs.
                page.goto(settings.simulation_base_url.rstrip('/')+'/simulation-portal/index.html#token='+token)
                page.locator('#loading').wait_for(state='hidden')
                for selector,expected in [('#company-name',snapshot['company_name']),('#tax-id',snapshot['tax_id']),
                                          ('#period',snapshot['period']),('#business-number',snapshot['business_number'])]:
                    if page.locator(selector).text_content()!=expected:raise RuntimeError('X01 身份、期间或业务标识不一致')
                steps.append('核对企业、税号、期间、业务标识')
                page.screenshot(path=str(folder/'01-context.png'),full_page=True)
                if page.locator('#accepted').is_visible():
                    if snapshot['acceptance_number'] and page.locator('#acceptance-number').text_content()!=snapshot['acceptance_number']:
                        raise RuntimeError('原受理号不一致')
                    steps.append('查询到原受理记录，跳过提交')
                else:
                    if recovering:raise RuntimeError('恢复时未找到原受理记录，禁止再次提交')
                    page.locator('#sales').fill(snapshot['sales_amount'])
                    page.locator('#tax').fill(snapshot['tax_amount'])
                    page.locator('#submit').click()
                    page.locator('#accepted').wait_for(state='visible')
                    steps.append('填写销售额及税额，点击表单提交，页面显示受理号')
                page.screenshot(path=str(folder/'02-accepted.png'),full_page=True)
                if page.locator('#receipt').is_disabled():
                    steps.append('已受理，回执中断，等待恢复')
                else:
                    with page.expect_download() as download_info:
                        page.locator('#receipt').click()
                    download=download_info.value
                    downloaded=Path(download.path()).read_bytes()
                    if not downloaded.startswith(b'%PDF-'):raise RuntimeError('回执不是 PDF')
                    (folder/'receipt.pdf').write_bytes(downloaded)
                    steps.append('点击回执入口，浏览器下载真实 PDF')
            finally:
                browser.close()
    except Exception as exc:
        # Avoid logging Playwright call logs which include the capability URL.
        error=f'浏览器执行失败（{type(exc).__name__}），可恢复后重试'
    with SessionLocal() as db:
        company=db.get(Company,snapshot['company_id'])
        a.lock(db,company)
        dec=db.get(Declaration,snapshot['id'])
        if dec is None or company.generation!=snapshot['generation']:
            # Reset has removed the business record. Do not resurrect it or its artifacts.
            import shutil
            shutil.rmtree(folder,ignore_errors=True)
            return
        task=db.get(AutomationTask,dec.task_id)
        if task.status=='WAITING_RECOVERY':
            outcome='WAITING_RECOVERY'
        elif error or downloaded is None:
            task.status='FAILED';task.failure_reason=error or '未能获取回执，可恢复后重试'
            a.event(task,'机器人运行失败','FAILED',task.failure_reason);outcome='FAILED'
        else:
            file=db.get(FileAsset,dec.receipt_file_id)
            if not file or file.content!=downloaded:
                task.status='FAILED';task.failure_reason='浏览器回执与服务端记录不一致'
                a.event(task,'回执核对失败','FAILED',task.failure_reason);outcome='FAILED'
            else:
                task.status='SUCCESS';task.failure_reason=None
                a.event(task,'浏览器获取并核对回执','SUCCESS',dec.acceptance_number)
                filing=db.get(TaxFiling,dec.filing_id);filing.status='COMPLETED';filing.updated_at=clock.now()
                filing.failure_reason=None;filing.nodes=list(task.events)
                outcome='SUCCESS'
        evidence={'declaration_id':str(dec.id),'task_id':str(dec.task_id),'company_id':str(company.id),
                  'generation':dec.generation,'period':dec.period,'business_number':dec.business_number,
                  'acceptance_number':dec.acceptance_number,'submission_count':dec.submission_count,
                  'steps':steps,'outcome':outcome,'error':error,'time':clock.iso(clock.now())}
        (folder/'result.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
        db.commit()
