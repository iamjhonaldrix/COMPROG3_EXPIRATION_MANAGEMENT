import os
import re


# ============================================================ CONFIGURATION ============================================================

# To add a new role, update: Configuration, AppState, JSONStorage, user_dashboard.

SUPER_ADMIN_FILE = "super_admin.json"
ADMIN_FILE = "admins.json"
USERS_FILE = "users.json"
STORES_FILE = "stores.json"
PRODUCTS_FILE = "products.json"
PURCHASES_FILE = "purchases.json"
REPORTS_FILE = "reports.json"
CHANGELOG_FILE = "changelogs.json"

STORAGE_DIR = "Storage"
CUSTOMER_DIR = os.path.join(STORAGE_DIR, "Customer")
STORES_DIR = os.path.join(STORAGE_DIR, "Stores")

STORE_REQUIRED_DOCUMENTS = [
    ("business_permit", "Business Permit"),
    ("food_inspection", "Food Inspection Permit"),
    ("inspection_records", "Inspection Record"),
    ("proof_ownership", "Proof of Ownership"),
    ("national_id", "National ID"),
]

CATEGORIES = [
    "FRESH PRODUCE",
    "DAIRY",
    "MEAT",
    "FROZEN",
    "PACKAGE",
    "CANNED",
    "DONATION",
    "OTHER",
]

# Units grouped by measurement type. Only Weight and Volume accept decimals.
UNITS = {
    "Weight": ["kg", "g"],
    "Volume": ["L", "mL"],
    "Count": ["piece", "pack", "box", "bottle", "can"],
    "Packaging": ["bag", "tray", "dozen", "jar", "tub", "bunch"],
}
DECIMAL_UNIT_TYPES = {"Weight", "Volume"}
UNIT_OPTIONS = [(unit, kind) for kind, units in UNITS.items() for unit in units]
DEFAULT_UNIT = "piece"  # used for products saved before units existed

DISCOUNT_BY_DAYS = {
    "same_day": 80,
    "above_7_days": 10,
    7: 20,
    6: 25,
    5: 30,
    4: 35,
    3: 40,
    2: 45,
    1: 50,
}

MIN_PASSWORD_LENGTH = 6
PASSWORD_ITERATIONS = 120_000

# Accepts 09XXXXXXXXX, +639XXXXXXXXX, or 639XXXXXXXXX.
PHONE_PATTERN = re.compile(r"^(?:\+?63|0)?(9\d{2})[\s-]?(\d{3})[\s-]?(\d{4})$")
