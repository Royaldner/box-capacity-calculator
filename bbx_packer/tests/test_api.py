"""
BBX Packer API Tests
====================
Tests all endpoints: calculate, optimize, validate, resize, can-fit, save,
and admin size management.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient
from bbx_packer.api.app import app
from bbx_packer.bbx_sizes import bbx_size_store

client = TestClient(app)


# ═══════════════════════════════════════════════════════════
# Test Data
# ═══════════════════════════════════════════════════════════

TOTE_BAG = {"sku": "BAG-001", "name": "Leather Tote", "category": "bag",
            "shape_type": "soft", "width": 12, "depth": 10, "height": 4,
            "weight_kg": 0.5, "price": 89.99, "status": "paid"}

LOTION = {"sku": "BOT-001", "name": "Body Lotion", "category": "bottle",
          "shape_type": "cylinder", "radius": 1.25, "height": 7,
          "weight_kg": 0.4, "price": 18.99, "status": "cart"}

TSHIRT = {"sku": "CLO-001", "name": "Cotton T-Shirt", "category": "clothing",
          "shape_type": "fabric", "width": 10, "depth": 8, "height": 0.5,
          "weight_kg": 0.15, "price": 29.99, "status": "cart", "max_folds": 3}

SHOES = {"sku": "FTW-001", "name": "Running Shoes", "category": "footwear",
         "shape_type": "box", "width": 13, "depth": 7.5, "height": 5,
         "weight_kg": 0.7, "price": 129.99, "status": "paid"}

OVERSIZED = {"sku": "BIG-001", "name": "Giant Duffel", "category": "bag",
             "shape_type": "soft", "width": 25, "depth": 25, "height": 25,
             "weight_kg": 2.0, "price": 199.99, "status": "cart"}

COIN_PURSE = {"sku": "BAG-003", "name": "Coin Purse", "category": "bag",
              "shape_type": "soft", "width": 3, "depth": 2, "height": 0.33,
              "weight_kg": 0.05, "price": 15.99, "status": "cart"}


# ═══════════════════════════════════════════════════════════
# Health + Sizes
# ═══════════════════════════════════════════════════════════

class TestBasic:
    def test_health(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_get_sizes(self):
        r = client.get("/api/bbx/sizes")
        assert r.status_code == 200
        sizes = r.json()["sizes"]
        assert len(sizes) >= 3
        ids = [s["id"] for s in sizes]
        assert "SMALL" in ids
        assert "MEDIUM" in ids
        assert "LARGE" in ids

    def test_sizes_have_volume(self):
        r = client.get("/api/bbx/sizes")
        for s in r.json()["sizes"]:
            assert s["volume"] > 0
            assert s["label"]


# ═══════════════════════════════════════════════════════════
# Calculate
# ═══════════════════════════════════════════════════════════

class TestCalculate:
    def test_calculate_empty(self):
        r = client.post("/api/bbx/calculate", json={"bbx_size": "LARGE", "items": []})
        assert r.status_code == 200
        data = r.json()
        assert data["fill_percentage"] == 0.0
        assert data["total_items"] == 0

    def test_calculate_single_item(self):
        r = client.post("/api/bbx/calculate", json={"bbx_size": "LARGE", "items": [TOTE_BAG]})
        assert r.status_code == 200
        data = r.json()
        assert data["total_items"] == 1
        assert data["fill_percentage"] > 0
        assert data["paid_items"] == 1
        assert data["cart_items"] == 0

    def test_calculate_mixed_status(self):
        r = client.post("/api/bbx/calculate", json={
            "bbx_size": "LARGE",
            "items": [TOTE_BAG, LOTION, TSHIRT]
        })
        data = r.json()
        assert data["total_items"] == 3
        assert data["paid_items"] == 1
        assert data["cart_items"] == 2

    def test_calculate_multiple_items(self):
        items = [TOTE_BAG, LOTION, TSHIRT, SHOES, COIN_PURSE]
        r = client.post("/api/bbx/calculate", json={"bbx_size": "LARGE", "items": items})
        data = r.json()
        assert data["total_items"] == 5
        assert len(data["failed_items"]) == 0
        assert data["fill_percentage"] > 0
        assert data["items_hash"]  # Hash exists

    def test_calculate_has_positions(self):
        r = client.post("/api/bbx/calculate", json={"bbx_size": "LARGE", "items": [TOTE_BAG]})
        item = r.json()["items"][0]
        assert "position" in item
        assert len(item["position"]) == 3
        assert "rotation" in item
        assert "fold" in item
        assert item["sku"] == "BAG-001"
        assert item["status"] == "paid"

    def test_calculate_invalid_size(self):
        r = client.post("/api/bbx/calculate", json={"bbx_size": "NONEXISTENT", "items": []})
        assert r.status_code == 404

    def test_calculate_oversized_fails(self):
        r = client.post("/api/bbx/calculate", json={"bbx_size": "SMALL", "items": [OVERSIZED]})
        data = r.json()
        assert len(data["failed_items"]) == 1
        assert data["failed_items"][0]["sku"] == "BIG-001"

    def test_paid_items_placed_first(self):
        """Paid items should get priority placement."""
        items = [LOTION, TOTE_BAG]  # Cart first in list, paid second
        r = client.post("/api/bbx/calculate", json={"bbx_size": "LARGE", "items": items})
        data = r.json()
        # Paid item (tote bag) should be at lower Z (placed first)
        paid = [i for i in data["items"] if i["status"] == "paid"][0]
        assert paid["position"][2] == 0  # On the floor


# ═══════════════════════════════════════════════════════════
# Optimize
# ═══════════════════════════════════════════════════════════

class TestOptimize:
    def test_optimize(self):
        items = [TOTE_BAG, LOTION, TSHIRT, SHOES]
        r = client.post("/api/bbx/optimize", json={"bbx_size": "LARGE", "items": items})
        data = r.json()
        assert data["total_items"] == 4
        assert data["fill_percentage"] > 0


# ═══════════════════════════════════════════════════════════
# Validate
# ═══════════════════════════════════════════════════════════

class TestValidate:
    def test_validate_matching(self):
        # First calculate to get hash
        items = [TOTE_BAG, LOTION]
        r = client.post("/api/bbx/calculate", json={"bbx_size": "LARGE", "items": items})
        saved_hash = r.json()["items_hash"]

        # Validate with same items
        r2 = client.post("/api/bbx/validate", json={
            "saved_hash": saved_hash,
            "current_items": items,
        })
        assert r2.json()["valid"] is True

    def test_validate_changed(self):
        items = [TOTE_BAG, LOTION]
        r = client.post("/api/bbx/calculate", json={"bbx_size": "LARGE", "items": items})
        saved_hash = r.json()["items_hash"]

        # Validate with different items (added tshirt)
        r2 = client.post("/api/bbx/validate", json={
            "saved_hash": saved_hash,
            "current_items": [TOTE_BAG, LOTION, TSHIRT],
        })
        assert r2.json()["valid"] is False


# ═══════════════════════════════════════════════════════════
# Resize
# ═══════════════════════════════════════════════════════════

class TestResize:
    def test_resize_up(self):
        items = [TOTE_BAG, SHOES]
        r = client.post("/api/bbx/resize", json={"new_size": "LARGE", "items": items})
        data = r.json()
        assert data["bbx"]["size_id"] == "LARGE"
        assert data["total_items"] == 2

    def test_resize_down_items_dont_fit(self):
        # Big items in small box
        items = [TOTE_BAG, SHOES, {"sku": "BIG-002", "name": "Big Bag",
                 "category": "bag", "shape_type": "soft",
                 "width": 13, "depth": 13, "height": 9,
                 "status": "cart", "price": 50}]
        r = client.post("/api/bbx/resize", json={"new_size": "SMALL", "items": items})
        data = r.json()
        # Some may not fit
        assert data["bbx"]["size_id"] == "SMALL"


# ═══════════════════════════════════════════════════════════
# Can Fit
# ═══════════════════════════════════════════════════════════

class TestCanFit:
    def test_can_fit_yes(self):
        r = client.post("/api/bbx/can-fit", json={
            "bbx_size": "LARGE",
            "current_items": [TOTE_BAG],
            "new_item": LOTION,
        })
        data = r.json()
        assert data["fits"] is True
        assert data["new_fill_percentage"] > 0

    def test_can_fit_no(self):
        r = client.post("/api/bbx/can-fit", json={
            "bbx_size": "SMALL",
            "current_items": [],
            "new_item": OVERSIZED,
        })
        data = r.json()
        assert data["fits"] is False
        assert data["suggestion"]


# ═══════════════════════════════════════════════════════════
# Save Validation
# ═══════════════════════════════════════════════════════════

class TestSave:
    def test_save_valid(self):
        r = client.post("/api/bbx/save", json={
            "bbx_size": "LARGE",
            "items_hash": "abc123",
            "arrangement": {"items": [{"sku": "BAG-001"}, {"sku": "BOT-001"}]},
            "customer_item_skus": ["BAG-001", "BOT-001"],
        })
        assert r.json()["ok"] is True

    def test_save_sku_mismatch(self):
        r = client.post("/api/bbx/save", json={
            "bbx_size": "LARGE",
            "items_hash": "abc123",
            "arrangement": {"items": [{"sku": "BAG-001"}, {"sku": "FAKE-999"}]},
            "customer_item_skus": ["BAG-001", "BOT-001"],
        })
        assert r.json()["ok"] is False
        assert "mismatch" in r.json()["reason"].lower()


# ═══════════════════════════════════════════════════════════
# Admin — Size Management
# ═══════════════════════════════════════════════════════════

class TestAdmin:
    def test_add_size(self):
        r = client.post("/api/admin/sizes", json={
            "id": "XL-TEST", "name": "Extra Large Test",
            "width": 24, "depth": 24, "height": 24,
            "price": 14.99, "sort_order": 4,
        })
        assert r.status_code == 200
        assert r.json()["size"]["id"] == "XL-TEST"
        # Cleanup
        client.delete("/api/admin/sizes/XL-TEST")

    def test_add_duplicate_fails(self):
        r = client.post("/api/admin/sizes", json={
            "id": "LARGE", "name": "Duplicate",
            "width": 10, "depth": 10, "height": 10,
        })
        assert r.status_code == 400

    def test_update_size(self):
        # Add a test size
        client.post("/api/admin/sizes", json={
            "id": "UPDATE-TEST", "name": "Test",
            "width": 10, "depth": 10, "height": 10,
        })
        r = client.put("/api/admin/sizes/UPDATE-TEST", json={"name": "Updated Name", "price": 9.99})
        assert r.status_code == 200
        assert r.json()["size"]["name"] == "Updated Name"
        assert r.json()["size"]["price"] == 9.99
        # Cleanup
        client.delete("/api/admin/sizes/UPDATE-TEST")

    def test_toggle_size(self):
        client.post("/api/admin/sizes", json={
            "id": "TOGGLE-TEST", "name": "Toggle",
            "width": 10, "depth": 10, "height": 10,
        })
        # Deactivate
        r = client.put("/api/admin/sizes/TOGGLE-TEST/toggle")
        assert r.json()["size"]["is_active"] is False

        # Reactivate
        r = client.put("/api/admin/sizes/TOGGLE-TEST/toggle")
        assert r.json()["size"]["is_active"] is True
        # Cleanup
        client.delete("/api/admin/sizes/TOGGLE-TEST")

    def test_delete_size(self):
        client.post("/api/admin/sizes", json={
            "id": "DELETE-ME", "name": "Temp",
            "width": 10, "depth": 10, "height": 10,
        })
        r = client.delete("/api/admin/sizes/DELETE-ME")
        assert r.status_code == 200
        # Verify gone
        assert bbx_size_store.get("DELETE-ME") is None

    def test_delete_nonexistent(self):
        r = client.delete("/api/admin/sizes/DOESNT-EXIST")
        assert r.status_code == 404

    def test_admin_sees_all_sizes(self):
        r = client.get("/api/admin/sizes")
        assert r.status_code == 200
        assert len(r.json()["sizes"]) >= 3


# ═══════════════════════════════════════════════════════════
# Fabric Folding via API
# ═══════════════════════════════════════════════════════════

class TestFolding:
    def test_fabric_item_can_fold(self):
        """A wide fabric item should be foldable to fit in SMALL box."""
        wide_scarf = {"sku": "CLO-X", "name": "Wide Scarf", "category": "clothing",
                      "shape_type": "fabric", "width": 20, "depth": 10, "height": 0.5,
                      "status": "cart", "max_folds": 2}
        r = client.post("/api/bbx/calculate", json={"bbx_size": "SMALL", "items": [wide_scarf]})
        data = r.json()
        assert data["total_items"] == 1
        assert data["items"][0]["fold"] != "original"  # Was folded


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
