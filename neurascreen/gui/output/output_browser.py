"""Output browser — list generated videos with SRT/chapters viewers."""

import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QFileSystemWatcher
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QPushButton, QLineEdit,
    QLabel, QTextEdit, QMenu, QMessageBox,
    QApplication, QTabWidget, QFrame, QSlider, QStyle,
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

from .viewers import (
    OutputFileInfo, list_output_files, compute_output_stats,
    parse_srt, parse_chapters,
    format_srt_display, format_chapters_display,
)

logger = logging.getLogger("neurascreen.gui")

COL_NAME = 0
COL_SIZE = 1
COL_DATE = 2
COL_SRT = 3
COL_CHAPTERS = 4
NUM_COLS = 5


class OutputBrowser(QWidget):
    """Browse generated video files with metadata viewers."""

    def __init__(self, output_dir: str | Path | None = None, parent=None):
        super().__init__(parent)
        self._output_dir = Path(output_dir) if output_dir else self._default_output_dir()
        self._files: list[OutputFileInfo] = []
        self._watcher: QFileSystemWatcher | None = None

        self._setup_ui()
        self.refresh()
        self._setup_watcher()

    @staticmethod
    def _default_output_dir() -> Path:
        return Path(__file__).parent.parent.parent.parent / "output"

    # ------------------------------------------------------------------ #
    #  UI                                                                 #
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Top bar: search + stats + buttons
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter by name...")
        self._search.textChanged.connect(self._on_filter_changed)
        top_bar.addWidget(self._search)

        self._stats_label = QLabel("")
        self._stats_label.setProperty("muted", True)
        top_bar.addWidget(self._stats_label)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh)
        top_bar.addWidget(btn_refresh)

        btn_open_folder = QPushButton("Open Folder")
        btn_open_folder.clicked.connect(self._on_open_folder)
        top_bar.addWidget(btn_open_folder)

        layout.addLayout(top_bar)

        # Splitter: table + viewers
        splitter = QSplitter(Qt.Orientation.Vertical)

        # File table
        self._table = QTableWidget(0, NUM_COLS)
        self._table.setHorizontalHeaderLabels(["Name", "Size", "Date", "SRT", "Ch."])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSortingEnabled(True)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)
        self._table.currentCellChanged.connect(self._on_selection_changed)
        self._table.doubleClicked.connect(self._on_double_click)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_SIZE, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(COL_SIZE, 80)
        header.setSectionResizeMode(COL_DATE, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(COL_DATE, 140)
        header.setSectionResizeMode(COL_SRT, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(COL_SRT, 40)
        header.setSectionResizeMode(COL_CHAPTERS, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(COL_CHAPTERS, 40)

        splitter.addWidget(self._table)

        # Viewer tabs
        self._viewer_tabs = QTabWidget()

        self._srt_view = QTextEdit()
        self._srt_view.setReadOnly(True)
        self._srt_view.setProperty("monospace", True)
        self._srt_view.setPlaceholderText("Select a file with SRT to view subtitles")
        self._viewer_tabs.addTab(self._srt_view, "Subtitles (SRT)")

        self._chapters_view = QTextEdit()
        self._chapters_view.setReadOnly(True)
        self._chapters_view.setProperty("monospace", True)
        self._chapters_view.setPlaceholderText("Select a file with chapters to view")
        self._viewer_tabs.addTab(self._chapters_view, "Chapters")

        self._youtube_view = QTextEdit()
        self._youtube_view.setReadOnly(True)
        self._youtube_view.setProperty("monospace", True)
        self._youtube_view.setPlaceholderText("Select a file with YouTube metadata to view")
        self._viewer_tabs.addTab(self._youtube_view, "YouTube")

        # Video preview tab
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(4)

        self._video_widget = QVideoWidget()
        self._video_widget.setMinimumHeight(200)
        preview_layout.addWidget(self._video_widget, 1)

        self._audio_output = QAudioOutput()
        self._audio_output.setVolume(0.8)

        self._media_player = QMediaPlayer()
        self._media_player.setAudioOutput(self._audio_output)
        self._media_player.setVideoOutput(self._video_widget)
        self._media_player.positionChanged.connect(self._on_position_changed)
        self._media_player.durationChanged.connect(self._on_duration_changed)
        self._media_player.playbackStateChanged.connect(self._on_playback_state_changed)

        # Controls bar
        controls_bar = QHBoxLayout()
        controls_bar.setSpacing(6)
        controls_bar.setContentsMargins(8, 0, 8, 4)

        self._btn_play = QPushButton("\u25B6")
        self._btn_play.setFixedWidth(40)
        self._btn_play.clicked.connect(self._on_play_pause)
        self._btn_play.setEnabled(False)
        controls_bar.addWidget(self._btn_play)

        self._btn_stop = QPushButton("\u25A0")
        self._btn_stop.setFixedWidth(40)
        self._btn_stop.clicked.connect(self._on_stop)
        self._btn_stop.setEnabled(False)
        controls_bar.addWidget(self._btn_stop)

        self._position_slider = QSlider(Qt.Orientation.Horizontal)
        self._position_slider.setRange(0, 0)
        self._position_slider.sliderMoved.connect(self._on_seek)
        controls_bar.addWidget(self._position_slider, 1)

        self._time_label = QLabel("00:00 / 00:00")
        self._time_label.setProperty("muted", True)
        self._time_label.setFixedWidth(100)
        controls_bar.addWidget(self._time_label)

        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(80)
        self._volume_slider.setFixedWidth(80)
        self._volume_slider.valueChanged.connect(self._on_volume_changed)
        controls_bar.addWidget(self._volume_slider)

        preview_layout.addLayout(controls_bar)

        self._viewer_tabs.insertTab(0, preview_widget, "Preview")

        splitter.addWidget(self._viewer_tabs)
        splitter.setSizes([250, 300])

        layout.addWidget(splitter, 1)

    # ------------------------------------------------------------------ #
    #  Data                                                               #
    # ------------------------------------------------------------------ #

    def refresh(self) -> None:
        """Reload the file listing from disk."""
        self._files = list_output_files(self._output_dir)
        self._apply_filter()
        self._update_stats()

    def _apply_filter(self) -> None:
        """Filter and populate the table."""
        query = self._search.text().strip().lower()
        filtered = [f for f in self._files if query in f.name.lower()] if query else self._files

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(filtered))

        for i, info in enumerate(filtered):
            # Name
            name_item = QTableWidgetItem(info.name)
            name_item.setData(Qt.ItemDataRole.UserRole, str(info.path))
            self._table.setItem(i, COL_NAME, name_item)

            # Size
            size_item = QTableWidgetItem(info.size_human)
            size_item.setData(Qt.ItemDataRole.UserRole + 1, info.size_bytes)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(i, COL_SIZE, size_item)

            # Date
            dt = datetime.fromtimestamp(info.modified)
            date_item = QTableWidgetItem(dt.strftime("%Y-%m-%d %H:%M"))
            date_item.setData(Qt.ItemDataRole.UserRole + 1, info.modified)
            self._table.setItem(i, COL_DATE, date_item)

            # SRT
            srt_item = QTableWidgetItem("\u2713" if info.has_srt else "")
            srt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, COL_SRT, srt_item)

            # Chapters
            ch_item = QTableWidgetItem("\u2713" if info.has_chapters else "")
            ch_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, COL_CHAPTERS, ch_item)

        self._table.setSortingEnabled(True)

    def _update_stats(self) -> None:
        stats = compute_output_stats(self._files)
        self._stats_label.setText(
            f"{stats['count']} video(s) — {stats['total_size_human']}"
        )

    def _setup_watcher(self) -> None:
        """Watch the output directory for changes."""
        if self._output_dir.exists():
            self._watcher = QFileSystemWatcher([str(self._output_dir)])
            self._watcher.directoryChanged.connect(self.refresh)

    # ------------------------------------------------------------------ #
    #  Selection & viewers                                                #
    # ------------------------------------------------------------------ #

    def _selected_file(self) -> OutputFileInfo | None:
        """Get the currently selected file info."""
        row = self._table.currentRow()
        if row < 0:
            return None
        name_item = self._table.item(row, COL_NAME)
        if not name_item:
            return None
        path = Path(name_item.data(Qt.ItemDataRole.UserRole))
        for f in self._files:
            if str(f.path) == str(path):
                return f
        return None

    def _on_selection_changed(self, row: int, *_args) -> None:
        if row < 0:
            return
        info = self._selected_file()
        if not info:
            return

        # Video preview
        self._media_player.stop()
        self._media_player.setSource(QUrl.fromLocalFile(str(info.path)))
        self._btn_play.setEnabled(True)
        self._btn_stop.setEnabled(True)
        self._viewer_tabs.setCurrentIndex(0)  # Switch to Preview tab

        # SRT viewer
        if info.has_srt:
            try:
                content = info.srt_path.read_text(encoding="utf-8")
                entries = parse_srt(content)
                self._srt_view.setPlainText(format_srt_display(entries))
            except OSError:
                self._srt_view.setPlainText("(failed to read SRT file)")
        else:
            self._srt_view.setPlainText("")

        # Chapters viewer
        if info.has_chapters:
            try:
                content = info.chapters_path.read_text(encoding="utf-8")
                chapters = parse_chapters(content)
                self._chapters_view.setPlainText(format_chapters_display(chapters))
            except OSError:
                self._chapters_view.setPlainText("(failed to read chapters file)")
        else:
            self._chapters_view.setPlainText("")

        # YouTube viewer
        if info.has_youtube:
            try:
                content = info.youtube_path.read_text(encoding="utf-8")
                self._youtube_view.setPlainText(content)
            except OSError:
                self._youtube_view.setPlainText("(failed to read YouTube file)")
        else:
            self._youtube_view.setPlainText("")

    def _on_filter_changed(self, _text: str) -> None:
        self._apply_filter()

    # ------------------------------------------------------------------ #
    #  Video player                                                       #
    # ------------------------------------------------------------------ #

    def _on_play_pause(self) -> None:
        if self._media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._media_player.pause()
        else:
            self._media_player.play()

    def _on_stop(self) -> None:
        self._media_player.stop()

    def _on_seek(self, position: int) -> None:
        self._media_player.setPosition(position)

    def _on_volume_changed(self, value: int) -> None:
        self._audio_output.setVolume(value / 100.0)

    def _on_position_changed(self, position: int) -> None:
        self._position_slider.setValue(position)
        self._update_time_label(position, self._media_player.duration())

    def _on_duration_changed(self, duration: int) -> None:
        self._position_slider.setRange(0, duration)
        self._update_time_label(self._media_player.position(), duration)

    def _on_playback_state_changed(self, state) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._btn_play.setText("\u23F8")  # Pause symbol
        else:
            self._btn_play.setText("\u25B6")  # Play symbol

    def _update_time_label(self, pos_ms: int, dur_ms: int) -> None:
        pos = self._format_time(pos_ms)
        dur = self._format_time(dur_ms)
        self._time_label.setText(f"{pos} / {dur}")

    @staticmethod
    def _format_time(ms: int) -> str:
        s = ms // 1000
        m = s // 60
        s = s % 60
        return f"{m:02d}:{s:02d}"

    # ------------------------------------------------------------------ #
    #  Actions                                                            #
    # ------------------------------------------------------------------ #

    def _on_double_click(self, _index) -> None:
        info = self._selected_file()
        if info:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(info.path)))

    def _on_open_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._output_dir)))

    def _on_copy_path(self) -> None:
        info = self._selected_file()
        if info:
            QApplication.clipboard().setText(str(info.path))

    def _on_delete(self) -> None:
        info = self._selected_file()
        if not info:
            return

        result = QMessageBox.question(
            self, "Delete Video",
            f"Delete {info.name} and associated files (SRT, chapters)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        try:
            info.path.unlink(missing_ok=True)
            if info.has_srt:
                info.srt_path.unlink(missing_ok=True)
            if info.has_chapters:
                info.chapters_path.unlink(missing_ok=True)
            if info.has_youtube:
                info.youtube_path.unlink(missing_ok=True)
            self.refresh()
        except OSError as e:
            QMessageBox.critical(self, "Delete Error", f"Failed to delete: {e}")

    def _on_context_menu(self, pos) -> None:
        info = self._selected_file()
        menu = QMenu(self)

        if info:
            menu.addAction("Open in player", self._on_double_click)
            menu.addAction("Copy path", self._on_copy_path)
            menu.addSeparator()
            act_del = menu.addAction("Delete")
            act_del.triggered.connect(self._on_delete)

        menu.addSeparator()
        menu.addAction("Open output folder", self._on_open_folder)
        menu.addAction("Refresh", self.refresh)

        menu.exec(self._table.viewport().mapToGlobal(pos))
