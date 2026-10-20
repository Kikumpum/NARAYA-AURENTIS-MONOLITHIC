from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.security import current_user, role_only

router = APIRouter()

import hashlib
import secrets
from datetime import timedelta
from fastapi import Request, Response
from pydantic import BaseModel
from backend.config import COOKIE_SECURE
from backend.models import Org, Patient, User, UserSession
from backend.security import patient_record, session_csrf
from backend.modules.audit import audit
from backend.utils import pwd_valid, utcnow
from backend.demo_accounts import LOGIN_ALIASES

class LoginIn(BaseModel):
    username: str
    password: str


# Dev-only throttling; production must use a shared durable rate limiter and SSO/MFA.
_failed_logins: dict[str, int] = {}


def verify_credentials(payload: LoginIn, request: Request, db: Session):
    ip = request.client.host if request.client else '?'
    if _failed_logins.get(ip, 0) >= 25:
        raise HTTPException(429, 'Terlalu banyak percobaan; restart demo untuk mereset')
    identifier = payload.username.strip().lower()
    matches = db.scalars(select(User).where(func.lower(User.username) == identifier).limit(2)).all()
    if not matches and identifier in LOGIN_ALIASES:
        matches = db.scalars(select(User).where(func.lower(User.username) == LOGIN_ALIASES[identifier]).limit(2)).all()
    # A legacy database may contain names that differ only by case. Fail closed
    # rather than silently select another user's role or organization.
    user = matches[0] if len(matches) == 1 else None
    if not user or not user.active or not pwd_valid(payload.password, user.password_hash):
        _failed_logins[ip] = _failed_logins.get(ip, 0) + 1
        raise HTTPException(401, 'Nama pengguna atau kata sandi salah')
    _failed_logins.pop(ip, None)
    return user


def patient_credentials(payload: LoginIn, db: Session):
    matches = db.scalars(select(Patient).where(func.lower(Patient.public_id) == payload.username.strip().lower(), Patient.org_id == 1).limit(2)).all()
    if len(matches) > 1:
        raise HTTPException(401, 'Nama pengguna atau kata sandi salah')
    reference = matches[0] if matches else None
    linked = db.get(User, reference.user_id) if reference and reference.user_id else None
    return payload.model_copy(update={'username': linked.username}) if linked else payload


@router.post('/api/access/resolve')
def resolve_access(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    """Choose a portal after authentication; never trust a client-supplied role.

    The actual login still uses its audience-specific endpoint, so the browser
    sends the correctly scoped existing cookie and re-login revokes that session.
    This lookup creates no session and exposes no organization or role roster.
    """
    origin = request.headers.get('origin')
    if ((origin and origin != str(request.base_url).rstrip('/'))
        or request.headers.get('sec-fetch-site') == 'cross-site'):
        raise HTTPException(403, 'Asal permintaan tidak diizinkan')
    user = verify_credentials(patient_credentials(payload, db), request, db)
    if user.role == 'patient':
        patient_record(db, user)
    return {'portal': 'patient' if user.role == 'patient' else 'workspace'}


def issue_session(user, request, response, db, *, cookie='nam_session', audience='workspace', path='/'):
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        raise HTTPException(403, 'Asal permintaan tidak diizinkan')
    previous = request.cookies.get(cookie)
    if previous:
        active = db.scalar(select(UserSession).where(UserSession.token_hash == hashlib.sha256(previous.encode()).hexdigest()))
        if active and active.audience == audience:
            db.delete(active)
    raw_token = secrets.token_urlsafe(36)
    session = UserSession(token_hash=hashlib.sha256(raw_token.encode()).hexdigest(), csrf_token_hash=secrets.token_hex(32), user_id=user.id, expires_at=utcnow()+timedelta(hours=8), audience=audience)
    db.add(session)
    audit(db,user,'auth.login','user',user.id,audience=audience)
    db.commit()
    response.set_cookie(cookie, raw_token, httponly=True, secure=COOKIE_SECURE, samesite='strict', max_age=8*3600, path=path)
    return session_csrf(session, raw_token)


@router.post('/api/login')
def login(payload: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    # Compatibility API for existing demo acceptance scripts. New UI uses audience-specific login.
    user = verify_credentials(payload, request, db)
    csrf = issue_session(user, request, response, db)
    org = db.get(Org, user.org_id)
    return {'user':{'id':user.id,'name':user.display_name,'role':user.role,'org_id':user.org_id,'org_name':org.name if org else ''}, 'csrf':csrf, 'demo':True}


@router.post('/api/workspace/login')
def workspace_login(payload: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    user = verify_credentials(payload, request, db)
    if user.role == 'patient':
        raise HTTPException(403, 'Silakan masuk melalui portal pasien di /pasien')
    csrf = issue_session(user, request, response, db)
    org = db.get(Org, user.org_id)
    return {'user':{'id':user.id,'name':user.display_name,'role':user.role,'org_id':user.org_id,'org_name':org.name if org else ''}, 'csrf':csrf, 'demo':True}


@router.get('/api/me')
def me(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = db.scalar(select(UserSession).where(UserSession.token_hash == hashlib.sha256(request.cookies['nam_session'].encode()).hexdigest()))
    org = db.get(Org, user.org_id)
    return {'id':user.id,'name':user.display_name,'role':user.role,'org_id':user.org_id,
            'org_name':org.name if org else '', 'session_expires':str(session.expires_at),
            'csrf':session_csrf(session, request.cookies['nam_session'])}


@router.post('/api/logout')
def logout(request: Request, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    digest = hashlib.sha256(request.cookies['nam_session'].encode()).hexdigest()
    active = db.scalar(select(UserSession).where(UserSession.token_hash == digest))
    if active:
        db.delete(active)
    audit(db,user,'auth.logout','user',user.id)
    db.commit()
    response.delete_cookie('nam_session', path='/')
    return {'ok': True}
