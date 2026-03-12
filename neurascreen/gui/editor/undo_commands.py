"""QUndoCommand subclasses for scenario editing operations."""

from PySide6.QtGui import QUndoCommand


class AddStepCommand(QUndoCommand):
    """Add a step at a given index."""

    def __init__(self, steps: list[dict], index: int, step_data: dict, description: str = "Add step"):
        super().__init__(description)
        self._steps = steps
        self._index = index
        self._data = step_data

    def redo(self) -> None:
        self._steps.insert(self._index, self._data.copy())

    def undo(self) -> None:
        self._steps.pop(self._index)


class DeleteStepCommand(QUndoCommand):
    """Delete a step at a given index."""

    def __init__(self, steps: list[dict], index: int, description: str = "Delete step"):
        super().__init__(description)
        self._steps = steps
        self._index = index
        self._data = steps[index].copy()

    def redo(self) -> None:
        self._steps.pop(self._index)

    def undo(self) -> None:
        self._steps.insert(self._index, self._data.copy())


class EditStepCommand(QUndoCommand):
    """Edit a step's data."""

    def __init__(self, steps: list[dict], index: int, new_data: dict, description: str = "Edit step"):
        super().__init__(description)
        self._steps = steps
        self._index = index
        self._old_data = steps[index].copy()
        self._new_data = new_data.copy()

    def redo(self) -> None:
        self._steps[self._index] = self._new_data.copy()

    def undo(self) -> None:
        self._steps[self._index] = self._old_data.copy()


class MoveStepCommand(QUndoCommand):
    """Move a step from one index to another."""

    def __init__(self, steps: list[dict], from_index: int, to_index: int, description: str = "Move step"):
        super().__init__(description)
        self._steps = steps
        self._from = from_index
        self._to = to_index

    def redo(self) -> None:
        item = self._steps.pop(self._from)
        self._steps.insert(self._to, item)

    def undo(self) -> None:
        item = self._steps.pop(self._to)
        self._steps.insert(self._from, item)


class EditMetadataCommand(QUndoCommand):
    """Edit scenario metadata (title, description, resolution)."""

    def __init__(self, metadata: dict, key: str, old_value, new_value, description: str = ""):
        super().__init__(description or f"Edit {key}")
        self._metadata = metadata
        self._key = key
        self._old = old_value
        self._new = new_value

    def redo(self) -> None:
        self._metadata[self._key] = self._new

    def undo(self) -> None:
        self._metadata[self._key] = self._old


class BulkDeleteCommand(QUndoCommand):
    """Delete multiple steps at given indices."""

    def __init__(self, steps: list[dict], indices: list[int], description: str = "Delete steps"):
        super().__init__(description)
        self._steps = steps
        # Store in reverse order for correct removal
        self._items = [(i, steps[i].copy()) for i in sorted(indices, reverse=True)]

    def redo(self) -> None:
        for idx, _ in self._items:
            self._steps.pop(idx)

    def undo(self) -> None:
        for idx, data in reversed(self._items):
            self._steps.insert(idx, data.copy())
