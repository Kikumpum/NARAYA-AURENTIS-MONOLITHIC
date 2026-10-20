"""Read-only learning materials derived from the versioned draft SOPs."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User
from backend.modules.audit import audit
from backend.organization_catalog import POSITIONS
from backend.security import current_user, role_only
from backend.sop_catalog import CATALOG, CATALOG_VERSION

router = APIRouter(prefix='/api/training', tags=['Materi pegawai'])
STAFF = tuple(sorted({r for p in POSITIONS for r in p[4]}))


@router.get('')
def materials(user: User = Depends(current_user), db: Session = Depends(get_db)):
    role_only(user, *STAFF)
    divisions = []
    for s in CATALOG:
        if not any(d['name'] == s['division'] for d in divisions):
            divisions.append({'name':s['division'], 'purpose':s['purpose']})
    return {'version':CATALOG_VERSION, 'draft':True, 'divisions':divisions,
            'modules':[{'code':s['code'], 'title':s['title'], 'purpose':s['purpose'],
                        'frequency':s['frequency']} for s in CATALOG if user.role in s['roles']]}


@router.get('/{code}')
def lesson(code: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    role_only(user, *STAFF)
    s = next((s for s in CATALOG if s['code'] == code and user.role in s['roles']), None)
    if not s:
        raise HTTPException(404, 'Materi tidak ditemukan untuk tugas Anda')
    audit(db, user, 'training.opened', 'training', 0, code=code, version=CATALOG_VERSION)
    db.commit()
    return {'code':s['code'], 'title':s['title'], 'purpose':s['purpose'],
            'frequency':s['frequency'], 'version':CATALOG_VERSION, 'draft':True,
            'steps':s['items'], 'evidence_examples':s['evidence_examples'],
            'exercise':'Gunakan kasus fiktif. Siapkan draf laporan dari SOP ini, isi hasil pemeriksaan, catat temuan beserta penanggung jawab dan tenggat, lalu lampirkan bukti yang diminta.',
            'review':'Membaca materi tidak berarti mendapat kewenangan baru atau dinyatakan lulus pelatihan. Penilaian dan pengesahan materi oleh penanggung jawab divisi masih diperlukan.'}
