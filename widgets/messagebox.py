"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/messagebox.py

Description:
    Provides a simplified wrapper around Qt QMessageBox for displaying standard application messages and collecting user responses.

Responsibilities:
    - Display information messages.
    - Display warning messages.
    - Display critical error messages.
    - Display question dialogs.
    - Configure standard dialog buttons.
    - Return user response selection.

Features:
    - Information dialogs.
    - Warning dialogs.
    - Critical dialogs.
    - Question dialogs.
    - Multiple button configurations.
    - Optional standalone styling support.

Architecture:
    Application Event
        ↓
    MessageBox
        ↓
    Message Type
        ├── Question
        ├── Information
        ├── Warning
        └── Critical
        ↓
    QMessageBox
        ↓
    User Response

Notes:
    - Supports standard Qt message box buttons.
    - Stores selected button result in replay.
    - Applies application stylesheet when no parent
      widget is supplied.
"""

from __future__ import absolute_import

from PySide6 import QtWidgets

from widgets.styles import SetStylesheet


class MessageBox(QtWidgets.QMessageBox):
    """Class for adding messageboxes.

    Args:
        typed(str),message(str),buttons(str)
        Maximum of 4 buttons can be given as arguments.

    Returns:
        None

    Examples:
        msgbox = MessageBox("Question", "Do you want to save file?", ["Yes", "No"])
        msgbox = MessageBox(domainTree.parent(), "Critical", stageContext["message"], ["Close"])
    """

    def __init__(self, parent, typed, message, buttons=None, **kwargs):
        """
        Initialize message box.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

            typed (str):
                Message type.

                Supported values:
                    - Question
                    - Information
                    - Warning
                    - Critical

            message (str):
                Message text displayed to the user.

            buttons (list[str], optional):
                List of button names.

                Supported values:
                    - Ok
                    - Yes
                    - No
                    - Save
                    - Cancel
                    - Close
                    - Retry

            **kwargs:
                Additional optional arguments.
        """

        # Initialize QMessageBox
        super(MessageBox, self).__init__(parent)

        # Default button collection
        buttons = buttons or list()

        # Apply application theme when running without a parent widget
        if not parent:
            SetStylesheet(self, theme=constants.GUI_THEMES[0])

        # Convert string button names into Qt button enums
        msg = list()
        for button in buttons:
            if button == "Ok":
                msg.append(QtWidgets.QMessageBox.Ok)
            if button == "Yes":
                msg.append(QtWidgets.QMessageBox.Yes)
            if button == "Save":
                msg.append(QtWidgets.QMessageBox.Save)
            if button == "Cancel":
                msg.append(QtWidgets.QMessageBox.Cancel)
            if button == "Close":
                msg.append(QtWidgets.QMessageBox.Close)
            if button == "Retry":
                msg.append(QtWidgets.QMessageBox.Retry)
            if button == "No":
                msg.append(QtWidgets.QMessageBox.No)

        # --------------------------------------------------
        # Display Message
        # --------------------------------------------------

        # Question dialog
        if typed == "Question":
            self.replay = self.question(self, "Question", message, *msg)

        # Information dialog
        if typed == "Information":
            self.replay = self.information(self, "Information", message, *msg)

        # Warning dialog
        if typed == "Warning":
            self.replay = self.warning(self, "Warning", message, *msg)

        # Critical dialog
        if typed == "Critical":
            self.replay = self.critical(self, "Critical", message, *msg)

    def getResult(self):
        """
        Return selected user response.

        Returns:
            QtWidgets.QMessageBox.StandardButton:
                Selected button value.
        """

        return self.replay


if __name__ == "__main__":
    pass
