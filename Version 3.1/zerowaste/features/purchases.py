from services.changelog import log_activity
from core.config import DEFAULT_UNIT
from core.helpers import find_record, get_owner_store, get_remaining_days, timestamp
from core.models import AppState, Record, Records
from features.products import refresh_product_status
from services.storage import save_state
from core.ui import show_error, show_header, show_info, show_success
from services.validation import format_quantity


# ============================================================ PURCHASE CONFIRMATION AND RECEIPT ============================================================
# This section is mainly CLI presentation. Keep heavy logic out of it.

def print_receipt(purchase: Record) -> None:
    receipt_number = purchase.get("receipt_number", purchase["purchase_id"])
    confirmed_date = purchase.get("confirmed_at", purchase["created_at"])
    unit = purchase.get("unit", DEFAULT_UNIT)

    print("\n" + "=" * 40)
    print("             PURCHASE RECEIPT")
    print("=" * 40)
    print(f"Receipt No. : {receipt_number}")
    print(f"Date        : {confirmed_date}")
    print(f"Store ID    : {purchase['store_id']}")
    print(f"Product     : {purchase['product_name']}")
    print(f"Quantity    : {format_quantity(purchase['quantity'], unit)}")
    print(f"Unit Price  : PHP {purchase['unit_price']:.2f} per {unit}")
    print(f"Discount    : {purchase['discount_percent']}%")
    print(f"Total       : PHP {purchase['total_price']:.2f}")
    print(f"Fulfillment : {purchase['fulfillment']}")
    print(f"Status      : {purchase['status']}")
    print("=" * 40)
    print("Thank you for helping reduce food waste!")


def review_purchase_requests(user: Record, state: AppState) -> None:
    store = get_owner_store(user, state.stores)
    if not store:
        show_error("No store record found for your account.")
        return

    pending = [
        p for p in state.purchases
        if p.get("store_id") == store["store_id"] and p.get("status") == "Pending"
    ]

    if not pending:
        show_info("No pending purchase requests.")
        return

    show_header(f"PENDING REQUESTS ({len(pending)})")

    for purchase in pending:
        product = find_record(state.products, "product_id", purchase["product_id"])
        customer = find_record(state.users, "user_id", purchase["customer_id"])
        unit = purchase.get("unit", DEFAULT_UNIT)

        stock_text = (
            format_quantity(product["quantity"], product.get("unit", DEFAULT_UNIT))
            if product else "unknown"
        )
        print(
            f"\n{purchase['purchase_id']} | {purchase['product_name']} | "
            f"Requested: {format_quantity(purchase['quantity'], unit)} | "
            f"Current stock: {stock_text} | Total: PHP {purchase['total_price']:.2f}"
        )
        print("1. Confirm\n2. Reject\n3. Leave pending")
        choice = input("Choose action: ").strip()

        if choice == "1":
            if not product or product.get("status") != "Available":
                show_error("Cannot confirm: the product is no longer available.")
                continue

            try:
                expired = get_remaining_days(product["expiration_date"]) < 0
            except (KeyError, TypeError, ValueError):
                expired = True

            if expired:
                product["status"] = "Expired"
                product["last_updated"] = timestamp()
                show_error("Cannot confirm: the product has expired or has an invalid expiry date.")
                continue

            if product.get("quantity", 0) < purchase["quantity"]:
                show_error(
                    f"Cannot confirm: only {stock_text} left, but "
                    f"{format_quantity(purchase['quantity'], unit)} was requested."
                )
                continue

            product["quantity"] = round(product["quantity"] - purchase["quantity"], 3)
            product["last_updated"] = timestamp()
            refresh_product_status(product)

            purchase["status"] = "Confirmed"
            purchase["confirmed_at"] = timestamp()
            purchase["updated_at"] = timestamp()
            purchase["receipt_number"] = purchase["purchase_id"]

            if customer:
                customer["trust_score"] = customer.get("trust_score", 0) + 1
            store["trust_score"] = store.get("trust_score", 0) + 1

            save_state(state)
            log_activity(state, user, "CONFIRM_PURCHASE", f"Confirmed {purchase['purchase_id']} for {purchase['product_name']}")
            print_receipt(purchase)
            show_success(f"Request {purchase['purchase_id']} confirmed and stock updated.")

        elif choice == "2":
            purchase["status"] = "Rejected"
            purchase["updated_at"] = timestamp()
            save_state(state)
            log_activity(state, user, "REJECT_PURCHASE", f"Rejected {purchase['purchase_id']} for {purchase['product_name']}")
            show_success(f"Request {purchase['purchase_id']} was rejected.")

        elif choice == "3":
            continue

        else:
            show_error("Invalid choice. The request was left pending.")

    save_state(state)


def view_my_purchases(user: Record, purchases: Records) -> None:
    own_purchases = [p for p in purchases if p.get("customer_id") == user.get("user_id")]

    if not own_purchases:
        show_info("You have no purchase records yet.")
        return

    show_header("MY PURCHASES")
    for purchase in own_purchases:
        unit = purchase.get("unit", DEFAULT_UNIT)
        print(
            f"{purchase['purchase_id']} | {purchase['product_name']} | "
            f"Qty: {format_quantity(purchase['quantity'], unit)} | "
            f"PHP {purchase['total_price']:.2f} | {purchase['status']}"
        )
        if purchase.get("status") in ("Confirmed", "Completed"):
            print_receipt(purchase)
