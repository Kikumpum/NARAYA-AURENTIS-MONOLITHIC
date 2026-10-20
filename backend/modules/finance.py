from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.security import current_user, role_only

router = APIRouter()

from typing import Literal
from pydantic import BaseModel, Field
from backend.models import Invoice, LabOrder, Org, Payment, User
from backend.modules.audit import audit
from backend.security import require_order

class InvoiceIn(BaseModel):
    order_id: int
    amount_idr: int=Field(gt=0,le=1_000_000_000)


@router.post('/api/invoices')
def create_invoice(data:InvoiceIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    role_only(user,'reception','finance')
    o=require_order(db,user,data.order_id)
    if db.scalar(select(Invoice).where(Invoice.order_id==o.id)):
        raise HTTPException(409,'Order sudah memiliki invoice')
    inv=Invoice(order_id=o.id,amount_idr=data.amount_idr,invoice_type='internal_cost' if o.source=='internal' else 'external_invoice')
    db.add(inv);db.flush();audit(db,user,'invoice.created','invoice',inv.id,amount=data.amount_idr,kind=inv.invoice_type)
    db.commit();return {'id':inv.id,'invoice_type':inv.invoice_type}


def invoice_view(db:Session, inv:Invoice):
    o=db.get(LabOrder,inv.order_id)
    payments=db.scalars(select(Payment).where(Payment.invoice_id==inv.id).order_by(Payment.id)).all()
    paid=sum(p.amount_idr for p in payments if p.status=='verified')
    pending=sum(p.amount_idr for p in payments if p.status=='pending_verification')
    return {'id':inv.id,'order_id':o.id,'order_code':o.code,'source':o.source,'customer':db.get(Org,o.org_id).name,'type':inv.invoice_type,'amount_idr':inv.amount_idr,'paid_idr':paid,'pending_idr':pending,'outstanding_idr':max(0,inv.amount_idr-paid),'status':'paid' if paid>=inv.amount_idr else 'partial' if paid else 'unpaid','payments':[{'id':p.id,'method':p.method,'amount_idr':p.amount_idr,'status':p.status,'received_by':p.received_by} for p in payments]}


@router.get('/api/invoices')
def invoices(user:User=Depends(current_user),db:Session=Depends(get_db)):
    role_only(user,'finance','reception','director','partner')
    rows=db.scalars(select(Invoice).order_by(Invoice.id.desc())).all()
    return [invoice_view(db,inv) for inv in rows if user.role!='partner' or db.get(LabOrder,inv.order_id).org_id==user.org_id]


class PaymentIn(BaseModel):
    method: Literal['cash','qris','bank_transfer','debit_edc','credit_card','insurance_corporate']
    amount_idr: int=Field(gt=0,le=1_000_000_000)
    reference: str | None=Field(default=None,max_length=120)


@router.post('/api/invoices/{iid}/payments')
def register_payment(iid:int,data:PaymentIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    role_only(user,'reception')
    inv=db.get(Invoice,iid)
    if not inv:raise HTTPException(404,'Invoice tidak ada')
    existing=invoice_view(db,inv)
    if data.amount_idr+existing['paid_idr']+existing['pending_idr']>inv.amount_idr:
        raise HTTPException(409,'Jumlah pembayaran melebihi tagihan termasuk pembayaran menunggu verifikasi')
    if data.reference and db.scalar(select(Payment).where(Payment.reference==data.reference)):
        raise HTTPException(409,'Referensi pembayaran sudah dipakai')
    p=Payment(invoice_id=inv.id,method=data.method,amount_idr=data.amount_idr,reference=data.reference,status='pending_verification',received_by=user.id)
    db.add(p);db.flush();audit(db,user,'payment.recorded','payment',p.id,invoice=inv.id,method=data.method,amount=data.amount_idr)
    db.commit();return {'id':p.id,'status':p.status}


@router.post('/api/payments/{pid}/verify')
def verify_payment(pid:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    role_only(user,'finance')
    p=db.get(Payment,pid)
    if not p:raise HTTPException(404,'Pembayaran tidak ditemukan')
    if p.status!='pending_verification':raise HTTPException(409,'Pembayaran sudah diproses')
    if p.received_by==user.id:raise HTTPException(403,'Penerima pembayaran tidak boleh memverifikasi transaksi sendiri')
    # Demo verification simulates an OFFLINE manual reconciliation; production electronic
    # payments require bank/gateway settlement evidence before this action is permitted.
    p.status='verified';p.verified_by=user.id
    audit(db,user,'payment.manually_verified','payment',p.id,method=p.method,amount=p.amount_idr)
    db.commit();return {'status':p.status,'manual_demo_verification':True}
