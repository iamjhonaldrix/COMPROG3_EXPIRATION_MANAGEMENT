from dataclasses import dataclass
from typing import Any, Dict, List


Record = Dict[str, Any]
Records = List[Record]


@dataclass
class AppState:
    """Holds the application's in-memory collections in one object."""

    users: Records
    admins: Records
    super_admins: Records
    stores: Records
    products: Records
    purchases: Records
    reports: Records
    changelogs: Records
