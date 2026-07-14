"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/dialogs.py

Description:
    This module provides reusable Qt dialog widgets used throughout the Review Player application.

Responsibilities:
    - Media file browsing
    - Image sequence handling
    - Sequence collapsing
    - QFileDialog customization
    - Sequence-aware proxy filtering

Features:
    - Video file browsing
    - Image sequence browsing
    - Sequence collapsing using #### notation
    - QFileSystemModel integration
    - Custom Qt item delegates
    - Sequence-aware filtering
    - Custom proxy models

Architecture:
    QFileDialog
        ↓
    Proxy Model
        ↓
    Sequence Delegate
        ↓
    Filtered File Display

Notes:
    This module is used by:
        - Media loading workflows
        - Image sequence selection
        - Video file browsing
        - Playlist loading systems
"""

from __future__ import absolute_import

import re

import utils
import constants

from PySide6 import QtCore
from PySide6 import QtWidgets

from widgets.styles import SetStylesheet


class SequenceDisplayDelegate(QtWidgets.QStyledItemDelegate):
    """
    Custom display delegate for sequence-aware file visualization.

    This delegate converts numbered image sequence filenames into
    collapsed #### format for cleaner display inside QFileDialog.

    Example:
        Input:
            shot010_comp.1001.exr

        Output:
            shot010_comp.####.exr
    """

    def initStyleOption(self, option, index):
        """
        Override item display text for sequence visualization.

        Args:
            option (QtWidgets.QStyleOptionViewItem):
                Qt style option.

            index (QtCore.QModelIndex):
                Current model index.
        """

        super().initStyleOption(option, index)

        proxy = index.model()
        if hasattr(proxy, "__collapse_sequences__") and proxy.__collapse_sequences__:
            if index.column() == 0:
                self.collapsename = re.sub(
                    r"\.(\d+)\.", lambda x: "." + ("#" * len(x.group(1))) + ".", option.text
                )
                option.text = self.collapsename


class SequenceFilterProxyModel(QtCore.QSortFilterProxyModel):
    """
    Proxy model used for collapsing image sequences.

    This model filters duplicate sequence frames and only displays
    a single representative item for each detected image sequence.

    Example:
        Input Files:
            render.1001.exr
            render.1002.exr
            render.1003.exr

        Displayed:
            render.####.exr
    """

    def __init__(self, parent=None):
        """
        Initialize sequence proxy model.

        Args:
            parent (QObject, optional):
                Parent Qt object.
        """

        super().__init__(parent)

        self.__collapse_sequences__ = False
        self.__seen_sequences__ = set()

    def setCombineSequences(self, enable):
        """
        Enable or disable sequence collapsing.

        Args:
            enable (bool):
                True to collapse sequences.
        """

        self.__collapse_sequences__ = enable
        self.clear_cache()

    def clear_cache(self):
        """
        Clear internal sequence tracking cache.
        This is required whenever folders change or filtering mode changes.
        """

        self.__seen_sequences__.clear()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        """
        Determine whether a row should be displayed.

        Args:
            source_row (int):
                Source model row index.

            source_parent (QtCore.QModelIndex):
                Parent model index.

        Returns:
            bool:
                True if row should be displayed.
        """

        if not self.__collapse_sequences__:
            return True

        # Always show directories
        source_model = self.sourceModel()
        index = source_model.index(source_row, 0, source_parent)

        # Always show directories
        if source_model.isDir(index):
            return True

        file_name = source_model.fileName(index)

        # Match pattern: name.number.ext
        match = re.search(r"(.*)\.(\d+)\.(\w+)$", file_name)

        if match:
            # Create key: "filename.ext"
            seq_key = f"{match.group(1)}.{match.group(3)}"
            if seq_key not in self.__seen_sequences__:
                self.__seen_sequences__.add(seq_key)
                return True
            return False

        return True


class OpenMediaDialog(QtWidgets.QFileDialog):
    """
    Custom media open dialog for Review Player.

    Supports:
        - Video files
        - Image sequences
        - Sequence collapsing
        - Sequence-aware path conversion

    Example:
        dialog = OpenMediaDialog(self)

        if dialog.exec():
            filepath = dialog.getfile()
            print(filepath)
    """

    def __init__(self, parent, **kwargs):
        """
        Initialize media open dialog.

        Args:
            parent (QWidget):
                Parent widget.

        Keyword Args:
            browsepath (str):
                Initial browse directory.
        """

        super().__init__(parent)

        self.browsepath = kwargs.get("browsepath") or QtCore.QDir.homePath()

        self.setDirectory(self.browsepath)

        # Define supported file filters
        self.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFiles)

        # Define the filters
        filefilters = (f"Image and Video Files (*.{' *.'.join(constants.OPEN_EXTENSIONS)})",)
        self.setNameFilters(filefilters)
        self.setWindowTitle("Open Media")

        # Required for custom proxy model support
        self.setOption(QtWidgets.QFileDialog.Option.DontUseNativeDialog, True)

        # Setup proxy model
        self.proxy = SequenceFilterProxyModel(self)
        self.setProxyModel(self.proxy)

        # Setup delegate
        self.delegate = SequenceDisplayDelegate(self)
        self.setItemDelegate(self.delegate)

        # Sequence collapse checkbox
        self.collapseCheckbox = QtWidgets.QCheckBox("Collapse Sequences (####)")
        self.collapseCheckbox.toggled.connect(self.proxy.setCombineSequences)

        # Add checkbox into dialog layout
        layout = self.layout()
        layout.addWidget(self.collapseCheckbox, layout.rowCount(), 0)

        # Connect internal QFileSystemModel
        source_model = self.proxy.sourceModel()
        if isinstance(source_model, QtWidgets.QFileSystemModel):
            source_model.rootPathChanged.connect(self.proxy.clear_cache)
            source_model.rootPathChanged.connect(self.uncheck)

    def uncheck(self):
        """
        Disable sequence collapsing checkbox.
        Called automatically when directory changes.
        """

        self.collapseCheckbox.setChecked(False)

    def getfile(self):
        """
        Return selected media filepath.

        Returns:
            str or None:
                Selected file path.

        Notes:
            When sequence collapsing is enabled,
            frame numbers are replaced using #### notation.

        Example:
            Output:
                render.####.exr
        """

        files = self.getfiles()
        return files[0] if files else None

    def getfiles(self):
        """Return every selected path, preserving collapsed image sequences."""
        selectedfiles = self.selectedFiles()
        if not selectedfiles:
            return list()

        result = list()
        for path in selectedfiles:
            if self.proxy.__collapse_sequences__:
                dirname = utils.dirname(path)
                basename = utils.fileName(path, extension=True)
                pattern_name = re.sub(
                    r"\.(\d+)\.",
                    lambda x: "." + ("#" * len(x.group(1))) + ".",
                    basename,
                )
                path = utils.pathResolver(dirname, filename=pattern_name)

            if path not in result:
                result.append(path)

        return result


class ColorDialog(QtWidgets.QColorDialog):
    """
    Custom color picker dialog.

    Provides a themed QColorDialog and helper method for returning the selected color as an RGB tuple.
    """

    def __init__(self, parent, **kwargs):
        """
        Initialize color dialog.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

            **kwargs:
                Additional optional arguments.
        """

        # Initialize QColorDialog
        super().__init__(parent)

        # Apply application theme
        SetStylesheet(self, theme=constants.DEFAULT_THEME)

    def getColor(self):
        """
        Return selected color.

        Returns:
            tuple or None:
                RGB color tuple in the form (red, green, blue).

                Returns None if no valid color was selected.
        """

        # Retrieve selected color
        color_form = self.selectedColor()

        # Validate color
        if not color_form.isValid():
            return

        # Convert QColor to RGB tuple
        color = (color_form.red(), color_form.green(), color_form.blue())

        return color


class FileDialog(QtWidgets.QFileDialog):
    """
    Custom file dialog wrapper.

    Provides helper methods for file selection and save file operations with configurable extensions.
    """

    def __init__(self, parent, title, **kwargs):
        """
        Initialize file dialog.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

            title (str):
                Dialog title.

            **kwargs:
                browsepath (str, optional):
                    Initial browse location.

                extensions (list[str], optional):
                    Allowed file extensions.

                label (str, optional):
                    File type label.
        """

        # Initialize QFileDialog
        super().__init__(parent)

        # Dialog title
        self.title = title

        # Initial browse path
        self.browsepath = kwargs.get("browsepath") or QtCore.QDir.homePath()

        # Supported file extensions
        self.extensions = kwargs.get("extensions", ["txt"])

        # Display label
        self.label = kwargs.get("label", "txt")

    def savefile(self, name):
        """
        Open save file dialog.

        Args:
            name (str):
                Suggested file name.

        Returns:
            str:
                Selected output file path.

                Returns an empty string if the user cancels.
        """

        # Build default file name
        filename = f"{name}.{self.extensions[0]}" if name else f"untitle.{self.extensions[0]}"

        # Build file filter pattern
        pattern = ";;".join(f"{ext.upper()} (*.{ext.lower()})" for ext in self.extensions)

        # Open save dialog
        filepath, fileFormat = self.getSaveFileName(self, self.title, filename, pattern)

        return filepath

    def pickFile(self):
        """
        Open file picker dialog.

        Returns:
            str:
                Selected file path.

                Returns an empty string if the user cancels.
        """

        # Build filter pattern
        pattern = f"{self.label} (*{' *'.join(self.extensions)})"

        # Open file dialog
        filepath, fileFormat = self.getOpenFileName(self, self.title, self.browsepath, pattern)

        # Update browse path
        if filepath:
            filepath = utils.pathResolver(filepath)
            self.browsepath = utils.dirname(filepath)

        return filepath


if __name__ == "__main__":
    pass
