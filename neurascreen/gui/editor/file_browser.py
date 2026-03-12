"""File browser sidebar for scenario files."""

import logging
from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QHBoxLayout, QFileDialog,
)

logger = logging.getLogger("neurascreen.gui")


class FileBrowser(QWidget):
    """Tree view of scenario JSON files with open-on-double-click."""

    file_selected = Signal(str)  # absolute path

    def __init__(self, parent=None):
        super().__init__(parent)
        self._roots: list[Path] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        layout.addSpacing(8)
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(4, 0, 4, 4)
        btn_layout.setSpacing(4)

        btn_add = QPushButton("+ Folder")
        btn_add.setToolTip("Add a scenarios folder")
        btn_add.clicked.connect(self._on_add_folder)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setToolTip("Refresh file tree")
        btn_refresh.clicked.connect(self.refresh)

        btn_layout.addWidget(btn_add, 1)
        btn_layout.addWidget(btn_refresh, 1)
        layout.addLayout(btn_layout)

        # Tree
        self._tree = QTreeWidget()
        self._tree.setHeaderLabel("Scenarios")
        self._tree.setRootIsDecorated(True)
        self._tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._tree)

    def set_roots(self, paths: list[Path]) -> None:
        """Set the root directories to display."""
        self._roots = [p for p in paths if p.exists()]
        self.refresh()

    def add_root(self, path: Path) -> None:
        """Add a root directory."""
        if path.exists() and path not in self._roots:
            self._roots.append(path)
            self.refresh()

    def refresh(self) -> None:
        """Rebuild the tree from root directories."""
        self._tree.clear()

        for root in self._roots:
            root_item = QTreeWidgetItem(self._tree, [root.name])
            root_item.setData(0, Qt.ItemDataRole.UserRole, str(root))
            root_item.setExpanded(True)
            self._populate_tree(root_item, root)

        if not self._roots:
            placeholder = QTreeWidgetItem(self._tree, ["No folders added"])
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)

    def _populate_tree(self, parent_item: QTreeWidgetItem, directory: Path) -> None:
        """Recursively add JSON files and subdirectories."""
        try:
            entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return

        for entry in entries:
            if entry.name.startswith("."):
                continue

            if entry.is_dir():
                dir_item = QTreeWidgetItem(parent_item, [entry.name])
                dir_item.setData(0, Qt.ItemDataRole.UserRole, str(entry))
                self._populate_tree(dir_item, entry)
                # Remove empty directories
                if dir_item.childCount() == 0:
                    parent_item.removeChild(dir_item)

            elif entry.suffix == ".json":
                file_item = QTreeWidgetItem(parent_item, [entry.name])
                file_item.setData(0, Qt.ItemDataRole.UserRole, str(entry))
                file_item.setToolTip(0, str(entry))

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle double-click: emit file_selected for JSON files."""
        path_str = item.data(0, Qt.ItemDataRole.UserRole)
        if path_str:
            path = Path(path_str)
            if path.is_file() and path.suffix == ".json":
                self.file_selected.emit(str(path))

    def _on_add_folder(self) -> None:
        """Open a dialog to add a folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Scenarios Folder")
        if folder:
            self.add_root(Path(folder))
