"""Offset-aware input must preserve the intended WIB time and shift day."""
from datetime import date,datetime,timedelta
from sqlalchemy import select
import pytest
from test_api import client, login, post
from backend import database
from backend.models import Appointment,Shift,User


def test_jakarta_input_is_stored_in_utc_and_remains_nine_wib(client):
    h=login(client,'resepsionis')
    day=date.today()+timedelta(days=5)
    result=post(client,'/api/appointments',h,{'patient_id':1,'dentist_id':2,'scheduled_at':str(day)+'T09:00:00+07:00'})
    with database.SessionLocal() as db:
        stored=db.get(Appointment,result['id'])
        assert stored.scheduled_at.hour==2
    row=next(a for a in client.get('/api/appointments').json() if a['id']==result['id'])
    assert '02:00:00' in row['scheduled_at']


def test_shift_and_replacement_use_wib_day_across_midnight(client):
    h=login(client,'resepsionis')
    utc_day=date.today()+timedelta(days=5)
    with database.SessionLocal() as db:
        for ident in (2,11):
            shift=db.scalar(select(Shift).where(Shift.user_id==ident,Shift.shift_day==utc_day))
            shift.available=False
        db.commit()
    result=post(client,'/api/appointments',h,{'patient_id':1,'dentist_id':2,'scheduled_at':str(utc_day)+'T23:30:00Z'})
    post(client,f"/api/appointments/{result['id']}/replacement",h,{'dentist_id':11})


def test_naive_appointment_input_is_rejected(client):
    h=login(client,'resepsionis')
    day=date.today()+timedelta(days=5)
    post(client,'/api/appointments',h,{'patient_id':1,'dentist_id':2,'scheduled_at':str(day)+'T09:00:00'},422)


@pytest.mark.parametrize('invalid',['inactive','tenant'])
def test_unavailable_doctor_cannot_be_scheduled_or_proposed(client,invalid):
    h=login(client,'resepsionis')
    with database.SessionLocal() as db:
        for ident in (2,11):
            doctor=db.get(User,ident)
            if invalid=='inactive':doctor.active=False
            else:doctor.org_id=2
        db.commit()
    day=date.today()+timedelta(days=5)
    post(client,'/api/appointments',h,{'patient_id':1,'dentist_id':2,'scheduled_at':str(day)+'T09:00:00+07:00'},400)
    post(client,'/api/appointments/1/replacement',h,{'dentist_id':11},400)
