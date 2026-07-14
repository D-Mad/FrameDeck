"""Cache controls for videos and image sequences."""

from __future__ import absolute_import

import os

from PySide6 import QtCore, QtGui, QtWidgets


class CacheManagerDialog(QtWidgets.QDialog):
    cache_cleared = QtCore.Signal()

    def __init__(self, media_cache, parent=None):
        super().__init__(parent)
        self.media_cache = media_cache
        self.setWindowTitle("FrameDeck Cache Manager")
        self.resize(620, 310)

        layout = QtWidgets.QVBoxLayout(self)
        note = QtWidgets.QLabel(
            "Cache server video or complete EXR/PNG/JPG sequences for faster review. "
            "Color-aware 2K EXR display proxies are also generated automatically here. "
            "Select multiple shots in Sources before choosing Cache Selected Shots."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        form = QtWidgets.QFormLayout()
        self.locationEdit = QtWidgets.QLineEdit(self.media_cache.root)
        self.locationEdit.setReadOnly(True)
        form.addRow("Cache location", self.locationEdit)
        self.usageLabel = QtWidgets.QLabel()
        form.addRow("Current usage", self.usageLabel)
        self.limitSpin = QtWidgets.QDoubleSpinBox(self)
        self.limitSpin.setRange(1.0, 500.0)
        self.limitSpin.setDecimals(1)
        self.limitSpin.setSuffix(" GB")
        self.limitSpin.setValue(self.media_cache.max_bytes / 1024**3)
        form.addRow("Maximum cache", self.limitSpin)
        self.workLabel = QtWidgets.QLabel()
        form.addRow("Active copies", self.workLabel)
        layout.addLayout(form)

        buttons = QtWidgets.QHBoxLayout()
        self.openButton = QtWidgets.QPushButton("Open Cache Folder")
        self.clearButton = QtWidgets.QPushButton("Clear All Cache")
        self.closeButton = QtWidgets.QPushButton("Close")
        buttons.addWidget(self.openButton)
        buttons.addWidget(self.clearButton)
        buttons.addStretch(1)
        buttons.addWidget(self.closeButton)
        layout.addLayout(buttons)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(750)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.limitSpin.valueChanged.connect(self._set_limit)
        self.openButton.clicked.connect(self.open_folder)
        self.clearButton.clicked.connect(self.clear_cache)
        self.closeButton.clicked.connect(self.close)
        self.refresh()

    def _set_limit(self, value):
        self.media_cache.max_bytes = max(1, int(float(value) * 1024**3))
        settings = QtCore.QSettings("FrameDeck", "FrameDeck")
        settings.setValue("cache/max_gb", float(value))

    def refresh(self):
        size = self.media_cache.size_bytes()
        self.usageLabel.setText(
            f"{size / 1024**3:.2f} GB  |  {self.media_cache.file_count()} files"
        )
        active = "  |  in use" if self.media_cache.active_path else ""
        self.workLabel.setText(f"{len(self.media_cache.workers)}{active}")
        self.clearButton.setEnabled(
            not self.media_cache.workers and not self.media_cache.active_path and size > 0
        )

    def open_folder(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(self.media_cache.root))

    def clear_cache(self):
        answer = QtWidgets.QMessageBox.question(
            self,
            "Clear FrameDeck Cache",
            "Delete all cached video and image-sequence frames?\nSource media is not affected.",
        )
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        if not self.media_cache.clear():
            QtWidgets.QMessageBox.information(
                self,
                "Cache Busy",
                "Wait for active copies to finish or open a non-cached source first.",
            )
        else:
            self.cache_cleared.emit()
        self.refresh()
