"""Explicit, password-protected temporary hosting; never a production switch."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from typing import Mapping

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse


@dataclass(frozen=True)
class DemoRuntime:
    hosted: bool = False
    opted_in: bool = False
    access_password: str = field(default='', repr=False)
    expires_at: datetime | None = None
    deployment: str = 'local'

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
                   deployment=env.get('VERCEL_URL', 'temporary-demo'))

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
        return None

    def database_url(self, local_url: str):
        if not self.hosted:
            return local_url
        # A hosted demo never opens a configured production/external database.
        # Each deployment/access-key pair has separate disposable scratch data.
        fingerprint = hashlib.sha256((self.deployment + '|' + self.access_password).encode()).hexdigest()[:24]
        path = Path(tempfile.gettempdir()) / f'nam-demo-{fingerprint}.sqlite3'
        return 'sqlite:///' + path.as_posix()

    def metadata(self):
        return {'mode': 'temporary_online_demo' if self.hosted else 'local_demo',
                'storage': 'ephemeral_per_instance' if self.hosted else 'local_sqlite',
                'expires_at': self.expires_at.isoformat() if self.hosted and self.expires_at else None}


def gate_response(request: Request, status: int, message: str, *, challenge=False):
    headers = {'WWW-Authenticate': 'Basic realm="NAM Demo Sementara", charset="UTF-8"'} if challenge else {}
    if request.url.path.startswith('/api/') or 'application/json' in request.headers.get('accept', ''):
        return JSONResponse({'detail': message}, status_code=status, headers=headers)
    return HTMLResponse('<!doctype html><html lang="id"><meta charset="utf-8">'
                        '<meta name="viewport" content="width=device-width,initial-scale=1">'
                        '<title>Naraya Aurentis - Demo sementara</title><main><h1>Demo Naraya Aurentis</h1><p>'
                        + escape(message) + '</p><p>Demo dengan data fiktif. Bukan layanan pasien sungguhan.</p></main></html>',
                        status_code=status, headers=headers)


def demo_access_gate(request: Request, runtime: DemoRuntime):
    if not runtime.hosted:
        return None
    problem = runtime.problem()
    if problem:
        message = ('Masa akses demo sementara telah berakhir. Hubungi pemilik proyek.' if problem == 'expired'
                   else 'Demo online belum diaktifkan dengan akses terbatas. Pemilik proyek perlu melengkapi konfigurasi deployment.')
        return gate_response(request, 410 if problem == 'expired' else 503, message)
    authorization = request.headers.get('authorization', '')
    valid = False
    if len(authorization) < 2048:
        try:
            scheme, raw = authorization.split(' ', 1)
            username, password = base64.b64decode(raw, validate=True).split(b':', 1)
            valid = (scheme.lower() == 'basic' and hmac.compare_digest(username, b'demo')
                     and hmac.compare_digest(password, runtime.access_password.encode()))
        except (ValueError, UnicodeError):
            pass
    if not valid:
        return gate_response(request, 401, 'Masuk dengan nama pengguna demo dan kunci akses yang diberikan pemilik proyek.', challenge=True)
    return None
