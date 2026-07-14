"""Horizontal editorial shot strip for local playlists."""

from __future__ import absolute_import

import os

from PySide6 import QtCore, QtGui, QtWidgets

from widgets.pixmaps import NamePixmap, NamePixmapIcon, PathPixmap


class ShotListWidget(QtWidgets.QListWidget):
    order_changed = QtCore.Signal(list)
    shot_requested = QtCore.Signal(bool, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_source_row = -1
        self.setFlow(QtWidgets.QListView.Flow.LeftToRight)
        self.setWrapping(False)
        self.setViewMode(QtWidgets.QListView.ViewMode.IconMode)
        self.setMovement(QtWidgets.QListView.Movement.Snap)
        self.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)
        self.setIconSize(QtCore.QSize(142, 80))
        self.setGridSize(QtCore.QSize(174, 112))
        self.setSpacing(2)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
        self.setDragDropOverwriteMode(False)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.itemClicked.connect(lambda item: self.shot_requested.emit(False, item.data(QtCore.Qt.ItemDataRole.UserRole)))
        self.itemDoubleClicked.connect(lambda item: self.shot_requested.emit(True, item.data(QtCore.Qt.ItemDataRole.UserRole)))
        self.setToolTip("Drag a shot left or right to change playlist order")

    def contexts(self):
        return [
            self.item(index).data(QtCore.Qt.ItemDataRole.UserRole)
            for index in range(self.count())
        ]

    def startDrag(self, supported_actions):
        """Remember the source row for the lifetime of Qt's nested drag loop."""
        self._drag_source_row = self.currentRow()
        try:
            super().startDrag(supported_actions)
        finally:
            self._drag_source_row = -1

    def dropEvent(self, event):
        # Resolve the horizontal slot explicitly, but do not remove/reinsert a
        # QListWidgetItem while Qt's drag loop still owns it.  Rebuilding the
        # synchronised source/timeline models inside that loop made Qt remove
        # the stale drag item a second time, which looked like a disappearing
        # shot.  Return IgnoreAction to suppress Qt's own model mutation, then
        # commit the context order on the next event-loop turn.
        if event.source() is self:
            source_row = (
                self._drag_source_row
                if self._drag_source_row >= 0
                else self.currentRow()
            )
            point = event.position().toPoint()
            target_item = self.itemAt(point)
            if target_item is None:
                target_row = self.count()
            else:
                target_row = self.row(target_item)
                if point.x() > self.visualItemRect(target_item).center().x():
                    target_row += 1

            if target_row > source_row:
                target_row -= 1
            target_row = max(0, min(target_row, self.count() - 1))

            if source_row >= 0 and target_row != source_row:
                contexts = self.contexts()
                moved = contexts.pop(source_row)
                contexts.insert(target_row, moved)
                QtCore.QTimer.singleShot(
                    0,
                    lambda ordered=contexts: self.order_changed.emit(ordered),
                )

            event.setDropAction(QtCore.Qt.DropAction.IgnoreAction)
            event.accept()
            return

        super().dropEvent(event)


class ShotSequenceWidget(QtWidgets.QFrame):
    order_changed = QtCore.Signal(list)
    shot_requested = QtCore.Signal(bool, dict)
    play_playlist_requested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_path = None
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setMinimumHeight(145)
        self.setMaximumHeight(145)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 5)
        layout.setSpacing(3)

        header = QtWidgets.QHBoxLayout()
        self.trackLabel = QtWidgets.QLabel("V1  SHOT PLAYLIST")
        self.trackLabel.setStyleSheet("font-weight: 700; color: #d7d7d7;")
        header.addWidget(self.trackLabel)
        header.addStretch(1)
        self.playAllButton = QtWidgets.QPushButton("Play Playlist")
        self.playAllButton.setIcon(NamePixmapIcon("play"))
        self.playAllButton.setToolTip("Play all shots on one continuous global timeline")
        self.playAllButton.setEnabled(False)
        header.addWidget(self.playAllButton)
        self.removeButton = QtWidgets.QPushButton("Remove Shot")
        self.removeButton.setIcon(NamePixmapIcon("remove"))
        self.removeButton.setToolTip("Remove selected occurrence from playlist (Delete)")
        self.removeButton.setEnabled(False)
        header.addWidget(self.removeButton)
        self.clearButton = QtWidgets.QPushButton("Clear Playlist")
        self.clearButton.setEnabled(False)
        header.addWidget(self.clearButton)
        self.earlierButton = QtWidgets.QPushButton(" Earlier")
        self.earlierButton.setIcon(NamePixmapIcon("backward"))
        self.earlierButton.setToolTip("Move selected shot earlier (Alt+Left)")
        self.earlierButton.setEnabled(False)
        header.addWidget(self.earlierButton)
        self.laterButton = QtWidgets.QPushButton("Later ")
        self.laterButton.setIcon(NamePixmapIcon("forward"))
        self.laterButton.setToolTip("Move selected shot later (Alt+Right)")
        self.laterButton.setEnabled(False)
        header.addWidget(self.laterButton)
        self.summaryLabel = QtWidgets.QLabel("0 shots  |  drag shots left/right to reorder")
        self.summaryLabel.setStyleSheet("color: #999;")
        header.addWidget(self.summaryLabel)
        layout.addLayout(header)

        self.shotList = ShotListWidget(self)
        self.shotList.setStyleSheet(
            "QListWidget { background: #202224; border: 1px solid #444; }"
            "QListWidget::item { background: #176078; border: 1px solid #111; color: white; }"
            "QListWidget::item:selected { background: #6b6d1d; border: 2px solid #ffbe28; }"
        )
        layout.addWidget(self.shotList)

        self.shotList.order_changed.connect(self._handle_reorder)
        self.shotList.shot_requested.connect(self.shot_requested)
        self.shotList.currentRowChanged.connect(self._update_reorder_buttons)
        self.earlierButton.clicked.connect(lambda: self.move_selected(-1))
        self.laterButton.clicked.connect(lambda: self.move_selected(1))
        self.playAllButton.clicked.connect(self.play_playlist_requested)
        self.removeButton.clicked.connect(self.remove_selected)
        self.clearButton.clicked.connect(self.clear_playlist)

        self.earlierShortcut = QtGui.QShortcut(QtGui.QKeySequence("Alt+Left"), self)
        self.earlierShortcut.activated.connect(lambda: self.move_selected(-1))
        self.laterShortcut = QtGui.QShortcut(QtGui.QKeySequence("Alt+Right"), self)
        self.laterShortcut.activated.connect(lambda: self.move_selected(1))
        self.deleteShortcut = QtGui.QShortcut(QtGui.QKeySequence("Delete"), self)
        self.deleteShortcut.activated.connect(self.remove_selected)

    def _update_reorder_buttons(self, row):
        self.earlierButton.setEnabled(row > 0)
        self.laterButton.setEnabled(0 <= row < self.shotList.count() - 1)
        self.removeButton.setEnabled(0 <= row < self.shotList.count())

    def remove_selected(self):
        row = self.shotList.currentRow()
        if row < 0:
            return
        self.shotList.takeItem(row)
        if self.shotList.count():
            self.shotList.setCurrentRow(min(row, self.shotList.count() - 1))
        self._handle_reorder(self.shotList.contexts())

    def clear_playlist(self):
        if not self.shotList.count():
            return
        self.shotList.clear()
        self._handle_reorder([])

    def _renumber_items(self):
        for index in range(self.shotList.count()):
            item = self.shotList.item(index)
            context = item.data(QtCore.Qt.ItemDataRole.UserRole) or {}
            duration = int(round(float(context.get("duration") or 0.0)))
            minutes, seconds = divmod(duration, 60)
            item.setText(
                f"{index + 1:02d}  {context.get('code', 'Shot')}\n"
                f"{minutes:02d}:{seconds:02d}"
            )

    def _handle_reorder(self, contexts):
        self._renumber_items()
        self._update_reorder_buttons(self.shotList.currentRow())
        self.order_changed.emit(contexts)

    def move_selected(self, offset):
        """Move the selected shot one slot and sync the playlist order."""
        row = self.shotList.currentRow()
        target = row + int(offset)
        if row < 0 or target < 0 or target >= self.shotList.count():
            return
        item = self.shotList.takeItem(row)
        self.shotList.insertItem(target, item)
        self.shotList.setCurrentItem(item)
        self.shotList.scrollToItem(item)
        self._handle_reorder(self.shotList.contexts())

    def set_contexts(self, contexts):
        self.shotList.blockSignals(True)
        self.shotList.clear()
        total_duration = 0.0
        for index, context in enumerate(contexts, start=1):
            duration = float(context.get("duration") or 0.0)
            total_duration += duration
            seconds = int(round(duration))
            minutes, seconds = divmod(seconds, 60)
            text = f"{index:02d}  {context.get('code', 'Shot')}\n{minutes:02d}:{seconds:02d}"
            item = QtWidgets.QListWidgetItem(text)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, context)
            item.setSizeHint(QtCore.QSize(170, 108))
            thumbnail = context.get("image")
            pixmap = PathPixmap(thumbnail) if thumbnail else NamePixmap("unknown")
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    142,
                    80,
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation,
                )
                item.setIcon(QtGui.QIcon(pixmap))
            item.setToolTip(context.get("media", ""))
            self.shotList.addItem(item)
        self.shotList.blockSignals(False)

        minutes, seconds = divmod(int(round(total_duration)), 60)
        self.summaryLabel.setText(
            f"{len(contexts)} shots  |  {minutes:02d}:{seconds:02d}  |  drag shots left/right"
        )
        self.playAllButton.setEnabled(bool(contexts))
        self.clearButton.setEnabled(bool(contexts))
        self._update_reorder_buttons(self.shotList.currentRow())
        if self.active_path:
            self.set_active_media(self.active_path)

    def set_active_media(self, path):
        if not path:
            return
        self.active_path = path
        normalized = os.path.normcase(os.path.abspath(path))
        for index in range(self.shotList.count()):
            item = self.shotList.item(index)
            context = item.data(QtCore.Qt.ItemDataRole.UserRole) or {}
            media = context.get("media")
            if media and os.path.normcase(os.path.abspath(media)) == normalized:
                self.shotList.setCurrentItem(item)
                self.shotList.scrollToItem(item)
                return
