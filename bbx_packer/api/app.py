"""
BBX Packer API
==============
FastAPI endpoints for e-commerce integration.

ENDPOINTS:
    Customer-facing (called by your e-commerce frontend):
        POST /api/bbx/calculate     → Full rebuild from item list
        POST /api/bbx/optimize      → Repack for best arrangement
        POST /api/bbx/validate      → Check if saved state is still current
        POST /api/bbx/resize        → Change BBX size, repack
        POST /api/bbx/can-fit       → Pre-check if new item fits
        POST /api/bbx/save          → Validate and acknowledge save
        GET  /api/bbx/sizes         → Get available BBX sizes

    Admin (called by your admin panel):
        POST   /api/admin/sizes          → Add new BBX size
        PUT    /api/admin/sizes/{id}     → Update BBX size
        DELETE /api/admin/sizes/{id}     → Delete BBX size
        PUT    /api/admin/sizes/{id}/toggle → Activate/deactivate
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

from ..packing.packing_service import packing_service
from ..bbx_sizes import bbx_size_store, BBXSizeConfig
from ..domain.exceptions import BBXSizeNotFoundError


# ═══════════════════════════════════════════════════════════
# API Models (Pydantic)
# ═══════════════════════════════════════════════════════════

class ProductItem(BaseModel):
    sku: str
    name: str
    category: str = "other"
    shape_type: str = "box"
    width: Optional[float] = None
    depth: Optional[float] = None
    height: Optional[float] = None
    radius: Optional[float] = None
    weight_kg: float = 0.0
    price: float = 0.0
    status: str = "cart"
    max_folds: int = 3

    class Config:
        json_schema_extra = {
            "example": {
                "sku": "BAG-001",
                "name": "Leather Tote Bag",
                "category": "bag",
                "shape_type": "soft",
                "width": 12, "depth": 10, "height": 4,
                "weight_kg": 0.5, "price": 89.99,
                "status": "paid"
            }
        }


class CalculateRequest(BaseModel):
    bbx_size: str = Field(..., description="BBX size ID (e.g., 'LARGE')")
    items: list[ProductItem]


class ValidateRequest(BaseModel):
    saved_hash: str
    current_items: list[ProductItem]


class ResizeRequest(BaseModel):
    new_size: str
    items: list[ProductItem]


class CanFitRequest(BaseModel):
    bbx_size: str
    current_items: list[ProductItem]
    new_item: ProductItem


class SaveRequest(BaseModel):
    """
    Arrangement data sent from browser to save.
    Your e-commerce backend saves this to your DB.
    We just validate the item SKUs match.
    """
    bbx_size: str
    items_hash: str
    arrangement: dict
    customer_item_skus: list[str]  # SKUs from your orders + cart DB


class AddSizeRequest(BaseModel):
    id: str = Field(..., min_length=1, max_length=50)
    name: str
    width: float = Field(..., gt=0)
    depth: float = Field(..., gt=0)
    height: float = Field(..., gt=0)
    price: float = 0.0
    sort_order: int = 0


class UpdateSizeRequest(BaseModel):
    name: Optional[str] = None
    width: Optional[float] = None
    depth: Optional[float] = None
    height: Optional[float] = None
    price: Optional[float] = None
    sort_order: Optional[int] = None


# ═══════════════════════════════════════════════════════════
# FastAPI App
# ═══════════════════════════════════════════════════════════

app = FastAPI(
    title="BBX Packer API",
    description="3D bin-packing engine for e-commerce",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════
# Customer Endpoints
# ═══════════════════════════════════════════════════════════

@app.get("/api/bbx/sizes")
async def get_sizes():
    """Get all available BBX sizes for the frontend dropdown."""
    return {"sizes": packing_service.get_available_sizes()}


@app.post("/api/bbx/calculate")
async def calculate(req: CalculateRequest):
    """
    Full calculation from item list.
    Called on first login or when saved state is stale.
    """
    try:
        items_data = [item.model_dump() for item in req.items]
        result = packing_service.calculate(req.bbx_size, items_data)
        return result.to_dict()
    except BBXSizeNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/bbx/optimize")
async def optimize(req: CalculateRequest):
    """
    Repack all items for optimal arrangement.
    Called when user clicks "Optimize" button.
    """
    try:
        items_data = [item.model_dump() for item in req.items]
        result = packing_service.optimize(req.bbx_size, items_data)
        return result.to_dict()
    except BBXSizeNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/bbx/validate")
async def validate(req: ValidateRequest):
    """
    Quick check: has the item list changed since last save?
    If valid=true, the browser can use its saved state.
    If valid=false, call /calculate to rebuild.
    """
    items_data = [item.model_dump() for item in req.current_items]
    return packing_service.validate(req.saved_hash, items_data)


@app.post("/api/bbx/resize")
async def resize(req: ResizeRequest):
    """Change BBX size and repack everything."""
    try:
        items_data = [item.model_dump() for item in req.items]
        result = packing_service.resize(req.new_size, items_data)
        return result.to_dict()
    except BBXSizeNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/bbx/can-fit")
async def can_fit(req: CanFitRequest):
    """
    Pre-check: will a new item fit in the current BBX?
    Call this before adding to cart to warn the user.
    """
    try:
        current = [item.model_dump() for item in req.current_items]
        new = req.new_item.model_dump()
        return packing_service.can_fit(req.bbx_size, current, new)
    except BBXSizeNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/bbx/save")
async def save_arrangement(req: SaveRequest):
    """
    Validate arrangement data before your backend saves to DB.

    Checks that the SKUs in the arrangement match the customer's
    actual orders + cart. Returns ok=true if valid.

    YOUR BACKEND then saves the arrangement to your bbx_arrangements table.
    """
    arrangement_skus = set()
    if "items" in req.arrangement:
        arrangement_skus = {item.get("sku") for item in req.arrangement["items"]}

    customer_skus = set(req.customer_item_skus)

    if arrangement_skus != customer_skus:
        return {
            "ok": False,
            "reason": "SKU mismatch — arrangement doesn't match current orders/cart",
            "arrangement_skus": sorted(arrangement_skus),
            "customer_skus": sorted(customer_skus),
        }

    # Verify BBX size exists
    size = bbx_size_store.get(req.bbx_size)
    if not size:
        return {"ok": False, "reason": f"BBX size '{req.bbx_size}' not found"}

    return {
        "ok": True,
        "message": "Arrangement validated. Save to your database.",
        "bbx_size": req.bbx_size,
        "items_hash": req.items_hash,
        "item_count": len(arrangement_skus),
    }


# ═══════════════════════════════════════════════════════════
# Admin Endpoints — BBX Size Management
# ═══════════════════════════════════════════════════════════

@app.get("/api/admin/sizes")
async def admin_get_sizes():
    """Get ALL sizes (including inactive) for admin panel."""
    return {"sizes": [s.to_dict() for s in bbx_size_store.get_all()]}


@app.post("/api/admin/sizes")
async def admin_add_size(req: AddSizeRequest):
    """Add a new BBX size option."""
    try:
        config = BBXSizeConfig(
            id=req.id.upper(),
            name=req.name,
            width=req.width,
            depth=req.depth,
            height=req.height,
            price=req.price,
            sort_order=req.sort_order,
        )
        result = bbx_size_store.add(config)
        return {"message": f"Size '{result.id}' created", "size": result.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/admin/sizes/{size_id}")
async def admin_update_size(size_id: str, req: UpdateSizeRequest):
    """Update an existing BBX size."""
    try:
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        if "width" in updates and updates["width"] <= 0:
            raise ValueError("Width must be positive")
        if "depth" in updates and updates["depth"] <= 0:
            raise ValueError("Depth must be positive")
        if "height" in updates and updates["height"] <= 0:
            raise ValueError("Height must be positive")

        result = bbx_size_store.update(size_id.upper(), **updates)
        return {"message": f"Size '{size_id}' updated", "size": result.to_dict()}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/admin/sizes/{size_id}")
async def admin_delete_size(size_id: str):
    """Hard delete a BBX size. Use toggle for soft delete."""
    try:
        bbx_size_store.delete(size_id.upper())
        return {"message": f"Size '{size_id}' deleted"}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.put("/api/admin/sizes/{size_id}/toggle")
async def admin_toggle_size(size_id: str):
    """Activate or deactivate a BBX size."""
    try:
        current = bbx_size_store.get(size_id.upper())
        if not current:
            raise KeyError(f"Size '{size_id}' not found")

        if current.is_active:
            result = bbx_size_store.deactivate(size_id.upper())
            action = "deactivated"
        else:
            result = bbx_size_store.activate(size_id.upper())
            action = "activated"

        return {"message": f"Size '{size_id}' {action}", "size": result.to_dict()}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ═══════════════════════════════════════════════════════════
# Health Check
# ═══════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "active_sizes": len(bbx_size_store.get_all_active()),
    }
