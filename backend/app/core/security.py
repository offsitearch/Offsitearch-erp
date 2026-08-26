import secrets
import string
import uuid
from datetime import date, datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings
from app.utils.shared import now_local


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))


def generate_numeric_password(length: int = 6) -> str:
    digits = string.digits
    return "".join(secrets.choice(digits) for _ in range(length))


def format_login_id(year: int, sequence: int) -> str:
    """6-digit user login id: ``YY####`` (e.g. year 2026 seq 1 -> ``260001``).

    Sequence is capped at 9999; callers must guarantee uniqueness.
    """
    return f"{year % 100:02d}{min(sequence, 9999):04d}"


def generate_email(name: str, joining_date: date | None = None) -> str:
    first_name = name.strip().split()[0].lower()
    first_name = "".join(c for c in first_name if c.isalnum())
    ref = joining_date or now_local().date()
    ddmm = f"{ref.day:02d}{ref.month:02d}"
    return f"{first_name}{ddmm}@offsitearch.com"


def create_access_token(subject: int, level: str, token_version: int = 0) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(subject),
        "level": level,
        "type": "access",
        "jti": str(uuid.uuid4()),
        "tvp": token_version,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: int, token_version: int = 0) -> tuple[str, str, datetime]:
    jti = str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": str(subject),
        "jti": jti,
        "type": "refresh",
        "tvp": token_version,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token, jti, expire


def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
