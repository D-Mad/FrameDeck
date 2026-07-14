"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/comboboxs.py

Description:
    This module provides reusable Qt combobox widgets used throughout the Review Player application.

Responsibilities:
    - Context-based combobox handling
    - FPS selection
    - Project selection
    - AOV selection
    - Context object management

Features:
    - Dictionary-based item storage
    - Automatic context tracking
    - Signal-driven updates
    - Project selection
    - FPS selection
    - AOV selection
    - Custom styling support

Architecture:
    Context Data
        ↓
    Combobox Widget
        ↓
    User Selection
        ↓
    Context Signal

Notes:
    This module is used by:
        - Playback controls
        - Viewer settings
        - Project browser
        - OCIO/AOV controls
        - Timeline systems
"""

from __future__ import absolute_import

import constants

from PySide6 import QtCore
from PySide6 import QtWidgets

from playback import speed as speedmath

from widgets.styles import Font
from widgets.styles import WaitCursor


class ContextCombobox(QtWidgets.QComboBox):
    """
    Generic context-aware combobox widget, stores dictionary-based context data while displaying user-friendly labels.

    Features:
        - Dictionary-based item storage
        - Automatic context tracking
        - Current item lookup
        - Value-based item selection

    Example:
        >>> items = [
        ...     {"code": "24 FPS", "value": 24},
        ...     {"code": "30 FPS", "value": 30},
        ... ]

        >>> combobox = ContextCombobox(self, key="code", contextList=items)
    """

    def __init__(self, parent, **kwargs):
        """
        Initialize context combobox.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

        Keyword Args:
            key (str):
                Dictionary key used for display labels.

            contextList (list):
                List of context dictionaries.

            tooltip (str):
                Tooltip text.
        """

        # Initialize QComboBox
        super(ContextCombobox, self).__init__(parent)

        # Store display key
        self.key = kwargs.get("key", "code")

        # Store context list
        self.contextList = kwargs.get("contextList", list())

        # Tooltip
        if kwargs.get("tooltip"):
            self.setToolTip(kwargs["tooltip"])

        # Initialize items
        self.setItems(contextList=None)

        # Connect signals
        self.currentIndexChanged.connect(self.indexChange)

    def setItems(self, contextList=None):
        """
        Set combobox items from context list.

        Args:
            contextList (list, optional):
                List of context dictionaries.
        """

        # Store context list
        self.contextList = contextList or self.contextList

        # Build display values
        if self.contextList:
            self.context = self.contextList[0]
            self.values = [x[self.key] for x in self.contextList]
        else:
            self.context = dict()
            self.values = list()

        # Refresh combobox items
        self.clear()

        self.addItems(self.values)

    def getValue(self):
        """
        Return current context dictionary.

        Returns:
            dict:
                Current selected context.
        """

        return self.context

    def setValue(self, value, **kwargs):
        """
        Set current combobox value.

        Supports:
            - Integer index
            - Dictionary object
            - Display string

        Args:
            value:
                Value to select.
        """

        # Default fallback
        value = 0 if value is None else value

        if isinstance(value, int):  # Integer index
            index = value
        elif isinstance(value, dict):  # Dictionary object
            if value in self.contextList:
                index = self.contextList.index(value)
            else:
                index = 0
        else:  # Display string
            index = self.values.index(value) if value in self.values else 0

        # Update combobox index
        self.setCurrentIndex(index)
        self.context = self.contextList[index]

    def indexChange(self, index):
        """
        Update active context when index changes.

        Args:
            index (int):
                Current combobox index.
        """

        # Validate context list
        if not self.contextList:
            return

        # Store active context
        self.context = self.contextList[index]

    def findByKey(self, value, key=None):
        key = key or self.key

        result = next(filter(lambda x: x[key] == value, self.contextList), None)

        return result


class SpeedCombobox(QtWidgets.QComboBox):
    """
    Playback speed multiplier selector.

    Signals:
        speed_changed(float):
            Emits the selected multiplier (1.0 is real time).

    Example:
        >>> combobox.speed_changed.connect(callback)
    """

    speed_changed = QtCore.Signal(float)

    def __init__(self, parent=None, **kwargs):
        """
        Initialize the playback speed combobox.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.
        """

        super(SpeedCombobox, self).__init__(parent)

        self.setToolTip("Playback speed (audio is silent off 1x)")

        # Transparent styling, matching the FPS selector beside it.
        self.setStyleSheet("QComboBox {background: transparent; border: none;}")

        for value in constants.PLAYBACK_SPEEDS:
            self.addItem(speedmath.label_for(value), float(value))

        self.setValue(constants.DEFAULT_PLAYBACK_SPEED)

        self.currentIndexChanged.connect(self.indexChange)

    def indexChange(self, index):
        """
        Handle a speed selection change.

        Args:
            index (int):
                Current combobox index.
        """

        value = self.itemData(index)

        if value is None:
            return

        self.speed_changed.emit(float(value))

    def setValue(self, value):
        """
        Select *value* without re-emitting speed_changed.

        Used to reflect a speed set from elsewhere (menu, shortcut) back into
        the combobox without looping the signal straight back out again.

        Args:
            value (float):
                Speed multiplier to select.
        """

        index = self.findData(float(value))

        if index < 0:
            return

        blocker = QtCore.QSignalBlocker(self)
        self.setCurrentIndex(index)
        del blocker


class FbsCombobox(ContextCombobox):
    """
    Frames-per-second selection combobox, provides playback FPS selection using predefined constants.

    Signals:
        fps_changed(dict):
            Emits selected FPS context.

    Example:
        >>> combobox.fps_changed.connect(callback)
    """

    fps_changed = QtCore.Signal(dict)

    def __init__(self, parent, **kwargs):
        """
        Initialize FPS combobox.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.
        """

        # Configure FPS context
        kwargs["key"] = "code"
        kwargs["contextList"] = constants.FPS_VALUES

        # Initialize base combobox
        super(FbsCombobox, self).__init__(parent, **kwargs)

        # Tooltip
        self.setToolTip("Frame Per Second")

        # Transparent styling
        self.setStyleSheet("QComboBox {background: transparent; border: none;}")

        # Set default FPS
        self.setValue(constants.DEFULT_FPS)

    def indexChange(self, index):
        """
        Handle FPS selection change.

        Args:
            index (int):
                Current combobox index.
        """

        # Update current context
        super().indexChange(index)

        # Emit FPS context
        self.fps_changed.emit(self.context)


class AovsCombobox(QtWidgets.QComboBox):
    """
    AOV selection combobox, is used for selecting available EXR AOV/image layers.

    Features:
        - Dynamic AOV population
        - Enable/disable support
        - Transparent styling

    Example:
        >>> combobox.setAovs(["rgb", "depth"])
    """

    def __init__(self, parent, **kwargs):
        """
        Initialize AOV combobox.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.
        """

        # Initialize QComboBox
        super(AovsCombobox, self).__init__(parent)

        # Tooltip
        self.setToolTip("Source Media Aovs")

        # Transparent styling
        self.setStyleSheet("QComboBox {background: transparent; border: none;}")

        # Minimum width
        # self.setMinimumSize(QtCore.QSize(100, 0))

        # Size policy
        sizepolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred
        )
        self.setSizePolicy(sizepolicy)

    def setAovs(self, aovs):
        """
        Set available AOV names.

        Args:
            aovs (list):
                List of AOV names.
        """

        # Normalize input
        aovs = aovs or list()

        # Refresh items
        self.clear()
        self.addItems(aovs)

        # Enable state
        self.setEnabled(True if aovs else False)


class ProjectCombobox(ContextCombobox):
    """
    Project selection combobox, provides project selection support using dictionary-based context objects.

    Signals:
        project_changed(dict):
            Emits selected project context.

    Example:
        >>> combobox.project_changed.connect(callback)
    """

    project_changed = QtCore.Signal(dict)

    def __init__(self, parent, **kwargs):
        """
        Initialize project combobox.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.
        """

        # Initialize base combobox
        super(ProjectCombobox, self).__init__(parent, **kwargs)

        # Setup font
        font = Font(15, bold=False)
        self.setFont(font)

        # Transparent styling
        self.setStyleSheet("QComboBox {background: transparent; border: none;}")

    def indexChange(self, index):
        """
        Handle project selection change.

        Args:
            index (int):
                Current combobox index.
        """

        # Update active context
        super().indexChange(index)

        # Emit project context
        self.project_changed.emit(self.context)

    def setProjects(self, contextList=None):
        """
        Collect and set the project block area
        """
        if contextList:
            result = contextList
        else:
            with WaitCursor():
                from scripts import Projects

                result = Projects.get()

        self.setItems(contextList=result)


class ReviewTypeCombobox(ContextCombobox):

    def __init__(self, parent, **kwargs):
        kwargs["contextList"] = constants.REVIEW_TYPES
        kwargs["key"] = "value"

        super(ReviewTypeCombobox, self).__init__(parent, **kwargs)


class StatusTypeCombobox(ContextCombobox):

    def __init__(self, parent, **kwargs):
        kwargs["contextList"] = constants.STATUS_LIST

        super(StatusTypeCombobox, self).__init__(parent, **kwargs)

        self.defatlt = next(filter(lambda x: x[self.key] == "Viewed", self.contextList), dict())
        self.setValue(self.defatlt)

    def value(self, key=None):
        key = key or self.key

        return self.context.get(key)


class NormalCombobox(QtWidgets.QComboBox):

    def __init__(self, parent, **kwargs):
        super(NormalCombobox, self).__init__(parent)

        self.values = kwargs.get("values")

        if self.values:
            self.setItems(values=self.values)

    def setItems(self, values=None):
        self.values = values or self.values

        self.clear()
        self.addItems([str(x) for x in self.values])

    def setValue(self, value, **kwargs):
        index = self.values.index(value)
        self.setCurrentIndex(index)

    def getValue(self):
        index = self.currentIndex()
        if not self.values:
            return

        value = None if self.values[index] == "null" else self.values[index]
        return value


if __name__ == "__main__":
    pass
