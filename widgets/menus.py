"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/menus.py

Description:
    This module contains reusable Qt menu and action wrappers used throughout the Review Player application.

The module primarily provides:
    - Watermark display menus
    - Overlay visibility controls
    - QAction wrapper utilities
    - Dynamic watermark configuration support

Main Components:
    WatermarkMenus:
        Dynamic watermark overlay menu system.

    WatermarkAction:
        Reusable QAction wrapper for overlay controls.

Features:
    - Watermark preset loading
    - Dynamic overlay toggles
    - Version/media watermark updates
    - Overlay state management
    - Signal-based UI communication
"""

from __future__ import absolute_import

import utils
import resources

from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtWidgets


class WatermarkMenus(QtWidgets.QMenu):
    """
    This menu dynamically builds watermark toggle actions from the ``watermarks.json`` preset configuration file.

    The menu is primarily used by the viewer overlay system to:

    - Enable or disable watermark items
    - Update watermark values from media/version data
    - Clear active watermark values
    - Emit UI display state changes

    Signals:
        display_changed (bool, str, str, dict):
            Emitted whenever a watermark action is toggled.

            Arguments:
                checked (bool):
                    Current checked state.

                key (str):
                    Watermark code/key.

                position (str):
                    Watermark screen position.

                param (dict):
                    Full watermark configuration dictionary.

    Example:
        >>> menu = WatermarkMenus(parent)
        >>> menu.display_changed.connect(callback)
    """

    display_changed = QtCore.Signal(bool, str, str, dict)

    def __init__(self, parent, **kwargs):
        """
        Initialize display watermark menu.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.
        """

        super().__init__(parent)

        # Configure menu
        self.setTitle("Display")
        self.setTearOffEnabled(True)

        # Load watermark preset configuration
        self.watermarks = resources.getPreset("watermarks")

        # Build watermark actions
        for position, values in self.watermarks.items():
            for context in values:
                # Skip disabled overlays
                if not context.get("enable"):
                    continue

                # Create menu action
                action = WatermarkAction(
                    self, context["code"], context["checked"], enable=context["enable"]
                )
                self.addAction(action)

                # Emit overlay state changes
                action.toggled.connect(
                    lambda checked, key=context[
                        "code"
                    ], pos=position, param=context: self.display_changed.emit(
                        checked, key, pos, param
                    )
                )

    def update_watermarks(self, inputs, **kwargs):
        """
        Override watermark values from version/media context.
        This updates overlay text and image values dynamically based on the currently loaded media/version data.

        Args:
            inputs (dict):
                Version/media data dictionary.

            **kwargs:
                Additional override values such as:

                - studio_logo
                - project_logo

        Example:
            >>> menu.update_watermarks(version)
        """

        self.watermarks = utils.overrideWatermarkValues(
            inputs, watermarks=self.watermarks, **kwargs
        )

    def clear_watermarks(self):
        """
        Clear all watermark display values.
        This preserves watermark configuration and visibility states but removes current overlay values.
        """

        for position in self.watermarks:
            for overlay in self.watermarks[position]:
                # Skip disabled overlays
                if not overlay.get("enable"):
                    continue

                # Reset overlay value
                overlay["value"] = None


class WatermarkAction(QtGui.QAction):
    """
    Watermark display QAction wrapper.

    This action represents an individual watermark toggle item inside the display menu.

    Features:
        - Checkable overlay state
        - Enable/disable support
        - Dynamic watermark labels

    Example:
        >>> action = WatermarkAction(menu, "project", True)
    """

    def __init__(self, parent, text, checked, **kwargs):
        """
        Initialize display action.

        Args:
            parent (QtWidgets.QWidget):
                Parent menu.

            text (str):
                Action display label.

            checked (bool):
                Initial checked state.

            **kwargs:
                Optional keyword arguments.

                enable (bool):
                    Enable or disable the action.
        """

        super(WatermarkAction, self).__init__(parent)

        # Resolve enabled state
        enable = True if kwargs.get("enable") is None else kwargs["enable"]

        # Configure action
        self.setCheckable(True)
        self.setChecked(checked)
        self.setText(text)
        self.setEnabled(enable)


if __name__ == "__main__":
    pass
