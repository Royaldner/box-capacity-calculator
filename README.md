# Box Capacity Calculator

  **A 3D bin-packing engine for e-commerce shipping optimization.**

  Given a list of products from a shopping cart or paid orders, BBX Packing Calculator determines exactly how to arrange them inside physical shipping boxes using a voxel-based 3D packing algorithm. It handles real product shapes
   -- rigid boxes, cylinders, compressible soft goods, and foldable fabrics -- and returns precise placement coordinates your frontend can visualize.

  <!-- Badges (replace URLs when CI/CD and publishing are configured)
  ![Python](https://img.shields.io/badge/python-3.13-blue)
  ![FastAPI](https://img.shields.io/badge/FastAPI-0.129-green)
  ![License](https://img.shields.io/badge/license-TBD-lightgrey)
  ![Tests](https://img.shields.io/badge/tests-passing-brightgreen)
  -->

  ---

  ## Why This Exists

  Most shipping calculators treat products as abstract volumes and give vague "percentage full" estimates. BBX Packing Calculator solves the actual 3D spatial packing problem:

  - **Real collision detection** -- Items are stamped into a voxel grid. No overlaps, no cheating.
  - **Shape-aware packing** -- Cylinders occupy circular cross-sections, not bounding rectangles.
  - **Fabric folding** -- Clothing items are folded along width or depth axes to fit, with configurable fold limits.
  - **Soft compression** -- Bags, pouches, and other soft goods model compressibility.
  - **Priority placement** -- Paid items are placed before cart items, ensuring confirmed orders always fit.

  The engine is fully stateless. Your e-commerce database remains the source of truth. Each API call receives a list of items and returns a complete packing result.

  ---

  ## Key Features

  - **Voxel-based 3D packing** with configurable resolution (0.25" precision, 0.5" for fast API responses)
  - **4 shape types**: Box, Cylinder, Soft (compressible), Fabric (foldable)
  - **6 rotation orientations** tested per item for optimal placement
  - **Greedy bottom-left-back algorithm** with paid-item priority sorting
  - **Dynamic box sizes** -- Add, edit, activate/deactivate sizes via admin API without redeployment
  - **Fit pre-checking** -- Verify if a new item fits before the customer adds it to their cart
  - **State validation** -- Hash-based detection of item list changes since last save
  - **Alternative size suggestions** -- When an item does not fit, the API recommends larger box options
  - **CORS-enabled** FastAPI backend with auto-generated OpenAPI docs

  ---

  ## Quick Start

  ### Prerequisites

  - Python 3.13+
  - pip

  ### Install

  ```bash
  # Clone the repository
  git clone <repository-url>
  cd bbx-packing-calculator

  # Create and activate a virtual environment
  python -m venv venv
  source venv/bin/activate        # Linux/macOS
  venv\Scripts\activate           # Windows

  # Install dependencies
  pip install -r requirements.txt
  ```

  ### Run

  ```bash
  python run_server.py
  ```

  The server starts at **http://localhost:8000** with hot-reload enabled for development.

  ### Verify

  ```bash
  curl http://localhost:8000/api/health
  ```

  ```json
  {"status": "ok", "version": "1.0.0", "active_sizes": 3}
  ```

  ### Try a packing calculation

  ```bash
  curl -X POST http://localhost:8000/api/bbx/calculate \
    -H "Content-Type: application/json" \
    -d '{
      "bbx_size": "LARGE",
      "items": [
        {
          "sku": "BAG-001",
          "name": "Leather Tote Bag",
          "category": "bag",
          "shape_type": "soft",
          "width": 12, "depth": 10, "height": 4,
          "weight_kg": 0.5, "price": 89.99,
          "status": "paid"
        },
        {
          "sku": "BOT-001",
          "name": "Body Lotion",
          "category": "bottle",
          "shape_type": "cylinder",
          "radius": 1.25, "height": 7,
          "weight_kg": 0.4, "price": 18.99,
          "status": "cart"
        }
      ]
    }'
  ```

  ### Interactive API Docs

  Once running, open **http://localhost:8000/docs** for the Swagger UI.

  ---

  ## API Reference

  ### Customer Endpoints

  | Method | Endpoint | Description |
  |--------|----------|-------------|
  | `GET` | `/api/bbx/sizes` | List all active box sizes for the frontend dropdown |
  | `POST` | `/api/bbx/calculate` | Full packing calculation from an item list |
  | `POST` | `/api/bbx/optimize` | Repack all items for the best arrangement |
  | `POST` | `/api/bbx/validate` | Check if a saved arrangement is still current (hash comparison) |
  | `POST` | `/api/bbx/resize` | Change box size and repack all items |
  | `POST` | `/api/bbx/can-fit` | Pre-check whether a new item fits before adding to cart |
  | `POST` | `/api/bbx/save` | Validate arrangement SKUs before your backend saves to DB |

  ### Admin Endpoints

  | Method | Endpoint | Description |
  |--------|----------|-------------|
  | `GET` | `/api/admin/sizes` | List all sizes including inactive ones |
  | `POST` | `/api/admin/sizes` | Add a new box size |
  | `PUT` | `/api/admin/sizes/{id}` | Update an existing box size |
  | `DELETE` | `/api/admin/sizes/{id}` | Hard-delete a box size |
  | `PUT` | `/api/admin/sizes/{id}/toggle` | Activate or deactivate a box size |

  ### Utility

  | Method | Endpoint | Description |
  |--------|----------|-------------|
  | `GET` | `/api/health` | Health check with version and active size count |

  ---

  ## Architecture Overview

  ```
                                E-Commerce Frontend
                                        |
                                   HTTP / JSON
                                        |
                             +----------v-----------+
                             |    FastAPI (app.py)   |
                             |  Pydantic validation  |
                             +----------+-----------+
                                        |
                             +----------v-----------+
                             |   Packing Service     |
                             |  (orchestrator)       |
                             +---+------+------+----+
                                 |      |      |
                     +-----------+  +---+---+  +-----------+
                     |              |       |              |
                BBX Sizes     Greedy     Item         Domain
                 Store       Packer    Factory       Objects
              (dynamic)    (algo)   (factory)    (BBX, Shape,
                                                 PlacedItem)
  ```

  ### Layer Responsibilities

  | Layer | Module | Responsibility |
  |-------|--------|----------------|
  | **API** | `api/app.py` | HTTP endpoints, request validation, error mapping |
  | **Service** | `packing/packing_service.py` | Orchestration: calculate, optimize, validate, resize, can-fit |
  | **Algorithm** | `packing/greedy_packer.py` | Bottom-left-back placement with rotation and fold search |
  | **Domain** | `domain/` | BBX container (voxel grid), Item, PlacedItem, Shape hierarchy |
  | **Config** | `config.py` | Constants, enums (ShapeType, ItemCategory, PackingMode) |
  | **Sizes** | `bbx_sizes.py` | Dynamic box size management (in-memory, swap to DB in production) |

  ### How the Voxel Grid Works

  The box interior is discretized into a 3D grid of voxels (small cubes). At API resolution (0.5"/voxel), a 20x20x18" box becomes a 40x40x36 grid.

  When an item is placed, its shape is converted to an occupancy grid (3D boolean array), rotated through 6 orientations, and stamped into the box grid. Collision detection checks for overlap between the item's occupied voxels   
  and already-filled voxels.

  For fabric items, fold variants (halving width or depth, doubling height with a thickness penalty) are also generated and tested in all rotations.

  ---

  ## Configuration

  ### Resolution

  | Constant | Default | Description |
  |----------|---------|-------------|
  | `DEFAULT_RESOLUTION` | `0.25` | Inches per voxel (precision mode) |
  | `API_RESOLUTION` | `0.5` | Inches per voxel (API speed mode) |

  ### Shape Behavior

  | Constant | Default | Description |
  |----------|---------|-------------|
  | `DEFAULT_COMPRESSIBILITY` | `0.85` | Compression factor for soft/fabric items |
  | `MAX_FOLDS` | `3` | Maximum fold count for fabric items |
  | `FOLD_THICKNESS_PENALTY` | `1.05` | Height multiplier per fold |

  ### Default Box Sizes

  | ID | Name | Dimensions (W x D x H) | Price |
  |----|------|------------------------|-------|
  | `SMALL` | Small Box | 14" x 14" x 10" | $5.99 |
  | `MEDIUM` | Medium Box | 16" x 16" x 34" | $8.99 |
  | `LARGE` | Large Box | 20" x 20" x 18" | $11.99 |

  ### Item Shape Types

  | Shape Type | Use Case | Behavior |
  |------------|----------|----------|
  | `box` | Rigid products | Solid rectangular occupancy |
  | `cylinder` | Bottles, sprays, cans | Circular cross-section |
  | `soft` | Bags, pouches | Rectangular + compressibility |
  | `fabric` | Clothing, scarves | Foldable along width/depth axes |

  ---

  ## Development

  ### Running Tests

  ```bash
  pytest bbx_packer/tests/ -v
  ```

  ### Adding a New Shape Type

  1. Create a class in `domain/shapes.py` extending `Shape`
  2. Implement `volume()`, `bounding_box()`, and `occupancy_grid(resolution)`
  3. Add to `ShapeType` enum in `config.py`
  4. Add creation branch in `item_from_product_data()` in `domain/item.py`

  ### Swapping to a Real Database

  Replace the `BBXSizeStore` in `bbx_sizes.py` with database queries. The store interface stays the same -- no other changes needed.

  ---

  ## Integration Guide

  ### Typical E-Commerce Flow

  ```
  1. Customer opens BBX page
     -> GET /api/bbx/sizes (populate dropdown)
     -> POST /api/bbx/validate (check saved state)
        -> If valid: use cached arrangement
        -> If stale: POST /api/bbx/calculate (full rebuild)

  2. Customer browses products
     -> POST /api/bbx/can-fit (before "Add to Cart")
        -> If fits: allow add
        -> If not: show suggestion ("Try Medium Box")

  3. Customer changes box size
     -> POST /api/bbx/resize

  4. Customer clicks "Optimize"
     -> POST /api/bbx/optimize

  5. Checkout
     -> POST /api/bbx/save (validate before DB write)
  ```

  ---

  ## Tech Stack

  | Component | Version | Purpose |
  |-----------|---------|---------|
  | Python | 3.13+ | Runtime |
  | FastAPI | 0.129 | Web framework + auto-generated API docs |
  | Pydantic | 2.12 | Request/response validation |
  | NumPy | 2.4 | Voxel grid operations and shape geometry |
  | Uvicorn | 0.41 | ASGI server |

  ---