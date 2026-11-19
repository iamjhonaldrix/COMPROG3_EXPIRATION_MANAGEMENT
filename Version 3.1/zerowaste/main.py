from features.accounts import login_user, register_user
from features.dashboards import user_dashboard
from features.products import expiry_guard
from services.storage import JSONStorage, save_state
from core.ui import show_error, show_info, show_success


# ============================================================ MAIN ============================================================

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
            user = register_user(state)
            if user:
                show_info("You are now logged in. No need to log in again.")
                user_dashboard(user, state)

        elif choice == "0":
            save_state(state)
            show_success("All data saved successfully. Exiting the application now.")
            break

        else:
            show_error("Invalid choice. Enter 1, 2, or 0.")


if __name__ == "__main__":
    main()
