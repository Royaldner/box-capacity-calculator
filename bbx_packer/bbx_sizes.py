"""
BBX Size Store
==============
Manages BBX sizes dynamically. In production, this reads/writes
to your e-commerce database. For now, it uses an in-memory store
with default sizes.

WHY DYNAMIC?
    Hardcoded sizes mean redeploying code to add a new box.
    Dynamic sizes mean an admin panel toggle. Much better for
    a real business where box suppliers change, new sizes get
    introduced, or seasonal boxes are offered.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
import json


@dataclass
class BBXSizeConfig:
    """One BBX size option."""
    id: str                    # Unique identifier, e.g. "SMALL", "HOLIDAY-XL"
    name: str                  # Display name, e.g. "Small Box"
    width: float               # inches
    depth: float               # inches
    height: float              # inches
    price: float = 0.0         # Box price (your business logic)
    is_active: bool = True     # Admin can disable without deleting
    sort_order: int = 0        # Display ordering

    @property
    def volume(self) -> float:
        return self.width * self.depth * self.height

    @property
    def label(self) -> str:
        return f'{self.width:.0f}"W × {self.depth:.0f}"D × {self.height:.0f}"H'

    def to_dict(self) -> dict:
        d = asdict(self)
        d["volume"] = self.volume
        d["label"] = self.label
        return d


class BBXSizeStore:
    """
    In-memory store for BBX sizes.

    In production, replace this with:
        class BBXSizeStore:
            def __init__(self, db_connection):
                self.db = db_connection

            def get_all_active(self):
                return self.db.query("SELECT * FROM bbx_sizes WHERE is_active=1")
    """

    def __init__(self):
        self._sizes: dict[str, BBXSizeConfig] = {}
        self._load_defaults()

    def _load_defaults(self):
        """Load the three original BBX sizes."""
        defaults = [
            BBXSizeConfig(id="SMALL", name="Small Box", width=14, depth=14, height=10, price=5.99, sort_order=1),
            BBXSizeConfig(id="MEDIUM", name="Medium Box", width=16, depth=16, height=34, price=8.99, sort_order=2),
            BBXSizeConfig(id="LARGE", name="Large Box", width=20, depth=20, height=18, price=11.99, sort_order=3),
        ]
        for s in defaults:
            self._sizes[s.id] = s

    def get(self, size_id: str) -> Optional[BBXSizeConfig]:
        return self._sizes.get(size_id)

    def get_all(self) -> list[BBXSizeConfig]:
        return sorted(self._sizes.values(), key=lambda s: s.sort_order)

    def get_all_active(self) -> list[BBXSizeConfig]:
        return [s for s in self.get_all() if s.is_active]

    def add(self, config: BBXSizeConfig) -> BBXSizeConfig:
        if config.id in self._sizes:
            raise ValueError(f"BBX size '{config.id}' already exists")
        if config.width <= 0 or config.depth <= 0 or config.height <= 0:
            raise ValueError("All dimensions must be positive")
        self._sizes[config.id] = config
        return config

    def update(self, size_id: str, **kwargs) -> BBXSizeConfig:
        if size_id not in self._sizes:
            raise KeyError(f"BBX size '{size_id}' not found")
        existing = self._sizes[size_id]
        for key, value in kwargs.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        return existing

    def delete(self, size_id: str) -> None:
        if size_id not in self._sizes:
            raise KeyError(f"BBX size '{size_id}' not found")
        del self._sizes[size_id]

    def deactivate(self, size_id: str) -> BBXSizeConfig:
        """Soft delete — disable without removing."""
        return self.update(size_id, is_active=False)

    def activate(self, size_id: str) -> BBXSizeConfig:
        return self.update(size_id, is_active=True)


# Global instance — in production, initialize with DB connection
bbx_size_store = BBXSizeStore()
