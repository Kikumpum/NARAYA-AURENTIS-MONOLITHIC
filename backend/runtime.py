"""Explicit, password-protected temporary hosting; never a production switch."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import json
import secrets
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from typing import Mapping

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

DEMO_COOKIE = 'nam_demo_access'
PUBLIC_PAGES = frozenset(('/', '/pasien', '/pasien/'))
# Login presentation assets are public; data and application sessions are protected.
PUBLIC_ASSETS = frozenset('/static/' + path for path in (
    'styles.css', 'portal.css', 'runtime.css', 'runtime.js', 'app.js', 'views.js',
    'actions.js', 'chat.js', 'sop.js', 'training.js', 'portal.js',
    'assets/naraya-aurentis-transparent.png',
))


@dataclass(frozen=True)
class DemoRuntime:
    hosted: bool = False
    opted_in: bool = False
    access_password: str = field(default='', repr=False)
    expires_at: datetime | None = None
    deployment: str = 'local'
    shared_database_enabled: bool = False
    shared_database_url: str = field(default='', repr=False)
    direct_database_url: str = field(default='', repr=False)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None):
        env = os.environ if env is None else env
        expires = None
        try:
            parsed = datetime.fromisoformat(env.get('NAM_DEMO_EXPIRES_AT', '').replace('Z', '+00:00'))
            if parsed.tzinfo is not None:
                expires = parsed.astimezone(timezone.utc)
        except ValueError:
            pass
        opted_in = env.get('NAM_ONLINE_DEMO') == '1'
        return cls(hosted=env.get('VERCEL') == '1' or opted_in, opted_in=opted_in,
                   access_password=env.get('NAM_DEMO_ACCESS_PASSWORD', ''), expires_at=expires,
                   deployment=env.get('VERCEL_URL', 'temporary-demo'),
                   shared_database_enabled=env.get('NAM_DEMO_SHARED_DATABASE') == '1',
                   shared_database_url=env.get('NAM_DEMO_DATABASE_URL', ''),
                   direct_database_url=env.get('NAM_DEMO_DATABASE_URL_UNPOOLED', ''))

    def migration_url(self):
        """Only a direct connection to the same authorized demo database may migrate."""
        if not self.hosted or not self.shared_database_enabled:
            return None
        try:
            pooled, direct = make_url(self.shared_database_url), make_url(self.direct_database_url)
            if (self.valid_shared_database() and direct.drivername in ('postgres','postgresql','postgresql+psycopg')
                and direct.host == pooled.host.replace('-pooler.', '.')
                and (direct.database,direct.username,direct.password,direct.port) ==
                    (pooled.database,pooled.username,pooled.password,pooled.port)
                and direct.query.get('sslmode') in ('require','verify-ca','verify-full')):
                return direct.set(drivername='postgresql+psycopg').render_as_string(hide_password=False)
        except (ArgumentError, ValueError, TypeError, AttributeError):
            pass
        raise RuntimeError('A matching direct demo database connection is required for migrations.')

    def valid_shared_database(self):
        try:
            url = make_url(self.shared_database_url)
            return (url.drivername in ('postgres', 'postgresql', 'postgresql+psycopg')
                    and bool(url.host and url.database and url.username and url.password)
                    and url.query.get('sslmode') in ('require', 'verify-ca', 'verify-full'))
        except (ArgumentError, ValueError, TypeError):
            return False

    def problem(self, now: datetime | None = None):
        if not self.hosted:
            return None
        now = now or datetime.now(timezone.utc)
        if not self.opted_in:
            return 'not_enabled'
        if len(self.access_password) < 24:
            return 'missing_access_key'
        if not self.expires_at or self.expires_at > now + timedelta(days=31):
            return 'invalid_expiry'
        if self.expires_at <= now:
            return 'expired'
        if self.shared_database_enabled and not self.valid_shared_database():
            return 'invalid_shared_database'
        return None

    def database_url(self, local_url: str):
        if not self.hosted:
            return local_url
        if self.shared_database_enabled and self.valid_shared_database():
            # Only the explicitly authorized demo URL is eligible. Never fall
            # back to a general DATABASE_URL that might point to real data.
            return make_url(self.shared_database_url).set(drivername='postgresql+psycopg').render_as_string(hide_password=False)
        # A hosted demo never opens a configured production/external database.
        # Each deployment/access-key pair has separate disposable scratch data.
        fingerprint = hashlib.sha256((self.deployment + '|' + self.access_password).encode()).hexdigest()[:24]
        path = Path(tempfile.gettempdir()) / f'nam-demo-{fingerprint}.sqlite3'
        return 'sqlite:///' + path.as_posix()

    def metadata(self):
        return {'mode': 'temporary_online_demo' if self.hosted else 'local_demo',
                'storage': ('shared_postgresql' if self.shared_database_enabled and self.valid_shared_database()
                            else 'ephemeral_per_instance') if self.hosted else 'local_sqlite',
                'expires_at': self.expires_at.isoformat() if self.hosted and self.expires_at else None}


def gate_response(request: Request, status: int, message: str):
    if request.url.path.startswith('/api/') or 'application/json' in request.headers.get('accept', ''):
        return JSONResponse({'detail': message}, status_code=status)
    return HTMLResponse('<!doctype html><html lang="id"><meta charset="utf-8">'
                        '<meta name="viewport" content="width=device-width,initial-scale=1">'
                        '<title>Naraya Aurentis - Demo sementara</title><main><h1>Demo Naraya Aurentis</h1><p>'
                        + escape(message) + '</p><p>Demo dengan data fiktif. Bukan layanan pasien sungguhan.</p></main></html>',
                        status_code=status)


def _signature(runtime: DemoRuntime, encoded: str):
    return hmac.new(runtime.access_password.encode(), ('nam-demo-gate:' + encoded).encode(), hashlib.sha256).hexdigest()


def gate_cookie(runtime: DemoRuntime):
    now = datetime.now(timezone.utc)
    until = min(int((now + timedelta(hours=8)).timestamp()), int(runtime.expires_at.timestamp()))
    payload = {'aud': 'temporary_demo', 'exp': until, 'deployment': runtime.deployment,
               'nonce': secrets.token_urlsafe(18)}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(',', ':')).encode()).decode().rstrip('=')
    return encoded + '.' + _signature(runtime, encoded), max(1, until - int(now.timestamp()))


def has_demo_access(request: Request, runtime: DemoRuntime):
    token = request.cookies.get(DEMO_COOKIE, '')
    if token and len(token) < 2048:
        try:
            encoded, signature = token.split('.', 1)
            if hmac.compare_digest(signature, _signature(runtime, encoded)):
                data = json.loads(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)))
                if (isinstance(data, dict) and data.get('aud') == 'temporary_demo'
                    and data.get('deployment') == runtime.deployment
                    and isinstance(data.get('exp'), int)
                    and datetime.now(timezone.utc).timestamp() < data['exp'] <= runtime.expires_at.timestamp()):
                    return True
        except (ValueError, UnicodeError, TypeError, AttributeError):
            pass
    return has_basic_access(request, runtime)


def has_basic_access(request: Request, runtime: DemoRuntime):
    # Compatibility for CLI/API checks; browser access uses the form and cookie.
    authorization = request.headers.get('authorization', '')
    if len(authorization) < 2048:
        try:
            scheme, raw = authorization.split(' ', 1)
            username, password = base64.b64decode(raw, validate=True).split(b':', 1)
            return (scheme.lower() == 'basic' and hmac.compare_digest(username, b'demo')
                    and hmac.compare_digest(password, runtime.access_password.encode()))
        except (ValueError, UnicodeError):
            pass
    return False


def demo_access_gate(request: Request, runtime: DemoRuntime):
    if not runtime.hosted:
        return None
    if request.method in ('GET', 'HEAD') and request.url.path in PUBLIC_PAGES | PUBLIC_ASSETS | {'/api/demo/status'}:
        return None
    problem = runtime.problem()
    if problem:
        message = ('Masa akses demo sementara telah berakhir. Hubungi pemilik proyek.' if problem == 'expired'
                   else 'Demo online belum diaktifkan dengan akses terbatas. Pemilik proyek perlu melengkapi konfigurasi deployment.')
        return gate_response(request, 410 if problem == 'expired' else 503, message)
    if request.method == 'POST' and request.url.path == '/api/demo/access':
        return None
    if not has_demo_access(request, runtime):
        return gate_response(request, 401, 'Masukkan kunci akses demo melalui halaman masuk aplikasi.')
    return None
