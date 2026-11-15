import os
import json
import sys
import shutil
import tkinter as tk
from tkinter import filedialog
from datetime import datetime, date, timedelta

USERS_FILE = "user_db.json"
PRODUCTS_FILE = "products.json"
STORAGE_DIR = "Storage"

CATEGORIES = ["FRESH PRODUCE", "DAIRY", "MEAT", "FROZEN", "PACKAGE", "CANNED", "DONATION", "OTHER"]

DISCOUNT_BY_DAYS = {
    "same_day": 80, 
    "above_7_days": 10, 
    7: 20, 
    6: 35, 
    5: 30, 
    4: 35, 
    3: 40, 
    2: 45, 
    1: 50 }

MAX_ITEMS_PER_CATEGORY = 3  # Anti-Hoarding Limit


def upload_single_document(doc_name):
    """
    Opens File Explorer to pick a file, copies it to 'storage/', 
    and returns the destination path.
    """
    print(f"\n[UPLOAD] Opening File Explorer to select photo for: '{doc_name}'...")
    
    # Hide Tkinter root window
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    file_path = filedialog.askopenfilename(
        title=f"Select Photo for {doc_name}",
        filetypes=[
            ("Image Files", "*.jpg *.jpeg *.png"),
            ("All Files", "*.*")
        ]
    )

    if file_path:
        os.makedirs(STORAGE_DIR, exist_ok=True)
        filename = os.path.basename(file_path)
        
        # Add timestamp to filename to prevent duplicates
        timestamp = int(datetime.now().timestamp())
        saved_filename = f"{timestamp}_{filename}"
        destination_path = os.path.join(STORAGE_DIR, saved_filename)

        shutil.copy(file_path, destination_path)
        print(f" -> SUCCESS! Photo saved to: {destination_path}")
        return destination_path
    else:
        print(" -> Upload canceled. No file selected.")
        return None

def upload_verification_menu(user, users, products):
    """
    Menu for unverified users to upload required documents individually.
    """
    if "verification_docs" not in user:
        user["verification_docs"] = {}

    while True:
        docs = user["verification_docs"]
        print("\n" + "="*45)
        print("    DOCUMENT VERIFICATION UPLOAD MENU    ")
        print("="*45)

        if user["role"] == "Store Owner":
            print(f"[1] Business Permit Photo      : {docs.get('business_permit', 'NOT UPLOADED')}")
            print(f"[2] Food Inspection Photo     : {docs.get('food_inspection', 'NOT UPLOADED')}")
            print(f"[3] Inspection Record Photo   : {docs.get('inspection_records', 'NOT UPLOADED')}")
            print(f"[4] Proof of Ownership Photo  : {docs.get('proof_ownership', 'NOT UPLOADED')}")
            print("[5] Save & Back to Dashboard")

            choice = input("\nSelect document to upload [1-5]: ").strip()

            if choice == "1":
                path = upload_single_document("Business Permit")
                if path: user["verification_docs"]["business_permit"] = path
            elif choice == "2":
                path = upload_single_document("Food Inspection Permit")
                if path: user["verification_docs"]["food_inspection"] = path
            elif choice == "3":
                path = upload_single_document("Inspection Record")
                if path: user["verification_docs"]["inspection_records"] = path
            elif choice == "4":
                path = upload_single_document("Proof of Ownership")
                if path: user["verification_docs"]["proof_ownership"] = path
            elif choice == "5":
                save_data(users, products)
                print("\nVerification documents saved! Admin will review your account.")
                break

        elif user["role"] == "Customer":
            print(f"[1] Phone Number        : {docs.get('phone', 'NOT SET')}")
            print(f"[2] National ID Photo   : {docs.get('national_id_photo', 'NOT UPLOADED')}")
            print("[3] Save & Back to Dashboard")

            choice = input("\nSelect option to update/upload [1-3]: ").strip()

            if choice == "1":
                user["verification_docs"]["phone"] = input("Enter Phone Number: ").strip()
            elif choice == "2":
                path = upload_single_document("National ID Photo")
                if path: user["verification_docs"]["national_id_photo"] = path
            elif choice == "3":
                save_data(users, products)
                print("\nVerification details saved! Admin will review your account.")
                break
            

# ==========================================
# FILE DATABASE HANDLERS
# ==========================================

def load_data():
    users = []
    products = []
    
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                users = json.load(f)
        except Exception as e:
            print(f"[LOAD ERROR] Failed to load {USERS_FILE}: {e}")

    if os.path.exists(PRODUCTS_FILE):
        try:
            with open(PRODUCTS_FILE, "r") as f:
                products = json.load(f)
        except Exception as e:
            print(f"[LOAD ERROR] Failed to load {PRODUCTS_FILE}: {e}")

    admin_found = False
    for user in users:
        if user["username"].lower() == "admin":
            admin_found = True
            break
    
    if not admin_found:
        new_admin = {
            "username": "admin",
            "role": "Admin",
            "is_verified": True,
            "trust_points": 100,
            "city": "BULACAN"
        }
        users.append(new_admin)
        save_data(users, products)
            
    return users, products


def save_data(users, products):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

    with open(PRODUCTS_FILE, "w") as f:
        json.dump(products, f, indent=4)


# ==========================================
# HELPER FUNCTIONS & EXPIRY GUARD
# ==========================================

def get_remaining_days(expiry_str):
    return (datetime.strptime(expiry_str, "%Y-%m-%d").date() - date.today()).days


def calculate_discount(price, remaining_days):
    if remaining_days <= 0:
        percent = DISCOUNT_BY_DAYS["same_day"]
    elif remaining_days > 7:
        percent = DISCOUNT_BY_DAYS["above_7_days"]
    else:
        percent = DISCOUNT_BY_DAYS.get(remaining_days, 10)
    
    discount = price * (percent / 100.0)
    return round(price - discount, 2), percent


def run_expiry_guard(users, products):
    """Auto removes expired products."""
    active = []

    for product in products:
        remaining_days = get_remaining_days(product["expiry_date"])
        
        if remaining_days >= 0:
            active.append(product)
   
    if len(active) != len(products):
        products.clear()
        products.extend(active)
        save_data(users, products)


# ==========================================
# SYSTEM FEATURES
# ==========================================

def register_user(users, products):
    print("\n--- REGISTER ---")
    role_choice = input("[1]. Customer\n[2]. Store Owner\nSelect Role: ").strip()
    role = "Customer" if role_choice == "1" else "Store Owner"
    
    uname = input("Username: ").strip()
    
    if uname.lower() == "admin" or any(u["username"].lower() == uname.lower() for u in users):
        print("Username invalid or already taken!")
        return

    city = input("City/Area: ").strip().upper()

    if role == "Customer":
        phone = input("Phone Number: ").strip()
        nat_id_num = input("National ID Number: ").strip()
        
        # Runs the upload image function for National ID
        nat_id_photo = upload_single_document("National ID Photo")
        
        user = {
            "username": uname, 
            "role": role, 
            "is_verified": False, 
            "trust_points": 100,
            "city": city, 
            "category_purchase_count": {c: 0 for c in CATEGORIES},
            "verification_docs": {
                "phone": phone, 
                "national_id": f"ID: {nat_id_num} | Photo: {nat_id_photo}"
            }
        }
    else:
        store_name = input("Store Name: ").strip()
        
        user = {
            "username": uname, 
            "role": role, 
            "store_name": store_name,
            "is_verified": False, 
            "trust_points": 100, 
            "city": city, 
        }

    users.append(user)
    save_data(users, products)
    print("Registered! Please proceed to verification")


def login_user(users):
    print("\n--- LOGIN ---")
    uname = input("Enter Username: ").strip()
    user = next((u for u in users if u["username"].lower() == uname.lower()), None)
    
    if user:
        print(f"Welcome {user['username']} ({user['role']})!")
        return user
    print("User not found!")
    return None


def post_product(user, users, products):
    if not user.get("is_verified"):
        print("Account pending verification! Cannot post products.")
        return

    print("\n--- POST PRODUCT ---")
    name = input("Product Name: ")
    for i, c in enumerate(CATEGORIES, 1):
        print(f"{i}. {c}")
    
    cat_idx = int(input("Select Category #: ")) - 1
    category = CATEGORIES[cat_idx] if 0 <= cat_idx < len(CATEGORIES) else "OTHER"
    
    price = float(input("Regular Price (PHP): "))
    qty = int(input("Quantity: "))
    days = int(input("Days until expiration (0 = today): "))

    if days < 0:
        print("Cannot post expired product!")
        return

    exp_date = (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")
    final_price, pct = calculate_discount(price, days)
    print(f"Final Price after {pct}% discount: PHP {final_price}")

    if input("Confirm Post? (y/n): ").lower() == 'y':
        new_id = max([p["id"] for p in products], default=0) + 1
        products.append({"id": new_id, "owner": user["username"], "name": name, "category": category, "price": price, "quantity": qty, "expiry_date": exp_date})
        user["trust_points"] += 5
        save_data(users, products)
        print("Product Posted!")


def buy_product(user, users, products):
    run_expiry_guard(users, products)

    # Ligtas na pagkuha ng owner key (p.get("owner") o p.get("owner_username"))
    local_prods = []
    for p in products:
        owner_name = p.get("owner") or p.get("owner_username")
        owner_obj = next((u for u in users if u["username"].lower() == owner_name.lower()), {})
        
        # Geofencing Check (Magkatugmang Lungsod/Area)
        if owner_obj.get("city", "").upper() == user.get("city", "").upper() and p["quantity"] > 0:
            local_prods.append(p)

    print(f"\n--- AVAILABLE PRODUCTS IN {user['city']} ---")
    if not local_prods:
        print(f"No items available in {user['city']} right now.")
        print("(Note: Make sure the Store Owner and Customer are registered in the same City/Area!)")
        return

    for p in local_prods:
        rem = get_remaining_days(p["expiry_date"])
        final_price, pct = calculate_discount(p["price"], rem)
        print(f"ID: {p['id']} | {p['name']} | {p['category']} | Stock: {p['quantity']} | PHP {final_price} ({pct}% OFF)")

    try:
        pid = int(input("\nEnter Product ID to buy (0 to cancel): "))
    except ValueError:
        return

    if pid == 0:
        return

    prod = next((p for p in local_prods if p["id"] == pid), None)
    if not prod:
        print("Invalid Product ID!")
        return

    cat = prod["category"]
    
    # Siguraduhing may purchase counter ang user
    if "category_purchase_count" not in user:
        user["category_purchase_count"] = {c: 0 for c in CATEGORIES}

    bought_so_far = user["category_purchase_count"].get(cat, 0)
    allowed = MAX_ITEMS_PER_CATEGORY - bought_so_far

    print(f"[ANTI-HOARDING] You can buy max {allowed} more items in {cat}.")
    if allowed <= 0:
        print("Buying limit reached for this category!")
        return

    try:
        qty = int(input("Quantity to buy: "))
    except ValueError:
        print("Invalid quantity!")
        return

    if qty <= 0 or qty > allowed or qty > prod["quantity"]:
        print("Invalid quantity or exceeds allowed limit/stock!")
        return

    method = "Pick-up" if input("1. Pick-up\n2. Same-Day Delivery\nChoice: ").strip() == "1" else "Same-Day Delivery"

    prod["quantity"] -= qty
    user["category_purchase_count"][cat] += qty
    user["trust_points"] += 10

    if prod["quantity"] == 0:
        products.remove(prod)

    save_data(users, products)
    print(f"\nOrder Placed successfully via {method}!")


def admin_panel(users, products):
    print("\n--- ADMIN VERIFICATION ---")
    unverified = [u for u in users if not u.get("is_verified")]
    
    if not unverified:
        print("No pending verifications.")
        return

    for i, u in enumerate(unverified, 1):
        print(f"\n[{i}] {u['username']} ({u['role']}) - Docs: {u.get('verification_docs')}")

    choice = int(input("\nEnter # to Approve (0 to cancel): "))
    if 0 < choice <= len(unverified):
        unverified[choice - 1]["is_verified"] = True
        unverified[choice - 1]["trust_points"] += 20
        save_data(users, products)
        print("User Approved!")


# ==========================================
# MAIN DASHBOARD & APPLICATION LOOP
# ==========================================
def user_dashboard(user, users, products):
    while True:
        status = "Verified" if user.get("is_verified") else "Pending"
        print(f"\n=== DASHBOARD: {user['username']} ({user['role']}) | Status: {status} | Points: {user['trust_points']} ===")

        if user["role"] == "Admin":
            print("[1] Verify Users\n[0] Logout")
            choice = input("Choice: ").strip()
            if choice == "1":
                admin_panel(users, products)
            elif choice == "0":
                break

        elif user["role"] == "Store Owner":
            if not user.get("is_verified"):
                print("[1] Post Product (Locked until verified)")
                print("[2] Verify Account / Upload Documents")
                print("[0] Logout")
                choice = input("Choice: ").strip()

                if choice == "1":
                    post_product(user, users, products)
                elif choice == "2":
                    # Direktang tatawagin ang hiwalay na upload menu function
                    upload_verification_menu(user, users, products)
                elif choice == "0":
                    break
            else:
                print("[1] Post Product\n[0] Logout")
                choice = input("Choice: ").strip()
                if choice == "1":
                    post_product(user, users, products)
                elif choice == "0":
                    break

        elif user["role"] == "Customer":
            if not user.get("is_verified"):
                print("[1] Browse & Buy Products")
                print("[2] Verify Account / Upload Documents")
                print("[0] Logout")
                choice = input("Choice: ").strip()

                if choice == "1":
                    buy_product(user, users, products)
                elif choice == "2":
                    upload_verification_menu(user, users, products)
                elif choice == "0":
                    break
            else:
                print("[1] Browse & Buy Products\n[0] Logout")
                choice = input("Choice: ").strip()
                if choice == "1":
                    buy_product(user, users, products)
                elif choice == "0":
                    break
def main():
    users, products = load_data()

    while True:
        run_expiry_guard(users, products)
        print("=" * 40)
        print(" " * 15 + "ZEROWASTE")
        print("=" * 40)
        print()
        print("[1] Login\n[2] Register\n[0] Exit")

        choice = input("Select [0-2]: ").strip()
        if choice == "1":
            u = login_user(users)
            if u: user_dashboard(u, users, products)
        elif choice == "2":
            register_user(users, products)
        elif choice == "0":
            save_data(users, products)
            sys.exit(0)

if __name__ == "__main__":
    main()