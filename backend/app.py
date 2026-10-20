"""NAM DMS local demonstration: application assembly and static UI."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from backend import database
from backend.config import BASE_DIR, runtime
from backend.runtime import demo_access_gate
from backend.demo import seed
from backend.modules import auth, clinic, lab, finance, communication, operations, audit, chat, organization, sop_reports
from backend.modules import patient_portal, training


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail closed without touching any database when hosting was not authorized/configured.
    if runtime.hosted and runtime.problem():
        yield
        return
    database.upgrade_schema()
    with database.SessionLocal() as db:
        seed(db)
        organization.seed_structure(db)
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

for domain in (auth, clinic, lab, finance, communication, operations, audit, chat, organization, sop_reports, patient_portal, training):
    app.include_router(domain.router)

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
