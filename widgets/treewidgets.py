"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/treewidgets.py

Description:
    This module contains the custom playlist tree widget used by the Review Player application.

The playlist tree widget is responsible for:
    - Displaying version/media items
    - Managing playlist item selection
    - Handling thumbnail/icon display
    - Supporting media browsing workflows
    - Creating custom playlist widget items

Main Components:
    PlaylistTreewidget:
        Custom QTreeWidget used for displaying playlist items.

Features:
    - Thumbnail-based playlist items
    - Single-selection support
    - Alternating row colors
    - Dynamic version population
    - Custom widget item integration

Widget Architecture:
    PlaylistTreewidget
        └── PlaylistWidgetItem
"""

from __future__ import absolute_import

from PySide6 import QtCore
from PySide6 import QtWidgets

from widgets.widgetItems import PlaylistWidgetItem


class PlaylistTreewidget(QtWidgets.QTreeWidget):
    """
    Custom playlist tree widget.

    This widget is used to display media/version items inside  the Review Player playlist interface.

    Features:
        - Thumbnail display
        - Single selection
        - Alternating row colors
        - Custom playlist items
        - Dynamic version population

    Example:
        >>> treewidget = PlaylistTreewidget(parent)
        >>> treewidget.setValues(versions)
    """

    files_dropped = QtCore.Signal(list)
    items_changed = QtCore.Signal(list)

    def __init__(self, parent, **kwargs):
        """
        Initialize playlist tree widget.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

            **kwargs:
                Optional keyword arguments.
        """

        super(PlaylistTreewidget, self).__init__(parent)

        # Thumbnail display size
        # Keep the source browser compact.  The larger editorial cards live in
        # Shot Playlist Timeline, so the left list only needs a quick visual ID.
        self.size = (112, 63)

        # Hide tree header
        self.setHeaderHidden(True)

        # Enable alternating row colors
        self.setAlternatingRowColors(True)

        # Ctrl+click selects two clips for RV-style A/B comparison.
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)

        # Stretch final column
        self.header().setStretchLastSection(True)

        # Set icon display size
        self.setIconSize(QtCore.QSize(*self.size))

        # External file drops add clips; internal drags reorder the playlist.
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
        self.setRootIsDecorated(False)

    def contexts(self):
        return [self.topLevelItem(index).context for index in range(self.topLevelItemCount())]

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
            if paths:
                self.files_dropped.emit(paths)
                event.acceptProposedAction()
                return

        super().dropEvent(event)
        QtCore.QTimer.singleShot(0, lambda: self.items_changed.emit(self.contexts()))

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Delete:
            for item in self.selectedItems():
                index = self.indexOfTopLevelItem(item)
                if index >= 0:
                    self.takeTopLevelItem(index)
            self.items_changed.emit(self.contexts())
            return
        super().keyPressEvent(event)

    def setValues(self, versions):
        """
        Populate playlist tree with version/media items.
        Existing items are cleared before inserting new playlist entries.

        Args:
            versions (list):
                List of version/media dictionaries.

        Example:
            >>> treewidget.setValues(versions)
        """

        # Clear existing items
        self.clear()

        # Create playlist items
        for version in versions:
            playlistWidgetItem = PlaylistWidgetItem(self, version, size=self.size)

            # Populate widget item UI
            playlistWidgetItem.setValue(context=None)


if __name__ == "__main__":
    pass
