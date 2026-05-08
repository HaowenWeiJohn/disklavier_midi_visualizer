"""Anchor table widget — list of timestamped labels for the current MIDI.

Adapted from midi_camera_alignment_tool's AnchorTableWidget, trimmed to a
self-contained widget (no AlignmentService indirection, no camera/probe
columns, no active-anchor toggle). The widget owns its own list[Anchor]
and emits signals on user-driven mutations.
"""
from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QShortcut,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from disklavier_visualizer.io.anchor_io import Anchor


NUM_COL = 0
TIME_COL = 1
LABEL_COL = 2
NUM_COLS = 3


class AnchorTableWidget(QWidget):
    """Table of (timestamp, label) anchors for the loaded MIDI file."""

    # Double-click on the time cell jumps the playhead.
    jump_requested = pyqtSignal(float)
    # Emitted on add / delete / label edit so the host can react (e.g. mark dirty).
    anchors_changed = pyqtSignal()
    # Emitted when the user clicks the Add button — the host knows the
    # current playhead time and calls add_anchor_at() in response.
    add_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._anchors: list[Anchor] = []
        # Suppress itemChanged round-trips while we repopulate cells in _refresh.
        self._populating = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("Anchors"))
        header_row.addStretch()

        self._add_btn = QPushButton("Add Anchor")
        self._add_btn.setToolTip("Add an anchor at the current playhead time (A)")
        self._add_btn.setEnabled(False)
        self._add_btn.clicked.connect(self.add_requested)
        header_row.addWidget(self._add_btn)

        self._delete_btn = QPushButton("Delete Selected")
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._on_delete)
        header_row.addWidget(self._delete_btn)

        layout.addLayout(header_row)

        self._table = QTableWidget(0, NUM_COLS)
        self._table.setHorizontalHeaderLabels(["#", "Time (s)", "Label"])
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(NUM_COL, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(TIME_COL, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(LABEL_COL, QHeaderView.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        # Editing is restricted to the Label column via per-item flags in
        # _refresh; the table-wide triggers stay enabled so double-click /
        # edit-key still open the editor on that column.
        self._table.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed
        )
        self._table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self._table.itemChanged.connect(self._on_item_changed)
        self._table.itemSelectionChanged.connect(self._update_delete_enabled)
        layout.addWidget(self._table)

        # Delete-key shortcut scoped to the table.
        del_shortcut = QShortcut(QKeySequence(Qt.Key_Delete), self._table)
        del_shortcut.setContext(Qt.WidgetShortcut)
        del_shortcut.activated.connect(self._on_delete)

    # ---- public API ----

    def set_enabled_for_midi(self, enabled: bool) -> None:
        """Enable/disable the Add button. Called by the main window when a MIDI loads/unloads."""
        self._add_btn.setEnabled(enabled)

    def add_anchor_at(self, timestamp_seconds: float) -> None:
        """Insert an anchor at the given time (used by the A shortcut and Add button).

        Sorts the resulting list by timestamp, selects the new row, and starts
        editing its label cell so the user can type immediately.
        """
        new_anchor = Anchor(timestamp_seconds=float(timestamp_seconds), label="")
        self._anchors.append(new_anchor)
        self._anchors.sort(key=lambda a: a.timestamp_seconds)
        new_row = self._anchors.index(new_anchor)
        self._refresh()
        self._table.selectRow(new_row)
        label_item = self._table.item(new_row, LABEL_COL)
        if label_item is not None:
            self._table.editItem(label_item)
        self.anchors_changed.emit()

    def set_anchors(self, anchors: list[Anchor]) -> None:
        """Replace the entire anchor list (used on JSON load)."""
        self._anchors = sorted(
            (Anchor(timestamp_seconds=a.timestamp_seconds, label=a.label) for a in anchors),
            key=lambda a: a.timestamp_seconds,
        )
        self._refresh()
        self.anchors_changed.emit()

    def get_anchors(self) -> list[Anchor]:
        """Return a sorted copy of the current anchor list."""
        return [
            Anchor(timestamp_seconds=a.timestamp_seconds, label=a.label)
            for a in sorted(self._anchors, key=lambda a: a.timestamp_seconds)
        ]

    def clear(self) -> None:
        """Remove all anchors."""
        if not self._anchors:
            self._refresh()
            return
        self._anchors = []
        self._refresh()
        self.anchors_changed.emit()

    # ---- internals ----

    def _refresh(self) -> None:
        self._populating = True
        try:
            self._table.setRowCount(0)
            for i, anchor in enumerate(self._anchors):
                self._table.insertRow(i)

                num_item = QTableWidgetItem(str(i + 1))
                num_item.setFlags(num_item.flags() & ~Qt.ItemIsEditable)
                num_item.setTextAlignment(Qt.AlignCenter)
                self._table.setItem(i, NUM_COL, num_item)

                time_item = QTableWidgetItem(f"{anchor.timestamp_seconds:.3f}")
                time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable)
                time_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                time_item.setToolTip("Double-click to jump the playhead here")
                self._table.setItem(i, TIME_COL, time_item)

                label_item = QTableWidgetItem(anchor.label)
                label_item.setFlags(label_item.flags() | Qt.ItemIsEditable)
                label_item.setToolTip("Double-click to edit")
                self._table.setItem(i, LABEL_COL, label_item)
        finally:
            self._populating = False
        self._update_delete_enabled()

    def _update_delete_enabled(self) -> None:
        self._delete_btn.setEnabled(bool(self._table.selectionModel().selectedRows()))

    def _on_cell_double_clicked(self, row: int, col: int) -> None:
        if col != TIME_COL:
            return
        if not (0 <= row < len(self._anchors)):
            return
        self.jump_requested.emit(self._anchors[row].timestamp_seconds)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._populating:
            return
        if item.column() != LABEL_COL:
            return
        row = item.row()
        if not (0 <= row < len(self._anchors)):
            return
        new_label = item.text()
        if new_label == self._anchors[row].label:
            return
        self._anchors[row].label = new_label
        self.anchors_changed.emit()

    def _on_delete(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return
        idx = rows[0].row()
        if not (0 <= idx < len(self._anchors)):
            return
        del self._anchors[idx]
        self._refresh()
        self.anchors_changed.emit()
