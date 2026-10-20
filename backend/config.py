"""Local demonstration configuration. Production is deliberately blocked."""
import os
from pathlib import Path
from backend.runtime import DemoRuntime

BASE_DIR = Path(__file__).resolve().parent.parent
runtime = DemoRuntime.from_env()
DATABASE_URL = runtime.database_url(os.getenv('DATABASE_URL', 'sqlite:///./nam_demo.db'))
IS_PRODUCTION = os.getenv('NAM_ENV', 'demo').lower() == 'production'
COOKIE_SECURE = runtime.hosted or os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
DEMO_PASSWORD = os.getenv('NAM_DEMO_PASSWORD', 'DemoNAM2026!')
if IS_PRODUCTION:
    # Prevent accidental deployment of a seeded demonstration as a production service.
    raise RuntimeError('This demo is intentionally blocked in production. Follow SECURITY.md and ROADMAP.md.')
