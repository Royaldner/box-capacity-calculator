"""
BBX Packer Configuration
========================
Single source of truth for constants.

KEY CHANGE: BBX sizes are now DYNAMIC.
They're loaded from a store (your database in production).
Admin can add/edit/remove sizes via API.
"""

from enum import Enum


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------
DEFAULT_RESOLUTION: float = 0.25  # inches per voxel (backend precision)
API_RESOLUTION: float = 0.5       # inches per voxel (API/optimize calls — faster)


# ---------------------------------------------------------------------------
# Item Categories
# ---------------------------------------------------------------------------
class ItemCategory(str, Enum):
    BAG = "bag"
    BOTTLE = "bottle"
    SPRAY = "spray"
    FOOTWEAR = "footwear"
    CLOTHING = "clothing"
    FLAT_ITEM = "flat_item"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Shape Types
# ---------------------------------------------------------------------------
class ShapeType(str, Enum):
    BOX = "box"
    CYLINDER = "cylinder"
    SOFT = "soft"
    FABRIC = "fabric"


# ---------------------------------------------------------------------------
# Packing
# ---------------------------------------------------------------------------
class PackingMode(str, Enum):
    REALTIME = "realtime"
    OPTIMIZED = "optimized"


# ---------------------------------------------------------------------------
# Soft / Fabric Settings
# ---------------------------------------------------------------------------
DEFAULT_COMPRESSIBILITY: float = 0.85
MAX_FOLDS: int = 3
FOLD_THICKNESS_PENALTY: float = 1.05
