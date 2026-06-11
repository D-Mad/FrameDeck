"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.
Author: Subin. Gopi (subing85@gmail.com).
Description: Review Player Qt QLayout wrapper module.
WARNING! All changes made in this file will be lost when recompiling source file!

This module provides reusable Qt layout wrapper classes used throughout the Review Player UI.

Responsibilities:
    - Simplify layout creation
    - Centralize spacing configuration
    - Centralize margin configuration
    - Provide layout utility helpers
    - Provide reusable spacer widgets
    - Provide splitter wrappers

Features:
    - Vertical layouts
    - Horizontal layouts
    - Layout clearing utilities
    - Child widget querying
    - Horizontal splitters
    - Spacer items
    - Margin customization
    - Spacing customization

Architecture:
    Widgets
        ↓
    Layout Wrappers
        ↓
    Qt Layout System
        ↓
    Window/UI Composition

Notes:
    This module is used by:
        - Main window layouts
        - Viewer layouts
        - Playlist layouts
        - Toolbar layouts
        - Settings dialogs
"""

from __future__ import absolute_import

from PySide6 import QtCore
from PySide6 import QtWidgets


class GridLayout(QtWidgets.QGridLayout):
    def __init__(self, parent, *args, **kwargs):
        super(GridLayout, self).__init__(parent)

        self.space = kwargs.get("space", [10, 10])
        self.margins = kwargs.get("margins", (10, 10, 10, 10))

        self.setHorizontalSpacing(self.space[0])
        self.setVerticalSpacing(self.space[1])
        self.setContentsMargins(*self.margins)

    def getChildren(self):

        stack = [self]
        children = list()

        while stack:
            layout = stack.pop()

            for index in range(layout.count()):
                item = layout.itemAt(index)

                if item.widget():
                    children.append(item.widget())

                if item.layout():
                    children.append(item.layout())
                    stack.append(item.layout())

        return children

    def clear(self):
        for child in self.getChildren():
            child.deleteLater()


class VerticalLayout(QtWidgets.QVBoxLayout):
    """Custom vertical layout wrapper.

    This layout provides centralized spacing and
    margin configuration for vertical widget layouts.

    Features:
        - Default spacing support
        - Default margins support
        - Child widget querying
        - Layout clearing utility

    Args:
        parent (QWidget):
            Parent widget.

    Keyword Args:
        space (int):
            Layout spacing.

        margins (tuple):
            Layout margins.

    Example:
        >>> layout = VerticalLayout(self, space=5, margins=(0, 0, 0, 0))
    """

    def __init__(self, parent, *args, **kwargs):
        """Initialize vertical layout.

        Args:
            parent (QWidget):
                Parent widget.

            *args:
                Reserved for future extension.

            **kwargs:
                Layout options.
        """

        # Initialize QVBoxLayout
        super(VerticalLayout, self).__init__(parent)

        # Layout Spacing
        self.space = kwargs.get("space", 10)

        # Layout Margins
        self.margins = kwargs.get("margins", (10, 10, 10, 10))

        # Apply Layout Settings
        self.setSpacing(self.space)
        self.setContentsMargins(*self.margins)


class HorizontalLayout(QtWidgets.QHBoxLayout):
    """Custom horizontal layout wrapper.

    This layout provides centralized spacing and margin configuration for horizontal widget layouts.

    Features:
        - Default spacing support
        - Default margins support
        - Child widget querying
        - Layout clearing utility

    Args:
        parent (QWidget):
            Parent widget.

    Keyword Args:
        space (int):
            Layout spacing.

        margins (tuple):
            Layout margins.

    Example:
        >>> layout = HorizontalLayout(self, space=5)
    """

    def __init__(self, parent, *args, **kwargs):
        """Initialize horizontal layout.

        Args:
            parent (QWidget):
                Parent widget.

            *args:
                Reserved for future extension.

            **kwargs:
                Layout options.
        """

        # Initialize QHBoxLayout
        super(HorizontalLayout, self).__init__(parent)

        # Layout Spacing
        self.space = kwargs.get("space", 10)

        # Layout Margins
        self.margins = kwargs.get("margins", (10, 10, 10, 10))

        # Apply Layout Settings
        self.setSpacing(self.space)
        self.setContentsMargins(*self.margins)


class HorizontalSplitter(QtWidgets.QSplitter):
    """Horizontal splitter widget.

    This wrapper provides a reusable horizontal Qt splitter used throughout the UI.

    Features:
        - Horizontal orientation
        - Resizable panels
        - Dynamic UI layouts

    Args:
        parent (QWidget):
            Parent widget.

    Example:
        >>> splitter = HorizontalSplitter(self)
    """

    def __init__(self, parent, **kwargs):
        """Initialize horizontal splitter.

        Args:
            parent (QWidget):
                Parent widget.

            **kwargs:
                Reserved for future extension.
        """

        # Initialize QSplitter
        super(HorizontalSplitter, self).__init__(parent)

        # Set Horizontal Orientation
        self.setOrientation(QtCore.Qt.Horizontal)


class HorizontalSpacer(QtWidgets.QSpacerItem):
    """Horizontal expanding spacer item.

    This spacer expands horizontally to push
    surrounding widgets apart.

    Features:
        - Horizontal expansion
        - Responsive layout spacing

    Example:
        >>> layout.addItem(HorizontalSpacer())
    """

    def __init__(self):
        """Initialize horizontal spacer."""

        # Initialize QSpacerItem
        super(HorizontalSpacer, self).__init__(
            40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )


class VerticalSpacer(QtWidgets.QSpacerItem):
    """Vertical expanding spacer item.

    This spacer expands vertically to push
    surrounding widgets apart.

    Features:
        - Vertical expansion
        - Responsive layout spacing

    Example:
        >>> layout.addItem(VerticalSpacer())
    """

    def __init__(self):
        """Initialize vertical spacer."""

        # Initialize QSpacerItem
        super(VerticalSpacer, self).__init__(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )


class HorizontalLineFrame(QtWidgets.QFrame):
    def __init__(self, parent, *args, **kwargs):
        super(HorizontalLineFrame, self).__init__(parent)
        self.setLineWidth(1)
        self.setMidLineWidth(0)
        self.setFrameShape(QtWidgets.QFrame.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)
        # self.setFrameShadow(QtWidgets.QFrame.Plain)


if __name__ == "__main__":
    pass
