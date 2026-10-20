"""Versioned SOP checklists, private evidence, independent review, scoped export."""
from __future__ import annotations
import hashlib
import io
import json
import re
import zipfile
from datetime import date, datetime, timedelta, timezone
from html import escape
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import LabOrder, ReportAttachment, SopReport, SopReportVersion, User, WorkflowReceipt
from backend.modules.audit import audit
from backend.modules.organization import STAFF_ROLES, user_position
from backend.security import can_view_order, current_user, role_only
from backend.sop_catalog import BY_CODE, CATALOG, CATALOG_VERSION, snapshot
from backend.utils import utcnow

router=APIRouter()
MAX_FILE=3*1024*1024
MAX_TOTAL=15*1024*1024
MAX_RETAINED=30*1024*1024
MAX_FILES=8
STATE_LABELS={'draft':'Draf','submitted':'Diajukan','reviewed':'Ditinjau','returned':'Perlu perbaikan'}
RESULT_LABELS={'todo':'Belum diperiksa','ok':'Sesuai','issue':'Ada temuan','na':'Tidak relevan'}


from backend.workflow import dumps, replay, finish


def internal(user):
    role_only(user,*STAFF_ROLES)


def order_scope(db,user,order):
    if not order or not can_view_order(user,order,db): return False
    if user.role=='qc' and order.technician_id==user.id:return False
    if user.role=='lab_supervisor': return order.lead_id==user.id
    return True


def check_order(db,user,sop,order_id,check_state=True):
    if sop['order_policy']=='required' and order_id is None:
        raise HTTPException(422,'SOP ini wajib dihubungkan dengan order yang menjadi kewenangan Anda')
    if sop['order_policy']=='none' and order_id is not None:
        raise HTTPException(422,'SOP ini memakai laporan administratif tanpa tautan data order')
    if order_id is None: return None
    order=db.get(LabOrder,order_id)
    if not order_scope(db,user,order): raise HTTPException(404,'Order tidak ditemukan dalam penugasan Anda')
    if check_state and sop['allowed_states'] and order.status not in sop['allowed_states']:
        raise HTTPException(409,'Tahap order tidak sesuai SOP ini: '+', '.join(sop['allowed_states']))
    return order


def may_read(db,user,report):
    if user.org_id!=report.org_id: return False
    spec=json.loads(report.sop_snapshot)
    # Drafts remain private. Review authority is per SOP, never inherited from reporting lines.
    if user.id!=report.author_id and (report.status=='draft' or user.role not in spec['reviewers']): return False
    if report.order_id is not None and not order_scope(db,user,db.get(LabOrder,report.order_id)): return False
    return True


def require_report(db,user,ident,owner=False):
    internal(user)
    report=db.get(SopReport,ident)
    if not report or not may_read(db,user,report) or (owner and report.author_id!=user.id):
        raise HTTPException(404,'Laporan tidak ditemukan')
    return report


def attachments(db,report):
    return db.scalars(select(ReportAttachment).where(ReportAttachment.report_id==report.id,ReportAttachment.org_id==report.org_id,ReportAttachment.removed==False).order_by(ReportAttachment.id)).all()


def attachment_view(a):
    return {'id':a.id,'item_key':a.item_key,'filename':a.filename,'size':a.size,'sha256':a.sha256,'media_type':a.media_type,'created_at':str(a.created_at)}


def report_view(db,user,r,history=True):
    spec=json.loads(r.sop_snapshot)
    author=db.get(User,r.author_id)
    data={'id':r.id,'author_id':r.author_id,'author':author.display_name if author else 'Akun nonaktif',
          'position':r.position_name,'division':r.division,'sop_code':r.sop_code,'title':spec['title'],
          'day':str(r.report_day),'status':r.status,'revision':r.revision,'updated_at':str(r.updated_at),
          'can_read':True,'can_edit':r.author_id==user.id and r.status in ('draft','returned'),
          'can_review':r.author_id!=user.id and user.role in spec['reviewers'] and r.status=='submitted',
          'sop':spec,'summary':r.summary,'results':json.loads(r.results),'order_id':r.order_id,
          'order_code':db.get(LabOrder,r.order_id).code if r.order_id else None,
          'order_state_at_creation':r.order_state,'review_note':r.review_note,
          'reviewer':db.get(User,r.reviewed_by).display_name if r.reviewed_by else None,
          'attachments':[attachment_view(a) for a in attachments(db,r)]}
    if history:
        versions=db.scalars(select(SopReportVersion).where(SopReportVersion.report_id==r.id).order_by(SopReportVersion.revision)).all()
        data['history']=[{'revision':v.revision,'at':str(v.created_at),'snapshot':json.loads(v.snapshot)} for v in versions]
    return data


def reserve(db,r,expected,statuses):
    if r.status not in statuses: raise HTTPException(409,'Tahap laporan tidak mengizinkan tindakan ini')
    changed=db.execute(update(SopReport).where(SopReport.id==r.id,SopReport.revision==expected,SopReport.status.in_(statuses)).values(revision=SopReport.revision+1,updated_at=utcnow()))
    if changed.rowcount!=1: raise HTTPException(409,'Laporan telah berubah. Muat ulang untuk mengambil versi terbaru.')


class StrictIn(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)


class RequestIn(StrictIn):
    request_key:str=Field(min_length=12,max_length=100,pattern=r'^[a-zA-Z0-9_-]+$')


class ResultIn(StrictIn):
    key:str=Field(min_length=1,max_length=60)
    result:str=Field(pattern=r'^(todo|ok|issue|na)$')
    note:str=Field(default='',max_length=1000)
    action:str=Field(default='',max_length=700)
    owner:str=Field(default='',max_length=120)
    due:date|None=None


class CreateIn(RequestIn):
    sop_code:str=Field(max_length=30)
    report_day:date
    order_id:int|None=None


class EditIn(RequestIn):
    expected_revision:int=Field(ge=1)
    summary:str=Field(max_length=3000)
    results:list[ResultIn]=Field(max_length=30)


class TransitionIn(RequestIn):
    expected_revision:int=Field(ge=1)


class ReviewIn(TransitionIn):
    decision:str=Field(pattern=r'^(reviewed|returned)$')
    note:str=Field(min_length=8,max_length=1500)


@router.get('/api/sops')
def catalog(user:User=Depends(current_user)):
    internal(user)
    return {'version':CATALOG_VERSION,'draft':True,'items':[{**s,'can_start':user.role in s['roles'],'can_review':user.role in s['reviewers']} for s in CATALOG],
            'limits':{'file_bytes':MAX_FILE,'total_bytes':MAX_TOTAL,'files_per_report':MAX_FILES,'types':['pdf','png','jpg','jpeg','txt']}}


@router.get('/api/sop-orders')
def available_orders(sop_code:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    internal(user)
    spec=BY_CODE.get(sop_code)
    if not spec or user.role not in spec['roles']: raise HTTPException(403,'SOP tidak tersedia untuk peran ini')
    if spec['order_policy']=='none': return []
    return [{'id':o.id,'code':o.code,'status':o.status} for o in db.scalars(select(LabOrder).order_by(LabOrder.id.desc()))
            if order_scope(db,user,o) and (not spec['allowed_states'] or o.status in spec['allowed_states'])][:100]


@router.get('/api/sops/manual')
def manual(user:User=Depends(current_user),db:Session=Depends(get_db)):
    internal(user)
    from backend.sop_documents import manual_html
    audit(db,user,'sop_catalog.exported','user',user.id,version=CATALOG_VERSION);db.commit()
    return Response(manual_html(),media_type='text/html; charset=utf-8',headers={'Content-Disposition':'attachment; filename="NAM-Draf-SOP-dan-Lampiran.html"'})


@router.post('/api/sop-reports')
def create(data:CreateIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    internal(user)
    spec=BY_CODE.get(data.sop_code)
    if not spec or user.role not in spec['roles']: raise HTTPException(403,'SOP tidak tersedia untuk peran ini')
    fingerprint,prior=replay(db,user,'report.create',data.model_dump())
    if prior is not None:
        require_report(db,user,prior['id'],True)
        return prior
    today=datetime.now(timezone(timedelta(hours=7))).date()  # WIB; portable to Windows without tzdata
    if data.report_day>today: raise HTTPException(422,'Tanggal laporan tidak boleh di masa depan')
    order=check_order(db,user,spec,data.order_id)
    pos=user_position(db,user)
    r=SopReport(author_id=user.id,org_id=user.org_id,position_name=pos.name if pos else user.role,
                division=pos.division if pos else spec['division'],sop_code=spec['code'],sop_snapshot=dumps(snapshot(spec['code'])),
                order_id=data.order_id,order_state=order.status if order else None,report_day=data.report_day,
                results=dumps([{'key':i['key'],'result':'todo','note':'','action':'','owner':'','due':None} for i in spec['items']]))
    db.add(r);db.flush()
    audit(db,user,'sop_report.created','sop_report',r.id,sop=spec['code'],version=spec['version'])
    return finish(db,user,data.request_key,fingerprint,report_view(db,user,r))


@router.get('/api/sop-reports')
def list_reports(user:User=Depends(current_user),db:Session=Depends(get_db)):
    internal(user)
    rows=db.scalars(select(SopReport).where(SopReport.org_id==user.org_id).order_by(SopReport.id.desc())).all()
    output=[]
    for r in rows:
        if may_read(db,user,r):
            view=report_view(db,user,r,False)
            output.append({k:v for k,v in view.items() if k not in ('sop','results','attachments','review_note','reviewer','order_state_at_creation')})
        elif user.role in ('director','chief_executive','commissioner','auditor','operations_manager') and r.status!='draft':
            # Management sees submission counts/status, without clinical summaries or evidence.
            spec=json.loads(r.sop_snapshot)
            output.append({'id':r.id,'sop_code':r.sop_code,'title':spec['title'],'division':r.division,
                           'day':str(r.report_day),'status':r.status,'can_read':False})
        if len(output)>=200: break
    return output


@router.get('/api/sop-reports/{ident}')
def detail(ident:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    r=require_report(db,user,ident)
    audit(db,user,'sop_report.viewed','sop_report',r.id);db.commit()
    return report_view(db,user,r)


@router.post('/api/sop-reports/{ident}/save')
def save(ident:int,data:EditIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    r=require_report(db,user,ident,True)
    fp,prior=replay(db,user,f'report.save:{ident}',data.model_dump())
    if prior is not None: return prior
    spec=json.loads(r.sop_snapshot)
    expected={i['key'] for i in spec['items']}
    if len(data.results)!=len(expected) or {i.key for i in data.results}!=expected:
        raise HTTPException(422,'Daftar checklist harus persis sesuai versi SOP laporan')
    reserve(db,r,data.expected_revision,('draft','returned'))
    r.summary=data.summary;r.results=dumps([i.model_dump() for i in data.results])
    db.flush();audit(db,user,'sop_report.saved','sop_report',r.id,revision=r.revision)
    return finish(db,user,data.request_key,fp,report_view(db,user,r))


def validate_submission(db,user,r):
    spec=json.loads(r.sop_snapshot)
    check_order(db,user,spec,r.order_id)
    if user.role not in spec['roles']: raise HTTPException(403,'Peran Anda tidak lagi berwenang mengajukan SOP ini')
    if len(r.summary.strip())<5: raise HTTPException(422,'Tuliskan ringkasan hasil minimal 5 karakter')
    rows={i['key']:i for i in json.loads(r.results)}
    evidence={a.item_key for a in attachments(db,r)}
    for item in spec['items']:
        result=rows.get(item['key'],{})
        label=item['key']
        if result.get('result') not in ('ok','issue','na'): raise HTTPException(422,f'{label}: hasil pemeriksaan belum diisi')
        if result['result']=='na' and (not item['allow_na'] or len(result.get('note','').strip())<5):
            raise HTTPException(422,f'{label}: tidak relevan hanya diizinkan pada item tertentu dengan alasan')
        if result['result']=='issue':
            if len(result.get('note','').strip())<5 or len(result.get('action','').strip())<5 or not result.get('owner','').strip() or not result.get('due'):
                raise HTTPException(422,f'{label}: temuan wajib memiliki uraian, tindakan, penanggung jawab, dan tenggat')
            if date.fromisoformat(result['due'])<r.report_day: raise HTTPException(422,f'{label}: tenggat tidak boleh sebelum tanggal laporan')
        if item['evidence_required'] and result['result']!='na' and item['key'] not in evidence:
            raise HTTPException(422,f'{label}: lampiran bukti wajib belum diunggah untuk item ini')


def archive(db,user,r,event):
    db.flush()
    view=report_view(db,user,r,False)
    db.add(SopReportVersion(report_id=r.id,revision=r.revision,snapshot=dumps(view)))
    audit(db,user,event,'sop_report',r.id,revision=r.revision,status=r.status)


@router.post('/api/sop-reports/{ident}/submit')
def submit(ident:int,data:TransitionIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    r=require_report(db,user,ident,True)
    fp,prior=replay(db,user,f'report.submit:{ident}',data.model_dump())
    if prior is not None:return prior
    validate_submission(db,user,r)
    reserve(db,r,data.expected_revision,('draft','returned'))
    r.status='submitted';r.review_note='';r.reviewed_by=None
    archive(db,user,r,'sop_report.submitted')
    return finish(db,user,data.request_key,fp,report_view(db,user,r))


@router.post('/api/sop-reports/{ident}/review')
def review(ident:int,data:ReviewIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    r=require_report(db,user,ident)
    spec=json.loads(r.sop_snapshot)
    if r.author_id==user.id or user.role not in spec['reviewers']:
        raise HTTPException(403,'Peninjau harus petugas lain dengan kewenangan SOP yang sesuai')
    fp,prior=replay(db,user,f'report.review:{ident}',data.model_dump())
    if prior is not None:return prior
    reserve(db,r,data.expected_revision,('submitted',))
    r.status=data.decision;r.review_note=data.note;r.reviewed_by=user.id
    archive(db,user,r,'sop_report.'+data.decision)
    return finish(db,user,data.request_key,fp,report_view(db,user,r))


def inspect_file(filename,content):
    if not re.fullmatch(r'[^\\/:*?"<>|\x00-\x1f]{1,150}\.(?:pdf|png|jpe?g|txt)',filename,re.I):
        raise HTTPException(422,'Nama berkas harus aman dan berformat PDF, PNG, JPG, atau TXT')
    if re.match(r'^(?:CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\.|$)',filename,re.I):
        raise HTTPException(422,'Nama berkas menggunakan nama sistem yang tidak diizinkan')
    ext=filename.rsplit('.',1)[-1].lower()
    valid=False;kind=''
    if ext=='pdf':
        valid=content.startswith(b'%PDF-') and b'%%EOF' in content[-2048:]
        kind='application/pdf'
        if re.search(rb'/(?:JavaScript|JS|Launch|EmbeddedFile|OpenAction|AA)\b',content,re.I):valid=False
    elif ext=='png': valid=content.startswith(b'\x89PNG\r\n\x1a\n') and b'IEND' in content[-20:];kind='image/png'
    elif ext in ('jpg','jpeg'):valid=content.startswith(b'\xff\xd8\xff') and content.endswith(b'\xff\xd9');kind='image/jpeg'
    elif ext=='txt':
        try:
            decoded=content.decode('utf-8');valid=bool(decoded.strip()) and not any(ord(c)<32 and c not in '\r\n\t' for c in decoded)
        except UnicodeDecodeError:pass
        kind='text/plain; charset=utf-8'
    if not valid: raise HTTPException(422,'Isi berkas tidak cocok dengan format atau mengandung fitur aktif yang tidak diizinkan')
    return kind


@router.post('/api/sop-reports/{ident}/attachments')
async def upload(ident:int,request:Request,filename:str=Query(max_length=160),item_key:str=Query(max_length=60),
                 expected_revision:int=Query(ge=1),request_key:str=Query(min_length=12,max_length=100,pattern=r'^[a-zA-Z0-9_-]+$'),
                 user:User=Depends(current_user),db:Session=Depends(get_db)):
    r=require_report(db,user,ident,True)
    length=request.headers.get('content-length')
    if length and (not length.isdigit() or int(length)>MAX_FILE): raise HTTPException(413,'Maksimal 3 MB per lampiran')
    content=bytearray()
    async for chunk in request.stream():
        if len(content)+len(chunk)>MAX_FILE:raise HTTPException(413,'Maksimal 3 MB per lampiran')
        content.extend(chunk)
    if not content:raise HTTPException(422,'Berkas kosong')
    content=bytes(content);digest=hashlib.sha256(content).hexdigest()
    payload=dict(filename=filename,item_key=item_key,expected_revision=expected_revision,request_key=request_key,sha256=digest)
    fp,prior=replay(db,user,f'report.upload:{ident}',payload)
    if prior is not None:return prior
    if item_key not in {i['key'] for i in json.loads(r.sop_snapshot)['items']}:
        raise HTTPException(422,'Lampiran harus dikaitkan dengan item checklist yang benar')
    kind=inspect_file(filename,content)
    current=attachments(db,r)
    if len(current)>=MAX_FILES or sum(a.size for a in current)+len(content)>MAX_TOTAL:
        raise HTTPException(413,'Batas 8 lampiran atau total 15 MB per laporan terlampaui')
    retained=db.scalar(select(func.coalesce(func.sum(ReportAttachment.size),0)).where(ReportAttachment.report_id==r.id))
    if retained+len(content)>MAX_RETAINED:
        raise HTTPException(413,'Total bukti beserta riwayat mencapai batas demo 30 MB per laporan')
    reserve(db,r,expected_revision,('draft','returned'))
    a=ReportAttachment(report_id=r.id,org_id=r.org_id,uploaded_by=user.id,item_key=item_key,filename=filename,
                       media_type=kind,sha256=digest,size=len(content),content=content)
    db.add(a);db.flush()
    audit(db,user,'sop_report.evidence_added','sop_report',r.id,attachment_id=a.id,sha256=digest,item_key=item_key)
    return finish(db,user,request_key,fp,{'attachment':attachment_view(a),'revision':r.revision})


@router.post('/api/sop-reports/{ident}/attachments/{attachment_id}/remove')
def remove(ident:int,attachment_id:int,data:TransitionIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    r=require_report(db,user,ident,True)
    fp,prior=replay(db,user,f'report.remove:{ident}:{attachment_id}',data.model_dump())
    if prior is not None:return prior
    a=db.get(ReportAttachment,attachment_id)
    if not a or a.report_id!=r.id or a.org_id!=r.org_id or a.removed:raise HTTPException(404,'Lampiran tidak ditemukan')
    reserve(db,r,data.expected_revision,('draft','returned'))
    a.removed=True
    audit(db,user,'sop_report.evidence_removed','sop_report',r.id,attachment_id=a.id)
    return finish(db,user,data.request_key,fp,{'ok':True,'revision':r.revision})


def attachment_in_history(db,r,attachment_id):
    for version in db.scalars(select(SopReportVersion).where(SopReportVersion.report_id==r.id)):
        if any(a['id']==attachment_id for a in json.loads(version.snapshot).get('attachments',[])):return True
    return False


@router.get('/api/sop-reports/{ident}/attachments/{attachment_id}')
def download(ident:int,attachment_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    r=require_report(db,user,ident)
    a=db.get(ReportAttachment,attachment_id)
    if not a or a.report_id!=r.id or a.org_id!=r.org_id or (a.removed and not attachment_in_history(db,r,a.id)):
        raise HTTPException(404,'Lampiran tidak ditemukan')
    audit(db,user,'sop_report.evidence_downloaded','sop_report',r.id,attachment_id=a.id);db.commit()
    from urllib.parse import quote
    return Response(a.content,media_type=a.media_type,headers={'Content-Disposition':"attachment; filename*=UTF-8''"+quote(a.filename),
                    'Content-Security-Policy':"default-src 'none'; sandbox",'X-Content-Type-Options':'nosniff'})


def report_html(data,files):
    e=lambda value:escape(str(value or ''))
    results={i['key']:i for i in data['results']}
    rows=[]
    for item in data['sop']['items']:
        result=results[item['key']]
        rows.append('<tr><td>'+e(item['key'])+'<br>'+e(item['text'])+'</td><td>'+e(RESULT_LABELS[result['result']])+
                    '</td><td>'+e(result.get('note'))+'<br>'+e(result.get('action'))+'<br>'+e(result.get('owner'))+' '+e(result.get('due'))+'</td></tr>')
    evidence=''.join('<li><a href="'+e(path)+'">'+e(a['filename'])+'</a> · '+e(a['item_key'])+'<br><small>SHA-256 '+e(a['sha256'])+'</small></li>' for a,path in files)
    return '''<!doctype html><html lang="id"><meta charset="utf-8"><title>Laporan SOP NAM</title><style>
    body{font:14px/1.55 "Segoe UI",sans-serif;color:#263a32;max-width:1000px;margin:40px auto;padding:0 24px}h1,h2{font-family:Georgia,serif}h1{font-size:30px}small{overflow-wrap:anywhere}table{width:100%;border-collapse:collapse}td,th{border:1px solid #d7d9d2;text-align:left;padding:12px;vertical-align:top}th{background:#eef0e9}p,td{white-space:pre-wrap}a{color:#385b4c}.label{color:#806b43;letter-spacing:2px}@media print{body{margin:0;padding:0}tr{break-inside:avoid}}@page{size:A4;margin:18mm}</style><body><div class="label">NARAYA AURENTIS MONOLITHIC · DEMO LOKAL</div>'''+\
        '<h1>'+e(data['title'])+'</h1><p>Laporan SOP-'+str(data['id']).zfill(5)+' · '+e(data['sop_code'])+' · SOP '+e(data['sop']['version'])+'\nTanggal '+e(data['day'])+' · '+e(STATE_LABELS[data['status']])+' · Revisi '+str(data['revision'])+\
        '\nPenyusun: '+e(data['author'])+' · '+e(data['position'])+' / '+e(data['division'])+'\nOrder: '+e(data.get('order_code') or data['order_id'] or 'Administratif')+'</p><h2>Hasil pekerjaan</h2><p>'+e(data['summary'])+\
        '</p><table><thead><tr><th>Pemeriksaan</th><th>Hasil</th><th>Temuan / tindakan / pemilik / tenggat</th></tr></thead><tbody>'+''.join(rows)+\
        '</tbody></table><h2>Lampiran bukti</h2><ul>'+evidence+'</ul><h2>Peninjauan</h2><p>'+e(data.get('reviewer') or 'Belum ditinjau')+'\n'+e(data.get('review_note'))+\
        '</p><p>Draf SOP untuk latihan. Peninjauan laporan tidak meluluskan QC, memverifikasi pembayaran, mengganti instruksi klinis, atau menjadi tanda tangan elektronik.</p></body></html>'


@router.get('/api/sop-reports/{ident}/export')
def export(ident:int,format:str=Query(default='zip',pattern=r'^(zip|html)$'),user:User=Depends(current_user),db:Session=Depends(get_db)):
    r=require_report(db,user,ident)
    data=report_view(db,user,r)
    current=attachments(db,r)
    if format=='html':
        content=report_html(data,[(attachment_view(a),f'/api/sop-reports/{r.id}/attachments/{a.id}') for a in current]).encode()
        mime='text/html; charset=utf-8'
    else:
        # Include prior submission versions and evidence so a revision never erases an earlier proof.
        all_files={a.id:a for a in current}
        for version in data['history']:
            for ref in version['snapshot'].get('attachments',[]):
                a=db.get(ReportAttachment,ref['id'])
                if a and a.report_id==r.id and a.org_id==r.org_id:all_files[a.id]=a
        if sum(a.size for a in all_files.values())>30*1024*1024:
            raise HTTPException(413,'Arsip riwayat melebihi 30 MB. Unduh lampiran dan versi secara terpisah.')
        file_path=lambda a:'lampiran/'+str(a.id)+'-'+a.filename
        from urllib.parse import quote
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive_file:
            archive_file.writestr('laporan.html',report_html(data,[(attachment_view(a),quote(file_path(a),safe='/')) for a in current]))
            archive_file.writestr('riwayat.json',dumps(data['history']))
            for a in all_files.values():archive_file.writestr(file_path(a),a.content)
            archive_file.writestr('PETUNJUK.txt','DEMO LOKAL — hanya data fiktif. Buka laporan.html untuk membaca/mencetak. Lampiran dan riwayat dipertahankan. Cocokkan SHA-256 pada laporan. Jangan membagikan arsip di luar penerima berwenang.')
        content=buffer.getvalue();mime='application/zip'
    audit(db,user,'sop_report.exported','sop_report',r.id,format=format,revision=r.revision);db.commit()
    return Response(content,media_type=mime,headers={'Content-Disposition':f'attachment; filename="NAM-SOP-{r.id:05}.{format}"'})
