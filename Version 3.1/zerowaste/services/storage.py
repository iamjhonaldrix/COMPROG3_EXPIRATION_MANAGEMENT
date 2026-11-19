import json
import os
import shutil
from datetime import datetime
from typing import Any

from core.config import (
    ADMIN_FILE,
    CHANGELOG_FILE,
    PRODUCTS_FILE,
    PURCHASES_FILE,
    REPORTS_FILE,
    STORES_FILE,
    SUPER_ADMIN_FILE,
    USERS_FILE,
)
from services.documents import organize_verification_documents
from core.models import AppState, Records
from services.security import new_staff_account, normalize_staff_accounts
from core.ui import show_error, show_info


# ============================================================ JSON STORAGE ============================================================

class JSONStorage:
    """Loads and saves the application's JSON collections."""

    FILES = {
        "users": USERS_FILE,
        "admins": ADMIN_FILE,
        "super_admins": SUPER_ADMIN_FILE,
        "stores": STORES_FILE,
        "products": PRODUCTS_FILE,
        "purchases": PURCHASES_FILE,
        "reports": REPORTS_FILE,
        "changelogs": CHANGELOG_FILE,
    }

    @staticmethod
    def save(filename: str, records: Any) -> None:
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(records, file, indent=4, ensure_ascii=False)

    @staticmethod
    def _default_records(filename: str) -> Records:
        """Fixed default accounts are seeded for the staff files only."""
        if filename == SUPER_ADMIN_FILE:
            return [new_staff_account("SA0001", "superadmin", "superadmin", "Super Admin")]
        if filename == ADMIN_FILE:
            return [new_staff_account("A0001", "admin", "admin", "Admin")]
        return []

    @staticmethod
    def _backup_corrupted(filename: str) -> None:
        """Keep a copy of an unreadable file before it is replaced."""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = f"{filename}.corrupt_{stamp}.bak"
        try:
            shutil.copy2(filename, backup)
            show_info(f"{filename} could not be read. A backup was saved as {backup}.")
        except OSError:
            show_error(f"{filename} could not be read and no backup could be made.")

    @classmethod
    def load(cls, filename: str) -> Records:
        if not os.path.exists(filename):
            records = cls._default_records(filename)
            cls.save(filename, records)
            return records

        try:
            with open(filename, "r", encoding="utf-8") as file:
                records = json.load(file)

            if not isinstance(records, list):
                raise ValueError("Expected a JSON list.")

            return records

        except (json.JSONDecodeError, ValueError, OSError):
            cls._backup_corrupted(filename)
            records = cls._default_records(filename)
            cls.save(filename, records)
            return records

    @classmethod
    def load_state(cls) -> AppState:
        state = AppState(
            users=cls.load(USERS_FILE),
            admins=cls.load(ADMIN_FILE),
            super_admins=cls.load(SUPER_ADMIN_FILE),
            stores=cls.load(STORES_FILE),
            products=cls.load(PRODUCTS_FILE),
            purchases=cls.load(PURCHASES_FILE),
            reports=cls.load(REPORTS_FILE),
            changelogs=cls.load(CHANGELOG_FILE),
        )

        changed = organize_verification_documents(state.users)
        changed = normalize_staff_accounts(state) or changed

        if changed:
            cls.save_state(state)

        return state

    @classmethod
    def save_state(cls, state: AppState) -> None:
        for attribute, filename in cls.FILES.items():
            cls.save(filename, getattr(state, attribute))


def save_state(state: AppState) -> None:
    JSONStorage.save_state(state)
