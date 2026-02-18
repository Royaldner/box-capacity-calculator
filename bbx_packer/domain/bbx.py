"""BBX Container — accepts dynamic dimensions from BBXSizeConfig."""

import numpy as np
from ..domain.placed_item import PlacedItem, Rotation
from ..domain.item import Item
from ..domain.exceptions import BBXFullError


class BBX:
    def __init__(self, width: float, depth: float, height: float,
                 resolution: float, size_id: str = "CUSTOM"):
        self.size_id = size_id
        self.resolution = resolution
        self.width = width
        self.depth = depth
        self.height = height

        self.nx = int(np.ceil(width / resolution))
        self.ny = int(np.ceil(depth / resolution))
        self.nz = int(np.ceil(height / resolution))

        self.grid = np.zeros((self.nx, self.ny, self.nz), dtype=np.uint8)
        self.placed_items: list[PlacedItem] = []
        self._next_id = 1

    @property
    def total_voxels(self) -> int:
        return self.grid.size

    @property
    def occupied_voxels(self) -> int:
        return int(np.count_nonzero(self.grid))

    @property
    def fill_percentage(self) -> float:
        if self.total_voxels == 0:
            return 0.0
        return (self.occupied_voxels / self.total_voxels) * 100.0

    @property
    def total_volume(self) -> float:
        return self.width * self.depth * self.height

    @property
    def occupied_volume(self) -> float:
        return self.occupied_voxels * self.resolution ** 3

    @property
    def remaining_percentage(self) -> float:
        return 100.0 - self.fill_percentage

    def _get_next_id(self) -> int:
        nid = self._next_id
        self._next_id += 1
        return nid

    def can_place_at(self, occupancy: np.ndarray, position: tuple[int, int, int]) -> bool:
        px, py, pz = position
        ix, iy, iz = occupancy.shape
        if px + ix > self.nx or py + iy > self.ny or pz + iz > self.nz:
            return False
        if px < 0 or py < 0 or pz < 0:
            return False
        region = self.grid[px:px + ix, py:py + iy, pz:pz + iz]
        return not np.logical_and(region > 0, occupancy).any()

    def place_item(self, item: Item, position: tuple[int, int, int],
                   rotation: Rotation = Rotation.WDH,
                   fold_description: str = "original",
                   occupancy: np.ndarray = None,
                   placed_dims: tuple[float, float, float] = (0, 0, 0)) -> PlacedItem:

        if occupancy is None:
            occupancy = item.shape.occupancy_grid(self.resolution)
            occupancy = self._rotate_grid(occupancy, rotation)

        if not self.can_place_at(occupancy, position):
            raise BBXFullError(item.name, self.fill_percentage)

        item_id = self._get_next_id()
        px, py, pz = position
        ix, iy, iz = occupancy.shape

        # Stamp with item ID
        voxels_used = 0
        for x in range(ix):
            for y in range(iy):
                for z in range(iz):
                    if occupancy[x, y, z]:
                        self.grid[px + x, py + y, pz + z] = item_id
                        voxels_used += 1

        placed = PlacedItem(
            item=item, position=position, rotation=rotation,
            fold_description=fold_description,
            placed_dims=placed_dims, voxels_used=voxels_used,
        )
        self.placed_items.append(placed)
        return placed

    def clear(self):
        self.grid.fill(0)
        self.placed_items.clear()
        self._next_id = 1

    @staticmethod
    def _rotate_grid(grid: np.ndarray, rotation: Rotation) -> np.ndarray:
        axis_map = {
            Rotation.WDH: (0, 1, 2), Rotation.WHD: (0, 2, 1),
            Rotation.DWH: (1, 0, 2), Rotation.DHW: (1, 2, 0),
            Rotation.HWD: (2, 0, 1), Rotation.HDW: (2, 1, 0),
        }
        return np.transpose(grid, axis_map[rotation])
