import math
from datetime import date, datetime
from typing import Any, Optional, Tuple

from core.config import DISCOUNT_BY_DAYS
from core.models import AppState, Record, Records


# ============================================================ COMMON HELPERS ============================================================

def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def next_id(records: Records, field: str, prefix: str) -> str:
    """Generate the next prefixed ID, such as U0001 or REP0001."""
    highest = 0

    for record in records:
        value = str(record.get(field, ""))
        suffix = value[len(prefix):] if value.startswith(prefix) else ""

        if suffix.isdigit():
            highest = max(highest, int(suffix))

    return f"{prefix}{str(highest + 1).zfill(4)}"


def find_record(records: Records, field: str, value: Any) -> Optional[Record]:
    for record in records:
        if record.get(field) == value:
            return record
    return None


def get_remaining_days(expiration_date: str) -> int:
    expiration = datetime.strptime(expiration_date, "%Y-%m-%d").date()
    return (expiration - date.today()).days


def calculate_discount(price: float, remaining_days: int) -> Tuple[float, int]:
    """Return the discounted price and percentage. Expired items cannot be sold."""
    if remaining_days < 0:
        return 0.0, 0

    if remaining_days == 0:
        percent = DISCOUNT_BY_DAYS["same_day"]
    elif remaining_days > 7:
        percent = DISCOUNT_BY_DAYS["above_7_days"]
    else:
        percent = DISCOUNT_BY_DAYS.get(remaining_days, 10)

    return round(price * (1 - percent / 100), 2), percent


def get_owner_store(user: Record, stores: Records) -> Optional[Record]:
    return find_record(stores, "owner_id", user.get("user_id"))


def read_number(prompt: str, cast: type) -> Optional[Any]:
    """Read a number; return None when the input is not a valid number."""
    try:
        value = cast(input(prompt).strip())
    except ValueError:
        return None

    if cast is float and not math.isfinite(value):
        return None
    return value


def all_accounts(state: AppState) -> Records:
    return state.users + state.admins + state.super_admins
