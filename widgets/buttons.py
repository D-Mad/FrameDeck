"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/buttons.py

Description:
    This module provides reusable Qt button widgets used throughout the Review Player application.

Responsibilities:
    - Standardize button appearance
    - Simplify icon button creation
    - Provide playback control buttons
    - Provide tool/menu button wrappers
    - Centralize icon handling

Features:
    - Icon-based push buttons
    - Playback controls
    - Loop toggle buttons
    - Display menu buttons
    - Tooltip support
    - Fixed-size buttons
    - Reusable button architecture

Architecture:
    Button Wrapper
        ↓
    Resource Icon
        ↓
    Qt Button Widget
        ↓
    UI Interaction

Notes:
    This module is used by:
        - Playback toolbar
        - Viewer controls
        - Timeline controls
        - Watermark menus
        - Utility toolbars
"""

from __future__ import absolute_import

from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtWidgets

from widgets.menus import DisplayMenus
from widgets.dialogs import ColorDialog
from widgets.pixmaps import NamePixmapIcon


class IconButton(QtWidgets.QPushButton):
    """Base icon push button widget.

    This class provides a reusable icon-based QPushButton wrapper used throughout the UI.

    Features:
        - Resource icon loading
        - Tooltip support
        - Fixed-size configuration
        - Flat button styling
        - Icon scaling

    Class Attributes:
        name (str):
            Resource icon name.

    Args:
        parent (QWidget):
            Parent widget.

    Keyword Args:
        width (int):
            Icon/button width.

        height (int):
            Icon/button height.

        tooltip (str):
            Tooltip text.

        locked (bool):
            Enable fixed-size locking.

    Example:
        >>> button = IconButton(self, width=24, height=24)
    """

    name = "icon"

    def __init__(self, parent, **kwargs):
        """Initialize icon button.

        Args:
            parent (QWidget):
                Parent widget.

            **kwargs:
                Button configuration options.
        """

        # Initialize QPushButton
        super(IconButton, self).__init__(parent)

        # Button Size
        self.width = kwargs.get("width", 22)
        self.height = kwargs.get("height", 22)

        # Fixed Size Lock
        self.locked = False if kwargs.get("locked") == False else True

        if kwargs.get("checkable"):
            self.setCheckable(kwargs["checkable"])

        # Tooltip
        if kwargs.get("tooltip"):
            self.setToolTip(kwargs["tooltip"])

        # Flat Button Style
        self.setFlat(True)

        # Load Button Icon
        icon = NamePixmapIcon(self.name)
        self.setIcon(icon)
        self.setIconSize(QtCore.QSize(self.width, self.height))

        # Apply Fixed Size
        if self.locked:
            self.setMinimumSize(QtCore.QSize(self.width, self.height))
            self.setMaximumSize(QtCore.QSize(self.width, self.height))


class OpenButton(IconButton):
    """Media/file open button."""

    name = "open"


class BackwordButton(IconButton):
    """Backward frame/playback button."""

    name = "backward"


class PlayPauseButton(IconButton):
    """Playback play/pause button.

    Features:
        - Dynamic play/pause icons
        - Dynamic tooltip updates

    Example:
        >>> button.switch(True)
    """

    name = "play"

    def switch(self, value):
        """Switch play/pause icon state.

        Args:
            value (bool):
                Playback state.

                True:
                    Show pause icon.

                False:
                    Show play icon.
        """

        # Resolve Icon Name
        name = "pause" if value else self.name

        # Update Tooltip
        self.setToolTip(name.capitalize())

        # Update Icon
        icon = NamePixmapIcon(name)
        self.setIcon(icon)


class ForwardButton(IconButton):
    """Forward frame/playback button."""

    name = "forward"


class PencilButton(IconButton):
    """Pencil button."""

    name = "pencil"


class ArrowButton(IconButton):
    """Arrow button."""

    name = "arrow"


class EllipseButton(IconButton):
    """Ellipse button."""

    name = "ellipse"


class RectangleButton(IconButton):
    """Rectangle button."""

    name = "rectangle"


class EraserButton(IconButton):
    """Erasier button."""

    name = "eraser"


class TxtButton(IconButton):
    """Txt button."""

    name = "txt"


class MoveButton(IconButton):
    """Move button."""

    name = "move"


class UndoButton(IconButton):
    """Undo button."""

    name = "undo"


class ClearButton(IconButton):
    """Clear button."""

    name = "clear"


class RenderButton(IconButton):
    """Render button."""

    name = "render"


class AttachButton(IconButton):
    """Attach button."""

    name = "attach"


class RecapsButton(IconButton):
    """Recaps button."""

    name = "recaps"


class SnapshotButton(IconButton):
    """Snapshot button."""

    name = "snapshot"


class RemoveButton(IconButton):
    """Remove button."""

    name = "remove"


class HelpButton(IconButton):
    """Help/documentation button."""

    name = "help"


class TextButton(QtWidgets.QPushButton):
    """
    Standard text-based push button.

    Provides a simple wrapper around QPushButton with support for label text and tooltip initialization through keyword arguments.
    """

    def __init__(self, parent, **kwargs):
        """
        Initialize text button.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

            **kwargs:
                label (str, optional):
                    Button display text.

                toolTip (str, optional):
                    Tooltip text displayed on hover.
        """

        # Initialize QPushButton
        super(TextButton, self).__init__(parent)

        # Apply tooltip
        if kwargs.get("toolTip"):
            self.setToolTip(kwargs["toolTip"])

        # Apply label text
        if kwargs.get("label"):
            self.setText(kwargs["label"])

        # Disable default button behavior
        self.setAutoDefault(False)
        self.setDefault(False)


class ColorButton(QtWidgets.QPushButton):
    """
    Circular color picker button.

    Displays the currently selected color and opens a custom color dialog when clicked.
    """

    # Emitted when color changes
    color_changed = QtCore.Signal(tuple)

    def __init__(self, parent, **kwargs):
        """
        Initialize color button.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

            **kwargs:
                width (int, optional):
                    Button width.

                height (int, optional):
                    Button height.

                locked (bool, optional):
                    Lock button size.

                tooltip (str, optional):
                    Tooltip text.
        """

        # Initialize QPushButton
        super(ColorButton, self).__init__(parent)

        # Button dimensions
        self.width = kwargs.get("width", 22)
        self.height = kwargs.get("height", 22)

        # Default color (red)
        self.color = (255, 0, 0)

        # Fixed size lock
        self.locked = False if kwargs.get("locked") == False else True

        # Apply tooltip
        if kwargs.get("tooltip"):
            self.setToolTip(kwargs["tooltip"])

        # Flat appearance
        self.setFlat(True)

        # Apply fixed size if enabled
        if self.locked:
            self.setMinimumSize(QtCore.QSize(self.width, self.height))
            self.setMaximumSize(QtCore.QSize(self.width, self.height))

        # Apply initial button style
        self.updateStyle()

        # Disable default button behavior
        self.setAutoDefault(False)
        self.setDefault(False)

        # Open color dialog on click
        self.clicked.connect(self.pickColor)

    def updateStyle(self):
        """
        Update button appearance using current color.
        """

        self.setStyleSheet(f"""
            border-radius: {self.width / 2}px;
            border: 1px solid #ffffff;
            background-color: rgb{self.color};
            """)

    def setColor(self, color):
        """
        Set button color.

        Args:
            color (tuple):
                RGB color tuple.
        """

        # Store color
        self.color = color

        # Refresh appearance
        self.updateStyle()

        # Emit change notification
        self.color_changed.emit(self.color)

    def getColor(self):
        """
        Return current color.

        Returns:
            tuple:
                RGB color tuple.
        """

        return self.color

    def pickColor(self):
        """
        Open color picker dialog and update color.
        """

        # Create dialog
        color_dialog = ColorDialog(self)

        if color_dialog.exec():
            result = color_dialog.getColor()

            if not result:
                return

            self.color = result

            # Apply selected color
            self.setColor(result)


class TextToolButton(QtWidgets.QToolButton):
    """
    Text-based tool button.

    Used for toolbar actions that display text instead of icons.
    """

    def __init__(self, parent, value, **kwargs):
        """
        Initialize tool button.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

            value (str):
                Button label text.

            **kwargs:
                checkable (bool, optional):
                    Enable checkable state.
        """

        # Initialize QToolButton
        super(TextToolButton, self).__init__(parent)

        # Set display text
        self.setText(value)

        # Enable toggle behavior
        if kwargs.get("checkable"):
            self.setCheckable(kwargs["checkable"])


class ToolButton(QtWidgets.QToolButton):
    """Base tool button widget.

    This class provides a reusable QToolButton wrapper used for toolbar actions.

    Features:
        - Resource icon loading
        - Fixed-size configuration
        - Tooltip support
        - Icon scaling

    Class Attributes:
        name (str):
            Resource icon name.

    Args:
        parent (QWidget):
            Parent widget.

    Keyword Args:
        width (int):
            Button width.

        height (int):
            Button height.

        tooltip (str):
            Tooltip text.

    Example:
        >>> button = ToolButton(self, tooltip="Settings")
    """

    name = "tool"

    def __init__(self, parent, **kwargs):
        """Initialize tool button.

        Args:
            parent (QWidget):
                Parent widget.

            **kwargs:
                Tool button options.
        """

        # Initialize QToolButton
        super(ToolButton, self).__init__(parent)

        # Button Size
        self.width = kwargs.get("width", 32)
        self.height = kwargs.get("height", 32)

        # Tooltip
        if kwargs.get("tooltip"):
            self.setToolTip(kwargs["tooltip"])

        # Load Button Icon
        icon = NamePixmapIcon(self.name)
        self.setIcon(icon)
        self.setIconSize(QtCore.QSize(self.width, self.height))

        # Apply Fixed Size
        self.setMinimumSize(QtCore.QSize(self.width, self.height))
        self.setMaximumSize(QtCore.QSize(self.width, self.height))


class LoopButton(ToolButton):
    """Loop playback toggle button.

    Features:
        - Checkable button
        - Loop playback state

    Example:
        >>> button.isChecked()
    """

    name = "loop"

    def __init__(self, parent, **kwargs):
        """Initialize loop button.

        Args:
            parent (QWidget):
                Parent widget.

            **kwargs:
                Button options.
        """

        # Initialize ToolButton
        super(LoopButton, self).__init__(parent, **kwargs)

        # Enable Toggle State
        self.setCheckable(True)

        # Default Loop State
        self.setChecked(False)


class DisplayMenuButton(ToolButton):
    """Watermark/display settings menu button.

    This button opens the watermark overlay display configuration menu.

    Features:
        - Display menu integration
        - Watermark settings access
        - Overlay controls

    Example:
        >>> button = DisplayMenuButton(self)
    """

    name = "display"

    def __init__(self, parent, **kwargs):
        """Initialize display menu button.

        Args:
            parent (QWidget):
                Parent widget.

            **kwargs:
                Button options.
        """

        # Initialize ToolButton
        super(DisplayMenuButton, self).__init__(parent, **kwargs)

        # Create Display Menu
        self.menu = DisplayMenus(self)

        # Connect Menu Trigger
        self.clicked.connect(self.contextMenu)

    def contextMenu(self):
        """Open display menu.

        Example:
            >>> button.contextMenu()
        """

        # Execute Menu
        self.menu.exec(QtGui.QCursor.pos())


if __name__ == "__main__":
    pass
