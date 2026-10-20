import hashlib
import hmac
import secrets
from datetime import datetime, timezone

def pwd_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 260_000).hex()
    return salt + ':' + key


def pwd_valid(password: str, encoded: str) -> bool:
    try:
        salt = encoded.split(':', 1)[0]
        return hmac.compare_digest(pwd_hash(password, salt), encoded)
    except ValueError:
        return False


def utcnow():
    return datetime.now(timezone.utc)
