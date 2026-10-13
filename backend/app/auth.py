"""Small, dependency-free password and signed-session helpers.

Passwords are stored using PBKDF2-SHA256 with a unique random salt.  Tokens are
HMAC-signed and expire; this keeps the first deploy simple while leaving the
HTTP contract compatible with a future identity provider.
"""
import base64, hashlib, hmac, json, secrets
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .config import settings
from .database import get_db

bearer = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 310_000)
    return f"pbkdf2_sha256${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"

def verify_password(password: str, encoded: str) -> bool:
    try:
        _, salt, expected = encoded.split('$')
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), base64.urlsafe_b64decode(salt), 310_000)
        return hmac.compare_digest(actual, base64.urlsafe_b64decode(expected))
    except (ValueError, TypeError):
        return False

def _secret() -> bytes:
    # A configured secret is mandatory outside local development.
    return (settings.auth_secret or 'local-development-secret-change-me').encode()

def create_token(user_id: str, workspace_id: str) -> str:
    payload = {'sub': user_id, 'workspace_id': workspace_id,
               'exp': int((datetime.now(timezone.utc) + timedelta(hours=settings.auth_token_hours)).timestamp())}
    raw = base64.urlsafe_b64encode(json.dumps(payload, separators=(',', ':')).encode()).decode().rstrip('=')
    signature = hmac.new(_secret(), raw.encode(), hashlib.sha256).hexdigest()
    return f'{raw}.{signature}'

def decode_token(token: str) -> dict:
    try:
        raw, signature = token.rsplit('.', 1)
        valid = hmac.compare_digest(signature, hmac.new(_secret(), raw.encode(), hashlib.sha256).hexdigest())
        payload = json.loads(base64.urlsafe_b64decode(raw + '=' * (-len(raw) % 4)))
        if not valid or payload['exp'] < datetime.now(timezone.utc).timestamp(): raise ValueError
        return payload
    except Exception as exc:
        raise HTTPException(401, 'Your session has expired. Please sign in again.') from exc

def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db=Depends(get_db)):
    if not credentials: raise HTTPException(401, 'Sign in is required.')
    claims = decode_token(credentials.credentials)
    from bson import ObjectId
    try: user = db.users.find_one({'_id': ObjectId(claims['sub']), 'workspace_id': claims['workspace_id']})
    except Exception: user = None
    if not user: raise HTTPException(401, 'Your account is no longer available.')
    return user
