"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/fontdialog.py

Description:
    Provides a rich text input dialog used for creating and editing text annotations within the review player.
    The dialog allows users to configure text appearance through font family selection, font size adjustment,text styling options, and color selection.

Responsibilities:
    - Collect user text input.
    - Manage font family selection.
    - Manage font size selection.
    - Manage text styling options.
    - Manage text color selection.
    - Return annotation settings to the caller.

Features:
    - Font family selection
    - Font size control
    - Bold text
    - Italic text
    - Underline text
    - Strike-out text
    - Text color selection
    - Multi-line text editing
    - Signal-based data return

Architecture:
    TxtInputDialog
        ├── Font Toolbar
        │   ├── FontComboBox
        │   ├── FontSizeSpinBox
        │   ├── Bold Button
        │   ├── Italic Button
        │   ├── Underline Button
        │   ├── Strike Button
        │   └── Color Button
        │
        ├── QTextEdit
        │
        ├── Action Buttons
        │   ├── Close
        │   └── Apply and Close
        │
        └── Copyright Label

Notes:
    - Formatting values are stored as a dictionary.
    - The dialog emits formatted text settings through
      the value_changed signal.
    - Intended for annotation and review workflows.

"""

from __future__ import absolute_import

from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtWidgets

from widgets.buttons import TextButton
from widgets.buttons import ColorButton
from widgets.labels import CopyrightLabel
from widgets.buttons import TextToolButton
from widgets.layouts import VerticalLayout
from widgets.layouts import HorizontalSpacer
from widgets.layouts import HorizontalLayout
from widgets.lineedits import FontSizeSpinBox


class TxtInputDialog(QtWidgets.QDialog):
    """
    Text input dialog with rich text formatting controls.

    Provides controls for selecting font family, font size, text style attributes, and text color.
    Returns the collected settings as a dictionary when applied.
    """

    # Emitted when user applies text settings
    value_changed = QtCore.Signal(str, bool, dict)

    def __init__(self, parent, **kwargs):
        """
        Initialize text input dialog.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

            **kwargs:
                Additional optional arguments.
        """

        # Initialize QDialog
        super().__init__(parent)

        # Current font object
        self.current_font = QtGui.QFont()

        # Stores current formatting values
        self.values = dict()

        # Build user interface
        self.setupUi()

    def setupUi(self):
        """
        Build dialog user interface.
        """

        # Set initial dialog size
        self.resize(665, 400)

        # Set dialog title
        self.setWindowTitle("Add Note")

        # Main layout
        self.verticallayout = VerticalLayout(self, space=10, margins=(20, 20, 20, 20))

        # --------------------------------------------------
        # Font Toolbar
        # --------------------------------------------------
        self.horizontallayout = HorizontalLayout(None, space=10, margins=(0, 0, 0, 0))
        self.verticallayout.addLayout(self.horizontallayout)

        # Font family selector
        self.fontComboBox = QtWidgets.QFontComboBox(self)
        self.fontComboBox.setWritingSystem(QtGui.QFontDatabase.Any)
        self.horizontallayout.addWidget(self.fontComboBox)

        # Font size selector
        self.fontSizeSpinBox = FontSizeSpinBox(self, 12)
        self.horizontallayout.addWidget(self.fontSizeSpinBox)

        # Bold button
        self.boldButton = TextToolButton(self, "B", name="bold", checkable=True)
        self.horizontallayout.addWidget(self.boldButton)

        # Italic button
        self.italicButton = TextToolButton(self, "I", name="italic", checkable=True)
        self.horizontallayout.addWidget(self.italicButton)

        # Underline button
        self.underlineButton = TextToolButton(self, "U", name="underline", checkable=True)
        self.horizontallayout.addWidget(self.underlineButton)

        # Strike-out button
        self.strikeButton = TextToolButton(self, "S", name="strike", checkable=True)
        self.horizontallayout.addWidget(self.strikeButton)

        # Text color button
        self.colorButton = ColorButton(self)
        self.colorButton.setText("T")
        self.horizontallayout.addWidget(self.colorButton)

        # --------------------------------------------------
        # Text Editor
        # --------------------------------------------------
        self.textEdit = QtWidgets.QTextEdit(self)
        self.textEdit.setPlaceholderText("Type here...")
        # self.textEdit.setMinimumSize(QtCore.QSize(590, 0))

        self.verticallayout.addWidget(self.textEdit)

        # --------------------------------------------------
        # Button Row
        # --------------------------------------------------
        self.horizontalayout2 = HorizontalLayout(None, space=5, margins=(5, 5, 5, 5))
        self.verticallayout.addLayout(self.horizontalayout2)

        # Push buttons to right side
        self.horizontalspacer = HorizontalSpacer()
        self.horizontalayout2.addItem(self.horizontalspacer)

        # Close button
        self.closeButton = TextButton(self, label="Close")
        self.horizontalayout2.addWidget(self.closeButton)

        # Apply button
        self.applyButton = TextButton(self, label="Apply and Close")
        self.horizontalayout2.addWidget(self.applyButton)

        # --------------------------------------------------
        # Footer
        # --------------------------------------------------
        self.copyrightLabel = CopyrightLabel(self)
        self.verticallayout.addWidget(self.copyrightLabel)

        # --------------------------------------------------
        # Connections
        # --------------------------------------------------
        self.boldButton.clicked.connect(self.updateValues)
        self.italicButton.clicked.connect(self.updateValues)
        self.underlineButton.clicked.connect(self.updateValues)
        self.strikeButton.clicked.connect(self.updateValues)

        self.fontSizeSpinBox.valueChanged.connect(self.updateValues)
        self.colorButton.color_changed.connect(self.updateValues)

        self.closeButton.clicked.connect(self.close)
        self.applyButton.clicked.connect(self.apply)

        # Initialize values
        self.updateValues()

    def updateValues(self, *args):
        """
        Update current font settings.

        Collects all current UI state and stores
        the values in a dictionary for later use.
        """

        # Current selected font
        current_font = self.fontComboBox.currentFont()

        # Update bold button appearance
        font = self.boldButton.font()
        font.setBold(self.boldButton.isChecked())
        self.boldButton.setFont(font)

        # Update italic button appearance
        font = self.italicButton.font()
        font.setItalic(self.italicButton.isChecked())
        self.italicButton.setFont(font)

        # Update underline button appearance
        font = self.underlineButton.font()
        font.setUnderline(self.underlineButton.isChecked())
        self.underlineButton.setFont(font)

        # Update strike button appearance
        font = self.strikeButton.font()
        font.setStrikeOut(self.strikeButton.isChecked())
        self.strikeButton.setFont(font)

        size = self.fontSizeSpinBox.value()

        # Store formatting values
        self.values = {
            "family": current_font.family(),
            "bold": self.boldButton.isChecked(),
            "italic": self.italicButton.isChecked(),
            "underline": self.underlineButton.isChecked(),
            "strike_out": self.strikeButton.isChecked(),
            "font_size": self.fontSizeSpinBox.value(),
            "color": self.colorButton.color,
            "txt": self.textEdit.toPlainText(),
        }

    def apply(self):
        """
        Apply current settings and close dialog.

        Emits value_changed signal containing the
        current text formatting configuration.
        """

        # Refresh values before emitting
        self.updateValues()

        # Emit settings
        self.value_changed.emit("txt", True, self.values)

        # Close dialog with Accepted state
        self.accept()


if __name__ == "__main__":
    pass
