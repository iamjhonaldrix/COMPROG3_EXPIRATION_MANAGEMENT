from services.changelog import log_activity
from core.config import STORE_REQUIRED_DOCUMENTS
from services.documents import missing_store_documents, verification_upload_status
from core.helpers import find_record, get_owner_store, next_id, read_number, timestamp
from core.models import AppState, Record
from services.storage import save_state
from core.ui import show_error, show_header, show_info, show_success


# ============================================================ ADMIN APPROVAL AND REPORTS ============================================================

def admin_panel(user: Record, state: AppState) -> None:
    pending = [s for s in state.stores if s.get("status") == "Pending"]

    if not pending:
        show_info("No pending store applications.")
        return

    show_header("STORE APPLICATIONS")

    for number, store in enumerate(pending, 1):
        owner = find_record(state.users, "user_id", store.get("owner_id"))
        owner_name = owner.get("username", "Unknown") if owner else "Unknown"
        documents = owner.get("verification_docs", {}) if owner else {}

        print(f"{number}. {store['store_id']} | {store['store_name']} | Owner: {owner_name} | Area: {store['area']}")

        statuses = [
            f"{label}: {verification_upload_status(documents.get(key))}"
            for key, label in STORE_REQUIRED_DOCUMENTS
        ]

        if documents.get("business_document"):
            statuses.append(
                "Legacy Business Document: "
                + verification_upload_status(documents["business_document"])
            )

        print("   Account verification: " + " | ".join(statuses))

    choice = read_number("Select application (0 to cancel): ", int)
    if choice is None:
        show_error("Enter a valid number.")
        return
    if choice == 0:
        return
    if not 1 <= choice <= len(pending):
        show_error(f"Invalid selection. Choose a number from 1 to {len(pending)}.")
        return

    store = pending[choice - 1]
    owner = find_record(state.users, "user_id", store.get("owner_id"))
    verification_docs = owner.get("verification_docs", {}) if owner else {}

    show_header("OWNER VERIFICATION DOCUMENTS")
    document_labels = STORE_REQUIRED_DOCUMENTS + [
        ("business_document", "Legacy Business Document")
    ]

    for key, label in document_labels:
        path = verification_docs.get(key)
        if path:
            print(f"{label}: {verification_upload_status(path)} - {path}")
        elif key != "business_document":
            print(f"{label}: NOT UPLOADED")

    print("1. Approve\n2. Reject\n3. Leave Pending / Return")
    decision = input("Decision: ").strip()

    if decision == "1":
        missing_documents = missing_store_documents(owner)
        if missing_documents:
            show_error(
                "Cannot approve this store. Required documents missing or unavailable: "
                + ", ".join(missing_documents)
                + "."
            )
            show_info(
                "The application remains pending. Ask the owner to upload the documents, "
                "then review the application again."
            )
            return

        store["status"] = "Approved"
        store["reviewed_at"] = timestamp()
        if owner:
            owner["status"] = "Approved"
        save_state(state)
        log_activity(state, user, "APPROVE_STORE", f"Approved store {store['store_name']} ({store['store_id']})")
        show_success(f"{store['store_name']} was approved and can now post products.")
    elif decision == "2":
        reason = input("Reason for rejection: ").strip()
        if not reason:
            show_error("A reason is required to reject a store application.")
            return

        store["status"] = "Rejected"
        store["reviewed_at"] = timestamp()
        store["rejection_reason"] = reason
        if owner:
            owner["status"] = "Rejected"
        save_state(state)
        log_activity(state, user, "REJECT_STORE", f"Rejected store {store['store_name']} ({store['store_id']})")
        show_success(
            f"{store['store_name']} was rejected. The owner can fix the issue and resubmit."
        )
    elif decision == "3":
        show_info(
            "The application remains pending. The owner can upload documents and be reviewed again."
        )
        return
    else:
        show_error("Invalid decision. Enter 1, 2, or 3.")


def resubmit_store_application(user: Record, state: AppState) -> None:
    store = get_owner_store(user, state.stores)
    if not store or store.get("status") != "Rejected":
        show_error("Only a rejected store application can be resubmitted.")
        return

    missing_documents = missing_store_documents(user)
    if missing_documents:
        show_error(
            "Cannot resubmit yet. Required documents missing or unavailable: "
            + ", ".join(missing_documents)
            + "."
        )
        show_info("Upload the required documents under Account Verification, then try again.")
        return

    if input("Resubmit this store application for review? (y/n): ").strip().lower() != "y":
        show_info("Resubmission cancelled.")
        return

    store["status"] = "Pending"
    store["resubmitted_at"] = timestamp()
    user["status"] = "Pending"
    save_state(state)
    log_activity(
        state,
        user,
        "RESUBMIT_STORE",
        f"Resubmitted store {store['store_name']} ({store['store_id']}) for review",
    )
    show_success(f"{store['store_name']} was resubmitted and is pending admin review.")


def create_report(user: Record, state: AppState) -> None:
    if not state.products:
        show_info("There are no products to report yet.")
        return

    product_id = input("Product ID to report: ").strip().upper()
    product = find_record(state.products, "product_id", product_id)

    if not product:
        show_error(f"No product with ID '{product_id}' was found.")
        return

    reason = input("Reason for report: ").strip()
    if not reason:
        show_error("Report reason cannot be empty.")
        return

    report = {
        "report_id": next_id(state.reports, "report_id", "REP"),
        "reporter_id": user["user_id"],
        "product_id": product["product_id"],
        "store_id": product["store_id"],
        "reason": reason,
        "status": "Pending",
        "created_at": timestamp(),
    }
    state.reports.append(report)

    save_state(state)
    log_activity(state, user, "REPORT_PRODUCT", f"Reported {product['name']} ({product['product_id']})")
    show_success(f"Report {report['report_id']} was submitted. An admin will review it.")


def review_reports(user: Record, state: AppState) -> None:
    pending = [r for r in state.reports if r.get("status") == "Pending"]

    if not pending:
        show_info("No pending reports.")
        return

    for report in pending:
        print(f"\n{report['report_id']} | Product: {report['product_id']} | Reason: {report['reason']}")
        choice = input("Confirm report? (y/n, Enter to skip): ").strip().lower()

        if choice not in ("y", "n"):
            continue

        report["status"] = "Confirmed" if choice == "y" else "Dismissed"
        report["reviewed_at"] = timestamp()

        if choice == "y":
            store = find_record(state.stores, "store_id", report["store_id"])
            product = find_record(state.products, "product_id", report["product_id"])

            if store:
                store["trust_score"] = store.get("trust_score", 0) - 1
            if product:
                product["status"] = "Removed"
                product["last_updated"] = timestamp()

            log_activity(state, user, "CONFIRM_REPORT", f"Confirmed {report['report_id']}; removed {report['product_id']}")
            show_success("Report confirmed. The listing was removed and the store's trust score reduced.")
        else:
            log_activity(state, user, "DISMISS_REPORT", f"Dismissed {report['report_id']}")
            show_success("Report dismissed. No action was taken on the listing.")

    save_state(state)


def remove_product(user: Record, state: AppState) -> None:
    product_id = input("Product ID to remove: ").strip().upper()
    product = find_record(state.products, "product_id", product_id)

    if not product:
        show_error(f"No product with ID '{product_id}' was found.")
        return
    if product.get("status") == "Removed":
        show_info("That listing is already removed.")
        return

    reason = input("Reason for removal: ").strip()
    if not reason:
        show_error("A reason is required to remove a listing.")
        return

    product["status"] = "Removed"
    product["last_updated"] = timestamp()
    save_state(state)
    log_activity(state, user, "REMOVE_PRODUCT", f"Removed {product['name']} ({product_id}): {reason}")
    show_success(f"{product['name']} ({product_id}) was removed from the marketplace.")
