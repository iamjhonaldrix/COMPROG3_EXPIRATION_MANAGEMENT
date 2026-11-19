from datetime import date, timedelta

from services.changelog import log_activity
from core.config import DEFAULT_UNIT
from core.helpers import (
    calculate_discount,
    find_record,
    get_owner_store,
    get_remaining_days,
    next_id,
    read_number,
    timestamp,
)
from core.models import AppState, Record
from services.storage import save_state
from core.ui import show_error, show_header, show_info, show_success
from services.validation import (
    choose_category,
    format_quantity,
    parse_quantity,
    prompt_unit,
    quantity_rule,
)


# ============================================================ PRODUCT LISTING AND EXPIRATION ============================================================

def refresh_product_status(product: Record) -> None:
    """Set Expired / Sold Out / Available from the expiry date and stock."""
    if product.get("status") == "Removed":
        return

    try:
        remaining = get_remaining_days(product["expiration_date"])
    except (KeyError, TypeError, ValueError):
        product["status"] = "Removed"
        return

    if remaining < 0:
        product["status"] = "Expired"
    elif product.get("quantity", 0) <= 0:
        product["status"] = "Sold Out"
    else:
        product["status"] = "Available"


def expiry_guard(state: AppState) -> None:
    """Mark expired listings without deleting their records."""
    changed = False

    for product in state.products:
        try:
            remaining = get_remaining_days(product["expiration_date"])
            if remaining < 0 and product.get("status") not in ("Expired", "Removed"):
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


def describe_price(product: Record, remaining_days: int) -> str:
    unit = product.get("unit", DEFAULT_UNIT)
    price, percent = calculate_discount(product["original_price"], remaining_days)
    return (
        f"PHP {price:.2f} per {unit} ({percent}% off, "
        f"original PHP {product['original_price']:.2f})"
    )


def post_product(user: Record, state: AppState) -> None:
    store = get_owner_store(user, state.stores)
    if not store or store.get("status") != "Approved":
        current = store.get("status") if store else "not registered"
        show_error(
            f"Your store status is '{current}'. Only approved stores can post products. "
            "Please wait for an admin to approve your application."
        )
        return

    show_header("POST PRODUCT")
    name = input("Product name: ").strip()
    if not name:
        show_error("Product name cannot be empty.")
        return

    valid, category = choose_category()
    if not valid:
        return

    unit = prompt_unit()
    if not unit:
        show_info("Posting cancelled.")
        return

    price = read_number(f"Original price per {unit} (PHP): ", float)
    if price is None or price <= 0:
        show_error(f"Enter a price greater than 0 for one {unit}, such as 100 or 49.50.")
        return

    quantity = parse_quantity(input(f"Available stock in {unit}: ").strip(), unit)
    if quantity is None:
        show_error(f"Invalid quantity. It must be greater than 0. {quantity_rule(unit)}")
        return

    days = read_number("Days until expiration (0 = expires today): ", int)
    if days is None or days < 0:
        show_error("Enter the days until expiration as a whole number of 0 or more.")
        return

    expiration_date = (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")
    final_price, percent = calculate_discount(price, days)

    print("\nProduct summary")
    print(f"  Name       : {name} ({category})")
    print(f"  Stock      : {format_quantity(quantity, unit)}")
    print(f"  Expires    : {expiration_date} ({days} day(s) left)")
    print(f"  Discount   : {percent}%")
    print(f"  Price      : PHP {final_price:.2f} per {unit} (original PHP {price:.2f})")

    if input("Confirm post? (y/n): ").strip().lower() != "y":
        show_info("Posting cancelled. Nothing was saved.")
        return

    product = {
        "product_id": next_id(state.products, "product_id", "P"),
        "store_id": store["store_id"],
        "name": name,
        "category": category,
        "unit": unit,
        "original_price": round(price, 2),  # price PER UNIT
        "quantity": quantity,
        "expiration_date": expiration_date,
        "status": "Available",
        "date_posted": timestamp(),
        "last_updated": timestamp(),
    }
    state.products.append(product)

    save_state(state)
    log_activity(state, user, "POST_PRODUCT", f"Posted {name} ({product['product_id']})")
    show_success(f"{name} was posted as {product['product_id']} and is now visible to customers.")


def view_my_products(user: Record, state: AppState) -> None:
    store = get_owner_store(user, state.stores)
    own_products = [p for p in state.products if store and p.get("store_id") == store["store_id"]]

    if not own_products:
        show_info("You have not posted any products yet.")
        return

    show_header("MY PRODUCTS")
    for product in own_products:
        unit = product.get("unit", DEFAULT_UNIT)
        print(
            f"{product['product_id']} | {product['name']} | "
            f"Stock: {format_quantity(product['quantity'], unit)} | "
            f"Expires: {product['expiration_date']} | "
            f"PHP {product['original_price']:.2f}/{unit} | {product['status']}"
        )


def edit_product(user: Record, state: AppState) -> None:
    store = get_owner_store(user, state.stores)
    if not store:
        show_error("No store record found for your account.")
        return

    editable = [
        p for p in state.products
        if p.get("store_id") == store["store_id"] and p.get("status") != "Removed"
    ]
    if not editable:
        show_info("You have no editable products. Removed listings cannot be edited.")
        return

    view_my_products(user, state)
    product_id = input("\nProduct ID to edit (Enter to cancel): ").strip().upper()
    if not product_id:
        return

    product = next((p for p in editable if p["product_id"] == product_id), None)
    if not product:
        show_error(f"{product_id} is not one of your editable products.")
        return

    unit = product.get("unit", DEFAULT_UNIT)

    while True:
        print(
            f"\nEditing {product['product_id']} - {product['name']} | "
            f"Stock: {format_quantity(product['quantity'], unit)} | "
            f"PHP {product['original_price']:.2f}/{unit} | Expires: {product['expiration_date']}"
        )
        print("1. Name\n2. Category\n3. Original price per unit\n4. Stock quantity\n5. Expiration\n0. Done")
        choice = input("Edit which field: ").strip()

        if choice == "0":
            return

        if choice == "1":
            name = input("New product name: ").strip()
            if not name:
                show_error("Product name cannot be empty.")
                continue
            product["name"] = name

        elif choice == "2":
            valid, category = choose_category()
            if not valid:
                continue
            product["category"] = category

        elif choice == "3":
            price = read_number(f"New original price per {unit} (PHP): ", float)
            if price is None or price <= 0:
                show_error("Enter a price greater than 0.")
                continue
            product["original_price"] = round(price, 2)

        elif choice == "4":
            text = input(f"New stock in {unit} (0 = sold out): ").strip()
            quantity = 0 if text == "0" else parse_quantity(text, unit)
            if quantity is None:
                show_error(f"Invalid quantity. {quantity_rule(unit)}")
                continue
            product["quantity"] = quantity

        elif choice == "5":
            days = read_number("New days until expiration (0 = today): ", int)
            if days is None or days < 0:
                show_error("Enter a whole number of 0 or more.")
                continue
            product["expiration_date"] = (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")

        else:
            show_error("Invalid choice. Enter a number from 0 to 5.")
            continue

        product["last_updated"] = timestamp()
        refresh_product_status(product)
        save_state(state)
        log_activity(state, user, "UPDATE_PRODUCT", f"Updated {product['name']} ({product['product_id']})")
        show_success(f"{product['product_id']} was updated. Current status: {product['status']}.")


def browse_products(user: Record, state: AppState) -> None:
    expiry_guard(state)

    show_header("BROWSE PRODUCTS")
    print(f"Your area: {user.get('area', '')}. Leave area blank to search all areas.")
    area_filter = input("Area filter: ").strip().upper()
    name_filter = input("Product name filter (blank for all): ").strip().lower()

    valid, selected_category = choose_category(allow_all=True)
    if not valid:
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
    matches.sort(key=lambda item: item[1].get("area", "").upper() != user.get("area", "").upper())

    if not matches:
        show_info("No products matched your search. Try a different area, name, or category.")
        return

    for product, store in matches:
        unit = product.get("unit", DEFAULT_UNIT)
        remaining = get_remaining_days(product["expiration_date"])
        print(f"\n{product['product_id']} | {product['name']} | {product['category']}")
        print(
            f"Store: {store['store_name']} | Area: {store['area']} | "
            f"Stock: {format_quantity(product['quantity'], unit)}"
        )
        print(f"Expires: {product['expiration_date']} ({remaining} day(s) left)")
        print(describe_price(product, remaining))

    product_id = input("\nProduct ID to request (Enter to cancel): ").strip().upper()
    if not product_id:
        return

    # The product must be one of the results shown above.
    chosen = next((m for m in matches if m[0]["product_id"] == product_id), None)
    if not chosen:
        show_error(f"{product_id} was not in the search results above. Please choose a listed product.")
        return

    product, store = chosen
    unit = product.get("unit", DEFAULT_UNIT)
    available_stock = product["quantity"]

    text = input(
        f"Quantity to request in {unit} (up to {format_quantity(available_stock, unit)}): "
    ).strip()
    quantity = parse_quantity(text, unit)

    if quantity is None:
        show_error(f"Invalid quantity. {quantity_rule(unit)}")
        return
    if quantity > available_stock:
        show_error(
            f"You requested {format_quantity(quantity, unit)}, but only "
            f"{format_quantity(available_stock, unit)} is available."
        )
        return

    print("1. Store Pickup\n2. Same-Day Express (arranged with store)")
    fulfillment_choice = input("Choose fulfillment: ").strip()
    if fulfillment_choice not in ("1", "2"):
        show_error("Invalid fulfillment option. Enter 1 or 2.")
        return

    fulfillment = "Store Pickup" if fulfillment_choice == "1" else "Same-Day Express"
    remaining_days = get_remaining_days(product["expiration_date"])
    unit_price, percent = calculate_discount(product["original_price"], remaining_days)
    total = round(unit_price * quantity, 2)

    print(
        f"\nRequest summary: {format_quantity(quantity, unit)} of {product['name']} "
        f"x PHP {unit_price:.2f} = PHP {total:.2f} ({fulfillment})"
    )
    if input("Submit this request? (y/n): ").strip().lower() != "y":
        show_info("Request cancelled. Nothing was submitted.")
        return

    purchase = {
        "purchase_id": next_id(state.purchases, "purchase_id", "R"),
        "customer_id": user["user_id"],
        "store_id": store["store_id"],
        "product_id": product["product_id"],
        "product_name": product["name"],
        "category": product["category"],
        "unit": unit,
        "quantity": quantity,
        "unit_price": unit_price,
        "discount_percent": percent,
        "total_price": total,
        "fulfillment": fulfillment,
        "status": "Pending",
        "created_at": timestamp(),
        "updated_at": timestamp(),
    }

    state.purchases.append(purchase)
    save_state(state)
    log_activity(
        state, user, "REQUEST_PURCHASE",
        f"Requested {format_quantity(quantity, unit)} of {product['name']} ({purchase['purchase_id']})",
    )
    show_success(
        f"Request {purchase['purchase_id']} was sent to {store['store_name']}. "
        "Stock is not reserved until the store confirms, so the request may still be "
        "rejected. Your receipt will be issued after confirmation."
    )
