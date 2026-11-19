from features.accounts import verification_menu
from services.changelog import view_changelogs
from core.helpers import get_owner_store
from core.models import AppState, Record
from features.moderation import (
    admin_panel,
    create_report,
    remove_product,
    resubmit_store_application,
    review_reports,
)
from features.monitoring import manage_admin_accounts, system_dashboard, view_users_and_stores
from features.products import browse_products, edit_product, post_product, view_my_products
from features.purchases import review_purchase_requests, view_my_purchases
from core.ui import show_error, show_info


# ============================================================ ROLE DASHBOARDS ============================================================

def user_dashboard(user: Record, state: AppState) -> None:
    while True:
        username = user["username"]
        role = user["role"]
        status = user.get("status", "Approved")
        trust = user.get("trust_score", 0)

        print(f"\n=== {username} | {role} | Status: {status} | Trust: {trust} ===")

        if role == "Super Admin":
            print(
                "1. System dashboard\n"
                "2. Manage admin accounts\n"
                "3. View users and stores\n"
                "4. View changelog\n"
                "0. Logout"
            )
            choice = input("Choice: ").strip()

            if choice == "1":
                system_dashboard(state)
            elif choice == "2":
                manage_admin_accounts(user, state)
            elif choice == "3":
                view_users_and_stores(state)
            elif choice == "4":
                view_changelogs(state)
            elif choice == "0":
                show_info("You have been logged out.")
                show_info("Exiting the application now.")
                return
            else:
                show_error("Invalid choice. Enter a number from 0 to 4.")

        elif role == "Admin":
            print(
                "1. Review store applications\n"
                "2. Review reports\n"
                "3. Remove a product listing\n"
                "4. View users and stores\n"
                "0. Logout"
            )
            choice = input("Choice: ").strip()

            if choice == "1":
                admin_panel(user, state)
            elif choice == "2":
                review_reports(user, state)
            elif choice == "3":
                remove_product(user, state)
            elif choice == "4":
                view_users_and_stores(state)
            elif choice == "0":
                show_info("You have been logged out.")
                show_info("Exiting the application now.")
                return
            else:
                show_error("Invalid choice. Enter a number from 0 to 4.")

        elif role == "Store Owner":
            store = get_owner_store(user, state.stores)
            if not store:
                show_error("Store application not found.")
                return

            print(f"Store: {store['store_name']} | Approval: {store['status']}")
            if store.get("status") == "Rejected":
                show_info(
                    f"Application feedback: {store.get('rejection_reason', 'No reason provided.')}"
                )
            print(
                "1. Post product\n"
                "2. View my products\n"
                "3. Edit a product\n"
                "4. Review purchase requests\n"
                "5. Account verification\n"
                + ("6. Resubmit store application\n" if store.get("status") == "Rejected" else "")
                + "0. Logout"
            )
            choice = input("Choice: ").strip()

            if choice == "1":
                post_product(user, state)
            elif choice == "2":
                view_my_products(user, state)
            elif choice == "3":
                edit_product(user, state)
            elif choice == "4":
                review_purchase_requests(user, state)
            elif choice == "5":
                verification_menu(user, state)
            elif choice == "6" and store.get("status") == "Rejected":
                resubmit_store_application(user, state)
            elif choice == "0":
                show_info("You have been logged out.")
                return
            else:
                max_choice = 6 if store.get("status") == "Rejected" else 5
                show_error(f"Invalid choice. Enter a number from 0 to {max_choice}.")

        elif role == "Customer":
            print(
                "1. Browse and request products\n"
                "2. View purchases/receipts\n"
                "3. Report product\n"
                "4. Account verification\n"
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
                show_info("You have been logged out.")
                return
            else:
                show_error("Invalid choice. Enter a number from 0 to 4.")

        else:
            show_error("Unrecognized account role.")
            return
