"""Placed Item — records where an item was placed in the BBX."""

from dataclasses import dataclass
from enum import Enum
from ..domain.item import Item


class Rotation(Enum):
    WDH = "wdh"
    WHD = "whd"
    DWH = "dwh"
    DHW = "dhw"
    HWD = "hwd"
    HDW = "hdw"


def get_rotated_dimensions(original, rotation):
    w, d, h = original
    m = {
        Rotation.WDH: (w, d, h), Rotation.WHD: (w, h, d),
        Rotation.DWH: (d, w, h), Rotation.DHW: (d, h, w),
        Rotation.HWD: (h, w, d), Rotation.HDW: (h, d, w),
    }
    return m[rotation]


@dataclass
class PlacedItem:
    item: Item
    position: tuple[int, int, int]
    rotation: Rotation = Rotation.WDH
    fold_description: str = "original"
    placed_dims: tuple[float, float, float] = (0, 0, 0)
    voxels_used: int = 0

    @property
    def name(self) -> str:
        return self.item.name

    @property
    def sku(self) -> str:
        return self.item.sku

    @property
    def status(self) -> str:
        return self.item.status

    @property
    def is_folded(self) -> bool:
        return self.fold_description != "original"

    def position_inches(self, resolution: float) -> tuple[float, float, float]:
        return tuple(p * resolution for p in self.position)

    def to_dict(self, resolution: float) -> dict:
        pos = self.position_inches(resolution)
        return {
            "sku": self.sku,
            "name": self.name,
            "status": self.status,
            "category": self.item.category.value,
            "position": [round(p, 2) for p in pos],
            "grid_position": list(self.position),
            "grid_size": [
                max(1, int(self.placed_dims[0] / resolution)) if self.placed_dims[0] else 0,
                max(1, int(self.placed_dims[1] / resolution)) if self.placed_dims[1] else 0,
                max(1, int(self.placed_dims[2] / resolution)) if self.placed_dims[2] else 0,
            ],
            "rotation": self.rotation.value,
            "fold": self.fold_description,
            "placed_dimensions": [round(d, 2) for d in self.placed_dims],
            "volume": round(self.item.volume, 2),
            "price": self.item.price,
            "weight_kg": self.item.weight_kg,
            "shape_type": self.item.shape_type.value,
            "voxels": self.voxels_used,
        }
