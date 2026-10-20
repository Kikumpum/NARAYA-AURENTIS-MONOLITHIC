"""Shared request receipts. Business authorization belongs to each endpoint."""
import hashlib
import json
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from backend.models import WorkflowReceipt


def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def replay(db, user, action, payload):
    fingerprint = hashlib.sha256(dumps([action, payload]).encode()).hexdigest()
    previous = db.scalar(select(WorkflowReceipt).where(
        WorkflowReceipt.actor_id == user.id, WorkflowReceipt.request_key == payload['request_key']))
    if previous:
        if previous.fingerprint != fingerprint:
            raise HTTPException(409, 'Kunci permintaan telah dipakai untuk data lain')
        return fingerprint, json.loads(previous.response)
    return fingerprint, None


def finish(db, user, key, fingerprint, response):
    db.add(WorkflowReceipt(actor_id=user.id, request_key=key, fingerprint=fingerprint, response=dumps(response)))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        prior = db.scalar(select(WorkflowReceipt).where(
            WorkflowReceipt.actor_id == user.id, WorkflowReceipt.request_key == key))
        if prior and prior.fingerprint == fingerprint:
            return json.loads(prior.response)
        raise HTTPException(409, 'Data telah berubah atau kunci permintaan bertabrakan. Muat ulang.')
    return response
