import hashlib
import hmac
import os

from core.config import PASSWORD_ITERATIONS
from core.helpers import next_id, timestamp
from core.models import AppState, Record


# ---------- Passwords ----------

def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PASSWORD_ITERATIONS
    ).hex()
    return f"pbkdf2${salt}${digest}"


def is_hashed(stored: str) -> bool:
    return isinstance(stored, str) and stored.startswith("pbkdf2$")


def verify_password(stored: str, entered: str) -> bool:
    """Supports hashed passwords and legacy plain-text passwords."""
    if not is_hashed(stored):
        return hmac.compare_digest(str(stored), entered)

    try:
        _, salt, digest = stored.split("$")
        check = hashlib.pbkdf2_hmac(
            "sha256", entered.encode("utf-8"), bytes.fromhex(salt), PASSWORD_ITERATIONS
        ).hex()
    except ValueError:
        return False
    return hmac.compare_digest(digest, check)


def new_staff_account(admin_id: str, username: str, password: str, role: str) -> Record:
    return {
        "admin_id": admin_id,
        "username": username,
        "password": hash_password(password),
        "role": role,
        "active": True,
        "date_created": timestamp(),
    }


def normalize_staff_accounts(state: AppState) -> bool:
    """Add missing 'active' and 'admin_id' fields to older staff records."""
    changed = False

    for records, prefix in ((state.super_admins, "SA"), (state.admins, "A")):
        for account in records:
            if "active" not in account:
                account["active"] = True
                changed = True
            if not account.get("admin_id"):
                account["admin_id"] = next_id(records, "admin_id", prefix)
                changed = True

    return changed
