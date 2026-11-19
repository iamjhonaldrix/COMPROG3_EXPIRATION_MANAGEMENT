import os
import shutil
from datetime import datetime
from typing import List, Optional

from core.config import CUSTOMER_DIR, STORAGE_DIR, STORE_REQUIRED_DOCUMENTS, STORES_DIR
from core.models import Record, Records
from core.ui import show_error, show_info, show_success


# ============================================================ VERIFICATION DOCUMENTS ============================================================

def verification_directory(user: Record) -> str:
    base_dir = STORES_DIR if user.get("role") == "Store Owner" else CUSTOMER_DIR
    return os.path.join(base_dir, str(user["user_id"]))


def organize_verification_documents(users: Records) -> bool:
    """Move referenced verification files into Storage's role-specific folders."""
    if not users:
        return False

    managed_roots = [
        os.path.abspath(STORAGE_DIR),
        os.path.abspath("Customer"),
        os.path.abspath("Stores"),
    ]
    changed = False

    for user in users:
        if not isinstance(user, dict):
            continue

        user_id = user.get("user_id")
        documents = user.get("verification_docs", {})

        if not user_id or not isinstance(documents, dict):
            continue

        user_directory = os.path.abspath(verification_directory(user))

        for key, stored_path in list(documents.items()):
            if not isinstance(stored_path, str) or not stored_path:
                continue

            source = os.path.abspath(stored_path)

            try:
                is_managed_file = any(
                    os.path.commonpath([root, source]) == root
                    for root in managed_roots
                )
            except ValueError:
                is_managed_file = False

            if not is_managed_file or not os.path.isfile(source):
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
                destination = os.path.join(user_directory, f"{stem}_{unique_stamp}{extension}")

            shutil.move(source, destination)
            documents[key] = os.path.relpath(destination)
            changed = True

    return changed


def verification_upload_status(path: Optional[str]) -> str:
    if not path:
        return "NOT UPLOADED"
    return "UPLOADED" if os.path.isfile(path) else "FILE NOT FOUND"


def missing_store_documents(owner: Optional[Record]) -> List[str]:
    documents = owner.get("verification_docs", {}) if owner else {}
    return [
        label
        for key, label in STORE_REQUIRED_DOCUMENTS
        if verification_upload_status(documents.get(key)) != "UPLOADED"
    ]


def upload_document(document_name: str, user: Record) -> Optional[str]:
    """Open a file picker and copy the selected image into the user's folder."""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        show_error("The file picker (tkinter) is not available on this computer.")
        return None

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
        show_info("Upload cancelled. No file was selected.")
        return None

    user_directory = verification_directory(user)
    os.makedirs(user_directory, exist_ok=True)

    document_type = document_name.lower().replace(" ", "_")
    unique_stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{document_type}_{unique_stamp}_{os.path.basename(selected_path)}"
    destination = os.path.join(user_directory, filename)

    shutil.copy2(selected_path, destination)
    show_success(f"{document_name} was saved to {destination}.")
    return destination
