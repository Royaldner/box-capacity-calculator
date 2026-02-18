"""
Product Item — Production Version
==================================
Items now have a status field (paid/cart) and can be created
directly from e-commerce product data via a factory function.
"""

from dataclasses import dataclass, field
from typing import Optional

from ..config import ItemCategory, ShapeType, MAX_FOLDS
from ..domain.shapes import Shape, BoxShape, CylinderShape, SoftShape, FabricShape


@dataclass
class Item:
    sku: str
    name: str
    shape: Shape
    category: ItemCategory = ItemCategory.OTHER
    shape_type: ShapeType = ShapeType.BOX
    status: str = "cart"       # "paid" or "cart"
    weight_kg: float = 0.0
    price: float = 0.0
    max_folds: int = MAX_FOLDS

    @property
    def volume(self) -> float:
        return self.shape.volume()

    @property
    def bounding_box(self) -> tuple[float, float, float]:
        return self.shape.bounding_box()

    @property
    def is_foldable(self) -> bool:
        return self.shape.is_foldable

    @property
    def is_compressible(self) -> bool:
        return self.shape.is_compressible


def item_from_product_data(data: dict) -> Item:
    """
    Factory: create an Item from e-commerce product data.

    This is the bridge between your store's data format and our engine.

    Expected data keys:
        sku, name, category, shape_type,
        width/depth/height OR radius/height,
        status ("paid"/"cart"), weight, price, max_folds (optional)
    """
    shape_type = ShapeType(data.get("shape_type", "box"))
    category = ItemCategory(data.get("category", "other"))

    if shape_type == ShapeType.CYLINDER:
        shape = CylinderShape(
            radius=float(data["radius"]),
            height=float(data["height"]),
        )
    elif shape_type == ShapeType.SOFT:
        shape = SoftShape(
            width=float(data["width"]),
            depth=float(data["depth"]),
            height=float(data["height"]),
        )
    elif shape_type == ShapeType.FABRIC:
        shape = FabricShape(
            width=float(data["width"]),
            depth=float(data["depth"]),
            height=float(data["height"]),
            max_folds=int(data.get("max_folds", MAX_FOLDS)),
        )
    else:
        shape = BoxShape(
            width=float(data["width"]),
            depth=float(data["depth"]),
            height=float(data["height"]),
        )

    return Item(
        sku=data["sku"],
        name=data["name"],
        shape=shape,
        category=category,
        shape_type=shape_type,
        status=data.get("status", "cart"),
        weight_kg=float(data.get("weight_kg", data.get("weight", 0))),
        price=float(data.get("price", 0)),
        max_folds=int(data.get("max_folds", MAX_FOLDS)),
    )
