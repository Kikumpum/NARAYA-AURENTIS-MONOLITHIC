"""NAM DMS local demonstration: application assembly and static UI."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException
from pydantic import BaseModel, Field
import hmac
import logging
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from backend import database
from backend.config import BASE_DIR, runtime
from backend.runtime import DEMO_COOKIE, demo_access_gate, gate_cookie, has_demo_access
from backend.demo import seed, seed_staff_accounts
from backend.modules import auth, clinic, lab, finance, communication, operations, audit, chat, organization, sop_reports
from backend.modules import patient_portal, patient_visits, patient_inbox, training


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail closed without touching any database when hosting was not authorized/configured.
    if runtime.hosted and runtime.problem():
        yield
        return
    database.bootstrap_demo(seed, organization.seed_structure, seed_staff_accounts)
    yield


app = FastAPI(title='NAM DMS — DEMO ONLY', version='0.4.0', lifespan=lifespan,
              docs_url='/api/docs', openapi_url='/api/openapi.json')

@app.middleware('http')
async def security_headers(request: Request, call_next):
    response = demo_access_gate(request, runtime)
    if response is None:
        response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    if runtime.hosted:
        response.headers['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
    response.headers.setdefault('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
    return response

for domain in (auth, clinic, lab, finance, communication, operations, audit, chat, organization, sop_reports, patient_portal, patient_visits, patient_inbox, training):
    app.include_router(domain.router)


@app.get('/api/demo/status')
def demo_status(request: Request):
    problem = runtime.problem()
    return {**runtime.metadata(), 'available': problem is None,
            'authorized': not runtime.hosted or (problem is None and has_demo_access(request, runtime)),
            'message': ('Masa demo telah berakhir. Hubungi pemilik proyek.' if problem == 'expired' else
                        'Demo online belum dapat diakses. Hubungi pemilik proyek.' if problem else '')}


class DemoAccessIn(BaseModel):
    access_key: str = Field(min_length=1, max_length=512)


@app.post('/api/demo/access')
def unlock_demo(payload: DemoAccessIn, request: Request, response: Response):
    if not runtime.hosted:
        raise HTTPException(404, 'Akses demo online tidak diperlukan di komputer lokal')
    if (request.headers.get('origin') != str(request.base_url).rstrip('/')
        or request.headers.get('sec-fetch-site') == 'cross-site'):
        raise HTTPException(403, 'Asal permintaan tidak diizinkan')
    if not hmac.compare_digest(payload.access_key.encode(), runtime.access_password.encode()):
        logging.getLogger('nam.demo').info('demo_access.denied')
        raise HTTPException(401, 'Kunci akses belum sesuai. Periksa kembali kunci dari pemilik proyek.')
    if not has_demo_access(request, runtime):
        token, age = gate_cookie(runtime)
        response.set_cookie(DEMO_COOKIE, token, max_age=age, secure=True, httponly=True, samesite='strict', path='/')
        logging.getLogger('nam.demo').info('demo_access.granted')
    return {'authorized': True}

@app.get('/api/health')
def health():
    return {'status':'demo','version':'0.4.0','real_data_allowed':False,'chat_assistant':'mock','sop_catalog':'1.0-draf',
            **runtime.metadata()}


app.mount('/static',StaticFiles(directory=str(BASE_DIR/'frontend')),name='static')


@app.get('/')
def index():
    return FileResponse(BASE_DIR/'frontend'/'index.html')


@app.get('/pasien')
@app.get('/pasien/')
def patient_index():
    return FileResponse(BASE_DIR/'frontend'/'portal.html')
