"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/widgetItems.py

Description:
    This module contains custom QTreeWidgetItem classes used by the playlist system.

Responsibilities:
    - Store playlist/version context
    - Display formatted playlist information
    - Generate thumbnail icons
    - Support URL and local image previews

Features:
    - Custom playlist item rendering
    - Thumbnail scaling
    - URL image support
    - Local image support
    - Fallback placeholder thumbnails
    - Context-based metadata display

Architecture:
    Playlist Data
        ↓
    PlaylistWidgetItem
        ↓
    Thumbnail/Icon Generation
        ↓
    QTreeWidget Display

Notes:
    This module is primarily used by:
        - Playlist tree widgets
        - Version browsers
        - Media selection UIs
"""

from __future__ import absolute_import

from PySide6 import QtCore
from PySide6 import QtWidgets

from widgets.pixmaps import PathPixmap
from widgets.pixmaps import NamePixmap
from widgets.pixmaps import PixmapIcon


class PlaylistWidgetItem(QtWidgets.QTreeWidgetItem):
    """Custom playlist tree widget item.

    This item stores media/version context data and
    provides thumbnail + metadata visualization for
    playlist UIs.

    Features:
        - Context storage
        - Thumbnail preview
        - URL image loading
        - Local image loading
        - Fallback placeholder support
        - Formatted metadata display

    Args:
        parent (QTreeWidget):
            Parent tree widget.

        *args:
            Context dictionary.

        **kwargs:
            Optional settings.

    Keyword Args:
        size (tuple):
            Thumbnail size.
            Default:
                (128, 72)

    Example:
        >>> item = PlaylistWidgetItem(tree_widget, version_data)
    """

    def __init__(self, parent, *args, **kwargs):
        """Initialize playlist widget item.

        Args:
            parent (QTreeWidget):
                Parent tree widget.

            *args:
                Playlist/version context.

            **kwargs:
                Additional options.
        """

        # Initialize Base QTreeWidgetItem
        super(PlaylistWidgetItem, self).__init__(parent)

        # Store Context Data
        self.context = args[0]

        # Thumbnail Size
        self.size = kwargs.get("size", (128, 72))

        # Configure Item Flags
        self.setFlags(
            QtCore.Qt.ItemIsSelectable
            | QtCore.Qt.ItemIsDragEnabled
            | QtCore.Qt.ItemIsEnabled
        )

    def getContext(self):
        """Return stored context data.

        Returns:
            dict:
                Playlist/version context.

        Example:
            >>> context = item.getContext()
        """

        # Return Context
        return self.context

    def setValue(self, context=None):
        """Update displayed item information.

        This method updates:
            - Display text
            - Thumbnail/icon
            - Internal context

        Args:
            context (dict | None):
                Optional replacement context.

        Example:
            >>> item.setValue(version_data)
        """

        # Store Context
        self.context = context or self.context

        if self.context.get("type") == "LocalMedia":
            duration = float(self.context.get("duration") or 0.0)
            minutes, seconds = divmod(int(round(duration)), 60)
            values = [
                f"#{self.context.get('playlist_index', 1):02d}  {self.context['code']}",
                f"{self.context.get('fps', 0):g} FPS  •  {self.context.get('frame_count', 0)} frames",
                f"{minutes:02d}:{seconds:02d}  •  {self.context.get('resolution', 'Unknown size')}",
            ]
            if self.context.get("media_kind") == "sequence":
                values.append(f"Color: {self.context.get('colorspace', 'Auto')}")
            else:
                values.append(
                    f"{self.context.get('container_format', 'Video')}  •  "
                    f"{self.context.get('codec', 'Unknown codec')}"
                )
            if self.context.get("metadata_error"):
                values.append("Metadata probe failed — click to retry")
            elif self.context.get("network_source"):
                status = self.context.get("cache_status", "Waiting")
                progress = int(self.context.get("cache_progress") or 0)
                if status == "Caching":
                    status = f"{status} {progress}%"
                values.append(f"Server cache: {status}")
            tooltip = self.context.get("media", "")
            if self.context.get("metadata_error"):
                tooltip += f"\n\nProbe error: {self.context['metadata_error']}"
            self.setToolTip(0, tooltip)
        else:
            # Build production/version display text.
            values = [
                f"\nVersion: {self.context['code']} | {self.context['id']}",
                f"Task: {self.context['sg_task']['name']}",
                f"Entity: {self.context['entity']['name']}",
                f"Status: {self.context['sg_status_list']}",
                f"created: {self.context['created_at']}",
                f"created By: {self.context['created_by']['name']}\n",
            ]

        # Set Item Text
        self.setText(0, "\n".join(values))

        # Update Thumbnail Icon
        self.setIndexIcon(self.context.get("image"), index=0)

    def setIndexIcon(self, filepath, index=0):
        """Set item thumbnail icon.

        Supports:
            - HTTP/HTTPS URLs
            - Local image paths
            - Placeholder thumbnails

        Args:
            filepath (str):
                Image path or URL.

            index (int):
                Tree column index.

        Example:
            >>> item.setIndexIcon("/tmp/image.png")
            >>> item.setIndexIcon("https://server/image.jpg")
        """

        # Build Pixmap
        if filepath:
            # From URL Image or Local Image
            pixmap = PathPixmap(filepath)
        else:
            # Fallback Placeholder
            pixmap = NamePixmap("unknown")

        if not pixmap.isNull():
            # Scale Thumbnail
            pixmap = pixmap.scaled(
                *self.size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
            )

        # Create Qt Icon
        icon = PixmapIcon(pixmap)

        # Set Tree Item Icon
        self.setIcon(index, icon)


if __name__ == "__main__":
    pass
