from core.config import CHANGELOG_FILE
from core.helpers import next_id, timestamp
from core.models import AppState, Record
from services.storage import JSONStorage
from core.ui import show_error, show_header, show_info


# ============================================================ CHANGELOG ============================================================

def log_activity(state: AppState, user: Record, action: str, description: str) -> None:
    """Record an important activity. Never pass passwords or document contents."""
    actor_id = user.get("user_id") or user.get("admin_id") or user.get("username", "")

    state.changelogs.append(
        {
            "log_id": next_id(state.changelogs, "log_id", "LOG"),
            "user_id": actor_id,
            "username": user.get("username", ""),
            "role": user.get("role", ""),
            "action": action,
            "description": description,
            "date_created": timestamp(),
        }
    )
    JSONStorage.save(CHANGELOG_FILE, state.changelogs)


def view_changelogs(state: AppState) -> None:
    show_header("SYSTEM CHANGELOG")

    if not state.changelogs:
        show_info("No activities have been recorded yet.")
        return

    raw = input("How many recent entries to show? (Enter for 20, 'all' for everything): ").strip().lower()

    if raw == "all":
        entries = state.changelogs
    elif raw == "":
        entries = state.changelogs[-20:]
    elif raw.isdigit() and int(raw) > 0:
        entries = state.changelogs[-int(raw):]
    else:
        show_error("Enter a positive number or 'all'.")
        return

    for entry in reversed(entries):
        print(
            f"{entry['log_id']} | {entry['date_created']} | {entry['username']} "
            f"({entry['role']}) | {entry['action']} | {entry['description']}"
        )
    print(f"\nShowing {len(entries)} of {len(state.changelogs)} entries (newest first).")
