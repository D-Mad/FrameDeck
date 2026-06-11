"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/lineedits.py

Description:
    Collection of custom spin box widgets used throughout the application for numeric value entry and editing.

Responsibilities:
    - Provide thickness value editing.
    - Provide font size editing.
    - Emit custom value change signals.
    - Provide consistent sizing and alignment.

Features:
    - Floating-point thickness input.
    - Integer font size input.
    - Configurable min/max ranges.
    - Alignment support.
    - Custom thickness changed signal.
    - Hidden spin box buttons.

Architecture:
    User Input
        ↓
    ThicknesSpinBox
        ↓
    thicknes_changed Signal
        ↓
    Annotation Thickness Update

    User Input
        ↓
    FontSizeSpinBox
        ↓
    Font Size Value
        ↓
    Text Annotation Rendering

Notes:
    - Thickness values support decimal precision.
    - Font size values are integer based.
    - Spin buttons are hidden for a cleaner UI.
"""

from __future__ import absolute_import

from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtWidgets


class ThicknesSpinBox(QtWidgets.QDoubleSpinBox):
    """
    Thickness value spin box.

    Specialized floating-point spin box used for editing brush, pen, or annotation thickness values.
    """

    # Emitted when thickness value changes
    thicknes_changed = QtCore.Signal(float)

    def __init__(self, parent, value, **kwargs):
        """
        Initialize thickness spin box.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

            value (float):
                Initial thickness value.

            **kwargs:
                decimals (int, optional):
                    Number of decimal places.

                minimum (float, optional):
                    Minimum allowed value.

                maximum (float, optional):
                    Maximum allowed value.

                alignment (str, optional):
                    Text alignment.
                    Supported values:
                    - left
                    - right
                    - center
        """

        # Initialize QDoubleSpinBox
        super(ThicknesSpinBox, self).__init__(parent)

        # Configuration values
        decimals = kwargs.get("decimals") or 1
        minimum = kwargs.get("minimum") or 0.00
        maximum = kwargs.get("maximum") or 999999999.00

        # Apply decimal precision
        self.setDecimals(2)

        # Apply value limits
        self.setMinimum(minimum)
        self.setMaximum(maximum)

        # Set initial value
        self.setValue(value)

        # Hide increment buttons
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)

        # Supported alignments
        alignments = {
            "left": QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
            "right": QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter,
            "Center": QtCore.Qt.AlignCenter,
        }

        # Apply alignment
        if kwargs.get("alignment") and kwargs["alignment"] in alignments:
            self.setAlignment(alignments[kwargs["alignment"]])

        # Fixed minimum width
        self.setMinimumSize(QtCore.QSize(106, 0))

        # Emit custom signal
        self.valueChanged.connect(self.value_change)

    def value_change(self):
        """
        Handle value changes.

        Emits the current thickness value through the thicknes_changed signal.
        """

        self.thicknes_changed.emit(self.value())


class FontSizeSpinBox(QtWidgets.QSpinBox):
    """
    Font size spin box.

    Specialized integer spin box used for editing text font sizes.
    """

    def __init__(self, parent, value, **kwargs):
        """
        Initialize font size spin box.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

            value (int):
                Initial font size.

            **kwargs:
                minimum (int, optional):
                    Minimum allowed value.

                maximum (int, optional):
                    Maximum allowed value.
        """

        # Initialize QSpinBox
        super(FontSizeSpinBox, self).__init__(parent)

        # Value limits
        minimum = kwargs.get("minimum") or 0
        maximum = kwargs.get("maximum") or 999999999

        # Apply limits
        self.setMinimum(minimum)
        self.setMaximum(maximum)

        # Increment amount
        self.setSingleStep(1)

        # Initial value
        self.setValue(value)


if __name__ == "__main__":
    pass
