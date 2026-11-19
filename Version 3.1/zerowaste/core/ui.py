# ============================================================ MESSAGE HELPERS ============================================================

def show_header(title: str) -> None:
    print(f"\n--- {title} ---")


def show_success(message: str) -> None:
    print(f"[SUCCESS] {message}")


def show_error(message: str) -> None:
    print(f"[ERROR] {message}")


def show_info(message: str) -> None:
    print(f"[INFO] {message}")
