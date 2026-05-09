"""Main window for the Disklavier MIDI visualizer."""
from __future__ import annotations

import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCloseEvent, QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QShortcut,
    QVBoxLayout,
    QWidget,
)

from disklavier_visualizer.io.anchor_io import (
    Anchor,
    AnchorFile,
    AnchorParseError,
    load_anchors,
    save_anchors,
)
from disklavier_visualizer.io.midi_adapter import MidiAdapter, MidiParseError
from disklavier_visualizer.ui.anchor_table import AnchorTableWidget
from disklavier_visualizer.ui.midi_canvas import MidiPanelWidget
from disklavier_visualizer.ui.timeline_slider import TimelineSliderWidget

DEFAULT_TITLE = "Disklavier MIDI Visualizer"
HELP_HINT = (
    "Drag canvas to scrub  |  Scroll to zoom  |  Arrows to step  |  "
    "Double-click a note to seek  |  A to add anchor"
)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(1400, 700)

        self._panel = MidiPanelWidget()
        self._slider = TimelineSliderWidget()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._panel, stretch=1)
        layout.addWidget(self._slider)
        self.setCentralWidget(central)

        self._anchor_table = AnchorTableWidget()
        self._anchor_dock = QDockWidget("Anchors", self)
        self._anchor_dock.setObjectName("anchorsDock")
        self._anchor_dock.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        )
        self._anchor_dock.setWidget(self._anchor_table)
        self.addDockWidget(Qt.RightDockWidgetArea, self._anchor_dock)

        self._current_midi_path: str | None = None
        # Tracks unsaved anchor edits since the last save / load. The flag
        # is flipped True by user-driven mutations (anchors_changed signal)
        # and reset False after a successful save or any fresh load.
        self._dirty: bool = False

        self._save_action: QAction | None = None
        self._build_menu()
        self._build_shortcuts()

        # Two-way bind. Both setters internally suppress signal echo, so a
        # single user action settles in one event-loop tick.
        self._panel.position_changed.connect(self._slider.set_position)
        self._slider.position_changed.connect(self._panel.set_position)

        # Anchor wiring.
        self._anchor_table.jump_requested.connect(self._panel.set_position)
        self._anchor_table.add_requested.connect(self._on_add_anchor)
        self._anchor_table.anchors_changed.connect(self._on_anchors_changed)

        self._update_title()
        self.statusBar().showMessage(HELP_HINT)

    def _build_menu(self):
        menu = self.menuBar().addMenu("&File")

        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self._on_open_file)
        menu.addAction(open_action)

        save_action = QAction("&Save Anchors...", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self._on_save_anchors)
        save_action.setEnabled(False)
        menu.addAction(save_action)
        self._save_action = save_action

        menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        menu.addAction(quit_action)

    def _build_shortcuts(self):
        def shortcut(seq, slot):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.WindowShortcut)
            sc.activated.connect(slot)
            return sc

        shortcut("Left", lambda: self._panel.step_ticks(-1))
        shortcut("Right", lambda: self._panel.step_ticks(1))
        shortcut("Shift+Left", lambda: self._panel.step_ticks(-100))
        shortcut("Shift+Right", lambda: self._panel.step_ticks(100))
        shortcut("A", self._on_add_anchor)

    # ---- dirty-state tracking ----

    def _on_anchors_changed(self) -> None:
        """User-driven anchor mutation — mark dirty, refresh title.

        Called for add/delete/label-edit. Loads use this same signal but
        explicitly reset the flag afterwards via _mark_clean().
        """
        self._dirty = True
        self._update_title()

    def _mark_clean(self) -> None:
        self._dirty = False
        self._update_title()

    def _update_title(self) -> None:
        adapter = self._panel.canvas.adapter
        if adapter is None:
            self.setWindowTitle(DEFAULT_TITLE)
            return
        marker = "*" if self._dirty else ""
        self.setWindowTitle(f"{adapter.filename}{marker} — {DEFAULT_TITLE}")

    def _maybe_confirm_discard(self) -> bool:
        """Return True if the caller may proceed; False if the user cancelled.

        Prompts the user with Save / Discard / Cancel when there are unsaved
        anchor edits. If the user picks Save and the save itself fails or the
        user cancels the save dialog, treat that as cancel — keep the user
        in the app rather than losing their anchors.
        """
        if not self._dirty:
            return True
        reply = QMessageBox.question(
            self,
            "Unsaved anchor changes",
            "You have unsaved anchor changes. Save before continuing?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if reply == QMessageBox.Cancel:
            return False
        if reply == QMessageBox.Save:
            return self._on_save_anchors()
        return True  # Discard

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._maybe_confirm_discard():
            event.accept()
        else:
            event.ignore()

    # ---- file open / dispatch ----

    def _on_open_file(self):
        if not self._maybe_confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open MIDI or Anchors",
            "",
            "MIDI or Anchors (*.mid *.MID *.json);;"
            "MIDI Files (*.mid *.MID);;"
            "Anchor Files (*.json);;"
            "All Files (*)",
        )
        if not path:
            return
        if path.lower().endswith(".json"):
            self._open_anchors(path)
        else:
            self._open_midi(path)

    def _open_midi(self, path: str) -> MidiAdapter | None:
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            adapter = MidiAdapter(path)
        except MidiParseError as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "Could not open MIDI", str(e))
            return None
        QApplication.restoreOverrideCursor()

        # Order matters: set the slider's duration first so the canvas's
        # auto-seek emit lands inside the new range. Then set position to
        # match the canvas's chosen first-note start.
        self._slider.set_duration(adapter.duration)
        self._panel.load_midi(adapter)
        self._slider.set_position(self._panel.current_time)

        self._current_midi_path = path
        # clear() may emit anchors_changed (flipping _dirty true), so the
        # _mark_clean() below MUST run after to settle the flag.
        self._anchor_table.clear()
        self._anchor_table.set_enabled_for_midi(True)
        if self._save_action is not None:
            self._save_action.setEnabled(True)

        self._mark_clean()
        self.statusBar().showMessage(
            f"Loaded {adapter.filename}  |  {len(adapter.notes)} notes  |  "
            f"{adapter.duration:.2f}s   —   {HELP_HINT}"
        )
        return adapter

    def _open_anchors(self, json_path: str) -> None:
        try:
            anchor_file = load_anchors(json_path)
        except AnchorParseError as e:
            QMessageBox.warning(self, "Could not open anchor file", str(e))
            return

        midi_path = anchor_file.midi_path
        if not os.path.isfile(midi_path):
            QMessageBox.warning(
                self,
                "MIDI file not found",
                f"The anchor file references:\n\n{midi_path}\n\n"
                f"That file no longer exists. Please locate the MIDI file.",
            )
            start_dir = os.path.dirname(json_path) or ""
            picked, _ = QFileDialog.getOpenFileName(
                self,
                "Locate MIDI file",
                start_dir,
                "MIDI Files (*.mid *.MID);;All Files (*)",
            )
            if not picked:
                return
            midi_path = picked

        adapter = self._open_midi(midi_path)
        if adapter is None:
            return

        if abs(adapter.duration - anchor_file.midi_duration_seconds) > 0.01:
            QMessageBox.warning(
                self,
                "MIDI duration mismatch",
                f"The loaded MIDI's duration ({adapter.duration:.3f}s) differs "
                f"from the value saved with the anchors "
                f"({anchor_file.midi_duration_seconds:.3f}s).\n\n"
                f"This may not be the same file the anchors were created for.",
            )

        # Clamp anchor timestamps into the loaded MIDI's range; in practice
        # they always will be, but guards against editing the JSON by hand.
        clamped: list[Anchor] = []
        clipped = 0
        for a in anchor_file.anchors:
            t = a.timestamp_seconds
            if t < 0 or t > adapter.duration:
                clipped += 1
                t = max(0.0, min(t, adapter.duration))
            clamped.append(Anchor(timestamp_seconds=t, label=a.label))
        # set_anchors() emits anchors_changed which flips _dirty true;
        # _mark_clean() below resets it because the in-memory anchors now
        # match the JSON we just loaded.
        self._anchor_table.set_anchors(clamped)
        self._mark_clean()

        msg = (
            f"Loaded {adapter.filename}  +  {len(clamped)} anchors from "
            f"{os.path.basename(json_path)}"
        )
        if clipped:
            msg += f"  ({clipped} timestamp(s) clamped to file range)"
        self.statusBar().showMessage(msg + "   —   " + HELP_HINT)

    # ---- anchor add / save ----

    def _on_add_anchor(self) -> None:
        if self._panel.canvas.adapter is None:
            return
        self._anchor_table.add_anchor_at(self._panel.current_time)

    def _on_save_anchors(self) -> bool:
        """Save the current anchors. Returns True on success, False on cancel/failure.

        The boolean lets _maybe_confirm_discard treat "user cancelled the
        save dialog" or "write failed" as a cancellation of the original
        action that prompted the save (open / close), rather than silently
        losing the anchors.
        """
        adapter = self._panel.canvas.adapter
        if adapter is None or self._current_midi_path is None:
            return False
        default_dir = os.path.dirname(self._current_midi_path) or ""
        default_stem = os.path.splitext(adapter.filename)[0]
        default_name = f"{default_stem}.anchors.json"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Anchors",
            os.path.join(default_dir, default_name),
            "Anchor Files (*.json);;All Files (*)",
        )
        if not path:
            return False
        anchor_file = AnchorFile(
            midi_path=os.path.abspath(self._current_midi_path),
            midi_duration_seconds=adapter.duration,
            anchors=self._anchor_table.get_anchors(),
        )
        try:
            save_anchors(anchor_file, path)
        except OSError as e:
            QMessageBox.warning(self, "Could not save anchors", str(e))
            return False
        self._mark_clean()
        self.statusBar().showMessage(
            f"Saved {len(anchor_file.anchors)} anchors to {os.path.basename(path)}"
        )
        return True
