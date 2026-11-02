import json
import os
import re
import shutil
import tkinter as tk
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from tkinter import filedialog
from typing import Any, Dict, List, Optional, Tuple


#Simplify function parameters that stores data

"""REMOVE THIS COMMENT AFTER TEST, PATEST UNG CODE NG MY TKINTER IF GAGANA,DI KO MATEST S CP"""

Record = Dict[str, Any]
Records = List[Record]


#FOR FUNCTIONS,WHEN USING TYPE MARKERS,YOU CAN USE A FUNCTIONS NAME FOR A MARKER SO IT IS MUCJ MORE READABLE

# ============================================================ CONFIGURATION ============================================================

#FOR ADDING NEW ROLES,CHANGE THE FOLLOWING SECTIONS

"""
* Configuration
* Application State Class
* Json Storage Class

"""

SUPER_ADMIN_FILE = "super_admin.json"
ADMIN_FILE = "admins.json"
USERS_FILE = "users.json"
STORES_FILE = "stores.json"
PRODUCTS_FILE = "products.json"
PURCHASES_FILE = "purchases.json"
REPORTS_FILE = "reports.json"

STORAGE_DIR = "Storage"
CUSTOMER_DIR = "Customer"
STORES_DIR = "Stores"

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

# Accepts 09XXXXXXXX, +639XXXXXXXX, or 639XXXXXXXX.
PHONE_PATTERN = re.compile(
    r"^(?:\+?63|0)?(9\d{2})[\s-]?(\d{3})[\s-]?(\d{4})$"
)


""" ============================================================
APPLICATION STATE AND JSON STORAGE ============================================================
"""


#Implemented this to avoid bloated parameters
@dataclass
class AppState:
    """Holds the application's in-memory collections in one object."""

    users: Records
    admins: Records
    super_admins: Records
    stores: Records
    products: Records
    purchases: Records
    reports: Records

#Use static method when adding meta features such as load and save and place them under a class

class JSONStorage:
    """Loads and saves the application's JSON collections."""

    DEFAULTS = {
        SUPER_ADMIN_FILE: [
            {
                "username": "superadmin",
                "password": "superadmin",
                "role": "Super Admin",
                "date_created": None,
            }
        ],
        ADMIN_FILE: [
            {
                "username": "admin",
                "password": "admin",
                "role": "Admin",
                "date_created": None,
            }
        ],
    }

    FILES = {
        "users": USERS_FILE,
        "admins": ADMIN_FILE,
        "super_admins": SUPER_ADMIN_FILE,
        "stores": STORES_FILE,
        "products": PRODUCTS_FILE,
        "purchases": PURCHASES_FILE,
        "reports": REPORTS_FILE,
    }

    @staticmethod
    def save(filename: str, records: Any):
        #Use type markers like the function above to indicate the data that this function wants to receive
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(records, file, indent=4, ensure_ascii=False)
            
    #USE CLASSMETHOD WHEN THE M3THOD USES CLASS OBJECTS FROM ITS OWN PARENT

    @classmethod
    def load(cls, filename: str):
        default = cls.DEFAULTS.get(filename, [])

        if not os.path.exists(filename):
            records = cls._with_default_timestamps(default)
            cls.save(filename, records)
            return records

        try:
            with open(filename, "r", encoding="utf-8") as file:
                records = json.load(file)

            if not isinstance(records, list):
                raise ValueError("Expected a JSON list.")

            return records

        except (json.JSONDecodeError, ValueError, OSError):
            records = cls._with_default_timestamps(default)
            cls.save(filename, records)
            return records

    @staticmethod
    def _with_default_timestamps(records: Records) -> Records:
        copied = [dict(record) for record in records]
        for record in copied:
            if record.get("date_created") is None:
                record["date_created"] = timestamp()
        return copied
       
       
      

    @classmethod
    def load_state(cls) -> AppState:
        state = AppState(
            users=cls.load(USERS_FILE),
            admins=cls.load(ADMIN_FILE),
            super_admins=cls.load(SUPER_ADMIN_FILE),
            stores=cls.load(STORES_FILE),
            products=cls.load(PRODUCTS_FILE),
            purchases=cls.load(PURCHASES_FILE),
            reports=cls.load(REPORTS_FILE),
        )

        if organize_verification_documents(state.users):
            cls.save(USERS_FILE, state.users)

        return state

    @classmethod
    def save_state(cls, state: AppState) -> None:
        for attribute, filename in cls.FILES.items():
            cls.save(filename, getattr(state, attribute))


""" ============================================================
COMMON HELPERS
============================================================
"""

"""Create Helper functions to reduce bloating on other functions. Compile all Helper functions in this field."""


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
    """Return discounted price and percentage. Expired items cannot be sold."""
    if remaining_days < 0:
        return 0.0, 0

    if remaining_days == 0:
        percent = DISCOUNT_BY_DAYS["same_day"]
    elif remaining_days > 7:
        percent = DISCOUNT_BY_DAYS["above_7_days"]
    else:
        percent = DISCOUNT_BY_DAYS.get(remaining_days, 10)

    discounted_price = round(price * (1 - percent / 100), 2)
    return discounted_price, percent


def get_owner_store(user: Record, stores: Records) -> Optional[Record]:
    return find_record(stores, "owner_id", user.get("user_id"))


def save_state(state: AppState) -> None:
    JSONStorage.save_state(state)


""" ============================================================
VERIFICATION DOCUMENTS
============================================================
"""

def organize_verification_documents(users: Records) -> bool:
    """Move referenced files from Storage into role-specific user folders."""
    if not users:
        return False

    storage_root = os.path.abspath(STORAGE_DIR)
    changed = False

    for user in users:
        if not isinstance(user, dict):
            continue

        user_id = user.get("user_id")
        documents = user.get("verification_docs", {})

        if not user_id or not isinstance(documents, dict):
            continue

        base_dir = STORES_DIR if user.get("role") == "Store Owner" else CUSTOMER_DIR
        user_directory = os.path.abspath(os.path.join(base_dir, str(user_id)))

        for key, stored_path in list(documents.items()):
            if not isinstance(stored_path, str) or not stored_path:
                continue

            source = os.path.abspath(stored_path)

            try:
                inside_storage = os.path.commonpath(
                    [storage_root, source]
                ) == storage_root
            except ValueError:
                inside_storage = False

            if not inside_storage or not os.path.isfile(source):
                continue

            filename = os.path.basename(source)
            if not filename.lower().startswith(f"{key.lower()}_"):
                filename = f"{key}_{filename}"

            destination = os.path.join(user_directory, filename)

            if os.path.normcase(source) == os.path.normcase(destination):
                continue

            os.makedirs(user_directory, exist_ok=True)

            if os.path.exists(destination):
                stem, extension = os.path.splitext(filename)
                unique_stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                filename = f"{stem}_{unique_stamp}{extension}"
                destination = os.path.join(user_directory, filename)

            shutil.move(source, destination)
            documents[key] = os.path.relpath(destination)
            changed = True

    return changed


def verification_upload_status(path: Optional[str]) -> str:
    if not path:
        return "NOT UPLOADED"
    return "UPLOADED" if os.path.isfile(path) else "FILE NOT FOUND"


def upload_document(document_name: str, user: Record) -> Optional[str]:
    """Open a file picker and copy the selected image into Storage."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    try:
        selected_path = filedialog.askopenfilename(
            title=f"Select {document_name}",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png")],
        )
    finally:
        root.destroy()

    if not selected_path:
        print("Upload cancelled.")
        return None

    user_directory = os.path.join(STORAGE_DIR, user["user_id"])
    os.makedirs(user_directory, exist_ok=True)

    document_type = document_name.lower().replace(" ", "_")
    unique_stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{document_type}_{unique_stamp}_{os.path.basename(selected_path)}"
    destination = os.path.join(user_directory, filename)

    shutil.copy2(selected_path, destination)
    print(f"Saved document to {destination}")
    return destination


def verification_menu(user: Record, state: AppState) -> None:
    user.setdefault("verification_docs", {})

    while True:
        print("\n--- VERIFICATION DETAILS ---")
        print("1. Update phone number")
        print("2. Upload verification proof")
        print("3. Save and return")

        choice = input("Select: ").strip()

        if choice == "1":
            phone = input("Phone number: ").strip()
            if not PHONE_PATTERN.fullmatch(phone):
                print("Invalid mobile number.")
                continue
            user["phone"] = phone

        elif choice == "2":
            if user.get("role") == "Store Owner":
                documents = [
                    ("business_permit", "Business Permit"),
                    ("food_inspection", "Food Inspection Permit"),
                    ("inspection_records", "Inspection Record"),
                    ("proof_ownership", "Proof of Ownership"),
                ]
            else:
                documents = [("national_id", "National ID")]

            while True:
                docs = user["verification_docs"]
                print("\n--- DOCUMENT VERIFICATION UPLOAD ---")

                for number, (key, label) in enumerate(documents, start=1):
                    status = verification_upload_status(docs.get(key))
                    print(f"[{number}] {label}: {status}")

                back_choice = len(documents) + 1
                print(f"[{back_choice}] Save & Back")
                selected = input(
                    f"\nSelect document to upload [1-{back_choice}]: "
                ).strip()

                if selected == str(back_choice):
                    save_state(state)
                    print("Verification documents saved.")
                    break

                if not selected.isdigit() or not (
                    1 <= int(selected) <= len(documents)
                ):
                    print("Invalid choice.")
                    continue

                key, label = documents[int(selected) - 1]
                path = upload_document(label, user)
                if path:
                    docs[key] = path

        elif choice == "3":
            save_state(state)
            print("Details saved.")
            return

        else:
            print("Invalid choice.")


""" ============================================================
 REGISTRATION AND LOGIN
============================================================
"""

#Main app loop logic is here. Did not separate controls/input from the UI(no time)

def register_user(state: AppState) -> None:
    print("\n--- REGISTER ---")
    print("1. Customer\n2. Store Owner")
    role_choice = input("Select role: ").strip()

    if role_choice not in ("1", "2"):
        print("Invalid role.")
        return

    role = "Customer" if role_choice == "1" else "Store Owner"

    username = input("Username: ").strip()
    if not username:
        print("Username cannot be empty.")
        return

    all_accounts = state.users + state.admins + state.super_admins
    if any(
        account.get("username", "").lower() == username.lower()
        for account in all_accounts
    ):
        print("Username is already taken.")
        return

    password = input("Password: ").strip()
    if not password:
        print("Password cannot be empty.")
        return

    phone = input("Phone number: ").strip()
    if not PHONE_PATTERN.fullmatch(phone):
        print("Invalid mobile number.")
        return

    area = input("City/Area: ").strip().upper()
    status = "Pending" if role == "Store Owner" else "Approved"

    user = {
        "user_id": next_id(state.users, "user_id", "U"),
        "username": username,
        "password": password,
        "role": role,
        "phone": phone,
        "area": area,
        "status": status,
        "trust_score": 0,
        "date_created": timestamp(),
        "verification_docs": {},
    }
    state.users.append(user)

    if role == "Store Owner":
        store_name = input("Store name: ").strip()
        if not store_name:
            state.users.remove(user)
            print("Store name cannot be empty. Registration cancelled.")
            return

        state.stores.append(
            {
                "store_id": next_id(state.stores, "store_id", "S"),
                "owner_id": user["user_id"],
                "store_name": store_name,
                "area": area,
                "status": "Pending",
                "trust_score": 0,
                "date_created": timestamp(),
            }
        )
        print(
            "Store application submitted. An admin must approve it "
            "before products can be posted."
        )
    else:
        print("Customer account created.")

    save_state(state)


def login_user(state: AppState) -> Optional[Record]:
    print("\n--- LOGIN ---")
    username = input("Username: ").strip()
    password = input("Password: ").strip()

    for account in state.super_admins + state.admins:
        if (
            username
            and password
            and account.get("username", "").lower() == username.lower()
            and account.get("password") == password
        ):
            user = dict(account)
            user["role"] = account.get(
                "role",
                "Super Admin" if account in state.super_admins else "Admin",
            )
            user["status"] = "Approved"
            user["trust_score"] = 0
            print(f"Welcome, {user['username']} ({user['role']})!")
            return user

    for account in state.users:
        if (
            username
            and password
            and account.get("username", "").lower() == username.lower()
            and account.get("password") == password
        ):
            print(f"Welcome, {account['username']} ({account['role']})!")
            return account

    print("Incorrect username or password.")
    return None


""" ===========================================================
PRODUCT LISTING AND EXPIRATION
============================================================
"""

#Majority of the feature logic goes here

def expiry_guard(state: AppState) -> None:
    """Mark expired listings without deleting their records."""
    changed = False

    for product in state.products:
        try:
            remaining = get_remaining_days(product["expiration_date"])
            if remaining < 0 and product.get("status") != "Expired":
                product["status"] = "Expired"
                product["last_updated"] = timestamp()
                changed = True
        except (KeyError, TypeError, ValueError):
            if product.get("status") != "Removed":
                product["status"] = "Removed"
                product["last_updated"] = timestamp()
                changed = True

    if changed:
        save_state(state)


def post_product(user: Record, state: AppState) -> None:
    store = get_owner_store(user, state.stores)
    if not store or store.get("status") != "Approved":
        print("Your store must be approved before you can post products.")
        return

    print("\n--- POST PRODUCT ---")
    name = input("Product name: ").strip()
    if not name:
        print("Product name cannot be empty.")
        return

    for number, category in enumerate(CATEGORIES, 1):
        print(f"{number}. {category}")

    try:
        category_number = int(input("Category number: ").strip())
        price = float(input("Original price (PHP): ").strip())
        quantity = int(input("Quantity: ").strip())
        days = int(input("Days until expiration (0 = today): ").strip())

        if not 1 <= category_number <= len(CATEGORIES):
            raise ValueError
    except ValueError:
        print("Enter valid numbers for category, price, quantity, and expiration days.")
        return

    if price <= 0 or quantity <= 0 or days < 0:
        print("Price and quantity must be positive. Expiration days cannot be negative.")
        return

    category = CATEGORIES[category_number - 1]
    expiration_date = (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")
    final_price, percent = calculate_discount(price, days)

    print(
        f"Expiration: {expiration_date} | Discount: {percent}% | "
        f"Price after discount: PHP {final_price:.2f}"
    )

    if input("Confirm post? (y/n): ").strip().lower() != "y":
        print("Posting cancelled.")
        return

    state.products.append(
        {
            "product_id": next_id(state.products, "product_id", "P"),
            "store_id": store["store_id"],
            "name": name,
            "category": category,
            "original_price": round(price, 2),
            "quantity": quantity,
            "expiration_date": expiration_date,
            "status": "Available",
            "date_posted": timestamp(),
            "last_updated": timestamp(),
        }
    )

    save_state(state)
    print("Product posted successfully.")


def browse_products(user: Record, state: AppState) -> None:
    expiry_guard(state)

    print("\n--- BROWSE PRODUCTS ---")
    print(f"Your area: {user.get('area', '')}. Leave area blank to search all areas.")
    area_filter = input("Area filter: ").strip().upper()
    name_filter = input("Product name filter (blank for all): ").strip().lower()

    print("0. All categories")
    for number, category in enumerate(CATEGORIES, 1):
        print(f"{number}. {category}")

    category_input = input("Category number: ").strip()
    selected_category = None

    if category_input:
        try:
            category_number = int(category_input)
            if category_number == 0:
                selected_category = None
            elif 1 <= category_number <= len(CATEGORIES):
                selected_category = CATEGORIES[category_number - 1]
            else:
                raise ValueError
        except ValueError:
            print("Invalid category.")
            return

    matches = []

    for product in state.products:
        if product.get("status") != "Available" or product.get("quantity", 0) <= 0:
            continue

        try:
            if get_remaining_days(product["expiration_date"]) < 0:
                continue
        except (KeyError, TypeError, ValueError):
            continue

        store = find_record(state.stores, "store_id", product.get("store_id"))
        if not store or store.get("status") != "Approved":
            continue

        if area_filter and store.get("area", "").upper() != area_filter:
            continue
        if name_filter and name_filter not in product.get("name", "").lower():
            continue
        if selected_category and product.get("category") != selected_category:
            continue

        matches.append((product, store))

    # Products from the customer's area appear first.
    matches.sort(
        key=lambda item: (
            item[1].get("area", "").upper() != user.get("area", "").upper()
        )
    )

    if not matches:
        print("No products matched your search.")
        return

    for product, store in matches:
        price, percent = calculate_discount(
            product["original_price"],
            get_remaining_days(product["expiration_date"]),
        )
        print(f"\n{product['product_id']} | {product['name']} | {product['category']}")
        print(
            f"Store: {store['store_name']} | Area: {store['area']} | "
            f"Stock: {product['quantity']}"
        )
        print(
            f"Expires: {product['expiration_date']} | "
            f"PHP {price:.2f} ({percent}% off)"
        )

    product_id = input("\nProduct ID to request (Enter to cancel): ").strip().upper()
    if not product_id:
        return

    product = find_record(state.products, "product_id", product_id)
    if not product or product.get("status") != "Available":
        print("Product is not available.")
        return

    store = find_record(state.stores, "store_id", product.get("store_id"))
    if not store or store.get("status") != "Approved":
        print("Store is not approved.")
        return

    available_stock = product.get("quantity", 0)
    if available_stock <= 0:
        print("Product is out of stock.")
        return

    try:
        quantity = int(input(f"Quantity to request (1-{available_stock}): ").strip())
    except ValueError:
        print("Enter a valid quantity.")
        return

    if quantity <= 0 or quantity > available_stock:
        print(f"Invalid quantity! Available stock is {available_stock}.")
        return

    try:
        remaining_days = get_remaining_days(product["expiration_date"])
    except (KeyError, TypeError, ValueError):
        print("Product has an invalid expiration date.")
        return

    if remaining_days < 0:
        print("Expired products cannot be purchased.")
        return

    print("1. Store Pickup\n2. Same-Day Express (arranged with store)")
    fulfillment_choice = input("Choose fulfillment: ").strip()
    if fulfillment_choice not in ("1", "2"):
        print("Invalid fulfillment option.")
        return

    fulfillment = (
        "Store Pickup" if fulfillment_choice == "1" else "Same-Day Express"
    )
    unit_price, percent = calculate_discount(
        product["original_price"], remaining_days
    )

    purchase = {
        "purchase_id": next_id(state.purchases, "purchase_id", "R"),
        "customer_id": user["user_id"],
        "store_id": store["store_id"],
        "product_id": product["product_id"],
        "product_name": product["name"],
        "category": product["category"],
        "quantity": quantity,
        "unit_price": unit_price,
        "discount_percent": percent,
        "total_price": round(unit_price * quantity, 2),
        "fulfillment": fulfillment,
        "status": "Pending",
        "created_at": timestamp(),
        "updated_at": timestamp(),
    }

    state.purchases.append(purchase)
    save_state(state)
    print(
        f"Purchase request {purchase['purchase_id']} submitted. "
        "Receipt will be issued after confirmation."
    )
    
    


""" ============================================================
PURCHASE CONFIRMATION AND RECEIPT
============================================================
 """

"""THIS IS MAINLY FOR CLI PRESENTATION 

AVOID HEAVY LOGIC IN THIS SECTION"""


def print_receipt(purchase: Record) -> None:
    receipt_number = purchase.get("receipt_number", purchase["purchase_id"])
    confirmed_date = purchase.get("confirmed_at", purchase["created_at"])

    print("\n" + "=" * 40)
    print("             PURCHASE RECEIPT")
    print("=" * 40)
    print(f"Receipt No. : {receipt_number}")
    print(f"Date        : {confirmed_date}")
    print(f"Store ID    : {purchase['store_id']}")
    print(f"Product     : {purchase['product_name']}")
    print(f"Quantity    : {purchase['quantity']}")
    print(f"Unit Price  : PHP {purchase['unit_price']:.2f}")
    print(f"Discount    : {purchase['discount_percent']}%")
    print(f"Total       : PHP {purchase['total_price']:.2f}")
    print(f"Fulfillment : {purchase['fulfillment']}")
    print(f"Status      : {purchase['status']}")
    print("=" * 40)
    print("Thank you for helping reduce food waste!")


def review_purchase_requests(user: Record, state: AppState) -> None:
    store = get_owner_store(user, state.stores)
    if not store:
        print("No store record found.")
        return

    pending = [
        purchase for purchase in state.purchases
        if purchase.get("store_id") == store["store_id"]
        and purchase.get("status") == "Pending"
    ]

    if not pending:
        print("No pending purchase requests.")
        return

    for purchase in pending:
        print(
            f"\n{purchase['purchase_id']} | {purchase['product_name']} | "
            f"Qty: {purchase['quantity']} | Total: PHP {purchase['total_price']:.2f}"
        )
        print("1. Confirm\n2. Reject\n3. Leave pending")
        choice = input("Choose action: ").strip()

        if choice == "1":
            product = find_record(
                state.products, "product_id", purchase["product_id"]
            )
            customer = find_record(
                state.users, "user_id", purchase["customer_id"]
            )

            if not product or product.get("status") != "Available":
                print("Cannot confirm: product is unavailable.")
                continue

            try:
                expired = get_remaining_days(product["expiration_date"]) < 0
            except (KeyError, TypeError, ValueError):
                expired = True

            if expired:
                product["status"] = "Expired"
                product["last_updated"] = timestamp()
                print("Cannot confirm: product has expired or has an invalid expiry date.")
                continue

            if product.get("quantity", 0) < purchase["quantity"]:
                print("Cannot confirm: not enough stock.")
                continue

            product["quantity"] -= purchase["quantity"]
            product["last_updated"] = timestamp()

            if product["quantity"] == 0:
                product["status"] = "Sold Out"

            purchase["status"] = "Confirmed"
            purchase["confirmed_at"] = timestamp()
            purchase["updated_at"] = timestamp()
            purchase["receipt_number"] = purchase["purchase_id"]

            if customer:
                customer["trust_score"] = customer.get("trust_score", 0) + 1
            store["trust_score"] = store.get("trust_score", 0) + 1

            print_receipt(purchase)
            print("Purchase confirmed.")

        elif choice == "2":
            purchase["status"] = "Rejected"
            purchase["updated_at"] = timestamp()
            print("Purchase rejected.")

        elif choice == "3":
            continue

        else:
            print("Invalid choice.")

    save_state(state)


def view_my_purchases(user: Record, purchases: Records) -> None:
    own_purchases = [
        purchase for purchase in purchases
        if purchase.get("customer_id") == user.get("user_id")
    ]

    if not own_purchases:
        print("No purchase records found.")
        return

    print("\n--- MY PURCHASES ---")
    for purchase in own_purchases:
        print(
            f"{purchase['purchase_id']} | {purchase['product_name']} | "
            f"Qty: {purchase['quantity']} | PHP {purchase['total_price']:.2f} | "
            f"{purchase['status']}"
        )
        if purchase.get("status") in ("Confirmed", "Completed"):
            print_receipt(purchase)


""" ============================================================
 ADMIN APPROVAL AND REPORTS ============================================================
"""

def admin_panel(state: AppState) -> None:
    pending = [
        store for store in state.stores
        if store.get("status") == "Pending"
    ]

    if not pending:
        print("No pending store applications.")
        return

    print("\n--- STORE APPLICATIONS ---")

    for number, store in enumerate(pending, 1):
        owner = find_record(state.users, "user_id", store.get("owner_id"))
        owner_name = owner.get("username", "Unknown") if owner else "Unknown"
        documents = owner.get("verification_docs", {}) if owner else {}

        print(
            f"{number}. {store['store_id']} | {store['store_name']} | "
            f"Owner: {owner_name} | Area: {store['area']}"
        )

        document_keys = [
            ("business_permit", "Business Permit"),
            ("food_inspection", "Food Inspection Permit"),
            ("inspection_records", "Inspection Record"),
            ("proof_ownership", "Proof of Ownership"),
        ]
        statuses = [
            f"{label}: {verification_upload_status(documents.get(key))}"
            for key, label in document_keys
        ]

        if documents.get("business_document"):
            statuses.append(
                "Legacy Business Document: "
                + verification_upload_status(documents["business_document"])
            )

        print("   Verification: " + " | ".join(statuses))

    try:
        choice = int(input("Select application (0 to cancel): ").strip())
    except ValueError:
        print("Enter a valid number.")
        return

    if choice == 0:
        return
    if not 1 <= choice <= len(pending):
        print("Invalid selection.")
        return

    store = pending[choice - 1]
    owner = find_record(state.users, "user_id", store.get("owner_id"))
    verification_docs = owner.get("verification_docs", {}) if owner else {}

    print("\n--- OWNER VERIFICATION DOCUMENTS ---")
    document_labels = [
        ("business_permit", "Business Permit"),
        ("food_inspection", "Food Inspection Permit"),
        ("inspection_records", "Inspection Record"),
        ("proof_ownership", "Proof of Ownership"),
        ("national_id", "National ID"),
        ("business_document", "Legacy Business Document"),
    ]

    for key, label in document_labels:
        path = verification_docs.get(key)
        if path:
            print(f"{label}: {verification_upload_status(path)} - {path}")
        elif key != "business_document":
            print(f"{label}: NOT UPLOADED")

    print("1. Approve\n2. Reject\n3. Return")
    decision = input("Decision: ").strip()

    if decision == "1":
        store["status"] = "Approved"
        store["reviewed_at"] = timestamp()
        print("Store approved.")
    elif decision == "2":
        store["status"] = "Rejected"
        store["reviewed_at"] = timestamp()
        print("Store rejected.")
    elif decision == "3":
        return
    else:
        print("Invalid decision.")
        return

    save_state(state)


def create_report(user: Record, state: AppState) -> None:
    product_id = input("Product ID to report: ").strip().upper()
    product = find_record(state.products, "product_id", product_id)

    if not product:
        print("Product not found.")
        return

    reason = input("Reason for report: ").strip()
    if not reason:
        print("Report reason cannot be empty.")
        return

    state.reports.append(
        {
            "report_id": next_id(state.reports, "report_id", "REP"),
            "reporter_id": user["user_id"],
            "product_id": product["product_id"],
            "store_id": product["store_id"],
            "reason": reason,
            "status": "Pending",
            "created_at": timestamp(),
        }
    )

    save_state(state)
    print("Report submitted for review.")


def review_reports(state: AppState) -> None:
    pending = [
        report for report in state.reports
        if report.get("status") == "Pending"
    ]

    if not pending:
        print("No pending reports.")
        return

    for report in pending:
        print(
            f"\n{report['report_id']} | Product: {report['product_id']} | "
            f"Reason: {report['reason']}"
        )
        choice = input(
            "Confirm report? (y/n, Enter to skip): "
        ).strip().lower()

        if choice not in ("y", "n"):
            continue

        report["status"] = "Confirmed" if choice == "y" else "Dismissed"
        report["reviewed_at"] = timestamp()

        if choice == "y":
            store = find_record(state.stores, "store_id", report["store_id"])
            product = find_record(
                state.products, "product_id", report["product_id"]
            )

            if store:
                store["trust_score"] = store.get("trust_score", 0) - 1
            if product:
                product["status"] = "Removed"
                product["last_updated"] = timestamp()

            print("Report confirmed. Listing removed and store trust score reduced.")
        else:
            print("Report dismissed.")

    save_state(state)


""" ============================================================
 ROLE DASHBOARDS
 ============================================================
"""


def user_dashboard(user: Record, state: AppState) -> None:
    while True:
        username = user["username"]
        role = user["role"]
        status = user.get("status", "Approved")
        trust = user.get("trust_score", 0)

        print(
            f"\n=== {username} | {role} | Status: {status} | Trust: {trust} ==="
        )

        if role in ("Admin", "Super Admin"):
            print("1. Review store applications\n2. Review reports\n0. Logout")
            choice = input("Choice: ").strip()

            if choice == "1":
                admin_panel(state)
            elif choice == "2":
                review_reports(state)
            elif choice == "0":
                return
            else:
                print("Invalid choice.")

        elif role == "Store Owner":
            store = get_owner_store(user, state.stores)
            if not store:
                print("Store application not found.")
                return

            print(f"Store: {store['store_name']} | Approval: {store['status']}")
            print(
                "1. Post product\n"
                "2. View my products\n"
                "3. Review purchase requests\n"
                "4. Verification details\n"
                "0. Logout"
            )
            choice = input("Choice: ").strip()

            if choice == "1":
                post_product(user, state)
            elif choice == "2":
                own_products = [
                    product for product in state.products
                    if product.get("store_id") == store["store_id"]
                ]

                if not own_products:
                    print("No products posted yet.")

                for product in own_products:
                    print(
                        f"{product['product_id']} | {product['name']} | "
                        f"Stock: {product['quantity']} | {product['status']}"
                    )
            elif choice == "3":
                review_purchase_requests(user, state)
            elif choice == "4":
                verification_menu(user, state)
            elif choice == "0":
                return
            else:
                print("Invalid choice.")

        elif role == "Customer":
            print(
                "1. Browse and request products\n"
                "2. View purchases/receipts\n"
                "3. Report product\n"
                "4. Verification details\n"
                "0. Logout"
            )
            choice = input("Choice: ").strip()

            if choice == "1":
                browse_products(user, state)
            elif choice == "2":
                view_my_purchases(user, state.purchases)
            elif choice == "3":
                create_report(user, state)
            elif choice == "4":
                verification_menu(user, state)
            elif choice == "0":
                return
            else:
                print("Invalid choice.")

        else:
            print("Unrecognized account role.")
            return


""" ============================================================
 MAIN
 ============================================================
 """

def main() -> None:
    state = JSONStorage.load_state()

    while True:
        expiry_guard(state)

        print("\n" + "=" * 42)
        print("              ZEROWASTE")
        print("=" * 42)
        print("1. Login\n2. Register\n0. Exit")

        choice = input("Select: ").strip()

        if choice == "1":
            user = login_user(state)
            if user:
                user_dashboard(user, state)

        elif choice == "2":
            register_user(state)

        elif choice == "0":
            save_state(state)
            print("Data saved. Goodbye!")
            break

        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
