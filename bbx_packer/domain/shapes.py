"""
Shape Definitions — Production Version
=======================================
BoxShape, CylinderShape, SoftShape, FabricShape (primary)
SphereShape, LShape (secondary, available)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np

from ..config import DEFAULT_COMPRESSIBILITY, MAX_FOLDS, FOLD_THICKNESS_PENALTY


class Shape(ABC):
    @abstractmethod
    def volume(self) -> float:
        pass

    @abstractmethod
    def bounding_box(self) -> tuple[float, float, float]:
        pass

    @abstractmethod
    def occupancy_grid(self, resolution: float) -> np.ndarray:
        pass

    @property
    def is_compressible(self) -> bool:
        return False

    @property
    def is_foldable(self) -> bool:
        return False

    def grid_dimensions(self, resolution: float) -> tuple[int, int, int]:
        w, d, h = self.bounding_box()
        return (
            max(1, int(np.ceil(w / resolution))),
            max(1, int(np.ceil(d / resolution))),
            max(1, int(np.ceil(h / resolution))),
        )


class BoxShape(Shape):
    def __init__(self, width: float, depth: float, height: float):
        if any(d <= 0 for d in (width, depth, height)):
            raise ValueError("All box dimensions must be positive.")
        self.width = width
        self.depth = depth
        self.height = height

    def volume(self) -> float:
        return self.width * self.depth * self.height

    def bounding_box(self) -> tuple[float, float, float]:
        return (self.width, self.depth, self.height)

    def occupancy_grid(self, resolution: float) -> np.ndarray:
        return np.ones(self.grid_dimensions(resolution), dtype=bool)


class CylinderShape(Shape):
    def __init__(self, radius: float, height: float):
        if radius <= 0 or height <= 0:
            raise ValueError("Radius and height must be positive.")
        self.radius = radius
        self.height = height

    def volume(self) -> float:
        return np.pi * self.radius ** 2 * self.height

    def bounding_box(self) -> tuple[float, float, float]:
        d = 2 * self.radius
        return (d, d, self.height)

    def occupancy_grid(self, resolution: float) -> np.ndarray:
        nx, ny, nz = self.grid_dimensions(resolution)
        cx, cy = (nx - 1) / 2.0, (ny - 1) / 2.0
        r_v = self.radius / resolution
        x, y = np.arange(nx), np.arange(ny)
        xx, yy = np.meshgrid(x, y, indexing='ij')
        mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= r_v ** 2
        grid = np.zeros((nx, ny, nz), dtype=bool)
        grid[:, :, :] = mask[:, :, np.newaxis]
        return grid


class SoftShape(Shape):
    def __init__(self, width: float, depth: float, height: float,
                 compressibility: float = DEFAULT_COMPRESSIBILITY):
        if any(d <= 0 for d in (width, depth, height)):
            raise ValueError("All dimensions must be positive.")
        self.width = width
        self.depth = depth
        self.height = height
        self.compressibility = compressibility

    def volume(self) -> float:
        return self.width * self.depth * self.height

    def bounding_box(self) -> tuple[float, float, float]:
        return (self.width, self.depth, self.height)

    def occupancy_grid(self, resolution: float) -> np.ndarray:
        return np.ones(self.grid_dimensions(resolution), dtype=bool)

    @property
    def is_compressible(self) -> bool:
        return True


@dataclass
class FoldVariant:
    width: float
    depth: float
    height: float
    num_folds: int
    fold_description: str

    @property
    def volume(self) -> float:
        return self.width * self.depth * self.height

    @property
    def bounding_box(self) -> tuple[float, float, float]:
        return (self.width, self.depth, self.height)


class FabricShape(Shape):
    def __init__(self, width: float, depth: float, height: float,
                 compressibility: float = DEFAULT_COMPRESSIBILITY,
                 max_folds: int = MAX_FOLDS):
        if any(d <= 0 for d in (width, depth, height)):
            raise ValueError("All dimensions must be positive.")
        self.width = width
        self.depth = depth
        self.height = height
        self.compressibility = compressibility
        self.max_folds = max_folds
        self._fold_variants = self._generate_fold_variants()

    def volume(self) -> float:
        return self.width * self.depth * self.height

    def bounding_box(self) -> tuple[float, float, float]:
        return (self.width, self.depth, self.height)

    def occupancy_grid(self, resolution: float) -> np.ndarray:
        return np.ones(self.grid_dimensions(resolution), dtype=bool)

    def occupancy_grid_for_variant(self, variant: FoldVariant, resolution: float) -> np.ndarray:
        nx = max(1, int(np.ceil(variant.width / resolution)))
        ny = max(1, int(np.ceil(variant.depth / resolution)))
        nz = max(1, int(np.ceil(variant.height / resolution)))
        return np.ones((nx, ny, nz), dtype=bool)

    @property
    def is_compressible(self) -> bool:
        return True

    @property
    def is_foldable(self) -> bool:
        return True

    @property
    def fold_variants(self) -> list[FoldVariant]:
        return self._fold_variants

    def _generate_fold_variants(self) -> list[FoldVariant]:
        variants = [FoldVariant(self.width, self.depth, self.height, 0, "original")]
        queue = [(self.width, self.depth, self.height, 0, [])]
        seen = {(self.width, self.depth, self.height)}

        while queue:
            w, d, h, nf, parts = queue.pop(0)
            if nf >= self.max_folds:
                continue

            for axis, nw, nd, nh in [
                ("width", w / 2, d, h * 2 * FOLD_THICKNESS_PENALTY),
                ("depth", w, d / 2, h * 2 * FOLD_THICKNESS_PENALTY),
            ]:
                key = (round(nw, 4), round(nd, 4), round(nh, 4))
                if key not in seen and nw >= 0.5 and nd >= 0.5:
                    seen.add(key)
                    new_parts = parts + [axis]
                    desc = "folded " + " + ".join(new_parts)
                    variants.append(FoldVariant(nw, nd, nh, nf + 1, desc))
                    queue.append((nw, nd, nh, nf + 1, new_parts))

        return variants


# Secondary shapes — available but not primary
class SphereShape(Shape):
    def __init__(self, radius: float):
        if radius <= 0:
            raise ValueError("Radius must be positive.")
        self.radius = radius

    def volume(self) -> float:
        return (4 / 3) * np.pi * self.radius ** 3

    def bounding_box(self) -> tuple[float, float, float]:
        d = 2 * self.radius
        return (d, d, d)

    def occupancy_grid(self, resolution: float) -> np.ndarray:
        nx, ny, nz = self.grid_dimensions(resolution)
        cx, cy, cz = (nx - 1) / 2.0, (ny - 1) / 2.0, (nz - 1) / 2.0
        r_v = self.radius / resolution
        x, y, z = np.arange(nx), np.arange(ny), np.arange(nz)
        xx, yy, zz = np.meshgrid(x, y, z, indexing='ij')
        return (xx - cx) ** 2 + (yy - cy) ** 2 + (zz - cz) ** 2 <= r_v ** 2


class LShape(Shape):
    def __init__(self, total_width: float, total_height: float, depth: float,
                 vertical_width: float, base_height: float):
        self.total_width = total_width
        self.total_height = total_height
        self.depth = depth
        self.vertical_width = vertical_width
        self.base_height = base_height

    def volume(self) -> float:
        return (self.total_width * self.depth * self.base_height +
                self.vertical_width * self.depth * (self.total_height - self.base_height))

    def bounding_box(self) -> tuple[float, float, float]:
        return (self.total_width, self.depth, self.total_height)

    def occupancy_grid(self, resolution: float) -> np.ndarray:
        nx, ny, nz = self.grid_dimensions(resolution)
        grid = np.zeros((nx, ny, nz), dtype=bool)
        bz = int(np.ceil(self.base_height / resolution))
        vx = int(np.ceil(self.vertical_width / resolution))
        grid[:, :, :bz] = True
        grid[:vx, :, bz:] = True
        return grid
