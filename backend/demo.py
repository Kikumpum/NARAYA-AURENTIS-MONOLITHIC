"""Synthetic fixtures only; never import these into a production deployment."""
from datetime import date, timedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from backend.config import DEMO_PASSWORD
from backend.models import Appointment, LabOrder, Org, Patient, Shift, User
from backend.utils import pwd_hash, utcnow
from backend.demo_accounts import BASE_USERS, EXTRA_STAFF

def seed(db: Session):
    if db.scalar(select(func.count()).select_from(User)):
        return False
    db.add_all([Org(id=1, name='Klinik Naraya (DEMO)', kind='internal'), Org(id=2, name='Klinik Mitra Contoh (DEMO)', kind='partner')])
    db.flush()
    demo_hash = pwd_hash(DEMO_PASSWORD)
    for ident, uname, name, role, org in BASE_USERS:
        db.add(User(id=ident, username=uname, display_name=name, role=role, org_id=org, password_hash=demo_hash, active=True))
    db.flush()
    db.add_all([
        Patient(id=1, public_id='DEMO-P-001', display_name='Pasien Demo Satu', phone='+620000000001', org_id=1, user_id=9, contact_verified=True, service_consent=True, preferred_channel='portal', notification_level='standard'),
        Patient(id=2, public_id='DEMO-P-002', display_name='Pasien Demo Dua', phone='+620000000002', org_id=2, contact_verified=False, service_consent=False),
    ])
    db.flush()
    day = date.today()
    for uid in (2,3,4,5,11,12):
        for offset in range(0, 31):
            db.add(Shift(user_id=uid, shift_day=day+timedelta(days=offset), available=True, max_active_orders=4))
    db.add_all([
        LabOrder(id=1, code='LAB-DEMO-001', source='internal', org_id=1, patient_id=1, dentist_id=2, title='Crown Demo', instruction='INSTRUKSI FIKTIF: crown simulasi tanpa data medis nyata.', category='crown', status='submitted', promised_due=day+timedelta(days=7)),
        LabOrder(id=2, code='LAB-DEMO-002', source='external', org_id=2, patient_id=2, title='Bridge Demo', instruction='INSTRUKSI FIKTIF: bridge simulasi.', category='bridge', status='submitted', promised_due=day+timedelta(days=10)),
    ])
    db.add(Appointment(id=1, patient_id=1, dentist_id=2, scheduled_at=utcnow()+timedelta(days=7), status='confirmed'))
    db.commit()
    return True


def seed_staff_accounts(db: Session):
    """Add only the explicit test fixtures; preserve all existing identities.

    Never reactivate an account, reset its password, change its tenant or role,
    or generate accounts from new/vacant organization positions.
    """
    if not db.get(Org, 1):
        return
    names = {name.strip().lower() for name in db.scalars(select(User.username))}
    missing = [spec for spec in EXTRA_STAFF if spec[0] not in names]
    if not missing:
        return
    password_hash = pwd_hash(DEMO_PASSWORD)
    for username, name, role, _ in missing:
        db.add(User(username=username, display_name=name, role=role, org_id=1,
                    password_hash=password_hash, active=True))
    db.commit()
