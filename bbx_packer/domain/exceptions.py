"""Domain Exceptions"""


class BBXPackerError(Exception):
    pass


class ItemTooLargeError(BBXPackerError):
    def __init__(self, item_name: str, item_dims: tuple, bbx_dims: tuple):
        self.item_name = item_name
        self.item_dims = item_dims
        self.bbx_dims = bbx_dims
        super().__init__(
            f'Item "{item_name}" {item_dims} cannot fit in BBX {bbx_dims} in any orientation.'
        )


class ItemTooLargeForAnyBBXError(BBXPackerError):
    def __init__(self, item_name: str, item_dims: tuple):
        self.item_name = item_name
        super().__init__(f'Item "{item_name}" {item_dims} does not fit in any available BBX.')


class BBXFullError(BBXPackerError):
    def __init__(self, item_name: str, fill_pct: float):
        self.item_name = item_name
        self.fill_pct = fill_pct
        super().__init__(f'Cannot place "{item_name}". BBX is {fill_pct:.1f}% full.')


class BBXSizeNotFoundError(BBXPackerError):
    def __init__(self, size_id: str):
        self.size_id = size_id
        super().__init__(f'BBX size "{size_id}" not found.')
