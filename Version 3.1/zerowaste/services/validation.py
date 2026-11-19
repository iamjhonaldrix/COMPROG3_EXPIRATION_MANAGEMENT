import math
from typing import Any, Optional, Tuple

from core.config import (
    CATEGORIES,
    DECIMAL_UNIT_TYPES,
    PHONE_PATTERN,
    UNIT_OPTIONS,
    UNITS,
)
from core.ui import show_error


# ---------- Phone numbers ----------

def normalize_phone(raw: str) -> Optional[str]:
    """Return the number as 09XXXXXXXXX, or None if it is invalid."""
    match = PHONE_PATTERN.fullmatch(raw.strip())
    return "0" + "".join(match.groups()) if match else None


def prompt_phone() -> Optional[str]:
    """Ask until the phone number is valid. Returns None if cancelled."""
    while True:
        raw = input("Phone number (e.g. 09171234567, 0 to cancel): ").strip()
        if raw == "0":
            return None

        phone = normalize_phone(raw)
        if phone:
            return phone

        show_error(
            "Invalid mobile number. Use 09XXXXXXXXX, +639XXXXXXXXX, or "
            "639XXXXXXXXX (a Philippine mobile number starting with 9)."
        )


# ---------- Units and quantities ----------

def unit_allows_decimals(unit: str) -> bool:
    for kind, units in UNITS.items():
        if unit in units:
            return kind in DECIMAL_UNIT_TYPES
    return False


def quantity_rule(unit: str) -> str:
    if unit_allows_decimals(unit):
        return f"Decimals are allowed for {unit} (example: 2.5)."
    return f"Only whole numbers are allowed for {unit} (example: 5)."


def parse_quantity(text: str, unit: str) -> Optional[Any]:
    """Return a positive quantity valid for the unit, or None if invalid."""
    try:
        value = float(text)
    except ValueError:
        return None

    if not math.isfinite(value) or value <= 0:
        return None

    if unit_allows_decimals(unit):
        return round(value, 3)

    if value != int(value):
        return None
    return int(value)


def format_quantity(quantity: Any, unit: str) -> str:
    number = float(quantity)
    if number.is_integer():
        text = str(int(number))
    else:
        text = f"{number:.3f}".rstrip("0").rstrip(".")
    return f"{text} {unit}"


def prompt_unit() -> Optional[str]:
    print("\nSelect the unit of measurement:")
    print("Choose the unit customers will order and you will price by.")
    print("Stock quantity and price must use the same unit.")
    print("Examples:")
    print("  kg/g    - meat, fish, loose vegetables or fruit sold by weight")
    print("  piece   - whole chicken, cabbage, or another item sold individually")
    print("  bunch   - leafy vegetables or herbs sold in bunches")
    print("  L/mL    - liquids sold by volume")
    print("  pack, box, bottle, can, bag, tray, dozen, jar, tub - packaged goods")
    print("For example, 5 kg at PHP 200/kg means 5 kg in stock, priced per kg.")
    print("If those same items are sold individually, choose piece and price per item.")
    for number, (unit, kind) in enumerate(UNIT_OPTIONS, start=1):
        note = "decimals allowed" if kind in DECIMAL_UNIT_TYPES else "whole numbers only"
        print(f"{number:>2}. {unit:<7} [{kind} - {note}]")

    raw = input("Unit number (0 to cancel): ").strip()

    if raw.isdigit() and 1 <= int(raw) <= len(UNIT_OPTIONS):
        return UNIT_OPTIONS[int(raw) - 1][0]

    if raw != "0":
        show_error(f"Invalid unit. Enter a number from 1 to {len(UNIT_OPTIONS)}.")
    return None


def choose_category(allow_all: bool = False) -> Tuple[bool, Optional[str]]:
    """Return (is_valid, category). category None means 'all categories'."""
    if allow_all:
        print("0. All categories")
    for number, category in enumerate(CATEGORIES, 1):
        print(f"{number}. {category}")

    raw = input("Category number: ").strip()

    if allow_all and raw in ("", "0"):
        return True, None
    if raw.isdigit() and 1 <= int(raw) <= len(CATEGORIES):
        return True, CATEGORIES[int(raw) - 1]

    low = 0 if allow_all else 1
    show_error(f"Invalid category. Enter a number from {low} to {len(CATEGORIES)}.")
    return False, None
