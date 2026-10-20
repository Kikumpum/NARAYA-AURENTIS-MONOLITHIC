from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.security import current_user, role_only

router = APIRouter()

from datetime import date
from pydantic import BaseModel, Field
from backend.models import DailyReport, Invoice, LabOrder, User
from backend.modules.audit import audit
from backend.modules.finance import invoice_view
from backend.security import can_view_order

class ReportIn(BaseModel):
    summary: str=Field(min_length=5,max_length=2000)
    blockers: str=Field(default='',max_length=1500)


@router.post('/api/daily-reports')
def submit_report(data:ReportIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    role_only(user,'reception','dentist','lab_supervisor','technician','qc','finance','nurse','cadcam','customer_service','warehouse','purchasing','hr','marketing','it_admin')
    report=DailyReport(author_id=user.id,org_id=user.org_id,division=user.role,report_day=date.today(),summary=data.summary,blockers=data.blockers)
    db.add(report);db.flush();audit(db,user,'daily_report.submitted','report',report.id)
    db.commit();return {'id':report.id,'report_day':str(report.report_day)}


@router.get('/api/daily-reports')
def list_reports(user:User=Depends(current_user),db:Session=Depends(get_db)):
    role_only(user,'reception','dentist','lab_supervisor','technician','qc','finance','director','nurse','cadcam','customer_service','warehouse','purchasing','hr','marketing','it_admin')
    rows=db.scalars(select(DailyReport).order_by(DailyReport.id.desc()).limit(100)).all()
    return [{'id':r.id,'day':str(r.report_day),'division':r.division,'author':db.get(User,r.author_id).display_name,'summary':r.summary,'blockers':r.blockers} for r in rows if r.org_id==user.org_id and (user.role=='director' or r.author_id==user.id or (user.role=='lab_supervisor' and r.division in ('technician','qc')))]


@router.get('/api/dashboard')
def dashboard(user:User=Depends(current_user),db:Session=Depends(get_db)):
    all_orders=db.scalars(select(LabOrder)).all()
    visible=[o for o in all_orders if can_view_order(user,o,db)]
    order_ids={o.id for o in visible}
    invs=db.scalars(select(Invoice)).all()
    selected=[inv for inv in invs if inv.order_id in order_ids]
    receivables=0; verified=0
    if user.role in ('director','finance','reception','partner'):
        for inv in selected:
            x=invoice_view(db,inv)
            verified+=x['paid_idr'];receivables+=x['outstanding_idr']
    return {'orders':len(visible),'submitted':sum(o.status in ('submitted','assigned','rejected') for o in visible), 'in_progress':sum(o.status in ('accepted','design','production','finishing','rework','qc_pending') for o in visible),'ready':sum(o.status=='ready' for o in visible),'delay_pending':sum(o.delay_response=='pending' for o in visible),'verified_revenue_idr':verified if user.role in ('director','finance') else None,'receivables_idr':receivables if user.role in ('director','finance') else None,'demo':True}
