"""
Password hashing utilities for Glasswatch.

Uses passlib bcrypt with truncate_error=False to handle passwords >= 72 bytes
gracefully (bcrypt silently truncates at 72 bytes, which is the expected behavior).
"""
from passlib.context import CryptContext

# Single shared password context used across the application
# truncate_error=False: don't raise ValueError for long passwords (bcrypt truncates silently)
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
    truncate_error=False,
)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)
