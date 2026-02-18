"""
Packing Service
===============
Orchestrates packing operations. This is what the API calls.

KEY DESIGN: Stateless.
    The service doesn't hold state between calls. Your e-commerce DB
    is the source of truth. Each call receives items and returns results.
    The client (browser) handles real-time add/remove locally.
    The server only runs: calculate, optimize, validate, resize.
"""

import hashlib
import json
from typing import Optional

from ..config import API_RESOLUTION
from ..bbx_sizes import BBXSizeConfig, bbx_size_store
from ..domain.bbx import BBX
from ..domain.item import Item, item_from_product_data
from ..domain.placed_item import PlacedItem
from ..domain.exceptions import BBXSizeNotFoundError
from ..packing.greedy_packer import GreedyPacker


class PackingResult:
    """Result of a packing operation."""

    def __init__(self, bbx: BBX, placed: list[PlacedItem],
                 failed: list[Item], size_config: BBXSizeConfig):
        self.bbx = bbx
        self.placed = placed
        self.failed = failed
        self.size_config = size_config

    def to_dict(self) -> dict:
        resolution = self.bbx.resolution
        items_data = [p.to_dict(resolution) for p in self.placed]
        failed_data = [{"sku": f.sku, "name": f.name, "status": f.status} for f in self.failed]

        # Generate hash for change detection
        skus_str = ",".join(sorted(f"{p.item.sku}:{p.item.status}" for p in self.placed))
        items_hash = hashlib.md5(skus_str.encode()).hexdigest()[:12]

        return {
            "bbx": {
                "size_id": self.size_config.id,
                "name": self.size_config.name,
                "width": self.size_config.width,
                "depth": self.size_config.depth,
                "height": self.size_config.height,
                "label": self.size_config.label,
                "price": self.size_config.price,
                "total_volume": round(self.bbx.total_volume, 1),
            },
            "fill_percentage": round(self.bbx.fill_percentage, 2),
            "remaining_percentage": round(self.bbx.remaining_percentage, 2),
            "occupied_volume": round(self.bbx.occupied_volume, 1),
            "total_items": len(self.placed),
            "paid_items": sum(1 for p in self.placed if p.status == "paid"),
            "cart_items": sum(1 for p in self.placed if p.status == "cart"),
            "items": items_data,
            "failed_items": failed_data,
            "items_hash": items_hash,
            "grid_info": {
                "resolution": resolution,
                "nx": self.bbx.nx,
                "ny": self.bbx.ny,
                "nz": self.bbx.nz,
            },
        }


class PackingService:
    """Main service for all packing operations."""

    def __init__(self):
        self.packer = GreedyPacker()

    def calculate(self, size_id: str, items_data: list[dict],
                  resolution: float = API_RESOLUTION) -> PackingResult:
        """
        Full calculation from item list.

        Called on:
        - First login (no saved state)
        - When saved state is stale (items changed)

        Args:
            size_id: BBX size identifier (e.g., "LARGE")
            items_data: List of product dicts from your e-commerce DB
            resolution: Voxel size (0.5 for API speed, 0.25 for precision)
        """
        size_config = bbx_size_store.get(size_id)
        if not size_config:
            raise BBXSizeNotFoundError(size_id)

        bbx = BBX(size_config.width, size_config.depth, size_config.height,
                   resolution, size_config.id)

        items = [item_from_product_data(d) for d in items_data]
        placed, failed = self.packer.pack_all(bbx, items)

        return PackingResult(bbx, placed, failed, size_config)

    def optimize(self, size_id: str, items_data: list[dict],
                 resolution: float = API_RESOLUTION) -> PackingResult:
        """
        Repack all items for optimal arrangement.
        Same as calculate but explicitly called by the "Optimize" button.
        Could use a smarter algorithm in the future.
        """
        return self.calculate(size_id, items_data, resolution)

    def validate(self, saved_hash: str, current_items: list[dict]) -> dict:
        """
        Quick check: has the item list changed since last save?

        Args:
            saved_hash: The items_hash from the saved arrangement
            current_items: Current list of items (from orders + cart)

        Returns:
            {"valid": bool, "current_hash": str}
        """
        skus_str = ",".join(sorted(
            f"{d['sku']}:{d.get('status', 'cart')}" for d in current_items
        ))
        current_hash = hashlib.md5(skus_str.encode()).hexdigest()[:12]

        return {
            "valid": saved_hash == current_hash,
            "saved_hash": saved_hash,
            "current_hash": current_hash,
        }

    def resize(self, new_size_id: str, items_data: list[dict],
               resolution: float = API_RESOLUTION) -> PackingResult:
        """
        Change BBX size and repack everything.
        Returns which items fit and which don't.
        """
        return self.calculate(new_size_id, items_data, resolution)

    def can_fit(self, size_id: str, current_items_data: list[dict],
                new_item_data: dict,
                resolution: float = API_RESOLUTION) -> dict:
        """
        Pre-check: will this new item fit if added?

        Used by your frontend before adding to cart.
        """
        size_config = bbx_size_store.get(size_id)
        if not size_config:
            raise BBXSizeNotFoundError(size_id)

        all_items = current_items_data + [new_item_data]
        result = self.calculate(size_id, all_items, resolution)

        new_sku = new_item_data["sku"]
        fits = any(p.sku == new_sku for p in result.placed)

        # Check which other sizes it would fit in
        alternative_sizes = []
        if not fits:
            for sc in bbx_size_store.get_all_active():
                if sc.id == size_id:
                    continue
                alt_result = self.calculate(sc.id, all_items, resolution)
                if all(p.sku == new_sku for p in alt_result.placed
                       if p.sku == new_sku):
                    alternative_sizes.append(sc.to_dict())

        # Find fold info if applicable
        fold_info = None
        if fits:
            for p in result.placed:
                if p.sku == new_sku and p.is_folded:
                    fold_info = p.fold_description

        return {
            "fits": fits,
            "new_fill_percentage": round(result.bbx.fill_percentage, 2) if fits else None,
            "fold_required": fold_info,
            "alternative_sizes": alternative_sizes,
            "suggestion": None if fits else (
                f"Try {alternative_sizes[0]['name']}" if alternative_sizes
                else "Remove an item to make room"
            ),
        }

    def get_available_sizes(self) -> list[dict]:
        """Return all active BBX sizes for the frontend."""
        return [s.to_dict() for s in bbx_size_store.get_all_active()]


# Global instance
packing_service = PackingService()
