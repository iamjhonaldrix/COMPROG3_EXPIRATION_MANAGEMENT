from services.changelog import log_activity
from core.config import MIN_PASSWORD_LENGTH
from core.helpers import all_accounts, find_record, next_id, read_number
from core.models import AppState, Record, Records
from services.security import new_staff_account
from services.storage import save_state
from core.ui import show_error, show_header, show_info, show_success


# ============================================================ SYSTEM MONITORING AND ADMIN MANAGEMENT ============================================================

def view_users_and_stores(state: AppState) -> None:
    show_header("REGISTERED USERS")
    if not state.users:
        show_info("No users registered yet.")
    for user in state.users:
        print(
            f"{user['user_id']} | {user['username']} | {user['role']} | "
            f"Area: {user.get('area', '')} | Status: {user.get('status', '')} | "
            f"Trust: {user.get('trust_score', 0)}"
        )

    show_header("REGISTERED STORES")
    if not state.stores:
        show_info("No stores registered yet.")
    for store in state.stores:
        owner = find_record(state.users, "user_id", store.get("owner_id"))
        print(
            f"{store['store_id']} | {store['store_name']} | "
            f"Owner: {owner['username'] if owner else 'Unknown'} | "
            f"Area: {store['area']} | Status: {store['status']} | "
            f"Trust: {store.get('trust_score', 0)}"
        )


def system_dashboard(state: AppState) -> None:
    def count(records: Records, field: str, value: str) -> int:
        return sum(1 for r in records if r.get(field) == value)

    show_header("SYSTEM DASHBOARD")
    print(f"Customers      : {count(state.users, 'role', 'Customer')}")
    print(f"Store Owners   : {count(state.users, 'role', 'Store Owner')}")
    print(
        f"Admins         : {len(state.admins)} "
        f"({sum(1 for a in state.admins if a.get('active', True))} active)"
    )
    print(
        f"Stores         : {len(state.stores)} "
        f"(Pending {count(state.stores, 'status', 'Pending')}, "
        f"Approved {count(state.stores, 'status', 'Approved')}, "
        f"Rejected {count(state.stores, 'status', 'Rejected')})"
    )
    print(
        f"Products       : {len(state.products)} "
        f"(Available {count(state.products, 'status', 'Available')}, "
        f"Sold Out {count(state.products, 'status', 'Sold Out')}, "
        f"Expired {count(state.products, 'status', 'Expired')}, "
        f"Removed {count(state.products, 'status', 'Removed')})"
    )
    print(
        f"Purchases      : {len(state.purchases)} "
        f"(Pending {count(state.purchases, 'status', 'Pending')}, "
        f"Confirmed {count(state.purchases, 'status', 'Confirmed')}, "
        f"Rejected {count(state.purchases, 'status', 'Rejected')})"
    )
    print(f"Pending reports: {count(state.reports, 'status', 'Pending')}")
    print(f"Logged actions : {len(state.changelogs)}")


def manage_admin_accounts(user: Record, state: AppState) -> None:
    while True:
        show_header("MANAGE ADMIN ACCOUNTS")
        print("1. View admin accounts\n2. Create admin account\n3. Activate / deactivate admin\n0. Back")
        choice = input("Choice: ").strip()

        if choice == "1":
            if not state.admins:
                show_info("No admin accounts exist.")
            for number, admin in enumerate(state.admins, 1):
                label = "Active" if admin.get("active", True) else "Deactivated"
                print(f"{number}. {admin['admin_id']} | {admin['username']} | {label} | Created: {admin.get('date_created')}")

        elif choice == "2":
            username = input("New admin username: ").strip()
            if not username:
                show_error("Username cannot be empty.")
                continue
            if any(a.get("username", "").lower() == username.lower() for a in all_accounts(state)):
                show_error(f"The username '{username}' is already taken.")
                continue

            password = input("Temporary password: ").strip()
            if len(password) < MIN_PASSWORD_LENGTH:
                show_error(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
                continue

            account = new_staff_account(
                next_id(state.admins, "admin_id", "A"), username, password, "Admin"
            )
            account["created_by"] = user["username"]
            state.admins.append(account)
            save_state(state)
            log_activity(state, user, "CREATE_ADMIN", f"Created admin account {username} ({account['admin_id']})")
            show_success(f"Admin account '{username}' was created.")

        elif choice == "3":
            if not state.admins:
                show_info("No admin accounts exist.")
                continue
            for number, admin in enumerate(state.admins, 1):
                label = "Active" if admin.get("active", True) else "Deactivated"
                print(f"{number}. {admin['username']} | {label}")

            number = read_number("Select admin (0 to cancel): ", int)
            if number is None or not 0 <= number <= len(state.admins):
                show_error(f"Enter a number from 0 to {len(state.admins)}.")
                continue
            if number == 0:
                continue

            admin = state.admins[number - 1]
            admin["active"] = not admin.get("active", True)
            save_state(state)
            action = "ACTIVATE_ADMIN" if admin["active"] else "DEACTIVATE_ADMIN"
            word = "activated" if admin["active"] else "deactivated"
            log_activity(state, user, action, f"{word.capitalize()} admin account {admin['username']}")
            show_success(f"Admin '{admin['username']}' was {word}.")

        elif choice == "0":
            return

        else:
            show_error("Invalid choice. Enter 1, 2, 3, or 0.")
