from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.security import current_user, role_only

router = APIRouter()

import json
from backend.models import Audit, User

def audit(db: Session, actor: User, event: str, entity: str, entity_id: int, **detail):
    db.add(Audit(actor_id=actor.id, event=event, entity=entity, entity_id=entity_id, detail=json.dumps(detail, ensure_ascii=False, default=str)))

@router.get('/api/admin/audits')
def audits(user:User=Depends(current_user),db:Session=Depends(get_db)):
    role_only(user,'director')
    rows=db.scalars(select(Audit).order_by(Audit.id.desc()).limit(100)).all()
    return [{'event':a.event,'entity':a.entity,'entity_id':a.entity_id,
             'reference':('CHAT '+str(json.loads(a.detail).get('conversation',''))[-6:].upper()) if a.entity=='chat' else None,
             'actor':db.get(User,a.actor_id).display_name,'at':str(a.occurred_at),'detail':a.detail} for a in rows]
