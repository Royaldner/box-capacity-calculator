"""Greedy Packer — Bottom-Left-Back with rotation and fold support."""

import numpy as np
from ..domain.bbx import BBX
from ..domain.item import Item
from ..domain.placed_item import PlacedItem, Rotation
from ..domain.shapes import FabricShape


class GreedyPacker:

    def find_position(self, bbx: BBX, item: Item) -> PlacedItem | None:
        configs = self._get_configs(item, bbx.resolution)
        best = None
        best_score = (float('inf'), float('inf'), float('inf'))
        best_occ = None
        best_fold = "original"
        best_rot = Rotation.WDH
        best_dims = (0, 0, 0)

        for occ_base, fold_desc, base_dims in configs:
            for rotation in Rotation:
                occ = BBX._rotate_grid(occ_base, rotation)
                ix, iy, iz = occ.shape
                if ix > bbx.nx or iy > bbx.ny or iz > bbx.nz:
                    continue

                pos = self._scan(bbx, occ, ix, iy, iz)
                if pos:
                    score = (pos[2], pos[0], pos[1])
                    if score < best_score:
                        best_score = score
                        best_occ = occ
                        best_fold = fold_desc
                        best_rot = rotation
                        best_dims = base_dims
                        best = pos

                    if score[0] == 0:
                        break
            if best and best_score[0] == 0:
                break

        if best is not None:
            return bbx.place_item(
                item, best, best_rot, best_fold,
                occupancy=best_occ, placed_dims=best_dims,
            )
        return None

    def pack_all(self, bbx: BBX, items: list[Item]) -> tuple[list[PlacedItem], list[Item]]:
        # Sort: paid first, then by volume descending
        sorted_items = sorted(items, key=lambda i: (
            0 if i.status == "paid" else 1,
            -i.volume,
        ))

        bbx.clear()
        placed, failed = [], []

        for item in sorted_items:
            result = self.find_position(bbx, item)
            if result:
                placed.append(result)
            else:
                failed.append(item)

        return placed, failed

    def _get_configs(self, item, resolution):
        configs = []
        shape = item.shape
        bb = shape.bounding_box()
        configs.append((shape.occupancy_grid(resolution), "original", bb))

        if item.is_foldable and isinstance(shape, FabricShape):
            for v in shape.fold_variants:
                if v.fold_description == "original":
                    continue
                occ = shape.occupancy_grid_for_variant(v, resolution)
                configs.append((occ, v.fold_description, v.bounding_box))

        return configs

    def _scan(self, bbx, occ, ix, iy, iz):
        for z in range(bbx.nz - iz + 1):
            for x in range(bbx.nx - ix + 1):
                for y in range(bbx.ny - iy + 1):
                    if bbx.can_place_at(occ, (x, y, z)):
                        return (x, y, z)
        return None
