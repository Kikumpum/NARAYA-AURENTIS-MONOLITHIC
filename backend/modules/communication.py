from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.security import current_user, role_only

router = APIRouter()

from backend.models import LabOrder, Notification, Patient, User

def queue_notice(db: Session, o: LabOrder, kind: str, text: str):
    patient = db.get(Patient, o.patient_id)
    if o.source=='internal' and kind=='progress' and patient.notification_level=='minimal':
        return
    if o.source == 'internal' and patient.contact_verified and patient.service_consent:
        db.add(Notification(patient_id=patient.id, org_id=o.org_id, order_id=o.id, channel=patient.preferred_channel, kind=kind, message=text, status='queued'))
    elif o.source == 'external':
        # Partner organization is primary recipient; never bypass it to reach a patient.
        db.add(Notification(patient_id=None, org_id=o.org_id, order_id=o.id, channel='partner_portal', kind=kind, message=text, status='queued'))

@router.get('/api/notifications')
def notifications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    role_only(user,'patient','partner','reception','lab_supervisor','director')
    rows=db.scalars(select(Notification).order_by(Notification.id.desc()).limit(100)).all()
    result=[]
    for n in rows:
        if user.role=='patient':
            patient=db.get(Patient,n.patient_id) if n.patient_id else None
            if not patient or patient.user_id!=user.id:continue
        elif user.role=='partner':
            if n.org_id!=user.org_id or n.patient_id is not None:continue
        elif user.role in ('reception','lab_supervisor','director'):
            if n.org_id!=1:continue
        result.append({'id':n.id,'order_id':n.order_id,'kind':n.kind,'channel':n.channel,'message':n.message,'status':n.status,'created_at':str(n.created_at)})
    return result
