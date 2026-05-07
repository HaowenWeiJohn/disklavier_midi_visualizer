"""Main window for the Disklavier MIDI visualizer."""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QShortcut,
    QVBoxLayout,
    QWidget,
)

from disklavier_visualizer.io.midi_adapter import MidiAdapter, MidiParseError
from disklavier_visualizer.ui.midi_canvas import MidiPanelWidget
from disklavier_visualizer.ui.timeline_slider import TimelineSliderWidget

DEFAULT_TITLE = "Disklavier MIDI Visualizer"
HELP_HINT = "Drag canvas to scrub  |  Scroll to zoom  |  Arrows to step  |  Double-click a note to seek"


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(DEFAULT_TITLE)
        self.resize(1200, 700)

        self._panel = MidiPanelWidget()
        self._slider = TimelineSliderWidget()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._panel, stretch=1)
        layout.addWidget(self._slider)
        self.setCentralWidget(central)

        self._build_menu()
        self._build_shortcuts()

        # Two-way bind. Both setters internally suppress signal echo, so a
        # single user action settles in one event-loop tick.
        self._panel.position_changed.connect(self._slider.set_position)
        self._slider.position_changed.connect(self._panel.set_position)

        self.statusBar().showMessage(HELP_HINT)

    def _build_menu(self):
        menu = self.menuBar().addMenu("&File")

        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self._on_open_file)
        menu.addAction(open_action)

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

    def _on_open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open MIDI", "", "MIDI Files (*.mid *.MID);;All Files (*)"
        )
        if not path:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            adapter = MidiAdapter(path)
        except MidiParseError as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "Could not open MIDI", str(e))
            return
        QApplication.restoreOverrideCursor()

        # Order matters: set the slider's duration first so the canvas's
        # auto-seek emit lands inside the new range. Then set position to
        # match the canvas's chosen first-note start.
        self._slider.set_duration(adapter.duration)
        self._panel.load_midi(adapter)
        self._slider.set_position(self._panel.current_time)

        self.setWindowTitle(f"{adapter.filename} — {DEFAULT_TITLE}")
        self.statusBar().showMessage(
            f"Loaded {adapter.filename}  |  {len(adapter.notes)} notes  |  "
            f"{adapter.duration:.2f}s   —   {HELP_HINT}"
        )
