"""Position mapping is administrative; application privileges never inherit."""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Org, OrganizationPosition, User, UserPosition
from backend.organization_catalog import ADDITIONAL_ROLES, DEMO_POSITION, POSITIONS, STRUCTURE_NOTES
from backend.security import current_user, role_only
from backend.constants import ROLES
from backend.modules.audit import audit

router = APIRouter()
STAFF_ROLES = tuple(r for r in ROLES if r not in ('patient','partner')) + ADDITIONAL_ROLES


def seed_structure(db):
    if not db.get(Org,1):
        return
    positions={p.code:p for p in db.scalars(select(OrganizationPosition).where(OrganizationPosition.org_id==1))}
    for code,name,parent,division,roles in POSITIONS:
        if code not in positions:
            p=OrganizationPosition(org_id=1,code=code,name=name,parent_code=parent,division=division,allowed_roles=json.dumps(roles))
            db.add(p); db.flush(); positions[code]=p
    for user in db.scalars(select(User).where(User.org_id==1)):
        code=DEMO_POSITION.get(user.username)
        if code and user.role in json.loads(positions[code].allowed_roles) and not db.scalar(select(UserPosition).where(UserPosition.user_id==user.id)):
            db.add(UserPosition(user_id=user.id,position_id=positions[code].id,org_id=1))
    db.commit()


def user_position(db,user):
    mapping=db.scalar(select(UserPosition).where(UserPosition.user_id==user.id,UserPosition.org_id==user.org_id))
    position=db.get(OrganizationPosition,mapping.position_id) if mapping else None
    if position and position.org_id==user.org_id:
        return position
    return None


@router.get('/api/organization')
def organization(user:User=Depends(current_user),db:Session=Depends(get_db)):
    role_only(user,*STAFF_ROLES)
    positions=db.scalars(select(OrganizationPosition).where(OrganizationPosition.org_id==user.org_id).order_by(OrganizationPosition.id)).all()
    staff=db.scalars(select(User).where(User.org_id==user.org_id,User.active==True)).all()
    maps={m.user_id:m for m in db.scalars(select(UserPosition).where(UserPosition.org_id==user.org_id))}
    return {'draft':True,'notes':STRUCTURE_NOTES,'positions':[{
        'id':p.id,'code':p.code,'name':p.name,'parent_code':p.parent_code,'division':p.division,
        'allowed_roles':json.loads(p.allowed_roles),
        'accounts':[{'id':u.id,'name':u.display_name,'role':u.role} for u in staff if u.id in maps and maps[u.id].position_id==p.id],
    } for p in positions], 'can_assign':user.role in ('director','hr'),
        'staff':[{'id':u.id,'name':u.display_name,'role':u.role,
                  'position_id':maps[u.id].position_id if u.id in maps else None,
                  'revision':maps[u.id].revision if u.id in maps else 0} for u in staff if u.role in STAFF_ROLES] if user.role in ('director','hr') else []}


class AssignmentIn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    user_id:int
    position_id:int
    expected_revision:int=Field(ge=0)
    reason:str=Field(min_length=8,max_length=500)
    request_key:str=Field(min_length=12,max_length=100,pattern=r'^[a-zA-Z0-9_-]+$')


@router.post('/api/organization/assignments')
def assign(data:AssignmentIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    role_only(user,'director','hr')
    # Imported lazily to keep the workflow infrastructure separate from role policy.
    from backend.modules.sop_reports import replay, finish
    fingerprint,previous=replay(db,user,'position.assign',data.model_dump())
    if previous is not None: return previous
    target=db.get(User,data.user_id); p=db.get(OrganizationPosition,data.position_id)
    if not target or not target.active or target.org_id!=user.org_id or not p or p.org_id!=user.org_id:
        raise HTTPException(404,'Akun atau jabatan tidak ditemukan')
    if target.role not in json.loads(p.allowed_roles):
        raise HTTPException(409,'Peran akun tidak sesuai jabatan. Pemetaan jabatan tidak boleh menaikkan hak akses.')
    mapping=db.scalar(select(UserPosition).where(UserPosition.user_id==target.id,UserPosition.org_id==user.org_id))
    old=mapping.position_id if mapping else None
    if mapping:
        changed=db.execute(update(UserPosition).where(UserPosition.id==mapping.id,UserPosition.revision==data.expected_revision).values(position_id=p.id,revision=UserPosition.revision+1))
        if changed.rowcount!=1: raise HTTPException(409,'Pemetaan telah berubah. Muat ulang sebelum menyimpan.')
    else:
        if data.expected_revision!=0: raise HTTPException(409,'Versi pemetaan tidak sesuai')
        db.add(UserPosition(user_id=target.id,position_id=p.id,org_id=user.org_id,revision=1))
    audit(db,user,'organization.position_assigned','user',target.id,old_position=old,new_position=p.id,reason=data.reason)
    return finish(db,user,data.request_key,fingerprint,{'ok':True,'user_id':target.id,'position_id':p.id,'revision':data.expected_revision+1})
