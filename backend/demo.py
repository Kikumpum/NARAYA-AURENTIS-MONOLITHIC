"""Synthetic fixtures only; never import these into a production deployment."""
from datetime import date, timedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from backend.config import DEMO_PASSWORD
from backend.models import Appointment, LabOrder, Org, Patient, Shift, User
from backend.utils import pwd_hash, utcnow

def seed(db: Session):
    if db.scalar(select(func.count()).select_from(User)):
        return
    db.add_all([Org(id=1, name='Klinik Naraya (DEMO)', kind='internal'), Org(id=2, name='Klinik Mitra Contoh (DEMO)', kind='partner')])
    people = [
        (1,'resepsionis','Resepsionis Demo','reception',1), (2,'dokter','Dokter Klinik Demo','dentist',1),
        (3,'lab','Supervisor Lab Demo','lab_supervisor',1), (4,'teknisi','Teknisi Demo','technician',1),
        (5,'qc','QC Demo','qc',1), (6,'fat','FAT Demo','finance',1),
        (7,'direktur','Direktur Demo','director',1), (8,'mitra','Klinik Mitra Demo','partner',2),
        (9,'pasien','Pasien Demo','patient',1), (10,'it','IT Demo','it_admin',1),
        (11,'dokter2','Dokter Klinik 2 Demo','dentist',1), (12,'lab2','Supervisor Lab 2 Demo','lab_supervisor',1),
        (13,'perawat','Perawat Demo','nurse',1), (14,'cadcam','CAD CAM Demo','cadcam',1),
        (15,'cs','Customer Service Demo','customer_service',1), (16,'gudang','Gudang Demo','warehouse',1),
        (17,'purchasing','Purchasing Demo','purchasing',1), (18,'hr','HR Demo','hr',1),
        (19,'marketing','Marketing Demo','marketing',1),
    ]
    demo_hash = pwd_hash(DEMO_PASSWORD)
    for ident, uname, name, role, org in people:
        db.add(User(id=ident, username=uname, display_name=name, role=role, org_id=org, password_hash=demo_hash, active=True))
    db.add_all([
        Patient(id=1, public_id='DEMO-P-001', display_name='Pasien Demo Satu', phone='+620000000001', org_id=1, user_id=9, contact_verified=True, service_consent=True, preferred_channel='portal', notification_level='standard'),
        Patient(id=2, public_id='DEMO-P-002', display_name='Pasien Demo Dua', phone='+620000000002', org_id=2, contact_verified=False, service_consent=False),
    ])
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
