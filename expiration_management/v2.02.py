import json
import os
import shutil
import tkinter as tk
from tkinter import filedialog
from datetime import datetime, date, timedelta

# ============================================================
# CONFIGURATION
# ============================================================
USERS_FILE = "users.json"
STORES_FILE = "stores.json"
PRODUCTS_FILE = "products.json"
PURCHASES_FILE = "purchases.json"
REPORTS_FILE = "reports.json"
STORAGE_DIR = "Storage"

CATEGORIES = ["FRESH PRODUCE", "DAIRY", "MEAT",
              "FROZEN", "PACKAGE", "CANNED", "DONATION", "OTHER"]

DISCOUNT_BY_DAYS = {"same_day": 80, "above_7_days": 10,
                    7: 20, 6: 25, 5: 30, 4: 35, 3: 40, 2: 45, 1: 50}

# ============================================================
# JSON STORAGE AND ID HELPERS
# ============================================================
def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_json(filename):
    """Load a JSON list or create an empty file if it does not exist."""
    if not os.path.exists(filename):
        save_json(filename, [])
        return []
    try:
        with open(filename, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as error:
        print(f"[LOAD ERROR] {filename}: {error}")
        return []


def save_json(filename, data):
    """Save one list of records to its JSON file."""
    try:
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
    except OSError as error:
        print(f"[SAVE ERROR] {filename}: {error}")


def save_all(users, stores, products, purchases, reports):
    save_json(USERS_FILE, users)
    save_json(STORES_FILE, stores)
    save_json(PRODUCTS_FILE, products)
    save_json(PURCHASES_FILE, purchases)
    save_json(REPORTS_FILE, reports)


def next_id(records, field, prefix):
    """Generate IDs such as U0001, S0001, P0001, R0001, and REP0001."""
    highest = 0
    for record in records:
        value = str(record.get(field, ""))
        suffix = value[len(prefix):] if value.startswith(prefix) else ""
        if suffix.isdigit():
            highest = max(highest, int(suffix))
    return f"{prefix}{highest + 1:04d}"


def load_data():
    """Load each data collection and create an initial admin if needed."""
    users = load_json(USERS_FILE)
    stores = load_json(STORES_FILE)
    products = load_json(PRODUCTS_FILE)
    purchases = load_json(PURCHASES_FILE)
    reports = load_json(REPORTS_FILE)
    documents_reorganized = organize_verification_documents(users)

    if not any(user.get("role") == "Admin" for user in users):
        print("\nCreate the initial administrator account.")
        username = input("Admin username: ").strip()
        password = input("Admin password: ").strip()
        if username and password:
            users.append({
                "user_id": next_id(users, "user_id", "U"),
                "username": username,
                "password": password,
                "role": "Admin",
                "phone": "",
                "area": "",
                "status": "Approved",
                "trust_score": 0,
                "date_created": timestamp(),
            })
            save_all(users, stores, products, purchases, reports)
        else:
            print("Admin account not created. Restart and enter valid details.")
    if documents_reorganized:
        save_json(USERS_FILE, users)
    return users, stores, products, purchases, reports


# ============================================================
# COMMON LOOKUP AND DISCOUNT HELPERS
# ============================================================
def find_record(records, field, value):
    return next((record for record in records if record.get(field) == value), None)


def get_remaining_days(expiration_date):
    return (datetime.strptime(expiration_date, "%Y-%m-%d").date() - date.today()).days


def calculate_discount(price, remaining_days):
    """Return the discounted price and discount percentage; expired food is not sellable."""
    if remaining_days < 0:
        return 0.0, 0
    if remaining_days == 0:
        percent = DISCOUNT_BY_DAYS["same_day"]
    elif remaining_days > 7:
        percent = DISCOUNT_BY_DAYS["above_7_days"]
    else:
        percent = DISCOUNT_BY_DAYS.get(remaining_days, 10)
    return round(price * (1 - percent / 100), 2), percent


def get_owner_store(user, stores):
    return next((store for store in stores if store.get("owner_id") == user.get("user_id")), None)


def save_state(users, stores, products, purchases, reports):
    save_all(users, stores, products, purchases, reports)


# ============================================================
# DOCUMENT UPLOAD
# ============================================================
def organize_verification_documents(users):
    """Move referenced verification files into per-user folders."""
    storage_root = os.path.abspath(STORAGE_DIR)
    changed = False

    for user in users:
        user_id = user.get("user_id")
        documents = user.get("verification_docs", {})
        if not user_id or not isinstance(documents, dict):
            continue

        user_storage_dir = os.path.join(STORAGE_DIR, user_id)
        for key, stored_path in documents.items():
            if not isinstance(stored_path, str) or not stored_path:
                continue

            source_path = os.path.abspath(stored_path)
            try:
                is_in_storage = (
                    os.path.commonpath([storage_root, source_path]) == storage_root
                )
            except ValueError:
                is_in_storage = False
            if not is_in_storage or not os.path.isfile(source_path):
                continue

            basename = os.path.basename(source_path)
            if not basename.lower().startswith(f"{key.lower()}_"):
                basename = f"{key}_{basename}"
            destination = os.path.abspath(os.path.join(user_storage_dir, basename))
            if os.path.normcase(source_path) == os.path.normcase(destination):
                continue

            os.makedirs(user_storage_dir, exist_ok=True)
            if os.path.exists(destination):
                stem, extension = os.path.splitext(basename)
                destination = os.path.join(
                    user_storage_dir,
                    f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{extension}",
                )
            shutil.move(source_path, destination)
            documents[key] = os.path.relpath(destination)
            changed = True

    return changed


def verification_upload_status(path):
    if not path:
        return "NOT UPLOADED"
    return "UPLOADED" if os.path.isfile(path) else "FILE NOT FOUND"


def upload_document(document_name, user):
    """Save an uploaded image in the uploader's folder with its document type."""
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
    user_storage_dir = os.path.join(STORAGE_DIR, user["user_id"])
    os.makedirs(user_storage_dir, exist_ok=True)
    document_type = document_name.lower().replace(" ", "_")
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{document_type}_{timestamp_str}_{os.path.basename(selected_path)}"
    destination = os.path.join(user_storage_dir, filename)
    shutil.copy(selected_path, destination)
    print(f"Saved document to {destination}")
    return destination


def verification_menu(user, users, stores, products, purchases, reports):
    user.setdefault("verification_docs", {})
    while True:
        print("\n--- VERIFICATION DETAILS ---")
        print("1. Update phone number")
        print("2. Upload verification proof")
        print("3. Save and return")
        choice = input("Select: ").strip()
        if choice == "1":
            user["phone"] = input("Phone number: ").strip()
        elif choice == "2":
            if user["role"] == "Store Owner":
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
                    print(f"[{number}] {label}: {docs.get(key, 'NOT UPLOADED')}")
                back_choice = len(documents) + 1
                print(f"[{back_choice}] Save & Back")
                upload_choice = input(
                    f"\nSelect document to upload [1-{back_choice}]: ").strip()
                if upload_choice == str(back_choice):
                    save_state(users, stores, products, purchases, reports)
                    print("Verification documents saved.")
                    break
                if upload_choice.isdigit() and 1 <= int(upload_choice) <= len(documents):
                    key, label = documents[int(upload_choice) - 1]
                    path = upload_document(label, user)
                    if path:
                        docs[key] = path
                else:
                    print("Invalid choice.")
        elif choice == "3":
            save_state(users, stores, products, purchases, reports)
            print("Details saved.")
            return
        else:
            print("Invalid choice.")


# ============================================================
# REGISTRATION AND LOGIN
# ============================================================
def register_user(users, stores, products, purchases, reports):
    print("\n--- REGISTER ---")
    print("1. Customer\n2. Store Owner")
    role_choice = input("Select role: ").strip()
    if role_choice not in ("1", "2"):
        print("Invalid role.")
        return
    role = "Customer" if role_choice == "1" else "Store Owner"
    username = input("Username: ").strip()
    if not username or any(u.get("username", "").lower() == username.lower() for u in users):
        print("Username is empty or already taken.")
        return
    password = input("Password: ").strip()
    if not password:
        print("Password cannot be empty.")
        return
    phone = input("Phone number: ").strip()
    area = input("City/Area: ").strip().upper()

    user = {
        "user_id": next_id(users, "user_id", "U"),
        "username": username,
        "password": password,
        "role": role,
        "phone": phone,
        "area": area,
        "status": "Pending" if role == "Store Owner" else "Approved",
        "trust_score": 0,
        "date_created": timestamp(),
        "verification_docs": {},
    }
    users.append(user)

    if role == "Store Owner":
        store_name = input("Store name: ").strip()
        stores.append({
            "store_id": next_id(stores, "store_id", "S"),
            "owner_id": user["user_id"],
            "store_name": store_name,
            "area": area,
            "status": "Pending",
            "trust_score": 0,
            "date_created": timestamp(),
        })
        print("Store application submitted. An admin must approve it before products can be posted.")
    else:
        print("Customer account created.")
    save_state(users, stores, products, purchases, reports)


def login_user(users):
    print("\n--- LOGIN ---")
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    user = next((u for u in users if u.get("username", "").lower() == username.lower()
                 and u.get("password") == password), None)
    if user:
        print(f"Welcome, {user['username']} ({user['role']})!")
        return user
    print("Incorrect username or password.")
    return None


# ============================================================
# PRODUCT LISTING AND EXPIRATION
# ============================================================
def expiry_guard(users, stores, products, purchases, reports):
    """Keep old listings in the data and mark them Expired instead of deleting them."""
    changed = False
    for product in products:
        try:
            if get_remaining_days(product["expiration_date"]) < 0 and product.get("status") != "Expired":
                product["status"] = "Expired"
                product["last_updated"] = timestamp()
                changed = True
        except (KeyError, ValueError):
            product["status"] = "Removed"
            product["last_updated"] = timestamp()
            changed = True
    if changed:
        save_state(users, stores, products, purchases, reports)


def post_product(user, users, stores, products, purchases, reports):
    store = get_owner_store(user, stores)
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
    expiration_date = (date.today() + timedelta(days=days)
                       ).strftime("%Y-%m-%d")
    final_price, percent = calculate_discount(price, days)
    print(
        f"Expiration: {expiration_date} | Discount: {percent}% | Price after discount: PHP {final_price:.2f}")
    if input("Confirm post? (y/n): ").strip().lower() != "y":
        print("Posting cancelled.")
        return

    products.append({
        "product_id": next_id(products, "product_id", "P"),
        "store_id": store["store_id"],
        "name": name,
        "category": category,
        "original_price": round(price, 2),
        "quantity": quantity,
        "expiration_date": expiration_date,
        "status": "Available",
        "date_posted": timestamp(),
        "last_updated": timestamp(),
    })
    save_state(users, stores, products, purchases, reports)
    print("Product posted successfully.")


def browse_products(user, users, stores, products, purchases, reports):
    expiry_guard(users, stores, products, purchases, reports)
    print("\n--- BROWSE PRODUCTS ---")
    print(
        f"Your area: {user.get('area', '')}. Leave area blank to search all areas.")
    area_filter = input("Area filter: ").strip().upper()
    name_filter = input(
        "Product name filter (blank for all): ").strip().lower()
    print("0. All categories")
    for number, category in enumerate(CATEGORIES, 1):
        print(f"{number}. {category}")
    category_input = input("Category number: ").strip()
    selected_category = None
    if category_input:
        try:
            category_number = int(category_input)
            if category_number != 0:
                selected_category = CATEGORIES[category_number - 1]
        except (ValueError, IndexError):
            print("Invalid category.")
            return

    matches = []
    for product in products:
        if product.get("status") != "Available" or product.get("quantity", 0) <= 0:
            continue
        if get_remaining_days(product["expiration_date"]) < 0:
            continue
        store = find_record(stores, "store_id", product.get("store_id"))
        if not store or store.get("status") != "Approved":
            continue
        if area_filter and store.get("area", "").upper() != area_filter:
            continue
        if name_filter and name_filter not in product.get("name", "").lower():
            continue
        if selected_category and product.get("category") != selected_category:
            continue
        matches.append((product, store))

    # Show the customer's area first, while keeping other areas searchable.
    matches.sort(key=lambda item: item[1].get(
        "area", "").upper() != user.get("area", "").upper())
    if not matches:
        print("No products matched your search.")
        return

    for product, store in matches:
        price, percent = calculate_discount(
            product["original_price"], get_remaining_days(product["expiration_date"]))
        max_allowed = get_max_allowed_for_customer(user, purchases, product["category"], product["quantity"])
        max_purchasable = min(product["quantity"], max_allowed)

        print(
            f"\n{product['product_id']} | {product['name']} | {product['category']}")
        print(
            f"Store: {store['store_name']} | Area: {store['area']} | Stock: {product['quantity']}")
        print(
            f"Expires: {product['expiration_date']} | PHP {price:.2f} ({percent}% off)")
        print(f"Max quantity you can request today: {max_purchasable}")

    product_id = input(
        "\nProduct ID to request (Enter to cancel): ").strip().upper()
    if not product_id:
        return
    product = find_record(products, "product_id", product_id)
    if not product or product.get("status") != "Available":
        print("Product is not available.")
        return
    store = find_record(stores, "store_id", product.get("store_id"))
    if not store or store.get("status") != "Approved":
        print("Store is not approved.")
        return

    max_allowed = get_max_allowed_for_customer(user, purchases, product["category"], product["quantity"])
    max_purchasable = min(product["quantity"], max_allowed)

    if max_purchasable <= 0:
        print("You have reached your daily purchase limit for this category.")
        return

    try:
        quantity = int(input(f"Quantity to request (1-{max_purchasable}): ").strip())
    except ValueError:
        print("Enter a valid quantity.")
        return
    if quantity <= 0 or quantity > max_purchasable:
        print(f"Invalid quantity! Maximum allowed is {max_purchasable}.")
        return
    if get_remaining_days(product["expiration_date"]) < 0:
        print("Expired products cannot be purchased.")
        return

    print("1. Store Pickup\n2. Same-Day Express (arranged with store)")
    fulfillment_choice = input("Choose fulfillment: ").strip()
    if fulfillment_choice not in ("1", "2"):
        print("Invalid fulfillment option.")
        return
    fulfillment = "Store Pickup" if fulfillment_choice == "1" else "Same-Day Express"
    unit_price, percent = calculate_discount(
        product["original_price"], get_remaining_days(product["expiration_date"]))
    purchase = {
        "purchase_id": next_id(purchases, "purchase_id", "R"),
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
    purchases.append(purchase)
    save_state(users, stores, products, purchases, reports)
    print(
        f"Purchase request {purchase['purchase_id']} submitted. Receipt will be issued after confirmation.")


def get_max_allowed_for_customer(customer, purchases, category, total_product_stock, exclude_purchase_id=None):
    """Calculates remaining quantity a customer can buy today based on percentage limit."""
    if total_product_stock <= 0:
        return 0

    today = date.today().isoformat()
    used_quantity = 0
    for purchase in purchases:
        if purchase.get("customer_id") != customer.get("user_id"):
            continue
        if (
            purchase.get("category") != category
            or purchase.get("purchase_id") == exclude_purchase_id
        ):
            continue
        if not str(purchase.get("created_at", "")).startswith(today):
            continue
        if purchase.get("status") in ("Pending", "Confirmed", "Completed"):
            used_quantity += int(purchase.get("quantity", 0))

    max_items_per_category = 0.15 if used_quantity < total_product_stock else 0.20
    max_allowed_units = int(total_product_stock * max_items_per_category)

    return max(0, max_allowed_units - used_quantity)


def daily_limit_allows(customer, purchases, category, requested_quantity, total_product_stock, exclude_purchase_id=None):
    """Check if customer request is within their allowed daily limit."""
    remaining_allowance = get_max_allowed_for_customer(customer, purchases, category, total_product_stock, exclude_purchase_id)
    return requested_quantity <= remaining_allowance


# ============================================================
# PURCHASE CONFIRMATION AND RECEIPTS
# ============================================================
def print_receipt(purchase):
    """Print the receipt after a purchase has been confirmed."""
    print("\n" + "=" * 40)
    print("             PURCHASE RECEIPT")
    print("=" * 40)
    print(
        f"Receipt No. : {purchase.get('receipt_number', purchase['purchase_id'])}")
    print(
        f"Date        : {purchase.get('confirmed_at', purchase['created_at'])}")
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


def review_purchase_requests(user, users, stores, products, purchases, reports):
    store = get_owner_store(user, stores)
    if not store:
        print("No store record found.")
        return
    pending = [p for p in purchases if p.get(
        "store_id") == store["store_id"] and p.get("status") == "Pending"]
    if not pending:
        print("No pending purchase requests.")
        return

    for purchase in pending:
        print(
            f"\n{purchase['purchase_id']} | {purchase['product_name']} | Qty: {purchase['quantity']} | Total: PHP {purchase['total_price']:.2f}")
        print("1. Confirm\n2. Reject\n3. Leave pending")
        choice = input("Choose action: ").strip()
        if choice == "1":
            product = find_record(products, "product_id",
                                  purchase["product_id"])
            customer = find_record(users, "user_id", purchase["customer_id"])
            # Recheck availability, expiration, stock, and daily limit at confirmation time.
            if not product or product.get("status") != "Available":
                print("Cannot confirm: product is unavailable.")
                continue
            if get_remaining_days(product["expiration_date"]) < 0:
                product["status"] = "Expired"
                print("Cannot confirm: product has expired.")
                continue
            if product["quantity"] < purchase["quantity"]:
                print("Cannot confirm: not enough stock.")
                continue
            if not customer or not daily_limit_allows(customer, purchases, purchase["category"], purchase["quantity"], product["quantity"], purchase["purchase_id"]):
                print("Cannot confirm: daily category limit would be exceeded.")
                continue
            product["quantity"] -= purchase["quantity"]
            product["last_updated"] = timestamp()
            if product["quantity"] == 0:
                product["status"] = "Sold Out"
            purchase["status"] = "Confirmed"
            purchase["confirmed_at"] = timestamp()
            purchase["updated_at"] = timestamp()
            purchase["receipt_number"] = purchase["purchase_id"]
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
    save_state(users, stores, products, purchases, reports)


def view_my_purchases(user, purchases):
    own = [p for p in purchases if p.get("customer_id") == user.get("user_id")]
    if not own:
        print("No purchase records found.")
        return
    print("\n--- MY PURCHASES ---")
    for purchase in own:
        print(f"{purchase['purchase_id']} | {purchase['product_name']} | Qty: {purchase['quantity']} | PHP {purchase['total_price']:.2f} | {purchase['status']}")
        if purchase.get("status") in ("Confirmed", "Completed"):
            print_receipt(purchase)


# ============================================================
# ADMIN APPROVAL AND REPORTS
# ============================================================
def admin_panel(users, stores, products, purchases, reports):
    pending = [store for store in stores if store.get("status") == "Pending"]
    if not pending:
        print("No pending store applications.")
        return
    print("\n--- STORE APPLICATIONS ---")
    for number, store in enumerate(pending, 1):
        owner = find_record(users, "user_id", store.get("owner_id"))
        owner_name = owner.get("username", "Unknown") if owner else "Unknown"
        documents = owner.get("verification_docs", {}) if owner else {}
        print(
            f"{number}. {store['store_id']} | {store['store_name']} | Owner: {owner_name} | Area: {store['area']}")
        verification_statuses = [
            f"{label}: {verification_upload_status(documents.get(key))}"
            for key, label in (
                ("business_permit", "Business Permit"),
                ("food_inspection", "Food Inspection Permit"),
                ("inspection_records", "Inspection Record"),
                ("proof_ownership", "Proof of Ownership"),
            )
        ]
        if documents.get("business_document"):
            verification_statuses.append(
                "Legacy Business Document: "
                + verification_upload_status(documents["business_document"])
            )
        print("   Verification: " + " | ".join(verification_statuses))
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
    owner = find_record(users, "user_id", store.get("owner_id"))
    print("\n--- OWNER VERIFICATION DOCUMENTS ---")
    verification_docs = owner.get("verification_docs", {}) if owner else {}
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

    print("1. Approve\n2. Reject")
    decision = input("Decision: ").strip()
    if decision == "1":
        store["status"] = "Approved"
        store["reviewed_at"] = timestamp()
        print("Store approved.")
    elif decision == "2":
        store["status"] = "Rejected"
        store["reviewed_at"] = timestamp()
        print("Store rejected.")
    else:
        print("Invalid decision.")
        return
    save_state(users, stores, products, purchases, reports)


def create_report(user, users, stores, products, purchases, reports):
    product_id = input("Product ID to report: ").strip().upper()
    product = find_record(products, "product_id", product_id)
    if not product:
        print("Product not found.")
        return
    reason = input("Reason for report: ").strip()
    if not reason:
        print("Report reason cannot be empty.")
        return
    reports.append({
        "report_id": next_id(reports, "report_id", "REP"),
        "reporter_id": user["user_id"],
        "product_id": product["product_id"],
        "store_id": product["store_id"],
        "reason": reason,
        "status": "Pending",
        "created_at": timestamp(),
    })
    save_state(users, stores, products, purchases, reports)
    print("Report submitted for review.")


def review_reports(users, stores, products, purchases, reports):
    pending = [report for report in reports if report.get(
        "status") == "Pending"]
    if not pending:
        print("No pending reports.")
        return
    for report in pending:
        print(
            f"\n{report['report_id']} | Product: {report['product_id']} | Reason: {report['reason']}")
        choice = input(
            "Confirm report? (y/n, Enter to skip): ").strip().lower()
        if choice not in ("y", "n"):
            continue
        report["status"] = "Confirmed" if choice == "y" else "Dismissed"
        report["reviewed_at"] = timestamp()
        if choice == "y":
            store = find_record(stores, "store_id", report["store_id"])
            product = find_record(products, "product_id", report["product_id"])
            if store:
                store["trust_score"] = store.get("trust_score", 0) - 1
            if product:
                product["status"] = "Removed"
                product["last_updated"] = timestamp()
            print("Report confirmed. Listing removed and store trust score reduced.")
        else:
            print("Report dismissed.")
    save_state(users, stores, products, purchases, reports)


# ============================================================
# ROLE MENUS AND MAIN LOOP
# ============================================================
def user_dashboard(user, users, stores, products, purchases, reports):
    while True:
        print(
            f"\n=== {user['username']} | {user['role']} | Status: {user.get('status', 'Approved')} | Trust: {user.get('trust_score', 0)} ===")
        if user["role"] == "Admin":
            print("1. Review store applications\n2. Review reports\n0. Logout")
            choice = input("Choice: ").strip()
            if choice == "1":
                admin_panel(users, stores, products, purchases, reports)
            elif choice == "2":
                review_reports(users, stores, products, purchases, reports)
            elif choice == "0":
                return
            else:
                print("Invalid choice.")
        elif user["role"] == "Store Owner":
            store = get_owner_store(user, stores)
            if not store:
                print("Store application not found.")
                return
            print(
                f"Store: {store['store_name']} | Approval: {store['status']}")
            print("1. Post product\n2. View my products\n3. Review purchase requests\n4. Verification details\n0. Logout")
            choice = input("Choice: ").strip()
            if choice == "1":
                post_product(user, users, stores, products, purchases, reports)
            elif choice == "2":
                own_products = [p for p in products if p.get(
                    "store_id") == store["store_id"]]
                if not own_products:
                    print("No products posted yet.")
                for product in own_products:
                    print(
                        f"{product['product_id']} | {product['name']} | Stock: {product['quantity']} | {product['status']}")
            elif choice == "3":
                review_purchase_requests(
                    user, users, stores, products, purchases, reports)
            elif choice == "4":
                verification_menu(user, users, stores,
                                  products, purchases, reports)
            elif choice == "0":
                return
            else:
                print("Invalid choice.")
        elif user["role"] == "Customer":
            print("1. Browse and request products\n2. View purchases/receipts\n3. Report product\n4. Verification details\n0. Logout")
            choice = input("Choice: ").strip()
            if choice == "1":
                browse_products(user, users, stores,
                                products, purchases, reports)
            elif choice == "2":
                view_my_purchases(user, purchases)
            elif choice == "3":
                create_report(user, users, stores,
                              products, purchases, reports)
            elif choice == "4":
                verification_menu(user, users, stores,
                                  products, purchases, reports)
            elif choice == "0":
                return
            else:
                print("Invalid choice.")


def main():
    users, stores, products, purchases, reports = load_data()
    while True:
        expiry_guard(users, stores, products, purchases, reports)
        print("\n" + "=" * 42)
        print("              ZEROWASTE")
        print("=" * 42)
        print("1. Login\n2. Register\n0. Exit")
        choice = input("Select: ").strip()
        if choice == "1":
            user = login_user(users)
            if user:
                user_dashboard(user, users, stores,
                               products, purchases, reports)
        elif choice == "2":
            register_user(users, stores, products, purchases, reports)
        elif choice == "0":
            save_state(users, stores, products, purchases, reports)
            print("Data saved. Goodbye!")
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()