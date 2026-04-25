"""
Password hashing utilities for Glasswatch.

Uses bcrypt directly to avoid passlib 1.7.4 + bcrypt 4.x compatibility issues.
passlib's CryptContext with bcrypt triggers a bug detection routine that fails
on bcrypt >= 4.0 when called with the 2a identifier.
"""
import bcrypt


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash."""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False
