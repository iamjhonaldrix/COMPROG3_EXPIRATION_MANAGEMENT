from typing import Optional

from services.changelog import log_activity
from core.config import MIN_PASSWORD_LENGTH
from services.documents import upload_document, verification_upload_status
from core.helpers import all_accounts, next_id, timestamp
from core.models import AppState, Record
from services.security import hash_password, is_hashed, verify_password
from services.storage import save_state
from core.ui import show_error, show_header, show_info, show_success
from services.validation import prompt_phone


def verification_menu(user: Record, state: AppState) -> None:
    user.setdefault("verification_docs", {})

    while True:
        show_header("ACCOUNT VERIFICATION")
        print(f"Current phone number: {user.get('phone', 'not set')}")
        print("1. Update phone number")
        print("2. Upload verification documents")
        print("3. Save and return")

        choice = input("Select: ").strip()

        if choice == "1":
            phone = prompt_phone()
            if phone:
                user["phone"] = phone
                save_state(state)
                show_success(f"Phone number updated to {phone}.")
            else:
                show_info("Phone number was not changed.")

        elif choice == "2":
            if user.get("role") == "Store Owner":
                documents = [
                    ("business_permit", "Business Permit"),
                    ("food_inspection", "Food Inspection Permit"),
                    ("inspection_records", "Inspection Record"),
                    ("proof_ownership", "Proof of Ownership"),
                    ("national_id", "National ID"),
                ]
            else:
                documents = [("national_id", "National ID")]

            while True:
                docs = user["verification_docs"]
                show_header("DOCUMENT UPLOAD")

                for number, (key, label) in enumerate(documents, start=1):
                    print(f"[{number}] {label}: {verification_upload_status(docs.get(key))}")

                back_choice = len(documents) + 1
                print(f"[{back_choice}] Save & Back")
                selected = input(f"\nSelect document to upload [1-{back_choice}]: ").strip()

                if selected == str(back_choice):
                    save_state(state)
                    show_success("Verification documents saved.")
                    break

                if not selected.isdigit() or not (1 <= int(selected) <= len(documents)):
                    show_error(f"Invalid choice. Enter a number from 1 to {back_choice}.")
                    continue

                key, label = documents[int(selected) - 1]
                path = upload_document(label, user)
                if path:
                    docs[key] = path

        elif choice == "3":
            save_state(state)
            show_success("Account verification details saved.")
            return

        else:
            show_error("Invalid choice. Enter 1, 2, or 3.")


# ============================================================ REGISTRATION AND LOGIN ============================================================

def register_user(state: AppState) -> Optional[Record]:
    """Create an account. Returns the new user so they are logged in right away."""
    show_header("REGISTER")
    print("1. Customer\n2. Store Owner")
    role_choice = input("Select role: ").strip()

    if role_choice not in ("1", "2"):
        show_error("Invalid role. Enter 1 for Customer or 2 for Store Owner.")
        return None

    role = "Customer" if role_choice == "1" else "Store Owner"

    username = input("Username: ").strip()
    if not username:
        show_error("Username cannot be empty.")
        return None

    if any(a.get("username", "").lower() == username.lower() for a in all_accounts(state)):
        show_error(f"The username '{username}' is already taken. Please choose another one.")
        return None

    password = input("Password: ").strip()
    if len(password) < MIN_PASSWORD_LENGTH:
        show_error(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
        return None

    phone = prompt_phone()
    if not phone:
        show_info("Registration cancelled.")
        return None

    area = input("City/Area: ").strip().upper()
    if not area:
        show_error("City/Area cannot be empty.")
        return None

    store_name = ""
    if role == "Store Owner":
        store_name = input("Store name: ").strip()
        if not store_name:
            show_error("Store name cannot be empty. Registration cancelled.")
            return None

    user = {
        "user_id": next_id(state.users, "user_id", "U"),
        "username": username,
        "password": hash_password(password),
        "role": role,
        "phone": phone,
        "area": area,
        "status": "Pending" if role == "Store Owner" else "Approved",
        "active": True,
        "trust_score": 0,
        "date_created": timestamp(),
        "verification_docs": {},
    }
    state.users.append(user)

    if role == "Store Owner":
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
        show_success(
            f"Account created. Your store '{store_name}' was submitted for review. "
            "You can post products once an admin approves it. Upload your documents "
            "under 'Account Verification' to speed up the review."
        )
    else:
        show_success("Customer account created.")

    save_state(state)
    log_activity(state, user, "REGISTER", f"Registered a new {role} account")
    return user


def login_user(state: AppState) -> Optional[Record]:
    show_header("LOGIN")
    username = input("Username: ").strip()
    password = input("Password: ").strip()

    if not username or not password:
        show_error("Both username and password are required.")
        return None

    accounts = (
        [(a, "Super Admin") for a in state.super_admins]
        + [(a, "Admin") for a in state.admins]
        + [(a, None) for a in state.users]
    )

    for account, staff_role in accounts:
        if account.get("username", "").lower() != username.lower():
            continue

        if not verify_password(account.get("password", ""), password):
            break

        if not account.get("active", True):
            show_error("This account has been deactivated. Please contact the Super Admin.")
            return None

        if not is_hashed(account.get("password", "")):
            account["password"] = hash_password(password)  # upgrade legacy password
            save_state(state)

        if staff_role:
            user = dict(account)
            user["role"] = account.get("role", staff_role)
            user["status"] = "Approved"
            user.setdefault("trust_score", 0)
        else:
            user = account

        show_success(f"Welcome, {user['username']} ({user['role']})!")
        return user

    show_error("Incorrect username or password. Please check your details and try again.")
    return None
