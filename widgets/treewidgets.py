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
        self.size = (200, 112)

        # Hide tree header
        self.setHeaderHidden(True)

        # Enable alternating row colors
        self.setAlternatingRowColors(True)

        # Allow single item selection only
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        # Stretch final column
        self.header().setStretchLastSection(True)

        # Set icon display size
        self.setIconSize(QtCore.QSize(*self.size))

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
